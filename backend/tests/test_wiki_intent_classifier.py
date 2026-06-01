from app.modules.wiki.services.intent_classifier import classify_intent


def test_classify_intent_returns_logic_for_explanatory_questions() -> None:
    assert classify_intent("Spiega come viene calcolato l'indicatore catasto") == "logic"


def test_classify_intent_returns_live_data_for_identifier_lookup() -> None:
    assert classify_intent("Trova soggetto ruolo con codice fiscale RSSMRA80A01H501U") == "live_data"


def test_classify_intent_returns_docs_only_for_generic_question() -> None:
    assert classify_intent("Cos'è GAIA?") == "docs_only"


def test_classify_intent_returns_live_data_for_operazioni_usage_session_lookup() -> None:
    assert classify_intent("Mostrami la sessione uso 123e4567-e89b-12d3-a456-426614174000") == "live_data"


def test_classify_intent_returns_live_data_for_operazioni_activity_lookup() -> None:
    assert classify_intent("Mostrami l'attivita operazioni 123e4567-e89b-12d3-a456-426614174000") == "live_data"


def test_classify_intent_returns_live_data_for_operazioni_pending_approvals() -> None:
    assert classify_intent("Quante approvazioni operazioni sono in revisione?") == "live_data"


def test_classify_intent_returns_live_data_for_operazioni_autodoc_sync() -> None:
    assert classify_intent("Qual è lo stato sync autodoc operazioni?") == "live_data"


def test_classify_intent_returns_live_data_for_operazioni_analytics_summary() -> None:
    assert classify_intent("Mostrami la summary analytics operazioni") == "live_data"


def test_classify_intent_returns_live_data_for_operazioni_analytics_top_km_operators() -> None:
    assert classify_intent("Mostrami i top operatori km analytics operazioni") == "live_data"


def test_classify_intent_returns_live_data_for_operazioni_storage_status() -> None:
    assert classify_intent("Qual è lo stato storage operazioni?") == "live_data"


def test_classify_intent_returns_live_data_for_operazioni_mobile_sync_status() -> None:
    assert classify_intent("Dammi lo stato mobile sync operazioni") == "live_data"


def test_classify_intent_returns_logic_for_operazioni_fuel_log_explanation() -> None:
    assert classify_intent("Spiega lo stato fuel log 123e4567-e89b-12d3-a456-426614174000") == "logic"


def test_classify_intent_returns_logic_for_operazioni_activity_explanation() -> None:
    assert classify_intent("Spiega lo stato attivita operazioni 123e4567-e89b-12d3-a456-426614174000") == "logic"


def test_classify_intent_returns_logic_for_operazioni_activity_approval_explanation() -> None:
    assert classify_intent("Spiega il motivo approvazione attivita 123e4567-e89b-12d3-a456-426614174000") == "logic"


def test_classify_intent_returns_logic_for_operazioni_autodoc_sync_explanation() -> None:
    assert classify_intent("Spiega lo stato job autodoc 123e4567-e89b-12d3-a456-426614174000") == "logic"


def test_classify_intent_returns_logic_for_operazioni_analytics_metric_explanation() -> None:
    assert classify_intent("Spiega come viene calcolato l'indicatore km analytics operazioni") == "logic"


def test_classify_intent_returns_logic_for_operazioni_storage_explanation() -> None:
    assert classify_intent("Spiega la soglia warning storage operazioni") == "logic"


def test_classify_intent_returns_logic_for_operazioni_mobile_sync_explanation() -> None:
    assert classify_intent("Spiega come funziona il mobile sync operazioni") == "logic"


def test_classify_intent_returns_live_data_for_unresolved_transaction_lookup() -> None:
    assert classify_intent("Mostrami la transazione non risolta 123e4567-e89b-12d3-a456-426614174000") == "live_data"


def test_classify_intent_returns_logic_for_operazioni_analytics_anomaly_explanation() -> None:
    assert classify_intent("Spiega l'anomalia analytics 123e4567-e89b-12d3-a456-426614174000") == "logic"


def test_classify_intent_prefers_docs_for_documentation_request() -> None:
    assert classify_intent("Apri la documentazione wiki di GAIA operazioni") == "docs_only"


def test_classify_intent_prefers_logic_when_explanation_and_live_terms_coexist() -> None:
    assert classify_intent("Spiega perché la sessione operazioni 123e4567-e89b-12d3-a456-426614174000 è validated") == "logic"
