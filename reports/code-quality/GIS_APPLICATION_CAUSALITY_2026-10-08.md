# GIS — Controlled Real-Application Causality Investigation

## Scope and disposition

Report-only investigation authorized by ownership registry `3d7a998c` and
baseline-resource extension `9f072bf3`. No repository runtime, E2E spec,
configuration, retry, timeout, baseline, threshold, exclusion or ignore was
modified. Classification: **NO_CHANGE — DIAGNOSTIC_ONLY**.

**Demonstrated in both application snapshots:** an early native canvas gesture
interrupts the real search camera animation, leaves the searched parcel away
from canvas center, and produces neither a parcel-popup request nor its panel.
Waiting for actual camera completion before the same center click opens the
panel. This is an **independently preexisting camera/center-click timing race**,
not a mechanism introduced by this campaign.

**Still UNKNOWN:** whether this was the definitive cause of the original R3
failure. Its trace did not record camera events. The new experiments establish
the mechanism and its preexistence; they cannot recover historical telemetry.
This report neither accepts residual risk nor authorizes the next runtime wave.

## Snapshots and unchanged inputs

| Item | Authoritative clean baseline | Integrated application |
| --- | --- | --- |
| Source commit | `55a1b1d35911451e018b662c2acc450bf5994ea2` | `70ae035d`, runtime-identical to diagnosis HEAD `3d7a998c` |
| Worktree | `GAIA-campaign-20261008-gis-baseline` | `GAIA-campaign-20261008-gis-causality` |
| Branch | Detached baseline | `refactor/complexity-gis-causality` |
| Backend/front-end | Both mounted/built from baseline | Both mounted/built from integrated source |
| Production build | PASS, exit0 | PASS, exit0 |

Integrated backend tree `32c1985fc44429f4ed3ea6938e4f62fa7bacb07e` and
frontend tree `1ddc7041881a24259e30dd81491aafba44fdb104` are exactly those of
`70ae035d`. Both worktrees were clean before and after browser/build activity;
only this report is subsequently added. The dirty main worktree was never
used as a source, copied, reset, stashed, committed or merged.

Both builds use the same installed dependency directory, Chromium executable,
1280x720 viewport, real synthetic-admin authentication, and domain fixtures
from their unchanged `frontend/tests/e2e/catasto-gis.spec.ts`. That spec has
SHA256 `71188977e1e20997c226d434788e6361af7c32afd5ccb0afdc4bf99895217ea7`
in both snapshots. Installed versions: Next15.5.25, React18.3.1,
MapLibre6.9.0, Playwright1.59.1, Chromium147.0.7727.15.

The campaign GIS diff is only Excel-reference normalization extraction in
`frontend/src/app/catasto/gis/page.tsx` and `excel-references.ts`. Native map,
unified-search hook, spec, Next configuration and package lock are unchanged.
Source inspection supports the comparison but is not its causal proof.

## Method

Disposable script `/tmp/gaia-gis-application-causality.cjs` reads the committed
spec, transpiles it with installed TypeScript, and uses its actual
`setupGisWorkspace` and fiscal-search test callback. It does not substitute
application state, handlers, camera methods or search responses beyond the
committed spec's existing route fixtures. Each scenario has a fresh browser
context and logs in against the real isolated backend.

After the real map exists, browser-only instrumentation locates it through
React fiber state. It records real `fitBounds` arguments, native mousedown,
camera start/move/end, map click, projected parcel position, actual rendered
search-layer center hits, request URLs and page errors. A pass-through wrapper
around `fitBounds` records calls without changing arguments or return value.
A pass-through public `stop` wrapper is also present, but native gesture
interruption does not call that public wrapper; evidence of stopping comes
from actual camera events and persistent final camera position, not a claimed
captured public-stop call. Installed MapLibre `src/ui/handler_manager.ts:473`
calls its separate `this._camera.stop(true)` when native handlers become active;
that source SHA256 is
`072306fde49f5d75e28b18a5071acf45570f8ecc2f61adf87b4b73b0221c9ca2`.
Instrumentation is absent from repository source.

