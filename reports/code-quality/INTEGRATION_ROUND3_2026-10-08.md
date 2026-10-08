# GAIA — Independent Integration Round 3

## Scope, ownership and provenance

- Integration worktree: `/home/cbo/CursorProjects/GAIA-campaign-20261008-integration`;
  branch `refactor/complexity-campaign-20261008`.
- Ownership authorization recorded by Coordinator in `b1f4d04c`; initial
  integration HEAD `b1f4d04c8fca39c7014e2e2c2a4f4a3fc0079ae6`, clean.
- Authoritative merge-base with main:
  `55a1b1d35911451e018b662c2acc450bf5994ea2`.
- This independent agent owns this report and approved cherry-picks only.
  Coordinator governance commits arriving during review are preserved.
  Dirty main, concurrent development and all shared/protected files remain
  untouched. No baseline update/repair, threshold, scope, ignore or tooling
  change is authorized or performed.
- Backend integration was held until Coordinator explicitly released the
  frozen Round2 backend suite after 6589 PASS / 449 skip in governance `a6373849`.
  Source review/testing did not release it.
- This is a checkpoint of the ACTIVE global goal, not campaign completion.

## P1 — Monthly record insights

### Review and equivalence

Source commit `471935ec0874ba92ff71ecec0208c05e28e00709`, worktree
`GAIA-campaign-20261008-r3-presenze`. Independent review PASS:

- Operational arithmetic is actually deduplicated across collaborator, day
  and global totals. Each field retains record-order floating-point addition,
  nullish defaults, explicit zero, signed values and NaN behavior.
- Daily attention uses one coherent descriptor/index accumulator. Counts
  remain per record; sets remain distinct collaborators in insertion order.
  Monthly/global anomalies remain blocking-only, daily anomalies include
  analysis. Request detail/description semantics are unchanged.
- Absence causes, overtime fallback, availability and Saturday duplicates/
  arrival order remain identical. Existing domain helpers remain unchanged.
- Schedule counts retain strict-greater tie choice and first global truthy
  label. The additional label evaluation is a pure property/nullish reader,
  not an API/effect. No JSX, state, lifecycle, dependency array or API changes.
- Private typed facts/model are not a mega context, setter bundle or wrapper.
  No reverse dependency, cycle, duplicate pipeline or component explosion.
- Existing tests remain intact; added real UI and pure-model cases cover
  signed/nullish/NaN arithmetic, count-versus-set, ties, labels, immutable
  source records and floating-point accumulation order.

### Independent metrics

Before is integration runtime prior to P1; after includes every callable in
page, unchanged selector and new monthly model.

| Metric | Before | After | Delta |
|---|---:|---:|---:|
| Principal cognitive | 506 | 437 | -69 |
| Principal cyclomatic | 417 | 385 | -32 |
| Principal callable LOC | 2182 | 2080 | -102 |
| Principal nesting / parameters | 3 / 0 | 2 / 0 | -1 / 0 |
| Aggregate cognitive | 1429 | 1332 | -97 |
| Aggregate cyclomatic | 1442 | 1414 | -28 |
| Aggregate effective file LOC | 3042 | 3046 | +4 |
| Callable count | 315 | 322 | +7 |
| Errors / warnings | 21 / 23 | 18 / 23 | -3 / 0 |
| Page useState / useEffect | 21 / 13 | 21 / 13 | 0 / 0 |

New helper cognitive/cyclomatic sums 39/33, zero findings. New reader and all
six model callables are below warning thresholds. Main-only reduction is not
mistaken for aggregate reduction; LOC growth is disclosed.

### Independent gates and integration

Source execution: **388 PASS / four files, zero skipped**, typecheck PASS,
smoke **18 PASS**, ratchet **PASS / zero findings** against main55a.
V8 JSON counters and source mapping inspected directly:

| Full runtime file | Statements | Branch outcomes | Functions | Last mapped / source lines |
|---|---:|---:|---:|---:|
| Giornalieri page | 1093/1093 | 1245/1245 | 301/301 | 3034 / 3037 |
| Monthly model | 60/60 | 43/43 | 6/6 | 117 / 119 |
| Unchanged selector | 30/30 | 22/22 | 13/13 | 82 / 84 |

