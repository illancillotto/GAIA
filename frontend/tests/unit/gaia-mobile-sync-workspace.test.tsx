import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { ElaborazioniGaiaMobileSyncWorkspace } from "@/components/elaborazioni/gaia-mobile-sync-workspace";

const mocks = vi.hoisted(() => {
  class MockApiError extends Error {
    status?: number;
    detailData: unknown;

    constructor(message: string, detailData?: unknown, status?: number) {
      super(message);
      this.name = "ApiError";
      this.status = status;
      this.detailData = detailData;
    }
  }

  return {
    ApiError: MockApiError,
    getStoredAccessToken: vi.fn(),
    getGateMobileSyncStatus: vi.fn(),
    triggerGateMobileSyncRun: vi.fn(),
  };
});

vi.mock("@/lib/auth", () => ({
  getStoredAccessToken: mocks.getStoredAccessToken,
}));

vi.mock("@/lib/api", () => ({
  ApiError: mocks.ApiError,
  getGateMobileSyncStatus: mocks.getGateMobileSyncStatus,
  triggerGateMobileSyncRun: mocks.triggerGateMobileSyncRun,
}));

function buildStatus(overrides: Record<string, unknown> = {}) {
  return {
    sync_enabled: true,
    gateway_base_url: "https://gateway.example.test",
    gateway_configured: true,
    token_configured: true,
    timeout_seconds: 20,
    outbound_scope: ["operators"],
    internal_connector_api: {
      path_prefix: "/api/mobile-sync",
      auth_header: "X-GAIA-Connector-Token",
    },
    last_run: {
      id: "run-1",
      trigger_source: "manual_api",
      status: "succeeded",
      requested_tasks_count: 1,
      operators_pushed: 12,
      duration_ms: 1200,
      requested_tasks: [{ type: "operators" }],
      error_kind: null,
      error_message: null,
      started_at: "2026-06-16T10:00:00Z",
      finished_at: "2026-06-16T10:00:02Z",
    },
    recent_runs: [
      {
        id: "run-1",
        trigger_source: "manual_api",
        status: "succeeded",
        requested_tasks_count: 1,
        operators_pushed: 12,
        duration_ms: 1200,
        requested_tasks: [{ type: "operators" }],
        error_kind: null,
        error_message: null,
        started_at: "2026-06-16T10:00:00Z",
        finished_at: "2026-06-16T10:00:02Z",
      },
      {
        id: "run-2",
        trigger_source: "systemd_timer",
        status: "failed",
        requested_tasks_count: 1,
        operators_pushed: 0,
        duration_ms: 900,
        requested_tasks: [{ type: "operators" }],
        error_kind: "http_status_error",
        error_message: "status=503 method=POST path=/api/mobile/connector/sync/plan",
        started_at: "2026-06-16T09:00:00Z",
        finished_at: "2026-06-16T09:00:01Z",
      },
      {
        id: "run-3",
        trigger_source: "systemd_timer",
        status: "skipped",
        requested_tasks_count: 0,
        operators_pushed: 0,
        duration_ms: 10,
        requested_tasks: [],
        error_kind: "disabled",
        error_message: "GATE_MOBILE_SYNC_ENABLED=false",
        started_at: "2026-06-16T08:00:00Z",
        finished_at: "2026-06-16T08:00:00Z",
      },
    ],
    ...overrides,
  };
}

describe("ElaborazioniGaiaMobileSyncWorkspace", () => {
  beforeEach(() => {
    mocks.getStoredAccessToken.mockReturnValue("token");
    mocks.getGateMobileSyncStatus.mockReset();
    mocks.triggerGateMobileSyncRun.mockReset();
  });

  test("filters history to failed and skipped runs", async () => {
    mocks.getGateMobileSyncStatus.mockResolvedValue(buildStatus());

    render(<ElaborazioniGaiaMobileSyncWorkspace embedded />);

    expect(await screen.findByText("Storico run")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Errori e skip" }));

    const table = screen.getByRole("table");
    await waitFor(() => {
      expect(within(table).queryByText("manual_api")).not.toBeInTheDocument();
    });
    expect(within(table).getAllByText("systemd_timer")).toHaveLength(2);
    expect(within(table).getByText("Fallito")).toBeInTheDocument();
    expect(within(table).getByText("Saltato")).toBeInTheDocument();
  });

  test("shows a dedicated notice when manual run hits a 409 conflict", async () => {
    mocks.getGateMobileSyncStatus.mockResolvedValue(buildStatus());
    mocks.triggerGateMobileSyncRun.mockRejectedValue(
      new mocks.ApiError("Gate mobile sync già in esecuzione: run_id=run-42", undefined, 409),
    );

    render(<ElaborazioniGaiaMobileSyncWorkspace embedded />);

    expect(await screen.findByRole("button", { name: "Esegui sync ora" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Esegui sync ora" }));

    expect(await screen.findByText("Una sync è già in esecuzione. Il monitor è stato aggiornato con il run attivo.")).toBeInTheDocument();
    await waitFor(() => {
      expect(mocks.getGateMobileSyncStatus).toHaveBeenCalledTimes(2);
    });
  });
});
