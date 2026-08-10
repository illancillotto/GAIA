const { chromium } = require('@playwright/test');
const fs = require('fs');
const path = require('path');

const appDir = path.join(process.cwd(), 'src', 'app');
const outDir = path.join(process.cwd(), '..', 'reports', 'mobile-friendly-audit', 'all-subpages');
const screenshotsDir = path.join(outDir, 'screenshots');
const failuresDir = path.join(outDir, 'failures');
fs.mkdirSync(screenshotsDir, { recursive: true });
fs.mkdirSync(failuresDir, { recursive: true });

const username = process.env.PLAYWRIGHT_ADMIN_USERNAME;
const password = process.env.PLAYWRIGHT_ADMIN_PASSWORD;
if (!username || !password) {
  throw new Error('Set PLAYWRIGHT_ADMIN_USERNAME and PLAYWRIGHT_ADMIN_PASSWORD to run mobile audit.');
}

function walk(dir) {
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  return entries.flatMap((entry) => {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) return walk(full);
    return [full];
  });
}

function routeFromPageFile(file) {
  const rel = path.relative(appDir, path.dirname(file)).split(path.sep);
  const routeParts = rel.filter((part) => part !== '' && !part.startsWith('('));
  const route = '/' + routeParts.join('/');
  return route === '/.' ? '/' : route.replace(/\/page$/, '') || '/';
}

