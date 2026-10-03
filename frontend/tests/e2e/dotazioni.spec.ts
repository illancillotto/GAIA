import { expect, test } from "@playwright/test";
import type { Asset, Custody } from "../../src/features/dotazioni/types";

test("custody lifecycle and stable QR route preserve history", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  const permissions = ["dotazioni.view", "dotazioni.manage", "dotazioni.assign", "dotazioni.custody", "dotazioni.history"];
  const history: Custody[] = [];
  const operations: string[] = [];
  let conflict = true;
  const asset: Asset = {
    id: "da802a1f-4972-4393-917d-af1a8085ea16", asset_code: "TEL-E2E-01", asset_type: "phone",
    name: "Telefono sintetico", description: null, brand: "Samsung", model: null, serial_number: null,
    imei: null, phone_number: null, mac_address: null, notes: null, status: "available",
    effective_status: "available", is_active: true, assigned_org_unit_id: null,
    assigned_org_unit_name: "Squadra sintetica", network_device_id: null, vehicle_id: null,
    plate_number: null, vehicle_status: null, current_custody: null,
  };
  await page.addInitScript(() => localStorage.setItem("gaia.access_token", "synthetic-dotazioni-session"));
  await page.route("**/api/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path.startsWith("/api/dotazioni/")) {
      expect(route.request().headers().authorization).toBe("Bearer synthetic-dotazioni-session");
    }
    if (/\/(take|return|transfer)$/.test(path)) {
      const action = path.split("/").at(-1)!;
      operations.push(action);
      if (conflict) {
        conflict = false;
        await route.fulfill({ status: 409, json: { detail: "Asset già in custodia" } });
        return;
      }
      if (asset.current_custody) asset.current_custody.returned_at = "2026-10-01T14:00:00Z";
      if (action === "return") asset.current_custody = null;
      else {
        const holder = action === "take" ? 7 : route.request().postDataJSON().holder_user_id;
        const custody: Custody = {
          id: `custody-${history.length}`, holder_user_id: holder,
          holder_name: holder === 7 ? "Mario Rossi" : "Antonio Piras",
          taken_at: action === "take" ? "2026-10-01T07:15:00Z" : "2026-10-01T14:00:00Z", returned_at: null,
          handover_from_user_id: action === "transfer" ? 7 : null, notes: null, return_notes: null,
          handover_from_name: action === "transfer" ? "Mario Rossi" : null,
        };
        history.push(custody);
        asset.current_custody = custody;
      }
      asset.effective_status = asset.current_custody ? "in_use" : "available";
      await route.fulfill({ json: asset });
      return;
    }
    const json = path === "/api/auth/me"
      ? { id: 7, username: "synthetic-dotazioni", role: "admin", is_active: true, enabled_modules: ["dotazioni"] }
      : path === "/api/auth/my-permissions" ? { granted_keys: permissions }
      : path.endsWith("/lookups") ? { users: [{ id: 7, name: "Mario Rossi" }, { id: 8, name: "Antonio Piras" }], org_units: [], network_devices: [], vehicles: [], permissions }
      : path.endsWith("/custody-history") ? { items: history, total: history.length }
      : path.startsWith("/api/dotazioni/assets/") ? asset : {};
    await route.fulfill({ json });
  });
  await page.goto(`/dotazioni/assets/${asset.id}`);
  await expect(page.getByRole("heading", { name: "TEL-E2E-01 · Telefono sintetico" })).toBeVisible();
  await expect(page.getByText("Bene del Consorzio · Disponibile")).toBeVisible();
  await expect(page.getByText("Unità / squadra: Squadra sintetica")).toBeVisible();
  await expect(page.getByText("Samsung", { exact: true })).not.toBeVisible();
  await page.locator("summary").filter({ hasText: "Caratteristiche e note" }).focus();
  await page.keyboard.press("Enter");
  await expect(page.getByText("Samsung", { exact: true })).toBeVisible();
  await page.keyboard.press("Enter");
  await page.getByRole("button", { name: "Prendi in consegna" }).focus();
  await page.keyboard.press("Enter");
  await expect(page.getByRole("alert").filter({ hasText: "Asset già in custodia" })).toBeVisible();
  await page.getByRole("button", { name: "Prendi in consegna" }).click();
  await expect(page.getByText("Custode corrente: Mario Rossi")).toBeVisible();
  await expect(page.getByText("Dalle: 01/10/2026, 09:15 (ora italiana)")).toBeVisible();
  await page.getByLabel("Operatore destinatario").selectOption("8");
  await page.getByRole("button", { name: "Passa a…" }).click();
  await expect(page.getByText("Custode corrente: Antonio Piras")).toBeVisible();
  await page.getByRole("button", { name: "Restituisci" }).click();
  await expect(page.getByText("Custode corrente: Nessuno")).toBeVisible();
  await expect(page.getByText("2 custodie · pagina 1")).toBeVisible();
  await expect(page.getByRole("columnheader", { name: "Passaggio da", exact: true })).toBeVisible();
  await page.getByRole("region", { name: "Storico custodie" }).focus();
  await expect(page.getByRole("region", { name: "Storico custodie" })).toBeFocused();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({ path: "/tmp/dotazioni-ux-mobile.png", fullPage: true });
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.screenshot({ path: "/tmp/dotazioni-ux-desktop.png", fullPage: true });
  await page.getByRole("link", { name: "Link stabile per QR" }).click();
  await expect(page).toHaveURL(/\/dotazioni\/by-code\/TEL-E2E-01$/);
  await expect(page.getByRole("heading", { name: "TEL-E2E-01 · Telefono sintetico" })).toBeVisible();
  expect(operations).toEqual(["take", "take", "transfer", "return"]);
  expect(history.every((custody) => custody.returned_at !== null)).toBe(true);
  expect(history[1].handover_from_user_id).toBe(7);
});

test("missing section permission blocks custody and asset reads", async ({ page }) => {
  const domainRequests: string[] = [];
  await page.addInitScript(() => localStorage.setItem("gaia.access_token", "synthetic-denied-session"));
  await page.route("**/api/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path.startsWith("/api/dotazioni/")) domainRequests.push(path);
    const json = path === "/api/auth/me"
      ? { id: 7, username: "denied", role: "viewer", is_active: true, enabled_modules: ["dotazioni"] }
      : path === "/api/auth/my-permissions" ? { granted_keys: [] } : {};
    await route.fulfill({ json });
  });
  await page.goto("/dotazioni/assets/da802a1f-4972-4393-917d-af1a8085ea16");
  await expect(page.getByText("Accesso non autorizzato")).toBeVisible();
  await expect(page.getByRole("button", { name: "Prendi in consegna" })).toHaveCount(0);
  expect(domainRequests).toEqual([]);
});
