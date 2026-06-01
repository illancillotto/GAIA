from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.application_user import ApplicationUser
from app.models.section_permission import Section
from app.modules.wiki.schemas import WikiChatResponse
from app.modules.wiki.services.logic_catalog import (
    ACCESSI_PERMISSION_SOURCE_EXPLANATIONS,
    CATALOG_CAT_METRICS,
    CATALOG_RUOLO_METRICS,
)
from app.modules.wiki.services.response_composer import build_logic_response


def explain_accessi_permissions(db: Session, current_user: ApplicationUser, question: str, section_key: str | None) -> WikiChatResponse:
    from app.services.permission_resolver import resolve_user_permissions

    resolved = [item for item in resolve_user_permissions(db, current_user) if item.module == "accessi"]
    if not resolved:
        return build_logic_response(
            answer="Il tuo account non ha sezioni Accessi attive o il modulo non e abilitato.",
            tool_name="explain_accessi_permissions",
            evidence_label="Permessi Accessi non disponibili",
            source_key="accessi.permissions.none",
            excerpt="Nessuna sezione Accessi risolta per l'utente corrente.",
            payload={"module_enabled": "accessi" in current_user.enabled_modules},
        )

    focused = next((item for item in resolved if item.section_key == section_key), None) if section_key else None
    if focused is not None:
        section = db.scalar(select(Section).where(Section.key == focused.section_key))
        answer = (
            f"La sezione {focused.section_key} e "
            f"{'abilitata' if focused.is_granted else 'negata'} per il tuo account: "
            f"{ACCESSI_PERMISSION_SOURCE_EXPLANATIONS.get(focused.source, focused.source)}."
        )
        excerpt = (
            f"Sezione {focused.section_key}, esito {'granted' if focused.is_granted else 'denied'}, "
            f"sorgente {focused.source}."
        )
        payload = {
            "section_key": focused.section_key,
            "section_label": focused.section_label,
            "module": focused.module,
            "is_granted": focused.is_granted,
            "resolution_source": focused.source,
            "resolution_reason": ACCESSI_PERMISSION_SOURCE_EXPLANATIONS.get(focused.source, focused.source),
            "min_role": section.min_role if section is not None else None,
        }
        return build_logic_response(
            answer=answer,
            tool_name="explain_accessi_permissions",
            evidence_label="Spiegazione permesso sezione",
            source_key=f"accessi.permissions.{focused.section_key}",
            excerpt=excerpt,
            payload=payload,
        )

    granted = [item.section_key for item in resolved if item.is_granted]
    denied = [item.section_key for item in resolved if not item.is_granted]
    answer = (
        f"Permessi Accessi risolti per {current_user.username}: "
        f"{len(granted)} sezioni abilitate e {len(denied)} negate. "
        "Se mi indichi una section key come accessi.permissions posso spiegarti la regola applicata."
    )
    excerpt = f"Granted: {', '.join(granted[:5]) or 'nessuna'}. Denied: {', '.join(denied[:5]) or 'nessuna'}."
    payload = {
        "granted_keys": granted,
        "denied_keys": denied,
        "resolution_sources": {item.section_key: item.source for item in resolved},
    }
    return build_logic_response(
        answer=answer,
        tool_name="explain_accessi_permissions",
        evidence_label="Risoluzione permessi Accessi",
        source_key="accessi.permissions.summary",
        excerpt=excerpt,
        payload=payload,
    )


def explain_catasto_metric(question: str) -> WikiChatResponse:
    metric_key = "anomalie"
    normalized = question.lower()
    if "particelle" in normalized:
        metric_key = "particelle"
    elif "importi" in normalized or "euro" in normalized:
        metric_key = "importi"
    elif any(term in normalized for term in ("copertura", "geometria", "distretto", "collegate")):
        metric_key = "copertura"

    explanation = CATALOG_CAT_METRICS[metric_key]
    return build_logic_response(
        answer=explanation.answer_template,
        tool_name="explain_catasto_metric",
        evidence_label=explanation.label,
        source_key=explanation.source_key,
        excerpt=explanation.excerpt,
        payload={"metric_key": metric_key},
    )


def explain_ruolo_metric(question: str) -> WikiChatResponse:
    normalized = question.lower()
    metric_key = "avvisi_non_collegati" if "non collegati" in normalized or "non collegato" in normalized else "avvisi_collegati"
    if any(term in normalized for term in ("importi", "totale", "euro")):
        metric_key = "totale_importi"

    explanation = CATALOG_RUOLO_METRICS[metric_key]
    return build_logic_response(
        answer=explanation.answer_template,
        tool_name="explain_ruolo_metric",
        evidence_label=explanation.label,
        source_key=explanation.source_key,
        excerpt=explanation.excerpt,
        payload={"metric_key": metric_key},
    )
