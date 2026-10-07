import { beforeEach, describe, expect, test, vi } from "vitest";

import { handleApplyTreeLayout, handleCompactVisibleArea, realignExpandedSubtree, resolveSectorParentId } from "@/features/organigramma/organigramma-layout-controller";
import type { OrganigrammaLayoutContext } from "@/features/organigramma/organigramma-layout-context";
import { applyCanvasPositionsToForest, computeHorizontalTreeLayout, computeVerticalTreeLayout, resolveSubtreeCollisionShift, safeCanvasCoord, updateTreeNodeInForest } from "@/features/organigramma/organigramma-workspace";
import { flattenTree } from "@/lib/organigramma";
import type { OrgUnitTreeNode } from "@/types/api";

const api = vi.hoisted(() => ({ updateOrgUnit: vi.fn() }));
vi.mock("@/lib/api", () => api);

const leaf: OrgUnitTreeNode = { id: "leaf", nome: "Settore", tipo: "settore", parent_id: "root", children: [], source: "manuale", is_active: true, wc_area_id: null, legacy_team_id: null, sort_order: 0, person_count: 0, child_count: 0, canvas_x: 504, canvas_y: 384 };
const root: OrgUnitTreeNode = { ...leaf, id: "root", nome: "Direzione", tipo: "direzione", parent_id: null, children: [leaf], canvas_x: 240, canvas_y: 240 };
const outside: OrgUnitTreeNode = { ...leaf, id: "outside", parent_id: null, canvas_x: 2000, canvas_y: 2000 };

function context() {
  return { token: "token" as string | null, canModifyStructure: true, structureKind: "territoriale" as const,
    schemaOrientation: "horizontal" as "horizontal" | "vertical", schemaCanvasMode: "free" as "free" | "guided", view: "schema",
    flatTree: flattenTree([root, outside]), scopedTree: [root], schemaRoots: [root],
    selectedNode: root as OrgUnitTreeNode | null, selectedSector: leaf as OrgUnitTreeNode | null, selectedId: "root" as string | null,
    setTree: vi.fn(), setSchemaOrientation: vi.fn(), setNotice: vi.fn(), fitSchemaToViewport: vi.fn(), refreshStructure: vi.fn().mockResolvedValue(undefined),
    snapCoordinate: (value: number) => Math.max(0, Math.round(value / 24) * 24), safeCanvasCoord,
    computeHorizontalTreeLayout, computeVerticalTreeLayout, resolveSubtreeCollisionShift, applyCanvasPositionsToForest, updateTreeNodeInForest,
  } satisfies OrganigrammaLayoutContext;
}

function updatedForest(state: ReturnType<typeof context>) {
  const update = state.setTree.mock.calls[0]![0] as (forest: OrgUnitTreeNode[]) => OrgUnitTreeNode[];
  return update([root, outside]);
}

beforeEach(() => {
  vi.resetAllMocks();
  api.updateOrgUnit.mockResolvedValue(undefined);
  vi.spyOn(window, "requestAnimationFrame").mockImplementation(callback => { callback(0); return 1; });
});

