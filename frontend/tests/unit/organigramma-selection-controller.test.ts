import { beforeEach, describe, expect, test, vi } from "vitest";

import { handleBeginSchemaLink, handleConnectSchemaNode, handleConnectSelectedNodeToTarget, handleSchemaCardContextMenu, handleSchemaCardPointerDown, handleSchemaCardSelect } from "@/features/organigramma/organigramma-selection-controller";
import type { OrganigrammaSelectionContext, SchemaLinkDraft } from "@/features/organigramma/organigramma-selection-context";
import { safeCanvasCoord } from "@/features/organigramma/organigramma-workspace";
import type { OrgUnitTreeNode } from "@/types/api";

const unit: OrgUnitTreeNode = { id: "unit", nome: "Settore", tipo: "settore", parent_id: null, children: [], canvas_x: 120, canvas_y: 240,
  source: "manuale", is_active: true, wc_area_id: null, legacy_team_id: null, sort_order: 0, person_count: 0, child_count: 0 };

function context() {
  return {
    canModifyStructure: true, schemaEditEnabled: true, selectedId: "other" as string | null,
    multiSelectedIds: new Set<string>(), flatTree: [unit], schemaLinkDraft: { sourceId: "unit", mode: "above" } as SchemaLinkDraft | null,
    setSchemaLinkDraft: vi.fn(), setMultiSelectedIds: vi.fn(), setSelectedId: vi.fn(), setSchemaDragging: vi.fn(),
    setSchemaContextMenu: vi.fn(), safeCanvasCoord, performSchemaLink: vi.fn().mockResolvedValue(true),
  } satisfies OrganigrammaSelectionContext;
}

function pointer(patch: Partial<React.PointerEvent<HTMLDivElement>> = {}) {
  const target = document.createElement("div");
  return { button: 0, ctrlKey: false, metaKey: false, shiftKey: false, target, currentTarget: target, pointerId: 7, clientX: 100, clientY: 200,
    preventDefault: vi.fn(), stopPropagation: vi.fn(), ...patch } as unknown as React.PointerEvent<HTMLDivElement>;
}

beforeEach(() => vi.resetAllMocks());

describe("schema selection", () => {
  test.each([undefined, pointer()])("ordinary selection resets the multi-selection", (event) => {
    const state = context();
    state.multiSelectedIds.add("other");
    handleSchemaCardSelect(state, "unit", event);
    expect(state.setMultiSelectedIds).toHaveBeenCalledWith(new Set());
    expect(state.setSelectedId).toHaveBeenCalledWith("unit");
    expect(state.multiSelectedIds).toEqual(new Set(["other"]));
  });

  test.each(["ctrlKey", "metaKey", "shiftKey"] as const)("%s seeds the first multi-selection with the previous selected card", (modifier) => {
    const state = context();
    handleSchemaCardSelect(state, "unit", pointer({ [modifier]: true }));
    const update = state.setMultiSelectedIds.mock.calls[0]![0] as (previous: Set<string>) => Set<string>;
    const previous = new Set<string>();
    expect(update(previous)).toEqual(new Set(["other", "unit"]));
    expect(previous.size).toBe(0);
    expect(state.setSelectedId).toHaveBeenCalledWith("unit");
  });

  test.each([null, "unit"])("does not invent a second selection when the previous card is %s", (selectedId) => {
    const state = { ...context(), selectedId };
    handleSchemaCardSelect(state, "unit", pointer({ shiftKey: true }));
    const update = state.setMultiSelectedIds.mock.calls[0]![0] as (previous: Set<string>) => Set<string>;
    expect(update(new Set())).toEqual(new Set(["unit"]));
  });

  test.each(["ctrlKey", "metaKey"] as const)("%s removes a selected card without changing the primary selection", (modifier) => {
    const state = context();
    state.multiSelectedIds = new Set(["unit", "other"]);
    handleSchemaCardSelect(state, "unit", pointer({ [modifier]: true }));
    const update = state.setMultiSelectedIds.mock.calls[0]![0] as (previous: Set<string>) => Set<string>;
    expect(update(state.multiSelectedIds)).toEqual(new Set(["other"]));
    expect(state.multiSelectedIds).toEqual(new Set(["unit", "other"]));
    expect(state.setSelectedId).not.toHaveBeenCalled();
  });

  test.each([
    [true, [], ["other"], false],
    [false, ["unit", "queued"], ["unit", "queued"], true],
  ] as const)("captures toggle=%s before the updater receives queued selection", (toggleOff, queuedIds, expectedIds, changesPrimary) => {
    const state = context();
    if (toggleOff) state.multiSelectedIds.add("unit");
    const event = pointer({ ctrlKey: true });
    handleSchemaCardSelect(state, "unit", event);
    const update = state.setMultiSelectedIds.mock.calls[0]![0] as (previous: Set<string>) => Set<string>;
    state.multiSelectedIds = new Set(toggleOff ? [] : ["unit"]);
    event.ctrlKey = false;
    const previous = new Set<string>(queuedIds);
    const result = update(previous);
    expect(Array.from(result)).toEqual(expectedIds);
    expect(previous).toEqual(new Set(queuedIds));
    expect(update(previous)).toEqual(result);
    expect(state.setSelectedId).toHaveBeenCalledTimes(Number(changesPrimary));
    if (changesPrimary) {
      expect(state.setMultiSelectedIds.mock.invocationCallOrder[0]).toBeLessThan(state.setSelectedId.mock.invocationCallOrder[0]!);
    }
  });

  test("shift selection retains an already selected card and its insertion order", () => {
    const state = context();
    state.multiSelectedIds = new Set(["unit", "other"]);
    handleSchemaCardSelect(state, "unit", pointer({ shiftKey: true }));
    const update = state.setMultiSelectedIds.mock.calls[0]![0] as (previous: Set<string>) => Set<string>;
    expect(Array.from(update(state.multiSelectedIds))).toEqual(["unit", "other"]);
    expect(state.setSelectedId).toHaveBeenCalledWith("unit");
  });
});

