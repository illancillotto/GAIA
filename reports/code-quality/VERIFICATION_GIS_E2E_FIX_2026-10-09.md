# GIS E2E Fix — Independent Final Verification

## Scope and snapshot

User target: **FAIL test GIS**, specifically fiscal-search parcel role details.
This verification certifies the test-only synchronization slice, not completion
of the multi-agent complexity campaign or historical R3 root-cause certainty.

- Source approved by independent reviewer: `13b6a8f2165ef6ddf0d6b64a092d1e710ed89743`.
- Verifier worktree: `GAIA-campaign-20261009-gis-verification`.
- Branch: `verify/gis-e2e-camera-sync`; source cherry-pick: `8789199778a15c07d6dc6fcd6abddd8c4a3178b2`.
- Initial clean HEAD: `db009a5d0a06883e47573d161da56e7fff3f0486`.
- Merge-base with main: `55a1b1d35911451e018b662c2acc450bf5994ea2`.
- Dirty main worktree is never used, modified, reset, stashed or merged.

The exact test diff matches source SHA. Test blobs are
`9fa0a619aa3609a258f6676d65320bb845e8c591` (spec) and
`a8ca5b95a9dbf148751bfb3f86e8e7a886fdec20` (helper).
The verifier owns only this report, not runtime, test or configuration edits.

## Frozen runtime and controls

These trees/blobs match verifier initial HEAD and approved source:

| Path | Git object |
| --- | --- |
| frontend/src | `0a8a94eb85866f573d7866b19ff29c8e6dc33d05` |
| backend/app | `37d7c15bb8bc48889ea8eb731e6df80512ccaadc` |
| frontend/playwright.config.ts | `bbdccd5fa61a88579871d9b290456300aa38f99a` |
| frontend/package-lock.json | `3bec094ba959bbe12bc7bd14b17fda93cf4fd282` |

Diff from initial verifier HEAD is empty for runtime, worker, quality baseline,
thresholds, scope, tooling, Makefile, package manifests and Playwright config.
No new ignore, skip, retry or timeout change. `git diff --check` passes.

Verifier runs fresh Playwright processes/browser contexts after independent
source approval and serial handoff of the author-owned isolated synthetic
stack. Gateway is loopback18089, production frontend loopback13009, backend
synthetic SQLite/tmpfs on its own internal Docker network. No real credentials,
business database, production volumes or occupied8081 service are touched.
Production build is reused from clean `febc7bfb51fc89bc46ba0dfdabbfa0ef7009ed61`
with identical frontend/src tree; this is **not a fresh verifier build**.

Installed versions: Next15.5.25, React18.3.1, MapLibre6.9.0,
Playwright1.59.1, Chromium147.0.7727.15. Headless Chromium, default motion,
1280x720 viewport, devicePixelRatio1. A separate default-browser observation
confirms `prefers-reduced-motion: reduce` is false; no reduced-motion override.

Temporary runner outside the repository imports unmodified committed config.
Only testDir/output/report paths, baseURL, workers1 and stable synthetic browser
device identity are supplied. Project timeout90000ms, expect timeout20000ms,
retries0, and original fiscal-search10-second assertion budget are retained.
The existing native click and popup request/panel assertions remain active.

Stable `gaia.client_device_id` is seeded without token/cookie bypass. The public
contract is `frontend/src/lib/auth.ts`: an existing localStorage identity is
reused. Backend `register_vpn_login_device` recognizes an existing fingerprint
before checking new-device count. This avoids allocating one new synthetic
device per fresh browser context, without changing authentication enforcement,
limits or source. Every applicable test still performs real login.

## Independent commands and results

Durable evidence root:
`/home/cbo/.cache/gaia-campaign/20261009-gis/verifier` (mode0700).
Synthetic credentials are loaded privately from author backend.env (mode0600),
not printed. `run.cjs` records each command, timestamps, exit code and signal.

From verifier frontend, using that private synthetic environment:

```bash
npm run test:e2e -- --config=/home/cbo/.cache/gaia-campaign/20261009-gis/verifier/playwright.config.ts tests/e2e/catasto-gis.spec.ts --grep 'fiscal search opens parcel role details' --repeat-each=10
npm run test:e2e -- --config=/home/cbo/.cache/gaia-campaign/20261009-gis/verifier/playwright.config.ts tests/e2e/catasto-gis.spec.ts
npm run test:e2e -- --config=/home/cbo/.cache/gaia-campaign/20261009-gis/verifier/playwright.config.ts
make complexity-ratchet BASE_REF=main
make complexity-report REPORT_JSON=/home/cbo/.cache/gaia-campaign/20261009-gis/verifier/complexity.json REPORT_MD=/home/cbo/.cache/gaia-campaign/20261009-gis/verifier/complexity.md
```

