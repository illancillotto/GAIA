import { afterEach, describe, expect, test, vi, beforeEach } from "vitest";

import {
  createAnagraficaSubject,
  deleteAnagraficaDocument,
  deleteUtenzeRegistryImportJob,
  getAnagraficaDocumentSummary,
  getAnagraficaImportJob,
  getAnagraficaImportJobs,
  getAnagraficaStats,
  getAnagraficaSubject,
  getAnagraficaSubjectDocuments,
  getAnagraficaSubjectNasCandidates,
  getAnagraficaSubjectNasImportStatus,
  getAnagraficaSubjects,
  getUtenzeAnprConfig,
  getUtenzeAnprJobStatus,
  getUtenzeAnprStatus,
  getUtenzeBonificaStaging,
  getUtenzeBonificaStagingItem,
  getUtenzeSubjectAuditLog,
  getUtenzeSubjectPaymentNotices,
  getUtenzeVisureRoutingAnomalies,
  getUtenzeXlsxImportBatch,
  getUtenzeXlsxImportBatches,
  importAnagraficaSubjectFromNas,
  importAnagraficaSubjectsCsv,
  importUtenzeSubjectsXlsx,
  resetAnagraficaData,
  searchAnagraficaSubjects,
  syncUtenzeAnprSubject,
  updateAnagraficaDocument,
  updateAnagraficaSubject,
  updateUtenzeAnprConfig,
} from "@/lib/api";

const TOKEN = "test-token";

class MockXHR {
  static instances: MockXHR[] = [];
  upload = { addEventListener: vi.fn() };
  status = 200;
  statusText = "OK";
  response: unknown = { ok: true };
  open = vi.fn();
  setRequestHeader = vi.fn();
  send = vi.fn();
  addEventListener = vi.fn((event: string, handler: () => void) => {
    if (event === "load") {
      this.loadHandler = handler;
    }
    if (event === "error") {
      this.errorHandler = handler;
    }
  });
  loadHandler: (() => void) | null = null;
  errorHandler: (() => void) | null = null;

  constructor() {
    MockXHR.instances.push(this);
  }
}


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

