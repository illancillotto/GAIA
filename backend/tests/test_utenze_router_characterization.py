import asyncio
import uuid
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.modules.utenze import router as router_facade
from app.modules.utenze.models import AnagraficaCompany, AnagraficaPerson
from app.modules.utenze.routes import bonifica, documents, imports, reporting, subjects, support
from app.modules.utenze.schemas import AnagraficaCompanyPayload, AnagraficaPersonPayload
from app.services.nas_connector import NasConnectorError


def _staging(**changes: object) -> SimpleNamespace:
    now = datetime.now(UTC)
    values = {
        "id": uuid.uuid4(),
        "wc_id": 7,
        "username": None,
        "email": None,
        "user_type": None,
        "business_name": None,
        "first_name": None,
        "last_name": None,
        "tax": None,
        "phone": None,
        "mobile": None,
        "role": None,
        "enabled": True,
        "wc_synced_at": now,
        "review_status": "new",
        "matched_subject_id": None,
        "mismatch_fields": None,
        "reviewed_by": None,
        "reviewed_at": None,
        "created_at": now,
        "updated_at": now,
    }
    values.update(changes)
    return SimpleNamespace(**values)


def test_dependency_and_close_hooks(monkeypatch: pytest.MonkeyPatch) -> None:
    connector = SimpleNamespace(close=MagicMock())
    monkeypatch.setattr(router_facade, "get_nas_client", lambda: connector)
    service = support.get_anagrafica_import_service()
    assert service.connector is connector
    support._close_import_service(service)
    connector.close.assert_called_once()
    support._close_import_service(SimpleNamespace(connector=SimpleNamespace()))


def test_registry_job_mutation_guards() -> None:
    job_id = uuid.uuid4()
    user = SimpleNamespace(id=2, is_super_admin=False)
    db = MagicMock()
    db.get.return_value = None
    with pytest.raises(HTTPException) as error:
        support._require_registry_import_job_for_mutation(db, job_id, user)
    assert error.value.status_code == 404

    db.get.return_value = SimpleNamespace(letter="A", requested_by_user_id=2)
    with pytest.raises(HTTPException) as error:
        support._require_registry_import_job_for_mutation(db, job_id, user)
    assert error.value.status_code == 409

    job = SimpleNamespace(letter="REGISTRY", requested_by_user_id=1)
    db.get.return_value = job
    with pytest.raises(HTTPException) as error:
        support._require_registry_import_job_for_mutation(db, job_id, user)
    assert error.value.status_code == 403
    user.is_super_admin = True
    assert support._require_registry_import_job_for_mutation(db, job_id, user) is job