describe("schema drag authorization and inputs", () => {
  test.each([
    ["edit disabled", { schemaEditEnabled: false }, {}],
    ["right click", {}, { button: 2 }],
    ["ctrl selection", {}, { ctrlKey: true }],
    ["meta selection", {}, { metaKey: true }],
    ["shift selection", {}, { shiftKey: true }],
    ["missing unit", { flatTree: [] }, {}],
  ] as const)("%s does not start or capture a drag", (_name, statePatch, eventPatch) => {
    const state = { ...context(), ...statePatch };
    const event = pointer(eventPatch);
    handleSchemaCardPointerDown(state, "unit", event);
    expect(state.setSchemaDragging).not.toHaveBeenCalled();
    expect(state.setSelectedId).not.toHaveBeenCalled();
    expect(event.preventDefault).not.toHaveBeenCalled();
  });

  test.each(["button", "input", "select", "textarea", "label", "a"])("%s retains its own interaction", (tag) => {
    const state = context();
    handleSchemaCardPointerDown(state, "unit", pointer({ target: document.createElement(tag) }));
    expect(state.setSchemaDragging).not.toHaveBeenCalled();
  });

  test("captures the pointer and begins a single-card drag without requiring capture support", () => {
    const state = context();
    const event = pointer();
    handleSchemaCardPointerDown(state, "unit", event);
    expect(event.preventDefault).toHaveBeenCalledOnce();
    expect(event.stopPropagation).toHaveBeenCalledOnce();
    expect(state.setSchemaDragging).toHaveBeenCalledWith({ nodeId: "unit", pointerId: 7, startX: 100, startY: 200, nodes: [{ nodeId: "unit", originX: 120, originY: 240 }] });
    const capture = vi.fn();
    Object.defineProperty(event.currentTarget, "setPointerCapture", { value: capture });
    handleSchemaCardPointerDown(state, "unit", event);
    expect(capture).toHaveBeenCalledWith(7);
  });

  test("drags selected existing cards and ignores cards removed during refresh", () => {
    const state = context();
    state.multiSelectedIds = new Set(["unit", "other", "removed"]);
    state.flatTree = [unit, { ...unit, id: "other", canvas_x: NaN, canvas_y: Infinity }];
    handleSchemaCardPointerDown(state, "unit", pointer());
    expect(state.setSchemaDragging).toHaveBeenCalledWith(expect.objectContaining({ nodes: [
      { nodeId: "unit", originX: 120, originY: 240 }, { nodeId: "other", originX: 0, originY: 0 },
    ] }));
    expect(state.setMultiSelectedIds).not.toHaveBeenCalled();
  });

  test("starting a different card drag clears a previous multi-selection", () => {
    const state = context();
    state.multiSelectedIds.add("other");
    handleSchemaCardPointerDown(state, "unit", pointer());
    expect(state.setMultiSelectedIds).toHaveBeenCalledWith(new Set());
    expect(state.setSchemaDragging).toHaveBeenCalledWith(expect.objectContaining({ nodeId: "unit", nodes: [{ nodeId: "unit", originX: 120, originY: 240 }] }));
  });

  test.each([false, true])("context menu edit-enabled=%s preserves permissions and pointer position", (schemaEditEnabled) => {
    const state = { ...context(), schemaEditEnabled };
    const event = pointer();
    handleSchemaCardContextMenu(state, "unit", event);
    if (schemaEditEnabled) {
      expect(event.preventDefault).toHaveBeenCalledOnce();
      expect(state.setSelectedId).toHaveBeenCalledWith("unit");
      expect(state.setSchemaContextMenu).toHaveBeenCalledWith({ nodeId: "unit", x: 100, y: 200 });
    } else {
      expect(event.preventDefault).not.toHaveBeenCalled();
      expect(state.setSchemaContextMenu).not.toHaveBeenCalled();
    }
  });
});

