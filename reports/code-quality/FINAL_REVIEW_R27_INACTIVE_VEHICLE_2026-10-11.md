# R27 — Independent Inactive-Vehicle Review

## Review Stage and Decision

**STATIC_REVIEW_ONLY / CHARACTERIZATION_RECOMMENDED / RUNTIME_NOT_ADMITTED.**

This is a bounded independent source review, not a final runtime acceptance.
No runtime candidate exists in the inputs reviewed. No independent pytest,
coverage, lint, native complexity, ratchet or Graphify command was run. The
Coordinator has not granted this reviewer a native execution token.

The proposed responsibility is coherent: share the inactive-vehicle anomaly
envelope while retaining the two distinct source queries and source loops.
Characterization on the original route is warranted. Runtime admission needs
the exact frozen candidate, readable source budget and original-test acceptance;
an estimated decrease or an extreme-tail preference is not sufficient.

## Ownership and Snapshot

- Reviewer worktree: `/home/cbo/CursorProjects/GAIA-campaign-20261011-r27-inactive-vehicle-review`.
- Reviewer branch: `review/complexity-r27-inactive-vehicle`.
- Reviewer HEAD: `6ab78dc42f33948d00410242e8a6a49f67a1eb90`.
- Merge-base with main: `55a1b1d35911451e018b662c2acc450bf5994ea2`.
- Initial reviewer working tree: clean.
- Exclusive reviewer output: this new report; no code, spec, shared tooling,
  baseline, ownership registry, progress or other report edits.
- Author worktree: `/home/cbo/CursorProjects/GAIA-campaign-20261011-r27-inactive-vehicle`.
- Author runtime and reviewer runtime SHA-256 independently read and equal:
  `e877a34cc20b570306939f9f527048bf77584f6b1d3e78f9b4addf557fc46279`.
- Author analysis report reviewed at SHA-256
  `5564996c89e6ee2bab2d7481d4e8b12bf88e9cf1205dab7ef3160b9f0c4cbf5f`.
- New author spec source reviewed at SHA-256
  `e4e640b12dfc451cb367e488ffdafd0f36545b684042cc7c4bc22dea07223db7`.
  It was untracked and not frozen for native admission at this observation.
  This review cannot certify later author changes under the same filename.

The checkpoint and Graphify skills, repository AGENTS, complexity skill and
quality references were consulted. No inherited main/concurrent work was edited.

## Baseline and Evidence Attribution

Coordinator-supplied accepted native baseline, not remeasured here:

| Scope | Cognitive | Cyclomatic | Effective LOC |
| --- | ---: | ---: | ---: |
| `anomalies_analytics` | 239 | 112 | 320 |
| Analytics file | Not independently measured | Not independently measured | 1204 |

The Coordinator original-run artifacts under
`~/.cache/gaia-campaign/20261011-r27-original/` were read, including
`original-audit.json`, `union.exit`, `original-audit.exit` and
`inputs-after-check.exit`. The audit records 276 tests, zero skipped, no
synthetic credit and full statement/branch coverage: analytics 634/264,
driver mapper 49/16 and orphan mapper 27/10. All three exit files contain 0.
This corroborates the reported original gate but does not constitute an
independent native reproduction or prove the new R27 spec passes.

## Behavioral Invariants

The original block at `analytics.py:1245` confirms the following:

1. The family runs only for a falsy type or `inactive_vehicle`.
2. The first query loads complete inactive `Vehicle` entities, and its
   comprehension produces IDs without assigning a new route-scope `v`.
3. No IDs means no fuel, session or second vehicle query. Otherwise query order
   is fuel, session, second complete-vehicle SELECT after the initial SELECT.
4. Both source queries use inclusive day bounds and the original inactive IDs.
   There is no status filter, ordering, limit, pagination or deduplication.
5. `all_vids` is the unfiltered union of source vehicle IDs. Even when both
   source result lists are empty, the second SELECT executes with an empty IN.
