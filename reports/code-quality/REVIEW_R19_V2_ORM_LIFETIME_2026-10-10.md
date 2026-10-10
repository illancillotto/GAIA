# Independent review — R19 V2 ORM lifetime

## Ownership and inputs

Reviewer `/root/r19_v2_review`; dedicated worktree
`GAIA-campaign-20261008-c1-tests`, branch
`review/complexity-r19-driver-mismatch-v2`, HEAD
`9f62fe26d47c73f15a54a43e7fe78281c6102fe8`, immutable merge-base
`55a1b1d35911451e018b662c2acc450bf5994ea2`. Ownership was allocated before
activation. Only this NEW review report and private NEW evidence are writable.
Imported source, tests, SLICE, configuration, tooling and baseline are read-only.
No commit, application edit or baseline operation is authorized to the reviewer.

Frozen input SHA256:

| Input | SHA256 |
| --- | --- |
| analytics.py |5246989341c71d6e16d81acdabef259e49b6ff0c11b318588deaf14e13000b80 |
| _driver_mismatch.py |d290e58ed7d0a39397b5551efb8d498f1a1587a9bdba956184ed05c17a6c447b |
| test_operazioni_driver_mismatch_r19.py |4943e9cd74fc407c6263f99560b5f9eb22eccf01a45c11df8a0e5198ec69f262 |
| SLICE_R19_V2_ORM_LIFETIME_2026-10-10.md |baa1ef123af6d3ba2bd6bb63dd373432798296e951e42326def5c59b13e25c99 |

## Static review

No static behavioral blocker found. Actual original source was read via
`git show 9f62fe26:backend/app/modules/operazioni/routes/analytics.py` and
compared with the exact imported candidate, not with rejected V1.

- Query statements, ordering, date/type filters and conditional retrieval
  remain the same. No ORDER BY, normalization, transaction or mutation added.
- Selection preserves falsey IDs, assignment iteration order and duplicates,
  inclusive start/end bounds, short-circuit end-before-start evaluation and
  matching-driver suppression. Response field construction and canonical
  display callback preserve their evaluation order and fallback.
- Original `sessions`, `vehicles_map2`, `users_map`, `assignments` and
  `assign_by_vehicle` are never reassigned by any later family. Later lists
  use `bad_sessions`, `op_sessions` and `open_assignments`. The V2 route-held
  `driver_mismatch_inputs` therefore preserves the strong ORM references of
  those original collections through return, rather than strengthening a
  lifetime that the original shortened. Changed loop-local names do not
  shorten collection-owned references. No identity-map pinning or refresh.
- Independent AST audit confirms every other anomaly-route statement and all
  12 other top-level functions are exact, including fuel/km/hours analytics.
  Typed input has one route-local assignment and is never overwritten.
- Helpers have concrete domain responsibilities: loading, temporal assignment
  selection and response mapping. No generic manager, circular import back
  to analytics, duplicated family or transplanted mega-callable found.
- Principal cognitive reduction and combined cognitive reduction support
  `IMPROVED` subject to fresh gates. Errors do not decrease; two new warning
  tradeoffs, increased LOC and cyclomatic callable overhead must remain
  disclosed. This is not a claim of debt eradication or global completion.

Static evidence: `/tmp/gaia-r19-v2-review-20261010/static-audit.json` and
`static_audit.py`. All 3563 protected manifest paths match exactly; imported
source/test/SLICE hashes match the authorized frozen inputs. No local Operazioni
graph exists in this reused reviewer tree. Dedicated Graphify maintenance
remains an integration closure requirement, not a complexity proof.

## Independent gates

After R16 terminal freeze and explicit heavy transfer, the reviewer executed
fresh gates on the exact imported sources. All first native invocations
completed with exit0; no retry, unexplained failure, source/test/config edit,
install, skip or weakened assertion. Private command manifests and raw
logs/exits are in `/tmp/gaia-r19-v2-review-20261010/`; `run_gates.sh` records
the exact serial sequence and test environment. Python is the installed
integration backend `.venv/bin/python`, used read-only. Bytecode and pytest
cacheprovider disabled; basetemp/coverage/database paths private.

