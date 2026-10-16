import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import {
  canReadHomePresenceSummary,
  emptyHomeDashboardData,
  loadHomeDashboardData,
} from "@/app/home-dashboard-data";
import { SESSION_BOOTSTRAP_TIMEOUT_MS } from "@/lib/api";

const mocks = vi.hoisted(() => ({
  getDashboardSummary: vi.fn(),
  getPresenceSummary: vi.fn(),
  getUtenzeStats: vi.fn(),
  getRuoloStats: vi.fn(),
  getRuoloStatsAnalytics: vi.fn(),
  catastoGetIndiciOverview: vi.fn(),
}));

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    getDashboardSummary: mocks.getDashboardSummary,
    getPresenceSummary: mocks.getPresenceSummary,
    getUtenzeStats: mocks.getUtenzeStats,
  };
});

vi.mock("@/lib/ruolo-api", () => ({
  getRuoloStats: mocks.getRuoloStats,
  getRuoloStatsAnalytics: mocks.getRuoloStatsAnalytics,
}));

vi.mock("@/lib/api/catasto", () => ({
  catastoGetIndiciOverview: mocks.catastoGetIndiciOverview,
}));

const allModules = ["accessi", "catasto", "utenze", "ruolo"];
const dashboard = { nas_users: 3, nas_groups: 2, shares: 1, reviews: 0, snapshots: 0, sync_runs: 0 };
const utenze = { ...emptyHomeDashboardData.utenzeSummary, total_subjects: 9 };
const presence = { window_minutes: 15, active_users: 2, visible_users: 1, items: [], by_module: [] };
const ruoloStats = { items: [{ anno_tributario: 2025 }] };
const ruoloAnalytics = { anno_tributario: 2025 };
const overview = { anno_riferimento: 2025 };

function mockAllFulfilled(): void {
  mocks.getDashboardSummary.mockResolvedValue(dashboard);
  mocks.getUtenzeStats.mockResolvedValue(utenze);
  mocks.getPresenceSummary.mockResolvedValue(presence);
  mocks.getRuoloStats.mockResolvedValue(ruoloStats);
  mocks.getRuoloStatsAnalytics.mockResolvedValue(ruoloAnalytics);
  mocks.catastoGetIndiciOverview.mockResolvedValue(overview);
}

describe("canReadHomePresenceSummary", () => {
  test.each([
    ["admin", ["accessi"], ["accessi.users"], true],
    ["super_admin", ["accessi"], ["accessi.users"], true],
    ["reviewer", ["accessi"], ["accessi.users"], false],
    ["admin", ["rete"], ["accessi.users"], false],
    ["admin", ["accessi"], [], false],
  ])("role=%s modules=%j sections=%j -> %s", (role, modules, sections, expected) => {
    expect(canReadHomePresenceSummary({ role, enabled_modules: modules }, sections)).toBe(expected);
  });
});

