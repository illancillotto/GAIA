import { beforeEach, describe, expect, test, vi } from "vitest";

import { handleAssignUserToUnit, handleCreateUnit, handleDeleteUnit, handleDetachAssignment, handleMoveNode, performSchemaLink } from "@/features/organigramma/organigramma-mutations";
import type { OrganigrammaMutationContext } from "@/features/organigramma/organigramma-mutation-context";
import type { ApplicationUser, OrgAssignment, OrgUnitCreateInput, OrgUnitTreeNode } from "@/types/api";

const api = vi.hoisted(() => ({
  createOrgAssignment: vi.fn(), createOrgUnit: vi.fn(), deleteOrgAssignment: vi.fn(),
  deleteOrgUnit: vi.fn(), updateOrgAssignment: vi.fn(), updateOrgUnit: vi.fn(),
}));
vi.mock("@/lib/api", () => api);

const unit: OrgUnitTreeNode = {
  id: "unit", nome: "Settore", tipo: "settore", parent_id: "parent",
  canvas_x: 240, canvas_y: 360, source: "manuale", is_active: true,
  wc_area_id: null, legacy_team_id: null, sort_order: 0, person_count: 0,
  child_count: 0, children: [],
};
const user = { id: 2, username: "utente", full_name: "Nome Utente", is_active: true } as ApplicationUser;
const input: OrgUnitCreateInput = { nome: "Nuova", tipo: "settore", parent_id: "unit", source: "manuale", is_active: true };
const assignment = { id: "assignment", org_unit_id: "unit", user_id: 3 } as OrgAssignment;

function context() {
  return {
    token: "token", canModifyStructure: true, schemaEditEnabled: true,
    structureKind: "organigramma" as const, entityLabel: "organigramma",
    flatTree: [unit], users: [user], allAssignments: [assignment],
    assignedUserIds: new Set<number>(),
    schemaMeta: new Map<string, { lead: OrgAssignment | null; descendantIds: Set<string>; directPeople: number }>([
      ["unit", { lead: null, descendantIds: new Set(["unit"]), directPeople: 0 }],
    ]),
    refreshStructure: vi.fn().mockResolvedValue(undefined), setNotice: vi.fn(),
    setSelectedId: vi.fn(), setMultiSelectedIds: vi.fn(), setDraggingNodeId: vi.fn(),
    setDraggingUserId: vi.fn(), setCreateUnitPreset: vi.fn(), setSchemaContextMenu: vi.fn(), setDetail: vi.fn(),
  } satisfies OrganigrammaMutationContext;
}

beforeEach(() => {
  vi.resetAllMocks();
  for (const mock of Object.values(api)) mock.mockResolvedValue(undefined);
  api.createOrgUnit.mockResolvedValue({ ...unit, id: "created", nome: "Nuova" });
  vi.stubGlobal("confirm", vi.fn(() => true));
});

describe("mutation access contracts", () => {
  const operations = [
    ["move", (state: OrganigrammaMutationContext) => handleMoveNode(state, "unit", "parent")],
    ["link", (state: OrganigrammaMutationContext) => performSchemaLink(state, "unit", "parent", "above")],
    ["assign", (state: OrganigrammaMutationContext) => handleAssignUserToUnit(state, 2, "unit", "member")],
    ["detach", (state: OrganigrammaMutationContext) => handleDetachAssignment(state, "assignment")],
    ["delete", (state: OrganigrammaMutationContext) => handleDeleteUnit(state, "unit")],
    ["create", (state: OrganigrammaMutationContext) => handleCreateUnit(state, input, null)],
  ] as const;

  test.each(operations)("%s rejects missing token and missing permission without effects", async (_name, run) => {
    for (const patch of [{ token: null }, { canModifyStructure: false }]) {
      const state = { ...context(), ...patch };
      await run(state);
      expect(state.setNotice).not.toHaveBeenCalled();
      expect(state.refreshStructure).not.toHaveBeenCalled();
      for (const mock of Object.values(api)) expect(mock).not.toHaveBeenCalled();
    }
  });

  test.each(operations.slice(0, 5))("%s rejects edit-disabled state", async (_name, run) => {
    const state = { ...context(), schemaEditEnabled: false };
    await run(state);
    for (const mock of Object.values(api)) expect(mock).not.toHaveBeenCalled();
    expect(state.setNotice).not.toHaveBeenCalled();
  });
});

