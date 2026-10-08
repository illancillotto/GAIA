# Round 3 — Browser Verification

## Scope and snapshot

Browser verification owns this report and its named disposable resources only.
No runtime, tests, committed configuration, ownership registry, PROGRESS,
complexity tooling, baseline, threshold, exclusion or ignore was modified.
Worktree `/home/cbo/CursorProjects/GAIA-campaign-20261008-integration`, branch
`refactor/complexity-campaign-20261008`.

- Ownership snapshot `f851553037b92bcc75f54217384c0fe733767a7c`.
- Execution preflight clean HEAD `2e4a87cc99c044e737efd3401a2684bda1abc07c`.
- Final observed verification HEAD `7a956dc9490c577afe4091564aa6cf95ad3b0582`.
  Coordinator documents changed during execution, but `git diff` found no
  backend/frontend changes from the ownership snapshot through this HEAD.
  Concurrent untracked `ROUND3_VERIFICATION_2026-10-08.md` was preserved.
- Latest integrated backend runtime commit
  `0b1a0d3767e4e75b4cf34cfe0daf737609e6ccb0`.
- Latest integrated frontend runtime commit
  `b0dd9228b8f2f492264b372bee0a9875b05426f9`.
- Frozen backend tree `32c1985fc44429f4ed3ea6938e4f62fa7bacb07e`;
  frontend tree `d842dc3f46ef2dec860b8c25cebc36957426418a`.
- Authoritative merge-base remains
  `55a1b1d35911451e018b662c2acc450bf5994ea2`.

The Coordinator supplied the production clean build from
`/tmp/gaia-r3-frontend-clean-build.log` and full frontend unit result
4099 PASS / 283 files from `/tmp/gaia-r3-frontend-full-tests.log`.
Those commands were not duplicated by this browser verifier. Backend full
suite, coverage, ratchet, Graphify and campaign completion belong to their
separate owners; this report does not certify them.

## Results — all attempts retained

| Attempt | Scope | Start UTC | Duration | Exit | Pass | Skip | Failed | Framework flaky |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Initial | All 59 configured scenarios | 2026-10-08T17:27:01.746Z | 89.231s | 1 | 51 | 7 | 1 | 0 |
| Diagnostic | Exact unchanged failing GIS scenario | 2026-10-08T17:29:37.403Z | 4.337s | 0 | 1 | 0 | 0 | 0 |
| Confirmation | All 59 configured scenarios | 2026-10-08T17:30:24.310Z | 83.699s | 0 | 52 | 7 | 0 | 0 |

The **final full confirmation run is PASS**, but the initial full run is
**FAIL** and remains recorded. No assertions, fixtures, credentials policy,
timeouts, retry configuration or skips were relaxed. All attempts use one
Chromium worker. The diagnostic filter is not presented as full verification.

Playwright reports zero framework-flaky tests because each invocation has no
configured automatic retry. The pass-after-failure across independent runs is
nevertheless an **observed intermittent GIS failure**, not an immaculate
first-run result or proof that the underlying issue has been fixed.
Final gate acceptance with that residual risk is a Coordinator decision.
This is not a declaration that the overall campaign is complete.

## Initial GIS failure and diagnosis

`frontend/tests/e2e/catasto-gis.spec.ts:365`,
`catasto gis fiscal search opens parcel role details`, failed at line383:
the repeated default-center click on `canvas.maplibregl-canvas` did not make
`[data-gis-parcel-panel]` contain visible exact text `A ruolo` within the
existing 10-second `toPass` window. The final error also records an outstanding
popup-request wait when the test ended.

Trace evidence:

- Fiscal search request returned200; search result assertions passed.
- **Zero** `/api/catasto/gis/particella/.../popup` requests were recorded.
- Screenshot shows the highlighted polygon left of canvas center; the default
  center-click is not visibly within that polygon in the captured final state.
- Native MapLibre map exists; this was not the WebGL-unavailable fallback.
- Unprovisioned native `/tiles/...` requests include404s. Optional DUI
  latest-layer and GIS territorio/layers APIs return503 in this disposable
  stack. Trace also records canceled/failing presence-heartbeat requests.
  No backend ERROR, Traceback or HTTP500 was found in the full backend log.

The evidence is consistent with an intermittent map-fit/viewport/click-target
interaction, but does **not** prove its exact root cause. Missing optional tile
services alone cannot be declared causal: the unchanged isolated diagnostic
and full confirmation both passed on the same stack.