- **Exact callback:** the committed fiscal-search callback, including its
  existing10-second `toPass`,1000ms panel assertion and retry intervals, runs
  unchanged. The diagnostic waits for map instrumentation after navigation;
  this is therefore not a timing-identical replay or a full Playwright-suite
  certification. No runner-wide PASS is inferred from this standalone callback.
- **Fast-native intervention:** precompute visible result, toolbar and canvas
  bounds; real `page.mouse.click` selects the result, closes search, then clicks
  canvas center without locator actionability delays. No private application
  callback or synthetic DOM event is invoked. Actual gesture timing is measured,
  not assumed from a requested delay.
- **Completion control:** identical native result/toggle clicks, then wait until
  a recorded fit has produced `moveend` and `map.isMoving()` is false before
  clicking the same canvas center. This is an experimental control, not a
  committed synchronization fix or increased test timeout.

Every valid scenario records exactly one fit with unchanged duration700ms,
padding48 and maxZoom17. After interventions, the camera is observed again
900ms later; no resumed movement or extra fit occurs. Requests and traces are
retained for every attempt, including failed setup.

## Controlled matrix — both real applications

Times are milliseconds from actual `fitBounds`; hits refer to actual rendered
search-overlay features at local canvas center `[530,277.5]`.

| Snapshot/run | Scenario | Native gesture ms | Moveend ms | Final center longitude | Center hits | Popup requests | Panel |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| Integrated2 | Early native gesture | 208.0 | 208.5 | 8.638063980 | 0 | 0 | Absent |
| Integrated3 | Camera-completion control | 836.0 | 716.9 | 8.555000000 | 1 | 1 | Visible |
| Integrated4 | Early native gesture | 237.4 | 237.9 | 8.591260691 | 0 | 0 | Absent |
| Integrated5 | Camera-completion control | 830.8 | 710.9 | 8.555000000 | 1 | 1 | Visible |
| Baseline2 | Early native gesture | 253.3 | 253.8 | 8.582443765 | 0 | 0 | Absent |
| Baseline3 | Camera-completion control | 831.2 | 713.1 | 8.555000000 | 1 | 1 | Visible |
| Baseline4 | Early native gesture | 227.6 | 228.1 | 8.596002109 | 0 | 0 | Absent |
| Baseline5 | Camera-completion control | 837.7 | 711.1 | 8.555000000 | 1 | 1 | Visible |

In all four interventions, mousedown observes `isMoving=true`, followed by
`moveend`0.5ms later, well before700ms. Camera center remains exactly equal to
that early-stop center at the later observation. Final parcel centers are
respectively `[-380.63,164.49]`, `[173.10,233.21]`, `[239.05,241.39]` and
`[136.41,228.65]`, not canvas center. All controls reach target longitude8.555
and project the parcel center to approximately `[530,277.51]` before the click.

The retained verifier `/tmp/gaia-gis-application-summary.cjs` asserts actual
event order, unchanged fit parameters, persistence of stopped camera, rendered
feature hits and popup-request counts across both controlled snapshots:
**PASS, exit0**. These small experiments demonstrate causality in their own
conditions;2/2 per condition is not a statistical flake-rate estimate.

## All attempts, including failures

| Attempt | Outcome | Interpretation |
| --- | --- | --- |
| Initial build invocation | Exit127; wrong relative executable path | Setup command failure, corrected before actual builds; log subsequently contains successful build, shell output retained in session |
| Both real production builds | Exit0; existing lint/start warnings retained | Actual compiled application, no development-mode substitute |
| Integrated initial locator-action matrix | Exact1PASS; early2/2 panels visible; controls2/2 visible | Supposed early locator clicks actually occurred575.7–597.1ms after fit; they stop animation but polygon already covers canvas center. Not evidence every interruption misses |
| Integrated fast-native matrix | Exact1PASS; early2/2 absent; controls2/2 visible | Actual early gestures208.0–237.4ms; causal matrix above |
| Baseline fast-native matrix, initial exact | FAIL: login502 before backend ready; zero fits | Setup failure, not GIS evidence; trace/log kept |
| Baseline same matrix, remaining scenarios | Early2/2 absent; controls2/2 visible | Real auth200 and actual baseline map; causal matrix above |
| Baseline exact callback after explicit backend health200 | PASS; popup1, panel visible | One focused diagnostic after readiness, no changed retry/timeout or erased original setup failure |

