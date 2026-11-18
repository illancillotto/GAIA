import { expect, test } from "@playwright/test";

test.use({ channel: "chromium" });

for (const width of [1440, 390]) {
  test(`Tributi filters all types by year at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.addInitScript(() => localStorage.setItem("gaia.access_token", "year-filter-test"));
    const errors: string[] = [];
    const queries: { path: string; params: Record<string, string> }[] = [];
    page.on("pageerror", (error) => errors.push(error.message));
    await page.route("**/api/**", async (route) => {
      const url = new URL(route.request().url());
      const path = url.pathname;
      let data: unknown = { items: [], total: 0, page: 1, page_size: 25 };
      if (path.endsWith("/auth/me")) data = { id: 1, username: "admin", role: "super_admin", is_active: true, enabled_modules: ["ruolo"] };
      if (path.endsWith("/auth/my-permissions")) data = { sections: [], granted_keys: ["ruolo.tributi.view"] };
      if (/\/tributi\/(avvisi|summary)$/.test(path)) {
        queries.push({ path, params: Object.fromEntries(url.searchParams) });
        const items = ["STEP - Agenzia recupero crediti", "Anno 2021 - avvisi non notificati"].map((label, index) => ({
          id: `notice-${index}`, anno_tributario: 2021, display_name: `Contribuente ${index + 1}`,
          annuality_manager_label: label, payment_status: "unpaid", reminder_enabled: false,
          importo_totale_euro: 50, paid_amount: 0, saldo_amount: 50,
        }));
        data = path.endsWith("/avvisi")
          ? { items, total: 2, page: Number(url.searchParams.get("page")), page_size: 25 }
          : { total_count: 2, total_amount: 100, to_send_count: 2, sent_count: 0, pec_count: 0, pec_amount: 0, raccomandata_count: 0, raccomandata_amount: 0 };
      }
      await route.fulfill({ status: 200, json: data });
    });
    await page.goto("/ruolo/tributi?manager_key=step&q=Rossi&page=3");
    const section = page.locator("section").filter({ has: page.getByText("Elenco tributi", { exact: true }) });
    const year = section.getByRole("textbox", { name: "Anno tributario" });
    await expect(section.getByText("STEP - Agenzia recupero crediti", { exact: true })).toBeVisible();
    await expect(section.getByText("Anno 2021 - avvisi non notificati", { exact: true })).toBeVisible();
    await expect(section.getByRole("button", { name: /^(Fino al 2017|2018-2021|2021|Dal 2022) ·/ })).toHaveCount(0);
    await year.fill("2021");
    await expect(page).toHaveURL(/anno=2021/);
    const filteredUrl = new URL(page.url());
    expect(Object.fromEntries(filteredUrl.searchParams)).toEqual({ q: "Rossi", anno: "2021", page: "1" });
    for (const endpoint of ["avvisi", "summary"]) {
      await expect.poll(() => queries.filter((query) => query.path.endsWith(`/${endpoint}`)).at(-1)?.params.anno).toBe("2021");
    }
    await expect(section.getByRole("checkbox", { name: "Solo non pagati (anche parziali)" })).toBeChecked();
    await page.screenshot({ path: test.info().outputPath("tributi-year-filter.png"), fullPage: true });
    await year.fill("");
    await expect(page).not.toHaveURL(/anno=/);
    for (const endpoint of ["avvisi", "summary"]) {
      await expect.poll(() => queries.filter((query) => query.path.endsWith(`/${endpoint}`)).at(-1)?.params.anno).toBeUndefined();
    }
    expect(queries.length).toBeGreaterThanOrEqual(6);
    expect(queries.every((query) => !("manager_key" in query.params))).toBe(true);
    expect(errors).toEqual([]);
  });
}
