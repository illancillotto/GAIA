import { request, requestBlob } from "@/lib/api";
import type { MeStraordinariExportRequest, MeStraordinariPreviewResponse } from "@/types/api";

const ME_STRAORDINARI_API_BASE = "/api/me/presenze/straordinari";

export async function previewMeStraordinariPeriodRequest(token: string, periodStart: string): Promise<MeStraordinariPreviewResponse> {
  return request<MeStraordinariPreviewResponse>(`${ME_STRAORDINARI_API_BASE}/preview/${periodStart}`, {
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
