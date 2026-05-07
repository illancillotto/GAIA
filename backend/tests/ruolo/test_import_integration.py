import asyncio
from collections.abc import Generator

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.db.base import Base
from app.models.application_user import ApplicationUser, ApplicationUserRole
from app.models.catasto import CatastoComune
from app.modules.ruolo.models import RuoloAvviso, RuoloImportJob, RuoloParticella, RuoloPartita
from app.modules.ruolo.services import import_service as import_service_module
from app.modules.ruolo.services.import_service import create_import_job
from app.modules.utenze.models import AnagraficaPerson, AnagraficaSubject


SQLALCHEMY_DATABASE_URL = "sqlite://"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


REALISTIC_IMPORT_SAMPLE = """\
<qm500>--Partita CNC 01.02025000405275------------------------------------------<017.743><01.A><02025000405275><inizio>
N2 PDDNMR53T54I384H 00000000 00 N
PODDIGHE ANNA MARIA 14.12.1953 I384 SAN VERO MILIS(OR)
Dom: VIA REGINA ELENA, 52 00000 09070 I384 SAN VERO MILIS(OR)
Res: 00000 00000 ( )
NP   4 PARTITA 000002624/00000 BENI IN COMUNE DI SAN VERO MILIS
NP   5 CONTRIBUENTE: PODDIGHE ANNA MARIA                          C.F. PDDNMR53T54I384H
NP   8 2025 0648 BENI IN SAN VERO MILIS - CONTRIBUTO OPERE IRRIGUE           30,00 EURO
NP   9 2025 0668 BENI IN SAN VERO MILIS - CONTRIBUTO UTENZA                  70,00 EURO
NP  10 2025 0985 BENI IN SAN VERO MILIS - CONSORZIO QUOTE ORDINARIE          20,00 EURO
NP  11 DOM. DIS. FOG. PART.  SUB SUP.CATA.  SUP.IRR. COLT.     MANUT.   IRRIG.     IST.
NP  12         4    9   877    I       805                       2,94              2,10
NP  13 1111    4    9   877    I       834       834 FRUTTETO             3,40
NP  14         2   13   231    A       824                       3,01              2,15
N4
   2025 0668        83.400           70,00    (L.       135.539 )
   OPERE DI BONIFICA (UTENZA 025004052)
N4
   2025 0648       195.480           30,00    (L.        58.088 )
   OPERE DI BONIFICA (UTENZA 025004052)
N4
   2025 0985       195.480           20,00    (L.        38.725 )
   OPERE DI BONIFICA (UTENZA 025004052)
--------------------------------------------------------------------------------<017.743><01.A><02025000405275><-fine->

---------Partita CNC 01.02025000263011------------------------------------------<097.173><01.A><02025000263011><inizio>
N2 E                00000000 00 N
ERDAS EFISIO
Dom: VIA MANNU 46 00000 09070 A721 BAULADU(OR)
Res: 00000 00000 ( )
NP   4 PARTITA 000000101/00000 BENI IN COMUNE DI BAULADU
NP   5 CONTRIBUENTE: ERDAS EFISIO                              C.F. E
NP   8 2025 0648 BENI IN BAULADU - CONTRIBUTO OPERE IRRIGUE            12,00 EURO
NP   9 2025 0985 BENI IN BAULADU - CONSORZIO QUOTE ORDINARIE            6,00 EURO
NP  10 DOM. DIS. FOG. PART.  SUB SUP.CATA.  SUP.IRR. COLT.     MANUT.   IRRIG.     IST.
NP  11         1    3   220            150                       0,55              0,39
N4
   2025 0648        20.000           12,00    (L.        23.235 )
   OPERE DI BONIFICA (UTENZA 025002630)
N4
   2025 0985        20.000            6,00    (L.        11.617 )
   OPERE DI BONIFICA (UTENZA 025002630)
--------------------------------------------------------------------------------<097.173><01.A><02025000263011><-fine->

---------Partita CNC 01.02025000634843------------------------------------------<017.743><01.A><02025000634843><inizio>
N2 SRRDNC42A05M153H 00000000 00 N
SERRA DOMENICO FELICE 05.01.1942 M153 ZEDDIANI(OR)
Dom: VIA ROMA 00112 09070 M153 ZEDDIANI(OR)
Res: 00000 00000 ( )
NP   4 PARTITA 000000548/00000 BENI IN COMUNE DI ZEDDIANI
NP   5 CONTRIBUENTE: SERRA DOMENICO FELICE                        C.F. SRRDNC42A05M153H
NP   7 2025 0648 BENI IN ZEDDIANI - CONTRIBUTO OPERE IRRIGUE                 35,24 EURO
NP   8 2025 0668 BENI IN ZEDDIANI - CONTRIBUTO UTENZA                        70,00 EURO
NP   9 2025 0985 BENI IN ZEDDIANI - CONSORZIO QUOTE ORDINARIE                25,17 EURO
NP  10 DOM. DIS. FOG. PART.  SUB SUP.CATA.  SUP.IRR. COLT.     MANUT.   IRRIG.     IST.
NP  11         7    8   752          1.870                       6,83              4,87
NP  12         7    9    27    A     5.565                      20,31             14,51
NP  16 CONSUMI DA CONTATORE:      908,000 MC    IMPOSTA:      10,90 EURO (TRIBUTO 0668)
NP  17 ANNO DOMANDA DISTRETTO SUP.DOMANDA CONTATORE  SERIALE    TESSERA   CONSUMO (MC)
NP  18 2025    1539         7             1846000490                           908,000
N4
   2025 0668        90.800           70,00    (L.       135.539 )
   OPERE DI BONIFICA (UTENZA 025006348)
N4
   2025 0648     1.419.840           35,24    (L.        83.628 )
   OPERE DI BONIFICA (UTENZA 025006348)
N4
   2025 0985     1.419.840           25,17    (L.        59.715 )
   OPERE DI BONIFICA (UTENZA 025006348)
--------------------------------------------------------------------------------<017.743><01.A><02025000634843><-fine->
"""


