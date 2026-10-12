# R64 — Independent Bonifica result-normalization review

## Ownership and snapshot

Static-only review; no application/test/config edits, commits, tests, scanner,
build or Graphify extraction performed by this reviewer. Dedicated branch
`review/complexity-r64-bonifica-results`, clean initial HEAD and actual main
merge-base `a51a48dc4caefbdd1aea82fe4d749054b9465970`.
Authoritative resumed registry is
`docs/code-quality/MULTI_AGENT_OWNERSHIP_RESUME_R64_2026-10-12.md` in the
integration checkout. Original campaign snapshot remains `55a1b1d35911451e018b662c2acc450bf5994ea2`.

Original runtime SHA256:
`ac6c0b36c3bd0fb8ab595c1fcee2912acbe489c618bf184f808738f6ebc40a7b`.
R40 guard prerequisite is present (`949bdf66`); no historical R35 candidate
was imported. R43/R51/R63 and rejected candidates remain outside this review.

## Independently identified invariants

`_run_bonifica_sync_background` has ten identical error-normalization
constructions, not ten interchangeable execution strategies. Preserve their
existing dispatch, awaited fetch, snapshot commit, synchronous sync call and
entity order. Only result construction is within ownership.

| Entity | Selected counters |
| --- | --- |
| report_types, reports, users, areas, warehouse_requests, org_charts, consorziati | synced / skipped |
| vehicles | vehicles_synced / vehicles_skipped |
| refuels | fuel_logs_synced / fuel_logs_skipped |
| taken_charge | usage_sessions_synced / usage_sessions_skipped |

Actual results are plain concrete dataclasses with `errors: list[str]`:
`WhiteReportTypesSyncResult`, `WhiteReportsSyncResult`,
`WhiteVehiclesSyncResult`, `WhiteOperatorsSyncResult`, `WhiteAreasSyncResult`,
`WhiteWarehouseSyncResult`, `WhiteOrgChartsSyncResult` and
`WhiteConsorziatiSyncResult`. Vehicles, refuels and taken-charge share the
vehicle-result dataclass; unrelated counters must not leak into normalization.
Reports' `total_events_created` and org charts' `entries_synced` are not the
orchestrator's synced count.

Original construction evaluates selected synced, selected skipped, full error
length, then error-list truthiness and (only when nonempty) first20 slicing and
newline join. Count is never truncated. Empty list produces `None`; a nonempty
list containing an empty string produces an empty detail, not `None`.
Ordering, embedded newlines, duplicates and whitespace are preserved; no
sorting, deduplication, conversion, sanitization or mutation is authorized.
Actual dataclass fields have no property getter side effects. New tests should
still observe list operation order and preserve invalid-item join failures.

`_finalize_job` is unchanged: errors with zero synced means failed; partial
success remains completed, including full error count/detail/report summary.
Successful finalize flushes then outer code commits. Entity exceptions persist
failed counters/detail and continue; bootstrap failure marks available jobs
failed. Nested cleanup awaits manager close and always closes the DB even if
manager close raises. No rollback/retry/transaction improvement is authorized
by this responsibility; existing semantics must be retained as-is.

## Characterization review

Existing integration coverage includes real SQLite persistence via
`test_elaborazioni_bonifica_oristanese.py`: report import, vehicles/taken-charge,
orphan refuel handling, operational users, areas, warehouse requests, canonical
org charts and consorziati. Existing failure tests cover missing user, bootstrap
login failure and provider timeout persisted in report summary. Existing live
unit and admitted date-guard tests retain date-window/scheduler/snapshot cases.
These observations are static source claims, not a fresh PASS certificate.

| Behavior | Existing source evidence | Required additional evidence |
| --- | --- | --- |
| Counter selection | Per-domain import tests | All ten actual result shapes, distinct unused counters |
| Empty/nonempty errors | Existing happy path and provider exceptions | 0, 1, 20, 21+, whitespace/newline/duplicate errors |
| Error count/detail | Persisted report summary | Full count with first20-only detail, unchanged source list |
| Partial result | Domain sync behavior | Synced >0 with errors vs zero synced with errors |
| Operation order | Original constructor source | len then truthiness then conditional slice; join failure |
| Entity error continuation | Existing orchestrator exception handlers | Persisted failure followed by next entity completion |
| Cleanup | Nested original finally | Manager close raises yet DB close still occurs |

