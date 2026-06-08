import { fireEvent, render, screen, waitFor } from "@testing-library/react";
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
  getOrgTree: vi.fn(),
  getOrgUnit: vi.fn(),
  getOrgOverrides: vi.fn(),
  getOrgVisibility: vi.fn(),
  getOrgAssignments: vi.fn(),
  createOrgOverride: vi.fn(),
  syncOrgWhiteCompany: vi.fn(),
  listAllApplicationUsers: vi.fn(),
}));

vi.mock("@/lib/auth", () => ({ getStoredAccessToken: mocks.getStoredAccessToken }));

vi.mock("@/lib/api", () => ({
  getOrgTree: mocks.getOrgTree,
  getOrgUnit: mocks.getOrgUnit,
  getOrgOverrides: mocks.getOrgOverrides,
  getOrgVisibility: mocks.getOrgVisibility,
  getOrgAssignments: mocks.getOrgAssignments,
  createOrgOverride: mocks.createOrgOverride,
  syncOrgWhiteCompany: mocks.syncOrgWhiteCompany,
  listAllApplicationUsers: mocks.listAllApplicationUsers,
  isAuthError: () => false,
}));

vi.mock("@/components/app/protected-page", () => ({
  ProtectedPage: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

function treeNode(id: string, nome: string, tipo: OrgUnitTreeNode["tipo"], parent: string | null, children: OrgUnitTreeNode[] = [], personCount = 0): OrgUnitTreeNode {
  return {
    id, nome, tipo, parent_id: parent, source: "whitecompany", wc_area_id: null, legacy_team_id: null,
    is_active: true, sort_order: 0, person_count: personCount, child_count: children.length, children,
  };
}

const settore = treeNode("u2", "Settore Idraulico", "settore", "u1", [], 1);
const direzione = treeNode("u1", "Direzione Generale", "direzione", null, [settore], 0);

const detail: OrgUnitDetail = {
  unit: { id: "u1", nome: "Direzione Generale", tipo: "direzione", parent_id: null, is_active: true, sort_order: 0, source: "manuale", wc_area_id: null, legacy_team_id: null, created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z" },
  path: [{ id: "u1", nome: "Direzione Generale", tipo: "direzione", parent_id: null, is_active: true, sort_order: 0, source: "manuale", wc_area_id: null, legacy_team_id: null, created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z" }],
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
    mocks.getOrgTree.mockResolvedValue([direzione]);
    mocks.listAllApplicationUsers.mockResolvedValue(users);
    mocks.getOrgOverrides.mockResolvedValue([]);
    mocks.getOrgUnit.mockResolvedValue(detail);
    mocks.getOrgVisibility.mockResolvedValue(visibility);
    mocks.getOrgAssignments.mockResolvedValue(detail.assignments);
  });

  test("renders tree and selected unit detail", async () => {
    render(<OrganigrammaPage />);

    expect(await screen.findByText("Albero organizzativo")).toBeInTheDocument();
    // tree node + detail responsabile
    expect(screen.getAllByText("Direzione Generale").length).toBeGreaterThan(0);
    expect((await screen.findAllByText("Mario Sanna")).length).toBeGreaterThan(0);
    expect(screen.getByText("Responsabile unità")).toBeInTheDocument();
  });

  test("switches to 'Chi vede chi' and shows effective visibility", async () => {
    render(<OrganigrammaPage />);
    await screen.findByText("Albero organizzativo");

    fireEvent.click(screen.getByRole("button", { name: /Chi vede chi/i }));

    await waitFor(() => expect(mocks.getOrgVisibility).toHaveBeenCalled());
    expect(await screen.findByText("Insieme effettivo di unità")).toBeInTheDocument();
    expect(screen.getByText("Unità visibili")).toBeInTheDocument();
  });
});
