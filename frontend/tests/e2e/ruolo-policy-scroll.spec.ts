import { expect, test } from "@playwright/test";

test.use({ locale: "en-US" });

for (const width of [1440, 390]) {
  test(`active policy cards scroll inside their panel at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.addInitScript(() => localStorage.setItem("gaia.access_token", "policy-scroll-test"));
    const errors: string[] = [];
    page.on("pageerror", (error) => errors.push(error.message));
    await page.route("**/api/**", async (route) => {
      const path = new URL(route.request().url()).pathname;
      let data: unknown = { items: [], total: 0, page: 1, page_size: 25 };
      if (path.endsWith("/auth/me")) data = { id: 1, username: "admin", role: "super_admin", is_active: true, enabled_modules: ["ruolo"] };
      if (path.endsWith("/auth/my-permissions")) data = { sections: [], granted_keys: ["ruolo.tributi.view"] };
      if (path.endsWith("/calculation-policies")) data = {
        items: [2025, 2022, 2024, 2023].map((year) => ({
          id: `policy-${year}`, name: `Regola ${year}`, year_from: year, year_to: year,
          bonario_due_date: `${year}-05-26`, surcharge_from: `${year}-05-27`,
          surcharge_rate_percent: 6, euribor_6m_rate_percent: 0, interest_rate_percent: 0,
          effective_interest_rate_percent: 0, interest_from: null, interest_start_mode: "notification_date",
          is_active: true, only_unnotified: false, euribor_source_url: null,
        })),
      };
      await route.fulfill({ status: 200, json: data });
    });
    await page.goto("/ruolo/tributi");
    const strip = page.getByRole("region", { name: "Regole ruolo attive per anno" });
    await expect(strip.getByRole("article")).toHaveCount(4);
    await expect(strip.getByRole("article").locator(":scope > p:first-child")).toHaveText([
      "Regola 2022", "Regola 2023", "Regola 2024", "Regola 2025",
    ]);
    await expect(page.getByText("4 attive")).toBeVisible();
    expect(await strip.evaluate((element) => element.scrollWidth > element.clientWidth)).toBe(true);
    await strip.scrollIntoViewIfNeeded();
    const manage = page.getByRole("button", { name: "Gestisci regole calcolo" });
    const originalButton = await manage.boundingBox();
    await strip.focus();
    await strip.press("ArrowRight");
    await expect.poll(() => strip.evaluate((element) => element.scrollLeft)).toBeGreaterThan(0);
    const last = strip.getByRole("article").last();
    await last.scrollIntoViewIfNeeded();
    const stripBounds = await strip.boundingBox();
    const lastBounds = await last.boundingBox();
    expect(lastBounds!.x + lastBounds!.width).toBeLessThanOrEqual(stripBounds!.x + stripBounds!.width + 1);
    expect(stripBounds!.x + stripBounds!.width).toBeLessThanOrEqual(width);
    expect((await manage.boundingBox())!.x).toBe(originalButton!.x);
    await manage.click();
    await expect(page.getByText("Scadenza bonaria, maggiorazioni e interessi")).toBeVisible();
    await expect(page.getByText("Scadenza bonaria 26/05/2022", { exact: true })).toBeVisible();
    const dueDate = page.getByRole("textbox", { name: "Scadenza pagamento bonario", exact: true });
    await expect(dueDate).toHaveAttribute("placeholder", "gg/mm/aaaa");
    await dueDate.fill("31/02/2026");
    expect(await dueDate.evaluate((element) => (element as HTMLInputElement).checkValidity())).toBe(false);
    await dueDate.fill("15/11/2026");
    await expect(page.getByLabel("Calendario Scadenza pagamento bonario", { exact: true })).toHaveValue("2026-11-15");
    await page.getByLabel("Calendario Scadenza pagamento bonario", { exact: true }).fill("2026-07-31");
    await expect(dueDate).toHaveValue("31/07/2026");
    await page.getByRole("textbox", { name: "Fallback/minimo interessi", exact: true }).fill("10/08/2026");
    await page.getByPlaceholder("Nome, es. Ruoli morosi 2024").fill("Regola data italiana");
    await page.getByPlaceholder("Anno da", { exact: true }).fill("2026");
    await page.getByPlaceholder("Anno a", { exact: true }).fill("2026");
    const saved = page.waitForRequest((request) => request.url().endsWith("/calculation-policies") && request.method() === "POST");
    await page.getByRole("button", { name: "Aggiungi", exact: true }).click();
    expect((await saved).postDataJSON()).toMatchObject({ bonario_due_date: "2026-07-31", interest_from: "2026-08-10" });
    expect(errors).toEqual([]);
  });
}
