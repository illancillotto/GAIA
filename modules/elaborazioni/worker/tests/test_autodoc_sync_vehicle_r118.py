"""Characterization of the per-vehicle step of ``run_autodoc_sync_job_by_id``.

All Playwright interactions are faked: no browser or live portal is used.
"""

from __future__ import annotations

import asyncio
import copy
import logging
import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

import autodoc_sync

VEHICLE_FIELDS = (
    "autodoc_url",
    "autodoc_title",
    "autodoc_data",
    "autodoc_synced_at",
    "autodoc_sync_error",
    "brand",
    "fuel_type",
    "year_of_manufacture",
)
MISSING_URL_ERROR = (
    "Link AUTODOC mancante: la sync massiva aggiorna solo i mezzi con URL AUTODOC gia salvato"
)


class _Scalars:
    def __init__(self, values):
        self._values = values

    def all(self):
        return self._values


class RecordingDb:
    """Fake session that snapshots job and vehicle state at every commit."""

    def __init__(self, job, vehicles):
        self.job = job
        self.vehicles = vehicles
        self.snapshots: list[dict] = []
        self.closed = False

    def get(self, _model, _identifier):
        return self.job

    def scalars(self, _statement):
        return _Scalars(self.vehicles)

    def commit(self):
        self.snapshots.append(
            {
                "status": self.job.status,
                "params": copy.deepcopy(self.job.params_json),
                "records": (
                    self.job.records_synced,
                    self.job.records_skipped,
                    self.job.records_errors,
                ),
                "error_detail": self.job.error_detail,
                "vehicles": [
                    {name: getattr(vehicle, name) for name in VEHICLE_FIELDS}
                    for vehicle in self.vehicles
                ],
            }
        )

    def close(self):
        self.closed = True


def _job(vehicles, *, force_refresh=False):
    return SimpleNamespace(
        entity=autodoc_sync.AUTODOC_SYNC_ENTITY,
        params_json={
            "vehicle_ids": [str(vehicle.id) for vehicle in vehicles],
            "force_refresh": force_refresh,
        },
        status="queued",
        finished_at=None,
        records_synced=None,
        records_skipped=None,
        records_errors=None,
        error_detail=None,
    )