All full-file counters 100%; no whole-file ignore or censored tail, no new
coverage exclusion/suppression. Source logs
`/tmp/r3-integration-p1-source-{tests,typecheck,smoke,ratchet}.log` and
`/tmp/r3-integration-p1-source-coverage/coverage-final.json`.

Approved cherry-pick integrated as
`fbd4172dcd8a11a49a76a17784f0a61dca761e56`, after Coordinator governance
commit `a36e67bf`. Postintegration **388 PASS / four files, zero skips**, the
same full-file V8 counters, and **ratchet PASS / zero findings** independently
reproduced in integration. Logs `/tmp/r3-integration-p1-{tests,ratchet}.log`,
coverage `/tmp/r3-integration-p1-coverage/coverage-final.json`.
Measurements `/tmp/r3-integration-p1-{before,after}.json` and Markdown.

Classification: **IMPROVED**, aggregate reduction without debt transfer.
Principal 437 remains extreme; no claim of reaching the original P1 target.

## P6 — Provider credential commands

Source `82ec7533e483e13b0e3e528e7911194605723b94`, worktree
`GAIA-campaign-20261008-r3-settings`. Independent review PASS:

- Shared create/update payload construction preserves id-null versus id-zero,
  trim of label/login only, raw create password, omitted whitespace-only
  replacement password, provider flags and allowed hours.
- Helpers return original API promises, with no added async/await boundary.
  Synchronous throw, awaited completion, feedback-before-reload and
  reset-after-reload remain unchanged. Token guards/state setters remain UI.
- Error normalization is equivalent; the removed Bonifica502 branch merely
  reassigned the same Error message. ApiError detail string/object/null,
  status nullability and fallback diagnostics remain unchanged.
- Probe completion consolidates duplicate dialog fields while retaining
  Date inside the functional updater, current dialog state/open flag, reload
  ordering, token preview and success/failure diagnosis. No hook/effect/JSX
  change, generic lifecycle abstraction or dependency cycle.
- Coordinator authorized the two stale smoke assertions: create/update
  contracts now check actual helper return calls, plus awaited workspace
  linkage; all remaining assertions stay intact. This is not weakened test
  coverage. Source's initial smoke 17 PASS / 1 FAIL is disclosed in its report.
- Additive UI tests exercise pending save/reload ordering, edit during save,
  zeroid, whitespace/raw password and closed-dialog async completion.

### Independent metrics

Aggregates deliberately also include the unchanged provider-pool helper
introduced in Round2, unlike the narrower workspace-only source baseline.

| Metric | Before | After | Delta |
|---|---:|---:|---:|
| Principal cognitive | 335 | 296 | -39 |
| Principal cyclomatic | 285 | 265 | -20 |
| Principal callable LOC | 1421 | 1358 | -63 |
| Principal nesting / parameters | 2 / 1 | 2 / 1 | 0 / 0 |
| Aggregate cognitive | 606 | 540 | -66 |
| Aggregate cyclomatic | 620 | 596 | -24 |
| Aggregate effective file LOC | 1891 | 1919 | +28 |
| Callable count | 129 | 135 | +6 |
| Errors / warnings | 6 / 11 | 4 / 11 | -2 / 0 |
| Workspace useState / useEffect | 11 / 2 | 11 / 2 | 0 / 0 |

Command helper cognitive/cyclomatic 15/20, zero findings. Narrower workspace+
commands aggregate 590→524 has the same delta; nothing omitted from reduction.
LOC +28 disclosed. Principal 296 leaves the >300 tail but is still substantial.

### Independent gates and integration

Source **131 PASS / three files, zero skips**, typecheck PASS, smoke 18 PASS,
ratchet PASS / 0 findings. Approved cherry-pick integrated as
`b0dd9228b8f2f492264b372bee0a9875b05426f9` after governance `ac614d76`.
Integration independently repeats 131 PASS / full-file 100% and ratchet PASS / 0.

