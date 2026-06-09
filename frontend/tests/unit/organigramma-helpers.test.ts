import { describe, expect, test } from "vitest";

import { computeTreeInclusion, flattenTree, unitPath } from "@/lib/organigramma";
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
