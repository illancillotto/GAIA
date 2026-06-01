from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.application_user import ApplicationUser
from app.modules.wiki.schemas import WikiChatResponse
from app.modules.wiki.services.policy import WikiToolMeta
from app.modules.wiki.services.ruolo_utenze_read_models import (
    get_ruolo_dashboard_summary_read_model,
    get_ruolo_subject_by_identifier_read_model,
    get_utenze_stats_read_model,
    get_utenze_subject_by_identifier_read_model,
)
from app.modules.wiki.services.response_composer import build_live_data_response
from app.modules.wiki.services.system_logic import explain_ruolo_metric
from app.modules.wiki.services.tool_registry_common import (
    TAX_ID_RE,
    WikiToolDefinition,
    contains_any,
    has_tax_id,
    score_terms,
)


def _match_subject(question: str) -> int:
    if not has_tax_id(question):
        return 0
    return 8 + score_terms(
        question,
        "codice fiscale",
        "cf ",
        "cf:",
        "utenze",
        "anagrafica",
        "soggetto",
        "consorziato",
        "partita iva",
    )


def _match_ruolo_subject(question: str) -> int:
    if not has_tax_id(question):
        return 0
    if not contains_any(question, "ruolo", "avvisi", "tributario"):
        return 0
    return 9 + score_terms(question, "ruolo", "avvisi", "tributario", "soggetto", "codice fiscale", "cf ")


def _match_ruolo_logic(question: str) -> int:
    if not contains_any(question, "ruolo", "avvisi", "collegati", "importi", "tributario"):
        return 0
    if not contains_any(question, "spiega", "significa", "come viene calcolato", "come si calcola", "perche", "perché"):
        return 0
    return 7 + score_terms(question, "ruolo", "avvisi", "collegati", "importi", "tributario")


def _utenze_stats(db: Session, current_user: ApplicationUser, question: str) -> WikiChatResponse:
    payload = get_utenze_stats_read_model(db, current_user)
    excerpt = (
        f"Soggetti {payload['total_subjects']}, persone {payload['total_persons']}, "
        f"aziende {payload['total_companies']}, documenti {payload['total_documents']}."
    )
    answer = (
        "Dati live Utenze: "
        f"{payload['total_subjects']} soggetti totali, {payload['total_persons']} persone, "
        f"{payload['total_companies']} aziende, {payload['total_documents']} documenti, "
        f"{payload['requires_review']} soggetti da rivedere."
    )
    return build_live_data_response(
        answer=answer,
        tool_name="get_utenze_stats",
        evidence_label="Statistiche Utenze",
        source_key="utenze.stats",
        excerpt=excerpt,
        payload=payload,
    )


def _ruolo_stats(db: Session, current_user: ApplicationUser, question: str) -> WikiChatResponse:
    payload = get_ruolo_dashboard_summary_read_model(db, current_user)
    latest = payload["items"][0] if payload["items"] else None
    if latest is None:
        answer = "Non ci sono ancora statistiche Ruolo disponibili."
        excerpt = "Nessuna statistica ruolo trovata."
    else:
        answer = (
            "Dati live Ruolo: "
            f"anno tributario {latest['anno_tributario']}, {latest['total_avvisi']} avvisi totali, "
            f"{latest['avvisi_collegati']} collegati, {latest['avvisi_non_collegati']} non collegati, "
            f"totale {(latest['totale_euro'] or 0):.2f} euro."
        )
        excerpt = (
            f"Anno {latest['anno_tributario']}, avvisi {latest['total_avvisi']}, "
            f"collegati {latest['avvisi_collegati']}, non collegati {latest['avvisi_non_collegati']}."
        )
    return build_live_data_response(
        answer=answer,
        tool_name="get_ruolo_dashboard_summary",
        evidence_label="Statistiche Ruolo",
        source_key="ruolo.stats",
        excerpt=excerpt,
        payload=payload,
    )