`MapContainer.tsx` and this E2E spec are unchanged by the campaign. The campaign
diff in the GIS page only extracts Excel-reference alias normalization and
does not alter this fiscal-search/click flow. No R3 runtime refactor touched
GIS. That excludes a direct diff in the failing handler, not every possible
indirect regression; definitive attribution remains **UNKNOWN**. No code fix,
test weakening, retry-until-green loop or native-map instrumentation was
introduced. One focused diagnostic and one complete confirmation were run,
with the original artifacts retained.

## Disposable real-auth stack

- Backend container `gaia-r3-e2e-backend-20261008` on internal Docker network
  `gaia-r3-e2e-20261008`; source mounted `/app:ro` from this integration worktree.
- Cached image `gaia-sister-watchdog-verification:local`, immutable ID
  `sha256:dfd01b8c715ae92cf28fd5490242f9556ac774c93f03bf6d679422adf0bfed4c`.
  No dependency installation or image build.
- Disposable SQLite `sqlite:////e2e/gaia.sqlite`, metadata initialized with
  SQLAlchemy; `/data` and `/e2e` tmpfs, no production volume, credentials
  directory or Docker socket.
- Synthetic admin, JWT secret and credential master key generated locally into
  exclusive-create mode0600 `/tmp/gaia-r3-e2e-backend.env`. Synthetic secret
  values were not printed or committed; no production environment was loaded.
- Production Next15.5.25 at loopback `127.0.0.1:13000`, using the Coordinator's
  clean build. Its existing standalone-output/start warning did not prevent
  readiness or requests.
- Gateway `gaia-r3-e2e-proxy-20261008`, cached `nginx:alpine`, immutable ID
  `sha256:e7257f1ef28ba17cf7c248cb8ccf6f0c6e0228ab9c315c152f9c203cd34cf6d1`.
  Host-network gateway binds only `127.0.0.1:8080`; `/api/` forwards to the
  dynamically inspected backend address `172.27.0.2:8000`; other paths to
  Next13000. WebSocket upgrade headers are preserved.

Ports8080/13000 were free before startup. Verified internal network=true,
backend configured env-file absent, database scheme=sqlite and backend
external TCP connect errno101 (`Network is unreachable`; no payload sent).
Before browser execution frontend `/login`, real `/api/auth/login` and real
`/api/auth/me` all returned200, with role `super_admin`. The backend log records
44 successful real login requests across preflight and the three invocations.

Backend network isolation does **not** imply an offline browser. The captured
GIS trace contains public `tile.openstreetmap.org` requests (37) and one
`lh3.googleusercontent.com` request alongside localhost. Existing browser code
was not intercepted or modified; public basemap fetching is an explicit
environmental dependency/limit. No production backend integration was enabled.

## Authentication and coverage limits

No global mocked login, fabricated access token or session cookie was added.
Environment-admin specs use the real backend for login/auth; the temporary
Playwright configuration adds only stable localStorage device identity
`gaia.client_device_id=gaia-disposable-campaign-browser` and no token/cookie.

Some committed specs already inject synthetic tokens or mock auth/domain
responses; Catasto admin tests typically use real login then mocked domain
data. The 52 passing scenarios are not all fully live-provider integration.
SQLite metadata initialization is not PostgreSQL/PostGIS migration validation.
No native Martin/QGIS server, populated parcel/district dataset, OAuth/Redis,
live MCP gateway/model provider or external business portal was provisioned.
Cached image dependencies were not reconciled against every current pin.
There is no browser coverage-percent or production-equivalence claim.

## Skip register

All seven skips are unchanged, present in both full runs and not counted PASS.

| Scenario | Existing reason | Impact |
| --- | --- | --- |
| Catasto single anagrafica search | Feature removed; bulk flow remains | Obsolete single search unexercised |
| Distretti → particella drilldown | No seeded districts in SQLite | Seeded district/parcel navigation unverified |
| Distretti → anomalie drilldown | Same missing district corpus | Seeded anomaly navigation unverified |
| GIS desktop/mobile console and toolbar | Optional GIS territorio flag disabled | Optional native tools unverified |
| GIS consultation/measurements/print/QGIS | Same optional flag | Full native GIS integration unverified |
| MCP live console and tool history | Synthetic Docker gateway opt-in absent | Live console integration unverified |
| MCP live gateway → model preview | Explicit synthetic provider opt-in absent | Model pipeline unverified |

Mobile-friendly audit actually runs with the synthetic admin environment; its
missing-credentials condition is not among these skips. The synthetic non-live
MCP source-failure scenario also runs unchanged.

