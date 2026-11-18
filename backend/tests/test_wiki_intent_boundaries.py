import pytest

from app.modules.wiki.services.intent_classifier import classify_intent


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("", "docs_only"),
        ("  \t\n", "docs_only"),
        ("?!", "docs_only"),
        ("bonjour", "docs_only"),
        ("wiki", "docs_only"),
        ("quanti", "live_data"),
        ("quanti wiki", "docs_only"),
        ("quanti quante wiki", "live_data"),
        ("quanti wiki manuale", "docs_only"),
        ("quanti quanti wiki", "docs_only"),
        ("dashboard wiki", "live_data"),
        ("dashboard wiki manuale", "docs_only"),
        ("spiega quanti quante wiki", "logic"),
        ("  QUANTI  WIKI  ", "docs_only"),
        ("Come funziona il modulo wiki? Quanti avvisi?", "docs_only"),
        ("123e4567-e89b-12d3-a456-426614174000", "live_data"),
        ("RSSMRA80A01H501U", "live_data"),
        ("01234567890", "live_data"),
        ("rssmra80a01h501u wiki manuale", "live_data"),
        ("rssmra80a01h501u wiki manuale guida", "docs_only"),
        ("rssmra80a01h501u wiki manuale guida overview", "docs_only"),
        ("spiega RSSMRA80A01H501U wiki", "logic"),
        ("Come funziona il modulo wiki? RSSMRA80A01H501U spiega", "docs_only"),
    ],
)
def test_intent_priorities_ties_and_nonnegative_scores(question, expected):
    assert classify_intent(question) == expected