describe("layout persistence", () => {
  test.each(["horizontal", "vertical"] as const)("applies the real %s layout only to the scoped forest", async orientation => {
    const state = context();
    await handleApplyTreeLayout(state, orientation);
    const positions = orientation === "horizontal" ? computeHorizontalTreeLayout([root]) : computeVerticalTreeLayout([root]);
    for (const [nodeId, position] of positions) expect(api.updateOrgUnit).toHaveBeenCalledWith("token", nodeId, { canvas_x: position.x, canvas_y: position.y }, "territoriale");
    const next = updatedForest(state);
    expect(next[1]).toBe(outside);
    expect(next[0]!.children[0]!.parent_id).toBe("root");
    expect(root.canvas_x).toBe(240);
    expect(state.setSchemaOrientation).toHaveBeenCalledWith(orientation);
    expect(state.refreshStructure).toHaveBeenCalledOnce();
    expect(state.fitSchemaToViewport).toHaveBeenCalledOnce();
    expect(api.updateOrgUnit).not.toHaveBeenCalledWith("token", "outside", expect.anything(), "territoriale");
  });

  test.each(["schema", "albero"])("guided layout is local even without write permission (%s)", async view => {
    const state = { ...context(), view, schemaCanvasMode: "guided" as const, token: null, canModifyStructure: false };
    await handleApplyTreeLayout(state, "vertical");
    expect(state.setSchemaOrientation).toHaveBeenCalledWith("vertical");
    expect(state.setNotice).toHaveBeenCalledWith("Vista guidata verticale applicata.");
    expect(api.updateOrgUnit).not.toHaveBeenCalled();
    expect(state.setTree).not.toHaveBeenCalled();
    expect(state.refreshStructure).not.toHaveBeenCalled();
    expect(state.fitSchemaToViewport).toHaveBeenCalledTimes(view === "schema" ? 1 : 0);
  });

  test("guided horizontal layout reports its orientation", async () => {
    const state = { ...context(), schemaCanvasMode: "guided" as const, token: null, canModifyStructure: false };
    await handleApplyTreeLayout(state, "horizontal");
    expect(state.setSchemaOrientation).toHaveBeenCalledWith("horizontal");
    expect(state.setNotice).toHaveBeenCalledWith("Vista guidata orizzontale applicata.");
    expect(state.fitSchemaToViewport).toHaveBeenCalledOnce();
    expect(state.setTree).not.toHaveBeenCalled();
  });

  test.each([{ token: null }, { canModifyStructure: false }])("requires a session and permission before changing a free layout (%j)", async patch => {
    const state = { ...context(), ...patch };
    await handleApplyTreeLayout(state, "horizontal");
    await handleCompactVisibleArea(state);
    expect(api.updateOrgUnit).not.toHaveBeenCalled();
    expect(state.setTree).not.toHaveBeenCalled();
    expect(state.setNotice).not.toHaveBeenCalled();
  });

  test("refreshes an empty scope without inventing nodes or persistence calls", async () => {
    const state = { ...context(), scopedTree: [] };
    await handleApplyTreeLayout(state, "horizontal");
    expect(api.updateOrgUnit).not.toHaveBeenCalled();
    expect(updatedForest(state)).toEqual([root, outside]);
    expect(state.refreshStructure).toHaveBeenCalledOnce();
  });

  test("does not fit a tree view after saving layout", async () => {
    const state = { ...context(), view: "albero" };
    await handleApplyTreeLayout(state, "vertical");
    expect(state.refreshStructure).toHaveBeenCalledOnce();
    expect(state.fitSchemaToViewport).not.toHaveBeenCalled();
  });

  test.each(["horizontal", "vertical"] as const)("reports non-Error persistence failure for %s without refresh or success", async orientation => {
    const state = context();
    api.updateOrgUnit.mockRejectedValue("unavailable");
    await handleApplyTreeLayout(state, orientation);
    expect(state.setNotice).toHaveBeenCalledWith(`Applicazione layout ${orientation === "horizontal" ? "orizzontale" : "verticale"} non riuscita`);
    expect(state.setSchemaOrientation).not.toHaveBeenCalled();
    expect(state.refreshStructure).not.toHaveBeenCalled();
    expect(state.fitSchemaToViewport).not.toHaveBeenCalled();
    expect(state.setTree).toHaveBeenCalledOnce();
  });

  test("reports refresh failure after persistence without adding rollback or retry", async () => {
    const state = context();
    state.refreshStructure.mockRejectedValue(new Error("Refresh unavailable"));
    await handleApplyTreeLayout(state, "vertical");
    expect(api.updateOrgUnit).toHaveBeenCalledTimes(2);
    expect(state.setSchemaOrientation).toHaveBeenCalledWith("vertical");
    expect(state.setNotice).toHaveBeenLastCalledWith("Refresh unavailable");
    expect(state.fitSchemaToViewport).not.toHaveBeenCalled();
  });
});

describe("visible area compaction", () => {
  test.each(["horizontal", "vertical"] as const)("preserves the visible origin and hierarchy in %s compaction", async schemaOrientation => {
    const state = { ...context(), schemaOrientation };
    await handleCompactVisibleArea(state);
    const next = updatedForest(state);
    const nodes = flattenTree([next[0]!]);
    expect(Math.min(...nodes.map(node => node.canvas_x!))).toBe(240);
    expect(Math.min(...nodes.map(node => node.canvas_y!))).toBe(240);
    expect(next[1]).toBe(outside);
    expect(next[0]!.children[0]!.parent_id).toBe("root");
    expect(root.children[0]!.canvas_x).toBe(504);
    expect(api.updateOrgUnit).toHaveBeenCalledTimes(2);
    expect(state.setNotice).toHaveBeenCalledWith("Area visibile compattata.");
    expect(state.refreshStructure).not.toHaveBeenCalled();
    expect(state.fitSchemaToViewport).toHaveBeenCalledOnce();
  });

  test("does not compact an empty visible forest", async () => {
    const state = { ...context(), schemaRoots: [] };
    await handleCompactVisibleArea(state);
    expect(state.setTree).not.toHaveBeenCalled();
    expect(api.updateOrgUnit).not.toHaveBeenCalled();
  });

  test("normalizes invalid external coordinates and does not fit the tree view", async () => {
    const state = { ...context(), view: "albero", schemaRoots: [{ ...leaf, parent_id: null, canvas_x: null, canvas_y: Number.NaN }] };
    await handleCompactVisibleArea(state);
    expect(api.updateOrgUnit).toHaveBeenCalledWith("token", "leaf", { canvas_x: 0, canvas_y: 0 }, "territoriale");
    expect(state.fitSchemaToViewport).not.toHaveBeenCalled();
  });

  test.each([new Error("Save failed"), "unavailable"])("reports compaction failures without claiming success (%s)", async failure => {
    const state = context();
    api.updateOrgUnit.mockRejectedValue(failure);
    await handleCompactVisibleArea(state);
    expect(state.setNotice).toHaveBeenCalledWith(failure instanceof Error ? failure.message : "Compattazione area visibile non riuscita");
    expect(state.fitSchemaToViewport).not.toHaveBeenCalled();
    expect(state.setTree).toHaveBeenCalledOnce();
  });
});

