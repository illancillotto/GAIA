from __future__ import annotations

from dataclasses import dataclass
import re

from app.modules.wiki.schemas import WikiChatResponse

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

_KNOWN_MODULE_TOKENS = (
    "wiki",
    "accessi",
    "catasto",
    "ruolo",
    "utenze",
    "operazioni",
    "riordino",
    "network",
    "rete",
)


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
    for token in _KNOWN_MODULE_TOKENS:
        if re.search(rf"\b{re.escape(token)}\b", normalized):
            return token
    return None


def postflight_docs_guardrail(
    *,
    question: str,
    response: WikiChatResponse,
    context_article: str | None = None,
) -> WikiGuardrailDecision | None:
    if not response.found:
        return WikiGuardrailDecision(
            answer=(
                "Non ho trovato documentazione interna sufficientemente rilevante per rispondere a questa domanda. "
                "Se vuoi, puoi riformularla indicando il modulo, il processo o l'entità che ti interessa."
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
                "Se esiste documentazione dedicata, va indicizzata oppure va richiamato un articolo più specifico."
            ),
            fallback_reason="module_docs_missing",
        )

    has_platform_scope = any(re.search(pattern, question.lower()) for pattern in _PLATFORM_PATTERNS)
    if not overlap and not has_platform_scope:
        return WikiGuardrailDecision(
            answer=(
                "La domanda sembra fuori dal perimetro documentale di GAIA oppure non abbastanza ancorata "
                "a un modulo, processo o dato interno. Posso aiutarti meglio se indichi il contesto GAIA rilevante."
            ),
            fallback_reason="question_out_of_scope",
        )
    return None
