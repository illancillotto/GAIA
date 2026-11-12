import { expect, test } from "@playwright/test";
import catalog from "../../../backend/app/modules/communications/template_catalog.json";
import { readFileSync } from "node:fs";
import { createHash } from "node:crypto";
import { join } from "node:path";

const pdf = readFileSync(join(__dirname, "../fixtures/communications-multipage.pdf"));
const sha256 = createHash("sha256").update(pdf).digest("hex");

for (const width of [1440, 390]) {
  test(`creazione template con logo e link, anteprima e versioni ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 950 });
    await page.addInitScript(() => localStorage.setItem("gaia.access_token", "synthetic-rich-template"));
    const errors: string[] = [];
    page.on("pageerror", (error) => errors.push(error.message));
    const templates: Record<string, unknown>[] = [];
    await page.route("**/api/**", async (route) => {
      const path = new URL(route.request().url()).pathname;
      let data: unknown = [];
      if (path.endsWith("/auth/me")) data = { id: 1, username: "synthetic", role: "admin", is_active: true, enabled_modules: ["ruolo"] };
      else if (path.endsWith("/auth/my-permissions")) data = { sections: [], granted_keys: ["ruolo.tributi.view", "ruolo.tributi.manage_status"] };
      else if (path.endsWith("/admin/monitor")) data = { paused: true, transport_enabled: false, worker_seen_at: null, queues: {}, uncertain: 0, unmatched_receipts: 0 };
      else if (path.endsWith("/admin/templates")) data = templates;
      else if (path.endsWith("/admin/template-catalog")) data = catalog;
      else if (path.endsWith("/communications/templates") && route.request().method() === "POST") {
        data = { ...route.request().postDataJSON(), id: `synthetic-${templates.length}`, version: templates.length + 1, status: "draft" };
        templates.push(data as Record<string, unknown>);
      }
      await route.fulfill({ status: 200, json: data });
    });
    await page.goto("/gaia/communications?embedded=1");
    await page.getByLabel("Codice template").fill("grafico_test");
    await page.getByLabel("Nome template").fill("Template grafico");
    await page.getByLabel("Oggetto template").fill("Avviso {{numero_avviso}}");
    await page.getByLabel("Corpo template").fill("Gentile {{contribuente_nome}}, verifica l’avviso allegato.");
    await page.getByRole("button", { name: "Crea layout con logo e link", exact: true }).click();
    await page.getByRole("button", { name: "+ Logo ufficiale", exact: true }).click();
    await page.getByLabel("Sposta su blocco 2").click();
    await page.getByRole("button", { name: "+ Pulsante", exact: true }).click();
    await page.getByLabel("Testo blocco 3").fill("Consulta la tua posizione");
    await page.getByLabel("URL blocco 3").fill("https://incatasto.servizicapacitas.com/pages/main.aspx?cons=090");
    const preview = page.getByRole("region", { name: "Anteprima messaggio" });
    await expect(preview.getByRole("img")).toBeVisible();
    await expect(preview.getByRole("link", { name: "Consulta la tua posizione" })).toHaveAttribute("href", /https:\/\/incatasto/);
    await expect(preview.getByRole("img")).toHaveJSProperty("naturalWidth", 1400);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    await page.screenshot({ path: `/tmp/gaia-templates-rich-${width}.png`, fullPage: true });
    await page.getByRole("button", { name: "Salva nuova versione bozza", exact: true }).click();
    await expect(page.getByLabel("Codice template")).toHaveValue("");
    expect(templates).toHaveLength(1);
    const blocks = JSON.parse((templates[0].body as string).slice("GAIA-BLOCKS/1\n".length));
    expect(blocks.map((block: { kind: string }) => block.kind)).toEqual(["logo", "paragraph", "button"]);
    await page.getByRole("button", { name: "Crea nuova versione", exact: true }).click();
    await expect(page.getByLabel("URL blocco 3")).toHaveValue("https://incatasto.servizicapacitas.com/pages/main.aspx?cons=090");
    expect(errors).toEqual([]);
  });

  test(`composizione grafica con dati avviso e PDF ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 950 });
    await page.addInitScript(() => localStorage.setItem("gaia.access_token", "synthetic-rich-composition"));
    const body = "GAIA-BLOCKS/1\n" + JSON.stringify([
      { kind: "logo" }, { kind: "paragraph", text: "Gentile Contribuente sintetico, avviso 1/2021" },
      { kind: "button", text: "Consulta il portale", url: "https://example.org/portale" },
    ]);
    const attachments = [{ id: "pdf", filename: "Avviso.pdf", mime_type: "application/pdf", size: pdf.length, pages: 3, sha256, version: 1 }];
    const message = { id: "message", channel: "pec", account_id: "account", sender: "sender@example.org", recipient: "recipient@example.org", subject: "Avviso 1/2021", body, state: "draft", version: 1, notice_number: "1/2021", source_entity_id: "source", attachments };
    let drafts = 0;
    await page.route("**/api/**", async (route) => {
      const path = new URL(route.request().url()).pathname;
      let data: unknown = [];
      if (path.endsWith("/auth/me")) data = { id: 1, username: "synthetic", role: "admin", is_active: true, enabled_modules: ["ruolo"] };
      else if (path.endsWith("/auth/my-permissions")) data = { sections: [], granted_keys: ["ruolo.tributi.view", "ruolo.tributi.manage_status"] };
      else if (path.endsWith("/candidates")) data = { items: [{ id: "source", batch_title: "Sintetico", notice_number: "1/2021", display_name: "Contribuente sintetico", tax_code: "SYNTHETIC", year: 2021, amount: "10.00", pec: message.recipient, document_state: "generated", payment_state: "unpaid", notification_state: "nessuna_evidenza" }], total: 1 };
      else if (path.endsWith("/accounts")) data = [{ id: "account", name: "Casella sintetica", channel: "pec", sender: message.sender, paused: false }];
      else if (path.endsWith("/templates")) data = [{ id: "approved", name: "Grafico approvato", channel: "pec", status: "approved", version: 1 }];
      else if (path.endsWith("/template-preview")) data = { subject: message.subject, body, source_sha256: sha256 };
      else if (path.endsWith("/messages") && route.request().method() === "POST") {
        expect(route.request().postDataJSON()).toMatchObject({ template_id: "approved", body, subject: message.subject, expected_source_sha256: sha256 });
        drafts++; data = message;
      } else if (path.endsWith("/messages/message")) data = message;
      else if (path.endsWith("/preview")) {
        await route.fulfill({ contentType: "application/pdf", body: pdf, headers: { "X-Communication-Review": "synthetic-review", "X-Content-SHA256": sha256, "X-PDF-Pages": "3" } }); return;
      } else if (path.endsWith("/rendered")) data = { recorded: true };
      await route.fulfill({ status: 200, json: data });
    });
    await page.goto("/ruolo/tributi/solleciti/pec?embedded=1");
    await page.getByRole("row", { name: "Apri avviso 1/2021" }).click();
    await expect(page.getByLabel("Template approvato")).toHaveValue("approved");
    const summary = page.locator("summary").filter({ hasText: /^Anteprima messaggio$/ });
    await summary.click();
    await expect(page.getByRole("link", { name: "Consulta il portale" })).toBeVisible();
    await summary.click();
    await expect(page.locator("canvas[data-page]")).toHaveCount(3);
    await expect(page.getByRole("button", { name: "Crea bozza e snapshot PDF" })).toBeEnabled();
    if (width >= 1280) {
      await page.evaluate(() => window.scrollTo(0, 0));
      expect((await page.locator('canvas[data-page="1"]').boundingBox())!.y).toBeLessThan(870);
    }
    await page.screenshot({ path: `/tmp/gaia-templates-rich-compose-${width}.png`, fullPage: true });
    await page.getByRole("button", { name: "Crea bozza e snapshot PDF" }).click();
    await expect(page.getByLabel("Destinatario", { exact: true })).toHaveValue(message.recipient);
    await expect(page.getByLabel("Messaggio da inviare")).toBeVisible();
    await expect(page.locator("canvas[data-page]")).toHaveCount(3);
    expect(drafts).toBe(1);
  });
}