describe("schema link lifecycle", () => {
  test.each([{ canModifyStructure: false }, { schemaEditEnabled: false }])("requires permission and edit mode before starting a link (%s)", (patch) => {
    const state = { ...context(), ...patch };
    handleBeginSchemaLink(state, "unit", "above");
    expect(state.setSchemaLinkDraft).not.toHaveBeenCalled();
  });

  test("toggles an identical draft and replaces other sources or modes", () => {
    const state = context();
    handleBeginSchemaLink(state, "unit", "above");
    const update = state.setSchemaLinkDraft.mock.calls[0]![0] as (previous: SchemaLinkDraft | null) => SchemaLinkDraft | null;
    expect(update({ sourceId: "unit", mode: "above" })).toBeNull();
    expect(update(null)).toEqual({ sourceId: "unit", mode: "above" });
    expect(update({ sourceId: "other", mode: "above" })).toEqual({ sourceId: "unit", mode: "above" });
    expect(update({ sourceId: "unit", mode: "below" })).toEqual({ sourceId: "unit", mode: "above" });
  });

  test("does not connect without a draft or a selected source", async () => {
    const state = { ...context(), schemaLinkDraft: null, selectedId: null };
    await handleConnectSchemaNode(state, "target");
    await handleConnectSelectedNodeToTarget(state, "target", "below");
    expect(state.performSchemaLink).not.toHaveBeenCalled();
    expect(state.setSchemaLinkDraft).not.toHaveBeenCalled();
  });

  test.each([
    ["above", true, false], ["above", false, true], ["below", true, true], ["below", false, true],
  ] as const)("%s link success=%s clears draft=%s", async (mode, success, clear) => {
    const state = { ...context(), schemaLinkDraft: { sourceId: "unit", mode } };
    state.performSchemaLink.mockResolvedValueOnce(success);
    await handleConnectSchemaNode(state, "target");
    expect(state.performSchemaLink).toHaveBeenCalledWith("unit", "target", mode);
    if (clear) expect(state.setSchemaLinkDraft).toHaveBeenCalledWith(null);
    else expect(state.setSchemaLinkDraft).not.toHaveBeenCalled();
  });

  test("connecting the selected source clears any draft before updating hierarchy", async () => {
    const state = context();
    await handleConnectSelectedNodeToTarget(state, "target", "below");
    expect(state.performSchemaLink).toHaveBeenCalledWith("other", "target", "below");
    expect(state.setSchemaLinkDraft).toHaveBeenCalledWith(null);
    expect(state.setSchemaLinkDraft.mock.invocationCallOrder[0]).toBeLessThan(state.performSchemaLink.mock.invocationCallOrder[0]!);
  });
});
