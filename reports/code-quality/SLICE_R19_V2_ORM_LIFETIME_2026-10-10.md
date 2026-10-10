# R19 V2 — Driver-mismatch analytics slice

## Ownership and snapshot

Coordinator author, dedicated reused tree `GAIA-campaign-20261008-catasto-ui`,
branch `refactor/complexity-r19-driver-mismatch-v2`, HEAD9f62fe26. Immutable
merge-base55a1b1d35911451e018b662c2acc450bf5994ea2. Registry
`MULTI_AGENT_OWNERSHIP_R19_V2_R16_DIAGNOSIS_2026-10-10.md` precedes runtime work.
Only analytics.py, NEW _driver_mismatch.py, NEW driver test and this report
owned. Frozen rejected V1, main concurrent work, existing tests and baseline
remain unchanged. V1 remains REJECTED, never integrated or relabeled.

## Responsibility and invariants

One family only: driver-mismatch queries, temporal operator selection and
response mapping. Typed inputs separate database retrieval from domain mapping.
The actual route keeps `driver_mismatch_inputs` as a local through its return,
preserving the original strong ORM references across subsequent family queries.
The family mapper accepts loaded inputs, never owns or shortens their lifetime.

Query statements/order and date/type filters unchanged; assignment start/end
inclusivity, duplicates/order/falsey IDs preserved. Same canonical display
callback and fallback, literal response fields and evaluation order. No commit,
rollback, mutation, refresh/expiration, identity-map pinning, authorization,
pagination or API change. Other seven family statements AST-identical; every
other top-level route function unchanged (fuel/km/hours included).

## Characterization matrix

| Behavior | Existing/new tests | Before | After |
| --- | --- | --- | --- |
| Driver queries/filters/ordering, assignment bounds, response fallbacks |NEW exact already-reviewed test_operazioni_driver_mismatch_r19.py, actual original route first |53PASS |53PASS |
| Inter-query distinct-writer lifetime and meaningful filtered controls |Existing accepted actual-route test_operazioni_driver_mismatch_lifetime.py |3PASS |3PASS |
| Seven-family isolation and established analytics contracts |Original eight-suite plus lifetime ORM union, synthetic diagnostics excluded |250PASS |250PASS |
| Supplemental controlled diagnostic getters/boundaries |Ten separately named synthetic tests, focused only |Included in56focused |Included in56focused |

No existing test changed. Original and V2 focused56PASS,0failure/error/skip.
ORM union250PASS,10synthetic deselected,0failure/error/skip. No production
PostgreSQL certification: real persisted ORM contracts use isolated SQLite;
direct-route tests do not certify auth dependencies or all isolation levels.
No synthetic diagnostic contributes to the full-file coverage union.

## Changes

Extract typed `DriverMismatchInputs`, query loader, temporal selector, item
mapper and family mapping. Route owns loaded input references through final
response. This is the minimum lifetime correction to the rejected V1 design,
not an import of its rejected report or a change in intended behavior.

## Metrics before / after / delta

Actual unchanged scanner over analytics + orphan helper, then those plus new
driver helper; retained original9f62 source versus exact V2 runtime.

| Metric | Original | V2 | Delta |
| --- | ---: | ---: | ---: |
| anomalies_analytics cognitive |298 |239 |-59 (-19.80%) |
| anomalies_analytics cyclomatic |137 |112 |-25 |
| anomalies_analytics callable LOC |372 |320 |-52 |
| anomalies_analytics nesting / params |4 /5 |4 /5 |0 |
| Combined cognitive |855 |829 |-26 (-3.04%) |
| Combined cyclomatic |568 |572 |+4 (four new callables) |
| Combined decisions sum(cyclomatic-1) |536 |536 |0 |
| Combined callable LOC |1355 |1390 |+35 |
| Combined file effective LOC |1298 |1352 |+54 |
| Callable count |32 |36 |+4 |
| Errors / warnings |19 /12 |19 /14 |0 /+2 |

New helpers cognitive/cyclomatic/LOC/nesting/params:
loader11/10/38/2/3, selector6/7/10/0/2, item3/4/20/0/5,
family13/8/19/2/2. All below error thresholds; two declared warning tradeoffs
loadercyclomatic10 and itemparams5. Aggregate decision count stays exact,
cognitive sum falls, no helper inherits a mega-function error. No debt laundering.
Classification **IMPROVED candidate**, independent review still required.

## Tests / coverage / ratchet / style

Before full actual analytics661/661statements288/288branches and orphan27/27+
10/10,100%. After analytics641/641+272/272, new driver49/49+16/16 and orphan
27/27+10/10, all100%; no missing or partial branches. Four inherited excluded
analytics pragma lines shift391392891892→394395894895 solely due imports;
comments and excluded code unchanged. New helper has zero exclusions.

Actual immutable55a Make ratchet PASS0 findings[]; style-ratchet PASS0, scoped
Ruff and NEW helper/test format-check PASS0. Original/v2 AST reports PASS0.
Raw JUnit/coverage/report/command output/exits in `/tmp/gaia-r19-v2-20261010/`.
Focused: original-focused.xml /v2-focused.xml; union original-union.xml /
v2-union.xml; coverage original-coverage.json /v2-coverage.json. Actual
v2-ratchet.log/.exit and v2-style.log/.exit record gates. Calls used installed
integration Python read-only, cacheprovider disabled, bytecode disabled and
private coverage files. No package/install/config/baseline modifications.

Ancillary path hash lookups twice used wrong cwd-relative path and returned
missing-file errors; correct root-path hash verified. A lookup of nonexistent
functions cell0 returned missing handle; no process restarted or native gate
failure. These bookkeeping incidents do not alter successful native results.

## Source custody

Fresh3563path original manifest SHA3eede86a39a68d49f69cad5f2c28cbc0fb852373f852662e98e5dc04d7457234.
All3562 unmodified paths exact; only analytics runtime intentionally changed.
Source hashesanalytics5246989341c71d6e16d81acdabef259e49b6ff0c11b318588deaf14e13000b80;
helperd290e58ed7d0a39397b5551efb8d498f1a1587a9bdba956184ed05c17a6c447b;
newtest4943e9cd74fc407c6263f99560b5f9eb22eccf01a45c11df8a0e5198ec69f262.
Coordinator audit records literal counters/coverage/exclusions and other-family
AST equality in coordinator-audit.json. No commit/integration yet. All actual
Coordinator native gates terminal; heavy RELEASED to read-only R16 diagnosis.

## Residual risks and next action

Independent V2 review must rerun focused/ORM full-file100%, metrics/style and
actual55a ratchet on exact frozen inputs. Check route-held object lifetime,
other families, SQL order, layering and aggregate tradeoffs; no V1 acceptance
inferred from V2. After acceptance integrate one coherent runtime slice with
fresh root gates, dedicated Operazioni Graphify, global accounting and closure.
No next anomaly family or global campaign completion. Callable239 remains
above error, errors unchanged; real cognitive reduction only, not eradication.
