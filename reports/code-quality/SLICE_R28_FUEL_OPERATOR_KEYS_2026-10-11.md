# R28 Fuel Operator Keys — Complexity Slice Report

## Ownership

- Author: `/root/r28_fuel_keys_author`, exclusive single responsibility.
- Worktree: `/home/cbo/CursorProjects/GAIA-campaign-20261011-r28-fuel-operator-keys`.
- Branch: `refactor/complexity-r28-fuel-operator-keys`.
- Starting HEAD `fed2cc7d0f2ee1dd128b6d11f68655179b9711d7`; main/merge-base
  `55a1b1d35911451e018b662c2acc450bf5994ea2`.
- Initial working tree clean. Coordinator registry established before activation.
- Ownership limited to analytics.py, the NEW R28 spec, this report and private evidence.

## Baseline

Authoritative native baseline report:
`~/.cache/gaia-campaign/20261011-r27-integrated/complexity.json`.
Source SHA256 `e877a34cc20b570306939f9f527048bf77584f6b1d3e78f9b4addf557fc46279`.
All 1673 runtime inputs matched accepted R27 bytes before modification.
Native before-test verification uses the exact original runtime, not a replay.

## Target callable

`fuel_analytics`: eliminate duplicated operator identity selection in its primary
grouping and per-vehicle related grouping. Do not change consolidation, query
phases, kilometre attribution, anomalies or another responsibility.

## Behavioral invariants

- `wc_operator_id is not None` wins, including zero UUID and contradictory name.
- Taken UUID branch reads the UUID attribute again. Otherwise operator_name is
  read for truthiness and again only on the taken name branch. No attribute caching.
- Truthy names remain raw: whitespace, casing and UUID-shaped strings unchanged.
- Null/empty names and literal `__no_operator__` intentionally share the unknown key.
- Primary groups alone consolidate matching name variants into referenced UUIDs.
  Per-vehicle related groups retain raw UUID/name keys.
- Net-liter ranking remains stable for ties. Related groups retain limit five;
  primary top_operators remains unbounded despite its preexisting top-ten comment.
- Existing route locals, loop locals, lists/maps and strong ORM references remain.
- SQL predicates, order, parameters, public authorization, inclusive dates,
  response schema and read-only database semantics unchanged.

## Characterization tests

NEW spec `backend/tests/test_operazioni_fuel_operator_keys_r28.py` contains 31
genuine persisted ORM/public-route cases. No existing spec changed.

| Behavior | Existing test | Missing | Added | Result |
| --- | --- | --- | --- | --- |
| UUID/name precedence and raw fallback | analytics characterization | exhaustive key families | 24 persisted cases, including zero UUID | PASS before/after |
| Consolidation differs from related keys | analytics characterization | explicit reversed insertion and each variant | 3 literal-payload cases | PASS before/after |
| Sentinel collides but does not consolidate | partial prior coverage | username collision | 1 persisted case | PASS before/after |
| Stable tie order and exact related limit | partial prior coverage | twelve equal groups, unbounded primary | 1 persisted case | PASS before/after |
| Public auth/module access and inclusive dates | original analytics | selector payload at date edges | 2 real-auth cases, 401/403/200 | PASS before/after |
| Exact SQL and mutation absence | R14 contracts | all new precedence families | included in all 24 key cases | PASS before/after |
| Other analytics and ORM lifetime | immutable R27 eleven-spec union | no scope change | unchanged existing tests | PASS before/after |

## Changes

Introduce nested typed `_fuel_operator_key(log: VehicleFuelLog) -> _uuid.UUID | str`
immediately after existing UUID import and sentinel. Two guard clauses express
one domain identity policy; both original branches become selector assignments.
No new imports, dependency, abstraction layer, query, response or shared-file edit.
Physical duplicated policies decrease two to one; four if decisions become two.
No minification, unrelated subtraction or relocated large function.

## Metric before

| Scope | Cognitive | Cyclomatic | Effective LOC | Nesting | Params |
| --- | ---: | ---: | ---: | ---: | ---: |
| fuel_analytics | 250 | 160 | 348 | 4 | 5 |
| Whole file | sum 757 / max 250 | sum 513 / max 160 | 1204 | — | — |

File callable count 28. Full-project 1673 files, 20322 callables, 1924 errors,
2740 warnings, 4664 findings. Findings are overlapping metric observations,
not independent-problem counts.

## Metric after

Native `make complexity-report` exit 0, full report under private evidence.

| Scope | Cognitive | Cyclomatic | Effective LOC | Nesting | Params |
| --- | ---: | ---: | ---: | ---: | ---: |
| fuel_analytics | 240 | 158 | 344 | 4 | 5 |
| New selector | 2 | 3 | 6 | 1 | 1 |
| Whole file | sum 749 / max 240 | sum 514 / max 158 | 1200 | — | — |

File callable count 29. Every other callable's cognitive/cyclomatic/LOC/nesting/
params/fingerprint unchanged. Selector below every threshold, zero findings.
Whole-project callable count 20323; all other aggregate counts unchanged.

## Delta

- Target cognitive -10 (-4%); cyclomatic -2 (-1.25%); LOC -4 (-1.15%).
- Whole-file cognitive sum -8 (-1.06%); LOC -4 (-0.33%).
- Raw file cyclomatic sum **+1**, explicitly not claimed reduced. One additional
  callable entry and scanner traversal of nested helpers explain the count:
  normalized sum(cyclomatic - 1) stays **485 → 485**, not a reduction.
- Physical selector duplication decreases and real covered branch outcomes
  decrease 264 → 260. Native recursive scanner counts the nested decisions both
  in parent and helper; no tooling/baseline change to alter this accounting.
