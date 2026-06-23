from __future__ import annotations

from dataclasses import dataclass, field
import json
import logging
import re

from app.modules.wiki.services.openai_client import CHAT_MODEL, get_openai_client, is_wiki_available

logger = logging.getLogger(__name__)

_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)
_OWNER_LOOKUP_PATTERNS = (
    r"\bproprietari[oa]\b",
    r"\bintestatari[oa]\b",
    r"\btitolar[ei]\b",
)
_PARCEL_LOOKUP_PATTERNS = (
    r"\bterren[oi]\b",
    r"\bparticell[ae]\b",
    r"\bfoglio\b",
)
_UUID_RE = re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b")
_CF_RE = re.compile(r"\b[A-Z]{6}[0-9]{2}[A-Z][0-9]{2}[A-Z][0-9]{3}[A-Z]\b")
_PIVA_RE = re.compile(r"\b\d{11}\b")
_FOGLIO_RE = re.compile(r"\bfoglio\s*[=:]?\s*([A-Za-z0-9/-]+)\b", re.IGNORECASE)
_PARTICELLA_RE = re.compile(r"\bparticell[ae]?\s*[=:]?\s*([A-Za-z0-9/-]+)\b", re.IGNORECASE)
_COMUNE_RE = re.compile(r"\bcomune\s*[=:]?\s*([A-Za-zÀ-ÿ' -]{2,})", re.IGNORECASE)
_NAMED_OWNER_RE = re.compile(
    r"\b(?:proprietari[oa]|intestatari[oa])\s+([A-Za-zÀ-ÿ' -]{3,})",
    re.IGNORECASE,
)
_ALLOWED_TASK_TYPES = {
    "greeting",
    "page_intro",
    "module_overview",
    "platform_overview",
    "navigation_help",
    "clarification",
    "docs_lookup",
    "entity_lookup",
    "owner_lookup",
    "metric_explanation",
    "workflow_explanation",
    "feature_gap",
    "blocked_request",
}


@dataclass(frozen=True, slots=True)
class WikiSemanticRoute:
    language: str
    normalized_query: str
    intent: str
    capability: str
    module_hint: str | None = None
    user_reply: str | None = None
    task_type: str = "docs_lookup"
    extracted_slots: dict[str, str | None] = field(default_factory=dict)

    @property
    def is_blocking(self) -> bool:
        return self.capability in {
            "unsupported_external_live",
            "unsupported_access_request",
            "unsupported_action_request",
            "out_of_scope",
        }

    @property
    def should_preflight_reply(self) -> bool:
        return self.capability in {
            "unsupported_external_live",
            "unsupported_access_request",
            "unsupported_action_request",
            "out_of_scope",
            "greeting",
            "page_intro",
            "module_overview",
            "platform_overview",
            "navigation_help",
            "clarification_needed",
        }


def infer_task_type(*, question: str, capability: str, intent: str, module_hint: str | None = None) -> str:
    normalized = question.strip().lower()
    if capability in {"unsupported_external_live", "unsupported_access_request", "unsupported_action_request", "out_of_scope"}:
        return "blocked_request"
    if capability in {"greeting", "page_intro", "module_overview", "platform_overview", "navigation_help"}:
        return capability
    if capability == "clarification_needed":
        return "clarification"
    if _looks_like_owner_lookup(normalized, module_hint=module_hint):
        return "owner_lookup"
    if intent == "logic":
        if any(token in normalized for token in ("workflow", "stato", "regola", "permess", "autorizz", "abilitat")):
            return "workflow_explanation"
        return "metric_explanation"
    if intent == "live_data":
        return "entity_lookup"
    if capability == "docs_supported":
        return "docs_lookup"
    return "feature_gap"


