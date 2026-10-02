import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";
import { renderToString } from "react-dom/server";

import OrganigrammaPage from "@/app/organigramma/page";
import { OrganigrammaWorkspace, PersonDrawer } from "@/features/organigramma/organigramma-workspace";
import type {
  ApplicationUser,
  OrgUnitDetail,
  OrgUnitTreeNode,
  OrgVisibilityResult,
  OrgVisibilityOverride,
} from "@/types/api";

const mocks = vi.hoisted(() => ({
  isAuthError: vi.fn(),
  getStoredAccessToken: vi.fn(),
  getCurrentUser: vi.fn(),
  getOrgTree: vi.fn(),
  getOrgUnit: vi.fn(),
  getOrgOverrides: vi.fn(),
  getOrgVisibility: vi.fn(),
  getOrgAssignments: vi.fn(),
  createOrgAssignment: vi.fn(),
  updateOrgAssignment: vi.fn(),
  createOrgUnit: vi.fn(),
  deleteOrgAssignment: vi.fn(),
  deleteOrgUnit: vi.fn(),
  createOrgOverride: vi.fn(),
  exportOrganigrammaSnapshot: vi.fn(),
  syncOrgWhiteCompany: vi.fn(),
  importOrganigrammaSnapshot: vi.fn(),
  updateOrgUnit: vi.fn(),
  listAllApplicationUsers: vi.fn(),
}));

vi.mock("@/lib/auth", () => ({ getStoredAccessToken: mocks.getStoredAccessToken }));

vi.mock("@/lib/api", () => ({
  getOrgTree: mocks.getOrgTree,
  getCurrentUser: mocks.getCurrentUser,
  getOrgUnit: mocks.getOrgUnit,
  getOrgOverrides: mocks.getOrgOverrides,
  getOrgVisibility: mocks.getOrgVisibility,
  getOrgAssignments: mocks.getOrgAssignments,
  createOrgAssignment: mocks.createOrgAssignment,
  updateOrgAssignment: mocks.updateOrgAssignment,
  createOrgUnit: mocks.createOrgUnit,
  deleteOrgAssignment: mocks.deleteOrgAssignment,
  deleteOrgUnit: mocks.deleteOrgUnit,
  createOrgOverride: mocks.createOrgOverride,
  exportOrganigrammaSnapshot: mocks.exportOrganigrammaSnapshot,
  syncOrgWhiteCompany: mocks.syncOrgWhiteCompany,
  importOrganigrammaSnapshot: mocks.importOrganigrammaSnapshot,
  updateOrgUnit: mocks.updateOrgUnit,
  listAllApplicationUsers: mocks.listAllApplicationUsers,
  isAuthError: mocks.isAuthError,
}));