## Commands and reproducible evidence

Full commands from integration/frontend, with synthetic admin variables passed
privately through subprocess environment:

```bash
PLAYWRIGHT_BASE_URL=http://127.0.0.1:8080 \
PLAYWRIGHT_JSON_OUTPUT_NAME=/tmp/gaia-r3-e2e.json \
  npm run test:e2e -- --config=/tmp/gaia-campaign-playwright.config.ts \
  --workers=1 --reporter=line,json --output=/tmp/gaia-r3-e2e-artifacts

PLAYWRIGHT_BASE_URL=http://127.0.0.1:8080 \
PLAYWRIGHT_JSON_OUTPUT_NAME=/tmp/gaia-r3-e2e-confirmation.json \
  npm run test:e2e -- --config=/tmp/gaia-campaign-playwright.config.ts \
  --workers=1 --reporter=line,json --output=/tmp/gaia-r3-e2e-confirmation-artifacts
```

The diagnostic uses identical options with separate `gis-diagnostic` artifacts
and only `--grep="catasto gis fiscal search opens parcel role details"`.
`PLAYWRIGHT_ADMIN_USERNAME/PASSWORD` are supplied from the synthetic environment
by the retained `/tmp/gaia-r3-{run-e2e,rerun-gis,run-e2e-confirmation}.py` recipes.
Bootstrap/auth recipes and nginx config remain without embedded secret values.

| Evidence | SHA256 |
| --- | --- |
| `/tmp/gaia-r3-e2e.json` | `64a0ca9bca16233d038c92833022f520da7823106682e599a4e14ef11ee36719` |
| `/tmp/gaia-r3-e2e.log` | `a867ee7ad88a441b9078be6bfb3bbb99b43203da98e3048217d0d9c9f440ab9a` |
| `/tmp/gaia-r3-gis-diagnostic.json` | `ac5c4cf9fdef75413e4a1315542585592843ea0bc1b8829cac0b0dcd3adf17db` |
| `/tmp/gaia-r3-gis-diagnostic.log` | `61154cb143456e2e153274d53fcf31ba293aea6005b78f97b6f402797f7ce88f` |
| `/tmp/gaia-r3-e2e-confirmation.json` | `4da989952a4c627f034e29df6eb4e307e4e0612939b8f0a4dd39771d54b6f3ef` |
| `/tmp/gaia-r3-e2e-confirmation.log` | `08c0ecfe992d880933c142c50221b0aac9e14e4f45ba224f20fbcc5022b0a458` |
| `/tmp/gaia-r3-backend.log` | `903ed7f6e2667efe68653b316fc8ccfafc56278fd353f7a8ce4d4883324aaf26` |
| `/tmp/gaia-r3-nginx.log` | `cf365187da6d2cedeea37ea08b32e201af2a748745b9ceec7a7a48557160189d` |
| `/tmp/gaia-r3-next.log` | `ca6916534453a55411668b74ce3c8c649e2fdd140ef20af212149e96647ee412` |
| Temporary Playwright config | `d61a5ffe60b712e177c5e02206b07bbf53bbe1e8616b3f6b3ed749b199239074` |
| Committed Playwright config | `cdbe81cf6276d83419a5916a9434f85713cb48cb58fca6c8375331f728fa4c3e` |

Original failure screenshot, error-context, video and trace.zip remain under
`/tmp/gaia-r3-e2e-artifacts/catasto-gis-catasto-gis-fi-545c3-h-opens-parcel-role-details-chromium/`.
Confirmation/mobile attachments remain in their separately named directories.
These local artifacts are not committed and may contain disposable auth data;
retain locally and redact before external sharing.

## Cleanup and residual action

Saved logs before removing **only** the named R3 backend/proxy containers and
R3 internal network. Stopped only owned Next session70039 (exit130), deleted
synthetic mode0600 environment, and verified ports8080/13000 free. Retained
non-secret recipes/config and verification artifacts.

Existing release20261007 resources remained. Preflight also observed
`gate-quality-resolution-postgres-20261008`; it was absent in the final Docker
listing due to concurrent owner activity, not this verifier's cleanup. It was
never stopped, queried or removed by this task. Other agents' files, staged
work and reports were not included in this report-only change.

Recommended follow-up: reserve explicit ownership for a separate native GIS
characterization of fit/resize/center-click ordering on a seeded stack. Preserve
this intermittent failure until its cause is demonstrated; do not silently
replace the original run with the confirmation result. No refactoring or
baseline change is authorized by this verification report.
