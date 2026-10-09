# GIS E2E fix — Complexity Slice Report

## Ownership

Authorized registry `docs/code-quality/MULTI_AGENT_OWNERSHIP_GIS_FIX_2026-10-09.md`
at `7b1758cb`. Exclusive test-only ownership of `catasto-gis.spec.ts`, adjacent
helper `gis-canvas-target.ts`, Catasto synchronization documentation and this
report. Worktree `GAIA-campaign-20261009-gis-test-fix`, branch
`fix/gis-e2e-camera-sync`. No integration, main change, push or runtime edit.

## Baseline and target

Source before: `7b1758cbdb9da79630a8a18f107db884da57ef58`; merge-base/main:
`55a1b1d35911451e018b662c2acc450bf5994ea2`. Working tree initially clean.
Target: intermittent fiscal-search E2E panel FAIL, not Capacitas coverage or
the30 global provenance findings. Existing historical investigation proves a
preexisting early native-gesture camera-stop mechanism in both application
snapshots. The exact cause of the historical R3 failure remains UNKNOWN.

## Behavioral invariants

- Search fiscal ID with `mode:auto`, select actual search result, close search.
- Use real default-motion application map and a native canvas-center click.
- Require exact actual fixture parcel popup request, `A ruolo` and `CFM-4201`.
- Preserve existing10s toPass, intervals250/500/1000,5s canvas action and1s
  panel assertion; keep90s test/20s globalexpect settings.
- No reduced motion, synthetic map, React-fiber/private map access, sleeps,
  excluded test, retry inflation, runtime/config/baseline/style change.

## Characterization tests and changes

| Behavior | Existing test | Missing | Added | Result |
| --- | --- | --- | --- | --- |
| Real fiscal search/popup/panel | Fiscal-search E2E | Safe click-point readiness | Central20x20 screenshot highlight condition before native click | PASS |
| Absent/off-center/small target | None | Screenshot/predicate rejection | Pixel matrix and real screenshot2D-canvas checks | PASS |
| Color compositing and pulse | None | Basemap blend handling | White/green/blue composites at0.9/0.98; dim0.22 rejection; captured water blend202/116/205 | PASS |
| XLSX saved selections | Existing E2E | None | Unchanged | PASS |
| WebGL fallback | Existing E2E | None | Unchanged | PASS |

Helper reads a real locator screenshot with animations allowed and CSS scale,
decodes PNG via browser `createImageBitmap`, and samples20x20 pixels in a
separate2D canvas. Every pixel must have sufficiently strong red/blue relative
to green. No WebGL drawing-buffer access or map object inspection. Production
focused fill is `#F000B8`; its pulse blends over basemap. Dim/ambiguous frames
are deliberately not readiness. The full20x20 patch supplies a native click
margin. This observes **target-hittability**, not camera-idle.

## Metrics before / after / delta

Runtime is byte-identical to starting source. `git diff --name-only 7b1758cb --
backend/app frontend/src modules/elaborazioni/worker config/code-quality
tools/code_quality Makefile` returns empty. Cognitive/cyclomatic/LOC/runtime
finding deltas of this slice: **0**. No complexity reduction attributed to the
test helper. Source hashes of final tested files:

- Spec: `51f783e310aaa21f9feaeb868605058e489fbeaf4131270070503013413a95bf`.
- Helper: `af44b17b3a096ecdf635bbe0e096574d2833e7baf82682ca21319726ff88b132`.

## Tests and evidence provenance

Host reboot at2026-10-09 07:57:04 destroyed `/tmp` raw artifacts and live tool
sessions. These earlier commands are **historical observations**, not current
reproducible raw evidence:

1. Original focused callback1PASS; first fixed spec4PASS.
2. Original-config repeat hit synthetic-auth20-device cap:21PASS,1imports
   FAIL,1fiscal interrupted,9notrun, exit130 after explicit interruption.
   Recorded trace response was auth/login403 and JSON `Limite dispositivi
   raggiunto: massimo20`; no GIS request was reached in that failure. Fresh
   context identities accumulated in one synthetic DB. Temporary stable client
   identity fixes the test environment without changing auth enforcement.
