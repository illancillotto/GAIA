# R2 P3 — Independent Analytics Integration

## Ownership, snapshot and lineage

- Integration worktree: `/home/cbo/CursorProjects/GAIA-campaign-20261008-integration`;
  branch `refactor/complexity-campaign-20261008`.
- Preflight HEAD `40171b07c52140d4fe4a65b7bf2cc03d9559fefd`, working tree clean.
- Authoritative merge-base main `55a1b1d35911451e018b662c2acc450bf5994ea2`.
- Exact approved source: `6909abd756567e48c501c8ef24d8d1a15b73ebdb`,
  branch `refactor/complexity-r2-fuel-analytics`.
- Cherry-picked as `bf4c9a2643bf57852893475597a40f106dfa63e0`. Source parent and pre-integration runtime/test
  paths were identical; no inherited incomplete branch work was copied.
- Coordinator owns registry, PROGRESS and global report. This agent owns only
  this report plus the approved cherry-pick; no main, shared, baseline or
  tooling edits. Coordinator checkpoint `0551b4b1` is documentation-only and
  preserves the integrated runtime. Backend runtime is now frozen for the
  Coordinator's separate full-suite verification.

## Independent equivalence review

**PASS** for the authorized prerequisite: invariant-implied guard removal and
minimum full-file Ruff closure. This is not fuel-phase extraction or a whole
analytics refactor. Reachable fallback branches remain intact.

| Removed guard | Independently verified proof |
| --- | --- |
| Missing session/log vehicle | `VehicleUsageSession.vehicle_id` and `VehicleFuelLog.vehicle_id` are `Uuid`, `nullable=False`; persisted UUID objects are truthy, including UUID zero |
| Null WC username selected by IN | The query operand contains only truthy session names; SQL NULL cannot satisfy this IN predicate |
| Null GAIA ID selected by IN | Operand is built from non-None user IDs; SQL NULL cannot satisfy IN; schema-valid ID zero remains allowed |
| WC UUID absent from fuel grouping | Selected WC IDs originate in log references; each referenced UUID creates its grouping key before name consolidation |
| Empty related vehicle groups / UUID set | Every surviving operator key has at least one log; each log has a nonnull vehicle UUID; consolidation extends lists and deletes only superseded string keys |
| Invalid vehicle output UUID / empty vehicle log list | Output IDs are constructed as `str(vid)` from the same persisted UUID keys inserted with their first log; output IDs and grouping lists are not altered before use |

The route works on its loaded ORM objects and local groups; removed branches
would require invalid persisted data or external mutation of those private
objects, not a legitimate HTTP input. Deleting DB rows after their initial
read does not invalidate the loaded UUID/log facts. Missing operator/vehicle
lookup fallbacks remain, including real staged SQL deletion cases. No fake
null UUID query result or unreachable-branch test is used to inflate coverage.

The review also confirms unchanged SQL predicates, selected entities, query
sequence for all valid grouping states, time bounds, ranking/tie order,
positive-versus-net fuel handling, means, weighted targets, rounding,
classification, response mapping, authentication and identity precedence.
No canonical GAIA/INAZ identity mapping is changed. Anomalies and km changes
are only the explicitly authorized invariant/style prerequisites, not a
second mega-callable restructuring.

### Style equivalence

- `datetime.UTC` is Python's `timezone.utc` singleton, not a timezone change.
- `"\u2013"` produces the same en-dash character as the previous literal;
  f-string marker removal applies only to a string without interpolation.
- Parenthesis removal preserves the consumption arithmetic AST/operator order.
- `round(delta / 60)` already returns an integer because `delta` is the float
  returned by `timedelta.total_seconds()` and no `ndigits` is supplied; the
  surrounding `int` was redundant. Existing None/negative/error paths remain.
- Two local sorting callbacks bind the current grouping dictionary through a
  default argument. Each is used immediately and synchronously by `sorted`,
  before the next loop iteration or grouping reassignment. Sort scores, stable
  ordering and values are unchanged. Parameters rise from one to two, still
  below warning thresholds; no public signature changes.
- Unused imports, import ordering and local fuel-log renames have no runtime
  behavior impact. No ignore directive or mass formatting was introduced.

## Tests and behavior matrix

Existing HTTP and characterization tests are untouched; the new 459-line
test file is additive. Real persisted fixtures exercise calculations and
state rather than returning fabricated analytics results.

| Behavior | Evidence retained/added | Review |
| --- | --- | --- |
| Auth/permissions, grouping, empty period, ranking | Original HTTP suite | Unchanged |
| Positive/net/storno means, prices, zero-distance and weighted targets | Existing characterization plus persisted R2 fixtures | Meaningful numeric assertions |
| Canonical linked operator, legacy fallback and zero user ID | Persisted user/operator/session fixtures | Identity/truthiness unchanged |
| Orphan severity, inactive entities and interval/threshold boundaries | Persisted anomaly and assignment cases | Exact counts/IDs/order retained |
| Fuel-card classification and first applicable reason | Disabled/unmapped/closed/unassigned records | No artificial query results |
| SQL snapshot drift and missing operator lookup | Connection-event staged deletion of actual rows | Reachable fallback retained |
| Route distance priority and duration | Persisted route-distance session | Existing rounding semantics |
| Read-only route behavior | Session dirty-state assertions | No pending mutation |

