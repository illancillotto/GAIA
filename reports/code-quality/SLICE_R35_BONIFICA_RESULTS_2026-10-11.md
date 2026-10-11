# R35 author — Bonifica result normalization static admission analysis

Status: `NO_SAFE_CHANGE` / `BLOCKED_COVERAGE` under the current original full-file statement/branch
100% precondition. Static preparation only; no runtime or test source edited,
no author heavy gate, commit, baseline or scope/config change.

## Source custody and scope

- Author branch `refactor/complexity-r35-bonifica-results`, HEAD
  `0078b65ce48ba06e89c4fc3681cda1f8ae286da7`, actual `main` merge-base
  `55a1b1d35911451e018b662c2acc450bf5994ea2`; initially clean worktree.
- Original runtime SHA256
  `e01d85f2cfbd726933819db1dc32b84b46cae37b443cfc4943a9b3ad843625e4`.
- Exclusive scope is the ten `_SyncExecutionResult` normalizations in
  `_run_bonifica_sync_background`, with a prospective small typed same-file
  helper. No dispatch rewrite, routing, retry or orchestration redesign.
- Registry read first from integration; checkpoint skill, AGENTS, complexity
  skill/references, quality ratchet, style, metrics and validation consulted.
  The 9809-line PROGRESS diary was inspected through current admission entries,
  relevant headings and final handoff, keeping output bounded.
- Private sibling `author-evidence/tracked_custody_before.json` captures 3655
  tracked file hashes; `native_static_metrics.json` and `prospective_source.py`
  hold exterior-only analysis. The prospective file was never installed in
  runtime or imported as application code.

## Concrete responsibility and invariants

Seven entities read `synced` / `skipped`; `vehicles` reads `vehicles_synced` /
`vehicles_skipped`, `refuels` reads `fuel_logs_synced` / `fuel_logs_skipped`,
and `taken_charge` reads `usage_sessions_synced` / `usage_sessions_skipped`.
All real returned types are dataclasses with an ordinary `errors: list[str]`
attribute. The prospective helper accepts explicit typed counters and that
list, counts the full list and joins only its first 20 items with newlines,
using `None` for an empty list. No conversion, error truncation before counting,
string lookup table or arbitrary attribute accessor is proposed.

Arguments preserve synced-counter then skipped-counter then error-list
evaluation. Original repeated reads of `sync_result.errors` have no property
or descriptor effects in the concrete domain dataclasses; normalization is
synchronous with no await or mutation. All client construction, fetch arguments,
runtime snapshots, domain synchronization, params assignment, finalization,
commits, exception handling, manager-close and database-close statements remain
in their original locations in the exterior sketch. This is static reasoning,
not a completed behavioral certification.

## Native prospective metrics

The installed repository `PyVisitor` / `py_complexities` / `effective_loc`
analyzed the original and exact exterior sketch. No native whole-report gate or
matcher was run by the author.

| Metric | Original | Exterior sketch |
| --- | ---: | ---: |
| Target cognitive | 269 | 174 |
| Target cyclomatic | 47 | 37 |
| Target effective LOC | 232 | 202 |
| Target nesting / params | 13 / 3 | 13 / 3 |
| File summed cognitive | 430 | 336 |
| File summed cyclomatic | 184 | 176 |
| File decisions, sum(cyclomatic - 1) | 163 | 154 |
| File effective LOC | 739 | 718 |
| Callable count | 21 | 22 |
| Callable findings | 13 | 13 |

Prospective helper cognitive/cyclomatic/LOC/nesting/params = `1/2/9/0/3`,
with zero findings. Reduction is prospective only: no `IMPROVED` credit.

## Fresh original evidence supplied by coordinator

Root ran unchanged `test_elaborazioni_bonifica_oristanese`,
`test_elaborazioni_bonifica_sync_live_unit`, `test_bonifica_scheduler`, and
`test_bonifica_form_parsers`. Native result: 97 tests pass, zero failure/skip;
coverage gate exits 1 solely because full-file 100% is not achieved. Statements
`399/399`; branches `120/128`; combined `98.4819734345351%`.
The report has two existing excluded lines; no author exclusion was added.

