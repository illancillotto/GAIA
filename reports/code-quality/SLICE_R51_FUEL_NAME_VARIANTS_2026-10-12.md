# R51 author — Fuel WC name variants static readiness

## Ownership

Exclusive grant: integration registry
`docs/code-quality/MULTI_AGENT_OWNERSHIP_R51_FUEL_NAME_VARIANTS_2026-10-12.md`.
Author worktree is SSD R51 `author-worktree`; branch
`refactor/complexity-r51-fuel-name-variants`. Runtime scope was exclusively
`backend/app/modules/operazioni/routes/analytics.py`; new R51 test and this
report were permitted. Existing test files were explicitly read-only.

## Baseline

Preflight working tree was clean. HEAD
`114fbf7196382c6446a7963c34bd89e4c9795ef5`; merge-base with main
`55a1b1d35911451e018b662c2acc450bf5994ea2`. No runtime edit, commit,
merge, dependency installation or baseline operation occurred.

Analytics SHA256:
`3f0032a3cf3783a6af5771fd89d7edaa58d9c9fe28fcd3d1c0ebcfd44d5bf32d`.
Existing R14 spec SHA256:
`210b958a4d2ecfa884ad141364281119575f637669580cb24474b920847892fc`.

R50 root AST JSON SHA256:
`504e7355bb6a893e8c5876a70e58c3d7b53366a272c995320fc048fa4791b311`.
Its analytics file object was read directly: 29 callables, LOC1193,
cognitive sum724/max239, cyclomatic sum501/max148, dependency count22.
Coordinator-provided callable baseline: fuel cognitive217/cyclomatic148/LOC329.
These are inherited measurements, not a new scanner execution.

## Target callable and responsibility

`fuel_analytics` constructs the identical ordered WC alias list twice:
consolidation and nested `_op_km` fallback. Proposed private helper:

```python
def _wc_operator_name_variants(operator: WCOperator) -> list[str]:
    return [
        f"{operator.first_name or ''} {operator.last_name or ''}".strip(),
        f"{operator.last_name or ''} {operator.first_name or ''}".strip(),
        operator.username or "",
    ]
```

Replace only the two list literals with calls passing the same ORM object.
No scalar argument projection, tuple, generator, filter, normalization,
caching, deduplication, wrapper or query change. This removes duplicated
branching rather than transferring one mega-function to another file.
Actual improvement remains UNMEASURED; no predicted delta is claimed.

## Behavioral invariants

- Eager descriptor order remains first_name, last_name, last_name,
  first_name, username; username is read even when the first alias matches.
- `or ''`, outer `.strip()`, internal whitespace, case and raw username
  whitespace remain exact, including empty or duplicate aliases.
- Consolidation retains query-return order and last writer for collisions;
  empty aliases and the legacy sentinel retain current behavior.
- Positive linked GAIA kilometres still short-circuit fallback. Otherwise
  first existing nonempty alias wins even with zero/negative kilometres.
- Query SQL/binds/order/count, ORM identity/state/lifetime, auth, rounding,
  sorting, raw vehicle-related aliases, filters and response remain unchanged.
- This is legacy WC alias lookup, not GAIA/INAZ canonical identity mapping.

## Characterization tests and test matrix

No test was added or executed: Coordinator stopped at the static blocker.
The following is a proposed matrix, not evidence of PASS.

| Behavior | Existing test | Missing | Proposed added | Result |
| --- | --- | --- | --- | --- |
| Nullable/empty names, internal whitespace, case, raw username | R14 route formatting matrix | Joint consolidation/km projections for same variants | Persisted R51 route parameter matrix | NOT_RUN |
| Forward/reverse/username and positive GAIA precedence, first zero/negative | R14 full-route matrix | No existing assertion deficit identified | Retain unchanged matrix | NOT_RUN |
| Raw vehicle-related keys vs top consolidation | R28 grouping tests | Joint formatting cases | Persisted R51 alias/log/session cases | NOT_RUN |
| Cross-WC alias collision, last query writer | Characterization consolidation tests | Explicit multiple-WC collision receipt | Persisted R51 collision test, capture real query-return order without sorting | NOT_RUN |
| Eager descriptor reads and exceptions | R14 AST access-order/eager tests | Real persisted whole-route read-order receipt | Record real WC descriptors without replacing return values | NOT_RUN |
| SQL order/binds and unchanged ORM state | R14 compiled-query/state assertions; R33 public route | No global assertion deficit | Retain existing union and add R51 state snapshot | NOT_RUN |
| Permission/date boundaries and absent values | Original public analytics/R28/R31 tests | None for helper scope | Retain unchanged union | NOT_RUN |

