from __future__ import annotations

from dataclasses import dataclass
import re

from app.modules.wiki.schemas import WikiChatResponse
from app.modules.wiki.services.context_hints import KNOWN_MODULE_TOKENS, MODULE_HINTS, PAGE_HINTS

_STOPWORDS = {
    "a",
    "ad",
    "al",
    "alla",
    "allo",
    "anche",
    "che",
    "chi",
    "con",
    "come",
    "cosa",
    "da",
    "de",
    "dei",
    "del",
    "della",
    "delle",
    "di",
    "e",
    "gli",
    "i",
    "il",
    "in",
    "io",
    "la",
    "le",
    "li",
    "lo",
    "ma",
    "mi",
    "ne",
    "nel",
    "nella",
    "o",
    "oggi",
    "per",
    "piu",
    "più",
    "puoi",
    "puo",
    "può",
    "qual",
    "quale",
    "quali",
    "quando",
    "quanto",
    "quanti",
    "quello",
    "questa",
    "questo",
    "se",
    "sei",
    "su",
    "tra",
    "tu",
    "una",
    "uno",
    "un",
}

_EXTERNAL_LIVE_PATTERNS = [
    r"\bnews\b",
    r"\bnotizi",
    r"\bultim[eo]\b",
    r"\baggiornat[oa]\b",
    r"\btempo reale\b",
    r"\bmeteo\b",
    r"\bborsa\b",
    r"\bmercat[oi]\b",
    r"\bquotazion",
    r"\bprezzo\b",
    r"\bcambio\b",
    r"\bcronaca\b",
    r"\bsport\b",
    r"\brisultat[oi]\b",
    r"\bnews\b",
    r"\bheadline",
    r"\blive news\b",
    r"\breal time\b",
    r"\bweather\b",
    r"\bstock(s)?\b",
    r"\bmarket(s)?\b",
    r"\bprice(s)?\b",
    r"\bexchange rate\b",
]

_ACTION_PATTERNS = [
    r"\bcrea\b",
    r"\baggiorna\b",
    r"\bmodifica\b",
    r"\bcancella\b",
    r"\belimina\b",
    r"\binvia\b",
    r"\bmanda\b",
    r"\bresetta\b",
    r"\bassegna\b",
    r"\bapprova\b",
    r"\bchiudi\b",
    r"\briapri\b",
    r"\besegui\b",
    r"\blancia\b",
    r"\bavvia\b",
    r"\bferma\b",
    r"\bdisattiva\b",
    r"\battiva\b",
    r"\bcreate\b",
    r"\bupdate\b",
    r"\bmodify\b",
    r"\bdelete\b",
    r"\bsend\b",
    r"\breset\b",
    r"\bassign\b",
    r"\bapprove\b",
    r"\bclose\b",
    r"\breopen\b",
    r"\brun\b",
    r"\bstart\b",
    r"\bstop\b",
    r"\bdisable\b",
    r"\benable\b",
]

_ACCESS_REQUEST_PATTERNS = [
    r"\bdammi accesso\b",
    r"\bconcedi(?:mi)? accesso\b",
    r"\babilita(?:mi)?\b",
    r"\bsblocca(?:mi)?\b",
    r"\bconsenti(?:mi)?\b",
    r"\bfammi vedere\b",
    r"\bposso accedere\b",
    r"\bnon posso accedere\b",
    r"\bnon riesco ad accedere\b",
    r"\bho accesso a\b",
    r"\bnon ho accesso a\b",
    r"\baprimi\b",
    r"\bgive me access\b",
    r"\bgrant me access\b",
    r"\benable access\b",
    r"\bunblock me\b",
    r"\blet me see\b",
    r"\bcan i access\b",
    r"\bi can(?:not|'t) access\b",
    r"\bi do not have access\b",
    r"\bopen for me\b",
]

_PLATFORM_PATTERNS = [
    r"\bgaia\b",
    r"\bwiki\b",
    r"\bmodulo\b",
    r"\bpiattaforma\b",
    r"\bdocumentazione\b",
    r"\baccessi\b",
    r"\bcatasto\b",
    r"\bruolo\b",
    r"\butenze\b",
    r"\boperazioni\b",
    r"\briordino\b",
    r"\bnetwork\b",
    r"\brete\b",
    r"\bmodule\b",
    r"\bplatform\b",
    r"\bnetwork\b",
    r"\bdocs\b",
]

@dataclass(frozen=True, slots=True)
class WikiGuardrailDecision:
    answer: str
    fallback_reason: str


def _normalize_tokens(value: str) -> set[str]:
    tokens = set(re.findall(r"[a-zA-Z0-9àèéìòù]+", value.lower()))
    return {token for token in tokens if len(token) >= 4 and token not in _STOPWORDS}


