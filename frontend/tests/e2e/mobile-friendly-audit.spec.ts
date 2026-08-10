import { expect, test, type Page } from "@playwright/test";

const username = process.env.PLAYWRIGHT_ADMIN_USERNAME;
const password = process.env.PLAYWRIGHT_ADMIN_PASSWORD;

const pagesToAudit = [
  { path: "/", name: "home" },
  { path: "/me", name: "me" },
  { path: "/catasto", name: "catasto" },
  { path: "/ruolo", name: "ruolo" },
  { path: "/ruolo/tributi", name: "ruolo-tributi" },
  { path: "/gis/catalogo", name: "gis-catalogo" },
  { path: "/nas-control", name: "nas-control" },
];

async function loginAsAdmin(page: Page) {
  if (!username || !password) {
    throw new Error("Set PLAYWRIGHT_ADMIN_USERNAME and PLAYWRIGHT_ADMIN_PASSWORD to run mobile audit.");
  }

  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/login");
  await expect(page.getByLabel("Username o email")).toBeVisible();
  const adminUsername = username;
  const adminPassword = password;
  await page.getByLabel("Username o email").fill(adminUsername);
  await page.locator("input#password").fill(adminPassword);
  await page.getByRole("button", { name: "Accedi alla piattaforma" }).click();
  await page.waitForURL("**/");
}

test.describe("mobile friendly smoke audit", () => {
  test.beforeEach(() => {
    test.skip(!username || !password, "Set PLAYWRIGHT_ADMIN_USERNAME and PLAYWRIGHT_ADMIN_PASSWORD to run mobile audit.");
  });

  test("login page fits a 390px mobile viewport", async ({ page }, testInfo) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/login");
    await expect(page.getByRole("button", { name: "Accedi alla piattaforma" })).toBeVisible();
    const metrics = await page.evaluate(() => ({
      innerWidth: window.innerWidth,
      scrollWidth: document.documentElement.scrollWidth,
      bodyScrollWidth: document.body.scrollWidth,
      viewportMeta: document.querySelector('meta[name="viewport"]')?.getAttribute("content") ?? null,
    }));
    await testInfo.attach("login-mobile-metrics", {
      body: JSON.stringify(metrics, null, 2),
      contentType: "application/json",
    });
    await page.screenshot({ path: testInfo.outputPath("login-mobile.png"), fullPage: true });
    expect(metrics.scrollWidth, JSON.stringify(metrics)).toBeLessThanOrEqual(metrics.innerWidth + 2);
  });

  test("authenticated pages do not overflow and expose usable navigation on mobile", async ({ page }, testInfo) => {
    await loginAsAdmin(page);
    const results: Array<Record<string, unknown>> = [];

    for (const entry of pagesToAudit) {
      await page.goto(entry.path);
      await page.waitForLoadState("networkidle", { timeout: 20_000 }).catch(() => undefined);
      await page.screenshot({ path: testInfo.outputPath(`${entry.name}-mobile.png`), fullPage: true });

      const metrics = await page.evaluate(() => {
        const navLinks = Array.from(document.querySelectorAll('a[href], button')).filter((element) => {
          const rect = element.getBoundingClientRect();
          const style = window.getComputedStyle(element);
          return rect.width > 0 && rect.height > 0 && style.visibility !== "hidden" && style.display !== "none";
        });
        const sidebar = Array.from(document.querySelectorAll("aside")).find((element) => {
          const rect = element.getBoundingClientRect();
          const style = window.getComputedStyle(element);
          return rect.width > 0 && rect.height > 0 && style.visibility !== "hidden" && style.display !== "none";
        });
        const sidebarRect = sidebar?.getBoundingClientRect();
        const wideElements = Array.from(document.body.querySelectorAll("*"))
          .map((element) => {
            const rect = element.getBoundingClientRect();
            const style = window.getComputedStyle(element);
            return {
              tag: element.tagName.toLowerCase(),
              text: (element.textContent ?? "").replace(/\s+/g, " ").trim().slice(0, 80),
              className: typeof (element as HTMLElement).className === "string" ? (element as HTMLElement).className : "",
              left: Math.round(rect.left),
              right: Math.round(rect.right),
              width: Math.round(rect.width),
              display: style.display,
              overflowX: style.overflowX,
            };
          })
          .filter((item) => item.width > 0 && (item.right > window.innerWidth + 2 || item.left < -2))
          .slice(0, 20);
        return {
          path: location.pathname,
          innerWidth: window.innerWidth,
          scrollWidth: document.documentElement.scrollWidth,
          bodyScrollWidth: document.body.scrollWidth,
          hasSidebar: Boolean(sidebar),
          sidebarWidth: sidebarRect ? Math.round(sidebarRect.width) : null,
          sidebarLeft: sidebarRect ? Math.round(sidebarRect.left) : null,
          sidebarRight: sidebarRect ? Math.round(sidebarRect.right) : null,
          visibleInteractiveCount: navLinks.length,
          wideElements,
        };
      });
      results.push({ name: entry.name, ...metrics });
    }

    await testInfo.attach("authenticated-mobile-audit", {
      body: JSON.stringify(results, null, 2),
      contentType: "application/json",
    });

    for (const result of results) {
      expect(result.scrollWidth, JSON.stringify(result)).toBeLessThanOrEqual(Number(result.innerWidth) + 2);
      expect(result.visibleInteractiveCount, JSON.stringify(result)).toBeGreaterThan(0);
    }
  });
});
