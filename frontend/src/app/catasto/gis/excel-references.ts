import type { GisParticellaRef, GisResolveRefsResponse } from "@/types/gis";

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

export type ExcelImportSummary = { kind: "error" | "info"; message: string } | null;

type ExcelImportCounts = Pick<GisResolveRefsResponse, "processed" | "found" | "not_found" | "multiple" | "invalid">;

export function summarizeExcelImport(resolved: ExcelImportCounts, withGeometry: number): ExcelImportSummary {
  if (resolved.found === 0) {
    return { kind: "error", message: `Nessuna particella trovata su ${resolved.processed} righe.` };
  }
  if (withGeometry === 0) {
    return {
      kind: "error",
      message: `Trovate ${resolved.found} particelle ma nessuna ha geometria: controlla che lo shapefile sia stato importato.`,
    };
  }
  if (!(resolved.not_found + resolved.multiple + resolved.invalid > 0)) return null;
  const parts: string[] = [`Import completato: trovate ${resolved.found}/${resolved.processed}.`];
  if (resolved.not_found > 0) parts.push(`Non trovate: ${resolved.not_found}.`);
  if (resolved.multiple > 0) parts.push(`Multiple: ${resolved.multiple}.`);
  if (resolved.invalid > 0) parts.push(`Righe invalide: ${resolved.invalid}.`);
  return { kind: "info", message: parts.join(" ") };
}
