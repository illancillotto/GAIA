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

test("wiki widget sends contextual payload and renders page intro without prompt leakage", async ({ page }) => {
  let wikiRequestBody: Record<string, unknown> | null = null;

  await loginAsAdmin(page);

  await page.route("**/api/wiki/conversations?**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([]),
    });
  });

  await page.route("**/api/catasto/meter-readings?**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        items: [
          {
            id: "00000000-0000-0000-0000-000000000701",
            punto_consegna: "PC-001",
            matricola: "MTR-001",
            subject_display_name: "Rossi Mario",
            validation_status: "valid",
            validation_messages: [],
            row_number: 2,
            anno: 2025,
            consumo_mc: "25.000",
            created_at: "2026-05-15T10:00:00Z",
            updated_at: "2026-05-15T10:00:00Z",
          },
        ],
        total: 1,
        page: 1,
        page_size: 50,
      }),
    });
  });

  await page.route("**/api/wiki/chat/stream", async (route) => {
    wikiRequestBody = route.request().postDataJSON() as Record<string, unknown>;
    await route.fulfill({
      status: 200,
      contentType: "text/event-stream",
      headers: {
        "Cache-Control": "no-cache",
        Connection: "keep-alive",
      },
      body: [
        'event: meta',
        `data: ${JSON.stringify({
          event: "meta",
          data: {
            mode: "docs_only",
            found: true,
            conversation_id: "11111111-1111-1111-1111-111111111111",
            tool_calls: [],
            sources: [],
            evidences: [],
            stream_mode: "synthetic",
          },
        })}`,
        "",
        'event: delta',
        `data: ${JSON.stringify({
          event: "delta",
          data: {
            text: "Ciao. In questa pagina Contatori irrigui trovi funzionalita operative e documentazione contestuale.",
          },
        })}`,
        "",
        'event: delta',
        `data: ${JSON.stringify({
          event: "delta",
          data: {
            text: "- Scopo: orientarti su cosa mostra la pagina e come usarla.",
          },
        })}`,
        "",
        'event: delta',
        `data: ${JSON.stringify({
          event: "delta",
          data: {
            text: "- Cosa puoi fare: come leggere una lettura; filtrare per contatore o periodo; aprire il dettaglio della lettura.",
          },
        })}`,
        "",
        'event: delta',
        `data: ${JSON.stringify({
          event: "delta",
          data: {
            text: "- Prossimi passi: dimmi cosa ti serve e ti rispondo in modo mirato.",
          },
        })}`,
        "",
        'event: done',
        `data: ${JSON.stringify({
          event: "done",
          data: {
            answer:
              "Ciao. In questa pagina Contatori irrigui trovi funzionalita operative e documentazione contestuale. - Scopo: orientarti su cosa mostra la pagina e come usarla. - Cosa puoi fare: come leggere una lettura; filtrare per contatore o periodo; aprire il dettaglio della lettura. - Prossimi passi: dimmi cosa ti serve e ti rispondo in modo mirato.",
            conversation_id: "11111111-1111-1111-1111-111111111111",
          },
        })}`,
        "",
      ].join("\n"),
    });
  });

  await page.goto("/catasto/letture-contatori");

  await expect(page.getByText("Registro letture Catasto")).toBeVisible();

  await page.getByLabel("Apri assistente GAIA").click();
  await expect(page.getByText("Assistente GAIA", { exact: true })).toBeVisible();

  await page.getByPlaceholder("Scrivi una domanda...").fill("come funziona questa pagina?");
  await page.getByPlaceholder("Scrivi una domanda...").press("Enter");

  await expect(page.getByText(/Contatori irrigui trovi funzionalita operative/)).toBeVisible();
  await expect(page.getByText(/Scopo: orientarti su cosa mostra la pagina/)).toBeVisible();
  await expect(page.getByText(/Cosa puoi fare: come leggere una lettura/)).toBeVisible();
  await expect(page.getByText(/Prossimi passi: dimmi cosa ti serve/)).toBeVisible();
  await expect(page.getByText(/Prompt interno|Pagina di benvenuto contestuale/)).toHaveCount(0);

  expect(wikiRequestBody).not.toBeNull();
  expect(wikiRequestBody).toMatchObject({
    question: "come funziona questa pagina?",
    module_key: "catasto",
    page_path: "/catasto/letture-contatori",
  });
});
