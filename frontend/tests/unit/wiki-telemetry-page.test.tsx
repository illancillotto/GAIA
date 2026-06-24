import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { WikiTelemetryPage } from "@/features/wiki/WikiTelemetryPage";

const mocks = vi.hoisted(() => ({
  exportWikiTelemetrySeries: vi.fn(),
  getStoredAccessToken: vi.fn(),
  getWikiTelemetryRetention: vi.fn(),
  getWikiTelemetrySummary: vi.fn(),
  getWikiTelemetrySeries: vi.fn(),
  getWikiTelemetrySchedule: vi.fn(),
  pruneWikiTelemetry: vi.fn(),
  refreshWikiTelemetry: vi.fn(),
}));

vi.mock("@/lib/auth", () => ({
  getStoredAccessToken: mocks.getStoredAccessToken,
}));

vi.mock("@/lib/api", () => ({
  exportWikiTelemetrySeries: mocks.exportWikiTelemetrySeries,
  getWikiTelemetryRetention: mocks.getWikiTelemetryRetention,
  getWikiTelemetrySummary: mocks.getWikiTelemetrySummary,
  getWikiTelemetrySeries: mocks.getWikiTelemetrySeries,
  getWikiTelemetrySchedule: mocks.getWikiTelemetrySchedule,
  pruneWikiTelemetry: mocks.pruneWikiTelemetry,
  refreshWikiTelemetry: mocks.refreshWikiTelemetry,
}));

describe("WikiTelemetryPage", () => {
  beforeEach(() => {
    mocks.getStoredAccessToken.mockReturnValue("token");
    mocks.getWikiTelemetrySummary.mockResolvedValue({
      total: 24,
      success_count: 19,
      denied_count: 3,
      no_match_count: 2,
      docs_only_count: 4,
      live_count: 10,
      logic_count: 4,
      hybrid_count: 6,
      avg_latency_ms: 82,
      top_tools: [{ key: "find_share_by_name", count: 6 }],
      top_modules: [{ key: "accessi", count: 8 }],
      top_modes: [{ key: "live_data", count: 10 }],
      top_fallback_reasons: [{ key: "docs_enrichment", count: 5 }],
    });
    mocks.getWikiTelemetrySchedule.mockResolvedValue({
      enabled: true,
      cron: "30 3 * * *",
      timezone: "Europe/Rome",
      lookback_days: 35,
    });
    mocks.getWikiTelemetryRetention.mockResolvedValue({
      audit_retention_days: 365,
      daily_retention_days: 365,
      period_retention_days: 730,
    });
    mocks.refreshWikiTelemetry.mockResolvedValue({ status: "ok", days: 30 });
    mocks.pruneWikiTelemetry.mockResolvedValue({
      status: "ok",
      deleted_audit_rows: 1,
      deleted_daily_rows: 2,
      deleted_period_rows: 3,
    });
    mocks.exportWikiTelemetrySeries.mockResolvedValue(new Blob(["csv"]));
    mocks.getWikiTelemetrySeries
      .mockResolvedValueOnce({
        dimension_type: "global",
        dimension_key: null,
        days: 30,
        granularity: "day",
        items: [
          {
            metric_date: "2026-05-27",
            period_label: "2026-05-27",
            total: 8,
            denied_count: 1,
            no_match_count: 1,
            docs_only_count: 2,
            live_count: 3,
            logic_count: 1,
            hybrid_count: 2,
            avg_latency_ms: 70,
          },
          {
            metric_date: "2026-05-28",
            period_label: "2026-05-28",
            total: 16,
            denied_count: 2,
            no_match_count: 1,
            docs_only_count: 2,
            live_count: 7,
            logic_count: 3,
            hybrid_count: 4,
            avg_latency_ms: 82,
          },
        ],
      })
      .mockResolvedValueOnce({
        dimension_type: "module",
        dimension_key: "accessi",
        days: 30,
        granularity: "day",
        items: [
          {
            metric_date: "2026-05-28",
            period_label: "2026-05-28",
            total: 8,
            denied_count: 1,
            no_match_count: 0,
            docs_only_count: 0,
            live_count: 6,
            logic_count: 1,
            hybrid_count: 1,
            avg_latency_ms: 64,
          },
        ],
      });
  });

  test("renders telemetry summary and trends", async () => {
    render(<WikiTelemetryPage />);

    await waitFor(() => {
      expect(screen.getByText("Telemetria operativa su volumi, fallback e qualità delle risposte del Wiki Agent.")).toBeInTheDocument();
      expect(screen.getByText("24")).toBeInTheDocument();
      expect(screen.getByText("find_share_by_name")).toBeInTheDocument();
      expect(screen.getAllByText("docs_enrichment").length).toBeGreaterThan(0);
      expect(screen.getAllByText("2026-05-28").length).toBeGreaterThan(0);
      expect(screen.getByText("Apri contesto")).toBeInTheDocument();
      expect(screen.getByText("Attivo")).toBeInTheDocument();
      expect(screen.getByText("Refresh metriche")).toBeInTheDocument();
      expect(screen.getByText("Export CSV")).toBeInTheDocument();
      expect(screen.getByText("Prune retention")).toBeInTheDocument();
      expect(screen.getAllByText("365").length).toBeGreaterThan(0);
    });
  });
});
