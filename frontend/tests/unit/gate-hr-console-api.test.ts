import { afterEach, describe, expect, it, vi } from "vitest";
import { updateGateMobileConsolePermissions } from "@/features/operazioni/api/client";

vi.mock("@/lib/api", () => ({ getApiBaseUrl: () => "/synthetic-api" }));
const auth = vi.hoisted(() => ({ token: "synthetic-token" as string | null }));
vi.mock("@/lib/auth", () => ({ getStoredAccessToken: () => auth.token }));
afterEach(() => { vi.unstubAllGlobals(); auth.token = "synthetic-token"; });

describe("HR permissions through the real Operazioni HTTP client", () => {
  it("sends the explicit HR role and authenticated PATCH to the canonical endpoint", async () => {
    const result = { id: "synthetic-operator", gate_mobile_console_enabled: true, gate_mobile_console_role: "hr_manager" };
    const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify(result), { status: 200 }));
    vi.stubGlobal("fetch", fetch);
    expect(await updateGateMobileConsolePermissions("synthetic-operator", { enabled: true, role: "hr_manager" })).toEqual(result);
    expect(fetch).toHaveBeenCalledWith("/synthetic-api/operazioni/operators/synthetic-operator/gate-mobile-console", expect.objectContaining({
      method: "PATCH", cache: "no-store", headers: { Authorization: "Bearer synthetic-token", "Content-Type": "application/json" },
      body: JSON.stringify({ enabled: true, role: "hr_manager" }),
    }));
  });

  it("preserves a server authorization refusal instead of reporting a successful save", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: "Admin role required" }), { status: 403 })));
    await expect(updateGateMobileConsolePermissions("synthetic-operator", { enabled: true, role: "hr_manager" })).rejects.toThrow("Admin role required");
  });

  it.each([
    { payload: { detail: [{ msg: "Unknown role" }, "Invalid permission", null] }, message: 'Unknown role, "Invalid permission", null' },
    { payload: { error: { message: "Permission update rejected" } }, message: "Permission update rejected" },
    { payload: { detail: 42, error: null }, message: "Request failed" },
    { payload: { error: {} }, message: "Request failed" },
    { payload: null, message: "Request failed" },
    { payload: "Unavailable", message: "Request failed" },
  ])("propagates permission error $message without a false successful save", async ({ payload, message }) => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify(payload), { status: 422 })));
    await expect(updateGateMobileConsolePermissions("synthetic-operator", { enabled: true, role: "hr_manager" })).rejects.toThrow(message);
  });

  it("reports an upstream non-JSON error using its HTTP status text", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("gateway temporarily unavailable", { status: 503, statusText: "Service Unavailable" })));
    await expect(updateGateMobileConsolePermissions("synthetic-operator", { enabled: true, role: "hr_manager" })).rejects.toThrow("Service Unavailable");
  });

  it("does not manufacture a bearer token after the session has expired", async () => {
    auth.token = null;
    const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: "Session expired" }), { status: 401 }));
    vi.stubGlobal("fetch", fetch);
    await expect(updateGateMobileConsolePermissions("synthetic-operator", { enabled: true, role: "hr_manager" })).rejects.toThrow("Session expired");
    expect(fetch).toHaveBeenCalledWith("/synthetic-api/operazioni/operators/synthetic-operator/gate-mobile-console", expect.objectContaining({
      headers: { "Content-Type": "application/json" }, cache: "no-store",
    }));
  });

  it("keeps a network failure visible to the permissions dialog", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Network unavailable")));
    await expect(updateGateMobileConsolePermissions("synthetic-operator", { enabled: true, role: "hr_manager" })).rejects.toThrow("Network unavailable");
  });
});
