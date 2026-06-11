"""Test API chat: POST /wiki/chat."""

from __future__ import annotations

from collections.abc import Generator
from datetime import date, datetime, timedelta
from unittest.mock import patch
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.core.security import hash_password
from app.db.base import Base
from app.main import app
from app.models.application_user import ApplicationUser
from app.models.catasto_phase1 import CatParticella
from app.models.effective_permission import EffectivePermission
from app.models.nas_user import NasUser
from app.models.review import Review
from app.models.section_permission import RoleSectionPermission, Section, UserSectionPermission
from app.models.share import Share
from app.models.wc_sync_job import WCSyncJob
from app.modules.operazioni.models.attachments import StorageQuotaAlert, StorageQuotaMetric
from app.modules.operazioni.models.activities import ActivityApproval, ActivityCatalog, OperatorActivity
from app.modules.operazioni.models.wc_operator import WCOperator
from app.modules.operazioni.models.vehicles import (
    FleetUnresolvedTransaction,
    Vehicle,
    VehicleAssignment,
    VehicleFuelLog,
    VehicleMaintenance,
    VehicleMaintenanceType,
    VehicleUsageSession,
)
from app.modules.operazioni.models.reports import FieldReport, FieldReportCategory, FieldReportSeverity, InternalCase, InternalCaseEvent
from app.modules.network.models import NetworkAlert, NetworkDevice, NetworkFirewall, NetworkFirewallEvent, NetworkScan
from app.modules.riordino.models import RiordinoIssue, RiordinoPhase, RiordinoPractice, RiordinoStep
from app.modules.ruolo.models import RuoloAvviso, RuoloImportJob
from app.modules.utenze.models import AnagraficaCompany, AnagraficaPerson, AnagraficaSubject
from app.modules.wiki.models import (
    WikiConversation,
    WikiConversationEvent,
    WikiConversationMetricsBackfillJob,
    WikiConversationMessage,
    WikiTelemetryDailyMetric,
    WikiTelemetryPeriodMetric,
    WikiToolAuditLog,
)
from app.modules.wiki.services.conversation_backfill_jobs import (
    process_next_wiki_conversation_metrics_backfill_job,
    prune_wiki_conversation_metrics_backfill_jobs,
)
from app.modules.wiki.schemas import WikiChatResponse, WikiChatStreamChunk, WikiChunkSource
from app.modules.wiki.services.semantic_router import WikiSemanticRoute


engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def override_get_db() -> Generator[Session, None, None]:
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_database() -> Generator[None, None, None]:
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(engine)
    yield
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)


def _create_user(username: str = "user", role: str = "viewer", **extra_fields: object) -> None:
    db = TestingSessionLocal()
    db.add(ApplicationUser(
        username=username,
        email=f"{username}@test.local",
        password_hash=hash_password("pass123"),
        role=role,
        is_active=True,
        **extra_fields,
    ))
    db.commit()
    db.close()


def _login(username: str) -> str:
    resp = client.post("/auth/login", json={"username": username, "password": "pass123"})
    assert resp.status_code == 200
    return resp.json()["access_token"]


_MOCK_RESPONSE = WikiChatResponse(
    answer="GAIA è la piattaforma IT governance del Consorzio.",
    sources=[WikiChunkSource(source_file="ARCHITECTURE.md", section_title="Intro", excerpt="...")],
    found=True,
    conversation_id=str(uuid4()),
)

_NOT_FOUND_RESPONSE = WikiChatResponse(
    answer="Non ho trovato documenti rilevanti.",
    sources=[],
    found=False,
)


# ── autenticazione ────────────────────────────────────────────────────────────

def test_chat_unauthenticated_returns_401() -> None:
    resp = client.post("/wiki/chat", json={"question": "Cos'è GAIA?"})
    assert resp.status_code == 401


# ── disponibilità orchestrator / codex-lb ──────────────────────────────────────

def test_chat_returns_503_when_codex_lb_unavailable() -> None:
    _create_user("u1")
    token = _login("u1")

    with patch(
        "app.modules.wiki.routes.chat.answer_with_orchestration",
        side_effect=RuntimeError("Wiki Agent non disponibile: codex-lb non raggiungibile su CODEX_LB_URL."),
    ):
        resp = client.post(
            "/wiki/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={"question": "Cos'è GAIA?"},
        )
    assert resp.status_code == 503
    assert "codex-lb" in resp.json()["detail"].lower() or "wiki" in resp.json()["detail"].lower()


