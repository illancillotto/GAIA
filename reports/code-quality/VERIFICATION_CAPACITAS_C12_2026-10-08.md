# Capacitas C12 — Independent Final Verification

## Ownership and frozen source

Final C12 verifier, authorized by ownership registry `198949c4`. Exclusive
ownership is this report; no runtime, test, shared document, baseline,
configuration or tooling edits. Report-only source commit is authorized;
integration remains Coordinator-owned.

- Worktree: `/home/cbo/CursorProjects/GAIA-campaign-20261008-c12-verification`.
- Branch: `refactor/complexity-c12-verification`.
- Clean verification HEAD: `198949c429c9a06bfd7e252c709a220cf495b2b9`.
- Accepted C12 source: `acdc95151894d31df7e7cf4c6bd8d593e3dd3b99`.
- Frozen frontend tree: `14de55bb9d5eb2bc34d97d7411281969b6fda44e`.
- Main merge-base: `55a1b1d35911451e018b662c2acc450bf5994ea2`.

Checked preflight status, HEAD, merge-base and exact frontend tree. Source to
verification HEAD differs only in Integration6's report and the ownership
registry, not application/test content. Dirty main work was not copied or
modified. Checkpoint skill, project rules and complexity references remain
active. Integration6, C12 source and prior provenance are reviewed read-only.

## Independently executed gates

These commands ran in this verifier worktree. Prefix for fresh artifacts is
`/tmp/gaia-c12-independent` unless another path is explicitly identified.

| Gate | Actual result | Artifact suffix |
|---|---|---|
| Full AST report | PASS exit0 | `-final.json`, `-final.md`, `-final-report.log` |
| Main change ratchet | PASS exit0, zero findings | `-final-ratchet.log` |
| Global recorded-baseline comparison | FAIL Make exit2/scanner exit1; exactly30 historical findings | `-final-check.log` |
| Actual sixteen-spec workspace union | 312 tests PASS, zero skip; full-file coverage FAIL exit1 | `-final-coverage.log`, `-final-coverage/coverage-final.json` |
| Explicit C12 test TypeScript | PASS exit0 | `-types.log`, `-test-tsconfig.json` |
| C12 ESLint | PASS exit0, no ESLint warnings/errors | `-lint.log` |
| Saved native browser precise-V8 evidence audit | PASS exit0; six witnesses, nine null updater executions | `-modal-audit.log` |
| Independent AST/hash/protected/finding/residual audit | PASS exit0 | `-audit.cjs`, `-audit.log`, `-evidence.json`, `-residual-ledger.md` |
| Whitespace / clean pre-report tree | PASS | `git diff --check`, `git status --short` |

Reproduction:

```sh
make complexity-report REPORT_JSON=/tmp/gaia-c12-independent-final.json \
  REPORT_MD=/tmp/gaia-c12-independent-final.md
make complexity-ratchet BASE_REF=main
make complexity-check
cd frontend
VITEST_COVERAGE_INCLUDE=src/components/elaborazioni/capacitas-workspace.tsx \
  npm run test:coverage -- 'tests/unit/campaign-capacitas-' --maxWorkers=1 \
  --coverage.reportsDirectory=/tmp/gaia-c12-independent-final-coverage
node_modules/.bin/tsc -p /tmp/gaia-c12-independent-test-tsconfig.json --noEmit
npx next lint --file tests/unit/campaign-capacitas-modal-race.test.tsx
cd ..
node /tmp/gaia-modal-probe/coverage-audit.mjs
node /tmp/gaia-c12-independent-audit.cjs
```

Temporary TypeScript config extends this checkout's actual frontend config,
explicitly includes the C12 spec and actual Vitest/jest-dom types, clears the
inherited test exclusion and disables incremental output. Shared configs are
unchanged. Next lint prints its existing command-deprecation notice only.

## Characterization review and behavioral matrix

The actual workspace, public DOM handlers, React state/effects and polling hook
execute. Deferred API Promise, coherent typed anomaly rows/resolution results,
auth and unrelated shell/modal boundaries are mocked. No fake setter, detached
private callback, impossible parser fixture or state substitution is present.
Existing specs and runtime are unchanged.

