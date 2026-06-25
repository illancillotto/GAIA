from __future__ import annotations

from dataclasses import dataclass, field
import json
import logging
import re

from app.modules.wiki.services.context_hints import MODULE_HINTS, PAGE_HINTS
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
_ALLOWED_CAPABILITIES = {
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
}
_ALLOWED_MODULE_HINTS = {
    "wiki",
    "accessi",
    "catasto",
    "ruolo",
    "utenze",
    "riordino",
    "operazioni",
    "rete",
    "network",
    "organigramma",
    "elaborazioni",
    "inaz",
    "inventario",
    None,
}
_CANONICAL_NAVIGATION_PAGES = (
    "/catasto/gis",
    "/catasto/particelle",
    "/catasto/letture-contatori",
    "/operazioni/pratiche",
    "/operazioni/attivita",
    "/operazioni/analisi",
    "/operazioni/mezzi",
    "/inaz/banca-ore",
    "/inaz/giornaliere",
    "/inaz/collaboratori",
    "/ruolo/particelle",
    "/ruolo/avvisi",
    "/ruolo/stats",
    "/ruolo/import",
    "/utenze/import",
    "/utenze/visure-routing-anomalies",
    "/elaborazioni/visure",
    "/elaborazioni/anpr",
    "/elaborazioni/capacitas",
    "/elaborazioni/ade-alignment",
    "/elaborazioni/autodoc",
    "/wiki/support",
    "/organigramma",
)


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
    resolved_page_path: str | None = None
    confidence: float | None = None
    disambiguation_needed: bool = False
    disambiguation_question: str | None = None

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


def _normalize_page_path(page_path: str | None) -> str | None:
    if not isinstance(page_path, str):
        return None
    normalized = page_path.strip()
    if not normalized:
        return None
    if not normalized.startswith("/"):
        normalized = f"/{normalized}"
    return normalized.rstrip("/") or "/"


def _page_module_key(path: str) -> str | None:
    normalized = _normalize_page_path(path)
    if normalized is None or normalized == "/":
        return None
    segments = [segment for segment in normalized.split("/") if segment]
    if not segments:
        return None
    first = segments[0].strip().lower()
    if first == "network":
        return "rete"
    return first or None


def _build_navigation_catalog(module_key: str | None, page_path: str | None) -> str:
    effective_module = (module_key or "").strip().lower() or _page_module_key(page_path)
    current_path = _normalize_page_path(page_path)
    selected_paths: list[str] = []
    seen_paths: set[str] = set()

    for path in _CANONICAL_NAVIGATION_PAGES:
        normalized_path = _normalize_page_path(path)
        if normalized_path is None or normalized_path in seen_paths:
            continue
        path_module = _page_module_key(normalized_path)
        if effective_module and path_module == effective_module:
            selected_paths.append(normalized_path)
            seen_paths.add(normalized_path)

    if current_path and current_path in PAGE_HINTS and current_path not in seen_paths:
        selected_paths.append(current_path)
        seen_paths.add(current_path)

    for path in sorted(PAGE_HINTS):
        normalized_path = _normalize_page_path(path)
        if normalized_path is None or normalized_path in seen_paths:
            continue
        selected_paths.append(normalized_path)
        seen_paths.add(normalized_path)

    lines: list[str] = []
    for path in selected_paths:
        hint = PAGE_HINTS.get(path)
        if hint is None:
            continue
        label = str(hint.get("label") or path)
        examples = ", ".join(str(example) for example in hint.get("examples", ()))
        page_module = _page_module_key(path) or "common"
        lines.append(f'- path: "{path}" | module: "{page_module}" | label: "{label}" | aliases: "{examples}"')
    return "\n".join(lines)


def _build_module_catalog() -> str:
    lines: list[str] = []
    for module_key in sorted(MODULE_HINTS):
        hint = MODULE_HINTS[module_key]
        label = str(hint.get("label") or module_key)
        examples = ", ".join(str(example) for example in hint.get("examples", ()))
        lines.append(f'- module: "{module_key}" | label: "{label}" | examples: "{examples}"')
    return "\n".join(lines)