describe("hierarchy mutations", () => {
  test("rejects self-moves and descendant moves before clearing drag state", async () => {
    const state = context();
    state.schemaMeta.get("unit")!.descendantIds.add("child");
    await handleMoveNode(state, "unit", "unit");
    await handleMoveNode(state, "unit", "child");
    expect(api.updateOrgUnit).not.toHaveBeenCalled();
    expect(state.setNotice).toHaveBeenLastCalledWith("Operazione non valida: non puoi spostare un nodo dentro un suo discendente.");
    expect(state.setDraggingNodeId).not.toHaveBeenCalled();
  });

  test.each(["parent", null])("moves to %s in API/selection/refresh order", async (parentId) => {
    const state = context();
    await handleMoveNode(state, "unit", parentId);
    expect(api.updateOrgUnit).toHaveBeenCalledWith("token", "unit", { parent_id: parentId }, "organigramma");
    expect(state.setSelectedId).toHaveBeenCalledWith("unit");
    expect(state.refreshStructure.mock.invocationCallOrder[0]).toBeGreaterThan(state.setSelectedId.mock.invocationCallOrder[0]!);
    expect(state.setNotice).toHaveBeenLastCalledWith(parentId ? "Gerarchia aggiornata." : "Nodo spostato in radice.");
    expect(state.setDraggingNodeId).toHaveBeenCalledWith(null);
    expect(state.setDraggingUserId).toHaveBeenCalledWith(null);
  });

  test("preserves API behavior for missing source metadata", async () => {
    const state = context();
    await handleMoveNode(state, "missing", "parent");
    expect(api.updateOrgUnit).toHaveBeenCalledWith("token", "missing", { parent_id: "parent" }, "organigramma");
  });

  test("rejects both link cycles and self-links", async () => {
    const state = context();
    state.schemaMeta.get("unit")!.descendantIds.add("child");
    expect(await performSchemaLink(state, "unit", "unit", "above")).toBe(false);
    expect(await performSchemaLink(state, "unit", "child", "below")).toBe(false);
    expect(await performSchemaLink(state, "child", "unit", "above")).toBe(false);
    expect(api.updateOrgUnit).not.toHaveBeenCalled();
    expect(state.setNotice).toHaveBeenLastCalledWith("Collegamento non valido: il blocco destinazione non può finire sotto un suo discendente.");
  });

  test.each(["above", "below"] as const)("links %s without requiring metadata for both nodes", async (mode) => {
    const state = context();
    expect(await performSchemaLink(state, "unit", "missing", mode)).toBe(true);
    expect(api.updateOrgUnit).toHaveBeenCalledWith("token", mode === "below" ? "unit" : "missing", { parent_id: mode === "below" ? "missing" : "unit" }, "organigramma");
    expect(state.setSelectedId).toHaveBeenCalledWith("unit");
    expect(state.setNotice).toHaveBeenLastCalledWith("Collegamento aggiornato.");
    expect(state.refreshStructure).toHaveBeenCalledTimes(1);
  });

  test("preserves below linking without source metadata", async () => {
    const state = context();
    expect(await performSchemaLink(state, "missing", "unit", "below")).toBe(true);
    expect(api.updateOrgUnit).toHaveBeenCalledWith("token", "missing", { parent_id: "unit" }, "organigramma");
  });
});

describe("assignment mutations", () => {
  test("rejects unknown users and units without effects", async () => {
    const state = context();
    await handleAssignUserToUnit(state, 2, "missing", "member");
    await handleAssignUserToUnit(state, 99, "unit", "member");
    expect(api.createOrgAssignment).not.toHaveBeenCalled();
    expect(state.setDraggingUserId).not.toHaveBeenCalled();
  });

  test("rejects an already assigned user and an occupied lead", async () => {
    const state = context();
    state.assignedUserIds.add(2);
    await handleAssignUserToUnit(state, 2, "unit", "member");
    expect(state.setNotice).toHaveBeenLastCalledWith("Questo utente risulta già assegnato a una unità.");
    state.assignedUserIds.clear();
    state.schemaMeta.get("unit")!.lead = assignment;
    await handleAssignUserToUnit(state, 2, "unit", "lead");
    expect(state.setNotice).toHaveBeenLastCalledWith("L'unità ha già un responsabile diretto. Spostalo o sostituiscilo prima di assegnarne un altro.");
    expect(api.createOrgAssignment).not.toHaveBeenCalled();
    expect(state.setDraggingUserId).toHaveBeenCalledTimes(2);
  });

  test.each(["lead", "member"] as const)("assigns %s with canonical payload and manager propagation", async (mode) => {
    const state = context();
    await handleAssignUserToUnit(state, 2, "unit", mode);
    expect(api.createOrgAssignment).toHaveBeenCalledWith("token", expect.objectContaining({ user_id: 2, org_unit_id: "unit", manager_user_id: null, is_primary: mode === "lead" }), "organigramma");
    if (mode === "lead") {
      expect(api.updateOrgAssignment).toHaveBeenCalledWith("token", "assignment", { manager_user_id: 2 }, "organigramma");
    } else {
      expect(api.updateOrgAssignment).not.toHaveBeenCalled();
    }
    expect(state.setNotice).toHaveBeenLastCalledWith(mode === "lead" ? "Nome Utente impostato come responsabile di Settore." : "Nome Utente assegnato a Settore.");
    expect(state.refreshStructure).toHaveBeenCalledTimes(1);
    expect(state.setDraggingUserId).toHaveBeenCalledWith(null);
  });

  test.each(["lead", "member"] as const)("uses the username for %s without full name or metadata", async (mode) => {
    const state = context();
    state.users = [{ ...user, full_name: null }];
    state.schemaMeta.clear();
    await handleAssignUserToUnit(state, 2, "unit", mode);
    expect(state.setNotice).toHaveBeenLastCalledWith(mode === "lead" ? "utente impostato come responsabile di Settore." : "utente assegnato a Settore.");
  });

  test("detaches before refreshing", async () => {
    const state = context();
    await handleDetachAssignment(state, "assignment");
    expect(api.deleteOrgAssignment).toHaveBeenCalledWith("token", "assignment", "organigramma");
    expect(state.setNotice).toHaveBeenLastCalledWith("Assegnazione rimossa da organigramma.");
    expect(state.refreshStructure).toHaveBeenCalledTimes(1);
  });
});

