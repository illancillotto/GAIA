from __future__ import annotations

import os
from datetime import date
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete, event, select
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError
from sqlalchemy.pool import StaticPool
from sqlalchemy.schema import CreateSchema, DropSchema

from app.core.database import get_db
from app.core.security import create_access_token
from app.models.application_user import ApplicationUser
from app.models.section_permission import RoleSectionPermission, Section, UserSectionPermission
from app.modules.ruolo.models import RuoloAvviso
from app.modules.ruolo.notice_register_models import (
    NoticeAttempt,
    NoticeAudit,
    NoticeDocument,
    NoticeNotification,
    NoticeRecovery,
)
from app.modules.ruolo.router import catasto_router, router

from .test_notice_register import _avviso, _metadata

URL = "/ruolo/tributi/registro-avvisi"


def _api_metadata():
    metadata = _metadata()
    metadata.remove(metadata.tables["application_users"])
    for model in (ApplicationUser, Section, RoleSectionPermission, UserSectionPermission):
        model.__table__.to_metadata(metadata)
    return metadata


@pytest.fixture(scope="module", params=["sqlite", "postgresql"])
def api_engine(request):
    if request.param == "sqlite":
        engine = create_engine(
            "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
        )

        @event.listens_for(engine, "connect")
        def foreign_keys(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")

        _api_metadata().create_all(engine)
        yield engine
        engine.dispose()
        return
    url = os.getenv("GAIA_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("GAIA_TEST_POSTGRES_URL non configurato")
    admin = create_engine(url)
    assert admin.dialect.name == "postgresql"
    schema = f"test_notice_api_{uuid4().hex}"
    with admin.begin() as connection:
        connection.execute(CreateSchema(schema))
    engine = create_engine(url, connect_args={"options": f"-csearch_path={schema}"})
    try:
        _api_metadata().create_all(engine)
        yield engine
    finally:
        engine.dispose()
        with admin.begin() as connection:
            connection.execute(DropSchema(schema, cascade=True))
        admin.dispose()


def _seed_auth(connection):
    for user_id, role, module, active in (
        (1, "admin", True, True),
        (2, "viewer", True, True),
        (3, "admin", False, True),
        (4, "admin", True, False),
        (5, "admin", True, True),
    ):
        connection.execute(
            ApplicationUser.__table__.insert().values(
                id=user_id,
                username=f"register-{user_id}",
                email=f"register-{user_id}@example.test",
                password_hash="not-used-with-token-auth",
                role=role,
                module_ruolo=module,
                is_active=active,
            )
        )
    connection.execute(
        Section.__table__.insert(),
        [
            {
                "id": 1,
                "key": "ruolo.tributi.view",
                "label": "View",
                "module": "ruolo",
                "min_role": "viewer",
            },
            {
                "id": 2,
                "key": "ruolo.tributi.manage_status",
                "label": "Manage",
                "module": "ruolo",
                "min_role": "admin",
            },
        ],
    )
    connection.execute(
        UserSectionPermission.__table__.insert().values(
            user_id=5,
            section_id=1,
            is_granted=False,
        )
    )


def _headers(user_id=1):
    token = create_access_token(str(user_id), "admin", ["ruolo"])
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def api(api_engine):
    app = FastAPI()
    app.include_router(router, prefix="/ruolo")
    with api_engine.connect() as connection:
        transaction = connection.begin()
        _seed_auth(connection)

        def session():
            return Session(connection, join_transaction_mode="create_savepoint", autoflush=False)

        def database():
            with session() as db:
                yield db

        app.dependency_overrides[get_db] = database
        try:
            with TestClient(app) as client:
                client.headers.update(_headers())
                yield SimpleNamespace(client=client, session=session, app=app)
        finally:
            transaction.rollback()


def _request(data, version=1):
    return {"data": data, "expected_version": version, "reason": "Verifica fascicolo cartaceo"}


def _create(api, **overrides):
    payload = {
        "document_number": "CUM-2022-2023",
        "tax_code": "TESTCF",
        "positions": [],
    } | overrides
    response = api.client.post(URL, json=_request(payload))
    assert response.status_code == 201, response.text
    return response.json()["document_id"]


def _detail(api, doc):
    response = api.client.get(f"{URL}/{doc}")
    assert response.status_code == 200, response.text
    return response.json()


def _add_position(api, doc, year=2022, reference="020220001834880"):
    payload = {"tax_year": year, "source_namespace": "incass", "source_reference": reference}
    response = api.client.post(
        f"{URL}/{doc}/posizioni", json=_request(payload, _detail(api, doc)["version"])
    )
    assert response.status_code == 201, response.text
    return response.json()["resource_id"]


def _write(api, doc, path, data, method="put"):
    return api.client.request(
        method, f"{URL}/{doc}{path}", json=_request(data, _detail(api, doc)["version"])
    )


def _link(api, doc, position, avviso):
    response = _write(
        api,
        doc,
        f"/posizioni/{position}/collegamento",
        {"avviso_id": str(avviso), "confirmed": True},
    )
    assert response.status_code == 200, response.text


def _seed_avviso(api, year=2022, **values):
    with api.session() as db:
        avviso = _avviso(db, year)
        for key, value in values.items():
            setattr(avviso, key, value)
        db.commit()
        return avviso.id


def _perfect_notification(api, doc):
    evidence = _write(
        api,
        doc,
        "/evidenze",
        {
            "kind": "ricevuta",
            "reference": "Fascicolo 42",
            "occurred_on": "2024-06-29",
        },
        method="post",
    )
    assert evidence.status_code == 201, evidence.text
    evidence_id = evidence.json()["resource_id"]
    response = _write(
        api,
        doc,
        "/notifica",
        {
            "state": "perfezionata",
            "notified_on": "2024-06-29",
            "evidence_id": evidence_id,
        },
    )
    assert response.status_code == 200, response.text
    return evidence_id


def test_list_create_detail_audit_and_read_permissions(api):
    assert api.client.get(URL).json()["total"] == 0
    doc = _create(api)
    detail = _detail(api, doc)
    assert detail["position_count"] == 0
    assert set(detail["anomalies"]) == {"posizioni_assenti", "notifica_da_verificare"}
    for path in ("", f"/{doc}", f"/{doc}/evidenze", f"/{doc}/invii", f"/{doc}/storico"):
        assert api.client.get(URL + path, headers=_headers(2)).status_code == 200
    audit = api.client.get(f"{URL}/{doc}/storico").json()
    assert audit["total"] == 1 and audit["items"][0]["actor_id"] == 1
    assert audit["items"][0]["after_json"]["document"]["source_system"] == "manual"
    assert catasto_router.routes


@pytest.mark.parametrize("user_id, expected", [(None, 401), (3, 403), (4, 401), (5, 403)])
def test_authentication_module_and_section_are_enforced(api, user_id, expected):
    api.client.headers.clear()
    headers = _headers(user_id) if user_id else {}
    assert api.client.get(URL, headers=headers).status_code == expected
    assert (
        api.client.post(URL, headers=headers, json=_request({"document_number": "x"})).status_code
        == expected
    )


def test_viewer_cannot_call_any_mutation(api):
    doc = _create(api)
    position = _add_position(api, doc)
    mutations = (
        ("post", "", {"document_number": "x"}),
        ("put", f"/{doc}", {"document_number": "x"}),
        ("post", f"/{doc}/posizioni", {}),
        ("put", f"/{doc}/posizioni/{position}", {}),
        ("put", f"/{doc}/posizioni/{position}/collegamento", {}),
        ("post", f"/{doc}/evidenze", {}),
        ("put", f"/{doc}/notifica", {}),
        ("put", f"/{doc}/posizioni/{position}/step", {}),
    )
    for method, path, data in mutations:
        response = api.client.request(method, URL + path, headers=_headers(2), json=_request(data))
        assert response.status_code == 403, response.text


def test_user_cannot_spoof_actor_provenance_or_confirmation(api):
    data = _request({"document_number": "x"})
    data["actor_id"] = 2
    assert api.client.post(URL, json=data).status_code == 422
    doc = _create(api)
    position = _add_position(api, doc)
    response = _write(
        api,
        doc,
        "/evidenze",
        {
            "kind": "consegna",
            "reference": "x",
            "source_system": "poste",
        },
        method="post",
    )
    assert response.status_code == 422
    for data in ({"avviso_id": None}, {"avviso_id": None, "confirmed": False}):
        assert _write(api, doc, f"/posizioni/{position}/collegamento", data).status_code == 422
    assert api.client.get(f"{URL}/{doc}/evidenze").json()["total"] == 0


def test_manual_positions_candidates_and_reversible_links(api):
    doc = _create(api)
    position = _add_position(api, doc)
    avviso = _seed_avviso(
        api, codice_cnc="CNC-123", codice_fiscale_raw="TESTCF", nominativo_raw="Test Person"
    )
    _seed_avviso(api, year=2023, codice_cnc="CNC-123", codice_fiscale_raw="TESTCF")
    url = f"{URL}/{doc}/posizioni/{position}/candidati"
    for text in ("CNC-123", "testcf", "Person", str(avviso)):
        candidates = api.client.get(url, params={"q": text}).json()
        assert candidates["total"] == 1
        assert candidates["items"][0]["id"] == str(avviso)
        assert candidates["items"][0]["already_linked"] is False
    assert api.client.get(url, params={"q": "020220001834880"}).json()["total"] == 0
    _link(api, doc, position, avviso)
    assert api.client.get(url, params={"q": "CNC-123"}).json()["items"][0]["already_linked"] is True
    assert _detail(api, doc)["positions"][0]["avviso"]["codice_cnc"] == "CNC-123"
    _perfect_notification(api, doc)
    response = _write(
        api,
        doc,
        f"/posizioni/{position}/step",
        {
            "state": "affidato",
            "verified_on": str(date.today()),
            "case_reference": "STEP-1",
            "evidence_reference": "Report",
            "amount": "123.45",
        },
    )
    assert response.status_code == 200
    assert _detail(api, doc)["anomalies"] == []
    assert api.client.get(URL, params={"view": "anomalie"}).json()["total"] == 0
    assert api.client.get(URL, params={"view": "affidamenti"}).json()["total"] == 1
    assert (
        _write(
            api, doc, f"/posizioni/{position}/collegamento", {"avviso_id": None, "confirmed": True}
        ).status_code
        == 200
    )
    detail = _detail(api, doc)
    assert detail["notification"]["state"] == "da_verificare"
    assert detail["positions"][0]["recovery"]["state"] == "da_verificare"
    audit = api.client.get(f"{URL}/{doc}/storico", params={"page_size": 1}).json()
    assert audit["items"][0]["before_json"]["recovery"]["case_reference"] == "STEP-1"
    _link(api, doc, position, avviso)


def test_correct_position_requires_fresh_link_and_preserves_original(api):
    original_position = {
        "tax_year": 2022,
        "source_namespace": "incass",
        "source_reference": "original",
    }
    doc = _create(api, positions=[original_position])
    position = _detail(api, doc)["positions"][0]["id"]
    avviso = _seed_avviso(api)
    _link(api, doc, position, avviso)
    old_version = _detail(api, doc)["version"]
    same = _write(api, doc, f"/posizioni/{position}", original_position)
    assert same.json()["version"] == old_version
    _perfect_notification(api, doc)
    changed = original_position | {"tax_year": 2023, "source_reference": "corrected"}
    response = _write(api, doc, f"/posizioni/{position}", changed)
    assert response.status_code == 200, response.text
    detail = _detail(api, doc)
    assert detail["positions"][0]["avviso_id"] is None
    assert detail["positions"][0]["tax_year"] == 2023
    assert detail["notification_state"] == "da_verificare"
    assert detail["original_json"]["positions"] == [original_position]


def test_metadata_change_and_added_scope_invalidate_notification_but_not_noop(api):
    doc = _create(api)
    _perfect_notification(api, doc)
    version = _detail(api, doc)["version"]
    assert (
        _write(api, doc, "", {"document_number": "CUM-2022-2023", "tax_code": "TESTCF"}).json()[
            "version"
        ]
        == version
    )
    assert (
        _write(api, doc, "", {"document_number": "CORRECTED", "tax_code": "TESTCF"}).status_code
        == 200
    )
    assert _detail(api, doc)["notification_state"] == "da_verificare"
    _perfect_notification(api, doc)
    _add_position(api, doc)
    assert _detail(api, doc)["notification_state"] == "da_verificare"


def test_http_errors_are_atomic_and_do_not_leak_sql(api, monkeypatch):
    doc = _create(api)
    position = _add_position(api, doc)
    version = _detail(api, doc)["version"]
    duplicate = _write(
        api,
        doc,
        "/posizioni",
        {
            "tax_year": 2022,
            "source_namespace": "incass",
            "source_reference": "020220001834880",
        },
        method="post",
    )
    assert duplicate.status_code == 409 and "INSERT" not in duplicate.text
    assert _detail(api, doc)["version"] == version
    stale = api.client.put(f"{URL}/{doc}", json=_request({"document_number": "stale"}))
    assert stale.status_code == 409
    wrong_year = _seed_avviso(api, year=2023)
    assert (
        _write(
            api,
            doc,
            f"/posizioni/{position}/collegamento",
            {"avviso_id": str(wrong_year), "confirmed": True},
        ).status_code
        == 422
    )
    assert (
        api.client.put(
            f"{URL}/{uuid4()}", json=_request({"document_number": "missing"})
        ).status_code
        == 404
    )

    def stale_commit(_):
        raise StaleDataError("private SQL detail")

    with monkeypatch.context() as patch:
        patch.setattr(Session, "commit", stale_commit)
        failed = _write(api, doc, "", {"document_number": "must-roll-back"})
        assert failed.status_code == 409 and "private" not in failed.text
    assert _detail(api, doc)["document_number"] == "CUM-2022-2023"
    assert _detail(api, doc)["version"] == version


def test_missing_and_cross_document_resources_are_rejected(api):
    doc = _create(api)
    other = _create(api)
    position = _add_position(api, other)
    assert api.client.get(f"{URL}/{uuid4()}").status_code == 404
    assert (
        api.client.get(
            f"{URL}/{doc}/posizioni/{uuid4()}/candidati", params={"q": "abc"}
        ).status_code
        == 404
    )
    assert (
        api.client.get(
            f"{URL}/{doc}/posizioni/{position}/candidati", params={"q": "abc"}
        ).status_code
        == 404
    )
    assert (
        _write(
            api,
            doc,
            f"/posizioni/{position}",
            {"tax_year": 2022, "source_namespace": "incass", "source_reference": "x"},
        ).status_code
        == 404
    )
    evidence_id = _perfect_notification(api, other)
    response = _write(
        api,
        doc,
        "/notifica",
        {
            "state": "perfezionata",
            "notified_on": "2024-06-29",
            "evidence_id": evidence_id,
        },
    )
    assert response.status_code == 422


def test_filters_search_and_pagination_are_consistent(api):
    doc = _create(api, document_number="letter-%_literal")
    _add_position(api, doc, reference="ref-annual")
    second = _create(api, document_number="other-number", tax_code="SECOND")
    with api.session() as db:
        db.add(
            NoticeAttempt(
                document_id=UUID(doc),
                source_system="poste",
                source_key="shipment",
                channel="posta",
                tracking_code="tracking-123",
            )
        )
        db.commit()
    for q in ("letter", "TESTCF", "ref-annual", "tracking-123", "%_literal"):
        response = api.client.get(URL, params={"q": q}).json()
        assert response["total"] == 1 and response["items"][0]["id"] == doc
    assert api.client.get(URL, params={"q": "___"}).json()["total"] == 0
    assert api.client.get(URL, params={"tax_year": 2022}).json()["total"] == 1
    assert api.client.get(URL, params={"tax_year": 2023}).json()["total"] == 0
    for state in ("da_verificare", "perfezionata"):
        assert api.client.get(URL, params={"notification_state": state}).json()["total"] == (
            2 if state == "da_verificare" else 0
        )
    assert api.client.get(URL, params={"recovery_state": "da_verificare"}).json()["total"] == 1
    assert api.client.get(URL, params={"recovery_state": "affidato"}).json()["total"] == 0
    assert api.client.get(URL, params={"view": "affidamenti"}).json()["total"] == 0
    pages = [
        api.client.get(URL, params={"page_size": 1, "page": page}).json() for page in (1, 2, 3)
    ]
    assert all(page["total"] == 2 for page in pages)
    assert {pages[0]["items"][0]["id"], pages[1]["items"][0]["id"]} == {doc, second}
    assert pages[2]["items"] == []
    attempts = api.client.get(f"{URL}/{doc}/invii").json()
    assert attempts["items"][0]["tracking_code"] == "tracking-123"


def test_year_and_step_filters_must_match_the_same_position(api):
    doc = _create(api)
    _add_position(api, doc, year=2022, reference="ref-2022")
    second = _add_position(api, doc, year=2023, reference="ref-2023")
    response = _write(
        api,
        doc,
        f"/posizioni/{second}/step",
        {
            "state": "affidato",
            "verified_on": str(date.today()),
            "evidence_reference": "Report STEP",
            "case_reference": "STEP-2023",
        },
    )
    assert response.status_code == 200
    for filters in ({"view": "affidamenti"}, {"recovery_state": "affidato"}):
        assert api.client.get(URL, params={**filters, "tax_year": 2022}).json()["total"] == 0
        assert api.client.get(URL, params={**filters, "tax_year": 2023}).json()["total"] == 1
    assert (
        api.client.get(
            URL, params={"view": "affidamenti", "recovery_state": "da_verificare"}
        ).json()["total"]
        == 0
    )


@pytest.mark.parametrize(
    "params",
    [
        {"page": 0},
        {"page_size": 101},
        {"q": "  "},
        {"q": "ab"},
        {"view": "wrong"},
        {"tax_year": 1800},
        {"notification_state": "notificato"},
        {"unknown": "value"},
    ],
)
def test_invalid_query_is_422_not_500(api, params):
    assert api.client.get(URL, params=params).status_code == 422


def test_candidate_search_requires_text_and_escapes_wildcards(api):
    doc = _create(api)
    position = _add_position(api, doc)
    _seed_avviso(api, codice_cnc="ordinary")
    url = f"{URL}/{doc}/posizioni/{position}/candidati"
    for params in ({}, {"q": "  "}, {"q": "ab"}):
        assert api.client.get(url, params=params).status_code == 422
    assert api.client.get(url, params={"q": "___"}).json()["total"] == 0
    _seed_avviso(api, codice_cnc="ABC-literal", codice_fiscale_raw="TESTCF")
    assert (
        api.client.get(url, params={"q": "TESTCF", "page": 2, "page_size": 1}).json()["items"] == []
    )


def test_conflicting_and_incomplete_records_remain_visible(api):
    doc = _create(api)
    position = _add_position(api, doc)
    avviso = _seed_avviso(api, codice_fiscale_raw="DIFFERENT")
    _link(api, doc, position, avviso)
    detail = _detail(api, doc)
    assert detail["conflicting_count"] == 1
    assert "collegamenti_discordanti" in detail["anomalies"]
    with api.session() as db:
        db.get(RuoloAvviso, avviso).anno_tributario = 2023
        db.get(RuoloAvviso, avviso).codice_fiscale_raw = "TESTCF"
        db.execute(delete(NoticeNotification).where(NoticeNotification.document_id == UUID(doc)))
        db.execute(delete(NoticeRecovery).where(NoticeRecovery.position_id == UUID(position)))
        db.commit()
    detail = _detail(api, doc)
    assert detail["notification"] is None and detail["positions"][0]["recovery"] is None
    assert detail["notification_state"] == "da_verificare"
    assert detail["conflicting_count"] == 1 and detail["recovery_review_count"] == 1
    assert (
        api.client.get(URL, params={"recovery_state": "da_verificare", "view": "anomalie"}).json()[
            "total"
        ]
        == 1
    )


def test_evidence_and_audit_pagination_does_not_mutate_state(api):
    doc = _create(api)
    _perfect_notification(api, doc)
    timeline = api.client.get(f"{URL}/{doc}/evidenze").json()
    assert timeline["items"][0]["source_system"] == "manual"
    assert timeline["items"][0]["original_json"]["reference"] == "Fascicolo 42"
    assert (
        api.client.get(f"{URL}/{doc}/evidenze", params={"page": 2, "page_size": 1}).json()["items"]
        == []
    )
    assert api.client.get(f"{URL}/{doc}/storico", params={"page_size": 1}).json()["total"] == 3
    assert _detail(api, doc)["notification_state"] == "perfezionata"
    with api.session() as db:
        assert db.scalar(select(NoticeDocument.version).where(NoticeDocument.id == UUID(doc))) == 3
        assert (
            len(list(db.scalars(select(NoticeAudit).where(NoticeAudit.document_id == UUID(doc)))))
            == 3
        )


def test_openapi_contains_only_new_register_paths_and_explicit_contracts(api):
    schema = api.app.openapi()
    paths = {path for path in schema["paths"] if path.startswith(URL)}
    assert len(paths) == 22
    assert f"{URL}/{{document_id}}/riconciliazione" in paths
    assert f"{URL}/{{document_id}}/riconciliazione/annulla" in paths
    assert {
        f"{URL}/importazioni{suffix}"
        for suffix in (
            "",
            "/excel",
            "/poste",
            "/{batch_id}",
            "/{batch_id}/righe",
            "/{batch_id}/originale",
            "/{batch_id}/conferma",
            "/{batch_id}/righe/{row_id}/risoluzione",
        )
    } <= paths
    assert schema["paths"][URL]["post"]["responses"]["201"]
    assert "DocumentDetail" in schema["components"]["schemas"]
