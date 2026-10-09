# R12 Capacitas rerun/delete command lifecycle

**IMPROVED / READY_FOR_REVIEW** for this bounded runtime slice. Global campaign
remains **ACTIVE / INCOMPLETE**. No commit, staging, pick, push or merge by the
author; independent runtime review/final certification/integration remain next.

## Authority and exact implementation

Coordinator updated integration R12 registry authorizes only
`frontend/src/components/elaborazioni/capacitas-workspace.tsx` and this new report,
after independent ORIGINAL review PASS80/476/20/full100%/main55a0, frozen review
`1a9eebed9e14be9ced7dd0418bed1b1bccaf5e84c3b8ba6d63a9b40266a41cf2`.
Runtime phase supersedes original-only ownership. All twenty specs, policy,
shared code, config/packages/tooling/baseline and previous reports remain frozen.
Coordinator retains exclusive publication/git custody and program PROGRESS.

Worktree `/home/cbo/CursorProjects/GAIA-campaign-20261009-r11-capacitas-monitors`,
branch `refactor/complexity-r12-capacitas-commands`, initial/runtime-phase HEAD
`c11503ead00a8bc5b1fe1066831254406c4d9600` includes the coordinator-published
original test commit. Main merge-base remains
`55a1b1d35911451e018b662c2acc450bf5994ea2`. Source before a232, after exactly
frozen candidate b69 (full hashes below); applied via apply_patch, no redesign.
Actual runtime diff is120insertions/120deletions in one file. All other3507
tracked paths are exact in runtime-before-protected.json; all20specs and frozen
readiness/characterization/candidate hash checks pass.

Private typed closed rerun/delete union owns real shared token, selected busy,
direct imported API call, confirmation/error, catch and finally phases.
Endpoint is a separate helper argument; state ports expose only action-specific
reload/expiry or functional row update. Eight named handlers return the shared
async helper promise directly without another async/await adoption layer.
Rerun awaits original reload; delete applies current.filter without any new
await. No export, hook, framework, generic manager or adjacent runtime module.

## Preserved behavior and proof boundaries

Missing token remains a no-op, initial busy is before try, APIs receive exact
captured token/requested ID, returned rerun ID is ignored. Exact family strings
and lazy Error.message/nonError fallback remain. Command ApiError401/403 stays
ordinary command Error; only unchanged loader classifies refresh auth. Only
rerun success resets expiry before confirmation/error/reload; delete never
resets expiry or lists. Reload reads token freshly, swallows original failures,
and finally releases busy. Functional deletion filters current rows by ID.

Original completion races remain: one scalar busy ID can be cleared by an
older command, last completion controls status/error, late list can resurrect
a deleted row, refresh and polling are not serialized with commands. No new
cancellation, generation, freshness, auth/business/status/API/render behavior.
No create/import/speed/stop or other handler was refactored.

Actual source hash equals previously independently reviewed b69. Protected
AST/source check confirms36other named functions exact and component excluding
precisely eight commands source-exact; imports, R11 helpers/constants/hooks/
JSX/other commands unchanged. Frozen readiness final oracle2664scenarios/
97872snapshot+microtick comparisons at12ticks is supplementary design evidence,
not a fresh rendered runtime execution claim. New fresh rendered gates below
exercise actual modified source with all frozen original cases.

## Fresh AST measurements before and after actual edit

Both full reports were generated from actual checkout, before then after patch,
with unchanged scanner. Full1672files:20320→20315callables; global1926errors/
2741warnings/4667findings unchanged. No transfer to another file.

| Owned workspace + unchanged fraction policy | Before | After | Delta |
| --- | ---: | ---: | ---: |
|Cognitive sum |926 |871 |-55 (-5.94%) |
|Decisions sum(cyclomatic-1) |803 |762 |-41 |
|Raw cyclomatic sum |1062 |1016 |-46 |
|Callable LOC |4677 |4615 |-62 |
|Effective file LOC |3131 |3131 |0 |
|Callables |259 |254 |-5 |
|Error findings |17 |17 |0 |
|Warning findings |16 |16 |0 |

Principal cognitive391→359 (-32,-8.18%),cyclomatic360→336,LOC2527→2487,
nesting2/params1 unchanged. Workspace3096LOC unchanged,253→248callables,
923→868cognitive,800→759decisions,1053→1007rawcyclomatic,4664→4602callableLOC.
31states/2effects/0reducers unchanged. Fraction policy35LOC/6callables unchanged.
All nested callbacks and enclosing ancestry are included in aggregates.

| New/changed callable | Cognitive | Cyclomatic | LOC | Nesting | Params |
| --- | ---: | ---: | ---: | ---: | ---: |
|runCapacitasJobCommand |9 |8 |24 |1 |3 |
|Functional updater callback |0 |1 |1 |0 |1 |
|Filter callback |0 |1 |1 |0 |1 |
|Each four rerun handlers |0 |1 |11 |0 |1 |
|Each four delete handlers |0 |1 |10 |0 |1 |

All new functions below thresholds, no new finding. Principal359 and existing
17errors/16warnings remain debt; this slice does not complete Capacitas or the
repository goal. Initial +8LOC and paired ambiguous designs remain rejected
in frozen readiness, with no waiver/matcher/baseline change.

## Fresh actual-runtime gates

Focused **80PASS / 1spec / zero skips**,7.87s,exit0. Full **476PASS / 20specs /
zero skips**,64.79s,exit0. JUnit independently476cases/20suites/0failures/0errors/
0skip. Both actual runtime files included explicitly and completely:

| Complete file | Statements | Branches | Functions | Lines |
| --- | ---: | ---: | ---: | ---: |
|Workspace |715/715 |798/798 |248/248 |622/622 |
|Fraction policy |9/9 |6/6 |6/6 |8/8 |
|Union |724/724 |804/804 |254/254 |630/630 |

All dimensions100%,0missing/0skipped; raw coverage contains exactly these two
files. Smaller counters follow actual deduplication, with include/exclude/gate
configuration unchanged. No test removed, altered, skipped or weakened.

Fresh project TypeScript exit0. Fresh explicit real-project config extension
including src, next-env, new original spec and setup-vitest exit0; no claim that
every old spec was explicitly TypeScript-checked. Actual runtime/policy/all20
spec ESLint max-warnings0:exit0,0errors/0warnings. Diff-check/integrity exit0.

**Actual `make complexity-ratchet BASE_REF=55a...` PASS0, findings[]**, immutable
baseline_commit55a, full unchanged scanner/context and17runtime paths changed
since main. This is the actual source gate, superseding exterior-only design
comparison as implementation evidence. Baseline/scanner/scope/thresholds and
exceptions byte-exact; no baseline generation/repair/sync or baseline-verify
claim. No new unexplained test/type/lint/ratchet failure.

## Graphify and attempts

Orientation used dedicated `make graphify-frontend-query Q="capacitas-workspace.tsx"`;
bounded filename relations do not prove runtime ordering. Ran pruning patch
target first: already patched. Then dedicated
`make graphify-frontend GRAPHIFY_CODE_FLAGS=--force`:exit0,AST650/650,
6048nodes/12645edges/237communities, graph.json and GRAPH_REPORT.md rebuilt.
New runCapacitasJobCommand node present with correct source_file. HTML skipped
by existing5000node visualization limit; code graph update succeeded. No docs
semantic extraction or raw root graphify; graphify-out remains ignored/uncommitted.

Initial generated apply_patch used standard unified numeric hunk headers and
was rejected (`Failed to find context '-168,6 +168,50 @@'`) before any source
write. Re-generated the same diff with apply_patch-native @@ headers; application
succeeded and exact b69hash proved no source redesign. Earlier readiness and
characterization failures remain frozen in their reports; no failed attempt
relabeled PASS. All runtime phase test/type/lint/report/ratchet/graph gates pass
on their first actual execution. No build/browser/backend/worker or unrelated
frontend suite. No install, reset, stash, source copying or worktree pruning.

## Reproduction and frozen publication

Evidence `E=/home/cbo/.cache/gaia-campaign/20261009-r12-capacitas/author`.
Actual frontend cwd for test/type/lint; root for report/ratchet/Graphify:

```bash
REPORT_JSON="$E/runtime-before-full.json" REPORT_MD="$E/runtime-before-full.md" make complexity-report
# Apply frozen b69 candidate via apply_patch, then frontend cwd:
npm run test:unit -- tests/unit/campaign-capacitas-command-lifecycle-r12.test.tsx --maxWorkers=1
VITEST_COVERAGE_INCLUDE=src/components/elaborazioni/capacitas-workspace.tsx,src/components/elaborazioni/capacitas-fraction-resolution.ts \
  npm run test:coverage -- tests/unit/campaign-capacitas- --maxWorkers=1 \
  --coverage.reportsDirectory="$E/runtime-coverage" --reporter=default --reporter=junit \
  --outputFile.junit="$E/runtime-junit.xml"
./node_modules/.bin/tsc --noEmit --incremental false
./node_modules/.bin/tsc --noEmit -p "$E/characterization-tsconfig.json"
./node_modules/.bin/eslint --max-warnings=0 src/components/elaborazioni/capacitas-workspace.tsx \
  src/components/elaborazioni/capacitas-fraction-resolution.ts tests/unit/campaign-capacitas-*.test.ts*
cd ..
REPORT_JSON="$E/runtime-after-full.json" REPORT_MD="$E/runtime-after-full.md" make complexity-report
BASE_REF=55a1b1d35911451e018b662c2acc450bf5994ea2 make complexity-ratchet
make graphify-patch-force-pruning
make graphify-frontend GRAPHIFY_CODE_FLAGS=--force
git diff --check
node "$E/audit-runtime.cjs"
```

Before/after report logs/exits, runtime-focused/coverage/project-type/
explicit-type/owned-lint/main-ratchet/graphify-pruning/graphify-force/final-audit
logs and .exit files all0. Runtime-final-audit.json retains exact protection,
metrics/helper/coverage/graph evidence. All processes terminal; author heavy
window **RELEASED**. Only actual workspace diff and this new slice report added
beside the previously frozen untracked readiness. Staging empty.

| Frozen artifact | SHA256 |
| --- | --- |
|Actual source after / exact selected candidate |b69cbc44b3c219503c940304ce9c1b335faeb7f3703d7569267ba5104bac555d |
|Actual source before |a23270634778b1243fb8ce2e01deef704ee0620a857b93b6a79591cd11c7474e |
|All-original new command characterization spec |6ca512806be4ebf2e399e1df7da735ecd37986eb485f7ca3b0cea9a6ac90189d |
|Unchanged fraction policy |0d635381b311c18477aeef375713cf336114329350bd74791a4d6da447c574eb |
|Frozen readiness |c56aab28792a9dd6060bf3b6db6b670c64e6d2b4d38cc8475c8918e16f45e9d8 |
|Frozen original characterization report |afdfc7f7e0822a0d295b3d177da58eb7f90815ef86c97936f8e9b4ee56455d3f |

This slice report hash is delivered separately. Stop terminal
**READY_FOR_REVIEW**. Independent runtime review/final verifier and Coordinator
publication/integration require separate allocation; no additional hotspot.
