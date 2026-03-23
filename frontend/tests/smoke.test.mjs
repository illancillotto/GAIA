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

test("frontend package exposes core scripts", () => {
  const pkg = JSON.parse(read("package.json"));

  assert.equal(pkg.name, "nas-access-audit-frontend");
  assert.equal(pkg.private, true);
  assert.ok(pkg.scripts.dev);
  assert.ok(pkg.scripts.build);
  assert.ok(pkg.scripts.start);
  assert.ok(pkg.scripts.lint);
});

test("frontend api client defaults to same-origin api base", () => {
  const apiClient = read("src/lib/api.ts");

  assert.match(apiClient, /const DEFAULT_API_BASE_URL = "\/api"/);
});

test("home page gates anonymous users behind login flow", () => {
  const homePage = read("src/app/page.tsx");

  assert.match(homePage, /router\.replace\("\/login"\)/);
  assert.match(homePage, /Verifica sessione/);
  assert.match(homePage, /Vai al login/);
  assert.match(homePage, /Utenti NAS/);
  assert.match(homePage, /Sync Run/);
  assert.match(homePage, /Apri Sync/);
});

test("login page contains real access form", () => {
  const loginPage = read("src/app/login/page.tsx");

  assert.match(loginPage, /Login applicativo/);
  assert.match(loginPage, /backend FastAPI reale/);
  assert.match(loginPage, /Username o email/);
  assert.match(loginPage, /Accedi/);
});

test("home page uses backend session helpers", () => {
  const homePage = read("src/app/page.tsx");

  assert.match(homePage, /getCurrentUser/);
  assert.match(homePage, /getDashboardSummary/);
  assert.match(homePage, /Accedi per caricare i dati reali dal backend/);
  assert.match(homePage, /isCheckingSession/);
});

test("app shell exposes only authenticated navigation labels", () => {
  const shell = read("src/components/layout/app-shell.tsx");

  assert.match(shell, /if \(!currentUser\)/);
  assert.match(shell, /Dashboard/);
  assert.match(shell, /Utenti/);
  assert.match(shell, /Gruppi/);
  assert.match(shell, /Share/);
  assert.match(shell, /Review/);
  assert.match(shell, /Sync/);
  assert.match(shell, /Permessi/);
});

test("frontend contains real backend-driven pages", () => {
  const usersPage = read("src/app/users/page.tsx");
  const groupsPage = read("src/app/groups/page.tsx");
  const sharesPage = read("src/app/shares/page.tsx");
  const reviewsPage = read("src/app/reviews/page.tsx");
  const syncPage = read("src/app/sync/page.tsx");
  const permissionsPage = read("src/app/effective-permissions/page.tsx");

  assert.match(usersPage, /getNasUsers/);
  assert.match(groupsPage, /getNasGroups/);
  assert.match(sharesPage, /getShares/);
  assert.match(reviewsPage, /getReviews/);
  assert.match(syncPage, /getSyncCapabilities/);
  assert.match(syncPage, /getSyncRuns/);
  assert.match(syncPage, /previewSync/);
  assert.match(syncPage, /applySync/);
  assert.match(syncPage, /applyLiveSync/);
  assert.match(syncPage, /auth_mode/);
  assert.match(syncPage, /retry_strategy/);
  assert.match(syncPage, /retry_jitter_enabled/);
  assert.match(syncPage, /Source/);
  assert.match(syncPage, /Refresh/);
  assert.match(syncPage, /Retry/);
  assert.match(syncPage, /jitter/);
  assert.match(permissionsPage, /getEffectivePermissions/);
  assert.match(permissionsPage, /calculatePermissionPreview/);
  assert.match(read("src/components/app/protected-page.tsx"), /router\.replace\("\/login"\)/);
});

test("frontend maps domain ids to readable labels", () => {
  const reviewsPage = read("src/app/reviews/page.tsx");
  const permissionsPage = read("src/app/effective-permissions/page.tsx");

  assert.match(reviewsPage, /useDomainData/);
  assert.match(reviewsPage, /getUserLabel/);
  assert.match(permissionsPage, /useDomainData/);
  assert.match(permissionsPage, /getShareLabel/);
});