- File/import/dependency count unchanged; no debt transferred to another file.
- Errors/warnings/findings unchanged; no finding-elimination credit claimed.

## Tests

Evidence directory: `~/.cache/gaia-campaign/20261011-r28-author/`.
Exact cwd/env/commands, hashes, raw native logs/exits/XML/coverage saved there.

1. Initial focused original: 29 PASS / 2 FAIL / 0 skip, exit 1. Both failures
   occurred during auth login before the analytics endpoint: configured default
   database lacked application_users. Original runtime unchanged. Failed spec
   SHA `3bd9358a55156c56dfc02d30d11b0cc807185bdd64e52e0b9f6dd78f06d980b9`,
   source/log/XML/exit preserved; pipeline stopped.
2. Coordinator separately admitted harness-only correction: move _auth_headers
   inside existing restoring real-database override, preserving every assertion.
   Corrected focus `focused-original-auth-override.*`: 31 PASS / no skip, exit 0.
3. ORIGINAL twelve-spec union: **342 PASS**, zero skips/errors/synthetic credit,
   actual session 46461 completed exit 0; audit-original exit 0.
4. Refactor only after original full-file100 verified. Same twelve-spec CANDIDATE
   union: **342 PASS**, zero skips/errors/synthetic credit, actual session 91188
   completed exit 0; audit-candidate exit 0.
5. Native full complexity-report session 27101 exit 0. Initial PRIVATE aggregate
   audit exit 1 required strict normalized cyclomatic decrease, incorrectly
   stronger than assigned non-growth requirement. STOP, original script/hash/
   log/exit preserved. Coordinator explicitly admitted audit-only non-growth
   correction: `metrics-audit-nongrowth.*` exit 0 with strict cognitive/fileLOC/
   physical duplication reduction and unchanged-other-callable checks. No
   source/spec/native report/test rerun to resolve this audit assertion.
6. Native authoritative ratchet session 49213 exit 0; Ruff runtime/spec check
   and new-spec format check exit 0; git diff --check clean.

Both unions use `-k 'not synthetic'`, coverage branch mode and fail-under100.
Old synthetic fixtures cannot contribute credit. JWT short test-secret warnings
remain visible; no warning suppression added. No broad suite/build/E2E claim.

## Coverage

| Full runtime file | Before statements/branch outcomes | After | Coverage |
| --- | ---: | ---: | --- |
| analytics.py | 634 / 264 | 632 / 260 | statement/branch 100% both |
| _driver_mismatch.py | 49 / 16 | 49 / 16 | statement/branch 100% both |
| _orphan_session_operators.py | 27 / 10 | 27 / 10 | statement/branch 100% both |

Raw JSON has zero missing statements/branch outcomes or partial branches.
Four existing excluded defensive except/return lines in analytics remain:
original 394/395/892/893, candidate 394/395/889/890. No new exclusions, skip,
ignore, fabricated model/scalar result, copied-source or handler-replay credit.
Temporary report filtering selects entire files, not changed lines; existing
R27 configuration copied byte-for-byte into private evidence only.

## Ratchet

Actual `make complexity-ratchet BASE_REF=main`: **PASS exit 0, findings []**.
Raw JSON confirms baseline_commit `55a1b1d35911451e018b662c2acc450bf5994ea2`.
No BASE_REF substitution. Baseline SHA remains
`38e6b7943cb4f2b214baac51290fdfc97a88c8ee1bf80d3c639642de77cd4d95`;
config/code-quality diff empty. No baseline command or threshold/scope changes.
Historical global FAIL30 is separate; not rerun or silently absorbed by this author.

## Classification

**IMPROVED**, bounded genuine cognitive/duplication/LOC reduction. Not elimination
of the fuel hotspot or completion of the whole campaign. Raw cyclomatic sum
increase is openly compensated by exactly one callable entry; normalized
aggregate unchanged and real physical decisions decrease.

## Files changed

- `backend/app/modules/operazioni/routes/analytics.py` — only runtime change.
  SHA `49b9ffeef7851e12aa4e8a309fb63356d226a6526cffbdaef052d4c9d3fde0d7`.
- NEW `backend/tests/test_operazioni_fuel_operator_keys_r28.py`.
  SHA `f899cf78f3842663108e624dc79658d36b5645de03676cab161ad36f21638163`.
- NEW this slice report. Root owns publication and governance updates.

Remaining 1672 runtime inputs unchanged; old specs immutable. Main binary diff
SHA9f85e574/statusSHA0d54d4eb exactly preserved; custody-final.json records full
digests. No old candidate/worktree/evidence, browser, cache or dependency removed.

## Commit

**None**: author does not commit/push/merge. Frozen uncommitted candidate ready
for separate static review, independent fresh verification and coordinator
publication. This report alone does not certify integration.

## Residual risks

- Still fuel cognitive240 and anomalies239; extreme debt remains globally.
- Real persisted tests cover externally observable semantics; exact descriptor
  read order additionally established by small source diff review, not fake
  getter coverage. Query/lifetime/transactions unchanged by construction.
- Native suite uses existing SQLite fixture, not a claim of full PostgreSQL or
  deployed-stack verification. Broad final suites/build/E2E still uncertified.
- `make graphify-operazioni-code` session67779 exit0: AST-only dedicated module
  graph rebuilt 534nodes/1533edges/26communities. Owning fuel_analytics node
  present; Graphify extractor does not expose nested selector as its own node.
  Graph ignored/uncommitted, not complexity evidence. Root refreshes its own
  integration graph after admission; no code graph copied across worktrees.

## Recommended next slice

Stop author work at this one responsibility. Coordinator reviews/verifies and
integrates only exact frozen inputs before assigning any different responsibility.
