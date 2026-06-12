import { describe, expect, test } from "vitest";

import { computeAutoCollapsedIds, computeTreeInclusion, filterTreeByRootIds, flattenTree, unitPath } from "@/lib/organigramma";
import type { OrgUnitTreeNode } from "@/types/api";

function node(id: string, nome: string, tipo: OrgUnitTreeNode["tipo"], parent: string | null, children: OrgUnitTreeNode[] = []): OrgUnitTreeNode {
  return {
    id,
    nome,
    tipo,
    parent_id: parent,
    canvas_x: 0,
    canvas_y: 0,
    source: "manuale",
    wc_area_id: null,
    legacy_team_id: null,
    is_active: true,
    sort_order: 0,
    person_count: 0,
    child_count: children.length,
    children,
  };
}

// Direzione > Distretto > [Settore Idraulico > Squadra A], Settore Elettro
const squadraA = node("d", "Squadra Manutenzione A", "squadra", "c");
const settoreIdr = node("c", "Settore Idraulico", "settore", "b", [squadraA]);
const settoreEl = node("e", "Settore Elettromeccanico", "settore", "b");
const distretto = node("b", "Distretto Tirso", "distretto", "a", [settoreIdr, settoreEl]);
const direzione = node("a", "Direzione Generale", "direzione", null, [distretto]);
const TREE = [direzione];

describe("flattenTree", () => {
  test("returns every node depth-first", () => {
    expect(flattenTree(TREE).map((n) => n.id)).toEqual(["a", "b", "c", "d", "e"]);
  });
});

describe("computeAutoCollapsedIds", () => {
  test("keeps root and next two levels visible when the tree is large", () => {
    const collapsed = computeAutoCollapsedIds(TREE, {
      threshold: 1,
      expandedDepth: 2,
    });

    expect(collapsed.has("a")).toBe(false);
    expect(collapsed.has("b")).toBe(false);
    expect(collapsed.has("c")).toBe(true);
    expect(collapsed.has("d")).toBe(false);
  });

  test("collapses deeper branching nodes after the expanded depth", () => {
    const squadraB = node("f", "Squadra B", "squadra", "d", [node("g", "Gruppo G", "squadra", "f")]);
    const deepTree = [node("a", "Direzione", "direzione", null, [node("b", "Distretto", "distretto", "a", [node("c", "Settore", "settore", "b", [node("d", "Reparto", "squadra", "c", [squadraB])])])])];

    const collapsed = computeAutoCollapsedIds(deepTree, {
      threshold: 1,
      expandedDepth: 2,
    });

    expect(collapsed.has("c")).toBe(true);
    expect(collapsed.has("d")).toBe(true);
    expect(collapsed.has("f")).toBe(true);
    expect(collapsed.has("a")).toBe(false);
    expect(collapsed.has("b")).toBe(false);
  });
});

describe("computeTreeInclusion", () => {
  test("no filter -> includeIds null", () => {
    const { includeIds, matchIds } = computeTreeInclusion(TREE, "", "all");
    expect(includeIds).toBeNull();
    expect(matchIds.size).toBe(0);
  });

  test("text search includes match and its ancestors", () => {
    const { includeIds, matchIds } = computeTreeInclusion(TREE, "manutenzione", "all");
    expect(matchIds).toEqual(new Set(["d"]));
    expect(includeIds).toEqual(new Set(["a", "b", "c", "d"])); // ancestor chain
    expect(includeIds?.has("e")).toBe(false);
  });

  test("type filter selects all units of a tipo plus ancestors", () => {
    const { includeIds, matchIds } = computeTreeInclusion(TREE, "", "settore");
    expect(matchIds).toEqual(new Set(["c", "e"]));
    expect(includeIds).toEqual(new Set(["a", "b", "c", "e"]));
  });

  test("combined text + type filter", () => {
    const { matchIds } = computeTreeInclusion(TREE, "idraulico", "settore");
    expect(matchIds).toEqual(new Set(["c"]));
  });
});

describe("unitPath", () => {
  test("builds breadcrumb root -> node", () => {
    expect(unitPath("d", flattenTree(TREE)).map((n) => n.nome)).toEqual([
      "Direzione Generale",
      "Distretto Tirso",
      "Settore Idraulico",
      "Squadra Manutenzione A",
    ]);
  });

  test("unknown id -> empty", () => {
    expect(unitPath("zzz", flattenTree(TREE))).toEqual([]);
  });
});

describe("filterTreeByRootIds", () => {
  test("focuses a settore subtree and promotes it to root", () => {
    const filtered = filterTreeByRootIds(TREE, new Set(["c"]));
    expect(filtered).toHaveLength(1);
    expect(filtered[0]?.id).toBe("c");
    expect(filtered[0]?.parent_id).toBeNull();
    expect(filtered[0]?.children.map((item) => item.id)).toEqual(["d"]);
  });

  test("returns the original forest when no root filter is active", () => {
    expect(filterTreeByRootIds(TREE, null)).toBe(TREE);
  });
});
