import type { WikiSupportClustersResponse, WikiSupportInsightsResponse, WikiSupportAnalyticsSeriesResponse, WikiSupportAnalyticsSummary, WikiToolAuditLogDetailResponse, WikiToolAuditLogRelatedResponse, WikiToolAuditSummary, WikiTelemetryPruneResponse, WikiTelemetryRefreshResponse, WikiTelemetryRetention, WikiTelemetrySchedule, WikiTelemetrySeriesResponse, WikiTelemetrySummary } from "@/types/api";
import { request, requestBlob } from "./core";

export async function getWikiSupportAnalyticsSummary(
  token: string,
  params: { days?: number | null; deliveryStatus?: string | null; ticketLinked?: boolean | null } = {},
): Promise<WikiSupportAnalyticsSummary> {
  const query = new URLSearchParams();
  if (params.days != null) {
    query.set("days", String(params.days));
  }
  if (params.deliveryStatus) {
    query.set("delivery_status", params.deliveryStatus);
  }
  if (params.ticketLinked != null) {
    query.set("ticket_linked", String(params.ticketLinked));
  }
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return request<WikiSupportAnalyticsSummary>(`/wiki/support/analytics/summary${suffix}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getWikiSupportAnalyticsSeries(
  token: string,
  params: { days?: number | null; deliveryStatus?: string | null; ticketLinked?: boolean | null } = {},
): Promise<WikiSupportAnalyticsSeriesResponse> {
  const query = new URLSearchParams();
  if (params.days != null) {
    query.set("days", String(params.days));
  }
  if (params.deliveryStatus) {
    query.set("delivery_status", params.deliveryStatus);
  }
  if (params.ticketLinked != null) {
    query.set("ticket_linked", String(params.ticketLinked));
  }
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return request<WikiSupportAnalyticsSeriesResponse>(`/wiki/support/analytics/series${suffix}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getWikiSupportAnalyticsClusters(
  token: string,
  params: { days?: number | null; limit?: number | null; deliveryStatus?: string | null; ticketLinked?: boolean | null } = {},
): Promise<WikiSupportClustersResponse> {
  const query = new URLSearchParams();
  if (params.days != null) {
    query.set("days", String(params.days));
  }
  if (params.limit != null) {
    query.set("limit", String(params.limit));
  }
  if (params.deliveryStatus) {
    query.set("delivery_status", params.deliveryStatus);
  }
  if (params.ticketLinked != null) {
    query.set("ticket_linked", String(params.ticketLinked));
  }
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return request<WikiSupportClustersResponse>(`/wiki/support/analytics/clusters${suffix}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getWikiSupportAnalyticsInsights(
  token: string,
  params: { days?: number | null; deliveryStatus?: string | null; ticketLinked?: boolean | null } = {},
): Promise<WikiSupportInsightsResponse> {
  const query = new URLSearchParams();
  if (params.days != null) {
    query.set("days", String(params.days));
  }
  if (params.deliveryStatus) {
    query.set("delivery_status", params.deliveryStatus);
  }
  if (params.ticketLinked != null) {
    query.set("ticket_linked", String(params.ticketLinked));
  }
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return request<WikiSupportInsightsResponse>(`/wiki/support/analytics/insights${suffix}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getWikiToolAuditSummary(
  token: string,
  params: {
    toolName?: string;
    moduleKey?: string;
    conversationId?: string;
    username?: string;
    intent?: string;
    mode?: string;
    success?: boolean | null;
  } = {},
): Promise<WikiToolAuditSummary> {
  const query = new URLSearchParams();
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
  return request<WikiToolAuditSummary>(`/wiki/audit/tool-calls/summary${suffix}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getWikiToolAuditLogDetail(
  token: string,
  auditId: string,
): Promise<WikiToolAuditLogDetailResponse> {
  return request<WikiToolAuditLogDetailResponse>(`/wiki/audit/tool-calls/${auditId}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getWikiToolAuditRelatedLogs(
  token: string,
  auditId: string,
  params: { limit?: number | null } = {},
): Promise<WikiToolAuditLogRelatedResponse> {
  const query = new URLSearchParams();
  if (params.limit != null) {
    query.set("limit", String(params.limit));
  }
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return request<WikiToolAuditLogRelatedResponse>(`/wiki/audit/tool-calls/${auditId}/related${suffix}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function exportWikiToolAuditLogs(
  token: string,
  params: {
    toolName?: string;
    moduleKey?: string;
    conversationId?: string;
    username?: string;
    intent?: string;
    mode?: string;
    success?: boolean | null;
  } = {},
): Promise<Blob> {
  const query = new URLSearchParams();
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
  return requestBlob(`/wiki/audit/tool-calls/export${suffix}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getWikiTelemetrySummary(
  token: string,
  params: { days?: number | null } = {},
): Promise<WikiTelemetrySummary> {
  const query = new URLSearchParams();
  if (params.days != null) {
    query.set("days", String(params.days));
  }

  const suffix = query.toString() ? `?${query.toString()}` : "";
  return request<WikiTelemetrySummary>(`/wiki/telemetry/summary${suffix}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getWikiTelemetrySeries(
  token: string,
  params: {
    dimensionType?: string | null;
    dimensionKey?: string | null;
    days?: number | null;
    granularity?: string | null;
  } = {},
): Promise<WikiTelemetrySeriesResponse> {
  const query = new URLSearchParams();
  if (params.dimensionType) {
    query.set("dimension_type", params.dimensionType);
  }
  if (params.dimensionKey) {
    query.set("dimension_key", params.dimensionKey);
  }
  if (params.days != null) {
    query.set("days", String(params.days));
  }
  if (params.granularity) {
    query.set("granularity", params.granularity);
  }

  const suffix = query.toString() ? `?${query.toString()}` : "";
  return request<WikiTelemetrySeriesResponse>(`/wiki/telemetry/series${suffix}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function refreshWikiTelemetry(
  token: string,
  params: { days?: number | null } = {},
): Promise<WikiTelemetryRefreshResponse> {
  const query = new URLSearchParams();
  if (params.days != null) {
    query.set("days", String(params.days));
  }
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return request<WikiTelemetryRefreshResponse>(`/wiki/telemetry/refresh${suffix}`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getWikiTelemetrySchedule(token: string): Promise<WikiTelemetrySchedule> {
  return request<WikiTelemetrySchedule>("/wiki/telemetry/schedule", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getWikiTelemetryRetention(token: string): Promise<WikiTelemetryRetention> {
  return request<WikiTelemetryRetention>("/wiki/telemetry/retention", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function pruneWikiTelemetry(token: string): Promise<WikiTelemetryPruneResponse> {
  return request<WikiTelemetryPruneResponse>("/wiki/telemetry/prune", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function exportWikiTelemetrySeries(
  token: string,
  params: {
    dimensionType?: string | null;
    dimensionKey?: string | null;
    days?: number | null;
    granularity?: string | null;
  } = {},
): Promise<Blob> {
  const query = new URLSearchParams();
  if (params.dimensionType) {
    query.set("dimension_type", params.dimensionType);
  }
  if (params.dimensionKey) {
    query.set("dimension_key", params.dimensionKey);
  }
  if (params.days != null) {
    query.set("days", String(params.days));
  }
  if (params.granularity) {
    query.set("granularity", params.granularity);
  }

  const suffix = query.toString() ? `?${query.toString()}` : "";
  return requestBlob(`/wiki/telemetry/series/export${suffix}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}
