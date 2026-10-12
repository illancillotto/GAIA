# R40 independent static review — Bonifica date guard prerequisite

Verdict: **STATIC_APPROVED_FOR_SERIAL_ORIGINAL_CHARACTERIZATION_ONLY**.
The exterior one-guard removal is source-equivalent for the actual production
resolver contract. No static blocker was found in the 89-case NEW spec. Runtime
source grant remains withheld until original characterization is observed;
runtime admission, coverage, native metrics and ratchet remain unverified.

## Ownership and snapshot

Reviewer owns only this NEW report and private sibling `review-evidence/`.
Registry and `COORDINATOR_REVIEW_GRANT.md` were read before review. Dedicated
review worktree is on `review/complexity-r40-bonifica-date-guard`, HEAD
`114fbf7196382c6446a7963c34bd89e4c9795ef5`, actual main merge-base
`55a1b1d35911451e018b662c2acc450bf5994ea2`, initially clean. Coordinator registry
still described reviewer creation as PLANNED when read; physical branch and
worktree were independently confirmed. No ownership overlap was introduced.

Checkpoint skill, Graphify skill, root AGENTS, repository complexity skill and
workflow/constraints, README, metrics, validation, quality ratchet and style
were consulted. The large PROGRESS diary was read through current entries and
the bounded R35 closure; initial aggregate output was truncated, so operative
policy sections were read separately. No scoped backend/reports AGENTS or
local module graph was found. No Graphify extraction/native-heavy gate ran.

Independently bound source SHA256:
`e01d85f2cfbd726933819db1dc32b84b46cae37b443cfc4943a9b3ad843625e4`.
Exterior proposal:
`ac6c0b36c3bd0fb8ab595c1fcee2912acbe489c618bf184f808738f6ebc40a7b`.
NEW spec:
`d77c1330e719207c4a4c3782b45080de67a8f7bb56c3ba1fb98c6e27b83dc5a0`.
Exact exterior patch:
`bc8ae7d62141972e3a3ce6fc6bcd7522520e744aaffcb926ff7e16aee7fb4368`.

Private `static-proof.json` independently rehashes 22 author freeze members,
468 frozen R35 members and 3667 tracked review inputs, with zero mismatch.
Main HEAD/status/diff, target source and baseline match the author's custody
capture; concurrent main changes remain untouched. Reviewer writes no runtime,
test, configuration, tooling, baseline or existing evidence file, and makes no
commit/merge/push.

## Source equivalence

The only byte change deletes the inner line214 predicate and dedents its sole
assignment. A separately implemented stdlib audit checks that exact replacement
against the proposal and compares the entire resulting module AST. Every other
statement/expression is unchanged, including the orchestrator and both resolvers.

The proof is specific to ordinary production values, not arbitrary monkeypatches:

1. `_resolve_job_params` first resolves the supplied real request and entity.
   Inheritance is admitted only for a date-aware entity, absent request dates
   and the same single-entity request. Other requests keep their initial dates.
2. The original same-entity SELECT, descending `started_at`, limit1 and lack of
   status filter stay in place. An absent job still keeps the initial defaults.
3. A found job reaches `_resolve_date_window_from_job` with the same entity.
   This synchronous path has no await, membership write or resolver replacement.
   Repository searches found no production writer to DATE_AWARE_SYNC_ENTITIES.
4. The inherited resolver's non-aware `(None,None)` return cannot occur here.
   Persisted missing/malformed date values are parsed and fed into the real
   Pydantic request, then the unchanged date-aware resolver.
5. Its normal return is two dates: explicit end or today, explicit start or end
   minus configured days. Inverted windows, request validation, malformed
   top-level params, timedelta overflow and date overflow can still raise at
   their original operation; none is converted into a successful null return.
6. Therefore line214 is true whenever its assignment is reached. Evaluating
   plain local `is not None` comparisons has no observable side effect; removal
   preserves the assigned dates and subsequent ISO response mapping.

Queries, transaction boundaries, DB mutation, ordering, authentication, external
calls, retry and error handling are byte/AST unchanged outside that predicate.
SQL or parsing exceptions still escape at the same operation before assignment.
The proof does not cover external mutation of the module set, internal resolver
stubs, adversarial request subclasses or fabricated `(None,None)` returns; no
such behavior is introduced to obtain coverage.

## Independent test-spec review

Static decorator counting confirms **89 cases across 13 test functions**.
No collection or execution was performed. Actual SQLite SQLAlchemy Session,
WCSyncJob, Vehicle and BonificaSyncRunRequest are used. SQL event listeners
observe SELECTs; they do not replace query methods. The only monkeypatched
inputs are `wc_sync_default_days` and `_BACKEND_PROCESS_STARTED_AT`.

