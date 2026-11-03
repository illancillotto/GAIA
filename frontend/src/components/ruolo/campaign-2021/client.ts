import { request, requestBlob } from "@/lib/api/core";

export type CampaignRow = {
  row: number; number: string; tax_code: string; name: string; digital: boolean;
  amounts: Record<string, string>;
  current: { accounting?: Record<string, string | null>; engine?: Record<string, string | null> };
  reconciliation: { kind: string; blockers: string[]; reviews: string[]; deltas: Record<string, string> };
};
export type CampaignReport = {
  id?: string; report_sha256: string; file_sha256: string; acquired_at: string;
  summary: { rows: number; ordinary: number; digital: number; total: string; warnings: string[]; parameters: { end: string } };
  rows: CampaignRow[];
};
export type Approval = { id: string; state: string; actor_id: number; approved_at: string; sent: false; notified: false };
export type ApprovalCommand = {
  report_sha256: string; row_number: number; amount_source: string; notification_fee: string;
  channel: string; fee_evidence: string; reason: string; resolutions: Record<string, string>; confirmed: true;
};
export type CampaignHistory = { id: string; filename: string; created_at: string };
const BASE = "/ruolo/tributi/campagna-2021";
const headers = (token: string) => ({ Authorization: `Bearer ${token}` });

export function history(token: string): Promise<CampaignHistory[]> {
  return request(BASE, { headers: headers(token) });
}

export function detail(token: string, id: string): Promise<CampaignReport> {
  return request(`${BASE}/${id}`, { headers: headers(token) });
}

export function analyze(token: string, file: File): Promise<CampaignReport> {
  const body = new FormData(); body.append("file", file);
  return request(`${BASE}/analisi`, { method: "POST", headers: headers(token), body });
}

export function retain(token: string, file: File, reportHash: string): Promise<CampaignReport> {
  const body = new FormData(); body.append("file", file); body.append("report_sha256", reportHash);
  return request(`${BASE}/importazioni`, { method: "POST", headers: headers(token), body });
}

export function approve(token: string, id: string, body: ApprovalCommand): Promise<Approval> {
  return request(`${BASE}/${id}/approvazioni`, { method: "POST", headers: headers(token), body: JSON.stringify(body) });
}

export function preview(token: string, id: string): Promise<Blob> {
  return requestBlob(`${BASE}/approvazioni/${id}/anteprima`, { method: "POST", headers: headers(token) });
}
