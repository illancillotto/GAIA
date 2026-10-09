# GIS E2E fix — independent source and integration review

## Scope and status

**APPROVED AND INTEGRATED — independent source and integration gates PASS.**
Ownership is the isolated GIS test fix registry dated 2026-10-09. The main
working tree is not an input. Review is limited to the fiscal-search E2E,
its adjacent test-only pixel helper, the domain contract and author report.
No runtime wave, baseline repair, threshold change or production behavior
change is authorized by this review.

## Independent behavioral review

The existing test assumes that selecting a search result makes its geometry
immediately clickable at canvas center. Actual application source starts a
700ms `fitBounds` operation. A native canvas gesture can stop that operation
before the target reaches center. Retrying the click cannot repair that
stopped camera. This is a test synchronization problem, not permission to
disable real gestures or change production animation.

The proposed helper observes a browser screenshot of the real canvas and
requires all 400 pixels in its central 20x20 CSS-pixel patch to classify as
the focused magenta parcel highlight. This is **target-hittability**, not a
claim that the camera is idle. It preserves native clicking and the exact
parcel popup request, `A ruolo` and `CFM-4201` assertions. Screenshot animation
mode remains `allow`; the existing retry intervals and action/assertion
timeouts remain unchanged. The new screenshot action is bounded at 5000ms.

Source contract: `TerritorioMapExperience.buildSearchOverlay` uses focused
fill `#F000B8`, outline `#C4008E`, opacity 0.9 and a six-second pulse;
`MapContainer` modulates opacity. An exact RGB match or whole-frame stability
check would incorrectly fail valid composited/pulsing targets. The helper
does not inspect React fibers, private MapLibre fields or application state.
Its synthetic canvas tests exercise screenshot decoding only; the fiscal
test still uses the real application and its existing API fixtures.

## Rejected intermediate predicate

Independent review found a real CPU-stress false negative in the earlier
`red - blue >= 15` predicate. The diagnostic showed a completed fit and an
actual rendered parcel hit but readiness timed out. The retained-in-session
PNG's central patch had RGB ranges 202–227 / 116–121 / 170–205; 118 of 400
pixels failed, although the target was visible. Water tiles can produce
blue-dominant magenta composites. The author replaced this test with red and
blue dominance over green and added compositing cases. That intermediate
failure is not a PASS and must remain in the author attempt history.

## Infrastructure attempts and recovery

An initial repeated run had 21 PASS, one import-test FAIL, one interrupted
fiscal test and nine not run. Independent inspection of its trace response
proved `/api/auth/login` returned 403 with the active-device limit of 20;
the page snapshot displayed the same message. This is synthetic account
saturation before GIS navigation, not a hidden GIS PASS. A stable disposable
browser device identity avoids creating a new active device per repetition
without changing production auth or weakening its contract.

The host reboot at 2026-10-09 07:57:04 removed `/tmp` diagnostics and stopped
the disposable stack. Earlier observations above survive as session evidence,
not accessible raw artifacts. Accepted-source certification must use fresh
durable evidence after recovery; no disappeared artifact is claimed present.

## Frozen-source execution and authorized integration

Source `13b6a8f2165ef6ddf0d6b64a092d1e710ed89743` was clean and independently
reviewed. Spec SHA256 is
`51f783e310aaa21f9feaeb868605058e489fbeaf4131270070503013413a95bf`;
helper SHA256 is
`af44b17b3a096ecdf635bbe0e096574d2833e7baf82682ca21319726ff88b132`.

Fresh independent execution used that source's actual Playwright runner and
the author's isolated recovered application on `127.0.0.1:18089`, after
backend health returned 200. The temporary runner imports unmodified committed
configuration and changes only source/output locations, origin and stable
synthetic client identity. Motion, timeouts and retry policy are unchanged.
Credentials are read privately from the owned synthetic environment, not
printed or copied into repository files.

```bash
npm run test:e2e -- \
  --config=/home/cbo/.cache/gaia-campaign/20261009-gis/reviewer/playwright.config.ts \
  tests/e2e/catasto-gis.spec.ts --workers=1 --repeat-each=3
```

**15 PASS, 0 skip, exit 0, 27.2 seconds**, including three real fiscal-search
callbacks, three unchanged import flows and three WebGL fallback checks.
Durable log is `reviewer/source-repeat.log`; separate screenshots/traces are
retained according to the unchanged failure-only runner settings. This was
one successful independent run, not a rewrite of earlier failed attempts.
No private instrumentation or diagnostic callback runner was used for this
certification. The browser window was relinquished before final verification.

After exact Coordinator authorization, the source was cherry-picked from
integration HEAD `6f9231693d5717464b0bbc4420b89e99f1a7a2f2` into
`286a82ccdb065d0c357cd47525f91ec14d707f0a`. All four integrated files compare
byte-identical to the approved source. Runtime, worker, scripts/tooling,
configuration, baseline, package/lockfile, Makefile and Playwright config
compare unchanged across this integration. Main's dirty concurrent work was
only inspected; no reset, stash, copy or main commit occurred.

## Integration gates

- Exact approved-source comparison: PASS; `reviewer/source-diff.log` is empty.
- Protected/runtime comparison: PASS; `reviewer/protected-diff.log` is empty.
- Explicit strict spec/helper TypeScript: PASS, exit 0;
  `reviewer/integration-types.log`.
- ESLint: PASS, exit 0, zero errors and one preexisting `_geojson` warning on
  unchanged fixture line 123; `reviewer/integration-lint.log`. No ignore added.
- `git diff --check`: PASS.
- `make complexity-ratchet BASE_REF=main`: PASS, exit 0, `findings: []`, against
  authoritative merge-base `55a1b1d35911451e018b662c2acc450bf5994ea2`.

Evidence paths above are relative to
`/home/cbo/.cache/gaia-campaign/20261009-gis/`. The ratchet log is
`reviewer/integration-ratchet.log`. No baseline command was executed.

The Coordinator independently refreshed the Catasto docs graph using its
dedicated Make target and `gpt-reserve`: `chunk 1/1 done`, no semantic failure,
59 nodes, 70 edges, nine communities. Durable evidence is
`coordinator/graph-catasto-final.log`. This is documentation maintenance, not
complexity evidence or a replacement for the browser gates.

## Limits and remaining verification

The final verifier owns fresh focused repetition and the full browser suite;
those results must be taken from its separate report, not inferred from these
15 tests. Backend, worker, build and full unit suites are not claimed rerun
by this reviewer, because their runtime is unchanged. Optional external tile
and isolated-stack limitations remain as described in the author report.

The color contract is intentionally local to this single-polygon fixture:
future changes to focus styling, multiple overlays or fixture geometry require
review. It is not a generic geospatial hit-testing API or proof of camera idle.
Classification for the complexity campaign is **NO_CHANGE — TEST_ONLY_FIX**;
the native target synchronization improves E2E reliability without asserting
any cognitive/cyclomatic reduction. No baseline repair was performed.

Runtime coverage is not applicable to this test-only fix; no full-file coverage
gate exemption or complexity reduction is claimed. Global campaign completion
remains unproven.
