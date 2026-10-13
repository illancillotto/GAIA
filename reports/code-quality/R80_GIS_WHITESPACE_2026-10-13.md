# R80 — GIS scale whitespace correction

## Scope

User authorized only whitespace correction in the new R79 readiness assertion,
followed by a distinct verification. `frontend/tests/e2e/gis-territorio.spec.ts`
changes ASCII space to `\s+`; metre/numeric intent unchanged. R79 public parcel
refocus retained. All original assertions, timeouts, helper, mocks, geometry,
runtime and build unchanged. Historical R78/R79 failures remain immutable.

Branch `refactor/complexity-campaign-20261008`, HEAD
`e458dcdeaac64ff8d8740524900cc3a0f576b411`, actual main/merge-base
`a51a48dc4caefbdd1aea82fe4d749054b9465970`. Main concurrent config/Bonifica test
excluded. No baseline, threshold, exclusion, ignore or policy changes.

## Evidence

Root `/media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-resume-20261012/r80-gis-scale-whitespace/`.
`freeze/` preserves original and R79 spec plus mutable documents before updates.
Candidate SHA256 `033efec7d70282978e3565d152d233c24c9475a0a310b4847e264239c1bfcb4a`.
`whitespace-only.diff` is the exact one-line delta from R79; `authorized-spec.diff`
is the complete two-addition diff against HEAD. Nine focused regex checks PASS:
NBSP/ASCII metre values accepted; kilometres, missing separator, invalid numeric
and trailing text rejected. Not a substitute for browser verification.

Runner and faithful fixture copied from R79. Exact protected-input hash allows
only this candidate spec; all runtime/build/browser/dependency inputs pinned to
the historical receipt. No backend, database or provider, isolated loopback/PID,
read-only mounts, owned cgroup. One full-file native invocation after independent
review and quiet slot, workers1/retries0/maxfail1; no automatic retry or repair.

## Test matrix

| Behavior | Existing test | Added | Result |
| --- | --- | --- | --- |
| Scale NBSP, metre-only contract | New R79 readiness assertion | Whitespace-only correction, nine focused cases | Focused and native PASS |
| Desktop/mobile layout | Original GIS first case | None | Native PASS |
| Search/drawing/detail visibility | Original consultation case | Refocus/readiness from R79 | Reached and visibility PASS |
| Parcel panel placement | Original consultation assertion | None | FAIL: right gap -316 versus minimum55 |
| Sheets/measure/print/QGIS | Original later consultation assertions | None | NOT_REACHED |

Runtime classification NO_CHANGE; runtime coverage not remeasured (identical
bytes). No inherited full-suite or global coverage claim.

## Verification

Preparation accepted independently1856checks,17frozen inputs; receipts
`review/PREPARATION_REVIEW.md`, `review/PREPARATION_SHA256SUMS` checked from review
cwd. First `execute.log` is guard refusal due to external Jest, before native
directory/containment/server/browser creation. Bounded240s waiter observed a free
slot immediately; `execute-distinct-native.log` records exactly one native run.
No retry of failed native execution, no overwritten receipt.

One full-file run:1PASS/1FAIL/0SKIP, workers1/retries0,11.3s. New scale assertion
passes with NBSP. Original detail visibility passes; failure now at original
right-gap assertion, candidate line515: expected>=55px, received-316px. Vertical
panel assertions pass. Later sheet/measure/print/QGIS checks not reached.
Preserve this new failure without reducing tolerance or changing layout/runtime.
Trace/video/screenshot/logs and original mock responses retained.

Inputs before/after exact; owned cgroup empty/removed, Next/proxy terminated,
private namespace loopback-only and mounts read-only. Main concurrent file hashes
unchanged. Ratchet once against actualmain PASS,0findings; diff-check PASS.
Baseline/global ambiguity unchanged, no thresholds/coverage changes.

## Admission and next steps

Candidate remains PARZIALE, excluded from commits. Whitespace correction verified,
but complete GIS case remains FAIL. Terminal review accepted WITH failure,
2930checks PASS and559files frozen; `review/TERMINAL_REVIEW.md`,
`review/TERMINAL_SHA256SUMS`, `review/terminal/CHECKS.json` checked. No new runtime
regression claim: a bounded read-only layout/trace diagnosis is the next proposed
decision; no automatic assertion correction, layout fix or second invocation.

Bounded offline review confirms saved canvas `box` at line491 precedes public
refocus496 and panel boundingBox511. Trace does not retain numeric box results,
so stale dimensions are a plausible risk, not a demonstrated cause. Failure
screenshot visually contains panel inside map; do not replace recorded assertion
failure with a visual PASS. No private state observation or browser rerun.

Graphify docs maintenance completed once after fresh free-slot guard:
`make graphify-platform-docs`, exit0, chunk1/1done, no semantic-failure warning.
944nodes/1205edges/164communities;6038input/2073outputtokens, estimated$0.0057.
Source/output hashes recorded; final receipt-only annotations postdate graph
snapshot. No runtime/component-boundary change; graphify-out ignored/not staged.
Goal incomplete; all prior failures immutable.

## Handoff

External `HANDOFF.md`, `HANDOFF_MANIFEST.json` and `.sha256` seal input/fixture
custody, failure, reviews, gates, freezes and final spec/docs. Eight unstaged
changes retained: six preexisting plus R80registry/report; no commits or staged
files, caches/build/DB/dependencies/private runners excluded. Main unchanged.