def test_chat_routes_live_network_summary_via_semantic_router() -> None:
    _create_user("wiki_network_user", module_rete=True)
    token = _login("wiki_network_user")

    db = TestingSessionLocal()
    scan = NetworkScan(
        network_range="192.168.1.0/24",
        scan_type="incremental",
        status="completed",
        hosts_scanned=12,
        active_hosts=10,
        discovered_devices=10,
        initiated_by="test",
    )
    db.add(scan)
    db.flush()
    db.add_all(
        [
            NetworkDevice(
                last_scan_id=scan.id,
                ip_address="192.168.1.13",
                hostname="SIMONA-PC",
                display_name="Simona Frau",
                status="online",
                is_known_device=True,
            ),
            NetworkDevice(
                last_scan_id=scan.id,
                ip_address="192.168.1.14",
                hostname="MARISA-PC",
                display_name="Marisa Carrus",
                status="offline",
                is_known_device=True,
            ),
            NetworkFirewall(
                vendor="Sophos",
                name="Sophos XGS87",
                management_ip="192.168.1.126",
                status="online",
            ),
            NetworkAlert(
                alert_type="FIREWALL_EVENT",
                severity="warning",
                status="open",
                title="Evento firewall warning",
            ),
        ]
    )
    db.commit()
    db.close()

    with (
        patch(
            "app.modules.wiki.services.orchestrator.route_wiki_question",
            return_value=WikiSemanticRoute(
                language="ru",
                normalized_query="mostrami il riepilogo rete",
                intent="live_data",
                capability="internal_live_data",
                module_hint="rete",
            ),
        ),
        patch("app.modules.wiki.services.orchestrator.is_wiki_available", return_value=True),
    ):
        resp = client.post(
            "/wiki/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={"question": "Покажи мне сводку по сети"},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["mode"] == "live_data"
    assert body["found"] is True
    assert body["tool_calls"][0]["tool_name"] == "get_network_dashboard_summary"
    assert body["evidences"][0]["source_key"] == "rete.dashboard.summary"
    assert "dispositivi" in body["answer"].lower()


def test_chat_persists_conversation_and_supports_reload() -> None:
    _create_user("wiki_thread_user")
    token = _login("wiki_thread_user")
    docs_response = WikiChatResponse(
        answer="GAIA thread test.",
        sources=[WikiChunkSource(source_file="THREAD.md", section_title="Intro", excerpt="...")],
        found=True,
    )

    with (
        patch("app.modules.wiki.services.orchestrator.is_wiki_available", return_value=True),
        patch("app.modules.wiki.services.orchestrator.answer_question", return_value=docs_response),
    ):
        first = client.post(
            "/wiki/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={"question": "Apri thread wiki"},
        )
    assert first.status_code == 200
    first_data = first.json()
    assert first_data["conversation_id"] is not None
    conversation_id = first_data["conversation_id"]
    conversation_uuid = UUID(conversation_id)

    db = TestingSessionLocal()
    conversation = db.get(WikiConversation, conversation_uuid)
    assert conversation is not None
    messages = db.query(WikiConversationMessage).filter(WikiConversationMessage.conversation_id == conversation.id).all()
    assert len(messages) == 2
    audit = db.query(WikiToolAuditLog).filter(WikiToolAuditLog.conversation_id == conversation.id).first()
    assert audit is not None
    db.close()

    with (
        patch("app.modules.wiki.services.orchestrator.is_wiki_available", return_value=True),
        patch("app.modules.wiki.services.orchestrator.answer_question", return_value=docs_response),
    ):
        second = client.post(
            "/wiki/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={"question": "Continua thread wiki", "conversation_id": conversation_id},
        )
    assert second.status_code == 200
    assert second.json()["conversation_id"] == conversation_id

    conversation_resp = client.get(
        f"/wiki/conversations/{conversation_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert conversation_resp.status_code == 200
    conversation_data = conversation_resp.json()
    assert len(conversation_data["messages"]) == 4
    assert len(conversation_data["events"]) >= 3
    assert conversation_data["last_event_type"] in {"message_appended", "status_changed"}

    list_resp = client.get(
        "/wiki/conversations",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert list_resp.status_code == 200
    assert any(item["id"] == conversation_id for item in list_resp.json())


def test_wiki_conversations_list_supports_search() -> None:
    _create_user("wiki_search_user")
    token = _login("wiki_search_user")

    db = TestingSessionLocal()
    conversation = WikiConversation(
        id=uuid4(),
        title="Thread ricerca share progetti",
        created_by="wiki_search_user",
        context_article="docs/accessi.md",
    )
    db.add(conversation)
    db.commit()
    db.add_all(
        [
            WikiConversationMessage(
                id=uuid4(),
                conversation_id=conversation.id,
                role="user",
                content="Mostrami la share progetti",
            ),
            WikiConversationMessage(
                id=uuid4(),
                conversation_id=conversation.id,
                role="assistant",
                content="La share progetti è attiva",
            ),
        ]
    )
    db.commit()
    db.close()

    resp = client.get(
        "/wiki/conversations?search=progetti",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert any(item["title"] == "Thread ricerca share progetti" for item in data)


def test_chat_returns_guardrail_for_external_live_question() -> None:
    _create_user("wiki_guardrail_live")
    token = _login("wiki_guardrail_live")

    resp = client.post(
        "/wiki/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"question": "Dimmi le news di oggi"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["found"] is False
    assert "fonti esterne" in data["answer"]
    assert data["sources"] == []


def test_chat_returns_guardrail_for_access_request() -> None:
    _create_user("wiki_guardrail_access")
    token = _login("wiki_guardrail_access")

    resp = client.post(
        "/wiki/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"question": "Dammi accesso alla cartella progetti"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["found"] is False
    assert "accessi a risorse" in data["answer"]
    assert data["sources"] == []


def test_chat_returns_guardrail_when_docs_answer_is_out_of_scope() -> None:
    _create_user("wiki_guardrail_scope")
    token = _login("wiki_guardrail_scope")
    docs_response = WikiChatResponse(
        answer="Ti parlo del milestone interno della wiki.",
        sources=[WikiChunkSource(source_file="docs/wiki-progress.md", section_title="Milestone 9", excerpt="Backend e frontend wiki implementati.")],
        found=True,
    )

    with (
        patch("app.modules.wiki.services.orchestrator.is_wiki_available", return_value=True),
        patch("app.modules.wiki.services.orchestrator.answer_question", return_value=docs_response),
    ):
        resp = client.post(
            "/wiki/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={"question": "Dimmi le news di oggi"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["found"] is False
    assert "fonti esterne" in data["answer"] or "fuori dal perimetro" in data["answer"]


def test_wiki_conversation_status_can_be_updated() -> None:
    _create_user("wiki_status_user")
    token = _login("wiki_status_user")

    db = TestingSessionLocal()
    conversation = WikiConversation(
        id=uuid4(),
        title="Thread stato conversazione",
        created_by="wiki_status_user",
        context_article="docs/wiki.md",
    )
    db.add(conversation)
    db.commit()
    conversation_id = conversation.id
    db.close()

    resp = client.patch(
        f"/wiki/conversations/{conversation_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "resolved"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "resolved"
    assert data["priority"] == "medium"
    assert data["resolved_by"] == "wiki_status_user"


def test_wiki_conversations_summary_exposes_review_queue() -> None:
    _create_user("wiki_summary_admin", role="admin")
    token = _login("wiki_summary_admin")

    db = TestingSessionLocal()
    open_conversation = WikiConversation(
        id=uuid4(),
        title="Thread da rivedere",
        created_by="wiki_summary_admin",
        context_article="docs/accessi.md",
        status="open",
    )
    resolved_conversation = WikiConversation(
        id=uuid4(),
        title="Thread risolto",
        created_by="wiki_summary_admin",
        context_article="docs/catasto.md",
        status="resolved",
        resolved_by="wiki_summary_admin",
    )
    db.add_all([open_conversation, resolved_conversation])
    db.commit()
    db.add_all(
        [
            WikiToolAuditLog(
                id=uuid4(),
                username="wiki_summary_admin",
                role="admin",
                intent="live_data",
                mode="hybrid",
                tool_name="find_share_by_name",
                module_key="accessi",
                conversation_id=open_conversation.id,
                question_hash="hash-open",
                question_preview="Apri share progetti",
                success=0,
                found=0,
                latency_ms=120,
                docs_source_count=0,
                evidence_count=0,
                fallback_reason="tool_denied",
            ),
            WikiToolAuditLog(
                id=uuid4(),
                username="wiki_summary_admin",
                role="admin",
                intent="docs_only",
                mode="docs_only",
                tool_name="rag_docs",
                module_key="catasto",
                conversation_id=resolved_conversation.id,
                question_hash="hash-resolved",
                question_preview="Mostra dashboard catasto",
                success=1,
                found=1,
                latency_ms=50,
                docs_source_count=1,
                evidence_count=1,
            ),
        ]
    )
    db.commit()
    db.close()

    resp = client.get(
        "/wiki/conversations/summary",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert data["open_count"] == 1
    assert data["in_review_count"] == 0
    assert data["waiting_user_count"] == 0
    assert data["resolved_count"] == 1
    assert data["needs_review_count"] == 1
    assert data["high_priority_count"] == 0
    assert data["unassigned_review_count"] == 1
    assert data["open_denied_count"] == 1
    assert data["open_fallback_count"] == 1
    assert data["top_review_reasons"][0]["key"] == "denied_present"
    assert data["items_needing_review"][0]["title"] == "Thread da rivedere"


def test_wiki_conversation_metrics_summary_and_series_endpoints() -> None:
    _create_user("wiki_metrics_admin", role="admin")
    token = _login("wiki_metrics_admin")

    db = TestingSessionLocal()
    created_at = datetime.utcnow() - timedelta(days=1)
    resolved_at = datetime.utcnow()
    conversation = WikiConversation(
        id=uuid4(),
        title="Thread metriche conversazioni",
        created_by="wiki_metrics_admin",
        context_article="docs/accessi.md",
        status="resolved",
        priority="high",
        assigned_to="wiki_metrics_admin",
        resolved_by="wiki_metrics_admin",
        created_at=created_at,
        resolved_at=resolved_at,
        last_reviewed_at=resolved_at,
    )
    db.add(conversation)
    db.add(
        WikiToolAuditLog(
            id=uuid4(),
            username="wiki_metrics_admin",
            role="admin",
            intent="live_data",
            mode="hybrid",
            tool_name="find_share_by_name",
            module_key="accessi",
            conversation_id=conversation.id,
            question_hash="metrics-hash",
            question_preview="Apri share metriche",
            success=0,
            found=0,
            latency_ms=140,
            docs_source_count=0,
            evidence_count=0,
            fallback_reason="tool_denied",
            entity_key="accessi.shares.progetti",
        )
    )
    db.add_all(
        [
            WikiConversationEvent(
                id=uuid4(),
                conversation_id=conversation.id,
                event_type="status_changed",
                actor_username="wiki_metrics_admin",
                from_status="open",
                to_status="in_review",
                created_at=created_at + timedelta(hours=1),
            ),
            WikiConversationEvent(
                id=uuid4(),
                conversation_id=conversation.id,
                event_type="assignment_changed",
                actor_username="wiki_metrics_admin",
                created_at=created_at + timedelta(hours=2),
            ),
            WikiConversationEvent(
                id=uuid4(),
                conversation_id=conversation.id,
                event_type="status_changed",
                actor_username="wiki_metrics_admin",
                from_status="resolved",
                to_status="open",
                created_at=created_at + timedelta(hours=3),
            ),
        ]
    )
    db.commit()
    db.close()

    summary_resp = client.get(
        "/wiki/conversations/metrics/summary?days=30",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert summary_resp.status_code == 200
    summary_data = summary_resp.json()
    assert summary_data["total_threads"] >= 1
    assert summary_data["closed_count"] >= 1
    assert summary_data["high_priority_count"] >= 1
    assert summary_data["review_entered_count"] >= 1
    assert summary_data["reassigned_count"] >= 1
    assert summary_data["reopened_count"] >= 1

    series_resp = client.get(
        "/wiki/conversations/metrics/series?dimension_type=global&days=30&granularity=day",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert series_resp.status_code == 200
    series_data = series_resp.json()
    assert series_data["dimension_type"] == "global"
    assert len(series_data["items"]) >= 1
    assert any(item["closed_count"] >= 1 for item in series_data["items"])
    assert any(item["review_entered_count"] >= 1 for item in series_data["items"])


def test_wiki_conversations_support_governance_filters() -> None:
    _create_user("wiki_filters_admin", role="admin")
    token = _login("wiki_filters_admin")

    db = TestingSessionLocal()
    review_conversation = WikiConversation(
        id=uuid4(),
        title="Thread backlog review",
        created_by="wiki_filters_admin",
        context_article="docs/accessi.md",
        status="in_review",
        priority="high",
        assigned_to="triage_admin",
        review_reason="manual_flag",
    )
    clean_conversation = WikiConversation(
        id=uuid4(),
        title="Thread clean",
        created_by="wiki_filters_admin",
        context_article="docs/catasto.md",
        status="open",
        priority="low",
    )
    db.add_all([review_conversation, clean_conversation])
    db.commit()
    review_conversation_id = review_conversation.id
    db.close()

    resp = client.get(
        "/wiki/conversations?assigned_to=triage_admin&priority=high&needs_review=true&review_reason=manual_flag",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["id"] == str(review_conversation_id)
    assert data[0]["status"] == "in_review"
    assert data[0]["priority"] == "high"
    assert data[0]["assigned_to"] == "triage_admin"
    assert data[0]["review_reason"] == "manual_flag"
    assert data[0]["reopen_count"] == 0


def test_wiki_conversation_patch_updates_priority_assignment_and_review_state() -> None:
    _create_user("wiki_queue_admin", role="admin")
    token = _login("wiki_queue_admin")

    db = TestingSessionLocal()
    conversation = WikiConversation(
        id=uuid4(),
        title="Thread presa in carico",
        created_by="wiki_queue_admin",
        context_article="docs/wiki.md",
    )
    db.add(conversation)
    db.commit()
    conversation_id = conversation.id
    db.close()

    resp = client.patch(
        f"/wiki/conversations/{conversation_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "in_review", "priority": "high", "assigned_to": "wiki_queue_admin"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "in_review"
    assert data["priority"] == "high"
    assert data["assigned_to"] == "wiki_queue_admin"
    assert data["last_reviewed_at"] is not None
    assert data["last_event_type"] == "status_changed"

    db = TestingSessionLocal()
    events = db.query(WikiConversationEvent).filter(WikiConversationEvent.conversation_id == conversation_id).all()
    assert len(events) >= 3
    db.close()


def test_wiki_conversation_flag_sets_manual_review_reason() -> None:
    _create_user("wiki_flag_admin", role="admin")
    token = _login("wiki_flag_admin")

    db = TestingSessionLocal()
    conversation = WikiConversation(
        id=uuid4(),
        title="Thread flag manuale",
        created_by="wiki_flag_admin",
        context_article="docs/wiki.md",
        status="open",
    )
    db.add(conversation)
    db.commit()
    conversation_id = conversation.id
    db.close()

    resp = client.post(
        f"/wiki/conversations/{conversation_id}/flag",
        headers={"Authorization": f"Bearer {token}"},
        json={"review_reason": "manual_flag"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "in_review"
    assert data["review_reason"] == "manual_flag"
    assert data["needs_review"] is True
    assert data["last_event_type"] == "flagged"


def test_wiki_conversation_context_link_resolves_accessi_records() -> None:
    _create_user("wiki_context_admin", role="admin")
    token = _login("wiki_context_admin")

    db = TestingSessionLocal()
    db.add(
        NasUser(
            id=12,
            username="mrossi",
            full_name="Mario Rossi",
            email="mrossi@test.local",
            source_uid="UID-12",
            is_active=True,
            last_seen_snapshot_id=9,
        )
    )
    db.add(
        Share(
            id=21,
            name="progetti",
            path="/volume1/progetti",
            sector="IT",
            description="Area progetti",
            last_seen_snapshot_id=4,
        )
    )
    db.commit()
    db.close()

    user_resp = client.get(
        "/wiki/conversations/context-link?entity_key=accessi.nas-users.mrossi&module_key=accessi",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert user_resp.status_code == 200
    assert user_resp.json()["href"] == "/nas-control/users/12"
    assert user_resp.json()["resolved"] is True

    share_resp = client.get(
        "/wiki/conversations/context-link?entity_key=accessi.shares.progetti&module_key=accessi",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert share_resp.status_code == 200
    assert share_resp.json()["href"] == "/nas-control/shares/21"
    assert share_resp.json()["resolved"] is True


def test_wiki_conversation_context_link_resolves_ruolo_record() -> None:
    _create_user("wiki_ruolo_admin", role="admin")
    token = _login("wiki_ruolo_admin")
    subject_id = uuid4()
    avviso_id = uuid4()
    import_job_id = uuid4()

    db = TestingSessionLocal()
    db.add(
        RuoloImportJob(
            id=import_job_id,
            anno_tributario=2026,
            filename="ruolo.csv",
            status="completed",
            triggered_by=None,
        )
    )
    db.add(
        RuoloAvviso(
            id=avviso_id,
            import_job_id=import_job_id,
            codice_cnc="CNC-1",
            anno_tributario=2026,
            subject_id=subject_id,
            codice_fiscale_raw="CNTMRC67P66A357L",
            nominativo_raw="Mario Contu",
            importo_totale_euro=120.5,
        )
    )
    db.commit()
    db.close()

    resp = client.get(
        f"/wiki/conversations/context-link?entity_key=ruolo.subjects.{subject_id}&module_key=ruolo",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["href"] == f"/ruolo/avvisi/{avviso_id}"
    assert resp.json()["resolved"] is True


def test_wiki_conversation_governance_config_and_backfill_endpoints() -> None:
    _create_user("wiki_governance_admin", role="admin")
    token = _login("wiki_governance_admin")

    get_resp = client.get(
        "/wiki/conversations/governance-config",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert get_resp.status_code == 200

    patch_resp = client.patch(
        "/wiki/conversations/governance-config",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "fallback_heavy_threshold": 3,
            "no_match_repeated_threshold": 4,
            "high_latency_ms_threshold": 1500,
        },
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["fallback_heavy_threshold"] == 3

    backfill_resp = client.post(
        "/wiki/conversations/metrics/backfill",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "start_date": "2026-05-01",
            "end_date": "2026-05-03",
            "data_complete_from": "2026-05-01",
        },
    )
    assert backfill_resp.status_code == 200
    assert backfill_resp.json()["data_complete_from"] == "2026-05-01"

    enqueue_resp = client.post(
        "/wiki/conversations/metrics/backfill-jobs",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "start_date": "2026-05-02",
            "end_date": "2026-05-03",
            "data_complete_from": "2026-05-01",
        },
    )
    assert enqueue_resp.status_code == 201
    assert enqueue_resp.json()["parent_job_id"] is None
    assert enqueue_resp.json()["retry_count"] == 0
    assert enqueue_resp.json()["requested_by"] == "wiki_governance_admin"
    assert enqueue_resp.json()["progress_total_days"] == 2
    assert enqueue_resp.json()["status"] == "pending"

    latest_job_resp = client.get(
        "/wiki/conversations/metrics/backfill-jobs/latest",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert latest_job_resp.status_code == 200
    assert latest_job_resp.json() is not None
    assert latest_job_resp.json()["requested_by"] == "wiki_governance_admin"

    list_jobs_resp = client.get(
        "/wiki/conversations/metrics/backfill-jobs?limit=5",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert list_jobs_resp.status_code == 200
    assert len(list_jobs_resp.json()["items"]) >= 1

    list_job_chains_resp = client.get(
        "/wiki/conversations/metrics/backfill-job-chains?limit=5",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert list_job_chains_resp.status_code == 200
    assert len(list_job_chains_resp.json()["items"]) >= 1
    assert list_job_chains_resp.json()["items"][0]["root_job_id"] == enqueue_resp.json()["id"]
    assert list_job_chains_resp.json()["items"][0]["chain_status"] == "pending"
    assert list_job_chains_resp.json()["items"][0]["latest_job"]["queue_position"] == 1
    assert list_job_chains_resp.json()["items"][0]["latest_job"]["is_latest_attempt"] is True

    summary_resp = client.get(
        "/wiki/conversations/metrics/backfill-job-chains/summary",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert summary_resp.status_code == 200
    assert summary_resp.json()["total_chains"] >= 1
    assert summary_resp.json()["chains_with_active_retry"] >= 1

    detail_resp = client.get(
        f"/wiki/conversations/metrics/backfill-job-chains/{enqueue_resp.json()['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert detail_resp.status_code == 200
    assert detail_resp.json()["root_job_id"] == enqueue_resp.json()["id"]
    assert detail_resp.json()["chain_status"] == "pending"

    db = TestingSessionLocal()
    processed_job = process_next_wiki_conversation_metrics_backfill_job(db)
    assert processed_job is not None
    assert processed_job.status == "completed"
    db.close()


def test_wiki_conversation_backfill_job_rejects_concurrent_runs() -> None:
    _create_user("wiki_backfill_admin", role="admin")
    token = _login("wiki_backfill_admin")

    db = TestingSessionLocal()
    db.add(
        WikiConversationMetricsBackfillJob(
            id=uuid4(),
            status="running",
            requested_by="wiki_backfill_admin",
            start_date=date(2026, 5, 1),
            end_date=date(2026, 5, 3),
            progress_total_days=3,
            progress_completed_days=1,
            progress_message="In corso",
        )
    )
    db.commit()
    db.close()

    resp = client.post(
        "/wiki/conversations/metrics/backfill-jobs",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "start_date": "2026-05-04",
            "end_date": "2026-05-05",
            "data_complete_from": "2026-05-04",
        },
    )
    assert resp.status_code == 409


def test_wiki_conversation_backfill_job_prune_removes_old_terminal_jobs() -> None:
    db = TestingSessionLocal()
    old_job = WikiConversationMetricsBackfillJob(
        id=uuid4(),
        status="completed",
        requested_by="admin",
        start_date=date(2026, 4, 1),
        end_date=date(2026, 4, 2),
        progress_total_days=2,
        progress_completed_days=2,
        created_at=datetime.now() - timedelta(days=90),
        finished_at=datetime.now() - timedelta(days=89),
    )
    fresh_job = WikiConversationMetricsBackfillJob(
        id=uuid4(),
        status="completed",
        requested_by="admin",
        start_date=date(2026, 5, 1),
        end_date=date(2026, 5, 2),
        progress_total_days=2,
        progress_completed_days=2,
    )
    db.add_all([old_job, fresh_job])
    db.commit()
    old_job_id = old_job.id
    fresh_job_id = fresh_job.id

    deleted_count = prune_wiki_conversation_metrics_backfill_jobs(db, retention_days=30)
    assert deleted_count >= 1
    assert db.get(WikiConversationMetricsBackfillJob, old_job_id) is None
    assert db.get(WikiConversationMetricsBackfillJob, fresh_job_id) is not None
    db.close()


def test_wiki_conversation_backfill_job_retry_and_clear_history() -> None:
    _create_user("wiki_retry_admin", role="admin")
    token = _login("wiki_retry_admin")

    db = TestingSessionLocal()
    failed_job = WikiConversationMetricsBackfillJob(
        id=uuid4(),
        status="failed",
        requested_by="wiki_retry_admin",
        start_date=date(2026, 5, 1),
        end_date=date(2026, 5, 2),
        data_complete_from=date(2026, 5, 1),
        progress_total_days=2,
        progress_completed_days=1,
        error_detail="boom",
    )
    completed_job = WikiConversationMetricsBackfillJob(
        id=uuid4(),
        status="completed",
        requested_by="wiki_retry_admin",
        start_date=date(2026, 5, 3),
        end_date=date(2026, 5, 4),
        progress_total_days=2,
        progress_completed_days=2,
    )
    db.add_all([failed_job, completed_job])
    db.commit()
    failed_job_id = failed_job.id
    db.close()

    retry_resp = client.post(
        f"/wiki/conversations/metrics/backfill-jobs/{failed_job_id}/retry",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert retry_resp.status_code == 201
    assert retry_resp.json()["status"] == "pending"
    assert retry_resp.json()["start_date"] == "2026-05-01"
    assert retry_resp.json()["parent_job_id"] == str(failed_job_id)
    assert retry_resp.json()["retry_count"] == 1

    filtered_chain_resp = client.get(
        "/wiki/conversations/metrics/backfill-job-chains?latest_status=pending&requested_by=wiki_retry_admin&has_active_retry=true&sort_by=oldest_active_first",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert filtered_chain_resp.status_code == 200
    assert len(filtered_chain_resp.json()["items"]) >= 1
    assert filtered_chain_resp.json()["items"][0]["has_active_retry"] is True

    detail_resp = client.get(
        f"/wiki/conversations/metrics/backfill-job-chains/{failed_job_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert detail_resp.status_code == 200
    assert detail_resp.json()["retry_count_total"] == 1

    stale_retry_resp = client.post(
        f"/wiki/conversations/metrics/backfill-jobs/{failed_job_id}/retry",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert stale_retry_resp.status_code == 409

    clear_resp = client.delete(
        "/wiki/conversations/metrics/backfill-jobs",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert clear_resp.status_code == 200
    assert clear_resp.json()["deleted_count"] >= 2


def test_wiki_non_admin_cannot_update_foreign_conversation() -> None:
    _create_user("wiki_owner")
    _create_user("wiki_other_user")
    token = _login("wiki_other_user")

    db = TestingSessionLocal()
    conversation = WikiConversation(
        id=uuid4(),
        title="Thread di altro owner",
        created_by="wiki_owner",
        context_article="docs/wiki.md",
    )
    db.add(conversation)
    db.commit()
    conversation_id = conversation.id
    db.close()

    resp = client.patch(
        f"/wiki/conversations/{conversation_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "resolved"},
    )

    assert resp.status_code == 403


# ── risposta corretta ─────────────────────────────────────────────────────────

def test_chat_returns_answer_and_sources() -> None:
    _create_user("u2")
    token = _login("u2")

    with patch("app.modules.wiki.routes.chat.answer_with_orchestration", return_value=_MOCK_RESPONSE):
        resp = client.post(
            "/wiki/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={"question": "Cos'è GAIA?"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["found"] is True
    assert "GAIA" in data["answer"]
    assert len(data["sources"]) == 1
    assert data["sources"][0]["source_file"] == "ARCHITECTURE.md"


def test_chat_stream_returns_sse_events() -> None:
    _create_user("u2_stream")
    token = _login("u2_stream")

    stream_chunks = [
        WikiChatStreamChunk(
            event="meta",
            data={
                "mode": _MOCK_RESPONSE.mode,
                "found": _MOCK_RESPONSE.found,
                "conversation_id": str(_MOCK_RESPONSE.conversation_id),
                "tool_calls": [],
                "sources": [item.model_dump(mode="json") for item in _MOCK_RESPONSE.sources],
                "evidences": [],
            },
        ),
        WikiChatStreamChunk(event="delta", data={"text": "GAIA è"}),
        WikiChatStreamChunk(
            event="done",
            data={"answer": _MOCK_RESPONSE.answer, "conversation_id": str(_MOCK_RESPONSE.conversation_id)},
        ),
    ]

    with patch("app.modules.wiki.routes.chat.stream_with_orchestration", return_value=iter(stream_chunks)):
        resp = client.post(
            "/wiki/chat/stream",
            headers={"Authorization": f"Bearer {token}"},
            json={"question": "Cos'è GAIA?"},
        )

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")
    assert "event: meta" in resp.text
    assert "event: delta" in resp.text
    assert "event: done" in resp.text
    assert str(_MOCK_RESPONSE.conversation_id) in resp.text


def test_chat_found_false_when_no_relevant_docs() -> None:
    _create_user("u3")
    token = _login("u3")

    with patch("app.modules.wiki.routes.chat.answer_with_orchestration", return_value=_NOT_FOUND_RESPONSE):
        resp = client.post(
            "/wiki/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={"question": "Feature inesistente"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["found"] is False
    assert data["sources"] == []


def test_chat_passes_context_article_to_rag() -> None:
    _create_user("u4")
    token = _login("u4")

    with patch("app.modules.wiki.routes.chat.answer_with_orchestration", return_value=_MOCK_RESPONSE) as mock_orchestrator:
        resp = client.post(
            "/wiki/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={"question": "Domanda", "context_article": "PRD.md"},
        )

    assert resp.status_code == 200
    call_args = mock_orchestrator.call_args
    assert call_args[0][3] == "PRD.md"


def test_chat_internal_error_returns_500() -> None:
    _create_user("u5")
    token = _login("u5")

    with patch("app.modules.wiki.routes.chat.answer_with_orchestration", side_effect=Exception("errore interno")):
        resp = client.post(
            "/wiki/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={"question": "Domanda"},
        )

    assert resp.status_code == 500


def test_chat_empty_question_returns_422() -> None:
    _create_user("u6")
    token = _login("u6")

    resp = client.post(
        "/wiki/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"question": ""},
    )
    assert resp.status_code == 422


def test_chat_all_user_roles_can_use() -> None:
    """Tutti i ruoli autenticati possono usare la chat."""
    for role in ("viewer", "reviewer", "admin", "super_admin"):
        username = f"role_{role}"
        _create_user(username, role)
        token = _login(username)

        with patch("app.modules.wiki.routes.chat.answer_with_orchestration", return_value=_MOCK_RESPONSE):
            resp = client.post(
                "/wiki/chat",
                headers={"Authorization": f"Bearer {token}"},
                json={"question": "Test"},
            )
        assert resp.status_code == 200, f"Role {role} got {resp.status_code}"


def test_chat_live_accessi_summary_uses_orchestrator_tool() -> None:
    _create_user("live_accessi")
    token = _login("live_accessi")

    resp = client.post(
        "/wiki/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"question": "Quante review accessi ci sono in dashboard?"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["mode"] == "live_data"
    assert data["tool_calls"][0]["tool_name"] == "get_nas_dashboard_summary"
    assert data["sources"] == []
    assert data["found"] is True


def test_chat_live_catasto_denied_when_module_not_enabled() -> None:
    _create_user("no_catasto", module_catasto=False)
    token = _login("no_catasto")

    resp = client.post(
        "/wiki/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"question": "Quante anomalie catasto ci sono?"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["mode"] == "live_data"
    assert data["found"] is False
    assert data["tool_calls"][0]["success"] is False
    assert "permessi" in data["answer"].lower()


def test_chat_lookup_particella_by_id_returns_live_detail() -> None:
    _create_user("catasto_user", module_catasto=True)
    token = _login("catasto_user")
    particella_id = uuid4()

    db = TestingSessionLocal()
    db.add(
        CatParticella(
            id=particella_id,
            cod_comune_capacitas=95,
            codice_catastale="A357",
            nome_comune="Oristano",
            foglio="12",
            particella="345",
            subalterno=None,
            source_type="shapefile",
            valid_from=date(2025, 1, 1),
            is_current=True,
            suppressed=False,
        )
    )
    db.commit()
    db.close()

    resp = client.post(
        "/wiki/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"question": f"Mostrami la particella catasto {particella_id}"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["mode"] == "live_data"
    assert data["tool_calls"][0]["tool_name"] == "find_particella_by_id"
    assert "Oristano" in data["answer"]
    assert str(particella_id) in data["evidences"][0]["source_key"]
    assert "geometry" not in data["evidences"][0]["payload"]
    assert data["evidences"][0]["payload"]["has_geometry"] is False


def test_chat_lookup_nas_user_returns_live_detail() -> None:
    _create_user("accessi_user")
    token = _login("accessi_user")

    db = TestingSessionLocal()
    db.add(
        NasUser(
            username="mrossi",
            full_name="Mario Rossi",
            email="mrossi@test.local",
            source_uid="UID-1",
            is_active=True,
            last_seen_snapshot_id=7,
        )
    )
    db.commit()
    db.close()

    resp = client.post(
        "/wiki/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"question": "Cerca utente NAS mrossi"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["mode"] == "live_data"
    assert data["tool_calls"][0]["tool_name"] == "find_nas_user"
    assert "Mario Rossi" in data["answer"]
    assert data["evidences"][0]["source_key"] == "accessi.nas-users.mrossi"
    assert "email" not in data["evidences"][0]["payload"]
    assert "source_uid" not in data["evidences"][0]["payload"]
    assert data["evidences"][0]["payload"]["email_domain"] == "test.local"


def test_chat_lookup_subject_by_cf_returns_live_detail() -> None:
    _create_user("utenze_user", module_utenze=True)
    token = _login("utenze_user")
    subject_id = uuid4()

    db = TestingSessionLocal()
    db.add(
        AnagraficaSubject(
            id=subject_id,
            subject_type="person",
            status="active",
            source_system="gaia",
            source_name_raw="Mario Rossi",
            nas_folder_letter="M",
            requires_review=False,
        )
    )
    db.add(
        AnagraficaPerson(
            subject_id=subject_id,
            cognome="Rossi",
            nome="Mario",
            codice_fiscale="RSSMRA80A01H501U",
        )
    )
    db.commit()
    db.close()

    resp = client.post(
        "/wiki/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"question": "Trova soggetto utenze con codice fiscale RSSMRA80A01H501U"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["mode"] == "live_data"
    assert data["tool_calls"][0]["tool_name"] == "find_subject_by_cf"
    assert "Mario Rossi" in data["answer"]
    assert str(subject_id) in data["evidences"][0]["source_key"]
    assert "documents" not in data["evidences"][0]["payload"]
    assert sorted(data["evidences"][0]["payload"].keys()) == [
        "display_name",
        "documents_count",
        "id",
        "requires_review",
        "status",
        "subject_type",
    ]


def test_chat_lookup_vehicle_by_id_returns_live_detail() -> None:
    _create_user("operazioni_user", module_operazioni=True)
    token = _login("operazioni_user")
    vehicle_id = uuid4()

    db = TestingSessionLocal()
    db.add(
        Vehicle(
            id=vehicle_id,
            code="VM-01",
            plate_number="AB123CD",
            asset_tag="MEZZO-01",
            name="Piaggio Porter",
            vehicle_type="van",
            brand="Piaggio",
            model="Porter",
            fuel_type="diesel",
            current_status="available",
            has_gps_device=True,
            is_active=True,
        )
    )
    db.commit()
    db.close()

    resp = client.post(
        "/wiki/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"question": f"Mostrami il mezzo operazioni {vehicle_id}"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["mode"] == "live_data"
    assert data["tool_calls"][0]["tool_name"] == "find_vehicle_by_id"
    assert "Piaggio Porter" in data["answer"]
    assert str(vehicle_id) in data["evidences"][0]["source_key"]


def test_chat_lookup_operazioni_activity_returns_live_detail() -> None:
    _create_user("operazioni_activity_user", module_operazioni=True)
    token = _login("operazioni_activity_user")
    activity_id = uuid4()

    db = TestingSessionLocal()
    user = db.query(ApplicationUser).filter(ApplicationUser.username == "operazioni_activity_user").one()
    vehicle = Vehicle(
        code="VM-ACT-01",
        plate_number="ZZ123YY",
        name="Daily attivita",
        vehicle_type="van",
        current_status="available",
        created_by_user_id=user.id,
    )
    catalog = ActivityCatalog(
        code="SOPR",
        name="Sopralluogo rete",
        category="field",
        requires_vehicle=True,
    )
    db.add_all([vehicle, catalog])
    db.flush()
    db.add(
        OperatorActivity(
            id=activity_id,
            activity_catalog_id=catalog.id,
            operator_user_id=user.id,
            vehicle_id=vehicle.id,
            status="submitted",
            started_at=datetime(2026, 5, 27, 8, 0, 0),
            ended_at=datetime(2026, 5, 27, 9, 15, 0),
            duration_minutes_declared=75,
            duration_minutes_calculated=75,
            text_note="Verifica rete irrigua",
            submitted_at=datetime(2026, 5, 27, 9, 16, 0),
            created_by_user_id=user.id,
        )
    )
    db.commit()
    db.close()

    resp = client.post(
        "/wiki/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"question": f"Mostrami l'attivita operazioni {activity_id}"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["mode"] == "live_data"
    assert data["tool_calls"][0]["tool_name"] == "find_operazioni_activity_by_id"
    assert "Sopralluogo rete" in data["answer"]
    assert str(activity_id) in data["evidences"][0]["source_key"]


def test_chat_live_operazioni_pending_approvals_returns_summary() -> None:
    _create_user("operazioni_pending_user", module_operazioni=True)
    token = _login("operazioni_pending_user")

    db = TestingSessionLocal()
    user = db.query(ApplicationUser).filter(ApplicationUser.username == "operazioni_pending_user").one()
    catalog = ActivityCatalog(
        code="PEND",
        name="Attivita pending",
        category="field",
        requires_vehicle=False,
    )
    db.add(catalog)
    db.flush()
    db.add(
        OperatorActivity(
            activity_catalog_id=catalog.id,
            operator_user_id=user.id,
            status="submitted",
            started_at=datetime(2026, 5, 27, 9, 0, 0),
            ended_at=datetime(2026, 5, 27, 9, 20, 0),
            submitted_at=datetime(2026, 5, 27, 9, 21, 0),
            created_by_user_id=user.id,
        )
    )
    db.commit()
    db.close()

    resp = client.post(
        "/wiki/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"question": "Quante approvazioni operazioni sono in revisione?"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["mode"] == "live_data"
    assert data["tool_calls"][0]["tool_name"] == "get_operazioni_pending_approvals"
    assert data["evidences"][0]["payload"]["count"] == 1


def test_chat_live_operazioni_storage_status_returns_summary() -> None:
    _create_user("operazioni_storage_user", module_operazioni=True)
    token = _login("operazioni_storage_user")

    db = TestingSessionLocal()
    metric = StorageQuotaMetric(
        measured_at=datetime(2026, 5, 27, 10, 0, 0),
        total_bytes_used=850,
        quota_bytes=1000,
        percentage_used=85,
    )
    db.add(metric)
    db.flush()
    db.add(
        StorageQuotaAlert(
            alert_level="warning",
            threshold_percentage=80,
            triggered_at=datetime(2026, 5, 27, 10, 5, 0),
            metric_id=metric.id,
        )
    )
    db.commit()
    db.close()

    resp = client.post(
        "/wiki/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"question": "Qual è lo stato storage operazioni?"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["mode"] == "live_data"
    assert data["tool_calls"][0]["tool_name"] == "get_operazioni_storage_status"
    assert data["evidences"][0]["payload"]["metric"]["percentage_used"] == 85.0
    assert data["evidences"][0]["payload"]["active_alert_count"] == 1


def test_chat_live_operazioni_mobile_sync_returns_summary() -> None:
    _create_user("operazioni_mobile_sync_user", module_operazioni=True)
    token = _login("operazioni_mobile_sync_user")

    db = TestingSessionLocal()
    user = db.query(ApplicationUser).filter(ApplicationUser.username == "operazioni_mobile_sync_user").one()
    db.add(
        WCOperator(
            wc_id=101,
            username="mob.user",
            email="mob.user@test.local",
            first_name="Mob",
            last_name="User",
            enabled=True,
            gaia_user_id=user.id,
            wc_synced_at=datetime(2026, 5, 27, 8, 0, 0),
        )
    )
    db.commit()
    db.close()

    resp = client.post(
        "/wiki/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"question": "Dammi lo stato mobile sync operazioni"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["mode"] == "live_data"
    assert data["tool_calls"][0]["tool_name"] == "get_operazioni_mobile_sync_status"
    assert data["evidences"][0]["payload"]["operators_count"] == 1
    assert data["evidences"][0]["payload"]["catalogs_count"] >= 1


def test_chat_live_operazioni_autodoc_sync_returns_summary() -> None:
    _create_user("operazioni_autodoc_user", module_operazioni=True)
    token = _login("operazioni_autodoc_user")

    db = TestingSessionLocal()
    user = db.query(ApplicationUser).filter(ApplicationUser.username == "operazioni_autodoc_user").one()
    job = WCSyncJob(
        entity="autodoc_vehicle_details",
        status="running",
        records_synced=4,
        records_skipped=1,
        records_errors=0,
        triggered_by=user.id,
        params_json={"selected_total": 8},
    )
    db.add(job)
    db.commit()
    db.close()

    resp = client.post(
        "/wiki/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"question": "Qual è lo stato sync autodoc operazioni?"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["mode"] == "live_data"
    assert data["tool_calls"][0]["tool_name"] == "get_operazioni_autodoc_sync_status"
    assert data["evidences"][0]["payload"]["status"] == "running"


def test_chat_live_operazioni_analytics_summary_returns_data() -> None:
    _create_user("operazioni_analytics_summary_user", module_operazioni=True)
    token = _login("operazioni_analytics_summary_user")

    db = TestingSessionLocal()
    user = db.query(ApplicationUser).filter(ApplicationUser.username == "operazioni_analytics_summary_user").one()
    vehicle = Vehicle(
        code="AN-SUM-01",
        name="Mezzo analytics summary",
        vehicle_type="van",
        current_status="available",
        created_by_user_id=user.id,
    )
    db.add(vehicle)
    db.flush()
    db.add(
        VehicleUsageSession(
            vehicle_id=vehicle.id,
            started_by_user_id=user.id,
            actual_driver_user_id=user.id,
            started_at=datetime(2026, 5, 27, 8, 0, 0),
            ended_at=datetime(2026, 5, 27, 9, 0, 0),
            start_odometer_km=1000,
            end_odometer_km=1040,
            status="closed",
        )
    )
    db.add(
        VehicleFuelLog(
            vehicle_id=vehicle.id,
            recorded_by_user_id=user.id,
            fueled_at=datetime(2026, 5, 27, 10, 0, 0),
            liters=30,
            total_cost=55,
            station_name="Test station",
        )
    )
    db.commit()
    db.close()

    resp = client.post(
        "/wiki/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"question": "Mostrami la summary analytics operazioni"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["mode"] == "live_data"
    assert data["tool_calls"][0]["tool_name"] == "get_operazioni_analytics_summary"
    assert data["evidences"][0]["payload"]["total_km"] > 0


def test_chat_live_operazioni_analytics_top_fuel_returns_data() -> None:
    _create_user("operazioni_analytics_top_user", module_operazioni=True)
    token = _login("operazioni_analytics_top_user")

    db = TestingSessionLocal()
    user = db.query(ApplicationUser).filter(ApplicationUser.username == "operazioni_analytics_top_user").one()
    vehicle = Vehicle(
        code="AN-TOP-01",
        plate_number="TOP123",
        name="Mezzo top fuel",
        vehicle_type="truck",
        current_status="available",
        created_by_user_id=user.id,
    )
    db.add(vehicle)
    db.flush()
    db.add(
        VehicleFuelLog(
            vehicle_id=vehicle.id,
            recorded_by_user_id=user.id,
            fueled_at=datetime(2026, 5, 27, 11, 0, 0),
            liters=80,
            total_cost=120,
            station_name="Top station",
        )
    )
    db.commit()
    db.close()

    resp = client.post(
        "/wiki/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"question": "Mostrami i top mezzi carburante analytics operazioni"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["mode"] == "live_data"
    assert data["tool_calls"][0]["tool_name"] == "get_operazioni_analytics_top_fuel_vehicles"
    assert data["evidences"][0]["payload"]["top_vehicles"][0]["total_liters"] > 0


def test_chat_live_operazioni_analytics_top_km_operators_returns_data() -> None:
    _create_user("operazioni_analytics_km_top_user", module_operazioni=True)
    token = _login("operazioni_analytics_km_top_user")

    db = TestingSessionLocal()
    user = db.query(ApplicationUser).filter(ApplicationUser.username == "operazioni_analytics_km_top_user").one()
    vehicle = Vehicle(
        code="AN-KM-01",
        plate_number="KMTOP1",
        name="Mezzo km top",
        vehicle_type="pickup",
        current_status="available",
        created_by_user_id=user.id,
    )
    db.add(vehicle)
    db.flush()
    db.add(
        VehicleUsageSession(
            vehicle_id=vehicle.id,
            started_by_user_id=user.id,
            actual_driver_user_id=user.id,
            started_at=datetime(2026, 5, 27, 12, 0, 0),
            ended_at=datetime(2026, 5, 27, 13, 0, 0),
            start_odometer_km=2000,
            end_odometer_km=2080,
            status="closed",
        )
    )
    db.commit()
    db.close()

    resp = client.post(
        "/wiki/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"question": "Mostrami i top operatori km analytics operazioni"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["mode"] == "live_data"
    assert data["tool_calls"][0]["tool_name"] == "get_operazioni_analytics_top_km_operators"
    assert data["evidences"][0]["payload"]["top_operators"][0]["total_km"] > 0


def test_chat_live_operazioni_analytics_work_hours_by_team_returns_data() -> None:
    _create_user("operazioni_analytics_team_user", module_operazioni=True)
    token = _login("operazioni_analytics_team_user")

    db = TestingSessionLocal()
    user = db.query(ApplicationUser).filter(ApplicationUser.username == "operazioni_analytics_team_user").one()
    catalog = ActivityCatalog(
        code="ANTEAM",
        name="Attivita team analytics",
        category="team",
        requires_vehicle=False,
    )
    from app.modules.operazioni.models.organizational import Team
    team = Team(code="TEAM-A", name="Team A")
    db.add_all([catalog, team])
    db.flush()
    db.add(
        OperatorActivity(
            activity_catalog_id=catalog.id,
            operator_user_id=user.id,
            team_id=team.id,
            status="approved",
            started_at=datetime(2026, 5, 27, 14, 0, 0),
            ended_at=datetime(2026, 5, 27, 15, 0, 0),
            duration_minutes_declared=60,
            duration_minutes_calculated=60,
            submitted_at=datetime(2026, 5, 27, 15, 1, 0),
            created_by_user_id=user.id,
        )
    )
    db.commit()
    db.close()

    resp = client.post(
        "/wiki/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"question": "Mostrami le ore per team analytics operazioni"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["mode"] == "live_data"
    assert data["tool_calls"][0]["tool_name"] == "get_operazioni_analytics_work_hours_by_team"
    assert data["evidences"][0]["payload"]["by_team"][0]["total_hours"] > 0


def test_chat_lookup_operazioni_activity_approval_returns_live_detail() -> None:
    _create_user("operazioni_activity_approval_user", module_operazioni=True)
    token = _login("operazioni_activity_approval_user")
    approval_id = uuid4()

    db = TestingSessionLocal()
    user = db.query(ApplicationUser).filter(ApplicationUser.username == "operazioni_activity_approval_user").one()
    reviewer = ApplicationUser(
        username="operazioni_approval_reviewer",
        email="operazioni_approval_reviewer@test.local",
        password_hash=hash_password("pass123"),
        role="reviewer",
        is_active=True,
        module_operazioni=True,
    )
    catalog = ActivityCatalog(
        code="APR",
        name="Attivita approvazione",
        category="field",
        requires_vehicle=False,
    )
    db.add_all([reviewer, catalog])
    db.flush()
    activity = OperatorActivity(
        activity_catalog_id=catalog.id,
        operator_user_id=user.id,
        status="approved",
        started_at=datetime(2026, 5, 27, 12, 0, 0),
        ended_at=datetime(2026, 5, 27, 12, 45, 0),
        submitted_at=datetime(2026, 5, 27, 12, 46, 0),
        reviewed_by_user_id=reviewer.id,
        reviewed_at=datetime(2026, 5, 27, 13, 0, 0),
        review_outcome="approved",
        created_by_user_id=user.id,
    )
    db.add(activity)
    db.flush()
    db.add(
        ActivityApproval(
            id=approval_id,
            operator_activity_id=activity.id,
            reviewer_user_id=reviewer.id,
            decision="approved",
            decision_at=datetime(2026, 5, 27, 13, 0, 0),
            note="Esito positivo",
        )
    )
    db.commit()
    db.close()

    resp = client.post(
        "/wiki/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"question": f"Mostrami l'approvazione attivita {approval_id}"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["mode"] == "live_data"
    assert data["tool_calls"][0]["tool_name"] == "find_operazioni_activity_approval_by_id"
    assert data["evidences"][0]["payload"]["decision"] == "approved"
    assert data["evidences"][0]["payload"]["activity_catalog_code"] == "APR"


def test_chat_lookup_operazioni_autodoc_sync_job_returns_live_detail() -> None:
    _create_user("operazioni_autodoc_lookup_user", module_operazioni=True)
    token = _login("operazioni_autodoc_lookup_user")
    job_id = uuid4()

    db = TestingSessionLocal()
    user = db.query(ApplicationUser).filter(ApplicationUser.username == "operazioni_autodoc_lookup_user").one()
    db.add(
        WCSyncJob(
            id=job_id,
            entity="autodoc_vehicle_details",
            status="queued",
            records_synced=0,
            records_skipped=0,
            records_errors=0,
            triggered_by=user.id,
            params_json={"selected_total": 2},
        )
    )
    db.commit()
    db.close()

    resp = client.post(
        "/wiki/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"question": f"Mostrami il job autodoc {job_id}"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["mode"] == "live_data"
    assert data["tool_calls"][0]["tool_name"] == "find_operazioni_autodoc_sync_job_by_id"
    assert data["evidences"][0]["payload"]["entity"] == "autodoc_vehicle_details"
    assert data["evidences"][0]["payload"]["status"] == "queued"


def test_chat_lookup_share_by_name_returns_live_detail() -> None:
    _create_user("share_user", module_accessi=True)
    token = _login("share_user")

    db = TestingSessionLocal()
    user = db.query(ApplicationUser).filter(ApplicationUser.username == "share_user").one()
    share = Share(name="contabilita", path="/volume1/contabilita", sector="amministrazione", description="Share contabilità")
    nas_user = NasUser(username="mrossi", full_name="Mario Rossi", is_active=True)
    db.add_all([share, nas_user])
    db.flush()
    db.add(
        EffectivePermission(
            nas_user_id=nas_user.id,
            share_id=share.id,
            can_read=True,
            can_write=False,
            is_denied=False,
            source_summary="user:mrossi",
        )
    )
    db.add(
        Review(
            nas_user_id=nas_user.id,
            share_id=share.id,
            reviewer_user_id=user.id,
            decision="pending",
            note="verifica accesso",
        )
    )
    db.commit()
    db.close()

    resp = client.post(
        "/wiki/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"question": "Mostrami la share contabilita"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["mode"] == "live_data"
    assert data["tool_calls"][0]["tool_name"] == "find_share_by_name"
    assert "contabilita" in data["answer"].lower()
    assert data["evidences"][0]["source_key"] == "accessi.shares.contabilita"
    assert "path" not in data["evidences"][0]["payload"]


def test_chat_lookup_ruolo_subject_returns_live_detail() -> None:
    _create_user("ruolo_user", module_ruolo=True)
    token = _login("ruolo_user")
    subject_id = uuid4()
    import_job_id = uuid4()

    db = TestingSessionLocal()
    db.add(
        AnagraficaSubject(
            id=subject_id,
            subject_type="person",
            status="active",
            source_system="gaia",
            source_name_raw="Mario Rossi",
        )
    )
    db.add(
        AnagraficaPerson(
            subject_id=subject_id,
            cognome="Rossi",
            nome="Mario",
            codice_fiscale="RSSMRA80A01H501U",
        )
    )
    db.add(
        RuoloImportJob(
            id=import_job_id,
            anno_tributario=2025,
            status="completed",
        )
    )
    db.add(
        RuoloAvviso(
            import_job_id=import_job_id,
            codice_cnc="CNC-001",
            anno_tributario=2025,
            subject_id=subject_id,
            codice_fiscale_raw="RSSMRA80A01H501U",
            nominativo_raw="Mario Rossi",
            importo_totale_euro=250.5,
        )
    )
    db.commit()
    db.close()

    resp = client.post(
        "/wiki/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"question": "Trova soggetto ruolo con codice fiscale RSSMRA80A01H501U"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["mode"] == "live_data"
    assert data["tool_calls"][0]["tool_name"] == "find_ruolo_subject"
    assert "Mario Rossi" in data["answer"]
    assert "250.50" in data["answer"]


def test_chat_logic_accessi_permissions_returns_explanation() -> None:
    _create_user("logic_accessi", role="reviewer", module_accessi=True)
    token = _login("logic_accessi")

    db = TestingSessionLocal()
    user = db.query(ApplicationUser).filter(ApplicationUser.username == "logic_accessi").one()
    section = Section(
        module="accessi",
        key="accessi.permissions",
        label="Permessi Accessi",
        description="Gestione permessi di sezione",
        min_role="admin",
        sort_order=10,
    )
    db.add(section)
    db.flush()
    db.add(
        RoleSectionPermission(
            section_id=section.id,
            role="reviewer",
            is_granted=True,
            updated_by_id=user.id,
        )
    )
    db.commit()
    db.close()

    resp = client.post(
        "/wiki/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"question": "Perché posso vedere accessi.permissions?"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["mode"] == "logic"
    assert data["tool_calls"][0]["tool_name"] == "explain_accessi_permissions"
    assert data["evidences"][0]["type"] == "logic"
    assert "accessi.permissions" in data["answer"]


def test_chat_logic_accessi_permissions_explains_user_override_denial() -> None:
    _create_user("logic_override", role="admin", module_accessi=True)
    token = _login("logic_override")

    db = TestingSessionLocal()
    user = db.query(ApplicationUser).filter(ApplicationUser.username == "logic_override").one()
    section = Section(
        module="accessi",
        key="accessi.sync",
        label="Sync Accessi",
        description="Sincronizzazione accessi",
        min_role="viewer",
        sort_order=20,
    )
    db.add(section)
    db.flush()
    db.add(
        UserSectionPermission(
            user_id=user.id,
            section_id=section.id,
            is_granted=False,
            granted_by_id=user.id,
        )
    )
    db.commit()
    db.close()

    resp = client.post(
        "/wiki/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"question": "Perché non vedo accessi.sync?"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["mode"] == "logic"
    assert data["tool_calls"][0]["tool_name"] == "explain_accessi_permissions"
    assert data["evidences"][0]["payload"]["resolution_source"] == "user_override"
    assert "override" in data["answer"].lower()


def test_chat_logic_operazioni_activity_returns_explanation() -> None:
    _create_user("operazioni_activity_logic_user", module_operazioni=True)
    token = _login("operazioni_activity_logic_user")
    activity_id = uuid4()

    db = TestingSessionLocal()
    user = db.query(ApplicationUser).filter(ApplicationUser.username == "operazioni_activity_logic_user").one()
    reviewer = ApplicationUser(
        username="operazioni_activity_reviewer",
        email="operazioni_activity_reviewer@test.local",
        password_hash=hash_password("pass123"),
        role="reviewer",
        is_active=True,
        module_operazioni=True,
    )
    vehicle = Vehicle(
        code="VM-ACT-02",
        plate_number="AA444BB",
        name="Pickup review",
        vehicle_type="pickup",
        current_status="available",
        created_by_user_id=user.id,
    )
    catalog = ActivityCatalog(
        code="ISPEZ",
        name="Ispezione impianto",
        category="inspection",
        requires_vehicle=True,
    )
    db.add_all([reviewer, vehicle, catalog])
    db.flush()
    db.add(
        OperatorActivity(
            id=activity_id,
            activity_catalog_id=catalog.id,
            operator_user_id=user.id,
            vehicle_id=vehicle.id,
            status="approved",
            started_at=datetime(2026, 5, 27, 7, 45, 0),
            ended_at=datetime(2026, 5, 27, 8, 30, 0),
            duration_minutes_declared=45,
            duration_minutes_calculated=45,
            submitted_at=datetime(2026, 5, 27, 8, 31, 0),
            reviewed_by_user_id=reviewer.id,
            reviewed_at=datetime(2026, 5, 27, 10, 0, 0),
            review_outcome="approved",
            review_note="Ok",
            created_by_user_id=user.id,
        )
    )
    db.commit()
    db.close()

    resp = client.post(
        "/wiki/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"question": f"Spiega lo stato attivita operazioni {activity_id}"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["mode"] == "logic"
    assert data["tool_calls"][0]["tool_name"] == "explain_operazioni_activity_status"
    assert "approved" in data["answer"]
    assert data["evidences"][0]["payload"]["activity_catalog_code"] == "ISPEZ"


def test_chat_logic_operazioni_activity_approval_returns_explanation() -> None:
    _create_user("operazioni_activity_approval_logic_user", module_operazioni=True)
    token = _login("operazioni_activity_approval_logic_user")
    approval_id = uuid4()

    db = TestingSessionLocal()
    user = db.query(ApplicationUser).filter(ApplicationUser.username == "operazioni_activity_approval_logic_user").one()
    reviewer = ApplicationUser(
        username="operazioni_activity_approval_logic_reviewer",
        email="operazioni_activity_approval_logic_reviewer@test.local",
        password_hash=hash_password("pass123"),
        role="reviewer",
        is_active=True,
        module_operazioni=True,
    )
    catalog = ActivityCatalog(
        code="APRLOG",
        name="Attivita approvazione logic",
        category="inspection",
        requires_vehicle=False,
    )
    db.add_all([reviewer, catalog])
    db.flush()
    activity = OperatorActivity(
        activity_catalog_id=catalog.id,
        operator_user_id=user.id,
        status="under_review",
        started_at=datetime(2026, 5, 27, 14, 0, 0),
        ended_at=datetime(2026, 5, 27, 14, 30, 0),
        submitted_at=datetime(2026, 5, 27, 14, 31, 0),
        reviewed_by_user_id=reviewer.id,
        reviewed_at=datetime(2026, 5, 27, 15, 0, 0),
        review_outcome="needs_integration",
        created_by_user_id=user.id,
    )
    db.add(activity)
    db.flush()
    db.add(
        ActivityApproval(
            id=approval_id,
            operator_activity_id=activity.id,
            reviewer_user_id=reviewer.id,
            decision="needs_integration",
            decision_at=datetime(2026, 5, 27, 15, 0, 0),
            note="Integrare il report finale",
        )
    )
    db.commit()
    db.close()

    resp = client.post(
        "/wiki/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"question": f"Spiega il motivo approvazione attivita {approval_id}"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["mode"] == "logic"
    assert data["tool_calls"][0]["tool_name"] == "explain_operazioni_activity_approval_decision"
    assert "needs_integration" in data["answer"]
    assert data["evidences"][0]["payload"]["activity_catalog_code"] == "APRLOG"


def test_chat_logic_operazioni_autodoc_sync_returns_explanation() -> None:
    _create_user("operazioni_autodoc_logic_user", module_operazioni=True)
    token = _login("operazioni_autodoc_logic_user")
    job_id = uuid4()

    db = TestingSessionLocal()
    user = db.query(ApplicationUser).filter(ApplicationUser.username == "operazioni_autodoc_logic_user").one()
    db.add(
        WCSyncJob(
            id=job_id,
            entity="autodoc_vehicle_details",
            status="failed",
            records_synced=2,
            records_skipped=1,
            records_errors=1,
            error_detail="Cloudflare block",
            triggered_by=user.id,
            params_json={"selected_total": 5},
        )
    )
    db.commit()
    db.close()

    resp = client.post(
        "/wiki/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"question": f"Spiega lo stato job autodoc {job_id}"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["mode"] == "logic"
    assert data["tool_calls"][0]["tool_name"] == "explain_operazioni_autodoc_sync_status"
    assert "failed" in data["answer"]
    assert data["evidences"][0]["payload"]["records_errors"] == 1


def test_chat_logic_operazioni_analytics_metric_returns_explanation() -> None:
    _create_user("operazioni_analytics_logic_user", module_operazioni=True)
    token = _login("operazioni_analytics_logic_user")

    resp = client.post(
        "/wiki/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"question": "Spiega come viene calcolato l'indicatore km analytics operazioni"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["mode"] == "logic"
    assert data["tool_calls"][0]["tool_name"] == "explain_operazioni_analytics_metric"
    assert data["evidences"][0]["payload"]["metric_key"] == "total_km"
def test_chat_logic_catasto_metric_can_be_enriched_with_docs() -> None:
    _create_user("catasto_logic", module_catasto=True)
    token = _login("catasto_logic")

    docs_response = WikiChatResponse(
        answer="La documentazione del dashboard Catasto descrive il significato operativo delle anomalie aperte.",
        sources=[WikiChunkSource(source_file="CATASTO_DASHBOARD.md", section_title="Indicatori", excerpt="Anomalie aperte...")],
        found=True,
    )

    with (
        patch("app.modules.wiki.services.orchestrator.is_wiki_available", return_value=True),
        patch("app.modules.wiki.services.orchestrator.answer_question", return_value=docs_response),
    ):
        resp = client.post(
            "/wiki/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={"question": "Spiega come viene calcolato l'indicatore anomalie catasto"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["mode"] == "hybrid"
    assert data["tool_calls"][0]["tool_name"] == "explain_catasto_metric"
    assert data["sources"][0]["source_file"] == "CATASTO_DASHBOARD.md"
    assert any(evidence["type"] == "docs" for evidence in data["evidences"])


def test_chat_logic_ruolo_metric_can_be_enriched_with_docs() -> None:
    _create_user("ruolo_logic", module_ruolo=True)
    token = _login("ruolo_logic")

    docs_response = WikiChatResponse(
        answer="La documentazione Ruolo spiega il significato degli avvisi non collegati.",
        sources=[WikiChunkSource(source_file="RUOLO_OVERVIEW.md", section_title="Collegamenti", excerpt="Avvisi non collegati...")],
        found=True,
    )

    with (
        patch("app.modules.wiki.services.orchestrator.is_wiki_available", return_value=True),
        patch("app.modules.wiki.services.orchestrator.answer_question", return_value=docs_response),
    ):
        resp = client.post(
            "/wiki/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={"question": "Spiega perché ci sono avvisi non collegati nel ruolo"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["mode"] == "hybrid"
    assert data["tool_calls"][0]["tool_name"] == "explain_ruolo_metric"
    assert data["sources"][0]["source_file"] == "RUOLO_OVERVIEW.md"
    assert any(evidence["type"] == "logic" for evidence in data["evidences"])


def test_chat_lookup_riordino_practice_returns_live_detail() -> None:
    _create_user("riordino_user", module_riordino=True)
    token = _login("riordino_user")
    practice_id = uuid4()
    phase_id = uuid4()

    db = TestingSessionLocal()
    user = db.query(ApplicationUser).filter(ApplicationUser.username == "riordino_user").one()
    section = Section(
        module="riordino",
        key="riordino.practices",
        label="Pratiche Riordino",
        min_role="viewer",
        sort_order=30,
    )
    db.add(section)
    db.add(
        RiordinoPractice(
            id=practice_id,
            code="RIO-2026-0001",
            title="Pratica demo",
            municipality="Oristano",
            grid_code="G1",
            lot_code="L1",
            current_phase="phase_1",
            status="open",
            owner_user_id=user.id,
            created_by=user.id,
        )
    )
    db.add(
        RiordinoPhase(
            id=phase_id,
            practice_id=practice_id,
            phase_code="phase_1",
            status="in_progress",
        )
    )
    db.commit()
    db.close()

    resp = client.post(
        "/wiki/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"question": f"Mostrami la pratica riordino {practice_id}"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["mode"] == "live_data"
    assert data["tool_calls"][0]["tool_name"] == "find_riordino_practice_by_id"
    assert "RIO-2026-0001" in data["answer"]


def test_chat_logic_riordino_practice_can_be_enriched_with_docs() -> None:
    _create_user("riordino_logic", module_riordino=True)
    token = _login("riordino_logic")
    practice_id = uuid4()
    phase_id = uuid4()
    step_id = uuid4()

    db = TestingSessionLocal()
    user = db.query(ApplicationUser).filter(ApplicationUser.username == "riordino_logic").one()
    practices_section = Section(
        module="riordino",
        key="riordino.practices",
        label="Pratiche Riordino",
        min_role="viewer",
        sort_order=30,
    )
    workflow_section = Section(
        module="riordino",
        key="riordino.workflow",
        label="Workflow Riordino",
        min_role="viewer",
        sort_order=31,
    )
    db.add_all([practices_section, workflow_section])
    db.add(
        RiordinoPractice(
            id=practice_id,
            code="RIO-2026-0002",
            title="Pratica bloccata",
            municipality="Cabras",
            grid_code="G2",
            lot_code="L2",
            current_phase="phase_1",
            status="blocked",
            owner_user_id=user.id,
            created_by=user.id,
        )
    )
    db.add(
        RiordinoPhase(
            id=phase_id,
            practice_id=practice_id,
            phase_code="phase_1",
            status="in_progress",
        )
    )
    db.add(
        RiordinoStep(
            id=step_id,
            practice_id=practice_id,
            phase_id=phase_id,
            code="F1_DOC",
            title="Carica documento",
            sequence_no=1,
            status="todo",
            is_required=True,
            is_decision=False,
            requires_document=True,
        )
    )
    db.add(
        RiordinoIssue(
            practice_id=practice_id,
            phase_id=phase_id,
            step_id=step_id,
            type="missing_document",
            category="documentary",
            severity="blocking",
            status="open",
            title="Documento mancante",
            opened_by=user.id,
        )
    )
    db.commit()
    db.close()

    docs_response = WikiChatResponse(
        answer="La documentazione Riordino descrive che le issue blocking fermano l'avanzamento.",
        sources=[WikiChunkSource(source_file="RIORDINO_WORKFLOW.md", section_title="Blocchi", excerpt="Issue blocking...")],
        found=True,
    )

    with (
        patch("app.modules.wiki.services.orchestrator.is_wiki_available", return_value=True),
        patch("app.modules.wiki.services.orchestrator.answer_question", return_value=docs_response),
    ):
        resp = client.post(
            "/wiki/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={"question": f"Spiega perché la pratica riordino {practice_id} è bloccata"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["mode"] == "hybrid"
    assert data["tool_calls"][0]["tool_name"] == "explain_riordino_practice_state"
    assert data["sources"][0]["source_file"] == "RIORDINO_WORKFLOW.md"
    assert any(evidence["type"] == "logic" for evidence in data["evidences"])


def test_chat_lookup_operazioni_case_returns_live_detail() -> None:
    _create_user("operazioni_case_user", module_operazioni=True)
    token = _login("operazioni_case_user")
    report_id = uuid4()
    category_id = uuid4()
    severity_id = uuid4()
    case_id = uuid4()

    db = TestingSessionLocal()
    user = db.query(ApplicationUser).filter(ApplicationUser.username == "operazioni_case_user").one()
    db.add(FieldReportCategory(id=category_id, code="GUASTO", name="Guasto"))
    db.add(FieldReportSeverity(id=severity_id, code="HIGH", name="Alta", rank_order=1))
    db.add(
        FieldReport(
            id=report_id,
            report_number="REP-001",
            reporter_user_id=user.id,
            category_id=category_id,
            severity_id=severity_id,
            title="Segnalazione guasto",
            status="submitted",
        )
    )
    db.add(
        InternalCase(
            id=case_id,
            case_number="CASE-001",
            source_report_id=report_id,
            title="Case demo",
            description="Case operativo",
            category_id=category_id,
            severity_id=severity_id,
            status="assigned",
            assigned_to_user_id=user.id,
        )
    )
    db.add(
        InternalCaseEvent(
            internal_case_id=case_id,
            event_type="assigned",
            actor_user_id=user.id,
            event_at=datetime(2026, 5, 27, 10, 0, 0),
        )
    )
    db.commit()
    db.close()

    resp = client.post(
        "/wiki/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"question": f"Mostrami il case operazioni {case_id}"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["mode"] == "live_data"
    assert data["tool_calls"][0]["tool_name"] == "find_operazioni_case_by_id"
    assert "CASE-001" in data["answer"]


def test_chat_logic_operazioni_case_can_be_enriched_with_docs() -> None:
    _create_user("operazioni_case_logic", module_operazioni=True)
    token = _login("operazioni_case_logic")
    report_id = uuid4()
    category_id = uuid4()
    severity_id = uuid4()
    case_id = uuid4()

    db = TestingSessionLocal()
    user = db.query(ApplicationUser).filter(ApplicationUser.username == "operazioni_case_logic").one()
    db.add(FieldReportCategory(id=category_id, code="SIC", name="Sicurezza"))
    db.add(FieldReportSeverity(id=severity_id, code="MED", name="Media", rank_order=2))
    db.add(
        FieldReport(
            id=report_id,
            report_number="REP-002",
            reporter_user_id=user.id,
            category_id=category_id,
            severity_id=severity_id,
            title="Segnalazione sicurezza",
            status="submitted",
        )
    )
    db.add(
        InternalCase(
            id=case_id,
            case_number="CASE-002",
            source_report_id=report_id,
            title="Case sicurezza",
            description="Da prendere in carico",
            category_id=category_id,
            severity_id=severity_id,
            status="assigned",
            assigned_to_user_id=user.id,
        )
    )
    db.add(
        InternalCaseEvent(
            internal_case_id=case_id,
            event_type="assigned",
            actor_user_id=user.id,
            event_at=datetime(2026, 5, 27, 11, 0, 0),
        )
    )
    db.commit()
    db.close()

    docs_response = WikiChatResponse(
        answer="La documentazione Operazioni descrive che un case assigned ha già un assegnatario ma non è ancora in lavorazione.",
        sources=[WikiChunkSource(source_file="OPERAZIONI_CASES.md", section_title="Workflow case", excerpt="Case assigned...")],
        found=True,
    )

    with (
        patch("app.modules.wiki.services.orchestrator.is_wiki_available", return_value=True),
        patch("app.modules.wiki.services.orchestrator.answer_question", return_value=docs_response),
    ):
        resp = client.post(
            "/wiki/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={"question": f"Spiega lo stato del case operazioni {case_id}"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["mode"] == "hybrid"
    assert data["tool_calls"][0]["tool_name"] == "explain_operazioni_case_status"
    assert data["sources"][0]["source_file"] == "OPERAZIONI_CASES.md"


def test_chat_lookup_operazioni_assignment_returns_live_detail() -> None:
    _create_user("operazioni_assignment_user", module_operazioni=True)
    token = _login("operazioni_assignment_user")

    db = TestingSessionLocal()
    user = db.query(ApplicationUser).filter(ApplicationUser.username == "operazioni_assignment_user").one()
    vehicle = Vehicle(
        code="VEH-API-001",
        name="Autocarro API",
        vehicle_type="truck",
        current_status="assigned",
        created_by_user_id=user.id,
    )
    db.add(vehicle)
    db.flush()
    assignment = VehicleAssignment(
        vehicle_id=vehicle.id,
        assignment_target_type="operator",
        operator_user_id=user.id,
        assigned_by_user_id=user.id,
        start_at=datetime(2026, 5, 27, 12, 0, 0),
        reason="Assegnazione test",
    )
    db.add(assignment)
    db.commit()
    assignment_id = assignment.id
    db.close()

    resp = client.post(
        "/wiki/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"question": f"Mostrami l'assegnazione mezzo {assignment_id}"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["mode"] == "live_data"
    assert data["tool_calls"][0]["tool_name"] == "find_operazioni_assignment_by_id"
    assert data["evidences"][0]["payload"]["vehicle_code"] == "VEH-API-001"
    assert data["found"] is True


def test_chat_logic_operazioni_assignment_can_be_enriched_with_docs() -> None:
    _create_user("operazioni_assignment_logic", module_operazioni=True)
    token = _login("operazioni_assignment_logic")

    db = TestingSessionLocal()
    user = db.query(ApplicationUser).filter(ApplicationUser.username == "operazioni_assignment_logic").one()
    vehicle = Vehicle(
        code="VEH-API-002",
        name="Pickup API",
        vehicle_type="pickup",
        current_status="assigned",
        created_by_user_id=user.id,
    )
    db.add(vehicle)
    db.flush()
    assignment = VehicleAssignment(
        vehicle_id=vehicle.id,
        assignment_target_type="operator",
        operator_user_id=user.id,
        assigned_by_user_id=user.id,
        start_at=datetime(2026, 5, 27, 12, 30, 0),
        reason="Assegnazione logic test",
    )
    db.add(assignment)
    db.commit()
    assignment_id = assignment.id
    db.close()

    docs_response = WikiChatResponse(
        answer="La documentazione Operazioni spiega che un'assegnazione aperta mantiene il mezzo nel perimetro del destinatario finché non viene chiusa.",
        sources=[WikiChunkSource(source_file="OPERAZIONI_VEHICLES.md", section_title="Assegnazioni", excerpt="Assegnazione aperta...")],
        found=True,
    )

    with (
        patch("app.modules.wiki.services.orchestrator.is_wiki_available", return_value=True),
        patch("app.modules.wiki.services.orchestrator.answer_question", return_value=docs_response),
    ):
        resp = client.post(
            "/wiki/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={"question": f"Spiega lo stato assegnazione mezzo {assignment_id}"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["mode"] == "hybrid"
    assert data["tool_calls"][0]["tool_name"] == "explain_operazioni_assignment_status"
    assert data["sources"][0]["source_file"] == "OPERAZIONI_VEHICLES.md"


def test_chat_lookup_operazioni_maintenance_returns_live_detail() -> None:
    _create_user("operazioni_maintenance_user", module_operazioni=True)
    token = _login("operazioni_maintenance_user")

    db = TestingSessionLocal()
    user = db.query(ApplicationUser).filter(ApplicationUser.username == "operazioni_maintenance_user").one()
    vehicle = Vehicle(
        code="VEH-MNT-001",
        name="Furgone manutenzione",
        vehicle_type="van",
        current_status="maintenance",
        created_by_user_id=user.id,
    )
    maintenance_type = VehicleMaintenanceType(code="REV", name="Revisione")
    db.add_all([vehicle, maintenance_type])
    db.flush()
    maintenance = VehicleMaintenance(
        vehicle_id=vehicle.id,
        maintenance_type_id=maintenance_type.id,
        title="Revisione annuale",
        status="planned",
        opened_at=datetime(2026, 5, 27, 13, 0, 0),
        scheduled_for=datetime(2026, 5, 30, 8, 0, 0),
        created_by_user_id=user.id,
    )
    db.add(maintenance)
    db.commit()
    maintenance_id = maintenance.id
    db.close()

    resp = client.post(
        "/wiki/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"question": f"Mostrami la manutenzione {maintenance_id}"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["mode"] == "live_data"
    assert data["tool_calls"][0]["tool_name"] == "find_operazioni_maintenance_by_id"
    assert data["evidences"][0]["payload"]["maintenance_type_code"] == "REV"
    assert data["found"] is True


def test_chat_logic_operazioni_maintenance_can_be_enriched_with_docs() -> None:
    _create_user("operazioni_maintenance_logic", module_operazioni=True)
    token = _login("operazioni_maintenance_logic")

    db = TestingSessionLocal()
    user = db.query(ApplicationUser).filter(ApplicationUser.username == "operazioni_maintenance_logic").one()
    vehicle = Vehicle(
        code="VEH-MNT-002",
        name="Pickup officina",
        vehicle_type="pickup",
        current_status="maintenance",
        created_by_user_id=user.id,
    )
    maintenance_type = VehicleMaintenanceType(code="TAGL", name="Tagliando")
    db.add_all([vehicle, maintenance_type])
    db.flush()
    maintenance = VehicleMaintenance(
        vehicle_id=vehicle.id,
        maintenance_type_id=maintenance_type.id,
        title="Tagliando motore",
        status="completed",
        opened_at=datetime(2026, 5, 25, 9, 30, 0),
        completed_at=datetime(2026, 5, 26, 17, 0, 0),
        created_by_user_id=user.id,
    )
    db.add(maintenance)
    db.commit()
    maintenance_id = maintenance.id
    db.close()

    docs_response = WikiChatResponse(
        answer="La documentazione Operazioni spiega che una manutenzione completed è un intervento chiuso con completamento registrato.",
        sources=[WikiChunkSource(source_file="OPERAZIONI_MAINTENANCE.md", section_title="Workflow manutenzioni", excerpt="Maintenance completed...")],
        found=True,
    )

    with (
        patch("app.modules.wiki.services.orchestrator.is_wiki_available", return_value=True),
        patch("app.modules.wiki.services.orchestrator.answer_question", return_value=docs_response),
    ):
        resp = client.post(
            "/wiki/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={"question": f"Spiega lo stato manutenzione {maintenance_id}"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["mode"] == "hybrid"
    assert data["tool_calls"][0]["tool_name"] == "explain_operazioni_maintenance_status"
    assert data["sources"][0]["source_file"] == "OPERAZIONI_MAINTENANCE.md"


def test_chat_lookup_operazioni_usage_session_returns_live_detail() -> None:
    _create_user("operazioni_usage_user", module_operazioni=True)
    token = _login("operazioni_usage_user")

    db = TestingSessionLocal()
    user = db.query(ApplicationUser).filter(ApplicationUser.username == "operazioni_usage_user").one()
    vehicle = Vehicle(
        code="VEH-USE-001",
        name="Mezzo sessione API",
        vehicle_type="pickup",
        current_status="in_use",
        created_by_user_id=user.id,
    )
    db.add(vehicle)
    db.flush()
    session = VehicleUsageSession(
        vehicle_id=vehicle.id,
        started_by_user_id=user.id,
        actual_driver_user_id=user.id,
        started_at=datetime(2026, 5, 27, 6, 45, 0),
        start_odometer_km=1200,
        status="open",
    )
    db.add(session)
    db.commit()
    session_id = session.id
    db.close()

    resp = client.post(
        "/wiki/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"question": f"Mostrami la sessione uso {session_id}"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["mode"] == "live_data"
    assert data["tool_calls"][0]["tool_name"] == "find_operazioni_usage_session_by_id"
    assert data["evidences"][0]["payload"]["vehicle_code"] == "VEH-USE-001"
    assert data["found"] is True


def test_chat_logic_operazioni_usage_session_can_be_enriched_with_docs() -> None:
    _create_user("operazioni_usage_logic", module_operazioni=True)
    token = _login("operazioni_usage_logic")

    db = TestingSessionLocal()
    user = db.query(ApplicationUser).filter(ApplicationUser.username == "operazioni_usage_logic").one()
    vehicle = Vehicle(
        code="VEH-USE-002",
        name="Mezzo validazione",
        vehicle_type="suv",
        current_status="available",
        created_by_user_id=user.id,
    )
    db.add(vehicle)
    db.flush()
    session = VehicleUsageSession(
        vehicle_id=vehicle.id,
        started_by_user_id=user.id,
        actual_driver_user_id=user.id,
        started_at=datetime(2026, 5, 27, 7, 0, 0),
        ended_at=datetime(2026, 5, 27, 8, 0, 0),
        start_odometer_km=3000,
        end_odometer_km=3025,
        status="validated",
        validated_by_user_id=user.id,
        validated_at=datetime(2026, 5, 27, 8, 10, 0),
    )
    db.add(session)
    db.commit()
    session_id = session.id
    db.close()

    docs_response = WikiChatResponse(
        answer="La documentazione Operazioni descrive che una sessione validated è chiusa e verificata.",
        sources=[WikiChunkSource(source_file="OPERAZIONI_USAGE_SESSIONS.md", section_title="Workflow sessioni", excerpt="Sessione validated...")],
        found=True,
    )

    with (
        patch("app.modules.wiki.services.orchestrator.is_wiki_available", return_value=True),
        patch("app.modules.wiki.services.orchestrator.answer_question", return_value=docs_response),
    ):
        resp = client.post(
            "/wiki/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={"question": f"Spiega lo stato sessione uso {session_id}"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["mode"] == "hybrid"
    assert data["tool_calls"][0]["tool_name"] == "explain_operazioni_usage_session_status"
    assert data["sources"][0]["source_file"] == "OPERAZIONI_USAGE_SESSIONS.md"


def test_chat_lookup_operazioni_fuel_log_returns_live_detail() -> None:
    _create_user("operazioni_fuel_user", module_operazioni=True)
    token = _login("operazioni_fuel_user")

    db = TestingSessionLocal()
    user = db.query(ApplicationUser).filter(ApplicationUser.username == "operazioni_fuel_user").one()
    vehicle = Vehicle(
        code="VEH-FUEL-001",
        name="Mezzo fuel API",
        vehicle_type="truck",
        current_status="available",
        created_by_user_id=user.id,
    )
    db.add(vehicle)
    db.flush()
    fuel_log = VehicleFuelLog(
        vehicle_id=vehicle.id,
        recorded_by_user_id=user.id,
        fueled_at=datetime(2026, 5, 27, 14, 0, 0),
        liters=55.5,
        total_cost=90.4,
        station_name="Q8 Oristano",
    )
    db.add(fuel_log)
    db.commit()
    fuel_log_id = fuel_log.id
    db.close()

    resp = client.post(
        "/wiki/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"question": f"Mostrami il fuel log {fuel_log_id}"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["mode"] == "live_data"
    assert data["tool_calls"][0]["tool_name"] == "find_operazioni_fuel_log_by_id"
    assert data["evidences"][0]["payload"]["vehicle_code"] == "VEH-FUEL-001"
    assert data["found"] is True


def test_chat_logic_operazioni_fuel_log_can_be_enriched_with_docs() -> None:
    _create_user("operazioni_fuel_logic", module_operazioni=True)
    token = _login("operazioni_fuel_logic")

    db = TestingSessionLocal()
    user = db.query(ApplicationUser).filter(ApplicationUser.username == "operazioni_fuel_logic").one()
    vehicle = Vehicle(
        code="VEH-FUEL-002",
        name="Mezzo fuel logic",
        vehicle_type="van",
        current_status="available",
        created_by_user_id=user.id,
    )
    db.add(vehicle)
    db.flush()
    fuel_log = VehicleFuelLog(
        vehicle_id=vehicle.id,
        recorded_by_user_id=user.id,
        fueled_at=datetime(2026, 5, 27, 15, 0, 0),
        liters=33.2,
        odometer_km=4500,
    )
    db.add(fuel_log)
    db.commit()
    fuel_log_id = fuel_log.id
    db.close()

    docs_response = WikiChatResponse(
        answer="La documentazione Operazioni spiega che un fuel log incompleto resta utile per audit ma limita l'analisi.",
        sources=[WikiChunkSource(source_file="OPERAZIONI_FUEL_LOGS.md", section_title="Qualità dati", excerpt="Fuel log incompleto...")],
        found=True,
    )

    with (
        patch("app.modules.wiki.services.orchestrator.is_wiki_available", return_value=True),
        patch("app.modules.wiki.services.orchestrator.answer_question", return_value=docs_response),
    ):
        resp = client.post(
            "/wiki/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={"question": f"Spiega lo stato fuel log {fuel_log_id}"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["mode"] == "hybrid"
    assert data["tool_calls"][0]["tool_name"] == "explain_operazioni_fuel_log_status"
    assert data["sources"][0]["source_file"] == "OPERAZIONI_FUEL_LOGS.md"


def test_chat_lookup_operazioni_unresolved_transaction_returns_live_detail() -> None:
    _create_user("operazioni_unresolved_user", module_operazioni=True)
    token = _login("operazioni_unresolved_user")

    db = TestingSessionLocal()
    user = db.query(ApplicationUser).filter(ApplicationUser.username == "operazioni_unresolved_user").one()
    row = FleetUnresolvedTransaction(
        import_ref="imp-007",
        status="pending",
        row_index=7,
        reason_type="no_card_operator",
        reason_detail="tessera senza operatore",
        card_code="CARD-007",
        operator_name=None,
        created_by_user_id=user.id,
    )
    db.add(row)
    db.commit()
    unresolved_id = row.id
    db.close()

    resp = client.post(
        "/wiki/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"question": f"Mostrami la transazione non risolta {unresolved_id}"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["mode"] == "live_data"
    assert data["tool_calls"][0]["tool_name"] == "find_operazioni_unresolved_transaction_by_id"
    assert data["evidences"][0]["payload"]["reason_type"] == "no_card_operator"
    assert data["found"] is True


def test_chat_logic_operazioni_unresolved_transaction_can_be_enriched_with_docs() -> None:
    _create_user("operazioni_unresolved_logic", module_operazioni=True)
    token = _login("operazioni_unresolved_logic")

    db = TestingSessionLocal()
    user = db.query(ApplicationUser).filter(ApplicationUser.username == "operazioni_unresolved_logic").one()
    row = FleetUnresolvedTransaction(
        import_ref="imp-008",
        status="pending",
        row_index=8,
        reason_type="no_vehicle",
        reason_detail="nessun mezzo assegnato all'operatore alla data del rifornimento",
        operator_name="Mario Rossi",
        card_code="CARD-008",
        created_by_user_id=user.id,
    )
    db.add(row)
    db.commit()
    unresolved_id = row.id
    db.close()

    docs_response = WikiChatResponse(
        answer="La documentazione import flotte spiega che no_vehicle richiede assegnazione manuale o completamento anagrafica mezzo.",
        sources=[WikiChunkSource(source_file="OPERAZIONI_UNRESOLVED_TRANSACTIONS.md", section_title="Reason types", excerpt="no_vehicle...")],
        found=True,
    )

    with (
        patch("app.modules.wiki.services.orchestrator.is_wiki_available", return_value=True),
        patch("app.modules.wiki.services.orchestrator.answer_question", return_value=docs_response),
    ):
        resp = client.post(
            "/wiki/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={"question": f"Spiega il motivo della transazione non risolta {unresolved_id}"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["mode"] == "hybrid"
    assert data["tool_calls"][0]["tool_name"] == "explain_operazioni_unresolved_transaction_reason"
    assert data["sources"][0]["source_file"] == "OPERAZIONI_UNRESOLVED_TRANSACTIONS.md"


def test_chat_lookup_operazioni_analytics_anomaly_returns_live_detail() -> None:
    _create_user("operazioni_analytics_user", module_operazioni=True)
    token = _login("operazioni_analytics_user")

    db = TestingSessionLocal()
    user = db.query(ApplicationUser).filter(ApplicationUser.username == "operazioni_analytics_user").one()
    vehicle = Vehicle(
        code="VEH-AN-001",
        name="Mezzo analytics",
        vehicle_type="truck",
        current_status="available",
        created_by_user_id=user.id,
    )
    db.add(vehicle)
    db.flush()
    fuel_log = VehicleFuelLog(
        vehicle_id=vehicle.id,
        recorded_by_user_id=user.id,
        fueled_at=datetime.now(),
        liters=140.0,
        total_cost=230.0,
        station_name="Stazione Test",
    )
    db.add(fuel_log)
    db.commit()
    fuel_log_id = fuel_log.id
    db.close()

    resp = client.post(
        "/wiki/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"question": f"Mostrami l'anomalia analytics {fuel_log_id}"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["mode"] == "live_data"
    assert data["tool_calls"][0]["tool_name"] == "find_operazioni_analytics_anomaly_by_id"
    assert data["evidences"][0]["payload"]["type"] == "excessive_fuel"
    assert data["found"] is True


def test_chat_logic_operazioni_analytics_anomaly_can_be_enriched_with_docs() -> None:
    _create_user("operazioni_analytics_logic", module_operazioni=True)
    token = _login("operazioni_analytics_logic")

    db = TestingSessionLocal()
    user = db.query(ApplicationUser).filter(ApplicationUser.username == "operazioni_analytics_logic").one()
    vehicle = Vehicle(
        code="VEH-AN-002",
        name="Mezzo analytics logic",
        vehicle_type="truck",
        current_status="available",
        created_by_user_id=user.id,
    )
    db.add(vehicle)
    db.flush()
    fuel_log = VehicleFuelLog(
        vehicle_id=vehicle.id,
        recorded_by_user_id=user.id,
        fueled_at=datetime.now(),
        liters=145.0,
        total_cost=240.0,
        station_name="Stazione Logic",
    )
    db.add(fuel_log)
    db.commit()
    fuel_log_id = fuel_log.id
    db.close()

    docs_response = WikiChatResponse(
        answer="La documentazione analytics spiega che excessive_fuel è un alert operativo basato su soglia litri.",
        sources=[WikiChunkSource(source_file="OPERAZIONI_ANALYTICS_ANOMALIES.md", section_title="Excessive fuel", excerpt="excessive_fuel...")],
        found=True,
    )

    with (
        patch("app.modules.wiki.services.orchestrator.is_wiki_available", return_value=True),
        patch("app.modules.wiki.services.orchestrator.answer_question", return_value=docs_response),
    ):
        resp = client.post(
            "/wiki/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={"question": f"Spiega l'anomalia analytics {fuel_log_id}"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["mode"] == "hybrid"
    assert data["tool_calls"][0]["tool_name"] == "explain_operazioni_analytics_anomaly"
    assert data["sources"][0]["source_file"] == "OPERAZIONI_ANALYTICS_ANOMALIES.md"


def test_chat_logic_operazioni_storage_explanation_returns_logic() -> None:
    _create_user("operazioni_storage_logic_user", module_operazioni=True)
    token = _login("operazioni_storage_logic_user")

    resp = client.post(
        "/wiki/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"question": "Spiega la soglia warning storage operazioni"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["mode"] == "logic"
    assert data["tool_calls"][0]["tool_name"] == "explain_operazioni_storage_alert_level"
    assert data["evidences"][0]["payload"]["explanation_key"] == "warning"


def test_chat_logic_operazioni_mobile_sync_explanation_returns_logic() -> None:
    _create_user("operazioni_mobile_logic_user", module_operazioni=True)
    token = _login("operazioni_mobile_logic_user")

    resp = client.post(
        "/wiki/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"question": "Spiega come funziona il mobile sync operazioni"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["mode"] == "logic"
    assert data["tool_calls"][0]["tool_name"] == "explain_operazioni_mobile_sync_flow"
    assert data["evidences"][0]["payload"]["explanation_key"] == "handshake"


def test_chat_persists_tool_audit_log() -> None:
    _create_user("audit_share", module_accessi=True)
    token = _login("audit_share")

    db = TestingSessionLocal()
    share = Share(name="progetti", path="/volume1/progetti", sector="tecnico")
    db.add(share)
    db.commit()
    db.close()

    resp = client.post(
        "/wiki/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"question": "Mostrami la share progetti"},
    )

    assert resp.status_code == 200

    db = TestingSessionLocal()
    audit = db.query(WikiToolAuditLog).filter(WikiToolAuditLog.tool_name == "find_share_by_name").one()
    assert audit.username == "audit_share"
    assert audit.intent == "live_data"
    assert audit.mode == "live_data"
    assert audit.success == 1
    assert audit.question_hash
    assert audit.question_preview == "Mostrami la share progetti"
    assert audit.entity_key == "accessi.shares.progetti"
    assert audit.response_excerpt
    db.close()


def test_wiki_audit_tool_calls_requires_admin() -> None:
    _create_user("audit_non_admin", role="viewer")
    token = _login("audit_non_admin")

    resp = client.get(
        "/wiki/audit/tool-calls",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 403


def test_wiki_audit_tool_calls_lists_items_for_admin() -> None:
    _create_user("audit_admin", role="admin", module_accessi=True)
    token = _login("audit_admin")

    db = TestingSessionLocal()
    db.add(
        WikiToolAuditLog(
            username="audit_admin",
            role="admin",
            intent="live_data",
            mode="live_data",
            tool_name="find_share_by_name",
            module_key="accessi",
            question_hash="abc123",
            question_preview="Mostrami la share contabilita",
            success=1,
            found=1,
            latency_ms=12,
        )
    )
    db.commit()
    db.close()

    resp = client.get(
        "/wiki/audit/tool-calls?tool_name=find_share_by_name",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["tool_name"] == "find_share_by_name"
    assert data["items"][0]["question_preview"] == "Mostrami la share contabilita"
    assert data["items"][0]["entity_key"] is None


def test_wiki_audit_tool_calls_summary_aggregates_filtered_items() -> None:
    _create_user("audit_summary_admin", role="admin", module_accessi=True, module_operazioni=True)
    token = _login("audit_summary_admin")

    db = TestingSessionLocal()
    db.add_all(
        [
            WikiToolAuditLog(
                username="audit_summary_admin",
                role="admin",
                intent="live_data",
                mode="live_data",
                tool_name="find_share_by_name",
                module_key="accessi",
                question_hash="hash-1",
                question_preview="share contabilita",
                success=1,
                found=1,
                latency_ms=50,
            ),
            WikiToolAuditLog(
                username="audit_summary_admin",
                role="admin",
                intent="logic",
                mode="hybrid",
                tool_name="explain_operazioni_case_status",
                module_key="operazioni",
                question_hash="hash-2",
                question_preview="spiega case",
                success=0,
                found=0,
                latency_ms=150,
            ),
        ]
    )
    db.commit()
    db.close()

    resp = client.get(
        "/wiki/audit/tool-calls/summary",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 2
    assert data["success_count"] >= 1
    assert data["denied_count"] >= 1
    assert data["no_match_count"] >= 1
    assert any(item["key"] == "find_share_by_name" for item in data["top_tools"])
    assert any(item["key"] == "operazioni" for item in data["top_modules"])
    assert "daily_counts" in data
    assert "latency_by_mode" in data


def test_wiki_audit_tool_call_detail_returns_extended_fields() -> None:
    _create_user("audit_detail_admin", role="admin", module_accessi=True)
    token = _login("audit_detail_admin")

    db = TestingSessionLocal()
    row = WikiToolAuditLog(
        username="audit_detail_admin",
        role="admin",
        intent="logic",
        mode="hybrid",
        tool_name="explain_accessi_permissions",
        module_key="accessi",
        question_hash="detail-hash",
        question_preview="spiega accessi.permissions",
        context_article="docs/accessi.md",
        entity_key="accessi.permissions.accessi.permissions",
        entity_label="Spiegazione permesso",
        response_excerpt="La sezione è concessa per role_default.",
        fallback_reason="docs_enrichment",
        success=1,
        found=1,
        latency_ms=88,
        docs_source_count=2,
        evidence_count=3,
    )
    db.add(row)
    db.commit()
    audit_id = str(row.id)
    db.close()

    resp = client.get(
        f"/wiki/audit/tool-calls/{audit_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 200
    data = resp.json()["item"]
    assert data["entity_key"] == "accessi.permissions.accessi.permissions"
    assert data["fallback_reason"] == "docs_enrichment"
    assert data["docs_source_count"] == 2


def test_wiki_telemetry_summary_returns_historical_kpis() -> None:
    _create_user("telemetry_admin", role="admin", module_accessi=True, module_operazioni=True)
    token = _login("telemetry_admin")

    db = TestingSessionLocal()
    db.add_all(
        [
            WikiToolAuditLog(
                username="telemetry_admin",
                role="admin",
                intent="live_data",
                mode="live_data",
                tool_name="find_share_by_name",
                module_key="accessi",
                question_hash="telemetry-1",
                question_preview="share contabilita",
                fallback_reason=None,
                success=1,
                found=1,
                latency_ms=40,
            ),
            WikiToolAuditLog(
                username="telemetry_admin",
                role="admin",
                intent="logic",
                mode="hybrid",
                tool_name="explain_operazioni_case_status",
                module_key="operazioni",
                question_hash="telemetry-2",
                question_preview="spiega case",
                fallback_reason="docs_enrichment",
                success=0,
                found=0,
                latency_ms=120,
            ),
        ]
    )
    db.commit()
    db.close()

    resp = client.get(
        "/wiki/telemetry/summary?days=30",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 2
    assert data["denied_count"] >= 1
    assert any(item["key"] == "accessi" for item in data["top_modules"])
    assert any(item["key"] == "docs_enrichment" for item in data["top_fallback_reasons"])


def test_wiki_telemetry_series_returns_global_points() -> None:
    _create_user("telemetry_series_admin", role="admin", module_accessi=True)
    token = _login("telemetry_series_admin")

    db = TestingSessionLocal()
    db.add(
        WikiToolAuditLog(
            username="telemetry_series_admin",
            role="admin",
            intent="docs_only",
            mode="docs_only",
            tool_name="docs_answer",
            module_key=None,
            question_hash="telemetry-series-1",
            question_preview="cos'è gaia",
            fallback_reason="docs_only",
            success=1,
            found=1,
            latency_ms=60,
        )
    )
    db.commit()
    db.close()

    resp = client.get(
        "/wiki/telemetry/series?dimension_type=global&days=30",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["dimension_type"] == "global"
    assert len(data["items"]) >= 1
    assert any(item["docs_only_count"] >= 1 for item in data["items"])


def test_wiki_telemetry_series_supports_weekly_granularity() -> None:
    _create_user("telemetry_week_admin", role="admin", module_accessi=True)
    token = _login("telemetry_week_admin")

    db = TestingSessionLocal()
    db.add_all(
        [
            WikiToolAuditLog(
                username="telemetry_week_admin",
                role="admin",
                intent="live_data",
                mode="live_data",
                tool_name="find_share_by_name",
                module_key="accessi",
                question_hash="telemetry-week-1",
                question_preview="share 1",
                fallback_reason=None,
                success=1,
                found=1,
                latency_ms=40,
            ),
            WikiToolAuditLog(
                username="telemetry_week_admin",
                role="admin",
                intent="live_data",
                mode="hybrid",
                tool_name="find_share_by_name",
                module_key="accessi",
                question_hash="telemetry-week-2",
                question_preview="share 2",
                fallback_reason="docs_enrichment",
                success=1,
                found=1,
                latency_ms=80,
            ),
        ]
    )
    db.commit()
    db.close()

    resp = client.get(
        "/wiki/telemetry/series?dimension_type=module&dimension_key=accessi&days=30&granularity=week",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["granularity"] == "week"
    assert len(data["items"]) >= 1
    assert data["items"][0]["period_label"].startswith("Week ")


def test_wiki_telemetry_schedule_returns_backend_config() -> None:
    _create_user("telemetry_schedule_admin", role="admin")
    token = _login("telemetry_schedule_admin")

    resp = client.get(
        "/wiki/telemetry/schedule",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert "enabled" in data
    assert "cron" in data
    assert "timezone" in data
    assert "lookback_days" in data


def test_wiki_telemetry_refresh_endpoint_rebuilds_metrics() -> None:
    _create_user("telemetry_refresh_admin", role="admin", module_accessi=True)
    token = _login("telemetry_refresh_admin")

    db = TestingSessionLocal()
    db.add(
        WikiToolAuditLog(
            username="telemetry_refresh_admin",
            role="admin",
            intent="live_data",
            mode="live_data",
            tool_name="find_share_by_name",
            module_key="accessi",
            question_hash="telemetry-refresh-1",
            question_preview="refresh share",
            success=1,
            found=1,
            latency_ms=44,
        )
    )
    db.commit()
    db.close()

    resp = client.post(
        "/wiki/telemetry/refresh?days=30",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data == {"status": "ok", "days": 30}


def test_wiki_telemetry_retention_endpoint_returns_backend_config() -> None:
    _create_user("telemetry_retention_admin", role="admin")
    token = _login("telemetry_retention_admin")

    resp = client.get(
        "/wiki/telemetry/retention",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["audit_retention_days"] >= 30
    assert data["daily_retention_days"] >= 30
    assert data["period_retention_days"] >= data["daily_retention_days"]


def test_wiki_telemetry_series_export_returns_csv() -> None:
    _create_user("telemetry_export_admin", role="admin", module_accessi=True)
    token = _login("telemetry_export_admin")

    db = TestingSessionLocal()
    db.add(
        WikiToolAuditLog(
            username="telemetry_export_admin",
            role="admin",
            intent="live_data",
            mode="live_data",
            tool_name="find_share_by_name",
            module_key="accessi",
            question_hash="telemetry-export-1",
            question_preview="export share",
            success=1,
            found=1,
            latency_ms=33,
        )
    )
    db.commit()
    db.close()

    resp = client.get(
        "/wiki/telemetry/series/export?dimension_type=global&days=30&granularity=day",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    assert "dimension_type,dimension_key,granularity" in resp.text


def test_wiki_telemetry_prune_removes_old_rows() -> None:
    _create_user("telemetry_prune_admin", role="admin")
    token = _login("telemetry_prune_admin")

    db = TestingSessionLocal()
    old_dt = datetime.utcnow() - timedelta(days=800)
    db.add(
        WikiToolAuditLog(
            username="telemetry_prune_admin",
            role="admin",
            intent="docs_only",
            mode="docs_only",
            tool_name="docs_answer",
            module_key=None,
            question_hash="telemetry-prune-1",
            question_preview="old docs",
            success=1,
            found=1,
            latency_ms=12,
            created_at=old_dt,
        )
    )
    db.add(
        WikiTelemetryDailyMetric(
            metric_date=date.today() - timedelta(days=800),
            dimension_type="global",
            dimension_key=None,
            total=1,
            success_count=1,
            avg_latency_ms=10,
        )
    )
    db.add(
        WikiTelemetryPeriodMetric(
            period_type="month",
            period_start=date.today() - timedelta(days=800),
            dimension_type="global",
            dimension_key=None,
            total=1,
            success_count=1,
            avg_latency_ms=10,
        )
    )
    db.commit()
    db.close()

    resp = client.post(
        "/wiki/telemetry/prune",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["deleted_audit_rows"] >= 1
    assert data["deleted_daily_rows"] >= 1
    assert data["deleted_period_rows"] >= 1


def test_wiki_audit_related_and_export_endpoints() -> None:
    _create_user("audit_related_admin", role="admin", module_accessi=True)
    token = _login("audit_related_admin")

    db = TestingSessionLocal()
    first = WikiToolAuditLog(
        username="audit_related_admin",
        role="admin",
        intent="live_data",
        mode="live_data",
        tool_name="find_share_by_name",
        module_key="accessi",
        question_hash="audit-related-hash",
        question_preview="Mostrami la share progetti",
        entity_key="accessi.share.progetti",
        entity_label="progetti",
        success=1,
        found=1,
        latency_ms=30,
    )
    second = WikiToolAuditLog(
        username="audit_related_admin",
        role="admin",
        intent="live_data",
        mode="hybrid",
        tool_name="find_share_by_name",
        module_key="accessi",
        question_hash="audit-related-hash",
        question_preview="Mostrami ancora la share progetti",
        entity_key="accessi.share.progetti",
        entity_label="progetti",
        success=1,
        found=1,
        latency_ms=45,
    )
    db.add_all([first, second])
    db.commit()
    audit_id = str(first.id)
    db.close()

    related_resp = client.get(
        f"/wiki/audit/tool-calls/{audit_id}/related",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert related_resp.status_code == 200
    related_data = related_resp.json()["items"]
    assert any(item["question_hash"] == "audit-related-hash" for item in related_data)

    export_resp = client.get(
        "/wiki/audit/tool-calls/export?module_key=accessi",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert export_resp.status_code == 200
    assert export_resp.headers["content-type"].startswith("text/csv")
    assert "question_preview" in export_resp.text
