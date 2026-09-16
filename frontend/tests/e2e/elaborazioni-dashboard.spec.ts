import { expect, test } from "@playwright/test";

const started = "2026-09-15T08:00:00Z";
const job = { id: 1, status: "completed", created_at: started, started_at: started, completed_at: started,
  result_json: { notices_synced: 12345, processed_subjects: 42 } };

for (const width of [1440, 390]) {
  test(`dashboard sync a ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    const errors: string[] = [];
    page.on("pageerror", (error) => errors.push(error.message));
    await page.addInitScript(() => localStorage.setItem("gaia.access_token", "dashboard-e2e"));
    await page.route("**/api/**", async (route) => {
      const path = new URL(route.request().url()).pathname;
      let body: unknown = [];
      if (path.endsWith("/auth/me")) body = { id: 1, username: "admin", role: "super_admin", is_active: true, enabled_modules: ["catasto", "elaborazioni"], module_catasto: true };
      else if (path.endsWith("/auth/my-permissions")) body = { sections: [], granted_keys: [] };
      else if (path.includes("notifications")) body = { items: [], unread_count: 0 };
      else if (path.endsWith("/incass/avvisi/jobs")) body = [job, { ...job, id: 2, created_at: "2026-09-01", result_json: { notices_synced: 99999 } }];
      else if (path.endsWith("/bonifica/sync/status")) body = { entities: {
        mezzi: { entity: "Mezzi", status: "running", last_started_at: started, records_synced: 120, records_errors: 0 },
        utenti: { entity: "Utenti", status: "failed", error_detail: "Errore del flusso utenti", records_errors: 3 },
      } };
      else if (path.includes("mobile-gateway-sync")) body = { sync_enabled: true, gateway_configured: true, token_configured: true, last_run: null };
      else if (path.endsWith("/ruolo-autosync/status")) body = { config: { enabled: true, batch_size: 10 }, last_batch: null, running_batch: null };
      else if (path.includes("anpr/summary")) body = { recent_runs: [], calls_today: 0, effective_daily_limit: 100 };
      else if (path.endsWith("/autodoc-sync/status")) body = null;
      else if (path.endsWith("/presenze/sync/jobs")) body = { items: [] };
      else if (path.endsWith("/ade-wfs/runs/latest")) return route.fulfill({ status: 404, json: { detail: "Nessun run" } });
      else if (path === "/api/sync/jobs") return route.fulfill({ status: 503, json: { detail: "Servizio temporaneamente non disponibile" } });
      await route.fulfill({ status: 200, json: body });
    });
    await page.routeWebSocket("**/ws/**", (socket) => socket.close());
    await page.goto("/elaborazioni");
    await expect(page.getByRole("button", { name: "Aggiorna ora" })).toBeEnabled();
    const catalog = page.getByRole("region", { name: "Servizi di sincronizzazione" });
    await expect(catalog.getByRole("article")).toHaveCount(15);
    const incass = page.getByRole("article", { name: "Capacitas inCass", exact: true });
    await expect(incass).toContainText("Completato");
    const sizes = await catalog.getByRole("article").evaluateAll((cards) => cards.map((card) => ({ width: card.getBoundingClientRect().width, height: card.getBoundingClientRect().height })));
    expect(Math.max(...sizes.map((size) => size.height)) - Math.min(...sizes.map((size) => size.height))).toBeLessThan(2);
    expect(Math.max(...sizes.map((size) => size.width)) - Math.min(...sizes.map((size) => size.width))).toBeLessThan(2);
    await expect(page.getByRole("article", { name: "NAS e directory", exact: true })).toContainText("Dati non disponibili");
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    await page.screenshot({ path: `/tmp/gaia-dashboard-${width}.png`, fullPage: true });
    await page.getByRole("searchbox").fill("inCass");
    await expect(catalog.getByRole("article")).toHaveCount(1);
    await incass.getByRole("button", { name: "Vedi dettagli" }).click();
    const detail = page.getByRole("dialog", { name: "Capacitas inCass" });
    await expect(detail).toBeVisible();
    await expect(detail).toContainText("12.345");
    await expect(detail).not.toContainText("99.999");
    await expect(detail.getByText("Ultima sincronizzazione", { exact: true })).toHaveCount(1);
    await expect(detail.getByRole("button", { name: "Chiudi" })).toBeFocused();
    await page.keyboard.press("Shift+Tab");
    await expect(detail.getByRole("button", { name: "Apri monitor" })).toBeFocused();
    await page.screenshot({ path: `/tmp/gaia-dashboard-details-${width}.png` });
    await page.keyboard.press("Escape");
    await expect(detail).not.toBeVisible();
    await expect(incass.getByRole("button", { name: "Vedi dettagli" })).toBeFocused();
    await expect(page.getByRole("searchbox")).toHaveValue("inCass");
    await incass.getByRole("button", { name: "Apri monitor" }).click();
    await expect(detail.getByRole("button", { name: "Avvisi pagamenti" })).toBeVisible();
    const monitorBounds = await detail.boundingBox();
    expect(monitorBounds!.width).toBeGreaterThanOrEqual(Math.min(width - 16, 1600));
    expect(monitorBounds!.height).toBeGreaterThanOrEqual(900 * 0.96);
    await expect(page).toHaveURL(/\/elaborazioni$/);
    await detail.getByRole("button", { name: "Chiudi", exact: true }).click();
    await page.getByRole("button", { name: "Pianificazioni automatiche", exact: true }).click();
    await expect(page.getByRole("dialog", { name: "Pianificazioni automatiche" })).toBeVisible();
    await page.keyboard.press("Escape");
    await page.getByRole("searchbox").fill("");
    await page.getByRole("button", { name: /Da verificare/ }).click();
    await expect(catalog.getByRole("article")).toHaveCount(2);
    await page.getByRole("article", { name: "WhiteCompany", exact: true }).getByRole("button", { name: "Vedi dettagli" }).click();
    const flows = page.getByRole("dialog", { name: "WhiteCompany" });
    await expect(flows).toContainText("Mezzi");
    await expect(flows).toContainText("Errore del flusso utenti");
    await page.keyboard.press("Escape");
    expect(errors).toEqual([]);
  });
}
