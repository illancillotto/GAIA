# R10 Capacitas — Independent Actual-Source Review

## Verdict and authorization

**APPROVED / IMPROVED for the exact frozen bounded source below.** The actual
implementation preserves the reviewed original behavior and reduces combined
cognitive/decision debt without transferring violations to its new domain
module. Source commit/integration and independent heavy/final verification
remain separate Coordinator phases; this review grants neither action.
The global campaign objective remains **ACTIVE / INCOMPLETE**.

Authoritative updated R10 ownership registry and
`coordinator/ACTUAL_SOURCE_REVIEW_APPROVAL.md` were read. Reviewer checkout is
`/home/cbo/CursorProjects/GAIA-campaign-20261009-r10-capacitas-review`, branch
`review/complexity-r10-capacitas`, HEAD
`5ecbfa9ba2902a79e4e7ca532e2011e9cb90285f`, clean before this new report.
Sole writable repository path is this report. Readiness, old/new tests,
runtime, configuration and baseline are frozen. Actual author source was read
from `/home/cbo/CursorProjects/GAIA-campaign-20261009-r10-capacitas`; reviewer
neither took source custody nor cherry-picked, committed or edited it.

Author HEAD remains characterization-only
`fd26c39594d438e271ad885d725f1e182920a1e2`; its working tree contains exactly
the four authorized runtime/direct-spec/slice-report paths. Main merge-base is
`55a1b1d35911451e018b662c2acc450bf5994ea2`. Dedicated author slice report was
read fully, SHA256
`1e8e0b0837690c2ac863d71212662ce589c56919b0c8d2c2899124e0fadaa05f`.

| Actual frozen path | SHA256 |
| --- | --- |
| `frontend/src/components/elaborazioni/capacitas-workspace.tsx` | `a409e88725f0c251df7e93560c909b4464d487f382ce8ceb74787c23b2c60b59` |
| `frontend/src/components/elaborazioni/capacitas-fraction-resolution.ts` | `0d635381b311c18477aeef375713cf336114329350bd74791a4d6da447c574eb` |
| `frontend/tests/unit/campaign-capacitas-fraction-resolution-r10.test.ts` | `c2d0bf12003c5d5718af7b0c6b02af4fcc2b2e39721c68a7d7712dddb6e8848c` |

## Independent actual-source proofs

`reviewer/actual-review.mjs` reads and asserts actual runtime hashes before any
proof. It separately compares the whole actual workspace and policy with the
frozen independently reviewed design, using TypeScript token equivalence with
trivia omitted. Only legitimate policy import paths/placement and indentation
differ. The policy retains one type-only API import and no runtime dependency
on React, services, API execution or the workspace.

It then inverts exactly21enumerated replacement groups, verifies each exact
occurrence count, and reconstructs the **entire original workspace byte for
byte**. This provides complete protected AST/source preservation, stronger
than sampling selected helpers: all original38top-level declarations,
80hookcalls,601JSXelements/931attributes, unrelated imports, effects and
dependencies, list/preview construction, authentication, API call and closure,
await/catch/result branch and anomaly filter remain unchanged outside the
explicitly approved fallbacks/type/import/fiveupdater replacements.

The actual extracted domain policy independently matches the original frozen
updaters in **60** null/original/replacement-state comparisons across all five
events and provided/null/undefined/empty unsuccessful errors. Values, retained
row reference and object property order match. Ten additional null/non-null
getter-trace comparisons verify **state spread before payload access** and
identical lazy candidate.frazione_id/result.error/Error.message access. Null
returns before spread, policy lookup or factory invocation. Getter probes are
symbolic pure-contract checks, not accessor-bearing API fixtures or React
reachability witnesses.

Original3166/3206 UNKNOWN null behavior is preserved centrally, without a
dead-code assertion. Original3214/3217/3220 genuinely reachable late-response
null defenses remain semantically effective. The component continues using
functional updates at the same callsites and the same render-captured request
row/fraction. Success filters the captured original row even if the current
modal is null or replaced; an old response still updates a current replacement.
No latest-state ref, new reducer queue, cancellation, token, ownership check,
busy normalization or race fix is introduced. Success retains old error;
failure/rejection retains old success; missing token still returns before start.

The actual five reader/cell/header declarations were extracted from actual AST
and checked against the original oracle's expected outputs/errors. **56** real
CSV/XLSX outcomes PASS using both installed SheetJS0.20.3entrypoints. This
includes alias-list precedence, normalized-header last-key collisions versus
exact-duplicate-header suffixing, blank-row compression, note-only skips,
optional strings/null history identifiers, empty/header-only inputs, minimum
column errors and original compressed-row error numbering. Actual options and
serialization are unchanged; no parser result or built-in is mocked.