6. Map construction retains the route-scope `v` binding. The original lists,
   map, `log`, `s` and their route lifetimes remain observable to later families.
7. Every fuel result precedes every session result. Within each source, returned
   order is retained, including ties under the final stable severity sort.
8. After resolving `v`, construction evaluates ID, fixed type/severity,
   description, entity ID, label, timestamp and details in that order.
9. Label is plate then code then string vehicle ID, with lazy short-circuiting.
   A truthy plate avoids the label's code read; details still reads code later.
10. Fuel details evaluates liters before vehicle code, retains float conversion
    and the zero fallback, and inserts those keys in that order. Session details
    contains only vehicle code. No eager per-vehicle label cache is equivalent.
11. This block has no explicit mutation, flush, commit, rollback or external call.
    Query execution still carries the original SQLAlchemy autoflush behavior.
12. Public authentication, response validation, counts and final sort are not
    part of this slice and must remain unchanged.

`test_operazioni_driver_mismatch_lifetime.py` supplies three real-reader,
distinct-writer and weak-reference contracts. Its unfiltered route retains a
driver vehicle and returns BEFORE after an external AFTER commit; inactive-only
returns AFTER without that prior retention. These are genuine observable ORM
semantics, not merely implementation preferences. Keep the existing tests and
do not replace them with fixtures that strongly retain every entity.

## Characterization Review and Minimum Matrix

The new spec delegates observed `scalars` to the actual database and uses
persisted native models. Its ordered-result adapter orders actual returned rows;
it does not fabricate scalar lists. The exact payload constants are literal
expectations, not a second implementation of the mapper. Public endpoint tests
use real login and a scoped real-database dependency override.

| Behavior | Existing / proposed evidence read | Static result / remaining gate |
| --- | --- | --- |
| Complete fuel and session payload | R2 plus new literal pair and detail-key order | Adequate source assertions; execution pending |
| Four SQL queries and bound dates/IDs | New predicate/parameter observer | Real query delegation; execution pending |
| No IDs versus empty source lists | New empty and active-only controls, explicit empty second SELECT | Essential and present; execution pending |
| Label fallback priority | Five plate/code combinations applied to both sources | Supported persisted null plate/empty code; execution pending |
| Zero/negative/positive Decimal liters | Three new values, exact float and session-key absence | Supported persisted values; execution pending |
| Both inclusive edges and just outside | Four timestamps on both source kinds | Essential and present; execution pending |
| No session status filter | Open/closed/cancelled matrix | Matches source predicate; execution pending |
| Exclude active vehicles | Real active/inactive control | Present; execution pending |
| Falsy/explicit/other type gates | Three inclusion and eight exclusion cases | Present; execution pending |
| Source order and stable family ties | New reverse-ID actual-row adapter and inactive-operator tie case; existing R19 driver tie case | Complementary, no production sort added; execution pending |
| Identity/lifetime with external writer | Existing three lifetime tests | Must remain in the native union; no new weakref boundary case in reviewed spec |
| Public type alias and auth | Real login literal payload; unauthenticated 401 and no source queries | Present; execution pending; inactive-auth control not added in reviewed spec |
| Field-read short-circuit and exception timing | Original-source inspection | Not established by ordinary persisted payload tests; exact candidate review still required |

Minimum original acceptance is the complete real-only union plus the new spec,
including all three lifetime tests, with no skips and full-file coverage. Any
descriptor/tracing diagnostics needed later must be reported separately from
real persisted coverage. Do not manufacture null liters or null vehicle code:
the reviewed model columns are nonnullable. Null plate and empty code are
legitimate inputs already represented by the spec.

The reviewed auth cases do not prove every authorization failure. That is not
a reason to modify unrelated auth runtime; preserve existing controls and add
an inactive-user case only if necessary for the exact admitted behavior.

## Source Budget and Simplification Assessment

