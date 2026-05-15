import { ApiError, getApiBaseUrl } from "@/lib/api";
import type {
  RuoloAvvisoDetailResponse,
  RuoloAvvisoListResponse,
  RuoloImportJobListResponse,
  RuoloImportJobResponse,
  RuoloImportUploadResponse,
  RuoloImportYearDetectionResponse,
  RuoloStatsResponse,
  RuoloStatsComuneResponse,
} from "@/types/ruolo";

async function extractError(response: Response): Promise<never> {
  let detail = "Request failed";
  try {
    const payload = (await response.json()) as { detail?: unknown };
    if (typeof payload.detail === "string") {
      detail = payload.detail;
    } else if (payload.detail != null) {
      detail = JSON.stringify(payload.detail);
    }
  } catch {
    detail = response.statusText || detail;
  }
  throw new ApiError(detail, undefined, response.status);
}

async function ruoloRequest<T>(path: string, token: string, init?: RequestInit): Promise<T> {
  const isFormData = typeof FormData !== "undefined" && init?.body instanceof FormData;
  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    ...init,
    headers: {
      ...(isFormData ? {} : { "Content-Type": "application/json" }),
      Authorization: `Bearer ${token}`,
      ...init?.headers,
    },
  });
  if (!response.ok) return extractError(response);
  return response.json() as Promise<T>;
}

// ── Import Jobs ───────────────────────────────────────────────────────────────

export async function uploadRuoloFile(
  token: string,
  file: File,
  annoTributario?: number,
): Promise<RuoloImportUploadResponse> {
  const form = new FormData();
  form.append("file", file);
  if (annoTributario != null) {
    form.append("anno_tributario", String(annoTributario));
  }
  return ruoloRequest<RuoloImportUploadResponse>("/ruolo/import/upload", token, {
    method: "POST",
    body: form,
  });
}

export async function detectRuoloImportYear(
  token: string,
  file: File,
): Promise<RuoloImportYearDetectionResponse> {
  const form = new FormData();
  form.append("file", file);
  return ruoloRequest<RuoloImportYearDetectionResponse>("/ruolo/import/detect-year", token, {
    method: "POST",
    body: form,
  });
}

export async function listImportJobs(
  token: string,
  anno?: number,
  page = 1,
  pageSize = 20,
): Promise<RuoloImportJobListResponse> {
  const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
  if (anno != null) params.set("anno", String(anno));
  return ruoloRequest<RuoloImportJobListResponse>(`/ruolo/import/jobs?${params}`, token);
}

export async function getImportJob(token: string, jobId: string): Promise<RuoloImportJobResponse> {
  return ruoloRequest<RuoloImportJobResponse>(`/ruolo/import/jobs/${jobId}`, token);
}

// ── Avvisi ────────────────────────────────────────────────────────────────────

export type ListAvvisiParams = {
  anno?: number;
  subject_id?: string;
  q?: string;
  codice_fiscale?: string;
  comune?: string;
  codice_utenza?: string;
  unlinked?: boolean;
  page?: number;
  page_size?: number;
};

export async function listAvvisi(
  token: string,
  params: ListAvvisiParams = {},
): Promise<RuoloAvvisoListResponse> {
  const qs = new URLSearchParams();
  if (params.anno != null) qs.set("anno", String(params.anno));
  if (params.subject_id) qs.set("subject_id", params.subject_id);
  if (params.q) qs.set("q", params.q);
  if (params.codice_fiscale) qs.set("codice_fiscale", params.codice_fiscale);
  if (params.comune) qs.set("comune", params.comune);
  if (params.codice_utenza) qs.set("codice_utenza", params.codice_utenza);
  if (params.unlinked) qs.set("unlinked", "true");
  qs.set("page", String(params.page ?? 1));
  qs.set("page_size", String(params.page_size ?? 20));
  return ruoloRequest<RuoloAvvisoListResponse>(`/ruolo/avvisi?${qs}`, token);
}

export async function getAvviso(token: string, avvisoId: string): Promise<RuoloAvvisoDetailResponse> {
  return ruoloRequest<RuoloAvvisoDetailResponse>(`/ruolo/avvisi/${avvisoId}`, token);
}

export async function getAvvisiBySubject(
  token: string,
  subjectId: string,
): Promise<RuoloAvvisoDetailResponse[]> {
  return ruoloRequest<RuoloAvvisoDetailResponse[]>(`/ruolo/soggetti/${subjectId}/avvisi`, token);
}

export function buildExportCsvUrl(params: ListAvvisiParams): string {
  const qs = new URLSearchParams();
  if (params.anno != null) qs.set("anno", String(params.anno));
  if (params.subject_id) qs.set("subject_id", params.subject_id);
  if (params.q) qs.set("q", params.q);
  if (params.codice_fiscale) qs.set("codice_fiscale", params.codice_fiscale);
  if (params.comune) qs.set("comune", params.comune);
  if (params.codice_utenza) qs.set("codice_utenza", params.codice_utenza);
  if (params.unlinked) qs.set("unlinked", "true");
  return `${getApiBaseUrl()}/ruolo/avvisi/export?${qs}`;
}

// ── Stats ─────────────────────────────────────────────────────────────────────

export async function getRuoloStats(token: string, anno?: number): Promise<RuoloStatsResponse> {
  const qs = new URLSearchParams();
  if (anno != null) qs.set("anno", String(anno));
  return ruoloRequest<RuoloStatsResponse>(`/ruolo/stats?${qs}`, token);
}

export async function getRuoloStatsComuni(
  token: string,
  anno: number,
): Promise<RuoloStatsComuneResponse> {
  return ruoloRequest<RuoloStatsComuneResponse>(`/ruolo/stats/comuni?anno=${anno}`, token);
}