| Gate | Independent result |
| --- | --- |
| Driver test + actual-route lifetime test, without selection |56 PASS,0failure/error/skip |
| Exact nine-file ORM union, `-k 'not synthetic'` |250 PASS,0failure/error/skip |
| Full-file analytics |641/641statements,272/272branches,100% |
| Full-file NEW driver helper |49/49statements,16/16branches,100% |
| Full-file orphan helper |27/27statements,10/10branches,100% |
| Scoped Ruff, NEW helper/test format-check |PASS0 |
| Actual Make style-ratchet, immutable55a |PASS0 |
| Fresh native scoped complexity report |PASS0;36callables19errors14warnings |
| Actual Make complexity-ratchet, immutable55a |PASS0;findings[] |
| Whitespace and protected-source custody |PASS0 |

Raw JUnit independently verifies56focused/250union actual cases, no failure,
error or skipped case. Ten separately named synthetic cases present in focused
JUnit are absent from the ORM union; all46 non-synthetic focused cases are in
the union. Coverage uses the actual `app` source and full-file report selection
for the three runtime files, not extracted functions or synthetic code. Every
statement/branch denominator is positive; missing lines, missing branches and
partial branches are zero. All actual runtime paths belong to the reviewer
tree. Four inherited analytics excluded pragma lines391392891892 shifted to
394395894895; excluded code is literal-original identical. NEW helper and
orphan helper have zero exclusions. No coverage waiver or source pragma added.

Unchanged existing auth tests emit30+30 JWT `InsecureKeyLengthWarning` messages
for the21byte fixture HMAC key, as in Coordinator evidence. Warnings are
retained, not silenced; no runtime credential or authentication change.
Persisted ORM cases use SQLite, including distinct reader/writer/witness
connections and the full-route lifetime contract. This does not certify
PostgreSQL isolation levels or the full repository suite.

## Independently verified metrics

Before metrics were recomputed by the unchanged scanner `PyVisitor`,
`py_complexities` and `effective_loc` over actual git-show9f62 source; no ROOT
override, source overlay or tooling mutation. Every before callable object and
file LOC/import count matches the retained original report exactly. The fresh
native after report matches every Coordinator callable/file/violation/summary/
scope/engine/error object. Evidence: `metric_audit.py`, `metric-audit.json`,
`original-fresh-callables.json` and native `metrics.json`.

| Metric | Before | After | Delta |
| --- | ---: | ---: | ---: |
| Principal cognitive |298 |239 |-59 (-19.80%) |
| Principal cyclomatic |137 |112 |-25 |
| Principal callable LOC |372 |320 |-52 |
| Principal nesting/params |4/5 |4/5 |0 |
| Combined cognitive |855 |829 |-26 (-3.04%) |
| Combined cyclomatic |568 |572 |+4 |
| Combined decisions, sum(cyclomatic-1) |536 |536 |0 |
| Combined callable LOC |1355 |1390 |+35 |
| Combined file LOC |1298 |1352 |+54 |
| Callable count |32 |36 |+4 |
| Errors/warnings |19/12 |19/14 |0/+2 |

The new loader11cognitive/10cyclomatic, selector6/7, item3/4 and family13/8
remain below every error threshold. The two declared warnings are loader
cyclomatic10 and item params5. No hidden mega-helper or transferred error-level
finding. Improved cognitive structure is real, while decisions are unchanged;
LOC growth and warning overhead are explicit tradeoffs, not removed debt.

## Final custody and limits

`final_audit.py` / `final-audit.json` verifies raw JUnit, positive full-file
coverage, unchanged exclusions, every native exit, immutable ratchet reference
and findings, metrics and custody. All3563 protected paths and all four imported
hashes remain exact after execution. Baseline SHA256 remains
`38e6b7943cb4f2b214baac51290fdfc97a88c8ee1bf80d3c639642de77cd4d95`.
Concurrent main binary diff/status hashes remain9f85e574/0d54d4eb, exactly the
original recorded full hashes. No main or baseline change; no commit created.
Only this owned review report is new beyond the four authorized imported files.

## Decision

**ACCEPT — IMPROVED**, for this R19 V2 driver-mismatch slice only. Route-held
inputs preserve original ORM lifetime; fresh actual behavior, full-file100%,
unchanged other families, real aggregate cognitive reduction and immutable55a
ratchet independently pass. Rejected V1 remains REJECTED and excluded.

Reviewer native gates and audits are terminal; heavy RELEASED after report and
evidence freeze. Coordinator still must publish/integrate sequentially, run
actual root post-integration ratchet and dedicated Operazioni Graphify and
update campaign accounting. No global campaign completion or full final-suite
certification. Principal239 remains high; errors unchanged. R16's unrelated
matching ambiguity remains separate and BLOCKED, not solved by this acceptance.