describe("unit lifecycle", () => {
  test.each([
    ["unit", undefined, undefined, 560, 580],
    [null, undefined, undefined, 120, 160],
    ["missing", undefined, undefined, 120, 160],
    ["unit", 0, 0, 0, 0],
  ] as const)("preserves seed positions (%s, %s, %s)", async (parentId, canvasX, canvasY, expectedX, expectedY) => {
    const state = context();
    await handleCreateUnit(state, { ...input, parent_id: parentId, canvas_x: canvasX, canvas_y: canvasY }, null);
    expect(api.createOrgUnit).toHaveBeenCalledWith("token", expect.objectContaining({ parent_id: parentId, canvas_x: expectedX, canvas_y: expectedY }), "organigramma");
    expect(api.createOrgAssignment).not.toHaveBeenCalled();
    expect(state.setCreateUnitPreset).toHaveBeenCalledWith(null);
    expect(state.setSelectedId).toHaveBeenCalledWith("created");
    expect(state.setNotice).toHaveBeenLastCalledWith("Unità Nuova creata correttamente.");
    expect(state.refreshStructure).toHaveBeenCalledTimes(1);
  });

  test("creates the initial lead after the unit, even with edit disabled", async () => {
    const state = { ...context(), schemaEditEnabled: false };
    await handleCreateUnit(state, input, 2);
    expect(api.createOrgAssignment).toHaveBeenCalledWith("token", expect.objectContaining({ user_id: 2, org_unit_id: "created", position_code: "capo_settore", manager_user_id: null }), "organigramma");
    expect(api.createOrgAssignment.mock.invocationCallOrder[0]).toBeGreaterThan(api.createOrgUnit.mock.invocationCallOrder[0]!);
  });

  test("refuses deletion without node or metadata and with children or direct people", async () => {
    const state = context();
    await handleDeleteUnit(state, "missing");
    state.schemaMeta.clear();
    await handleDeleteUnit(state, "unit");
    state.schemaMeta.set("unit", { lead: null, descendantIds: new Set(["unit", "child"]), directPeople: 0 });
    await handleDeleteUnit(state, "unit");
    expect(state.setNotice).toHaveBeenLastCalledWith("Non puoi eliminare un blocco che contiene sotto-unità. Scollega o rimuovi prima i blocchi figli.");
    state.schemaMeta.set("unit", { lead: null, descendantIds: new Set(["unit"]), directPeople: 1 });
    await handleDeleteUnit(state, "unit");
    expect(state.setNotice).toHaveBeenLastCalledWith("Non puoi eliminare un blocco con assegnazioni dirette. Rimuovi prima le persone assegnate.");
    expect(window.confirm).not.toHaveBeenCalled();
    expect(api.deleteOrgUnit).not.toHaveBeenCalled();
  });

  test("respects cancelled confirmation", async () => {
    vi.mocked(window.confirm).mockReturnValue(false);
    const state = context();
    await handleDeleteUnit(state, "unit");
    expect(window.confirm).toHaveBeenCalledWith("Eliminare definitivamente il blocco “Settore”?");
    expect(api.deleteOrgUnit).not.toHaveBeenCalled();
    expect(state.refreshStructure).not.toHaveBeenCalled();
  });

  test("deletes and cleans only the deleted selection before refresh", async () => {
    const state = context();
    await handleDeleteUnit(state, "unit");
    expect(api.deleteOrgUnit).toHaveBeenCalledWith("token", "unit", "organigramma");
    expect(state.setSchemaContextMenu).toHaveBeenCalledWith(null);
    expect(state.setDetail).toHaveBeenCalledWith(null);
    const select = state.setSelectedId.mock.calls[0]![0] as (previous: string | null) => string | null;
    expect(select("unit")).toBeNull();
    expect(select("other")).toBe("other");
    const multiSelect = state.setMultiSelectedIds.mock.calls[0]![0] as (previous: Set<string>) => Set<string>;
    const selected = new Set(["unit", "other"]);
    expect(multiSelect(selected)).toEqual(new Set(["other"]));
    expect(selected).toEqual(new Set(["unit", "other"]));
    const unchanged = new Set(["other"]);
    expect(multiSelect(unchanged)).toBe(unchanged);
    expect(state.setNotice).toHaveBeenLastCalledWith("Blocco “Settore” eliminato da organigramma.");
    expect(state.refreshStructure).toHaveBeenCalledTimes(1);
  });
});