describe("api utenze clients", () => {

  beforeEach(() => {
    MockXHR.instances = [];
    vi.stubGlobal("XMLHttpRequest", MockXHR as unknown as typeof XMLHttpRequest);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  test("createAnagraficaSubject", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(createAnagraficaSubject(TOKEN, {})).resolves.toBeDefined();
  });
  test("deleteAnagraficaDocument", async () => {
    stubFetch(emptyOkResponse());
    await expect(deleteAnagraficaDocument(TOKEN, "id-1", "value")).resolves.toBeUndefined();
  });
  test("deleteUtenzeRegistryImportJob", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(deleteUtenzeRegistryImportJob(TOKEN, "id-1")).resolves.toBeDefined();
  });
  test("getAnagraficaDocumentSummary", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(getAnagraficaDocumentSummary(TOKEN)).resolves.toBeDefined();
  });
  test("getAnagraficaImportJob", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(getAnagraficaImportJob(TOKEN, "id-1")).resolves.toBeDefined();
  });
  test("getAnagraficaImportJobs", async () => {
    stubFetch(jsonResponse([]));
    await expect(getAnagraficaImportJobs(TOKEN)).resolves.toBeDefined();
  });
  test("getAnagraficaStats", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(getAnagraficaStats(TOKEN)).resolves.toBeDefined();
  });
  test("getAnagraficaSubject", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(getAnagraficaSubject(TOKEN, "id-1")).resolves.toBeDefined();
  });
  test("getAnagraficaSubjectDocuments", async () => {
    stubFetch(jsonResponse([]));
    await expect(getAnagraficaSubjectDocuments(TOKEN, "id-1")).resolves.toBeDefined();
  });
  test("getAnagraficaSubjectNasCandidates", async () => {
    stubFetch(jsonResponse([]));
    await expect(getAnagraficaSubjectNasCandidates(TOKEN, "id-1", {})).resolves.toBeDefined();
  });
  test("getAnagraficaSubjectNasImportStatus", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(getAnagraficaSubjectNasImportStatus(TOKEN, "id-1")).resolves.toBeDefined();
  });
  test("getAnagraficaSubjects", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(getAnagraficaSubjects(TOKEN, false)).resolves.toBeDefined();
  });
  test("getUtenzeAnprConfig", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(getUtenzeAnprConfig(TOKEN)).resolves.toBeDefined();
  });
  test("getUtenzeAnprJobStatus", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(getUtenzeAnprJobStatus(TOKEN)).resolves.toBeDefined();
  });
  test("getUtenzeAnprStatus", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(getUtenzeAnprStatus(TOKEN, "id-1")).resolves.toBeDefined();
  });
  test("getUtenzeBonificaStaging", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(getUtenzeBonificaStaging(TOKEN, { page: 1, pageSize: 20, periodStart: '2026-08-01', periodEnd: '2026-08-31', parentId: 'id-1', structureKind: 'organigramma', toolName: 'x', moduleKey: 'wiki', module: 'wiki', success: true, limit: 10, skip: 0, activeOnly: true, windowMinutes: 15, status: 'active', conversationId: 'c1', username: 'u', intent: 'x', mode: 'x', q: 'x', bustCache: true })).resolves.toBeDefined();
  });
  test("getUtenzeBonificaStagingItem", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(getUtenzeBonificaStagingItem(TOKEN, "id-1")).resolves.toBeDefined();
  });
  test("getUtenzeSubjectAuditLog", async () => {
    stubFetch(jsonResponse([]));
    await expect(getUtenzeSubjectAuditLog(TOKEN, "id-1")).resolves.toBeDefined();
  });
  test("getUtenzeSubjectPaymentNotices", async () => {
    stubFetch(jsonResponse([]));
    await expect(getUtenzeSubjectPaymentNotices(TOKEN, "id-1")).resolves.toBeDefined();
  });
  test("getUtenzeVisureRoutingAnomalies", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(getUtenzeVisureRoutingAnomalies(TOKEN, false)).resolves.toBeDefined();
  });
  test("getUtenzeXlsxImportBatch", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(getUtenzeXlsxImportBatch(TOKEN, "id-1")).resolves.toBeDefined();
  });
  test("getUtenzeXlsxImportBatches", async () => {
    stubFetch(jsonResponse([]));
    await expect(getUtenzeXlsxImportBatches(TOKEN)).resolves.toBeDefined();
  });
  test("importAnagraficaSubjectFromNas", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(importAnagraficaSubjectFromNas(TOKEN, "id-1")).resolves.toBeDefined();
  });
  test("importAnagraficaSubjectsCsv", async () => {
    const pending = importAnagraficaSubjectsCsv(TOKEN, new File(['x'], 'file.csv'), () => undefined);
    const xhr = MockXHR.instances.at(-1)!;
    xhr.loadHandler?.();
    await expect(pending).resolves.toBeDefined();
  });
  test("importUtenzeSubjectsXlsx", async () => {
    const pending = importUtenzeSubjectsXlsx(TOKEN, new File(['x'], 'file.csv'), () => undefined);
    const xhr = MockXHR.instances.at(-1)!;
    xhr.loadHandler?.();
    await expect(pending).resolves.toBeDefined();
  });
  test("resetAnagraficaData", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(resetAnagraficaData(TOKEN, {})).resolves.toBeDefined();
  });
  test("searchAnagraficaSubjects", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(searchAnagraficaSubjects(TOKEN, "value", {})).resolves.toBeDefined();
  });
  test("syncUtenzeAnprSubject", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(syncUtenzeAnprSubject(TOKEN, "id-1")).resolves.toBeDefined();
  });
  test("updateAnagraficaDocument", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(updateAnagraficaDocument(TOKEN, "id-1", {})).resolves.toBeDefined();
  });
  test("updateAnagraficaSubject", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(updateAnagraficaSubject(TOKEN, "id-1", {})).resolves.toBeDefined();
  });
  test("updateUtenzeAnprConfig", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(updateUtenzeAnprConfig(TOKEN, {})).resolves.toBeDefined();
  });
});
