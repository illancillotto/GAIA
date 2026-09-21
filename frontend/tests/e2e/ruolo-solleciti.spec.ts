import { expect, test } from "@playwright/test";

for (const width of [1440, 390]) {
  test(`conferma lotto e conflitto ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.addInitScript(() => localStorage.setItem("gaia.access_token", "solleciti-browser-test"));
    const errors: string[] = [];
    page.on("pageerror", (error) => errors.push(error.message));
    let calls = 0;
    const batch = {
      id: "batch-1", title: "Verifica 2022/2023", status: "review_required",
      items_total: 1, items_generated: 0, items_failed: 0,
      created_at: "2026-09-21T10:00:00Z", generated_at: "2026-09-21T10:00:00Z",
      items: [{ id: "item-1", display_name: "Mario Rossi", codice_fiscale: "RSSMRA80A01H501Z", status: "draft", years_json: [2022, 2023], payload_json: { notice_identity_key: "a".repeat(64) } }],
    };
    await page.route("**/api/**", async (route) => {
      const path = new URL(route.request().url()).pathname;
      let data: unknown = {};
      if (path.endsWith("/auth/me")) data = { id: 1, username: "operatore", role: "admin", is_active: true, enabled_modules: ["ruolo"] };
      if (path.endsWith("/auth/my-permissions")) data = { sections: [], granted_keys: ["ruolo.tributi.view", "ruolo.tributi.manage_status"] };
      if (path.endsWith("/batches")) data = { items: [batch], total: 1, page: 1, page_size: 50 };
      if (path.endsWith("/batch-1")) data = batch;
      if (path.endsWith("/confirm")) {
        expect(route.request().postDataJSON()).toEqual({ batch: true });
        calls += 1;
        if (calls === 1) {
          await route.fulfill({ status: 409, json: { detail: "Revisione obsoleta: rigenerare" } });
          return;
        }
        batch.status = "confirmed";
        data = { review_digest: "b".repeat(64) };
      }
      await route.fulfill({ status: 200, json: data });
    });
    await page.goto("/ruolo/tributi/solleciti?embedded=1");
    await page.getByRole("button", { name: /Verifica 2022/ }).click();
    await expect(page.getByText("Mario Rossi")).toBeVisible();
    await page.getByRole("button", { name: "Conferma lotto" }).click();
    await expect(page.locator("div.rounded-2xl.border-rose-200")).toContainText("Revisione obsoleta");
    await page.getByRole("button", { name: "Conferma lotto" }).click();
    await expect(page.getByText(/Lotto confermato. Digest/)).toBeVisible();
    await expect(page.getByRole("button", { name: "Conferma lotto" })).toHaveCount(0);
    await page.screenshot({ path: `/tmp/gaia-solleciti-${width}.png`, fullPage: true });
    expect(await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth)).toBe(false);
    expect(errors).toEqual([]);
    expect(calls).toBe(2);
  });
}
