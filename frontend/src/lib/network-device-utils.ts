import type { NetworkDevice } from "@/types/api";

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
