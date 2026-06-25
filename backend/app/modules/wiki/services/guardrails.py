from __future__ import annotations

from dataclasses import dataclass
import re

from app.modules.wiki.schemas import WikiChatResponse
from app.modules.wiki.services.context_hints import KNOWN_MODULE_TOKENS, MODULE_HINTS, PAGE_HINTS
from app.modules.wiki.services.navigation_resolver import resolve_navigation

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


@dataclass(frozen=True, slots=True)
class WikiPreflightResponseDecision:
    answer: str
    fallback_reason: str
    tool_name: str
    found: bool = True


_GREETING_PATTERNS = [
    r"^ciao[!. ]*$",
    r"^salve[!. ]*$",
    r"^buongiorno[!. ]*$",
    r"^buonasera[!. ]*$",
    r"^hello[!. ]*$",
    r"^hi[!. ]*$",
    r"^aiuto[!. ]*$",
    r"^help[!. ]*$",
    r"^ok[!. ]*$",
]

_PAGE_INTRO_PATTERNS = [
    r"\bcosa posso fare qui\b",
    r"\bche cosa posso fare qui\b",
    r"\bcosa posso fare in questa pagina\b",
    r"\bche cosa posso fare in questa pagina\b",
    r"\bcosa si (?:può|puo) fare in questa pagina\b",
    r"\bcome posso usare questa pagina\b",
    r"\bcome funziona questa pagina\b",
    r"\ba cosa serve questa pagina\b",
    r"\bspiegami questa pagina\b",
]

_MODULE_OVERVIEW_PATTERNS = [
    r"\bcome funziona il modulo\b",
    r"\bcosa fa il modulo\b",
    r"\bche cosa fa il modulo\b",
    r"\ba cosa serve il modulo\b",
]

_PLATFORM_OVERVIEW_PATTERNS = [
    r"\bcos['’][eè] gaia\b",
    r"\bche cos['’][eè] gaia\b",
    r"\bcosa fa gaia\b",
    r"\bche cosa fa gaia\b",
    r"\bcome funziona gaia\b",
    r"\bche moduli ci sono\b",
    r"\bquali moduli ci sono\b",
]

_NAVIGATION_PATTERNS = [
    r"\bdove trovo\b",
    r"\bdove vedo\b",
    r"\bdove sono\b",
    r"\bdove si trova\b",
    r"\bdove si trovano\b",
    r"\bdov['’]?\s?è\b",
    r"\bcome apro\b",
    r"\bcome raggiungo\b",
    r"\bcome arrivo\b",
    r"\bvai a\b",
    r"\bvai alla\b",
    r"\bportami a\b",
    r"\bportami alla\b",
    r"\bapri (?:la|il|le|i)\b",
]

_SHORT_GENERIC_PATTERNS = [
    r"^come faccio\??$",
    r"^non capisco\??$",
    r"^mi aiuti\??$",
]

_CATASTO_OWNER_LOOKUP_PATTERNS = [
    r"\bproprietari[oa]\b",
    r"\bintestatari[oa]\b",
    r"\btitolar[ei]\b",
]

_CATASTO_PARCEL_PATTERNS = [
    r"\bterren[oi]\b",
    r"\bparticell[ae]\b",
    r"\bfoglio\b",
]


def _normalize_tokens(value: str, *, min_length: int = 4) -> set[str]:
    tokens = set(re.findall(r"[a-zA-Z0-9àèéìòù]+", value.lower()))
    return {token for token in tokens if len(token) >= min_length and token not in _STOPWORDS}


def _normalize_page_path(page_path: str | None) -> str | None:
    if not page_path:
        return None
    trimmed = page_path.strip()
    if not trimmed:
        return None
    normalized = trimmed.split("?", 1)[0].rstrip("/")
    return normalized or "/"


def is_widget_context(page_path: str | None) -> bool:
    normalized_path = _normalize_page_path(page_path)
    return normalized_path is not None and not normalized_path.startswith("/wiki")


def is_greeting_message(question: str) -> bool:
    normalized = question.strip().lower()
    return any(re.search(pattern, normalized) for pattern in _GREETING_PATTERNS)


