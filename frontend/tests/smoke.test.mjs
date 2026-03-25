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
  assert.match(homePage, /Gestione Apparati Informativi e Accessi/);
  assert.match(homePage, /Seleziona il dominio operativo/);
  assert.match(homePage, /GAIA Catasto/);
  assert.match(homePage, /servizi catastali/);
  assert.match(loginPage, /router\.replace\("\/"\)/);
  assert.match(loginPage, /router\.push\("\/"\)/);
  assert.match(loginPage, /GAIA Catasto/);
  assert.match(loginPage, /home GAIA/);
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
  assert.match(platformSidebar, /Modulo:/);
  assert.match(platformSidebar, /Catasto/);
  assert.match(moduleSidebar, /Sincronizzazione/);
  assert.match(moduleSidebar, /Review accessi/);
  assert.match(topbar, /StatusPill/);
  assert.match(statusPill, /Backend connesso/);
});

test("catasto pages wire api client and realtime workflow", () => {
  const dashboardPage = read("src/app/catasto/page.tsx");
  const settingsPage = read("src/app/catasto/settings/page.tsx");
  const newBatchPage = read("src/app/catasto/new-batch/page.tsx");
  const newSinglePage = read("src/app/catasto/new-single/page.tsx");
  const batchDetailPage = read("src/app/catasto/batches/[id]/page.tsx");
  const documentsPage = read("src/app/catasto/documents/page.tsx");
  const documentDetailPage = read("src/app/catasto/documents/[id]/page.tsx");

  assert.match(dashboardPage, /GAIA Catasto/);
  assert.match(settingsPage, /Credenziali SISTER/);
  assert.match(settingsPage, /testCatastoCredentials/);
  assert.match(settingsPage, /getCatastoCredentialTest/);
  assert.match(settingsPage, /createCatastoCredentialTestWebSocket/);
  assert.match(newBatchPage, /createCatastoBatch/);
  assert.match(newBatchPage, /startCatastoBatch/);
  assert.match(newBatchPage, /Scarica template CSV/);
  assert.match(newSinglePage, /useForm/);
  assert.match(newSinglePage, /createCatastoSingleVisura/);
  assert.match(batchDetailPage, /createCatastoBatchWebSocket/);
  assert.match(batchDetailPage, /cancelCatastoBatch/);
  assert.match(batchDetailPage, /retryFailedCatastoBatch/);
  assert.match(batchDetailPage, /CaptchaDialog/);
  assert.match(batchDetailPage, /fetchCatastoCaptchaImageBlob/);
  assert.match(batchDetailPage, /downloadCatastoBatchZipBlob/);
  assert.match(read("src/app/catasto/batches/page.tsx"), /cancelCatastoBatch/);
  assert.match(read("src/app/catasto/batches/page.tsx"), /retryFailedCatastoBatch/);
  assert.match(documentsPage, /DataTable/);
  assert.match(documentsPage, /searchCatastoDocuments/);
  assert.match(documentsPage, /downloadSelectedCatastoDocumentsZipBlob/);
  assert.match(documentsPage, /getCatastoComuni/);
  assert.match(documentDetailPage, /downloadCatastoDocumentBlob/);
  assert.match(documentDetailPage, /iframe/);
});

test("shared ui components exist for redesign system", () => {
  assert.match(read("src/components/ui/avatar.tsx"), /getInitials/);
  assert.match(read("src/components/ui/permission-badge.tsx"), /R\+W/);
  assert.match(read("src/components/ui/source-tag.tsx"), /font-mono/);
  assert.match(read("src/components/ui/metric-card.tsx"), /text-2xl font-medium/);
  assert.match(read("src/components/ui/sync-button.tsx"), /Sincronizza ora/);
});

test("users page uses data table and detail links", () => {
  const usersPage = read("src/app/accessi/users/page.tsx");
  const userDetailPage = read("src/app/accessi/users/[id]/page.tsx");

  assert.match(usersPage, /DataTable/);
  assert.match(usersPage, /Cartelle accessibili/);
  assert.match(usersPage, /Permesso massimo/);
  assert.match(usersPage, /Apri pagina completa/);
  assert.match(usersPage, /href=\{`\/accessi\/users\/\$\{selectedUserId\}`\}/);
  assert.match(userDetailPage, /Dettaglio utente/);
  assert.match(userDetailPage, /UserDetailPanel/);
});

test("shares page uses cards and share detail route", () => {
  const sharesPage = read("src/app/accessi/shares/page.tsx");
  const shareDetailPage = read("src/app/accessi/shares/[id]/page.tsx");

  assert.match(sharesPage, /Cartelle condivise/);
  assert.match(sharesPage, /deny/);
  assert.match(sharesPage, /\/accessi\/shares\/\$\{share\.id\}/);
  assert.match(shareDetailPage, /Accessi effettivi/);
  assert.match(shareDetailPage, /PermissionBadge/);
});

test("reviews and sync pages expose redesigned administrative views", () => {
  const reviewsPage = read("src/app/accessi/reviews/page.tsx");
  const syncPage = read("src/app/accessi/sync/page.tsx");

  assert.match(reviewsPage, /Review accessi/);
  assert.match(reviewsPage, /In attesa/);
  assert.match(reviewsPage, /Approvate/);
  assert.match(syncPage, /Sincronizzazione/);
  assert.match(syncPage, /Stato connector/);
  assert.match(syncPage, /Storico snapshot/);
  assert.match(syncPage, /SyncButton/);
});

test("effective permissions page keeps preview and persistent table", () => {
  const permissionsPage = read("src/app/accessi/effective-permissions/page.tsx");

  assert.match(permissionsPage, /Permessi persistiti/);
  assert.match(permissionsPage, /Preview guidata/);
  assert.match(permissionsPage, /calculatePermissionPreview/);
  assert.match(permissionsPage, /available-groups/);
});
