from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from app.modules.catasto.services.ade_status_scan import persist_ade_status_scan_result
from app.modules.ruolo.models import RuoloParticella


class FakeSession:
    def __init__(self, ruolo_particella) -> None:
        self.ruolo_particella = ruolo_particella
        self.get_calls: list[tuple[object, object]] = []

    def get(self, model, object_id):
        self.get_calls.append((model, object_id))
        if model is RuoloParticella and object_id == self.ruolo_particella.id:
            return self.ruolo_particella
        return None


def test_persist_ade_status_scan_result_updates_ruolo_particella_payload() -> None:
    ruolo_id = uuid4()
    request_id = uuid4()
    document_id = uuid4()
    payload = {
        "classification": "suppressed",
        "requested": {"comune": "SAN VERO MILIS", "foglio": "18", "particella": "1174"},
        "originated_or_varied_parcels": [
            {"foglio": "18", "particella": "4180", "subalterno": None},
            {"foglio": "18", "particella": "4181", "subalterno": None},
        ],
    }
    ruolo_particella = SimpleNamespace(
        id=ruolo_id,
        ade_scan_status=None,
        ade_scan_classification=None,
        ade_scan_checked_at=None,
        ade_scan_request_id=None,
        ade_scan_document_id=None,
        ade_scan_error="old error",
        ade_scan_payload_json=None,
    )

    persist_ade_status_scan_result(
        FakeSession(ruolo_particella),
        ruolo_particella_id=ruolo_id,
        request_id=request_id,
        status="completed",
        classification="suppressed",
        document_id=document_id,
        payload=payload,
        error=None,
    )

    assert ruolo_particella.ade_scan_status == "completed"
    assert ruolo_particella.ade_scan_classification == "suppressed"
    assert ruolo_particella.ade_scan_checked_at is not None
    assert ruolo_particella.ade_scan_request_id == request_id
    assert ruolo_particella.ade_scan_document_id == document_id
    assert ruolo_particella.ade_scan_error is None
    assert ruolo_particella.ade_scan_payload_json == payload


def test_persist_ade_status_scan_result_ignores_missing_ruolo_particella() -> None:
    ruolo_particella = SimpleNamespace(id=uuid4())

    persist_ade_status_scan_result(
        FakeSession(ruolo_particella),
        ruolo_particella_id=uuid4(),
        request_id=uuid4(),
        status="failed",
        classification="unknown",
        payload={"classification": "unknown"},
        error="not found",
    )

    assert not hasattr(ruolo_particella, "ade_scan_status")
