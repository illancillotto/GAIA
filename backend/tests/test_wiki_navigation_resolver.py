from __future__ import annotations

import pytest

from app.modules.wiki.services.navigation_resolver import (
    NavigationCandidate,
    NavigationResolution,
    extract_named_module,
    resolve_navigation,
)


# Dataset di eval per la navigation resolution: ogni riga e' un failure mode
# osservato in produzione (vedi docs/WIKI_LLM_REVIEW_MEMO_2026-06-25.md) o un
# caso canonico di regressione. Forma:
#   (domanda, module_key, page_path, page_path_atteso)
NAVIGATION_EVAL_CASES = [
    # Failure #1 - collisione catasto vs ruolo
    ("dove trovo le particelle?", None, None, "/catasto/particelle"),
    ("dove trovo le particelle?", "catasto", "/catasto/gis", "/catasto/particelle"),
    ("dove trovo le particelle del ruolo?", None, None, "/ruolo/particelle"),
    ("particelle ruolo", None, None, "/ruolo/particelle"),
    # Failure #2 - collisione operazioni vs riordino
    ("dove trovo le pratiche?", None, None, "/operazioni/pratiche"),
    ("dove trovo le pratiche di riordino?", None, None, "/riordino/pratiche"),
    # Failure #3 - collisione operazioni vs elaborazioni
    ("dove trovo i mezzi?", None, None, "/operazioni/mezzi"),
    # Failure #4 - presenze / giornaliere (inaz)
    ("dove trovo le giornaliere?", None, None, "/inaz/giornaliere"),
    ("dove trovo i collaboratori?", None, None, "/inaz/collaboratori"),
    # Failure #5 - anomalie visure routing (utenze), non catasto live
    ("dove vedo le anomalie delle visure routing?", None, None, "/utenze/visure-routing-anomalies"),
    # Casi canonici aggiuntivi
    ("dove trovo il gis?", None, None, "/catasto/gis"),
    ("dove trovo i contatori irrigui?", None, None, "/catasto/letture-contatori"),
    ("dove sono gli avvisi del ruolo?", None, None, "/ruolo/avvisi"),
]


@pytest.mark.parametrize("question,module_key,page_path,expected", NAVIGATION_EVAL_CASES)
def test_navigation_resolution_top1_accuracy(question, module_key, page_path, expected) -> None:
    resolution = resolve_navigation(question, module_key=module_key, page_path=page_path)
    assert resolution is not None, f"Nessuna risoluzione per: {question!r}"
    assert resolution.page_path == expected, (
        f"{question!r} -> {resolution.page_path} (atteso {expected})"
    )


def test_navigation_resolution_returns_none_without_signal() -> None:
    assert resolve_navigation("ciao come stai", module_key=None, page_path=None) is None


def test_current_module_context_breaks_tie_without_jumping_module() -> None:
    # In contesto catasto, "particelle" non deve deviare verso ruolo.
    resolution = resolve_navigation("dove trovo le particelle", module_key="catasto")
    assert resolution is not None
    assert resolution.page_path == "/catasto/particelle"
    assert resolution.module_key == "catasto"


def test_explicit_module_is_a_hard_filter() -> None:
    resolution = resolve_navigation("mostrami le pratiche in riordino", module_key="operazioni")
    assert resolution is not None
    # Il modulo nominato esplicitamente (riordino) vince sul contesto corrente (operazioni).
    assert resolution.page_path == "/riordino/pratiche"


def test_high_confidence_for_unambiguous_keyword() -> None:
    resolution = resolve_navigation("dove trovo le giornaliere?")
    assert resolution is not None
    assert resolution.confidence >= 0.75
    assert resolution.disambiguation_needed is False


def test_candidates_shortlist_is_populated_and_sorted() -> None:
    resolution = resolve_navigation("dove trovo le particelle?")
    assert resolution is not None
    assert len(resolution.candidates) >= 2
    scores = [candidate.score for candidate in resolution.candidates]
    assert scores == sorted(scores, reverse=True)
    assert isinstance(resolution.candidates[0], NavigationCandidate)


def test_disambiguation_question_format() -> None:
    resolution = NavigationResolution(
        page_path="/catasto/particelle",
        label="Particelle Catasto",
        module_key="catasto",
        examples=(),
        confidence=0.5,
        disambiguation_needed=True,
        candidates=(
            NavigationCandidate("/catasto/particelle", "Particelle Catasto", "catasto", 3.0),
            NavigationCandidate("/ruolo/particelle", "Particelle Ruolo", "ruolo", 3.0),
        ),
    )
    assert resolution.disambiguation_question == "Stai cercando Particelle Catasto o Particelle Ruolo?"


def test_extract_named_module_normalizes_aliases() -> None:
    assert extract_named_module("come apro la rete") == "rete"
    assert extract_named_module("vai al network") == "rete"
    assert extract_named_module("dove trovo le particelle") is None
