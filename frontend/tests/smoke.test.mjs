import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const frontendRoot = path.resolve(__dirname, "..");

function read(relativePath) {
  return fs.readFileSync(path.join(frontendRoot, relativePath), "utf8");
}

test("frontend package exposes core scripts and redesign dependencies", () => {
  const pkg = JSON.parse(read("package.json"));

  assert.equal(pkg.name, "gaia-frontend");
  assert.equal(pkg.private, true);
  assert.ok(pkg.scripts.dev);
  assert.ok(pkg.scripts.build);
  assert.ok(pkg.scripts["build:clean"]);
  assert.ok(pkg.dependencies["@tanstack/react-table"]);
  assert.ok(pkg.dependencies["react-hook-form"]);
  assert.ok(pkg.devDependencies.tailwindcss);
  assert.ok(pkg.dependencies.clsx);
});

test("frontend api client defaults to same-origin api base", () => {
  const apiClient = read("src/lib/api.ts");

  assert.match(apiClient, /const DEFAULT_API_BASE_URL = "\/api"/);
});

test("dashboard keeps login gate and GAIA module selector copy", () => {
  const homePage = read("src/app/page.tsx");
  const loginPage = read("src/app/login/page.tsx");

  assert.match(homePage, /router\.replace\("\/login"\)/);
  assert.match(homePage, /GAIA NAS Control/);
  assert.match(homePage, /GAIA Rete/);
  assert.match(homePage, /GAIA Catasto/);
  assert.match(homePage, /In sviluppo/);
  assert.match(homePage, /GAIA Elaborazioni/);
  assert.match(loginPage, /router\.replace\("\/"\)/);
  assert.match(loginPage, /router\.push\("\/"\)/);
  assert.match(loginPage, /GAIA Catasto/);
  assert.match(loginPage, /Piattaforma modulare unificata/);
});

test("layout includes app shell, sidebar and topbar", () => {
  const shell = read("src/components/layout/app-shell.tsx");
  const sidebar = read("src/components/layout/sidebar.tsx");
  const platformSidebar = read("src/components/layout/platform-sidebar.tsx");
  const moduleSidebar = read("src/components/layout/module-sidebar.tsx");
  const topbar = read("src/components/layout/topbar.tsx");
  const statusPill = read("src/components/ui/status-pill.tsx");

  assert.match(shell, /Sidebar/);
  assert.match(sidebar, /PlatformSidebar/);
  assert.match(sidebar, /ModuleSidebar/);
  assert.match(platformSidebar, /Consorzio di Bonifica/);
  assert.match(platformSidebar, /dell&apos;Oristanese/);
  assert.match(platformSidebar, /Home GAIA/);
  assert.match(platformSidebar, /Modulo attivo/);
  assert.match(platformSidebar, /Catasto/);
  assert.match(moduleSidebar, /Sincronizzazione/);
  assert.match(moduleSidebar, /Review NAS/);
  assert.match(moduleSidebar, /Capacitas/);
  assert.match(moduleSidebar, /Elaborazione massiva/);
  assert.match(topbar, /StatusPill/);
  assert.match(statusPill, /Backend connesso/);
});

