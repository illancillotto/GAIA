import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { GisPermissionsPanel } from "@/app/gis/amministrazione/permissions-panel";
import type { ApplicationUser } from "@/types/api";
import type { GisCatalogLayer, GisCatalogLayerPermission } from "@/types/gis";

const mocks = vi.hoisted(() => ({
  listAllApplicationUsers: vi.fn(),
  listGisLayerPermissions: vi.fn(),
  revokeGisLayerPermission: vi.fn(),
  upsertGisLayerPermission: vi.fn(),
}));

vi.mock("@/lib/api", () => ({
  listAllApplicationUsers: (...args: unknown[]) => mocks.listAllApplicationUsers(...args),
}));

vi.mock("@/lib/api/gis", () => ({
  listGisLayerPermissions: (...args: unknown[]) => mocks.listGisLayerPermissions(...args),
  revokeGisLayerPermission: (...args: unknown[]) => mocks.revokeGisLayerPermission(...args),
  upsertGisLayerPermission: (...args: unknown[]) => mocks.upsertGisLayerPermission(...args),
}));

const layer = {
  id: "layer-1",
  workspace: "rete",
  name: "rete_condotte",
  title: "Condotte irrigue",
  source_type: "postgis",
  official_source: "postgis",
  metadata: {},
  is_active: true,
  effective_access_level: "admin",
  can_view: true,
  can_annotate: true,
  can_edit: true,
  can_approve: true,
  can_manage: true,
  created_at: "2026-08-25T08:00:00Z",
  updated_at: "2026-08-25T08:00:00Z",
} satisfies GisCatalogLayer;

const user = {
  id: 7,
  username: "mrossi",
  email: "m.rossi@example.local",
  full_name: "Mario Rossi",
  role: "operator",
  is_active: true,
  module_gis: true,
} as ApplicationUser;

const rolePermission = {
  id: "permission-role",
  layer_id: layer.id,
  principal_type: "role",
  principal_key: "viewer",
  access_level: "viewer",
  can_view: true,
  can_annotate: false,
  can_edit: false,
  can_approve: false,
  can_manage: false,
  created_at: "2026-08-25T08:00:00Z",
  updated_at: "2026-08-25T08:00:00Z",
} satisfies GisCatalogLayerPermission;

const userPermission = {
  ...rolePermission,
  id: "permission-user",
  principal_type: "user",
  principal_key: "7",
  access_level: "editor",
  can_edit: true,
} satisfies GisCatalogLayerPermission;

