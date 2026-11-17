import { expect, test } from "@playwright/test";

const account = {
  id: "synthetic", version: 1, name: "Account sintetico", channel: "pec", provider: "Test",
  sender: "test@example.org", display_name: "Test", smtp_host: "smtp.example.org", smtp_port: 465,
  smtp_encryption: "tls", imap_host: "imap.example.org", imap_port: 993, imap_encryption: "tls",
  auth_method: "password", username: "test", secret_ref: "synthetic", active: false, paused: true,
  allowed_modules: ["ruolo"], allowed_user_ids: [], default_modules: [], is_default: false,
  priority: 100, max_bytes: 16777216, hourly_limit: 30, health: "untested", last_test_at: null,
  last_sync_at: null,
};

for (const width of [1440, 390]) {
  test(`Account panel collapses, supports keyboard and opens edits at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.addInitScript(() => localStorage.setItem("gaia.access_token", "synthetic-account-panel"));
    const writes: string[] = [];
    const errors: string[] = [];
    page.on("pageerror", error => errors.push(error.message));
    await page.route("**/api/**", async route => {
      const request = route.request();
      const path = new URL(request.url()).pathname;
      if (request.method() !== "GET" && path.startsWith("/api/communications/")) writes.push(request.url());
      let data: unknown = [];
      if (path.endsWith("/auth/me")) data = { id: 1, username: "synthetic", role: "admin", is_active: true, enabled_modules: ["accessi", "ruolo"] };
      else if (path.endsWith("/auth/my-permissions")) data = { sections: [], granted_keys: ["ruolo.tributi.view", "ruolo.tributi.manage_status"] };
      else if (path.endsWith("/admin/accounts")) data = [account];
      else if (path.endsWith("/admin/monitor")) data = { paused: true, transport_enabled: false, worker_seen_at: null, queues: {}, uncertain: 0, unmatched_receipts: 0 };
      await route.fulfill({ status: 200, json: data });
    });
    await page.goto("/gaia/communications");
    const panel = page.locator("details").filter({ has: page.locator("summary", { hasText: "Nuovo account" }) });
    const summary = panel.locator("summary");
    const name = page.getByLabel("Nome account", { exact: true });
    await expect(summary).toBeVisible();
    await expect(name).toBeHidden();
    await expect(panel).not.toHaveAttribute("open");
    await page.screenshot({ path: test.info().outputPath(`account-panel-closed-${width}.png`), fullPage: true });
    await summary.focus();
    await page.keyboard.press("Enter");
    await expect(name).toBeVisible();
    await name.fill("Bozza da conservare");
    await summary.focus();
    await page.keyboard.press("Space");
    await expect(name).toBeHidden();
    await summary.click();
    await expect(name).toHaveValue("Bozza da conservare");
    await summary.click();
    await page.getByRole("button", { name: "Modifica", exact: true }).click();
    await expect(name).toBeVisible();
    await expect(name).toHaveValue(account.name);
    await page.locator("summary", { hasText: "Modifica account" }).click();
    await expect(name).toBeHidden();
    await page.getByRole("button", { name: "Modifica", exact: true }).click();
    await expect(name).toBeVisible();
    await page.screenshot({ path: test.info().outputPath(`account-panel-${width}.png`), fullPage: true });
    expect(writes).toEqual([]);
    expect(errors).toEqual([]);
  });
}
