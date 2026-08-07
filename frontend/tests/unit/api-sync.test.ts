import { afterEach, describe, expect, test, vi } from "vitest";

import {
  applySync,
  cancelSyncJob,
  createSyncJob,
  getSyncCapabilities,
  getSyncJobs,
  getSyncRuns,
  previewSync,
  retrySyncJob,
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

describe("api sync clients", () => {

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  test("applySync", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(applySync(TOKEN, {})).resolves.toBeDefined();
  });
  test("cancelSyncJob", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(cancelSyncJob(TOKEN, 1)).resolves.toBeDefined();
  });
  test("createSyncJob", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(createSyncJob(TOKEN, {})).resolves.toBeDefined();
  });
  test("getSyncCapabilities", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(getSyncCapabilities(TOKEN)).resolves.toBeDefined();
  });
  test("getSyncJobs", async () => {
    stubFetch(jsonResponse([]));
    await expect(getSyncJobs(TOKEN)).resolves.toBeDefined();
  });
  test("getSyncRuns", async () => {
    stubFetch(jsonResponse([]));
    await expect(getSyncRuns(TOKEN)).resolves.toBeDefined();
  });
  test("previewSync", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(previewSync(TOKEN, {})).resolves.toBeDefined();
  });
  test("retrySyncJob", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(retrySyncJob(TOKEN, 1)).resolves.toBeDefined();
  });
});