Successful exact callbacks can still interrupt animation: integrated fast
matrix mousedown568.4ms/moveend569.0ms, baseline ready580.8ms/581.4ms. Their
polygons already cover canvas center, so both produce popup1. Animation
interruption by itself therefore does **not** imply a popup failure.

The original R3 full run remains51PASS7skip1FAIL, followed by unchanged
diagnostic1PASS and unchanged full confirmation52PASS7skip. Those historical
results are not overwritten or newly certified by this report.

## Disposable stack and limits

- Owned network `gaia-gis-causality-20261008`, verified internal=true.
- Owned backend `gaia-gis-causality-backend-20261008`, recreated between snapshots
  with each snapshot's backend read-only at `/app`, exclusive synthetic env,
  `/e2e` and `/data` tmpfs, SQLite metadata initialized from actual models.
- Same cached backend image ID
  `sha256:dfd01b8c715ae92cf28fd5490242f9556ac774c93f03bf6d679422adf0bfed4c`.
- Owned proxy `gaia-gis-causality-proxy-20261008`, host-network nginx bound only
  to127.0.0.1:18081, API to isolated backend172.27.0.2:8000, frontend to13001.
  Same cached nginx ID
  `sha256:e7257f1ef28ba17cf7c248cb8ccf6f0c6e0228ab9c315c152f9c203cd34cf6d1`.
- Frontends run sequentially on127.0.0.1:13001 from their own production builds.
  Existing8081 listener was identified as occupied and never touched.

No production environment, credentials, database, volumes, Docker socket,
live external business provider, Martin/QGIS or PostGIS dataset was used.
Browser contexts still request public OpenStreetMap tiles and a Google-hosted
asset, as the original spec does. Those external responses and machine load
are not replay-controlled; actual measured gesture times differ between runs.
Optional local tile404 and layer503 endpoints remain. This limits equivalence
to a full production stack and historical replay, but does not negate the
measured native camera-stop mechanism on each snapshot's own application.
Instrumentation overhead can also change scheduling; no historical timing
identity or exact original root-cause claim is made.

## Reproduction and evidence

Build each clean worktree from its frontend directory:

```bash
NEXT_TELEMETRY_DISABLED=1 node_modules/.bin/next build
```

The retained bootstrap script creates exclusive mode0600 synthetic environment
and the retained nginx configuration names only disposable addresses/resources.
Start each snapshot's backend with actual metadata initialization and uvicorn,
and its production frontend with `next start --hostname 127.0.0.1 --port 13001`.
The actual resource-start recipe, with snapshot root set to either authorized
worktree and only after confirming the named resources and ports are free, is:

```bash
python3 /tmp/gaia-gis-application-bootstrap.py
docker network create --internal gaia-gis-causality-20261008
docker run -d --name gaia-gis-causality-backend-20261008 \
  --network gaia-gis-causality-20261008 \
  --env-file /tmp/gaia-gis-application-backend.env \
  --tmpfs /e2e --tmpfs /data -v "$GIS_SNAPSHOT_ROOT/backend:/app:ro" \
  -w /app --entrypoint sh gaia-sister-watchdog-verification:local -c \
  'python -c "import app.main; from app.db.base import Base; from app.core.database import engine; Base.metadata.create_all(bind=engine)" && exec uvicorn app.main:app --host 0.0.0.0 --port 8000'
docker inspect gaia-gis-causality-backend-20261008 \
  --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}'
```

Set the disposable nginx configuration's backend IP to the inspected value
if it is not the retained172.27.0.2. In a separately tracked frontend session,
run the production start command from `$GIS_SNAPSHOT_ROOT/frontend`; then:

```bash
docker run -d --name gaia-gis-causality-proxy-20261008 --network host \
  -v /tmp/gaia-gis-application-nginx.conf:/etc/nginx/nginx.conf:ro nginx:alpine
```

