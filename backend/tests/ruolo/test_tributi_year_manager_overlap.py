from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy import func, select

from app.modules.ruolo import tributi_repositories as repo
from app.modules.ruolo.models import RuoloTributiRegisteredMail, RuoloTributiYearManager

from .test_tributi_api import (
    TestingSessionLocal,
    auth_headers,
    client,
    seed_avviso,
    seed_subject_with_nas,
)
from .test_tributi_api import setup_database as setup_database


@pytest.mark.parametrize("policy_group", [False, True])
def test_overlapping_2021_manager_generates_only_unnotified_notices(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, policy_group: bool
) -> None:
    subject_id = seed_subject_with_nas(tmp_path)
    pending = seed_avviso(anno=2021, subject_id=subject_id)
    delivered = seed_avviso(anno=2021, subject_id=subject_id)
    seed_avviso(anno=2020, subject_id=subject_id)
    headers = auth_headers()
    managers = client.get("/ruolo/tributi/year-managers", headers=headers)
    assert managers.status_code == 200
    step = next(item for item in managers.json()["items"] if item["manager_key"] == "step")
    manager = client.post(
        "/ruolo/tributi/year-managers",
        headers=headers,
        json={
            "manager_key": "avvisi_2021",
            "manager_label": "Avvisi 2021 non notificati",
            "year_from": 2021,
            "year_to": 2021,
            "calculation_policy": "internal_gaia",
        },
    )
    assert manager.status_code == 200
    policy = client.post(
        "/ruolo/tributi/calculation-policies",
        headers=headers,
        json={
            "name": "Avvisi 2021",
            "year_from": 2021,
            "year_to": 2021,
            "only_unnotified": True,
            "surcharge_rate_percent": 0,
            "interest_rate_percent": 0,
        },
    )
    assert policy.status_code == 200
    with TestingSessionLocal() as db:
        db.add(
            RuoloTributiRegisteredMail(
                avviso_id=UUID(delivered),
                source_shipment_id="delivered-2021",
                raw_payload_json={"received_at": "2021-12-01"},
            )
        )
        db.commit()

    listed = client.get("/ruolo/tributi/avvisi?manager_key=avvisi_2021", headers=headers)
    assert listed.status_code == 200
    items = {item["id"]: item for item in listed.json()["items"]}
    assert set(items) == {pending, delivered}
    assert items[pending]["annuality_manager_key"] == "avvisi_2021"
    assert items[pending]["reminder_enabled"] is True
    assert items[delivered]["reminder_enabled"] is False
    detail = client.get(f"/ruolo/tributi/avvisi/{pending}", headers=headers)
    assert detail.json()["annuality_manager_key"] == "avvisi_2021"
    candidates = client.get(
        "/ruolo/tributi/solleciti/candidates?manager_key=avvisi_2021&anno_from=2021&anno_to=2021",
        headers=headers,
    )
    assert candidates.status_code == 200
    assert candidates.json()["total"] == 1
    assert candidates.json()["items"][0]["years"] == [2021]
    assert candidates.json()["items"][0]["avvisi_count"] == 1

    def generate_pdf(payload: dict, *, output_path: Path) -> None:
        assert payload["years"] == [2021]
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"%PDF-1.4 test")

    monkeypatch.setattr(repo, "generate_batch_reminder_pdf", generate_pdf)
    batch = client.post(
        "/ruolo/tributi/solleciti/batches",
        headers=headers,
        json={
            "codice_fiscale": ["RSSMRA80A01H501Z"],
            "filters": {
                "manager_key": "avvisi_2021",
                "years": [2021],
                "policy_group": policy_group,
            },
        },
    )
    assert batch.status_code == 200
    item = batch.json()["items"][0]
    assert item["status"] == "generated"
    assert item["years_json"] == [2021]
    assert item["avviso_ids_json"] == [pending]
    assert (
        client.post(
            f"/ruolo/tributi/avvisi/{delivered}/reminders", headers=headers, json={}
        ).status_code
        == 422
    )
    current_managers = client.get("/ruolo/tributi/year-managers", headers=headers)
    assert (
        next(item for item in current_managers.json()["items"] if item["id"] == step["id"]) == step
    )


