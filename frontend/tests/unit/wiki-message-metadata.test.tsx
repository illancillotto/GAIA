import { render, screen } from "@testing-library/react";

import { EvidenceBadge, ModeBadge, ToolCallBadge } from "@/features/wiki/message-metadata";

describe("Wiki message metadata", () => {
  test("renders live mode badge", () => {
    render(<ModeBadge mode="live_data" />);

    expect(screen.getByText("Live")).toBeInTheDocument();
  });

  test("renders logic evidence with source key and excerpt", () => {
    render(
      <EvidenceBadge
        evidence={{
          type: "logic",
          label: "Spiegazione permesso sezione",
          source_key: "accessi.permissions.accessi.permissions",
          excerpt: "Permesso derivato da role_default.",
        }}
      />,
    );

    expect(screen.getByText("Spiegazione permesso sezione")).toBeInTheDocument();
    expect(screen.getByText("accessi.permissions.accessi.permissions")).toBeInTheDocument();
    expect(screen.getByText("Permesso derivato da role_default.")).toBeInTheDocument();
  });

  test("renders denied tool call badge", () => {
    render(<ToolCallBadge toolCall={{ tool_name: "find_subject_by_cf", success: false, redacted: true }} />);

    expect(screen.getByText("find_subject_by_cf")).toBeInTheDocument();
  });

  test("renders hybrid mode badge", () => {
    render(<ModeBadge mode="hybrid" />);

    expect(screen.getByText("Hybrid")).toBeInTheDocument();
  });

  test("renders docs evidence label", () => {
    render(
      <EvidenceBadge
        evidence={{
          type: "docs",
          label: "RUOLO_OVERVIEW",
          source_key: "RUOLO_OVERVIEW.md",
          excerpt: "Spiegazione collegamenti ruolo.",
        }}
      />,
    );

    expect(screen.getByText("RUOLO_OVERVIEW")).toBeInTheDocument();
    expect(screen.getByText("RUOLO_OVERVIEW.md")).toBeInTheDocument();
  });

  test("renders analytics payload preview for top operators", () => {
    render(
      <EvidenceBadge
        evidence={{
          type: "live_data",
          label: "Top operatori km Operazioni",
          source_key: "operazioni.analytics.km.top-operators",
          payload_kind: "operazioni_analytics_top_km_operators",
          excerpt: "Classifica km operatori.",
          payload: {
            top_operators: [{ label: "Mario Rossi", total_km: 80 }],
          },
        }}
      />,
    );

    expect(screen.getByText("Mario Rossi: 80 km")).toBeInTheDocument();
  });

  test("renders storage payload preview with quota and alerts", () => {
    render(
      <EvidenceBadge
        evidence={{
          type: "live_data",
          label: "Storage alerts Operazioni",
          source_key: "operazioni.storage.summary",
          payload_kind: "operazioni_storage_status",
          payload: {
            metric: { percentage_used: 85 },
            active_alert_count: 1,
            highest_level: "warning",
            alerts: [{ level: "warning", threshold: 80 }],
          },
        }}
      />,
    );

    expect(screen.getByText("Quota: 85%")).toBeInTheDocument();
    expect(screen.getByText("Alert: 1")).toBeInTheDocument();
    expect(screen.getByText("warning: soglia 80%")).toBeInTheDocument();
  });

  test("renders workflow payload preview for usage session detail", () => {
    render(
      <EvidenceBadge
        evidence={{
          type: "live_data",
          label: "Dettaglio sessione d'uso Operazioni",
          source_key: "operazioni.usage-sessions.123",
          payload_kind: "operazioni_usage_session_detail",
          payload: {
            status: "validated",
            vehicle_code: "MEZZO-07",
            actual_driver_username: "mrossi",
            started_at: "2026-05-27T08:00:00",
            ended_at: "2026-05-27T09:15:00",
          },
        }}
      />,
    );

    expect(screen.getByText("Stato: validated")).toBeInTheDocument();
    expect(screen.getByText("Mezzo: MEZZO-07")).toBeInTheDocument();
    expect(screen.getByText("Driver: mrossi")).toBeInTheDocument();
  });

  test("renders AUTODOC payload preview with sync counters", () => {
    render(
      <EvidenceBadge
        evidence={{
          type: "logic",
          label: "Spiegazione job AUTODOC Operazioni",
          source_key: "operazioni.autodoc-sync.logic.job-1",
          payload_kind: "operazioni_autodoc_sync_status",
          payload: {
            status: "failed",
            records_synced: 3,
            records_errors: 2,
          },
        }}
      />,
    );

    expect(screen.getByText("Job: failed")).toBeInTheDocument();
    expect(screen.getByText("Synced: 3")).toBeInTheDocument();
    expect(screen.getByText("Errori: 2")).toBeInTheDocument();
  });

  test("renders operazioni dashboard payload preview", () => {
    render(
      <EvidenceBadge
        evidence={{
          type: "live_data",
          label: "Dashboard Operazioni",
          source_key: "operazioni.dashboard.summary",
          payload_kind: "operazioni_dashboard_summary",
          payload: {
            vehicles: { total: 12 },
            activities: { in_progress: 4 },
            cases: { open: 3 },
          },
        }}
      />,
    );

    expect(screen.getByText("Mezzi: 12")).toBeInTheDocument();
    expect(screen.getByText("Attività in corso: 4")).toBeInTheDocument();
    expect(screen.getByText("Case aperti: 3")).toBeInTheDocument();
  });

  test("renders business payload preview for catasto detail", () => {
    render(
      <EvidenceBadge
        evidence={{
          type: "live_data",
          label: "Dettaglio particella Catasto",
          source_key: "catasto.particelle.123",
          payload_kind: "catasto_particella_detail",
          payload: {
            nome_comune: "Oristano",
            foglio: "12",
            particella: "345",
            ha_anagrafica: true,
          },
        }}
      />,
    );

    expect(screen.getByText("Comune: Oristano")).toBeInTheDocument();
    expect(screen.getByText("Foglio: 12")).toBeInTheDocument();
    expect(screen.getByText("Particella: 345")).toBeInTheDocument();
  });

  test("renders business payload preview for utenze subject", () => {
    render(
      <EvidenceBadge
        evidence={{
          type: "live_data",
          label: "Dettaglio soggetto Utenze",
          source_key: "utenze.subjects.123",
          payload_kind: "utenze_subject_detail",
          payload: {
            display_name: "Mario Rossi",
            status: "active",
            subject_type: "person",
            documents_count: 2,
            requires_review: false,
          },
        }}
      />,
    );

    expect(screen.getByText("Nome: Mario Rossi")).toBeInTheDocument();
    expect(screen.getByText("Stato: active")).toBeInTheDocument();
    expect(screen.getByText("Documenti: 2")).toBeInTheDocument();
  });
});
