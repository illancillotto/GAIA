from app.modules.wiki.services.tool_registry import find_matching_tool


def test_find_matching_tool_prefers_share_lookup_over_accessi_summary() -> None:
    tool = find_matching_tool("Mostrami la share contabilita", "live_data")

    assert tool is not None
    assert tool.meta.name == "find_share_by_name"


def test_find_matching_tool_matches_ruolo_subject_lookup() -> None:
    tool = find_matching_tool("Trova soggetto ruolo con codice fiscale RSSMRA80A01H501U", "live_data")

    assert tool is not None
    assert tool.meta.name == "find_ruolo_subject"


def test_find_matching_tool_matches_ruolo_logic() -> None:
    tool = find_matching_tool("Spiega perché ci sono avvisi non collegati nel ruolo", "logic")

    assert tool is not None
    assert tool.meta.name == "explain_ruolo_metric"


def test_find_matching_tool_matches_riordino_practice_lookup() -> None:
    tool = find_matching_tool("Mostrami la pratica riordino 123e4567-e89b-12d3-a456-426614174000", "live_data")

    assert tool is not None
    assert tool.meta.name == "find_riordino_practice_by_id"


def test_find_matching_tool_matches_operazioni_case_lookup() -> None:
    tool = find_matching_tool("Mostrami il case operazioni 123e4567-e89b-12d3-a456-426614174000", "live_data")

    assert tool is not None
    assert tool.meta.name == "find_operazioni_case_by_id"


def test_find_matching_tool_matches_operazioni_assignment_lookup() -> None:
    tool = find_matching_tool("Mostrami l'assegnazione mezzo 123e4567-e89b-12d3-a456-426614174000", "live_data")

    assert tool is not None
    assert tool.meta.name == "find_operazioni_assignment_by_id"


def test_find_matching_tool_matches_operazioni_assignment_logic() -> None:
    tool = find_matching_tool("Spiega lo stato assegnazione mezzo 123e4567-e89b-12d3-a456-426614174000", "logic")

    assert tool is not None
    assert tool.meta.name == "explain_operazioni_assignment_status"


def test_find_matching_tool_matches_operazioni_maintenance_lookup() -> None:
    tool = find_matching_tool("Mostrami la manutenzione 123e4567-e89b-12d3-a456-426614174000", "live_data")

    assert tool is not None
    assert tool.meta.name == "find_operazioni_maintenance_by_id"


def test_find_matching_tool_matches_operazioni_maintenance_logic() -> None:
    tool = find_matching_tool("Spiega lo stato manutenzione 123e4567-e89b-12d3-a456-426614174000", "logic")

    assert tool is not None
    assert tool.meta.name == "explain_operazioni_maintenance_status"


def test_find_matching_tool_matches_operazioni_usage_session_lookup() -> None:
    tool = find_matching_tool("Mostrami la sessione uso mezzo 123e4567-e89b-12d3-a456-426614174000", "live_data")

    assert tool is not None
    assert tool.meta.name == "find_operazioni_usage_session_by_id"


def test_find_matching_tool_matches_operazioni_activity_lookup() -> None:
    tool = find_matching_tool("Mostrami l'attivita operazioni 123e4567-e89b-12d3-a456-426614174000", "live_data")

    assert tool is not None
    assert tool.meta.name == "find_operazioni_activity_by_id"


def test_find_matching_tool_matches_operazioni_activity_approval_lookup() -> None:
    tool = find_matching_tool("Mostrami l'approvazione attivita 123e4567-e89b-12d3-a456-426614174000", "live_data")

    assert tool is not None
    assert tool.meta.name == "find_operazioni_activity_approval_by_id"


def test_find_matching_tool_matches_operazioni_autodoc_sync_lookup() -> None:
    tool = find_matching_tool("Mostrami il job autodoc 123e4567-e89b-12d3-a456-426614174000", "live_data")

    assert tool is not None
    assert tool.meta.name == "find_operazioni_autodoc_sync_job_by_id"


def test_find_matching_tool_matches_operazioni_fuel_log_lookup() -> None:
    tool = find_matching_tool("Mostrami il fuel log 123e4567-e89b-12d3-a456-426614174000", "live_data")

    assert tool is not None
    assert tool.meta.name == "find_operazioni_fuel_log_by_id"


def test_find_matching_tool_matches_operazioni_usage_session_logic() -> None:
    tool = find_matching_tool("Spiega lo stato sessione uso 123e4567-e89b-12d3-a456-426614174000", "logic")

    assert tool is not None
    assert tool.meta.name == "explain_operazioni_usage_session_status"


def test_find_matching_tool_matches_operazioni_activity_logic() -> None:
    tool = find_matching_tool("Spiega lo stato attivita operazioni 123e4567-e89b-12d3-a456-426614174000", "logic")

    assert tool is not None
    assert tool.meta.name == "explain_operazioni_activity_status"


