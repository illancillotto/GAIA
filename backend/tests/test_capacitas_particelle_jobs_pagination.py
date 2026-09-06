from __future__ import annotations

from test_elaborazioni_capacitas import TestingSessionLocal, auth_headers, client
from test_elaborazioni_capacitas import setup_database as setup_database

from app.models.capacitas import CapacitasParticelleSyncJob
from app.services.elaborazioni_capacitas_particelle_sync import list_particelle_sync_jobs

JOBS_URL = "/elaborazioni/capacitas/involture/particelle/jobs"


def test_recent_jobs_are_limited_in_sql_without_hiding_active_jobs() -> None:
    with TestingSessionLocal() as db:
        jobs = [
            CapacitasParticelleSyncJob(
                status=job_status,
                mode="progressive_catalog",
                payload_json={"only_due": True},
                result_json={"processed_items": index},
            )
            for index, job_status in enumerate(
                ["pending", "processing", "queued_resume", "cancelling"] + ["succeeded"] * 205
            )
        ]
        db.add_all(jobs)
        db.commit()
        ids = [job.id for job in jobs]

    response = client.get(JOBS_URL, headers=auth_headers())
    assert response.status_code == 200
    assert [row["id"] for row in response.json()] == ids[-50:][::-1] + ids[:4][::-1]
    assert response.json()[0]["result_json"] == {"processed_items": 208}

    # A job outside the recent window remains available through its detail endpoint.
    detail = client.get(f"{JOBS_URL}/{ids[4]}", headers=auth_headers())
    assert detail.status_code == 200
    assert detail.json()["result_json"] == {"processed_items": 4}

    with TestingSessionLocal() as db:
        assert [job.id for job in list_particelle_sync_jobs(db)] == ids[-50:][::-1] + ids[:4][::-1]


def test_empty_jobs_page_and_authentication() -> None:
    response = client.get(JOBS_URL, headers=auth_headers())
    assert response.status_code == 200
    assert response.json() == []
    assert client.get(JOBS_URL).status_code == 401
