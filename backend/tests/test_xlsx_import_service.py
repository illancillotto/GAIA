from __future__ import annotations

from datetime import date, datetime
from io import BytesIO
from uuid import uuid4

import pytest
from openpyxl import Workbook
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.core.security import hash_password
from app.models.application_user import ApplicationUser, ApplicationUserRole
from app.modules.utenze.models import (
    AnagraficaAuditLog,
    AnagraficaCompany,
    AnagraficaPerson,
    AnagraficaPersonSnapshot,
    AnagraficaSubject,
    AnagraficaSubjectStatus,
    AnagraficaXlsxImportBatch,
    AnagraficaXlsxImportBatchStatus,
)
from app.modules.utenze.services import xlsx_import_service as service


engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
TEST_TABLES = [
    ApplicationUser.__table__,
    AnagraficaSubject.__table__,
    AnagraficaPerson.__table__,
    AnagraficaPersonSnapshot.__table__,
    AnagraficaCompany.__table__,
    AnagraficaAuditLog.__table__,
    AnagraficaXlsxImportBatch.__table__,
]


def setup_function() -> None:
    Base.metadata.drop_all(bind=engine, tables=TEST_TABLES)
    Base.metadata.create_all(bind=engine, tables=TEST_TABLES)


def _create_user(db: Session, *, username: str = "xlsx-admin") -> ApplicationUser:
    user = ApplicationUser(
        username=username,
        email=f"{username}@example.local",
        password_hash=hash_password("secret123"),
        role=ApplicationUserRole.ADMIN.value,
        is_active=True,
        module_utenze=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _create_batch(db: Session, user: ApplicationUser, *, filename: str = "input.xlsx") -> AnagraficaXlsxImportBatch:
    batch = AnagraficaXlsxImportBatch(
        requested_by_user_id=user.id,
        filename=filename,
        status=AnagraficaXlsxImportBatchStatus.PENDING.value,
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)
    return batch


def _xlsx_bytes(rows: list[list[object]]) -> bytes:
    wb = Workbook()
    ws = wb.active
    for row in rows:
        ws.append(row)
    out = BytesIO()
    wb.save(out)
    return out.getvalue()


def test_parse_xlsx_and_helper_functions_cover_supported_shapes() -> None:
    with pytest.raises(ValueError, match="privo di intestazione"):
        service._parse_xlsx(_xlsx_bytes([]))

    file_bytes = _xlsx_bytes(
        [
            ["Denominazione", "Nome", "Tipo", "Dat. nas.", "Topon. res.", "Indir. res.", "Civico res.", "Città res.", "Prov. res.", "Stato"],
            [" Rossi Mario ", "Mario", "F", "01/02/2026", "Via", "Roma", "1", "Oristano", "or", "attivo"],
        ]
    )
    rows = service._parse_xlsx(file_bytes)
    assert rows == [
        {
            "denominazione": "Rossi Mario",
            "nome": "Mario",
            "tipo": "F",
            "data_nascita": "01/02/2026",
            "topon_res": "Via",
            "indirizzo_res": "Roma",
            "civico_res": "1",
            "citta_res": "Oristano",
            "prov_res": "or",
            "stato": "attivo",
        }
    ]

    assert service._clean("  abc  ") == "abc"
    assert service._clean(None) is None
    assert service._normalize_id(" ab cd 12 ") == "ABCD12"
    assert service._normalize_id("a") == ""
    assert service._parse_date(datetime(2026, 6, 22, 12, 0)) == date(2026, 6, 22)
    assert service._parse_date(date(2026, 6, 23)) == date(2026, 6, 23)
    assert service._parse_date("24/06/2026") == date(2026, 6, 24)
    assert service._parse_date("2026-06-25") == date(2026, 6, 25)
    assert service._parse_date("26-06-2026") == date(2026, 6, 26)
    assert service._parse_date("bad") is None
    assert service._build_address({"topon_res": "Via", "indirizzo_res": "Roma", "civico_res": "1"}) == "Via Roma 1"
    assert service._build_city("Oristano", "or") == "Oristano (OR)"
    assert service._build_city(None, "or") == "or"
    assert service._resolve_status({"stato": "deceduto"}) == AnagraficaSubjectStatus.INACTIVE.value
    assert service._resolve_status({"stato": "attivo"}) == AnagraficaSubjectStatus.ACTIVE.value
    assert service._derive_letter("  1beta") == "B"
    assert service._derive_letter(" 123 ") is None
    assert service._build_address_dom({"topon_dom": "Piazza", "indirizzo_dom": "Italia", "civico_dom": "2", "citta_dom": "Oristano", "prov_dom": "OR"}) == "Piazza Italia 2 Oristano (OR)"
    assert service._build_person_note({"sesso": "M", "stato": "attivo", "topon_dom": "Piazza"}) == "Sesso: M\nStato: attivo\nDomicilio: Piazza"
    assert service._build_company_note({"stato": "Cessato"}) == "Stato: Cessato"
    assert service._build_company_note({}) is None
    assert service._safe_row({"a": 1, "b": None}) == {"a": "1", "b": None}
    assert service.row_number_from_cf("ABC") == "ABC"
    hashed = service._hash_dict({"b": 1, "a": datetime(2026, 6, 22, 10, 0)})
    assert isinstance(hashed, str)
    assert service._json_safe({"d": date(2026, 6, 22), "x": 1}) == {"d": "2026-06-22", "x": 1}


def test_upsert_person_insert_unchanged_update_and_lookup_helpers() -> None:
    with TestingSessionLocal() as db:
        user = _create_user(db)
        row = {
            "tipo": "F",
            "cognome": "Rossi",
            "nome": "Mario",
            "codice_fiscale": "RSSMRA80A01H501Z",
            "data_nascita": "01/01/1980",
            "luogo_nascita": "Oristano",
            "indirizzo_res": "Roma",
            "civico_res": "1",
            "citta_res": "Oristano",
            "prov_res": "OR",
            "cap_res": "09170",
            "email": "mario@example.local",
            "mobile": "333",
            "sesso": "M",
            "stato": "attivo",
        }

        assert service._upsert_person(db, row, "RSSMRA80A01H501Z", user) == "inserted"
        db.commit()

        person = service._find_person_by_cf(db, "RSSMRA80A01H501Z")
        assert person is not None
        subject = db.get(AnagraficaSubject, person.subject_id)
        assert subject is not None
        assert subject.subject_type == "person"
        assert subject.nas_folder_letter == "R"
        assert person.comune_residenza == "Oristano (OR)"
        assert service._person_snapshot(person)["codice_fiscale"] == "RSSMRA80A01H501Z"

        assert service._upsert_person(db, row, "RSSMRA80A01H501Z", user) == "unchanged"
        db.commit()

        updated_row = dict(row, email="mario2@example.local", telefono="070", stato="deceduto")
        assert service._upsert_person(db, updated_row, "RSSMRA80A01H501Z", user) == "updated"
        db.commit()

        db.refresh(person)
        db.refresh(subject)
        snapshots = db.query(AnagraficaPersonSnapshot).filter_by(subject_id=person.subject_id).all()
        audits = db.query(AnagraficaAuditLog).filter_by(subject_id=person.subject_id).all()

        assert person.email == "mario2@example.local"
        assert subject.status == AnagraficaSubjectStatus.INACTIVE.value
        assert len(snapshots) == 1
        assert {item.action for item in audits} == {"xlsx_import_created", "xlsx_import_updated"}


def test_upsert_company_insert_unchanged_update_and_find_company() -> None:
    with TestingSessionLocal() as db:
        user = _create_user(db)
        row = {
            "tipo": "G",
            "denominazione": "ACME SRL",
            "partita_iva": "01234567890",
            "codice_fiscale": "01234567890",
            "indirizzo_res": "Milano",
            "civico_res": "10",
            "citta_res": "Cagliari",
            "prov_res": "ca",
            "cap_res": "09100",
            "email": "info@acme.local",
            "pec": "pec@acme.local",
            "telefono": "0783",
            "stato": "attivo",
        }

        assert service._upsert_company(db, row, "01234567890", "01234567890", user) == "inserted"
        db.commit()

        company = service._find_company(db, "01234567890", "01234567890")
        assert company is not None
        subject = db.get(AnagraficaSubject, company.subject_id)
        assert subject is not None
        assert company.email_pec == "pec@acme.local"
        assert company.codice_fiscale is None
        assert service._company_snapshot(company)["ragione_sociale"] == "ACME SRL"

        assert service._upsert_company(db, row, "01234567890", "01234567890", user) == "unchanged"
        db.commit()

        updated_row = dict(row, pec=None, email="mail@acme.local", telefono="070", stato="cessato")
        assert service._upsert_company(db, updated_row, "01234567890", "01234567890", user) == "updated"
        db.commit()

        db.refresh(company)
        db.refresh(subject)
        audits = db.query(AnagraficaAuditLog).filter_by(subject_id=company.subject_id).all()

        assert company.email_pec == "mail@acme.local"
        assert company.telefono == "070"
        assert subject.status == AnagraficaSubjectStatus.INACTIVE.value
        assert {item.action for item in audits} == {"xlsx_import_created", "xlsx_import_updated"}
        assert service._find_company(db, "01234567890", None) is not None


def test_upsert_anomaly_and_process_chunk_error_tracking(monkeypatch: pytest.MonkeyPatch) -> None:
    with TestingSessionLocal() as db:
        user = _create_user(db)
        anomaly_row = {"denominazione": "Soggetto senza id"}
        assert service._upsert_anomaly(db, anomaly_row, 12, user) == "anomaly"
        db.commit()

        anomaly_subject = db.query(AnagraficaSubject).filter_by(source_external_id=service.ANOMALIA_EXTERNAL_ID).one()
        anomaly_audit = db.query(AnagraficaAuditLog).filter_by(subject_id=anomaly_subject.id).one()
        assert anomaly_subject.requires_review is True
        assert anomaly_audit.action == "xlsx_import_anomaly"

        result = service.XlsxImportResult(batch_id=uuid4())
        calls = iter(["inserted", "updated", "unchanged", "anomaly", RuntimeError("bad row")])

        def fake_upsert_row(current_db, row, row_number, current_user):
            value = next(calls)
            if isinstance(value, Exception):
                raise value
            return value

        monkeypatch.setattr(service, "_upsert_row", fake_upsert_row)
        service._process_chunk(
            db,
            [{"denominazione": "A"}, {"denominazione": "B"}, {"denominazione": "C"}, {"denominazione": "D"}, {"denominazione": "E"}],
            0,
            user,
            result,
        )

        assert result.inserted == 1
        assert result.updated == 1
        assert result.unchanged == 1
        assert result.anomalies == 1
        assert result.errors == 1
        assert result.error_log[0]["row"] == 6


def test_upsert_row_dispatch_and_integrityerror_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    with TestingSessionLocal() as db:
        user = _create_user(db)

        assert service._upsert_row(db, {"tipo": "F", "denominazione": "X"}, 7, user) == "anomaly"
        db.commit()

        calls = {"person": 0, "company": 0}
        fake_person = object()
        fake_company = object()

        def boom_person(current_db, row, cf, current_user):
            calls["person"] += 1
            if calls["person"] == 1:
                raise IntegrityError("stmt", "params", Exception("orig"))
            return "updated"

        def boom_company(current_db, row, cf, piva, current_user):
            calls["company"] += 1
            if calls["company"] == 1:
                raise IntegrityError("stmt", "params", Exception("orig"))
            return "updated"

        monkeypatch.setattr(service, "_upsert_person", boom_person)
        monkeypatch.setattr(service, "_upsert_company", boom_company)
        monkeypatch.setattr(service, "_find_person_by_cf", lambda current_db, cf: fake_person)
        monkeypatch.setattr(service, "_find_company", lambda current_db, cf, piva: fake_company)

        person_row = {"tipo": "F", "codice_fiscale": "ABCD1234"}
        company_row = {"tipo": "G", "partita_iva": "01234567890"}

        assert service._upsert_row(db, person_row, 2, user) == "updated"
        assert service._upsert_row(db, company_row, 3, user) == "updated"
        assert calls == {"person": 2, "company": 2}


def test_run_xlsx_import_happy_path_and_failed_path(monkeypatch: pytest.MonkeyPatch) -> None:
    with TestingSessionLocal() as db:
        user = _create_user(db)
        batch = _create_batch(db, user, filename="ok.xlsx")
        rows = [{"denominazione": "A"}, {"denominazione": "B"}]

        monkeypatch.setattr(service, "_parse_xlsx", lambda file_bytes: rows)

        def fake_process_chunk(current_db, chunk, chunk_start, current_user, result):
            assert current_db is db
            assert current_user.id == user.id
            result.inserted += len(chunk)

        monkeypatch.setattr(service, "_process_chunk", fake_process_chunk)

        service.run_xlsx_import(db, batch.id, b"file", user)
        db.refresh(batch)

        assert batch.status == AnagraficaXlsxImportBatchStatus.COMPLETED.value
        assert batch.total_rows == 2
        assert batch.processed_rows == 2
        assert batch.inserted == 2
        assert batch.completed_at is not None

        failed_batch = _create_batch(db, user, filename="fail.xlsx")
        monkeypatch.setattr(service, "_parse_xlsx", lambda file_bytes: (_ for _ in ()).throw(RuntimeError("fatal boom")))

        service.run_xlsx_import(db, failed_batch.id, b"file", user)
        db.refresh(failed_batch)

        assert failed_batch.status == AnagraficaXlsxImportBatchStatus.FAILED.value
        assert failed_batch.errors == 0
        assert failed_batch.error_log[0]["message"] == "Errore fatale: fatal boom"