Independent bounded `awk` counts of nonempty, noncomment original source lines:

- Inactive block 1245–1295: 49 effective lines.
- Two projection loops 1272–1295: 24 effective lines.
- With both loops, both original `v` assignments and both appends preserved,
  six ordinary effective lines are already committed to the parent. At most
  18 remain for the entire mapper, added imports/aliases/metadata and extra
  multiline call-site lines if the file is not to grow beyond 1204.

This is source-budget arithmetic, not a native scanner result. Constants,
discriminator selection, type aliases and signatures all count. The author
report correctly acknowledges this limit and does not yet promise a fitting
shape. A conventional four-parameter mapper is a coherent domain boundary but
the two long identifier/description calls consume more than the minimum six
parent lines when formatted readably. A smaller discriminator call can recover
call-site space while requiring new selection logic and metadata in the mapper.
Neither alternative was implemented or admitted in the reviewed inputs.

Avoid claiming label deduplication alone as aggregate simplification. The two
existing labels contain four `or` choices in total; fuel adds one liters `or`.
Sharing the label removes two physical choices, but independently discriminating
ID, description, timestamp and details adds four choices, retaining the shared
two label choices and liters fallback. That illustrative shape has seven
choices instead of five before counting its discriminator setup. It may reduce
nesting-weighted cognitive complexity, but it does not remove all those domain
decisions. Native parent/helper/whole-file metrics and justified deltas are
required, not a lower parent number obtained by source transfer.

A metadata-based shape can avoid repeating some decisions, but its constants,
index/type choice and lazy timestamp/detail handling must be included in the
same source and aggregate budget. Ordered dict union can preserve fuel details
only when the literals use the original primitive string keys and the liters
dict is fully evaluated before the vehicle-code dict. Reading vehicle code
first and rebuilding insertion order later does not preserve evaluation order.
An `isinstance` discriminator must correctly accept native ORM subclasses;
exact-class equality or unrelated duck typing is not an equivalent substitute.

No reviewed exact readable shape currently proves file non-growth. This is
not proof that every possible small shape is impossible. Do not widen the
responsibility, move a conditional generator into a loader, shorten unrelated
code, join statements, or use squeezed long lines solely to make the arithmetic
green. Cognitive <=200 remains a preference, not permission or a hard stop.

## Required Admission and Verification

1. Freeze new-spec/report hashes and execute original characterization under
   the Coordinator's serial token; preserve any first unexplained failure.
2. Independently reproduce original real-only union/full-file coverage before
   accepting characterization. Native original evidence above is Coordinator's.
3. Review an exact private source-only candidate, with physical/effective LOC,
   all added constants/branches, field-read order and retained route bindings.
4. Authorize runtime only if that candidate fits and is genuinely simpler.
5. After implementation, reproduce the same tests/coverage; measure native
   before/after parent, helpers, aggregate decisions and whole-file LOC; require
   Ruff and actual55a ratchet zero new findings.
6. Update the dedicated Operazioni Graphify corpus for any accepted responsibility
   change, then review/integrate separately. Graph output is not complexity proof.

If no safe fitting candidate is found, retain genuine characterization and
classify runtime `NO_SAFE_CHANGE`, not `IMPROVED`. Nothing here authorizes a
baseline change, threshold/scope/ignore change, commit, integration or a second
hotspot. The full campaign remains active and incomplete.

## Files Changed / Commit / Residual Risks

Only this report was written by the reviewer. No commit was created. Runtime
and existing tests remain unchanged in this review worktree. After metrics and
runtime delta are not measured and carry zero reduction credit.

Principal unresolved risks: ORM strong-reference lifetimes, implicit autoflush,
empty-set query elimination, eager field evaluation, discriminator type behavior,
and hiding a positive file-LOC delta through metadata or formatting. An exact
candidate and serial native evidence, not an optimistic proposal, resolve them.

## Independent Native Phase — STOP on Engine Availability

