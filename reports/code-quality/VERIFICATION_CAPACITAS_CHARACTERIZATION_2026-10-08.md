# Capacitas — Independent Final Characterization Verification

## Ownership and frozen source

Independent Final Characterization Verifier, ownership registry authorization
`d18ecaff`. Owns only this report. No runtime, test, baseline, configuration,
tooling or shared-documentation changes; no self-integration/cherry-pick.

- Worktree: `/home/cbo/CursorProjects/GAIA-campaign-20261008-char-verification`.
- Branch: `refactor/complexity-characterization-verification`.
- Verified source: `df86527b4fe979b507dde7dbdcbc443c574e1869`.
- Frozen frontend tree: `1ddc7041881a24259e30dd81491aafba44fdb104`.
- `git status --short`: empty before verification and after all gates.
- `git merge-base HEAD main`: `55a1b1d35911451e018b662c2acc450bf5994ea2`.
- The report-only commit SHA is delivered separately to the Coordinator; it
  does not change the verified frontend tree and is not a self-referential SHA.

Read the checkpoint/project complexity skills and quality references. Reviewed
Integration5 and the latest defensive provenance read-only from the integration
worktree, without importing its later documentation commits. Main's concurrent
dirty work was neither copied nor modified.

## Independently executed gates

All commands below execute in this verifier worktree, not an inherited run.
Logs and reports are disposable `/tmp` artifacts.

| Gate | Actual result | Artifact prefix `/tmp/gaia-capacitas-independent-final` |
|---|---|---|
| Full AST complexity report | PASS, exit0 | `-complexity.json`, `-complexity.md`, `-complexity.log` |
| Change ratchet against main | PASS, exit0, zero findings | `-ratchet.log` |
| Global baseline comparison | FAIL, Make exit2/scanner exit1; 30 historical findings | `-check.log` |
| Actual fifteen-spec coverage union | 306 tests PASS, 15 specs PASS, zero skips; coverage FAIL exit1 | `-coverage.log`, `-coverage.exit`, `-coverage/coverage-final.json` |
| Explicit new C10/C11 TypeScript | PASS, exit0 | `-types.json`, `-types.log` |
| Scoped new C10/C11 lint | PASS, exit0; existing Next lint deprecation only | `-lint.log` |
| Independent AST/finding/protected/residual assertions | PASS, exit0 | `-audit.cjs`, `-audit.log`, `-audit.json`, `-residual-ledger.md` |
| Runtime diff against R3 `0b1a0d37` | Empty, exit0 | `git diff --exit-code` |
| Whitespace and clean verifier tree | PASS | `git diff --check`, `git status --short` |

Reproduction from worktree root:

```bash
make complexity-report QUALITY_PYTHON=backend/.venv/bin/python \
  REPORT_JSON=/tmp/gaia-capacitas-independent-final-complexity.json \
  REPORT_MD=/tmp/gaia-capacitas-independent-final-complexity.md
make complexity-ratchet BASE_REF=main QUALITY_PYTHON=backend/.venv/bin/python
make complexity-check QUALITY_PYTHON=backend/.venv/bin/python
cd frontend
VITEST_COVERAGE_INCLUDE=src/components/elaborazioni/capacitas-workspace.tsx \
  npm run test:coverage -- 'tests/unit/campaign-capacitas-' --maxWorkers=1 \
  --coverage.reportsDirectory=/tmp/gaia-capacitas-independent-final-coverage
./node_modules/.bin/tsc --noEmit \
  --project /tmp/gaia-capacitas-independent-final-types.json
npm run lint -- --file tests/unit/campaign-capacitas-particelle-presentation.test.tsx \
  --file tests/unit/campaign-capacitas-terreni-residual.test.tsx
```

The temporary TypeScript project extends this frozen checkout's real frontend
configuration, disables incremental writes, explicitly includes both new specs,
loads actual Vitest/testing-library types, and removes the main project's test
exclusion. Imported runtime is type-checked too. No repository config changes.

## Full-file coverage and characterization

Fresh V8 execution, 40.63 seconds, matches Integration5's actual union:

| Metric | Covered / total | Coverage | Full-file100 gate |
|---|---:|---:|---|
| Statements | 857/857 | 100% | PASS |
| Branch arms | 903/929 | 97.20% | **FAIL** |
| Functions | 251/251 | 100% | PASS |
| Lines | 748/748 | 100% | PASS |

Unit PASS and coverage FAIL are different results. The coverage command exits1
because branches do not meet the unchanged100% threshold. No waiver, ignored
branch, configuration shrink, fabricated state or parser output is introduced.
All branch/function/statement maps match Integration5; uncovered arm identities
match exactly, independently of absolute coverage-report source paths.

Reviewed C10 public rendering matrices: absent/null current label, null/object/
array persisted result handling, valid terminal statuses and corresponding
counters/progress colors, mixed active/terminal ordering and controls. C11 uses
real public refresh/modal actions to retain an errors snapshot when its target
disappears, and a real CSV upload followed by worker toggles1→2→1 with exact
submitted payload assertions. API boundaries/protected-shell components are
mocked; component hooks, state and handlers are real. Tests do not execute
detached private closures or force a setter to invent an otherwise unreachable
branch. These are local UI characterization results, not backend/live permission
or external-portal equivalence proofs.

## Exhaustive residual branch ledger

26 uncovered arms, on25 source lines. Every arm has a source line and start
column. Coordinates below preserve V8's raw1-based lines/0-based columns;
`null` end columns are genuinely unspecified in five instrumentation locations,
not silently fabricated. The JSON artifact retains each exact raw arm and
containing-branch location/type.

`C`: conditional construction candidate; `L`: installed-library conditional
candidate; `U`: modal UNKNOWN_REACHABILITY. These are provenance classifications,
not coverage exemptions or authorization to remove defenses.

| Branch:arm | Source line | Raw arm start–end | Class |
|---|---:|---|---|
|16:1|258|258:25–258:27|C|
|19:1|281|281:58–281:null|C|
|23:1|291|291:41–291:43|L|
|24:1|293|293:46–293:48|L|
|27:1|313|313:34–313:null|L|
|28:1|314|314:74–314:84|C|
|29:1|315|315:74–315:84|C|
|30:1|316|316:82–316:96|C|
|32:1|317|317:89–317:100|C|
|34:1|318|318:77–318:84|C|
|41:1|378|378:58–378:null|C|
|45:1|388|388:41–388:43|L|
|46:1|390|390:46–390:48|L|
|49:1|403|403:34–403:null|L|
|51:1|404|404:96–404:109|C|
|53:1|405|405:86–405:96|C|
|285:1|2056|2056:82–2056:null|C|
|337:1|2482|2482:51–2482:54|C|
|338:1|2482|2482:103–2482:106|C|
|333:1|2483|2483:83–2483:91|C|
|334:1|2484|2484:46–2484:54|C|
|426:1|3166|3166:104–3166:108|U|
|434:1|3206|3206:94–3206:98|U|
|436:1|3214|3214:101–3214:105|U|
|437:1|3217|3217:124–3217:128|U|
|439:1|3220|3220:138–3220:142|U|

Cross-check against `CAPACITAS_DEFENSIVE_BRANCH_PROVENANCE_2026-10-08.md`:
15 construction plus6 installed-library candidates, total21;5 unresolved modal
arms. Source inspection confirms string `split().pop()` construction, aliases
selected from the same normalized keys used by the Map, exclusively string
`Object.keys` inputs, synchronously reread plain-JSON array length, and preview
items built exclusively by the genuine reader. These proofs are conditional on
the stated builtins/input/callsite contracts, not every imaginable substitution.

Installed SheetJS0.20.3 `xlsx.mjs` SHA256 independently matches
`1a0fb062ee9781b13f6687371b202aaefc53b6ce55b530c027e01f9c087b77db`.
The inspected `make_json_row`/`sheet_to_json` implementation constructs object
rows and appends densely via `out[outi++]=row.row`, then sets `out.length=outi`
with the actual reader options. Future upgrades may change this contract.
Modal updater false arms are not proven dead: async handlers can outlive UI
state, and ordinary busy/close tests do not prove null-updater race semantics.
All defenses remain unchanged. The assigned thirteen previously reachable
residual arms are covered in this fresh union, not merely inferred from a report.

## Complexity and protected provenance

Fresh complete report:

| Aggregate | R3 | This frozen source | Delta |
|---|---:|---:|---:|
| Files |1668|1668|0|
| Callables |20280|20280|0|
| Error findings |1938|1938|0|
| Warning findings |2749|2749|0|
| Total findings |4687|4687|0|

Entire `files`, `callables`, `violations` and `summary` objects match
`/tmp/gaia-r3-integrated-complexity.json` exactly, not just a rounded total.
Timestamps/source-commit provenance differ legitimately between scans.
Runtime Git diff against frozen R3 is empty. Capacitas principal remains
cognitive472/cyclomatic416/LOC2631/nesting2/params1; file remains cognitive1099/
cyclomatic1174/LOC3109/251callables/31useState/2useEffect. No debt reduction or
architecture decomposition is attributed to characterization.

Independent SHA256 checks:

- Capacitas runtime: `d52100728961e0188a41c6f3e1286abd860d2b364bdbf1e7af2d6945a3a99935`.
- Original19-case batch spec: `4e6a9e6f2e23f4340470c4d09867224f60a0a89f5ad3dfd821ec47e6eb5b8fe3`.

Protected diff against authoritative55a is empty: baseline/exceptions directory,
complexity tooling, Makefile, root/frontend dependency manifests/lockfile,
backend manifests/Ruff config, complexity CI gate/workflow, coverage-check
scripts, frontend Vitest/TypeScript/Next/Playwright/lint configs. No baseline
update/repair commands were executed; no thresholds, scope, exclusions or
ignores were changed. The JSON audit records the exact protected path list.

Ratchet JSON explicitly identifies main and baseline commit55a with no findings.
The global check retains exactly30 finding objects identical in order/content
to `/tmp/gaia-r3-independent-check.log`. All14 distinct affected paths remain
unchanged by the campaign:15 historical runtime metric regressions and15 worker
test divergences, as classified by the dedicated provenance report. They are
neither ignored nor absorbed, and do not become campaign failures by association.
This verifier independently rechecks object equality/path preservation; it does
not claim to rerun the Baseline Agent's full commit-by-commit historical analysis.

## Evidence integrity

- Full AST JSON SHA256: `acc17c1aeb0fc18ad85106d63b342d9efd7b7395e0f372db23d43b73ca7a72c6`.
- Fresh coverage JSON SHA256: `d8852412b8cf6db591f846cf69e6964c3bc7269847803fea007f8b17eb97c9eb`.
- Independent audit JSON SHA256: `8471fc1f361da49d85455fa04045566dd1b4d52f33f9ae0d6115912c617ce3ee`.

## Limitations, classification and decision boundary

**NO_CHANGE — CHARACTERIZATION_ONLY.** Independent local verification of
characterization is accepted; full-file runtime coverage remains **FAIL**.
This is not an acceptance of a new runtime refactor and not campaign completion.

Coordinator separately executes `npm run test:unit -- --maxWorkers=2` on frozen
frontend tree `1ddc7041881a24259e30dd81491aafba44fdb104`: exit0,4386 tests PASS/
297 specs,192.73 seconds, artifact
`/tmp/gaia-capacitas-characterization-final-unit.log`. No separate skipped-test
count is printed; all4386 counted tests pass. Coordinator's fresh `npm test`
exits0 with18 PASS/0 skipped, artifact
`/tmp/gaia-capacitas-characterization-final-smoke.log`. This verifier reads their
terminal summaries but does not claim to independently rerun those suites.
Backend/worker full suites,
clean build, E2E, live services and GIS experiments are NOT_RUN here. Existing
R3 execution evidence remains historical evidence for unchanged runtime, not
an independent rerun in this task or proof of new test integration. No runtime
dependency/boundary changes require Graphify refresh here; final platform-docs
refresh remains Coordinator-owned through the dedicated Make target.

Global mission remains **ACTIVE/INCOMPLETE**. GIS original failure causality is
UNKNOWN and its separate risk decision remains pending. A potential defensive
expression cleanup requires explicit new ownership/authorization and preserved
input/library invariants; provenance alone is not permission to remove guards.
The five modal races require genuine reachability analysis, not fabricated
updaters. Stop after delivering this report-only commit; no next runtime wave,
automatic integration, coverage exemption or baseline reconciliation is implied.
