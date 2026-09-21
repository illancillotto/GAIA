import { request, requestBlob } from "@/lib/api/core";

export type ImportBatch = {
  id: string; filename: string; source: string; status: string; digest: string;
  parser_version: string; actor_id: number; confirmed_by: number | null;
  created_at: string; confirmed_at: string | null; reason: string | null;
  summary: { rows: number; ignored_non_operational: number; outcomes: Record<string, number> };
};
export type ImportRow = {
  id: string; row_number: number; source_key: string; fingerprint: string;
  document_id: string | null; outcome: string; anomalies: string[];
  resolution: { decision: string; actor_id: number; reason: string; decided_at: string; document_version: number; document_id: string; evidence_id: string | null } | null;
  payload: { document_number: string; tax_code: string | null; positions: unknown[]; original: unknown; dates?: Record<string, string | null> };
};
const BASE = "/ruolo/tributi/registro-avvisi/importazioni";

export function submitImport(token: string, path: string, body: FormData | Record<string, unknown>) {
  return request<ImportBatch>(`${BASE}${path}`, {
    method: "POST", headers: { Authorization: `Bearer ${token}` },
    body: body instanceof FormData ? body : JSON.stringify(body),
  });
}

export async function downloadImport(token: string, batch: ImportBatch) {
  const blob = await requestBlob(`${BASE}/${batch.id}/originale`, { headers: { Authorization: `Bearer ${token}` } });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = batch.source === "poste_db" ? "poste-snapshot.json" : "avvisi-originale.xlsx";
  link.click();
  URL.revokeObjectURL(url);
}
