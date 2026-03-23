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

  assert.equal(pkg.name, "nas-access-audit-frontend");
  assert.equal(pkg.private, true);
  assert.ok(pkg.scripts.dev);
  assert.ok(pkg.scripts.build);
  assert.ok(pkg.dependencies["@tanstack/react-table"]);
  assert.ok(pkg.devDependencies.tailwindcss);
  assert.ok(pkg.dependencies.clsx);
});

test("frontend api client defaults to same-origin api base", () => {
  const apiClient = read("src/lib/api.ts");

  assert.match(apiClient, /const DEFAULT_API_BASE_URL = "\/api"/);
});

test("dashboard keeps login gate and redesigned dashboard copy", () => {
  const homePage = read("src/app/page.tsx");

  assert.match(homePage, /router\.replace\("\/login"\)/);
  assert.match(homePage, /Controllo centralizzato degli accessi NAS/);
  assert.match(homePage, /review in attesa/);
  assert.match(homePage, /Permessi effettivi recenti/);
});

test("layout includes app shell, sidebar and topbar", () => {
  const shell = read("src/components/layout/app-shell.tsx");
  const sidebar = read("src/components/layout/sidebar.tsx");
  const topbar = read("src/components/layout/topbar.tsx");
  const statusPill = read("src/components/ui/status-pill.tsx");

  assert.match(shell, /Sidebar/);
  assert.match(sidebar, /Consorzio di Bonifica/);
  assert.match(sidebar, /Oristanese — Synology NAS/);
  assert.match(sidebar, /Review accessi/);
  assert.match(topbar, /StatusPill/);
  assert.match(statusPill, /Backend connesso/);
});

test("shared ui components exist for redesign system", () => {
  assert.match(read("src/components/ui/avatar.tsx"), /getInitials/);
  assert.match(read("src/components/ui/permission-badge.tsx"), /R\+W/);
  assert.match(read("src/components/ui/source-tag.tsx"), /font-mono/);
  assert.match(read("src/components/ui/metric-card.tsx"), /text-2xl font-medium/);
  assert.match(read("src/components/ui/sync-button.tsx"), /Sincronizza ora/);
});

test("users page uses data table and detail links", () => {
  const usersPage = read("src/app/users/page.tsx");
  const userDetailPage = read("src/app/users/[id]/page.tsx");

  assert.match(usersPage, /DataTable/);
  assert.match(usersPage, /Cartelle accessibili/);
  assert.match(usersPage, /Permesso massimo/);
  assert.match(usersPage, /\/users\/\$\{row\.original\.id\}/);
  assert.match(userDetailPage, /Permessi effettivi/);
  assert.match(userDetailPage, /SourceTag/);
});

test("shares page uses cards and share detail route", () => {
  const sharesPage = read("src/app/shares/page.tsx");
  const shareDetailPage = read("src/app/shares/[id]/page.tsx");

  assert.match(sharesPage, /Cartelle condivise/);
  assert.match(sharesPage, /deny/);
  assert.match(sharesPage, /\/shares\/\$\{share\.id\}/);
  assert.match(shareDetailPage, /Accessi effettivi/);
  assert.match(shareDetailPage, /PermissionBadge/);
});

test("reviews and sync pages expose redesigned administrative views", () => {
  const reviewsPage = read("src/app/reviews/page.tsx");
  const syncPage = read("src/app/sync/page.tsx");

  assert.match(reviewsPage, /Review accessi/);
  assert.match(reviewsPage, /In attesa/);
  assert.match(reviewsPage, /Approvate/);
  assert.match(syncPage, /Sincronizzazione/);
  assert.match(syncPage, /Stato connector/);
  assert.match(syncPage, /Storico snapshot/);
  assert.match(syncPage, /SyncButton/);
});

test("effective permissions page keeps preview and persistent table", () => {
  const permissionsPage = read("src/app/effective-permissions/page.tsx");

  assert.match(permissionsPage, /Permessi persistiti/);
  assert.match(permissionsPage, /Preview guidata/);
  assert.match(permissionsPage, /calculatePermissionPreview/);
  assert.match(permissionsPage, /available-groups/);
});
