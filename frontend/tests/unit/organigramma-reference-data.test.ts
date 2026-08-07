import { describe, expect, test } from "vitest";

import { getOrgReference, ORG_REFERENCE_BY_UNIT } from "@/app/organigramma/reference-data";

describe("organigramma reference data", () => {
  test("exports area catasto reference sheet", () => {
    expect(ORG_REFERENCE_BY_UNIT["area catasto"].totalHeadcount).toBe(75);
    expect(ORG_REFERENCE_BY_UNIT["area catasto"].rows).toHaveLength(10);
  });

  test("getOrgReference resolves case-insensitive trimmed names", () => {
    expect(getOrgReference(" Area Catasto ")).toEqual(ORG_REFERENCE_BY_UNIT["area catasto"]);
  });

  test("getOrgReference returns null for missing or empty names", () => {
    expect(getOrgReference(null)).toBeNull();
    expect(getOrgReference("unknown unit")).toBeNull();
  });
});
