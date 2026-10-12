# R57 GIS popup — Complexity Slice Report

## Ownership

One coherent frontend GIS parcel identity/status presentation responsibility.
Author dedicated SSD worktree/branch, independent reviewer distinct worktree,
Coordinator actual integration `refactor/complexity-campaign-20261008`.
Only page.tsx, new parcel-popup-presentation.ts and new mounted spec changed.
Main concurrent working tree, baseline, thresholds and matcher untouched.

## Baseline

Integration HEAD114fbf7196382c6446a7963c34bd89e4c9795ef5;
main/merge-base55a1b1d35911451e018b662c2acc450bf5994ea2.
Original page b5f14eab, current page791e7732, new helper0b89c623,
final new specb88cb6ac. Current complete report3c6d6678a18603afce28b0961f29eb08a946a33a10732b3aa5ba8146c673ff46.

## Target callable

CatastoGisPage parcel-popup header policy only, not the remaining orchestration.

## Behavioral invariants

Both independent ha_ruolo reads and summary/source-mode/inferred evaluation
order preserved; key code→sheet→parcel short circuit; truthy CFM precedence;
location nullish empty-string preservation; truthy subalterno reread; suppressed
skips current-state read. Labels/classes/title/location/state byte-equivalent.
No JSX/state/hook/effect/API/permission/coordinate/async boundary change.

## Characterization tests

| Behavior | Existing test | Missing | Added | Result |
|---|---|---|---|---|
| Real popup workflows | 34 GIS and 3 coordinate cases | Close/reopen/null status | Mounted lifecycle and exact UI assertions | PASS |
| Role/class/label precedence | Rich/incomplete existing fixtures | Unknown/empty/absent source and getter differences | Nine role variants plus accessor cases | PASS |
| Key/title/location | Existing complete/incomplete fixtures | Empty/null/whitespace/zero-like and read ordering | Eleven identity variants plus guard cases | PASS |
| State precedence | Existing suppressed incomplete fixture | Current/history and skipped getter | Four state variants and short circuits | PASS |
| Full file coverage | Historical C2 | Fresh current dependency execution | Original/candidate 73-case union | Four measures100 |

36 new mounted cases retain every existing assertion; historical37descriptor
multiset exact against R54. Strong typed DTO/Promise fixtures; no fake branch
tests, skips, ignores or config changes. Strict NEW spec check preserves all
project roots rather than relying on project config that excludes tests.

## Changes

Five small typed domain selectors, no new component/hook. The duplicated badge
decision tree is shared by class/label calls while preserving separate source
reads. Key/title/location extraction alone is reorganization, not net credit.
Record guard order is clearer; two duplicate physical decisions actually removed.

## Metric before / after / delta

| Metric | Before | After | Delta |
|---|---:|---:|---:|
| Principal cognitive |317|298|-19 (-5.99%)|
| Principal cyclomatic |281|262|-19|
| Principal LOC |1889|1868|-21|
| Principal nesting / params |4 / 0|4 / 0|0|
| Owned aggregate cognitive |568|566|-2 (-0.35%)|
| Owned cyclomatic sum |657|660|+3 from five new callable roots|
| Owned sum(cyclomatic-1) |483|481|-2 decisions|
| Main file LOC |2155|2141|-14|
| Main+helper LOC |2155|2178|+23 explicitly disclosed|
| useState / useEffect |28 / 8|28 / 8|0|
| >300 / >200 / >100 tail |4 / 17 / 55|3 / 17 / 55|-1 / 0 / 0|

Helpers cognitive2/3/3/6/3, cyclomatic3/4/4/7/4, LOC4/3/4/4/5,
nesting0–1, params1–2; all below warning. All173 surviving callable identities,
fingerprints and primary metrics exact, all nonowned report metrics exact.
Global1675files20342callables1920errors2735warnings4655overlapping findings;
application1620files19011callables319041LOC. No finding reduction claimed.
Principal19-point drop is not19-point global debt reduction; net credit is2.

## Tests / coverage / ratchet

Original-v2 root44465 and candidate90196 TERMINAL0, all12 gates0 each;
73PASS/zero skips, source custody/types/strict-new/lint/report/ratchet/diff-check.
Raw original page587statement613branch174function523lines100; candidate page
587/578/174/523 and helper18/31/5/13 all100, excel9/4/3/8 unchanged100.
Source/map/counter/bounds/implicit-else and provider whole-line-end audit retained;
R37 negative-location controls separate, not counted as application coverage.
Authoritative ratchet main55a PASS0findings. Baseline38e6b794 unchanged.

## Retained failure / global baseline status

Initial original53524 TERMINAL1:37historicalPASS36newFAIL because the new DUI
API mock returned undefined instead of Promise; no runtime edit/regression.
Diagnosed, frozen exactaa8cspec/argv/log/exit. Distinct typed mock correction,
static review and fresh original-v2 gate; no old successful gate retried or
assertion weakened. Initial reviewer stale-content error and correction retained.

Fresh global-check38144 exits2 at unchanged GAIAusers callback ambiguous_identity
(four candidates), same known path as R53, not automatically historical30 nor
current regression. Findings totals are debt observations, not identity causes.
Local ratchet0 and global check2 are separate; baseline not inflated.

## Classification

**IMPROVED — small local net reduction**, behavior characterized and independently
reviewed. Architecture isolation adds23LOC; no file-LOC/hook/parameter reduction
credit beyond the main file, no claim that extreme debt is solved project-wide.

## Files changed / commit

Runtime page and new typed helper; new test; ownership/progress/global/local reports.
No commit, push or Git merge. Integration source byte-exact approved candidate.

## Residual risks / recommended next slice

Principal298 remains highly complex; three callable>300 remain (Utenze391,
Catasto anomalie390, Presenze360). Complete frontend/build checkpoints R54/R55
predate this source change; do not relabel them fresh current-suite PASS. R56
backend remains unchanged-source evidence with449skips. Worker/E2E/global baseline
and R43 fixture decision remain open. Campaign ACTIVE/INCOMPLETE.
Stop after this responsibility. Further work requires fresh ownership/invariants,
not automatic expansion into other popup overlays or the rest of GIS.

## Evidence

SSD `.codex-gaia-campaign-20261012-r57-gis-popup`: root-evidence/original-v2
contains original/candidate raw native logs/argv/exits/tests/coverage/reports/
metrics/custody; reviewer-evidence independent audits; prior FAIL and correction
snapshots immutable. Three original publication docs archived byte-exact before
updates, R56companion4d76593c and nested older custody preserved.
Graphify frontend force target PASS6075nodes12688edges228communities, ignored
graph; local pruning patch applied first. Maintenance not metric/test evidence.
Platform docs target30089 PASS/chunk1of1done/no failed semantic warning,
625nodes732edges126communities/6423input1708outputtokens/$0.0053. Catasto docs
53212 PASS/chunk1of1done/no failed semantic warning,112nodes142edges12communities/
685input3963outputtokens/$0.0066. All graphs ignored, API keys not exposed.