function screenshotName(route) {
  if (route === '/') return 'root.png';
  return route.replace(/^\//, '').replace(/[^a-zA-Z0-9]+/g, '-').replace(/^-|-$/g, '') + '.png';
}

const allPageFiles = walk(appDir).filter((file) => file.endsWith(`${path.sep}page.tsx`));
const dynamicRoutes = [];
const routes = [];
for (const file of allPageFiles) {
  const route = routeFromPageFile(file);
  if (route.includes('[') || route.includes(']')) {
    dynamicRoutes.push({ route, file: path.relative(process.cwd(), file) });
  } else {
    routes.push({ route, file: path.relative(process.cwd(), file) });
  }
}
routes.sort((a, b) => a.route.localeCompare(b.route));
dynamicRoutes.sort((a, b) => a.route.localeCompare(b.route));

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 390, height: 844 },
    deviceScaleFactor: 2,
    isMobile: true,
  });
  const page = await context.newPage();
  const consoleMessages = [];
  page.on('console', (msg) => {
    if (['error', 'warning'].includes(msg.type())) {
      consoleMessages.push({ type: msg.type(), text: msg.text().slice(0, 500), url: page.url() });
    }
  });
  page.on('pageerror', (err) => consoleMessages.push({ type: 'pageerror', text: String(err).slice(0, 500), url: page.url() }));

  const loginResponse = await page.request.post('http://127.0.0.1:8080/api/auth/login', {
    data: { username, password },
  });
  if (!loginResponse.ok()) {
    throw new Error(`Login API failed with status ${loginResponse.status()}`);
  }
  const loginPayload = await loginResponse.json();
  await page.goto('http://127.0.0.1:8080/', { waitUntil: 'domcontentloaded', timeout: 20000 });
  await page.evaluate((token) => window.localStorage.setItem('gaia.access_token', token), loginPayload.access_token);
  await page.reload({ waitUntil: 'domcontentloaded', timeout: 20000 });
  await page.waitForLoadState('networkidle', { timeout: 10000 }).catch(() => undefined);

  const results = [];
  for (const entry of routes) {
    const started = Date.now();
    const beforeConsole = consoleMessages.length;
    let navigationError = null;
    try {
      await page.goto(`http://127.0.0.1:8080${entry.route}`, { waitUntil: 'domcontentloaded', timeout: 20000 });
      await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => undefined);
    } catch (error) {
      navigationError = String(error).slice(0, 500);
    }

    const metrics = await page.evaluate(() => {
      const visible = (sel) => [...document.querySelectorAll(sel)].filter((el) => {
        const rect = el.getBoundingClientRect();
        const style = getComputedStyle(el);
        return rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none';
      });
      const desktopSidebar = [...document.querySelectorAll('aside')].find((el) => {
        const rect = el.getBoundingClientRect();
        const style = getComputedStyle(el);
        const className = typeof el.className === 'string' ? el.className : '';
        const looksLikeAppSidebar = className.includes('h-screen') && className.includes('w-[220px]');
        const occupiesMobileLeftRail = rect.left <= 2 && rect.top <= 2 && rect.width >= 180 && rect.width <= 260 && rect.height >= innerHeight * 0.75;
        return rect.width > 0 && rect.height > 0 && style.display !== 'none' && style.visibility !== 'hidden' && (looksLikeAppSidebar || occupiesMobileLeftRail);
      });
      const mobileMenu = [...document.querySelectorAll('button')].find((el) => el.getAttribute('aria-label') === 'Apri navigazione');
      const wideElements = [...document.body.querySelectorAll('*')]
        .map((el) => {
          const rect = el.getBoundingClientRect();
          const style = getComputedStyle(el);
          return {
            tag: el.tagName.toLowerCase(),
            text: (el.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 100),
            className: typeof el.className === 'string' ? el.className.slice(0, 180) : '',
            left: Math.round(rect.left),
            right: Math.round(rect.right),
            width: Math.round(rect.width),
            overflowX: style.overflowX,
            display: style.display,
          };
        })
        .filter((item) => item.width > 0 && (item.right > innerWidth + 2 || item.left < -2))
        .slice(0, 20);
      return {
        finalPath: location.pathname,
        title: document.title,
        innerWidth,
        scrollWidth: document.documentElement.scrollWidth,
        bodyScrollWidth: document.body.scrollWidth,
        hasVisibleDesktopSidebar: Boolean(desktopSidebar),
        mobileMenuVisible: Boolean(mobileMenu && mobileMenu.getBoundingClientRect().width > 0),
        visibleInteractiveCount: visible('a,button,input,select,textarea').length,
        mainText: (document.body.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 300),
        wideElements,
      };
    });

    const routeConsole = consoleMessages.slice(beforeConsole);
    const status = {
      noPageOverflow: metrics.scrollWidth <= metrics.innerWidth + 2,
      noVisibleDesktopSidebar: !metrics.hasVisibleDesktopSidebar,
      hasInteractiveOrContent: metrics.visibleInteractiveCount > 0 || metrics.mainText.length > 0,
      noNavigationError: !navigationError,
    };
    const ok = Object.values(status).every(Boolean);
    const shot = path.join(screenshotsDir, screenshotName(entry.route));
    let screenshotError = null;
    try {
      await page.screenshot({ path: shot, fullPage: false, timeout: 10_000 });
    } catch (error) {
      screenshotError = String(error).slice(0, 500);
    }
    if (!ok) {
      try {
        await page.screenshot({ path: path.join(failuresDir, screenshotName(entry.route)), fullPage: false, timeout: 10_000 });
      } catch (error) {
        screenshotError = screenshotError ?? String(error).slice(0, 500);
      }
    }
    results.push({
      ...entry,
      ok,
      status,
      navigationError,
      durationMs: Date.now() - started,
      screenshot: path.relative(path.join(process.cwd(), '..'), shot),
      screenshotError,
      consoleMessages: routeConsole,
      ...metrics,
    });
    console.log(`${ok ? 'OK   ' : 'FAIL '} ${entry.route} scroll=${metrics.scrollWidth}/${metrics.innerWidth} desktopSidebar=${metrics.hasVisibleDesktopSidebar} final=${metrics.finalPath}`);
  }

  const summary = {
    generatedAt: new Date().toISOString(),
    viewport: { width: 390, height: 844 },
    totalStaticRoutes: routes.length,
    ok: results.filter((r) => r.ok).length,
    failed: results.filter((r) => !r.ok).length,
    skippedDynamicRoutes: dynamicRoutes.length,
    routes,
    dynamicRoutes,
    results,
    consoleMessages,
  };
  fs.writeFileSync(path.join(outDir, 'all-subpages-mobile-audit-results.json'), JSON.stringify(summary, null, 2));
  await browser.close();
})();
