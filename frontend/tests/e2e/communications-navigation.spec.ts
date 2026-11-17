import { expect, test, type Page } from "@playwright/test";

async function expectRuoloNavigation(page: Page, mobile: boolean) {
  if (mobile) await page.getByRole("button", { name: "Apri navigazione" }).click();
  const sidebar = page.locator("aside:visible");
  await expect(sidebar.getByRole("button", { name: "Ruolo", exact: true })).toBeVisible();
  await expect(sidebar.getByRole("link", { name: "Invio solleciti", exact: true })).toHaveAttribute("href", "/ruolo/tributi/solleciti");
  await expect(sidebar.getByRole("button", { name: "NAS Control", exact: true })).toHaveCount(0);
  if (mobile) await sidebar.getByRole("button", { name: "Chiudi navigazione" }).click();
  else await expect(page.getByRole("link", { name: "Ruolo", exact: true })).toHaveClass(/bg-\[#EAF3E8\]/);
}

for (const channel of ["pec", "email"]) for (const width of [1440, 390]) {
  test(`Amministrazione mantiene Ruolo da ${channel}, ${width}px e dopo ricaricamento`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.addInitScript(() => localStorage.setItem("gaia.access_token", "synthetic-navigation"));
    const errors: string[] = [];
    page.on("pageerror", error => errors.push(error.message));
    await page.route("**/api/**", async route => {
      const path = new URL(route.request().url()).pathname;
      let data: unknown = [];
      if (path.endsWith("/auth/me")) data = { id: 1, username: "synthetic", role: "admin", is_active: true, enabled_modules: ["accessi", "ruolo"] };
      else if (path.endsWith("/auth/my-permissions")) data = { sections: [], granted_keys: ["ruolo.tributi.view", "ruolo.tributi.manage_status"] };
      else if (path.endsWith("/candidates")) data = { items: [], total: 0 };
      else if (path.endsWith("/admin/monitor")) data = { paused: true, transport_enabled: false, worker_seen_at: null, queues: {}, uncertain: 0, unmatched_receipts: 0 };
      await route.fulfill({ status: 200, json: data });
    });
    await page.goto(`/ruolo/tributi/solleciti/${channel}`);
    await expectRuoloNavigation(page, width < 768);
    await page.getByRole("link", { name: "Amministrazione comunicazioni" }).click();
    await expect(page).toHaveURL(/\/gaia\/communications$/);
    await expect(page.getByRole("heading", { name: "GAIA Communications", exact: true, level: 2 })).toBeVisible();
    await expectRuoloNavigation(page, width < 768);
    await page.reload();
    await expect(page.getByRole("heading", { name: "GAIA Communications", exact: true, level: 2 })).toBeVisible();
    await expectRuoloNavigation(page, width < 768);
    await page.locator('main').getByRole("link", { name: "Invio solleciti", exact: true }).click();
    await expect(page).toHaveURL(/\/ruolo\/tributi\/solleciti\/pec$/);
    await expectRuoloNavigation(page, width < 768);
    expect(errors).toEqual([]);
  });
}
