import { describe, expect, test } from "vitest";

import {
  buildDeviceTrackingKey,
  buildNetworkTrackingKey,
  formatIpWithReference,
  getDeviceReferenceLabel,
  getNetworkDeviceAdminUrl,
  isPrivateNetworkIp,
  normalizeNetworkTrackingValue,
} from "@/lib/network-device-utils";

describe("getNetworkDeviceAdminUrl", () => {
  test("prefers absolute http refresh targets", () => {
    expect(
      getNetworkDeviceAdminUrl({
        ip_address: "10.0.0.5",
        metadata_sources: { http_refresh_target: "https://admin.example.local/path" },
        open_ports: null,
      }),
    ).toBe("https://admin.example.local/path");
  });

  test("builds refresh target from relative path and http source scheme", () => {
    expect(
      getNetworkDeviceAdminUrl({
        ip_address: "10.0.0.5",
        metadata_sources: { http_refresh_target: "/admin", http: "https:443" },
        open_ports: null,
      }),
    ).toBe("https://10.0.0.5/admin");

    expect(
      getNetworkDeviceAdminUrl({
        ip_address: "10.0.0.5",
        metadata_sources: { http_refresh_target: "/admin" },
        open_ports: null,
      }),
    ).toBe("http://10.0.0.5/admin");

    expect(
      getNetworkDeviceAdminUrl({
        ip_address: "10.0.0.5",
        metadata_sources: { http_refresh_target: "admin-panel" },
        open_ports: "80",
      }),
    ).toBe("http://10.0.0.5/");
  });

  test("ignores malformed http metadata sources", () => {
    expect(
      getNetworkDeviceAdminUrl({
        ip_address: "10.0.0.5",
        metadata_sources: { http: "ftp:21" },
        open_ports: null,
      }),
    ).toBeNull();
  });

  test("falls back to metadata http source or open ports", () => {
    expect(
      getNetworkDeviceAdminUrl({
        ip_address: "10.0.0.5",
        metadata_sources: { http: "https:8443" },
        open_ports: null,
      }),
    ).toBe("https://10.0.0.5:8443/");

    expect(
      getNetworkDeviceAdminUrl({
        ip_address: "10.0.0.5",
        metadata_sources: {},
        open_ports: "22,443,8080",
      }),
    ).toBe("https://10.0.0.5/");

    expect(
      getNetworkDeviceAdminUrl({
        ip_address: "10.0.0.5",
        metadata_sources: {},
        open_ports: "22,80",
      }),
    ).toBe("http://10.0.0.5/");

    expect(
      getNetworkDeviceAdminUrl({
        ip_address: "10.0.0.5",
        metadata_sources: {},
        open_ports: null,
      }),
    ).toBeNull();
  });
});

describe("device reference helpers", () => {
  test("prefers assigned user labels", () => {
    expect(
      getDeviceReferenceLabel({
        ip_address: "10.0.0.5",
        resolved_label: "Printer",
        display_name: "HP",
        hostname: "hp.local",
        assigned_user: { full_name: "Mario Rossi", username: "mrossi" },
      }),
    ).toBe("Mario Rossi");

    expect(
      getDeviceReferenceLabel({
        ip_address: "10.0.0.5",
        resolved_label: null,
        display_name: null,
        hostname: null,
        assigned_user: { full_name: null, username: "mrossi" },
      }),
    ).toBe("mrossi");

    expect(
      getDeviceReferenceLabel({
        ip_address: "10.0.0.5",
        resolved_label: "Printer",
        display_name: "HP",
        hostname: "hp.local",
        assigned_user_label: "Scan station",
      }),
    ).toBe("Scan station");
  });

  test("formats IP with reference when different from address", () => {
    expect(
      formatIpWithReference({
        ip_address: "10.0.0.5",
        resolved_label: "Printer",
        display_name: null,
        hostname: null,
        assigned_user: null,
      }),
    ).toBe("10.0.0.5 · Printer");

    expect(
      formatIpWithReference({
        ip_address: "10.0.0.5",
        resolved_label: "10.0.0.5",
        display_name: null,
        hostname: null,
        assigned_user: null,
      }),
    ).toBe("10.0.0.5");
  });

  test("falls back through label fields when no assignee is present", () => {
    expect(
      getDeviceReferenceLabel({
        ip_address: "10.0.0.5",
        resolved_label: null,
        display_name: "Switch",
        hostname: "sw.local",
        assigned_user: null,
      }),
    ).toBe("Switch");

    expect(
      getDeviceReferenceLabel({
        ip_address: "10.0.0.5",
        resolved_label: null,
        display_name: null,
        hostname: "sw.local",
        assigned_user: null,
      }),
    ).toBe("sw.local");

    expect(
      getDeviceReferenceLabel({
        ip_address: "10.0.0.5",
        resolved_label: null,
        display_name: null,
        hostname: null,
        assigned_user: null,
      }),
    ).toBeNull();
  });
});

describe("network tracking helpers", () => {
  test("detects private network ranges", () => {
    expect(isPrivateNetworkIp("10.1.2.3")).toBe(true);
    expect(isPrivateNetworkIp("192.168.0.10")).toBe(true);
    expect(isPrivateNetworkIp("172.16.0.1")).toBe(true);
    expect(isPrivateNetworkIp("172.31.255.1")).toBe(true);
    expect(isPrivateNetworkIp("8.8.8.8")).toBe(false);
    expect(isPrivateNetworkIp(null)).toBe(false);
  });

  test("normalizes tracking values by entity type", () => {
    expect(normalizeNetworkTrackingValue("domain", "Example.COM.")).toBe("example.com");
    expect(normalizeNetworkTrackingValue("domain", "https://Example.COM/path")).toBe("example.com");
    expect(normalizeNetworkTrackingValue("domain", "://bad")).toBe("://bad");
    expect(normalizeNetworkTrackingValue("url", " https://example.com ")).toBe("https://example.com");
    expect(normalizeNetworkTrackingValue("ip", " 10.0.0.5 ")).toBe("10.0.0.5");
  });

  test("builds tracking keys", () => {
    expect(buildNetworkTrackingKey("domain", "Example.COM.")).toBe("domain:example.com");
    expect(buildDeviceTrackingKey(42)).toBe("device:42");
  });
});