def is_page_intro_request(question: str) -> bool:
    normalized = question.strip().lower()
    return any(re.search(pattern, normalized) for pattern in _PAGE_INTRO_PATTERNS)


def is_module_overview_request(question: str) -> bool:
    normalized = question.strip().lower()
    return any(re.search(pattern, normalized) for pattern in _MODULE_OVERVIEW_PATTERNS)


def is_platform_overview_request(question: str) -> bool:
    normalized = question.strip().lower()
    return any(re.search(pattern, normalized) for pattern in _PLATFORM_OVERVIEW_PATTERNS)


def is_navigation_help_request(question: str) -> bool:
    normalized = question.strip().lower()
    return any(re.search(pattern, normalized) for pattern in _NAVIGATION_PATTERNS)


def is_short_generic_request(question: str) -> bool:
    normalized = question.strip().lower()
    if is_greeting_message(normalized):
        return False
    if any(re.search(pattern, normalized) for pattern in _SHORT_GENERIC_PATTERNS):
        return True
    tokens = re.findall(r"[a-zA-Z0-9àèéìòù]+", normalized)
    return 0 < len(tokens) <= 3 and not has_platform_scope(question) and not normalized.endswith("?")


def is_brief_platform_request(question: str) -> bool:
    normalized = question.strip().lower()
    tokens = re.findall(r"[a-zA-Z0-9àèéìòù]+", normalized)
    return 0 < len(tokens) <= 3 and has_platform_scope(question) and not is_platform_overview_request(normalized)


def is_catasto_owner_lookup_request(question: str) -> bool:
    normalized = question.strip().lower()
    has_owner_signal = any(re.search(pattern, normalized) for pattern in _CATASTO_OWNER_LOOKUP_PATTERNS)
    has_parcel_signal = any(re.search(pattern, normalized) for pattern in _CATASTO_PARCEL_PATTERNS)
    return has_owner_signal and has_parcel_signal


def _has_lookup_identifier(question: str) -> bool:
    normalized = question.strip()
    if re.search(r"\b[A-Z0-9]{16}\b", normalized.upper()):
        return True
    if re.search(r"\b\d{11}\b", normalized):
        return True
    if re.search(r"\bcomune\b", normalized.lower()) and re.search(r"\bfoglio\b", normalized.lower()) and re.search(r"\bparticell[ae]\b", normalized.lower()):
        return True
    if re.search(r"\bfoglio\s*[=:]?\s*[A-Za-z0-9]+\b", normalized.lower()) and re.search(r"\bparticell[ae]?\s*[=:]?\s*[A-Za-z0-9]+\b", normalized.lower()):
        return True
    if re.search(r"\bintestatari[oa]\s+[A-Za-zÀ-ÿ]{2,}\b", normalized.lower()):
        return True
    return False


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


def build_page_intro_answer(module_key: str | None = None, page_path: str | None = None) -> str:
    scope_hint = describe_page_scope(module_key, page_path)
    page_hint = _page_hint(page_path)
    module_hint_obj = _module_hint(module_key)
    examples = page_hint["examples"] if page_hint is not None else None
    if not examples and module_hint_obj is not None:
        examples = module_hint_obj["examples"]
    if not examples:
        examples = (
            "come funziona questa pagina",
            "quali dati mostra",
            "come orientarti nella navigazione",
        )
    examples_text = "; ".join(examples)
    return (
        f"Ciao. {scope_hint} trovi funzionalita operative e documentazione contestuale.\n"
        f"- Scopo: orientarti su cosa mostra la pagina e come usarla.\n"
        f"- Cosa puoi fare: {examples_text}.\n"
        f"- Prossimi passi: dimmi cosa ti serve e ti rispondo in modo mirato."
    )


def build_short_greeting_answer(module_key: str | None = None, page_path: str | None = None) -> str:
    scope_hint = describe_page_scope(module_key, page_path)
    return (
        f"Ciao. {scope_hint} dimmi pure cosa ti serve. "
        "Posso aiutarti a capire come funziona la pagina, quali dati mostra o dove trovare una funzione."
    )


