# ANPR and E2E validation follow-up — 2026-10-07

## Scope and ownership

Follow-up explicitly authorized after historical mismatch reconciliation:
repair the legacy ANPR test and provision an isolated E2E backend, then update
obsolete browser tests. A separate user decision authorizes the GIS console
layout fix exposed by those tests. No business logic, API, database schema,
permissions, complexity baseline, thresholds or coverage policy changes.

Specialists own disjoint ANPR/Catasto, import and GIS test files; the coordinator
owns integration, mobile test synchronization, validation and documentation.
Concurrent campaign/unrelated working-tree changes remain untouched. No commits.

## Corrections and characterization

| Area | Root cause | Correction and preserved checks |
| --- | --- | --- |
| ANPR | Test patches removed `utenze_router.settings` | Patch `utenze.routes.support.settings`; keep frozen router clock and exact deceased KPI values 1/2/3 |
| Bulk anagrafica | Old synchronous endpoint and picker label | Mock current multipart job upload/completed result; assert filename/source rows, FOUND/NOT_FOUND, exports and error message |
| Distretti | Duplicate labels, updated formatting and modal navigation | Scope names to table; assert 15.5 ha and rounded currency totals; assert visible detail iframe with original UUID |
| Meter readings | Incomplete record fixture crashes drawer | Supply required audit/classification fields; assert operator/crop in drawer, validation and exact import counts |
| Import | Missing preview/confirmation, removed ZIP UI, obsolete report labels | Exercise current Excel upload/preview/confirm and historical report; preserve numeric/anomaly checks |
| GIS tests | Console closed by default, new layer/search controls | Exercise real district filter, parsed XLSX request, save/update/remove/reload/delete and fiscal search-to-map-to-role details |
| Mobile audit | Layout measured while fonts are loading | Await `document.fonts.ready`; retain 390px viewport and +2px tolerance |
| GIS runtime CSS | Flex layer section collapses under tall non-shrinking controls | Make direct console `div` sections natural-height (`flex: none`); existing outer scroll reaches every action |

The GIS defect reproduces at **1280×720**: `Salva permanentemente` is enabled
but intercepted by adjacent sections. Tests keep native clicks and the original
viewport; no force clicks, JavaScript-triggered save, wider viewport or skip
conceals this failure. The CSS-only fix is four added lines in
`frontend/src/components/catasto/gis/gis-workspace.module.css`. It does not
change React state, persistence or API calls. CSS is outside callable metrics;
no numerical complexity reduction is claimed for this repair.

The old GIS fiscal-detail assertions are retained in a separate third test:
select the unified-search result, focus the map and click the actual parcel;
verify the specific parcel UUID request, `A ruolo` and `CFM-4201`. Tests are
split to keep archive behavior independently verifiable, not to drop coverage.

## Disposable E2E environment

- Current backend source mounted read-only at `/app`; SQLite and storage use
  fresh `/e2e` and `/data` tmpfs. No production database, volumes, secret mounts,
  repository `.env`, Docker socket or production Compose services.
- Cached image `gaia-sister-watchdog-verification:local`, immutable ID
  `sha256:dfd01b8c715ae92cf28fd5490242f9556ac774c93f03bf6d679422adf0bfed4c`;
  Python 3.12.3, MCP 2.0.0, FastAPI 0.118.0. The first older image failed import
  with missing `mcp`; it was replaced, not mistaken for a successful run.
- Dedicated internal Docker network; outbound connection check returns errno
  101. Nginx gateway binds `127.0.0.1:8080`, routes `/api/` to the isolated
  backend and other requests to Next on `127.0.0.1:13000`.
- Real `/api/auth/login` and `/api/auth/me` return 200 using a synthetic admin.
  Schema uses SQLAlchemy metadata, not production migrations or imported data.
- Fresh browser contexts initially exhausted the real 20-device account limit.
  Only disposable device/session rows were reset. A temporary Playwright
  storage state supplies a stable browser device ID; authentication and device
  enforcement remain enabled. No tests share an authentication token.

Reproduction details, image/environment checks and startup commands are in
`/tmp/gaia-followup-environment-review.md`. Temporary Playwright config:
`/tmp/gaia-followup-playwright.config.ts`; it imports the repository config and
adds only testDir/storageState. Credentials are synthetic and not documented.
All browser artifacts use unique `/tmp` paths to avoid collisions.

## Executed validation

