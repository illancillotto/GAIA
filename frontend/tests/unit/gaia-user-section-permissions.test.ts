import { describe, expect, test } from "vitest";

import {
  buildEditableSectionCatalog,
  buildSectionDraftFromOverrides,
  computeSectionOverrideChanges,
  filterEditableSections,
  groupSectionsByModule,
  hasUnsavedSectionDraftChanges,
} from "@/app/gaia/users/section-permissions";
import type { SectionResponse, UserPermissionsAdminView } from "@/types/api";

function section(id: number, module: string, key: string, label: string, description: string | null = null): SectionResponse {
  return {
    id,
    module,
    key,
    label,
    description,
    min_role: "viewer",
    is_active: true,
    sort_order: id,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  };
}

function override(sectionId: number, isGranted: boolean): UserPermissionsAdminView["overrides"][number] {
  return {
    id: sectionId,
    user_id: 99,
    section_id: sectionId,
    is_granted: isGranted,
    granted_by_id: 1,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  };
}

const CATALOG = [
  section(1, "accessi", "accessi.users", "Utenti Accessi", "Gestione utenti applicativi"),
  section(2, "organigramma", "organigramma.read", "Vista organigramma", "Lettura struttura"),
  section(3, "catasto", "catasto.particelle", "Particelle", "Consulta particelle"),
  section(4, "accessi", "accessi.reports", "Report Accessi", "Report e audit"),
];

describe("gaia user section permissions helpers", () => {
  test("builds draft values from existing overrides", () => {
    expect(buildSectionDraftFromOverrides([override(1, true), override(3, false)])).toEqual({
      1: "grant",
      3: "deny",
    });
  });

  test("includes catalog sections for enabled modules and preserved overrides", () => {
    const result = buildEditableSectionCatalog({
      sectionCatalog: CATALOG,
      enabledModuleKeys: ["accessi"],
      overriddenSectionIds: new Set([3]),
    });

    expect(result.map((item) => item.id)).toEqual([1, 3, 4]);
  });

  test("filters by search term and override-only toggle", () => {
    const filtered = filterEditableSections({
      sections: CATALOG,
      draft: { 2: "grant", 4: "deny" },
      searchTerm: "report",
      overrideOnly: true,
    });

    expect(filtered.map((item) => item.id)).toEqual([4]);
  });

  test("groups visible sections by module preserving order", () => {
    const grouped = groupSectionsByModule([CATALOG[0], CATALOG[3], CATALOG[2]]);
    expect(grouped).toEqual([
      ["accessi", [CATALOG[0], CATALOG[3]]],
      ["catasto", [CATALOG[2]]],
    ]);
  });

  test("computes delete and upsert operations from draft diff", () => {
    const changes = computeSectionOverrideChanges(
      {
        1: "inherit",
        2: "grant",
        3: "deny",
      },
      [override(1, true), override(4, false)],
    );

    expect(changes.toDelete).toEqual([1]);
    expect(changes.toUpsert).toEqual([
      { section_id: 2, is_granted: true },
      { section_id: 3, is_granted: false },
    ]);
  });

  test("detects unsaved changes only for the selected module sections", () => {
    expect(
      hasUnsavedSectionDraftChanges({
        sectionIds: [1, 4],
        draft: { 1: "grant", 3: "deny", 4: "inherit" },
        overrides: [override(1, true), override(4, false)],
      }),
    ).toBe(true);

    expect(
      hasUnsavedSectionDraftChanges({
        sectionIds: [1, 4],
        draft: { 1: "grant", 3: "deny", 4: "deny" },
        overrides: [override(1, true), override(4, false)],
      }),
    ).toBe(false);
  });
});
