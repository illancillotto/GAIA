import { getApiBaseUrl } from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import type { Asset, AssetInput, Custody, Lookups, PageResult } from "./types";

async function request<T>(path: string, method = "GET", body?: unknown): Promise<T> {
  const token = getStoredAccessToken();
  const response = await fetch(`${getApiBaseUrl()}/dotazioni${path}`, {
    method,
    headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    body: body === undefined ? undefined : JSON.stringify(body),
    cache: "no-store",
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    const detail = payload?.detail;
    throw new Error(typeof detail === "string" ? detail : `Operazione non riuscita (${response.status})`);
  }
  return response.json();
}

export const dotazioniApi = {
  list: (filters: URLSearchParams) => request<PageResult<Asset>>(`/assets?${filters}`),
  asset: (id: string) => request<Asset>(`/assets/${encodeURIComponent(id)}`),
  byCode: (code: string) => request<Asset>(`/assets/by-code/${encodeURIComponent(code)}`),
  create: (body: AssetInput) => request<Asset>("/assets", "POST", body),
  update: (id: string, body: Partial<AssetInput>) => request<Asset>(`/assets/${encodeURIComponent(id)}`, "PATCH", body),
  history: (id: string, page: number) => request<PageResult<Custody>>(`/assets/${encodeURIComponent(id)}/custody-history?page=${page}&page_size=25`),
  custody: (id: string, action: "take" | "return" | "transfer", body: { holder_user_id?: number; notes?: string }) => request<Asset>(`/assets/${encodeURIComponent(id)}/${action}`, "POST", body),
  operatorAssets: (id: number) => request<PageResult<Asset>>(`/operators/${id}/assets?page=1&page_size=100`),
  lookups: () => request<Lookups>("/lookups"),
};
