import { describe, expect, test } from "vitest";

import {
  applyCanvasPositionsToForest, computeHorizontalGuidedLayout, computeHorizontalTreeLayout,
  computeSchemaCanvasBounds, computeSchemaDisplayPositions, computeVerticalGuidedLayout,
  computeVerticalTreeLayout, resolveSubtreeCollisionShift, updateTreeNodeInForest,
} from "@/features/organigramma/organigramma-workspace";
import type { OrgUnitTreeNode } from "@/types/api";
import { flattenTree } from "@/lib/organigramma";

function node(id: string, children: OrgUnitTreeNode[] = [], canvasX = 120, canvasY = 120): OrgUnitTreeNode {
  return { id, nome: id, tipo: "settore", parent_id: null, children, canvas_x: canvasX, canvas_y: canvasY,
    source: "manuale", is_active: true, wc_area_id: null, legacy_team_id: null,
    sort_order: 0, person_count: 0, child_count: children.length };
}

describe("canvas positions and persistence", () => {
  test.each([[], [node("single")], [node("root", [node("branch", [node("leaf")]), node("sibling")]), node("other")]].map(forest => [forest]))("every layout assigns finite coordinates to every input node", (forest) => {
    const before = structuredClone(forest);
    const flat = flattenTree(forest);
    const layouts = [computeSchemaDisplayPositions(flat), computeHorizontalTreeLayout(forest), computeVerticalTreeLayout(forest),
      ...(["compact", "standard", "presentation"] as const).flatMap(density => [computeHorizontalGuidedLayout(forest, density), computeVerticalGuidedLayout(forest, density)])];
    for (const positions of layouts) {
      expect(new Set(positions.keys())).toEqual(new Set(flat.map(entry => entry.id)));
      for (const position of positions.values()) {
        expect(Number.isFinite(position.x)).toBe(true);
        expect(Number.isFinite(position.y)).toBe(true);
      }
    }
    expect(forest).toEqual(before);
  });
  test("normalizes non-finite coordinates without mutating the source nodes", () => {
    const nodes = [node("nan", [], NaN, Infinity), node("negative", [], -20, -40)];
    expect(computeSchemaDisplayPositions(nodes)).toEqual(new Map([
      ["nan", { x: 0, y: 0 }], ["negative", { x: -20, y: -40 }],
    ]));
    expect(nodes[0]!.canvas_x).toBeNaN();
    expect(nodes[0]!.canvas_y).toBe(Infinity);
  });

  test("uses default bounds for an empty canvas and tolerates partial position maps", () => {
    expect(computeSchemaCanvasBounds([], new Map())).toEqual({ width: 1600, height: 900, offsetX: 0, offsetY: 0 });
    const nodes = [node("first", [], -20, -40), node("second", [], 500, 600)];
    expect(computeSchemaCanvasBounds(nodes, new Map([["first", { x: 40, y: 60 }]]))).toEqual({
      width: 946, height: 968, offsetX: 80, offsetY: 60,
    });
    expect(computeSchemaCanvasBounds([nodes[0]!], new Map())).toEqual({ width: 486, height: 428, offsetX: 140, offsetY: 160 });
  });

  test("updates nested coordinates without changing siblings, provenance or persisted input", () => {
    const child = { ...node("child"), parent_id: "root" };
    const sibling = node("sibling");
    const tree = [node("root", [child, sibling])];
    const updated = updateTreeNodeInForest(tree, "child", { canvas_x: 0, canvas_y: 24 });
    expect(updated[0]!.children[0]).toEqual({ ...child, canvas_x: 0, canvas_y: 24 });
    expect(updated[0]!.children[1]).toBe(sibling);
    expect(tree[0]!.children[0]).toBe(child);
    expect(child.canvas_x).toBe(120);
    expect(updateTreeNodeInForest(tree, "missing", { parent_id: null })).toEqual(tree);
    expect(updateTreeNodeInForest([], "missing", { canvas_x: 0 })).toEqual([]);
  });

  test("applies partial position snapshots recursively and preserves unlisted leaves", () => {
    const child = node("child");
    const sibling = node("sibling");
    const tree = [node("root", [child, sibling])];
    const updated = applyCanvasPositionsToForest(tree, new Map([["child", { x: 240, y: 480 }]]));
    expect(updated[0]!.children[0]).toEqual({ ...child, canvas_x: 240, canvas_y: 480 });
    expect(updated[0]!.children[1]).toBe(sibling);
    expect(updated[0]!.canvas_x).toBe(120);
    expect(applyCanvasPositionsToForest([], new Map())).toEqual([]);
    expect(child.canvas_x).toBe(120);
  });
});

