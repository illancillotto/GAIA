import { afterEach, describe, expect, test, vi } from "vitest";

import {
  downloadCatastoDocumentBlob,
  getCatastoComuni,
  getCatastoDocument,
  getCatastoDocuments,
  searchCatastoDocuments,
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

describe("api catasto clients", () => {

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  test("downloadCatastoDocumentBlob", async () => {
    stubFetch(blobResponse());
    await expect(downloadCatastoDocumentBlob(TOKEN, "id-1")).resolves.toBeDefined();
  });
  test("getCatastoComuni", async () => {
    stubFetch(jsonResponse([]));
    await expect(getCatastoComuni(TOKEN, "value")).resolves.toBeDefined();
  });
  test("getCatastoDocument", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(getCatastoDocument(TOKEN, "id-1")).resolves.toBeDefined();
  });
  test("getCatastoDocuments", async () => {
    stubFetch(jsonResponse([]));
    await expect(getCatastoDocuments(TOKEN, "value")).resolves.toBeDefined();
  });
  test("searchCatastoDocuments", async () => {
    stubFetch(jsonResponse([]));
    await expect(searchCatastoDocuments(TOKEN, "value")).resolves.toBeDefined();
  });
});
