import { request } from "@/lib/api";

export interface YearStatus {
  year: number;
  total: number;
  ready: number;
  failed: { item_id: string; label: string }[];
  missing: { label: string; avviso_ids: string[] }[];
}

export interface YearGenerationResult {
  batch_id: string | null;
  generated: number;
  problems: { label: string; detail: string }[];
}

const BASE = "/ruolo/tributi/solleciti/years";

export function getYearStatus(token: string, year: number): Promise<YearStatus> {
  return request<YearStatus>(`${BASE}/${year}/status`, { headers: { Authorization: `Bearer ${token}` } });
}

export function generateYearNotices(token: string, year: number, avvisoIds: string[]): Promise<YearGenerationResult> {
  return request<YearGenerationResult>(`${BASE}/${year}/generate`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify({ avviso_ids: avvisoIds }),
  });
}