Stop/recreate only the owned backend and frontend between snapshots, preserving
their logs and using the same synthetic env; the actual comparison did so.
Both `/e2e` tmpfs databases are newly initialized, not shared or production.
Before the browser
probe, verify backend `/api/health`200, not only frontend `/login` readiness.
After using the separately named local resource recipe, run:

```bash
GIS_SNAPSHOT_ROOT=/absolute/path/to/snapshot GIS_SNAPSHOT_NAME=label \
  node /tmp/gaia-gis-application-causality.cjs

GIS_SCENARIOS=exact GIS_SNAPSHOT_ROOT=/absolute/path/to/baseline \
GIS_SNAPSHOT_NAME=baseline-exact-ready \
  node /tmp/gaia-gis-application-causality.cjs

node /tmp/gaia-gis-application-summary.cjs
```

| Artifact | SHA256 |
| --- | --- |
| `gaia-gis-application-causality.cjs` | `44c2a420eb265d6cd5052bc2741534bbc3aac2641dbd96e1db6975398c62fcca` |
| `gaia-gis-application-summary.cjs` | `dd3ca02edf68517c59502592d7d9811de9b1f98d7e82ac4a198918a69fab9a52` |
| `gaia-gis-application-integrated.json` | `0d90e220c12516276c3cf4c6deb22be50dfcd742c11b4dbf9ac64aa0e3582925` |
| `gaia-gis-application-integrated-native-fast.json` | `e6c3219111faefc5eab67a728f9e1a5919e0a213c27a7a1b05a03f8491ce3b37` |
| `gaia-gis-application-baseline-native-fast.json` | `0018cb506bcb6beb8db16b1de019d3f1dd95bb04ee27f77006efe9a4c0596f4b` |
| `gaia-gis-application-baseline-exact-ready.json` | `aef712032123220e1ffaccac4aba7e742558222ee2daba75beb158f11535c7f6` |
| `gaia-gis-application-summary.json` | `b323ed84f1a4076d39aeab78e6603d33bc37e257b6cd7a6eabdcd34f8e0bc849` |

All artifacts live in `/tmp/`, including per-run screenshots/traces and full
build/backend/proxy/browser logs. Browser traces may contain disposable auth
data; redact before external sharing. Synthetic env was deleted at cleanup.

## Repository gates

- `make complexity-ratchet BASE_REF=main`: PASS, exit0, `findings: []`,
  authoritative baseline commit55a1b1d3. Log
  `/tmp/gaia-gis-application-ratchet.log`; no baseline command executed.
- `git diff --check`: PASS. Diff against frozen70ae035d for backend, frontend,
  worker, quality tooling and Makefile: empty. Only the owned report is new.
- No full backend, frontend unit, worker or E2E suite is claimed as rerun here;
  this is a focused read-only browser experiment, not a new global release gate.
- Runtime coverage: not applicable to this report-only slice. No runtime file
  changed and no exemption from existing100% coverage policy is introduced.

## Cleanup and practical decision

Stopped only owned Next sessions98614/70567, removed the two named containers
and owned internal network after preserving logs, deleted only the owned
mode0600 synthetic env, and verified18081/13001 free. Existing release20261007
containers remained. Generated builds and diagnostic artifacts are retained;
tracked files in both source worktrees were unchanged before adding this report.

**Recommended Coordinator decision:** record the camera/center-click mechanism
as independently preexisting and consider releasing an unrelated, separately
owned runtime slice using the existing R3 verification and this controlled
comparison. Keep original R3 historical attribution UNKNOWN and disclose the
intermittent failure; do not imply that later passes fixed it. This report is
evidence for a decision, not acceptance of the risk on the user's behalf.

A separately authorized test-maintenance slice can characterize and synchronize
the GIS center click with actual completed camera and rendered parcel geometry.
Do not increase retries, add arbitrary sleeps, remove native gesture semantics,
change map behavior or weaken assertions to hide the failure. No such test or
runtime modification is included here. No complexity reduction or runtime
coverage change is claimed; Graphify boundary maintenance is not triggered by
this report-only investigation. Global campaign completion remains unproven.