| Check | Result |
| --- | --- |
| Original ANPR failure | Reproduced missing settings AttributeError on isolated SQLite |
| Final ANPR file | 48 PASS; imports/UTC aligned with Ruff; all original assertions retained |
| ANPR counterchecks | All three independently corrupted deceased KPI values fail original assertions |
| Full backend | **6361 PASS, 448 skipped**, 1458.13s; no failures |
| Frontend smoke | 18 PASS |
| Frontend full unit, `--maxWorkers=2` | **3986 PASS, 277 files**, 189.97s |
| Initial unrestricted parallel unit run | 3978 PASS, 8 timeout failures; same suite passes with two workers, no timeout changes |
| Typecheck and backend/frontend lint | PASS; existing frontend warnings remain |
| Clean production build | PASS after CSS fix |
| Tooling suite | 169 PASS |
| `BASE_REF=main make complexity-ratchet` | PASS, zero findings |
| Mobile repeats | 3 PASS after font synchronization; injected 600px overflow still rejected |
| ANPR owner's three browser specs | 6 PASS, 1 unchanged retired-feature skip |
| Two import browser specs | 7 PASS, no skips |
| Adjacent `GisWorkspace.tsx` coverage | 100%: 27 statements, 12 branches, 11 functions, 22 lines |

Backend command from `backend/`:
`APP_ENV=test DATABASE_URL=sqlite:////tmp/gaia-followup-pytest.db timeout --signal=TERM 2400 .venv/bin/python -m pytest -q -o addopts='' --tb=short`.
The full suite collected the ANPR semantic fix before the final import/UTC
style adjustment; the final file separately passed all 48 tests. Skips are not
passes or validation of unavailable PostgreSQL dependencies.

Frontend commands: `npm test`, `npm run test:unit -- --maxWorkers=2`,
`npm run typecheck`, `npm run lint`, `npm run build:clean`.
Coverage uses `VITEST_COVERAGE_INCLUDE=src/components/catasto/gis/GisWorkspace.tsx`
and the existing `gis-workspace.test.tsx`, with reports only under `/tmp`.
That component is unchanged; this evidence does not pretend CSS has V8 branches.

Initial E2E run with real auth: 38 PASS, 13 FAIL, 7 skipped. It exposes obsolete
fixtures/selectors, font-loading timing and device-limit exhaustion previously
hidden by login 404. Intermediate Catasto runs are retained as failed evidence,
not counted as final acceptance.

## Final browser and CSS verification

Built GIS suite: **3 PASS at 1280×720**. The complete XLSX lifecycle also passes
at 390×844. Chromium CSS coverage records the exact new compiled rule in a used
range on both viewports. This exercises the entire added rule, not a claim of
100% V8 coverage for CSS or every pre-existing stylesheet declaration.

Negative countercheck removes only that rule from the served CSS response,
without changing the repository/build: the layer section collapses from 197px
to 16px and the native save click fails again. The rule-removal run is an
**expected failure**, not a passing application test.

Evidence: `/tmp/gaia-followup-owner-gis.log`,
`/tmp/gaia-gis-css-built-desktop.log`, `/tmp/gaia-gis-css-built-mobile.log`,
`/tmp/gaia-gis-css-removal.log`.

**Final complete rebuilt browser suite: 52 PASS, 7 skipped, zero failures and
zero flaky tests, 49.7s.** The extra GIS test raises collection from 58 to 59.
Evidence: `/tmp/gaia-followup-e2e-final.json` and `.log`.

Command from `frontend/`, with synthetic `PLAYWRIGHT_ADMIN_USERNAME` and
`PLAYWRIGHT_ADMIN_PASSWORD` supplied only for the disposable backend:

```sh
PLAYWRIGHT_BASE_URL=http://127.0.0.1:8080 \
PLAYWRIGHT_JSON_OUTPUT_NAME=/tmp/gaia-followup-e2e-final.json \
npm run test:e2e -- --config=/tmp/gaia-followup-playwright.config.ts \
  --workers=2 --output=/tmp/gaia-followup-e2e-final-results --reporter=line,json
```

For reproduction, the temporary config imports `frontend/playwright.config.ts`,
retains all its options, sets absolute `testDir`, and adds
`use.storageState = { cookies: [], origins: [{ origin: "http://127.0.0.1:8080",
localStorage: [{ name: "gaia.client_device_id", value: "gaia-disposable-e2e-browser" }]
}] }`. It contains no access token and does not mock login.

Seven existing skip conditions remain: one retired single-search scenario,
two unseeded real Catasto drilldowns, two optional GIS/Territorio checks, and
two MCP/provider integration opt-ins. No skip was added to silence a failure.
Full real-domain coverage is not inferred from the passing browser count.

## Limits

SQLite/mocked domain routes do not certify live PostGIS, QGIS, Martin, SISTER,
OAuth or production data. The campaign's quantitative reduction targets remain
unmet. These fixes close validation blockers, not the global complexity program.
Raw `/tmp/gaia-followup-*` artifacts are local and ephemeral. The disposable
backend/proxy/network and Next process are stopped/removed after validation;
synthetic credentials/token files are deleted. Browser/log evidence is retained.
Graphify frontend update reports no code-topology changes; CSS does not add
AST nodes. Domain/platform documentation graphs are refreshed separately.