def test_find_matching_tool_matches_operazioni_activity_approval_logic() -> None:
    tool = find_matching_tool("Spiega il motivo approvazione attivita 123e4567-e89b-12d3-a456-426614174000", "logic")

    assert tool is not None
    assert tool.meta.name == "explain_operazioni_activity_approval_decision"


def test_find_matching_tool_matches_operazioni_autodoc_sync_logic() -> None:
    tool = find_matching_tool("Spiega lo stato job autodoc 123e4567-e89b-12d3-a456-426614174000", "logic")

    assert tool is not None
    assert tool.meta.name == "explain_operazioni_autodoc_sync_status"


def test_find_matching_tool_matches_operazioni_fuel_log_logic() -> None:
    tool = find_matching_tool("Spiega lo stato fuel log 123e4567-e89b-12d3-a456-426614174000", "logic")

    assert tool is not None
    assert tool.meta.name == "explain_operazioni_fuel_log_status"


def test_find_matching_tool_keeps_vehicle_lookup_distinct_from_maintenance() -> None:
    tool = find_matching_tool("Mostrami la manutenzione mezzo 123e4567-e89b-12d3-a456-426614174000", "live_data")

    assert tool is not None
    assert tool.meta.name == "find_operazioni_maintenance_by_id"


def test_find_matching_tool_matches_operazioni_unresolved_transaction_lookup() -> None:
    tool = find_matching_tool("Mostrami la transazione non risolta 123e4567-e89b-12d3-a456-426614174000", "live_data")

    assert tool is not None
    assert tool.meta.name == "find_operazioni_unresolved_transaction_by_id"


def test_find_matching_tool_matches_operazioni_unresolved_transaction_logic() -> None:
    tool = find_matching_tool("Spiega il motivo della transazione non risolta 123e4567-e89b-12d3-a456-426614174000", "logic")

    assert tool is not None
    assert tool.meta.name == "explain_operazioni_unresolved_transaction_reason"


def test_find_matching_tool_matches_operazioni_analytics_anomaly_lookup() -> None:
    tool = find_matching_tool("Mostrami l'anomalia analytics 123e4567-e89b-12d3-a456-426614174000", "live_data")

    assert tool is not None
    assert tool.meta.name == "find_operazioni_analytics_anomaly_by_id"


def test_find_matching_tool_matches_operazioni_analytics_summary() -> None:
    tool = find_matching_tool("Mostrami la summary analytics operazioni", "live_data")

    assert tool is not None
    assert tool.meta.name == "get_operazioni_analytics_summary"


def test_find_matching_tool_matches_operazioni_analytics_top_fuel() -> None:
    tool = find_matching_tool("Mostrami i top mezzi carburante analytics operazioni", "live_data")

    assert tool is not None
    assert tool.meta.name == "get_operazioni_analytics_top_fuel_vehicles"


def test_find_matching_tool_matches_operazioni_analytics_top_km_operators() -> None:
    tool = find_matching_tool("Mostrami i top operatori km analytics operazioni", "live_data")

    assert tool is not None
    assert tool.meta.name == "get_operazioni_analytics_top_km_operators"


def test_find_matching_tool_matches_operazioni_analytics_work_hours_by_team() -> None:
    tool = find_matching_tool("Mostrami le ore per team analytics operazioni", "live_data")

    assert tool is not None
    assert tool.meta.name == "get_operazioni_analytics_work_hours_by_team"


def test_find_matching_tool_matches_operazioni_analytics_anomaly_logic() -> None:
    tool = find_matching_tool("Spiega l'anomalia analytics 123e4567-e89b-12d3-a456-426614174000", "logic")

    assert tool is not None
    assert tool.meta.name == "explain_operazioni_analytics_anomaly"


def test_find_matching_tool_matches_operazioni_analytics_metric_logic() -> None:
    tool = find_matching_tool("Spiega come viene calcolato l'indicatore km analytics operazioni", "logic")

    assert tool is not None
    assert tool.meta.name == "explain_operazioni_analytics_metric"


def test_find_matching_tool_matches_operazioni_storage_summary() -> None:
    tool = find_matching_tool("Qual è lo stato storage operazioni?", "live_data")

    assert tool is not None
    assert tool.meta.name == "get_operazioni_storage_status"


def test_find_matching_tool_matches_operazioni_storage_logic() -> None:
    tool = find_matching_tool("Spiega la soglia warning storage operazioni", "logic")

    assert tool is not None
    assert tool.meta.name == "explain_operazioni_storage_alert_level"


def test_find_matching_tool_matches_operazioni_mobile_sync_summary() -> None:
    tool = find_matching_tool("Dammi lo stato mobile sync operazioni", "live_data")

    assert tool is not None
    assert tool.meta.name == "get_operazioni_mobile_sync_status"


def test_find_matching_tool_matches_operazioni_mobile_sync_logic() -> None:
    tool = find_matching_tool("Spiega come funziona il mobile sync operazioni", "logic")

    assert tool is not None
    assert tool.meta.name == "explain_operazioni_mobile_sync_flow"
