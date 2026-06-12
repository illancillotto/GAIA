import type { SectionResponse, UserPermissionsAdminView } from "@/types/api";

export type SectionOverrideValue = "inherit" | "grant" | "deny";

export function buildSectionDraftFromOverrides(
  overrides: UserPermissionsAdminView["overrides"],
): Record<number, SectionOverrideValue> {
  return Object.fromEntries(
    overrides.map((override) => [override.section_id, override.is_granted ? "grant" : "deny"]),
  );
}

export function buildEditableSectionCatalog(options: {
  sectionCatalog: SectionResponse[];
  enabledModuleKeys: string[];
  overriddenSectionIds: Set<number>;
}): SectionResponse[] {
  const moduleSet = new Set(options.enabledModuleKeys);
  return options.sectionCatalog.filter(
    (section) => moduleSet.has(section.module) || options.overriddenSectionIds.has(section.id),
  );
}

export function filterEditableSections(options: {
  sections: SectionResponse[];
  draft: Record<number, SectionOverrideValue>;
  searchTerm: string;
  overrideOnly: boolean;
}): SectionResponse[] {
  const normalizedSearch = options.searchTerm.trim().toLowerCase();

  return options.sections.filter((section) => {
    const draftValue = options.draft[section.id] ?? "inherit";

    if (options.overrideOnly && draftValue === "inherit") {
      return false;
    }

    if (!normalizedSearch) {
      return true;
    }

    return [section.label, section.description ?? "", section.key, section.module]
      .some((value) => value.toLowerCase().includes(normalizedSearch));
  });
}

export function groupSectionsByModule(sections: SectionResponse[]): Array<[string, SectionResponse[]]> {
  const groups = new Map<string, SectionResponse[]>();

  for (const section of sections) {
    const current = groups.get(section.module) ?? [];
    current.push(section);
    groups.set(section.module, current);
  }

  return [...groups.entries()];
}

export function computeSectionOverrideChanges(
  draft: Record<number, SectionOverrideValue>,
  overrides: UserPermissionsAdminView["overrides"],
): {
  toDelete: number[];
  toUpsert: Array<{ section_id: number; is_granted: boolean }>;
} {
  const existingSectionIds = new Set(overrides.map((override) => override.section_id));
  const desiredEntries = Object.entries(draft).map(([sectionId, value]) => ({
    sectionId: Number(sectionId),
    value,
  }));

  return {
    toDelete: desiredEntries
      .filter((entry) => entry.value === "inherit" && existingSectionIds.has(entry.sectionId))
      .map((entry) => entry.sectionId),
    toUpsert: desiredEntries
      .filter((entry) => entry.value !== "inherit")
      .map((entry) => ({
        section_id: entry.sectionId,
        is_granted: entry.value === "grant",
      })),
  };
}

export function hasUnsavedSectionDraftChanges(options: {
  sectionIds: number[];
  draft: Record<number, SectionOverrideValue>;
  overrides: UserPermissionsAdminView["overrides"];
}): boolean {
  const overridesBySectionId = new Map(
    options.overrides.map((override) => [
      override.section_id,
      override.is_granted ? "grant" : "deny",
    ] satisfies [number, SectionOverrideValue]),
  );

  return options.sectionIds.some((sectionId) => {
    const currentDraftValue = options.draft[sectionId] ?? "inherit";
    const persistedValue = overridesBySectionId.get(sectionId) ?? "inherit";
    return currentDraftValue !== persistedValue;
  });
}