describe("GisPermissionsPanel", () => {
  beforeEach(() => {
    Object.values(mocks).forEach((mock) => mock.mockReset());
    mocks.listAllApplicationUsers.mockResolvedValue([user]);
    mocks.listGisLayerPermissions.mockResolvedValue([rolePermission]);
  });

  test("assigns readable user permissions and confirms revocation", async () => {
    mocks.listGisLayerPermissions
      .mockResolvedValueOnce([rolePermission])
      .mockResolvedValueOnce([rolePermission, userPermission]);
    mocks.upsertGisLayerPermission.mockResolvedValue(userPermission);
    mocks.revokeGisLayerPermission.mockResolvedValue(undefined);

    const secondLayer = { ...layer, id: "layer-2", title: "Valvole" };
    render(<GisPermissionsPanel token="token" layers={[layer, secondLayer]} />);

    expect(await screen.findByText("Ruolo: Consultazione")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Mappa"), { target: { value: "layer-1" } });
    fireEvent.change(screen.getByLabelText("Ruolo"), { target: { value: "operator" } });
    fireEvent.change(screen.getByLabelText("Assegna a"), { target: { value: "user" } });
    fireEvent.change(screen.getByLabelText("Persona"), { target: { value: "7" } });
    fireEvent.change(screen.getByLabelText("Cosa può fare"), { target: { value: "editor" } });
    fireEvent.click(screen.getByRole("button", { name: "Salva permesso" }));

    await waitFor(() => expect(mocks.upsertGisLayerPermission).toHaveBeenCalledWith("token", "layer-1", {
      principalType: "user",
      principalKey: "7",
      accessLevel: "editor",
    }));
    expect(await screen.findByText(/^Utente: Mario Rossi/)).toBeInTheDocument();
    fireEvent.click(screen.getAllByRole("button", { name: "Revoca" })[0]);
    expect(mocks.revokeGisLayerPermission).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Annulla" }));
    expect(screen.queryByRole("button", { name: "Conferma revoca" })).not.toBeInTheDocument();
    fireEvent.click(screen.getAllByRole("button", { name: "Revoca" })[0]);
    fireEvent.click(screen.getByRole("button", { name: "Conferma revoca" }));
    await waitFor(() => expect(mocks.revokeGisLayerPermission).toHaveBeenCalledWith("token", "layer-1", "permission-role"));
    expect(screen.queryByText("Ruolo: Consultazione")).not.toBeInTheDocument();
    expect(screen.getByText("Permesso revocato.")).toBeInTheDocument();
  });

  test("validates missing selections and handles unavailable users", async () => {
    mocks.listAllApplicationUsers.mockResolvedValue([
      { ...user, id: 8, is_active: false },
      { ...user, id: 9, module_gis: false },
    ]);
    mocks.listGisLayerPermissions.mockResolvedValue([{ ...userPermission, principal_key: "99" }]);
    const firstRender = render(<GisPermissionsPanel token="token" layers={[layer]} />);

    expect(await screen.findByText("Utente non più disponibile (99)")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Assegna a"), { target: { value: "user" } });
    fireEvent.click(screen.getByRole("button", { name: "Salva permesso" }));
    expect(screen.getByText("Scegli una mappa e una persona o un ruolo.")).toBeInTheDocument();

    firstRender.unmount();
    render(<GisPermissionsPanel token="token" layers={[]} />);
    expect(screen.getByText("Non ci sono mappe amministrabili con questa utenza.")).toBeInTheDocument();
    await waitFor(() => expect(mocks.listAllApplicationUsers).toHaveBeenCalled());
  });

  test("reports user, permission, save and revoke errors", async () => {
    mocks.listAllApplicationUsers.mockRejectedValueOnce("users offline");
    mocks.listGisLayerPermissions.mockRejectedValueOnce(new Error("permissions offline"));
    const failedLoad = render(<GisPermissionsPanel token="token" layers={[layer]} />);
    expect(await screen.findByText("permissions offline")).toBeInTheDocument();
    failedLoad.unmount();

    mocks.listAllApplicationUsers.mockResolvedValueOnce([user]);
    mocks.listGisLayerPermissions.mockResolvedValueOnce([rolePermission]);
    mocks.upsertGisLayerPermission.mockRejectedValueOnce("save offline");
    const { unmount } = render(<GisPermissionsPanel token="token" layers={[layer]} />);
    expect(await screen.findAllByText("Ruolo: Consultazione")).not.toHaveLength(0);
    fireEvent.click(screen.getAllByRole("button", { name: "Salva permesso" }).at(-1) as HTMLElement);
    expect(await screen.findByText("Salvataggio permesso non riuscito")).toBeInTheDocument();
    unmount();

    mocks.listGisLayerPermissions.mockResolvedValueOnce([rolePermission]);
    mocks.revokeGisLayerPermission.mockRejectedValueOnce(new Error("revoca negata"));
    render(<GisPermissionsPanel token="token" layers={[layer]} />);
    expect(await screen.findByText("Ruolo: Consultazione")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Revoca" }));
    fireEvent.click(screen.getByRole("button", { name: "Conferma revoca" }));
    expect(await screen.findAllByText("revoca negata")).toHaveLength(2);
  });

  test("uses readable label fallbacks and ignores late user and permission requests", async () => {
    const usernameOnly = { ...user, full_name: null, username: "solo.username" };
    mocks.listAllApplicationUsers.mockResolvedValueOnce([usernameOnly]);
    mocks.listGisLayerPermissions.mockResolvedValueOnce([
      { ...rolePermission, principal_key: "custom_role", access_level: "custom_access" as GisCatalogLayerPermission["access_level"] },
    ]);
    const labels = render(<GisPermissionsPanel token="token" layers={[layer]} />);
    expect(await screen.findByText("Ruolo: custom_role")).toBeInTheDocument();
    expect(screen.getByText("custom_access")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Assegna a"), { target: { value: "user" } });
    expect(screen.getByRole("option", { name: /solo.username/ })).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Assegna a"), { target: { value: "role" } });
    expect(screen.getByLabelText("Ruolo")).toHaveValue("viewer");
    labels.rerender(<GisPermissionsPanel token="token" layers={[layer]} />);
    labels.unmount();

    let resolveUsers: (value: unknown) => void = () => undefined;
    let resolvePermissions: (value: unknown) => void = () => undefined;
    mocks.listAllApplicationUsers.mockReturnValueOnce(new Promise((resolve) => { resolveUsers = resolve; }));
    mocks.listGisLayerPermissions.mockReturnValueOnce(new Promise((resolve) => { resolvePermissions = resolve; }));
    const late = render(<GisPermissionsPanel token="token" layers={[layer]} />);
    await waitFor(() => expect(mocks.listGisLayerPermissions).toHaveBeenCalled());
    late.unmount();
    await act(async () => {
      resolveUsers([user]);
      resolvePermissions([rolePermission]);
      await Promise.resolve();
    });

    let rejectUsers: (reason: unknown) => void = () => undefined;
    let rejectPermissions: (reason: unknown) => void = () => undefined;
    mocks.listAllApplicationUsers.mockReturnValueOnce(new Promise((_, reject) => { rejectUsers = reject; }));
    mocks.listGisLayerPermissions.mockReturnValueOnce(new Promise((_, reject) => { rejectPermissions = reject; }));
    const rejected = render(<GisPermissionsPanel token="token" layers={[layer]} />);
    await waitFor(() => expect(mocks.listGisLayerPermissions).toHaveBeenCalled());
    rejected.unmount();
    await act(async () => {
      rejectUsers(new Error("late users"));
      rejectPermissions(new Error("late permissions"));
      await Promise.resolve();
    });
  });
});