3. First pixel predicate incorrectly required red-blue>=15. CPU4 diagnostic
   found centered rendered parcel but no click; water blend202/116/205 caused
   rejection. Removed that invalid red/blue assumption, kept red-green and
   blue-green saturation checks, and added the captured-value regression case.
4. Initial compositing test incorrectly expected0.6 opacity over darkgreen/
   blue to satisfy the high-saturation predicate;3classifierFAIL/12PASS.
   At0.6 those frames are legitimately not sufficiently saturated. Positive
   compositing matrix corrected to0.9/0.98, dim0.22 remains negative. Native
   application test was never weakened to click those ambiguous frames.
5. Other successful repetitions and probes before reboot are not counted as
   surviving final evidence. Graphify process was killed by reboot; no docs
   graph success inferred from missing output or partial files.

**Fresh durable post-reboot evidence directory:**
`/home/cbo/.cache/gaia-campaign/20261009-gis/author`.
All current logs, traces, PNGs and matrix JSONs below live there, not `/tmp`.
The directory is outside Git and mode0700. Synthetic backend.env is0600;
its secrets are never logged.

### Fresh final commands

From source worktree frontend, privately load synthetic env and map bootstrap
username/password to `PLAYWRIGHT_ADMIN_USERNAME`/`PLAYWRIGHT_ADMIN_PASSWORD`.
Do not print these variables. Then:

```bash
npm run test:e2e -- \
  --config=/home/cbo/.cache/gaia-campaign/20261009-gis/author/playwright.config.ts \
  tests/e2e/catasto-gis.spec.ts --workers=1 --repeat-each=4
npm test
npm run test:unit -- tests/unit/territorio-map-experience.test.tsx \
  tests/unit/catasto-gis-map-container-overlay-click.test.tsx \
  tests/unit/use-territorio-unified-search.test.ts
node_modules/.bin/eslint tests/e2e/catasto-gis.spec.ts tests/e2e/gis-canvas-target.ts
node_modules/.bin/tsc --noEmit --strict --target ES2022 --module commonjs \
  --moduleResolution node --esModuleInterop --skipLibCheck --lib ES2022,DOM \
  tests/e2e/catasto-gis.spec.ts tests/e2e/gis-canvas-target.ts
```

- Complete finalGIS spec repeated4times: **20PASS,0skip**, exit0,1minute;
  `final-repeat.log`. Includes4real fiscal-search callbacks.
- Existing relevant runtime units: **17PASS/3files**, exit0; `unit.log`.
- Smoke: **18PASS,0skip**, exit0; `smoke.log`.
- Explicit spec/helper TypeScript: PASS exit0; `types.log`.
- ESLint: exit0,0errors,1preexisting `_geojson` warning in unchanged fixture
  line123; `lint.log`. No disable/ignore added.
- `git diff --check`: PASS.

Temporary runner imports unmodified versioned configuration, changes only
test/output locations, baseURL and stable synthetic client localStorage.
Default Chromium/motion, test/expect timeouts, native gestures and real auth
enforcement remain identical. No committed runner configuration change.

## Controlled native-click reproduction

Fresh `native-controls.cjs` loads the exact spec fixtures and helper via actual
TypeScript transpilation. It uses only public DOM/browser actions; no private
map/fiber instrumentation. Native result/select/toggle clicks are precomputed
before search selection so the old premature click can genuinely occur fast.
Recorded elapsed time starts before native result click, **not at fitBounds**;
no camera-idle claim is made. Each scenario has a fresh browser context, native
application login, actual search fixture, real canvas, actual popup request
count and role/CFM panel checks. Screenshot/trace/JSON retained per attempt.

