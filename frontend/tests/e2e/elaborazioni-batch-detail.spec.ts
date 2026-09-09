import { expect, test } from "@playwright/test";

const detail = {
  id: "batch", user_id: 1, name: "Verifica credenziali batch", status: "completed",
  total_items: 2, completed_items: 2, failed_items: 0, skipped_items: 0, not_found_items: 0,
  current_operation: null, created_at: "2026-09-07T10:00:00Z", started_at: "2026-09-07T10:00:00Z",
  completed_at: "2026-09-09T12:00:00Z", report_json_path: null, report_md_path: null,
  requests: [1, 2].map((row) => ({
    id: `r${row}`, row_index: row, status: "completed", search_mode: "immobile",
    comune: `Comune ${row}`, foglio: "1", particella: String(row), tipo_visura: "Completa",
    current_operation: null, processed_at: `2026-09-09T1${row}:00:00Z`,
    created_at: "2026-09-07T10:00:00Z", sister_credential_id: `c${row}`,
    artifact_dir: null, document_id: null, error_message: null,
  })),
  statistics: {
    duration_seconds: 180000, processed_items: 2, remaining_items: 0, progress_percent: 100,
    success_rate_percent: 100, completed_per_hour: 0.04, processed_per_hour: 0.04,
    estimated_remaining_seconds: 0, total_attempts: 3, average_attempts: 1.5,
    credentials_used: ["Alessandro", "Carlo"].map((label, index) => ({
      credential_id: `c${index + 1}`, label, sister_username: null,
      request_count: 1, execution_count: index + 1, completed_count: 1,
    })),
  },
};

for (const viewport of [{ width: 1440, height: 1000 }, { width: 390, height: 844 }]) {
  test(`batch names, counts and descending rows at ${viewport.width}px`, async ({ page }) => {
    await page.setViewportSize(viewport);
    const errors: string[] = [];
    page.on("pageerror", (error) => errors.push(error.message));
    await page.addInitScript(() => localStorage.setItem("gaia.access_token", "batch-e2e"));
    await page.route("**/api/**", async (route) => {
      const path = new URL(route.request().url()).pathname;
      let body: unknown = {};
      if (path.endsWith("/auth/me")) body = {
        id: 1, username: "admin", email: "admin@example.local", role: "super_admin", is_active: true,
        enabled_modules: ["elaborazioni", "catasto"], module_catasto: true,
      };
      else if (path.endsWith("/auth/my-permissions")) body = { sections: [], granted_keys: [] };
      else if (path.endsWith("/elaborazioni/batches/batch")) body = detail;
      else if (path.includes("notifications")) body = { items: [], unread_count: 0 };
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });
    });
    await page.routeWebSocket("**/ws/**", (socket) => socket.close());
    await page.goto("/elaborazioni/batches/batch");
    const stats = page.getByRole("region", { name: "Statistiche batch" });
    await expect(stats).toContainText("1 visure completate");
    await expect(stats).toContainText("2 avvii elaborazione");
    const rows = page.getByRole("table").getByRole("row");
    await expect(rows).toHaveCount(3);
    await expect(rows.nth(1)).toContainText("Comune 2");
    await expect(rows.nth(1)).toContainText("Carlo");
    await expect(rows.nth(2)).toContainText("Alessandro");
    await page.getByRole("button", { name: "Completate 2" }).click();
    await expect(rows.nth(1)).toContainText("Comune 2");
    await page.screenshot({ path: `/tmp/gaia-batch-${viewport.width}.png`, fullPage: true });
    expect(errors).toEqual([]);
  });
}
