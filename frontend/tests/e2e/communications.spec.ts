import { expect, test, type Page } from "@playwright/test";
import { readFileSync } from "node:fs";
import { createHash } from "node:crypto";
import { join } from "node:path";
const pdf = readFileSync(join(__dirname, "../fixtures/communications-multipage.pdf"));
const sha256 = createHash("sha256").update(pdf).digest("hex");
for (const channel of ["pec", "email"]) for (const width of [1920, 1440, 390]) {
  test("PDF integrale e approvazione individuale " + channel + width + "px", async ({ page }) => {
    await page.setViewportSize({ width, height: width === 1920 ? 1080 : 900 });
    await page.addInitScript(() => localStorage.setItem("gaia.access_token", "communications-test"));
    const errors: string[] = [];
    page.on("pageerror", (error) => errors.push(error.message));
    const attachment = { id: "pdf", filename: "Avviso sintetico.pdf", mime_type: "application/pdf", size: pdf.length, sha256, pages: 3, version: 1 };
    const message = { id: "message", notice_number: "1/2021", account_id: "account", channel, sender: "sender@example.org", recipient: "recipient@example.org", subject: "Avviso sintetico", body: "Testo sintetico", state: "draft", version: 1, attachments: [attachment] };
    let rendered = 0, dispatched = 0, drafts = 0;
    await page.route("**/api/**", async (route) => {
      const path = new URL(route.request().url()).pathname;
      const method = route.request().method();
      let data: unknown = [];
      if (path.endsWith("/auth/me")) data = { id: 1, username: "synthetic", role: "admin", is_active: true, enabled_modules: ["ruolo"] };
      else if (path.endsWith("/auth/my-permissions")) data = { sections: [], granted_keys: ["ruolo.tributi.view", "ruolo.tributi.manage_status"] };
      else if (path.endsWith("/candidates")) {
        const query = new URL(route.request().url()).searchParams;
        expect(query.get(`has_${channel}`)).toBe("true");
        expect(query.get(channel === "pec" ? "has_email" : "has_pec")).toBeNull();
        data = { items: [{ id: "source", batch_title: "Sintetico", notice_number: "1/2021", display_name: "Contribuente di prova", tax_code: "SYNTHETIC", year: 2021, amount: "10.00", pec: message.recipient, email: message.recipient, document_state: "generated", payment_state: "unpaid", notification_state: "nessuna_evidenza" }], total: 1 };
      } else if (path.endsWith("/accounts")) data = [{ id: "account", name: "Casella sintetica", provider: "synthetic", channel, sender: message.sender, paused: false }];
      else if (path.endsWith("/templates")) data = [{ id: "approved", name: "Sollecito ufficio", channel, status: "approved", version: 2 }];
      else if (path.endsWith("/template-preview")) {
        expect(method).toBe("GET");
        expect(new URL(route.request().url()).searchParams.get("template_id")).toBe("approved");
        data = { subject: message.subject, body: message.body, source_sha256: sha256 };
      }
      else if (path.endsWith("/messages") && method === "POST") { expect(route.request().postDataJSON()).toMatchObject({ expected_source_sha256: sha256, template_id: "approved" }); drafts++; data = message; }
      else if (path.endsWith("/messages/message")) data = message;
      else if (path.endsWith("/preview")) {
        await route.fulfill({ contentType: "application/pdf", body: pdf, headers: { "X-Communication-Review": "synthetic-review", "X-Content-SHA256": sha256, "X-PDF-Pages": "3" } }); return;
      } else if (path.endsWith("/rendered")) {
        const payload = route.request().postDataJSON();
        expect(payload.pages).toBe(3); expect(payload.sha256).toBe(sha256); rendered++; data = { recorded: true };
      } else if (path.endsWith("/validate")) { message.state = "ready"; data = message; }
      else if (path.endsWith("/approve")) {
        expect(rendered).toBeGreaterThan(0);
        expect(Object.values(route.request().postDataJSON().checklist)).toEqual(Array(8).fill(true));
        message.state = "approved"; data = message;
      } else if (path.endsWith("/dispatch")) { expect(method).toBe("POST"); expect(message.state).toBe("approved"); dispatched++; message.state = "queued"; data = { id: "job" }; }
      await route.fulfill({ status: 200, json: data });
    });
    await page.goto("/ruolo/tributi/solleciti/" + channel + (width === 1920 ? "" : "?embedded=1"));
    await expectSidebarLayout(page, width);
    await expect(page.getByRole("combobox", { name: channel === "pec" ? "Presenza PEC" : "Presenza email", exact: true })).toHaveValue("true");
    await page.getByRole("checkbox", { name: "Seleziona 1/2021" }).check();
    await expect(page.locator("canvas[data-page]")).toHaveCount(3);
    await expect(page.getByRole("button", { name: "Crea bozza e snapshot PDF" })).toBeEnabled();
    expect(drafts).toBe(0); expect(rendered).toBe(0);
    await page.getByRole("checkbox", { name: "Seleziona 1/2021" }).uncheck();
    await expect(page.locator("canvas[data-page]")).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Componi", exact: true })).toHaveCount(0);
    const noticeRow = page.getByRole("row", { name: "Apri avviso 1/2021" });
    if (width >= 1280) await noticeRow.press("Enter");
    else await noticeRow.click();
    await expect(page.getByRole("complementary").getByLabel("Recapito verificato")).toHaveValue(message.recipient);
    await expect(page.getByLabel("Template approvato")).toHaveValue("approved");
    await expect(page.getByLabel("Oggetto", { exact: true })).toHaveValue(message.subject);
    await expect(page.getByRole("textbox", { name: "Testo", exact: true })).toHaveValue(message.body);
    await expect(page.getByRole("complementary").getByText("Contribuente di prova", { exact: true })).toBeVisible();
    await expect(page.locator("canvas[data-page]")).toHaveCount(3);
    await expect(page.getByRole("link", { name: "Apri PDF in nuova scheda" })).toHaveAttribute("href", /^blob:/);
    expect(drafts).toBe(0); expect(rendered).toBe(0);
    if (width >= 1280) {
      await page.evaluate(() => window.scrollTo(0, 0));
      const firstPage = (await page.locator('canvas[data-page="1"]').boundingBox())!;
      expect(firstPage.y).toBeLessThan((page.viewportSize()!).height - 80);
      const list = page.getByRole("region", { name: "Elenco avvisi" });
      expect(await list.locator("table").evaluate(table => table.scrollWidth <= table.clientWidth + 1)).toBe(true);
    }
    await page.screenshot({ path: `/tmp/gaia-communications-ui/compose-${channel}-${width}.png`, fullPage: false });
    await page.getByRole("button", { name: "Crea bozza e snapshot PDF" }).click();
    await expect(page.getByRole("button", { name: channel === "pec" ? "Invia PEC" : "Invia Email", exact: true })).toBeDisabled();
    await expect(page.locator("canvas[data-page]")).toHaveCount(3);
    await expect.poll(() => rendered).toBeGreaterThan(0);
    const fieldsTop = await page.getByLabel("Oggetto", { exact: true }).evaluate((el) => el.getBoundingClientRect().top);
    const previewTop = await page.getByRole("region", { name: "Anteprima allegati PDF" }).evaluate((el) => el.getBoundingClientRect().top);
    expect(fieldsTop).toBeLessThan(previewTop);
    await page.getByRole("complementary", { name: "Composizione avviso" }).evaluate((el) => { el.scrollTop = 0; });
    await page.screenshot({ path: "/tmp/gaia-sidebar-" + channel + width + ".png", fullPage: true });
    expect(await page.locator('canvas[data-page="3"]').evaluate((canvas) => (canvas as HTMLCanvasElement).width)).toBeGreaterThan(100);
    await page.getByRole("button", { name: "Pagina successiva" }).click();
    await expect(page.getByText("2 / 3", { exact: true })).toBeVisible();
    await page.getByRole("button", { name: "Aumenta zoom" }).click();
    await expect(page.getByRole("link", { name: "Apri PDF in nuova scheda" })).toHaveAttribute("href", /^blob:/);
    await page.getByRole("button", { name: "Verifica dati attuali" }).click();
    for (const checkbox of await page.locator('fieldset input[type="checkbox"]').all()) await checkbox.check();
    await page.getByRole("button", { name: "Conferma e approva" }).click();
    await expect(page.getByRole("button", { name: channel === "pec" ? "Invia PEC" : "Invia Email", exact: true })).toBeEnabled();
    await page.screenshot({ path: "/tmp/gaia-communications-" + channel + width + ".png", fullPage: true });
    await page.getByRole("button", { name: channel === "pec" ? "Invia PEC" : "Invia Email", exact: true }).click();
    await expect.poll(() => dispatched).toBe(1);
    expect(errors).toEqual([]);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 2)).toBe(true);
  });
}

