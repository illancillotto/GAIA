import { expect, test } from "@playwright/test";

test("live synthetic login to gateway to MCP to model", async ({ page }) => {
  test.skip(process.env.GAIA_MCP_LIVE_BROWSER !== "1", "Explicit synthetic fixture/provider opt-in required");
  test.setTimeout(180_000);
  const backend = process.env.GAIA_MCP_SYNTHETIC_BACKEND_URL;
  expect(backend).toMatch(/^http:\/\/127\.0\.0\.1:\d+$/);
  await page.route("**/api/**", async (route) => {
    const original = new URL(route.request().url());
    const response = await route.fetch({ url: `${backend}${original.pathname.slice(4)}${original.search}` });
    await route.fulfill({ response });
  });
  await page.goto("/login");
  await page.getByLabel("Username o email").fill("synthetic-mcp");
  await page.locator("input#password").fill("synthetic-login-password");
  const login = page.waitForResponse((response) => response.url().endsWith("/api/auth/login") && response.request().method() === "POST");
  await page.getByRole("button", { name: "Accedi alla piattaforma" }).click();
  expect((await login).status()).toBe(200);
  await expect.poll(() => page.evaluate(() => Boolean(localStorage.getItem("gaia.access_token")))).toBe(true);
  await page.goto("/wiki/mcp?embedded=1");
  await expect(page.getByLabel("Domanda sintetica")).toBeVisible();
  const found = page.waitForResponse((response) => response.url().endsWith("/api/wiki/mcp/chat"));
  await page.getByRole("button", { name: "Interroga Data MCP" }).click();
  const foundResponse = await found;
  expect(foundResponse.status()).toBe(200);
  const answer = await foundResponse.json();
  expect(answer.found).toBe(true);
  expect(answer.tool_calls).toBeGreaterThan(0);
  expect(answer.provenance.some((source: { entity: string; source: string }) => source.entity === "subjects" && source.source === "gaia_synthetic_db")).toBe(true);
  expect(answer.provenance.filter((source: { entity: string }) => source.entity === "subjects")
    .map((source: { record_id: string }) => source.record_id))
    .toEqual(["4a00bb81-2eb8-5fbc-81fe-98e6858033af"]);
  await expect(page.getByRole("region", { name: "Risposta sintetica" }).getByText(/gaia_synthetic_db \/ subjects/)).toBeVisible();
  await page.getByLabel("Domanda sintetica").selectOption("Cerca il soggetto sintetico con identificativo SYN-NOT-EXISTENT.");
  const absent = page.waitForResponse((response) => response.url().endsWith("/api/wiki/mcp/chat"));
  await page.getByRole("button", { name: "Interroga Data MCP" }).click();
  const absentResponse = await absent;
  expect(absentResponse.status()).toBe(200);
  const empty = await absentResponse.json();
  expect(empty.found).toBe(false);
  expect(empty.provenance).toEqual([]);
  expect(empty.tool_calls).toBeGreaterThan(0);
  await expect(page.getByText(/Nessuna evidenza/)).toBeVisible();
});

test("synthetic preview uses MCP only and handles source failure", async ({ page }) => {
  const questions: string[] = [];
  let unavailable = false;
  await page.addInitScript(() => localStorage.setItem("gaia.access_token", "synthetic-browser-session"));
  await page.route("**/api/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path === "/api/wiki/mcp/chat") {
      expect(route.request().headers().authorization).toBe("Bearer synthetic-browser-session");
      questions.push(route.request().postDataJSON().question);
      await route.fulfill({ status: unavailable ? 503 : 200, json: unavailable
        ? { detail: "MCP agent unavailable" }
        : { answer: "Risposta solo sintetica", found: true, tool_calls: 1, evidence_tokens: 100,
            provenance: [{ source: "gaia_synthetic_db", entity: "subjects", record_id: "synthetic-browser-uuid", dataset_version: "synthetic-browser-v1" }] } });
      return;
    }
    const json = path === "/api/auth/me"
      ? { id: 1, username: "synthetic-browser-user", role: "viewer", is_active: true }
      : path === "/api/auth/my-permissions" ? { granted_keys: [] } : {};
    await route.fulfill({ status: 200, json });
  });
  await page.goto("/wiki/mcp?embedded=1");
  await expect(page.getByLabel("Domanda sintetica")).toBeVisible();
  await expect(page.getByRole("textbox")).toHaveCount(0);
  await page.getByRole("button", { name: "Interroga Data MCP" }).click();
  await expect(page.getByText("Risposta solo sintetica")).toBeVisible();
  await expect(page.getByText(/gaia_synthetic_db \/ subjects \/ synthetic-browser-uuid/)).toBeVisible();
  unavailable = true;
  await page.getByLabel("Domanda sintetica").selectOption("Cerca il soggetto sintetico con identificativo SYN-NOT-EXISTENT.");
  await page.getByRole("button", { name: "Interroga Data MCP" }).click();
  await expect(page.getByRole("alert").filter({ hasText: "Agente non disponibile" })).toBeVisible();
  await expect(page.getByText("Risposta solo sintetica")).toHaveCount(0);
  expect(questions).toEqual([
    "Cerca il soggetto sintetico con identificativo SYN-SUBJECT-0001.",
    "Cerca il soggetto sintetico con identificativo SYN-NOT-EXISTENT.",
  ]);
});
