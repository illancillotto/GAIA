"""Resolver deterministico di navigazione per il Wiki GAIA.

Questo modulo centralizza la risoluzione `domanda -> pagina GAIA` in modo
deterministico e indipendente dal provider LLM. Implementa una selezione a
shortlist con pesi espliciti per modulo (vedi `NAVIGATION_KEYWORD_WEIGHTS`) e
una stima di confidenza usata sia come fallback quando l'LLM e' degradato sia
come shortlist da cui il router semantico puo scegliere.

Obiettivi rispetto ai failure mode osservati:
- collisioni lessicali tra moduli (`particelle`, `pratiche`, `mezzi`)
  risolte con pesi operativi e boost di contesto, non con il path piu corto;
- nessun salto verso un altro modulo quando il modulo corrente ha una
  corrispondenza forte;
- segnalazione esplicita di `disambiguation_needed` quando due moduli sono
  ugualmente plausibili.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re

from app.modules.wiki.services.context_hints import (
    KNOWN_MODULE_TOKENS,
    NAVIGATION_KEYWORD_WEIGHTS,
    PAGE_HINTS,
)

_TOKEN_RE = re.compile(r"[a-zA-Z0-9àèéìòù]+")

_NAVIGATION_NOISE_TOKENS = {
    "dove",
    "vedo",
    "vede",
    "trovo",
    "trova",
    "trovare",
    "apro",
    "apri",
    "aprire",
    "raggiungo",
    "raggiungere",
    "arrivo",
    "arrivare",
    "vai",
    "vado",
    "portami",
    "mostrami",
    "pagina",
    "pagine",
    "funzione",
    "funzioni",
    "sezione",
    "sezioni",
    "modulo",
    "moduli",
    "menu",
    "come",
    "cosa",
    "quale",
    "quali",
    "posso",
    "voglio",
}

_STOPWORDS = {
    "a", "ad", "al", "alla", "allo", "anche", "che", "chi", "con", "da", "de",
    "dei", "del", "della", "delle", "di", "e", "gli", "i", "il", "in", "io",
    "la", "le", "li", "lo", "ma", "mi", "ne", "nel", "nella", "o", "per",
    "se", "su", "tra", "tu", "una", "uno", "un",
}

_MODULE_ALIASES = {
    "network": "rete",
    "nas-control": "accessi",
    "inventory": "inventario",
}

# Soglia di confidenza sotto la quale, in presenza di un secondo candidato in
# un modulo diverso, chiediamo disambiguazione invece di scegliere a caso.
_DISAMBIGUATION_CONFIDENCE_FLOOR = 0.6


@dataclass(frozen=True, slots=True)
class NavigationCandidate:
    page_path: str
    label: str
    module_key: str | None
    score: float


@dataclass(frozen=True, slots=True)
class NavigationResolution:
    page_path: str
    label: str
    module_key: str | None
    examples: tuple[str, ...]
    confidence: float
    disambiguation_needed: bool
    candidates: tuple[NavigationCandidate, ...] = field(default_factory=tuple)

    @property
    def disambiguation_question(self) -> str | None:
        if not self.disambiguation_needed:
            return None
        labels = [candidate.label for candidate in self.candidates[:3]]
        if len(labels) < 2:
            return None
        joined = ", ".join(labels[:-1]) + f" o {labels[-1]}"
        return f"Stai cercando {joined}?"


def _normalize_page_path(page_path: str | None) -> str | None:
    if not page_path:
        return None
    trimmed = page_path.strip()
    if not trimmed:
        return None
    normalized = trimmed.split("?", 1)[0].rstrip("/")
    return normalized or "/"


def _page_module_key(path: str) -> str | None:
    segments = [segment for segment in path.split("/") if segment]
    if not segments:
        return None
    first = segments[0].strip().lower()
    return _MODULE_ALIASES.get(first, first) or None


def _tokens(value: str, *, min_length: int = 3) -> set[str]:
    tokens = {token for token in _TOKEN_RE.findall(value.lower()) if len(token) >= min_length}
    return {token for token in tokens if token not in _STOPWORDS}


def _focus_tokens(question: str) -> set[str]:
    return {token for token in _tokens(question) if token not in _NAVIGATION_NOISE_TOKENS}


def extract_named_module(question: str) -> str | None:
    """Modulo esplicitamente nominato dall'utente (segnale forte)."""
    normalized = question.strip().lower()
    for token in KNOWN_MODULE_TOKENS:
        if re.search(rf"\b{re.escape(token)}\b", normalized):
            return _MODULE_ALIASES.get(token, token)
    return None