describe("hierarchy layouts", () => {
  const layouts = [
    ["horizontal", computeHorizontalTreeLayout], ["vertical", computeVerticalTreeLayout],
    ["horizontal guided", (tree: OrgUnitTreeNode[]) => computeHorizontalGuidedLayout(tree, "standard")],
    ["vertical guided", (tree: OrgUnitTreeNode[]) => computeVerticalGuidedLayout(tree, "standard")],
  ] as const;

  test.each(layouts)("%s lays out branching forests and leaves without modifying domain data", (_name, layout) => {
    const first = node("first", [node("child-a"), node("child-b", [node("grandchild")])]);
    const tree = [first, node("second")];
    const before = JSON.stringify(tree);
    expect(layout([])).toEqual(new Map());
    const positions = layout(tree);
    expect([...positions.keys()].sort()).toEqual(["child-a", "child-b", "first", "grandchild", "second"]);
    for (const position of positions.values()) {
      expect(position.x).toBeGreaterThanOrEqual(120);
      expect(position.y).toBeGreaterThanOrEqual(120);
    }
    expect(positions.get("child-a")).not.toEqual(positions.get("child-b"));
    expect(positions.get("first")).not.toEqual(positions.get("second"));
    expect(JSON.stringify(tree)).toBe(before);
  });
});

describe("collision resolution", () => {
  test.each(["horizontal", "vertical"] as const)("%s leaves empty and disjoint canvases unchanged", (orientation) => {
    const positions = new Map([["unit", { x: 0, y: 0 }]]);
    expect(resolveSubtreeCollisionShift(new Map(), [{ x: 0, y: 0 }], orientation)).toEqual({ x: 0, y: 0 });
    expect(resolveSubtreeCollisionShift(positions, [], orientation)).toEqual({ x: 0, y: 0 });
    expect(resolveSubtreeCollisionShift(positions, [{ x: 10000, y: 10000 }], orientation)).toEqual({ x: 0, y: 0 });
  });

  test.each(["horizontal", "vertical"] as const)("%s moves a colliding subtree while preserving relative positions", (orientation) => {
    const positions = new Map([["unit", { x: 0, y: 0 }], ["child", { x: 0, y: 260 }]]);
    const before = [...positions];
    const shift = resolveSubtreeCollisionShift(positions, [{ x: 0, y: 0 }], orientation);
    expect(shift).toEqual({ x: orientation === "horizontal" ? 302 : 286, y: 0 });
    expect([...positions]).toEqual(before);
  });

  test.each(["horizontal", "vertical"] as const)("%s uses the deterministic fallback on a saturated canvas", (orientation) => {
    const primaryStep = orientation === "horizontal" ? 302 : 286;
    const secondaryStep = orientation === "horizontal" ? 224 : 236;
    const occupied = [];
    for (let primaryIndex = -24; primaryIndex <= 24; primaryIndex += 1) {
      for (let secondaryIndex = -8; secondaryIndex <= 8; secondaryIndex += 1) {
        occupied.push({ x: primaryStep * primaryIndex, y: secondaryStep * secondaryIndex });
      }
    }
    expect(resolveSubtreeCollisionShift(new Map([["unit", { x: 0, y: 0 }]]), occupied, orientation)).toEqual(
      orientation === "horizontal" ? { x: primaryStep * 8, y: 0 } : { x: primaryStep * 6, y: secondaryStep * 2 },
    );
  });
});
