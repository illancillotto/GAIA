import { describe, expect, test } from "vitest";

import { buildHomeGateMobileSummary } from "@/app/home-gate-mobile-summary";

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
      operators_pushed: 276,
      duration_ms: 850,
      requested_tasks: [{ type: "operators" }],
      error_kind: null,
      error_message: null,
      started_at: "2026-06-22T11:10:00Z",
      finished_at: "2026-06-22T11:10:01Z",
    },
    recent_runs: [],
    ...overrides,
  };
}

describe("buildHomeGateMobileSummary", () => {
  test("returns unavailable summary when status is absent", () => {
    expect(buildHomeGateMobileSummary(null)).toEqual({
      value: "Non disponibile",
      copy: "Monitor del canale tablet per letture contatori non caricato.",
    });
  });

  test("returns disabled summary when sync flag is off", () => {
    expect(buildHomeGateMobileSummary(buildStatus({ sync_enabled: false }))).toEqual({
      value: "Disattiva",
      copy: "Flag runtime spento: i tablet contatori non ricevono aggiornamenti automatici.",
    });
  });

  test("returns configuration warning when gateway is incomplete", () => {
    expect(buildHomeGateMobileSummary(buildStatus({ gateway_configured: false }))).toEqual({
      value: "Config mancante",
      copy: "Gateway pubblico o token tecnico per i tablet contatori non configurati.",
    });
  });

  test("returns ready summary when no run exists yet", () => {
    expect(buildHomeGateMobileSummary(buildStatus({ last_run: null }))).toEqual({
      value: "Pronta",
      copy: "Canale tablet configurato per contatori, ma nessun run registrato.",
    });
  });

  test("returns running summary", () => {
    const result = buildHomeGateMobileSummary(buildStatus({ last_run: { ...buildStatus().last_run, status: "running", finished_at: null } }));
    expect(result.value).toBe("In esecuzione");
    expect(result.copy).toContain("Aggiornamento tablet contatori avviato");
  });

  test("returns failed summary", () => {
    const result = buildHomeGateMobileSummary(buildStatus({ last_run: { ...buildStatus().last_run, status: "failed" } }));
    expect(result.value).toBe("Errore");
    expect(result.copy).toContain("Ultimo aggiornamento tablet contatori fallito");
  });

  test("returns skipped summary", () => {
    const result = buildHomeGateMobileSummary(buildStatus({ last_run: { ...buildStatus().last_run, status: "skipped" } }));
    expect(result.value).toBe("Saltata");
    expect(result.copy).toContain("Ultimo aggiornamento tablet contatori saltato");
  });

  test("returns pushed operators when latest run succeeded", () => {
    const result = buildHomeGateMobileSummary(buildStatus());
    expect(result.value).toBe("276");
    expect(result.copy).toContain("Operatori pubblicati verso i tablet letture");
    expect(result.copy).toContain("22/06/26");
  });
});
