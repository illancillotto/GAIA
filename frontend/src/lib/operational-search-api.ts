import { request } from "@/lib/api";
import type { OperationalSearchResponse } from "@/types/api";


export function searchOperational(
  token: string,
  query: string,
  params: { limit?: number } = {},
): Promise<OperationalSearchResponse> {
  const searchParams = new URLSearchParams({ q: query });
  if (params.limit != null) {
    searchParams.set("limit", String(params.limit));
  }
  return request<OperationalSearchResponse>(`/search?${searchParams.toString()}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
}