async function expectSidebarLayout(page: Page, width: number) {
  const list = page.getByRole("region", { name: "Elenco avvisi" });
  const panel = page.getByRole("complementary", { name: "Composizione avviso" });
  await expect(list.getByRole("row", { name: "Apri avviso 1/2021" })).toBeVisible();
  const a = (await list.boundingBox())!;
  const b = (await panel.boundingBox())!;
  if (width >= 1280) {
    expect(b.x).toBeGreaterThan(a.x + a.width);
    expect(b.width).toBeGreaterThan(a.width * 1.8);
  } else {
    expect(b.y).toBeGreaterThanOrEqual(a.y + a.height);
  }
}

for (const poste of [false, true]) test(`Anteprima con invio bloccato ${poste ? "Poste riconciliato" : "storico e credenziali"}`, async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem("gaia.access_token", "communications-test"));
  let revised = false, repairs = 0, drafts = 0, previews = 0;
  const blocker = poste ? "Avviso riconciliato con Poste: invio PEC/email escluso per ora" : "Sollecito non eleggibile: storico_non_verificato";
  await page.route("**/api/**", async route => {
    const path = new URL(route.request().url()).pathname;
    let data: unknown = [];
    if (path.endsWith("/auth/me")) data = { id: 1, username: "synthetic", role: "admin", is_active: true, enabled_modules: ["ruolo"] };
    else if (path.endsWith("/auth/my-permissions")) data = { sections: [], granted_keys: ["ruolo.tributi.view", "ruolo.tributi.manage_status"] };
    else if (path.endsWith("/candidates")) data = { items: [{ id: "source", batch_title: "Sintetico", notice_number: "1/2021", display_name: "Contribuente di prova", tax_code: "SYNTHETIC", year: 2021, amount: "10.00", pec: "recipient@example.org", document_state: "generated", payment_state: "unpaid", notification_state: "da_verificare" }], total: 1 };
    else if (path.endsWith("/templates")) data = [{ id: "approved", name: "Sollecito ufficio", channel: "pec", status: "approved", version: 2 }];
    else if (path.endsWith("/template-preview")) data = { subject: "Avviso sintetico 1/2021", body: revised || poste ? "Credenziali sintetiche verificate" : "PIN [Da verificare: pin_utenza]", source_sha256: sha256, missing_variables: revised || poste ? [] : ["pin_utenza"], send_blockers: [blocker] };
    else if (path.endsWith("/complete-portal-snapshot")) { expect(route.request().method()).toBe("POST"); expect(new URL(route.request().url()).searchParams.get("expected_source_sha256")).toBe(sha256); revised = true; repairs++; data = { source_sha256: sha256 }; }
    else if (path.endsWith("/preview")) { previews++; await route.fulfill({ contentType: "application/pdf", body: pdf, headers: { "X-Content-SHA256": sha256, "X-PDF-Pages": "3" } }); return; }
    else if (path.endsWith("/messages") && route.request().method() === "POST") drafts++;
    await route.fulfill({ status: 200, json: data });
  });
  await page.goto("/ruolo/tributi/solleciti/pec?embedded=1");
  await page.getByRole("row", { name: "Apri avviso 1/2021" }).click();
  await expect(page.getByLabel("Oggetto", { exact: true })).toHaveValue("Avviso sintetico 1/2021");
  await expect(page.getByText(`Invio bloccato: ${blocker}. Verifica la posizione nel Registro avvisi e aggiorna gli stati.`)).toBeVisible();
  await expect(page.locator("canvas[data-page]")).toHaveCount(3);
  await expect(page.getByRole("button", { name: "Crea bozza e snapshot PDF" })).toBeDisabled();
  if (!poste) {
    await expect(page.getByRole("textbox", { name: "Testo", exact: true })).toHaveValue("PIN [Da verificare: pin_utenza]");
    await page.getByRole("button", { name: "Crea nuova revisione PDF con credenziali" }).click();
    await expect(page.getByRole("textbox", { name: "Testo", exact: true })).toHaveValue("Credenziali sintetiche verificate");
    await expect(page.getByRole("button", { name: "Crea nuova revisione PDF con credenziali" })).toHaveCount(0);
    await expect.poll(() => previews).toBe(2);
    expect(repairs).toBe(1);
  }
  await expect(page.getByRole("button", { name: "Crea bozza e snapshot PDF" })).toBeDisabled();
  expect(drafts).toBe(0);
});
