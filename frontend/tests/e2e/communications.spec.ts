import { expect, test, type Page } from "@playwright/test";
import { readFileSync } from "node:fs";
import { createHash } from "node:crypto";
import { join } from "node:path";
const pdf = readFileSync(join(__dirname, "../fixtures/communications-multipage.pdf"));
const sha256 = createHash("sha256").update(pdf).digest("hex");
for (const channel of ["pec", "email"]) for (const width of [1440, 390]) {
  test("PDF integrale e approvazione individuale " + channel + width + "px", async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.addInitScript(() => localStorage.setItem("gaia.access_token", "communications-test"));
    const errors: string[] = [];
    page.on("pageerror", (error) => errors.push(error.message));
    const attachment = { id: "pdf", filename: "Avviso sintetico.pdf", mime_type: "application/pdf", size: pdf.length, sha256, pages: 3, version: 1 };
    const message = { id: "message", notice_number: "1/2021", account_id: "account", channel, sender: "sender@example.org", recipient: "recipient@example.org", subject: "Avviso sintetico", body: "Testo sintetico", state: "draft", version: 1, attachments: [attachment] };
    let rendered = 0, dispatched = 0;
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
        data = { items: [{ id: "source", batch_title: "Sintetico", notice_number: "1/2021", display_name: "Contribuente di prova", year: 2021, amount: "10.00", pec: message.recipient, email: message.recipient, document_state: "generated", payment_state: "unpaid", notification_state: "nessuna_evidenza" }], total: 1 };
      } else if (path.endsWith("/accounts")) data = [{ id: "account", name: "Casella sintetica", provider: "synthetic", channel, sender: message.sender, paused: false }];
      else if (path.endsWith("/messages") && method === "POST") data = message;
      else if (path.endsWith("/messages/message")) data = message;
      else if (path.endsWith("/preview")) {
        await route.fulfill({ contentType: "application/pdf", body: pdf, headers: { "X-Communication-Review": "synthetic-review", "X-Content-SHA256": sha256 } }); return;
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
    await page.goto("/ruolo/tributi/solleciti/" + channel + "?embedded=1");
    await expectSidebarLayout(page, width);
    await expect(page.getByRole("combobox", { name: channel === "pec" ? "Presenza PEC" : "Presenza email", exact: true })).toHaveValue("true");
    await page.getByRole("button", { name: "Componi", exact: true }).click();
    await expect(page.getByRole("complementary").getByLabel("Recapito verificato")).toHaveValue(message.recipient);
    await page.getByRole("button", { name: "Crea bozza e snapshot PDF" }).click();
    await expect(page.getByRole("button", { name: channel === "pec" ? "Invia PEC" : "Invia Email", exact: true })).toBeDisabled();
    await expect(page.locator("canvas[data-page]")).toHaveCount(3);
    await expect.poll(() => rendered).toBeGreaterThan(0);
    const fieldsTop = await page.getByLabel("Oggetto", { exact: true }).evaluate((el) => el.getBoundingClientRect().top);
    const previewTop = await page.getByRole("region", { name: "Anteprima allegati PDF" }).evaluate((el) => el.getBoundingClientRect().top);
    expect(fieldsTop).toBeLessThan(previewTop);
    await page.getByRole("complementary").evaluate((el) => { el.scrollTop = 0; });
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
  await expect(list.getByRole("button", { name: "Componi", exact: true })).toBeVisible();
  const a = (await list.boundingBox())!;
  const b = (await panel.boundingBox())!;
  if (width >= 1280) {
    expect(b.x).toBeGreaterThan(a.x + a.width);
    expect(Math.abs(a.width - b.width)).toBeLessThan(2);
  } else {
    expect(b.y).toBeGreaterThanOrEqual(a.y + a.height);
  }
}