def preflight_capability_guardrail(question: str) -> WikiGuardrailDecision | None:
    normalized = question.strip().lower()
    if any(re.search(pattern, normalized) for pattern in _EXTERNAL_LIVE_PATTERNS):
        return WikiGuardrailDecision(
            answer=(
                "Non ho accesso a fonti esterne o dati live generali da questo contesto. "
                "Posso aiutarti solo con documentazione interna GAIA o con dati live dei moduli supportati."
            ),
            fallback_reason="unsupported_external_live",
        )
    if any(re.search(pattern, normalized) for pattern in _ACCESS_REQUEST_PATTERNS):
        return WikiGuardrailDecision(
            answer=(
                "Da questa chat non posso concedere, sbloccare o valutare accessi a risorse, aree o dati. "
                "Posso solo spiegare la documentazione e le procedure ufficiali da seguire."
            ),
            fallback_reason="unsupported_access_request",
        )
    if any(re.search(pattern, normalized) for pattern in _ACTION_PATTERNS):
        return WikiGuardrailDecision(
            answer=(
                "Da questa chat posso spiegare procedure, documentazione e dati consultabili, "
                "ma non eseguire azioni operative o modifiche dirette."
            ),
            fallback_reason="unsupported_action_request",
        )
    return None


def has_platform_scope(question: str) -> bool:
    normalized = question.strip().lower()
    return any(re.search(pattern, normalized) for pattern in _PLATFORM_PATTERNS)


def extract_requested_module(question: str) -> str | None:
    normalized = question.strip().lower()
    for token in KNOWN_MODULE_TOKENS:
        if re.search(rf"\b{re.escape(token)}\b", normalized):
            return token
    return None


def _module_hint(module_key: str | None) -> dict[str, object] | None:
    normalized_module = (module_key or "").strip().lower()
    return MODULE_HINTS.get(normalized_module)


def _page_hint(page_path: str | None) -> dict[str, object] | None:
    normalized_path = _normalize_page_path(page_path)
    if not normalized_path:
        return None
    return PAGE_HINTS.get(normalized_path)


def describe_page_scope(module_key: str | None = None, page_path: str | None = None) -> str:
    page_hint = _page_hint(page_path)
    if page_hint is not None:
        return f"In questa pagina {page_hint['label']}"

    module_hint = _module_hint(module_key)
    if module_hint is not None:
        label = str(module_hint["label"])
        if page_path:
            return f"In questa pagina {label}"
        return f"In questo modulo {label}"

    if page_path:
        segments = [segment for segment in page_path.split("/") if segment]
        if segments:
            leaf = segments[-1].replace("-", " ").strip().title()
            if leaf:
                return f"In questa pagina {leaf}"
        return "In questa pagina"

    return "In questa sezione"


def _normalize_page_path(page_path: str | None) -> str | None:
    if not page_path:
        return None
    trimmed = page_path.strip()
    if not trimmed:
        return None
    normalized = trimmed.split("?", 1)[0].rstrip("/")
    return normalized or "/"


def build_page_capability_hint(module_key: str | None = None, page_path: str | None = None) -> str:
    scope_hint = describe_page_scope(module_key, page_path)
    page_hint = _page_hint(page_path)
    module_hint = _module_hint(module_key)
    examples = page_hint["examples"] if page_hint is not None else None
    if not examples and module_hint is not None:
        examples = module_hint["examples"]
    if not examples:
        examples = (
            "come funziona questa pagina",
            "quali dati mostra",
            "come orientarti nella navigazione",
        )
    examples_text = "; ".join(examples)
    return (
        f"{scope_hint} posso aiutarti soprattutto con documentazione, procedure, dati interni collegati "
        f"e navigazione operativa. Per esempio: {examples_text}."
    )


def postflight_docs_guardrail(
    *,
    question: str,
    response: WikiChatResponse,
    context_article: str | None = None,
    module_key: str | None = None,
    page_path: str | None = None,
) -> WikiGuardrailDecision | None:
    if not response.found:
        return WikiGuardrailDecision(
            answer=(
                "Non ho trovato documentazione interna sufficientemente rilevante per rispondere a questa domanda. "
                f"{build_page_capability_hint(module_key, page_path)} "
                "Se vuoi, riformula indicando modulo, pagina, processo o entità che ti interessa."
            ),
            fallback_reason="docs_insufficient_context",
        )

    if context_article:
        return None

    question_tokens = _normalize_tokens(question)
    if not question_tokens:
        return None

    source_text = " ".join(
        " ".join(
            filter(
                None,
                [
                    source.source_file,
                    source.section_title,
                    source.excerpt,
                ],
            )
        )
        for source in response.sources
    )
    source_tokens = _normalize_tokens(source_text)
    overlap = question_tokens & source_tokens

    requested_module = extract_requested_module(question)
    if requested_module is not None and requested_module not in source_tokens:
        return WikiGuardrailDecision(
            answer=(
                f"Non ho trovato documentazione interna sufficientemente rilevante sul modulo {requested_module}. "
                f"{build_page_capability_hint(module_key, page_path)} "
                "Posso aiutarti meglio se la richiesta è ancorata a una pagina, processo o articolo più specifico."
            ),
            fallback_reason="module_docs_missing",
        )

    has_platform_scope = any(re.search(pattern, question.lower()) for pattern in _PLATFORM_PATTERNS)
    if not overlap and not has_platform_scope:
        return WikiGuardrailDecision(
            answer=(
                "La domanda sembra fuori dal perimetro documentale di GAIA oppure non abbastanza ancorata "
                f"a un modulo, pagina, processo o dato interno. {build_page_capability_hint(module_key, page_path)}"
            ),
            fallback_reason="question_out_of_scope",
        )
    return None
