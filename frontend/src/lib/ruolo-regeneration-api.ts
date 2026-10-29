import { request } from "@/lib/api";

export type RegenerationMode = "template" | "recompute";

export interface RegenerationTarget {
  item_id: string;
  batch_id: string;
  display_name: string | null;
  codice_fiscale: string;
}

export interface RegenerationTargets {
  items: RegenerationTarget[];
  excluded_drafts: number;
}

export interface RegenerationResult {
  item_id: string;
  outcome: "regenerated" | "skipped" | "failed";
  detail: string | null;
}

const BASE = "/ruolo/tributi/solleciti";

function auth(token: string) {
  return { Authorization: `Bearer ${token}` };
}

export function listRegenerationTargets(token: string, batchId: string | null): Promise<RegenerationTargets> {
  const query = batchId ? `?${new URLSearchParams({ batch_id: batchId })}` : "";
  return request<RegenerationTargets>(`${BASE}/regeneration-targets${query}`, { headers: auth(token) });
}

export function regenerateReminderItem(token: string, itemId: string, mode: RegenerationMode): Promise<RegenerationResult> {
  return request<RegenerationResult>(`${BASE}/items/${itemId}/regenerate`, {
    method: "POST",
    headers: auth(token),
    body: JSON.stringify({ mode }),
  });
}
