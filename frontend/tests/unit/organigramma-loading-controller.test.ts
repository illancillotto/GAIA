import { beforeEach, describe, expect, test, vi } from "vitest";

import { loadCore, refreshStructure } from "@/features/organigramma/organigramma-loading-controller";
import type { OrganigrammaLoadingContext } from "@/features/organigramma/organigramma-loading-context";
import type { CurrentUser, OrgUnitDetail, OrgUnitTreeNode } from "@/types/api";

const api = vi.hoisted(() => ({ getCurrentUser: vi.fn(), getOrgTree: vi.fn(), listAllApplicationUsers: vi.fn(), getOrgAssignments: vi.fn(), getOrgOverrides: vi.fn(), getOrgUnit: vi.fn(), isAuthError: vi.fn() }));
vi.mock("@/lib/api", () => api);

const root: OrgUnitTreeNode = { id: "root", nome: "Direzione", tipo: "direzione", parent_id: null, children: [], source: "manuale", is_active: true, wc_area_id: null, legacy_team_id: null, sort_order: 0, person_count: 0, child_count: 0, canvas_x: 120, canvas_y: 120 };
const user = { id: 1, role: "super_admin" } as CurrentUser;
const detail = { unit: root, assignments: [] } as unknown as OrgUnitDetail;

function context() {
  return { token: "token" as string | null, structureKind: "territoriale" as const, selectedId: "root" as string | null,
    setError: vi.fn(), setLoading: vi.fn(), setCurrentUser: vi.fn(), setTree: vi.fn(), setUsers: vi.fn(), setAllAssignments: vi.fn(),
    setExpanded: vi.fn(), setSelectedId: vi.fn(), setOverrides: vi.fn(), setCanManage: vi.fn(), setDetail: vi.fn(), setNotice: vi.fn(),
  } satisfies OrganigrammaLoadingContext;
}

beforeEach(() => {
  vi.resetAllMocks();
  api.getCurrentUser.mockResolvedValue(user);
  api.getOrgTree.mockResolvedValue([root]);
  api.listAllApplicationUsers.mockResolvedValue([]);
  api.getOrgAssignments.mockResolvedValue([]);
  api.getOrgOverrides.mockResolvedValue([]);
  api.getOrgUnit.mockResolvedValue(detail);
  api.isAuthError.mockReturnValue(false);
});

