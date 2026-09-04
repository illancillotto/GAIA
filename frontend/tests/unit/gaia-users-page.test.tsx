import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import GaiaUsersPage from "@/app/gaia/users/page";

const mocks = vi.hoisted(() => ({
  getStoredAccessToken: vi.fn(),
  getCurrentUser: vi.fn(),
  getPresenceSummary: vi.fn(),
  listAllApplicationUsers: vi.fn(),
  listSectionCatalog: vi.fn(),
  createApplicationUser: vi.fn(),
  updateApplicationUser: vi.fn(),
  sendApplicationUserInvite: vi.fn(),
  getApplicationUserPermissions: vi.fn(),
  updateApplicationUserPermissions: vi.fn(),
  deleteApplicationUserPermissionOverride: vi.fn(),
  clearPresenceAction: vi.fn(),
  recordPresenceAction: vi.fn(),
}));

vi.mock("@/lib/auth", () => ({
  getStoredAccessToken: mocks.getStoredAccessToken,
}));

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    getCurrentUser: mocks.getCurrentUser,
    getPresenceSummary: mocks.getPresenceSummary,
    listAllApplicationUsers: mocks.listAllApplicationUsers,
    listSectionCatalog: mocks.listSectionCatalog,
    createApplicationUser: mocks.createApplicationUser,
    updateApplicationUser: mocks.updateApplicationUser,
    sendApplicationUserInvite: mocks.sendApplicationUserInvite,
    getApplicationUserPermissions: mocks.getApplicationUserPermissions,
    updateApplicationUserPermissions: mocks.updateApplicationUserPermissions,
    deleteApplicationUserPermissionOverride: mocks.deleteApplicationUserPermissionOverride,
  };
});

vi.mock("@/lib/presence-actions", () => ({
  clearPresenceAction: mocks.clearPresenceAction,
  recordPresenceAction: mocks.recordPresenceAction,
}));

vi.mock("@/components/app/protected-page", () => ({
  ProtectedPage: ({ children, title }: { children: ReactNode; title: string }) => (
    <div>
      <h1>{title}</h1>
      {children}
    </div>
  ),
}));