def _build_routing_prompt(question: str, *, module_key: str | None = None, page_path: str | None = None) -> str:
    normalized_page_path = _normalize_page_path(page_path)
    normalized_module = (module_key or "").strip().lower() or _page_module_key(normalized_page_path)
    current_module = normalized_module or "null"
    current_page = normalized_page_path or "null"
    modules_catalog = _build_module_catalog()
    pages_catalog = _build_navigation_catalog(normalized_module, normalized_page_path)
    return f"""
You are the GAIA Wiki navigation and intent router.

Your job is NOT to answer with a generic explanation unless the request is truly not resolvable.
Your primary job is to classify the request and resolve the most likely GAIA destination.

Return only one valid JSON object with these keys:
- language
- normalized_query
- intent: one of ["docs_only","live_data","logic"]
- capability: one of ["greeting","page_intro","module_overview","platform_overview","navigation_help","clarification_needed","docs_supported","internal_live_data","internal_explanation","unsupported_external_live","unsupported_access_request","unsupported_action_request","out_of_scope"]
- module_hint: one of ["wiki","accessi","catasto","ruolo","utenze","riordino","operazioni","rete","organigramma","elaborazioni","inaz","inventario"] or null
- page_path: exact GAIA route or null
- confidence: number from 0.0 to 1.0
- disambiguation_needed: boolean
- disambiguation_question: short question in the SAME language as the user, or null
- task_type: one of ["greeting","page_intro","module_overview","platform_overview","navigation_help","clarification","docs_lookup","entity_lookup","owner_lookup","metric_explanation","workflow_explanation","feature_gap","blocked_request"]
- extracted_slots: object with only scalar string-or-null fields useful for execution
- user_reply: null unless capability is greeting, page_intro, module_overview, platform_overview, navigation_help, clarification_needed, unsupported_* or out_of_scope; if present, write a short final reply in the SAME language as the user

Current GAIA context:
- current_module: {current_module}
- current_page_path: {current_page}

Known modules:
{modules_catalog}

Known pages:
{pages_catalog}

Strict routing rules:
- If the user asks "where", "dove trovo", "dove vedo", "apri", "vai a", "come arrivo", classify as navigation_help.
- Prefer exact GAIA navigation resolution over generic guidance.
- Use current_module and current_page_path as strong signals, unless the user explicitly names another module.
- Never route to another module if the current module already has an exact or near-exact page match.
- If a term is ambiguous, prefer in this order:
  1. explicit module named by the user
  2. current module or current page context
  3. exact page alias match in known pages
  4. the most operationally common page in that module
- Navigation disambiguation examples:
  - "particelle" in catasto context => /catasto/particelle
  - "particelle del ruolo" or "particelle ruolo" => /ruolo/particelle
  - "pratiche" in operazioni context => /operazioni/pratiche
  - "pratiche" in riordino context => /riordino/pratiche
  - "mezzi" => /operazioni/mezzi
  - "banca ore" => /inaz/banca-ore
  - "giornaliere" => /inaz/giornaliere
  - "collaboratori" => /inaz/collaboratori
  - "contatori irrigui" => /catasto/letture-contatori
  - "anomalie visure routing" => /utenze/visure-routing-anomalies
- If confidence is below 0.75 and more than one page is plausible, set disambiguation_needed=true and ask a short targeted question.
- If you choose capability=navigation_help and page_path is not null, user_reply should directly point to that page in operational language.
- Questions about what GAIA is, what modules exist or what the current page is for => platform_overview or page_intro.
- Questions about what a specific module does, without asking current data => module_overview.
- Questions asking for current counts/status/detail from GAIA data => live_data + internal_live_data.
- Questions asking explanations of internal rules, permissions, workflow, metrics => logic + internal_explanation.
- If the user asks to find the owner/intestatario/titolare of a terreno or particella, prefer task_type owner_lookup.
- If a request is vague but plausibly internal, prefer clarification_needed over out_of_scope.
- normalized_query must be in Italian even if the original question is not.
- user_reply must be concise, operational and must not mention prompts, tools, workspace or internal implementation.

Question:
{question}
""".strip()


def route_wiki_question(
    question: str,
    *,
    module_key: str | None = None,
    page_path: str | None = None,
) -> WikiSemanticRoute | None:
    if not is_wiki_available():
        return None

    client = get_openai_client()
    prompt = _build_routing_prompt(question, module_key=module_key, page_path=page_path)
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
        resolved_page_path = _normalize_page_path(payload.get("page_path")) if isinstance(payload, dict) else None
        confidence_raw = payload.get("confidence")
        confidence = float(confidence_raw) if isinstance(confidence_raw, (int, float)) else None
        disambiguation_needed = bool(payload.get("disambiguation_needed"))
        disambiguation_question_raw = payload.get("disambiguation_question")
        disambiguation_question = (
            str(disambiguation_question_raw).strip()
            if isinstance(disambiguation_question_raw, str) and disambiguation_question_raw.strip()
            else None
        )
    except Exception as exc:
        logger.warning("Semantic wiki router payload normalization failed: %s", exc)
        return None

    if intent not in {"docs_only", "live_data", "logic"}:
        intent = "docs_only"
    if module_hint == "network":
        module_hint = "rete"
    if capability not in _ALLOWED_CAPABILITIES:
        capability = "out_of_scope"
    if module_hint not in _ALLOWED_MODULE_HINTS:
        module_hint = None
    if task_type not in _ALLOWED_TASK_TYPES:
        task_type = infer_task_type(question=question, capability=capability, intent=intent, module_hint=module_hint)
    if confidence is not None:
        confidence = max(0.0, min(1.0, confidence))
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
        resolved_page_path=resolved_page_path,
        confidence=confidence,
        disambiguation_needed=disambiguation_needed,
        disambiguation_question=disambiguation_question,
    )
