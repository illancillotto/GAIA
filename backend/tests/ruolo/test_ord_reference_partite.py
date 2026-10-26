import uuid

from app.modules.ruolo.models import RuoloAvviso, RuoloImportJob, RuoloPartita
from app.modules.ruolo.services.ord_reference_partite import (
    ord_cnc_prefix,
    partite_source_avviso_id,
)

from .test_tributi_api import TestingSessionLocal
from .test_tributi_api import setup_database as setup_database

TAX_CODE = "00721660959"


def _avviso(
    db, cnc: str, *, year: int = 2021, tax_code: str | None = TAX_CODE, partita: bool = False
) -> uuid.UUID:
    job = RuoloImportJob(id=uuid.uuid4(), anno_tributario=year, status="completed")
    avviso = RuoloAvviso(
        id=uuid.uuid4(),
        import_job_id=job.id,
        codice_cnc=cnc,
        anno_tributario=year,
        codice_fiscale_raw=tax_code,
    )
    db.add_all([job, avviso])
    if partita:
        db.add(RuoloPartita(avviso_id=avviso.id, codice_partita=f"P-{cnc}", comune_nome="ARBOREA"))
    db.commit()
    return avviso.id


def test_list_b_avviso_borrows_the_same_year_ord_partite() -> None:
    assert ord_cnc_prefix(2021) == "01.020210"
    with TestingSessionLocal() as db:
        list_b = _avviso(db, "01.02021780106258")
        ord_avviso = _avviso(
            db, "01.02021000074364", tax_code=f" {TAX_CODE.lower()} ", partita=True
        )
        _avviso(db, "01.72021700000378", partita=True)  # list 2021.99: not ORD
        _avviso(db, "01.02020000074364", year=2020, partita=True)  # other year
        assert partite_source_avviso_id(db, list_b) == ord_avviso
        assert partite_source_avviso_id(db, ord_avviso) == ord_avviso


def test_avvisi_without_reference_keep_their_own_id() -> None:
    with TestingSessionLocal() as db:
        alone = _avviso(db, "01.02021780000001", tax_code="RSSMRA80A01H501Z")
        no_tax_code = _avviso(db, "01.02021780000002", tax_code=None)
        missing = uuid.uuid4()
        assert partite_source_avviso_id(db, alone) == alone
        assert partite_source_avviso_id(db, no_tax_code) == no_tax_code
        assert partite_source_avviso_id(db, missing) == missing
