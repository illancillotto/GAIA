import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import HomePage from "@/app/page";

const BOOTSTRAP_TIMEOUT_MS = 8_000;
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
  getRuoloStats: vi.fn(),
  getRuoloStatsAnalytics: vi.fn(),
  catastoGetIndiciOverview: vi.fn(),
  searchOperational: vi.fn(),
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
    mocks.getRuoloStats.mockReset();
    mocks.getRuoloStatsAnalytics.mockReset();
    mocks.catastoGetIndiciOverview.mockReset();
    mocks.searchOperational.mockReset();
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
      module_utenze: true,
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
    mocks.getRuoloStats.mockResolvedValue({ items: [] });
    mocks.getRuoloStatsAnalytics.mockResolvedValue(null);
    mocks.catastoGetIndiciOverview.mockResolvedValue(null);
    mocks.searchOperational.mockResolvedValue({ query: "", items: [], total: 0, modules: [] });
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

    expect(mocks.getCurrentUser).toHaveBeenCalledWith("token", { timeoutMs: BOOTSTRAP_TIMEOUT_MS });
    expect(mocks.getDashboardSummary).toHaveBeenCalledWith("token", { timeoutMs: BOOTSTRAP_TIMEOUT_MS });
    expect(mocks.getMyPermissions).toHaveBeenCalledWith("token", { timeoutMs: BOOTSTRAP_TIMEOUT_MS });
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

  test("focuses the main operational search after loading the home", async () => {
    mocks.getPresenceSummary.mockResolvedValue({
      window_minutes: 15,
      active_users: 0,
      visible_users: 0,
      by_module: [],
      items: [],
    });

    render(<HomePage />);

    const input = await screen.findByPlaceholderText("Cerca utenza, ruolo, catasto o coordinate…");

    expect(document.activeElement).toBe(input);
    fireEvent.keyDown(input, { key: "Enter" });
    expect(mocks.push).not.toHaveBeenCalled();
  });

  test("shows GIS Platform in home and global search for GIS-enabled users", async () => {
    mocks.getCurrentUser.mockResolvedValue({
      id: 2,
      username: "gis-viewer",
      email: "gis-viewer@example.local",
      role: "viewer",
      is_active: true,
      module_accessi: true,
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

    expect(await screen.findByRole("link", { name: "Apri GIS Platform" })).toHaveAttribute("href", "/gis/catalogo");

    fireEvent.change(screen.getByPlaceholderText("Cerca utenza, ruolo, catasto o coordinate…"), { target: { value: "postgis" } });
    fireEvent.click(screen.getByRole("button", { name: "GIS Platform · Catalogo" }));

    expect(mocks.push).toHaveBeenCalledWith("/gis/catalogo");
    expect(mocks.getCatastoDocuments).not.toHaveBeenCalled();
  });

  test("shows role and cadastral metrics in the secondary operational status row", async () => {
    mocks.getCurrentUser.mockResolvedValue({
      id: 11,
      username: "ruolo-admin",
      email: "ruolo-admin@example.local",
      role: "admin",
      is_active: true,
      module_accessi: false,
      module_rete: true,
      module_inventario: false,
      module_catasto: true,
      module_utenze: false,
      module_operazioni: false,
      module_riordino: false,
      module_ruolo: true,
      module_presenze: false,
      enabled_modules: ["accessi", "rete", "catasto", "ruolo", "utenze"],
    });
    mocks.getDashboardSummary.mockResolvedValue({
      nas_users: 10,
      nas_groups: 5,
      shares: 3,
      reviews: 0,
      snapshots: 0,
      sync_runs: 0,
    });
    mocks.getUtenzeStats.mockResolvedValue({
      total_subjects: 1240,
      total_persons: 1100,
      total_companies: 100,
      total_unknown: 40,
      total_documents: 0,
      requires_review: 17,
      active_subjects: 1212,
      inactive_subjects: 28,
      documents_unclassified: 0,
      deceased_updates_last_24h: 0,
      deceased_updates_current_month: 0,
      deceased_updates_current_year: 0,
      by_letter: {},
    });
    mocks.getMyPermissions.mockResolvedValue({
      sections: [],
      granted_keys: [],
    });
    mocks.getCatastoDocuments.mockResolvedValue([{}]);
    mocks.getRuoloStats.mockResolvedValue({
      items: [
        {
          anno_tributario: 2026,
          total_avvisi: 123,
          avvisi_collegati: 100,
          avvisi_non_collegati: 23,
          totale_0648: 100000,
          totale_0985: 250000,
          totale_0668: 106789,
          totale_euro: 456789,
        },
      ],
    });
    mocks.getRuoloStatsAnalytics.mockResolvedValue({
      anno_tributario: 2026,
      particelle_summary: {
        anno_tributario: 2026,
        total_particelle: 44,
        collegate_catasto: 40,
        non_collegate_catasto: 4,
        soppresse_ade: 0,
      },
      tributi_breakdown: [],
      match_status_breakdown: [],
      match_reason_breakdown: [],
      distretto_breakdown: [{ key: "1", label: "Distretto 1", count: 10 }],
      coltura_breakdown: [],
      comuni: [],
    });
    mocks.catastoGetIndiciOverview.mockResolvedValue({
      anno_riferimento: 2026,
      total_distretti: 37,
      total_particelle: 200,
      available_colture: [],
      items: [
        {
          indice_key: "alta_pressione",
          superficie_irrigata_ha: "12.5",
          distretti: [
            { num_distretto: "1" },
            { num_distretto: "01" },
            { num_distretto: "FD" },
          ],
          distretti_analytics: [
            {
              key: "01",
              label: "01 · Distretto",
              particelle_count: 0,
              ruolo_particelle_count: 5,
              particelle_con_anagrafica_count: 0,
              superficie_irrigata_ha: "0",
              importo_stimato: "0",
              importo_ruolo: "0",
              importo_ruolo_manutenzione: "0",
              importo_ruolo_irrigazione: "0",
              importo_ruolo_istituzionale: "0",
            },
          ],
        },
        {
          indice_key: "bassa_pressione",
          superficie_irrigata_ha: "3.25",
          distretti: [
            { num_distretto: "2" },
            { num_distretto: "1" },
            { num_distretto: null },
          ],
          distretti_analytics: [],
        },
        {
          indice_key: "non_classificato",
          superficie_irrigata_ha: "0",
          distretti: [
            { num_distretto: "FD" },
            { num_distretto: "F.D." },
            { num_distretto: "Fuori distretto" },
          ],
          distretti_analytics: [
            {
              key: "FD",
              label: "FD · Fuori distretto",
              particelle_count: 0,
              ruolo_particelle_count: 7,
              particelle_con_anagrafica_count: 0,
              superficie_irrigata_ha: "0",
              importo_stimato: "0",
              importo_ruolo: "0",
              importo_ruolo_manutenzione: "0",
              importo_ruolo_irrigazione: "0",
              importo_ruolo_istituzionale: "0",
            },
            {
              key: "F.D.",
              label: "Fuori distretto legacy",
              particelle_count: 0,
              ruolo_particelle_count: 2,
              particelle_con_anagrafica_count: 0,
              superficie_irrigata_ha: "0",
              importo_stimato: "0",
              importo_ruolo: "0",
              importo_ruolo_manutenzione: "0",
              importo_ruolo_irrigazione: "0",
              importo_ruolo_istituzionale: "0",
            },
          ],
        },
      ],
      ruolo_reconciliation: {
        particelle_ruolo_totali_count: 88,
        importo_ruolo_totale: "456789",
      },
    });

    render(<HomePage />);

    await waitFor(() => {
      expect(mocks.getRuoloStatsAnalytics).toHaveBeenCalledWith("token", 2026);
    });
    expect(mocks.catastoGetIndiciOverview).toHaveBeenCalledWith("token", 2026);
    expect(screen.getByText("Stato operativo")).toBeInTheDocument();
    expect(screen.getByText("Utenti in anagrafica")).toBeInTheDocument();
    expect(await screen.findByTitle(/attivi nel modulo Utenze/)).toHaveTextContent(/1[.,]?240/);
    expect(screen.getByText("Anagrafiche anomale")).toBeInTheDocument();
    expect(screen.getByText("17")).toBeInTheDocument();
    expect(screen.getByText("Ruoli caricati")).toBeInTheDocument();
    expect(screen.getByText("Particelle a ruolo")).toBeInTheDocument();
    expect(screen.getByText("Particelle FD")).toBeInTheDocument();
    expect(screen.getByTitle("Particelle a ruolo agganciate a FD / fuori distretto")).toHaveTextContent("9");
    expect(screen.getByText("Distretti")).toBeInTheDocument();
    expect(screen.getByTitle("Distretti ruolo effettivi, esclusi FD e fuori distretto")).toHaveTextContent("2");
    expect(screen.getByText("Dati NAS")).toBeInTheDocument();
    expect(screen.getByTitle("10 utenti, 5 gruppi, 3 cartelle")).toHaveTextContent("18");
    expect(screen.queryByText("Utenti a ruolo")).not.toBeInTheDocument();
    expect(screen.queryByText("Ettari a ruolo")).not.toBeInTheDocument();
    expect(screen.queryByText("Importo ruolo")).not.toBeInTheDocument();
    expect(screen.queryByText("Dispositivi connessi")).not.toBeInTheDocument();
    expect(screen.queryByText("Alert rete aperti")).not.toBeInTheDocument();
  });

  test("counts only operational role districts when cadastral overview is unavailable", async () => {
    mocks.getCurrentUser.mockResolvedValue({
      id: 12,
      username: "ruolo-only",
      email: "ruolo-only@example.local",
      role: "viewer",
      is_active: true,
      module_accessi: false,
      module_rete: false,
      module_inventario: false,
      module_catasto: false,
      module_utenze: false,
      module_operazioni: false,
      module_riordino: false,
      module_ruolo: true,
      module_presenze: false,
      enabled_modules: ["ruolo"],
    });
    mocks.getMyPermissions.mockResolvedValue({ sections: [], granted_keys: [] });
    mocks.getRuoloStats.mockResolvedValue({
      items: [
        {
          anno_tributario: 2026,
          total_avvisi: 1,
          avvisi_collegati: 0,
          avvisi_non_collegati: 1,
          totale_0648: null,
          totale_0985: null,
          totale_0668: null,
          totale_euro: null,
        },
      ],
    });
    mocks.getRuoloStatsAnalytics.mockResolvedValue({
      anno_tributario: 2026,
      particelle_summary: {
        anno_tributario: 2026,
        total_particelle: 4,
        collegate_catasto: 0,
        non_collegate_catasto: 4,
        soppresse_ade: 0,
      },
      tributi_breakdown: [],
      match_status_breakdown: [],
      match_reason_breakdown: [],
      distretto_breakdown: [
        { key: "1", label: "Distretto 1", count: 2 },
        { key: "FD", label: "Fuori distretto", count: 1 },
        { key: "F.D.", label: "Fuori distretto legacy", count: 2 },
        { key: "N/D", label: "Non disponibile", count: 1 },
      ],
      coltura_breakdown: [],
      comuni: [],
    });

    render(<HomePage />);

    expect(await screen.findByTitle("Distretti ruolo effettivi, esclusi FD e fuori distretto")).toHaveTextContent("1");
    expect(screen.getByTitle("Particelle a ruolo agganciate a FD / fuori distretto")).toHaveTextContent("3");
    expect(mocks.catastoGetIndiciOverview).not.toHaveBeenCalled();
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
      module_ruolo: true,
      module_presenze: false,
      enabled_modules: ["accessi", "rete", "catasto", "utenze", "ruolo"],
    });
    mocks.getDashboardSummary.mockRejectedValue(new Error("dashboard down"));
    mocks.getUtenzeStats.mockRejectedValue(new Error("utenze down"));
    mocks.getPresenceSummary.mockRejectedValue(new Error("presence down"));
    mocks.getRuoloStats.mockRejectedValue(new Error("ruolo stats down"));

    render(<HomePage />);

    expect(await screen.findByText("Hub operativo GAIA")).toBeInTheDocument();
    expect(warnSpy).toHaveBeenCalledWith(
      "Home dashboard loaded with partial module data",
      expect.objectContaining({
        dashboardError: expect.any(Error),
        utenzeError: expect.any(Error),
        presenceSummaryError: expect.any(Error),
        ruoloStatsError: expect.any(Error),
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
      module_ruolo: true,
      module_presenze: false,
      enabled_modules: ["accessi", "rete", "catasto", "utenze", "ruolo"],
    };
    mocks.getCurrentUser.mockResolvedValue(allModuleAdmin);
    mocks.getPresenceSummary.mockRejectedValueOnce(new Error("presence down"));

    const firstRender = render(<HomePage />);

    expect(await screen.findByText("Hub operativo GAIA")).toBeInTheDocument();
    expect(warnSpy).toHaveBeenLastCalledWith(
      "Home dashboard loaded with partial module data",
      expect.objectContaining({
        dashboardError: null,
        presenceSummaryError: expect.any(Error),
        ruoloStatsError: null,
        ruoloAnalyticsError: null,
        catastoIndiciOverviewError: null,
      }),
    );

    firstRender.unmount();
    warnSpy.mockClear();
    mocks.getCurrentUser.mockResolvedValue(allModuleAdmin);
    mocks.getRuoloStats.mockResolvedValueOnce({
      items: [
        {
          anno_tributario: 2026,
          total_avvisi: 1,
          avvisi_collegati: 0,
          avvisi_non_collegati: 1,
          totale_0648: null,
          totale_0985: null,
          totale_0668: null,
          totale_euro: null,
        },
      ],
    });
    mocks.getRuoloStatsAnalytics.mockRejectedValueOnce(new Error("analytics down"));
    mocks.catastoGetIndiciOverview.mockRejectedValueOnce(new Error("indici down"));
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
        ruoloAnalyticsError: expect.any(Error),
        catastoIndiciOverviewError: expect.any(Error),
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

    await screen.findByText("Hub operativo GAIA");
    const input = screen.getByPlaceholderText("Cerca utenza, ruolo, catasto o coordinate…");

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

  test("opens Catasto GIS when the home search receives latitude and longitude", async () => {
    mocks.getCurrentUser.mockResolvedValue({
      id: 9,
      username: "catasto-coordinate",
      email: "catasto-coordinate@example.local",
      role: "viewer",
      is_active: true,
      module_accessi: false,
      module_rete: false,
      module_inventario: false,
      module_catasto: true,
      module_utenze: false,
      module_operazioni: false,
      module_riordino: false,
      module_ruolo: false,
      module_presenze: false,
      enabled_modules: ["catasto"],
    });
    mocks.getMyPermissions.mockResolvedValue({
      sections: [],
      granted_keys: [],
    });

    render(<HomePage />);

    await screen.findByText("Hub operativo GAIA");
    const input = screen.getByPlaceholderText("Cerca utenza, ruolo, catasto o coordinate…");

    fireEvent.change(input, { target: { value: "39,9042 8,5917" } });
    expect(screen.getByRole("button", { name: "Catasto · GIS coordinate" })).toBeInTheDocument();
    fireEvent.keyDown(input, { key: "Enter" });

    expect(mocks.push).toHaveBeenCalledWith("/catasto/gis?coordinate=39.904200%2C+8.591700");

    mocks.push.mockClear();
    fireEvent.change(input, { target: { value: "39°54'15\"N 8°35'30\"E" } });
    expect(screen.getByRole("button", { name: "Catasto · GIS coordinate" })).toBeInTheDocument();
    fireEvent.keyDown(input, { key: "Enter" });

    expect(mocks.push).toHaveBeenCalledWith("/catasto/gis?coordinate=39.904167%2C+8.591667");
  });

  test("shows operational search results before shortcut results", async () => {
    mocks.getCurrentUser.mockResolvedValue({
      id: 8,
      username: "domain-admin",
      email: "domain-admin@example.local",
      role: "admin",
      is_active: true,
      module_accessi: false,
      module_rete: false,
      module_inventario: false,
      module_catasto: true,
      module_utenze: true,
      module_operazioni: false,
      module_riordino: false,
      module_ruolo: true,
      module_presenze: false,
      enabled_modules: ["catasto", "utenze", "ruolo"],
    });
    mocks.getMyPermissions.mockResolvedValue({ sections: [], granted_keys: [] });
    mocks.searchOperational.mockResolvedValue({
      query: "rossi",
      total: 1,
      modules: ["utenze", "ruolo", "catasto"],
      items: [
        {
          id: "subject-1",
          module: "utenze",
          type: "subject_person",
          title: "Rossi Mario",
          subtitle: "Utenze · Persona",
          description: "RSSMRA80A01H501U · Oristano",
          href: "/utenze/subject-1",
          score: 86,
          metadata: {},
        },
        {
          id: "legacy-1",
          module: "legacy",
          type: "legacy",
          title: "Risultato legacy",
          subtitle: "Archivio esterno",
          description: null,
          href: "/legacy/1",
          score: 40,
          metadata: {},
        },
      ],
    });

    render(<HomePage />);

    await screen.findByText("Hub operativo GAIA");
    const input = screen.getByPlaceholderText("Cerca utenza, ruolo, catasto o coordinate…");
    fireEvent.change(input, { target: { value: "rossi" } });

    expect(screen.getByText("Ricerca operativa in corso…")).toBeInTheDocument();
    await waitFor(() => {
      expect(mocks.searchOperational).toHaveBeenCalledWith("token", "rossi", { limit: 8 });
    });
    const result = await screen.findByRole("button", { name: /Rossi Mario/i });
    expect(screen.getByRole("button", { name: /Vedi tutti i risultati/i })).toBeInTheDocument();
    fireEvent.click(result);

    expect(mocks.push).toHaveBeenCalledWith("/utenze/subject-1");
  });

  test("shows operational search errors while keeping shortcut fallback", async () => {
    mocks.getCurrentUser.mockResolvedValue({
      id: 9,
      username: "fallback-admin",
      email: "fallback-admin@example.local",
      role: "admin",
      is_active: true,
      module_accessi: false,
      module_rete: false,
      module_inventario: false,
      module_catasto: true,
      module_utenze: false,
      module_operazioni: false,
      module_riordino: false,
      module_ruolo: false,
      module_presenze: false,
      enabled_modules: ["catasto"],
    });
    mocks.getMyPermissions.mockResolvedValue({ sections: [], granted_keys: [] });
    mocks.searchOperational.mockRejectedValue(new Error("Backend ricerca non disponibile"));

    render(<HomePage />);

    await screen.findByText("Hub operativo GAIA");
    fireEvent.change(screen.getByPlaceholderText("Cerca utenza, ruolo, catasto o coordinate…"), { target: { value: "catasto" } });

    expect(await screen.findByText("Backend ricerca non disponibile")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Catasto · Dashboard" })).toBeInTheDocument();
  });

  test("normalizes non-error operational search failures", async () => {
    mocks.getCurrentUser.mockResolvedValue({
      id: 10,
      username: "string-error-admin",
      email: "string-error-admin@example.local",
      role: "admin",
      is_active: true,
      module_accessi: false,
      module_rete: false,
      module_inventario: false,
      module_catasto: true,
      module_utenze: false,
      module_operazioni: false,
      module_riordino: false,
      module_ruolo: false,
      module_presenze: false,
      enabled_modules: ["catasto"],
    });
    mocks.getMyPermissions.mockResolvedValue({ sections: [], granted_keys: [] });
    mocks.searchOperational.mockRejectedValue("offline");

    render(<HomePage />);

    await screen.findByText("Hub operativo GAIA");
    fireEvent.change(screen.getByPlaceholderText("Cerca utenza, ruolo, catasto o coordinate…"), { target: { value: "particella" } });

    expect(await screen.findByText("Ricerca non disponibile")).toBeInTheDocument();
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
    const input = screen.getByPlaceholderText("Cerca utenza, ruolo, catasto o coordinate…");

    fireEvent.change(input, { target: { value: "dashboard" } });
    expect(screen.getByRole("button", { name: "Catasto · Dashboard" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Ruolo · Dashboard" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Vedi tutti i risultati/i }));
    expect(screen.getByRole("dialog", { name: /Risultati per “dashboard”/i })).toBeInTheDocument();
    expect(mocks.push).not.toHaveBeenCalledWith("/search?q=dashboard");

    fireEvent.click(screen.getByRole("button", { name: "Ruolo · Dashboard" }));
    expect(mocks.push).toHaveBeenCalledWith("/ruolo");
    mocks.push.mockClear();

    fireEvent.focus(input);
    fireEvent.click(screen.getByRole("button", { name: /Vedi tutti i risultati/i }));
    expect(screen.getByRole("dialog", { name: /Risultati per “dashboard”/i })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Chiudi modal ricerca" }));
    expect(screen.queryByRole("dialog", { name: /Risultati per “dashboard”/i })).not.toBeInTheDocument();

    fireEvent.change(input, { target: { value: "dashboard" } });
    fireEvent.keyDown(input, { key: "Enter" });
    expect(screen.getByRole("dialog", { name: /Risultati per “dashboard”/i })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Vista estesa" }));
    expect(mocks.push).toHaveBeenCalledWith("/search?q=dashboard");

    fireEvent.change(input, { target: { value: "catasto" } });
    expect(screen.getByRole("button", { name: "Catasto · Dashboard" })).toBeInTheDocument();

    fireEvent.change(input, { target: { value: "gis platform · catalogo gis catalogo layer postgis martin" } });
    expect(screen.getByRole("button", { name: "GIS Platform · Catalogo" })).toBeInTheDocument();
  });

  test("opens the home results modal with operational results and navigates from it", async () => {
    mocks.getCurrentUser.mockResolvedValue({
      id: 13,
      username: "modal-admin",
      email: "modal-admin@example.local",
      role: "admin",
      is_active: true,
      module_accessi: false,
      module_rete: false,
      module_inventario: false,
      module_catasto: true,
      module_utenze: true,
      module_operazioni: false,
      module_riordino: false,
      module_ruolo: true,
      module_presenze: false,
      enabled_modules: ["catasto", "utenze", "ruolo"],
    });
    mocks.getMyPermissions.mockResolvedValue({ sections: [], granted_keys: [] });
    mocks.searchOperational.mockResolvedValue({
      query: "rossi",
      total: 2,
      modules: ["utenze", "catasto", "legacy"],
      items: [
        {
          id: "subject-1",
          module: "utenze",
          type: "subject_person",
          title: "Rossi Mario",
          subtitle: "Utenze · Persona",
          description: "RSSMRA80A01H501U",
          href: "/utenze/subject-1",
          score: 90,
          metadata: {},
        },
        {
          id: "parcel-1",
          module: "catasto",
          type: "particella",
          title: "Foglio 1 particella 2",
          subtitle: "Catasto · Particella",
          description: null,
          href: "/catasto/particelle/parcel-1",
          score: 80,
          metadata: {},
        },
        {
          id: "legacy-1",
          module: "legacy",
          type: "legacy",
          title: "Archivio legacy",
          subtitle: "Archivio esterno",
          description: null,
          href: "/legacy/1",
          score: 10,
          metadata: {},
        },
      ],
    });

    render(<HomePage />);

    await screen.findByText("Hub operativo GAIA");
    const input = screen.getByPlaceholderText("Cerca utenza, ruolo, catasto o coordinate…");
    fireEvent.change(input, { target: { value: "rossi" } });

    await waitFor(() => expect(mocks.searchOperational).toHaveBeenCalledWith("token", "rossi", { limit: 8 }));
    fireEvent.click(screen.getByRole("button", { name: /Vedi tutti i risultati/i }));

    expect(screen.getByRole("dialog", { name: /Risultati per “rossi”/i })).toBeInTheDocument();
    await waitFor(() => expect(mocks.searchOperational).toHaveBeenCalledWith("token", "rossi", { limit: 30 }));
    expect(screen.getAllByText("Utenze").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Catasto").length).toBeGreaterThan(0);
    expect(screen.getByText("legacy")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Foglio 1 particella 2/i }));
    expect(mocks.push).toHaveBeenCalledWith("/catasto/particelle/parcel-1");
  });

  test("shows empty and error states inside the home results modal", async () => {
    mocks.getCurrentUser.mockResolvedValue({
      id: 14,
      username: "modal-empty-admin",
      email: "modal-empty-admin@example.local",
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
    mocks.getMyPermissions.mockResolvedValue({ sections: [], granted_keys: [] });

    render(<HomePage />);

    await screen.findByText("Hub operativo GAIA");
    const input = screen.getByPlaceholderText("Cerca utenza, ruolo, catasto o coordinate…");
    fireEvent.change(input, { target: { value: "qq" } });
    await waitFor(() => expect(mocks.searchOperational).toHaveBeenCalledWith("token", "qq", { limit: 8 }));

    fireEvent.click(screen.getByRole("button", { name: /Vedi tutti i risultati/i }));
    expect(screen.getByRole("dialog", { name: /Risultati per “qq”/i })).toBeInTheDocument();
    await waitFor(() => expect(mocks.searchOperational).toHaveBeenCalledWith("token", "qq", { limit: 30 }));
    await waitFor(() => {
      expect(screen.getAllByText("Nessun risultato disponibile per i permessi correnti.").length).toBeGreaterThan(0);
    });

    fireEvent.click(screen.getByRole("button", { name: "Chiudi risultati ricerca" }));
    mocks.searchOperational.mockRejectedValue(new Error("Backend ricerca non disponibile"));
    fireEvent.change(input, { target: { value: "qx" } });
    await screen.findByText("Backend ricerca non disponibile");

    fireEvent.click(screen.getByRole("button", { name: /Vedi tutti i risultati/i }));
    expect(screen.getByRole("dialog", { name: /Risultati per “qx”/i })).toBeInTheDocument();
    expect(await screen.findByText("Backend ricerca non disponibile")).toBeInTheDocument();
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

    await screen.findByRole("link", { name: "Apri GIS Platform" });
    fireEvent.change(screen.getByPlaceholderText("Cerca utenza, ruolo, catasto o coordinate…"), { target: { value: "NAS" } });

    await waitFor(() => {
      expect(screen.getByText("Nessun risultato disponibile per i permessi correnti.")).toBeInTheDocument();
    });
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
