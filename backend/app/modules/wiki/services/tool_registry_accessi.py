from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.application_user import ApplicationUser
from app.modules.wiki.schemas import WikiChatResponse
from app.modules.wiki.services.accessi_read_models import (
    get_accessi_dashboard_summary_read_model,
    get_nas_user_read_model,
    get_share_read_model,
)
from app.modules.wiki.services.policy import WikiToolMeta
from app.modules.wiki.services.response_composer import build_live_data_response
from app.modules.wiki.services.system_logic import explain_accessi_permissions
from app.modules.wiki.services.tool_registry_common import (
    NAS_USER_RE,
    SECTION_KEY_RE,
    SHARE_RE,
    WikiToolDefinition,
    contains_any,
    score_terms,
)


def _match_nas_user(question: str) -> int:
    if NAS_USER_RE.search(question) is None:
        return 0
    return 8 + score_terms(question, "nas", "utente")


def _match_share(question: str) -> int:
    if SHARE_RE.search(question) is None:
        return 0
    return 9 + score_terms(question, "share", "accessi", "nas")


def _match_access_logic(question: str) -> int:
    if not contains_any(
        question,
        "permess",
        "autorizz",
        "abilitat",
        "accessi",
        "sezione",
        "posso vedere",
        "non vedo",
    ):
        return 0
    return 6 + score_terms(question, "permess", "accessi", "sezione", "posso vedere", "non vedo")


def _accessi_summary(db: Session, current_user: ApplicationUser, question: str) -> WikiChatResponse:
    payload = get_accessi_dashboard_summary_read_model(db, current_user)
    excerpt = (
        f"Utenti NAS {payload['nas_users']}, gruppi {payload['nas_groups']}, "
        f"share {payload['shares']}, review {payload['reviews']}."
    )
    answer = (
        "Dati live NAS Control: "
        f"{payload['nas_users']} utenti NAS, {payload['nas_groups']} gruppi, "
        f"{payload['shares']} share, {payload['reviews']} review aperte, "
        f"{payload['snapshots']} snapshot e {payload['sync_runs']} sync run."
    )
    return build_live_data_response(
        answer=answer,
        tool_name="get_nas_dashboard_summary",
        evidence_label="Dashboard NAS Control",
        source_key="accessi.dashboard.summary",
        excerpt=excerpt,
        payload=payload,
    )


def _find_nas_user(db: Session, current_user: ApplicationUser, question: str) -> WikiChatResponse:
    match = NAS_USER_RE.search(question)
    if not match:
        return build_live_data_response(
            answer="Per cercare un utente NAS devo ricevere uno username esplicito nella domanda.",
            tool_name="find_nas_user",
            evidence_label="Lookup utente NAS non eseguito",
            source_key="accessi.nas-users.lookup",
            excerpt="Username NAS non individuato nella domanda.",
        )

    username = match.group(1).strip().lower()
    payload = get_nas_user_read_model(db, current_user, username)
    if payload is None:
        return build_live_data_response(
            answer=f"Non ho trovato nessun utente NAS con username {username}.",
            tool_name="find_nas_user",
            evidence_label="Utente NAS non trovato",
            source_key=f"accessi.nas-users.{username}",
            excerpt=f"Username cercato: {username}.",
        )

    answer = (
        "Lookup utente NAS: "
        f"{payload['username']}, stato {'attivo' if payload['is_active'] else 'disattivo'}, "
        f"nome {payload['full_name'] or 'n/d'}, dominio email {payload['email_domain'] or 'n/d'}, "
        f"ultimo snapshot {payload['last_seen_snapshot_id'] or 'n/d'}."
    )
    excerpt = f"Username {payload['username']}, stato {'attivo' if payload['is_active'] else 'disattivo'}."
    return build_live_data_response(
        answer=answer,
        tool_name="find_nas_user",
        evidence_label="Dettaglio utente NAS",
        source_key=f"accessi.nas-users.{payload['username']}",
        excerpt=excerpt,
        payload=payload,
    )


def _find_share_by_name(db: Session, current_user: ApplicationUser, question: str) -> WikiChatResponse:
    match = SHARE_RE.search(question)
    if not match:
        return build_live_data_response(
            answer="Per cercare una share NAS devo ricevere un nome share esplicito nella domanda.",
            tool_name="find_share_by_name",
            evidence_label="Lookup share NAS non eseguito",
            source_key="accessi.shares.lookup",
            excerpt="Nome share non individuato nella domanda.",
        )

    share_name = match.group(1).strip().lower()
    payload = get_share_read_model(db, current_user, share_name)
    if payload is None:
        return build_live_data_response(
            answer=f"Non ho trovato nessuna share NAS con nome {share_name}.",
            tool_name="find_share_by_name",
            evidence_label="Share NAS non trovata",
            source_key=f"accessi.shares.{share_name}",
            excerpt=f"Share cercata: {share_name}.",
        )
    answer = (
        "Lookup share NAS: "
        f"{payload['name']}, settore {payload['sector'] or 'n/d'}, "
        f"permessi {payload['total_permissions']} (read {payload['read_count']}, write {payload['write_count']}), "
        f"review pending {payload['pending_reviews']}, ultimo snapshot {payload['last_seen_snapshot_id'] or 'n/d'}."
    )
    excerpt = (
        f"Share {payload['name']}, settore {payload['sector'] or 'n/d'}, "
        f"permessi {payload['total_permissions']}, review pending {payload['pending_reviews']}."
    )
    return build_live_data_response(
        answer=answer,
        tool_name="find_share_by_name",
        evidence_label="Dettaglio share NAS",
        source_key=f"accessi.shares.{payload['name']}",
        excerpt=excerpt,
        payload=payload,
    )


def _explain_accessi_permissions(db: Session, current_user: ApplicationUser, question: str) -> WikiChatResponse:
    section_key_match = SECTION_KEY_RE.search(question.lower())
    section_key = section_key_match.group(0) if section_key_match else None
    return explain_accessi_permissions(db, current_user, question, section_key)


ACCESSI_TOOLS: tuple[WikiToolDefinition, ...] = (
    WikiToolDefinition(
        meta=WikiToolMeta(name="find_nas_user", module_key="accessi"),
        intents=("live_data",),
        priority=85,
        matcher=_match_nas_user,
        handler=_find_nas_user,
    ),
    WikiToolDefinition(
        meta=WikiToolMeta(name="find_share_by_name", module_key="accessi", redacted_payload_keys=("path",)),
        intents=("live_data",),
        priority=88,
        matcher=_match_share,
        handler=_find_share_by_name,
    ),
    WikiToolDefinition(
        meta=WikiToolMeta(name="get_nas_dashboard_summary", module_key="accessi"),
        intents=("live_data",),
        priority=10,
        matcher=lambda question: 1 if contains_any(question, "nas", "share", "review", "accessi") else 0,
        handler=_accessi_summary,
    ),
    WikiToolDefinition(
        meta=WikiToolMeta(name="explain_accessi_permissions", module_key="accessi"),
        intents=("logic",),
        priority=50,
        matcher=_match_access_logic,
        handler=_explain_accessi_permissions,
    ),
)