Use concrete dataclasses for normalization inputs, genuine SQLite jobs for
observable persistence and real external boundaries for mocks. Coverage-only
patches of language builtins or unreachable branches are not characterization.

## Typing and debt review criteria

A small pure helper receiving typed selected counters and `list[str]` is a
cohesive responsibility: it deduplicates error count/detail logic and returns
the existing immutable domain result. Do not add dynamic attribute dispatch,
generic context, broad dictionaries, new entity selection or a wrapper with
the original branch tree. Counter selection remains explicit at each caller.

Before/after evidence must include principal callable and file sums/maxima,
cyclomatic/cognitive/LOC/nesting/parameters, new helpers and violation deltas.
Removing ten repeated deep conditional expressions and retaining one shallow
conditional is potentially real reduction, but not yet measured or admitted.
Fresh initial full-file100 and candidate full-file statement/branch100 are
mandatory; no new exclusions and no existing test changes.

## Pending gates and disposition

Static original review: invariants identifiable; bounded design viable.
Author original terminal evidence independently read: 186 tests, zero skipped,
398/398 statements and 126/126 branches; original source hash matches this
review checkout. Two preexisting unsupported-entity excluded lines persist;
this is no-exclusion-increase evidence, not a claim of zero historic exclusions.
Receipts are `author-evidence/original` under the resumed external evidence
root. Native execution was performed by the author, not this reviewer.

NEW characterization source statically reviewed at SHA256
`ff2a94381cc8c6c33efce1b4f3651511d041502c7cc1f39f872da85657eda96e`:
60 concrete-result cases across all ten entities plus one continuation case;
no original tests edited. Real SQLite, credential decrypt/mark-used, snapshot
and final commit observations, selected/unused counters and cleanup checks
are meaningful. Date-aware fetches retain actual date arguments. Source test
does not yet prove empty-string/whitespace/newline error fidelity or list
operation ordering; reviewer requests these targeted cases before source edit.
Domain-result stubs isolate this normalization contract; original integration
tests still exercise actual domain sync implementations and remain required.
Updated specification SHA256
`10d585752de78c23b3caa831736aaa6e2a3de0b0ddb3eef287b682b86de76152`
statically ACCEPTED for original characterization: 67 cases add exact empty,
whitespace, duplicate/embedded-newline persisted fidelity, observed list
length/truthiness/slice order and malformed-int join failure with continuation.
The list subclass observes ordinary operations; it does not patch language
builtins. Runtime remains original `ac6c0b36`; no fresh native PASS inferred.
Prior report and updated spec archived under `review-evidence/static-v1`
before this update. Independent `review-evidence/reverse_substitution.py`
will bind selected constructor arguments and reverse candidate changes to
prove all other full-module AST statements exact; execution remains pending.
Candidate not imported or reviewed yet. Original/candidate tests, coverage,
metrics, lint, exact-source custody, actual-main ratchet and independent final
verification are PENDING. No classification `IMPROVED` or admission is claimed.
Historical global baseline ambiguity and 449 backend skips remain distinct
and unverified. Native-heavy token remains with the author; this reviewer
requires a fresh Coordinator grant before independent native gates.

## Characterization STOP — required fixture email

Author `characterized-original.exit` is 1; log identifies 67 NEW setup errors
at the fixture's initial SQLite commit, before `_run_bonifica_sync_background`.
SQL insert contains `email=None`. Actual `ApplicationUser.email` is
`nullable=False`, unique and indexed; NEW fixture omitted this required field.
Original 186 cases pass, zero assertion failures, and original full-file
398/126 coverage remains100. None of this certifies NEW behavioral cases.
Author source/spec custody remains original `ac6c0b36` / `10d58575`.

