# R35 independent static review — Bonifica result normalization

Verdict: **NO_SAFE_CHANGE / original coverage admission blocked** under the
current R35 responsibility and original full-file statement/branch 100%
precondition. The exterior normalization design is source-backed and locally
coherent, but is not admitted, applied, tested or certified. No IMPROVED credit.

## Ownership and custody

Registry read first from the integration checkout:
`docs/code-quality/MULTI_AGENT_OWNERSHIP_R35_BONIFICA_RESULTS_2026-10-11.md`.
Reviewer owns this NEW report only and private `review-evidence/`; no runtime,
tests, baseline, configuration, shared tooling or original evidence was edited.
No native gate, runtime import, Graphify extraction or commit was performed.

Review worktree:
`/media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-20261011-r35-bonifica-results/review-worktree`.
Branch `review/complexity-r35-bonifica-results`; HEAD
`0078b65ce48ba06e89c4fc3681cda1f8ae286da7`, actual main merge-base
`55a1b1d35911451e018b662c2acc450bf5994ea2`, initially clean.

Checkpoint skill, root AGENTS, repository complexity skill and workflow/
constraints, README, metrics/baseline, validation, quality ratchet, style and
coverage policy were consulted. The long PROGRESS diary was inspected through
current campaign entries, relevant headings, foundation checkpoint and final
handoff, with bounded output. No more-specific backend AGENTS was discovered.

Original runtime SHA256:
`e01d85f2cfbd726933819db1dc32b84b46cae37b443cfc4943a9b3ad843625e4`.
Reviewed exterior `../author-evidence/prospective_source.py` SHA256:
`99de7df115811f768cc3fff66ae67aa0dfeb8fac3a7f9709f28b09adae6598b3`.

## Normalization and evaluation proof

An independent stdlib AST audit found exactly ten helper calls. Replacing
each with its corresponding original result constructor, then removing the
one helper declaration, reproduces the **entire original module AST** exactly.
This establishes static preservation of every other statement and expression,
not runtime certification. Private `review-evidence/static-proof.json` records
the exact source hashes, ten counter pairs and concrete result-class hashes.

| Entity | Synced / skipped fields |
| --- | --- |
| report_types, reports, users, areas, warehouse_requests, org_charts, consorziati | synced / skipped |
| vehicles | vehicles_synced / vehicles_skipped |
| refuels | fuel_logs_synced / fuel_logs_skipped |
| taken_charge | usage_sessions_synced / usage_sessions_skipped |

The helper takes three explicit typed arguments: `synced: int`, `skipped: int`,
`errors: list[str]`. It preserves the full `len(errors)` independently from
`"\n".join(errors[:20])`, and returns None detail for an empty list. It does not
convert counters, trim error strings, sort errors, truncate before counting,
use getattr or dispatch on result types.

Original evaluation is synced field, skipped field, errors read/len, errors
read/truth, then errors read/slice/join when nonempty. Candidate evaluates
synced field, skipped field, one errors read, then len/truth/slice/join inside
the synchronous helper. All eight actual result classes are frozen plain
dataclasses with annotated fields, no bases, properties or methods; their
errors fields are ordinary lists constructed by the domain implementations.
The org-chart wrapper returns the actual accessi result after canonical sync.
There is no await, mutation or callback between these reads. Reduced repeated
attribute reads are therefore equivalent for these concrete production types.
Arbitrary result descriptors or non-list stand-ins are outside that proof.
The literal read/call trace is different and is not claimed identical.

List len, truth, slice and string join retain their ordering. Failures in
these operations remain inside the same per-entity try/except. The helper adds
a stack frame; exact traceback text is not certified. No DB operation or await
is introduced, and client construction/fetch arguments, snapshot before domain
sync, domain commits, params assignment, finalization/flush, outer commit,
entity/bootstrapping exception handling and nested manager/database cleanup
retain their original AST positions. Authentication, dependency checks, dates,
request parsing, retry behavior and entity ordering are unchanged by the sketch.

## Fresh original evidence and the blocking arc

Read-only inspection of coordinator `../root-evidence/original-coverage.json`
confirms 399/399 statements, 120/128 branch arms, 98.4819734345351% combined,
zero missing statements and two existing excluded lines (548–549). Coordinator
reports original 97 tests PASS, zero failure/skip; native 100% coverage exit1.
Those tests/gates were **not rerun by this reviewer**. No missing arc lies in a
normalization block; that does not certify positive-error or first20 behavior.

The eight missing arcs are 99→101, 101→105, 105→107, 107→109, 109→112,
214→217, 254→253 and 634→637 in the original runtime.