describe("loadHomeDashboardData", () => {
  let warnSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    for (const mock of Object.values(mocks)) mock.mockReset();
    warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
  });

  afterEach(() => {
    warnSpy.mockRestore();
  });

  test("skips every fetch and returns the empty data when no module is enabled", async () => {
    const data = await loadHomeDashboardData("token", { role: "admin", enabled_modules: [] }, ["accessi.users"]);

    expect(data).toEqual(emptyHomeDashboardData);
    expect(data.dashboardSummary).toBe(emptyHomeDashboardData.dashboardSummary);
    expect(data.ruoloStats).toBe(emptyHomeDashboardData.ruoloStats);
    for (const mock of Object.values(mocks)) expect(mock).not.toHaveBeenCalled();
    expect(warnSpy).not.toHaveBeenCalled();
  });

  test("loads every module with the expected arguments when all are enabled", async () => {
    mockAllFulfilled();

    const data = await loadHomeDashboardData("tok", { role: "super_admin", enabled_modules: allModules }, ["accessi.users"]);

    expect(data).toEqual({
      dashboardSummary: dashboard,
      utenzeSummary: utenze,
      presenceSummary: presence,
      ruoloStats,
      ruoloAnalytics,
      catastoIndiciOverview: overview,
    });
    expect(mocks.getDashboardSummary).toHaveBeenCalledWith("tok", { timeoutMs: SESSION_BOOTSTRAP_TIMEOUT_MS });
    expect(mocks.getUtenzeStats).toHaveBeenCalledWith("tok");
    expect(mocks.getPresenceSummary).toHaveBeenCalledWith("tok", { windowMinutes: 15 });
    expect(mocks.getRuoloStats).toHaveBeenCalledWith("tok");
    expect(mocks.getRuoloStatsAnalytics).toHaveBeenCalledWith("tok", 2025);
    expect(mocks.catastoGetIndiciOverview).toHaveBeenCalledWith("tok", 2025);
    expect(warnSpy).not.toHaveBeenCalled();
  });

  test("skips presence for non-admin roles and analytics without a ruolo year", async () => {
    mockAllFulfilled();
    mocks.getRuoloStats.mockResolvedValue({ items: [] });

    const data = await loadHomeDashboardData("tok", { role: "operator", enabled_modules: allModules }, ["accessi.users"]);

    expect(mocks.getPresenceSummary).not.toHaveBeenCalled();
    expect(mocks.getRuoloStatsAnalytics).not.toHaveBeenCalled();
    expect(mocks.catastoGetIndiciOverview).toHaveBeenCalledWith("tok", undefined);
    expect(data.presenceSummary).toBe(emptyHomeDashboardData.presenceSummary);
    expect(data.ruoloAnalytics).toBeNull();
  });

  test("loads the cadastral overview without a ruolo year when only catasto is enabled", async () => {
    mockAllFulfilled();

    const data = await loadHomeDashboardData("tok", { role: "operator", enabled_modules: ["catasto"] }, []);

    expect(mocks.getRuoloStats).not.toHaveBeenCalled();
    expect(mocks.getRuoloStatsAnalytics).not.toHaveBeenCalled();
    expect(mocks.catastoGetIndiciOverview).toHaveBeenCalledTimes(1);
    expect(mocks.catastoGetIndiciOverview).toHaveBeenCalledWith("tok", undefined);
    expect(data).toEqual({ ...emptyHomeDashboardData, catastoIndiciOverview: overview });
  });

  test("falls back per module and warns with the exact partial payload", async () => {
    const dashboardError = new Error("dashboard down");
    mockAllFulfilled();
    mocks.getDashboardSummary.mockRejectedValue(dashboardError);
    mocks.getRuoloStats.mockRejectedValue(null);

    const data = await loadHomeDashboardData("tok", { role: "admin", enabled_modules: allModules }, ["accessi.users"]);

    expect(data).toEqual({
      ...emptyHomeDashboardData,
      utenzeSummary: utenze,
      presenceSummary: presence,
      catastoIndiciOverview: overview,
    });
    expect(mocks.getRuoloStatsAnalytics).not.toHaveBeenCalled();
    expect(warnSpy).toHaveBeenCalledTimes(1);
    expect(warnSpy).toHaveBeenCalledWith("Home dashboard loaded with partial module data", {
      dashboardError,
      utenzeError: null,
      presenceSummaryError: null,
      ruoloStatsError: null,
      ruoloAnalyticsError: null,
      catastoIndiciOverviewError: null,
    });
  });

  test("warns on rejection status even when the only rejection reason is nullish", async () => {
    mockAllFulfilled();
    mocks.getRuoloStats.mockRejectedValue(undefined);

    await loadHomeDashboardData("tok", { role: "admin", enabled_modules: allModules }, ["accessi.users"]);

    expect(warnSpy).toHaveBeenCalledWith("Home dashboard loaded with partial module data", {
      dashboardError: null,
      utenzeError: null,
      presenceSummaryError: null,
      ruoloStatsError: undefined,
      ruoloAnalyticsError: null,
      catastoIndiciOverviewError: null,
    });
  });

  test("falls back to null for failed ruolo analytics and cadastral overview", async () => {
    const analyticsError = new Error("analytics down");
    const overviewError = new Error("indici down");
    mockAllFulfilled();
    mocks.getUtenzeStats.mockRejectedValue("utenze down");
    mocks.getPresenceSummary.mockRejectedValue("presence down");
    mocks.getRuoloStatsAnalytics.mockRejectedValue(analyticsError);
    mocks.catastoGetIndiciOverview.mockRejectedValue(overviewError);

    const data = await loadHomeDashboardData("tok", { role: "admin", enabled_modules: allModules }, ["accessi.users"]);

    expect(data).toEqual({
      ...emptyHomeDashboardData,
      dashboardSummary: dashboard,
      ruoloStats,
    });
    expect(warnSpy).toHaveBeenCalledWith("Home dashboard loaded with partial module data", {
      dashboardError: null,
      utenzeError: "utenze down",
      presenceSummaryError: "presence down",
      ruoloStatsError: null,
      ruoloAnalyticsError: analyticsError,
      catastoIndiciOverviewError: overviewError,
    });
  });
});