| Full runtime file | Statements | Branch outcomes | Functions | Last mapped / source lines |
|---|---:|---:|---:|---:|
| Workspace | 455/455 | 556/556 | 118/118 | 1811 / 1814 |
| Command helper | 24/24 | 26/26 | 7/7 | 95 / 97 |

Source mapping reaches the runtime tail; no new ignore/exclusion. Combined
P1/P6 typecheck PASS and smoke 18 PASS on integrated UI. ESLint exit 0:
seven legacy warnings independently reproduced from source65097ce2 using
stdin (three Presenze, three Settings hook dependencies, one old test unused
variable). No new error/warning, suppression or dependency-array alteration.

Evidence `/tmp/r3-integration-p6-{before,after}.json`, source and integration
`p6-{tests,ratchet}.log`, both coverage-final JSONs;
`/tmp/r3-integration-ui-{typecheck,smoke,eslint}.log`,
`/tmp/r3-integration-p1-eslint-before.log`,
`/tmp/r3-integration-p6-{eslint,tests-eslint}-before.log`.
Classification **IMPROVED**, not mere command relocation.

## P3 — Fuel vehicle metrics

Source `399825ab7118839d29e94d7106dd6569260f38ca`, worktree
`GAIA-campaign-20261008-r3-analytics`. Source review PASS, integration approved:

- Positive-liters scan and mean calculation actually run once per vehicle,
  instead of repeated scans/three identical mean calls. Arithmetic order,
  positive-versus-net distinction, net ranking/ties and nullable distance
  remain unchanged; query, authorization, SQL ordering and transactions do
  not change.
- Raw coefficient determines judgement before final coefficient rounding;
  consumption2/coefficient3/price4/cost2/liters2 precision preserved.
  NaN/infinity comparisons are preserved on pure numeric inputs; SQLite
  tests are not misrepresented as nonfinite persistence guarantees.
- Frozen three-field result is a computation value, not generic context.
  Identical judgement relocation is neutral and included in aggregates.
- Existing79 tests stay intact; ten SQL-backed response cases and nine
  direct pure-model cases are additive. No fake ORM result or gate weakening.
- Claimed improvement is deliberately modest: aggregate cognitive991→988,
  cyclomatic604→596, LOC1282→1277; principal332→322 remains extreme.

Independent source 98 cases PASS / full-file 100%, ratchet PASS / 0 and style PASS.
Coordinator explicit freeze release followed 6589 PASS / 449 skip on old Round2
backend; that result is not a PASS for the new backend. Approved cherry-pick
integrated as `0b1a0d3767e4e75b4cf34cfe0daf737609e6ccb0`, after governance
`1b195d23`. Postintegration **98 PASS, zero skipped**, independently inspected
full-file coverage 100%, ratchet PASS / 0 and changed Python style gate PASS.
Existing 60 JWT short-test-key warnings remain visible, not suppressed.

| Full runtime file | Statements | Branch outcomes | Existing exclusions |
|---|---:|---:|---:|
| Analytics | 664/664 | 302/302 | 4 defensive lines, unchanged |
| Fuel model | 20/20 | 8/8 | 0 |

JSON contains no missing/partial branch, line or omitted helper. Four excluded
analytics lines 369/370/869/870 are existing defensive handlers; their pragma
and handler text are unchanged. This is not an exclusion-free analytics claim.
Evidence `/tmp/r3-integration-p3-{tests,ratchet,style}.log`,
`/tmp/r3-integration-p3-coverage.json`, source equivalents and scoped metrics
`/tmp/r3-integration-p3-{before,after}.json`.

### Independent metrics

Before integration analytics; after includes all callables in analytics and
new computation helper, including neutral judgement relocation.

