import type { PresenzeDashboardWorkspaceResponse } from "@/types/api";

import { request } from "./core";

export async function getPresenzeDashboardWorkspace(
  token: string,
  params: { periodStart: string; periodEnd: string },
): Promise<PresenzeDashboardWorkspaceResponse> {
  const query = new URLSearchParams({
    period_start: params.periodStart,
    period_end: params.periodEnd,
  });
  return request<PresenzeDashboardWorkspaceResponse>(`/presenze/dashboard?${query.toString()}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}
