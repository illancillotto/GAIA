import { afterEach, describe, expect, test, vi } from "vitest";

import {
  bulkUpdateNetworkDevices,
  createNetworkDetectionWatchlistRule,
  createNetworkFloorPlan,
  createNetworkTrackedSubject,
  getNetworkAlerts,
  getNetworkDashboard,
  getNetworkDetectionWatchlist,
  getNetworkDevice,
  getNetworkDevices,
  getNetworkFirewallEvents,
  getNetworkFirewallLogCoverage,
  getNetworkFirewallMetrics,
  getNetworkFirewalls,
  getNetworkFloorPlan,
  getNetworkFloorPlanDevices,
  getNetworkFloorPlans,
  getNetworkIpWhois,
  getNetworkScan,
  getNetworkScanDiff,
  getNetworkScans,
  getNetworkSophosConfig,
  getNetworkStatistics,
  getNetworkTrackedSubjectActivities,
  getNetworkVpnBypassArpTimeline,
  getNetworkVpnBypassSummary,
  listNetworkVpnAccessDevices,
  listNetworkVpnAccessSessions,
  listNetworkDeviceAssignees,
  listNetworkTrackedSubjects,
  triggerNetworkScan,
  updateNetworkAlert,
  updateNetworkDetectionWatchlistRule,
  updateNetworkDevice,
  updateNetworkDevicePosition,
  updateNetworkVpnAccessDeviceStatus,
  updateNetworkSophosConfig,
  updateNetworkTrackedSubject,
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

describe("api network clients", () => {

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  test("bulkUpdateNetworkDevices", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(bulkUpdateNetworkDevices(TOKEN, {})).resolves.toBeDefined();
  });
  test("createNetworkDetectionWatchlistRule", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(createNetworkDetectionWatchlistRule(TOKEN, {})).resolves.toBeDefined();
  });
  test("createNetworkFloorPlan", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(createNetworkFloorPlan(TOKEN, {})).resolves.toBeDefined();
  });
  test("createNetworkTrackedSubject", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(createNetworkTrackedSubject(TOKEN, {})).resolves.toBeDefined();
  });
  test("getNetworkAlerts", async () => {
    stubFetch(jsonResponse([]));
    await expect(getNetworkAlerts(TOKEN)).resolves.toBeDefined();
  });
  test("getNetworkDashboard", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(getNetworkDashboard(TOKEN)).resolves.toBeDefined();
  });
  test("getNetworkDetectionWatchlist", async () => {
    stubFetch(jsonResponse([]));
    await expect(getNetworkDetectionWatchlist(TOKEN)).resolves.toBeDefined();
  });
  test("getNetworkDevice", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(getNetworkDevice(TOKEN, 1)).resolves.toBeDefined();
  });
  test("getNetworkDevices", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(getNetworkDevices(TOKEN, 1)).resolves.toBeDefined();
  });
  test("getNetworkFirewallEvents", async () => {
    stubFetch(jsonResponse([]));
    await expect(getNetworkFirewallEvents(TOKEN, 1, 1)).resolves.toBeDefined();
  });
  test("getNetworkFirewallLogCoverage", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(getNetworkFirewallLogCoverage(TOKEN, 1, { page: 1, pageSize: 20, periodStart: '2026-08-01', periodEnd: '2026-08-31', parentId: 'id-1', structureKind: 'organigramma', toolName: 'x', moduleKey: 'wiki', module: 'wiki', success: true, limit: 10, skip: 0, activeOnly: true, windowMinutes: 15, status: 'active', conversationId: 'c1', username: 'u', intent: 'x', mode: 'x', q: 'x', bustCache: true })).resolves.toBeDefined();
  });
  test("getNetworkFirewallMetrics", async () => {
    stubFetch(jsonResponse([]));
    await expect(getNetworkFirewallMetrics(TOKEN, 1, 1)).resolves.toBeDefined();
  });
  test("getNetworkFirewalls", async () => {
    stubFetch(jsonResponse([]));
    await expect(getNetworkFirewalls(TOKEN)).resolves.toBeDefined();
  });
  test("getNetworkFloorPlan", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(getNetworkFloorPlan(TOKEN, 1)).resolves.toBeDefined();
  });
  test("getNetworkFloorPlanDevices", async () => {
    stubFetch(jsonResponse([]));
    await expect(getNetworkFloorPlanDevices(TOKEN, 1)).resolves.toBeDefined();
  });
  test("getNetworkFloorPlans", async () => {
    stubFetch(jsonResponse([]));
    await expect(getNetworkFloorPlans(TOKEN)).resolves.toBeDefined();
  });
  test("getNetworkIpWhois", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(getNetworkIpWhois(TOKEN, "value")).resolves.toBeDefined();
  });
  test("getNetworkScan", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(getNetworkScan(TOKEN, 1)).resolves.toBeDefined();
  });
  test("getNetworkScanDiff", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(getNetworkScanDiff(TOKEN, 1, 1)).resolves.toBeDefined();
  });
  test("getNetworkScans", async () => {
    stubFetch(jsonResponse([]));
    await expect(getNetworkScans(TOKEN)).resolves.toBeDefined();
  });
  test("getNetworkSophosConfig", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(getNetworkSophosConfig(TOKEN)).resolves.toBeDefined();
  });
  test("getNetworkStatistics", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(getNetworkStatistics(TOKEN, { page: 1, pageSize: 20, periodStart: '2026-08-01', periodEnd: '2026-08-31', parentId: 'id-1', structureKind: 'organigramma', toolName: 'x', moduleKey: 'wiki', module: 'wiki', success: true, limit: 10, skip: 0, activeOnly: true, windowMinutes: 15, status: 'active', conversationId: 'c1', username: 'u', intent: 'x', mode: 'x', q: 'x', bustCache: true })).resolves.toBeDefined();
  });
  test("getNetworkTrackedSubjectActivities", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(getNetworkTrackedSubjectActivities(TOKEN, 1, 1)).resolves.toBeDefined();
  });
  test("getNetworkVpnBypassArpTimeline", async () => {
    stubFetch(jsonResponse([]));
    await expect(getNetworkVpnBypassArpTimeline(TOKEN, 1)).resolves.toBeDefined();
  });
  test("getNetworkVpnBypassSummary", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(getNetworkVpnBypassSummary(TOKEN, 1)).resolves.toBeDefined();
  });
  test("network VPN access clients", async () => {
    const fetchMock = stubFetch(
      jsonResponse({ items: [], total: 0, skip: 0, limit: 100 }),
      jsonResponse({ items: [], total: 0, skip: 0, limit: 100 }),
      jsonResponse({ id: 7, status: "revoked" }),
    );

    await expect(listNetworkVpnAccessDevices(TOKEN, { userId: 3, status: "active", limit: 25 })).resolves.toBeDefined();
    await expect(listNetworkVpnAccessSessions(TOKEN, { userId: 3, eventType: "login_blocked", limit: 25 })).resolves.toBeDefined();
    await expect(updateNetworkVpnAccessDeviceStatus(TOKEN, 7, "revoked")).resolves.toBeDefined();

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "/api/network/vpn-access/devices?user_id=3&status=active&limit=25",
      expect.objectContaining({ headers: expect.objectContaining({ Authorization: `Bearer ${TOKEN}` }) }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      "/api/network/vpn-access/sessions?user_id=3&event_type=login_blocked&limit=25",
      expect.objectContaining({ headers: expect.objectContaining({ Authorization: `Bearer ${TOKEN}` }) }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      3,
      "/api/network/vpn-access/devices/7",
      expect.objectContaining({
        method: "PATCH",
        body: JSON.stringify({ status: "revoked" }),
      }),
    );
  });
  test("listNetworkDeviceAssignees", async () => {
    stubFetch(jsonResponse([]));
    await expect(listNetworkDeviceAssignees(TOKEN)).resolves.toBeDefined();
  });
  test("listNetworkTrackedSubjects", async () => {
    stubFetch(jsonResponse([]));
    await expect(listNetworkTrackedSubjects(TOKEN, false)).resolves.toBeDefined();
  });
  test("triggerNetworkScan", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(triggerNetworkScan(TOKEN, {})).resolves.toBeDefined();
  });
  test("updateNetworkAlert", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(updateNetworkAlert(TOKEN, 1, {})).resolves.toBeDefined();
  });
  test("updateNetworkDetectionWatchlistRule", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(updateNetworkDetectionWatchlistRule(TOKEN, 1, {})).resolves.toBeDefined();
  });
  test("updateNetworkDevice", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(updateNetworkDevice(TOKEN, 1, {})).resolves.toBeDefined();
  });
  test("updateNetworkDevicePosition", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(updateNetworkDevicePosition(TOKEN, 1, {})).resolves.toBeDefined();
  });
  test("updateNetworkSophosConfig", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(updateNetworkSophosConfig(TOKEN, {})).resolves.toBeDefined();
  });
  test("updateNetworkTrackedSubject", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(updateNetworkTrackedSubject(TOKEN, 1, {})).resolves.toBeDefined();
  });
});
