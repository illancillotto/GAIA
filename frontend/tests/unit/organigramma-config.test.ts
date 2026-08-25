import { describe, expect, test } from "vitest";

import { defaultLeadPositionCode, defaultLeadTitle, TYPE_FILTERS, TYPE_META } from "@/features/organigramma/organigramma-config";
import type { OrgUnitType } from "@/types/api";

const TYPES: OrgUnitType[] = ["direzione", "distretto", "settore", "reparto", "squadra"];

describe("organigramma config", () => {
  test("defines labels and filters for every organizational unit", () => {
    expect(Object.keys(TYPE_META)).toEqual(TYPES);
    expect(TYPE_FILTERS.map((item) => item.value)).toEqual(["all", ...TYPES]);
  });

  test.each([
    ["direzione", "Dirigente", "dirigente"],
    ["distretto", "Responsabile distretto", null],
    ["settore", "Capo settore", "capo_settore"],
    ["reparto", "Capo reparto", "capo_reparto"],
    ["squadra", "Capo operai", "capo_operai"],
  ] as const)("maps %s to its lead title and position", (tipo, title, position) => {
    expect(defaultLeadTitle(tipo)).toBe(title);
    expect(defaultLeadPositionCode(tipo)).toBe(position);
  });
});
