import type { NetworkAlert, NetworkAlertUpdateInput, NetworkDashboardSummary, NetworkDetectionWatchlistRule, NetworkDetectionWatchlistRuleCreateInput, NetworkDetectionWatchlistRuleUpdateInput, NetworkAssignedUserSummary, NetworkDevice, NetworkDeviceBulkUpdateInput, NetworkDeviceBulkUpdateResponse, NetworkDeviceListResponse, NetworkStatisticsSummary, NetworkDeviceUpdateInput, NetworkFirewall, NetworkFirewallEvent, NetworkFirewallLogCoverageSummary, NetworkFirewallMetric, NetworkSophosConfig, NetworkSophosConfigUpdateInput, NetworkIpWhois, NetworkTrackedSubject, NetworkTrackedSubjectActivitySummary, NetworkTrackedSubjectCreateInput, NetworkTrackedSubjectUpdateInput, NetworkArpTimelineItem, NetworkVpnAccessDevice, NetworkVpnAccessDeviceListResponse, NetworkVpnAccessSessionListResponse, NetworkVpnDeviceStatus, NetworkVpnBypassSummary, DevicePositionUpdateInput, DevicePosition, NetworkFloorPlan, NetworkFloorPlanCreateInput, NetworkFloorPlanDevice, NetworkFloorPlanDetail, NetworkScan, NetworkScanDetail, NetworkScanDiff, NetworkScanTriggerInput, NetworkScanTriggerResponse } from "@/types/api";
import { request } from "./core";

