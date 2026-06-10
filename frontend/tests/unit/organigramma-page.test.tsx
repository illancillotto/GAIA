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
  createOrgUnit: vi.fn(),
  deleteOrgAssignment: vi.fn(),
  createOrgOverride: vi.fn(),
  syncOrgWhiteCompany: vi.fn(),
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
  createOrgUnit: mocks.createOrgUnit,
  deleteOrgAssignment: mocks.deleteOrgAssignment,
  createOrgOverride: mocks.createOrgOverride,
  syncOrgWhiteCompany: mocks.syncOrgWhiteCompany,
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
      is_primary: true, active: true, valid_from: null, valid_to: null, source: "manuale", wc_operator_id: null,
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
    mocks.updateOrgUnit.mockResolvedValue(detail.unit);
  });

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

  test("switches to schema view and links a block below another using arrows", async () => {
    render(<OrganigrammaPage />);

    expect(await screen.findByText("Schema organigramma")).toBeInTheDocument();
    expect(mocks.updateOrgUnit).not.toHaveBeenCalled();

    fireEvent.click(screen.getAllByLabelText("Abilita modifica")[0]!);

    const sourceNode = await screen.findByTestId("schema-node-u2");
    const targetNode = await screen.findByTestId("schema-node-u1");
    const downButton = within(sourceNode).getByRole("button", { name: "↓" });

    fireEvent.click(downButton);
    fireEvent.mouseDown(targetNode);

    await waitFor(() => {
      expect(mocks.updateOrgUnit).toHaveBeenCalledWith("token", "u2", { parent_id: "u1" });
    });
  });

  test("applies vertical and horizontal layouts from schema controls", async () => {
    render(<OrganigrammaPage />);

    expect(await screen.findByText("Schema organigramma")).toBeInTheDocument();
    mocks.updateOrgUnit.mockClear();

    fireEvent.click(screen.getAllByLabelText("Abilita modifica")[0]!);
    fireEvent.click(screen.getByRole("button", { name: "Orizzontale" }));

    await waitFor(() => {
      expect(mocks.updateOrgUnit).toHaveBeenCalledWith(
        "token",
        expect.any(String),
        expect.objectContaining({
          canvas_x: expect.any(Number),
          canvas_y: expect.any(Number),
        }),
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
      );
    });
  });

  test("detaches a schema block from its parent using the dedicated action", async () => {
    render(<OrganigrammaPage />);

    expect(await screen.findByText("Schema organigramma")).toBeInTheDocument();
    fireEvent.click(screen.getAllByLabelText("Abilita modifica")[0]!);

    const sourceNode = await screen.findByTestId("schema-node-u2");
    const detachButton = within(sourceNode).getByRole("button", { name: /Scollega/i });

    fireEvent.click(detachButton);

    await waitFor(() => {
      expect(mocks.updateOrgUnit).toHaveBeenCalledWith("token", "u2", { parent_id: null });
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
      expect(mocks.updateOrgUnit).toHaveBeenCalledWith("token", "u2", { parent_id: "u1" });
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
        is_primary: false,
        active: true,
        source: "manuale",
      });
    });
  });
});