Root artifacts are in private sibling `root-evidence/original-coverage.json`,
`original-tests.xml`, `original-tests.log`, native exit and 8-input custody.
The author read these artifacts without rerunning the gate.

| Missing original arc | Legitimate characterization approach |
| --- | --- |
| 99→101, 101→105 | Real persisted job; call snapshot without source_total, retain existing params |
| 105→107, 107→109, 109→112 | Existing non-null counters, including nonzero values; snapshot must preserve each |
| 254→253 | Real eligible Vehicle whose search candidates are all empty, whitespace-only or already seen after stripping; exhaust the inner loop without a valid fallback |
| 634→637 | Real persisted WCSyncJob assigned aware started_at in the Session identity map; expire path preserves aware timestamp semantics |
| 214→217 | Unreachable under unchanged real date-resolver contracts; proof below |

## Admission blocker: arc 214→217

`_resolve_job_params` enters its inheritance block only when `entity` is in
`DATE_AWARE_SYNC_ENTITIES` (lines 200–204). It passes the same unchanged entity
to `_resolve_date_window_from_job` (line 213). That function therefore cannot
take its non-date-aware `(None, None)` return (lines 183–185); it constructs a
normal `BonificaSyncRunRequest` from parsed job values and calls
`_resolve_date_window` (lines 187–192).

For a date-aware entity `_resolve_date_window` computes `end_date` as the
request's date_to or `date.today()`, and `start_date` as the request's date_from
or that end date minus a timedelta (lines 154–156). Every successful return
contains two dates. Invalid dates parse to None and receive these defaults;
inverted windows, invalid settings or overflow raise instead of returning two
None values. Thus the line-214 predicate is true on every successful normal
return, and its false arc to 217 cannot execute through the admitted real flow.

Covering this arc would require fabricating an internal resolver return,
changing membership/state during resolution, changing unrelated runtime code,
or excluding/waiving the branch. Current authorization expressly forbids those
approaches. Original branch 100% must precede the normalization runtime edit,
so removing the blocker while refactoring the normalization also cannot satisfy
the stated admission order and single-responsibility scope.

## Real-flow behavior matrix for a future admitted slice

Existing SQLite/public-route tests cover imports across all ten entities,
credential encryption/use, report summaries, date-window reuse, bootstrap
failure/missing user, missing jobs, stale jobs, vehicle dependencies and APIs.
Existing tests remain immutable. Real domain outputs, persisted counters and
public statuses must remain the primary characterization; helper unit examples
would only supplement them.

Useful additions after a scope decision: repeat real imports for skip counters;
actual taken-charge missing vehicles/invalid dates and refuel invalid dates for
error-only and mixed success/error runs; more than 20 actual errors for full
count versus first20 detail and first5 report preview; continue later entities
after a client-boundary failure; observe snapshot/domain/final commit order
through SQLAlchemy events without replacing database methods; assert real
credential state and manager cleanup at the external boundary.

Most other entity error lists are defensive exception outcomes. Artificially
manufacturing impossible typed parser outputs or mocked sync results is not a
valid substitute for real orchestration. Native coverage exposes no missing
normalization IfExp arcs in this original run; their truthy/error semantics
remain behavior obligations, not a justification for fake coverage.

## Stop and next decision

The author sent the unreachable-arc proof and requested coordinator decision
before test-only or runtime admission. Seven legitimate missing arcs can be
characterized, but doing so cannot meet original full-file 100%. Current source,
old tests, configuration and baseline are preserved. No Graphify update is
needed for an unapplied exterior sketch; any future accepted runtime change
still requires the dedicated backend target and related docs updates.

## Coordinator closure

The coordinator independently confirmed the unreachable `214→217` arc and
accepted the R35 stop. No test-only work to cover the other seven arcs is
admitted, since it cannot meet the required original full-file 100%. A separate
guard-removal prerequisite has been proposed to the user by the coordinator;
it is outside R35 and is not authorized in this author worktree. No native
gate, retry, runtime/test edit or commit follows this static closure. Private
prospective evidence is frozen, and the author releases the slot.

Independent review also confirmed the unreachable inheritance arc. Its precise
correction of the `254→253` plan is incorporated above: a valid later fallback
breaks the inner loop and does not cover the loop-exhaustion arc. No test is
admitted or executed for this documentation correction.
