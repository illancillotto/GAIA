import { createQueryString, request, requestBlob } from "@/lib/api";
import type { CatDistrettoExportJob, CatDistrettoExportJobListResponse, UUID } from "@/types/catasto";

function authHeaders(token: string): Record<string, string> {
  return { Authorization: `Bearer ${token}` };
}

export async function catastoCreateElaborazioneMassivaDistrettoExportJob(
  token: string,
  numDistretto: string,
  format: "csv" | "xlsx",
): Promise<CatDistrettoExportJob> {
  return request<CatDistrettoExportJob>(
    `/catasto/elaborazioni-massive/particelle/distretti/${encodeURIComponent(numDistretto)}/exports?format=${format}`,
    {
      method: "POST",
      headers: authHeaders(token),
    },
  );
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
