import { request } from "@/lib/api";
import type { BatchPosteDispatch } from "@/lib/ruolo-batch-overview-api";
import type { PosteDispatchLotDetail } from "@/types/ruolo-poste-dispatch";

export type WorkspaceStage = "available" | "processing" | "draft" | "sent" | "review" | "conflict";
export type WorkspaceFilters = { q: string; year: string; account: string; stage: string; page: number };
export type WorkspaceGroup = { years: number[]; account_key: string; account_label: string; total: number; stages: Partial<Record<WorkspaceStage, number>> };
export type WorkspaceNotice = {
  item_id: string; batch_id: string; notice_number: string | null; codice_fiscale: string;
  label: string; years: number[]; document_status: string; amount: number; can_prepare: boolean;
  download_url: string | null; poste_dispatches: BatchPosteDispatch[]; account_key: string;
  account_label: string; lot_id: string | null; stage: WorkspaceStage;
};
export type WorkspaceResult = { groups: WorkspaceGroup[]; items: WorkspaceNotice[]; total: number; page: number; page_size: number };
export type GenerationResult = { reused: string[]; created: string[]; problems: { item_id: string; detail: string }[] };

const BASE = "/ruolo/tributi/solleciti/workspace";
const auth = (token: string) => ({ Authorization: `Bearer ${token}` });

export function getSollecitiWorkspace(token: string, filters: WorkspaceFilters): Promise<WorkspaceResult> {
  const query = new URLSearchParams({ q: filters.q, account: filters.account, stage: filters.stage, page: String(filters.page), page_size: "20" });
  if (filters.year) query.set("year", filters.year);
  return request(`${BASE}?${query}`, { headers: auth(token), cache: "no-store" });
}

export function generateSolleciti(token: string, year: number, taxCode: string): Promise<GenerationResult> {
  return request(`${BASE}/generate`, { method: "POST", headers: auth(token), body: JSON.stringify({ year, tax_code: taxCode }) });
}

export function prepareSolleciti(token: string, itemIds: string[], credentialId: number): Promise<PosteDispatchLotDetail> {
  return request(`${BASE}/prepare`, { method: "POST", headers: auth(token), body: JSON.stringify({ item_ids: itemIds, credential_id: credentialId }) });
}

export function reconcileSollecitiAccount(token: string, credentialId: number, year: number | null): Promise<{ queued_jobs: number[]; busy_lots: number }> {
  return request(`${BASE}/reconcile`, { method: "POST", headers: auth(token), body: JSON.stringify({ credential_id: credentialId, year }) });
}
