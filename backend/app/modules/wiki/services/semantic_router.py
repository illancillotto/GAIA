from __future__ import annotations

from dataclasses import dataclass
import json
import logging
import re

from app.modules.wiki.services.openai_client import CHAT_MODEL, get_openai_client, is_wiki_available

logger = logging.getLogger(__name__)

_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)


@dataclass(frozen=True, slots=True)
class WikiSemanticRoute:
    language: str
    normalized_query: str
    intent: str
    capability: str
    module_hint: str | None = None
    user_reply: str | None = None

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

    return WikiSemanticRoute(
        language=language,
        normalized_query=normalized_query,
        intent=intent,
        capability=capability,
        module_hint=module_hint,
        user_reply=user_reply,
    )
