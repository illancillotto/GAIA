import { fireEvent } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { bindSchemaDrag, focusSchemaNode } from "@/features/organigramma/organigramma-viewport-controller";
import type { OrganigrammaDragContext, OrganigrammaFocusContext } from "@/features/organigramma/organigramma-viewport-context";
import { computeGuidedSchemaLayout, computeSchemaCanvasBounds, computeSchemaDisplayPositions, updateTreeNodeInForest } from "@/features/organigramma/organigramma-workspace";
import type { OrgUnitTreeNode } from "@/types/api";

const api = vi.hoisted(() => ({ updateOrgUnit: vi.fn() }));
vi.mock("@/lib/api", () => api);

const node: OrgUnitTreeNode = { id: "node", nome: "Settore", tipo: "settore", parent_id: null, children: [], source: "manuale", is_active: true, wc_area_id: null, legacy_team_id: null, sort_order: 0, person_count: 0, child_count: 0, canvas_x: 120, canvas_y: 240 };
const cleanups: Array<() => void> = [];

function dragContext() {
  const treeRef = { current: [node] };
  return { schemaDragging: { nodeId: "node", pointerId: 7, startX: 100, startY: 200, nodes: [{ nodeId: "node", originX: 120, originY: 240 }] },
    token: "token", schemaEditEnabled: true, schemaScale: 2, schemaSnapToGrid: false, treeRef,
    setTree: vi.fn((update: React.SetStateAction<OrgUnitTreeNode[]>) => { treeRef.current = typeof update === "function" ? update(treeRef.current) : update; }),
    setSchemaDragging: vi.fn(), structureKind: "territoriale", setNotice: vi.fn(),
    snapCoordinate: (value: number) => Math.max(0, Math.round(value / 24) * 24), updateTreeNodeInForest,
  } satisfies OrganigrammaDragContext;
}

function bind(state: OrganigrammaDragContext) {
  const cleanup = bindSchemaDrag(state);
  if (cleanup) cleanups.push(cleanup);
  return cleanup;
}

function focusContext() {
  const viewport = document.createElement("div");
  Object.defineProperties(viewport, { clientWidth: { value: 900 }, clientHeight: { value: 600 } });
  return { view: "schema", schemaFocusNodeId: "node", schemaViewportRef: { current: viewport as HTMLDivElement | null }, roots: [node],
    setSchemaFocusNodeId: vi.fn(), schemaCanvasMode: "free", computeGuidedSchemaLayout, schemaOrientation: "vertical", guidedSchemaDensity: "standard",
    computeSchemaDisplayPositions, computeSchemaCanvasBounds, setSchemaScale: vi.fn(), SCHEMA_NODE_WIDTH: 246, SCHEMA_NODE_HEIGHT: 188,
  } satisfies OrganigrammaFocusContext;
}

beforeEach(() => {
  vi.resetAllMocks();
  api.updateOrgUnit.mockResolvedValue(undefined);
});

afterEach(() => {
  cleanups.splice(0).forEach(cleanup => cleanup());
  vi.restoreAllMocks();
});

