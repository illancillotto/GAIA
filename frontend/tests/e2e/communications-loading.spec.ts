import { expect, test } from "@playwright/test";

test("La ricerca accorpa la digitazione e non ricarica account e template", async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem("gaia.access_token", "communications-test"));
  const queries: string[] = [];
  let accounts = 0, templates = 0;
  await page.route("**/api/**", async route => {
    const url = new URL(route.request().url());
    const path = url.pathname;
    let data: unknown = [];
    if (path.endsWith("/auth/me")) data = { id: 1, username: "synthetic", role: "admin", is_active: true, enabled_modules: ["ruolo"] };
    else if (path.endsWith("/auth/my-permissions")) data = { sections: [], granted_keys: ["ruolo.tributi.view", "ruolo.tributi.manage_status"] };
    else if (path.endsWith("/accounts")) { accounts++; data = []; }
    else if (path.endsWith("/templates")) { templates++; data = []; }
    else if (path.endsWith("/candidates")) {
      queries.push(url.search);
      data = { items: [{ id: "source", batch_title: "Sintetico", notice_number: "1/2021", display_name: url.searchParams.get("q") ? "Montisci sintetico" : "Contribuente di prova", tax_code: "SYNTHETIC", year: 2021, amount: "10.00", pec: "recipient@example.org", document_state: "generated", payment_state: "unpaid", notification_state: "da_verificare" }], total: 26 };
    }
    await route.fulfill({ status: 200, json: data });
  });
  await page.goto("/ruolo/tributi/solleciti/pec");
  await expect(page.getByRole("row", { name: "Apri avviso 1/2021" })).toBeVisible();
  const search = page.getByRole("textbox", { name: "Cerca nominativo, CF o avviso" });
  await search.pressSequentially("montisci", { delay: 30 });
  await expect(page.getByText("Montisci sintetico", { exact: true })).toBeVisible();
  expect(queries).toHaveLength(2);
  expect(queries[1]).toContain("q=montisci");
  await page.getByRole("button", { name: "Successiva" }).click();
  await expect(page.getByText("2 / 2", { exact: true })).toBeVisible();
  await expect.poll(() => queries.length).toBe(3);
  expect(queries[2]).toContain("page=2");
  expect(accounts).toBe(1);
  expect(templates).toBe(1);
});
