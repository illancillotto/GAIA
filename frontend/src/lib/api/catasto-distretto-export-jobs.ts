import { createQueryString, request, requestBlob } from "@/lib/api";
import type { CatDistrettoExportJob, CatDistrettoExportJobListResponse, UUID } from "@/types/catasto";

function authHeaders(token: string): Record<string, string> {
  return { Authorization: `Bearer ${token}` };
}

export async function catastoCreateElaborazioneMassivaScopeExportJob(
  token: string,
  kind: "distretti" | "comuni",
  values: string[],
  format: "csv" | "xlsx",
): Promise<CatDistrettoExportJob> {
  return request<CatDistrettoExportJob>("/catasto/elaborazioni-massive/particelle/exports", {
    method: "POST",
    headers: { ...authHeaders(token), "Content-Type": "application/json" },
    body: JSON.stringify({ kind, values, format }),
  });
}

export async function catastoListElaborazioneMassivaDistrettoExportJobs(
  token: string,
  params?: { limit?: number },
): Promise<CatDistrettoExportJobListResponse> {
  const query = createQueryString({ limit: params?.limit != null ? String(params.limit) : undefined });
  return request<CatDistrettoExportJobListResponse>(`/catasto/elaborazioni-massive/particelle/distretti/exports${query}`, {
    headers: authHeaders(token),
  });
}

export async function catastoGetElaborazioneMassivaDistrettoExportJob(
  token: string,
  jobId: UUID,
): Promise<CatDistrettoExportJob> {
  return request<CatDistrettoExportJob>(`/catasto/elaborazioni-massive/particelle/distretti/exports/${jobId}`, {
    headers: authHeaders(token),
  });
}

export async function catastoDownloadElaborazioneMassivaDistrettoExportJob(
  token: string,
  jobId: UUID,
): Promise<Blob> {
  return requestBlob(`/catasto/elaborazioni-massive/particelle/distretti/exports/${jobId}/download`, {
    headers: authHeaders(token),
  });
}