def _vehicle(name, **overrides):
    values = {
        "id": uuid.uuid4(),
        "name": name,
        "code": name.upper(),
        "plate_number": None,
        "autodoc_url": None,
        "autodoc_synced_at": None,
        "autodoc_data": None,
        "autodoc_sync_error": None,
        "autodoc_title": None,
        "brand": None,
        "fuel_type": None,
        "year_of_manufacture": None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


class FakeBrowser:
    def __init__(self) -> None:
        self.playwright = object()
        self.browser = object()
        self.context = object()
        self.page = object()
        self.closed: list[tuple[object, ...]] = []

    async def build(self):
        return self.playwright, self.browser, self.context, self.page

    async def close(self, *parts):
        self.closed.append(parts)


@pytest.fixture
def browser(monkeypatch) -> FakeBrowser:
    fake = FakeBrowser()
    monkeypatch.setattr(autodoc_sync, "_build_browser", fake.build)
    monkeypatch.setattr(autodoc_sync, "_close_browser", fake.close)
    return fake


def _run(db) -> None:
    asyncio.run(autodoc_sync.run_autodoc_sync_job_by_id(lambda: db, uuid.uuid4()))


def _install_snapshots(monkeypatch, browser, snapshots, calls):
    async def extract(page, url):
        assert page is browser.page
        calls.append(url)
        outcome = snapshots[url]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    monkeypatch.setattr(autodoc_sync, "_extract_vehicle_snapshot", extract)


def test_recent_results_are_trimmed_to_last_ten(browser) -> None:
    vehicles = [_vehicle(f"v{index:02d}") for index in range(12)]
    job = _job(vehicles)
    db = RecordingDb(job, vehicles)

    _run(db)

    final = db.snapshots[-1]["params"]
    expected = [
        {"vehicle_id": str(vehicle.id), "status": "skipped", "reason": "missing_autodoc_url"}
        for vehicle in vehicles[2:]
    ]
    assert final["recent_results"] == expected
    # The 11th progress commit is the first one that trims the list.
    progress = [snap["params"]["recent_results"] for snap in db.snapshots[2:-1:2]]
    assert [len(item) for item in progress] == [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 10, 10]
    assert progress[10][0]["vehicle_id"] == str(vehicles[1].id)
    assert final["processed_items"] == 12
    assert final["skipped_items"] == 12
    assert final["progress_percent"] == 100
    assert job.status == "completed"
    assert job.error_detail is None
    assert (job.records_synced, job.records_skipped, job.records_errors) == (0, 12, 0)
    assert all(vehicle.autodoc_sync_error == MISSING_URL_ERROR for vehicle in vehicles)
    assert browser.closed == [(browser.playwright, browser.browser, browser.context)]
    assert db.closed is True


def test_snapshot_never_overwrites_existing_identity_fields(monkeypatch, browser) -> None:
    previous = datetime(2020, 1, 1, tzinfo=UTC)
    keeps = _vehicle(
        "a-keeps",
        autodoc_url="https://saved/keeps",
        autodoc_sync_error="old error",
        brand="Iveco",
        fuel_type="Benzina",
        year_of_manufacture=1999,
    )
    non_digit = _vehicle("b-non-digit", autodoc_url="https://saved/non-digit")
    empty_data = _vehicle(
        "c-empty",
        autodoc_url="https://saved/empty",
        autodoc_synced_at=previous,
    )
    vehicles = [keeps, non_digit, empty_data]
    job = _job(vehicles)
    db = RecordingDb(job, vehicles)
    calls: list[str] = []
    full = {"Marca": "Fiat", "Carburante": "Diesel", "Anno da": "2012"}
    _install_snapshots(
        monkeypatch,
        browser,
        {
            "https://saved/keeps": ("Keeps title", full),
            "https://saved/non-digit": (
                "Non digit title",
                {"Marca": "Fiat", "Carburante": "", "Anno da": "20XX"},
            ),
            "https://saved/empty": ("Empty title", {}),
        },
        calls,
    )
    before = datetime.now(UTC)

    _run(db)

    after = datetime.now(UTC)
    assert calls == ["https://saved/keeps", "https://saved/non-digit", "https://saved/empty"]
    assert (keeps.brand, keeps.fuel_type, keeps.year_of_manufacture) == ("Iveco", "Benzina", 1999)
    assert keeps.autodoc_title == "Keeps title"
    assert keeps.autodoc_data is full
    assert keeps.autodoc_sync_error is None
    assert (non_digit.brand, non_digit.fuel_type, non_digit.year_of_manufacture) == (
        "Fiat",
        None,
        None,
    )
    assert (empty_data.brand, empty_data.fuel_type, empty_data.year_of_manufacture) == (
        None,
        None,
        None,
    )
    assert empty_data.autodoc_data == {}
    for vehicle in vehicles:
        assert before <= vehicle.autodoc_synced_at <= after
    results = db.snapshots[-1]["params"]["recent_results"]
    assert results == [
        {"vehicle_id": str(vehicle.id), "status": "synced", "autodoc_url_discovered": False}
        for vehicle in vehicles
    ]
    assert (job.records_synced, job.records_skipped, job.records_errors) == (3, 0, 0)
    assert job.status == "completed"


def test_discovery_disabled_with_plate_skips_without_lookup(monkeypatch, browser) -> None:
    discovered_for: list[str] = []

    async def discover(_page, plate):
        discovered_for.append(plate)
        return "https://discovered/unexpected"

    monkeypatch.setattr(autodoc_sync, "_discover_vehicle_url_by_plate", discover)
    vehicle = _vehicle("plate-only", plate_number="AB123CD")
    job = _job([vehicle])
    db = RecordingDb(job, [vehicle])

    _run(db)

    assert discovered_for == []
    assert vehicle.autodoc_url is None
    assert vehicle.autodoc_synced_at is None
    assert vehicle.autodoc_sync_error == MISSING_URL_ERROR
    assert db.snapshots[-1]["params"]["recent_results"] == [
        {"vehicle_id": str(vehicle.id), "status": "skipped", "reason": "missing_autodoc_url"}
    ]
    assert job.status == "completed"


def test_discovery_outcomes_none_found_and_error(monkeypatch, browser) -> None:
    returns_none = _vehicle("a-none", plate_number="NONE01", autodoc_url="")
    found = _vehicle("b-found", plate_number="FOUND1")
    raises = _vehicle("c-raises", plate_number="RAISE1")
    no_plate = _vehicle("d-no-plate", plate_number="")
    vehicles = [returns_none, found, raises, no_plate]
    discovered_for: list[str] = []

    async def discover(page, plate):
        assert page is browser.page
        discovered_for.append(plate)
        if plate == "RAISE1":
            raise RuntimeError("discovery blocked")
        if plate == "FOUND1":
            return "https://discovered/found"
        return None

    calls: list[str] = []
    _install_snapshots(
        monkeypatch,
        browser,
        {"https://discovered/found": ("Found", {"Marca": "Fiat"})},
        calls,
    )
    monkeypatch.setattr(autodoc_sync, "AUTODOC_ENABLE_PLATE_DISCOVERY", True)
    monkeypatch.setattr(autodoc_sync, "_discover_vehicle_url_by_plate", discover)
    job = _job(vehicles)
    db = RecordingDb(job, vehicles)

    _run(db)

    assert discovered_for == ["NONE01", "FOUND1", "RAISE1"]
    assert calls == ["https://discovered/found"]
    assert returns_none.autodoc_url is None
    assert returns_none.autodoc_sync_error == MISSING_URL_ERROR
    assert returns_none.autodoc_synced_at is None
    assert found.autodoc_url == "https://discovered/found"
    assert found.brand == "Fiat"
    assert raises.autodoc_url is None
    assert raises.autodoc_sync_error == "discovery blocked"
    assert raises.autodoc_synced_at is not None
    assert no_plate.autodoc_url is None
    assert no_plate.autodoc_sync_error == MISSING_URL_ERROR
    assert db.snapshots[-1]["params"]["recent_results"] == [
        {"vehicle_id": str(returns_none.id), "status": "skipped", "reason": "missing_autodoc_url"},
        {"vehicle_id": str(found.id), "status": "synced", "autodoc_url_discovered": True},
        {"vehicle_id": str(raises.id), "status": "failed", "reason": "discovery blocked"},
        {"vehicle_id": str(no_plate.id), "status": "skipped", "reason": "missing_autodoc_url"},
    ]
    assert (job.records_synced, job.records_skipped, job.records_errors) == (1, 2, 1)
    assert job.status == "completed"
    assert job.error_detail == "c-raises: discovery blocked"


def test_partial_success_is_completed_with_first_twenty_errors(monkeypatch, browser) -> None:
    failures = [
        _vehicle(f"f{index:02d}", autodoc_url=f"https://saved/f{index:02d}") for index in range(21)
    ]
    success = _vehicle("zz-success", autodoc_url="https://saved/ok")
    vehicles = [*failures, success]
    snapshots = {vehicle.autodoc_url: RuntimeError(f"boom {vehicle.name}") for vehicle in failures}
    snapshots["https://saved/ok"] = ("Ok", {})
    _install_snapshots(monkeypatch, browser, snapshots, [])
    job = _job(vehicles)
    db = RecordingDb(job, vehicles)

    _run(db)

    assert job.status == "completed"
    assert job.error_detail == "\n".join(
        f"{vehicle.name}: boom {vehicle.name}" for vehicle in failures[:20]
    )
    assert (job.records_synced, job.records_skipped, job.records_errors) == (1, 0, 21)
    final = db.snapshots[-1]["params"]
    assert final["failed_items"] == 21
    assert final["success_items"] == 1
    assert final["completed_at"] == job.finished_at.isoformat()
    assert failures[0].autodoc_sync_error == "boom f00"


CACHED_AT = datetime(2024, 5, 1, tzinfo=UTC)


def _run_mixed_job(monkeypatch, browser):
    vehicles = [
        _vehicle("a-missing"),
        _vehicle(
            "b-cached",
            autodoc_url="https://saved/cached",
            autodoc_synced_at=CACHED_AT,
            autodoc_data={"cached": True},
        ),
        _vehicle("c-fresh", autodoc_url="https://saved/fresh"),
        _vehicle("d-broken", autodoc_url="https://saved/broken"),
    ]
    calls: list[str] = []
    _install_snapshots(
        monkeypatch,
        browser,
        {
            "https://saved/fresh": ("Fresh", {"Anno da": "2001"}),
            "https://saved/broken": RuntimeError("snapshot failed"),
        },
        calls,
    )
    job = _job(vehicles)
    original_params = copy.deepcopy(job.params_json)
    db = RecordingDb(job, vehicles)
    _run(db)
    return db, original_params, calls


def _expected_params_per_commit(original_params, vehicles, results, counters):
    progress = {
        **original_params,
        "selected_total": len(vehicles),
        "processed_items": 0,
        "success_items": 0,
        "failed_items": 0,
        "skipped_items": 0,
        "current_vehicle": None,
        "progress_percent": 0,
        "recent_results": [],
    }
    expected = [progress]
    for index, (synced, errors, skipped) in enumerate(counters, start=1):
        progress = {
            **progress,
            "current_vehicle": vehicles[index - 1].name,
            "processed_items": index - 1,
        }
        expected.append(progress)
        progress = {
            **progress,
            "recent_results": results[:index],
            "processed_items": index,
            "success_items": synced,
            "failed_items": errors,
            "skipped_items": skipped,
            "progress_percent": round(index / len(vehicles) * 100),
            "current_vehicle": None,
        }
        expected.append(progress)
    return expected


def test_per_commit_params_snapshots(monkeypatch, browser) -> None:
    db, original_params, calls = _run_mixed_job(monkeypatch, browser)
    missing, cached, fresh, broken = db.vehicles
    job = db.job

    assert calls == ["https://saved/fresh", "https://saved/broken"]
    results = [
        {"vehicle_id": str(missing.id), "status": "skipped", "reason": "missing_autodoc_url"},
        {"vehicle_id": str(cached.id), "status": "skipped", "reason": "already_synced"},
        {"vehicle_id": str(fresh.id), "status": "synced", "autodoc_url_discovered": False},
        {"vehicle_id": str(broken.id), "status": "failed", "reason": "snapshot failed"},
    ]
    expected = _expected_params_per_commit(
        original_params,
        db.vehicles,
        results,
        [(0, 0, 1), (0, 0, 2), (1, 0, 2), (1, 1, 2)],
    )
    expected.append({**expected[-1], "completed_at": job.finished_at.isoformat()})
    assert [snap["params"] for snap in db.snapshots] == expected
    assert [snap["status"] for snap in db.snapshots] == ["running"] * 9 + ["completed"]
    assert [snap["records"] for snap in db.snapshots] == [
        (None, None, None),
        (None, None, None),
        (0, 1, 0),
        (0, 1, 0),
        (0, 2, 0),
        (0, 2, 0),
        (1, 2, 0),
        (1, 2, 0),
        (1, 2, 1),
        (1, 2, 1),
    ]
    assert [snap["error_detail"] for snap in db.snapshots] == [None] * 9 + [
        "d-broken: snapshot failed"
    ]
    assert job.status == "completed"
    assert db.closed is True


def test_vehicle_mutations_are_visible_at_their_progress_commit(monkeypatch, browser) -> None:
    db, _original_params, _calls = _run_mixed_job(monkeypatch, browser)
    _missing, cached, _fresh, broken = db.vehicles

    assert db.snapshots[5]["vehicles"][2]["autodoc_title"] is None
    assert db.snapshots[6]["vehicles"][2]["autodoc_title"] == "Fresh"
    assert db.snapshots[6]["vehicles"][2]["year_of_manufacture"] == 2001
    assert db.snapshots[7]["vehicles"][3]["autodoc_sync_error"] is None
    assert db.snapshots[8]["vehicles"][3]["autodoc_sync_error"] == "snapshot failed"
    assert cached.autodoc_synced_at == CACHED_AT
    assert cached.autodoc_title is None
    assert cached.autodoc_sync_error is None
    assert broken.autodoc_synced_at is not None


def test_per_vehicle_log_messages(monkeypatch, browser, caplog) -> None:
    with caplog.at_level(logging.INFO, logger=autodoc_sync.logger.name):
        db, _original_params, _calls = _run_mixed_job(monkeypatch, browser)

    messages = [record.getMessage() for record in caplog.records]
    for index, vehicle in enumerate(db.vehicles, start=1):
        assert (
            f"AUTODOC sync mezzo {index}/4 id={vehicle.id} code={vehicle.code} plate=None"
            in messages
        )
    assert "AUTODOC snapshot avviata per mezzo C-FRESH url=https://saved/fresh" in messages
    assert "AUTODOC sync completata per mezzo C-FRESH discovered=False" in messages
    assert "AUTODOC sync fallita per mezzo D-BROKEN: snapshot failed" in messages


def test_force_refresh_resyncs_already_synced_vehicle(monkeypatch, browser) -> None:
    cached = _vehicle(
        "cached",
        autodoc_url="https://saved/cached",
        autodoc_synced_at=datetime(2024, 5, 1, tzinfo=UTC),
        autodoc_data={"cached": True},
    )
    calls: list[str] = []
    _install_snapshots(
        monkeypatch, browser, {"https://saved/cached": ("Refreshed", {"new": "1"})}, calls
    )
    job = _job([cached], force_refresh=True)
    db = RecordingDb(job, [cached])

    _run(db)

    assert calls == ["https://saved/cached"]
    assert cached.autodoc_title == "Refreshed"
    assert cached.autodoc_data == {"new": "1"}
    assert (job.records_synced, job.records_skipped, job.records_errors) == (1, 0, 0)


def test_non_ascii_digit_year_fails_after_partial_snapshot_write(monkeypatch, browser) -> None:
    vehicle = _vehicle("superscript", autodoc_url="https://saved/superscript")
    data = {"Marca": "Fiat", "Carburante": "Diesel", "Anno da": "²"}
    assert data["Anno da"].isdigit()
    _install_snapshots(
        monkeypatch, browser, {"https://saved/superscript": ("Superscript", data)}, []
    )
    job = _job([vehicle])
    db = RecordingDb(job, [vehicle])

    _run(db)

    message = "invalid literal for int() with base 10: '²'"
    assert job.status == "failed"
    assert (job.records_synced, job.records_skipped, job.records_errors) == (0, 0, 1)
    assert job.error_detail == f"superscript: {message}"
    final = db.snapshots[-1]["params"]
    assert (final["success_items"], final["skipped_items"], final["failed_items"]) == (0, 0, 1)
    assert final["recent_results"] == [
        {"vehicle_id": str(vehicle.id), "status": "failed", "reason": message}
    ]
    assert vehicle.autodoc_title == "Superscript"
    assert vehicle.autodoc_data is data
    assert vehicle.brand == "Fiat"
    assert vehicle.fuel_type == "Diesel"
    assert vehicle.year_of_manufacture is None
    assert vehicle.autodoc_synced_at is not None
    assert vehicle.autodoc_sync_error == message
