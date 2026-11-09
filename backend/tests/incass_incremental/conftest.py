"""All identities and workbooks in this suite are synthetic, never portal evidence."""

from datetime import UTC, datetime
from io import BytesIO
from uuid import uuid4

import pytest
from openpyxl import Workbook
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models.application_user import ApplicationUser
from app.models.capacitas import CapacitasCredential, CapacitasInCassSyncJob
from app.models.catasto import CatastoComune
from app.modules.elaborazioni.capacitas.incremental.config import IncrementalSettings
from app.modules.elaborazioni.capacitas.incremental.models import (
    IncrementalChange,
    IncrementalCycle,
    IncrementalHead,
)
from app.modules.elaborazioni.capacitas.incremental.normalize import KNOWN
from app.modules.ruolo.models import RuoloAvviso, RuoloImportJob, RuoloParticella, RuoloPartita
from app.modules.utenze.models import (
    AnagraficaCompany,
    AnagraficaPaymentNotice,
    AnagraficaPerson,
    AnagraficaSubject,
)

NOW = datetime(2026, 11, 9, 9, tzinfo=UTC)
CF = "TESTAA80A01H501A"
NOTICE = "020250000000001"
TABLES = [
    model.__table__
    for model in (
        ApplicationUser,
        CatastoComune,
        CapacitasCredential,
        CapacitasInCassSyncJob,
        AnagraficaSubject,
        AnagraficaPerson,
        AnagraficaCompany,
        AnagraficaPaymentNotice,
        RuoloImportJob,
        RuoloAvviso,
        RuoloPartita,
        RuoloParticella,
        IncrementalCycle,
        IncrementalHead,
        IncrementalChange,
    )
]


def raw_row(**overrides):
    row = dict.fromkeys(sorted(KNOWN))
    row.update(
        Avviso=NOTICE,
        Anno="2025",
        CodFisc=CF,
        ID="1",
        Denominaz="SOGGETTO TEST",
        Carico="1.000,00",
        Sgravio="0,00",
        Riscosso="0,00",
        Differenza="1.000,00",
        Riporto="0,00",
        Rateizzato="0,00",
        Annullato="0,00",
        StatoPag="0",
    )
    return {**row, **overrides}


def workbook(rows, headers=None, footer=False):
    book = Workbook()
    sheet = book.active
    headers = headers or sorted(KNOWN)
    sheet.append(headers)
    for row in rows:
        sheet.append([row.get(key) for key in headers])
    if footer:
        sheet.append(["\n" if key == "Reso" else None for key in headers])
    stream = BytesIO()
    book.save(stream)
    return stream.getvalue()


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    AnagraficaSubject.metadata.create_all(engine, tables=TABLES)
    with Session(engine, expire_on_commit=False) as session:
        session.add(IncrementalHead(id=1))
        session.add(CatastoComune(nome="TEST", codice_sister="T001"))
        session.commit()
        yield session
    engine.dispose()


@pytest.fixture
def config(tmp_path):
    return IncrementalSettings(mode="shadow", credential_id=123, root=tmp_path)


@pytest.fixture
def owner(db):
    subject = AnagraficaSubject(id=uuid4(), subject_type="person", source_name_raw="SOGGETTO TEST")
    db.add(subject)
    db.flush()
    db.add(
        AnagraficaPerson(subject_id=subject.id, cognome="Test", nome="Persona", codice_fiscale=CF)
    )
    db.commit()
    return subject
