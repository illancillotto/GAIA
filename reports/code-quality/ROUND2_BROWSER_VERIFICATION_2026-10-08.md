# Round 2 — Browser Verification

## Scope and snapshot

Browser specialist owns this report and disposable resources only. No runtime,
test, configuration, registry, PROGRESS, baseline or threshold change.
Worktree `/home/cbo/CursorProjects/GAIA-campaign-20261008-integration`;
branch `refactor/complexity-campaign-20261008`.

- Preflight clean HEAD `3d6eca9e58ee6f8e4211ca63246b868d18a574a1`.
- Frozen UI source/build snapshot `3f9863fbba7c7d3d918ce19d8168383b32eaac32`.
- Final observed HEAD `a5fd8be8dddbc5b0b77b7371bf4c4b8ee9c7c38e` differs only
  by coordinator documents; runtime backend/frontend and E2E specs unchanged.
- Backend mount is this same integration snapshot, read-only. Latest backend
  commit present: `6ee6fdf8339753564fd466b14c3513b19a63d776` (Wiki metrics).
  The concurrent R2 P3 backend branch was **not** integrated/tested by this run.
- Coordinator's clean build PASS log `/tmp/gaia-r2-frontend-clean-build.log`
  supplied the production Next build; browser specialist did not duplicate it.

## Result

**Full configured E2E run: exit0, 52 PASS, 7 SKIPPED, 0 failed, 0 flaky**.
59 scenarios selected across all committed specs; single Chromium worker.
Start `2026-10-08T16:43:19.886Z`, duration71.975s.
No filter, retry, timeout change, skip addition, fixture relaxation or test edit.

Seven skips are preexisting conditional/obsolete scenarios, not PASS and not
new exclusions. This agrees with R1 final52PASS7skip; it does not claim all59
behaviors were exercised. Campaign/extreme-tail goal remains incomplete.

## Disposable real-auth environment

Resources created exclusively for this verification:

- Backend `gaia-r2-e2e-backend-20261008`, internal network
  `gaia-r2-e2e-20261008`, tmpfs `/data` and `/e2e` only.
- Cached image `gaia-sister-watchdog-verification:local`, immutable
  `sha256:dfd01b8c715ae92cf28fd5490242f9556ac774c93f03bf6d679422adf0bfed4c`.
  Python3.12.3, FastAPI0.118.0, mcp2.0.0 verified. No install/image build.
- Source `/home/cbo/CursorProjects/GAIA-campaign-20261008-integration/backend`
  mounted `/app:ro`, no production data, secret directory or Docker socket.
- Fresh SQLite `sqlite:////e2e/gaia.sqlite` initialized with SQLAlchemy metadata;
  synthetic JWT, encryption key and super_admin generated into0600 temporary
  environment. No production `.env` or credentials used/copied/output.
- Local production Next server at `127.0.0.1:13000` from integration build.
- Gateway `gaia-r2-e2e-proxy-20261008`, cached `nginx:alpine` image
  `sha256:e7257f1ef28ba17cf7c248cb8ccf6f0c6e0228ab9c315c152f9c203cd34cf6d1`,
  host network but listen restricted to `127.0.0.1:8080`.
  `/api/` forwards to freshly resolved internal bridge address `172.27.0.2:8000`;
  other requests to Next13000. WebSocket upgrade headers preserved.

Preflight ports8080/13000 were free. Internal network flag verified true;
backend root environment absent; database scheme sqlite. External TCP connect
returned errno101 (`Network is unreachable`), with no transmitted payload.
Before browser execution, actual `/api/auth/login` and `/api/auth/me` returned
**200** and real `super_admin`; frontend `/login` returned200.
Backend log records22 successful real login requests including preflight.
No disposable device-session cleanup was needed; configured stable device ID
prevented accumulation across real-login scenarios.

The first curl immediately after nginx container creation returned HTTP000
(exit7), before startup was ready. The subsequent readiness request returned200,
and login/me succeeded before Playwright started. This is recorded as startup
timing, not a silently claimed successful first probe or a test failure.
Next15.5.25 emitted its existing standalone-output/start recommendation, then
reported Ready; all browser requests used the production build successfully.

## Authentication and mocking limits

No global login mock or fabricated token/session was added by this verifier.
Environment-admin specs use the real backend for browser login and auth/me;
the preflight also independently validates live authentication.
**Not every existing spec is a fully live integration:** committed dotazioni,
operational controls, dashboards and some permission cases already inject
synthetic tokens or mock auth/domain endpoints. Those tests were run unchanged,
not mislabeled as52 end-to-end live-backend scenarios. Catasto admin specs
commonly use real login but mock domain data afterward.

