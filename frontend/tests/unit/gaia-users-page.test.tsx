import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import GaiaUsersPage from "@/app/gaia/users/page";

const mocks = vi.hoisted(() => ({
  getStoredAccessToken: vi.fn(),
  getCurrentUser: vi.fn(),
  listAllApplicationUsers: vi.fn(),
  listSectionCatalog: vi.fn(),
}));

vi.mock("@/lib/auth", () => ({
  getStoredAccessToken: mocks.getStoredAccessToken,
}));

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    getCurrentUser: mocks.getCurrentUser,
    listAllApplicationUsers: mocks.listAllApplicationUsers,
    listSectionCatalog: mocks.listSectionCatalog,
  };
});

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
    data,
    onRowClick,
  }: {
    data: Array<{ id: number; username: string }>;
    onRowClick?: (row: { id: number }) => void;
  }) => (
    <div>
      {data.map((row) => (
        <button key={row.id} type="button" onClick={() => onRowClick?.(row)}>
          {row.username}
        </button>
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
  module_catasto: boolean;
  module_utenze: boolean;
  module_riordino: boolean;
  module_ruolo: boolean;
  module_presenze: boolean;
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
    mocks.getStoredAccessToken.mockReset();
    mocks.getCurrentUser.mockReset();
    mocks.listAllApplicationUsers.mockReset();
    mocks.listSectionCatalog.mockReset();

    mocks.getStoredAccessToken.mockReturnValue("token");
    mocks.getCurrentUser.mockResolvedValue(buildCurrentUser());
    mocks.listSectionCatalog.mockResolvedValue([]);
  });

  test("does not preselect NAS Control or Operazioni for a new user", async () => {
    mocks.listAllApplicationUsers.mockResolvedValue([]);

    render(<GaiaUsersPage />);

    await screen.findByText("Nuovo utente GAIA");

    expect(getModuleCheckbox("NAS Control").checked).toBe(false);
    expect(getModuleCheckbox("Operazioni").checked).toBe(false);
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
});
