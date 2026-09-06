import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import {
  formatPortalDuration,
  portalStatusLabel,
  SisterPortalHealthWorkspace,
} from "@/components/elaborazioni/sister-portal-health-workspace";
import type { SisterPortalHealth } from "@/types/api";


const mocks = vi.hoisted(() => ({
  getSisterPortalHealth: vi.fn(),
  getStoredAccessToken: vi.fn(),
}));

vi.mock("@/lib/auth", () => ({ getStoredAccessToken: mocks.getStoredAccessToken }));
vi.mock("@/lib/portal-health-api", () => ({ getSisterPortalHealth: mocks.getSisterPortalHealth }));


function health(overrides: Partial<SisterPortalHealth> = {}): SisterPortalHealth {
  return {
    generated_at: "2026-08-20T12:00:00Z",
    window_hours: 24,
    status: "critical",
    totals: {
      events: 12,
      executions: 4,
      operating_credentials: 2,
      average_executions_per_credential: 2,
      successes: 3,
      errors: 2,
      retries: 1,
      cooldowns: 1,
      success_rate: 60,
      average_duration_ms: 1500,
      p95_duration_ms: 120000,
    },
    downloads: {
      total: 6,
      by_visura_type: { Sintetica: 4, Completa: 2 },
      by_request_type: { ATTUALITA: 4, STORICA: 1, NON_CLASSIFICATA: 1 },
    },
    timeline: [
      {
        bucket: "2026-08-20T11:00:00Z",
        events: 5,
        successes: 3,
        errors: 2,
        average_duration_ms: 1500,
      },
    ],
    steps: [
      {
        step: "download_pdf",
        events: 5,
        successes: 3,
        errors: 2,
        average_duration_ms: 1500,
        p95_duration_ms: 120000,
      },
      {
        step: "login",
        events: 2,
        successes: 2,
        errors: 0,
        average_duration_ms: 400,
        p95_duration_ms: 500,
      },
    ],
    errors: [
      {
        event_type: "http_error",
        step: "portal_response",
        count: 2,
        last_seen_at: "2026-08-20T11:30:00Z",
        http_status: 503,
      },
      {
        event_type: "timeout",
        step: "login",
        count: 1,
        last_seen_at: "2026-08-20T10:30:00Z",
        http_status: null,
      },
    ],
    credentials: [
      {
        credential_id: "11111111-1111-1111-1111-111111111111",
        label: "Profilo A",
        events: 10,
        successes: 3,
        errors: 2,
        downloads: 4,
        success_rate: 60,
        last_seen_at: "2026-08-20T11:30:00Z",
      },
      {
        credential_id: null,
        label: "Sessione non associata",
        events: 2,
        successes: 0,
        errors: 0,
        downloads: 0,
        success_rate: 0,
        last_seen_at: "2026-08-20T10:30:00Z",
      },
    ],
    alerts: [
      {
        id: "critical",
        severity: "critical",
        title: "Errori server SISTER ripetuti",
        detail: "3 risposte HTTP 5xx.",
        active_since: "2026-08-20T09:00:00Z",
      },
      {
        id: "warning",
        severity: "warning",
        title: "Portale lento",
        detail: "P95 elevato.",
        active_since: "2026-08-20T10:00:00Z",
      },
    ],
    recent_events: [
      {
        id: "event-1",
        occurred_at: "2026-08-20T11:30:00Z",
        event_type: "http_error",
        step: "portal_response",
        outcome: "error",
        severity: "error",
        duration_ms: null,
        http_status: 503,
        endpoint: "/Visure/test.do",
        attempt: 1,
        cooldown_seconds: 90,
        credential_id: "11111111-1111-1111-1111-111111111111",
        credential_label: "Profilo A",
        batch_id: null,
        request_id: null,
      },
      {
        id: "event-2",
        occurred_at: "2026-08-20T11:00:00Z",
        event_type: "download",
        step: "download_pdf",
        outcome: "success",
        severity: "info",
        duration_ms: 1500,
        http_status: null,
        endpoint: null,
        attempt: null,
        cooldown_seconds: null,
        credential_id: null,
        credential_label: null,
        batch_id: null,
        request_id: null,
      },
    ],
    ...overrides,
  };
}


