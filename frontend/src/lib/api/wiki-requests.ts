import type { WikiRequest, WikiRequestAssignee, WikiRequestArtifact, WikiRequestArtifactCreateInput, WikiRequestDuplicateCandidate, WikiRequestCreateInput, WikiRequestEvent, WikiRequestFeedbackInput, WikiRequestFamily, WikiRequestMakeCanonicalInput, WikiRequestMarkDuplicateInput, WikiMyRequestsSummary, WikiRequestReopenInput, WikiRequestUpdateInput, WikiToolAuditLogListResponse } from "@/types/api";
import { ApiError, getApiBaseUrl, request } from "./core";

export async function getWikiToolAuditLogs(
  token: string,
  params: {
    page?: number;
    pageSize?: number;
    toolName?: string;
    moduleKey?: string;
    conversationId?: string;
    username?: string;
    intent?: string;
    mode?: string;
    success?: boolean | null;
  } = {},
): Promise<WikiToolAuditLogListResponse> {
  const query = new URLSearchParams();
  if (params.page) {
    query.set("page", String(params.page));
  }
  if (params.pageSize) {
    query.set("page_size", String(params.pageSize));
  }
  if (params.toolName) {
    query.set("tool_name", params.toolName);
  }
  if (params.moduleKey) {
    query.set("module_key", params.moduleKey);
  }
  if (params.conversationId) {
    query.set("conversation_id", params.conversationId);
  }
  if (params.username) {
    query.set("username", params.username);
  }
  if (params.intent) {
    query.set("intent", params.intent);
  }
  if (params.mode) {
    query.set("mode", params.mode);
  }
  if (params.success != null) {
    query.set("success", String(params.success));
  }

  const suffix = query.toString() ? `?${query.toString()}` : "";
  return request<WikiToolAuditLogListResponse>(`/wiki/audit/tool-calls${suffix}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getWikiRequests(token: string): Promise<WikiRequest[]> {
  return request<WikiRequest[]>("/wiki/requests", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getWikiRequest(token: string, requestId: string): Promise<WikiRequest> {
  return request<WikiRequest>(`/wiki/requests/${requestId}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getWikiRequestArtifacts(token: string, requestId: string): Promise<WikiRequestArtifact[]> {
  return request<WikiRequestArtifact[]>(`/wiki/requests/${requestId}/artifacts`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function downloadWikiRequestArtifact(token: string, requestId: string, artifactId: string): Promise<Blob> {
  const response = await fetch(`${getApiBaseUrl()}/wiki/requests/${requestId}/artifacts/${artifactId}/download`, {
    method: "GET",
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
    throw new ApiError(detail, null, response.status);
  }

  return response.blob();
}

export async function getWikiRequestAssignees(token: string): Promise<WikiRequestAssignee[]> {
  return request<WikiRequestAssignee[]>("/wiki/requests/assignees", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getWikiRequestEvents(token: string, requestId: string): Promise<WikiRequestEvent[]> {
  return request<WikiRequestEvent[]>(`/wiki/requests/${requestId}/events`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getWikiRequestDuplicates(token: string, requestId: string): Promise<WikiRequestDuplicateCandidate[]> {
  return request<WikiRequestDuplicateCandidate[]>(`/wiki/requests/${requestId}/duplicates`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getWikiRequestLinkedDuplicates(token: string, requestId: string): Promise<WikiRequestDuplicateCandidate[]> {
  return request<WikiRequestDuplicateCandidate[]>(`/wiki/requests/${requestId}/linked-duplicates`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getWikiRequestFamily(token: string, requestId: string): Promise<WikiRequestFamily> {
  return request<WikiRequestFamily>(`/wiki/requests/${requestId}/family`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getMyWikiRequests(token: string): Promise<WikiRequest[]> {
  return request<WikiRequest[]>("/wiki/requests/mine", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getMyWikiRequestsSummary(token: string): Promise<WikiMyRequestsSummary> {
  return request<WikiMyRequestsSummary>("/wiki/requests/mine/summary", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function markWikiRequestViewed(token: string, requestId: string): Promise<WikiRequest> {
  return request<WikiRequest>(`/wiki/requests/${requestId}/mark-viewed`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function reopenWikiRequest(
  token: string,
  requestId: string,
  payload: WikiRequestReopenInput,
): Promise<WikiRequest> {
  return request<WikiRequest>(`/wiki/requests/${requestId}/reopen`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function createWikiRequest(token: string, payload: WikiRequestCreateInput): Promise<WikiRequest> {
  return request<WikiRequest>("/wiki/requests", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function createWikiRequestWithArtifacts(
  token: string,
  payload: WikiRequestCreateInput,
  artifacts: WikiRequestArtifactCreateInput,
): Promise<WikiRequest> {
  const formData = new FormData();
  formData.set("payload_json", JSON.stringify(payload));
  if (artifacts.screenshotMeta) {
    formData.set("screenshot_meta_json", JSON.stringify(artifacts.screenshotMeta));
  }
  if (artifacts.uiSnapshot) {
    formData.set("ui_snapshot_json", JSON.stringify(artifacts.uiSnapshot));
  }
  if (artifacts.screenshotFile) {
    formData.set("screenshot", artifacts.screenshotFile);
  }
  return request<WikiRequest>("/wiki/requests/with-artifacts", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: formData,
  });
}

export async function updateWikiRequest(
  token: string,
  requestId: string,
  payload: WikiRequestUpdateInput,
): Promise<WikiRequest> {
  return request<WikiRequest>(`/wiki/requests/${requestId}`, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function markWikiRequestDuplicate(
  token: string,
  requestId: string,
  payload: WikiRequestMarkDuplicateInput,
): Promise<WikiRequest> {
  return request<WikiRequest>(`/wiki/requests/${requestId}/mark-duplicate`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function unlinkWikiRequestDuplicate(token: string, requestId: string): Promise<WikiRequest> {
  return request<WikiRequest>(`/wiki/requests/${requestId}/unlink-duplicate`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function makeWikiRequestCanonical(
  token: string,
  requestId: string,
  payload: WikiRequestMakeCanonicalInput = {},
): Promise<WikiRequestFamily> {
  return request<WikiRequestFamily>(`/wiki/requests/${requestId}/make-canonical`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function updateWikiRequestFeedback(
  token: string,
  requestId: string,
  payload: WikiRequestFeedbackInput,
): Promise<WikiRequest> {
  return request<WikiRequest>(`/wiki/requests/${requestId}/feedback`, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}