def _keyword_scores(question: str) -> dict[str, float]:
    """Punteggi derivati dai pesi espliciti per keyword/frase."""
    normalized = question.strip().lower()
    scores: dict[str, float] = {}
    for keyword, weights in NAVIGATION_KEYWORD_WEIGHTS.items():
        if re.search(rf"\b{re.escape(keyword)}\b", normalized):
            for path, weight in weights.items():
                scores[path] = max(scores.get(path, 0.0), float(weight))
    return scores


def resolve_navigation(
    question: str,
    *,
    module_key: str | None = None,
    page_path: str | None = None,
) -> NavigationResolution | None:
    focus_tokens = _focus_tokens(question)
    keyword_scores = _keyword_scores(question)
    if not focus_tokens and not keyword_scores:
        return None

    named_module = extract_named_module(question)
    current_module = (module_key or "").strip().lower() or _page_module_key(
        _normalize_page_path(page_path) or ""
    )
    current_module = _MODULE_ALIASES.get(current_module or "", current_module)

    scored: list[NavigationCandidate] = []
    for path, hint in PAGE_HINTS.items():
        page_module = _page_module_key(path)
        # Modulo nominato esplicitamente: filtro forte.
        if named_module and page_module and page_module != named_module:
            continue

        score = keyword_scores.get(path, 0.0)

        path_tokens = _tokens(path.replace("/", " ").replace("-", " "))
        label_tokens = _tokens(str(hint.get("label") or ""))
        example_tokens = _tokens(" ".join(str(ex) for ex in hint.get("examples", ())))
        overlap = focus_tokens & (path_tokens | label_tokens | example_tokens)
        # L'overlap su path/label vale piu dell'overlap sugli esempi.
        strong_overlap = overlap & (path_tokens | label_tokens)
        score += len(strong_overlap) * 1.0
        score += len(overlap - strong_overlap) * 0.5

        if score <= 0:
            continue

        # Boost di contesto: il modulo corrente e' un segnale, non un filtro.
        if named_module and page_module == named_module:
            score += 3.0
        elif current_module and page_module == current_module:
            score += 2.0

        scored.append(
            NavigationCandidate(
                page_path=path,
                label=str(hint.get("label") or path),
                module_key=page_module,
                score=round(score, 3),
            )
        )

    if not scored:
        return None

    scored.sort(key=lambda candidate: (candidate.score, -len(candidate.page_path)), reverse=True)
    top = scored[0]
    second = scored[1] if len(scored) > 1 else None

    margin = top.score - (second.score if second is not None else 0.0)
    # Confidenza: combina forza assoluta e distacco dal secondo candidato.
    confidence = min(1.0, 0.45 + 0.1 * top.score + 0.1 * margin)
    confidence = round(confidence, 3)

    disambiguation_needed = (
        second is not None
        and second.module_key != top.module_key
        and margin < 1.0
        and confidence < _DISAMBIGUATION_CONFIDENCE_FLOOR
    )

    top_hint = PAGE_HINTS.get(top.page_path, {})
    return NavigationResolution(
        page_path=top.page_path,
        label=top.label,
        module_key=top.module_key,
        examples=tuple(str(ex) for ex in top_hint.get("examples", ())),
        confidence=confidence,
        disambiguation_needed=disambiguation_needed,
        candidates=tuple(scored[:4]),
    )
