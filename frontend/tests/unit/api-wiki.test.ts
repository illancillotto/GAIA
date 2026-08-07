import { afterEach, describe, expect, test, vi } from "vitest";

import {
  createWikiRequest,
  createWikiRequestWithArtifacts,
  getWikiArticles,
  getWikiConversationDetail,
  getWikiConversationGovernanceConfig,
  getWikiConversationMetricsBackfillJobChainDetail,
  getWikiConversationMetricsBackfillJobChainSummary,
  getWikiConversationMetricsSeries,
  getWikiConversationMetricsSummary,
  getWikiConversationSummary,
  getWikiConversations,
  getWikiRequest,
  getWikiRequestArtifacts,
  getWikiRequestAssignees,
  getWikiRequestDuplicates,
  getWikiRequestEvents,
  getWikiRequestFamily,
  getWikiRequestLinkedDuplicates,
  getWikiRequests,
  getWikiSupportAnalyticsClusters,
  getWikiSupportAnalyticsInsights,
  getWikiSupportAnalyticsSeries,
  getWikiSupportAnalyticsSummary,
  getWikiTelemetryRetention,
  getWikiTelemetrySchedule,
  getWikiTelemetrySeries,
  getWikiTelemetrySummary,
  getWikiToolAuditLogDetail,
  getWikiToolAuditLogs,
  getWikiToolAuditRelatedLogs,
  getWikiToolAuditSummary,
  listWikiConversationMetricsBackfillJobChains,
  updateWikiConversation,
  updateWikiConversationGovernanceConfig,
  updateWikiRequest,
  updateWikiRequestFeedback,
} from "@/lib/api";

const TOKEN = "test-token";

function jsonResponse(payload: unknown, status = 200): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "content-type": "application/json" },
  });
}

function blobResponse(content = "blob-data"): Response {
  return new Response(new Blob([content]), { status: 200 });
}

function emptyOkResponse(status = 204): Response {
  return new Response(null, { status });
}