This later section supersedes the preliminary static-only execution status.
Coordinator explicitly admitted ORIGINAL CHARACTERIZATION ONLY and assigned
the exclusive serial native token. The corrected frozen new spec was reread
in full at SHA-256
`d4790f9121ec81f198804557ed06f47b49d24ec94642dec2be7b67e90beb021b`.
Author report was reread at
`95981fe6796e2028019655b3b8ac0b01dd99c00c10237cc196bd951423dcabfd`.
Runtime remains the original `e877a34c` source, not a runtime candidate.

The private draft was independently read at
`2c486e7c2fa08e446f9dd5869d382c5ec9b961ebbf8ae98af92ea629b510b257`.
Bounded source counting confirms 23 mapper lines plus 16 replacement-loop
lines, totaling 39 against the original 24: **+15 effective LOC**. This exact
draft is `NO_SAFE_CHANGE / NOT_ADMITTED`; no native candidate gate or complexity
credit is inferred from successful tests of the original source.

### Independent Commands and Results

Evidence directory: `~/.cache/gaia-campaign/20261011-r27-review/`.
The private `run-native.sh` retains the exact serial argv; individual
`*.command`, `*.pid`, `*.log`, `*.exit`, XML and JSON files retain actual results.
It used integration's venv Python with this review worktree's backend CWD,
isolated SQLite path, unchanged 100% coverage threshold and private coverage
configuration. All environment variables were retained in `environment.txt`.
No tests, runtime, dependency files, baseline or shared config were edited.

| Gate | Actual result |
| --- | --- |
| Frozen source/spec/ten original specs/baseline manifest | PASS, native 0 |
| Before custody, 1673 runtime inputs plus main diff/status | PASS, native 0; byte-identical to accepted R24 and exact55a base |
| New spec plus unchanged three lifetime tests | **38 PASS**, native 0, no skipped/todo |
| Ten original specs plus new spec, `-k 'not synthetic'`, full-file coverage | **311 PASS**, native 0, no skipped/todo or synthetic credit |
| Raw XML/coverage/source/manifest audit | PASS, native 0 |
| Ruff check of new spec | PASS, native 0 |
| Ruff format check of new spec | PASS, native 0 |
| Actual `make complexity-ratchet BASE_REF=main` | **FAIL, Make exit 2: `ratchet_engine_changed`** |
| Scheduled after-manifest and after-custody gates | NOT RUN: pipeline stopped at first nonzero gate |

Raw coverage JSON and independent audit establish the exact original files:

| Runtime | Covered statements | Covered branch outcomes | Missing / partial |
| --- | ---: | ---: | --- |
| `analytics.py` | 634/634 | 264/264 | Zero |
| `_driver_mismatch.py` | 49/49 | 16/16 | Zero |
| `_orphan_session_operators.py` | 27/27 | 10/10 | Zero |

The inherited test JWT key emits unsuppressed `InsecureKeyLengthWarning` in the
public login case. Warnings are preserved in both logs; thresholds, keys and
warning handling were not altered to change the outcome.

### Exact Failure and Freeze

Actual command:

```text
make complexity-ratchet BASE_REF=main QUALITY_PYTHON=/home/cbo/CursorProjects/GAIA-campaign-20261008-integration/backend/.venv/bin/python
```

`ratchet.log` contains an explicit engine-availability failure, not a callable
matching ambiguity or a new regression finding: baseline JavaScript engine
`babel-parser-ast` version 1 records `@babel/parser: available`, whereas current
engine records `@babel/parser: missing`. Python AST engine remains version 1.
The native comparator therefore cannot certify a ratchet PASS in this review
environment. It is not valid to infer zero findings from that early failure.

Pipeline session 24497 terminated with exit 2; Make PID 794031 is terminal.
All logs, source/spec inputs and intermediate outputs were retained. No retry,
installation, dependency link, alternate base, baseline repair, exclusion or
suppression was performed. The Coordinator was notified immediately; the native
token is released with no remaining reviewer native process. Evidence occupies
approximately 3 MiB, within the 64 MiB allocation.

