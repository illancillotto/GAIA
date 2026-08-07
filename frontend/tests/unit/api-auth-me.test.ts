import { afterEach, describe, expect, test, vi } from "vitest";

import {
  getAuthProviders,
  getCurrentUser,
  getMeOperazioniSummary,
  getMePresenzeSummary,
  getMePresenzeStatus,
  getMeStatus,
  getMeSummary,
  getPresenceSummary,
  listMeAssignedDevices,
  login,
  sendPresenceHeartbeat,
} from "@/lib/api";

function jsonResponse(payload: unknown, status = 200): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "content-type": "application/json" },
  });
}

describe("api auth and /me clients", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  test("login and auth providers", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ access_token: "token", token_type: "bearer" }))
      .mockResolvedValueOnce(jsonResponse({ providers: [{ id: "google", label: "Google" }] }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(login("admin", "secret")).resolves.toEqual({
      access_token: "token",
      token_type: "bearer",
    });
    await expect(getAuthProviders()).resolves.toEqual({
      providers: [{ id: "google", label: "Google" }],
    });

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "/api/auth/login",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ username: "admin", password: "secret" }),
      }),
    );
  });

  test("current user and presence endpoints", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ id: 1, username: "admin", role: "admin" }))
      .mockResolvedValueOnce(jsonResponse({ ok: true, last_seen_at: "2026-08-07T08:00:00Z" }))
      .mockResolvedValueOnce(jsonResponse({ total: 2, online: 1, items: [] }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(getCurrentUser("token", { timeoutMs: 5000 })).resolves.toEqual({
      id: 1,
      username: "admin",
      role: "admin",
    });
    await expect(
      sendPresenceHeartbeat("token", {
        path: "/me",
        route_label: "La mia attivita",
        module_key: "me",
        action_label: null,
        visible: true,
      }),
    ).resolves.toEqual({ ok: true, last_seen_at: "2026-08-07T08:00:00Z" });
    await expect(getPresenceSummary("token", { windowMinutes: 15 })).resolves.toEqual({
      total: 2,
      online: 1,
      items: [],
    });
  });

  test("/me module summaries and lists", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ presenze: { enabled: true } }))
      .mockResolvedValueOnce(jsonResponse({ period_start: "2026-08-01", period_end: "2026-08-31", records: [] }))
      .mockResolvedValueOnce(jsonResponse({ period_start: "2026-08-01", period_end: "2026-08-31", totals: {} }))
      .mockResolvedValueOnce(jsonResponse({ period_start: "2026-08-01", period_end: "2026-08-31", widgets: [] }))
      .mockResolvedValueOnce(jsonResponse({ period_start: "2026-08-01", period_end: "2026-08-31", totals: {} }))
      .mockResolvedValueOnce(jsonResponse({ items: [{ id: "device-1" }] }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(getMeStatus("token")).resolves.toEqual({ presenze: { enabled: true } });
    await expect(getMePresenzeStatus("token")).resolves.toEqual({
      period_start: "2026-08-01",
      period_end: "2026-08-31",
      records: [],
    });
    await expect(getMePresenzeSummary("token", "2026-08-01", "2026-08-31")).resolves.toEqual({
      period_start: "2026-08-01",
      period_end: "2026-08-31",
      totals: {},
    });
    await expect(
      getMeSummary("token", { periodStart: "2026-08-01", periodEnd: "2026-08-31" }),
    ).resolves.toEqual({
      period_start: "2026-08-01",
      period_end: "2026-08-31",
      widgets: [],
    });
    await expect(
      getMeOperazioniSummary("token", { periodStart: "2026-08-01", periodEnd: "2026-08-31" }),
    ).resolves.toEqual({
      period_start: "2026-08-01",
      period_end: "2026-08-31",
      totals: {},
    });
    await expect(listMeAssignedDevices("token")).resolves.toEqual({ items: [{ id: "device-1" }] });
  });
});