def test_overlapping_manager_precedence_is_deterministic_and_reversible() -> None:
    instant = datetime(2026, 1, 1, tzinfo=UTC)
    with TestingSessionLocal() as db:
        managers = [
            RuoloTributiYearManager(
                id=UUID(int=index),
                manager_key=key,
                manager_label=key,
                year_from=start,
                year_to=end,
                calculation_policy="internal_gaia",
                is_active=True,
                updated_at=updated,
            )
            for index, key, start, end, updated in [
                (1, "all", None, None, instant),
                (2, "step", 2018, 2021, instant),
                (3, "open", 2021, None, instant),
                (4, "wide", 2021, 2025, instant),
                (5, "single", 2021, 2021, instant),
                (6, "latest", 2021, 2021, datetime(2026, 1, 2, tzinfo=UTC)),
                (7, "tie", 2021, 2021, datetime(2026, 1, 2, tzinfo=UTC)),
            ]
        ]
        db.add_all(managers)
        db.flush()
        for expected in reversed(managers):
            assert repo.get_year_manager_for_year(db, 2021)["manager_key"] == expected.manager_key
            expected.is_active = False
            db.flush()
        assert repo.get_year_manager_for_year(db, 2021)["manager_key"] is None


@pytest.mark.parametrize("username", [None, "ruolo-tributi-viewer"])
def test_overlapping_manager_mutations_require_manage_permission(username: str | None) -> None:
    admin_headers = auth_headers()
    managers = client.get("/ruolo/tributi/year-managers", headers=admin_headers).json()["items"]
    manager_id = next(item["id"] for item in managers if item["manager_key"] == "step")
    headers = auth_headers(username) if username else {}
    payload = {
        "manager_key": "avvisi_2021",
        "manager_label": "Avvisi 2021",
        "year_from": 2021,
        "year_to": 2021,
        "calculation_policy": "internal_gaia",
    }
    for method, path in [
        ("POST", "/ruolo/tributi/year-managers"),
        ("PUT", f"/ruolo/tributi/year-managers/{manager_id}"),
        ("DELETE", f"/ruolo/tributi/year-managers/{manager_id}"),
    ]:
        response = client.request(method, path, headers=headers, json=payload)
        assert response.status_code == (403 if username else 401)
    assert (
        client.get("/ruolo/tributi/year-managers", headers=admin_headers).json()["items"]
        == managers
    )


def test_overlapping_manager_update_rollback_and_delete_persist_across_sessions() -> None:
    headers = auth_headers()
    client.get("/ruolo/tributi/year-managers", headers=headers)
    payload = {
        "manager_key": "Avvisi 2021!",
        "manager_label": "Avvisi 2021",
        "year_from": 2021,
        "year_to": 2021,
        "calculation_policy": "internal_gaia",
    }
    created = client.post("/ruolo/tributi/year-managers", headers=headers, json=payload)
    assert created.status_code == 200
    manager_id = created.json()["id"]
    with TestingSessionLocal() as db:
        manager = db.get(RuoloTributiYearManager, UUID(manager_id))
        assert manager.manager_key == "avvisi_2021"
        assert manager.updated_by == 1
        assert repo.get_year_manager_for_year(db, 2021)["manager_key"] == "avvisi_2021"
    invalid = client.put(
        f"/ruolo/tributi/year-managers/{manager_id}",
        headers=headers,
        json={**payload, "manager_label": "Non salvare", "year_from": 2022},
    )
    assert invalid.status_code == 422
    with TestingSessionLocal() as db:
        assert db.get(RuoloTributiYearManager, UUID(manager_id)).manager_label == "Avvisi 2021"
        assert db.scalar(select(func.count()).select_from(RuoloTributiYearManager)) == 4
    updated = client.put(
        f"/ruolo/tributi/year-managers/{manager_id}",
        headers=headers,
        json={**payload, "year_from": 2020, "is_active": False},
    )
    assert updated.status_code == 200
    with TestingSessionLocal() as db:
        assert db.get(RuoloTributiYearManager, UUID(manager_id)).year_from == 2020
        assert repo.get_year_manager_for_year(db, 2021)["manager_key"] == "step"
    assert (
        client.delete(f"/ruolo/tributi/year-managers/{manager_id}", headers=headers).status_code
        == 204
    )
    with TestingSessionLocal() as db:
        assert db.get(RuoloTributiYearManager, UUID(manager_id)) is None
        assert repo.get_year_manager_for_year(db, 2021)["manager_key"] == "step"


def test_2021_external_management_stays_ineligible_for_generation() -> None:
    avviso_id = seed_avviso(anno=2021)
    headers = auth_headers()
    detail = client.get(f"/ruolo/tributi/avvisi/{avviso_id}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["annuality_manager_key"] == "step"
    assert detail.json()["reminder_enabled"] is False
    candidates = client.get(
        "/ruolo/tributi/solleciti/candidates?anno_from=2021&anno_to=2021", headers=headers
    )
    assert candidates.status_code == 200
    assert candidates.json()["items"] == []
    assert (
        client.post(
            f"/ruolo/tributi/avvisi/{avviso_id}/reminders", headers=headers, json={}
        ).status_code
        == 422
    )