Installed source hashes were independently rechecked:
ESM `1a0fb062ee9781b13f6687371b202aaefc53b6ce55b530c027e01f9c087b77db`,
CJS `fd159f1e2d694e12cd0709c1ec1b63c6e1f045d2c4ce857a346f9b965798cbfa`.
The six density-dependent fallback removals remain conditional on this version
and `{defval:null,raw:false}` with header omitted. Fifteen other fallback arms
follow the independently inspected JS/Map/string/preview construction proof.
No-sheet, empty-data, cell-null, missing/optional-column, row validation/skip,
outer Array.isArray and meaningful UI guards remain intact.

## Actual metrics and debt accounting

Reviewer independently ran the unchanged production scanner on the actual two
runtime files, with output exclusively outside the repository. Its **complete
files/callables/summary/violations objects match author output exactly**, including
every new factory, nested updater and enclosing callback. No principal-only
measurement or fabricated callback identity is used.

| Metric | Original | Actual workspace | Actual policy | Actual combined / delta |
| --- | ---: | ---: | ---: | ---: |
| Cognitive sum | 1099 | 1019 | 3 | 1022 /−77 |
| Raw cyclomatic sum | 1174 | 1120 | 9 | 1129 /−45 |
| Decisions, sum(cyclomatic−1) | 923 | 869 | 3 | 872 /−51 |
| Callables | 251 | 251 | 6 | 257 /+6 |
| Effective file LOC | 3109 | 3105 | 35 | 3140 /+31 |
| Effective callable LOC | 4782 | 4776 | 13 | 4789 /+7 |
| Error findings | 24 | 22 | 0 | 22 /−2 |
| Warning findings | 20 | 19 | 0 | 19 /−1 |
| Total findings | 44 | 41 | 0 | 41 /−3 |

Principal472→455cognitive,416→404cyclomatic,2631→2625LOC; nesting2/params1
unchanged. Terreni reader51→35cognitive and28→19cyclomatic,53LOCunchanged;
history reader31→21cognitive and20→14cyclomatic,35LOCunchanged. History's
twoerrors become warnings; the total finding count nevertheless decreases.
The workspace retains31useState/2useEffect, and its legacy file LOC decreases.

All six new policy callables are below thresholds: selected/started/
synchronized0cognitive/1cyclomatic/1LOC each; unsuccessful/rejected1/2/1each;
transition1/2/8LOC/nesting1/3params. Policy has35effectiveLOC and zero findings.
Combined+31fileLOC/+7callableLOC and sixcallables are disclosed structural cost,
not hidden with formatting compression, renamed callbacks or a baseline update.

This is genuine closed-domain event decision deduplication: four redundant
nullable-state decisions disappear while the one shared invariant covers all
events and retains lazy factory evaluation. Five typed concrete event patches
do not move five guarded branches elsewhere. Combined debt decreases even
including every introduced callable. Reader fallback removal simplifies real
constructed invariants independently. The adjacent module owns a coherent
fraction-resolution state contract and no request/UI orchestration; it is
**not debt laundering or an arbitrary LOC split**. Current literal callsites
have correlated event payloads. Generic union callers remain a future API
limitation, not an introduced callsite behavior; this is a small internal domain
module, not an unrestricted public dispatcher.

## Test, coverage and gate provenance

All17frozen rendered specs, including the originalR10characterization, are
independently byte-identical. Author readiness is unchanged. The new direct
spec is exactly the frozen hash and has14genuine pure-domain tests: all five
events on null/non-null state, field retention, frozen-state/candidate/response
immutability, row identity, empty/null error rules, realError/nonError rejection
forms, and three lazy getter probes. These probes exercise the real module and
do not inject React state or manufacture upload/API output. No coverage ignore,
new skip, weakened old test, configuration exclusion or gate change is present.

Reviewer inspected the **complete actual author** coverage/ratchet/type/lint
outputs; it did not rerun heavy test/build/browser gates in this read-only phase.
Author union: **338PASS /18specs,0skip,52.94seconds,exit0**, comprising324frozen
rendered tests and14directpolicy tests. Both actual runtime paths are the only
entries in raw `coverage-final.json`. Reviewer independently recomputed line
summaries through installed Istanbul from that raw JSON, verified every raw
statement/function/branch count positive, map/counter lengths and every line
dimension100% with zero skipped entries.