## Static blocker and exact minimum scope decision

`backend/tests/test_operazioni_operator_km_r14.py:289` defines
`nested_ast_factory`. It extracts only live `_op_km`, wraps it with the
seven fixed legacy closure arguments, then executes with `namespace = {}`
at line323. A legitimate new module helper cannot resolve in that namespace.
Many existing `test_nested_ast_*` contracts will therefore raise NameError
after the proposed refactor. They are not excluded by `-k 'not synthetic'`.

Both author and independent reviewer found this before any runtime edit or
native gate. Runtime equivalence is not the issue: the source-extraction test
harness cannot bind a new legitimate global. Existing test ownership cannot
be assumed. No anticipated failing suite was launched.

Minimum candidate-phase fixture adaptation, only if separately authorized:

```python
namespace = {"_wc_operator_name_variants": analytics._wc_operator_name_variants}
```

This replaces only `namespace = {}` after the helper exists; original-phase
tests remain byte-exact. It binds actual production behavior, not a copied
helper, fake return, weakened assertion or test bypass. All assertions and
legacy seven closure arguments would remain intact. Its own style/metric
gate would be required. No lazy runtime import, default-argument trick or
artificial wrapper should be introduced to satisfy the AST harness.

Coordinator explicitly stopped execution pending the separate decision.

## Proposed genuine full-file coverage launcher

Original genuine twelve-spec union was read from
`/home/cbo/.cache/gaia-campaign/20261011-r28-final/union-candidate.command`.
For current source, append existing R31 and R33 specs plus NEW R51 spec:

```text
tests/test_operazioni_analytics.py
tests/test_operazioni_analytics_characterization.py
tests/test_operazioni_analytics_r2.py
tests/test_operazioni_fuel_vehicle_r3.py
tests/test_operazioni_fuel_related_r4.py
tests/test_operazioni_orphan_operator_r5.py
tests/test_operazioni_operator_km_r14.py
tests/test_operazioni_driver_mismatch_r19.py
tests/test_operazioni_driver_mismatch_lifetime.py
tests/test_operazioni_fuel_targets_r24.py
tests/test_operazioni_inactive_vehicle_r27.py
tests/test_operazioni_fuel_operator_keys_r28.py
tests/test_operazioni_session_distance_r31.py
tests/test_operazioni_operator_consumption_r33.py
tests/test_operazioni_fuel_name_variants_r51.py
```

Use real integration backend venv, private synthetic environment/SQLite,
private unique basetemp/JUnit/logs/exits and `--cov=app --cov-branch`.
Coverage config includes ENTIRE analytics.py and existing driver/orphan
helpers as in the inherited genuine union; target statement/branch100,
zero new exclusions. Candidate gates must not count copied/nested AST
synthetic execution as runtime coverage. The legacy AST assertions should
also run separately without coverage. Exact genuine-only selection must be
audited against collected test names before approving the final launcher;
the historical `not synthetic` filter alone does not omit `nested_ast` tests.
No launcher was executed and no new suite count is claimed.

## Changes

Only this report and private static evidence were added. Source and all
old tests remain byte-exact. No NEW test file was created, since running it
with a candidate was not authorized after the fixture blocker was found.

## Metric before / after / delta

Runtime metrics unchanged by source identity; new native measurements
NOT_RUN. Claimed complexity credit: zero. Baseline/scope/sensitivity unchanged.

## Tests / coverage / ratchet

All native tests, coverage, Ruff, format, report, ratchet and Graphify
NOT_RUN. Heavy execution token was never granted. This report is not a
certificate of those gates. A small static JSON lookup mistakenly treated
the file object's integer `callables` count as a list; it exited TypeError.
That observation defect is preserved in private readiness evidence, and
did not execute/retry a test or scanner.

## Classification

**NO_CHANGE_RUNTIME / BLOCKED — existing AST-fixture dependency binding.**
Not IMPROVED, not admitted, no hidden test failure ignored.

## Files changed / commit

This new report only in author working tree; private readiness evidence
outside it. No commit.

## Residual risks and next action

Await the explicit decision on existing R14 fixture ownership. If approved,
extend the registry first, add honest characterization, request serial token,
test original, refactor, test candidate, measure actual aggregates, ratchet,
independent review. If not approved, retain NO_CHANGE and select another
authorized hotspot. No automatic continuation authorizes this scope change.