describe("mutation error contracts", () => {
  const operations = [
    ["move", "updateOrgUnit", "Aggiornamento gerarchia non riuscito", (state: OrganigrammaMutationContext) => handleMoveNode(state, "unit", "parent")],
    ["link", "updateOrgUnit", "Aggiornamento collegamento non riuscito", (state: OrganigrammaMutationContext) => performSchemaLink(state, "unit", "parent", "above")],
    ["assign", "createOrgAssignment", "Assegnazione non riuscita", (state: OrganigrammaMutationContext) => handleAssignUserToUnit(state, 2, "unit", "member")],
    ["create", "createOrgUnit", "Creazione unità non riuscita", (state: OrganigrammaMutationContext) => handleCreateUnit(state, input, null)],
    ["detach", "deleteOrgAssignment", "Rimozione assegnazione non riuscita", (state: OrganigrammaMutationContext) => handleDetachAssignment(state, "assignment")],
    ["delete", "deleteOrgUnit", "Eliminazione blocco non riuscita", (state: OrganigrammaMutationContext) => handleDeleteUnit(state, "unit")],
  ] as const;

  test.each(operations)("%s preserves Error and non-Error notices", async (name, apiMethod, fallback, run) => {
    for (const failure of [new Error("Errore remoto"), "failure"]) {
      const state = context();
      api[apiMethod].mockRejectedValueOnce(failure);
      const result = await run(state);
      expect(state.setNotice).toHaveBeenLastCalledWith(failure instanceof Error ? failure.message : fallback);
      expect(state.refreshStructure).not.toHaveBeenCalled();
      if (name === "link") expect(result).toBe(false);
      if (name === "move" || name === "assign") expect(state.setDraggingUserId).toHaveBeenCalledWith(null);
      if (name === "create") expect(state.setCreateUnitPreset).not.toHaveBeenCalled();
      if (name === "delete") expect(state.setDetail).not.toHaveBeenCalled();
    }
  });

  test.each(operations)("%s reports refresh failures after the mutation without undoing it", async (name, apiMethod, _fallback, run) => {
    const state = context();
    state.refreshStructure.mockRejectedValueOnce(new Error("Refresh rifiutato"));
    await run(state);
    expect(api[apiMethod]).toHaveBeenCalledTimes(1);
    expect(state.setNotice).toHaveBeenLastCalledWith("Refresh rifiutato");
    if (name === "create") expect(state.setCreateUnitPreset).toHaveBeenCalledWith(null);
    if (name === "delete") expect(state.setDetail).toHaveBeenCalledWith(null);
  });

  test.each(operations)("%s forwards the territorial structure kind", async (_name, apiMethod, _fallback, run) => {
    const state = { ...context(), structureKind: "territoriale" as const, entityLabel: "assegnazione territoriale" };
    await run(state);
    const call = api[apiMethod].mock.calls[0]!;
    expect(call[0]).toBe("token");
    expect(call.at(-1)).toBe("territoriale");
  });

  test("keeps a created unit when its initial assignment fails", async () => {
    const state = context();
    api.createOrgAssignment.mockRejectedValueOnce(new Error("Responsabile rifiutato"));
    await handleCreateUnit(state, input, 2);
    expect(api.createOrgUnit).toHaveBeenCalledTimes(1);
    expect(api.deleteOrgUnit).not.toHaveBeenCalled();
    expect(state.setCreateUnitPreset).not.toHaveBeenCalled();
    expect(state.setNotice).toHaveBeenLastCalledWith("Responsabile rifiutato");
  });

  test("does not refresh when updating direct reports fails", async () => {
    const state = context();
    api.updateOrgAssignment.mockRejectedValueOnce(new Error("Manager rifiutato"));
    await handleAssignUserToUnit(state, 2, "unit", "lead");
    expect(api.createOrgAssignment).toHaveBeenCalledTimes(1);
    expect(state.refreshStructure).not.toHaveBeenCalled();
    expect(state.setNotice).toHaveBeenLastCalledWith("Manager rifiutato");
    expect(state.setDraggingUserId).toHaveBeenCalledWith(null);
  });
});
