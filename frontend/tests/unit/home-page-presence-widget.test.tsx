import { fireEvent, render, screen, waitFor } from "@testing-library/react";
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
  isAuthError: vi.fn(),
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
    isAuthError: mocks.isAuthError,
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
    mocks.isAuthError.mockReset();
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
    mocks.isAuthError.mockReturnValue(false);
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
        {
          user_id: 6,
          username: "fallback-user",
          full_name: null,
          role: "viewer",
          module_key: null,
          route_label: null,
          action_label: null,
          path: "/fallback-route",
          visible: true,
          last_seen_at: "2026-06-29T10:00:00Z",
          minutes_since_last_seen: 2,
          last_login_at: null,
          recent_routes: [],
          recent_actions: [],
        },
      ],
    });

    render(<HomePage />);

    await waitFor(() => {
      expect(screen.getByText("Attività utenti GAIA")).toBeInTheDocument();
    });

    expect(screen.getByText("Mario Rossi")).toBeInTheDocument();
    expect(screen.getByText("fallback-user")).toBeInTheDocument();
    expect(screen.getByText("/fallback-route")).toBeInTheDocument();
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

  test("shows GIS Platform in home and global search for GIS-enabled users", async () => {
    mocks.getCurrentUser.mockResolvedValue({
      id: 2,
      username: "gis-viewer",
      email: "gis-viewer@example.local",
      role: "viewer",
      is_active: true,
      module_accessi: false,
      module_rete: false,
      module_inventario: false,
      module_catasto: false,
      module_utenze: false,
      module_operazioni: false,
      module_riordino: false,
      module_ruolo: false,
      module_presenze: false,
      enabled_modules: ["gis"],
    });
    mocks.getMyPermissions.mockResolvedValue({
      sections: [],
      granted_keys: [],
    });

    render(<HomePage />);

    expect(await screen.findByRole("heading", { name: "GIS Platform" })).toBeInTheDocument();

    fireEvent.change(screen.getByPlaceholderText("Ricerca globale…"), { target: { value: "postgis" } });
    fireEvent.click(screen.getByRole("button", { name: "GIS Platform · Catalogo" }));

    expect(mocks.push).toHaveBeenCalledWith("/gis/catalogo");
    expect(mocks.getCatastoDocuments).not.toHaveBeenCalled();
  });

  test("handles partial module dashboard failures and logout", async () => {
    const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
    mocks.getCurrentUser.mockResolvedValue({
      id: 3,
      username: "ops-admin",
      email: "ops-admin@example.local",
      role: "admin",
      is_active: true,
      module_accessi: true,
      module_rete: true,
      module_inventario: false,
      module_catasto: true,
      module_utenze: true,
      module_operazioni: false,
      module_riordino: false,
      module_ruolo: false,
      module_presenze: false,
      enabled_modules: ["accessi", "rete", "catasto", "utenze"],
    });
    mocks.getNetworkDashboard.mockRejectedValue(new Error("network down"));
    mocks.getUtenzeStats.mockRejectedValue(new Error("utenze down"));
    mocks.getCatastoDocuments.mockRejectedValue(new Error("catasto down"));
    mocks.getGateMobileSyncStatus.mockRejectedValue(new Error("sync down"));
    mocks.getPresenceSummary.mockRejectedValue(new Error("presence down"));

    render(<HomePage />);

    expect(await screen.findByText("Hub operativo GAIA")).toBeInTheDocument();
    expect(warnSpy).toHaveBeenCalledWith(
      "Home dashboard loaded with partial module data",
      expect.objectContaining({
        networkError: expect.any(Error),
        utenzeError: expect.any(Error),
        catastoError: expect.any(Error),
        gateMobileSyncError: expect.any(Error),
        presenceSummaryError: expect.any(Error),
      }),
    );

    fireEvent.click(screen.getByRole("button", { name: "Logout" }));

    expect(mocks.clearStoredAccessToken).toHaveBeenCalled();
    expect(mocks.replace).toHaveBeenCalledWith("/login");
    warnSpy.mockRestore();
  });

  test("logs partial module dashboard failures with null entries for fulfilled modules", async () => {
    const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
    const allModuleAdmin = {
      id: 6,
      username: "mixed-admin",
      email: "mixed-admin@example.local",
      role: "admin",
      is_active: true,
      module_accessi: true,
      module_rete: true,
      module_inventario: false,
      module_catasto: true,
      module_utenze: true,
      module_operazioni: false,
      module_riordino: false,
      module_ruolo: false,
      module_presenze: false,
      enabled_modules: ["accessi", "rete", "catasto", "utenze"],
    };
    mocks.getCurrentUser.mockResolvedValue(allModuleAdmin);
    mocks.getPresenceSummary.mockRejectedValueOnce(new Error("presence down"));

    const firstRender = render(<HomePage />);

    expect(await screen.findByText("Hub operativo GAIA")).toBeInTheDocument();
    expect(warnSpy).toHaveBeenLastCalledWith(
      "Home dashboard loaded with partial module data",
      expect.objectContaining({
        networkError: null,
        utenzeError: null,
        catastoError: null,
        gateMobileSyncError: null,
        presenceSummaryError: expect.any(Error),
      }),
    );

    firstRender.unmount();
    warnSpy.mockClear();
    mocks.getCurrentUser.mockResolvedValue(allModuleAdmin);
    mocks.getNetworkDashboard.mockRejectedValueOnce(new Error("network down"));
    mocks.getPresenceSummary.mockResolvedValueOnce({
      window_minutes: 15,
      active_users: 0,
      visible_users: 0,
      by_module: [],
      items: [],
    });

    render(<HomePage />);

    expect(await screen.findByText("Hub operativo GAIA")).toBeInTheDocument();
    expect(warnSpy).toHaveBeenLastCalledWith(
      "Home dashboard loaded with partial module data",
      expect.objectContaining({
        networkError: expect.any(Error),
        presenceSummaryError: null,
      }),
    );
    warnSpy.mockRestore();
  });

  test("clears stored auth when home session loading fails with an auth error", async () => {
    mocks.getCurrentUser.mockRejectedValue(new Error("expired"));
    mocks.isAuthError.mockReturnValue(true);

    render(<HomePage />);

    expect(await screen.findByText("expired")).toBeInTheDocument();
    expect(mocks.clearStoredAccessToken).toHaveBeenCalled();
    expect(mocks.replace).toHaveBeenCalledWith("/login");
  });

  test("shows a generic home load error when backend failure is not an Error", async () => {
    mocks.getCurrentUser.mockRejectedValue("fatal");

    render(<HomePage />);

    expect(await screen.findByText("Errore imprevisto")).toBeInTheDocument();
    expect(mocks.clearStoredAccessToken).not.toHaveBeenCalled();
  });

  test("supports keyboard and outside-click global search interactions", async () => {
    mocks.getCurrentUser.mockResolvedValue({
      id: 4,
      username: "gis-keyboard",
      email: "gis-keyboard@example.local",
      role: "viewer",
      is_active: true,
      module_accessi: false,
      module_rete: false,
      module_inventario: false,
      module_catasto: false,
      module_utenze: false,
      module_operazioni: false,
      module_riordino: false,
      module_ruolo: false,
      module_presenze: false,
      enabled_modules: ["gis"],
    });
    mocks.getMyPermissions.mockResolvedValue({
      sections: [],
      granted_keys: [],
    });

    render(<HomePage />);

    await screen.findByRole("heading", { name: "GIS Platform" });
    const input = screen.getByPlaceholderText("Ricerca globale…");

    fireEvent.change(input, { target: { value: "GIS Platform · Catalogo" } });
    fireEvent.keyDown(input, { key: "Enter" });
    expect(mocks.push).toHaveBeenCalledWith("/gis/catalogo");

    fireEvent.change(input, { target: { value: "GIS P" } });
    expect(screen.getByRole("button", { name: "GIS Platform · Catalogo" })).toBeInTheDocument();
    fireEvent.keyDown(input, { key: "Escape" });
    expect(screen.queryByRole("button", { name: "GIS Platform · Catalogo" })).not.toBeInTheDocument();

    fireEvent.focus(input);
    fireEvent.change(input, { target: { value: "postgis" } });
    expect(screen.getByRole("button", { name: "GIS Platform · Catalogo" })).toBeInTheDocument();
    fireEvent.mouseDown(input);
    expect(screen.getByRole("button", { name: "GIS Platform · Catalogo" })).toBeInTheDocument();
    fireEvent.mouseDown(document.body);
    expect(screen.queryByRole("button", { name: "GIS Platform · Catalogo" })).not.toBeInTheDocument();
  });

  test("lets admins search across modules and sorts multiple global results", async () => {
    mocks.getCurrentUser.mockResolvedValue({
      id: 7,
      username: "global-admin",
      email: "global-admin@example.local",
      role: "admin",
      is_active: true,
      module_accessi: false,
      module_rete: false,
      module_inventario: false,
      module_catasto: false,
      module_utenze: false,
      module_operazioni: false,
      module_riordino: false,
      module_ruolo: false,
      module_presenze: false,
      enabled_modules: [],
    });
    mocks.getMyPermissions.mockResolvedValue({
      sections: [],
      granted_keys: [],
    });

    render(<HomePage />);

    await screen.findByText("Hub operativo GAIA");
    const input = screen.getByPlaceholderText("Ricerca globale…");

    fireEvent.change(input, { target: { value: "dashboard" } });
    expect(screen.getByRole("button", { name: "Catasto · Dashboard" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Ruolo · Dashboard" })).toBeInTheDocument();

    fireEvent.change(input, { target: { value: "catasto" } });
    expect(screen.getByRole("button", { name: "Catasto · Dashboard" })).toBeInTheDocument();

    fireEvent.change(input, { target: { value: "gis platform · catalogo gis catalogo layer postgis martin" } });
    expect(screen.getByRole("button", { name: "GIS Platform · Catalogo" })).toBeInTheDocument();
  });

  test("shows an empty global search result for routes outside current permissions", async () => {
    mocks.getCurrentUser.mockResolvedValue({
      id: 5,
      username: "gis-only",
      email: "gis-only@example.local",
      role: "viewer",
      is_active: true,
      module_accessi: false,
      module_rete: false,
      module_inventario: false,
      module_catasto: false,
      module_utenze: false,
      module_operazioni: false,
      module_riordino: false,
      module_ruolo: false,
      module_presenze: false,
      enabled_modules: ["gis"],
    });
    mocks.getMyPermissions.mockResolvedValue({
      sections: [],
      granted_keys: [],
    });

    render(<HomePage />);

    await screen.findByRole("heading", { name: "GIS Platform" });
    fireEvent.change(screen.getByPlaceholderText("Ricerca globale…"), { target: { value: "NAS" } });

    expect(screen.getByText("Nessun risultato disponibile per i permessi correnti.")).toBeInTheDocument();
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
