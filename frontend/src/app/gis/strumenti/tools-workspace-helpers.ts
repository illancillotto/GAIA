import { createGisShapefileImportChangeRequests } from "@/lib/api/gis";
import type {
  GisCatalogLayer,
  GisShapefileImport,
  GisShapefileImportCreateInput,
} from "@/types/gis";

export type PendingImportAction = "publish" | "reject";

export function readableError(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback;
}

export function inferLayerName(filename: string): string {
  return filename
    .replace(/\.zip$/i, "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "")
    .slice(0, 120);
}

export function isEditablePostgisLayer(layer: GisCatalogLayer): boolean {
  return layer.is_active && layer.source_type === "postgis" && layer.can_edit;
}

export function firstEditableLayerId(layers: GisCatalogLayer[]): string {
  return layers.find(isEditablePostgisLayer)?.id ?? "";
}

export function parseSourceSrid(sourceSrid: string): number | undefined | "invalid" {
  if (!sourceSrid.trim()) return undefined;
  const parsedSrid = Number.parseInt(sourceSrid, 10);
  if (!Number.isInteger(parsedSrid) || parsedSrid < 1) return "invalid";
  return parsedSrid;
}

export type ShapefileUploadBuild =
  | { ok: false; error: string }
  | { ok: true; token: string; payload: GisShapefileImportCreateInput };

export function buildShapefileUpload(input: {
  token: string | null;
  file: File | null;
  workspace: string;
  title: string;
  layerName: string;
  sourceSrid: string;
  encoding: string;
}): ShapefileUploadBuild {
  if (!input.token || !input.file || !input.workspace.trim() || !input.title.trim() || !input.layerName) {
    return { ok: false, error: "Scegli un file ZIP e indica area e titolo della mappa." };
  }
  const parsedSrid = parseSourceSrid(input.sourceSrid);
  if (parsedSrid === "invalid") {
    return { ok: false, error: "Il sistema di coordinate deve essere un numero valido." };
  }
  return {
    ok: true,
    token: input.token,
    payload: {
      file: input.file,
      workspace: input.workspace.trim(),
      domainModule: input.workspace === "rete" ? "network" : input.workspace,
      targetLayerName: input.layerName,
      targetLayerTitle: input.title.trim(),
      officialSource: "shapefile_upload",
      sourceSrid: parsedSrid,
      encoding: input.encoding,
    },
  };
}

export function canPreviewImport(item: GisShapefileImport): boolean {
  return item.status === "validated" || item.status === "published";
}

export function canPublishImport(item: GisShapefileImport): boolean {
  return item.status === "validated";
}

export function canRejectImport(item: GisShapefileImport): boolean {
  return item.status !== "rejected" && item.status !== "published";
}

export function canProposeChanges(item: GisShapefileImport, editableCount: number): boolean {
  return canPreviewImport(item) && editableCount > 0;
}

export function guidedChangesNotice(created: number, existing: number): string {
  return `${created} proposte create${existing ? `, ${existing} già presenti` : ""}.`;
}

export async function createAllGuidedChangeRequests(
  token: string,
  importId: string,
  targetLayerId: string,
  justification: string,
): Promise<{ created: number; existing: number }> {
  let offset = 0;
  let created = 0;
  let existing = 0;
  while (true) {
    const result = await createGisShapefileImportChangeRequests(token, importId, {
      targetLayerId,
      justification,
      limit: 100,
      offset,
    });
    created += result.created_count;
    existing += result.existing_count;
    if (!result.has_more || result.returned_count === 0) break;
    offset += result.returned_count;
  }
  return { created, existing };
}
