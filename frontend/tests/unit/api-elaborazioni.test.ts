import { afterEach, describe, expect, test, vi } from "vitest";

import {
  cancelElaborazioneBatch,
  createBonificaOristaneseCredential,
  createCapacitasAnagraficaHistoryJob,
  createCapacitasCredential,
  createCapacitasDomandeIrrigueSyncJob,
  createCapacitasInCassRuoloHarvest,
  createCapacitasInCassSyncJob,
  createCapacitasParticelleSyncJob,
  createCapacitasTerreniJob,
  createElaborazioneBatch,
  createElaborazioneRichiesta,
  createPostaOnlineCredential,
  createPostaOnlineRegisteredMailJob,
  deleteBonificaOristaneseCredential,
  deleteBonificaSyncJob,
  deleteCapacitasAnagraficaHistoryJob,
  deleteCapacitasCredential,
  deleteCapacitasDomandeIrrigueSyncJob,
  deleteCapacitasInCassSyncJob,
  deleteCapacitasParticelleSyncJob,
  deleteCapacitasTerreniJob,
  deleteElaborazioneCredential,
  deleteElaborazioneCredentials,
  deletePostaOnlineCredential,
  deletePostaOnlineRegisteredMailJob,
  downloadElaborazioneBatchReportJsonBlob,
  downloadElaborazioneBatchReportMarkdownBlob,
  downloadElaborazioneBatchZipBlob,
  downloadElaborazioneRequestArtifactsBlob,
  getBonificaSyncStatus,
  getCapacitasFogli,
  getCapacitasSezioni,
  getElaborazioneAnprSummary,
  getElaborazioneAutoJobControls,
  getElaborazioneBatch,
  getElaborazioneBatches,
  getElaborazioneCaptchaSummary,
  getElaborazioneCredentialTest,
  getElaborazioneCredentials,
  getElaborazioneRuntimeMetrics,
  getElaborazioneRuoloAutoSyncConfig,
  getElaborazioneRuoloAutoSyncStatus,
  getGateMobileSyncStatus,
  listBonificaOristaneseCredentials,
  listCapacitasAnagraficaHistoryJobs,
  listCapacitasCredentials,
  listCapacitasDomandeIrrigueSyncJobs,
  listCapacitasInCassSyncJobs,
  listCapacitasParticelleAnomalie,
  listCapacitasParticelleSyncJobs,
  listCapacitasTerreniJobs,
  listPostaOnlineCredentials,
  listPostaOnlineRegisteredMailJobs,
  refetchCapacitasCertificatiEmpty,
  resolveCapacitasParticellaFrazione,
  runBonificaSync,
  searchCapacitasFrazioni,
  searchCapacitasInvolture,
  searchCapacitasTerreni,
  startElaborazioneBatch,
  testBonificaOristaneseCredential,
  testCapacitasCredential,
  testElaborazioneCredentials,
  testPostaOnlineCredential,
  triggerGateMobileSyncRun,
  updateBonificaOristaneseCredential,
  updateCapacitasCredential,
  updateElaborazioneAutoJobControl,
  updateElaborazioneCredential,
  updateElaborazioneRuoloAutoSyncConfig,
  updatePostaOnlineCredential,
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

describe("api elaborazioni clients", () => {

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  test("cancelElaborazioneBatch", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(cancelElaborazioneBatch(TOKEN, "id-1")).resolves.toBeDefined();
  });
  test("createBonificaOristaneseCredential", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(createBonificaOristaneseCredential(TOKEN, {})).resolves.toBeDefined();
  });
  test("createCapacitasAnagraficaHistoryJob", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(createCapacitasAnagraficaHistoryJob(TOKEN, {})).resolves.toBeDefined();
  });
  test("createCapacitasCredential", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(createCapacitasCredential(TOKEN, {})).resolves.toBeDefined();
  });
  test("createCapacitasDomandeIrrigueSyncJob", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(createCapacitasDomandeIrrigueSyncJob(TOKEN, {})).resolves.toBeDefined();
  });
  test("createCapacitasInCassRuoloHarvest", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(createCapacitasInCassRuoloHarvest(TOKEN, {})).resolves.toBeDefined();
  });
  test("createCapacitasInCassSyncJob", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(createCapacitasInCassSyncJob(TOKEN, {})).resolves.toBeDefined();
  });
  test("createCapacitasParticelleSyncJob", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(createCapacitasParticelleSyncJob(TOKEN, {})).resolves.toBeDefined();
  });
  test("createCapacitasTerreniJob", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(createCapacitasTerreniJob(TOKEN, {})).resolves.toBeDefined();
  });
  test("createElaborazioneBatch", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(createElaborazioneBatch(TOKEN, new File(['x'], 'file.csv'), "value")).resolves.toBeDefined();
  });
  test("createElaborazioneRichiesta", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(createElaborazioneRichiesta(TOKEN, {})).resolves.toBeDefined();
  });
  test("createPostaOnlineCredential", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(createPostaOnlineCredential(TOKEN, {})).resolves.toBeDefined();
  });
  test("createPostaOnlineRegisteredMailJob", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(createPostaOnlineRegisteredMailJob(TOKEN, {})).resolves.toBeDefined();
  });
  test("deleteBonificaOristaneseCredential", async () => {
    stubFetch(emptyOkResponse());
    await expect(deleteBonificaOristaneseCredential(TOKEN, 1)).resolves.toBeUndefined();
  });
  test("deleteBonificaSyncJob", async () => {
    stubFetch(emptyOkResponse());
    await expect(deleteBonificaSyncJob(TOKEN, "id-1")).resolves.toBeUndefined();
  });
  test("deleteCapacitasAnagraficaHistoryJob", async () => {
    stubFetch(emptyOkResponse());
    await expect(deleteCapacitasAnagraficaHistoryJob(TOKEN, 1)).resolves.toBeUndefined();
  });
  test("deleteCapacitasCredential", async () => {
    stubFetch(emptyOkResponse());
    await expect(deleteCapacitasCredential(TOKEN, 1)).resolves.toBeUndefined();
  });
  test("deleteCapacitasDomandeIrrigueSyncJob", async () => {
    stubFetch(emptyOkResponse());
    await expect(deleteCapacitasDomandeIrrigueSyncJob(TOKEN, 1)).resolves.toBeUndefined();
  });
  test("deleteCapacitasInCassSyncJob", async () => {
    stubFetch(emptyOkResponse());
    await expect(deleteCapacitasInCassSyncJob(TOKEN, 1)).resolves.toBeUndefined();
  });
  test("deleteCapacitasParticelleSyncJob", async () => {
    stubFetch(emptyOkResponse());
    await expect(deleteCapacitasParticelleSyncJob(TOKEN, 1)).resolves.toBeUndefined();
  });
  test("deleteCapacitasTerreniJob", async () => {
    stubFetch(emptyOkResponse());
    await expect(deleteCapacitasTerreniJob(TOKEN, 1)).resolves.toBeUndefined();
  });
  test("deleteElaborazioneCredential", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(deleteElaborazioneCredential(TOKEN, "id-1")).resolves.toBeDefined();
  });
  test("deleteElaborazioneCredentials", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(deleteElaborazioneCredentials(TOKEN)).resolves.toBeDefined();
  });
  test("deletePostaOnlineCredential", async () => {
    stubFetch(emptyOkResponse());
    await expect(deletePostaOnlineCredential(TOKEN, 1)).resolves.toBeUndefined();
  });
  test("deletePostaOnlineRegisteredMailJob", async () => {
    stubFetch(emptyOkResponse());
    await expect(deletePostaOnlineRegisteredMailJob(TOKEN, 1)).resolves.toBeUndefined();
  });
  test("downloadElaborazioneBatchReportJsonBlob", async () => {
    stubFetch(blobResponse());
    await expect(downloadElaborazioneBatchReportJsonBlob(TOKEN, "id-1")).resolves.toBeDefined();
  });
  test("downloadElaborazioneBatchReportMarkdownBlob", async () => {
    stubFetch(blobResponse());
    await expect(downloadElaborazioneBatchReportMarkdownBlob(TOKEN, "id-1")).resolves.toBeDefined();
  });
  test("downloadElaborazioneBatchZipBlob", async () => {
    stubFetch(blobResponse());
    await expect(downloadElaborazioneBatchZipBlob(TOKEN, "id-1")).resolves.toBeDefined();
  });
  test("downloadElaborazioneRequestArtifactsBlob", async () => {
    stubFetch(blobResponse());
    await expect(downloadElaborazioneRequestArtifactsBlob(TOKEN, "id-1")).resolves.toBeDefined();
  });
  test("getBonificaSyncStatus", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(getBonificaSyncStatus(TOKEN)).resolves.toBeDefined();
  });
  test("getCapacitasFogli", async () => {
    stubFetch(jsonResponse([]));
    await expect(getCapacitasFogli(TOKEN, "id-1", "value", 1)).resolves.toBeDefined();
  });
  test("getCapacitasSezioni", async () => {
    stubFetch(jsonResponse([]));
    await expect(getCapacitasSezioni(TOKEN, "id-1", 1)).resolves.toBeDefined();
  });
  test("getElaborazioneAnprSummary", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(getElaborazioneAnprSummary(TOKEN)).resolves.toBeDefined();
  });
  test("getElaborazioneAutoJobControls", async () => {
    stubFetch(jsonResponse([]));
    await expect(getElaborazioneAutoJobControls(TOKEN)).resolves.toBeDefined();
  });
  test("getElaborazioneBatch", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(getElaborazioneBatch(TOKEN, "id-1", false)).resolves.toBeDefined();
  });
  test("getElaborazioneBatches", async () => {
    stubFetch(jsonResponse([]));
    await expect(getElaborazioneBatches(TOKEN, "value")).resolves.toBeDefined();
  });
  test("getElaborazioneCaptchaSummary", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(getElaborazioneCaptchaSummary(TOKEN)).resolves.toBeDefined();
  });
  test("getElaborazioneCredentialTest", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(getElaborazioneCredentialTest(TOKEN, "id-1")).resolves.toBeDefined();
  });
  test("getElaborazioneCredentials", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(getElaborazioneCredentials(TOKEN)).resolves.toBeDefined();
  });
  test("getElaborazioneRuntimeMetrics", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(getElaborazioneRuntimeMetrics(TOKEN)).resolves.toBeDefined();
  });
  test("getElaborazioneRuoloAutoSyncConfig", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(getElaborazioneRuoloAutoSyncConfig(TOKEN)).resolves.toBeDefined();
  });
  test("getElaborazioneRuoloAutoSyncStatus", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(getElaborazioneRuoloAutoSyncStatus(TOKEN)).resolves.toBeDefined();
  });
  test("getGateMobileSyncStatus", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(getGateMobileSyncStatus(TOKEN)).resolves.toBeDefined();
  });
  test("listBonificaOristaneseCredentials", async () => {
    stubFetch(jsonResponse([]));
    await expect(listBonificaOristaneseCredentials(TOKEN)).resolves.toBeDefined();
  });
  test("listCapacitasAnagraficaHistoryJobs", async () => {
    stubFetch(jsonResponse([]));
    await expect(listCapacitasAnagraficaHistoryJobs(TOKEN)).resolves.toBeDefined();
  });
  test("listCapacitasCredentials", async () => {
    stubFetch(jsonResponse([]));
    await expect(listCapacitasCredentials(TOKEN)).resolves.toBeDefined();
  });
  test("listCapacitasDomandeIrrigueSyncJobs", async () => {
    stubFetch(jsonResponse([]));
    await expect(listCapacitasDomandeIrrigueSyncJobs(TOKEN)).resolves.toBeDefined();
  });
  test("listCapacitasInCassSyncJobs", async () => {
    stubFetch(jsonResponse([]));
    await expect(listCapacitasInCassSyncJobs(TOKEN)).resolves.toBeDefined();
  });
  test("listCapacitasParticelleAnomalie", async () => {
    stubFetch(jsonResponse([]));
    await expect(listCapacitasParticelleAnomalie(TOKEN, 1)).resolves.toBeDefined();
  });
  test("listCapacitasParticelleSyncJobs", async () => {
    stubFetch(jsonResponse([]));
    await expect(listCapacitasParticelleSyncJobs(TOKEN)).resolves.toBeDefined();
  });
  test("listCapacitasTerreniJobs", async () => {
    stubFetch(jsonResponse([]));
    await expect(listCapacitasTerreniJobs(TOKEN)).resolves.toBeDefined();
  });
  test("listPostaOnlineCredentials", async () => {
    stubFetch(jsonResponse([]));
    await expect(listPostaOnlineCredentials(TOKEN)).resolves.toBeDefined();
  });
  test("listPostaOnlineRegisteredMailJobs", async () => {
    stubFetch(jsonResponse([]));
    await expect(listPostaOnlineRegisteredMailJobs(TOKEN)).resolves.toBeDefined();
  });
  test("refetchCapacitasCertificatiEmpty", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(refetchCapacitasCertificatiEmpty(TOKEN, {})).resolves.toBeDefined();
  });
  test("resolveCapacitasParticellaFrazione", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(resolveCapacitasParticellaFrazione(TOKEN, "id-1", {})).resolves.toBeDefined();
  });
  test("runBonificaSync", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(runBonificaSync(TOKEN, {})).resolves.toBeDefined();
  });
  test("searchCapacitasFrazioni", async () => {
    stubFetch(jsonResponse([]));
    await expect(searchCapacitasFrazioni(TOKEN, "x", 1)).resolves.toBeDefined();
  });
  test("searchCapacitasInvolture", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(searchCapacitasInvolture(TOKEN, {})).resolves.toBeDefined();
  });
  test("searchCapacitasTerreni", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(searchCapacitasTerreni(TOKEN, {})).resolves.toBeDefined();
  });
  test("startElaborazioneBatch", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(startElaborazioneBatch(TOKEN, "id-1")).resolves.toBeDefined();
  });
  test("testBonificaOristaneseCredential", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(testBonificaOristaneseCredential(TOKEN, 1)).resolves.toBeDefined();
  });
  test("testCapacitasCredential", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(testCapacitasCredential(TOKEN, 1)).resolves.toBeDefined();
  });
  test("testElaborazioneCredentials", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(testElaborazioneCredentials(TOKEN, "value")).resolves.toBeDefined();
  });
  test("testPostaOnlineCredential", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(testPostaOnlineCredential(TOKEN, 1, {})).resolves.toBeDefined();
  });
  test("triggerGateMobileSyncRun", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(triggerGateMobileSyncRun(TOKEN)).resolves.toBeDefined();
  });
  test("updateBonificaOristaneseCredential", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(updateBonificaOristaneseCredential(TOKEN, 1, {})).resolves.toBeDefined();
  });
  test("updateCapacitasCredential", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(updateCapacitasCredential(TOKEN, 1, {})).resolves.toBeDefined();
  });
  test("updateElaborazioneAutoJobControl", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(updateElaborazioneAutoJobControl(TOKEN, "value", {})).resolves.toBeDefined();
  });
  test("updateElaborazioneCredential", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(updateElaborazioneCredential(TOKEN, "id-1", {})).resolves.toBeDefined();
  });
  test("updateElaborazioneRuoloAutoSyncConfig", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(updateElaborazioneRuoloAutoSyncConfig(TOKEN, {})).resolves.toBeDefined();
  });
  test("updatePostaOnlineCredential", async () => {
    stubFetch(jsonResponse({ ok: true }));
    await expect(updatePostaOnlineCredential(TOKEN, 1, {})).resolves.toBeDefined();
  });
});