This stack has SQLite metadata initialization, not PostgreSQL/PostGIS migration
validation. No real external provider, OAuth, Redis, MCP model fixture, QGIS
server, Martin or populated district/parcel corpus was provisioned. Cached
dependencies are not certified against every current requirement pin. No
claims of browser coverage percentages or production-system equivalence.

## Skip register

| Scenario | Existing reason | Impact |
| --- | --- | --- |
| Catasto anagrafica single search | Removed feature; bulk flow remains | Obsolete single search not exercised |
| Distretti → particella drilldown | No districts in disposable SQLite | Real seeded district/parcel navigation unverified |
| Distretti → anomalie drilldown | No districts in disposable SQLite | Real seeded anomaly navigation unverified |
| GIS console/toolbar desktop/mobile | Optional PLAYWRIGHT_GIS_TERRITORIO_ENABLED not enabled | Optional map/browser tools unverified |
| GIS consultation/measurements/print/QGIS | Same optional GIS flag | Live/native optional GIS interaction unverified |
| MCP console/tool history | Requires isolated synthetic Docker gateway opt-in | MCP console live integration unverified |
| MCP gateway→model preview | Requires explicit synthetic provider opt-in | External/model pipeline unverified |

Mobile-friendly audit receives synthetic admin environment and actually runs;
its credential-missing skip is **not** among the seven. The non-live synthetic
MCP source-failure scenario also runs; only the opt-in live counterpart skips.

## Command and artifacts

From integration/frontend, with ephemeral admin values passed through process
environment without logging them:

```bash
PLAYWRIGHT_BASE_URL=http://127.0.0.1:8080 \
PLAYWRIGHT_JSON_OUTPUT_NAME=/tmp/gaia-r2-e2e.json \
  npm run test:e2e -- --config=/tmp/gaia-campaign-playwright.config.ts \
  --workers=1 --reporter=line,json --output=/tmp/gaia-r2-e2e-artifacts
```

`PLAYWRIGHT_ADMIN_USERNAME` and `PLAYWRIGHT_ADMIN_PASSWORD` were supplied from
the synthetic environment by `/tmp/gaia-r2-run-e2e.py`, not committed or printed.
Config inherits the committed Playwright configuration, changes testDir for the
worktree and adds only stable device localStorage; no access token/cookie.

- Structured result `/tmp/gaia-r2-e2e.json`, SHA256
  `f60ca3f8e60fbd58c11e74b86b2cf2b2f46c1786a809a1109d36317a498c6a54`.
- Full log `/tmp/gaia-r2-e2e.log`, SHA256
  `4c9566778791e07e6ea0bd4704e7f766f726e4f58e63c2d55cffa278b9a91a0e`.
- Browser attachments `/tmp/gaia-r2-e2e-artifacts`, including mobile metrics
  and screenshots where explicitly attached by existing specs.
- Backend `/tmp/gaia-r2-backend.log`, gateway `/tmp/gaia-r2-nginx.log`,
  Next `/tmp/gaia-r2-next.log`; no backend ERROR/Traceback/HTTP500 observed.
- Temporary recipes `/tmp/gaia-r2-{e2e-bootstrap,auth-check,run-e2e}.py`,
  `/tmp/gaia-r2-nginx.conf`, no embedded secrets retained.
- Playwright config SHA256
  `d61a5ffe60b712e177c5e02206b07bbf53bbe1e8616b3f6b3ed749b199239074`;
  original committed config SHA256
  `cdbe81cf6276d83419a5916a9434f85713cb48cb58fca6c8375331f728fa4c3e`.

Result JSON has `errors: []`, expected52, skipped7, unexpected0 and flaky0.
No failure diagnosis or rejected regression required in this full run.
Backend logs were saved before removing containers.

## Cleanup

Removed only verifier-owned backend/proxy and internal network by exact name.
Stopped only this verifier's Next exec session29098 using Ctrl-C; ports8080
and13000 confirmed free afterward. Synthetic environment file deleted.
Disposable SQLite/tmpfs disappeared with the backend; no production volume
removed and no project-wide compose command executed.
Existing `gaia-release-*` containers and their PostgreSQL15437 remain untouched;
other Next server13007 likewise untouched. Git working tree clean before adding
this report. Runtime frozen snapshot still matches backend/frontend/E2E spec
blobs, despite coordinator documentation commits during execution.

## Handoff

Browser gate is **PASS_WITH_PREEXISTING_SKIPS**, not all-scenario coverage or
global campaign completion. Integrate no runtime based on this result alone:
P3 backend still requires independent integration/testing after this snapshot.
Coordinator owns final campaign decision, remaining extreme hotspot work,
coverage/ratchet aggregation and report integration.
