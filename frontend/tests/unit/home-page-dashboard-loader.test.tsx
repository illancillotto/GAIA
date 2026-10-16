import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import HomePage from "@/app/page";
import { clearSessionBootstrapCache } from "@/lib/session-bootstrap";

const mocks = vi.hoisted(() => ({
  router: { replace: vi.fn(), push: vi.fn() },
  getStoredAccessToken: vi.fn(),
  clearStoredAccessToken: vi.fn(),
  getCurrentUser: vi.fn(),
  getMyPermissions: vi.fn(),
  getDashboardSummary: vi.fn(),
  getUtenzeStats: vi.fn(),
  getPresenceSummary: vi.fn(),
  getRuoloStats: vi.fn(),
  getRuoloStatsAnalytics: vi.fn(),
  catastoGetIndiciOverview: vi.fn(),
  searchOperational: vi.fn(),
  isAuthError: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => mocks.router,
}));

vi.mock("@/lib/auth", () => ({
  getStoredAccessToken: mocks.getStoredAccessToken,
  clearStoredAccessToken: mocks.clearStoredAccessToken,
}));

vi.mock("@/lib/use-presence-heartbeat", () => ({
  usePresenceHeartbeat: vi.fn(),
}));

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    getCurrentUser: mocks.getCurrentUser,
    getMyPermissions: mocks.getMyPermissions,
    getDashboardSummary: mocks.getDashboardSummary,
    getUtenzeStats: mocks.getUtenzeStats,
    getPresenceSummary: mocks.getPresenceSummary,
    isAuthError: mocks.isAuthError,
  };
});

vi.mock("@/lib/operational-search-api", () => ({
  searchOperational: mocks.searchOperational,
}));

vi.mock("@/lib/ruolo-api", () => ({
  getRuoloStats: mocks.getRuoloStats,
  getRuoloStatsAnalytics: mocks.getRuoloStatsAnalytics,
}));

vi.mock("@/lib/api/catasto", () => ({
  catastoGetIndiciOverview: mocks.catastoGetIndiciOverview,
}));

type Dashboard = { nas_users: number; nas_groups: number; shares: number; reviews: number; snapshots: number; sync_runs: number };

function user(enabledModules: string[]) {
  return {
    id: 7,
    username: "home-user",
    email: "home-user@example.local",
    role: "operator",
    is_active: true,
    module_accessi: enabledModules.includes("accessi"),
    module_rete: false,
    module_inventario: false,
    module_catasto: enabledModules.includes("catasto"),
    module_utenze: false,
    module_operazioni: false,
    module_riordino: false,
    module_ruolo: enabledModules.includes("ruolo"),
    module_presenze: false,
    enabled_modules: enabledModules,
  };
}

function nasStat(users: number, groups: number, shares: number): HTMLElement {
  return screen.getByTitle(`${users} utenti, ${groups} gruppi, ${shares} cartelle`);
}

describe("HomePage dashboard loader", () => {
  beforeEach(() => {
    clearSessionBootstrapCache();
    for (const mock of Object.values(mocks)) {
      if (typeof mock === "function") mock.mockReset();
    }
    mocks.router = { replace: vi.fn(), push: vi.fn() };
    mocks.getStoredAccessToken.mockReturnValue("token");
    mocks.getMyPermissions.mockResolvedValue({ sections: [], granted_keys: [] });
    mocks.getRuoloStats.mockResolvedValue({ items: [] });
    mocks.getRuoloStatsAnalytics.mockResolvedValue(null);
    mocks.catastoGetIndiciOverview.mockResolvedValue(null);
    mocks.searchOperational.mockResolvedValue({ query: "", items: [], total: 0, modules: [] });
    mocks.isAuthError.mockReturnValue(false);
  });

  test("loads the cadastral overview without ruolo when only catasto is enabled", async () => {
    mocks.getCurrentUser.mockResolvedValue(user(["catasto"]));
    mocks.catastoGetIndiciOverview.mockResolvedValue({
      anno_riferimento: 2024,
      items: [],
      ruolo_reconciliation: { particelle_ruolo_totali_count: 42 },
    });

    render(<HomePage />);

    expect(await screen.findByTitle("Particelle distinte nel perimetro ruolo 2024")).toHaveTextContent("42");
    expect(mocks.catastoGetIndiciOverview).toHaveBeenCalledTimes(1);
    expect(mocks.catastoGetIndiciOverview).toHaveBeenCalledWith("token", undefined);
    expect(mocks.getRuoloStats).not.toHaveBeenCalled();
    expect(mocks.getRuoloStatsAnalytics).not.toHaveBeenCalled();
  });

  test("logout clears loaded dashboard data so a new session never shows stale values", async () => {
    let resolveSecondDashboard!: (value: Dashboard) => void;
    mocks.getCurrentUser.mockResolvedValue(user(["accessi"]));
    mocks.getDashboardSummary
      .mockResolvedValueOnce({ nas_users: 3, nas_groups: 2, shares: 1, reviews: 0, snapshots: 0, sync_runs: 0 })
      .mockReturnValueOnce(new Promise<Dashboard>((resolve) => {
        resolveSecondDashboard = resolve;
      }));

    const view = render(<HomePage />);
    await waitFor(() => expect(nasStat(3, 2, 1)).toHaveTextContent("6"));

    fireEvent.click(screen.getByRole("button", { name: "Logout" }));
    expect(mocks.clearStoredAccessToken).toHaveBeenCalledTimes(1);
    expect(mocks.router.replace).toHaveBeenCalledWith("/login");
    expect(await screen.findByText("Accesso richiesto")).toBeInTheDocument();

    // A new router instance re-runs session verification in the same mounted page.
    mocks.getStoredAccessToken.mockReturnValue("token-2");
    mocks.router = { replace: vi.fn(), push: vi.fn() };
    view.rerender(<HomePage />);

    expect(await screen.findByText("Hub operativo GAIA")).toBeInTheDocument();
    await waitFor(() => expect(mocks.getDashboardSummary).toHaveBeenCalledTimes(2));
    expect(nasStat(0, 0, 0)).toHaveTextContent("0");
    expect(screen.queryByTitle("3 utenti, 2 gruppi, 1 cartelle")).not.toBeInTheDocument();

    await act(async () => {
      resolveSecondDashboard({ nas_users: 1, nas_groups: 1, shares: 1, reviews: 0, snapshots: 0, sync_runs: 0 });
    });
    expect(nasStat(1, 1, 1)).toHaveTextContent("3");
  });
});