| Metric | Before | After | Delta |
|---|---:|---:|---:|
| Principal cognitive | 332 | 322 | -10 |
| Principal cyclomatic | 198 | 183 | -15 |
| Principal callable LOC | 384 | 348 | -36 |
| Principal nesting / parameters | 4 / 5 | 4 / 5 | 0 / 0 |
| Aggregate cognitive | 991 | 988 | -3 |
| Aggregate cyclomatic | 604 | 596 | -8 |
| Aggregate effective file LOC | 1282 | 1277 | -5 |
| Callable count | 27 | 28 | +1 |
| Errors / warnings | 19 / 13 | 19 / 13 | 0 / 0 |

New computation 7 cognitive / 7 cyclomatic, neutral judgement 3/4, zero helper
finding. Only 0.30% aggregate cognitive reduction, not advertised as drastic.
Classification **IMPROVED** after all scoped integration gates PASS.

## Reproducible commands

Executed independently on the exact source commits before cherry-pick, then
again in integration. All stdout/stderr redirected to the named bounded-log
evidence; no retry or failed run is counted PASS.

From `frontend/`, P1:

```bash
VITEST_COVERAGE_INCLUDE=src/app/presenze/giornaliere/page.tsx,src/app/presenze/giornaliere/collaborator-rows.ts,src/app/presenze/giornaliere/monthly-record-insights.ts \
  npm run test:coverage -- tests/unit/presenze-giornaliere-page.test.tsx \
  tests/unit/presenze-giornaliere-regressions.test.tsx \
  tests/unit/presenze-giornaliere-collaborator-rows.test.ts \
  tests/unit/presenze-giornaliere-monthly-record-insights.test.ts \
  --coverage.reportsDirectory=/tmp/r3-integration-p1-coverage
```

From `frontend/`, P6 and combined UI:

```bash
VITEST_COVERAGE_INCLUDE=src/components/elaborazioni/settings-workspace.tsx,src/components/elaborazioni/settings-provider-commands.ts \
  node_modules/.bin/vitest run \
  tests/unit/elaborazioni-settings-presenze-tab.test.tsx \
  tests/unit/elaborazioni-settings-sister.test.tsx \
  tests/unit/elaborazioni-workspace-modal.test.tsx --maxWorkers=1 --coverage \
  --coverage.reportsDirectory=/tmp/r3-integration-p6-coverage
npm run typecheck
npm test
node_modules/.bin/eslint src/app/presenze/giornaliere/page.tsx \
  src/app/presenze/giornaliere/monthly-record-insights.ts \
  tests/unit/presenze-giornaliere-page.test.tsx \
  tests/unit/presenze-giornaliere-monthly-record-insights.test.ts \
  src/components/elaborazioni/settings-workspace.tsx \
  src/components/elaborazioni/settings-provider-commands.ts \
  tests/unit/elaborazioni-settings-sister.test.tsx tests/smoke.test.mjs
```

From `backend/`, P3:

```bash
APP_ENV=test DATABASE_URL=sqlite:////tmp/r3-integration-p3.db \
  COVERAGE_FILE=/tmp/r3-integration-p3.coverage .venv/bin/python -m pytest -q \
  tests/test_operazioni_analytics.py \
  tests/test_operazioni_analytics_characterization.py \
  tests/test_operazioni_analytics_r2.py \
  tests/test_operazioni_fuel_vehicle_r3.py -o addopts='' \
  -o cache_dir=/tmp/r3-integration-p3-cache \
  --cov=app.modules.operazioni.routes.analytics \
  --cov=app.modules.operazioni.routes._fuel_vehicle_metrics \
  --cov-branch --cov-fail-under=100 \
  --cov-report=json:/tmp/r3-integration-p3-coverage.json --cov-report=term-missing
```

From repository root, ratchet after each sequential integration:

```bash
make complexity-ratchet BASE_REF=main
make lint-backend BASE_REF=main QUALITY_PYTHON=backend/.venv/bin/python
make graphify-patch-force-pruning
make graphify-frontend GRAPHIFY_CODE_FLAGS=--force
make graphify-frontend-query Q='buildMonthlyRecordInsights saveCapacitasCredentialForm'
make graphify-operazioni-code GRAPHIFY_CODE_FLAGS=--force
make graphify-operazioni-query Q='vehicle_fuel_consumption'
git diff --check
git diff main --name-only -- config/code-quality tools/code_quality Makefile \
  frontend/package.json frontend/vitest.config.ts
```