describe("expanded subtree realignment", () => {
  test.each(["missing", "leaf"])("does not move an absent or childless expanded node (%s)", async nodeId => {
    const state = context();
    await realignExpandedSubtree(state, nodeId);
    expect(state.setTree).not.toHaveBeenCalled();
    expect(api.updateOrgUnit).not.toHaveBeenCalled();
  });

  test.each(["horizontal", "vertical"] as const)("anchors the parent in %s realignment and preserves unrelated nodes", async schemaOrientation => {
    const branch = { ...leaf, children: [{ ...leaf, id: "grandchild", parent_id: "leaf" }] };
    const forest = [{ ...root, children: [branch] }, outside];
    const state = { ...context(), flatTree: flattenTree(forest), schemaOrientation };
    await realignExpandedSubtree(state, "leaf");
    expect(api.updateOrgUnit).toHaveBeenCalledTimes(2);
    expect(api.updateOrgUnit).not.toHaveBeenCalledWith("token", "root", expect.anything(), "territoriale");
    const update = state.setTree.mock.calls[0]![0] as (previous: OrgUnitTreeNode[]) => OrgUnitTreeNode[];
    const next = update(forest);
    expect(next[0]!.canvas_x).toBe(240);
    expect(next[0]!.canvas_y).toBe(240);
    expect(next[1]).toBe(outside);
    expect(forest[0]!.children[0]!.canvas_x).toBe(504);
  });

  test("realigns an orphan subtree relative to its own root", async () => {
    const orphan = { ...root, parent_id: "removed-parent" };
    const state = { ...context(), flatTree: flattenTree([orphan]) };
    await realignExpandedSubtree(state, "root");
    expect(api.updateOrgUnit).toHaveBeenCalledTimes(1);
    expect(api.updateOrgUnit).toHaveBeenCalledWith("token", "leaf", expect.objectContaining({ canvas_x: expect.any(Number), canvas_y: expect.any(Number) }), "territoriale");
  });

  test("does not realign when the parent snapshot has no descendants", async () => {
    const branch = { ...leaf, children: [{ ...leaf, id: "grandchild" }] };
    const state = { ...context(), flatTree: [{ ...root, children: [] }, branch] };
    await realignExpandedSubtree(state, "leaf");
    expect(state.setTree).not.toHaveBeenCalled();
    expect(api.updateOrgUnit).not.toHaveBeenCalled();
  });

  test.each([{ token: null }, { canModifyStructure: false }])("keeps read-only realignment local (%j)", async patch => {
    const state = { ...context(), ...patch };
    await realignExpandedSubtree(state, "root");
    expect(state.setTree).toHaveBeenCalledOnce();
    expect(api.updateOrgUnit).not.toHaveBeenCalled();
  });

  test("propagates save failures to the collapse caller without retry", async () => {
    const state = context();
    api.updateOrgUnit.mockRejectedValue(new Error("Save failed"));
    await expect(realignExpandedSubtree(state, "root")).rejects.toThrow("Save failed");
    expect(api.updateOrgUnit).toHaveBeenCalledOnce();
    expect(state.setTree).toHaveBeenCalledOnce();
  });
});

describe("sector parent resolution", () => {
  test.each(["distretto", "direzione"] as const)("uses the selected %s as the sector parent", tipo => {
    expect(resolveSectorParentId({ ...context(), selectedNode: { ...root, tipo } })).toBe("root");
  });
  test("uses the parent of an existing sector", () => {
    expect(resolveSectorParentId({ ...context(), selectedNode: leaf })).toBe("root");
  });
  test("uses a focused sector's parent when selecting a reparto", () => {
    expect(resolveSectorParentId({ ...context(), selectedNode: { ...leaf, id: "reparto", tipo: "reparto" } })).toBe("root");
  });
  test.each([null, "selected"])("falls back to the selection when no sector parent is available (%s)", selectedId => {
    expect(resolveSectorParentId({ ...context(), selectedNode: null, selectedSector: null, selectedId })).toBe(selectedId);
  });
});