**Current independent decision: BLOCKED_NATIVE_RATCHET_ENVIRONMENT.**
Tests and coverage independently pass, but `ACCEPT_CHARACTERIZATION_ONLY` is
not yet issued while the required actual ratchet gate is uncertified. The
Coordinator must diagnose and explicitly authorize any environment correction
and rerun. No publication, commit, merge or runtime admission is authorized
by this report. The full campaign remains active and incomplete.

## Explained Environment Correction — Final Independent Decision

**ACCEPT_CHARACTERIZATION_ONLY.** This later decision supersedes the preceding
environment block; the original failure and freeze remain preserved evidence.
No runtime candidate is accepted, and no complexity improvement is claimed.

The Coordinator diagnosed the explicit missing-parser error, updated ownership
before correction, and linked only ignored `frontend/node_modules` to the
existing integration dependency graph. Independent inspection confirmed:

```text
review/frontend/node_modules -> /home/cbo/CursorProjects/GAIA-campaign-20261008-integration/frontend/node_modules
resolved parser: /home/cbo/CursorProjects/GAIA/frontend/node_modules/@babel/parser/lib/index.js
```

`git check-ignore` confirms the link is ignored. Versioned state did not change;
no package was installed and no source, scanner, baseline, threshold, exclusion,
config or gate was changed. The exact frozen source/spec and original manifest
were independently checked again before the explicitly re-admitted command.

The Coordinator granted the reviewer the sole native token for **only the same
actual Make ratchet command**, with separate corrected evidence labels:
`ratchet-parser-available.command`, `.pid`, `.log`, `.exit`. Original
`ratchet.command`, `.log` and `.exit=2` were not overwritten. Tests, coverage,
raw original characterization audit, Ruff and formatter were not rerun: their
inputs and previous passing evidence remain exact.

Corrected native session 15483 and Make PID 801403 terminated with exit 0.
The raw result and `audit-corrected-ratchet.cjs` independently assert:

- `base_ref`: `main`.
- `baseline_commit`: `55a1b1d35911451e018b662c2acc450bf5994ea2`.
- `findings`: `[]`.
- The new R27 spec is listed in the actual changed-file scope.
- Corrected Make exit 0; original engine-availability Make exit 2 retained.

The resumed after-manifest and after-custody commands both pass, native 0.
All 1673 runtime inputs remain byte-identical to accepted R24. Main diff/status
hashes remain `9f85e574` / `0d54d4eb`; baseline SHA remains `38e6b794`.
The full new-spec SHA remains `d4790f91`, original analytics SHA `e877a34c`,
HEAD `6ab78dc4`, merge-base exact55a. Versioned status is unchanged; only the
read-only imported new spec and this reviewer-owned new report are untracked.

Final independent evidence therefore earns original characterization acceptance:
38 focused and 311 real-only union cases PASS; no skips/todo; analytics634/264,
driver49/16 and orphan27/10 statement/branch coverage full100; raw audit, Ruff,
new-spec format, actual55a ratchet and custody PASS. No synthetic execution was
used for coverage credit. No code or test was removed, weakened or rewritten
by the reviewer.

The rejected private draft still adds 15 effective LOC and was never copied to
runtime or natively tested. Its classification remains `NO_SAFE_CHANGE /
NOT_ADMITTED`, with zero metric reduction credit. This accepted test-only stage
does not certify the full campaign, broad suites, global baseline freshness,
future runtime candidates or every ORM field-observation edge case.

No Graphify invocation, commit, integration or publication was performed by this
reviewer. Original runtime relationships did not change; the Coordinator owns
any subsequent report publication and required documentation graph refresh.
Evidence remains approximately 3.3 MiB. Native processes are terminal and the
exclusive token is released with this final report. Campaign remains active
and incomplete.