describe("initial loading", () => {
  test("rejects a missing session before contacting any API", async () => {
    const state = { ...context(), token: null };
    await loadCore(state);
    expect(state.setError).toHaveBeenCalledWith("Sessione non disponibile.");
    expect(state.setLoading.mock.calls).toEqual([[false]]);
    expect(api.getCurrentUser).not.toHaveBeenCalled();
    expect(api.getOrgTree).not.toHaveBeenCalled();
    expect(state.setTree).not.toHaveBeenCalled();
  });

  test.each(["super_admin", "viewer"])("loads the catalogs and grants editing only to super admins (%s)", async (role) => {
    const state = context();
    const sessionUser = { ...user, role };
    api.getCurrentUser.mockResolvedValue(sessionUser);
    await loadCore(state);
    expect(api.getCurrentUser).toHaveBeenCalledWith("token");
    expect(api.getOrgTree).toHaveBeenCalledWith("token", "territoriale");
    expect(api.getOrgAssignments).toHaveBeenCalledWith("token", { structureKind: "territoriale" });
    expect(api.listAllApplicationUsers).toHaveBeenCalledWith("token");
    expect(api.getOrgOverrides).toHaveBeenCalledWith("token", "territoriale");
    expect(state.setCurrentUser).toHaveBeenCalledWith(sessionUser);
    expect(state.setTree).toHaveBeenCalledWith([root]);
    expect(state.setUsers).toHaveBeenCalledWith([]);
    expect(state.setAllAssignments).toHaveBeenCalledWith([]);
    expect(state.setCanManage).toHaveBeenCalledWith(role === "super_admin");
    expect(state.setLoading.mock.calls).toEqual([[true], [false]]);
    expect(state.setError).toHaveBeenCalledWith(null);
    const select = state.setSelectedId.mock.calls[0]![0] as (previous: string | null) => string;
    expect(select(null)).toBe("root");
    expect(select("existing-selection")).toBe("existing-selection");
  });

  test("does not invent a selection for an empty forest", async () => {
    const state = context();
    api.getOrgTree.mockResolvedValue([]);
    await loadCore(state);
    expect(state.setTree).toHaveBeenCalledWith([]);
    expect(state.setExpanded).not.toHaveBeenCalled();
    expect(state.setSelectedId).not.toHaveBeenCalled();
    expect(state.setError).toHaveBeenCalledWith(null);
  });

  test("expands only the first three nodes without mutating the API forest", async () => {
    const state = context();
    const forest = [root, ...Array.from({ length: 3 }, (_unused, index) => ({ ...root, id: `root-${index}` }))];
    api.getOrgTree.mockResolvedValue(forest);
    await loadCore(state);
    expect(state.setExpanded).toHaveBeenCalledWith(new Set(["root", "root-0", "root-1"]));
    expect(forest.map(node => node.id)).toEqual(["root", "root-0", "root-1", "root-2"]);
  });

  test.each([false, true])("preserves the override catalog on auth failure but clears non-auth failures (auth=%s)", async (authFailure) => {
    const state = context();
    const failure = new Error("Catalogo rifiutato");
    api.getOrgOverrides.mockRejectedValue(failure);
    api.isAuthError.mockReturnValue(authFailure);
    await loadCore(state);
    expect(api.isAuthError).toHaveBeenCalledWith(failure);
    if (authFailure) expect(state.setOverrides).not.toHaveBeenCalled();
    else expect(state.setOverrides).toHaveBeenCalledWith([]);
    expect(state.setTree).toHaveBeenCalledWith([root]);
    expect(state.setLoading).toHaveBeenLastCalledWith(false);
  });

  test.each(["getCurrentUser", "getOrgTree", "listAllApplicationUsers", "getOrgAssignments"] as const)("does not partially publish catalogs when %s fails", async (endpoint) => {
    const state = context();
    api[endpoint].mockRejectedValue(new Error("API indisponibile"));
    await loadCore(state);
    expect(state.setError).toHaveBeenCalledWith("API indisponibile");
    expect(state.setTree).not.toHaveBeenCalled();
    expect(state.setUsers).not.toHaveBeenCalled();
    expect(state.setAllAssignments).not.toHaveBeenCalled();
    expect(state.setCurrentUser).not.toHaveBeenCalled();
    expect(state.setCanManage).not.toHaveBeenCalled();
    expect(state.setLoading).toHaveBeenLastCalledWith(false);
  });

  test("normalizes a non-Error rejection and always ends loading", async () => {
    const state = context();
    api.getOrgTree.mockRejectedValue("server failure");
    await loadCore(state);
    expect(state.setError).toHaveBeenCalledWith("Errore di caricamento");
    expect(state.setLoading.mock.calls).toEqual([[true], [false]]);
  });
});

describe("lightweight refresh", () => {
  test("does not refresh an expired session or alter existing data", async () => {
    const state = { ...context(), token: null };
    await refreshStructure(state);
    expect(api.getOrgTree).not.toHaveBeenCalled();
    expect(state.setTree).not.toHaveBeenCalled();
    expect(state.setDetail).not.toHaveBeenCalled();
  });

  test.each([null, "root"])("refreshes catalogs and only the currently selected detail (%s)", async (selectedId) => {
    const state = { ...context(), selectedId };
    await refreshStructure(state);
    expect(api.getOrgTree).toHaveBeenCalledWith("token", "territoriale");
    expect(api.getOrgAssignments).toHaveBeenCalledWith("token", { structureKind: "territoriale" });
    expect(state.setTree).toHaveBeenCalledWith([root]);
    expect(state.setAllAssignments).toHaveBeenCalledWith([]);
    expect(state.setLoading).not.toHaveBeenCalled();
    expect(api.getCurrentUser).not.toHaveBeenCalled();
    if (selectedId) {
      expect(api.getOrgUnit).toHaveBeenCalledWith("token", selectedId, "territoriale");
      expect(state.setDetail).toHaveBeenCalledWith(detail);
    } else expect(api.getOrgUnit).not.toHaveBeenCalled();
  });

  test("retains refreshed catalogs when the selected unit was deleted", async () => {
    const state = context();
    api.getOrgUnit.mockRejectedValue(new Error("404"));
    await refreshStructure(state);
    expect(state.setTree).toHaveBeenCalledWith([root]);
    expect(state.setDetail).not.toHaveBeenCalled();
    expect(state.setNotice).not.toHaveBeenCalled();
  });

  test.each([new Error("Refresh rifiutato"), "remote failure"])("does not partially refresh after a catalog failure (%s)", async (failure) => {
    const state = context();
    api.getOrgAssignments.mockRejectedValue(failure);
    await refreshStructure(state);
    expect(state.setTree).not.toHaveBeenCalled();
    expect(state.setAllAssignments).not.toHaveBeenCalled();
    expect(api.getOrgUnit).not.toHaveBeenCalled();
    expect(state.setNotice).toHaveBeenCalledWith(failure instanceof Error ? failure.message : "Aggiornamento dati non riuscito");
  });
});
