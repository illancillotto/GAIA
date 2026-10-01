import { expect, test } from "@playwright/test";

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
