import { expect, test } from "@playwright/test";

for (const width of [1440, 390]) {
  test(`overlapping 2021 manager handles save errors and wizard selection at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.addInitScript(() => localStorage.setItem("gaia.access_token", "overlap-test"));
    const errors: string[] = [];
    const candidateYears: string[] = [];
    page.on("pageerror", (error) => errors.push(error.message));
    const managers = [
      { id: "step", manager_key: "step", manager_label: "STEP", year_from: 2018, year_to: 2021, calculation_policy: "external_recovery", is_active: true },
      { id: "gaia", manager_key: "gaia", manager_label: "Consorzio/GAIA", year_from: 2022, year_to: null, calculation_policy: "internal_gaia", is_active: true },
    ];
    let failSave = true;
    await page.route("**/api/**", async (route) => {
      const request = route.request();
      const url = new URL(request.url());
      let data: unknown = { items: [], total: 0, page: 1, page_size: 25 };
      if (url.pathname.endsWith("/auth/me")) data = { id: 1, username: "admin", role: "super_admin", is_active: true, enabled_modules: ["ruolo"] };
      if (url.pathname.endsWith("/auth/my-permissions")) data = { sections: [], granted_keys: ["ruolo.tributi.view", "ruolo.tributi.manage_status"] };
      if (url.pathname.endsWith("/year-managers")) {
        if (request.method() === "POST") {
          expect(request.postDataJSON()).toMatchObject({
            manager_key: "avvisi_2021", year_from: 2021, year_to: 2021,
            calculation_policy: "internal_gaia", is_active: true,
          });
          if (failSave) {
            await route.fulfill({ status: 422, json: { detail: "Salvataggio di prova non disponibile" } });
            return;
          }
          const manager = { id: "avvisi-2021", ...request.postDataJSON() };
          managers.push(manager);
          data = manager;
        } else data = { items: managers };
      }
      if (url.pathname.endsWith("/solleciti/candidates")) candidateYears.push(url.searchParams.get("anno_from") ?? "");
      await route.fulfill({ status: 200, json: data });
    });

    await page.goto("/ruolo/tributi");
    await page.getByRole("button", { name: "Gestisci regole", exact: true }).click();
    await expect(page.getByText(/I range possono sovrapporsi/)).toBeVisible();
    await page.getByPlaceholder("Descrizione, es. STEP").fill("Avvisi 2021");
    await page.getByPlaceholder("Chiave, es. step").fill("avvisi_2021");
    await page.getByPlaceholder("Anno da, vuoto = -inf").fill("2021");
    await page.getByPlaceholder("Anno a, vuoto = aperto").fill("2021");
    await page.getByPlaceholder("Policy calcolo").fill("internal_gaia");
    await page.getByRole("button", { name: "Aggiungi", exact: true }).click();
    await expect(page.getByText("Salvataggio di prova non disponibile", { exact: true }).last()).toBeVisible();
    await expect(page.getByPlaceholder("Chiave, es. step")).toHaveValue("avvisi_2021");
    failSave = false;
    await page.getByRole("button", { name: "Aggiungi", exact: true }).click();
    await expect(page.getByText("Gestore annualita creato.").last()).toBeVisible();
    await expect(page.getByText("2018-2021", { exact: true })).toBeVisible();
    await page.getByRole("button", { name: "Chiudi", exact: true }).click();
    await page.getByRole("button", { name: "2021 · Avvisi 2021", exact: true }).click();
    await expect(page).toHaveURL(/manager_key=avvisi_2021/);
    await page.getByRole("button", { name: "Wizard solleciti", exact: true }).click();
    const year = page.getByRole("button", { name: "2021", exact: true });
    await expect(year).toHaveAttribute("aria-pressed", "false");
    await year.click();
    await expect(year).toHaveAttribute("aria-pressed", "true");
    await expect.poll(() => candidateYears.includes("2021")).toBe(true);
    expect(errors).toEqual([]);
  });
}
