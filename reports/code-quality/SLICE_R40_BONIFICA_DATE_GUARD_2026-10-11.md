# R40 author — Bonifica date-guard prerequisite

Status: ANALYZED_AND_CHARACTERIZATION_SPEC_READY, awaiting independent review
and serial native grant. Runtime remains untouched. No test/lint/coverage/ratchet
execution or commit is claimed. The user authorized this separate prerequisite,
not the R35 result-normalization sketch or broader orchestrator refactor.

## Ownership

Dedicated SSD `r40/author-worktree`, branch
`refactor/complexity-r40-bonifica-date-guard`, HEAD
`114fbf7196382c6446a7963c34bd89e4c9795ef5`; actual main merge-base
`55a1b1d35911451e018b662c2acc450bf5994ea2`. Registry read before work from the
integration checkout. Author initially owns only this NEW report, NEW test spec
and private sibling `author-evidence/`; runtime source grant is withheld.

Checkpoint skill, root AGENTS, repository complexity skill and references,
README, metrics, validation, quality ratchet and style consulted. PROGRESS's
9888-line diary inspected through current admission entries, relevant R35
closure and final handoff. No more-specific backend AGENTS is tracked. Fresh
worktree has no code graph; no Graphify invocation without its serial grant.

## Baseline and custody

Original runtime SHA256:
`e01d85f2cfbd726933819db1dc32b84b46cae37b443cfc4943a9b3ad843625e4`.
Baseline SHA256:
`38e6b7943cb4f2b214baac51290fdfc97a88c8ee1bf80d3c639642de77cd4d95`.

Private `custody-before.json` records all3667 tracked files and main HEAD/status/
diff hash, preserving concurrent work. Fresh source census:168 registered
worktrees,153 present,15 missing registrations,220 local branches. No present
worktree has a dirty Bonifica source. Missing directories are not called clean.
Frozen R35 provenance/author/review458+5+5 members independently rehashed with
zero mismatch; originals remain untouched. Discovery initially assumed reviewer
evidence was a sibling directory; actual path is `review-worktree/review-evidence`.
The read-only directory-discovery exit2 is not a native validation failure.

## Target callable and proof

Target: `_resolve_job_params`, lines194–220. Only the redundant inheritance
guard at line214 is proposed for removal; the binding assignment stays in place.

1. Inheritance requires `entity in DATE_AWARE_SYNC_ENTITIES`, both request dates
   absent and a single-entity request.
2. The query selects the latest same-entity WCSyncJob by descending started_at,
   limit1, without filtering status. No job preserves the original defaults.
3. A found job is passed with the SAME entity to `_resolve_date_window_from_job`.
   No await, user callback or membership mutation occurs between checks.
4. The non-date-aware `(None,None)` return is unavailable on this path. Actual
   params are parsed and a real Pydantic request invokes `_resolve_date_window`.
5. A successful date-aware return always contains two dates: request.date_to or
   today, and request.date_from or end minus configured days. Missing/malformed
   persisted dates default normally. Inversion, timedelta/date overflow and
   request validation fail by raising, never by returning `(None,None)`.
6. Therefore the guard is true after every normal return in the admitted flow;
   its false arc214→217 is unreachable. Internal resolver stubs, membership
   mutation, exclusions and fake coverage are explicitly NOT used.

Private `proposed-source.py` and `guard-removal.patch` are exterior-only. The
stdlib AST verifier removes exactly the original inner If and lifts its sole
assignment; the full module AST then equals the proposal. All other callable
records are identical except shifted positions. Orchestrator, queries, API,
retry, transactions, external calls and ordering are unchanged by the proposal.
This is source proof, not completed runtime certification.

## Behavioral invariants and test matrix

The NEW spec uses real SQLite-backed SQLAlchemy sessions, actual WCSyncJob and
Vehicle entities, and real BonificaSyncRunRequest validation/resolvers. SQL
listeners observe queries; they do not replace database methods. Configuration
and process-start inputs are scoped by pytest monkeypatch, not resolver outputs.
No preexisting test is altered or mocked internal resolver introduced.

