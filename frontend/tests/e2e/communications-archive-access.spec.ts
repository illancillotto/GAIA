import { expect, test } from "@playwright/test";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { join } from "node:path";

const pdf = readFileSync(join(__dirname, "../fixtures/communications-multipage.pdf"));
const sha256 = createHash("sha256").update(pdf).digest("hex");

for (const width of [1440, 390]) {
  for (const channel of ["pec", "email"] as const) {
    test(`accessi archivio nel messaggio ${channel}, PDF invariato ${width}px`, async ({ page }) => {
      await page.setViewportSize({ width, height: 950 });
      await page.addInitScript(() => localStorage.setItem("gaia.access_token", "synthetic-archive"));
      const body = "GAIA-BLOCKS/1\n" + JSON.stringify([
        { kind: "paragraph", text: "SERVIZIO ICATASTO · Codice utenza 0001234 PIN: 0007654" },
        { kind: "button", text: "Accedi al portale", url: "https://example.org/portale" },
      ]);
      let drafts = 0;
      const mutations: string[] = [];
      const message = { id: "message", channel, account_id: "account", sender: "sender@example.org", recipient: "recipient@example.org", subject: "Avviso 1/2021", body, state: "draft", version: 1, notice_number: "1/2021", source_entity_id: "source", attachments: [{ id: "pdf", filename: "Avviso.pdf", mime_type: "application/pdf", size: pdf.length, pages: 3, sha256, version: 1 }] };
      await page.route("**/api/**", async (route) => {
        const request = route.request();
        const path = new URL(request.url()).pathname;
        // Presence heartbeats are independent of communication composition.
        if (request.method() !== "GET" && path.includes("/communications/")) mutations.push(path);
        let data: unknown = [];
        if (path.endsWith("/auth/me")) data = { id: 1, username: "synthetic", role: "admin", is_active: true, enabled_modules: ["ruolo"] };
        else if (path.endsWith("/auth/my-permissions")) data = { sections: [], granted_keys: ["ruolo.tributi.view", "ruolo.tributi.manage_status"] };
        else if (path.endsWith("/candidates")) data = { items: [{ id: "source", batch_title: "Sintetico", notice_number: "1/2021", display_name: "Contribuente sintetico", tax_code: "SYNTHETIC", year: 2021, amount: "10.00", [channel]: message.recipient, document_state: "generated", payment_state: "unpaid", notification_state: "nessuna_evidenza" }], total: 1 };
        else if (path.endsWith("/accounts")) data = [{ id: "account", name: "Casella sintetica", channel, sender: message.sender, paused: false }];
        else if (path.endsWith("/templates")) data = [{ id: "approved", name: "ICATASTO approvato", channel, status: "approved", version: 1 }];
        else if (path.endsWith("/template-preview")) data = { subject: message.subject, body, source_sha256: sha256, portal_access_source: "archive", missing_variables: [], send_blockers: [] };
        else if (path.endsWith("/messages") && request.method() === "POST") {
          expect(request.postDataJSON()).toMatchObject({ template_id: "approved", body, expected_source_sha256: sha256 });
          drafts++; data = message;
        } else if (path.endsWith("/messages/message")) data = message;
        else if (path.endsWith("/preview")) {
          await route.fulfill({ contentType: "application/pdf", body: pdf, headers: { "X-Communication-Review": "synthetic-review", "X-Content-SHA256": sha256, "X-PDF-Pages": "3" } }); return;
        } else if (path.endsWith("/rendered")) data = { recorded: true };
        await route.fulfill({ status: 200, json: data });
      });
      await page.goto(`/ruolo/tributi/solleciti/${channel}?embedded=1`);
      await page.getByRole("row", { name: "Apri avviso 1/2021" }).click();
      await expect(page.getByText(/Codice utenza e PIN ICATASTO recuperati dall’archivio GAIA/)).toBeVisible();
      await page.locator("summary").filter({ hasText: /^Anteprima messaggio$/ }).click();
      const messagePreview = page.getByRole("region", { name: "Anteprima messaggio", exact: true });
      await expect(messagePreview.getByText(/Codice utenza 0001234 PIN: 0007654/)).toBeVisible();
      await expect(messagePreview.getByRole("link", { name: "Accedi al portale" })).toBeVisible();
      await expect(page.locator("canvas[data-page]")).toHaveCount(3);
      await expect(page.getByRole("button", { name: "Crea bozza e snapshot PDF" })).toBeEnabled();
      expect(mutations).toEqual([]);
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
      await page.screenshot({ path: `/tmp/gaia-communication-archive-20261117/${channel}-${width}.png`, fullPage: true });
      await page.getByRole("button", { name: "Crea bozza e snapshot PDF" }).click();
      await expect.poll(() => drafts).toBe(1);
      expect(mutations.some(path => path.includes("complete-portal-snapshot") || path.endsWith("/dispatch"))).toBe(false);
    });
  }
}