def test_document_local_recovery_branches(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db = MagicMock()
    existing = tmp_path / "existing.pdf"
    existing.write_bytes(b"pdf")
    document = SimpleNamespace(
        id=uuid.uuid4(),
        subject_id=uuid.uuid4(),
        filename="../unsafe.pdf",
        local_path=str(existing),
        nas_path=None,
    )
    assert support._ensure_document_available_locally(db, document) == existing

    document.local_path = None
    with pytest.raises(HTTPException) as error:
        support._ensure_document_available_locally(db, document)
    assert error.value.status_code == 404

    monkeypatch.setattr(support.settings, "utenze_document_storage_path", str(tmp_path))
    document.nas_path = "/nas/file.pdf"
    connector = SimpleNamespace(download_file=lambda _: b"recovered", close=MagicMock())
    monkeypatch.setattr(router_facade, "get_nas_client", lambda: connector)
    recovered = support._ensure_document_available_locally(db, document)
    assert recovered.read_bytes() == b"recovered"
    assert recovered.name.endswith("-unsafe.pdf")
    connector.close.assert_called_once()
    db.commit.assert_called_once()

    document.local_path = str(tmp_path / "missing.pdf")
    download_to_local = MagicMock(
        side_effect=lambda _remote, local: Path(local).write_bytes(b"direct")
    )
    connector = SimpleNamespace(download_to_local=download_to_local)
    monkeypatch.setattr(router_facade, "get_nas_client", lambda: connector)
    assert support._ensure_document_available_locally(db, document).read_bytes() == b"direct"

    connector = SimpleNamespace(download_file=MagicMock(side_effect=NasConnectorError("missing")))
    monkeypatch.setattr(router_facade, "get_nas_client", lambda: connector)
    document.local_path = str(tmp_path / "missing-again.pdf")
    with pytest.raises(HTTPException) as error:
        support._ensure_document_available_locally(db, document)
    assert error.value.status_code == 404

    connector = SimpleNamespace(download_file=lambda _: b"")
    monkeypatch.setattr(router_facade, "get_nas_client", lambda: connector)
    monkeypatch.setattr(Path, "write_bytes", lambda self, data: len(data))
    with pytest.raises(HTTPException) as error:
        support._ensure_document_available_locally(db, document)
    assert error.value.status_code == 404


@pytest.mark.parametrize(
    ("subject_type", "person", "company"),
    [
        ("person", None, None),
        ("company", None, None),
        ("person", object(), object()),
        ("company", object(), object()),
    ],
)
def test_subject_payload_validation_errors(
    subject_type: str, person: object, company: object
) -> None:
    with pytest.raises(HTTPException):
        support._validate_subject_payload(subject_type, person, company)
    support._validate_subject_payload(subject_type, None, None, allow_empty=True)


def test_apply_subject_payload_all_types(monkeypatch: pytest.MonkeyPatch) -> None:
    subject = SimpleNamespace(id=uuid.uuid4(), source_system=None, source_external_id=None)
    person_model = SimpleNamespace(old=True)
    company_model = SimpleNamespace(old=True)
    db = MagicMock()
    db.get.side_effect = lambda model, _id: (
        person_model if model is AnagraficaPerson else company_model
    )
    monkeypatch.setattr(support, "snapshot_person_if_changed", MagicMock())
    person = SimpleNamespace(model_dump=lambda: {"nome": "Ada", "cognome": "Lovelace"})
    company = SimpleNamespace(model_dump=lambda: {"ragione_sociale": "ACME"})
    support._apply_subject_payload(db, subject, "person", person, None)
    support._apply_subject_payload(db, subject, "company", None, company)
    support._apply_subject_payload(db, subject, "unknown", None, None)
    assert db.flush.call_count == 3
    assert db.delete.call_count == 4

    db.reset_mock()
    db.get.return_value = None
    db.get.side_effect = None
    support._apply_subject_payload(db, subject, "person", person, None)
    support._apply_subject_payload(db, subject, "company", None, company)
    support._apply_subject_payload(db, subject, "person", None, None)
    support._apply_subject_payload(db, subject, "company", None, None)
    db.get.side_effect = lambda model, _id: person_model if model is AnagraficaPerson else None
    support._apply_subject_payload(db, subject, "unknown", None, None)
    db.get.side_effect = lambda model, _id: company_model if model is AnagraficaCompany else None
    support._apply_subject_payload(db, subject, "unknown", None, None)


def test_query_and_duplicate_helpers() -> None:
    assert (
        support._build_subjects_query(" ada lovelace ", "person", "active", " a ", False)
        is not None
    )
    person = AnagraficaPersonPayload(cognome="Rossi", nome="Mario", codice_fiscale=" RSSMRA ")
    company = AnagraficaCompanyPayload(
        ragione_sociale="ACME", partita_iva="12345678901", codice_fiscale=" ACME01 "
    )
    db = MagicMock()
    db.scalar.side_effect = [object()]
    assert support._find_duplicate_codice_fiscale(db, person, company) == "RSSMRA"
    db.scalar.side_effect = [None, object()]
    assert support._find_duplicate_codice_fiscale(db, person, company) == "ACME01"
    db.scalar.side_effect = [None, None]
    assert support._find_duplicate_codice_fiscale(db, person, company) is None
    assert support._find_duplicate_codice_fiscale(db, None, None) is None


def test_bonifica_value_helpers() -> None:
    assert support._normalize_bonifica_tax(None) is None
    assert support._normalize_bonifica_tax("  ") is None
    assert support._normalize_bonifica_tax(" ab 12 ") == "AB12"
    assert support._staging_display_name(_staging(business_name="ACME")) == "ACME"
    assert (
        support._staging_display_name(_staging(first_name="Ada", last_name="Lovelace"))
        == "Lovelace Ada"
    )
    assert support._staging_display_name(_staging(username="ada")) == "ada"
    assert support._staging_display_name(_staging()) == "Consorziato 7"
    assert support._infer_staging_subject_type(_staging(user_type="company")) == "company"
    assert support._infer_staging_subject_type(_staging(business_name="ACME")) == "company"
    assert support._infer_staging_subject_type(_staging(user_type="private")) == "person"
    assert support._infer_staging_subject_type(_staging(first_name="Ada")) == "person"
    assert support._infer_staging_subject_type(_staging()) == "unknown"

    with pytest.raises(HTTPException):
        support._build_staging_person_payload(_staging())
    with pytest.raises(HTTPException):
        support._build_staging_person_payload(_staging(tax="ABC"))
    person = support._build_staging_person_payload(
        _staging(tax="ABC", first_name="Ada", last_name="Lovelace")
    )
    assert person.codice_fiscale == "ABC"
    with pytest.raises(HTTPException):
        support._build_staging_company_payload(_staging())
    with pytest.raises(HTTPException):
        support._build_staging_company_payload(_staging(tax="123"))
    assert (
        support._build_staging_company_payload(
            _staging(tax="12345678901", business_name="ACME")
        ).codice_fiscale
        is None
    )
    assert (
        support._build_staging_company_payload(
            _staging(tax="ABC", business_name="ACME")
        ).codice_fiscale
        == "ABC"
    )


def test_simple_not_found_and_identity_helpers() -> None:
    db = MagicMock()
    db.get.return_value = None
    with pytest.raises(HTTPException):
        support._require_subject_exists(db, uuid.uuid4())
    with pytest.raises(HTTPException):
        support._require_bonifica_staging_exists(db, uuid.uuid4())

    subject = SimpleNamespace(id=uuid.uuid4(), source_name_raw="source")
    company = SimpleNamespace(ragione_sociale="ACME", codice_fiscale="CF", partita_iva="IVA")
    db.get.side_effect = lambda model, _id: company if model is AnagraficaCompany else None
    assert support._subject_identity_summary(db, subject) == ("ACME", "CF", "IVA")
    db.get.side_effect = lambda model, _id: (
        SimpleNamespace(cognome="Rossi", nome="Mario", codice_fiscale="CF")
        if model is AnagraficaPerson
        else None
    )
    assert support._subject_identity_summary(db, subject) == ("Rossi Mario", "CF", None)
    db.get.side_effect = lambda *_: None
    assert support._subject_identity_summary(db, subject) == ("source", None, None)
    assert support._export_headers()[0] == "id"
    assert support._build_catasto_correlations(db, None) == []
    assert support._build_catasto_correlations(db, SimpleNamespace(codice_fiscale=None)) == []


def test_import_route_error_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    user = SimpleNamespace(id=1, username="ada", is_super_admin=True)
    db = MagicMock()
    assert imports.get_anagrafica_module_status(user, user)["username"] == "ada"

    db.scalar.side_effect = [0, 0, 0]
    db.scalars.return_value.all.return_value = []
    assert imports.list_visura_routing_anomalies(user, user, db, True, "needle", 1, 25).total == 0
    db.get.return_value = None
    with pytest.raises(HTTPException):
        imports.resolve_visura_routing_anomaly(uuid.uuid4(), user, user, db)

    payload = SimpleNamespace(letter="A")
    for error_type, expected in ((ValueError, 422), (NasConnectorError, 503)):
        monkeypatch.setattr(imports, "preview_import", MagicMock(side_effect=error_type("failure")))
        with pytest.raises(HTTPException) as error:
            imports.post_import_preview(payload, user, user, object())
        assert error.value.status_code == expected
        monkeypatch.setattr(
            imports, "create_import_snapshot", MagicMock(side_effect=error_type("failure"))
        )
        with pytest.raises(HTTPException) as error:
            imports.post_import_run(payload, user, user, db, object())
        assert error.value.status_code == expected

    monkeypatch.setattr(
        imports, "start_registry_bulk_import_job", MagicMock(side_effect=ValueError("bad"))
    )
    with pytest.raises(HTTPException) as error:
        asyncio.run(imports.post_import_run_from_subjects(user, user, db))
    assert error.value.status_code == 422
    job_id = uuid.uuid4()
    monkeypatch.setattr(imports, "start_registry_bulk_import_job", lambda *_: job_id)
    db.get.return_value = None
    with pytest.raises(HTTPException) as error:
        asyncio.run(imports.post_import_run_from_subjects(user, user, db))
    assert error.value.status_code == 500

    with pytest.raises(HTTPException):
        imports.get_import_job(job_id, user, user, db)
    monkeypatch.setattr(imports, "_require_registry_import_job_for_mutation", lambda *_: None)
    monkeypatch.setattr(
        imports, "finalize_stuck_registry_import_job", lambda *_args, **_kwargs: None
    )
    with pytest.raises(HTTPException):
        imports.post_abort_registry_import_job(job_id, user, user, db)
    monkeypatch.setattr(imports, "delete_registry_import_job", lambda *_: False)
    with pytest.raises(HTTPException):
        imports.delete_registry_import_job_route(job_id, user, user, db)
    with pytest.raises(HTTPException) as error:
        imports.post_resume_import_job(job_id, user, user, db)
    assert error.value.status_code == 409


def test_resume_registry_route_guards(monkeypatch: pytest.MonkeyPatch) -> None:
    user = SimpleNamespace(id=1, is_super_admin=True)
    db = MagicMock()
    job_id = uuid.uuid4()
    monkeypatch.setattr(imports, "_require_registry_import_job_for_mutation", lambda *_: None)
    monkeypatch.setattr(imports, "registry_job_completed_subject_ids", lambda *_: set())
    db.scalar.return_value = 0
    with pytest.raises(HTTPException):
        asyncio.run(imports.post_resume_registry_import_job(job_id, user, user, db))

    job = SimpleNamespace(
        status="pending",
        total_folders=1,
        imported_ok=0,
        imported_errors=0,
        warning_count=0,
        created_at=datetime.now(UTC),
        completed_at=None,
        log_json=None,
    )
    monkeypatch.setattr(imports, "queue_resume_registry_bulk_import_job", lambda *_: job)
    monkeypatch.setattr(
        imports,
        "_job_progress",
        lambda *_: {
            "pending_items": 1,
            "running_items": 0,
            "completed_items": 0,
            "failed_items": 0,
        },
    )
    db.scalar.return_value = 1
    assert (
        asyncio.run(imports.post_resume_registry_import_job(job_id, user, user, db)).status
        == "pending"
    )

    monkeypatch.setattr(
        imports, "finalize_stuck_registry_import_job", lambda *_args, **_kwargs: job
    )
    monkeypatch.setattr(imports, "_serialize_import_job", lambda _db, value: value)
    assert imports.post_abort_registry_import_job(job_id, user, user, db) is job
    monkeypatch.setattr(imports, "delete_registry_import_job", lambda *_: True)
    assert imports.delete_registry_import_job_route(job_id, user, user, db).deleted is True
    monkeypatch.setattr(imports, "registry_job_completed_subject_ids", lambda *_: {uuid.uuid4()})
    with pytest.raises(HTTPException):
        asyncio.run(imports.post_resume_registry_import_job(job_id, user, user, db))
    monkeypatch.setattr(imports, "registry_job_completed_subject_ids", lambda *_: set())
    monkeypatch.setattr(imports, "queue_resume_registry_bulk_import_job", lambda *_: None)
    with pytest.raises(HTTPException):
        asyncio.run(imports.post_resume_registry_import_job(job_id, user, user, db))


def test_bonifica_route_branches(monkeypatch: pytest.MonkeyPatch) -> None:
    user = SimpleNamespace(id=1)
    db = MagicMock()
    db.scalar.return_value = 0
    db.scalars.return_value.all.return_value = []
    assert bonifica.get_bonifica_staging(user, user, db, 1, 25, "ada", "new").total == 0
    assert bonifica.get_bonifica_staging(user, user, db, 1, 25, None, None).total == 0

    valid_id = uuid.uuid4()
    skipped = _staging(review_status="matched")
    approved = _staging()
    db.get.side_effect = [None, skipped, approved]
    approve = MagicMock()
    monkeypatch.setattr(bonifica, "_approve_bonifica_staging_item", approve)
    result = bonifica.bulk_approve_bonifica_staging(
        SimpleNamespace(ids=["invalid", str(uuid.uuid4()), str(uuid.uuid4()), str(valid_id)]),
        user,
        user,
        db,
    )
    assert (result.approved, result.skipped, len(result.errors)) == (1, 1, 2)
    approve.assert_called_once_with(db, user, approved)

    staging_id = uuid.uuid4()
    staging = _staging(id=staging_id)
    require = MagicMock(return_value=staging)
    serialize = MagicMock(return_value=staging)
    monkeypatch.setattr(bonifica, "_require_bonifica_staging_exists", require)
    monkeypatch.setattr(bonifica, "_serialize_bonifica_staging", serialize)
    assert bonifica.get_bonifica_staging_item(staging_id, user, user, db) is staging

    monkeypatch.setattr(bonifica, "_approve_bonifica_staging_item", approve)
    approve.return_value = staging
    assert bonifica.approve_bonifica_staging_item(staging_id, user, user, db) is staging

    assert bonifica.reject_bonifica_staging_item(staging_id, user, user, db) is staging
    assert staging.review_status == "rejected"
    assert staging.reviewed_by == user.id
    assert staging.reviewed_at is not None


class _Upload:
    def __init__(
        self, filename: str | None, content: bytes, content_type: str = "text/plain"
    ) -> None:
        self.filename = filename
        self.content = content
        self.content_type = content_type

    async def read(self) -> bytes:
        return self.content


def test_subject_import_error_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    user = SimpleNamespace(id=1)
    db = MagicMock()
    with pytest.raises(HTTPException):
        asyncio.run(subjects.import_subjects_csv(_Upload("bad.txt", b"x"), user, user, db))
    with pytest.raises(HTTPException):
        asyncio.run(subjects.import_subjects_csv(_Upload("data.csv", b""), user, user, db))
    monkeypatch.setattr(
        subjects, "import_subjects_from_csv", MagicMock(side_effect=ValueError("bad csv"))
    )
    with pytest.raises(HTTPException):
        asyncio.run(subjects.import_subjects_csv(_Upload("data.csv", b"x"), user, user, db))

    for upload in (_Upload("bad.csv", b"x"), _Upload("data.xlsx", b"")):
        with pytest.raises(HTTPException):
            asyncio.run(subjects.import_subjects_xlsx(upload, MagicMock(), user, user, db))
    db.scalars.return_value.all.return_value = []
    assert subjects.get_xlsx_import_batches(user, user, db) == []
    db.get.return_value = None
    with pytest.raises(HTTPException):
        subjects.get_xlsx_import_batch(uuid.uuid4(), user, user, db)

    batch = SimpleNamespace(id=uuid.uuid4())
    monkeypatch.setattr(subjects, "AnagraficaXlsxImportBatch", lambda **_kwargs: batch)
    background_tasks = MagicMock()
    response = asyncio.run(
        subjects.import_subjects_xlsx(
            _Upload("data.xlsx", b"content"), background_tasks, user, user, db
        )
    )
    assert response.batch_id == str(batch.id)
    assert background_tasks.add_task.call_count == 1
    callback = background_tasks.add_task.call_args.args[0]
    fake_session = MagicMock()
    fake_context = MagicMock()
    fake_context.__enter__.return_value = fake_session
    monkeypatch.setattr("app.core.database.SessionLocal", lambda: fake_context)
    run = MagicMock()
    monkeypatch.setattr(subjects, "run_xlsx_import", run)
    callback()
    run.assert_called_once()

    monkeypatch.setattr(subjects, "_serialize_xlsx_batch", lambda value: value)
    db.get.return_value = batch
    assert subjects.get_xlsx_import_batch(batch.id, user, user, db) is batch
    entry = SimpleNamespace(
        id=uuid.uuid4(),
        subject_id=uuid.uuid4(),
        changed_by_user_id=1,
        action="updated",
        diff_json={},
        changed_at=datetime.now(UTC),
    )
    monkeypatch.setattr(subjects, "_require_subject_exists", lambda *_: object())
    db.scalars.return_value.all.return_value = [entry]
    assert len(subjects.get_subject_audit_log(entry.subject_id, user, user, db, 5)) == 1


def test_subject_nas_and_mutation_error_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    user = SimpleNamespace(id=1)
    db = MagicMock()
    service = SimpleNamespace(connector=SimpleNamespace(close=MagicMock()))
    subject_id = uuid.uuid4()
    for error_type, expected in ((ValueError, 404), (NasConnectorError, 503)):
        message = "not found" if error_type is ValueError else "nas"
        monkeypatch.setattr(
            subjects,
            "import_subject_from_existing_registry",
            MagicMock(side_effect=error_type(message)),
        )
        with pytest.raises(HTTPException) as error:
            subjects.post_import_subject_from_nas(subject_id, user, user, db, service)
        assert error.value.status_code == expected
    monkeypatch.setattr(
        subjects,
        "import_subject_from_existing_registry",
        MagicMock(side_effect=ValueError("invalid")),
    )
    with pytest.raises(HTTPException) as error:
        subjects.post_import_subject_from_nas(subject_id, user, user, db, service)
    assert error.value.status_code == 422

    monkeypatch.setattr(subjects, "_require_subject_exists", lambda *_: object())
    service.get_subject_import_status = MagicMock(side_effect=NasConnectorError("nas"))
    with pytest.raises(HTTPException):
        subjects.get_subject_nas_import_status(subject_id, user, user, db, service)
    service.list_existing_subject_folder_candidates = MagicMock(
        side_effect=NasConnectorError("nas")
    )
    with pytest.raises(HTTPException):
        subjects.get_subject_nas_candidates(subject_id, user, user, db, service, 20)

    db.get.return_value = None
    with pytest.raises(HTTPException):
        subjects.update_subject(subject_id, SimpleNamespace(), user, user, db)
    with pytest.raises(HTTPException):
        subjects.deactivate_subject(subject_id, user, user, db)

    subject = SimpleNamespace(
        id=subject_id,
        subject_type="person",
        source_name_raw="old",
        status="active",
        nas_folder_path=None,
        nas_folder_letter=None,
        requires_review=False,
    )
    db.get.return_value = subject
    monkeypatch.setattr(subjects, "_validate_subject_payload", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(subjects, "_apply_subject_payload", MagicMock())
    monkeypatch.setattr(subjects, "_create_subject_audit", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(subjects, "_build_subject_detail", lambda *_: "detail")
    payload = SimpleNamespace(
        source_name_raw="new",
        status="inactive",
        nas_folder_path="/nas",
        nas_folder_letter=" b ",
        requires_review=True,
        person=object(),
        company=None,
    )
    assert subjects.update_subject(subject_id, payload, user, user, db) == "detail"
    assert subject.nas_folder_letter == "B"
    with pytest.raises(HTTPException):
        asyncio.run(
            subjects.upload_subject_document(
                subject_id, _Upload(None, b"x"), "altro", None, user, user, db
            )
        )
    with pytest.raises(HTTPException):
        asyncio.run(
            subjects.upload_subject_document(
                subject_id, _Upload("x.txt", b""), "altro", None, user, user, db
            )
        )
    monkeypatch.setattr(
        subjects, "create_manual_document", MagicMock(side_effect=ValueError("missing"))
    )
    with pytest.raises(HTTPException):
        asyncio.run(
            subjects.upload_subject_document(
                subject_id, _Upload("x.txt", b"x"), "altro", None, user, user, db
            )
        )
    monkeypatch.setattr(
        subjects, "create_manual_document", MagicMock(side_effect=NasConnectorError("nas"))
    )
    with pytest.raises(HTTPException):
        asyncio.run(
            subjects.upload_subject_document(
                subject_id, _Upload("x.txt", b"x"), "altro", None, user, user, db
            )
        )


def test_document_route_branches(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    user = SimpleNamespace(id=1)
    db = MagicMock()
    document_id = uuid.uuid4()
    db.get.return_value = None
    with pytest.raises(HTTPException):
        documents.patch_document(
            document_id, SimpleNamespace(doc_type=None, notes=None), user, user, db
        )
    with pytest.raises(HTTPException):
        documents.classify_document_content(document_id, SimpleNamespace(text="x"), user, user, db)
    with pytest.raises(HTTPException):
        documents.download_document(document_id, user, user, db)

    monkeypatch.setattr(documents.settings, "utenze_delete_password", "secret")
    with pytest.raises(HTTPException):
        documents.delete_document(document_id, user, user, db, "bad")
    monkeypatch.setattr(documents.settings, "utenze_delete_password", "")
    monkeypatch.setattr(documents.settings, "anagrafica_delete_password", "")
    with pytest.raises(HTTPException):
        documents.delete_document(document_id, user, user, db)
    with pytest.raises(HTTPException):
        documents.post_reset_anagrafica(SimpleNamespace(confirm="wrong"), user, user, db)

    document = SimpleNamespace(
        id=document_id,
        subject_id=uuid.uuid4(),
        filename="x.txt",
        content_classification_status="not_requested",
        content_category=None,
        content_classification_source=None,
    )
    db.get.return_value = document
    monkeypatch.setattr(documents, "_build_document_response", lambda value: value)
    documents.patch_document(
        document_id, SimpleNamespace(doc_type="altro", notes="note"), user, user, db
    )
    documents.patch_document(
        document_id, SimpleNamespace(doc_type=None, notes="changed"), user, user, db
    )
    documents.patch_document(
        document_id, SimpleNamespace(doc_type="altro", notes=None), user, user, db
    )
    local = tmp_path / "x.txt"
    local.write_text("x")
    monkeypatch.setattr(documents, "_ensure_document_available_locally", lambda *_: local)
    monkeypatch.setattr(
        documents, "classify_document_content_file", lambda *_args, **_kwargs: object()
    )
    monkeypatch.setattr(documents, "_apply_document_content_classification", lambda *_: None)
    documents.classify_document_content(document_id, SimpleNamespace(text=None), user, user, db)


def test_reporting_skips_orphan_summary_document() -> None:
    db = MagicMock()
    db.scalar.return_value = 0
    db.execute.return_value.all.side_effect = [[], []]
    db.scalars.return_value.all.return_value = [SimpleNamespace(subject_id=uuid.uuid4())]
    db.get.return_value = None
    result = reporting.get_documents_summary(object(), object(), db)
    assert result.recent_unclassified == []


def test_remaining_support_serialization_and_approval_branches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = MagicMock()
    subject = SimpleNamespace(id=uuid.uuid4(), subject_type="person", imported_at=None)
    user = SimpleNamespace(id=1)
    serialize_bonifica = support._serialize_bonifica_staging
    monkeypatch.setattr(support, "_apply_subject_payload", lambda *_: None)
    monkeypatch.setattr(support, "_create_subject_audit", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(support, "_serialize_bonifica_staging", lambda _db, value: value)

    created_subject = SimpleNamespace(id=uuid.uuid4())
    monkeypatch.setattr(support, "AnagraficaSubject", lambda **_kwargs: created_subject)
    created = _staging(user_type="private", tax="CF", first_name="Ada", last_name="L")
    assert support._approve_bonifica_staging_item(db, user, created) is created
    assert created.matched_subject_id == created_subject.id

    with pytest.raises(HTTPException):
        support._approve_bonifica_staging_item(db, user, _staging(review_status="rejected"))
    with pytest.raises(HTTPException):
        support._approve_bonifica_staging_item(db, user, _staging())
    with pytest.raises(HTTPException):
        support._approve_bonifica_staging_item(
            db,
            user,
            _staging(
                review_status="matched",
                user_type="private",
                tax="CF",
                first_name="Ada",
                last_name="L",
            ),
        )

    staging = _staging(
        review_status="matched",
        matched_subject_id=subject.id,
        user_type="company",
        tax="12345678901",
        business_name="ACME",
    )
    db.get.return_value = subject
    with pytest.raises(HTTPException):
        support._approve_bonifica_staging_item(db, user, staging)
    subject.subject_type = "company"
    assert support._approve_bonifica_staging_item(db, user, staging) is staging
    assert subject.imported_at is not None

    monkeypatch.setattr(support, "_serialize_bonifica_staging", serialize_bonifica)
    unmatched = _staging()
    assert support._serialize_bonifica_staging(db, unmatched).matched_subject_display_name is None
    matched = _staging(matched_subject_id=subject.id)
    db.get.return_value = None
    assert support._serialize_bonifica_staging(db, matched).matched_subject_display_name is None
    db.get.return_value = subject
    monkeypatch.setattr(support, "_subject_display_name", lambda *_: "ACME")
    assert support._serialize_bonifica_staging(db, matched).matched_subject_display_name == "ACME"

    db.get.return_value = matched
    assert support._require_bonifica_staging_exists(db, matched.id) is matched

    smart = SimpleNamespace(
        category="other", label="Other", priority=0, confidence=0.1, reason="fallback"
    )
    monkeypatch.setattr(support, "derive_document_smart_classification", lambda **_kwargs: smart)
    document = SimpleNamespace(
        id=uuid.uuid4(),
        filename="README",
        nas_path=None,
        local_path=None,
        doc_type="altro",
        classification_source="manual",
        notes=None,
        content_classification_status="not_requested",
        content_category=None,
        content_category_label=None,
        content_confidence=None,
        content_reason=None,
        content_excerpt=None,
        content_classification_source=None,
        content_classified_at=None,
        content_classification_error=None,
    )
    assert support._build_document_response(document).extension is None

    now = datetime.now(UTC)
    batch = SimpleNamespace(
        id=uuid.uuid4(),
        requested_by_user_id=1,
        filename="data.xlsx",
        status="pending",
        total_rows=0,
        processed_rows=0,
        inserted=0,
        updated=0,
        unchanged=0,
        anomalies=0,
        errors=0,
        error_log=None,
        created_at=now,
        started_at=None,
        completed_at=None,
        updated_at=now,
    )
    assert support._serialize_xlsx_batch(batch).filename == "data.xlsx"
