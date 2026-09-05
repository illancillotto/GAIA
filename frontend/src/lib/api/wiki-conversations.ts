import type { WikiConversationMetricsSeriesResponse, WikiConversationMetricsSummary, WikiConversationContextLink, WikiConversationGovernanceConfig, WikiConversationMetricsBackfillJob, WikiConversationMetricsBackfillJobChainDetail, WikiConversationMetricsBackfillJobChainListResponse, WikiConversationMetricsBackfillJobChainSummary, WikiConversationMetricsBackfillJobPruneResponse } from "@/types/api";
import type { WikiConversation, WikiConversationSummary, WikiConversationSummaryMetrics } from "@/features/wiki/types";
import { request } from "./core";

export async function getWikiConversationMetricsSummary(
  token: string,
  params: { days?: number | null } = {},
): Promise<WikiConversationMetricsSummary> {
  const query = new URLSearchParams();
  if (params.days != null) {
    query.set("days", String(params.days));
  }
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return request<WikiConversationMetricsSummary>(`/wiki/conversations/metrics/summary${suffix}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getWikiConversationMetricsSeries(
  token: string,
  params: {
    dimensionType?: string | null;
    dimensionKey?: string | null;
    days?: number | null;
    granularity?: string | null;
  } = {},
): Promise<WikiConversationMetricsSeriesResponse> {
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
  return request<WikiConversationMetricsSeriesResponse>(`/wiki/conversations/metrics/series${suffix}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getWikiConversations(
  token: string,
  params: {
    limit?: number;
    search?: string | null;
    status?: string | null;
    priority?: string | null;
    assignedTo?: string | null;
    reviewReason?: string | null;
    needsReview?: boolean | null;
    createdBy?: string | null;
    contextArticle?: string | null;
  } = {},
): Promise<WikiConversationSummary[]> {
  const query = new URLSearchParams();
  if (params.limit != null) {
    query.set("limit", String(params.limit));
  }
  if (params.search) {
    query.set("search", params.search);
  }
  if (params.status) {
    query.set("status", params.status);
  }
  if (params.priority) {
    query.set("priority", params.priority);
  }
  if (params.assignedTo) {
    query.set("assigned_to", params.assignedTo);
  }
  if (params.reviewReason) {
    query.set("review_reason", params.reviewReason);
  }
  if (params.needsReview != null) {
    query.set("needs_review", String(params.needsReview));
  }
  if (params.createdBy) {
    query.set("created_by", params.createdBy);
  }
  if (params.contextArticle) {
    query.set("context_article", params.contextArticle);
  }
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return request<WikiConversationSummary[]>(`/wiki/conversations${suffix}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getWikiConversationSummary(
  token: string,
): Promise<WikiConversationSummaryMetrics> {
  return request<WikiConversationSummaryMetrics>("/wiki/conversations/summary", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getWikiConversationDetail(token: string, conversationId: string): Promise<WikiConversation> {
  return request<WikiConversation>(`/wiki/conversations/${conversationId}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function updateWikiConversation(
  token: string,
  conversationId: string,
  payload: Partial<Pick<WikiConversationSummary, "status" | "priority" | "assigned_to">>,
): Promise<WikiConversation> {
  return request<WikiConversation>(`/wiki/conversations/${conversationId}`, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function resolveWikiConversationContextLink(
  token: string,
  params: {
    entityKey?: string | null;
    moduleKey?: string | null;
  } = {},
): Promise<WikiConversationContextLink> {
  const query = new URLSearchParams();
  if (params.entityKey) {
    query.set("entity_key", params.entityKey);
  }
  if (params.moduleKey) {
    query.set("module_key", params.moduleKey);
  }
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return request<WikiConversationContextLink>(`/wiki/conversations/context-link${suffix}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getWikiConversationGovernanceConfig(token: string): Promise<WikiConversationGovernanceConfig> {
  return request<WikiConversationGovernanceConfig>("/wiki/conversations/governance-config", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function updateWikiConversationGovernanceConfig(
  token: string,
  payload: {
    fallback_heavy_threshold?: number;
    no_match_repeated_threshold?: number;
    high_latency_ms_threshold?: number;
  },
): Promise<WikiConversationGovernanceConfig> {
  return request<WikiConversationGovernanceConfig>("/wiki/conversations/governance-config", {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function backfillWikiConversationMetrics(
  token: string,
  payload: {
    start_date: string;
    end_date: string;
    data_complete_from?: string | null;
  },
): Promise<WikiConversationGovernanceConfig> {
  return request<WikiConversationGovernanceConfig>("/wiki/conversations/metrics/backfill", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function enqueueWikiConversationMetricsBackfill(
  token: string,
  payload: {
    start_date: string;
    end_date: string;
    data_complete_from?: string | null;
  },
): Promise<WikiConversationMetricsBackfillJob> {
  return request<WikiConversationMetricsBackfillJob>("/wiki/conversations/metrics/backfill-jobs", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function getLatestWikiConversationMetricsBackfillJob(
  token: string,
): Promise<WikiConversationMetricsBackfillJob | null> {
  return request<WikiConversationMetricsBackfillJob | null>("/wiki/conversations/metrics/backfill-jobs/latest", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function listWikiConversationMetricsBackfillJobChains(
  token: string,
  limit = 10,
  filters: {
    latestStatus?: string;
    requestedBy?: string;
    hasActiveRetry?: boolean;
    sortBy?: string;
  } = {},
): Promise<WikiConversationMetricsBackfillJobChainListResponse> {
  const query = new URLSearchParams();
  query.set("limit", String(limit));
  if (filters.latestStatus) {
    query.set("latest_status", filters.latestStatus);
  }
  if (filters.requestedBy) {
    query.set("requested_by", filters.requestedBy);
  }
  if (filters.hasActiveRetry != null) {
    query.set("has_active_retry", String(filters.hasActiveRetry));
  }
  if (filters.sortBy) {
    query.set("sort_by", filters.sortBy);
  }
  return request<WikiConversationMetricsBackfillJobChainListResponse>(
    `/wiki/conversations/metrics/backfill-job-chains?${query.toString()}`,
    {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    },
  );
}

export async function getWikiConversationMetricsBackfillJobChainSummary(
  token: string,
  filters: {
    latestStatus?: string;
    requestedBy?: string;
    hasActiveRetry?: boolean;
    sortBy?: string;
  } = {},
): Promise<WikiConversationMetricsBackfillJobChainSummary> {
  const query = new URLSearchParams();
  if (filters.latestStatus) {
    query.set("latest_status", filters.latestStatus);
  }
  if (filters.requestedBy) {
    query.set("requested_by", filters.requestedBy);
  }
  if (filters.hasActiveRetry != null) {
    query.set("has_active_retry", String(filters.hasActiveRetry));
  }
  if (filters.sortBy) {
    query.set("sort_by", filters.sortBy);
  }
  const queryString = query.toString();
  return request<WikiConversationMetricsBackfillJobChainSummary>(
    `/wiki/conversations/metrics/backfill-job-chains/summary${queryString ? `?${queryString}` : ""}`,
    {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    },
  );
}

export async function getWikiConversationMetricsBackfillJobChainDetail(
  token: string,
  rootJobId: string,
): Promise<WikiConversationMetricsBackfillJobChainDetail> {
  return request<WikiConversationMetricsBackfillJobChainDetail>(
    `/wiki/conversations/metrics/backfill-job-chains/${encodeURIComponent(rootJobId)}`,
    {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    },
  );
}

export async function retryWikiConversationMetricsBackfillJob(
  token: string,
  jobId: string,
): Promise<WikiConversationMetricsBackfillJob> {
  return request<WikiConversationMetricsBackfillJob>(
    `/wiki/conversations/metrics/backfill-jobs/${encodeURIComponent(jobId)}/retry`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
      },
    },
  );
}

export async function clearWikiConversationMetricsBackfillJobHistory(
  token: string,
): Promise<WikiConversationMetricsBackfillJobPruneResponse> {
  return request<WikiConversationMetricsBackfillJobPruneResponse>("/wiki/conversations/metrics/backfill-jobs", {
    method: "DELETE",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}
