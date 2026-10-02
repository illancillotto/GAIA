import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { handleSchemaPanStart, handleSchemaZoomWheel, handleTreePanStart, handleTreeZoomWheel } from "@/features/organigramma/organigramma-viewport-controller";
import { computeSchemaCanvasBounds, computeSchemaDisplayPositions, safeCanvasCoord } from "@/features/organigramma/organigramma-workspace";
import type { OrganigrammaViewportContext } from "@/features/organigramma/organigramma-viewport-context";
import type { OrgUnitTreeNode } from "@/types/api";

function node(id: string, canvasX: number, canvasY: number): OrgUnitTreeNode {
  return { id, nome: id, tipo: "settore", parent_id: null, children: [], canvas_x: canvasX, canvas_y: canvasY,
    source: "manuale", is_active: true, wc_area_id: null, legacy_team_id: null, sort_order: 0, person_count: 0, child_count: 0 };
}

function context() {
  const treeViewport = document.createElement("div");
  const schemaViewport = document.createElement("div");
  document.body.append(treeViewport, schemaViewport);
  return {
    treeViewportRef: { current: treeViewport as HTMLDivElement | null },
    schemaViewportRef: { current: schemaViewport as HTMLDivElement | null },
    treePanStateRef: { current: { active: false, startX: 0, startY: 0, scrollLeft: 0, scrollTop: 0 } },
    schemaPanStateRef: { current: { active: false, startX: 0, startY: 0, scrollLeft: 0, scrollTop: 0 } },
    schemaRoots: [node("first", 120, 120), node("second", 800, 800)], schemaScale: 1,
    setTreeScale: vi.fn(), setSchemaScale: vi.fn(), setSchemaMarquee: vi.fn(), setMultiSelectedIds: vi.fn(),
    setSchemaLinkDraft: vi.fn(), computeSchemaCanvasBounds, computeSchemaDisplayPositions, safeCanvasCoord,
    SCHEMA_NODE_WIDTH: 246, SCHEMA_NODE_HEIGHT: 188,
  } satisfies OrganigrammaViewportContext;
}

function panEvent(target: HTMLElement, run: (event: React.MouseEvent<HTMLDivElement>) => void, options: MouseEventInit = {}) {
  target.addEventListener("mousedown", (event) => run(event as unknown as React.MouseEvent<HTMLDivElement>), { once: true });
  const event = new MouseEvent("mousedown", { bubbles: true, cancelable: true, button: 0, ...options });
  target.dispatchEvent(event);
  return event;
}

beforeEach(() => {
  vi.spyOn(window, "requestAnimationFrame").mockImplementation((callback) => {
    callback(0);
    return 1;
  });
});

afterEach(() => {
  window.dispatchEvent(new MouseEvent("mouseup"));
  vi.restoreAllMocks();
  document.body.replaceChildren();
});

