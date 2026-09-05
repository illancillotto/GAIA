import { afterEach, describe, expect, test, vi } from "vitest";

import {
  createApplicationUser,
  deleteApplicationUser,
  deleteApplicationUserPermissionOverride,
  getApplicationUserPermissions,
  getDashboardSummary,
  getEffectivePermissions,
  getMyPermissions,
  getNasGroups,
  getNasUsers,
  getNasUsersForUsersSection,
  getReviews,
  getShares,
  listAllApplicationUsers,
  listApplicationUsers,
  listSectionCatalog,
  updateApplicationUser,
  updateApplicationUserPermissions,
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

describe("api platform clients", () => {

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  test("createApplicationUser", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(createApplicationUser(TOKEN, {})).resolves.toBeDefined();
  });
  test("deleteApplicationUser", async () => {
    stubFetch(emptyOkResponse());
    await expect(deleteApplicationUser(TOKEN, 1)).resolves.toBeUndefined();
  });
  test("deleteApplicationUserPermissionOverride", async () => {
    stubFetch(emptyOkResponse());
    await expect(deleteApplicationUserPermissionOverride(TOKEN, 1, 1)).resolves.toBeUndefined();
  });
  test("getApplicationUserPermissions", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(getApplicationUserPermissions(TOKEN, 1)).resolves.toBeDefined();
  });
  test("getDashboardSummary", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(getDashboardSummary(TOKEN, 1)).resolves.toBeDefined();
  });
  test("getEffectivePermissions", async () => {
    stubFetch(jsonResponse([]));
    await expect(getEffectivePermissions(TOKEN)).resolves.toBeDefined();
  });
  test("getMyPermissions", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(getMyPermissions(TOKEN, 1)).resolves.toBeDefined();
  });
  test("getNasGroups", async () => {
    stubFetch(jsonResponse([]));
    await expect(getNasGroups(TOKEN)).resolves.toBeDefined();
  });
  test("getNasUsers", async () => {
    stubFetch(jsonResponse([]));
    await expect(getNasUsers(TOKEN)).resolves.toBeDefined();
  });
  test("getNasUsersForUsersSection", async () => {
    stubFetch(jsonResponse([]));
    await expect(getNasUsersForUsersSection(TOKEN)).resolves.toBeDefined();
  });
  test("getReviews", async () => {
    stubFetch(jsonResponse([]));
    await expect(getReviews(TOKEN)).resolves.toBeDefined();
  });
  test("getShares", async () => {
    stubFetch(jsonResponse([]));
    await expect(getShares(TOKEN)).resolves.toBeDefined();
  });
  test("listAllApplicationUsers", async () => {
    stubFetch(jsonResponse({ items: [], total: 0 }));
    await expect(listAllApplicationUsers(TOKEN)).resolves.toEqual([]);
  });
  test("listApplicationUsers", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(listApplicationUsers(TOKEN, { page: 1, pageSize: 20, periodStart: '2026-08-01', periodEnd: '2026-08-31', parentId: 'id-1', structureKind: 'organigramma', toolName: 'x', moduleKey: 'wiki', module: 'wiki', success: true, limit: 10, skip: 0, activeOnly: true, windowMinutes: 15, status: 'active', conversationId: 'c1', username: 'u', intent: 'x', mode: 'x', q: 'x', bustCache: true })).resolves.toBeDefined();
  });
  test("listSectionCatalog", async () => {
    stubFetch(jsonResponse([]));
    await expect(listSectionCatalog(TOKEN, { page: 1, pageSize: 20, periodStart: '2026-08-01', periodEnd: '2026-08-31', parentId: 'id-1', structureKind: 'organigramma', toolName: 'x', moduleKey: 'wiki', module: 'wiki', success: true, limit: 10, skip: 0, activeOnly: true, windowMinutes: 15, status: 'active', conversationId: 'c1', username: 'u', intent: 'x', mode: 'x', q: 'x', bustCache: true })).resolves.toBeDefined();
  });
  test("updateApplicationUser", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(updateApplicationUser(TOKEN, 1, {})).resolves.toBeDefined();
  });
  test("updateApplicationUserPermissions", async () => {
    stubFetch(jsonResponse({ ok: true }), jsonResponse({ ok: true }));
    await expect(updateApplicationUserPermissions(TOKEN, 1, [])).resolves.toBeDefined();
  });
});