def _find_subject_by_cf(db: Session, current_user: ApplicationUser, question: str) -> WikiChatResponse:
    from app.modules.utenze.services.subject_identity import normalize_tax_identifier

    match = TAX_ID_RE.search(question.upper())
    if not match:
        return build_live_data_response(
            answer="Per cercare un soggetto Utenze devo ricevere un codice fiscale o una partita IVA validi.",
            tool_name="find_subject_by_cf",
            evidence_label="Lookup soggetto non eseguito",
            source_key="utenze.subjects.lookup",
            excerpt="Identificativo fiscale non presente nella domanda.",
        )

    identifier = normalize_tax_identifier(match.group(0))
    if not identifier:
        return build_live_data_response(
            answer="L'identificativo fiscale ricevuto non e utilizzabile per il lookup Utenze.",
            tool_name="find_subject_by_cf",
            evidence_label="Lookup soggetto non eseguito",
            source_key="utenze.subjects.lookup",
            excerpt="Identificativo fiscale non normalizzabile.",
        )

    payload = get_utenze_subject_by_identifier_read_model(db, current_user, identifier)
    if payload is None:
        return build_live_data_response(
            answer=f"Non ho trovato nessun soggetto Utenze con identificativo {identifier}.",
            tool_name="find_subject_by_cf",
            evidence_label="Soggetto Utenze non trovato",
            source_key=f"utenze.subjects.{identifier}",
            excerpt=f"Identificativo cercato: {identifier}.",
        )
    answer = (
        "Lookup soggetto Utenze: "
        f"{payload['display_name']}, stato {payload['status']}, tipo {payload['subject_type']}, "
        f"documenti {payload['documents_count']}, review {'sì' if payload['requires_review'] else 'no'}."
    )
    excerpt = (
        f"Subject {payload['id']}, tipo {payload['subject_type']}, "
        f"status {payload['status']}, documenti {payload['documents_count']}."
    )
    return build_live_data_response(
        answer=answer,
        tool_name="find_subject_by_cf",
        evidence_label="Dettaglio soggetto Utenze",
        source_key=f"utenze.subjects.{payload['id']}",
        excerpt=excerpt,
        payload=payload,
    )


def _find_ruolo_subject(db: Session, current_user: ApplicationUser, question: str) -> WikiChatResponse:
    from app.modules.utenze.services.subject_identity import normalize_tax_identifier

    match = TAX_ID_RE.search(question.upper())
    if not match:
        return build_live_data_response(
            answer="Per cercare un soggetto Ruolo devo ricevere un codice fiscale o una partita IVA validi.",
            tool_name="find_ruolo_subject",
            evidence_label="Lookup soggetto ruolo non eseguito",
            source_key="ruolo.subjects.lookup",
            excerpt="Identificativo fiscale non presente nella domanda.",
        )

    identifier = normalize_tax_identifier(match.group(0))
    if not identifier:
        return build_live_data_response(
            answer="L'identificativo fiscale ricevuto non e utilizzabile per il lookup Ruolo.",
            tool_name="find_ruolo_subject",
            evidence_label="Lookup soggetto ruolo non eseguito",
            source_key="ruolo.subjects.lookup",
            excerpt="Identificativo fiscale non normalizzabile.",
        )

    payload = get_ruolo_subject_by_identifier_read_model(db, current_user, identifier)
    if payload is None:
        return build_live_data_response(
            answer=f"Non ho trovato nessun soggetto Ruolo con identificativo {identifier}.",
            tool_name="find_ruolo_subject",
            evidence_label="Soggetto ruolo non trovato",
            source_key=f"ruolo.subjects.{identifier}",
            excerpt=f"Identificativo cercato: {identifier}.",
        )
    answer = (
        "Lookup soggetto Ruolo: "
        f"{payload['display_name'] or identifier}, {payload['avvisi_count']} avvisi collegati, "
        f"totale {payload['total_importo']:.2f} euro."
    )
    excerpt = (
        f"Subject {payload['subject_id']}, avvisi {payload['avvisi_count']}, totale {payload['total_importo']:.2f} euro."
    )
    return build_live_data_response(
        answer=answer,
        tool_name="find_ruolo_subject",
        evidence_label="Dettaglio soggetto Ruolo",
        source_key=f"ruolo.subjects.{payload['subject_id']}",
        excerpt=excerpt,
        payload=payload,
    )


def _explain_ruolo_metric(db: Session, current_user: ApplicationUser, question: str) -> WikiChatResponse:
    return explain_ruolo_metric(question)


RUOLO_UTENZE_TOOLS: tuple[WikiToolDefinition, ...] = (
    WikiToolDefinition(
        meta=WikiToolMeta(name="find_subject_by_cf", module_key="utenze"),
        intents=("live_data",),
        priority=80,
        matcher=_match_subject,
        handler=_find_subject_by_cf,
    ),
    WikiToolDefinition(
        meta=WikiToolMeta(name="find_ruolo_subject", module_key="ruolo"),
        intents=("live_data",),
        priority=90,
        matcher=_match_ruolo_subject,
        handler=_find_ruolo_subject,
    ),
    WikiToolDefinition(
        meta=WikiToolMeta(name="get_ruolo_dashboard_summary", module_key="ruolo"),
        intents=("live_data",),
        priority=10,
        matcher=lambda question: 1 if contains_any(question, "ruolo", "avvisi", "tributario") else 0,
        handler=_ruolo_stats,
    ),
    WikiToolDefinition(
        meta=WikiToolMeta(name="get_utenze_stats", module_key="utenze"),
        intents=("live_data",),
        priority=10,
        matcher=lambda question: 1 if contains_any(question, "utenze", "anagrafica", "soggetti", "documenti") else 0,
        handler=_utenze_stats,
    ),
    WikiToolDefinition(
        meta=WikiToolMeta(name="explain_ruolo_metric", module_key="ruolo"),
        intents=("logic",),
        priority=50,
        matcher=_match_ruolo_logic,
        handler=_explain_ruolo_metric,
    ),
)
