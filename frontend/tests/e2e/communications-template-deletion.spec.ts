import { expect, test } from "@playwright/test";

for (const width of [1440, 390]) {
  test(`eliminazione template con conferma, annullamento ed errore ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.addInitScript(() => localStorage.setItem("gaia.access_token", "synthetic-template-test"));
    const errors: string[] = [];
    page.on("pageerror", (error) => errors.push(error.message));
    const template = { id: "synthetic-v1", code: "synthetic", name: "Sollecito sintetico", channel: "pec", module: "ruolo", subject: "Avviso {{numero_avviso}}", body: "Testo sintetico", version: 1, status: "draft" };
    let templates = [template, { ...template, id: "synthetic-v2", version: 2, status: "approved" }];
    let deletes = 0;
    await page.route("**/api/**", async (route) => {
      const path = new URL(route.request().url()).pathname;
      let data: unknown = [];
      if (path.endsWith("/auth/me")) data = { id: 1, username: "synthetic", role: "admin", is_active: true, enabled_modules: ["ruolo"] };
      else if (path.endsWith("/auth/my-permissions")) data = { sections: [], granted_keys: ["ruolo.tributi.view", "ruolo.tributi.manage_status"] };
      else if (path.endsWith("/admin/monitor")) data = { paused: true, transport_enabled: false, worker_seen_at: null, queues: {}, uncertain: 0, unmatched_receipts: 0 };
      else if (path.endsWith("/admin/templates")) data = templates;
      else if (route.request().method() === "DELETE") {
        expect(path).toMatch(/\/communications\/templates\/synthetic-v1$/);
        expect(route.request().postDataJSON()).toEqual({ confirmed: true });
        deletes++;
        if (deletes === 1) {
          await route.fulfill({ status: 409, json: { detail: "Audit temporaneamente indisponibile" } });
          return;
        }
        templates = templates.filter((value) => value.id !== template.id);
        data = { ...template, status: "deleted" };
      }
      await route.fulfill({ status: 200, json: data });
    });
    await page.goto("/gaia/communications?embedded=1");
    const panel = page.locator("section").filter({ has: page.getByRole("heading", { name: "Template versionati", exact: true }) });
    const first = page.getByRole("button", { name: "Elimina Sollecito sintetico, pec, versione 1", exact: true });
    const second = page.getByRole("button", { name: "Elimina Sollecito sintetico, pec, versione 2", exact: true });
    await expect(first).toBeVisible();
    await expect(second).toBeVisible();
    page.once("dialog", async (dialog) => {
      expect(dialog.type()).toBe("confirm");
      expect(dialog.message()).toContain("codice synthetic, versione 1");
      expect(dialog.message()).toContain("I messaggi già creati e lo storico resteranno conservati");
      await dialog.dismiss();
    });
    await first.click();
    expect(deletes).toBe(0);
    await expect(first).toBeEnabled();
    page.once("dialog", (dialog) => dialog.accept());
    await first.click();
    await expect(panel.getByRole("alert")).toContainText("Audit temporaneamente indisponibile");
    await expect(first).toBeEnabled();
    await expect(second).toBeEnabled();
    page.once("dialog", (dialog) => dialog.accept());
    await first.click();
    await expect(first).toHaveCount(0);
    await expect(second).toBeEnabled();
    await expect(panel.getByRole("alert")).toHaveCount(0);
    expect(deletes).toBe(2);
    expect(errors).toEqual([]);
    await page.screenshot({ path: `/tmp/gaia-template-delete-20261107/template-deleted-${width}.png`, fullPage: true });
  });
}