| Contract | NEW cases | Static assessment |
| --- | ---: | --- |
| Four aware entities, string/list request, seven persisted-date variants |56|Real inherited and outer resolver outputs, nonnull dates, job unchanged |
| Latest same-entity job, four statuses |4|Real three-job ordering; SQL entity/limit/order parameters observed |
| Missing job defaults |4|Real empty-table query and expected dates |
| Non-aware bypass |6|Real resolver null return only outside inheritance; no SELECT |
| Explicit dates, all, multi-entity bypass |5|Invalid persisted window must not be queried |
| Direct/inherited inversion |2|Original RuntimeError, SELECT count and no mutation |
| Inherited underflow, invalid request, configured overflow |3|Actual raising operations, not fabricated resolver outputs |
| Zero/negative/normal default days |3|Real successful resolver always returns dates |
| Existing snapshot params and counters |4|Actual flush/commit and refreshed persisted state |
| Exhausted whitespace vehicle candidates |1|Real eligible ORM vehicle, empty code list |
| Aware recent active-job timestamp |1|Actual ORM identity map retains aware value/status |

All four existing Bonifica test files remain byte-identical. Tests contain no
skip, exclusion, resolver-output stub or membership manipulation. The initial
report's NOT_RUN labels are accurate; 89 is a static count, not 89 passed tests.

## Original coverage and seven reachable arcs

Read-only inspection of frozen R35 `root-evidence/original-coverage.json`
confirms 399/399 statements and 120/128 branches, with two existing excluded
lines. This is historical evidence, not a new reviewer gate.

| Original missing arc | Honest NEW input |
| --- | --- |
|99→101|Snapshot called without source_total |
|101→105|Empty updates preserve absent/existing params |
|105→107|Existing records_synced, including zero |
|107→109|Existing records_skipped, including zero |
|109→112|Existing records_errors, including zero |
|254→253|wc_id-qualified vehicle, two absent candidates and whitespace code |
|634→637|Recent timezone-aware started_at on a real Session-managed job |

These seven arcs are plausibly reachable from honest tests; only a native
coverage report can establish that they were exercised. The remaining original
arc **214→217 is KNOWN_UNREACHABLE**, not waived or manufactured. Original
characterization must have no failed test and no missing arc beyond this one.
After exact guard removal, full-file statements/branches100 is mandatory with
the unchanged coverage policy and exclusions.

## Fixture limits and residual risks

The aware timestamp case is legitimate: WCSyncJob's production column is
DateTime(timezone=True). `expire_on_commit=False` preserves the submitted UTC
datetime in the actual identity map; its identical reassignment does not invent
a resolver return. SQLite storage does not establish PostgreSQL timezone
round-trip behavior. This case tests the aware branch, not database portability.

The fixture uses Session's default autoflush=True rather than production
SessionLocal autoflush=False. Resolver cases enter with committed clean state,
so this does not fabricate the inheritance contract; no dirty-session production
transaction equivalence is claimed. Snapshot tests prove the explicit commit,
while unchanged module AST protects untouched transaction ordering.

Multiple `date.today()` reads have a small midnight-boundary flake risk. Dates
are appropriately relative, not a fixed historical window. This is not a reason
to retry a failed native test blindly; diagnose and freeze any failure first.
No full PostgreSQL integration, concurrency, external portal or campaign-wide
suite certification is supplied by this static review.

## Metrics and classification

Author exterior-only native-AST metrics report target cognitive18→10,
cyclomatic12→9, LOC26→25 and nesting3→2; all other callables remain the same
apart from positions. The independent whole-module comparison proves no helper,
relocation or transferred implementation debt. These are **prospective** metrics,
not accepted campaign reduction. Orchestrator cognitive269 remains untouched.

Current classification: **NO_CHANGE**, runtime original. The separate R35
normalization proposal is neither applied nor authorized by this review.

## Next required checkpoint

Coordinator may grant serial native **original-only** characterization with the
NEW spec and all four old files. Preserve the known one-arc deficit explicitly;
freeze/stop on any new unexplained failure or remaining reachable gap. Only
after that evidence may the exact guard patch be separately source-granted.
Final admission still requires candidate full-file100, relevant suites, Ruff,
fresh before/after report, actual main55a ratchet0, independent final/root custody
and applicable dedicated Graphify maintenance. None is declared PASS here.

## Commands and evidence

Reviewer ran bounded git status/HEAD/merge-base and read-only source/evidence
inspection. `PYTHONDONTWRITEBYTECODE=1 python3 ../review-evidence/static_audit.py`
exits0 and records hashes/AST/case count/custody, without importing application
runtime or running any native test/lint/coverage/report/ratchet gate. An empty
scoped-AGENTS discovery returned rg exit1 (no match), not a validation failure.

Static review terminates here; no native-heavy token is held.