def build_module_overview_answer(module_key: str | None = None, page_path: str | None = None) -> str:
    module_hint = _module_hint(module_key)
    if module_hint is None:
        return build_page_intro_answer(module_key, page_path)
    label = str(module_hint["label"])
    examples = "; ".join(module_hint["examples"])
    page_scope = describe_page_scope(module_key, page_path)
    return (
        f"{page_scope} il modulo {label} supporta consultazione e attivita operative interne.\n"
        f"- Scopo: gestire {label} e i flussi collegati al Consorzio.\n"
        f"- Cosa puoi fare: {examples}.\n"
        f"- Dati tipici: dipendono dalla pagina; indica comune, identificativo o entita se cerchi un dato specifico.\n"
        f"- Prossimi passi: dimmi l'obiettivo (consultazione, ricerca, spiegazione workflow) e ti guido."
    )


def build_platform_overview_answer(module_key: str | None = None, page_path: str | None = None) -> str:
    return (
        "GAIA e la piattaforma interna che raccoglie moduli operativi, documentazione contestuale, navigazione guidata "
        "e dati interni collegati ai processi del Consorzio. "
        f"{build_page_capability_hint(module_key, page_path)}"
    )


def build_navigation_help_answer(
    question: str,
    *,
    module_key: str | None = None,
    page_path: str | None = None,
) -> str:
    normalized = question.strip().lower()
    normalized_page_path = _normalize_page_path(page_path)
    if "support" in normalized and "wiki" in normalized:
        return (
            "Le richieste supporto Wiki si trovano nella sezione **Supporto Wiki** (`/wiki/support`). "
            "Da li puoi aprire una richiesta completa, aggiungere contesto e seguire gli aggiornamenti della segnalazione."
        )
    resolution = resolve_navigation(question, module_key=module_key, page_path=page_path)
    if resolution is not None:
        if resolution.disambiguation_needed:
            return build_navigation_disambiguation_answer(resolution.disambiguation_question)
        rendered = render_navigation_answer(resolution.page_path, current_page_path=page_path)
        if rendered is not None:
            return rendered
    return (
        f"{build_page_capability_hint(module_key, page_path)} "
        "Se mi dici quale funzione, sezione o dato stai cercando, posso orientarti meglio nella navigazione."
    )


def build_navigation_disambiguation_answer(disambiguation_question: str | None) -> str:
    question_text = disambiguation_question or "Quale modulo ti interessa?"
    return (
        "Questo termine esiste in piu moduli. "
        f"{question_text} Indicami il modulo e ti porto direttamente alla pagina giusta."
    )


def render_navigation_answer(page_path: str | None, *, current_page_path: str | None = None) -> str | None:
    """Compone la risposta di navigazione per un path noto del catalogo."""
    target = _normalize_page_path(page_path)
    hint = PAGE_HINTS.get(target or "")
    if hint is None:
        return None
    label = str(hint.get("label") or target)
    examples = tuple(str(example) for example in hint.get("examples", ()))
    if _normalize_page_path(current_page_path) == target:
        details = f" Qui puoi: {'; '.join(examples)}." if examples else ""
        return f"Sei gia nella pagina **{label}** (`{target}`).{details}".strip()
    details = f" Da li puoi: {'; '.join(examples)}." if examples else ""
    return f"La funzione che stai cercando si trova in **{label}** (`{target}`).{details}".strip()


def build_clarification_answer(module_key: str | None = None, page_path: str | None = None) -> str:
    return (
        f"{build_page_capability_hint(module_key, page_path)} "
        "Se vuoi, indica il modulo, la pagina, il processo o il dato che ti interessa e ti rispondo in modo piu mirato."
    )


def build_catasto_owner_lookup_clarification_answer() -> str:
    return (
        "Ciao. Per aiutarti a trovare il proprietario di un terreno mi servono almeno comune, foglio e particella, "
        "oppure un nominativo, codice fiscale o partita IVA. "
        "Se me li indichi, posso guidarti nella ricerca Catasto in modo operativo."
    )


