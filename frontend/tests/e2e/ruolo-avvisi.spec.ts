import { expect, test, type Page } from "@playwright/test";

async function loginAsAdmin(page: Page) {
  const username = process.env.PLAYWRIGHT_ADMIN_USERNAME ?? "admin";
  const password = process.env.PLAYWRIGHT_ADMIN_PASSWORD ?? "#0r1st4n3s1";

  await page.goto("/login");
  await page.getByLabel("Username o email").fill(username);
  await page.locator("input#password").fill(password);
  await page.getByRole("button", { name: "Accedi alla piattaforma" }).click();
  await page.waitForURL("**/");
}

function makeAvviso(id: string, label: string) {
  return {
    id,
    codice_cnc: `CNC-${id.slice(-3)}`,
    anno_tributario: 2025,
    subject_id: "11111111-1111-1111-1111-111111111111",
    codice_fiscale_raw: "RSSMRA80A01H501Z",
    nominativo_raw: label,
    codice_utenza: "U12345",
    importo_totale_0648: 50,
    importo_totale_0985: 20,
    importo_totale_0668: 0,
    importo_totale_euro: 70,
    display_name: label,
    is_linked: true,
    created_at: "2026-05-15T08:00:00Z",
    updated_at: "2026-05-15T08:00:00Z",
  };
}

test("ruolo avvisi live search waits for 3 chars, debounces requests and opens modal detail", async ({ page }) => {
  await loginAsAdmin(page);

  const qRequests: string[] = [];
  const baseAvviso = makeAvviso("00000000-0000-0000-0000-000000000101", "Rossi Mario");
  const yearAvviso = makeAvviso("00000000-0000-0000-0000-000000000202", "Avviso 2025");
  const codeAvviso = makeAvviso("00000000-0000-0000-0000-000000000303", "PRCLS Service");

  await page.route("**/api/ruolo/avvisi/*", async (route) => {
    const url = new URL(route.request().url());
    const avvisoId = url.pathname.split("/").at(-1);
    const detail =
      avvisoId === yearAvviso.id
        ? yearAvviso
        : avvisoId === codeAvviso.id
          ? codeAvviso
          : baseAvviso;

    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        ...detail,
        import_job_id: "99999999-9999-9999-9999-999999999999",
        domicilio_raw: "Via Roma 1",
        residenza_raw: "Oristano",
        n2_extra_raw: null,
        importo_totale_lire: null,
        n4_campo_sconosciuto: null,
        partite: [],
      }),
    });
  });

  await page.route("**/api/ruolo/avvisi**", async (route) => {
    const url = new URL(route.request().url());
    if (url.pathname !== "/api/ruolo/avvisi") {
      await route.continue();
      return;
    }

    const q = url.searchParams.get("q") ?? "";
    if (q) {
      qRequests.push(q);
    }

    let items = [baseAvviso];
    if (q === "2025") {
      items = [yearAvviso];
    } else if (q.toLowerCase() === "prcls") {
      items = [codeAvviso];
    }

    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        items,
        total: items.length,
        page: 1,
        page_size: 25,
      }),
    });
  });

  await page.goto("/ruolo/avvisi");

  await expect(page.getByText("Ricerca pronta")).toBeVisible();
  const searchInput = page.getByRole("searchbox", { name: "Cerca avviso" });

  await searchInput.pressSequentially("20", { delay: 40 });
  await page.waitForTimeout(500);
  await expect(page.getByText("Inserisci almeno 3 caratteri per avviare la ricerca.")).toBeVisible();
  expect(qRequests).toEqual([]);

  await searchInput.pressSequentially("25", { delay: 40 });
  await expect(page.getByText('Ricerca attiva su "2025".')).toBeVisible();
  await expect(page.getByText("Avviso 2025")).toBeVisible();
  expect(qRequests).toEqual(["2025"]);

  await searchInput.fill("");
  await expect(page.getByText("Ricerca pronta")).toBeVisible();

  await searchInput.pressSequentially("prcls", { delay: 40 });
  await expect(page.getByText('Ricerca attiva su "prcls".')).toBeVisible();
  await expect(page.getByText("PRCLS Service")).toBeVisible();
  expect(qRequests).toEqual(["2025", "prcls"]);

  await page.getByRole("button", { name: /PRCLS Service/ }).click();
  await expect(page.getByText("Dettaglio avviso", { exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: "Apri pagina" })).toHaveAttribute(
    "href",
    `/ruolo/avvisi/${codeAvviso.id}`,
  );
  await expect(page.locator('iframe[title="Dettaglio avviso CNC-303"]')).toHaveAttribute(
    "src",
    `/ruolo/avvisi/${codeAvviso.id}?embedded=1`,
  );
});