vi.mock("@/components/app/protected-page", () => ({
  ProtectedPage: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

function treeNode(id: string, nome: string, tipo: OrgUnitTreeNode["tipo"], parent: string | null, children: OrgUnitTreeNode[] = [], personCount = 0): OrgUnitTreeNode {
  return {
    id, nome, tipo, parent_id: parent, canvas_x: parent ? 420 : 120, canvas_y: parent ? 320 : 120, source: "whitecompany", wc_area_id: null, legacy_team_id: null,
    is_active: true, sort_order: 0, person_count: personCount, child_count: children.length, children,
  };
}

const settore = treeNode("u2", "Settore Idraulico", "settore", "u1", [], 1);
const direzione = treeNode("u1", "Direzione Generale", "direzione", null, [settore], 0);

const detail: OrgUnitDetail = {
  unit: { id: "u1", nome: "Direzione Generale", tipo: "direzione", parent_id: null, is_active: true, sort_order: 0, canvas_x: 120, canvas_y: 120, source: "manuale", wc_area_id: null, legacy_team_id: null, created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z" },
  path: [{ id: "u1", nome: "Direzione Generale", tipo: "direzione", parent_id: null, is_active: true, sort_order: 0, canvas_x: 120, canvas_y: 120, source: "manuale", wc_area_id: null, legacy_team_id: null, created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z" }],
  responsabile: { user_id: 1, full_name: "Mario Sanna", username: "msanna", email: "m@x.it", rbac_role: "super_admin", is_active: true },
  responsabile_title: "Direttore Generale",
  assignments: [
    {
      id: "a1", user_id: 1, org_unit_id: "u1", manager_user_id: null, title: "Direttore Generale",
      position_code: "dirigente", is_primary: true, active: true, valid_from: null, valid_to: null, source: "manuale", wc_operator_id: null,
      created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z",
      person: { user_id: 1, full_name: "Mario Sanna", username: "msanna", email: "m@x.it", rbac_role: "super_admin", is_active: true },
      manager: null,
    },
  ],
};

const users: ApplicationUser[] = [
  { id: 1, username: "msanna", email: "m@x.it", full_name: "Mario Sanna", role: "super_admin", is_active: true } as ApplicationUser,
  { id: 2, username: "acabras", email: "a@x.it", full_name: "Anna Cabras", role: "viewer", is_active: true } as ApplicationUser,
];

const visibility: OrgVisibilityResult = {
  viewer: { user_id: 1, full_name: "Mario Sanna", username: "msanna", email: "m@x.it", rbac_role: "super_admin", is_active: true },
  full: true,
  units: [{ org_unit_id: "u1", nome: "Direzione Generale", tipo: "direzione", parent_id: null, via: "gerarchia", scope: null }],
  people: [{ user_id: 1, full_name: "Mario Sanna", title: "Direttore Generale", org_unit_id: "u1", via: "gerarchia" }],
};

describe("Organigramma page", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    mocks.isAuthError.mockReturnValue(false);
    mocks.getStoredAccessToken.mockReturnValue("token");
    mocks.getCurrentUser.mockResolvedValue({
      id: 1,
      username: "msanna",
      email: "m@x.it",
      full_name: "Mario Sanna",
      role: "super_admin",
      is_active: true,
      module_organigramma: true,
      enabled_modules: ["organigramma"],
    });
    mocks.getOrgTree.mockResolvedValue([direzione]);
    mocks.listAllApplicationUsers.mockResolvedValue(users);
    mocks.getOrgOverrides.mockResolvedValue([]);
    mocks.createOrgOverride.mockResolvedValue(undefined);
    mocks.getOrgUnit.mockResolvedValue(detail);
    mocks.getOrgVisibility.mockResolvedValue(visibility);
    mocks.getOrgAssignments.mockResolvedValue(detail.assignments);
    mocks.createOrgAssignment.mockResolvedValue({
      id: "a2",
      user_id: 2,
      org_unit_id: "u2",
      manager_user_id: null,
      title: null,
      position_code: "collaboratore",
      is_primary: false,
      active: true,
      valid_from: null,
      valid_to: null,
      source: "manuale",
      wc_operator_id: null,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
      person: { user_id: 2, full_name: "Anna Cabras", username: "acabras", email: "a@x.it", rbac_role: "viewer", is_active: true },
      manager: null,
    });
    mocks.updateOrgAssignment.mockResolvedValue(undefined);
    mocks.createOrgUnit.mockResolvedValue({
      id: "u3",
      nome: "Nuovo Settore",
      tipo: "settore",
      parent_id: "u1",
      is_active: true,
      sort_order: 0,
      canvas_x: 440,
      canvas_y: 360,
      source: "manuale",
      wc_area_id: null,
      legacy_team_id: null,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    });
    mocks.exportOrganigrammaSnapshot.mockResolvedValue({
      schema_version: 1,
      exported_at: "2026-01-01T00:00:00Z",
      exported_by_user_id: 1,
      exported_by_username: "msanna",
      units: [],
      assignments: [],
      overrides: [],
    });
    mocks.importOrganigrammaSnapshot.mockResolvedValue({
      mode: "merge",
      units_created: 1,
      units_updated: 0,
      assignments_created: 0,
      assignments_updated: 0,
      overrides_created: 0,
      overrides_updated: 0,
    });
    mocks.updateOrgUnit.mockResolvedValue(detail.unit);
    mocks.deleteOrgUnit.mockResolvedValue(undefined);
    vi.stubGlobal("URL", {
      createObjectURL: vi.fn(() => "blob:test"),
      revokeObjectURL: vi.fn(),
    });
    vi.stubGlobal("confirm", vi.fn(() => true));
  });

  async function enableFreeSchemaEditMode() {
    expect(await screen.findByText("Schema organigramma")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /lavagna libera/i }));
    fireEvent.click(screen.getAllByLabelText("Abilita modifica")[0]!);
  }

  test("renders tree and selected unit detail", async () => {
    render(<OrganigrammaPage />);

    fireEvent.click(await screen.findByRole("button", { name: /Albero/i }));
    expect(await screen.findByText("Albero organizzativo")).toBeInTheDocument();
    // tree node + detail responsabile
    expect(screen.getAllByText("Direzione Generale").length).toBeGreaterThan(0);
    expect((await screen.findAllByText("Mario Sanna")).length).toBeGreaterThan(0);
    expect(screen.getByText("Responsabile unità")).toBeInTheDocument();
    expect(screen.getByText("Assegnazioni dirette")).toBeInTheDocument();
    expect(screen.getByText("Persone nel sotto-albero")).toBeInTheDocument();
  });

  test("does not load a person's assignments without a session and loads them after authentication", async () => {
    const props = { userId: 1, structureKind: "territoriale" as const, overrides: [], units: [], onClose: vi.fn() };
    const rendered = render(<PersonDrawer {...props} token={null} />);
    expect(screen.getByText("Caricamento…")).toBeInTheDocument();
    expect(mocks.getOrgAssignments).not.toHaveBeenCalled();
    rendered.rerender(<PersonDrawer {...props} token="restored-token" />);
    expect(await screen.findByText("Assegnazioni · 1")).toBeInTheDocument();
    expect(mocks.getOrgAssignments).toHaveBeenCalledWith("restored-token", { userId: 1, structureKind: "territoriale" });
  });

  test("renders missing person data and unnamed override targets without inventing identities", async () => {
    const assignment = { ...detail.assignments[0]!, person: null, manager: { ...visibility.viewer, full_name: null } };
    mocks.getOrgAssignments.mockResolvedValue([assignment]);
    render(<PersonDrawer token="token" userId={1} structureKind="organigramma" units={[direzione]} onClose={vi.fn()} overrides={[
      visibilityOverride("out", { target_label: null }),
      visibilityOverride("in", { viewer_user_id: 2, viewer: null, target_type: "user", target_user_id: 1 }),
    ]} />);
    expect(await screen.findByText("Assegnazioni · 1")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Utente #1" })).toBeInTheDocument();
    expect(screen.getByText("riporta a msanna")).toBeInTheDocument();
    expect(screen.getByText("da ?")).toBeInTheDocument();
    expect(screen.queryByText("Mario Sanna")).not.toBeInTheDocument();
  });

  test("opens the visibility simulator from its deep link", async () => {
    const previousHash = window.location.hash;
    window.location.hash = "#chi-vede-chi";
    try {
      render(<OrganigrammaPage />);
      expect(await screen.findByText("Insieme effettivo di unità")).toBeInTheDocument();
      expect(mocks.getOrgVisibility).toHaveBeenCalledWith("token", 1, "organigramma");
    } finally {
      window.location.hash = previousHash;
    }
  });

  test("does not interpret an authentication failure as an empty override catalog", async () => {
    const failure = new Error("Sessione scaduta");
    mocks.isAuthError.mockReturnValue(true);
    mocks.getOrgOverrides.mockResolvedValueOnce([visibilityOverride("existing", { motivo: "Override preesistente" })]).mockRejectedValueOnce(failure);
    mocks.syncOrgWhiteCompany.mockResolvedValue({ message: "Sincronizzazione completata" });
    render(<OrganigrammaPage />);
    expect(await screen.findByText("Schema organigramma")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Albero/i }));
    expect(await screen.findByText(/Override preesistente/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Sync WhiteCompany" }));
    expect(await screen.findByText("Sincronizzazione completata")).toBeInTheDocument();
    expect(await screen.findByText(/Override preesistente/)).toBeInTheDocument();
    expect(mocks.isAuthError).toHaveBeenCalledWith(failure);
    expect(mocks.createOrgOverride).not.toHaveBeenCalled();
  });

  test.each([false, true])("does not apply a late detail response to a newer selection (failure=%s)", async (failure) => {
    let settle: () => void = () => undefined;
    const pending = new Promise<OrgUnitDetail>((resolve, reject) => {
      settle = () => failure ? reject(new Error("Vecchia selezione")) : resolve(detail);
    });
    mocks.getOrgUnit.mockImplementation((_token, id) => id === "u1" ? pending : Promise.resolve({
      ...detail, unit: { ...detail.unit, id: "u2", nome: "Settore Idraulico", tipo: "settore" },
      responsabile: null, assignments: [],
    }));
    render(<OrganigrammaPage />);
    await screen.findByText("Schema organigramma");
    fireEvent.click(screen.getByRole("button", { name: /Albero/i }));
    fireEvent.click(screen.getByRole("treeitem", { name: /Settore Idraulico/ }));
    await waitFor(() => expect(mocks.getOrgUnit).toHaveBeenCalledWith("token", "u2", "organigramma"));
    await act(async () => settle());
    expect(screen.getByText("Nessuna persona assegnata direttamente.")).toBeInTheDocument();
    expect(screen.queryByText("Direttore Generale")).not.toBeInTheDocument();
  });

  test.each([false, true])("does not overwrite the current viewer with a late visibility response (failure=%s)", async (failure) => {
    let settle: () => void = () => undefined;
    const pending = new Promise<OrgVisibilityResult>((resolve, reject) => {
      settle = () => failure ? reject(new Error("Vecchio viewer")) : resolve(visibility);
    });
    mocks.getOrgVisibility.mockImplementation((_token, userId) => userId === 1 ? pending : Promise.resolve({
      ...visibility, viewer: { ...visibility.viewer, user_id: 2, full_name: "Anna Cabras" },
      units: [], people: [], full: false,
    }));
    await openVisibility();
    await waitFor(() => expect(mocks.getOrgVisibility).toHaveBeenCalledWith("token", 1, "organigramma"));
    fireEvent.click(screen.getByRole("button", { name: /Anna Cabras/ }));
    expect(await screen.findByText("Nessun perimetro gerarchico né override attivi.")).toBeInTheDocument();
    await act(async () => settle());
    expect(screen.getByText("Persone visibili · 0")).toBeInTheDocument();
    expect(screen.getByText("Nessun perimetro gerarchico né override attivi.")).toBeInTheDocument();
  });

  test("renders an orphan unit without a dangling schema connector", async () => {
    const normal = render(<OrganigrammaPage />);
    await screen.findByText("Schema organigramma");
    expect(document.querySelectorAll("svg path[marker-end]")).toHaveLength(1);
    normal.unmount();
    mocks.getOrgTree.mockResolvedValue([{ ...settore, parent_id: "parent-removed" }]);
    render(<OrganigrammaPage />);
    await screen.findByText("Schema organigramma");
    expect(screen.getByTestId("schema-node-u2")).toBeInTheDocument();
    expect(document.querySelectorAll("svg path[marker-end]")).toHaveLength(0);
    expect(mocks.updateOrgUnit).not.toHaveBeenCalled();
  });

  test("retains all sectors in the filter when quick shortcuts are capped", async () => {
    const sectors = Array.from({ length: 11 }, (_unused, index) => treeNode(`sector-${index}`, `Settore ${index}`, "settore", "u1"));
    mocks.getOrgTree.mockResolvedValue([{ ...direzione, children: sectors }]);
    render(<OrganigrammaPage />);
    expect(await screen.findByText("+1 nel filtro completo")).toBeInTheDocument();
    const filter = screen.getByRole("combobox", { name: /Filtro settore/i });
    expect(within(filter).getByRole("option", { name: "Settore 10" })).toBeInTheDocument();
    fireEvent.change(filter, { target: { value: "sector-10" } });
    expect(screen.getByTestId("schema-node-sector-10")).toBeInTheDocument();
    expect(screen.queryByTestId("schema-node-sector-0")).not.toBeInTheDocument();
  });

  test("switches to 'Chi vede chi' and shows effective visibility", async () => {
    render(<OrganigrammaPage />);
    await screen.findByText("Schema organigramma");

    fireEvent.click(screen.getByRole("button", { name: /Chi vede chi/i }));

    await waitFor(() => expect(mocks.getOrgVisibility).toHaveBeenCalled());
    expect(await screen.findByText("Insieme effettivo di unità")).toBeInTheDocument();
    expect(screen.getByText("Unità visibili")).toBeInTheDocument();
  });

  async function openVisibility() {
    render(<OrganigrammaPage />);
    await screen.findByText("Schema organigramma");
    fireEvent.click(screen.getByRole("button", { name: /Chi vede chi/i }));
  }

  async function openOverrideForm() {
    render(<OrganigrammaPage />);
    await screen.findByText("Schema organigramma");
    fireEvent.click(screen.getByRole("button", { name: /Albero/i }));
    fireEvent.click(await screen.findByRole("button", { name: "+ Aggiungi eccezione" }));
    return screen.getByRole("dialog");
  }

  function visibilityOverride(id: string, changes: Partial<OrgVisibilityOverride> = {}): OrgVisibilityOverride {
    return {
      id, viewer_user_id: 1, target_type: "org_unit", target_user_id: null,
      target_org_unit_id: "u1", scope: "read", motivo: null, valid_from: null,
      valid_to: null, is_active: true, created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z", status: "attivo",
      viewer: visibility.viewer, target_label: "Direzione Generale", ...changes,
    };
  }

  test("simulates another viewer and distinguishes hierarchy from overrides", async () => {
    mocks.getOrgVisibility.mockResolvedValue({
      ...visibility, full: false,
      viewer: { ...visibility.viewer, user_id: 2, full_name: null, username: "acabras", rbac_role: "viewer" },
      units: [visibility.units[0], { ...visibility.units[0], org_unit_id: "u2", nome: "Settore Idraulico", via: "override", scope: "approve" }],
      people: [{ user_id: 2, full_name: null, title: null, org_unit_id: "u2", via: "override", scope: "read" }],
    });
    await openVisibility();
    expect(await screen.findByText("RBAC: viewer")).toBeInTheDocument();
    expect(screen.getByText("override · Approvazione")).toBeInTheDocument();
    expect(screen.getByText("gerarchia")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /#2/ })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Anna Cabras/ }));
    await waitFor(() => expect(mocks.getOrgVisibility).toHaveBeenLastCalledWith("token", 2, "organigramma"));
    expect(screen.getByText("Persone visibili · 1")).toBeInTheDocument();
  });

  test("shows an empty effective perimeter and recovers from visibility API errors", async () => {
    mocks.getOrgVisibility.mockRejectedValueOnce(new Error("Visibilità indisponibile"));
    mocks.getOrgVisibility.mockResolvedValue({ ...visibility, full: false, units: [], people: [] });
    await openVisibility();
    await waitFor(() => expect(mocks.getOrgVisibility).toHaveBeenCalledTimes(1));
    expect(await screen.findByText("Seleziona un utente per calcolarne la visibilità effettiva.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Anna Cabras/ }));
    expect(await screen.findByText("Nessun perimetro gerarchico né override attivi.")).toBeInTheDocument();
    expect(screen.getByText("Persone visibili · 0")).toBeInTheDocument();
  });

  test("creates an organizational unit override with null optional fields", async () => {
    const dialog = await openOverrideForm();
    fireEvent.click(within(dialog).getByRole("button", { name: "Crea eccezione" }));
    await waitFor(() => expect(mocks.createOrgOverride).toHaveBeenCalledWith("token", {
      viewer_user_id: 1, target_type: "org_unit", target_org_unit_id: "u1",
      target_user_id: null, scope: "read", motivo: null, valid_from: null, valid_to: null,
    }, "organigramma"));
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(mocks.getOrgOverrides).toHaveBeenCalledTimes(2);
  });

  test("creates a user override with selected scope, reason and validity dates", async () => {
    const dialog = await openOverrideForm();
    fireEvent.change(within(dialog).getByLabelText("Viewer (utente)"), { target: { value: "2" } });
    fireEvent.change(within(dialog).getByLabelText("Tipo target"), { target: { value: "user" } });
    fireEvent.change(within(dialog).getByLabelText("Target"), { target: { value: "2" } });
    fireEvent.change(within(dialog).getByLabelText("Scope"), { target: { value: "full" } });
    fireEvent.change(within(dialog).getByLabelText("Motivo"), { target: { value: "Sostituzione ferie" } });
    fireEvent.change(within(dialog).getByLabelText("Valido da"), { target: { value: "2026-10-02" } });
    fireEvent.change(within(dialog).getByLabelText("Valido fino a"), { target: { value: "2026-10-09" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Crea eccezione" }));
    await waitFor(() => expect(mocks.createOrgOverride).toHaveBeenCalledWith("token", {
      viewer_user_id: 2, target_type: "user", target_org_unit_id: null, target_user_id: 2,
      scope: "full", motivo: "Sostituzione ferie", valid_from: "2026-10-02T00:00:00.000Z", valid_to: "2026-10-09T00:00:00.000Z",
    }, "organigramma"));
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
  });

  test.each([new Error("Override rifiutato"), "errore remoto"])("keeps the override form editable after an API rejection (%s)", async (failure) => {
    mocks.createOrgOverride.mockRejectedValueOnce(failure);
    const dialog = await openOverrideForm();
    fireEvent.click(within(dialog).getByRole("button", { name: "Crea eccezione" }));
    expect(await within(dialog).findByText(failure instanceof Error ? failure.message : "Errore")).toBeInTheDocument();
    expect(within(dialog).getByRole("button", { name: "Crea eccezione" })).toBeEnabled();
    fireEvent.click(within(dialog).getByRole("button", { name: "Annulla" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(mocks.getOrgOverrides).toHaveBeenCalledTimes(1);
  });

  test("hides override management for read-only users and tolerates a forbidden catalog", async () => {
    mocks.getCurrentUser.mockResolvedValue({ ...users[1], module_organigramma: true, enabled_modules: ["organigramma"] });
    mocks.getOrgOverrides.mockRejectedValue(new Error("Forbidden"));
    render(<OrganigrammaPage />);
    await screen.findByText("Schema organigramma");
    fireEvent.click(screen.getByRole("button", { name: /Albero/i }));
    expect(await screen.findByText(/Le eccezioni sono visibili solo a chi gestisce il modulo/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "+ Aggiungi eccezione" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Importa JSON" })).not.toBeInTheDocument();
  });

  test("renders override status, missing viewer labels and validity fallbacks", async () => {
    mocks.getOrgOverrides.mockResolvedValue([
      visibilityOverride("expired", { status: "scaduto", viewer: null, target_label: null, motivo: "Ferie", valid_from: "2026-01-01T00:00:00Z", valid_to: "2026-01-02T00:00:00Z" }),
      visibilityOverride("disabled", { status: "disattivato", target_type: "user", target_label: null, viewer: { ...visibility.viewer, full_name: null }, scope: "approve" }),
      visibilityOverride("plain", { status: null, scope: "full" }),
    ]);
    render(<OrganigrammaPage />);
    await screen.findByText("Schema organigramma");
    fireEvent.click(screen.getByRole("button", { name: /Albero/i }));
    const panel = screen.getByText("Override di visibilità").closest("section")!;
    expect(within(panel).getByText("#1")).toBeInTheDocument();
    expect(within(panel).getByText("msanna")).toBeInTheDocument();
    expect(within(panel).getByText("scaduto")).toBeInTheDocument();
    expect(within(panel).getByText("disattivato")).toBeInTheDocument();
    expect(within(panel).getByText("scope: Completo")).toBeInTheDocument();
    expect(within(panel).getByText("“Ferie”")).toBeInTheDocument();
    expect(within(panel).getAllByText(/senza scadenza/)).toHaveLength(2);
  });

  async function openVisiblePerson() {
    await openVisibility();
    const heading = await screen.findByText("Persone visibili · 1");
    fireEvent.click(within(heading.parentElement!).getByRole("button"));
    return screen.getByRole("dialog");
  }

  test("loads a person drawer with assignments, hierarchy and relevant overrides", async () => {
    const assignment = { ...detail.assignments[0]!, org_unit_id: "u2", manager: visibility.viewer };
    mocks.getOrgAssignments.mockImplementation((_token, options) => Promise.resolve(options.userId ? [assignment] : detail.assignments));
    mocks.getOrgOverrides.mockResolvedValue([
      visibilityOverride("out", { target_org_unit_id: "u2", target_label: "Settore Idraulico", motivo: "Accesso temporaneo" }),
      visibilityOverride("direct", { viewer_user_id: 2, target_type: "user", target_user_id: 1, viewer: null, target_label: "Persona" }),
      visibilityOverride("ancestor", { viewer_user_id: 2, viewer: { ...visibility.viewer, full_name: null } }),
      visibilityOverride("unrelated", { viewer_user_id: 2, target_org_unit_id: "altro", motivo: "Non pertinente" }),
    ]);
    const dialog = await openVisiblePerson();
    expect(await within(dialog).findByText("Assegnazioni · 1")).toBeInTheDocument();
    expect(mocks.getOrgAssignments).toHaveBeenCalledWith("token", { userId: 1, structureKind: "organigramma" });
    expect(within(dialog).getByText("Percorso organizzativo")).toBeInTheDocument();
    expect(within(dialog).getByText(/riporta a Mario Sanna/)).toBeInTheDocument();
    expect(within(dialog).getByText("da ?")).toBeInTheDocument();
    expect(within(dialog).getByText("da msanna")).toBeInTheDocument();
    expect(within(dialog).queryByText("“Non pertinente”")).not.toBeInTheDocument();
    fireEvent.click(within(dialog).getByRole("button", { name: "Chiudi" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  test.each([false, true])("shows an empty drawer for missing assignments or API errors (error=%s)", async (reject) => {
    mocks.getOrgAssignments.mockImplementation((_token, options) => options.userId
      ? reject ? Promise.reject(new Error("Assegnazioni indisponibili")) : Promise.resolve([])
      : Promise.resolve(detail.assignments));
    const dialog = await openVisiblePerson();
    expect(await within(dialog).findByText("Nessuna assegnazione.")).toBeInTheDocument();
    expect(within(dialog).getByText("Utente #1")).toBeInTheDocument();
    expect(within(dialog).getByText("Nessuna eccezione assegnata.")).toBeInTheDocument();
    expect(within(dialog).getByText("Nessuna eccezione la riguarda.")).toBeInTheDocument();
    expect(within(dialog).queryByText("Percorso organizzativo")).not.toBeInTheDocument();
  });

  test.each([false, true])("ignores a pending drawer response after closing (error=%s)", async (reject) => {
    let completeRequest: () => void = () => undefined;
    const pending = new Promise<typeof detail.assignments>((resolve, rejectRequest) => {
      completeRequest = () => reject ? rejectRequest(new Error("Risposta tardiva")) : resolve(detail.assignments);
    });
    mocks.getOrgAssignments.mockImplementation((_token, options) => options.userId ? pending : Promise.resolve(detail.assignments));
    const dialog = await openVisiblePerson();
    expect(within(dialog).getByText("Caricamento…")).toBeInTheDocument();
    fireEvent.click(within(dialog).getByRole("button", { name: "Chiudi" }));
    completeRequest();
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(screen.getByText("Persone visibili · 1")).toBeInTheDocument();
  });

  test("uses assignment fallbacks for an unknown unit and an unnamed person", async () => {
    const assignment = {
      ...detail.assignments[0]!, org_unit_id: "unità-esterna", title: null, active: false,
      source: "whitecompany" as const, person: { ...visibility.viewer, full_name: null, email: null },
    };
    mocks.getOrgAssignments.mockImplementation((_token, options) => Promise.resolve(options.userId ? [assignment] : detail.assignments));
    const dialog = await openVisiblePerson();
    expect(await within(dialog).findByText("Assegnazioni · 1")).toBeInTheDocument();
    expect(within(dialog).getByText("msanna")).toBeInTheDocument();
    expect(within(dialog).getByText("unità-esterna")).toBeInTheDocument();
    expect(within(dialog).getByText("vertice")).toBeInTheDocument();
    expect(within(dialog).getByText("—")).toBeInTheDocument();
    expect(within(dialog).queryByText("Percorso organizzativo")).not.toBeInTheDocument();
  });

  test("filters the workspace by settore and focuses the subtree in schema", async () => {
    render(<OrganigrammaPage />);

    expect(await screen.findByText("Schema organigramma")).toBeInTheDocument();
    fireEvent.change(screen.getByRole("combobox", { name: /Filtro settore/i }), {
      target: { value: "u2" },
    });

    expect(await screen.findByText(/Vista focalizzata sul settore/i)).toBeInTheDocument();
    expect(await screen.findByTestId("schema-node-u2")).toBeInTheDocument();
    expect(screen.queryByTestId("schema-node-u1")).not.toBeInTheDocument();
  });

  test("uses quick sector filters to jump directly to the selected block", async () => {
    render(<OrganigrammaPage />);

    expect(await screen.findByText("Schema organigramma")).toBeInTheDocument();
    fireEvent.click(screen.getAllByRole("button", { name: "Settore Idraulico" })[0]!);

    expect(await screen.findByText(/Vista focalizzata sul settore/i)).toBeInTheDocument();
    expect(await screen.findByTestId("schema-node-u2")).toBeInTheDocument();
    expect(screen.queryByTestId("schema-node-u1")).not.toBeInTheDocument();
  });

  test("shows JSON import/export controls for super admin", async () => {
    render(<OrganigrammaPage />);

    expect(await screen.findByText("Schema organigramma")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Esporta JSON" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Importa JSON" })).toBeInTheDocument();
  });

  test("reports a missing session without requesting data", async () => {
    mocks.getStoredAccessToken.mockReturnValue(null);
    render(<OrganigrammaPage />);
    expect(await screen.findByText("Sessione non disponibile.")).toBeInTheDocument();
    expect(mocks.getCurrentUser).not.toHaveBeenCalled();
  });

  test.each([new Error("Caricamento rifiutato"), "errore remoto"])("reports core loading failures (%s)", async (failure) => {
    mocks.getCurrentUser.mockRejectedValueOnce(failure);
    render(<OrganigrammaPage />);
    expect(await screen.findByText(failure instanceof Error ? failure.message : "Errore di caricamento")).toBeInTheDocument();
  });

  test.each([new Error("Sync rifiutata"), "errore remoto"])("reports sync failures and re-enables the control (%s)", async (failure) => {
    mocks.syncOrgWhiteCompany.mockRejectedValueOnce(failure);
    render(<OrganigrammaPage />);
    fireEvent.click(await screen.findByRole("button", { name: "Sync WhiteCompany" }));
    expect(await screen.findByText(failure instanceof Error ? failure.message : "Sync non riuscito")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Sync WhiteCompany" })).toBeEnabled();
  });

  test("refreshes the core data after synchronizing WhiteCompany", async () => {
    mocks.syncOrgWhiteCompany.mockResolvedValueOnce({ message: "Sincronizzazione completata" });
    render(<OrganigrammaPage />);
    fireEvent.click(await screen.findByRole("button", { name: "Sync WhiteCompany" }));
    expect(await screen.findByText("Sincronizzazione completata")).toBeInTheDocument();
    expect(mocks.syncOrgWhiteCompany).toHaveBeenCalledWith("token");
    expect(mocks.getOrgTree).toHaveBeenCalledTimes(2);
  });

  test.each([new Error("Export rifiutato"), "errore remoto"])("reports export failures and re-enables the control (%s)", async (failure) => {
    mocks.exportOrganigrammaSnapshot.mockRejectedValueOnce(failure);
    render(<OrganigrammaPage />);
    fireEvent.click(await screen.findByRole("button", { name: "Esporta JSON" }));
    expect(await screen.findByText(failure instanceof Error ? failure.message : "Export JSON non riuscito")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Esporta JSON" })).toBeEnabled();
  });

  test("downloads the snapshot and releases its object URL", async () => {
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
    try {
      render(<OrganigrammaPage />);
      fireEvent.click(await screen.findByRole("button", { name: "Esporta JSON" }));
      expect(await screen.findByText("Snapshot JSON esportato.")).toBeInTheDocument();
      expect(mocks.exportOrganigrammaSnapshot).toHaveBeenCalledWith("token", "organigramma");
      expect(click).toHaveBeenCalledTimes(1);
      expect(URL.createObjectURL).toHaveBeenCalledWith(expect.any(Blob));
      expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:test");
    } finally {
      click.mockRestore();
    }
  });

  test("opens the native file picker and ignores an empty selection", async () => {
    const rendered = render(<OrganigrammaPage />);
    await screen.findByRole("button", { name: "Importa JSON" });
    const input = rendered.container.querySelector<HTMLInputElement>('input[type="file"]')!;
    const click = vi.spyOn(input, "click");
    fireEvent.click(screen.getByRole("button", { name: "Importa JSON" }));
    expect(click).toHaveBeenCalledTimes(1);
    fireEvent.change(input, { target: { files: [] } });
    expect(mocks.importOrganigrammaSnapshot).not.toHaveBeenCalled();
  });

  test.each(["horizontal", "vertical"])("uses guided %s layout without persisting coordinates", async (orientation) => {
    render(<OrganigrammaPage />);
    await screen.findByText("Schema organigramma");
    fireEvent.click(screen.getByRole("button", { name: "Schema guidato" }));
    fireEvent.click(screen.getByRole("button", { name: orientation === "horizontal" ? "Orizzontale" : "Verticale" }));
    expect(await screen.findByText(`Vista guidata ${orientation === "horizontal" ? "orizzontale" : "verticale"} applicata.`)).toBeInTheDocument();
    expect(mocks.updateOrgUnit).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Reset" }));
    expect(await screen.findByText("Vista guidata consigliata ripristinata.")).toBeInTheDocument();
    await waitFor(() => expect(JSON.parse(localStorage.getItem("gaia.organigramma.schema-prefs.organigramma.1")!)).toEqual({
      canvasMode: "guided", guidedDensity: "standard", orientation: "vertical",
    }));
    expect(mocks.updateOrgUnit).not.toHaveBeenCalled();
  });

  test("restores stored schema preferences and changes guided density", async () => {
    localStorage.setItem("gaia.organigramma.schema-prefs.organigramma.1", JSON.stringify({ canvasMode: "guided", guidedDensity: "compact", orientation: "horizontal" }));
    render(<OrganigrammaPage />);
    await screen.findByText("Schema organigramma");
    expect(screen.getByText("vista orizzontale")).toBeInTheDocument();
    for (const label of ["Presentazione", "Standard", "Compatta"]) {
      fireEvent.click(screen.getByRole("button", { name: label }));
      expect(screen.getByRole("button", { name: label })).toHaveClass("bg-[#eef3fb]");
    }
  });

  test.each([
    [{ canvasMode: "unknown", guidedDensity: "dense", orientation: "diagonal" }, { canvasMode: "guided", guidedDensity: "standard", orientation: "vertical" }],
    [{ canvasMode: "guided", guidedDensity: "presentation", orientation: "horizontal" }, { canvasMode: "guided", guidedDensity: "presentation", orientation: "horizontal" }],
  ])("validates persisted preference values without writing structure data (%j)", async (stored, expected) => {
    const key = "gaia.organigramma.schema-prefs.organigramma.1";
    localStorage.setItem(key, JSON.stringify(stored));
    render(<OrganigrammaPage />);
    await screen.findByText("Schema organigramma");
    await waitFor(() => expect(JSON.parse(localStorage.getItem(key)!)).toEqual(expected));
    expect(mocks.updateOrgUnit).not.toHaveBeenCalled();
  });

  test("resets a removed sector filter after a structure refresh", async () => {
    render(<OrganigrammaPage />);
    await screen.findByText("Schema organigramma");
    const filter = screen.getByRole("combobox", { name: /Filtro settore/i });
    fireEvent.change(filter, { target: { value: "u2" } });
    expect(filter).toHaveValue("u2");
    mocks.getOrgTree.mockResolvedValue([{ ...direzione, children: [] }]);
    mocks.syncOrgWhiteCompany.mockResolvedValue({ message: "Struttura aggiornata" });
    fireEvent.click(screen.getByRole("button", { name: "Sync WhiteCompany" }));
    expect(await screen.findByText("Struttura aggiornata")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByRole("combobox", { name: /Filtro settore/i })).toHaveValue("all"));
    expect(screen.getByTestId("schema-node-u1")).toBeInTheDocument();
    expect(screen.queryByTestId("schema-node-u2")).not.toBeInTheDocument();
  });

  test("dismisses the context menu when its node disappears during refresh", async () => {
    render(<OrganigrammaPage />);
    await enableFreeSchemaEditMode();
    fireEvent.contextMenu(screen.getByTestId("schema-node-u2"), { clientX: 100, clientY: 100 });
    expect(screen.getByText("Azioni blocco")).toBeInTheDocument();
    mocks.getOrgTree.mockResolvedValue([{ ...direzione, children: [] }]);
    mocks.syncOrgWhiteCompany.mockResolvedValue({ message: "Nodo eliminato" });
    fireEvent.click(screen.getByRole("button", { name: "Sync WhiteCompany" }));
    expect(await screen.findByText("Nodo eliminato")).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByText("Azioni blocco")).not.toBeInTheDocument());
    expect(screen.queryByTestId("schema-node-u2")).not.toBeInTheDocument();
  });

  test("sorts unnamed active operators by username while retaining assignment status", async () => {
    const operators = [
      { ...users[1]!, id: 3, full_name: null, username: "beta" },
      { ...users[0]!, full_name: null, username: "zeta" },
      { ...users[1]!, full_name: null, username: "alpha" },
    ];
    mocks.listAllApplicationUsers.mockResolvedValue(operators);
    mocks.getOrgAssignments.mockResolvedValue([detail.assignments[0]!, { ...detail.assignments[0]!, id: "a2", user_id: 2 }]);
    render(<OrganigrammaPage />);
    await screen.findByText("Schema organigramma");
    const panel = screen.getByText("Blocchi e operatori").closest("aside")!;
    const cards = Array.from(panel.querySelectorAll('[draggable="false"]'));
    expect(cards.map(card => card.textContent)).toEqual([
      expect.stringContaining("beta"), expect.stringContaining("alpha"), expect.stringContaining("zeta"),
    ]);
    fireEvent.change(within(panel).getByPlaceholderText("Cerca operatore…"), { target: { value: "alpha" } });
    expect(within(panel).getByText("alpha")).toBeInTheDocument();
    expect(within(panel).queryByText("beta")).not.toBeInTheDocument();
    expect(mocks.updateOrgUnit).not.toHaveBeenCalled();
  });

  test("shows a no-match message for a nonempty filtered tree", async () => {
    render(<OrganigrammaPage />);
    await screen.findByText("Schema organigramma");
    fireEvent.click(screen.getByRole("button", { name: /Albero/i }));
    fireEvent.change(screen.getByPlaceholderText("Cerca unità…"), { target: { value: "non-esistente" } });
    expect(screen.getByText("Nessuna unità corrisponde alla ricerca.")).toBeInTheDocument();
    expect(mocks.deleteOrgUnit).not.toHaveBeenCalled();
    fireEvent.change(screen.getByPlaceholderText("Cerca unità…"), { target: { value: "" } });
    expect(screen.getByTestId("tree-node-u1")).toBeInTheDocument();
  });

  test("supports an orphan context action without inventing a parent name", async () => {
    mocks.getOrgTree.mockResolvedValue([{ ...settore, parent_id: "removed-parent" }]);
    render(<OrganigrammaPage />);
    await enableFreeSchemaEditMode();
    fireEvent.contextMenu(screen.getByTestId("schema-node-u2"), { clientX: 100, clientY: 100 });
    expect(screen.getByRole("button", { name: "Scollega da “padre”" })).toBeInTheDocument();
    fireEvent.keyDown(window, { key: "a" });
    expect(screen.getByText("Azioni blocco")).toBeInTheDocument();
    fireEvent.keyDown(window, { key: "Escape" });
    expect(screen.queryByText("Azioni blocco")).not.toBeInTheDocument();
  });

  test("renders visibility with a missing scope and unnamed viewer", async () => {
    mocks.listAllApplicationUsers.mockResolvedValue([{ ...users[0]!, full_name: null }]);
    mocks.getOrgVisibility.mockResolvedValue({ ...visibility, units: [{ ...visibility.units[0], via: "override", scope: null }] });
    await openVisibility();
    expect(await screen.findByText("override")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /msanna/ })).toBeInTheDocument();
  });

  test("renders a drawer override without a lifecycle status", async () => {
    mocks.getOrgOverrides.mockResolvedValue([visibilityOverride("no-status", { status: null, motivo: "Accesso speciale" })]);
    const dialog = await openVisiblePerson();
    expect(await within(dialog).findAllByText(/Accesso speciale/)).toHaveLength(2);
    expect(within(dialog).queryByText("attivo")).not.toBeInTheDocument();
  });

  test("handles malformed stored preferences and forces territorial presentation defaults", async () => {
    localStorage.setItem("gaia.organigramma.schema-prefs.organigramma.1", "{");
    const rendered = render(<OrganigrammaPage />);
    await screen.findByText("Schema organigramma");
    expect(() => JSON.parse(localStorage.getItem("gaia.organigramma.schema-prefs.organigramma.1")!)).not.toThrow();
    rendered.unmount();
    render(<OrganigrammaWorkspace structureKind="territoriale" entityKey="territoriale" forceStandardOnOpen forcedGuidedDensityOnOpen="presentation" emphasizeUnassignedFilter />);
    await screen.findByText("Schema organigramma");
    expect(screen.getByText("vista verticale")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Sync WhiteCompany" })).not.toBeInTheDocument();
    expect(screen.getByText(/Da assegnare:/)).toBeInTheDocument();
    const filter = screen.getByLabelText<HTMLInputElement>(/Solo non assegnati/);
    const wasChecked = filter.checked;
    fireEvent.click(filter);
    expect(filter.checked).toBe(!wasChecked);
  });

  test.each([true, false])("shows empty-tree messaging for WhiteCompany support (%s)", async (whitecompany) => {
    mocks.getOrgTree.mockResolvedValue([]);
    mocks.getOrgAssignments.mockResolvedValue([]);
    mocks.listAllApplicationUsers.mockResolvedValue([]);
    render(<OrganigrammaWorkspace structureKind={whitecompany ? "organigramma" : "territoriale"} />);
    await screen.findByText("Schema organigramma");
    fireEvent.click(screen.getByRole("button", { name: /Albero/i }));
    expect(screen.getByText(whitecompany ? "Nessuna unità. Usa “Sync WhiteCompany” o crea la struttura via API." : "Nessuna unità. Crea la struttura via UI o API.")).toBeInTheDocument();
    expect(screen.getByText("Seleziona un nodo in albero o schema.")).toBeInTheDocument();
  });

  test("filters and clears searches, sector focus and operator lists", async () => {
    render(<OrganigrammaPage />);
    await screen.findByText("Schema organigramma");
    fireEvent.change(screen.getByPlaceholderText("Cerca unità…"), { target: { value: "inesistente" } });
    expect(screen.queryByTestId("schema-node-u1")).not.toBeInTheDocument();
    fireEvent.change(screen.getByPlaceholderText("Cerca unità…"), { target: { value: "" } });
    fireEvent.change(screen.getByLabelText("Filtro settore"), { target: { value: "u2" } });
    fireEvent.change(screen.getByLabelText("Filtro settore"), { target: { value: "all" } });
    fireEvent.click(screen.getAllByRole("button", { name: "Tutti" }).at(-1)!);
    fireEvent.change(screen.getByPlaceholderText("Cerca operatore…"), { target: { value: "inesistente" } });
    expect(screen.queryByTestId("unassigned-user-2")).not.toBeInTheDocument();
    fireEvent.change(screen.getByPlaceholderText("Cerca blocco da collegare…"), { target: { value: "inesistente" } });
    expect(screen.getByText("Nessun blocco disponibile con il filtro corrente.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Provenienza WhiteCompany" }));
    fireEvent.click(screen.getByRole("button", { name: "Provenienza WhiteCompany" }));
  });

  test.each([
    ["horizontal", new Error("Layout rifiutato")],
    ["horizontal", "errore remoto"],
    ["vertical", new Error("Layout verticale rifiutato")],
    ["vertical", "errore remoto"],
  ] as const)("reports free %s layout persistence failures (%s)", async (orientation, failure) => {
    render(<OrganigrammaPage />);
    await enableFreeSchemaEditMode();
    mocks.updateOrgUnit.mockRejectedValue(failure);
    fireEvent.click(screen.getByRole("button", { name: orientation === "horizontal" ? "Orizzontale" : "Verticale" }));
    expect(await screen.findByText(failure instanceof Error ? failure.message : `Applicazione layout ${orientation === "horizontal" ? "orizzontale" : "verticale"} non riuscita`)).toBeInTheDocument();
  });

  test("ignores a drop on the root target when no organizational node is being dragged", async () => {
    await openEditableTree();
    const target = screen.getByText("Rilascia qui per portare il nodo in radice.");
    expect(fireEvent.dragOver(target)).toBe(true);
    expect(fireEvent.drop(target)).toBe(true);
    expect(mocks.updateOrgUnit).not.toHaveBeenCalled();
    expect(screen.getByTestId("tree-node-u2")).toBeInTheDocument();
  });

  test("does not offer schema context actions or move cards to read-only users", async () => {
    mocks.getCurrentUser.mockResolvedValue({ ...users[1], module_organigramma: true });
    render(<OrganigrammaPage />);
    await screen.findByText("Schema organigramma");
    const card = screen.getByTestId("schema-node-u2");
    fireEvent.contextMenu(card, { clientX: 100, clientY: 100 });
    fireEvent.pointerDown(card, { button: 0, pointerId: 7, clientX: 100, clientY: 100 });
    fireEvent.pointerMove(window, { pointerId: 7, clientX: 200, clientY: 200 });
    fireEvent.pointerUp(window, { pointerId: 7 });
    expect(screen.queryByText("Azioni blocco")).not.toBeInTheDocument();
    expect(mocks.updateOrgUnit).not.toHaveBeenCalled();
  });

  test("summarizes large collapsed groups without omitting their child count", async () => {
    const children = Array.from({ length: 6 }, (_unused, index) => treeNode(`child-${index}`, `Reparto ${index}`, "reparto", "u1"));
    mocks.getOrgTree.mockResolvedValue([{ ...direzione, children }]);
    render(<OrganigrammaPage />);
    await screen.findByText("Schema organigramma");
    fireEvent.click(within(screen.getByTestId("schema-node-u1")).getByRole("button", { name: "Raggruppa" }));
    expect(screen.getByText("+2 altre")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Esplodi (+6)" })).toBeInTheDocument();
    expect(screen.queryByTestId("schema-node-child-5")).not.toBeInTheDocument();
    expect(mocks.updateOrgUnit).not.toHaveBeenCalled();
  });

  test.each(["horizontal", "vertical"])("compacts visible %s cards without changing hierarchy", async (orientation) => {
    render(<OrganigrammaPage />);
    await enableFreeSchemaEditMode();
    fireEvent.click(screen.getByRole("button", { name: orientation === "horizontal" ? "Orizzontale" : "Verticale" }));
    await screen.findByText(`Layout ${orientation === "horizontal" ? "orizzontale" : "verticale"} applicato.`);
    mocks.updateOrgUnit.mockClear();
    fireEvent.click(screen.getByRole("button", { name: "Compatta" }));
    expect(await screen.findByText("Area visibile compattata.")).toBeInTheDocument();
    expect(mocks.updateOrgUnit).toHaveBeenCalledWith("token", "u1", expect.objectContaining({ canvas_x: expect.any(Number), canvas_y: expect.any(Number) }), "organigramma");
  });

  test.each([new Error("Compattazione rifiutata"), "errore remoto"])("reports compaction failures (%s)", async (failure) => {
    render(<OrganigrammaPage />);
    await enableFreeSchemaEditMode();
    mocks.updateOrgUnit.mockRejectedValue(failure);
    fireEvent.click(screen.getByRole("button", { name: "Compatta" }));
    expect(await screen.findByText(failure instanceof Error ? failure.message : "Compattazione area visibile non riuscita")).toBeInTheDocument();
  });

  test("pans and zooms the schema viewport and toggles the grid", async () => {
    render(<OrganigrammaPage />);
    await enableFreeSchemaEditMode();
    const viewport = screen.getByTestId("schema-viewport");
    fireEvent.mouseDown(viewport, { button: 0, clientX: 100, clientY: 100 });
    fireEvent.mouseMove(window, { clientX: 70, clientY: 60 });
    expect(viewport.scrollLeft).toBe(30);
    expect(viewport.scrollTop).toBe(40);
    fireEvent.mouseUp(window);
    expect(viewport.style.cursor).toBe("grab");
    fireEvent.wheel(viewport, { ctrlKey: true, deltaY: -1, clientX: 10, clientY: 10 });
    fireEvent.wheel(viewport, { ctrlKey: true, deltaY: 1, clientX: 10, clientY: 10 });
    fireEvent.wheel(viewport, { deltaY: 1 });
    fireEvent.click(screen.getByRole("button", { name: "+", exact: true }));
    fireEvent.click(screen.getByRole("button", { name: "-", exact: true }));
    fireEvent.click(screen.getByRole("button", { name: "Fit", exact: true }));
    fireEvent.click(screen.getByLabelText("Snap griglia"));
    expect(screen.getByText("griglia libera")).toBeInTheDocument();
    fireEvent.resize(window);
  });

  test("pans and zooms the tree viewport", async () => {
    render(<OrganigrammaPage />);
    await screen.findByText("Schema organigramma");
    fireEvent.click(screen.getByRole("button", { name: /Albero/i }));
    const viewport = screen.getByRole("tree").parentElement!.parentElement!;
    fireEvent.mouseDown(viewport, { button: 0, clientX: 100, clientY: 100 });
    fireEvent.mouseMove(window, { clientX: 60, clientY: 50 });
    expect(viewport.scrollLeft).toBe(40);
    expect(viewport.scrollTop).toBe(50);
    fireEvent.mouseUp(window);
    fireEvent.wheel(viewport, { ctrlKey: true, deltaY: 1, clientX: 10, clientY: 10 });
    fireEvent.wheel(viewport, { ctrlKey: true, deltaY: -1, clientX: 10, clientY: 10 });
    expect(screen.getByText("100%")).toBeInTheDocument();
  });

  async function openEditableTree() {
    render(<OrganigrammaPage />);
    await screen.findByText("Schema organigramma");
    fireEvent.click(screen.getByRole("button", { name: /Albero/i }));
    fireEvent.click(screen.getAllByLabelText("Abilita modifica")[0]!);
  }

  test.each([new Error("Rimozione rifiutata"), "errore remoto", null])("detaches a direct assignment or reports its failure (%s)", async (failure) => {
    if (failure !== null) mocks.deleteOrgAssignment.mockRejectedValueOnce(failure);
    await openEditableTree();
    fireEvent.click(await screen.findByRole("button", { name: "Stacca dall'unità" }));
    const message = failure === null ? "Assegnazione rimossa da organigramma." : failure instanceof Error ? failure.message : "Rimozione assegnazione non riuscita";
    expect(await screen.findByText(message)).toBeInTheDocument();
    expect(mocks.deleteOrgAssignment).toHaveBeenCalledWith("token", "a1", "organigramma");
  });

  test("selects tree nodes using the keyboard and toggles expansion", async () => {
    await openEditableTree();
    const root = screen.getByTestId("tree-node-u1");
    fireEvent.keyDown(root, { key: "ArrowLeft" });
    expect(root).toHaveAttribute("aria-expanded", "false");
    fireEvent.keyDown(root, { key: "ArrowRight" });
    expect(root).toHaveAttribute("aria-expanded", "true");
    fireEvent.keyDown(screen.getByTestId("tree-node-u2"), { key: "Enter" });
    expect(screen.getByTestId("tree-node-u2")).toHaveAttribute("aria-selected", "true");
    fireEvent.keyDown(root, { key: " " });
    expect(root).toHaveAttribute("aria-selected", "true");
    fireEvent.keyDown(root, { key: "Escape" });
    fireEvent.click(within(root).getByRole("button", { name: "Comprimi" }));
    expect(root).toHaveAttribute("aria-expanded", "false");
  });

  test("rejects moving a tree parent below its own descendant", async () => {
    await openEditableTree();
    const root = screen.getByTestId("tree-node-u1");
    const child = screen.getByTestId("tree-node-u2");
    fireEvent.dragStart(root);
    fireEvent.dragOver(child);
    fireEvent.drop(child);
    expect(await screen.findByText("Operazione non valida: non puoi spostare un nodo dentro un suo discendente.")).toBeInTheDocument();
    expect(mocks.updateOrgUnit).not.toHaveBeenCalled();
    fireEvent.dragEnd(root);
  });

  test.each([new Error("Gerarchia rifiutata"), "errore remoto", null])("promotes a dragged tree node to root or reports failure (%s)", async (failure) => {
    await openEditableTree();
    if (failure !== null) mocks.updateOrgUnit.mockRejectedValueOnce(failure);
    const child = screen.getByTestId("tree-node-u2");
    fireEvent.dragStart(child);
    const dropZone = screen.getByText("Rilascia qui per portare il nodo in radice.");
    fireEvent.dragOver(dropZone);
    fireEvent.drop(dropZone);
    const message = failure === null ? "Nodo spostato in radice." : failure instanceof Error ? failure.message : "Aggiornamento gerarchia non riuscito";
    expect(await screen.findByText(message)).toBeInTheDocument();
    expect(mocks.updateOrgUnit).toHaveBeenCalledWith("token", "u2", { parent_id: null }, "organigramma");
  });

  test.each(["above", "below"])("rejects cyclic schema links (%s)", async (mode) => {
    render(<OrganigrammaPage />);
    await enableFreeSchemaEditMode();
    const root = screen.getByTestId("schema-node-u1");
    const child = screen.getByTestId("schema-node-u2");
    const source = mode === "below" ? root : child;
    const target = mode === "below" ? child : root;
    fireEvent.click(within(source).getByTitle(mode === "below" ? "Scegli il padre: questo blocco verrà spostato sotto la card che clicchi" : "Aggancia figli: i blocchi che clicchi finiranno sotto questa card (anche più di uno)"));
    fireEvent.pointerDown(target, { button: 0, pointerId: 1 });
    expect(await screen.findByText(mode === "below"
      ? "Collegamento non valido: il blocco sorgente non può finire sotto un suo discendente."
      : "Collegamento non valido: il blocco destinazione non può finire sotto un suo discendente.")).toBeInTheDocument();
    expect(mocks.updateOrgUnit).not.toHaveBeenCalled();
  });

  test.each([new Error("Collegamento rifiutato"), "errore remoto"])("reports schema link failures (%s)", async (failure) => {
    render(<OrganigrammaPage />);
    await enableFreeSchemaEditMode();
    mocks.updateOrgUnit.mockRejectedValueOnce(failure);
    fireEvent.click(within(screen.getByTestId("schema-node-u2")).getByTitle("Scegli il padre: questo blocco verrà spostato sotto la card che clicchi"));
    fireEvent.pointerDown(screen.getByTestId("schema-node-u1"), { button: 0, pointerId: 1 });
    expect(await screen.findByText(failure instanceof Error ? failure.message : "Aggiornamento collegamento non riuscito")).toBeInTheDocument();
  });

  test("links a selected block from the assignment panel and filters link targets", async () => {
    render(<OrganigrammaPage />);
    await enableFreeSchemaEditMode();
    fireEvent.click(screen.getByTitle("Collega Direzione Generale sopra Settore Idraulico"));
    expect(await screen.findByText("Collegamento aggiornato.")).toBeInTheDocument();
    expect(mocks.updateOrgUnit).toHaveBeenCalledWith("token", "u2", { parent_id: "u1" }, "organigramma");
    fireEvent.change(screen.getByPlaceholderText("Cerca blocco da collegare…"), { target: { value: "idraulico" } });
    fireEvent.click(screen.getAllByRole("button", { name: "Settore Idraulico", exact: true }).at(-1)!);
    expect(screen.getByTestId("schema-node-u2")).toHaveClass("ring-2");
  });

  test.each([new Error("Eliminazione rifiutata"), "errore remoto", null])("deletes a leaf via context menu or reports failure (%s)", async (failure) => {
    render(<OrganigrammaPage />);
    await enableFreeSchemaEditMode();
    if (failure !== null) mocks.deleteOrgUnit.mockRejectedValueOnce(failure);
    fireEvent.contextMenu(screen.getByTestId("schema-node-u2"), { clientX: 5000, clientY: 5000 });
    fireEvent.click(screen.getByRole("button", { name: "Elimina blocco" }));
    const message = failure === null ? "Blocco “Settore Idraulico” eliminato da organigramma." : failure instanceof Error ? failure.message : "Eliminazione blocco non riuscita";
    expect(await screen.findByText(message)).toBeInTheDocument();
    expect(mocks.deleteOrgUnit).toHaveBeenCalledWith("token", "u2", "organigramma");
  });

  test("cancels leaf deletion when the confirmation is declined", async () => {
    vi.stubGlobal("confirm", vi.fn(() => false));
    render(<OrganigrammaPage />);
    await enableFreeSchemaEditMode();
    fireEvent.contextMenu(screen.getByTestId("schema-node-u2"));
    fireEvent.click(screen.getByRole("button", { name: "Elimina blocco" }));
    expect(mocks.deleteOrgUnit).not.toHaveBeenCalled();
  });

  test.each([new Error("Assegnazione rifiutata"), "errore remoto"])("reports user assignment failures in the tree (%s)", async (failure) => {
    await openEditableTree();
    mocks.createOrgAssignment.mockRejectedValueOnce(failure);
    const user = screen.getByTestId("unassigned-user-2");
    fireEvent.dragStart(user);
    const target = screen.getByTestId("tree-node-u2");
    fireEvent.dragOver(target);
    fireEvent.drop(target);
    expect(await screen.findByText(failure instanceof Error ? failure.message : "Assegnazione non riuscita")).toBeInTheDocument();
    fireEvent.dragEnd(user);
  });

  test.each(["assigned", "existing-lead"])("prevents conflicting assignments (%s)", async (conflict) => {
    await openEditableTree();
    if (conflict === "existing-lead") fireEvent.click(screen.getByRole("button", { name: "Imposta responsabile" }));
    const user = screen.getByTestId(conflict === "assigned" ? "unassigned-user-1" : "unassigned-user-2");
    fireEvent.dragStart(user);
    fireEvent.drop(screen.getByTestId("tree-node-u1"));
    expect(await screen.findByText(conflict === "assigned"
      ? "Questo utente risulta già assegnato a una unità."
      : "L'unità ha già un responsabile diretto. Spostalo o sostituiscilo prima di assegnarne un altro.")).toBeInTheDocument();
    expect(mocks.createOrgAssignment).not.toHaveBeenCalled();
  });

  test.each([new Error("Creazione rifiutata"), "errore remoto"])("reports unit creation failures without changing the tree (%s)", async (failure) => {
    mocks.createOrgUnit.mockRejectedValueOnce(failure);
    render(<OrganigrammaPage />);
    fireEvent.click((await screen.findAllByRole("button", { name: "+ Nuovo settore" }))[0]!);
    const dialog = screen.getByRole("dialog");
    fireEvent.change(within(dialog).getByLabelText("Nome"), { target: { value: "Nuova unità" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Crea unità" }));
    expect(await screen.findByText(failure instanceof Error ? failure.message : "Creazione unità non riuscita")).toBeInTheDocument();
    expect(screen.getByTestId("schema-node-u1")).toBeInTheDocument();
  });

  test("validates blank unit names, creates a root without a lead and closes the modal", async () => {
    render(<OrganigrammaPage />);
    fireEvent.click((await screen.findAllByRole("button", { name: "+ Nuovo settore" }))[0]!);
    const dialog = screen.getByRole("dialog");
    fireEvent.click(within(dialog).getByRole("button", { name: "Crea unità" }));
    expect(within(dialog).getByText("Inserisci il nome della nuova unità.")).toBeInTheDocument();
    fireEvent.change(within(dialog).getByLabelText("Nome"), { target: { value: "  Radice nuova  " } });
    fireEvent.change(within(dialog).getByLabelText("Unità padre"), { target: { value: "" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Crea unità" }));
    expect(await screen.findByText("Unità Nuovo Settore creata correttamente.")).toBeInTheDocument();
    expect(mocks.createOrgUnit).toHaveBeenCalledWith("token", expect.objectContaining({ nome: "Radice nuova", parent_id: null, canvas_x: 120, canvas_y: 200 }), "organigramma");
    expect(mocks.createOrgAssignment).not.toHaveBeenCalled();
  });

  test.each(["Escape", "pointerdown", "contextmenu"])("dismisses a schema context menu on %s", async (event) => {
    render(<OrganigrammaPage />);
    await enableFreeSchemaEditMode();
    fireEvent.contextMenu(screen.getByTestId("schema-node-u1"));
    expect(screen.getByText("Azioni blocco")).toBeInTheDocument();
    if (event === "Escape") fireEvent.keyDown(window, { key: "Escape" });
    else if (event === "pointerdown") fireEvent.pointerDown(window);
    else fireEvent.contextMenu(window);
    expect(screen.queryByText("Azioni blocco")).not.toBeInTheDocument();
  });

  test("starts and cancels schema links using context actions and Escape", async () => {
    render(<OrganigrammaPage />);
    await enableFreeSchemaEditMode();
    const root = screen.getByTestId("schema-node-u1");
    for (const label of ["Aggancia figli sotto questo blocco", "Sposta sotto un altro blocco"]) {
      fireEvent.contextMenu(root);
      fireEvent.click(screen.getByRole("button", { name: label }));
      expect(root).toHaveClass("ring-[#b45309]/60");
      fireEvent.keyDown(window, { key: "Tab" });
      expect(root).toHaveClass("ring-[#b45309]/60");
      fireEvent.keyDown(window, { key: "Escape" });
      expect(root).not.toHaveClass("ring-[#b45309]/60");
    }
    const arrow = within(root).getByRole("button", { name: "↓" });
    fireEvent.click(arrow);
    fireEvent.click(arrow);
    expect(root).not.toHaveClass("ring-[#b45309]/60");
  });

  test("opens the responsible person from the context menu", async () => {
    render(<OrganigrammaPage />);
    await enableFreeSchemaEditMode();
    fireEvent.contextMenu(screen.getByTestId("schema-node-u1"));
    fireEvent.click(screen.getAllByRole("button", { name: "Apri scheda responsabile" }).at(-1)!);
    expect(await within(screen.getByRole("dialog")).findByText("Assegnazioni · 1")).toBeInTheDocument();
  });

  test("groups, expands and expands all via context menu and tooltip", async () => {
    render(<OrganigrammaPage />);
    await enableFreeSchemaEditMode();
    const root = screen.getByTestId("schema-node-u1");
    fireEvent.contextMenu(root);
    fireEvent.click(screen.getByRole("button", { name: "Raggruppa sottoalbero (1 blocchi)" }));
    expect(screen.queryByTestId("schema-node-u2")).not.toBeInTheDocument();
    fireEvent.pointerDown(screen.getByRole("button", { name: "Esplodi", exact: true }));
    fireEvent.click(screen.getByRole("button", { name: "Esplodi", exact: true }));
    expect(screen.getByTestId("schema-node-u2")).toBeInTheDocument();
    fireEvent.contextMenu(root);
    fireEvent.click(screen.getByRole("button", { name: "Raggruppa sottoalbero (1 blocchi)" }));
    fireEvent.click(screen.getByRole("button", { name: "Esplodi tutto (1)" }));
    expect(screen.getByTestId("schema-node-u2")).toBeInTheDocument();
  });

  test.each([new Error("Riallineamento rifiutato"), "errore remoto"])("reports expanded subtree persistence failures (%s)", async (failure) => {
    render(<OrganigrammaPage />);
    await enableFreeSchemaEditMode();
    const root = screen.getByTestId("schema-node-u1");
    fireEvent.click(within(root).getByRole("button", { name: "Raggruppa" }));
    mocks.updateOrgUnit.mockRejectedValueOnce(failure);
    fireEvent.click(within(root).getByRole("button", { name: /Esplodi \(\+1\)/ }));
    expect(await screen.findByText(failure instanceof Error ? failure.message : "Riallineamento del sotto-albero non riuscito")).toBeInTheDocument();
  });

  test.each([new Error("Posizione rifiutata"), "errore remoto"])("reports card position save failures (%s)", async (failure) => {
    render(<OrganigrammaPage />);
    await enableFreeSchemaEditMode();
    fireEvent.click(screen.getByLabelText("Snap griglia"));
    const child = screen.getByTestId("schema-node-u2");
    mocks.updateOrgUnit.mockRejectedValueOnce(failure);
    fireEvent.pointerDown(child, { button: 0, clientX: 100, clientY: 100, pointerId: 7 });
    fireEvent.pointerMove(window, { clientX: 140, clientY: 140, pointerId: 8 });
    fireEvent.pointerUp(window, { pointerId: 8 });
    expect(mocks.updateOrgUnit).not.toHaveBeenCalled();
    fireEvent.pointerMove(window, { clientX: 140, clientY: 140, pointerId: 7 });
    fireEvent.pointerCancel(window, { pointerId: 7 });
    expect(await screen.findByText(failure instanceof Error ? failure.message : "Salvataggio posizione non riuscito")).toBeInTheDocument();
  });

  test.each([new Error("Refresh rifiutato"), "errore remoto"])("reports lightweight structure refresh failures (%s)", async (failure) => {
    await openEditableTree();
    mocks.getOrgTree.mockRejectedValueOnce(failure);
    fireEvent.click(screen.getByRole("button", { name: "Stacca dall'unità" }));
    expect(await screen.findByText(failure instanceof Error ? failure.message : "Aggiornamento dati non riuscito")).toBeInTheDocument();
    expect(screen.getByTestId("tree-node-u1")).toBeInTheDocument();
  });

  test("tolerates detail fetch failures during initial load and refresh", async () => {
    mocks.getOrgUnit.mockRejectedValue(new Error("Dettaglio indisponibile"));
    render(<OrganigrammaPage />);
    await enableFreeSchemaEditMode();
    fireEvent.click(within(screen.getByTestId("schema-node-u2")).getByTitle("Scollega questo blocco dal padre"));
    expect(await screen.findByText("Nodo spostato in radice.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Albero/i }));
    expect(screen.getByText("Seleziona un'unità nell'albero per vederne responsabile e persone.")).toBeInTheDocument();
  });

  test("opens person cards and creates or cancels a unit from the assignment inbox", async () => {
    await openEditableTree();
    fireEvent.click(screen.getByRole("button", { name: /Mario Sanna.*Attivo/i }));
    expect(await within(screen.getByRole("dialog")).findByText("Assegnazioni · 1")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Chiudi" }));
    const buttons = screen.getAllByRole("button", { name: "+ Nuovo settore" });
    fireEvent.click(buttons.at(-1)!);
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    fireEvent.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Annulla" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  test("toggles multi-selection off and leaves edit mode", async () => {
    render(<OrganigrammaPage />);
    await enableFreeSchemaEditMode();
    const root = screen.getByTestId("schema-node-u1");
    const child = screen.getByTestId("schema-node-u2");
    fireEvent.click(root);
    fireEvent.click(child, { metaKey: true });
    expect(screen.getByText("2 blocchi selezionati")).toBeInTheDocument();
    fireEvent.click(child, { ctrlKey: true });
    expect(screen.queryByText("2 blocchi selezionati")).not.toBeInTheDocument();
    fireEvent.pointerDown(child, { ctrlKey: true, button: 0, pointerId: 1 });
    fireEvent.pointerDown(child, { button: 2, pointerId: 1 });
    fireEvent.click(screen.getAllByLabelText("Abilita modifica")[0]!);
    expect(screen.getAllByLabelText("Abilita modifica")[0]!).not.toBeChecked();
    expect(mocks.updateOrgUnit).not.toHaveBeenCalled();
  });

  test("filters node types and selects linking targets using both directions", async () => {
    render(<OrganigrammaPage />);
    await enableFreeSchemaEditMode();
    fireEvent.click(screen.getByRole("button", { name: "Settore", exact: true }));
    expect(screen.getByTestId("schema-node-u2")).toBeInTheDocument();
    fireEvent.click(screen.getAllByRole("button", { name: "Tutti", exact: true })[0]!);
    fireEvent.click(screen.getByTestId("schema-node-u2"));
    fireEvent.click(screen.getByTitle("Collega Settore Idraulico sotto Direzione Generale"));
    expect(await screen.findByText("Collegamento aggiornato.")).toBeInTheDocument();
    expect(mocks.updateOrgUnit).toHaveBeenCalledWith("token", "u2", { parent_id: "u1" }, "organigramma");
  });

  test("promotes and deletes a unit through the tree detail controls", async () => {
    const leafDetail = { ...detail, unit: { ...detail.unit, id: "u2", parent_id: "u1", nome: "Settore Idraulico" }, responsabile: null, responsabile_title: null, path: [detail.unit, { ...detail.unit, id: "u2", nome: "Settore Idraulico" }], assignments: [] };
    mocks.getOrgUnit.mockResolvedValue(leafDetail);
    await openEditableTree();
    fireEvent.click(screen.getByTestId("tree-node-u2"));
    fireEvent.click(await screen.findByRole("button", { name: "Imposta come radice" }));
    expect(await screen.findByText("Nodo spostato in radice.")).toBeInTheDocument();
    fireEvent.click(await screen.findByRole("button", { name: "Elimina blocco" }));
    expect(await screen.findByText("Blocco “Settore Idraulico” eliminato da organigramma.")).toBeInTheDocument();
  });

  test("opens the schema card responsible person and grouped tooltip from its card", async () => {
    render(<OrganigrammaPage />);
    await enableFreeSchemaEditMode();
    const root = screen.getByTestId("schema-node-u1");
    fireEvent.click(within(root).getByRole("button", { name: "Apri scheda responsabile" }));
    expect(await within(screen.getByRole("dialog")).findByText("Assegnazioni · 1")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Chiudi" }));
    fireEvent.click(within(root).getByRole("button", { name: "Raggruppa" }));
    fireEvent.pointerDown(within(root).getByRole("button", { name: /Esplodi/ }));
    fireEvent.contextMenu(root);
    fireEvent.click(screen.getByRole("button", { name: "Esplodi sottoalbero" }));
    expect(screen.getByTestId("schema-node-u2")).toBeInTheDocument();
  });

  test("creates a sector from both the focused workspace and tree assignment panel", async () => {
    render(<OrganigrammaPage />);
    await screen.findByText("Schema organigramma");
    fireEvent.click(screen.getByTestId("schema-node-u2"));
    fireEvent.click(screen.getAllByRole("button", { name: "+ Nuovo settore" }).at(-1)!);
    expect(within(screen.getByRole("dialog")).getByLabelText("Unità padre")).toHaveValue("u1");
    fireEvent.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Annulla" }));
    fireEvent.click(screen.getByRole("button", { name: /Albero/i }));
    fireEvent.click(screen.getByRole("button", { name: "+ Nuova unità" }));
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    fireEvent.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Annulla" }));
  });

  test("renders reference staffing deltas, missing person fields and bridge provenance", async () => {
    const children = [treeNode("catasto", "Catasto", "settore", "u1"), treeNode("tributi", "Tributi, Ruoli, Scarichi", "settore", "u1")];
    mocks.getOrgTree.mockResolvedValue([{ ...direzione, nome: "Area Catasto", children }]);
    const assignments = Array.from({ length: 10 }, (_, index) => ({
      ...detail.assignments[0]!, id: `ref-${index}`, org_unit_id: index < 7 ? "catasto" : "tributi",
      title: null, manager: { ...visibility.viewer, full_name: null }, source: "bridge_team" as const,
      person: index === 0 ? null : { ...visibility.viewer, full_name: " ", is_active: false },
    }));
    mocks.getOrgAssignments.mockResolvedValue(assignments);
    mocks.getOrgUnit.mockResolvedValue({ ...detail, unit: { ...detail.unit, nome: "Area Catasto", source: "bridge_team", legacy_team_id: "legacy" }, assignments, responsabile: { ...visibility.viewer, full_name: null }, responsabile_title: null });
    render(<OrganigrammaPage />);
    await screen.findByText("Schema organigramma");
    fireEvent.click(screen.getByRole("button", { name: /Albero/i }));
    expect(await screen.findByText("Riferimento consorzio 2026")).toBeInTheDocument();
    expect(screen.getByText("delta 0")).toBeInTheDocument();
    expect(screen.getByText("delta +1")).toBeInTheDocument();
    expect(screen.getByText("delta -24")).toBeInTheDocument();
    fireEvent.click(screen.getByTestId("tree-node-catasto"));
    mocks.getOrgUnit.mockResolvedValue({ ...detail, unit: { ...detail.unit, id: "catasto", nome: "Catasto" }, assignments, responsabile: null });
    fireEvent.click(screen.getByTestId("tree-node-u1"));
    expect(screen.getByText(/Copertura del sotto-albero/)).toBeInTheDocument();
  });

  test("does not submit an override without any available viewer", async () => {
    mocks.listAllApplicationUsers.mockResolvedValue([]);
    const dialog = await openOverrideForm();
    fireEvent.click(within(dialog).getByRole("button", { name: "Crea eccezione" }));
    expect(mocks.createOrgOverride).not.toHaveBeenCalled();
    fireEvent.click(dialog.firstElementChild!);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  test("renders invalid validity dates literally", async () => {
    mocks.getOrgOverrides.mockResolvedValue([visibilityOverride("invalid-date", { valid_from: "non-data", valid_to: "non-data-fine" })]);
    render(<OrganigrammaPage />);
    await screen.findByText("Schema organigramma");
    fireEvent.click(screen.getByRole("button", { name: /Albero/i }));
    expect(screen.getByText("non-data → non-data-fine")).toBeInTheDocument();
  });

  test("uses assignment-panel controls and modal backdrops", async () => {
    render(<OrganigrammaPage />);
    await enableFreeSchemaEditMode();
    fireEvent.click(screen.getByRole("button", { name: "Imposta responsabile" }));
    fireEvent.click(screen.getByRole("button", { name: "Assegna persona" }));
    fireEvent.click(screen.getAllByLabelText("Abilita modifica").at(-1)!);
    expect(screen.getAllByLabelText("Abilita modifica")[0]!).not.toBeChecked();
    fireEvent.click(screen.getByRole("button", { name: "+ Nuova unità" }));
    fireEvent.click(screen.getByRole("dialog").firstElementChild!);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    fireEvent.click(screen.getAllByRole("button", { name: "+ Nuovo settore" })[0]!);
    fireEvent.click(screen.getByRole("dialog").firstElementChild!);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Albero/i }));
    fireEvent.click(screen.getByRole("button", { name: "+ Aggiungi eccezione" }));
    fireEvent.change(within(screen.getByRole("dialog")).getByLabelText("Target"), { target: { value: "u2" } });
    fireEvent.click(screen.getByRole("dialog").firstElementChild!);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  test("ignores drag events when editing is disabled and closes a drawer via its backdrop", async () => {
    render(<OrganigrammaPage />);
    await screen.findByText("Schema organigramma");
    fireEvent.click(screen.getByRole("button", { name: /Albero/i }));
    const child = screen.getByTestId("tree-node-u2");
    fireEvent.dragOver(child);
    fireEvent.drop(child);
    expect(mocks.updateOrgUnit).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: /Mario Sanna.*Attivo/i }));
    fireEvent.click(screen.getByRole("dialog").firstElementChild!);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  test("filters tree children while retaining their ancestors", async () => {
    render(<OrganigrammaPage />);
    await screen.findByText("Schema organigramma");
    fireEvent.click(screen.getByRole("button", { name: /Albero/i }));
    fireEvent.change(screen.getByPlaceholderText("Cerca unità…"), { target: { value: "idraulico" } });
    expect(screen.getByTestId("tree-node-u1")).toBeInTheDocument();
    expect(screen.getByTestId("tree-node-u2")).toBeInTheDocument();
    fireEvent.change(screen.getByPlaceholderText("Cerca unità…"), { target: { value: "direzione" } });
    expect(screen.queryByTestId("tree-node-u2")).not.toBeInTheDocument();
  });

  test("keeps the context menu open on pointer down and closes on a context gesture", async () => {
    render(<OrganigrammaPage />);
    await enableFreeSchemaEditMode();
    fireEvent.contextMenu(screen.getByTestId("schema-node-u1"));
    const menu = screen.getByText("Azioni blocco").parentElement!.parentElement!;
    fireEvent.pointerDown(menu);
    expect(screen.getByText("Azioni blocco")).toBeInTheDocument();
    fireEvent.contextMenu(menu);
    expect(screen.queryByText("Azioni blocco")).not.toBeInTheDocument();
  });

  test("opens sector and generic unit creation from every schema control", async () => {
    render(<OrganigrammaPage />);
    await screen.findByText("Schema organigramma");
    const sectorButtons = screen.getAllByRole("button", { name: "+ Nuovo settore" });
    for (const button of sectorButtons) {
      fireEvent.click(button);
      expect(screen.getByRole("dialog")).toBeInTheDocument();
      fireEvent.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Annulla" }));
    }
    fireEvent.click(screen.getByRole("button", { name: "+ Nuova unità" }));
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    fireEvent.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Annulla" }));
  });

  test.each(["horizontal", "vertical"])("avoids collisions when expanding a focused %s subtree", async (orientation) => {
    const root = { ...direzione, tipo: "settore" as const, children: [{ ...settore, tipo: "reparto" as const }] };
    const childPosition = orientation === "horizontal" ? { x: 456, y: 120 } : { x: 120, y: 384 };
    const primaryStep = orientation === "horizontal" ? 302 : 286;
    const occupied = [
      { ...treeNode("occupied-1", "Occupato 1", "direzione", null), canvas_x: childPosition.x, canvas_y: childPosition.y },
      { ...treeNode("occupied-2", "Occupato 2", "direzione", null), canvas_x: childPosition.x + primaryStep, canvas_y: childPosition.y },
      { ...treeNode("occupied-3", "Occupato 3", "direzione", null), canvas_x: childPosition.x + primaryStep, canvas_y: childPosition.y + (orientation === "horizontal" ? 224 : 236) },
    ];
    mocks.getOrgTree.mockResolvedValue([root, ...occupied]);
    localStorage.setItem("gaia.organigramma.schema-prefs.organigramma.1", JSON.stringify({ canvasMode: "free", guidedDensity: "standard", orientation }));
    render(<OrganigrammaPage />);
    await enableFreeSchemaEditMode();
    fireEvent.change(screen.getByLabelText("Filtro settore"), { target: { value: "u1" } });
    const card = screen.getByTestId("schema-node-u1");
    fireEvent.click(within(card).getByRole("button", { name: "Raggruppa" }));
    fireEvent.click(within(card).getByRole("button", { name: /Esplodi \(\+1\)/ }));
    await waitFor(() => expect(mocks.updateOrgUnit).toHaveBeenCalledWith("token", "u2", expect.objectContaining({ canvas_x: expect.any(Number), canvas_y: expect.any(Number) }), "organigramma"));
    const payload = mocks.updateOrgUnit.mock.calls.at(-1)![2] as { canvas_x: number; canvas_y: number };
    expect(payload).not.toEqual({ canvas_x: childPosition.x, canvas_y: childPosition.y });
    expect(payload.canvas_x).toBeGreaterThanOrEqual(0);
    expect(payload.canvas_y).toBeGreaterThanOrEqual(0);
  });

  async function uploadSnapshot(snapshot: unknown, mode = "replace") {
    const rendered = render(<OrganigrammaPage />);
    await screen.findByRole("button", { name: "Importa JSON" });
    fireEvent.change(screen.getByLabelText("Import"), { target: { value: mode } });
    const input = rendered.container.querySelector<HTMLInputElement>('input[type="file"]');
    expect(input).not.toBeNull();
    const file = new File([], "organigramma.json", { type: "application/json" });
    Object.defineProperty(file, "text", { value: vi.fn().mockResolvedValue(JSON.stringify(snapshot)) });
    fireEvent.change(input!, { target: { files: [file] } });
    return input!;
  }

  test("imports merge immediately and reports the server counters", async () => {
    const snapshot = { schema_version: 1, units: [], assignments: [], overrides: [] };
    const input = await uploadSnapshot(snapshot, "merge");
    expect(await screen.findByText(/Import merge completato\. Unità create 1, aggiornate 0\./)).toBeInTheDocument();
    expect(mocks.importOrganigrammaSnapshot).toHaveBeenCalledWith("token", snapshot, "merge", "organigramma");
    expect(mocks.getOrgTree).toHaveBeenCalledTimes(2);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(input.value).toBe("");
  });

  test("requires the exact confirmation phrase before replacing the snapshot", async () => {
    const snapshot = { schema_version: 1, units: [], assignments: [], overrides: [] };
    mocks.importOrganigrammaSnapshot.mockResolvedValueOnce({
      mode: "replace", units_created: 2, units_updated: 0,
      assignments_created: 3, assignments_updated: 0, overrides_created: 4, overrides_updated: 0,
    });
    await uploadSnapshot(snapshot);
    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getByText("organigramma.json")).toBeInTheDocument();
    const confirm = within(dialog).getByRole("button", { name: "Conferma replace" });
    expect(confirm).toBeDisabled();
    expect(mocks.importOrganigrammaSnapshot).not.toHaveBeenCalled();
    fireEvent.change(within(dialog).getByPlaceholderText("SOSTITUISCI"), { target: { value: "sostituisci" } });
    expect(confirm).toBeDisabled();
    fireEvent.change(within(dialog).getByPlaceholderText("SOSTITUISCI"), { target: { value: " SOSTITUISCI " } });
    expect(confirm).toBeEnabled();
    fireEvent.click(confirm);
    expect(await screen.findByText(/Import replace completato\. Unità create 2, aggiornate 0\./)).toHaveTextContent(
      "Assegnazioni create 3, aggiornate 0. Override create 4, aggiornate 0.",
    );
    expect(mocks.importOrganigrammaSnapshot).toHaveBeenCalledWith("token", snapshot, "replace", "organigramma");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  test("cancels a pending replacement without calling the import API", async () => {
    const input = await uploadSnapshot({});
    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getByText("n/d")).toBeInTheDocument();
    fireEvent.click(within(dialog).getByRole("button", { name: "Annulla" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(mocks.importOrganigrammaSnapshot).not.toHaveBeenCalled();
    expect(input.value).toBe("");
  });

  test.each([
    { snapshot: { units: [{ id: "a" }, { id: "a" }] }, message: "ID unità duplicati: a" },
    {
      snapshot: { units: ["a", "b", "c", "d", "a", "b", "c", "d"].map((id) => ({ id })) },
      message: "ID unità duplicati: a, b, c…",
    },
    { snapshot: { units: [{ id: "a", parent_id: "missing" }] }, message: "1 unità con parent_id non presente nello snapshot." },
    { snapshot: { assignments: [{ org_unit_id: "missing" }] }, message: "1 assegnazioni puntano a unità mancanti." },
    {
      snapshot: { overrides: [{ target_type: "org_unit", target_org_unit_id: "missing" }] },
      message: "1 override puntano a unità mancanti.",
    },
  ])("blocks replace when the snapshot reports $message", async ({ snapshot, message }) => {
    await uploadSnapshot(snapshot);
    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getByText(message)).toBeInTheDocument();
    fireEvent.change(within(dialog).getByPlaceholderText("SOSTITUISCI"), { target: { value: "SOSTITUISCI" } });
    expect(within(dialog).getByRole("button", { name: "Conferma replace" })).toBeDisabled();
    expect(mocks.importOrganigrammaSnapshot).not.toHaveBeenCalled();
  });

  test.each([
    { snapshot: { units: [{ id: "a", parent_id: "a" }] }, message: "Nessuna unità radice trovata nel file." },
    { snapshot: { units: [{ id: "a" }, { id: "b", parent_id: null }] }, message: "Il file contiene 2 radici distinte." },
    {
      snapshot: { units: [{ id: "a" }], assignments: [{ org_unit_id: "a", active: false }] },
      message: "1 assegnazioni risultano già inattive nel file.",
    },
  ])("keeps replace available for the warning $message", async ({ snapshot, message }) => {
    await uploadSnapshot(snapshot);
    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getByText(message)).toBeInTheDocument();
    fireEvent.change(within(dialog).getByPlaceholderText("SOSTITUISCI"), { target: { value: "SOSTITUISCI" } });
    expect(within(dialog).getByRole("button", { name: "Conferma replace" })).toBeEnabled();
    expect(mocks.importOrganigrammaSnapshot).not.toHaveBeenCalled();
  });

  test("accepts valid assignment and override references without blocking replacement", async () => {
    await uploadSnapshot({
      units: [{ id: "a" }, { id: "b", parent_id: "a" }],
      assignments: [{ org_unit_id: "b", active: true }],
      overrides: [
        { target_type: "org_unit", target_org_unit_id: "b" },
        { target_type: "org_unit", target_org_unit_id: null },
        { target_type: "person", target_org_unit_id: "missing" },
      ],
    });
    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).queryByText("Problemi bloccanti nel file JSON")).not.toBeInTheDocument();
    expect(within(dialog).queryByText("Avvisi da verificare")).not.toBeInTheDocument();
    fireEvent.change(within(dialog).getByPlaceholderText("SOSTITUISCI"), { target: { value: "SOSTITUISCI" } });
    expect(within(dialog).getByRole("button", { name: "Conferma replace" })).toBeEnabled();
  });

  test.each(["merge", "replace"])("reports file reading errors in %s mode without importing", async (mode) => {
    const rendered = render(<OrganigrammaPage />);
    await screen.findByRole("button", { name: "Importa JSON" });
    fireEvent.change(screen.getByLabelText("Import"), { target: { value: mode } });
    const input = rendered.container.querySelector<HTMLInputElement>('input[type="file"]')!;
    const file = new File([], "organigramma.json");
    Object.defineProperty(file, "text", { value: vi.fn().mockRejectedValue(new Error("Lettura file fallita")) });
    fireEvent.change(input, { target: { files: [file] } });
    expect(await screen.findByText("Lettura file fallita")).toBeInTheDocument();
    expect(mocks.importOrganigrammaSnapshot).not.toHaveBeenCalled();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(input.value).toBe("");
  });

  test("keeps the replacement dialog available after an API error", async () => {
    mocks.importOrganigrammaSnapshot.mockRejectedValueOnce(new Error("Import rifiutato"));
    await uploadSnapshot({ units: [], assignments: [], overrides: [] });
    const dialog = await screen.findByRole("dialog");
    fireEvent.change(within(dialog).getByPlaceholderText("SOSTITUISCI"), { target: { value: "SOSTITUISCI" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Conferma replace" }));
    expect(await screen.findByText("Import rifiutato")).toBeInTheDocument();
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(within(dialog).getByRole("button", { name: "Conferma replace" })).toBeEnabled();
  });

  test("centers the schema viewport on first render without pressing Fit", async () => {
    let frameId = 0;
    const requestAnimationFrameSpy = vi.spyOn(window, "requestAnimationFrame").mockImplementation((callback) => {
      frameId += 1;
      callback(frameId);
      return frameId;
    });
    const cancelAnimationFrameSpy = vi.spyOn(window, "cancelAnimationFrame").mockImplementation(() => undefined);
    const clientWidthSpy = vi.spyOn(HTMLElement.prototype, "clientWidth", "get").mockImplementation(function getClientWidth() {
      return this.getAttribute("data-testid") === "schema-viewport" ? 1000 : 0;
    });
    const clientHeightSpy = vi.spyOn(HTMLElement.prototype, "clientHeight", "get").mockImplementation(function getClientHeight() {
      return this.getAttribute("data-testid") === "schema-viewport" ? 520 : 0;
    });
    const scrollWidthSpy = vi.spyOn(HTMLElement.prototype, "scrollWidth", "get").mockImplementation(function getScrollWidth() {
      return this.getAttribute("data-testid") === "schema-viewport" ? 1000 : 4000;
    });
    const scrollHeightSpy = vi.spyOn(HTMLElement.prototype, "scrollHeight", "get").mockImplementation(function getScrollHeight() {
      return this.getAttribute("data-testid") === "schema-viewport" ? 520 : 900;
    });

    try {
      render(<OrganigrammaPage />);

      const viewport = await screen.findByTestId("schema-viewport");
      await waitFor(() => expect(viewport.scrollLeft).toBeGreaterThan(0));
      expect(viewport.scrollTop).toBeGreaterThanOrEqual(0);
    } finally {
      clientWidthSpy.mockRestore();
      clientHeightSpy.mockRestore();
      scrollWidthSpy.mockRestore();
      scrollHeightSpy.mockRestore();
      requestAnimationFrameSpy.mockRestore();
      cancelAnimationFrameSpy.mockRestore();
    }
  });

  test("switches to schema view and links a block below another using arrows", async () => {
    render(<OrganigrammaPage />);

    await enableFreeSchemaEditMode();
    expect(mocks.updateOrgUnit).not.toHaveBeenCalled();

    const sourceNode = await screen.findByTestId("schema-node-u2");
    const targetNode = await screen.findByTestId("schema-node-u1");
    const chooseParentButton = within(sourceNode).getByRole("button", { name: "↑" });

    fireEvent.click(chooseParentButton);
    fireEvent.pointerDown(targetNode, { button: 0, pointerId: 1 });

    await waitFor(() => {
      expect(mocks.updateOrgUnit).toHaveBeenCalledWith("token", "u2", { parent_id: "u1" }, "organigramma");
    });
  });

  test("collects multiple children in sequence with the down arrow", async () => {
    render(<OrganigrammaPage />);

    await enableFreeSchemaEditMode();
    mocks.updateOrgUnit.mockClear();

    const parentNode = await screen.findByTestId("schema-node-u1");
    const childNode = await screen.findByTestId("schema-node-u2");
    const collectChildrenButton = within(parentNode).getByRole("button", { name: "↓" });

    fireEvent.click(collectChildrenButton);
    fireEvent.pointerDown(childNode, { button: 0, pointerId: 1 });

    await waitFor(() => {
      expect(mocks.updateOrgUnit).toHaveBeenCalledWith("token", "u2", { parent_id: "u1" }, "organigramma");
    });

    // The draft stays active: linking another child must not require pressing ↓ again.
    expect(screen.getByText(/puoi collegarne più di uno in sequenza/i)).toBeInTheDocument();
  });

  test("applies vertical and horizontal layouts from schema controls", async () => {
    render(<OrganigrammaPage />);

    await enableFreeSchemaEditMode();
    mocks.updateOrgUnit.mockClear();
    fireEvent.click(screen.getByRole("button", { name: "Orizzontale" }));

    await waitFor(() => {
      expect(mocks.updateOrgUnit).toHaveBeenCalledWith(
        "token",
        expect.any(String),
        expect.objectContaining({
          canvas_x: expect.any(Number),
          canvas_y: expect.any(Number),
        }),
        "organigramma",
      );
    });

    mocks.updateOrgUnit.mockClear();
    fireEvent.click(screen.getByRole("button", { name: "Verticale" }));

    await waitFor(() => {
      expect(mocks.updateOrgUnit).toHaveBeenCalledWith(
        "token",
        expect.any(String),
        expect.objectContaining({
          canvas_x: expect.any(Number),
          canvas_y: expect.any(Number),
        }),
        "organigramma",
      );
    });
  });

  test("detaches a schema block from its parent using the dedicated action", async () => {
    render(<OrganigrammaPage />);

    await enableFreeSchemaEditMode();

    const sourceNode = await screen.findByTestId("schema-node-u2");
    const detachButton = within(sourceNode).getByRole("button", { name: /Scollega/i });

    fireEvent.click(detachButton);

    await waitFor(() => {
      expect(mocks.updateOrgUnit).toHaveBeenCalledWith("token", "u2", { parent_id: null }, "organigramma");
    });
  });

  test("moves a schema card after enabling edit mode", async () => {
    render(<OrganigrammaPage />);

    await enableFreeSchemaEditMode();
    mocks.updateOrgUnit.mockClear();

    const sourceNode = await screen.findByTestId("schema-node-u2");

    fireEvent.pointerDown(sourceNode, { button: 0, clientX: 100, clientY: 100, pointerId: 1 });
    fireEvent.pointerMove(window, { clientX: 180, clientY: 160, pointerId: 1 });
    fireEvent.pointerUp(window, { clientX: 180, clientY: 160, pointerId: 1 });

    await waitFor(() => {
      expect(mocks.updateOrgUnit).toHaveBeenCalledWith(
        "token",
        "u2",
        expect.objectContaining({
          canvas_x: expect.any(Number),
          canvas_y: expect.any(Number),
        }),
        "organigramma",
      );
    });

    const lastCall = mocks.updateOrgUnit.mock.calls.at(-1);
    expect(lastCall?.[2]).toEqual(
      expect.objectContaining({
        canvas_x: expect.any(Number),
        canvas_y: expect.any(Number),
      }),
    );
    expect((lastCall?.[2] as { canvas_x: number }).canvas_x).toBeGreaterThan(420);
    expect((lastCall?.[2] as { canvas_y: number }).canvas_y).toBeGreaterThan(320);
  });

  test("moves multiple cards together with ctrl+click multi-selection", async () => {
    render(<OrganigrammaPage />);

    await enableFreeSchemaEditMode();
    mocks.updateOrgUnit.mockClear();

    const nodeU1 = await screen.findByTestId("schema-node-u1");
    const nodeU2 = await screen.findByTestId("schema-node-u2");

    fireEvent.click(nodeU1);
    fireEvent.click(nodeU2, { ctrlKey: true });

    expect(await screen.findByText(/2 blocchi selezionati/i)).toBeInTheDocument();

    fireEvent.pointerDown(nodeU2, { button: 0, clientX: 100, clientY: 100, pointerId: 1 });
    fireEvent.pointerMove(window, { clientX: 180, clientY: 160, pointerId: 1 });
    fireEvent.pointerUp(window, { clientX: 180, clientY: 160, pointerId: 1 });

    await waitFor(() => {
      const updatedIds = mocks.updateOrgUnit.mock.calls.map((call) => call[1]);
      expect(updatedIds).toEqual(expect.arrayContaining(["u1", "u2"]));
    });
  });

  test("selects blocks with a shift+drag marquee on the canvas background", async () => {
    render(<OrganigrammaPage />);

    await enableFreeSchemaEditMode();

    await screen.findByTestId("schema-node-u1");
    const canvasBackground = document.querySelector(".w-full.overflow-auto.pb-2") as HTMLElement | null;
    expect(canvasBackground).not.toBeNull();

    fireEvent.mouseDown(canvasBackground!, { button: 0, shiftKey: true, clientX: 0, clientY: 0 });
    fireEvent.mouseMove(window, { clientX: 1600, clientY: 1200 });
    fireEvent.mouseUp(window, { clientX: 1600, clientY: 1200 });

    expect(await screen.findByText(/2 blocchi selezionati/i)).toBeInTheDocument();
  });

  test("collapses and expands a subtree from the card toggle", async () => {
    render(<OrganigrammaPage />);

    expect(await screen.findByText("Schema organigramma")).toBeInTheDocument();
    expect(await screen.findByTestId("schema-node-u2")).toBeInTheDocument();

    const parentNode = await screen.findByTestId("schema-node-u1");
    fireEvent.click(within(parentNode).getByRole("button", { name: "Raggruppa" }));

    expect(screen.queryByTestId("schema-node-u2")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Esplodi tutto \(1\)/i })).toBeInTheDocument();

    fireEvent.click(within(parentNode).getByRole("button", { name: /Esplodi \(\+1\)/i }));
    expect(await screen.findByTestId("schema-node-u2")).toBeInTheDocument();
  });

  test("shows a recap tooltip on collapsed groups and expands from it", async () => {
    render(<OrganigrammaPage />);

    expect(await screen.findByText("Schema organigramma")).toBeInTheDocument();

    const parentNode = await screen.findByTestId("schema-node-u1");
    fireEvent.click(within(parentNode).getByRole("button", { name: "Raggruppa" }));
    expect(screen.queryByTestId("schema-node-u2")).not.toBeInTheDocument();

    // Recap tooltip content is rendered (visible on hover via CSS).
    const tooltipTitle = screen.getByText(/Gruppo compresso/i);
    const tooltip = tooltipTitle.parentElement!;
    expect(within(tooltip).getByText("Settore Idraulico")).toBeInTheDocument();
    expect(tooltip.textContent).toMatch(/1.*unità/i);

    fireEvent.click(screen.getByRole("button", { name: "Esplodi" }));
    expect(await screen.findByTestId("schema-node-u2")).toBeInTheDocument();
  });

  test("auto-groups deep levels when the visible tree is large", async () => {
    const squadre = (distrettoId: string) =>
      Array.from({ length: 3 }, (_, index) =>
        treeNode(`${distrettoId}-sq${index}`, `Squadra ${distrettoId}-${index}`, "squadra", distrettoId),
      );
    const distretti = (sectorId: string) =>
      Array.from({ length: 4 }, (_, index) =>
        treeNode(`${sectorId}-d${index}`, `Distretto ${sectorId}-${index}`, "distretto", sectorId, squadre(`${sectorId}-d${index}`)),
      );
    const settori = Array.from({ length: 3 }, (_, index) => {
      const id = `s${index}`;
      return treeNode(id, `Settore ${index}`, "settore", "root", distretti(id));
    });
    const bigTree = treeNode("root", "Direzione Grande", "direzione", null, settori);
    mocks.getOrgTree.mockResolvedValue([bigTree]);

    render(<OrganigrammaPage />);

    expect(await screen.findByText("Schema organigramma")).toBeInTheDocument();
    // Root, settori e distretti restano visibili; le squadre sotto i distretti sono auto-raggruppate.
    expect(await screen.findByTestId("schema-node-s0")).toBeInTheDocument();
    expect(await screen.findByTestId("schema-node-s0-d0")).toBeInTheDocument();
    expect(screen.queryByTestId("schema-node-s0-d0-sq0")).not.toBeInTheDocument();
    expect(within(screen.getByTestId("schema-node-s0-d0")).getByRole("button", { name: /Esplodi \(\+3\)/i })).toBeInTheDocument();

    // Expanding one group reveals only its squadre.
    fireEvent.click(within(screen.getByTestId("schema-node-s0-d0")).getByRole("button", { name: /Esplodi \(\+3\)/i }));
    expect(await screen.findByTestId("schema-node-s0-d0-sq0")).toBeInTheDocument();
    expect(screen.queryByTestId("schema-node-s0-d1-sq0")).not.toBeInTheDocument();
  });

  test("selects a whole subtree from the context menu", async () => {
    render(<OrganigrammaPage />);

    await enableFreeSchemaEditMode();

    const parentNode = await screen.findByTestId("schema-node-u1");
    fireEvent.contextMenu(parentNode, { clientX: 220, clientY: 160 });

    const selectSubtreeButton = await screen.findByRole("button", { name: /Seleziona sottoalbero/i });
    fireEvent.click(selectSubtreeButton);

    expect(await screen.findByText(/2 blocchi selezionati/i)).toBeInTheDocument();
  });

  test("opens the schema context menu on right click and promotes a block to root", async () => {
    render(<OrganigrammaPage />);

    await enableFreeSchemaEditMode();

    const sourceNode = await screen.findByTestId("schema-node-u2");
    fireEvent.contextMenu(sourceNode, { clientX: 220, clientY: 160 });

    const detachButton = await screen.findByRole("button", { name: /Scollega da/i });
    fireEvent.click(detachButton);

    await waitFor(() => {
      expect(mocks.updateOrgUnit).toHaveBeenCalledWith("token", "u2", { parent_id: null }, "organigramma");
    });
  });

  test("deletes a leaf block from the schema context menu", async () => {
    render(<OrganigrammaPage />);

    await enableFreeSchemaEditMode();

    const sourceNode = await screen.findByTestId("schema-node-u2");
    fireEvent.contextMenu(sourceNode, { clientX: 220, clientY: 160 });

    const deleteButton = await screen.findByRole("button", { name: "Elimina blocco" });
    fireEvent.click(deleteButton);

    await waitFor(() => {
      expect(mocks.deleteOrgUnit).toHaveBeenCalledWith("token", "u2", "organigramma");
    });
  });

  test("allows hierarchy move from tree view only after enabling edit", async () => {
    render(<OrganigrammaPage />);

    fireEvent.click(await screen.findByRole("button", { name: /Albero/i }));
    expect(await screen.findByText("Albero organizzativo")).toBeInTheDocument();

    const editToggle = screen.getAllByLabelText("Abilita modifica")[0]!;
    fireEvent.click(editToggle);

    const draggableNodes = document.querySelectorAll("[role='treeitem'][draggable='true']");
    expect(draggableNodes.length).toBeGreaterThanOrEqual(2);

    fireEvent.dragStart(draggableNodes[1]!);
    fireEvent.dragOver(draggableNodes[0]!);
    fireEvent.drop(draggableNodes[0]!);

    await waitFor(() => {
      expect(mocks.updateOrgUnit).toHaveBeenCalledWith("token", "u2", { parent_id: "u1" }, "organigramma");
    });
  });

  test("assigns an unassigned application user to a node via drag and drop", async () => {
    render(<OrganigrammaPage />);

    expect(await screen.findByText("Schema organigramma")).toBeInTheDocument();
    fireEvent.click(screen.getAllByLabelText("Abilita modifica")[0]!);

    const userCard = await screen.findByTestId("unassigned-user-2");
    const targetNode = await screen.findByTestId("schema-node-u2");

    fireEvent.dragStart(userCard);
    fireEvent.dragOver(targetNode);
    fireEvent.drop(targetNode);

    await waitFor(() => {
      expect(mocks.createOrgAssignment).toHaveBeenCalledWith("token", {
        user_id: 2,
        org_unit_id: "u2",
        manager_user_id: null,
        title: null,
        position_code: "collaboratore",
        is_primary: false,
        active: true,
        source: "manuale",
      }, "organigramma");
    });
  });

  test("assigns a unit lead and realigns existing direct reports", async () => {
    const thirdUser = {
      id: 3, username: "ppiras", email: "p@x.it", full_name: "Paolo Piras", role: "viewer", is_active: true,
    } as ApplicationUser;
    const directReport = {
      ...detail.assignments[0], id: "a2", user_id: 2, org_unit_id: "u2", manager_user_id: null,
      title: null, position_code: "collaboratore", is_primary: false, person: detail.assignments[0]!.person,
    };
    mocks.listAllApplicationUsers.mockResolvedValue([...users, thirdUser]);
    mocks.getOrgAssignments.mockResolvedValue([...detail.assignments, directReport]);

    render(<OrganigrammaPage />);

    expect(await screen.findByText("Schema organigramma")).toBeInTheDocument();
    fireEvent.click(screen.getAllByLabelText("Abilita modifica")[0]!);
    fireEvent.click(screen.getByRole("button", { name: "Imposta responsabile" }));
    expect((await screen.findAllByText("Drop su un nodo per impostarlo come responsabile.")).length).toBeGreaterThan(0);
    fireEvent.dragStart(await screen.findByTestId("unassigned-user-3"));
    const targetNode = await screen.findByTestId("schema-node-u2");
    fireEvent.dragOver(targetNode);
    fireEvent.drop(targetNode);

    await waitFor(() => {
      expect(mocks.createOrgAssignment).toHaveBeenCalledWith("token", expect.objectContaining({
        user_id: 3,
        org_unit_id: "u2",
        manager_user_id: 1,
        title: "Capo settore",
        position_code: "capo_settore",
        is_primary: true,
      }), "organigramma");
      expect(mocks.updateOrgAssignment).toHaveBeenCalledWith(
        "token", "a2", { manager_user_id: 3 }, "organigramma",
      );
    });
  });

  test("creates a reparto with its initial lead", async () => {
    mocks.createOrgUnit.mockResolvedValueOnce({
      ...detail.unit, id: "u3", nome: "Reparto Pompe", tipo: "reparto", parent_id: "u2",
    });
    render(<OrganigrammaPage />);

    expect(await screen.findByText("Schema organigramma")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "+ Nuova unità" }));
    fireEvent.change(screen.getByLabelText("Nome"), { target: { value: "Reparto Pompe" } });
    fireEvent.change(screen.getByLabelText("Tipo"), { target: { value: "reparto" } });
    fireEvent.change(screen.getByLabelText("Unità padre"), { target: { value: "u2" } });
    fireEvent.change(screen.getByLabelText("Responsabile iniziale"), { target: { value: "2" } });
    fireEvent.click(screen.getByRole("button", { name: "Crea unità" }));

    await waitFor(() => {
      expect(mocks.createOrgAssignment).toHaveBeenCalledWith("token", expect.objectContaining({
        user_id: 2,
        org_unit_id: "u3",
        title: "Capo reparto",
        position_code: "capo_reparto",
      }), "organigramma");
    });
  });

  test("opens generic unit creation from the tree workspace", async () => {
    render(<OrganigrammaPage />);

    fireEvent.click(await screen.findByRole("button", { name: /Albero/i }));
    fireEvent.click(screen.getByRole("button", { name: "+ Nuova unità" }));

    expect(await screen.findByRole("dialog")).toHaveTextContent("Nuova unità organizzativa");
  });

  test("switches back to schema and clears an operator drag without assigning it", async () => {
    render(<OrganigrammaPage />);
    await screen.findByTestId("unassigned-user-2");
    fireEvent.click(screen.getByRole("button", { name: "Albero" }));
    fireEvent.click(screen.getByRole("button", { name: "Schema" }));
    const operator = await screen.findByTestId("unassigned-user-2");
    fireEvent.dragStart(operator);
    fireEvent.dragEnd(operator);
    expect(screen.getByText("Schema organigramma")).toBeInTheDocument();
    expect(mocks.createOrgAssignment).not.toHaveBeenCalled();
  });

  test("renders the server loading state without accessing browser authentication", () => {
    const browserWindow = window;
    vi.stubGlobal("window", undefined);
    try {
      expect(renderToString(<OrganigrammaWorkspace />)).toContain("Caricamento");
      expect(mocks.getStoredAccessToken).not.toHaveBeenCalled();
      expect(mocks.getOrgTree).not.toHaveBeenCalled();
    } finally {
      vi.stubGlobal("window", browserWindow);
    }
  });

  test("does not persist layout or sync when the browser session disappears after loading", async () => {
    const rendered = render(<OrganigrammaWorkspace />);
    await enableFreeSchemaEditMode();
    const treeRequests = mocks.getOrgTree.mock.calls.length;
    mocks.getStoredAccessToken.mockReturnValue(null);
    rendered.rerender(<OrganigrammaWorkspace />);
    expect(await screen.findByText("Sessione non disponibile.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Sync WhiteCompany" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Esporta JSON" })).not.toBeInTheDocument();
    expect(mocks.syncOrgWhiteCompany).not.toHaveBeenCalled();
    expect(mocks.exportOrganigrammaSnapshot).not.toHaveBeenCalled();
    expect(mocks.updateOrgUnit).not.toHaveBeenCalled();
    expect(mocks.getOrgTree).toHaveBeenCalledTimes(treeRequests);
    mocks.getStoredAccessToken.mockReturnValue("new-token");
    rendered.rerender(<OrganigrammaWorkspace />);
    expect(await screen.findByTestId("schema-node-u1")).toBeInTheDocument();
    expect(mocks.getOrgTree).toHaveBeenLastCalledWith("new-token", "organigramma");
  });

  test("rejects a sector whose parent is a reparto", async () => {
    const reparto = treeNode("u3", "Reparto Pompe", "reparto", "u2");
    mocks.getOrgTree.mockResolvedValue([
      treeNode("u1", "Direzione Generale", "direzione", null, [
        treeNode("u2", "Settore Idraulico", "settore", "u1", [reparto]),
      ]),
    ]);
    render(<OrganigrammaPage />);

    expect(await screen.findByText("Schema organigramma")).toBeInTheDocument();
    fireEvent.click(screen.getAllByRole("button", { name: "+ Nuovo settore" })[0]!);
    fireEvent.change(screen.getByLabelText("Nome"), { target: { value: "Settore non valido" } });
    fireEvent.change(screen.getByLabelText("Unità padre"), { target: { value: "u3" } });
    fireEvent.click(screen.getByRole("button", { name: "Crea unità" }));

    expect(await screen.findByText("Un settore non può essere creato sotto un reparto o una squadra.")).toBeInTheDocument();
    expect(mocks.createOrgUnit).not.toHaveBeenCalled();
  });
});
