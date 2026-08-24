import { request, requestBlob } from "@/lib/api";
import type { MeStraordinariExportRequest, MeStraordinariPreviewResponse } from "@/types/api";

const ME_STRAORDINARI_API_BASE = "/me/presenze/straordinari";

export type MeStraordinariPeriodPreviewResponse = MeStraordinariPreviewResponse & {
  available_months: string[];
};

export async function previewMeStraordinariPeriodRequest(token: string, periodStart: string): Promise<MeStraordinariPeriodPreviewResponse> {
  return request<MeStraordinariPeriodPreviewResponse>(`${ME_STRAORDINARI_API_BASE}/preview/${periodStart}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function downloadMeStraordinariPeriodRequest(
  token: string,
  format: "xlsx" | "pdf",
  payload: MeStraordinariExportRequest,
  periodStart: string,
): Promise<Blob> {
  return requestBlob(`${ME_STRAORDINARI_API_BASE}/export/${format}/${periodStart}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}
