import { expect, test } from "@playwright/test";
import { readFileSync } from "node:fs";
import { join } from "node:path";

const previewPdf = readFileSync(join(__dirname, "../fixtures/notice-preview.pdf"));
test.use({ channel: "chromium" });

for (const width of [1440, 390]) {
  test(`Tributi opens private 2022 draft preview at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.addInitScript(() => {
      if (window.top === window) localStorage.setItem("gaia.access_token", "draft-preview-test");
    });
    const errors: string[] = [];
    const requests: string[] = [];
    page.on("pageerror", (error) => errors.push(error.message));
    const item = {
      id: "item-1", batch_id: "batch-1", status: "draft", years_json: [2022],
      display_name: "Mario Rossi", codice_fiscale: "RSSMRA80A01H501Z", saldo_amount: 100,
      download_url: null, generated_document_path: null,
    };
    let failPreview = false;
    await page.route("**/api/**", async (route) => {
      const path = new URL(route.request().url()).pathname;
      requests.push(`${route.request().method()} ${path}`);
      let data: unknown = { items: [], total: 0, page: 1, page_size: 25 };
      if (path.endsWith("/auth/me")) data = { id: 1, username: "admin", role: "super_admin", is_active: true, enabled_modules: ["ruolo"] };
      if (path.endsWith("/auth/my-permissions")) data = { sections: [], granted_keys: ["ruolo.tributi.view"] };
      if (path.endsWith("/tributi/avvisi")) data = {
        items: [{ ...item, id: "avviso-1", codice_fiscale_raw: item.codice_fiscale, anno_tributario: 2022, payment_status: "unpaid", reminder_enabled: true }],
        total: 1, page: 1, page_size: 25,
      };
      if (path.endsWith("/batches")) {
        expect(route.request().postDataJSON().filters).toMatchObject({ preview_only: true, years: [2022] });
        data = { id: "batch-1", status: "review_required", items: [item] };
      }
      if (path.endsWith("/items/item-1/preview")) {
        expect(route.request().headers().authorization).toBe("Bearer draft-preview-test");
        if (failPreview) await route.fulfill({ status: 503, json: { detail: "Anteprima non disponibile" } });
        else await route.fulfill({ status: 200, contentType: "application/pdf", body: previewPdf });
        return;
      }
      await route.fulfill({ status: 200, json: data });
    });
    await page.goto("/ruolo/tributi?anno=2022&manager_key=gaia");
    await page.getByRole("button", { name: "Avviso sollecito", exact: true }).click();
    await expect(page.getByText(/BOZZA - NON VALIDA PER INVIO/)).toBeVisible();
    await expect(page.getByTitle("Preview PDF avviso sollecito")).toHaveAttribute("src", /^blob:/);
    await expect.poll(() => page.frames().some((frame) => frame.url().startsWith("chrome-extension://"))).toBe(true);
    await page.screenshot({ path: test.info().outputPath("draft-preview.png") });
    const downloadEvent = page.waitForEvent("download");
    await page.getByRole("link", { name: "Scarica PDF" }).click();
    expect((await downloadEvent).suggestedFilename()).toBe("bozza-RSSMRA80A01H501Z_avviso_sollecito.pdf");
    await page.getByRole("button", { name: "Chiudi", exact: true }).click();
    await expect(page.getByTitle("Preview PDF avviso sollecito")).toHaveCount(0);
    failPreview = true;
    await page.getByRole("button", { name: "Avviso sollecito", exact: true }).click();
    await expect(page.getByText("Anteprima non disponibile", { exact: true })).toBeVisible();
    await expect(page.getByRole("link", { name: "Scarica PDF" })).toHaveCount(0);
    expect(requests.some((request) => /\/download|\/export|\/confirm/.test(request))).toBe(false);
    expect(errors).toEqual([]);
  });
}