The final two commands run from verifier root. Browser runs are serial.

| Attempt | Result | Duration | Retained evidence |
| --- | --- | ---: | --- |
| Focused fiscal search, repeat10 | 10PASS,0skip,0unexpected,0flaky; exit0 | 47.323s | focused.log/json, focused-exit.json |
| Entire GIS spec | 5PASS,0skip,0unexpected,0flaky; exit0 | 11.639s | gis.log/json, gis-exit.json |
| Full E2E integration suite | 54PASS,7existing skips,0unexpected,0flaky; exit0 | 72.350s | full.log/json, full-exit.json |
| Complexity ratchet/main | PASS,0findings; exit0 | — | ratchet.log |
| Read-only AST report | PASS,0parse/exception errors; exit0 | — | complexity.json/md/log |

All test result retries are zero. No browser attempt failed or was interrupted
in this independent final verification. The full suite collects61 scenarios,
including the two new readiness regression tests; the historical59 count is
not used as a current result. The fiscal-search scenario passes12 times total
across focused, GIS and full-suite runs.

## Existing skips — not PASS

| Test | Existing skip reason | Impact |
| --- | --- | --- |
| catasto-anagrafica.spec.ts:14 | Single search removed; bulk-only remains | Obsolete single-search path not exercised |
| catasto-drilldown.spec.ts:14 | No districts seeded in synthetic stack | District/parcel drilldown not exercised |
| catasto-drilldown.spec.ts:52 | No districts seeded in synthetic stack | District/anomaly drilldown not exercised |
| gis-territorio.spec.ts:381 | Optional smoke flag not enabled | Optional responsive GIS console smoke not exercised |
| gis-territorio.spec.ts:439 | Optional smoke flag not enabled | Optional territory/QGIS smoke not exercised |
| wiki-mcp-console.spec.ts:3 | Requires isolated synthetic Docker gateway opt-in | Live MCP console not exercised |
| wiki-mcp-preview.spec.ts:3 | Explicit synthetic fixture/provider opt-in required | Live MCP/model path not exercised |

No skip added by this slice. Exact annotations are retained in full.json.

## Complexity, coverage and other suites

Current read-only report:1668files,20280callables,1938error,2749warning,
4687findings. Unchanged versus pre-fix campaign checkpoint: delta0 for all
listed metrics. Tests are not classified as runtime complexity reduction.
No baseline update, repair, exclusion or threshold modification is executed.

No runtime file changes in this fix: no new runtime coverage requirement or
claim of full-repository100% coverage. Backend/worker full suites, frontend
full unit suite and fresh build are not rerun by this verifier for this
test-only slice; they are **not independently certified PASS here**. Author
and earlier campaign evidence are separate reports, not substituted results.
Global baseline check is not rerun here; Coordinator's independent global
check and provenance remain authoritative. Historical30 divergences and
Capacitas97.52% coverage failure are separate, unresolved campaign issues.

## Reboot, limitations and disposition

External host reboot at2026-10-09 07:57:04 removed earlier volatile/tmp
diagnostic evidence and stack. No independent verifier browser run had started
before that event. Final verification above uses recovered stack and durable
logs only; lost author experiments are not presented as retained verifier
evidence. The author report records those attempts separately.

Public map assets and host scheduling remain environmental inputs. Repeated
green runs demonstrate the fixed fixture's native click path, not a guarantee
for every overlay style or geometry. The visual predicate is target-hittability,
not camera-idle proof: it may become true before moveend and intentionally
leaves normal gesture interruption semantics unchanged. Historical R3 cause
remains uncertain. A future overlay color/style change requires contract review.

Classification: **NO_CHANGE — TEST_SYNCHRONIZATION_FIX** for runtime complexity.
**Final GIS test-fix gate: PASS**, with the seven existing skips explicitly
unverified. No further hotspot/wave, main merge, push or PR is authorized by
this report. Graphify domain documentation refresh belongs to Coordinator;
this report changes no code dependencies or runtime boundaries.