Static model audit: `id`, `username`, `password_hash`, `role`, `is_active`
are supplied; remaining nonnullable application-user columns have defaults.
A synthetic email in this private per-case SQLite DB satisfies the identified
required-field omission without modifying runtime, schema, original tests,
coverage policy or permissions. No such correction or retry is authorized by
this report; Coordinator awaits an explicit separate fixture-only decision.
Classification: BLOCKED_TEST_FIXTURE, no runtime candidate or admission.
Native token released by author; reviewer ran no tests or scanner.

Previous review archived before this append under
`review-evidence/static-v2/review.md`; STOP evidence remains immutable in
`author-evidence/characterized-original` and its original log/exit receipts.

## Authorized fixture-only correction

User explicitly approved the synthetic required email only. Independent diff
against frozen `10d58575` spec contains exactly one added line:
`email="result-admin@example.local"`. Updated spec SHA256
`a3b01fd736878b0d95068a958e213773e13a6056dc4b252c4a150418e0aab150`;
runtime remains original `ac6c0b36`. Static correction ACCEPTED within scope;
original STOP receipts remain intact. Author fresh `characterized-original-v2`
execution is pending, not a PASS. Runtime modification grant remains conditional
on all253 tests PASS and full-file statement/branch100. Reviewer has no native
token; previous report and corrected spec archived in `review-evidence/static-v3`.

## Fresh original-v2 characterization

Author `characterized-original-v2.exit`0 and final log record independently
read: 253 tests PASS, full398/398 statements and126/126 branches100 with
unchanged two historic exclusions; before/after inputs equal. Runtime/source
hashes remain `ac6c0b36` / corrected spec `a3b01fd7`. Coordinator independently
read JUnit253 with zero failure/error/skip and activated bounded source grant.
This supersedes the fixture blocker for prospective refactoring only; original
failed characterization remains durable and is not rewritten as PASS.
Previous review frozen in `review-evidence/static-v4/review.md` before append.

## Exact frozen runtime candidate review

Candidate `f03279ca606ef3e2de6a77a35841205a063ff422174dd90695006c5ba77c4082`
and spec `a3b01fd7` match frozen author payload and live source. Independent
`review-evidence/reverse-substitution-frozen.json` proves exactly ten helper
calls, exact selected counter/error argument ASTs, and full-module AST equality
after reversing these calls and removing the single new helper. All query,
DB, dispatch, async, mutation, cleanup, exception, finalize and import statements
therefore remain structurally exact. Diff adds no pragma/noqa or other exclusions.

Helper has three typed parameters and returns the existing domain dataclass.
It computes full len before truthiness then conditional first20 slice/join.
Call arguments read synced, skipped, errors in that order; actual results have
plain frozen dataclass fields, not property getters, so reading the same list
once rather than repeatedly changes no concrete result-field behavior.
Error list mutation, conversion, sanitization and exception interception are
absent. Dataclass typing is retained, no generic context/dynamic dispatch added.

Author targeted native metric receipts statically inspected, not rescanned:

| Metric | Before | Candidate | Delta |
| --- | ---: | ---: | ---: |
| Principal cognitive | 269 | 174 | -95 |
| Principal cyclomatic | 47 | 37 | -10 |
| Principal LOC | 232 | 202 | -30 |
| Principal nesting / params | 13 / 3 | 13 / 3 | 0 / 0 |
| File cognitive sum | 422 | 328 | -94 |
| File cyclomatic sum | 181 | 173 | -8 |
| Effective file LOC | 738 | 717 | -21 |

New helper cognitive1/cyclomatic2/LOC9/nesting0/params3 has zero violations.
Ten duplicated normalization decisions become one shallow decision: this is
real deduplication, not transfer of the dispatch tree or a mega-helper wrapper.
Extreme >200 principal moves to174 but still above100; nesting13 and legacy
findings remain. Static disposition ACCEPTED_DESIGN, prospective IMPROVED
only if author and independent final coverage/ratchet/tests/custody gates pass.
No runtime candidate imported into review checkout yet and no native token used.
Previous report and exact candidate frozen in `review-evidence/static-v5`.
