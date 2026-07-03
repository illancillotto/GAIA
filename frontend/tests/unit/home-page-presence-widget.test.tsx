import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import HomePage from "@/app/page";

const mocks = vi.hoisted(() => ({
  replace: vi.fn(),
  push: vi.fn(),
  router: { replace: vi.fn(), push: vi.fn() },
  getStoredAccessToken: vi.fn(),
  getCurrentUser: vi.fn(),
  getDashboardSummary: vi.fn(),
  getMyPermissions: vi.fn(),
  getNetworkDashboard: vi.fn(),
  getUtenzeStats: vi.fn(),
  getCatastoDocuments: vi.fn(),
  getGateMobileSyncStatus: vi.fn(),
  getPresenceSummary: vi.fn(),
  clearStoredAccessToken: vi.fn(),
  usePresenceHeartbeat: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => mocks.router,
}));

vi.mock("@/lib/auth", () => ({
  getStoredAccessToken: mocks.getStoredAccessToken,
  clearStoredAccessToken: mocks.clearStoredAccessToken,
}));

vi.mock("@/lib/use-presence-heartbeat", () => ({
  usePresenceHeartbeat: mocks.usePresenceHeartbeat,
}));

vi.mock("@/app/home-gate-mobile-summary", () => ({
  buildHomeGateMobileSummary: () => ({ value: "0", copy: "nessuna sync" }),
}));

vi.mock("@/components/wiki/WikiWelcomePopup", () => ({
  WikiWelcomePopup: () => null,
}));

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    getCurrentUser: mocks.getCurrentUser,
    getDashboardSummary: mocks.getDashboardSummary,
    getMyPermissions: mocks.getMyPermissions,
    getNetworkDashboard: mocks.getNetworkDashboard,
    getUtenzeStats: mocks.getUtenzeStats,
    getCatastoDocuments: mocks.getCatastoDocuments,
    getGateMobileSyncStatus: mocks.getGateMobileSyncStatus,
    getPresenceSummary: mocks.getPresenceSummary,
  };
});

describe("HomePage presence widget", () => {
  beforeEach(() => {
    mocks.replace.mockReset();
    mocks.push.mockReset();
    mocks.getStoredAccessToken.mockReset();
    mocks.getCurrentUser.mockReset();
    mocks.getDashboardSummary.mockReset();
    mocks.getMyPermissions.mockReset();
    mocks.getNetworkDashboard.mockReset();
    mocks.getUtenzeStats.mockReset();
    mocks.getCatastoDocuments.mockReset();
    mocks.getGateMobileSyncStatus.mockReset();
    mocks.getPresenceSummary.mockReset();
    mocks.clearStoredAccessToken.mockReset();
    mocks.usePresenceHeartbeat.mockReset();
    mocks.router = { replace: mocks.replace, push: mocks.push };

    mocks.getStoredAccessToken.mockReturnValue("token");
    mocks.getCurrentUser.mockResolvedValue({
      id: 1,
      username: "admin",
      email: "admin@example.local",
      role: "admin",
      is_active: true,
      module_accessi: true,
      module_rete: true,
      module_inventario: false,
      module_catasto: false,
      module_utenze: false,
      module_operazioni: false,
      module_riordino: false,
      module_ruolo: false,
      module_presenze: false,
      enabled_modules: ["accessi", "rete"],
    });
    mocks.getDashboardSummary.mockResolvedValue({
      nas_users: 0,
      nas_groups: 0,
      shares: 0,
      reviews: 0,
      snapshots: 0,
      sync_runs: 0,
    });
    mocks.getMyPermissions.mockResolvedValue({
      sections: [],
      granted_keys: ["accessi.users"],
    });
    mocks.getNetworkDashboard.mockResolvedValue({
      total_devices: 10,
      online_devices: 4,
      offline_devices: 6,
      open_alerts: 1,
      firewalls_online: 1,
      scans_last_24h: 0,
      floor_plans: 0,
      latest_scan_at: null,
    });
    mocks.getUtenzeStats.mockResolvedValue({
      total_subjects: 0,
      total_persons: 0,
      total_companies: 0,
      total_unknown: 0,
      total_documents: 0,
      requires_review: 0,
      active_subjects: 0,
      inactive_subjects: 0,
      documents_unclassified: 0,
      deceased_updates_last_24h: 0,
      deceased_updates_current_month: 0,
      deceased_updates_current_year: 0,
      by_letter: {},
    });
    mocks.getCatastoDocuments.mockResolvedValue([]);
    mocks.getGateMobileSyncStatus.mockResolvedValue(null);
  });

  test("shows GAIA user activity widget for authorized admins", async () => {
    mocks.getPresenceSummary.mockResolvedValue({
      window_minutes: 15,
      active_users: 2,
      visible_users: 1,
      by_module: [{ module_key: "operazioni", count: 2 }],
      items: [
        {
          user_id: 5,
          username: "mrossi",
          full_name: "Mario Rossi",
          role: "admin",
          module_key: "operazioni",
          route_label: "Operazioni",
          action_label: "Monitoraggio utenti attivi",
          path: "/operazioni",
          visible: true,
          last_seen_at: "2026-06-29T10:00:00Z",
          minutes_since_last_seen: 1,
          last_login_at: "2026-06-29T09:00:00Z",
          recent_routes: [],
          recent_actions: [
            {
              action_label: "Monitoraggio utenti attivi",
              occurred_at: "2026-06-29T10:00:00Z",
            },
          ],
        },
      ],
    });

    render(<HomePage />);

    await waitFor(() => {
      expect(screen.getByText("Attività utenti GAIA")).toBeInTheDocument();
    });

    expect(screen.getByText("Mario Rossi")).toBeInTheDocument();
    expect(screen.getByText("Attivi 15 min")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Apri dettaglio/i })).toHaveAttribute("href", "/gaia/users/attivita");
  });

  test("hides GAIA user activity widget when section permission is missing", async () => {
    mocks.getMyPermissions.mockResolvedValue({
      sections: [],
      granted_keys: [],
    });
    mocks.getPresenceSummary.mockResolvedValue({
      window_minutes: 15,
      active_users: 0,
      visible_users: 0,
      by_module: [],
      items: [],
    });

    render(<HomePage />);

    await waitFor(() => {
      expect(screen.getByText("Hub operativo GAIA")).toBeInTheDocument();
    });

    expect(screen.queryByText("Attività utenti GAIA")).not.toBeInTheDocument();
  });

  test("redirects anonymous users to login without leaving the home page in session-check loading", async () => {
    mocks.getStoredAccessToken.mockReturnValue(null);

    render(<HomePage />);

    await waitFor(() => {
      expect(mocks.replace).toHaveBeenCalledWith("/login");
    });

    expect(screen.getByText("Accesso richiesto")).toBeInTheDocument();
    expect(screen.getByText("Accesso richiesto. Effettua il login.")).toBeInTheDocument();
    expect(screen.queryByText("Verifica sessione in corso…")).not.toBeInTheDocument();
    expect(mocks.getCurrentUser).not.toHaveBeenCalled();
  });
});