describe("schema drag lifecycle", () => {
  test.each([{ schemaDragging: null }, { token: null }, { schemaEditEnabled: false }])("does not bind a gesture without its prerequisites (%j)", patch => {
    const state = { ...dragContext(), ...patch };
    expect(bind(state)).toBeUndefined();
    fireEvent.pointerMove(window, { pointerId: 7, clientX: 200, clientY: 300 });
    fireEvent.pointerUp(window, { pointerId: 7 });
    expect(state.setTree).not.toHaveBeenCalled();
    expect(api.updateOrgUnit).not.toHaveBeenCalled();
  });

  test.each([false, true])("updates immutable coordinates at the current zoom with grid snapping=%s", schemaSnapToGrid => {
    const state = { ...dragContext(), schemaSnapToGrid };
    bind(state);
    fireEvent.pointerMove(window, { pointerId: 7, clientX: 150, clientY: 250 });
    expect(state.treeRef.current[0]!.canvas_x).toBe(schemaSnapToGrid ? 144 : 145);
    expect(state.treeRef.current[0]!.canvas_y).toBe(schemaSnapToGrid ? 264 : 265);
    expect(node.canvas_x).toBe(120);
    expect(api.updateOrgUnit).not.toHaveBeenCalled();
    fireEvent.pointerUp(window, { pointerId: 7 });
    expect(api.updateOrgUnit).toHaveBeenCalledWith("token", "node", {
      canvas_x: schemaSnapToGrid ? 144 : 145, canvas_y: schemaSnapToGrid ? 264 : 265,
    }, "territoriale");
    expect(state.setSchemaDragging).toHaveBeenCalledWith(null);
  });

  test("ignores another pointer and unregisters listeners when the gesture is cancelled by the owner", () => {
    const state = dragContext();
    const cleanup = bind(state)!;
    fireEvent.pointerMove(window, { pointerId: 8, clientX: 900, clientY: 900 });
    fireEvent.pointerUp(window, { pointerId: 8 });
    expect(state.setTree).not.toHaveBeenCalled();
    expect(state.setSchemaDragging).not.toHaveBeenCalled();
    expect(api.updateOrgUnit).not.toHaveBeenCalled();
    cleanup();
    fireEvent.pointerMove(window, { pointerId: 7, clientX: 200, clientY: 300 });
    fireEvent.pointerCancel(window, { pointerId: 7 });
    expect(state.setTree).not.toHaveBeenCalled();
    expect(api.updateOrgUnit).not.toHaveBeenCalled();
  });

  test("clamps negative coordinates and persists a pointercancel like a pointerup", () => {
    const state = dragContext();
    bind(state);
    fireEvent.pointerMove(window, { pointerId: 7, clientX: -900, clientY: -900 });
    fireEvent.pointerCancel(window, { pointerId: 7 });
    expect(api.updateOrgUnit).toHaveBeenCalledWith("token", "node", { canvas_x: 0, canvas_y: 0 }, "territoriale");
  });

  test("does not persist a dragged node removed by a concurrent structure refresh", () => {
    const state = dragContext();
    bind(state);
    state.treeRef.current = [];
    fireEvent.pointerUp(window, { pointerId: 7 });
    expect(state.setSchemaDragging).toHaveBeenCalledWith(null);
    expect(api.updateOrgUnit).not.toHaveBeenCalled();
    expect(state.setNotice).not.toHaveBeenCalled();
  });

  test.each([new Error("Save unavailable"), "remote failure"])("reports save failure without replaying the gesture (%s)", async failure => {
    const state = dragContext();
    api.updateOrgUnit.mockRejectedValue(failure);
    bind(state);
    fireEvent.pointerUp(window, { pointerId: 7 });
    await Promise.resolve();
    expect(state.setNotice).toHaveBeenCalledWith(failure instanceof Error ? failure.message : "Salvataggio posizione non riuscito");
    expect(api.updateOrgUnit).toHaveBeenCalledOnce();
    expect(state.setSchemaDragging).toHaveBeenCalledWith(null);
  });
});

describe("schema focus lifecycle", () => {
  test.each([{ view: "albero" }, { schemaFocusNodeId: null }, { schemaViewportRef: { current: null } }])("does not focus without a mounted schema target (%j)", patch => {
    const state = { ...focusContext(), ...patch };
    const schedule = vi.spyOn(window, "requestAnimationFrame");
    expect(focusSchemaNode(state)).toBeUndefined();
    expect(schedule).not.toHaveBeenCalled();
    expect(state.setSchemaScale).not.toHaveBeenCalled();
  });

  test("clears a stale focus after the requested node is removed", () => {
    const state = { ...focusContext(), roots: [] };
    expect(focusSchemaNode(state)).toBeUndefined();
    expect(state.setSchemaFocusNodeId).toHaveBeenCalledWith(null);
    expect(state.setSchemaScale).not.toHaveBeenCalled();
  });

  test.each(["free", "guided"] as const)("centers a %s layout and cancels a pending focus frame on cleanup", schemaCanvasMode => {
    const state = { ...focusContext(), schemaCanvasMode };
    let frame: FrameRequestCallback | undefined;
    vi.spyOn(window, "requestAnimationFrame").mockImplementation(callback => { frame = callback; return 42; });
    const cancel = vi.spyOn(window, "cancelAnimationFrame");
    const cleanup = focusSchemaNode(state)!;
    const scale = state.setSchemaScale.mock.calls[0]![0] as number;
    const positions = schemaCanvasMode === "guided" ? computeGuidedSchemaLayout(state.roots, "vertical", "standard") : computeSchemaDisplayPositions(state.roots);
    const bounds = computeSchemaCanvasBounds(state.roots, positions);
    const position = positions.get("node")!;
    expect(state.setSchemaFocusNodeId).not.toHaveBeenCalled();
    frame!(0);
    expect(state.schemaViewportRef.current!.scrollLeft).toBe(Math.max((position.x + bounds.offsetX) * scale - (900 - 246 * scale) / 2, 0));
    expect(state.schemaViewportRef.current!.scrollTop).toBe(Math.max((position.y + bounds.offsetY) * scale - (600 - 188 * scale) / 2, 0));
    expect(state.setSchemaFocusNodeId).toHaveBeenCalledWith(null);
    cleanup();
    expect(cancel).toHaveBeenCalledWith(42);
  });
});
