import type { GisParticellaRef } from "@/types/gis";

const REFERENCE_ALIASES = {
  comune: ["comune", "Comune", "COMUNE"],
  sezione: ["sezione", "Sezione", "SEZIONE"],
  foglio: ["foglio", "Foglio", "FOGLIO"],
  particella: ["particella", "Particella", "PARTICELLA"],
  sub: ["sub", "Sub", "SUB", "subalterno", "Subalterno"],
};

function readReferenceCell(row: Record<string, unknown>, aliases: string[]): string | null {
  for (const alias of aliases) {
    const value = row[alias];
    if (value != null) {
      const normalized = String(value).trim();
      return normalized.length > 0 ? normalized : null;
    }
  }
  return null;
}

export function normalizeExcelReferences(rows: Record<string, unknown>[]): GisParticellaRef[] {
  return rows.slice(0, 5000).map((row, index) => ({
    row_index: index + 2,
    comune: readReferenceCell(row, REFERENCE_ALIASES.comune),
    sezione: readReferenceCell(row, REFERENCE_ALIASES.sezione),
    foglio: readReferenceCell(row, REFERENCE_ALIASES.foglio),
    particella: readReferenceCell(row, REFERENCE_ALIASES.particella),
    sub: readReferenceCell(row, REFERENCE_ALIASES.sub),
  }));
}