test("catasto stays minimal while elaborazioni wires api client and realtime workflow", () => {
  const dashboardPage = read("src/app/catasto/page.tsx");
  const catastoSettingsPage = read("src/app/catasto/settings/page.tsx");
  const catastoCapacitasPage = read("src/app/catasto/capacitas/page.tsx");
  const catastoPageWrapper = read("src/components/catasto/catasto-page.tsx");
  const elaborazioniDashboardPage = read("src/app/elaborazioni/page.tsx");
  const elaborazioniSettingsPage = read("src/app/elaborazioni/settings/page.tsx");
  const elaborazioniCapacitasPage = read("src/app/elaborazioni/capacitas/page.tsx");
  const newBatchPage = read("src/app/catasto/new-batch/page.tsx");
  const newSinglePage = read("src/app/catasto/new-single/page.tsx");
  const requestWorkspace = read("src/components/catasto/request-workspace.tsx");
  const archiveWorkspace = read("src/components/catasto/archive-workspace.tsx");
  const batchDetailPage = read("src/app/catasto/batches/[id]/page.tsx");
  const documentsPage = read("src/app/catasto/documents/page.tsx");
  const documentDetailPage = read("src/app/catasto/documents/[id]/page.tsx");
  const catastoLayout = read("src/app/catasto/layout.tsx");
  const importPage = read("src/app/catasto/import/page.tsx");
  const importDetailPage = read("src/app/catasto/import/[id]/page.tsx");
  const distrettiPage = read("src/app/catasto/distretti/page.tsx");
  const distrettoDetailPage = read("src/app/catasto/distretti/[id]/page.tsx");
  const particelleDetailPage = read("src/app/catasto/particelle/[id]/page.tsx");
  const anomaliePage = read("src/app/catasto/anomalie/page.tsx");
  const anagraficaPage = read("src/app/catasto/elaborazioni-massive/page.tsx");
  const anagraficaBulkPanel = read("src/components/catasto/anagrafica/AnagraficaBulkPanel.tsx");
  const elaborazioniAdeAlignmentPage = read("src/app/elaborazioni/ade-alignment/page.tsx");
  const elaborazioniAdeAlignmentWorkspace = read("src/components/elaborazioni/ade-alignment-workspace.tsx");
  const gisPage = read("src/app/catasto/gis/page.tsx");
  const mapContainer = read("src/components/catasto/gis/MapContainer.tsx");
  const catastoApi = read("src/lib/api/catasto.ts");
  const catastoTypes = read("src/types/catasto.ts");

  assert.match(dashboardPage, /GAIA Catasto/);
  assert.match(dashboardPage, /catastoGetDashboardSummary/);
  assert.match(dashboardPage, /Cruscotto dati catastali/);
  assert.match(catastoApi, /catastoGetDashboardSummary/);
  assert.match(catastoApi, /catastoGisSyncAdeWfsBboxAsync/);
  assert.match(catastoApi, /catastoGisGetAdeWfsRunStatus/);
  assert.match(catastoTypes, /CatDashboardSummary/);
  assert.match(catastoPageWrapper, /ProtectedPage/);
  assert.doesNotMatch(catastoPageWrapper, /CatastoPhase1Nav/);
  assert.doesNotMatch(catastoLayout, /CatastoPhase1Nav/);
  assert.match(catastoSettingsPage, /redirect\("\/elaborazioni\/settings"\)/);
  assert.match(catastoCapacitasPage, /redirect\("\/elaborazioni\/capacitas"\)/);
  assert.match(elaborazioniDashboardPage, /GAIA Elaborazioni/);
  assert.match(elaborazioniDashboardPage, /\/elaborazioni\/capacitas/);
  assert.match(elaborazioniDashboardPage, /\/elaborazioni\/ade-alignment/);
  assert.match(elaborazioniSettingsPage, /ElaborazioniSettingsWorkspace/);
  assert.match(read("src/components/elaborazioni/settings-workspace.tsx"), /createCapacitasCredential/);
  assert.match(read("src/components/elaborazioni/settings-workspace.tsx"), /updateCapacitasCredential/);
  assert.match(read("src/components/elaborazioni/settings-workspace.tsx"), /listCapacitasCredentials/);
  assert.match(elaborazioniCapacitasPage, /ElaborazioniCapacitasWorkspace/);
  assert.match(elaborazioniAdeAlignmentPage, /ElaborazioniAdeAlignmentWorkspace/);
  assert.match(elaborazioniAdeAlignmentWorkspace, /catastoGisSyncAdeWfsBboxAsync/);
  assert.match(elaborazioniAdeAlignmentWorkspace, /catastoGisPreviewAdeAlignmentApply/);
  assert.match(elaborazioniAdeAlignmentWorkspace, /catastoGisApplyAdeAlignment/);
  assert.match(elaborazioniAdeAlignmentWorkspace, /catastoGisGetLatestAdeWfsRunStatus/);
  assert.match(elaborazioniAdeAlignmentWorkspace, /progress_percent/);
  assert.match(elaborazioniAdeAlignmentWorkspace, /tiles_completed/);
  assert.match(read("src/components/elaborazioni/capacitas-workspace.tsx"), /listCapacitasCredentials/);
  assert.match(read("src/components/elaborazioni/capacitas-workspace.tsx"), /CAPACITAS_SECTIONS/);
  assert.match(read("src/components/elaborazioni/capacitas-workspace.tsx"), /PREVIEW_ROWS_LIMIT/);
  assert.match(newBatchPage, /redirect\("\/elaborazioni\/new-batch"\)/);
  assert.match(newSinglePage, /redirect\("\/elaborazioni\/new-single"\)/);
  assert.match(importPage, /Polling ogni 2s/);
  assert.match(importPage, /type StepKey = "upload" \| "progress" \| "report"/);
  assert.match(importPage, /catastoUploadCapacitas/);
  assert.match(importPage, /catastoGetImportStatus/);
  assert.match(importPage, /catastoGetImportReport/);
  assert.match(importPage, /setBatchId\(result\.batch_id\)/);
  assert.match(importPage, /setStep\("progress"\)/);
  assert.match(importPage, /status\.status === "completed" \|\| status\.status === "failed"/);
  assert.match(importPage, /setStep\("report"\)/);
  assert.match(importPage, /Import fallito/);
  assert.match(importPage, /batchFailureMessage/);
  assert.match(importPage, /Sintesi batch/);
  assert.match(importPage, /Distretti rilevati/);
  assert.match(importPage, /Comuni rilevati/);
  assert.match(importPage, /Storico import recenti/);
  assert.match(importPage, /Audit import/);
  assert.match(importPage, /catastoGetImportSummary/);
  assert.match(importPage, /Ultimo completato/);
  assert.match(importPage, /catastoGetImportHistory/);
  assert.match(importPage, /Apri report/);
  assert.match(importPage, /Dettaglio/);
  assert.match(importDetailPage, /Dettaglio import/);
  assert.match(importDetailPage, /catastoGetImportStatus/);
  assert.match(importDetailPage, /catastoGetImportReport/);
  assert.match(importPage, /historyStatus/);
  assert.match(importPage, /historyLimit/);
  assert.match(importPage, /setReportTipo\(c\.tipo\)/);
  assert.match(importPage, /setReportPage\(1\)/);
  assert.match(distrettiPage, /catastoListDistretti/);
  assert.match(distrettiPage, /catastoGetDistrettoKpi/);
  assert.match(distrettiPage, /L'anno corrente/);
  assert.match(distrettiPage, /Tabella distretti/);
  assert.match(distrettoDetailPage, /catastoGetDistretto/);
  assert.match(distrettoDetailPage, /catastoListParticelle/);
  assert.match(distrettoDetailPage, /catastoListAnomalie/);
  assert.match(distrettoDetailPage, /Esporta CSV/);
  assert.match(distrettoDetailPage, /Esporta XLS/);
  assert.match(distrettoDetailPage, /Esporta PDF/);
  assert.match(distrettoDetailPage, /Vista completa/);
  assert.match(anomaliePage, /catastoUpdateAnomalia/);
  assert.match(anomaliePage, /catastoGetAnomalieSummary/);
  assert.match(anomaliePage, /catastoGetCfWizardItems/);
  assert.match(anomaliePage, /catastoApplyCfWizard/);
  assert.match(anomaliePage, /catastoGetComuneWizardItems/);
  assert.match(anomaliePage, /catastoApplyComuneWizard/);
  assert.match(anomaliePage, /catastoGetParticellaWizardItems/);
  assert.match(anomaliePage, /catastoApplyParticellaWizard/);
  assert.match(anomaliePage, /Code di lavoro/);
  assert.match(anomaliePage, /Wizard codice fiscale/);
  assert.match(anomaliePage, /Wizard comune invalido/);
  assert.match(anomaliePage, /Wizard particella assente/);
  assert.match(anomaliePage, /requiredRoles=\{\["admin", "super_admin"\]\}/);
  assert.match(catastoApi, /catastoGetAnomalieSummary/);
  assert.match(catastoApi, /catastoGetCfWizardItems/);
  assert.match(catastoApi, /catastoApplyCfWizard/);
  assert.match(catastoApi, /catastoGetComuneWizardItems/);
  assert.match(catastoApi, /catastoApplyComuneWizard/);
  assert.match(catastoApi, /catastoGetParticellaWizardItems/);
  assert.match(catastoApi, /catastoApplyParticellaWizard/);
  assert.match(catastoTypes, /CatAnomaliaSummary/);
  assert.match(catastoTypes, /CatAnomaliaCfWizardItem/);
  assert.match(catastoTypes, /CatAnomaliaComuneWizardItem/);
  assert.match(catastoTypes, /CatAnomaliaParticellaWizardItem/);
  assert.match(anagraficaPage, /Elaborazione massiva/);
  assert.match(anagraficaPage, /AnagraficaBulkPanel/);
  assert.match(anagraficaBulkPanel, /catastoBulkSearchAnagrafica/);
  assert.match(particelleDetailPage, /catastoGetParticellaUtenze/);
  assert.match(particelleDetailPage, /catastoGetParticellaAnomalie/);
  assert.match(mapContainer, /\/tiles\/cat_distretti\/\{z\}\/\{x\}\/\{y\}/);
  assert.match(mapContainer, /"source-layer": "cat_distretti"/);
  assert.match(mapContainer, /id: "distretti-fill"/);
  assert.match(mapContainer, /id: "distretti-outline"/);
  assert.match(gisPage, /Stato allineamento AdE/);
  assert.match(gisPage, /\/elaborazioni\/ade-alignment/);
  assert.match(gisPage, /progress_message/);
  assert.match(requestWorkspace, /createElaborazioneBatch/);
  assert.match(requestWorkspace, /startElaborazioneBatch/);
  assert.match(requestWorkspace, /Scarica template CSV/);
  assert.match(requestWorkspace, /useForm/);
  assert.match(requestWorkspace, /createElaborazioneRichiesta/);
  assert.match(batchDetailPage, /createElaborazioneBatchWebSocket/);
  assert.match(batchDetailPage, /cancelElaborazioneBatch/);
  assert.match(batchDetailPage, /retryFailedElaborazioneBatch/);
  assert.match(batchDetailPage, /CaptchaDialog/);
  assert.match(batchDetailPage, /fetchElaborazioneCaptchaImageBlob/);
  assert.match(batchDetailPage, /downloadElaborazioneBatchZipBlob/);
  assert.match(read("src/app/catasto/batches/page.tsx"), /redirect\("\/elaborazioni\/batches"\)/);
  assert.match(documentsPage, /router\.replace\("\/catasto\/archive\?view=documents"\)/);
  assert.match(archiveWorkspace, /searchCatastoDocuments/);
  assert.match(archiveWorkspace, /downloadSelectedCatastoDocumentsZipBlob/);
  assert.match(archiveWorkspace, /getCatastoComuni/);
  assert.match(archiveWorkspace, /cancelElaborazioneBatch/);
  assert.match(archiveWorkspace, /retryFailedElaborazioneBatch/);
  assert.match(documentDetailPage, /CatastoDocumentDetailWorkspace/);
  assert.match(read("src/components/catasto/document-detail-workspace.tsx"), /downloadCatastoDocumentBlob/);
  assert.match(read("src/components/catasto/document-detail-workspace.tsx"), /iframe/);
});

test("shared ui components exist for redesign system", () => {
  assert.match(read("src/components/ui/avatar.tsx"), /getInitials/);
  assert.match(read("src/components/ui/permission-badge.tsx"), /R\+W/);
  assert.match(read("src/components/ui/source-tag.tsx"), /font-mono/);
  assert.match(read("src/components/ui/metric-card.tsx"), /text-2xl font-medium/);
  assert.match(read("src/components/ui/sync-button.tsx"), /Sincronizza ora/);
});

test("users page uses data table and detail links", () => {
  const usersPage = read("src/app/nas-control/users/page.tsx");

  assert.match(usersPage, /DataTable/);
  assert.match(usersPage, /Cartelle accessibili/);
  assert.match(usersPage, /Permesso massimo/);
  assert.match(usersPage, /Apri pagina completa/);
  assert.match(usersPage, /UserDetailPanel/);
  assert.match(usersPage, /selectedUserId/);
});

test("shares page uses cards and share detail route", () => {
  const sharesPage = read("src/app/nas-control/shares/page.tsx");

  assert.match(sharesPage, /Cartelle condivise/);
  assert.match(sharesPage, /deny/);
  assert.match(sharesPage, /\/nas-control\/shares\/\$\{share\.id\}/);
  assert.match(sharesPage, /ShareDetailPanel/);
  assert.match(sharesPage, /Apri pagina completa/);
});

test("reviews and sync pages expose redesigned administrative views", () => {
  const reviewsPage = read("src/app/nas-control/reviews/page.tsx");
  const syncPage = read("src/app/nas-control/sync/page.tsx");

  assert.match(reviewsPage, /Review NAS/);
  assert.match(reviewsPage, /In attesa/);
  assert.match(reviewsPage, /Approvate/);
  assert.match(syncPage, /Sincronizzazione/);
  assert.match(syncPage, /Stato connector/);
  assert.match(syncPage, /Storico snapshot/);
  assert.match(syncPage, /SyncButton/);
});

test("effective permissions page keeps preview and persistent table", () => {
  const permissionsPage = read("src/app/nas-control/effective-permissions/page.tsx");

  assert.match(permissionsPage, /Permessi effettivi/);
  assert.match(permissionsPage, /Preview guidata/);
  assert.match(permissionsPage, /calculatePermissionPreview/);
  assert.match(permissionsPage, /groupsInput/);
});

test("utenze dashboard opens subject and document summaries in modal overlays", () => {
  const dashboardPage = read("src/app/utenze/page.tsx");
  const apiClient = read("src/lib/api.ts");

  assert.match(dashboardPage, /selectedSubject/);
  assert.match(dashboardPage, /<iframe/);
  assert.match(dashboardPage, /Dettaglio soggetto/);
  assert.match(dashboardPage, /Riepilogo documenti/);
  assert.match(dashboardPage, /recent_unclassified/);
  assert.match(dashboardPage, /(getAnagraficaDocumentSummary|getUtenzeDocumentSummary)/);
  assert.match(dashboardPage, /onClick=\{\(\) => setSelectedSubject\(subject\)\}/);
  assert.match(dashboardPage, /onClick=\{\(\) => void handleOpenDocumentSummary\(\)\}/);
  assert.match(apiClient, /export async function getAnagraficaDocumentSummary/);
  assert.match(apiClient, /export const getUtenzeDocumentSummary/);
});

test("utenze subject detail exposes quick visura action wired to elaborazioni runtime", () => {
  const subjectDetailPage = read("src/app/utenze/[id]/page.tsx");
  const apiClient = read("src/lib/api.ts");

  assert.match(subjectDetailPage, /Visura per soggetto/);
  assert.match(subjectDetailPage, /handleRequestSubjectVisura/);
  assert.match(subjectDetailPage, /createElaborazioneRichiesta/);
  assert.match(subjectDetailPage, /search_mode: "soggetto"/);
  assert.match(subjectDetailPage, /window\.open\(`\/elaborazioni\/batches\/\$\{subjectVisuraResult\.id\}`/);
  assert.match(apiClient, /export async function createElaborazioneRichiesta/);
});

test("utenze import page exposes bulk import progress feedback", () => {
  const importPage = read("src/app/utenze/import/page.tsx");

  assert.match(importPage, /Aggiornamento utenze da NAS/);
  assert.match(importPage, /activeBulkJob/);
  assert.match(importPage, /bulkJobProgress/);
  assert.match(importPage, /bulkTrackingJobId/);
  assert.match(importPage, /setInterval/);
  assert.match(importPage, /completed_items/);
  assert.match(importPage, /running_items/);
  assert.match(importPage, /failed_items/);
  assert.match(importPage, /Storico aggiornamenti massivi/);
});

test("catasto anagrafica bulk export normalizes foglio+sezione and exposes ruolo/cnc before note", () => {
  const panel = read("src/components/catasto/anagrafica/AnagraficaBulkPanel.tsx");

  assert.match(panel, /const FOGLIO_WITH_SEZIONE_RE =/);
  assert.match(panel, /function normalizeFoglioSezioneInput/);
  assert.match(panel, /stato_ruolo: m\?\.stato_ruolo \?\? ""/);
  assert.match(panel, /stato_cnc: m\?\.stato_cnc \?\? ""/);
  assert.match(panel, /deceduto: intestatario\.deceduto \? "si" : "",\s+note: m\?\.note \?\? ""/s);
  assert.match(panel, /rows\.push\(\{ \.\.\.base, \.\.\.emptyInt, note: m\?\.note \?\? "" \}\)/);
});

test("catasto particelle page exposes solo a ruolo toggle", () => {
  const particellePage = read("src/app/catasto/particelle/page.tsx");
  const catastoApi = read("src/lib/api/catasto.ts");

  assert.match(particellePage, /Visualizza solo particelle con anagrafica/);
  assert.match(particellePage, /Solo particelle con anagrafica/);
  assert.match(particellePage, /la vedi comunque anche se manca l&apos;anagrafica/);
  assert.match(particellePage, /Senza anagrafica/);
  assert.match(particellePage, /Particella trovata, ma senza anagrafica collegata/);
  assert.match(particellePage, /soloConAnagrafica: true/);
  assert.match(particellePage, /soloConAnagrafica: nextFilters\.soloConAnagrafica/);
  assert.match(particellePage, /Visualizza solo particelle a ruolo/);
  assert.match(particellePage, /Solo particelle a ruolo/);
  assert.match(particellePage, /anno piu recente, usa automaticamente l&apos;anno precedente/);
  assert.match(particellePage, /verifica che l'archivio Ruolo sia stato importato e collegato al Catasto/);
  assert.match(particellePage, /tracking-\[0\.16em\] text-\[#52715d\]/);
  assert.match(particellePage, /soloARuolo: false/);
  assert.match(particellePage, /soloARuolo: nextFilters\.soloARuolo/);
  assert.match(particellePage, /void applyFilters\(nextFilters\)/);
  assert.match(particellePage, /\/\^\[A-Z0-9\]\{16\}\$\/i\.test\(trimmed\)/);
  assert.match(particellePage, /\/\^\\d\{11\}\$\/\.test\(trimmed\)/);
  assert.match(particellePage, /CF\/P\.IVA \(es\. RSSMRA80A01H501T o 00588230953\) o nome/);
  assert.match(catastoApi, /soloConAnagrafica\?: boolean/);
  assert.match(catastoApi, /query\.set\("solo_con_anagrafica", filters\.soloConAnagrafica \? "true" : "false"\)/);
  assert.match(catastoApi, /soloARuolo\?: boolean/);
  assert.match(catastoApi, /query\.set\("solo_a_ruolo", filters\.soloARuolo \? "true" : "false"\)/);
});

test("utenze detail page keeps preview modal and delete password flow", () => {
  const detailPage = read("src/app/utenze/[id]/page.tsx");
  const apiClient = read("src/lib/api.ts");

  assert.match(detailPage, /Anteprima documento/);
  assert.match(detailPage, /iframe className=/);
  assert.match(detailPage, /Cancellazione documento/);
  assert.match(apiClient, /X-GAIA-Delete-Password/);
  assert.match(detailPage, /cursor-pointer rounded-lg border border-gray-100/);
  assert.match(detailPage, /event\.stopPropagation\(\)/);
  assert.match(apiClient, /(export async function downloadAnagraficaDocumentBlob|export const downloadUtenzeDocumentBlob)/);
});

test("bonifica sync workspace exposes final import report panel", () => {
  const bonificaWorkspace = read("src/components/elaborazioni/bonifica-sync-workspace.tsx");

  assert.match(bonificaWorkspace, /Report finale importazione/);
  assert.match(bonificaWorkspace, /report_summary/);
  assert.match(bonificaWorkspace, /Prime anomalie/);
  assert.match(bonificaWorkspace, /formatDurationSeconds/);
  assert.match(bonificaWorkspace, /Esporta JSON/);
  assert.match(bonificaWorkspace, /Esporta CSV/);
  assert.match(bonificaWorkspace, /buildFinalReportsCsv/);
});

test("operazioni dashboard exposes quick search for vehicles, activities, reports and cases", () => {
  const operazioniDashboard = read("src/app/operazioni/page.tsx");

  assert.match(operazioniDashboard, /useDeferredValue/);
  assert.match(operazioniDashboard, /QuickSearchInput/);
  assert.match(operazioniDashboard, /getVehicles\(\{ search: deferredVehicleSearch, page_size: "5" \}\)/);
  assert.match(operazioniDashboard, /getActivities\(\{ search: deferredActivitySearch, page_size: "5" \}\)/);
  assert.match(operazioniDashboard, /getReports\(\{ search: deferredReportSearch, page_size: "5" \}\)/);
  assert.match(operazioniDashboard, /getCases\(\{ search: deferredCaseSearch, page_size: "5" \}\)/);
  assert.match(operazioniDashboard, /Inserisci almeno 3 caratteri/);
});