function stubFetch(...responses: Response[]) {
  const fetchMock = vi.fn();
  for (const response of responses) {
    fetchMock.mockResolvedValueOnce(response);
  }
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

describe("api wiki clients", () => {

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  test("createWikiRequest", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(createWikiRequest(TOKEN, {})).resolves.toBeDefined();
  });
  test("createWikiRequestWithArtifacts", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(createWikiRequestWithArtifacts(TOKEN, {}, {})).resolves.toBeDefined();
  });
  test("getWikiArticles", async () => {
    stubFetch(jsonResponse([]));
    await expect(getWikiArticles(TOKEN)).resolves.toBeDefined();
  });
  test("getWikiConversationDetail", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(getWikiConversationDetail(TOKEN, "id-1")).resolves.toBeDefined();
  });
  test("getWikiConversationGovernanceConfig", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(getWikiConversationGovernanceConfig(TOKEN)).resolves.toBeDefined();
  });
  test("getWikiConversationMetricsBackfillJobChainDetail", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(getWikiConversationMetricsBackfillJobChainDetail(TOKEN, "id-1")).resolves.toBeDefined();
  });
  test("getWikiConversationMetricsBackfillJobChainSummary", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(getWikiConversationMetricsBackfillJobChainSummary(TOKEN, {})).resolves.toBeDefined();
  });
  test("getWikiConversationMetricsSeries", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(getWikiConversationMetricsSeries(TOKEN, { page: 1, pageSize: 20, periodStart: '2026-08-01', periodEnd: '2026-08-31', parentId: 'id-1', structureKind: 'organigramma', toolName: 'x', moduleKey: 'wiki', module: 'wiki', success: true, limit: 10, skip: 0, activeOnly: true, windowMinutes: 15, status: 'active', conversationId: 'c1', username: 'u', intent: 'x', mode: 'x', q: 'x', bustCache: true })).resolves.toBeDefined();
  });
  test("getWikiConversationMetricsSummary", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(getWikiConversationMetricsSummary(TOKEN, { page: 1, pageSize: 20, periodStart: '2026-08-01', periodEnd: '2026-08-31', parentId: 'id-1', structureKind: 'organigramma', toolName: 'x', moduleKey: 'wiki', module: 'wiki', success: true, limit: 10, skip: 0, activeOnly: true, windowMinutes: 15, status: 'active', conversationId: 'c1', username: 'u', intent: 'x', mode: 'x', q: 'x', bustCache: true })).resolves.toBeDefined();
  });
  test("getWikiConversationSummary", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(getWikiConversationSummary(TOKEN)).resolves.toBeDefined();
  });
  test("getWikiConversations", async () => {
    stubFetch(jsonResponse([]));
    await expect(getWikiConversations(TOKEN, { page: 1, pageSize: 20, periodStart: '2026-08-01', periodEnd: '2026-08-31', parentId: 'id-1', structureKind: 'organigramma', toolName: 'x', moduleKey: 'wiki', module: 'wiki', success: true, limit: 10, skip: 0, activeOnly: true, windowMinutes: 15, status: 'active', conversationId: 'c1', username: 'u', intent: 'x', mode: 'x', q: 'x', bustCache: true })).resolves.toBeDefined();
  });
  test("getWikiRequest", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(getWikiRequest(TOKEN, "id-1")).resolves.toBeDefined();
  });
  test("getWikiRequestArtifacts", async () => {
    stubFetch(jsonResponse([]));
    await expect(getWikiRequestArtifacts(TOKEN, "id-1")).resolves.toBeDefined();
  });
  test("getWikiRequestAssignees", async () => {
    stubFetch(jsonResponse([]));
    await expect(getWikiRequestAssignees(TOKEN)).resolves.toBeDefined();
  });
  test("getWikiRequestDuplicates", async () => {
    stubFetch(jsonResponse([]));
    await expect(getWikiRequestDuplicates(TOKEN, "id-1")).resolves.toBeDefined();
  });
  test("getWikiRequestEvents", async () => {
    stubFetch(jsonResponse([]));
    await expect(getWikiRequestEvents(TOKEN, "id-1")).resolves.toBeDefined();
  });
  test("getWikiRequestFamily", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(getWikiRequestFamily(TOKEN, "id-1")).resolves.toBeDefined();
  });
  test("getWikiRequestLinkedDuplicates", async () => {
    stubFetch(jsonResponse([]));
    await expect(getWikiRequestLinkedDuplicates(TOKEN, "id-1")).resolves.toBeDefined();
  });
  test("getWikiRequests", async () => {
    stubFetch(jsonResponse([]));
    await expect(getWikiRequests(TOKEN)).resolves.toBeDefined();
  });
  test("getWikiSupportAnalyticsClusters", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(getWikiSupportAnalyticsClusters(TOKEN, { page: 1, pageSize: 20, periodStart: '2026-08-01', periodEnd: '2026-08-31', parentId: 'id-1', structureKind: 'organigramma', toolName: 'x', moduleKey: 'wiki', module: 'wiki', success: true, limit: 10, skip: 0, activeOnly: true, windowMinutes: 15, status: 'active', conversationId: 'c1', username: 'u', intent: 'x', mode: 'x', q: 'x', bustCache: true })).resolves.toBeDefined();
  });
  test("getWikiSupportAnalyticsInsights", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(getWikiSupportAnalyticsInsights(TOKEN, { page: 1, pageSize: 20, periodStart: '2026-08-01', periodEnd: '2026-08-31', parentId: 'id-1', structureKind: 'organigramma', toolName: 'x', moduleKey: 'wiki', module: 'wiki', success: true, limit: 10, skip: 0, activeOnly: true, windowMinutes: 15, status: 'active', conversationId: 'c1', username: 'u', intent: 'x', mode: 'x', q: 'x', bustCache: true })).resolves.toBeDefined();
  });
  test("getWikiSupportAnalyticsSeries", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(getWikiSupportAnalyticsSeries(TOKEN, { page: 1, pageSize: 20, periodStart: '2026-08-01', periodEnd: '2026-08-31', parentId: 'id-1', structureKind: 'organigramma', toolName: 'x', moduleKey: 'wiki', module: 'wiki', success: true, limit: 10, skip: 0, activeOnly: true, windowMinutes: 15, status: 'active', conversationId: 'c1', username: 'u', intent: 'x', mode: 'x', q: 'x', bustCache: true })).resolves.toBeDefined();
  });
  test("getWikiSupportAnalyticsSummary", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(getWikiSupportAnalyticsSummary(TOKEN, { page: 1, pageSize: 20, periodStart: '2026-08-01', periodEnd: '2026-08-31', parentId: 'id-1', structureKind: 'organigramma', toolName: 'x', moduleKey: 'wiki', module: 'wiki', success: true, limit: 10, skip: 0, activeOnly: true, windowMinutes: 15, status: 'active', conversationId: 'c1', username: 'u', intent: 'x', mode: 'x', q: 'x', bustCache: true })).resolves.toBeDefined();
  });
  test("getWikiTelemetryRetention", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(getWikiTelemetryRetention(TOKEN)).resolves.toBeDefined();
  });
  test("getWikiTelemetrySchedule", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(getWikiTelemetrySchedule(TOKEN)).resolves.toBeDefined();
  });
  test("getWikiTelemetrySeries", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(getWikiTelemetrySeries(TOKEN, { page: 1, pageSize: 20, periodStart: '2026-08-01', periodEnd: '2026-08-31', parentId: 'id-1', structureKind: 'organigramma', toolName: 'x', moduleKey: 'wiki', module: 'wiki', success: true, limit: 10, skip: 0, activeOnly: true, windowMinutes: 15, status: 'active', conversationId: 'c1', username: 'u', intent: 'x', mode: 'x', q: 'x', bustCache: true })).resolves.toBeDefined();
  });
  test("getWikiTelemetrySummary", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(getWikiTelemetrySummary(TOKEN, { page: 1, pageSize: 20, periodStart: '2026-08-01', periodEnd: '2026-08-31', parentId: 'id-1', structureKind: 'organigramma', toolName: 'x', moduleKey: 'wiki', module: 'wiki', success: true, limit: 10, skip: 0, activeOnly: true, windowMinutes: 15, status: 'active', conversationId: 'c1', username: 'u', intent: 'x', mode: 'x', q: 'x', bustCache: true })).resolves.toBeDefined();
  });
  test("getWikiToolAuditLogDetail", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(getWikiToolAuditLogDetail(TOKEN, "id-1")).resolves.toBeDefined();
  });
  test("getWikiToolAuditLogs", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(getWikiToolAuditLogs(TOKEN, { page: 1, pageSize: 20, periodStart: '2026-08-01', periodEnd: '2026-08-31', parentId: 'id-1', structureKind: 'organigramma', toolName: 'x', moduleKey: 'wiki', module: 'wiki', success: true, limit: 10, skip: 0, activeOnly: true, windowMinutes: 15, status: 'active', conversationId: 'c1', username: 'u', intent: 'x', mode: 'x', q: 'x', bustCache: true })).resolves.toBeDefined();
  });
  test("getWikiToolAuditRelatedLogs", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(getWikiToolAuditRelatedLogs(TOKEN, "id-1", { page: 1, pageSize: 20, periodStart: '2026-08-01', periodEnd: '2026-08-31', parentId: 'id-1', structureKind: 'organigramma', toolName: 'x', moduleKey: 'wiki', module: 'wiki', success: true, limit: 10, skip: 0, activeOnly: true, windowMinutes: 15, status: 'active', conversationId: 'c1', username: 'u', intent: 'x', mode: 'x', q: 'x', bustCache: true })).resolves.toBeDefined();
  });
  test("getWikiToolAuditSummary", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(getWikiToolAuditSummary(TOKEN, { page: 1, pageSize: 20, periodStart: '2026-08-01', periodEnd: '2026-08-31', parentId: 'id-1', structureKind: 'organigramma', toolName: 'x', moduleKey: 'wiki', module: 'wiki', success: true, limit: 10, skip: 0, activeOnly: true, windowMinutes: 15, status: 'active', conversationId: 'c1', username: 'u', intent: 'x', mode: 'x', q: 'x', bustCache: true })).resolves.toBeDefined();
  });
  test("listWikiConversationMetricsBackfillJobChains", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(listWikiConversationMetricsBackfillJobChains(TOKEN, {}, {})).resolves.toBeDefined();
  });
  test("updateWikiConversation", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(updateWikiConversation(TOKEN, "id-1", {})).resolves.toBeDefined();
  });
  test("updateWikiConversationGovernanceConfig", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(updateWikiConversationGovernanceConfig(TOKEN, {})).resolves.toBeDefined();
  });
  test("updateWikiRequest", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(updateWikiRequest(TOKEN, "id-1", {})).resolves.toBeDefined();
  });
  test("updateWikiRequestFeedback", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(updateWikiRequestFeedback(TOKEN, "id-1", {})).resolves.toBeDefined();
  });
});
