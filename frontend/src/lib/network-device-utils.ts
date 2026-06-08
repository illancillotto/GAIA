import type { NetworkDevice, NetworkScanDevice } from "@/types/api";

export type NetworkTrackingEntityType = "device" | "ip" | "domain" | "url";

function hasPort(openPorts: string | null, port: number): boolean {
  if (!openPorts) {
    return false;
  }
  return openPorts
    .split(",")
    .map((value) => Number(value.trim()))
    .includes(port);
}

export function getNetworkDeviceAdminUrl(device: Pick<NetworkDevice, "ip_address" | "metadata_sources" | "open_ports">): string | null {
  const refreshTarget = device.metadata_sources?.http_refresh_target;
  if (refreshTarget) {
    if (refreshTarget.startsWith("http://") || refreshTarget.startsWith("https://")) {
      return refreshTarget;
    }
    if (refreshTarget.startsWith("/")) {
      if (device.metadata_sources?.http?.startsWith("https:")) {
        return `https://${device.ip_address}${refreshTarget}`;
      }
      return `http://${device.ip_address}${refreshTarget}`;
    }
  }

  const httpSource = device.metadata_sources?.http;
  if (httpSource) {
    const [scheme, port] = httpSource.split(":");
    if ((scheme === "http" || scheme === "https") && port) {
      return `${scheme}://${device.ip_address}:${port}/`;
    }
  }

  if (hasPort(device.open_ports, 443)) {
    return `https://${device.ip_address}/`;
  }
  if (hasPort(device.open_ports, 80)) {
    return `http://${device.ip_address}/`;
  }

  return null;
}

type DeviceLike = Pick<NetworkDevice, "ip_address" | "resolved_label" | "display_name" | "hostname" | "assigned_user">;
type ScanDeviceLike = Pick<NetworkScanDevice, "ip_address" | "resolved_label" | "display_name" | "hostname" | "assigned_user_label">;

export function getDeviceReferenceLabel(device: DeviceLike | ScanDeviceLike): string | null {
  if ("assigned_user" in device && device.assigned_user) {
    return device.assigned_user.full_name || device.assigned_user.username;
  }
  if ("assigned_user_label" in device && device.assigned_user_label) {
    return device.assigned_user_label;
  }
  return device.resolved_label || device.display_name || device.hostname || null;
}

export function formatIpWithReference(device: DeviceLike | ScanDeviceLike): string {
  const reference = getDeviceReferenceLabel(device);
  if (reference && reference !== device.ip_address) {
    return `${device.ip_address} · ${reference}`;
  }
  return device.ip_address;
}

export function isPrivateNetworkIp(value: string | null | undefined): boolean {
  if (!value) {
    return false;
  }
  return value.startsWith("10.") || value.startsWith("192.168.") || /^172\.(1[6-9]|2\d|3[0-1])\./.test(value);
}

export function normalizeNetworkTrackingValue(entityType: NetworkTrackingEntityType, value: string): string {
  const normalized = value.trim();
  if (entityType === "domain") {
    try {
      const parsed = normalized.includes("://") ? new URL(normalized) : null;
      return (parsed?.hostname || normalized).trim().replace(/\.$/, "").toLowerCase();
    } catch {
      return normalized.replace(/\.$/, "").toLowerCase();
    }
  }
  if (entityType === "url") {
    return normalized;
  }
  return normalized;
}

export function buildNetworkTrackingKey(entityType: NetworkTrackingEntityType, value: string): string {
  return `${entityType}:${normalizeNetworkTrackingValue(entityType, value)}`;
}

export function buildDeviceTrackingKey(deviceId: number): string {
  return `device:${deviceId}`;
}