Local measurements use `backend/.venv/bin/python tools/code_quality/complexity.py
report <all slice runtime paths> --json /tmp/r3-integration-<slice>-<phase>.json
--markdown /tmp/r3-integration-<slice>-<phase>.md`. P1 includes existing selector;
P6 includes existing provider pool; P3 includes relocated judgement helper.

## Integration checkpoint

All three sequential integration gates passed; no unresolved overlap, cycle,
new helper finding or rejected regression. Runtime frozen at
`0b1a0d3767e4e75b4cf34cfe0daf737609e6ccb0`; no further runtime edits made.

| Reviewed slice | Source commit | Integrated commit | Classification |
|---|---|---|---|
| P1 monthly insights | 471935ec | fbd4172d | IMPROVED |
| P6 provider commands | 82ec7533 | b0dd9228 | IMPROVED |
| P3 vehicle fuel model | 399825ab | 0b1a0d37 | IMPROVED |

Total scoped postintegration tests **617 PASS**, zero skips (388+131+98);
smoke 18 PASS separate, not double-counted. All five changed/new runtime files
full-file statement/branch 100%, with existing analytics exclusions disclosed.

| Aggregate delta versus Round2 in the three disjoint reviewed scopes | Delta |
|---|---:|
| Cognitive, including all new/relocated helpers | -166 |
| Cyclomatic, including all callbacks/helpers | -60 |
| Effective file LOC | +27 |
| Callable count | +14 |
| Error findings | -5 |
| Warning findings | 0 |

These are scoped AST sums, not a fabricated full-repository report or a count
of independent defects. P1/P3 principal437/322 remain >300; Settings296 leaves
that tail. Campaign success targets remain open and global goal ACTIVE.

Protected
file hashes byte-identical before/after; diff versus main empty for baseline,
exceptions, complexity engines, Makefile, package manifest and V8 config.
Graphify frontend forced refresh PASS 647/647 AST files, 5999 nodes / 12563 edges /
243 communities; HTML automatically skipped above existing 5000-node limit.
Operazioni forced refresh PASS 517 nodes / 1497 edges / 26 communities. Dedicated
queries confirm model/command relationships; extracted and inferred edges
remain distinct, not evidence of complexity or functional equivalence.
Logs `/tmp/r3-integration-{frontend,operazioni}-{graphify,query}.log`.
Code graphs ignored, not committed; no raw-root or docs-semantic claim.
Baseline SHA256 remains
`38e6b7943cb4f2b214baac51290fdfc97a88c8ee1bf80d3c639642de77cd4d95`.
Protected before/after Git-object hashes in
`/tmp/r3-integration-protected-{before,after}.hash` are byte-identical.
Diff check PASS. Only this report untracked before its explicitly authorized
commit; source runtime diffs clean, dirty main never edited by this agent.
Presenze source has concurrent untracked `PLAN_R4_P1_2026-10-08.md` at the
final status check; it belongs to next-slice planning, is preserved untouched
and is not cherry-picked, reviewed or certified by this integration.
Repository-wide suites, clean build,
browser and global baseline comparison are Coordinator verification gates,
not PASS inferred from these scoped checks or prior rounds.

## Residual risks and handoff

Very large pages/routes remain. Scope-limited SQLite/unit characterization
does not certify external provider availability, PostgreSQL isolation or every
real-browser interleaving. Seven preexisting frontend style warnings, four
analytics defensive coverage exclusions and legacy global provenance remain
explicit. No new exclusion, ignore, threshold or baseline inflation.

Independent integration responsibilities complete: stop after these three
reviewed slices. Coordinator/verification agent must finish full suites,
clean build, browser gates, whole-repository metrics and provenance comparison
on this frozen runtime before opening a new authorized hotspot. Do not mark
the global goal complete based on this scoped GREEN checkpoint.
