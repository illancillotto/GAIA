# R51 — Fuel WC name variants: independent review

## Ownership and snapshot

- Reviewer worktree: `/media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-20261012-r51-fuel-name-variants/review-worktree`.
- HEAD: `114fbf7196382c6446a7963c34bd89e4c9795ef5`.
- Main/merge-base: `55a1b1d35911451e018b662c2acc450bf5994ea2`.
- Initial reviewer working tree clean. Runtime, tests, configuration, baseline and prior campaign evidence are read-only for this reviewer.
- Scope: one duplicated eager ordered WC name-variant construction inside `fuel_analytics`; not canonical GAIA/INAZ identity mapping.

## Static finding: test-harness binding prerequisite

The two original lists are expression-identical modulo the operator variable name. A typed helper accepting the `WCOperator` object and returning the same eager list can preserve their semantics. However, `backend/tests/test_operazioni_operator_km_r14.py:nested_ast_factory` independently compiles only the live `_op_km` node with `namespace = {}` and seven hard-coded closure bindings. It does not compile or bind a newly introduced module-level or enclosing helper. The straightforward shared-helper extraction therefore causes a `NameError` in the existing AST contracts despite equivalent production behavior.

The author independently identified this issue, agrees not to introduce runtime import/default/wrapper tricks, and has requested Coordinator authorization for a narrow test-harness binding correction. Existing tests are read-only in the initial registry. No runtime candidate or anticipated failing native gate should be admitted before that scope decision. This is a static source proof, not an executed failure or a claim that existing tests fail on original source.

## Behavioral invariants

1. Preserve eager `list[str]` evaluation before entering each consuming loop. Descriptor-read order is `first_name`, `last_name`, `last_name`, `first_name`, `username`; each display expression applies its original `or ''` and final `.strip()`. Do not cache scalar attributes or use a generator.
2. Preserve exactly three entries, including empty strings and duplicates. Username uses `or ""` without stripping, case-folding or normalization. Internal whitespace in the formatted display names is retained.
3. Consolidation iterates the existing `wc_ops_map` insertion order, skips only falsey variants, and uses assignment: collisions remain last-writer-wins. No sorting, unique set or first-match optimization.
4. `_op_km` first uses a truthy GAIA link only if the resulting aggregate is positive. Otherwise it selects the first nonempty variant present in the legacy map, including a present zero/negative/NaN total; it does not search for the first positive legacy total.
5. Preserve existing query statements, parameters, order, ORM entity references and request/session lifetime. No new query, mutation, commit, rollback, callback or cached operator state.
6. Preserve raw related-vehicle operator keys, unknown sentinel behavior, response ordering, roundings, authorization and all other analytics endpoints.

## Test matrix before implementation

| Behavior | Existing test evidence | Missing or proposed R51 addition | Current result |
|---|---|---|---|
| First-last/reverse/username fallback precedence | R14 `test_route_ordered_kilometres_and_vehicle_targets`; R2 characterization | Retain every assertion; harness binding prerequisite | Source reviewed; native not run by reviewer |
| Positive GAIA preference; zero/negative fallback; first present legacy zero/negative | R14 ordered route and bounded AST contracts | Do not fake internal maps to obtain route coverage | Source reviewed; native not run by reviewer |
| None/empty values, case, outer/internal spaces, untrimmed username | R14 `test_route_exact_name_formatting_and_nonmatches`; R28 raw key contracts | Additional persisted consolidation cases and null username | Source reviewed; native not run by reviewer |
| Consolidation and unconsolidated vehicle-related keys | R28 and original characterization | Multi-operator alias collisions with real loaded-row order | Collision test pending |
| Sentinel collision / UUID key precedence | R28 persisted tests | Retain unchanged | Source reviewed; native not run by reviewer |
| SELECT sequence, parameters, no ORM writes | R14, R28, R4 persisted route contracts | New persisted R51 cases must retain statements and refreshed entity state | Source reviewed; native not run by reviewer |
| Snapshot lifetime across external deletion | R2 `test_fuel_snapshot_survives_operator_and_logs_deleted_between_reads` | Retain unchanged | Source reviewed; native not run by reviewer |
| Five repeated eager descriptor reads | Literal source and SQLAlchemy mapped scalar attributes | Supplemental descriptor-read contract, explicitly not substitute for persisted runtime coverage | Pending |
| Full analytics statement/branch coverage100 | Prior campaign reports require fresh original and candidate union | All twelve existing specs plus R51; no filtering or exclusion | Not run for R51 |

## Complexity acceptance criteria

The target baseline supplied by Coordinator is `fuel_analytics` cognitive217/cyclomatic148/LOC329; full file cognitive724/cyclomatic501/LOC1193 with29callables. These are prior authoritative metrics, not a new reviewer measurement.

Acceptance requires fresh before/after native measurements for target, helper, every other callable and file aggregates. The duplicated five boolean fallback expressions must be physically removed once, leaving one real domain helper and two calls; recursive scanner attribution alone is insufficient proof. Aggregate cognitive and normalized decision count must decrease, legacy significant metrics must not grow, new helper must have no violations, and no debt may be moved to another file. Ratchet must actually run against main55a with zero findings; baseline/scope/configuration unchanged.

## Current disposition

**STATIC_PREREQUISITE_REQUIRED — NOT_ADMITTED**. No native-heavy command, pytest, coverage, complexity scanner, style gate or Graphify target executed by reviewer. No runtime/test edit, commit, push or merge. Final acceptance and `IMPROVED` classification remain unproven pending scope decision, candidate review and native evidence.