describe("viewport panning", () => {
  const views = [
    ["tree", "treeViewportRef", "treePanStateRef", handleTreePanStart],
    ["schema", "schemaViewportRef", "schemaPanStateRef", handleSchemaPanStart],
  ] as const;

  test.each(views)("%s preserves scroll anchors and removes listeners after mouseup", (_view, viewportKey, panKey, start) => {
    const state = context();
    const viewport = state[viewportKey].current!;
    viewport.scrollLeft = 80;
    viewport.scrollTop = 60;
    expect(panEvent(viewport, (event) => start(state, event), { clientX: 100, clientY: 100 }).defaultPrevented).toBe(true);
    expect(viewport.style.cursor).toBe("grabbing");
    expect(state[panKey].current.active).toBe(true);
    window.dispatchEvent(new MouseEvent("mousemove", { clientX: 50, clientY: 70 }));
    expect(viewport.scrollLeft).toBe(130);
    expect(viewport.scrollTop).toBe(90);
    window.dispatchEvent(new MouseEvent("mouseup"));
    expect(state[panKey].current.active).toBe(false);
    expect(viewport.style.cursor).toBe("grab");
    window.dispatchEvent(new MouseEvent("mousemove", { clientX: 0, clientY: 0 }));
    expect(viewport.scrollLeft).toBe(130);
    expect(viewport.scrollTop).toBe(90);
  });

  test.each(views)("%s ignores right clicks and an unmounted viewport", (_view, viewportKey, panKey, start) => {
    const state = context();
    const viewport = state[viewportKey].current!;
    const rightClick = panEvent(viewport, (event) => start(state, event), { button: 2 });
    expect(rightClick.defaultPrevented).toBe(false);
    state[viewportKey].current = null;
    panEvent(viewport, (event) => start(state, event));
    expect(state[panKey].current.active).toBe(false);
    expect(viewport.style.cursor).toBe("");
  });

  test.each(views)("%s does not move after gesture state is cancelled", (_view, viewportKey, panKey, start) => {
    const state = context();
    const viewport = state[viewportKey].current!;
    panEvent(viewport, (event) => start(state, event), { clientX: 100, clientY: 100 });
    state[panKey].current.active = false;
    window.dispatchEvent(new MouseEvent("mousemove", { clientX: 0, clientY: 0 }));
    expect(viewport.scrollLeft).toBe(0);
    expect(viewport.scrollTop).toBe(0);
  });

  test.each(["button", "input", "select", "textarea", "label", "a"])("interactive %s does not start a background pan", (tag) => {
    const state = context();
    const control = document.createElement(tag);
    state.treeViewportRef.current!.appendChild(control);
    panEvent(control, (event) => handleTreePanStart(state, event));
    expect(state.treePanStateRef.current.active).toBe(false);
    state.schemaViewportRef.current!.appendChild(control);
    panEvent(control, (event) => handleSchemaPanStart(state, event));
    expect(state.schemaPanStateRef.current.active).toBe(false);
  });

  test("tree items and schema cards preserve their own selection gestures", () => {
    const state = context();
    const treeItem = document.createElement("div");
    treeItem.setAttribute("role", "treeitem");
    const card = document.createElement("div");
    card.setAttribute("data-schema-node-card", "");
    panEvent(treeItem, (event) => handleTreePanStart(state, event));
    panEvent(card, (event) => handleSchemaPanStart(state, event));
    expect(state.treePanStateRef.current.active).toBe(false);
    expect(state.schemaPanStateRef.current.active).toBe(false);
  });

  test("schema background clears link and multi-selection before panning", () => {
    const state = context();
    panEvent(state.schemaViewportRef.current!, (event) => handleSchemaPanStart(state, event));
    expect(state.setSchemaLinkDraft).toHaveBeenCalledWith(null);
    expect(state.setMultiSelectedIds).toHaveBeenCalledWith(new Set());
  });
});