The source report separately records its corrected test-construction failures
and pre-refactor coverage below100%; these are not hidden or claimed PASS.
Independent post-integration execution and counters are recorded below.

## Independent metrics

Before is integration HEAD40171b07, after is the approved P3 runtime. No helper
files or new callable transfer exist; the entire file aggregate is included.

| Metric | Before | After | Delta | Delta % |
| --- | ---: | ---: | ---: | ---: |
| Cognitive sum | 1034 | 991 | -43 | -4.16% |
| Cyclomatic sum | 617 | 604 | -13 | -2.11% |
| Decisions sum(cyclomatic-1) | 590 | 577 | -13 | -2.20% |
| Effective file LOC | 1305 | 1282 | -23 | -1.76% |
| Callable count | 27 | 27 | 0 | 0% |
| Errors | 19 | 19 | 0 | 0% |
| Warnings | 14 | 13 | -1 | -7.14% |

| Callable | Cognitive before/after | Cyclomatic before/after | LOC before/after | Nesting before/after | Params before/after |
| --- | ---: | ---: | ---: | ---: | ---: |
| fuel_analytics | 366/332 | 208/198 | 402/384 | 4/4 | 5/5 |
| _build_session_attribution_context | 13/10 | 10/9 | 21/19 | 3/2 | 2/2 |
| km_analytics | 46/44 | 38/37 | 138/137 | 2/2 | 5/5 |
| anomalies_analytics | 365/361 | 160/159 | 388/387 | 4/4 | 5/5 |

Classification **IMPROVED**: real aggregate reduction, unchanged callable
count, no moved debt or new/worsened violation. The two private sort callback
parameters increase1→2 for safe binding, below warning thresholds. Fuel and anomalies remain
extreme at cognitive332/361. This prerequisite does not finish either hotspot,
the extreme-tail target or the campaign.

Metrics: `/tmp/r2-integration-p3-{before,after}.json` and `.md`.

## Independent validation commands

```bash
cd backend
APP_ENV=test DATABASE_URL=sqlite:////tmp/r2-integration-p3.db \
  COVERAGE_FILE=/tmp/r2-integration-p3.coverage .venv/bin/python -m pytest -q \
  tests/test_operazioni_analytics.py \
  tests/test_operazioni_analytics_characterization.py \
  tests/test_operazioni_analytics_r2.py -o cache_dir=/tmp/r2-integration-p3-cache \
  --cov=app.modules.operazioni.routes.analytics --cov-branch \
  --cov-report=json:/tmp/r2-integration-p3-coverage.json --cov-report=term-missing
cd ..
make lint-backend BASE_REF=main QUALITY_PYTHON=backend/.venv/bin/python
make complexity-ratchet BASE_REF=main
git diff --check
```

- Lint-backend **PASS**: compilation and style ratchet across all seven changed
  Python files, including format checks of all new tests.
- Complexity ratchet **PASS**, exit0, `findings: []`, main55a.
- Diff-check and baseline/scope/exception/tooling/Makefile/package integrity
  **PASS**; no baseline-update/repair command, exclusion or suppression change.
- Targeted **79 PASS, zero skipped/failures**: original HTTP suite30,
  existing characterization20 and additive R2 cases29. Collection independently
  confirms the selected79 cases; execution completes72+7 cases without skips.
- Full-file coverage JSON directly verified: **669/669 statements and310/310
  branch outcomes,100%**, no missing statements, missing/partial branches.
  The four legacy excluded lines365–366/904–905 are the same two existing
  defensive exception handlers shifted by the refactor, not new exclusions.
- JWT short-key warnings (existing synthetic test secret) remain explicit;
  no warning suppression or auth change.
- Evidence `/tmp/r2-integration-p3-tests.log`,
  `/tmp/r2-integration-p3-coverage.json`, `/tmp/r2-integration-p3-collect.log`,
  `/tmp/r2-integration-p3-lint.log`, `/tmp/r2-integration-p3-ratchet.log`.

## Integration checkpoint

**GREEN for this single prerequisite slice**: independent review,79 tests,
full-file coverage, lint and authoritative change ratchet PASS. No overlap
with R2 frontend runtime; no subsequent backend change authorized here.
Synchronous callback binding and UTC/UUID-zero/Unicode/round invariants also
checked independently in the active Python environment. A single report-only
commit records this evidence; root retains registry/global status ownership.
Final integrated runtime SHA-256 matches the exact approved source blob:
`e3be30cc0ae8675c2e8375ee26c8d958754f6aa6c34dd3797ee5ad0ad1d8b479`.

## Graphify and verification limits

Dedicated `make graphify-operazioni-code` and module query PASS: 512 nodes,
1489 edges, 26 communities. Code corpus only; ignored artifacts not committed.
No root extraction, docs semantic extraction or Graphify complexity claim.
Evidence `/tmp/r2-integration-p3-graphify.log` and
`/tmp/r2-integration-p3-graph-query.log`.

Full backend suite is the Coordinator's separate frozen-runtime verification,
not a result claimed by this report. Prior Round2 frontend full-suite/build and
browser52PASS/7SKIP evidence explicitly predates P3. Those results are not
retroactively represented as validation of this backend commit. Historical
global-baseline divergences remain separate and unabsorbed.