**214→217 cannot be exercised by the admitted real flow.**
`_resolve_job_params` lines199–203 admits inheritance only for a date-aware
entity. Line213 passes that same entity to `_resolve_date_window_from_job`
lines181–191. Its non-date-aware `(None, None)` return is therefore unavailable.
After parsing persisted params it constructs a real request and invokes
`_resolve_date_window` lines147–156. For a date-aware entity the successful
return always has `end_date = request.date_to or date.today()` and
`start_date = request.date_from or end_date - timedelta(...)`. Missing/invalid
stored dates receive defaults. Inversion, invalid settings or date overflow
raise; they do not return `(None, None)`. Hence the line214 predicate always
succeeds after a normal return and its false edge cannot execute.

An internal resolver stub returning `(None, None)`, membership mutation,
synthetic result, new exclusion or waiver would manufacture the missing path.
Removing the redundant guard is outside the ten-block R35 responsibility and
does not satisfy its original-full100-before-edit requirement. A separately
authorized prerequisite is required before reconsidering R35.

**Retracted reviewer assessment:** my initial message suggested absent/invalid
stored dates could hit214→217. That was incorrect; the defaults above disprove
it. Author and coordinator identified the mistake, and I independently checked
and explicitly corrected the proof. Private `initial-diagnostic.txt` retains
the mistaken assessment and an unrelated static metadata-parser AttributeError;
neither is a native gate outcome. The corrected static audit succeeded without
running application code or changing the reviewed source.

## Authentic characterization boundaries

Seven arcs have legitimate helper/DB characterization paths, but cannot close
the original 100% gate while214→217 remains. No such new test work is admitted.

| Arcs | Genuine contract and limitation |
| --- | --- |
| 99→101, 101→105 | Call the actual snapshot helper on a persisted WCSyncJob with omitted source_total; preserve stored params. This is helper coverage, not a claim that public background orchestration omits totals. |
| 105→107, 107→109, 109→112 | Persist non-null counters, including nonzero values, and assert snapshot preservation using the actual SQLAlchemy session. The model permits nullable and populated counters. |
| 254→253 | Persist a query-eligible Vehicle whose three candidates all exhaust through empty/whitespace/previously-seen normalized values. Distinct raw unique codes can strip to an already-seen code. A blank first candidate followed by a valid fallback breaks the loop and does not prove this exhaustion edge. |
| 634→637 | Exercise the real stale-job helper with an aware started_at on a real Session-managed job. PostgreSQL DateTime(timezone=True) supports this; SQLite reload strips timezone. A direct aware identity-map/helper case must not be represented as SQLite public-route reachability. |

Existing original tests use real SQLite sessions and public GAIA routes, patch
external manager/client boundaries and exercise actual domain sync functions.
They assert persisted imports/statuses across the ten entities, date reuse,
credential handling, missing users/jobs, bootstrap failures, stale jobs and
dependencies. Existing historical FakeDb helper/scheduler unit tests supplement
that flow; they are not evidence of persisted orchestration or a replacement
for it. No author NEW test file exists at this review cutoff.

For a future admitted normalization slice, real repeat imports should test skip
counters; real taken-charge/refuel validation errors can characterize error-only
and mixed results. More than20 actual domain errors should verify full count,
ordered first20 newline detail and persisted summary. Helper list examples may
supplement this, but fake sync return objects or impossible parser rows cannot
be credited as domain-result coverage. Client-boundary failures and observable
SQLAlchemy events can characterize continuation, commit order and cleanup;
these behavior obligations have not been newly certified here.

## Prospective metrics, not a native gate

The author provided installed-scanner static metrics. This reviewer inspected
them and verified the exact source/AST boundary, but did not run a whole native
report, style check, matcher, coverage or ratchet.

| Metric | Original | Exterior candidate |
| --- | ---: | ---: |
| Target cognitive / cyclomatic / LOC | 269 / 47 / 232 | 174 / 37 / 202 |
| Target nesting / parameters | 13 / 3 | 13 / 3 |
| File cognitive | 430 | 336 |
| File cyclomatic | 184 | 176 |
| File normalized decisions | 163 | 154 |
| File effective LOC | 739 | 718 |
| Callable count / callable findings | 21 / 13 | 22 / 13 |

Helper cognitive/cyclomatic/LOC/nesting/params =1/2/9/0/3, zero findings.
Static aggregates show a reduction without relocation of the ten blocks, but
target debt remains above threshold and findings are unchanged. This is a
prospective opportunity, not accepted reduction credit or full-file certification.

## Closure

Stop with source/tests/configuration/baseline unchanged. Coordinator original
coverage work and any separate user decision remain coordinator-owned; the
reviewer does not retry gates or expand scope. Dedicated backend Graphify and
relevant documentation remain obligations of any future accepted runtime
change; an unapplied exterior sketch needs no graph refresh. Campaign/global
coverage and broad suites are not certified by this report.