| Actual runtime | Statements | Branches | Functions | Lines |
| --- | ---: | ---: | ---: | ---: |
| Workspace | 857/857 | 873/873 | 251/251 | 748/748 |
| Policy | 9/9 | 6/6 | 6/6 | 8/8 |
| Combined | 866/866 | 879/879 | 257/257 | 756/756 |

Raw coverage SHA256:
`7c8b07b5906a6d5f015be16658a1f4751f75567eec1982ffd61bf335b38fbae3`.
Original independent324PASS replay had906/929branches97.52%,exit1FAIL100,
retained in readiness; it is not retroactively waived. Actual branch maps
change because redundant expressions disappear and shared policy branches are
tested. No former impossible original arm is claimed artificially executed.

Complete actual `make complexity-ratchet BASE_REF=main` output has159changed
paths, explicitly including bothruntimepaths/directspec, baseline commit
`55a1b1d35911451e018b662c2acc450bf5994ea2`, empty findings, exit0. Reviewer parsed
the actual standalone JSON object, not Make's shell interpolation. This is the
author's real whole-change authoritative ratchet, not an external prototype
comparator. It was inspected rather than independently rerun in this phase.

Explicit actual-runtime/direct+rendered-spec TypeScript and scoped Next lint
outputs both exit0. External typeconfig includes actual source/specs and existing
runtime types with no emitted incrementals/shared config edits. Lint reports
no ESLint warning/error; its existing Next lint deprecation is distinguished.
Focused26tests also exit0. No broad frontend, build, E2E or final verifier PASS
is claimed here.

Reviewer independently hashes baseline, vitest config, package, tsconfig,
Makefile and both scanner sources against its frozen original checkout; all
match. Baseline remains
`38e6b7943cb4f2b214baac51290fdfc97a88c8ee1bf80d3c639642de77cd4d95`.
No threshold, scope, matcher, tool, package, coverage config or exclusion edit
occurred. Actual author's only tracked working-tree difference is workspace;
the policy/directspec/slicereport are its authorized untracked additions.

Dedicated author frontendGraphify target output was inspected:650freshAST
sources,6034nodes/12627edges/250communities,exit0. No prior local graph meant no
stale-edge pruning was needed. Existing5000node HTML visualization limit skips
HTML while JSON/report succeeds. No graph artifact is staged. This is graph
maintenance provenance, not a functional/complexity gate or fresh reviewer run.

## Reproduction, limitations and freeze

External reviewer evidence prefix:
`/home/cbo/.cache/gaia-campaign/20261009-r10-capacitas/reviewer/`.

| Independently executed proof | Evidence |
| --- | --- |
| Actual state/lazy/readers/design/protected source | `actual-review.mjs`, `actual-review-results.json` |
| Actual all-callable production scanner | `actual-complexity.json`/`.md`/`.log` |
| Raw coverage/gate/protected hashes audit | `actual-evidence-audit.mjs`, `actual-evidence-audit.json` |

Scanner command runs from author checkout without modifying source:

```text
PYTHONDONTWRITEBYTECODE=1 python3 tools/code_quality/complexity.py report frontend/src/components/elaborazioni/capacitas-workspace.tsx frontend/src/components/elaborazioni/capacitas-fraction-resolution.ts --json /home/cbo/.cache/gaia-campaign/20261009-r10-capacitas/reviewer/actual-complexity.json --markdown /home/cbo/.cache/gaia-campaign/20261009-r10-capacitas/reviewer/actual-complexity.md
```

The first external raw-audit attempt expected a coverage-summary reporter file
that the unchanged configuration does not generate, and failedENOENT. It was
corrected to independently derive Istanbul summaries from **raw coverage**;
no author evidence, production config or runtime changed. Final audit passes.
No unexplained functional failure or blocker remains in this bounded review.

Original/library/state source proofs are conditional on real constructed inputs
and installed dependency contract; future upgrades/options changes require
revalidation. Getter probes do not establish synchronous null-event reachability;
UNKNOWN branches remain defended. Heavy candidate replay and final application
verification are still mandatory separate phases. Main455 remains extreme,
other legacy findings/global targets remain open; this slice does not fulfill
the campaign's complete definition of success.

Only this new report is writable and uncommitted. Freeze its exact hash in
external evidence and return to Coordinator. No source/report commit,
integration, runtime custody, additional hotspot or main mutation follows
automatically from **APPROVED / IMPROVED**.
