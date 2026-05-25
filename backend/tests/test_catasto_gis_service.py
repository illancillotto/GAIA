from __future__ import annotations

import uuid
from collections.abc import Generator
from datetime import date, datetime, timezone
import sys
import types

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.catasto_phase1 import CatImportBatch, CatParticella, CatUtenzaIrrigua
from app.modules.ruolo.models import RuoloAvviso, RuoloParticella, RuoloPartita


shapely_module = types.ModuleType("shapely")
shapely_geometry_module = types.ModuleType("shapely.geometry")
shapely_geometry_module.shape = lambda geometry: geometry
shapely_module.geometry = shapely_geometry_module
sys.modules.setdefault("shapely", shapely_module)
sys.modules.setdefault("shapely.geometry", shapely_geometry_module)

from app.modules.catasto.services.gis_service import _load_particella_ruolo_summary, _search_particelle_by_tax_code


engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


@pytest.fixture(autouse=True)
def setup_database() -> Generator[None, None, None]:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def _add_particella(
    db,
    *,
    foglio: str,
    particella: str,
    created_at: datetime,
    with_ruolo: bool = False,
) -> str:
    batch_id = uuid.uuid4()
    db.add(
        CatImportBatch(
            id=batch_id,
            filename=f"batch-{foglio}-{particella}.csv",
            tipo="utenze",
            anno_campagna=2025,
            status="completed",
        )
    )
    particella_id = uuid.uuid4()
    db.add(
        CatParticella(
            id=particella_id,
            cod_comune_capacitas=95,
            codice_catastale="A357",
            nome_comune="ARBOREA",
            foglio=foglio,
            particella=particella,
            source_type="test",
            import_batch_id=batch_id,
            valid_from=date(2025, 1, 1),
            is_current=True,
            suppressed=False,
            created_at=created_at,
            updated_at=created_at,
        )
    )
    db.add(
        CatUtenzaIrrigua(
            id=uuid.uuid4(),
            import_batch_id=batch_id,
            anno_campagna=2025,
            particella_id=particella_id,
            codice_fiscale="03122560927",
            created_at=created_at,
        )
    )
    if with_ruolo:
        db.add(
            RuoloParticella(
                id=uuid.uuid4(),
                partita_id=uuid.uuid4(),
                anno_tributario=2025,
                foglio=foglio,
                particella=particella,
                cat_particella_id=particella_id,
            )
        )
    db.flush()
    return str(particella_id)


def test_search_particelle_prioritizes_ruolo_for_tax_code() -> None:
    db = TestingSessionLocal()
    try:
        older_role_id = _add_particella(
            db,
            foglio="1",
            particella="10",
            created_at=datetime(2025, 1, 10, tzinfo=timezone.utc),
            with_ruolo=True,
        )
        newest_non_role_id = _add_particella(
            db,
            foglio="2",
            particella="20",
            created_at=datetime(2025, 3, 10, tzinfo=timezone.utc),
            with_ruolo=False,
        )
        middle_non_role_id = _add_particella(
            db,
            foglio="3",
            particella="30",
            created_at=datetime(2025, 2, 10, tzinfo=timezone.utc),
            with_ruolo=False,
        )
        db.commit()

        result_ids = _search_particelle_by_tax_code(db, "03122560927", 3)

        assert result_ids == [
            older_role_id,
            newest_non_role_id,
            middle_non_role_id,
        ]
    finally:
        db.close()


def test_load_particella_ruolo_summary_falls_back_to_subject_comune_match() -> None:
    db = TestingSessionLocal()
    try:
        particella_id = uuid.UUID(
            _add_particella(
                db,
                foglio="9",
                particella="99",
                created_at=datetime(2025, 4, 10, tzinfo=timezone.utc),
                with_ruolo=False,
            )
        )
        avviso_id = uuid.uuid4()
        db.add(
            RuoloAvviso(
                id=avviso_id,
                import_job_id=uuid.uuid4(),
                codice_cnc="01.02025009999999",
                anno_tributario=2025,
                codice_fiscale_raw="03122560927",
                nominativo_raw="LAORE SARDEGNA",
            )
        )
        db.add(
            RuoloPartita(
                id=uuid.uuid4(),
                avviso_id=avviso_id,
                codice_partita="000000402/00000",
                comune_nome="ARBOREA",
                contribuente_cf="03122560927",
                importo_0648=17288.12,
                importo_0985=12346.56,
            )
        )
        db.commit()

        particella = db.get(CatParticella, particella_id)
        assert particella is not None

        summary = _load_particella_ruolo_summary(db, particella)

        assert summary is not None
        assert summary.source_mode == "subject_comune_fallback"
        assert summary.n_righe == 1
        assert summary.importo_manut_euro_totale == 17288.12
        assert summary.importo_ist_euro_totale == 12346.56
        assert summary.importo_totale_euro == 29634.68
        assert summary.items[0].codice_partita == "000000402/00000"
    finally:
        db.close()
