import type { PresenzeCollaboratorScheduleAssignment, PresenzeCollaboratorScheduleAssignmentCreateInput, PresenzeRecoveryAdjustment, PresenzeRecoveryAdjustmentCreateInput, PresenzeRecoveryAdjustmentReviewInput, PresenzeRecoveryAdjustmentUpdateInput, PresenzeRecoveryDashboardResponse, PresenzeBankHoursAdjustment, PresenzeBankHoursAdjustmentCreateInput, PresenzeBankHoursAdjustmentReviewInput, PresenzeBankHoursAdjustmentUpdateInput, PresenzeBankHoursCollaboratorDetailResponse, PresenzeBankHoursDashboardResponse, PresenzeHoliday, PresenzeHolidayCreateInput, PresenzeHolidayUpdateInput, PresenzeScheduleRule, PresenzeScheduleRuleCreateInput, PresenzeScheduleRuleUpdateInput, PresenzeScheduleTemplate, PresenzeScheduleTemplateCreateInput, PresenzeScheduleTemplateUpdateInput, PresenzeDashboardSummaryResponse, PresenzeDailyRecord, PresenzeDailyRecordManualUpdateInput } from "@/types/api";
import { ApiError, getApiBaseUrl, request } from "./core";

const PRESENZE_API_BASE = "/presenze";
export async function getPresenzeDashboardSummary(
  token: string,
  params: { periodStart: string; periodEnd: string },
): Promise<PresenzeDashboardSummaryResponse> {
  const query = new URLSearchParams({
    period_start: params.periodStart,
    period_end: params.periodEnd,
  });
  return request<PresenzeDashboardSummaryResponse>(`${PRESENZE_API_BASE}/dashboard/summary?${query.toString()}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function updatePresenzeDailyRecord(
  token: string,
  recordId: string,
  payload: PresenzeDailyRecordManualUpdateInput,
): Promise<PresenzeDailyRecord> {
  return request(`${PRESENZE_API_BASE}/giornaliere/${recordId}`, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function getPresenzeRecoveryDashboard(
  token: string,
  params: {
    dateFrom?: string;
    dateTo?: string;
    q?: string;
    negativeOnly?: boolean;
    pendingValidationOnly?: boolean;
    pendingAdjustmentsOnly?: boolean;
    manualAdjustmentsOnly?: boolean;
  } = {},
): Promise<PresenzeRecoveryDashboardResponse> {
  const query = new URLSearchParams();
  if (params.dateFrom) query.set("date_from", params.dateFrom);
  if (params.dateTo) query.set("date_to", params.dateTo);
  if (params.q) query.set("q", params.q);
  if (params.negativeOnly) query.set("negative_only", "true");
  if (params.pendingValidationOnly) query.set("pending_validation_only", "true");
  if (params.pendingAdjustmentsOnly) query.set("pending_adjustments_only", "true");
  if (params.manualAdjustmentsOnly) query.set("manual_adjustments_only", "true");
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return request<PresenzeRecoveryDashboardResponse>(`${PRESENZE_API_BASE}/recovery/dashboard${suffix}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function listPresenzeRecoveryAdjustments(
  token: string,
  collaboratorId?: string,
  approvalStatus?: "pending" | "approved" | "rejected",
): Promise<PresenzeRecoveryAdjustment[]> {
  const query = new URLSearchParams();
  if (collaboratorId) query.set("collaborator_id", collaboratorId);
  if (approvalStatus) query.set("approval_status", approvalStatus);
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return request<PresenzeRecoveryAdjustment[]>(`${PRESENZE_API_BASE}/recovery/adjustments${suffix}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function createPresenzeRecoveryAdjustment(
  token: string,
  payload: PresenzeRecoveryAdjustmentCreateInput,
): Promise<PresenzeRecoveryAdjustment> {
  return request<PresenzeRecoveryAdjustment>(`${PRESENZE_API_BASE}/recovery/adjustments`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function updatePresenzeRecoveryAdjustment(
  token: string,
  adjustmentId: string,
  payload: PresenzeRecoveryAdjustmentUpdateInput,
): Promise<PresenzeRecoveryAdjustment> {
  return request<PresenzeRecoveryAdjustment>(`${PRESENZE_API_BASE}/recovery/adjustments/${adjustmentId}`, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function deletePresenzeRecoveryAdjustment(token: string, adjustmentId: string): Promise<void> {
  await request<void>(`${PRESENZE_API_BASE}/recovery/adjustments/${adjustmentId}`, {
    method: "DELETE",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function reviewPresenzeRecoveryAdjustment(
  token: string,
  adjustmentId: string,
  payload: PresenzeRecoveryAdjustmentReviewInput,
): Promise<PresenzeRecoveryAdjustment> {
  return request<PresenzeRecoveryAdjustment>(`${PRESENZE_API_BASE}/recovery/adjustments/${adjustmentId}/review`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function getPresenzeBankHoursDashboard(
  token: string,
  params: {
    dateFrom?: string;
    dateTo?: string;
    q?: string;
    negativeOnly?: boolean;
    pendingAdjustmentsOnly?: boolean;
    manualAdjustmentsOnly?: boolean;
  },
): Promise<PresenzeBankHoursDashboardResponse> {
  const query = new URLSearchParams();
  if (params.dateFrom) query.set("date_from", params.dateFrom);
  if (params.dateTo) query.set("date_to", params.dateTo);
  if (params.q) query.set("q", params.q);
  if (params.negativeOnly) query.set("negative_only", "true");
  if (params.pendingAdjustmentsOnly) query.set("pending_adjustments_only", "true");
  if (params.manualAdjustmentsOnly) query.set("manual_adjustments_only", "true");
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return request<PresenzeBankHoursDashboardResponse>(`${PRESENZE_API_BASE}/bank-hours/dashboard${suffix}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getPresenzeBankHoursCollaboratorDetail(
  token: string,
  collaboratorId: string,
  params: {
    dateFrom?: string;
    dateTo?: string;
  },
): Promise<PresenzeBankHoursCollaboratorDetailResponse> {
  const query = new URLSearchParams();
  if (params.dateFrom) query.set("date_from", params.dateFrom);
  if (params.dateTo) query.set("date_to", params.dateTo);
  return request<PresenzeBankHoursCollaboratorDetailResponse>(
    `${PRESENZE_API_BASE}/bank-hours/collaborators/${collaboratorId}?${query.toString()}`,
    {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    },
  );
}

export async function listPresenzeBankHoursAdjustments(
  token: string,
  collaboratorId?: string,
  approvalStatus?: "pending" | "approved" | "rejected",
): Promise<PresenzeBankHoursAdjustment[]> {
  const query = new URLSearchParams();
  if (collaboratorId) query.set("collaborator_id", collaboratorId);
  if (approvalStatus) query.set("approval_status", approvalStatus);
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return request<PresenzeBankHoursAdjustment[]>(`${PRESENZE_API_BASE}/bank-hours/adjustments${suffix}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function createPresenzeBankHoursAdjustment(
  token: string,
  payload: PresenzeBankHoursAdjustmentCreateInput,
): Promise<PresenzeBankHoursAdjustment> {
  return request<PresenzeBankHoursAdjustment>(`${PRESENZE_API_BASE}/bank-hours/adjustments`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function updatePresenzeBankHoursAdjustment(
  token: string,
  adjustmentId: string,
  payload: PresenzeBankHoursAdjustmentUpdateInput,
): Promise<PresenzeBankHoursAdjustment> {
  return request<PresenzeBankHoursAdjustment>(`${PRESENZE_API_BASE}/bank-hours/adjustments/${adjustmentId}`, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function deletePresenzeBankHoursAdjustment(token: string, adjustmentId: string): Promise<void> {
  await request<void>(`${PRESENZE_API_BASE}/bank-hours/adjustments/${adjustmentId}`, {
    method: "DELETE",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function reviewPresenzeBankHoursAdjustment(
  token: string,
  adjustmentId: string,
  payload: PresenzeBankHoursAdjustmentReviewInput,
): Promise<PresenzeBankHoursAdjustment> {
  return request<PresenzeBankHoursAdjustment>(`${PRESENZE_API_BASE}/bank-hours/adjustments/${adjustmentId}/review`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function listPresenzeHolidays(token: string, year?: number): Promise<PresenzeHoliday[]> {
  const query = year != null ? `?year=${year}` : "";
  return request<PresenzeHoliday[]>(`${PRESENZE_API_BASE}/holidays${query}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function bootstrapPresenzeHolidays(token: string, year: number): Promise<{ year: number; created: number; items: PresenzeHoliday[] }> {
  return request(`${PRESENZE_API_BASE}/holidays/bootstrap?year=${year}`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function createPresenzeHoliday(token: string, payload: PresenzeHolidayCreateInput): Promise<PresenzeHoliday> {
  return request<PresenzeHoliday>(`${PRESENZE_API_BASE}/holidays`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function updatePresenzeHoliday(token: string, holidayId: number, payload: PresenzeHolidayUpdateInput): Promise<PresenzeHoliday> {
  return request<PresenzeHoliday>(`${PRESENZE_API_BASE}/holidays/${holidayId}`, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function deletePresenzeHoliday(token: string, holidayId: number): Promise<void> {
  await request<void>(`${PRESENZE_API_BASE}/holidays/${holidayId}`, {
    method: "DELETE",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function listPresenzeScheduleTemplates(token: string): Promise<PresenzeScheduleTemplate[]> {
  return request<PresenzeScheduleTemplate[]>(`${PRESENZE_API_BASE}/schedule/templates`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function createPresenzeScheduleTemplate(token: string, payload: PresenzeScheduleTemplateCreateInput): Promise<PresenzeScheduleTemplate> {
  return request<PresenzeScheduleTemplate>(`${PRESENZE_API_BASE}/schedule/templates`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function updatePresenzeScheduleTemplate(token: string, templateId: number, payload: PresenzeScheduleTemplateUpdateInput): Promise<PresenzeScheduleTemplate> {
  return request<PresenzeScheduleTemplate>(`${PRESENZE_API_BASE}/schedule/templates/${templateId}`, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function deletePresenzeScheduleTemplate(token: string, templateId: number): Promise<void> {
  await request<void>(`${PRESENZE_API_BASE}/schedule/templates/${templateId}`, {
    method: "DELETE",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function createPresenzeScheduleRule(token: string, templateId: number, payload: PresenzeScheduleRuleCreateInput): Promise<PresenzeScheduleRule> {
  return request<PresenzeScheduleRule>(`${PRESENZE_API_BASE}/schedule/templates/${templateId}/rules`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function updatePresenzeScheduleRule(token: string, ruleId: number, payload: PresenzeScheduleRuleUpdateInput): Promise<PresenzeScheduleRule> {
  return request<PresenzeScheduleRule>(`${PRESENZE_API_BASE}/schedule/rules/${ruleId}`, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function deletePresenzeScheduleRule(token: string, ruleId: number): Promise<void> {
  await request<void>(`${PRESENZE_API_BASE}/schedule/rules/${ruleId}`, {
    method: "DELETE",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function listPresenzeCollaboratorScheduleAssignments(token: string, collaboratorId: string): Promise<PresenzeCollaboratorScheduleAssignment[]> {
  return request<PresenzeCollaboratorScheduleAssignment[]>(`${PRESENZE_API_BASE}/collaborators/${collaboratorId}/schedule-assignments`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function createPresenzeCollaboratorScheduleAssignment(
  token: string,
  collaboratorId: string,
  payload: PresenzeCollaboratorScheduleAssignmentCreateInput,
): Promise<PresenzeCollaboratorScheduleAssignment> {
  return request<PresenzeCollaboratorScheduleAssignment>(`${PRESENZE_API_BASE}/collaborators/${collaboratorId}/schedule-assignments`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function deletePresenzeCollaboratorScheduleAssignment(token: string, assignmentId: number): Promise<void> {
  const response = await fetch(`${getApiBaseUrl()}${PRESENZE_API_BASE}/schedule-assignments/${assignmentId}`, {
    method: "DELETE",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    cache: "no-store",
  });

  if (!response.ok) {
    let detail = "Request failed";
    try {
      const payload = (await response.json()) as { detail?: unknown };
      if (typeof payload.detail === "string") {
        detail = payload.detail;
      }
    } catch {
      detail = response.statusText || detail;
    }
    throw new ApiError(detail, undefined, response.status);
  }
}

export async function deletePresenzeScheduleAssignment(token: string, assignmentId: number): Promise<void> {
  await deletePresenzeCollaboratorScheduleAssignment(token, assignmentId);
}
