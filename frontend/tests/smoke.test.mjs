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

test("home page contains dashboard bootstrap copy", () => {
  const homePage = read("src/app/page.tsx");

  assert.match(homePage, /Controllo centralizzato degli accessi NAS/);
  assert.match(homePage, /API target: \/api/);
  assert.match(homePage, /Utenti NAS/);
});

test("login page contains placeholder access form", () => {
  const loginPage = read("src/app/login/page.tsx");

  assert.match(loginPage, /Placeholder login/);
  assert.match(loginPage, /Username o email/);
  assert.match(loginPage, /Accedi/);
});

test("app shell exposes main navigation labels", () => {
  const shell = read("src/components/layout/app-shell.tsx");

  assert.match(shell, /Dashboard/);
  assert.match(shell, /Login/);
  assert.match(shell, /Snapshot/);
  assert.match(shell, /Review/);
});