def extract_task_slots(question: str, task_type: str) -> dict[str, str | None]:
    if task_type == "owner_lookup":
        return {
            "comune": _extract_comune(question),
            "foglio": _extract_match(_FOGLIO_RE, question),
            "particella": _extract_match(_PARTICELLA_RE, question),
            "nominativo": _extract_named_owner(question),
            "codice_fiscale": _extract_match(_CF_RE, question.upper()),
            "partita_iva": _extract_piva(question),
        }
    if task_type == "entity_lookup":
        return {
            "uuid": _extract_match(_UUID_RE, question),
            "codice_fiscale": _extract_match(_CF_RE, question.upper()),
            "partita_iva": _extract_piva(question),
        }
    return {}


def _extract_match(pattern: re.Pattern[str], value: str) -> str | None:
    match = pattern.search(value)
    if match is None:
        return None
    if match.lastindex:
        return str(match.group(1)).strip() or None
    return str(match.group(0)).strip() or None


def _extract_piva(question: str) -> str | None:
    value = _extract_match(_PIVA_RE, question)
    if value is None:
        return None
    if _CF_RE.fullmatch(value.upper()):
        return None
    return value


def _extract_comune(question: str) -> str | None:
    match = _COMUNE_RE.search(question)
    if match is None:
        return None
    value = re.split(r"\b(?:foglio|particell[ae]?|sub|sezione)\b", match.group(1), maxsplit=1, flags=re.IGNORECASE)[0]
    normalized = value.strip(" ,.;:-")
    return normalized or None


def _extract_named_owner(question: str) -> str | None:
    match = _NAMED_OWNER_RE.search(question)
    if match is None:
        return None
    value = re.split(r"\b(?:di|del|della|terreno|particell[ae]?|foglio|comune)\b", match.group(1), maxsplit=1, flags=re.IGNORECASE)[0]
    normalized = value.strip(" ,.;:-")
    if not normalized:
        return None
    if len(normalized.split()) < 2:
        return None
    return normalized


def _looks_like_owner_lookup(normalized: str, *, module_hint: str | None = None) -> bool:
    has_owner_signal = any(re.search(pattern, normalized) for pattern in _OWNER_LOOKUP_PATTERNS)
    has_parcel_signal = any(re.search(pattern, normalized) for pattern in _PARCEL_LOOKUP_PATTERNS)
    return has_owner_signal and (has_parcel_signal or module_hint == "catasto")


def _extract_json(payload: str) -> dict[str, object] | None:
    payload = payload.strip()
    if not payload:
        return None
    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        match = _JSON_BLOCK_RE.search(payload)
        if match is None:
            return None
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None