@pytest.fixture(autouse=True)
def setup_database(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    monkeypatch.setattr(import_service_module, "SessionLocal", TestingSessionLocal)

    db = TestingSessionLocal()
    db.add(
        ApplicationUser(
            username="ruolo-integration-admin",
            email="ruolo-integration@example.local",
            password_hash=hash_password("secret123"),
            role=ApplicationUserRole.ADMIN.value,
            is_active=True,
            module_ruolo=True,
        )
    )
    db.add_all(
        [
            CatastoComune(nome="SAN VERO MILIS", codice_sister="I384#SAN VERO MILIS#0#0", ufficio="ORISTANO Territorio"),
            CatastoComune(nome="BAULADU", codice_sister="A721", ufficio="ORISTANO Territorio"),
            CatastoComune(nome="ZEDDIANI", codice_sister="M153", ufficio="ORISTANO Territorio"),
        ]
    )

    subject_1 = AnagraficaSubject(source_name_raw="PODDIGHE ANNA MARIA", subject_type="person", source_system="gaia")
    subject_2 = AnagraficaSubject(source_name_raw="SERRA DOMENICO FELICE", subject_type="person", source_system="gaia")
    db.add_all([subject_1, subject_2])
    db.flush()
    db.add_all(
        [
            AnagraficaPerson(
                subject_id=subject_1.id,
                cognome="PODDIGHE",
                nome="ANNA MARIA",
                codice_fiscale="PDDNMR53T54I384H",
            ),
            AnagraficaPerson(
                subject_id=subject_2.id,
                cognome="SERRA",
                nome="DOMENICO FELICE",
                codice_fiscale="SRRDNC42A05M153H",
            ),
        ]
    )
    db.commit()
    db.close()

    yield

    Base.metadata.drop_all(bind=engine)


def test_run_import_job_with_realistic_2025_blocks_exercises_parser_and_report(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = TestingSessionLocal()
    job = create_import_job(
        db,
        anno_tributario=2025,
        filename="R2025.14215.integration-sample.dmp",
        triggered_by=1,
    )
    db.commit()
    job_id = job.id
    db.close()

    monkeypatch.setattr(import_service_module, "extract_text_from_content", lambda *_args, **_kwargs: REALISTIC_IMPORT_SAMPLE)

    asyncio.run(
        import_service_module.run_import_job(
            job_id,
            REALISTIC_IMPORT_SAMPLE.encode("latin1", errors="ignore"),
            2025,
            filename="R2025.14215.integration-sample.dmp",
        )
    )

    db = TestingSessionLocal()
    try:
        saved_job = db.get(RuoloImportJob, job_id)
        assert saved_job is not None
        assert saved_job.status == "completed"
        assert saved_job.total_partite == 3
        assert saved_job.records_imported == 2
        assert saved_job.records_skipped == 1
        assert saved_job.records_errors == 0
        assert saved_job.params_json is not None
        assert saved_job.params_json["report_summary"]["records_imported"] == 2
        assert saved_job.params_json["report_preview"]["skipped_total_count"] == 1
        assert saved_job.params_json["report_preview"]["error_total_count"] == 0

        avvisi = db.scalars(select(RuoloAvviso).order_by(RuoloAvviso.codice_cnc.asc())).all()
        partite = db.scalars(select(RuoloPartita)).all()
        particelle = db.scalars(select(RuoloParticella).order_by(RuoloParticella.foglio.asc(), RuoloParticella.particella.asc())).all()

        assert len(avvisi) == 3
        assert len(partite) == 3
        assert len(particelle) == 5

        avviso_linked = next(item for item in avvisi if item.codice_cnc == "01.02025000405275")
        avviso_skipped = next(item for item in avvisi if item.codice_cnc == "01.02025000263011")
        avviso_consumi = next(item for item in avvisi if item.codice_cnc == "01.02025000634843")

        assert avviso_linked.subject_id is not None
        assert avviso_consumi.subject_id is not None
        assert avviso_skipped.subject_id is None

        skipped_items = saved_job.params_json["report_preview"]["skipped_items"]
        assert len(skipped_items) == 1
        assert skipped_items[0]["codice_cnc"] == "01.02025000263011"
        assert skipped_items[0]["reason_code"] == "subject_not_found"

        merged_particella = next(
            item
            for item in particelle
            if item.foglio == "9" and item.particella == "877" and item.subalterno == "I"
        )
        assert float(merged_particella.sup_catastale_are) == 834.0
        assert float(merged_particella.sup_irrigata_ha) == 834.0
        assert merged_particella.coltura == "FRUTTETO"
        assert float(merged_particella.importo_manut) == 2.94
        assert float(merged_particella.importo_irrig) == 3.40

        assert not any(item.foglio == "2025" for item in particelle)
        assert not any(item.particella == "1846000490" for item in particelle)
    finally:
        db.close()