| Behavior | Existing test | Missing | Added in NEW spec | Result |
| --- | --- | --- | --- | --- |
| Four aware entities, string/list request, absent/empty/malformed/nonstring/partial/bounded stored dates | R35 route/unit tests, partial | Proof-focused matrix |56 cases assert real two-date output and unchanged ORM job |NOT_RUN |
| Latest same entity and any latest status | Existing route reuse, partial | Query constraints/status matrix |4 cases, real three-job ordering and observed SELECT/limit |NOT_RUN |
| Missing job defaults | Existing run routes | Direct invariant |4 entities |NOT_RUN |
| Non-date-aware bypass | Existing resolver users example | Full non-aware entities |6 entities, no inheritance SELECT |NOT_RUN |
| Explicit dates/all/multiple bypass malformed latest window | Existing explicit route tests, partial | No-query observation |5 cases |NOT_RUN |
| Inverted direct/inherited window exception | Existing direct unit test | Inherited real-job exception |2 cases, no mutation |NOT_RUN |
| Inherited date underflow | None located | Raising rather than null return |Real date.min job |NOT_RUN |
| Invalid request dates | Pydantic route validation | Direct real-model contract |ValidationError assertion |NOT_RUN |
| Zero/negative/normal day configuration | Existing defaults | Successful return contract |3 configurations |NOT_RUN |
| Overflowing day configuration | None located | Exception before SELECT |Real timedelta overflow |NOT_RUN |
| Snapshot retains absent/existing params and nonnull zero/nonzero counters | Existing snapshots, partial | Five reachable missing arcs99→101/101→105/105→107/107→109/109→112 |4 cases; actual commit listener and persisted refresh |NOT_RUN |
| Empty eligible vehicle exhausts candidate loop | Existing candidate fallback | Missing arc254→253 |Real wc_id vehicle with whitespace code |NOT_RUN |
| Aware active job timestamp | Existing stale jobs, mostly SQLite-naive | Missing arc634→637 |Session identity-map aware datetime, retained status |NOT_RUN |

The spec defines89 parametrized cases. Counting is static; collection/execution
has not run. Existing four test files stay byte-identical and will run with it.
Tests do not pretend to cover unreachable original214→217.

## Metric before / prospective after / delta

Installed native `PyVisitor`/effective_loc on original and exact exterior bytes:

| Metric | Original | Prospective | Delta |
| --- | ---: | ---: | ---: |
| Target cognitive |18 |10 |-8 |
| Target cyclomatic |12 |9 |-3 |
| Target LOC |26 |25 |-1 |
| Target nesting |3 |2 |-1 |
| Target params |3 |3 |0 |
| Target findings |2 warning |0 |-2 |
| File effective LOC |739 |738 |-1 |
| File summed cognitive |430 |422 |-8 |
| File summed cyclomatic |184 |181 |-3 |
| Callable count |21 |21 |0 |
| Orchestrator cognitive |269 |269 |0 |

No helper, relocation or transferred debt. These are prospective values ONLY.
Fresh before/after whole-report and ratchet remain required after source grant.

## Tests / coverage / ratchet

Frozen original R35 native evidence, NOT rerun:97 tests PASS,0failure/skip;
399/399 statements,120/128 branch arms,98.4819734345351% combined; coverage
gate exit1. Existing two excluded lines unchanged. Eight missing arcs include
the one KNOWN_UNREACHABLE214→217 and seven reachable characterization targets.

Proposed gate sequence after reviewer/native authorization:
1. NEW spec plus four existing Bonifica files on ORIGINAL runtime with full-file
   statement/branch denominator and unchanged100 threshold. Expected original
   deficit is ONLY214→217; any other failing test/missing arc STOP/freeze.
2. Only after independent original evidence/source grant, apply exact tiny
   guard patch; rerun all five files. Require full-file statement/branch100.
3. Ruff runtime/spec, format-check NEW spec, diff-check, whole complexity-report
   and actual main55a complexity-ratchet0 findings; no baseline changes.
4. Independent review/final/root custody and required dedicated Graphify before
   admission. Native-heavy gates are serial; R39 has current priority.

## Classification / files / commit / risks

Current classification: NO_CHANGE (runtime original; analysis/spec only).
NOT IMPROVED yet. Files changed: NEW
`backend/tests/test_bonifica_date_guard_prerequisite.py` and this report only.
No commit/merge/push, baseline/config/old-test/runtime edits.

Residual risks: tests not executed; full-file100 remains unproven. SQLite is
the existing characterization stack, not PostgreSQL concurrency certification.
The aware-datetime test exercises actual Session identity-map semantics, not
an invented resolver return. Broader campaign final suites remain outstanding.

Recommended next slice: none until this prerequisite is independently reviewed,
tested, measured and admitted. R35 normalization269→174 is a SEPARATE future
decision/gate, receives no credit or implementation in R40.
