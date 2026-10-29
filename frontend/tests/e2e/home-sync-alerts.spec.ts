import { expect, test } from "@playwright/test";

for (const width of [1440, 390]) {
  test(`toast sincronizzazioni nella home admin a ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    const errors: string[] = [];
    page.on("pageerror", (error) => errors.push(error.message));
    await page.addInitScript(() => localStorage.setItem("gaia.access_token", "home-alerts-e2e"));
    let alerts = [{ id: "presenze:credential:1:1", service: "Presenze INAZ", message: "Credenziale disabilitata." }];
    let reads = 0;
    await page.route("**/api/**", async (route) => {
      const path = new URL(route.request().url()).pathname;
      let body: unknown = [];
      if (path.endsWith("/auth/me")) body = { id: 1, username: "admin", role: "admin", is_active: true, enabled_modules: [] };
      else if (path.endsWith("/auth/my-permissions")) body = { sections: [], granted_keys: [] };
      else if (path.endsWith("/sync-alerts")) { reads += 1; body = alerts; }
      else if (path.includes("notifications")) body = { items: [], unread_count: 0 };
      await route.fulfill({ status: 200, json: body, headers: {
        "access-control-allow-origin": "*", "access-control-allow-headers": "authorization,content-type",
      } });
    });
    await page.routeWebSocket("**/ws/**", (socket) => socket.close());
    await page.clock.install();
    await page.goto("/");
    const toast = page.getByRole("alert", { name: "Avvisi sincronizzazioni" });
    await expect(toast).toBeVisible();
    await expect(toast).toContainText("Presenze INAZ");
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    const box = await toast.boundingBox();
    expect(box!.x).toBeGreaterThanOrEqual(0);
    expect(box!.x + box!.width).toBeLessThanOrEqual(width);
    const assistant = await page.getByRole("button", { name: "Apri assistente GAIA" }).boundingBox();
    expect(box!.y + box!.height).toBeLessThanOrEqual(assistant!.y);
    await page.screenshot({ path: `/tmp/gaia-admin-sync-alerts/home-toast-${width}.png` });
    await toast.getByRole("button", { name: "Chiudi avvisi sincronizzazioni" }).click();
    await expect(toast).toHaveCount(0);
    await page.clock.fastForward(30000);
    await expect.poll(() => reads).toBeGreaterThanOrEqual(2);
    await expect(toast).toHaveCount(0);
    alerts = [];
    await page.clock.fastForward(30000);
    await expect.poll(() => reads).toBeGreaterThanOrEqual(3);
    alerts = [{ id: "capacitas:job:42:failed", service: "Capacitas particelle", message: "Esecuzione interrotta." }];
    await page.clock.fastForward(30000);
    await expect(toast).toBeVisible();
    await expect(toast).toContainText("Capacitas particelle");
    expect(errors).toEqual([]);
  });
}

test("la home operatore non legge né visualizza gli allarmi amministrativi", async ({ page }) => {
  let reads = 0;
  await page.addInitScript(() => localStorage.setItem("gaia.access_token", "home-operator-e2e"));
  await page.route("**/api/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    let body: unknown = [];
    if (path.endsWith("/auth/me")) body = { id: 2, username: "operator", role: "operator", is_active: true, enabled_modules: [] };
    else if (path.endsWith("/auth/my-permissions")) body = { sections: [], granted_keys: [] };
    else if (path.endsWith("/sync-alerts")) reads += 1;
    else if (path.includes("notifications")) body = { items: [], unread_count: 0 };
    await route.fulfill({ status: 200, json: body, headers: {
      "access-control-allow-origin": "*", "access-control-allow-headers": "authorization,content-type",
    } });
  });
  await page.routeWebSocket("**/ws/**", (socket) => socket.close());
  await page.clock.install();
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "GAIA", exact: true })).toBeVisible();
  await page.clock.fastForward(60000);
  expect(reads).toBe(0);
  await expect(page.getByRole("alert", { name: "Avvisi sincronizzazioni" })).toHaveCount(0);
});
