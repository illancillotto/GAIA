import { afterEach, describe, expect, test, vi } from "vitest";

import {
  abortUtenzeRegistryImportJob,
  approveUtenzeBonificaStagingItem,
  backfillWikiConversationMetrics,
  bulkApproveUtenzeBonificaStaging,
  calculatePermissionPreview,
  classifyAnagraficaDocumentContent,
  clearWikiConversationMetricsBackfillJobHistory,
  deactivateAnagraficaSubject,
  downloadAnagraficaDocumentBlob,
  downloadAnagraficaExportBlob,
  downloadMeStraordinariRequest,
  downloadSelectedCatastoDocumentsZipBlob,
  downloadWikiRequestArtifact,
  enqueueWikiConversationMetricsBackfill,
  exportWikiTelemetrySeries,
  exportWikiToolAuditLogs,
  fetchElaborazioneCaptchaImageBlob,
  fetchElaborazioneRequestArtifactPreviewBlob,
  getLatestWikiConversationMetricsBackfillJob,
  getMyWikiRequests,
  getMyWikiRequestsSummary,
  getPendingElaborazioneCaptcha,
  importCapacitasAnagraficaHistory,
  importCapacitasAnagraficaHistoryFile,
  listAllPresenzeCollaborators,
  makeWikiRequestCanonical,
  markWikiRequestDuplicate,
  markWikiRequestViewed,
  patchCapacitasParticelleSyncJobSpeed,
  pollNetworkFirewallMetrics,
  previewAnagraficaImport,
  previewLookupUtenzeAnprByCf,
  previewMeStraordinariRequest,
  pruneWikiTelemetry,
  refreshElaborazioneRuoloAutoSyncSource,
  refreshWikiTelemetry,
  rejectUtenzeBonificaStagingItem,
  releaseElaborazioneCredentials,
  reopenWikiRequest,
  rerunCapacitasAnagraficaHistoryJob,
  rerunCapacitasDomandeIrrigueSyncJob,
  rerunCapacitasInCassSyncJob,
  rerunCapacitasParticelleSyncJob,
  rerunCapacitasTerreniJob,
  rerunPostaOnlineRegisteredMailJob,
  resolveUtenzeVisureRoutingAnomaly,
  resolveWikiConversationContextLink,
  resumeAnagraficaImportJob,
  resumeUtenzeRegistryImportJob,
  retryFailedElaborazioneBatch,
  retrySelectedPresenzeSyncJob,
  retryWikiConversationMetricsBackfillJob,
  runAnagraficaImport,
  runAnagraficaImportFromSubjects,
  runElaborazioneRuoloAutoSyncNow,
  saveElaborazioneCredentials,
  sendApplicationUserInvite,
  skipElaborazioneCaptcha,
  solveElaborazioneCaptcha,
  stopCapacitasParticelleSyncJob,
  triggerUtenzeAnprJob,
  unlinkWikiRequestDuplicate,
  uploadAnagraficaSubjectDocument,
  verifyUtenzeAnprAlive,
  verifyUtenzeAnprDeathDate,
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

describe("api misc clients", () => {

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  test("abortUtenzeRegistryImportJob", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(abortUtenzeRegistryImportJob(TOKEN, "id-1")).resolves.toBeDefined();
  });
  test("approveUtenzeBonificaStagingItem", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(approveUtenzeBonificaStagingItem(TOKEN, "id-1")).resolves.toBeDefined();
  });
  test("backfillWikiConversationMetrics", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(backfillWikiConversationMetrics(TOKEN, {})).resolves.toBeDefined();
  });
  test("bulkApproveUtenzeBonificaStaging", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(bulkApproveUtenzeBonificaStaging(TOKEN, [])).resolves.toBeDefined();
  });
  test("calculatePermissionPreview", async () => {
    stubFetch(jsonResponse([]));
    await expect(calculatePermissionPreview(TOKEN, {}, {})).resolves.toBeDefined();
  });
  test("classifyAnagraficaDocumentContent", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(classifyAnagraficaDocumentContent(TOKEN, "id-1", "value")).resolves.toBeDefined();
  });
  test("clearWikiConversationMetricsBackfillJobHistory", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(clearWikiConversationMetricsBackfillJobHistory(TOKEN)).resolves.toBeDefined();
  });
  test("deactivateAnagraficaSubject", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(deactivateAnagraficaSubject(TOKEN, "id-1")).resolves.toBeDefined();
  });
  test("downloadAnagraficaDocumentBlob", async () => {
    stubFetch(blobResponse());
    await expect(downloadAnagraficaDocumentBlob(TOKEN, "id-1")).resolves.toBeDefined();
  });
  test("downloadAnagraficaExportBlob", async () => {
    stubFetch(blobResponse());
    await expect(downloadAnagraficaExportBlob(TOKEN, false)).resolves.toBeDefined();
  });
  test("downloadMeStraordinariRequest", async () => {
    stubFetch(blobResponse());
    await expect(downloadMeStraordinariRequest(TOKEN, {}, {})).resolves.toBeDefined();
  });
  test("downloadSelectedCatastoDocumentsZipBlob", async () => {
    stubFetch(blobResponse());
    await expect(downloadSelectedCatastoDocumentsZipBlob(TOKEN, [])).resolves.toBeDefined();
  });
  test("downloadWikiRequestArtifact", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(downloadWikiRequestArtifact(TOKEN, "id-1", "id-1")).resolves.toBeDefined();
  });
  test("enqueueWikiConversationMetricsBackfill", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(enqueueWikiConversationMetricsBackfill(TOKEN, {})).resolves.toBeDefined();
  });
  test("exportWikiTelemetrySeries", async () => {
    stubFetch(blobResponse());
    await expect(exportWikiTelemetrySeries(TOKEN, { page: 1, pageSize: 20, periodStart: '2026-08-01', periodEnd: '2026-08-31', parentId: 'id-1', structureKind: 'organigramma', toolName: 'x', moduleKey: 'wiki', module: 'wiki', success: true, limit: 10, skip: 0, activeOnly: true, windowMinutes: 15, status: 'active', conversationId: 'c1', username: 'u', intent: 'x', mode: 'x', q: 'x', bustCache: true })).resolves.toBeDefined();
  });
  test("exportWikiToolAuditLogs", async () => {
    stubFetch(blobResponse());
    await expect(exportWikiToolAuditLogs(TOKEN, { page: 1, pageSize: 20, periodStart: '2026-08-01', periodEnd: '2026-08-31', parentId: 'id-1', structureKind: 'organigramma', toolName: 'x', moduleKey: 'wiki', module: 'wiki', success: true, limit: 10, skip: 0, activeOnly: true, windowMinutes: 15, status: 'active', conversationId: 'c1', username: 'u', intent: 'x', mode: 'x', q: 'x', bustCache: true })).resolves.toBeDefined();
  });
  test("fetchElaborazioneCaptchaImageBlob", async () => {
    stubFetch(blobResponse());
    await expect(fetchElaborazioneCaptchaImageBlob(TOKEN, "id-1")).resolves.toBeDefined();
  });
  test("fetchElaborazioneRequestArtifactPreviewBlob", async () => {
    stubFetch(blobResponse());
    await expect(fetchElaborazioneRequestArtifactPreviewBlob(TOKEN, "id-1")).resolves.toBeDefined();
  });
  test("getLatestWikiConversationMetricsBackfillJob", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(getLatestWikiConversationMetricsBackfillJob(TOKEN)).resolves.toBeDefined();
  });
  test("getMyWikiRequests", async () => {
    stubFetch(jsonResponse([]));
    await expect(getMyWikiRequests(TOKEN)).resolves.toBeDefined();
  });
  test("getMyWikiRequestsSummary", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(getMyWikiRequestsSummary(TOKEN)).resolves.toBeDefined();
  });
  test("getPendingElaborazioneCaptcha", async () => {
    stubFetch(jsonResponse([]));
    await expect(getPendingElaborazioneCaptcha(TOKEN)).resolves.toBeDefined();
  });
  test("importCapacitasAnagraficaHistory", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(importCapacitasAnagraficaHistory(TOKEN, {})).resolves.toBeDefined();
  });
  test("importCapacitasAnagraficaHistoryFile", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(importCapacitasAnagraficaHistoryFile(TOKEN, new File(['x'], 'file.csv'), false)).resolves.toBeDefined();
  });
  test("listAllPresenzeCollaborators", async () => {
    stubFetch(jsonResponse({ items: [], total: 0 }));
    await expect(listAllPresenzeCollaborators(TOKEN)).resolves.toEqual([]);
  });
  test("makeWikiRequestCanonical", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(makeWikiRequestCanonical(TOKEN, "id-1", {})).resolves.toBeDefined();
  });
  test("markWikiRequestDuplicate", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(markWikiRequestDuplicate(TOKEN, "id-1", {})).resolves.toBeDefined();
  });
  test("markWikiRequestViewed", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(markWikiRequestViewed(TOKEN, "id-1")).resolves.toBeDefined();
  });
  test("patchCapacitasParticelleSyncJobSpeed", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(patchCapacitasParticelleSyncJobSpeed(TOKEN, 1, false)).resolves.toBeDefined();
  });
  test("pollNetworkFirewallMetrics", async () => {
    stubFetch(jsonResponse([]));
    await expect(pollNetworkFirewallMetrics(TOKEN, 1)).resolves.toBeDefined();
  });
  test("previewAnagraficaImport", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(previewAnagraficaImport(TOKEN, "value")).resolves.toBeDefined();
  });
  test("previewLookupUtenzeAnprByCf", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(previewLookupUtenzeAnprByCf(TOKEN, "value")).resolves.toBeDefined();
  });
  test("previewMeStraordinariRequest", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(previewMeStraordinariRequest(TOKEN)).resolves.toBeDefined();
  });
  test("pruneWikiTelemetry", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(pruneWikiTelemetry(TOKEN)).resolves.toBeDefined();
  });
  test("refreshElaborazioneRuoloAutoSyncSource", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(refreshElaborazioneRuoloAutoSyncSource(TOKEN)).resolves.toBeDefined();
  });
  test("refreshWikiTelemetry", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(refreshWikiTelemetry(TOKEN, { page: 1, pageSize: 20, periodStart: '2026-08-01', periodEnd: '2026-08-31', parentId: 'id-1', structureKind: 'organigramma', toolName: 'x', moduleKey: 'wiki', module: 'wiki', success: true, limit: 10, skip: 0, activeOnly: true, windowMinutes: 15, status: 'active', conversationId: 'c1', username: 'u', intent: 'x', mode: 'x', q: 'x', bustCache: true })).resolves.toBeDefined();
  });
  test("rejectUtenzeBonificaStagingItem", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(rejectUtenzeBonificaStagingItem(TOKEN, "id-1")).resolves.toBeDefined();
  });
  test("releaseElaborazioneCredentials", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(releaseElaborazioneCredentials(TOKEN)).resolves.toBeDefined();
  });
  test("reopenWikiRequest", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(reopenWikiRequest(TOKEN, "id-1", {})).resolves.toBeDefined();
  });
  test("rerunCapacitasAnagraficaHistoryJob", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(rerunCapacitasAnagraficaHistoryJob(TOKEN, 1)).resolves.toBeDefined();
  });
  test("rerunCapacitasDomandeIrrigueSyncJob", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(rerunCapacitasDomandeIrrigueSyncJob(TOKEN, 1)).resolves.toBeDefined();
  });
  test("rerunCapacitasInCassSyncJob", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(rerunCapacitasInCassSyncJob(TOKEN, 1)).resolves.toBeDefined();
  });
  test("rerunCapacitasParticelleSyncJob", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(rerunCapacitasParticelleSyncJob(TOKEN, 1)).resolves.toBeDefined();
  });
  test("rerunCapacitasTerreniJob", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(rerunCapacitasTerreniJob(TOKEN, 1)).resolves.toBeDefined();
  });
  test("rerunPostaOnlineRegisteredMailJob", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(rerunPostaOnlineRegisteredMailJob(TOKEN, 1)).resolves.toBeDefined();
  });
  test("resolveUtenzeVisureRoutingAnomaly", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(resolveUtenzeVisureRoutingAnomaly(TOKEN, "id-1")).resolves.toBeDefined();
  });
  test("resolveWikiConversationContextLink", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(resolveWikiConversationContextLink(TOKEN, { page: 1, pageSize: 20, periodStart: '2026-08-01', periodEnd: '2026-08-31', parentId: 'id-1', structureKind: 'organigramma', toolName: 'x', moduleKey: 'wiki', module: 'wiki', success: true, limit: 10, skip: 0, activeOnly: true, windowMinutes: 15, status: 'active', conversationId: 'c1', username: 'u', intent: 'x', mode: 'x', q: 'x', bustCache: true })).resolves.toBeDefined();
  });
  test("resumeAnagraficaImportJob", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(resumeAnagraficaImportJob(TOKEN, "id-1")).resolves.toBeDefined();
  });
  test("resumeUtenzeRegistryImportJob", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(resumeUtenzeRegistryImportJob(TOKEN, "id-1")).resolves.toBeDefined();
  });
  test("retryFailedElaborazioneBatch", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(retryFailedElaborazioneBatch(TOKEN, "id-1")).resolves.toBeDefined();
  });
  test("retrySelectedPresenzeSyncJob", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(retrySelectedPresenzeSyncJob(TOKEN, "id-1", {})).resolves.toBeDefined();
  });
  test("retryWikiConversationMetricsBackfillJob", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(retryWikiConversationMetricsBackfillJob(TOKEN, "id-1")).resolves.toBeDefined();
  });
  test("runAnagraficaImport", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(runAnagraficaImport(TOKEN, "value")).resolves.toBeDefined();
  });
  test("runAnagraficaImportFromSubjects", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(runAnagraficaImportFromSubjects(TOKEN)).resolves.toBeDefined();
  });
  test("runElaborazioneRuoloAutoSyncNow", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(runElaborazioneRuoloAutoSyncNow(TOKEN)).resolves.toBeDefined();
  });
  test("saveElaborazioneCredentials", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(saveElaborazioneCredentials(TOKEN, {})).resolves.toBeDefined();
  });
  test("sendApplicationUserInvite", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(sendApplicationUserInvite(TOKEN, 1)).resolves.toBeDefined();
  });
  test("skipElaborazioneCaptcha", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(skipElaborazioneCaptcha(TOKEN, "id-1")).resolves.toBeDefined();
  });
  test("solveElaborazioneCaptcha", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(solveElaborazioneCaptcha(TOKEN, "id-1", "text")).resolves.toBeDefined();
  });
  test("stopCapacitasParticelleSyncJob", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(stopCapacitasParticelleSyncJob(TOKEN, 1)).resolves.toBeDefined();
  });
  test("triggerUtenzeAnprJob", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(triggerUtenzeAnprJob(TOKEN)).resolves.toBeDefined();
  });
  test("unlinkWikiRequestDuplicate", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(unlinkWikiRequestDuplicate(TOKEN, "id-1")).resolves.toBeDefined();
  });
  test("uploadAnagraficaSubjectDocument", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(uploadAnagraficaSubjectDocument(TOKEN, "id-1", new File(['x'], 'file.csv'), "value", "value")).resolves.toBeDefined();
  });
  test("verifyUtenzeAnprAlive", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(verifyUtenzeAnprAlive(TOKEN, "id-1")).resolves.toBeDefined();
  });
  test("verifyUtenzeAnprDeathDate", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(verifyUtenzeAnprDeathDate(TOKEN, "id-1")).resolves.toBeDefined();
  });
});