vi.mock("@/components/table/data-table", () => ({
  DataTable: ({
    columns,
    data,
    emptyTitle,
    onRowClick,
  }: {
    columns?: Array<{
      header?: string;
      accessorKey?: string;
      cell?: (context: { row: { original: Record<string, unknown> } }) => ReactNode;
    }>;
    data: Array<{ id: number; username: string }>;
    emptyTitle?: string;
    onRowClick?: (row: { id: number }) => void;
  }) => (
    <div>
      {data.length === 0 ? <p>{emptyTitle}</p> : null}
      {data.map((row) => (
        <div key={row.id}>
          <button type="button" onClick={() => onRowClick?.(row)}>
            {row.username}
          </button>
          <div>
            {columns?.map((column, index) => (
              <div key={`${row.id}-${column.accessorKey ?? index}`}>
                {column.cell ? column.cell({ row: { original: row as unknown as Record<string, unknown> } }) : null}
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  ),
}));

function buildCurrentUser() {
  return {
    id: 1,
    username: "admin",
    email: "admin@example.local",
    role: "admin",
    is_active: true,
    module_accessi: true,
    module_rete: false,
    module_inventario: false,
    module_gis: false,
    module_catasto: false,
    module_utenze: false,
    module_operazioni: false,
    module_riordino: false,
    module_ruolo: false,
    module_presenze: false,
    enabled_modules: ["accessi"],
  };
}

function buildUser(overrides: Partial<{
  id: number;
  username: string;
  email: string;
  role: string;
  is_active: boolean;
  module_accessi: boolean;
  module_operazioni: boolean;
  module_rete: boolean;
  module_inventario: boolean;
  module_gis: boolean;
  module_catasto: boolean;
  module_utenze: boolean;
  module_riordino: boolean;
  module_ruolo: boolean;
  module_presenze: boolean;
  login_count: number;
  last_login_at: string | null;
  last_login_ip: string | null;
  enabled_modules: string[];
  gate_mobile_console: {
    operator_id: string;
    enabled: boolean;
    role: string | null;
  } | null;
}> = {}) {
  return {
    id: 7,
    username: "mrossi",
    email: "mrossi@example.local",
    role: "viewer",
    is_active: true,
    module_accessi: false,
    module_rete: false,
    module_inventario: false,
    module_gis: false,
    module_catasto: false,
    module_utenze: false,
    module_operazioni: false,
    module_riordino: false,
    module_ruolo: false,
    module_presenze: false,
    login_count: 0,
    last_login_at: null,
    last_login_ip: null,
    enabled_modules: [],
    gate_mobile_console: null,
    created_at: "2026-06-23T08:00:00Z",
    updated_at: "2026-06-23T08:00:00Z",
    ...overrides,
  };
}

function buildSection(overrides: Partial<{
  id: number;
  module: string;
  key: string;
  label: string;
  description: string | null;
  min_role: string;
  is_active: boolean;
  sort_order: number;
}> = {}) {
  return {
    id: 101,
    module: "accessi",
    key: "accessi.users",
    label: "Utenti",
    description: "Gestione utenti",
    min_role: "admin",
    is_active: true,
    sort_order: 1,
    created_at: "2026-06-23T08:00:00Z",
    updated_at: "2026-06-23T08:00:00Z",
    ...overrides,
  };
}

function buildPermissionsView() {
  return {
    user_id: 7,
    username: "mrossi",
    role: "viewer",
    resolved: [
      {
        section_key: "accessi.users",
        section_label: "Utenti",
        module: "accessi",
        is_granted: true,
        source: "user_override",
      },
      {
        section_key: "accessi.audit",
        section_label: "Audit",
        module: "accessi",
        is_granted: false,
        source: "denied",
      },
      {
        section_key: "presenze.dashboard",
        section_label: "Giornaliere dashboard",
        module: "presenze",
        is_granted: true,
        source: "min_role",
      },
    ],
    overrides: [
      {
        id: 501,
        user_id: 7,
        section_id: 101,
        is_granted: true,
        granted_by_id: 1,
        created_at: "2026-06-23T08:00:00Z",
        updated_at: "2026-06-23T08:00:00Z",
      },
    ],
  };
}

function createDeferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((promiseResolve, promiseReject) => {
    resolve = promiseResolve;
    reject = promiseReject;
  });

  return { promise, resolve, reject };
}

function getModuleCheckbox(label: string): HTMLInputElement {
  const textNode = screen.getAllByText(label).find((node) => node.closest(".rounded-\\[22px\\]"));
  expect(textNode).toBeTruthy();
  const card = textNode?.closest(".rounded-\\[22px\\]");
  expect(card).toBeTruthy();
  const checkbox = card?.querySelector('input[type="checkbox"]');
  expect(checkbox).toBeInstanceOf(HTMLInputElement);
  return checkbox as HTMLInputElement;
}

describe("Gaia users page", () => {
  beforeEach(() => {
    vi.useRealTimers();
    mocks.getStoredAccessToken.mockReset();
    mocks.getCurrentUser.mockReset();
    mocks.getPresenceSummary.mockReset();
    mocks.listAllApplicationUsers.mockReset();
    mocks.listSectionCatalog.mockReset();
    mocks.createApplicationUser.mockReset();
    mocks.updateApplicationUser.mockReset();
    mocks.sendApplicationUserInvite.mockReset();
    mocks.getApplicationUserPermissions.mockReset();
    mocks.updateApplicationUserPermissions.mockReset();
    mocks.deleteApplicationUserPermissionOverride.mockReset();
    mocks.clearPresenceAction.mockReset();
    mocks.recordPresenceAction.mockReset();

    mocks.getStoredAccessToken.mockReturnValue("token");
    mocks.getCurrentUser.mockResolvedValue(buildCurrentUser());
    mocks.getPresenceSummary.mockResolvedValue({
      window_minutes: 15,
      active_users: 0,
      visible_users: 0,
      items: [],
      by_module: [],
    });
    mocks.listSectionCatalog.mockResolvedValue([]);
    mocks.createApplicationUser.mockImplementation(async (_token: string, payload: { username: string; email: string; role: string }) =>
      buildUser({ id: 99, username: payload.username || "nuovo", email: payload.email || "nuovo@example.local", role: payload.role }),
    );
    mocks.updateApplicationUser.mockResolvedValue(buildUser());
    mocks.sendApplicationUserInvite.mockResolvedValue({
      user_id: 7,
      email: "mrossi@example.local",
      expires_at: "2026-06-24T08:00:00Z",
      activation_url: "https://gaia.local/activate",
      activation_url_path: "/activate",
      email_sent: true,
    });
    mocks.getApplicationUserPermissions.mockResolvedValue(buildPermissionsView());
    mocks.updateApplicationUserPermissions.mockResolvedValue(buildPermissionsView());
    mocks.deleteApplicationUserPermissionOverride.mockResolvedValue(undefined);
    Element.prototype.scrollIntoView = vi.fn();
  });

  test("does not preselect NAS Control or Operazioni for a new user", async () => {
    mocks.listAllApplicationUsers.mockResolvedValue([]);

    render(<GaiaUsersPage />);

    await screen.findByText("Nuovo utente GAIA");

    expect(getModuleCheckbox("NAS Control").checked).toBe(false);
    expect(getModuleCheckbox("Operazioni").checked).toBe(false);
  });

  test("handles missing token, denied access and load failures", async () => {
    mocks.getStoredAccessToken.mockReturnValueOnce(null);
    const missingTokenView = render(<GaiaUsersPage />);
    expect(await screen.findByText("Nuovo utente GAIA")).toBeInTheDocument();
    expect(mocks.getCurrentUser).not.toHaveBeenCalled();
    missingTokenView.unmount();

    mocks.getCurrentUser.mockResolvedValueOnce({ ...buildCurrentUser(), role: "viewer", enabled_modules: [] });
    const deniedView = render(<GaiaUsersPage />);
    await screen.findAllByText("Directory utenti applicativi");
    expect(mocks.listAllApplicationUsers).not.toHaveBeenCalled();
    deniedView.unmount();

    mocks.getCurrentUser.mockRejectedValueOnce(new Error("Backend non disponibile"));
    const loadFailureView = render(<GaiaUsersPage />);
    expect(await screen.findByText("Backend non disponibile")).toBeInTheDocument();
    loadFailureView.unmount();

    mocks.getCurrentUser.mockRejectedValueOnce("boom");
    render(<GaiaUsersPage />);
    expect(await screen.findByText("Errore caricamento utenti GAIA")).toBeInTheDocument();
  });

  test("auto-dismisses toast notifications after the timeout", async () => {
    vi.useFakeTimers();
    mocks.getCurrentUser.mockRejectedValueOnce(new Error("Backend non disponibile"));

    render(<GaiaUsersPage />);

    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });
    expect(screen.getByText("Backend non disponibile")).toBeInTheDocument();

    await act(async () => {
      vi.advanceTimersByTime(3500);
    });

    expect(screen.queryByText("Backend non disponibile")).not.toBeInTheDocument();
  });

  test("renders mixed users, table cells and filters", async () => {
    mocks.listAllApplicationUsers.mockResolvedValue([
      buildUser({
        id: 8,
        username: "super-admin",
        email: "super@example.local",
        role: "super_admin",
        module_accessi: true,
        module_rete: true,
        module_inventario: true,
        module_gis: true,
        module_catasto: true,
        module_utenze: true,
        module_operazioni: true,
        module_riordino: true,
        module_ruolo: true,
        module_presenze: true,
        last_login_at: "2026-06-29T09:30:00Z",
        last_login_ip: "10.0.0.8",
        enabled_modules: ["accessi", "rete", "inventario", "catasto", "utenze", "operazioni", "riordino", "ruolo", "presenze"],
      }),
      buildUser({
        id: 9,
        username: "admin-inattivo",
        email: "admin-inattivo@example.local",
        role: "admin",
        is_active: false,
        module_accessi: true,
        login_count: 3,
        enabled_modules: ["accessi"],
      }),
      buildUser({
        id: 10,
        username: "operatore-bg",
        email: "operatore-bg@example.local",
        role: "operator",
        module_operazioni: true,
        enabled_modules: ["operazioni"],
      }),
      buildUser({
        id: 11,
        username: "ruolo-custom",
        email: "ruolo-custom@example.local",
        role: "custom_role",
      }),
    ]);
    mocks.getPresenceSummary.mockResolvedValue({
      window_minutes: 15,
      active_users: 2,
      visible_users: 1,
      by_module: [{ module_key: "operazioni", count: 1 }],
      items: [
        {
          user_id: 8,
          username: "super-admin",
          full_name: null,
          role: "super_admin",
          module_key: "accessi",
          route_label: null,
          action_label: null,
          path: "/gaia/users",
          visible: true,
          last_seen_at: "2026-06-29T10:00:00Z",
          minutes_since_last_seen: 0,
          last_login_at: null,
          recent_routes: [],
          recent_actions: [],
        },
        {
          user_id: 10,
          username: "operatore-bg",
          full_name: null,
          role: "operator",
          module_key: null,
          route_label: null,
          action_label: null,
          path: "",
          visible: false,
          last_seen_at: "2026-06-29T09:55:00Z",
          minutes_since_last_seen: 6,
          last_login_at: null,
          recent_routes: [],
          recent_actions: [],
        },
      ],
    });

    render(<GaiaUsersPage />);

    expect((await screen.findAllByText("super-admin")).length).toBeGreaterThan(0);
    expect(screen.getAllByText("Super Admin").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Admin").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Inattivo").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Attivo adesso").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Attivo 6 min fa").length).toBeGreaterThan(0);
    expect(screen.getAllByText("In background").length).toBeGreaterThan(0);
    expect(screen.getAllByText("10 moduli abilitati").length).toBeGreaterThan(0);
    expect(screen.getAllByText("custom_role").length).toBeGreaterThan(0);

    fireEvent.change(screen.getByLabelText("Stato"), { target: { value: "active" } });
    await waitFor(() => expect(screen.getByText("Stato: attivi")).toBeInTheDocument());
    fireEvent.change(screen.getByLabelText("Stato"), { target: { value: "inactive" } });
    await waitFor(() => expect(screen.getByText("Stato: inattivi")).toBeInTheDocument());
    fireEvent.change(screen.getByLabelText("Stato"), { target: { value: "all" } });

    fireEvent.change(screen.getByPlaceholderText("Es. admin, maria.rossi, operazioni, dashboard..."), {
      target: { value: "operazioni" },
    });
    await waitFor(() => expect(screen.getByText("Ricerca: operazioni")).toBeInTheDocument());

    fireEvent.change(screen.getAllByLabelText("Ruolo")[0], { target: { value: "admin" } });
    await waitFor(() => expect(screen.getByText("Ruolo: Admin")).toBeInTheDocument());

    fireEvent.change(screen.getByLabelText("Stato"), { target: { value: "inactive" } });
    await waitFor(() => expect(screen.getByText("Stato: inattivi")).toBeInTheDocument());

    fireEvent.click(screen.getByRole("button", { name: "Reset filtri" }));
    await waitFor(() => expect(screen.queryByText("Ricerca: operazioni")).not.toBeInTheDocument());
  });

  test("shows GIS Platform module in metrics, rows and edit form", async () => {
    mocks.listAllApplicationUsers.mockResolvedValue([
      buildUser({
        username: "utente-gis",
        module_gis: true,
        enabled_modules: ["gis"],
      }),
    ]);

    render(<GaiaUsersPage />);

    expect((await screen.findAllByText("utente-gis")).length).toBeGreaterThan(0);
    expect(screen.getAllByText("GIS Platform").length).toBeGreaterThan(0);
    expect(screen.getByText("Utenti con modulo GIS abilitato")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "utente-gis" }));

    await waitFor(() => {
      expect(screen.getByText("Modifica utente GAIA")).toBeInTheDocument();
    });
    expect(getModuleCheckbox("GIS Platform").checked).toBe(true);
  });

  test("creates a user, sends activation mail and opens the created account", async () => {
    const createdUser = buildUser({
      id: 99,
      username: "nuovo.utente",
      email: "nuovo.utente@example.local",
      role: "reviewer",
      module_accessi: true,
      enabled_modules: ["accessi"],
    });
    mocks.listAllApplicationUsers.mockResolvedValueOnce([]).mockResolvedValueOnce([createdUser]);
    mocks.getPresenceSummary
      .mockResolvedValueOnce({ window_minutes: 15, active_users: 0, visible_users: 0, items: [], by_module: [] })
      .mockRejectedValueOnce(new Error("Presence non disponibile"));
    mocks.createApplicationUser.mockResolvedValueOnce(createdUser);
    mocks.getApplicationUserPermissions.mockResolvedValueOnce({ ...buildPermissionsView(), user_id: 99, username: "nuovo.utente", role: "reviewer" });

    render(<GaiaUsersPage />);

    const editor = (await screen.findByText("Nuovo utente GAIA")).closest("article") as HTMLElement;
    fireEvent.change(within(editor).getByPlaceholderText("nome.cognome"), { target: { value: "nuovo.utente" } });
    fireEvent.change(within(editor).getByPlaceholderText("utente@ente.local"), { target: { value: "nuovo.utente@example.local" } });
    fireEvent.change(within(editor).getByPlaceholderText("Minimo 8 caratteri"), { target: { value: "password123" } });
    fireEvent.change(within(editor).getByLabelText("Ruolo"), { target: { value: "reviewer" } });
    fireEvent.click(getModuleCheckbox("NAS Control"));
    fireEvent.click(within(editor).getByRole("button", { name: "Crea e apri permessi sezione" }));

    await waitFor(() => {
      expect(mocks.createApplicationUser).toHaveBeenCalledWith(
        "token",
        expect.objectContaining({
          username: "nuovo.utente",
          email: "nuovo.utente@example.local",
          password: "password123",
          role: "reviewer",
          module_accessi: true,
        }),
      );
      expect(mocks.sendApplicationUserInvite).toHaveBeenCalledWith("token", 99);
    });
    expect(await screen.findByText("Utente nuovo.utente creato e mail di attivazione inviata.")).toBeInTheDocument();
    fireEvent.click(screen.getByLabelText("Chiudi notifica"));
    await waitFor(() => expect(screen.queryByText("Utente nuovo.utente creato e mail di attivazione inviata.")).not.toBeInTheDocument());
    expect(await screen.findByText("Modifica utente GAIA")).toBeInTheDocument();
  });

  test("falls back when presence summary loading fails", async () => {
    mocks.listAllApplicationUsers.mockResolvedValue([buildUser({ username: "utente-presenza-fallback" })]);
    mocks.getPresenceSummary.mockRejectedValueOnce(new Error("Presence KO"));

    render(<GaiaUsersPage />);

    expect(await screen.findByRole("button", { name: "utente-presenza-fallback" })).toBeInTheDocument();
    expect(screen.getByText("Fuori finestra 15 min")).toBeInTheDocument();
  });

  test("renders sparse recent presence details without module, route or action labels", async () => {
    mocks.listAllApplicationUsers.mockResolvedValue([
      buildUser({ id: 31, username: "presenza-minima", module_rete: true }),
      buildUser({ id: 32, username: "presenza-path", module_catasto: true }),
    ]);
    mocks.getPresenceSummary.mockResolvedValue({
      window_minutes: 15,
      active_users: 2,
      visible_users: 0,
      by_module: [],
      items: [
        {
          user_id: 31,
          username: "presenza-minima",
          full_name: null,
          role: "viewer",
          module_key: null,
          route_label: null,
          action_label: null,
          path: "",
          visible: false,
          last_seen_at: "2026-06-29T10:00:00Z",
          minutes_since_last_seen: 2,
          last_login_at: null,
          recent_routes: [],
          recent_actions: [],
        },
        {
          user_id: 32,
          username: "presenza-path",
          full_name: null,
          role: "viewer",
          module_key: "catasto",
          route_label: null,
          action_label: null,
          path: "/catasto",
          visible: false,
          last_seen_at: "2026-06-29T09:59:00Z",
          minutes_since_last_seen: 1,
          last_login_at: null,
          recent_routes: [
            {
              path: "/catasto/mappa",
              route_label: null,
              module_key: "catasto",
              seen_at: "2026-06-29T09:58:00Z",
            },
          ],
          recent_actions: [],
        },
      ],
    });

    render(<GaiaUsersPage />);

    fireEvent.click(await screen.findByRole("button", { name: "presenza-minima" }));
    await waitFor(() => expect(screen.getAllByText("In background").length).toBeGreaterThan(0));
    expect(screen.getAllByText("n/d").length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText("Nessuna azione esplicita")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Apri pagina corrente" })).not.toBeInTheDocument();

    fireEvent.click(screen.getByLabelText("Chiudi modifica utente"));
    await waitFor(() => expect(screen.queryByText("Attività GAIA recente")).not.toBeInTheDocument());

    fireEvent.click(screen.getByRole("button", { name: "presenza-path" }));
    expect(await screen.findByRole("link", { name: "Apri pagina corrente" })).toHaveAttribute("href", "/catasto");
    expect(screen.queryByRole("link", { name: "Vedi attività operatore" })).not.toBeInTheDocument();
    expect(screen.getAllByText("/catasto/mappa").length).toBeGreaterThan(0);
  });

  test("creates a user without invite and handles submit errors", async () => {
    mocks.listAllApplicationUsers.mockResolvedValue([]);
    mocks.createApplicationUser.mockRejectedValueOnce(new Error("Username duplicato")).mockResolvedValueOnce(
      buildUser({ id: 100, username: "senza.invito", email: "senza.invito@example.local" }),
    );
    mocks.listAllApplicationUsers.mockResolvedValueOnce([]).mockResolvedValueOnce([buildUser({ id: 100, username: "senza.invito", email: "senza.invito@example.local" })]);

    render(<GaiaUsersPage />);

    const editor = (await screen.findByText("Nuovo utente GAIA")).closest("article") as HTMLElement;
    fireEvent.change(within(editor).getByPlaceholderText("nome.cognome"), { target: { value: "senza.invito" } });
    fireEvent.change(within(editor).getByPlaceholderText("utente@ente.local"), { target: { value: "senza.invito@example.local" } });
    const inviteCheckbox = within(editor).getByText("Invia mail di attivazione").closest("label")?.querySelector('input[type="checkbox"]');
    expect(inviteCheckbox).toBeInstanceOf(HTMLInputElement);
    fireEvent.click(inviteCheckbox as HTMLInputElement);
    fireEvent.click(within(editor).getByRole("button", { name: "Crea e apri permessi sezione" }));

    expect(await screen.findByText("Username duplicato")).toBeInTheDocument();

    fireEvent.click(within(editor).getByRole("button", { name: "Crea e apri permessi sezione" }));
    expect(await screen.findByText("Utente senza.invito creato. Ora puoi configurare anche le singole sezioni del modulo.")).toBeInTheDocument();
    expect(mocks.sendApplicationUserInvite).not.toHaveBeenCalled();
  });

  test("does not submit when the token disappears before saving a new user", async () => {
    mocks.getStoredAccessToken.mockReturnValueOnce("token").mockReturnValueOnce("token").mockReturnValueOnce(null).mockReturnValue("token");
    mocks.listAllApplicationUsers.mockResolvedValue([]);

    render(<GaiaUsersPage />);

    const editor = (await screen.findByText("Nuovo utente GAIA")).closest("article") as HTMLElement;
    fireEvent.click(within(editor).getByRole("button", { name: "Crea e apri permessi sezione" }));

    expect(mocks.createApplicationUser).not.toHaveBeenCalled();
  });

  test("does not reload users when the token disappears after creating a user", async () => {
    mocks.getStoredAccessToken
      .mockReturnValueOnce("token")
      .mockReturnValueOnce("token")
      .mockReturnValueOnce("token")
      .mockReturnValueOnce(null)
      .mockReturnValue("token");
    mocks.listAllApplicationUsers.mockResolvedValue([]);
    mocks.createApplicationUser.mockResolvedValueOnce(buildUser({ id: 120, username: "creato-senza-reload" }));

    render(<GaiaUsersPage />);

    const editor = (await screen.findByText("Nuovo utente GAIA")).closest("article") as HTMLElement;
    const inviteCheckbox = within(editor).getByText("Invia mail di attivazione").closest("label")?.querySelector('input[type="checkbox"]');
    fireEvent.click(inviteCheckbox as HTMLInputElement);
    fireEvent.click(within(editor).getByRole("button", { name: "Crea e apri permessi sezione" }));

    expect(await screen.findByText("Utente creato-senza-reload creato. Ora puoi configurare anche le singole sezioni del modulo.")).toBeInTheDocument();
    expect(mocks.listAllApplicationUsers).toHaveBeenCalledTimes(1);
  });

  test("does not send an invite when the token disappears in edit mode", async () => {
    mocks.getStoredAccessToken
      .mockReturnValueOnce("token")
      .mockReturnValueOnce("token")
      .mockReturnValueOnce("token")
      .mockReturnValueOnce(null)
      .mockReturnValue("token");
    mocks.listAllApplicationUsers.mockResolvedValue([buildUser({ username: "utente-invite-no-token" })]);

    render(<GaiaUsersPage />);

    fireEvent.click(await screen.findByRole("button", { name: "utente-invite-no-token" }));
    const dialog = (await screen.findByText("Modifica utente GAIA")).closest("article") as HTMLElement;
    fireEvent.click(within(dialog).getByRole("button", { name: "Invia mail di accesso" }));

    expect(mocks.sendApplicationUserInvite).not.toHaveBeenCalled();
  });

  test("does not save section permissions when the token disappears", async () => {
    mocks.getStoredAccessToken
      .mockReturnValueOnce("token")
      .mockReturnValueOnce("token")
      .mockReturnValueOnce("token")
      .mockReturnValueOnce(null)
      .mockReturnValue("token");
    mocks.getCurrentUser.mockResolvedValue({ ...buildCurrentUser(), role: "super_admin" });
    mocks.listSectionCatalog.mockResolvedValue([
      buildSection({ id: 101, module: "accessi", key: "accessi.users", label: "Utenti" }),
      buildSection({ id: 102, module: "accessi", key: "accessi.audit", label: "Audit" }),
    ]);
    mocks.listAllApplicationUsers.mockResolvedValue([
      buildUser({
        username: "utente-permessi-no-token",
        module_accessi: true,
        enabled_modules: ["accessi"],
      }),
    ]);

    render(<GaiaUsersPage />);

    fireEvent.click(await screen.findByRole("button", { name: "utente-permessi-no-token" }));
    fireEvent.click(await screen.findByRole("button", { name: "Apri componenti (2)" }));
    const permissionSelects = await screen.findAllByLabelText("Permesso");
    fireEvent.change(permissionSelects[1], { target: { value: "grant" } });
    fireEvent.click(screen.getAllByRole("button", { name: "Salva" }).find((button) => !(button as HTMLButtonElement).disabled)!);

    await waitFor(() => expect(mocks.updateApplicationUserPermissions).not.toHaveBeenCalled());
  });

  test("edit modal reflects stored module flags without forcing NAS Control or Operazioni", async () => {
    mocks.listAllApplicationUsers.mockResolvedValue([
      buildUser({
        username: "utente-senza-moduli",
        module_accessi: false,
        module_operazioni: false,
      }),
    ]);

    render(<GaiaUsersPage />);

    const rowButton = await screen.findByRole("button", { name: "utente-senza-moduli" });
    fireEvent.click(rowButton);

    await waitFor(() => {
      expect(screen.getByText("Modifica utente GAIA")).toBeInTheDocument();
    });

    const dialog = screen.getByText("Modifica utente GAIA").closest("article");
    expect(dialog).toBeTruthy();
    expect(within(dialog as HTMLElement).getByDisplayValue("utente-senza-moduli")).toBeInTheDocument();
    expect(getModuleCheckbox("NAS Control").checked).toBe(false);
    expect(getModuleCheckbox("Operazioni").checked).toBe(false);
  });

  test("edits module component permissions and restores draft", async () => {
    mocks.getCurrentUser.mockResolvedValue({ ...buildCurrentUser(), role: "super_admin" });
    mocks.listSectionCatalog.mockResolvedValue([
      buildSection({ id: 101, module: "accessi", key: "accessi.users", label: "Utenti", description: "Gestione utenti" }),
      buildSection({ id: 102, module: "accessi", key: "accessi.audit", label: "Audit", description: "Audit accessi" }),
      buildSection({ id: 201, module: "presenze", key: "presenze.dashboard", label: "Dashboard giornaliere" }),
      buildSection({ id: 202, module: "organigramma", key: "organigramma.read", label: "Organigramma" }),
    ]);
    mocks.listAllApplicationUsers.mockResolvedValue([
      buildUser({
        username: "utente-permessi",
        module_accessi: true,
        module_presenze: true,
        enabled_modules: ["accessi", "presenze"],
      }),
    ]);
    mocks.updateApplicationUserPermissions.mockResolvedValueOnce({
      ...buildPermissionsView(),
      overrides: [
        {
          id: 502,
          user_id: 7,
          section_id: 102,
          is_granted: true,
          granted_by_id: 1,
          created_at: "2026-06-23T08:00:00Z",
          updated_at: "2026-06-23T08:00:00Z",
        },
      ],
    });

    render(<GaiaUsersPage />);

    fireEvent.click(await screen.findByRole("button", { name: "utente-permessi" }));
    expect(await screen.findByText("Sezioni abilitate")).toBeInTheDocument();
    expect(screen.getByText("1 override")).toBeInTheDocument();

    fireEvent.click(screen.getAllByRole("button", { name: "Apri componenti (2)" })[0]);
    expect(await screen.findByText("Componenti modulo")).toBeInTheDocument();
    expect(screen.getByText("Modulo abilitato")).toBeInTheDocument();
    expect(screen.getByLabelText("Chiudi componenti modulo").parentElement?.className).toContain("z-[75]");
    expect(screen.getByLabelText("Chiudi modifica utente").parentElement?.className).toContain("z-[70]");

    const permissionSelects = screen.getAllByLabelText("Permesso");
    fireEvent.change(permissionSelects[0], { target: { value: "inherit" } });
    fireEvent.change(permissionSelects[1], { target: { value: "grant" } });
    expect(screen.getByText("Modifiche non salvate")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Cerca componente"), { target: { value: "audit" } });
    await waitFor(() => expect(screen.getByText("Ricerca: audit")).toBeInTheDocument());
    fireEvent.click(screen.getByLabelText("Mostra solo override"));
    expect(screen.getByText("Solo override")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Ripristina draft" }));
    fireEvent.change(screen.getByLabelText("Cerca componente"), { target: { value: "" } });
    fireEvent.click(screen.getByLabelText("Mostra solo override"));
    await waitFor(() => expect(screen.getAllByLabelText("Permesso").length).toBe(2));
    const restoredPermissionSelects = screen.getAllByLabelText("Permesso");
    fireEvent.change(restoredPermissionSelects[0], { target: { value: "inherit" } });
    fireEvent.change(restoredPermissionSelects[1], { target: { value: "grant" } });

    const saveButton = screen.getAllByRole("button", { name: "Salva" }).find((button) => !(button as HTMLButtonElement).disabled);
    expect(saveButton).toBeDefined();
    fireEvent.click(saveButton!);

    await waitFor(() => {
      expect(mocks.deleteApplicationUserPermissionOverride).toHaveBeenCalledWith("token", 7, 101);
      expect(mocks.updateApplicationUserPermissions).toHaveBeenCalledWith("token", 7, [{ section_id: 102, is_granted: true }]);
    });
    expect(await screen.findByText("Permessi di sezione aggiornati per utente-permessi.")).toBeInTheDocument();

    fireEvent.keyDown(window, { key: "Enter" });
    expect(screen.getByText("Componenti modulo")).toBeInTheDocument();
    fireEvent.keyDown(window, { key: "Escape" });
    await waitFor(() => expect(screen.queryByText("Componenti modulo")).not.toBeInTheDocument());
  });

  test("saves section permissions when only an existing override is removed", async () => {
    const nextPermissions = {
      ...buildPermissionsView(),
      resolved: [
        {
          section_key: "accessi.users",
          section_label: "Utenti",
          module: "accessi",
          is_granted: false,
          source: "denied",
        },
      ],
      overrides: [],
    };
    mocks.getCurrentUser.mockResolvedValue({ ...buildCurrentUser(), role: "super_admin" });
    mocks.listSectionCatalog.mockResolvedValue([
      buildSection({ id: 101, module: "accessi", key: "accessi.users", label: "Utenti" }),
    ]);
    mocks.listAllApplicationUsers.mockResolvedValue([
      buildUser({
        username: "utente-solo-delete",
        module_accessi: true,
        enabled_modules: ["accessi"],
      }),
    ]);
    mocks.getApplicationUserPermissions.mockResolvedValueOnce(buildPermissionsView()).mockResolvedValueOnce(nextPermissions);

    render(<GaiaUsersPage />);

    fireEvent.click(await screen.findByRole("button", { name: "utente-solo-delete" }));
    fireEvent.click(await screen.findByRole("button", { name: "Apri componenti (1)" }));
    fireEvent.change((await screen.findByLabelText("Permesso")) as HTMLSelectElement, { target: { value: "inherit" } });
    fireEvent.click(screen.getAllByRole("button", { name: "Salva" }).find((button) => !(button as HTMLButtonElement).disabled)!);

    await waitFor(() => {
      expect(mocks.deleteApplicationUserPermissionOverride).toHaveBeenCalledWith("token", 7, 101);
      expect(mocks.getApplicationUserPermissions).toHaveBeenCalledTimes(2);
      expect(mocks.updateApplicationUserPermissions).not.toHaveBeenCalled();
    });
    expect(await screen.findByText("Permessi di sezione aggiornati per utente-solo-delete.")).toBeInTheDocument();
    expect(await screen.findByText("Nessuna sezione concessa")).toBeInTheDocument();
  });

  test("surfaces section permission save failures", async () => {
    mocks.getCurrentUser.mockResolvedValue({ ...buildCurrentUser(), role: "super_admin" });
    mocks.listSectionCatalog.mockResolvedValue([
      buildSection({ id: 101, module: "accessi", key: "accessi.users", label: "Utenti" }),
      buildSection({ id: 102, module: "accessi", key: "accessi.audit", label: "Audit" }),
    ]);
    mocks.listAllApplicationUsers.mockResolvedValue([
      buildUser({
        username: "utente-permessi-ko",
        module_accessi: true,
        enabled_modules: ["accessi"],
      }),
    ]);
    mocks.updateApplicationUserPermissions.mockRejectedValueOnce(new Error("Permessi KO"));

    render(<GaiaUsersPage />);

    fireEvent.click(await screen.findByRole("button", { name: "utente-permessi-ko" }));
    fireEvent.click(await screen.findByRole("button", { name: "Apri componenti (2)" }));

    const permissionSelects = await screen.findAllByLabelText("Permesso");
    fireEvent.change(permissionSelects[1], { target: { value: "grant" } });
    fireEvent.click(screen.getAllByRole("button", { name: "Salva" }).find((button) => !(button as HTMLButtonElement).disabled)!);

    expect(await screen.findByText("Permessi KO")).toBeInTheDocument();

    mocks.updateApplicationUserPermissions.mockRejectedValueOnce("boom");
    fireEvent.click(screen.getAllByRole("button", { name: "Salva" }).find((button) => !(button as HTMLButtonElement).disabled)!);

    expect(await screen.findByText("Aggiornamento permessi sezione non riuscito")).toBeInTheDocument();
  });

  test("saves section permissions when the permissions preview is unavailable", async () => {
    mocks.getCurrentUser.mockResolvedValue({ ...buildCurrentUser(), role: "super_admin" });
    mocks.listSectionCatalog.mockResolvedValue([
      buildSection({ id: 101, module: "accessi", key: "accessi.users", label: "Utenti" }),
    ]);
    mocks.listAllApplicationUsers.mockResolvedValue([
      buildUser({
        username: "utente-permessi-null",
        module_accessi: true,
        enabled_modules: ["accessi"],
      }),
    ]);
    mocks.getApplicationUserPermissions.mockRejectedValueOnce(new Error("Permessi non disponibili"));

    render(<GaiaUsersPage />);

    fireEvent.click(await screen.findByRole("button", { name: "utente-permessi-null" }));
    expect(await screen.findByText("Anteprima permessi sezione non disponibile.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Apri componenti (1)" }));
    fireEvent.change(await screen.findByLabelText("Permesso"), { target: { value: "grant" } });
    fireEvent.click(screen.getAllByRole("button", { name: "Salva" }).find((button) => !(button as HTMLButtonElement).disabled)!);

    await waitFor(() => {
      expect(mocks.updateApplicationUserPermissions).toHaveBeenCalledWith("token", 7, [{ section_id: 101, is_granted: true }]);
    });
    expect(await screen.findByText("Permessi di sezione aggiornati per utente-permessi-null.")).toBeInTheDocument();
  });

  test("shows readonly and unavailable states for component permissions", async () => {
    mocks.getCurrentUser.mockResolvedValue({ ...buildCurrentUser(), role: "admin" });
    mocks.listSectionCatalog.mockResolvedValue([
      buildSection({ id: 101, module: "accessi", key: "accessi.users", label: "Utenti" }),
    ]);
    mocks.listAllApplicationUsers.mockResolvedValue([
      buildUser({
        username: "admin-target",
        role: "admin",
        module_accessi: false,
      }),
    ]);
    mocks.getApplicationUserPermissions.mockRejectedValueOnce(new Error("Permessi non disponibili"));

    render(<GaiaUsersPage />);

    fireEvent.click(await screen.findByRole("button", { name: "admin-target" }));
    expect(await screen.findByText("Anteprima permessi sezione non disponibile.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Apri componenti (1)" }));

    expect(await screen.findByText("Modulo disattivato")).toBeInTheDocument();
    expect(screen.getAllByText("Sola lettura").length).toBeGreaterThan(0);
    expect(screen.getByText("Attiva il modulo per rendere effettivi i permessi")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Cerca componente"), { target: { value: "nessun-match" } });
    expect(screen.getByText("Nessun componente visibile con i filtri attivi per questo modulo.")).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Salva" }).every((button) => (button as HTMLButtonElement).disabled)).toBe(true);
  });

  test("shows component permission loading state and section description fallback", async () => {
    const pendingPermissions = createDeferred<ReturnType<typeof buildPermissionsView>>();
    mocks.getCurrentUser.mockResolvedValue({ ...buildCurrentUser(), role: "super_admin" });
    mocks.listSectionCatalog.mockResolvedValue([
      buildSection({
        id: 301,
        module: "presenze",
        key: "presenze.dashboard",
        label: "Dashboard giornaliere",
        description: null,
      }),
    ]);
    mocks.listAllApplicationUsers.mockResolvedValue([
      buildUser({
        username: "utente-loading-permessi",
        module_presenze: true,
        enabled_modules: ["presenze"],
      }),
    ]);
    mocks.getApplicationUserPermissions.mockReturnValueOnce(pendingPermissions.promise);

    render(<GaiaUsersPage />);

    fireEvent.click(await screen.findByRole("button", { name: "utente-loading-permessi" }));
    fireEvent.click(await screen.findByRole("button", { name: "Apri componenti (1)" }));

    expect(await screen.findByText("Caricamento permessi in corso...")).toBeInTheDocument();

    await act(async () => {
      pendingPermissions.resolve(buildPermissionsView());
    });
    expect(await screen.findByText("presenze.dashboard")).toBeInTheDocument();
  });

  test("ignores late section permission responses after the editor is unmounted", async () => {
    const resolvedPermissions = createDeferred<ReturnType<typeof buildPermissionsView>>();
    mocks.listAllApplicationUsers.mockResolvedValue([buildUser({ username: "utente-resolve-lento" })]);
    mocks.getApplicationUserPermissions.mockReturnValueOnce(resolvedPermissions.promise);

    const resolvedView = render(<GaiaUsersPage />);

    fireEvent.click(await screen.findByRole("button", { name: "utente-resolve-lento" }));
    expect(await screen.findByText("Modifica utente GAIA")).toBeInTheDocument();
    resolvedView.unmount();

    await act(async () => {
      resolvedPermissions.resolve(buildPermissionsView());
    });

    const rejectedPermissions = createDeferred<ReturnType<typeof buildPermissionsView>>();
    mocks.listAllApplicationUsers.mockResolvedValue([buildUser({ username: "utente-reject-lento" })]);
    mocks.getApplicationUserPermissions.mockReturnValueOnce(rejectedPermissions.promise);

    const rejectedView = render(<GaiaUsersPage />);

    fireEvent.click(await screen.findByRole("button", { name: "utente-reject-lento" }));
    expect(await screen.findByText("Modifica utente GAIA")).toBeInTheDocument();
    rejectedView.unmount();

    await act(async () => {
      rejectedPermissions.reject(new Error("Permessi tardivi"));
    });
  });

  test("keeps delete user action disabled in edit mode", async () => {
    mocks.getCurrentUser.mockResolvedValue({ ...buildCurrentUser(), role: "super_admin" });
    mocks.listAllApplicationUsers.mockResolvedValue([
      buildUser({
        username: "utente-eliminabile",
        role: "super_admin",
        is_active: false,
      }),
    ]);

    render(<GaiaUsersPage />);

    fireEvent.click(await screen.findByRole("button", { name: "utente-eliminabile" }));

    await waitFor(() => {
      expect(screen.getByText("Modifica utente GAIA")).toBeInTheDocument();
    });

    const deleteButton = screen.getByRole("button", { name: "Elimina utente" });
    expect(screen.getAllByText("Inattivo").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Super Admin").length).toBeGreaterThan(0);
    expect(deleteButton).toBeDisabled();
    expect(deleteButton).toHaveAttribute("title", "Eliminazione utente disabilitata");
  });

  test("closes the inline edit form action and clears selection state", async () => {
    mocks.listAllApplicationUsers.mockResolvedValue([buildUser({ username: "utente-chiudi" })]);

    render(<GaiaUsersPage />);

    fireEvent.click(await screen.findByRole("button", { name: "utente-chiudi" }));
    const dialog = (await screen.findByText("Modifica utente GAIA")).closest("article") as HTMLElement;

    fireEvent.keyDown(window, { key: "Enter" });
    expect(screen.getByText("Modifica utente GAIA")).toBeInTheDocument();
    fireEvent.click(within(dialog).getByRole("button", { name: "Chiudi" }));

    await waitFor(() => {
      expect(screen.queryByText("Modifica utente GAIA")).not.toBeInTheDocument();
      expect(screen.getByText("Nuovo utente GAIA")).toBeInTheDocument();
    });
    expect(mocks.clearPresenceAction).toHaveBeenCalled();
  });

  test("updates selected user and sends access invite from edit mode", async () => {
    const editableUser = buildUser({
      username: "utente-edit",
      email: "old@example.local",
      role: "viewer",
      is_active: true,
      module_accessi: true,
      enabled_modules: ["accessi"],
      last_login_at: "2026-06-29T08:00:00Z",
      last_login_ip: "10.0.0.7",
      login_count: 2,
    });
    mocks.listAllApplicationUsers.mockResolvedValue([editableUser]);
    mocks.updateApplicationUser.mockResolvedValueOnce({ ...editableUser, email: "new@example.local", role: "admin" });
    mocks.sendApplicationUserInvite.mockResolvedValueOnce({
      user_id: editableUser.id,
      email: "new@example.local",
      expires_at: "2026-06-24T08:00:00Z",
      activation_url: "https://gaia.local/activate",
      activation_url_path: "/activate",
      email_sent: true,
    });

    render(<GaiaUsersPage />);

    fireEvent.click(await screen.findByRole("button", { name: "utente-edit" }));
    const dialog = (await screen.findByText("Modifica utente GAIA")).closest("article") as HTMLElement;

    fireEvent.change(within(dialog).getByPlaceholderText("utente@ente.local"), { target: { value: "new@example.local" } });
    fireEvent.change(within(dialog).getByPlaceholderText("Lascia vuoto per non cambiarla"), { target: { value: "newpass123" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Mostra password" }));
    fireEvent.change(within(dialog).getByLabelText("Ruolo"), { target: { value: "admin" } });
    fireEvent.click(within(dialog).getByLabelText("Account attivo"));
    fireEvent.click(within(dialog).getByRole("button", { name: "Invia mail di accesso" }));

    expect(await screen.findByText("Mail di accesso inviata a new@example.local.")).toBeInTheDocument();

    fireEvent.click(within(dialog).getByRole("button", { name: "Salva modifiche" }));
    await waitFor(() => {
      expect(mocks.updateApplicationUser).toHaveBeenCalledWith(
        "token",
        editableUser.id,
        expect.objectContaining({
          email: "new@example.local",
          password: "newpass123",
          role: "admin",
          is_active: false,
        }),
      );
    });
    expect(await screen.findByText("Utente utente-edit aggiornato.")).toBeInTheDocument();
  });

  test("surfaces edit and invite failures", async () => {
    const editableUser = buildUser({ username: "utente-errori" });
    mocks.listAllApplicationUsers.mockResolvedValue([editableUser]);
    mocks.updateApplicationUser.mockRejectedValueOnce("boom");
    mocks.sendApplicationUserInvite.mockRejectedValueOnce("boom");

    render(<GaiaUsersPage />);

    fireEvent.click(await screen.findByRole("button", { name: "utente-errori" }));
    const dialog = (await screen.findByText("Modifica utente GAIA")).closest("article") as HTMLElement;

    fireEvent.click(within(dialog).getByRole("button", { name: "Invia mail di accesso" }));
    expect(await screen.findByText("Invio mail non riuscito")).toBeInTheDocument();

    mocks.sendApplicationUserInvite.mockRejectedValueOnce(new Error("SMTP KO"));
    fireEvent.click(within(dialog).getByRole("button", { name: "Invia mail di accesso" }));
    expect(await screen.findByText("SMTP KO")).toBeInTheDocument();

    fireEvent.click(within(dialog).getByRole("button", { name: "Salva modifiche" }));
    expect(await screen.findByText("Operazione non riuscita")).toBeInTheDocument();
  });

  test("edit modal shows readonly GaTe Mobile state and deep link when an operator is linked", async () => {
    mocks.listAllApplicationUsers.mockResolvedValue([
      buildUser({
        username: "operatore-mobile",
        gate_mobile_console: {
          operator_id: "11111111-1111-1111-1111-111111111111",
          enabled: true,
          role: "device_manager",
        },
      }),
    ]);

    render(<GaiaUsersPage />);

    fireEvent.click(await screen.findByRole("button", { name: "operatore-mobile" }));

    await waitFor(() => {
      expect(screen.getByText("GaTe Mobile")).toBeInTheDocument();
    });

    expect(screen.getByText("Enabled")).toBeInTheDocument();
    expect(screen.getByText("Device manager")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Gestisci in Operazioni" })).toHaveAttribute(
      "href",
      "/operazioni/operatori?operatorId=11111111-1111-1111-1111-111111111111&from=gaia-users",
    );
  });

  test("formats all GaTe Mobile console role variants", async () => {
    mocks.listAllApplicationUsers.mockResolvedValue([
      buildUser({
        id: 21,
        username: "console-admin",
        gate_mobile_console: { operator_id: "op-console", enabled: false, role: "console_admin" },
      }),
      buildUser({
        id: 22,
        username: "console-viewer",
        gate_mobile_console: { operator_id: "op-viewer", enabled: true, role: "viewer" },
      }),
      buildUser({
        id: 24,
        username: "console-team-manager",
        gate_mobile_console: { operator_id: "op-team", enabled: true, role: "team_manager" },
      }),
      buildUser({
        id: 23,
        username: "console-senza-ruolo",
        gate_mobile_console: { operator_id: "op-empty", enabled: false, role: null },
      }),
    ]);

    render(<GaiaUsersPage />);

    fireEvent.click(await screen.findByRole("button", { name: "console-admin" }));
    expect(await screen.findByText("Console admin")).toBeInTheDocument();
    expect(screen.getByText("Disabled")).toBeInTheDocument();
    fireEvent.keyDown(window, { key: "Escape" });
    await waitFor(() => expect(screen.queryByText("Console admin")).not.toBeInTheDocument());

    fireEvent.click(screen.getByRole("button", { name: "console-viewer" }));
    expect((await screen.findAllByText("Viewer")).length).toBeGreaterThan(0);
    fireEvent.click(screen.getByLabelText("Chiudi modifica utente"));

    fireEvent.click(screen.getByRole("button", { name: "console-team-manager" }));
    expect(await screen.findByText("Team manager")).toBeInTheDocument();
    fireEvent.click(screen.getByLabelText("Chiudi modifica utente"));

    fireEvent.click(screen.getByRole("button", { name: "console-senza-ruolo" }));
    expect(await screen.findByText("Ruolo non assegnato")).toBeInTheDocument();
  });

  test("edit modal shows that GaTe Mobile is not linked when no operator is associated", async () => {
    mocks.listAllApplicationUsers.mockResolvedValue([
      buildUser({
        username: "utente-senza-operatore",
        gate_mobile_console: null,
      }),
    ]);

    render(<GaiaUsersPage />);

    fireEvent.click(await screen.findByRole("button", { name: "utente-senza-operatore" }));

    await waitFor(() => {
      expect(screen.getByText("GaTe Mobile")).toBeInTheDocument();
    });

    expect(screen.getByText("Non collegato")).toBeInTheDocument();
    expect(screen.getByText("Nessun operatore Operazioni collegato a questo utente GAIA.")).toBeInTheDocument();
  });

  test("edit modal shows recent GAIA activity when the user is active in the presence window", async () => {
    mocks.listAllApplicationUsers.mockResolvedValue([
      buildUser({
        username: "operatore-online",
        module_operazioni: true,
      }),
    ]);
    mocks.getPresenceSummary.mockResolvedValue({
      window_minutes: 15,
      active_users: 1,
      visible_users: 1,
      by_module: [{ module_key: "operazioni", count: 1 }],
      items: [
        {
          user_id: 7,
          username: "operatore-online",
          full_name: null,
          role: "viewer",
          module_key: "operazioni",
          route_label: "Operazioni / Attività",
          action_label: "Modifica utente GAIA: operatore-online",
          path: "/operazioni/attivita",
          visible: true,
          last_seen_at: "2026-06-29T10:00:00Z",
          minutes_since_last_seen: 1,
          last_login_at: "2026-06-29T09:00:00Z",
          recent_routes: [
            {
              path: "/operazioni/attivita",
              route_label: "Operazioni / Attività",
              module_key: "operazioni",
              seen_at: "2026-06-29T10:00:00Z",
            },
            {
              path: "/operazioni",
              route_label: "Operazioni",
              module_key: "operazioni",
              seen_at: "2026-06-29T09:57:00Z",
            },
          ],
          recent_actions: [
            {
              action_label: "Modifica utente GAIA: operatore-online",
              occurred_at: "2026-06-29T10:00:00Z",
            },
          ],
        },
      ],
    });

    render(<GaiaUsersPage />);

    fireEvent.click(await screen.findByRole("button", { name: "operatore-online" }));

    await waitFor(() => {
      expect(screen.getByText("Attività GAIA recente")).toBeInTheDocument();
    });

    expect(screen.getAllByText("Scheda visibile").length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Attivo 1 min fa/).length).toBeGreaterThan(0);
    expect(screen.getAllByText("Operazioni / Attività").length).toBeGreaterThan(0);
    expect(screen.getByText(/Modifica utente GAIA: operatore-online/)).toBeInTheDocument();
    expect(screen.getByText("Ultimi passaggi")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Apri pagina corrente" })).toHaveAttribute("href", "/operazioni/attivita");
    expect(screen.getByRole("link", { name: "Vedi attività operatore" })).toHaveAttribute(
      "href",
      "/operazioni/attivita?operator_user_id=7",
    );
  });
});
