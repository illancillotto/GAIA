import { afterEach, describe, expect, test, vi } from "vitest";

import {
  bootstrapOrgStructureFromWhiteCompany,
  createOrgAssignment,
  createOrgOverride,
  createOrgUnit,
  deleteOrgAssignment,
  deleteOrgOverride,
  deleteOrgStructureAssignment,
  deleteOrgUnit,
  exportOrganigrammaSnapshot,
  getOrgAssignments,
  getOrgOverrides,
  getOrgStructureWorkspace,
  getOrgTree,
  getOrgUnit,
  getOrgUnits,
  getOrgVisibility,
  importOrganigrammaSnapshot,
  syncOrgWhiteCompany,
  updateOrgAssignment,
  updateOrgOverride,
  updateOrgUnit,
  upsertOrgStructureAssignment,
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

describe("api organigramma clients", () => {

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  test("bootstrapOrgStructureFromWhiteCompany", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(bootstrapOrgStructureFromWhiteCompany(TOKEN)).resolves.toBeDefined();
  });
  test("createOrgAssignment", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(createOrgAssignment(TOKEN, {}, "organigramma")).resolves.toBeDefined();
  });
  test("createOrgOverride", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(createOrgOverride(TOKEN, {}, "organigramma")).resolves.toBeDefined();
  });
  test("createOrgUnit", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(createOrgUnit(TOKEN, {}, "organigramma")).resolves.toBeDefined();
  });
  test("deleteOrgAssignment", async () => {
    stubFetch(emptyOkResponse());
    await expect(deleteOrgAssignment(TOKEN, "id-1", "organigramma")).resolves.toBeUndefined();
  });
  test("deleteOrgOverride", async () => {
    stubFetch(emptyOkResponse());
    await expect(deleteOrgOverride(TOKEN, "id-1", "organigramma")).resolves.toBeUndefined();
  });
  test("deleteOrgStructureAssignment", async () => {
    stubFetch(emptyOkResponse());
    await expect(deleteOrgStructureAssignment(TOKEN, 1)).resolves.toBeUndefined();
  });
  test("deleteOrgUnit", async () => {
    stubFetch(emptyOkResponse());
    await expect(deleteOrgUnit(TOKEN, "id-1", "organigramma")).resolves.toBeUndefined();
  });
  test("exportOrganigrammaSnapshot", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(exportOrganigrammaSnapshot(TOKEN, "organigramma")).resolves.toBeDefined();
  });
  test("getOrgAssignments", async () => {
    stubFetch(jsonResponse([]));
    await expect(getOrgAssignments(TOKEN, { page: 1, pageSize: 20, periodStart: '2026-08-01', periodEnd: '2026-08-31', parentId: 'id-1', structureKind: 'organigramma', toolName: 'x', moduleKey: 'wiki', module: 'wiki', success: true, limit: 10, skip: 0, activeOnly: true, windowMinutes: 15, status: 'active', conversationId: 'c1', username: 'u', intent: 'x', mode: 'x', q: 'x', bustCache: true })).resolves.toBeDefined();
  });
  test("getOrgOverrides", async () => {
    stubFetch(jsonResponse([]));
    await expect(getOrgOverrides(TOKEN, "organigramma")).resolves.toBeDefined();
  });
  test("getOrgStructureWorkspace", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(getOrgStructureWorkspace(TOKEN)).resolves.toBeDefined();
  });
  test("getOrgTree", async () => {
    stubFetch(jsonResponse([]));
    await expect(getOrgTree(TOKEN, "organigramma")).resolves.toBeDefined();
  });
  test("getOrgUnit", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(getOrgUnit(TOKEN, "id-1", "organigramma")).resolves.toBeDefined();
  });
  test("getOrgUnits", async () => {
    stubFetch(jsonResponse([]));
    await expect(getOrgUnits(TOKEN, { page: 1, pageSize: 20, periodStart: '2026-08-01', periodEnd: '2026-08-31', parentId: 'id-1', structureKind: 'organigramma', toolName: 'x', moduleKey: 'wiki', module: 'wiki', success: true, limit: 10, skip: 0, activeOnly: true, windowMinutes: 15, status: 'active', conversationId: 'c1', username: 'u', intent: 'x', mode: 'x', q: 'x', bustCache: true })).resolves.toBeDefined();
  });
  test("getOrgVisibility", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(getOrgVisibility(TOKEN, 1, "organigramma")).resolves.toBeDefined();
  });
  test("importOrganigrammaSnapshot", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(importOrganigrammaSnapshot(TOKEN, {}, "x", "organigramma")).resolves.toBeDefined();
  });
  test("syncOrgWhiteCompany", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(syncOrgWhiteCompany(TOKEN)).resolves.toBeDefined();
  });
  test("updateOrgAssignment", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(updateOrgAssignment(TOKEN, "id-1", {}, "organigramma")).resolves.toBeDefined();
  });
  test("updateOrgOverride", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(updateOrgOverride(TOKEN, "id-1", {}, "organigramma")).resolves.toBeDefined();
  });
  test("updateOrgUnit", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(updateOrgUnit(TOKEN, "id-1", {}, "organigramma")).resolves.toBeDefined();
  });
  test("upsertOrgStructureAssignment", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(upsertOrgStructureAssignment(TOKEN, 1, {})).resolves.toBeDefined();
  });
});
