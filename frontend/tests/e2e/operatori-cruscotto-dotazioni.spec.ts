import { expect, test } from "@playwright/test";

test("operator dashboard displays custody by canonical GAIA ID without inferring ownership", async ({ page }) => {
  const custodyRequests: string[] = [];
  const linked = { id: "operator-a", wc_id: 100, gaia_user_id: 7, first_name: "Mario", last_name: "Rossi", enabled: true, current_fuel_cards: [] };
  const unlinked = { id: "operator-b", wc_id: 7, gaia_user_id: null, first_name: "Antonio", last_name: "Piras", enabled: true, current_fuel_cards: [] };
  await page.addInitScript(() => localStorage.setItem("gaia.access_token", "synthetic-custody-dashboard"));
  await page.route("**/api/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    let json: unknown = {};
    if (path === "/api/auth/me") json = { id: 1, username: "synthetic-admin", role: "admin", is_active: true, enabled_modules: ["accessi", "dotazioni"] };
    else if (path === "/api/auth/my-permissions") json = { granted_keys: ["dotazioni.view"] };
    else if (path === "/api/operazioni/operators") json = { items: [linked, unlinked], total: 2 };
    else if (path.endsWith("/detail")) json = {
      operator: path.includes("operator-a") ? linked : unlinked,
      stats: {}, current_fuel_cards: [], recent_usage_sessions: [], recent_fuel_logs: [],
    };
    else if (path.startsWith("/api/dotazioni/operators/")) {
      custodyRequests.push(path);
      expect(route.request().headers().authorization).toBe("Bearer synthetic-custody-dashboard");
      json = { items: [{ id: "asset-1", asset_code: "RAD-01", name: "Radio sintetica", asset_type: "radio", assigned_org_unit_name: "Squadra Nord",
        is_active: true, effective_status: "in_use", current_custody: { holder_name: "Mario Rossi", taken_at: "2026-10-01T07:15:00Z" } }], total: 1 };
    } else if (path.includes("/network/") || path.includes("/presenze/") || path.includes("/admin/users")) json = { items: [], total: 0 };
    await route.fulfill({ json });
  });
  await page.goto("/gaia/users/operatori-cruscotto");
  await expect(page.getByRole("heading", { name: "Dotazioni in custodia" })).toBeVisible();
  await expect(page.getByRole("link", { name: "RAD-01 · Radio sintetica" })).toHaveAttribute("href", "/dotazioni/assets/asset-1");
  expect(custodyRequests.length).toBeGreaterThan(0);
  expect(new Set(custodyRequests)).toEqual(new Set(["/api/dotazioni/operators/7/assets"]));
  const requestsBeforeUnlinkedSelection = custodyRequests.length;
  await page.getByRole("button", { name: /Antonio Piras/ }).click();
  await expect(page.getByText("Identità GAIA non collegata: custodie non consultabili.")).toBeVisible();
  await expect(page.getByRole("link", { name: "RAD-01 · Radio sintetica" })).toHaveCount(0);
  expect(custodyRequests).toHaveLength(requestsBeforeUnlinkedSelection);
});
