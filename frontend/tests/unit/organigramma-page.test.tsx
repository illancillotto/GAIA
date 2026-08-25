import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import OrganigrammaPage from "@/app/organigramma/page";
import type {
  ApplicationUser,
  OrgUnitDetail,
  OrgUnitTreeNode,
  OrgVisibilityResult,
} from "@/types/api";

const mocks = vi.hoisted(() => ({
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
  isAuthError: () => false,
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
    vi.clearAllMocks();
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

  test("switches to 'Chi vede chi' and shows effective visibility", async () => {
    render(<OrganigrammaPage />);
    await screen.findByText("Schema organigramma");

    fireEvent.click(screen.getByRole("button", { name: /Chi vede chi/i }));

    await waitFor(() => expect(mocks.getOrgVisibility).toHaveBeenCalled());
    expect(await screen.findByText("Insieme effettivo di unità")).toBeInTheDocument();
    expect(screen.getByText("Unità visibili")).toBeInTheDocument();
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
