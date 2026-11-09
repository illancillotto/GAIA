import { expect, test } from "@playwright/test";
import { readFileSync } from "node:fs";
import { createHash } from "node:crypto";
import { join } from "node:path";

const pdf = readFileSync(join(__dirname, "../fixtures/communications-multipage.pdf"));
const sha256 = createHash("sha256").update(pdf).digest("hex");

for (const [channel, total, pages] of [["pec", 230, 10], ["email", 140, 6]] as const) {
  test(`paginazione candidati ${channel} oltre la terza pagina e ritorno`, async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 });
    // Serve synthetic API data only; exercise the frontend bundle at baseURL.
    await page.addInitScript(() => localStorage.setItem("gaia.access_token", "pagination-synthetic"));
    const requested: number[] = [];
    const errors: string[] = [];
    page.on("pageerror", error => errors.push(error.message));
    await page.route("**/api/**", async route => {
      const url = new URL(route.request().url());
      let data: unknown = [];
      if (url.pathname.endsWith("/preview")) {
        await route.fulfill({ contentType: "application/pdf", body: pdf,
          headers: { "X-Content-SHA256": sha256, "X-PDF-Pages": "3" } });
        return;
      }
      if (url.pathname.endsWith("/auth/me")) {
        data = { id: 1, username: "synthetic", role: "operator", is_active: true, enabled_modules: ["ruolo"] };
      } else if (url.pathname.endsWith("/auth/my-permissions")) {
        data = { sections: [], granted_keys: ["ruolo.tributi.view", "ruolo.tributi.manage_status"] };
      } else if (url.pathname.endsWith("/communications/ruolo/candidates")) {
        expect(url.searchParams.get(`has_${channel}`)).toBe("true");
        const current = Number(url.searchParams.get("page"));
        requested.push(current);
        const start = (current - 1) * 25;
        data = { total, page: current, page_size: 25, items: Array.from({ length: Math.min(25, total - start) }, (_, i) => ({
          id: `synthetic-${start + i + 1}`, notice_number: `${start + i + 1}/2021`, batch_title: "Lotto sintetico",
          display_name: `Contribuente sintetico ${start + i + 1}`, tax_code: "SYNTHETIC", year: 2021,
          amount: "10.00", pec: "synthetic@example.org", email: "synthetic@example.org", document_state: "generated",
          payment_state: "unpaid", notification_state: "nessuna_evidenza",
        })) };
        // Preserve asynchronous loading, including a late fourth-page response.
        if (current === 4) await new Promise(resolve => setTimeout(resolve, 250));
      }
      await route.fulfill({ status: 200, json: data });
    });
    await page.goto(`/ruolo/tributi/solleciti/${channel}?embedded=1`);
    const nav = page.getByRole("navigation", { name: "Paginazione candidati" });
    const next = nav.getByRole("button", { name: "Successiva" });
    const previous = nav.getByRole("button", { name: "Precedente" });
    async function expectPage(current: number) {
      await expect(nav.getByText(`${current} / ${pages}`, { exact: true })).toBeVisible();
      await expect(page.getByRole("row", { name: `Apri avviso ${(current - 1) * 25 + 1}/2021`, exact: true })).toBeVisible();
      await expect(page.getByRole("status").filter({ hasText: "Caricamento candidati" })).toHaveCount(0);
    }
    await expectPage(1);
    await page.getByRole("row", { name: "Apri avviso 1/2021", exact: true }).click();
    await expect(page.locator("canvas[data-page]")).toHaveCount(3);
    await expect(previous).toBeDisabled();
    for (let current = 2; current <= pages; current++) {
      await next.click();
      await expectPage(current);
    }
    await expect(next).toBeDisabled();
    for (let current = pages - 1; current >= 1; current--) {
      await previous.click();
      await expectPage(current);
    }
    await expect(previous).toBeDisabled();
    // Session bootstrap may repeat the initial request; navigation order must remain correct.
    expect(requested.filter((current, i) => current !== requested[i - 1])).toEqual([
      ...Array.from({ length: pages }, (_, i) => i + 1),
      ...Array.from({ length: pages - 1 }, (_, i) => pages - i - 1),
    ]);
    expect(errors).toEqual([]);
  });
}