| Behavior | C12 test and independently observed result |
|---|---|
| Original request pending | Uras/FRA-A exact token/UUID/payload, one API call; original close and synchronization controls disabled |
| Public background replacement | Enabled Terralba action focused and dispatched; fresh Terralba/FRA-C modal appears, close enabled; no second request |
| Close then late successful response | Modal stays null, only original Uras row removed; fresh Terralba reopen has no stale success |
| Close then late unsuccessful result | Modal stays null, both rows retained; reopened replacement has no stale error |
| Close then late rejection | Modal stays null, both rows retained; reopened replacement has no stale rejection |
| Replacement remains open during old response | Three cases preserve the current race: original response updates replacement presentation while retaining Terralba identity/selection; only success removes Uras |

Six new cases are included in the actual312-test union. They preserve existing
behavior, including the mismatched request/current-modal presentation; they do
not fix that race or characterize production permissions/external portals.

### Native witness and jsdom boundary

Reviewed the seven `setResolveModal` writer sites and the separate native
Tab/Enter witness in `CAPACITAS_MODAL_REACHABILITY_2026-10-08.md`. Independently
reran its audit against saved raw Chromium precise-V8 function/range evidence:
six browser cases, ordinary/StrictMode × success/unsuccessful/rejection, prove
nine null updater executions at3214/3217/3220. Positive updater execution and
zero object-arm count in the exact `prev ? { ... } : null` functions are required.
The browser experiment itself is not rerun by this verifier.

C12 uses `.focus()` plus `fireEvent.click` on the live enabled public control.
That establishes the React/API transition under jsdom, not native Tab ordering,
Enter default activation, pointer hit-testing or production CSS/focus trapping.
Reachability relies on the separate genuine keyboard witness, not a forced
pointer click through an overlay. Browser probe counts are not added to Vitest
coverage. These three async guards are necessary and remain unchanged.

## Actual full-file coverage and exhaustive residual ledger

Fresh union finishes in44.10s. All four full-file thresholds remain100%; one
runtime include has its complete unchanged denominator. Unit PASS does not
turn coverage FAIL into runtime-refactoring authorization.

| Metric | Integration6 measured before | Independent final | Delta covered | Final gate |
|---|---:|---:|---:|---|
| Statements |857/857|857/857|0|PASS100%|
| Branch arms |903/929|906/929|+3|**FAIL97.52%**|
| Functions |251/251|251/251|0|PASS100%|
| Lines |748/748|748/748|0|PASS100%|

The before artifact is Integration6's independently executed fifteen-spec union,
not a before run by this final verifier. Exact statement/function/branch maps
match. Exact newly covered arms are3214 `436:1`,3217 `437:1`,3220 `439:1`;
zero previously covered arms are lost. Fresh final covered/uncovered identities
match Integration6 exactly, regardless of absolute source-path differences.

Remaining23 arms across22 source lines are exhaustively located below. Raw
coordinates retain V8's1-based lines and0-based columns. `null` end columns are
unspecified instrumentation metadata, not fabricated endpoints. `C` means
conditional JS-construction candidate; `L` installed-library conditional
candidate; `U` unresolved modal reachability. None is a coverage exemption.

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

No uncovered statements/functions/lines or unlocated arms remain. The21
conditional candidates comprise15 JS-construction cases and6 SheetJS cases.
Read-only source review confirms only string Object.keys inputs to the private
normalizer, nonempty split-result arrays, alias Set/Map built from identical
keys, synchronous plain-JSON length access and reader-only preview construction.
Installed SheetJS0.20.3 `make_json_row` and `sheet_to_json`, under actual options,
construct object rows and append densely with `out[outi++]=row.row` before
`out.length=outi`. These arguments remain conditional on builtins/callsites/
installed version, not arbitrary substitutions or future upgrades.
Modal3166/3206 remain **UNKNOWN**, not proven dead. No guard removal or coverage
waiver is authorized by this report; full-file100% remains FAIL.

## Complexity, protected provenance and historical global findings

Entire `files`, `callables`, `violations`, `summary`, `scope`, `engines`, parse
errors and exception errors match `/tmp/gaia-r3-integrated-complexity.json`
exactly. Legitimate scan timestamps/source provenance differ.

| Aggregate | Frozen R3 | Final C12 source | Delta |
|---|---:|---:|---:|
| Files |1668|1668|0|
| Callables |20280|20280|0|
| Error findings |1938|1938|0|
| Warning findings |2749|2749|0|
| Total findings |4687|4687|0|