describe("SisterPortalHealthWorkspace", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.getStoredAccessToken.mockReturnValue("token");
    mocks.getSisterPortalHealth.mockResolvedValue(health());
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  test("formats durations and state labels", () => {
    expect(formatPortalDuration(null)).toBe("n/d");
    expect(formatPortalDuration(450)).toBe("450 ms");
    expect(formatPortalDuration(1500)).toBe("1.5 s");
    expect(formatPortalDuration(120000)).toBe("2.0 min");
    expect(portalStatusLabel("healthy")).toBe("Operativo");
    expect(portalStatusLabel("degraded")).toBe("Degradato");
    expect(portalStatusLabel("critical")).toBe("Critico");
    expect(portalStatusLabel("unknown")).toBe("In attesa di dati");
  });

  test("renders metrics, alerts, breakdowns and reload controls", async () => {
    render(<SisterPortalHealthWorkspace />);
    expect(screen.getByText("In attesa di dati")).toBeInTheDocument();

    await waitFor(() => expect(screen.getByText("Critico")).toBeInTheDocument());
    expect(screen.getByText("Errori server SISTER ripetuti")).toBeInTheDocument();
    expect(screen.getByText("Portale lento")).toBeInTheDocument();
    expect(screen.getAllByText("Profilo A")).toHaveLength(2);
    expect(screen.getByText("Visure scaricate")).toBeInTheDocument();
    expect(screen.getByText("Credenziali attive")).toBeInTheDocument();
    expect(screen.getByText("Media operazioni")).toBeInTheDocument();
    expect(screen.getByText("con esecuzioni nella finestra")).toBeInTheDocument();
    expect(screen.getByText("per credenziale attiva")).toBeInTheDocument();
    expect(screen.getByText((_, element) => element?.textContent === "4visure")).toBeInTheDocument();
    expect(screen.getByText("Completa 2 · Sintetica 4 · Attualità 4 · NON_CLASSIFICATA 1 · Storiche 1")).toBeInTheDocument();
    expect(screen.getByText("Non associata")).toBeInTheDocument();
    expect(screen.getAllByText("download pdf").length).toBeGreaterThan(0);
    expect(screen.getAllByText("HTTP 503").length).toBeGreaterThan(0);
    expect(screen.getByText("timeout")).toBeInTheDocument();
    expect(screen.getByText("error")).toBeInTheDocument();
    expect(screen.getByText("success")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "7 giorni" }));
    await waitFor(() => expect(mocks.getSisterPortalHealth).toHaveBeenCalledWith("token", 168));
    fireEvent.click(screen.getByRole("button", { name: "Aggiorna" }));
    await waitFor(() => expect(mocks.getSisterPortalHealth.mock.calls.length).toBeGreaterThanOrEqual(3));
  });

  test("renders empty states and healthy status", async () => {
    mocks.getSisterPortalHealth.mockResolvedValue(health({
      status: "healthy",
      timeline: [],
      steps: [],
      errors: [],
      credentials: [],
      alerts: [],
      recent_events: [],
      downloads: { total: 0, by_visura_type: {}, by_request_type: {} },
    }));
    render(<SisterPortalHealthWorkspace />);
    await waitFor(() => expect(screen.getByText("Operativo")).toBeInTheDocument());
    expect(screen.getByText("Nessun evento nella finestra")).toBeInTheDocument();
    expect(screen.getByText("Nessun alert attivo nella finestra selezionata.")).toBeInTheDocument();
    expect(screen.getByText("Nessuna sessione associata a credenziali nella finestra.")).toBeInTheDocument();
    expect(screen.getByText("Nessun errore classificato.")).toBeInTheDocument();
    expect(screen.getByText("Nessun evento recente.")).toBeInTheDocument();
    expect(screen.getByText("nessuna visura nella finestra")).toBeInTheDocument();
  });

  test("shows degraded state and refreshes on interval", async () => {
    vi.useFakeTimers();
    mocks.getSisterPortalHealth.mockResolvedValue(health({ status: "degraded" }));
    render(<SisterPortalHealthWorkspace />);
    await act(async () => Promise.resolve());
    expect(screen.getByText("Degradato")).toBeInTheDocument();
    await act(async () => vi.advanceTimersByTimeAsync(30_000));
    expect(mocks.getSisterPortalHealth).toHaveBeenCalledTimes(2);
  });

  test("handles missing token and both error shapes", async () => {
    mocks.getStoredAccessToken.mockReturnValue(null);
    const first = render(<SisterPortalHealthWorkspace />);
    await waitFor(() => expect(screen.getByText("Sessione non disponibile.")).toBeInTheDocument());
    first.unmount();

    mocks.getStoredAccessToken.mockReturnValue("token");
    mocks.getSisterPortalHealth.mockRejectedValueOnce(new Error("backend down"));
    const second = render(<SisterPortalHealthWorkspace />);
    await waitFor(() => expect(screen.getByText("backend down")).toBeInTheDocument());
    second.unmount();

    mocks.getSisterPortalHealth.mockRejectedValueOnce("unknown");
    render(<SisterPortalHealthWorkspace />);
    await waitFor(() => expect(screen.getByText("Errore nel caricamento della telemetria SISTER.")).toBeInTheDocument());
  });
});