```bash
GIS_LABEL=native-normal node \
  /home/cbo/.cache/gaia-campaign/20261009-gis/author/native-controls.cjs
GIS_LABEL=cpu4 GIS_CPU_RATE=4 GIS_SCENARIOS=exact,ready,exact,ready node \
  /home/cbo/.cache/gaia-campaign/20261009-gis/author/native-controls.cjs
```

| Fresh scenario | Gesture after selection sequence ms | Popup | Panel |
| --- | ---: | ---: | --- |
| Default-motion old premature native click1 | 315.5 | 0 | Absent |
| Default-motion actual target readiness1 | 5558.2 | 1 | A ruolo/CFM visible |
| Default-motion old premature native click2 | 354.3 | 0 | Absent |
| Default-motion actual target readiness2 | 1274.5 | 1 | A ruolo/CFM visible |

`native-normal.log`/`.json` and4traces/screenshots demonstrate the old failure
mechanism remains reproducible while the corrected readiness succeeds.
These controlled negative observations are expected, not new suite failures.
CPU4 is an actual browser CPU throttle, not a mocked animation or elapsed-time
assumption. Fresh finalCPU4 matrix: **2/2 exact fiscal callbacksPASS and2/2
fast-native readiness controlsPANEL_VISIBLE**, popup1 in every scenario,
no pageerrors; native readiness click sequences6678.4ms and1947.2ms. Durable
`cpu4.log`/`.json` and4traces/screenshots retained. No stress attempt was skipped.

## Coverage

No runtime file modified; full-file runtime coverage policy is not relaxed or
claimed achieved by test-only helper checks. Existing Capacitas branch gate
remains unchanged. New helper's valid/rejection screenshot and pixel paths
are exercised directly, not by fake application state.

## Ratchet

`make complexity-ratchet BASE_REF=main`, authoritative merge-base55a.
Fresh durable `ratchet.log`: **PASS,0finding,exit0**. No baseline,
threshold, scope, exclusion, exception, tooling or runtime hash changes.
Global30 divergence problem is not repaired or ignored by this slice.

## Classification

**NO_CHANGE — TEST_SYNCHRONIZATION_FIX** for runtime complexity. The E2E
readiness is materially fixed, but no runtime complexity improvement claimed.

## Files changed / commit

- `frontend/tests/e2e/catasto-gis.spec.ts`
- `frontend/tests/e2e/gis-canvas-target.ts`
- `domain-docs/catasto/docs/GIS_E2E_CAMERA_SYNC_2026-10-09.md`
- This slice report.

One source commit, obtainable via `git log -1 --format=%H --
reports/code-quality/SLICE_GIS_E2E_FIX_2026-10-09.md`. Integration is reserved
for independent reviewer; source author does not cherry-pick own branch.

## Residual risks / next step

Real OpenStreetMap/external assets and host scheduling are not replay-controlled;
repetitions are not a statistical guarantee. Predicate is a documented visual
contract for this single focus-overlay fixture; a color/geometry/style change
must explicitly update/review the contract. User gestures still stop map camera
in runtime, intentionally unchanged. The historical R3 cause remains uncertain.

Disposable stack uses own internalDocker network `gaia-gis-fix-20261009`, own
syntheticSQLite backend/tmpfs, own proxy18089 and productionfrontend13009.
Reusable clean causality build has `frontend/src` tree
`0a8a94eb85866f573d7866b19ff29c8e6dc33d05`, exactly source tree here;
buildworktreeHEAD `febc7bfb51fc89bc46ba0dfdabbfa0ef7009ed61`, buildID
`PcA7DG2ACjI_qItoqxRQu`. No dirty main runtime copied. No production env,
DB, volumes or business providers used. Optional unavailable GIS catalog/tile
endpoints in the synthetic stack are retained, not called production PASS.

GraphifyCatasto docs refresh is delegated to Coordinator after final source
integration; pre-reboot process did not yield retained successful semantic
evidence. Runtime graph unchanged. Independent source review and fresh final
browser verification remain mandatory before integration acceptance.