def route_wiki_question(question: str) -> WikiSemanticRoute | None:
    if not is_wiki_available():
        return None

    client = get_openai_client()
    prompt = f"""
You are a multilingual routing layer for the GAIA Wiki assistant.

Classify the user question regardless of language.
Return only one JSON object with these keys:
- language: ISO-like short tag for the user language (example: it, en, fr, ru)
- normalized_query: a compact Italian reformulation for retrieval/tool matching inside GAIA; preserve entities, identifiers, module names and quoted terms
- intent: one of ["docs_only","live_data","logic"]
- capability: one of
  ["greeting","page_intro","module_overview","platform_overview","navigation_help","clarification_needed","docs_supported","internal_live_data","internal_explanation","unsupported_external_live","unsupported_access_request","unsupported_action_request","out_of_scope"]
- module_hint: one of ["wiki","accessi","catasto","ruolo","utenze","riordino","operazioni","rete"] or null
- task_type: one of ["greeting","page_intro","module_overview","platform_overview","navigation_help","clarification","docs_lookup","entity_lookup","owner_lookup","metric_explanation","workflow_explanation","feature_gap","blocked_request"]
- extracted_slots: object with only scalar string-or-null fields useful for execution; include known values you can infer from the question such as comune, foglio, particella, codice_fiscale, partita_iva, nominativo, uuid
- user_reply: null unless capability is greeting, page_intro, module_overview, platform_overview, navigation_help, clarification_needed, unsupported_* or out_of_scope; if present, write a short final reply in the SAME language as the user

Rules:
- Short greetings or openers like "ciao", "salve", "help" => greeting
- Questions about what GAIA is, what modules exist or what the current page is for => platform_overview or page_intro
- Questions about what a specific module does, without asking current data => module_overview
- Questions asking where to find a function/page/section => navigation_help
- If the request is vague but plausibly about GAIA/internal use, prefer clarification_needed over out_of_scope
- Questions about current news, weather, markets, public facts outside GAIA => unsupported_external_live
- Questions asking to grant/unlock/enable/access data, folders, permissions, visibility => unsupported_access_request
- Questions asking to create/update/delete/execute/approve/change state => unsupported_action_request
- Questions asking what a GAIA module does, how it works, documentation, overview => docs_only + docs_supported
- Questions asking for current counts/status/detail from GAIA data => live_data + internal_live_data
- Questions asking explanations of internal rules, permissions, workflow, metrics => logic + internal_explanation
- If the user asks to find the owner/intestatario/titolare of a terreno or particella, prefer task_type owner_lookup
- If a request is a live lookup but lacks enough identifiers, keep the best task_type and leave missing slot values as null
- Use out_of_scope only when the request is not reasonably related to GAIA, its modules, its pages, its internal data or procedures
- normalized_query must be in Italian even if the question is in another language
- user_reply must be concise, operational and not mention internal implementation

Question:
{question}
""".strip()
    try:
        completion = client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[
                {"role": "system", "content": "Return only valid JSON. No markdown."},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
            max_tokens=350,
        )
    except Exception as exc:
        logger.warning("Semantic wiki router failed before parsing: %s", exc)
        return None

    content = completion.choices[0].message.content or ""
    payload = _extract_json(content)
    if payload is None:
        logger.warning("Semantic wiki router returned non-JSON content: %s", content[:400])
        return None

    try:
        language = str(payload.get("language") or "und").strip().lower() or "und"
        normalized_query = str(payload.get("normalized_query") or question).strip() or question
        intent = str(payload.get("intent") or "docs_only").strip()
        capability = str(payload.get("capability") or "out_of_scope").strip()
        module_hint_raw = payload.get("module_hint")
        module_hint = str(module_hint_raw).strip().lower() if isinstance(module_hint_raw, str) and module_hint_raw.strip() else None
        task_type_raw = payload.get("task_type")
        task_type = str(task_type_raw).strip().lower() if isinstance(task_type_raw, str) and task_type_raw.strip() else ""
        extracted_slots_raw = payload.get("extracted_slots")
        user_reply_raw = payload.get("user_reply")
        user_reply = str(user_reply_raw).strip() if isinstance(user_reply_raw, str) and user_reply_raw.strip() else None
    except Exception as exc:
        logger.warning("Semantic wiki router payload normalization failed: %s", exc)
        return None

    if intent not in {"docs_only", "live_data", "logic"}:
        intent = "docs_only"
    if module_hint == "network":
        module_hint = "rete"
    if capability not in {
        "greeting",
        "page_intro",
        "module_overview",
        "platform_overview",
        "navigation_help",
        "clarification_needed",
        "docs_supported",
        "internal_live_data",
        "internal_explanation",
        "unsupported_external_live",
        "unsupported_access_request",
        "unsupported_action_request",
        "out_of_scope",
    }:
        capability = "out_of_scope"
    if module_hint not in {"wiki", "accessi", "catasto", "ruolo", "utenze", "riordino", "operazioni", "rete", None}:
        module_hint = None
    if task_type not in _ALLOWED_TASK_TYPES:
        task_type = infer_task_type(question=question, capability=capability, intent=intent, module_hint=module_hint)
    extracted_slots = extract_task_slots(question, task_type)
    if isinstance(extracted_slots_raw, dict):
        for key, value in extracted_slots_raw.items():
            if not isinstance(key, str):
                continue
            if value is None:
                extracted_slots[key] = None
            elif isinstance(value, (str, int, float, bool)):
                normalized_value = str(value).strip()
                extracted_slots[key] = normalized_value or None

    return WikiSemanticRoute(
        language=language,
        normalized_query=normalized_query,
        intent=intent,
        capability=capability,
        module_hint=module_hint,
        user_reply=user_reply,
        task_type=task_type,
        extracted_slots=extracted_slots,
    )