export async function getNetworkDashboard(token: string): Promise<NetworkDashboardSummary> {
  return request<NetworkDashboardSummary>("/network/dashboard", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getNetworkStatistics(
  token: string,
  params: { windowHours?: number } = {},
): Promise<NetworkStatisticsSummary> {
  const query = new URLSearchParams();
  if (params.windowHours != null) {
    query.set("window_hours", String(params.windowHours));
  }
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return request<NetworkStatisticsSummary>(`/network/statistics${suffix}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getNetworkDevices(
  token: string,
  params?: {
    search?: string;
    status?: string;
    lifecycle?: string;
    assignment?: string;
    known?: string;
    vendor?: string;
    deviceType?: string;
    page?: number;
    pageSize?: number;
  },
): Promise<NetworkDeviceListResponse> {
  const query = new URLSearchParams();
  if (params?.search) {
    query.set("search", params.search);
  }
  if (params?.status) {
    query.set("status", params.status);
  }
  if (params?.lifecycle) {
    query.set("lifecycle", params.lifecycle);
  }
  if (params?.assignment) {
    query.set("assignment", params.assignment);
  }
  if (params?.known) {
    query.set("known", params.known);
  }
  if (params?.vendor) {
    query.set("vendor", params.vendor);
  }
  if (params?.deviceType) {
    query.set("device_type", params.deviceType);
  }
  if (params?.page) {
    query.set("page", String(params.page));
  }
  if (params?.pageSize) {
    query.set("page_size", String(params.pageSize));
  }

  const suffix = query.toString() ? `?${query.toString()}` : "";
  return request<NetworkDeviceListResponse>(`/network/devices${suffix}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getNetworkDevice(token: string, deviceId: number): Promise<NetworkDevice> {
  return request<NetworkDevice>(`/network/devices/${deviceId}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function listNetworkDeviceAssignees(token: string): Promise<NetworkAssignedUserSummary[]> {
  return request<NetworkAssignedUserSummary[]>("/network/device-assignees", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function listNetworkTrackedSubjects(
  token: string,
  params?: { includeInactive?: boolean; includeInferred?: boolean; windowHours?: number; search?: string; entityType?: string },
): Promise<NetworkTrackedSubject[]> {
  const query = new URLSearchParams();
  if (params?.includeInactive) {
    query.set("include_inactive", "true");
  }
  if (params?.includeInferred) {
    query.set("include_inferred", "true");
  }
  if (params?.windowHours != null) {
    query.set("window_hours", String(params.windowHours));
  }
  if (params?.search) {
    query.set("search", params.search);
  }
  if (params?.entityType) {
    query.set("entity_type", params.entityType);
  }
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return request<NetworkTrackedSubject[]>(`/network/tracking${suffix}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function createNetworkTrackedSubject(
  token: string,
  payload: NetworkTrackedSubjectCreateInput,
): Promise<NetworkTrackedSubject> {
  return request<NetworkTrackedSubject>("/network/tracking", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function updateNetworkTrackedSubject(
  token: string,
  subjectId: number,
  payload: NetworkTrackedSubjectUpdateInput,
): Promise<NetworkTrackedSubject> {
  return request<NetworkTrackedSubject>(`/network/tracking/${subjectId}`, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function getNetworkIpWhois(token: string, ipAddress: string): Promise<NetworkIpWhois> {
  return request<NetworkIpWhois>(`/network/ip-whois/${encodeURIComponent(ipAddress)}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getNetworkTrackedSubjectActivities(
  token: string,
  subjectId: number,
  params?: { windowHours?: number; limit?: number },
): Promise<NetworkTrackedSubjectActivitySummary> {
  const query = new URLSearchParams();
  if (params?.windowHours != null) {
    query.set("window_hours", String(params.windowHours));
  }
  if (params?.limit != null) {
    query.set("limit", String(params.limit));
  }
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return request<NetworkTrackedSubjectActivitySummary>(`/network/tracking/${subjectId}/activities${suffix}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getNetworkDetectionWatchlist(token: string): Promise<NetworkDetectionWatchlistRule[]> {
  return request<NetworkDetectionWatchlistRule[]>("/network/detection-watchlist", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function createNetworkDetectionWatchlistRule(
  token: string,
  payload: NetworkDetectionWatchlistRuleCreateInput,
): Promise<NetworkDetectionWatchlistRule> {
  return request<NetworkDetectionWatchlistRule>("/network/detection-watchlist", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function updateNetworkDetectionWatchlistRule(
  token: string,
  ruleId: number,
  payload: NetworkDetectionWatchlistRuleUpdateInput,
): Promise<NetworkDetectionWatchlistRule> {
  return request<NetworkDetectionWatchlistRule>(`/network/detection-watchlist/${ruleId}`, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function getNetworkVpnBypassSummary(
  token: string,
  params?: { windowHours?: number },
): Promise<NetworkVpnBypassSummary> {
  const query = new URLSearchParams();
  if (params?.windowHours != null) {
    query.set("window_hours", String(params.windowHours));
  }
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return request<NetworkVpnBypassSummary>(`/network/vpn-bypass/summary${suffix}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getNetworkVpnBypassArpTimeline(
  token: string,
  params?: { windowHours?: number; limit?: number },
): Promise<NetworkArpTimelineItem[]> {
  const query = new URLSearchParams();
  if (params?.windowHours != null) {
    query.set("window_hours", String(params.windowHours));
  }
  if (params?.limit != null) {
    query.set("limit", String(params.limit));
  }
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return request<NetworkArpTimelineItem[]>(`/network/vpn-bypass/arp-timeline${suffix}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function listNetworkVpnAccessDevices(
  token: string,
  params?: { userId?: number; status?: NetworkVpnDeviceStatus | ""; skip?: number; limit?: number },
): Promise<NetworkVpnAccessDeviceListResponse> {
  const query = new URLSearchParams();
  if (params?.userId != null) {
    query.set("user_id", String(params.userId));
  }
  if (params?.status) {
    query.set("status", params.status);
  }
  if (params?.skip != null) {
    query.set("skip", String(params.skip));
  }
  if (params?.limit != null) {
    query.set("limit", String(params.limit));
  }
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return request<NetworkVpnAccessDeviceListResponse>(`/network/vpn-access/devices${suffix}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function listNetworkVpnAccessSessions(
  token: string,
  params?: { userId?: number; eventType?: string; skip?: number; limit?: number },
): Promise<NetworkVpnAccessSessionListResponse> {
  const query = new URLSearchParams();
  if (params?.userId != null) {
    query.set("user_id", String(params.userId));
  }
  if (params?.eventType) {
    query.set("event_type", params.eventType);
  }
  if (params?.skip != null) {
    query.set("skip", String(params.skip));
  }
  if (params?.limit != null) {
    query.set("limit", String(params.limit));
  }
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return request<NetworkVpnAccessSessionListResponse>(`/network/vpn-access/sessions${suffix}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function updateNetworkVpnAccessDeviceStatus(
  token: string,
  deviceId: number,
  status: NetworkVpnDeviceStatus,
): Promise<NetworkVpnAccessDevice> {
  return request<NetworkVpnAccessDevice>(`/network/vpn-access/devices/${deviceId}`, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ status }),
  });
}

export async function updateNetworkDevice(
  token: string,
  deviceId: number,
  payload: NetworkDeviceUpdateInput,
): Promise<NetworkDevice> {
  return request<NetworkDevice>(`/network/devices/${deviceId}`, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function bulkUpdateNetworkDevices(
  token: string,
  payload: NetworkDeviceBulkUpdateInput,
): Promise<NetworkDeviceBulkUpdateResponse> {
  return request<NetworkDeviceBulkUpdateResponse>("/network/devices/bulk-update", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function getNetworkAlerts(token: string): Promise<NetworkAlert[]> {
  return request<NetworkAlert[]>("/network/alerts", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getNetworkFirewalls(token: string): Promise<NetworkFirewall[]> {
  return request<NetworkFirewall[]>("/network/firewalls", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getNetworkSophosConfig(token: string): Promise<NetworkSophosConfig> {
  return request<NetworkSophosConfig>("/network/sophos-config", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function updateNetworkSophosConfig(
  token: string,
  payload: NetworkSophosConfigUpdateInput,
): Promise<NetworkSophosConfig> {
  return request<NetworkSophosConfig>("/network/sophos-config", {
    method: "PUT",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function getNetworkFirewallEvents(
  token: string,
  firewallId: number,
  params?: { severity?: string; limit?: number },
): Promise<NetworkFirewallEvent[]> {
  const query = new URLSearchParams();
  if (params?.severity) {
    query.set("severity", params.severity);
  }
  if (params?.limit) {
    query.set("limit", String(params.limit));
  }
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return request<NetworkFirewallEvent[]>(`/network/firewalls/${firewallId}/events${suffix}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getNetworkFirewallLogCoverage(
  token: string,
  firewallId: number,
  params: { windowHours?: number } = {},
): Promise<NetworkFirewallLogCoverageSummary> {
  const query = new URLSearchParams();
  if (params.windowHours) {
    query.set("window_hours", String(params.windowHours));
  }
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return request<NetworkFirewallLogCoverageSummary>(`/network/firewalls/${firewallId}/log-coverage${suffix}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getNetworkFirewallMetrics(
  token: string,
  firewallId: number,
  params?: { metricKey?: string; limit?: number },
): Promise<NetworkFirewallMetric[]> {
  const query = new URLSearchParams();
  if (params?.metricKey) {
    query.set("metric_key", params.metricKey);
  }
  if (params?.limit) {
    query.set("limit", String(params.limit));
  }
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return request<NetworkFirewallMetric[]>(`/network/firewalls/${firewallId}/metrics${suffix}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function pollNetworkFirewallMetrics(token: string, firewallId: number): Promise<NetworkFirewallMetric[]> {
  return request<NetworkFirewallMetric[]>(`/network/firewalls/${firewallId}/metrics/poll`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function updateNetworkAlert(
  token: string,
  alertId: number,
  payload: NetworkAlertUpdateInput,
): Promise<NetworkAlert> {
  return request<NetworkAlert>(`/network/alerts/${alertId}`, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function getNetworkScans(token: string): Promise<NetworkScan[]> {
  return request<NetworkScan[]>("/network/scans", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getNetworkScan(token: string, scanId: number): Promise<NetworkScanDetail> {
  return request<NetworkScanDetail>(`/network/scans/${scanId}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getNetworkScanDiff(token: string, scanId: number, otherScanId: number): Promise<NetworkScanDiff> {
  return request<NetworkScanDiff>(`/network/scans/${scanId}/diff/${otherScanId}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function triggerNetworkScan(
  token: string,
  payload?: NetworkScanTriggerInput,
): Promise<NetworkScanTriggerResponse> {
  return request<NetworkScanTriggerResponse>("/network/scans", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: payload ? JSON.stringify(payload) : undefined,
  });
}

export async function getNetworkFloorPlans(token: string): Promise<NetworkFloorPlan[]> {
  return request<NetworkFloorPlan[]>("/network/floor-plans", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function createNetworkFloorPlan(
  token: string,
  payload: NetworkFloorPlanCreateInput,
): Promise<NetworkFloorPlan> {
  return request<NetworkFloorPlan>("/network/floor-plans", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}

export async function getNetworkFloorPlan(token: string, floorPlanId: number): Promise<NetworkFloorPlanDetail> {
  return request<NetworkFloorPlanDetail>(`/network/floor-plans/${floorPlanId}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getNetworkFloorPlanDevices(
  token: string,
  floorPlanId: number,
): Promise<NetworkFloorPlanDevice[]> {
  return request<NetworkFloorPlanDevice[]>(`/network/floor-plans/${floorPlanId}/devices`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function updateNetworkDevicePosition(
  token: string,
  deviceId: number,
  payload: DevicePositionUpdateInput,
): Promise<DevicePosition> {
  return request<DevicePosition>(`/network/devices/${deviceId}/position`, {
    method: "PUT",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });
}
