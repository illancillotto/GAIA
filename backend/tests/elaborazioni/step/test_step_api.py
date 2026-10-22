from __future__ import annotations

import uuid

from sqlalchemy import select
from step_fixtures import PDF, add_avviso, build_archive, login, scheda

from app.modules.elaborazioni.step.archive import import_archive
from app.modules.elaborazioni.step.models import (
    StepContribuente,
    StepCredential,
    StepDocumento,
    StepSyncJob,
)


def _create_credential(client, headers, **overrides) -> dict:
    payload = {"label": "STEP", "username": " utente ", "password": "segreta", **overrides}
    response = client.post("/elaborazioni/step/credentials", headers=headers, json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_credentials_api_is_super_admin_only_and_hides_password(client, session_factory) -> None:
    headers = login(client)
    assert (
        client.get(
            "/elaborazioni/step/credentials", headers=login(client, "step-viewer")
        ).status_code
        == 403
    )

    created = _create_credential(client, headers)
    assert created["username"] == "utente" and "password" not in created
    assert created["portal_url"].startswith("https://prunesenti-step")
    invalid = client.post(
        "/elaborazioni/step/credentials",
        headers=headers,
        json={"label": "x", "username": "u", "password": "p", "portal_url": "http://insecure"},
    )
    assert invalid.status_code == 422

    with session_factory() as db:
        stored = db.get(StepCredential, created["id"])
        stored.consecutive_failures = 2
        stored.active = False
        db.commit()
    updated = client.patch(
        f"/elaborazioni/step/credentials/{created['id']}",
        headers=headers,
        json={
            "label": " Nuova ",
            "password": "altra",
            "active": True,
            "portal_url": "https://step.example/?c=1",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["label"] == "Nuova" and updated.json()["consecutive_failures"] == 0
    assert (
        client.get("/elaborazioni/step/credentials", headers=headers).json()[0]["portal_url"]
        == "https://step.example/?c=1"
    )

    assert (
        client.patch("/elaborazioni/step/credentials/999", headers=headers, json={}).status_code
        == 404
    )
    assert client.delete("/elaborazioni/step/credentials/999", headers=headers).status_code == 404
    assert (
        client.delete(
            f"/elaborazioni/step/credentials/{created['id']}", headers=headers
        ).status_code
        == 204
    )


def test_jobs_api_lifecycle(client, session_factory) -> None:
    headers = login(client)
    assert (
        client.post("/elaborazioni/step/jobs", headers=headers, json={"mode": "sync"}).status_code
        == 503
    )
    credential = _create_credential(client, headers)

    assert (
        client.post("/elaborazioni/step/credentials/999/test", headers=headers).status_code == 404
    )
    test_job = client.post(
        f"/elaborazioni/step/credentials/{credential['id']}/test", headers=headers
    )
    assert test_job.status_code == 202 and test_job.json()["mode"] == "credential_test"
    assert (
        client.post(
            f"/elaborazioni/step/credentials/{credential['id']}/test", headers=headers
        ).status_code
        == 409
    )
    assert (
        client.post("/elaborazioni/step/jobs", headers=headers, json={"mode": "relink"}).status_code
        == 409
    )

    cancelled = client.post(
        f"/elaborazioni/step/jobs/{test_job.json()['id']}/cancel", headers=headers
    )
    assert cancelled.json()["status"] == "cancelled"
    assert (
        client.post(
            f"/elaborazioni/step/jobs/{test_job.json()['id']}/cancel", headers=headers
        ).status_code
        == 409
    )

    assert (
        client.post(
            "/elaborazioni/step/jobs", headers=headers, json={"mode": "archive_import"}
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/elaborazioni/step/jobs",
            headers=headers,
            json={"mode": "archive_import", "archive_name": "../x.zip"},
        ).status_code
        == 422
    )
    sync = client.post(
        "/elaborazioni/step/jobs", headers=headers, json={"mode": "sync", "max_details": 5}
    )
    assert sync.status_code == 202 and sync.json()["credential_id"] is None
    assert (
        client.get(f"/elaborazioni/step/jobs/{sync.json()['id']}", headers=headers).json()[
            "payload_json"
        ]["max_details"]
        == 5
    )
    assert (
        client.delete(f"/elaborazioni/step/jobs/{sync.json()['id']}", headers=headers).status_code
        == 409
    )
    assert [job["id"] for job in client.get("/elaborazioni/step/jobs", headers=headers).json()] == [
        sync.json()["id"],
        test_job.json()["id"],
    ]

    with session_factory() as db:
        db.get(StepSyncJob, sync.json()["id"]).status = "succeeded"
        db.commit()
    archive = client.post(
        "/elaborazioni/step/jobs",
        headers=headers,
        json={"mode": "archive_import", "archive_name": "raccolta.zip"},
    )
    assert archive.status_code == 202 and archive.json()["credential_id"] is None
    assert (
        client.delete(f"/elaborazioni/step/jobs/{sync.json()['id']}", headers=headers).status_code
        == 204
    )
    assert client.get("/elaborazioni/step/jobs/999", headers=headers).status_code == 404


def test_read_api_exposes_archive_links_and_pdfs(
    client, session_factory, storage_dirs, tmp_path
) -> None:
    headers = login(client)
    assert (
        client.get("/elaborazioni/step/overview", headers=login(client, "step-viewer")).status_code
        == 403
    )
    _, import_root = storage_dirs
    import_root.mkdir()
    build_archive(
        import_root / "raccolta.zip", [scheda(), scheda("ZZZZZZ80A01G113X", RESIDUO="0,00")]
    )
    with session_factory() as db:
        avviso_id = add_avviso(db, "01.02019000601804", 2019)
        not_found = scheda("NNNNNN80A01G113X")
        not_found["documents"][0]["tributi"]["rows"][0]["DES_TRI1"] = "Avv. N. 020199999999990 Not."
        build_archive(tmp_path / "extra.zip", [not_found])
        import_archive(db, import_root / "raccolta.zip", job_id=None)
        import_archive(db, tmp_path / "extra.zip", job_id=None)
        contribuente = db.scalar(
            select(StepContribuente).where(StepContribuente.codice_fiscale == "RSSMRA80A01G113X")
        )
        documento = db.scalar(
            select(StepDocumento).where(StepDocumento.contribuente_id == contribuente.id)
        )
        contribuente_id, documento_id = contribuente.id, documento.id

    overview = client.get("/elaborazioni/step/overview", headers=headers).json()
    assert overview["contribuenti"] == 3 and overview["pdf_scaricati"] == 3
    assert overview["links"] == {"linked": 2, "not_found": 1, "ambiguous": 0, "unrecognized": 0}
    assert overview["import_archives"] == ["raccolta.zip"]

    page = client.get(
        "/elaborazioni/step/contribuenti", headers=headers, params={"q": "RSSMRA", "page_size": 1}
    ).json()
    assert page["total"] == 1 and page["items"][0]["codice_fiscale"] == "RSSMRA80A01G113X"
    assert (
        client.get(
            "/elaborazioni/step/contribuenti", headers=headers, params={"only_residuo": True}
        ).json()["total"]
        == 2
    )

    detail = client.get(
        f"/elaborazioni/step/contribuenti/{contribuente_id}", headers=headers
    ).json()
    assert detail["documenti"][0]["tributi"][0]["codice_cnc"] == "020190006018040"
    assert detail["documenti"][0]["links"][0]["ruolo_avviso_id"] == str(avviso_id)
    assert len(detail["pagamenti"]) == 2
    assert (
        client.get(f"/elaborazioni/step/contribuenti/{uuid.uuid4()}", headers=headers).status_code
        == 404
    )

    pdf = client.get(f"/elaborazioni/step/documenti/{documento_id}/pdf", headers=headers)
    assert (
        pdf.status_code == 200
        and pdf.content == PDF
        and "Doc_1.pdf" in pdf.headers["content-disposition"]
    )
    assert (
        client.get(f"/elaborazioni/step/documenti/{uuid.uuid4()}/pdf", headers=headers).status_code
        == 404
    )

    anomalies = client.get("/elaborazioni/step/ruolo-links", headers=headers).json()
    assert anomalies["total"] == 1 and anomalies["items"][0]["codice_fiscale"] == "NNNNNN80A01G113X"
    assert (
        client.get(
            "/elaborazioni/step/ruolo-links", headers=headers, params={"status": "linked"}
        ).json()["total"]
        == 2
    )
    assert (
        client.get(
            "/elaborazioni/step/ruolo-links", headers=headers, params={"status": "bogus"}
        ).status_code
        == 422
    )

    avviso_links = client.get(
        f"/elaborazioni/step/ruolo-avvisi/{avviso_id}", headers=headers
    ).json()
    assert {item["codice_fiscale"] for item in avviso_links} == {
        "RSSMRA80A01G113X",
        "ZZZZZZ80A01G113X",
    }


def test_pdf_download_handles_missing_files(client, session_factory, storage_dirs) -> None:
    headers = login(client)
    _, import_root = storage_dirs
    import_root.mkdir()
    build_archive(import_root / "raccolta.zip", [scheda()])
    with session_factory() as db:
        import_archive(db, import_root / "raccolta.zip", job_id=None)
        documento = db.scalar(select(StepDocumento))
        documento.pdf_path = "14215/missing.pdf"
        db.commit()
        documento_id = documento.id
    assert (
        client.get(f"/elaborazioni/step/documenti/{documento_id}/pdf", headers=headers).status_code
        == 404
    )
    assert client.get("/elaborazioni/step/overview", headers=headers).json()["import_archives"] == [
        "raccolta.zip"
    ]


def test_overview_without_import_folder(client, storage_dirs) -> None:
    overview = client.get("/elaborazioni/step/overview", headers=login(client)).json()
    assert overview["import_archives"] == [] and overview["contribuenti"] == 0