_META_PHRASE_PATTERNS = (
    re.compile(r"\b(?:verifico|controllo|cerco|consulto)\s+(?:nel|nella|nei|nelle)\s+(?:workspace|documento|contesto)\b", re.IGNORECASE),
    re.compile(r"\b(?:non\s+)?(?:ho|dispongo\s+di)\s+(?:abbastanza\s+)?contesto\s+tecnico\b", re.IGNORECASE),
    re.compile(r"\b(?:nel|nella|secondo\s+il)\s+documento\s+(?:fornito|recuperato|indicato)\b", re.IGNORECASE),
    re.compile(r"\b(?:come\s+(?:assistente|modello|llm)|in\s+base\s+al\s+prompt)\b", re.IGNORECASE),
    re.compile(r"\b(?:nel\s+workspace|contesto\s+documentale\s+fornito)\b", re.IGNORECASE),
)


def sanitize_operational_answer(answer: str) -> str:
    """Rimuove o attenua meta-frasi comuni dalle risposte LLM destinate all'operatore."""
    cleaned = answer.strip()
    if not cleaned:
        return cleaned
    for pattern in _META_PHRASE_PATTERNS:
        cleaned = pattern.sub("", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def build_contextual_preflight_response(
    question: str,
    *,
    module_key: str | None = None,
    page_path: str | None = None,
) -> WikiPreflightResponseDecision | None:
    """Preflight operativo valido anche fuori dal widget (es. pagina /wiki)."""
    if is_page_intro_request(question):
        return WikiPreflightResponseDecision(
            answer=build_page_intro_answer(module_key, page_path),
            fallback_reason="page_intro",
            tool_name="page_intro",
            found=True,
        )

    if is_module_overview_request(question):
        requested_module = extract_requested_module(question)
        return WikiPreflightResponseDecision(
            answer=build_module_overview_answer(requested_module or module_key, page_path),
            fallback_reason="module_overview",
            tool_name="module_overview",
            found=True,
        )

    if is_platform_overview_request(question):
        return WikiPreflightResponseDecision(
            answer=build_platform_overview_answer(module_key, page_path),
            fallback_reason="platform_overview",
            tool_name="platform_overview",
            found=True,
        )

    if is_navigation_help_request(question):
        return WikiPreflightResponseDecision(
            answer=build_navigation_help_answer(question, module_key=module_key, page_path=page_path),
            fallback_reason="navigation_help",
            tool_name="navigation_help",
            found=True,
        )

    if is_short_generic_request(question) or is_brief_platform_request(question):
        return WikiPreflightResponseDecision(
            answer=build_clarification_answer(module_key, page_path),
            fallback_reason="clarification_needed",
            tool_name="clarification_needed",
            found=True,
        )

    return None


def build_operational_preflight_response(
    question: str,
    *,
    module_key: str | None = None,
    page_path: str | None = None,
) -> WikiPreflightResponseDecision | None:
    requested_module = extract_requested_module(question)
    effective_module = requested_module or module_key
    if effective_module == "catasto" and is_catasto_owner_lookup_request(question) and not _has_lookup_identifier(question):
        return WikiPreflightResponseDecision(
            answer=build_catasto_owner_lookup_clarification_answer(),
            fallback_reason="owner_lookup_clarification",
            tool_name="owner_lookup_clarification",
            found=True,
        )
    if requested_module is None and is_catasto_owner_lookup_request(question) and not _has_lookup_identifier(question):
        return WikiPreflightResponseDecision(
            answer=build_catasto_owner_lookup_clarification_answer(),
            fallback_reason="owner_lookup_clarification",
            tool_name="owner_lookup_clarification",
            found=True,
        )
    return None


def build_widget_preflight_response(
    question: str,
    *,
    module_key: str | None = None,
    page_path: str | None = None,
    has_active_conversation: bool = False,
) -> WikiPreflightResponseDecision | None:
    if not is_widget_context(page_path):
        return None

    if not has_active_conversation and (
        is_greeting_message(question) or is_short_generic_request(question) or is_page_intro_request(question)
    ):
        return WikiPreflightResponseDecision(
            answer=build_page_intro_answer(module_key, page_path),
            fallback_reason="page_intro",
            tool_name="page_intro",
            found=True,
        )

    if has_active_conversation and is_greeting_message(question):
        return WikiPreflightResponseDecision(
            answer=build_short_greeting_answer(module_key, page_path),
            fallback_reason="greeting",
            tool_name="greeting",
            found=True,
        )

    return build_contextual_preflight_response(
        question,
        module_key=module_key,
        page_path=page_path,
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