describe("marquee selection", () => {
  test("selects only intersecting blocks and cleans up on mouseup", () => {
    const state = context();
    panEvent(state.schemaViewportRef.current!, (event) => handleSchemaPanStart(state, event), { shiftKey: true, clientX: 100, clientY: 100 });
    window.dispatchEvent(new MouseEvent("mousemove", { clientX: 500, clientY: 500 }));
    expect(state.setSchemaMarquee).toHaveBeenLastCalledWith({ x: 100, y: 100, width: 400, height: 400 });
    expect(state.setMultiSelectedIds).toHaveBeenLastCalledWith(new Set(["first"]));
    expect(state.schemaPanStateRef.current.active).toBe(false);
    window.dispatchEvent(new MouseEvent("mouseup", { clientX: 900, clientY: 900 }));
    expect(state.setMultiSelectedIds).toHaveBeenLastCalledWith(new Set(["first", "second"]));
    expect(state.setSchemaMarquee).toHaveBeenLastCalledWith(null);
    const updates = state.setMultiSelectedIds.mock.calls.length;
    window.dispatchEvent(new MouseEvent("mousemove", { clientX: 0, clientY: 0 }));
    expect(state.setMultiSelectedIds).toHaveBeenCalledTimes(updates);
  });

  test("normalizes reverse drags using current scale and scroll offsets", () => {
    const state = { ...context(), schemaScale: 2 };
    state.schemaViewportRef.current!.scrollLeft = 100;
    state.schemaViewportRef.current!.scrollTop = 100;
    panEvent(state.schemaViewportRef.current!, (event) => handleSchemaPanStart(state, event), { shiftKey: true, clientX: 900, clientY: 900 });
    window.dispatchEvent(new MouseEvent("mouseup", { clientX: 100, clientY: 100 }));
    expect(state.setMultiSelectedIds).toHaveBeenLastCalledWith(new Set(["first"]));
    expect(state.setSchemaMarquee.mock.calls.at(-2)![0]).toEqual({ x: 100, y: 100, width: 400, height: 400 });
  });

  test("empty forests and zero scale do not introduce invalid coordinates", () => {
    const state = { ...context(), schemaRoots: [], schemaScale: 0 };
    panEvent(state.schemaViewportRef.current!, (event) => handleSchemaPanStart(state, event), { shiftKey: true });
    window.dispatchEvent(new MouseEvent("mouseup", { clientX: 10, clientY: 10 }));
    expect(state.setMultiSelectedIds).toHaveBeenLastCalledWith(new Set());
    expect(state.setSchemaMarquee.mock.calls.at(-2)![0]).toEqual({ x: 0, y: 0, width: 1000, height: 1000 });
  });
});

describe("anchored zoom", () => {
  const views = [
    ["tree", "treeViewportRef", "setTreeScale", handleTreeZoomWheel, 0.65],
    ["schema", "schemaViewportRef", "setSchemaScale", handleSchemaZoomWheel, 0.5],
  ] as const;

  test.each(views)("%s preserves ordinary wheel scrolling and handles a detached viewport", (_view, viewportKey, setterKey, zoom) => {
    const state = context();
    const scroll = new WheelEvent("wheel", { cancelable: true, deltaY: 1 });
    zoom(state, scroll);
    expect(scroll.defaultPrevented).toBe(false);
    expect(state[setterKey]).not.toHaveBeenCalled();
    state[viewportKey].current = null;
    const detached = new WheelEvent("wheel", { cancelable: true, ctrlKey: true });
    zoom(state, detached);
    expect(detached.defaultPrevented).toBe(true);
    expect(state[setterKey]).not.toHaveBeenCalled();
  });

  test.each(views)("%s keeps the pointer anchored when zooming in and out", (_view, viewportKey, setterKey, zoom) => {
    const state = context();
    const viewport = state[viewportKey].current!;
    for (const deltaY of [-1, 1]) {
      viewport.scrollLeft = 80;
      viewport.scrollTop = 60;
      zoom(state, new WheelEvent("wheel", { ctrlKey: true, deltaY, clientX: 100, clientY: 50 }));
      const update = state[setterKey].mock.calls.at(-1)![0] as (previous: number) => number;
      const next = update(1);
      expect(next).toBe(deltaY > 0 ? 0.92 : 1.08);
      expect(viewport.scrollLeft).toBeCloseTo(180 * next - 100);
      expect(viewport.scrollTop).toBeCloseTo(110 * next - 50);
    }
  });

  test.each(views)("%s clamps both scale boundaries without moving an already anchored viewport", (_view, viewportKey, setterKey, zoom, minimum) => {
    const state = context();
    const viewport = state[viewportKey].current!;
    zoom(state, new WheelEvent("wheel", { ctrlKey: true, deltaY: -1 }));
    expect((state[setterKey].mock.calls.at(-1)![0] as (previous: number) => number)(1.6)).toBe(1.6);
    zoom(state, new WheelEvent("wheel", { ctrlKey: true, deltaY: 1 }));
    expect((state[setterKey].mock.calls.at(-1)![0] as (previous: number) => number)(minimum)).toBe(minimum);
    expect(viewport.scrollLeft).toBe(0);
    expect(viewport.scrollTop).toBe(0);
  });
});
