import { createQueryString, request } from "@/lib/api";
import type { CatDomandeIrrigueListResponse } from "@/types/catasto";

function authHeaders(token: string): Record<string, string> {
  return { Authorization: `Bearer ${token}` };
}

export type ListSubjectDomandeIrrigueParams = {
  anno?: number;
  stato?: string;
  utenzaId?: string | null;
  limit?: number;
  offset?: number;
};

export async function listSubjectDomandeIrrigue(
  token: string,
  subjectId: string,
  params: ListSubjectDomandeIrrigueParams = {},
): Promise<CatDomandeIrrigueListResponse> {
  const query = createQueryString({
    subject_id: subjectId,
    utenza_id: params.utenzaId ?? undefined,
    anno: params.anno != null ? String(params.anno) : undefined,
    stato: params.stato,
    limit: params.limit != null ? String(params.limit) : undefined,
    offset: params.offset != null ? String(params.offset) : undefined,
  });
  return request<CatDomandeIrrigueListResponse>(`/catasto/domande-irrigue${query}`, {
    headers: authHeaders(token),
  });
}