Runtime Git diff against R3 `0b1a0d3767e4e75b4cf34cfe0daf737609e6ccb0` is empty.
Capacitas principal remains cognitive472/cyclomatic416/LOC2631/nesting2/params1;
file remains LOC3109/cognitive1099/cyclomatic1174/251callables/31useState/2useEffect.
Characterization does not decrease complexity, relocate debt or decompose the
architecture and is not classified IMPROVED.

Independent preserved SHA256:

- Runtime: `d52100728961e0188a41c6f3e1286abd860d2b364bdbf1e7af2d6945a3a99935`.
- Original19-case batch spec: `4e6a9e6f2e23f4340470c4d09867224f60a0a89f5ad3dfd821ec47e6eb5b8fe3`.
- Baseline: `38e6b7943cb4f2b214baac51290fdfc97a88c8ee1bf80d3c639642de77cd4d95`.
- Installed SheetJS source: `1a0fb062ee9781b13f6687371b202aaefc53b6ce55b530c027e01f9c087b77db`.

Protected55a diff is empty for baseline/exceptions, complexity tooling, Makefile,
dependency manifests/lockfile, Ruff/backend manifest, complexity CI gate/workflow,
changed-coverage scripts and frontend Vitest/TypeScript/Next/Playwright/lint
configs. The audit JSON records the exact path list. No threshold, exclusion,
ignore, baseline synchronization/repair or shared-config modification occurred.

Ratchet JSON explicitly identifies main/baseline55a with zero findings. Global
check keeps exactly30 finding objects identical in order/content to
`/tmp/gaia-r3-independent-check.log`; all14 distinct affected paths remain unchanged
by the campaign. Dedicated provenance classifies15 historical runtime metric
regressions plus15 worker-test divergences. They are neither absorbed nor
ignored. This verifier independently checks equality/path preservation, not
the Baseline Agent's entire commit-by-commit historical reconstruction.

## Evidence integrity and diagnostic correction

- Full AST JSON SHA256: `4942e9029808804bf66569f7fd1b07729e78dd8320add20b1d30da798a3217f9`.
- Fresh coverage JSON SHA256: `ae9cef59bd57962f38afcc11a3a31d5fe97702dc94530b14aeabdacbba4a43c5`.
- Independent evidence JSON SHA256: `68d1c156fcb3e3d3f73496713092798b231e339ee422e6af38d6a48df9fbc09c`.

Initial disposable audit failed its principal lookup because the report schema
uses `name`, not `qualified_name`. Corrected only that verifier selector after
inspecting actual schema; all original equality/hash/coverage assertions remain.
Failure retained in `/tmp/gaia-c12-independent-audit-initial-schema.log`. Final
audit exits0. This was a diagnosed temporary verifier error, not an application
test failure or weakening of a gate. Coverage FAIL and global-check FAIL are
separately retained as actual results.

## Coordinator-run suites, limitations and disposition

Coordinator confirmed terminal full frontend execution on the same frozen
tree: `npm run test:unit -- --maxWorkers=2`,4392 tests PASS/298 specs,exit0,
187.69s, `/tmp/gaia-capacitas-c12-final-unit.log`. No distinct skipped-test count
is printed; all4392 counted tests pass. Coordinator's fresh `npm test`:18 PASS,
0 skipped,exit0, `/tmp/gaia-capacitas-c12-final-smoke.log`. This verifier reads
both terminal summaries and does **not** claim independent execution of those
two commands. Native browser probe, backend/worker suites, builds and E2E are
NOT_RUN here; existing frozen-runtime R3 suite evidence remains historical,
not newly executed verification of this test-only task.

The separately accepted GIS application diagnosis `46c6f872` demonstrates the
native camera-interruption mechanism in both clean55a and integrated snapshots.
Original R3 failure attribution remains UNKNOWN, and residual-risk acceptance
is still pending; this report does not accept that risk or reopen a runtime wave.
There are no runtime dependency/component-boundary changes in C12. Dedicated
Graphify documentation refresh and global checkpoint remain Coordinator-owned.

**NO_CHANGE — CHARACTERIZATION_ONLY. READY_FOR_REVIEW for this report-only
verification; full-file runtime coverage FAIL.** No runtime-refactor clearance,
coverage exemption, global campaign completion or self-integration is implied.
Global mission remains **ACTIVE/INCOMPLETE**. A future defense cleanup requires
explicit independent authorization/ownership, demonstrated preserved invariants
and the unchanged full-file/ratchet gates; necessary async guards and unresolved
synchronous modal guards are not disposable complexity/coverage debt.
