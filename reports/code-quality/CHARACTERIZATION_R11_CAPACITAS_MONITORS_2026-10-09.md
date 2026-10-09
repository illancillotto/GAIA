# R11 Capacitas monitors — original rendered characterization

Global campaign remains **ACTIVE / INCOMPLETE**. Classification of this phase:
**NO_CHANGE — CHARACTERIZATION_ONLY**. No runtime implementation is claimed.

## Ownership and immutable inputs

Successor works only in `GAIA-campaign-20261009-r11-capacitas-monitors`, branch
`refactor/complexity-r11-capacitas-monitors`, HEAD
`d2f222f9b48a2e8b728ad2801a240f2d9bdd0ba5`, merge-base/main
`55a1b1d35911451e018b662c2acc450bf5994ea2`.
Coordinator approval `~/.cache/gaia-campaign/20261009-r11-capacitas/coordinator/CHARACTERIZATION_APPROVAL.md`
and integration registry `docs/code-quality/MULTI_AGENT_OWNERSHIP_R11_CAPACITAS_MONITORS_2026-10-09.md`
allocate only the new lifecycle spec and this report. Both terminal readiness
reports remain frozen; the pre-existing author readiness report remains untracked.
Checkpoint skill, repository AGENTS and project complexity constraints apply.

Only additions:

- `frontend/tests/unit/campaign-capacitas-monitor-lifecycle-r11.test.tsx`;
- this CHARACTERIZATION report.

All original eighteen campaign specs, runtime, R10 policy, dependencies,
test configuration, scanner and baseline remain byte-exact. No staging, commit,
push, source implementation or integration. Ignored node_modules symlink still
points to `/home/cbo/CursorProjects/GAIA/frontend/node_modules`; no install.
Installed versions: Node24.14.0, Vitest4.1.6, TypeScript5.8.3, React18.3.1,
Next15.5.25, SheetJS0.20.3.

## Rendered matrix and observations

Exactly **58 new cases**, all rendered on original source using actual
`usePolling`, authentic `ApiError`/`isAuthError`, fake clocks driving the real
hook, plain API JSON fixtures and deferred API boundary promises. No private
React state, hook replacement, parser getters, test-only runtime export,
coverage-only interface, skip/only, or inline code comments.
ProtectedPage and the unrelated workspace modal are replaced by existing-style
test boundaries; Terreni completion modal and public workspace controls are real.

| Cases | Observable protection |
| --- | --- |
| 8: four families ×401/403 | Actual API auth rejection on a real tick preserves rows, displays exact expiry/guidance, hides API detail, releases refresh loading, freezes timer/visibility requests, and permits manual token restoration. Manual success clears expiry error while guidance remains; next real interval resumes. |
| 2: Terreni reversed tracked response orders | Skip an unrelated terminal ahead of two tracked terminals; modal chooses the first tracked terminal in API order. Assert chosen modal ID, all rows/statuses, public close and absence of further polling. |
| 48: four families ×six outcome pairs ×two completion orders | Dispatch manual via public refresh, then a genuine15s/20s tick while manual loading remains active. Capture token-A/token-B and inCASS limit300; lose storage after dispatch. Assert intermediate loading/button, rows or their loading-time absence, errors/guidance, modal/history result, final list identity/status/order, stale replacement and next real polling eligibility after restoring storage. |

Six pairs, each in manual-first and silent-first order:

1. manual active success / silent terminal success;
2. manual ordinary Error / silent active success;
3. manual ApiError401 / silent active success;
4. manual active success / silent ordinary Error;
5. manual active success / silent ApiError403;
6. manual untyped `{status:401}` rejection / silent terminal success.

The status-only rejection is deliberately nonauth: family fallback renders,
without expiry guidance. Ordinary silent errors stay hidden. Ordinary manual
errors survive silent success. Late manual success replaces terminal rows with
active rows; no latest-response protection is invented. Auth then silent success
can resume polling while preserving the expiry message; silent auth then manual
success clears that error while preserving guidance; auth resolving last freezes
polling. Poll-to-poll single-flight does not prevent manual overlap.

History cases seed stored report7, then terminal responses place invalid first
result, valid report22 and later valid report33 in API order. Report22 is selected
and retained across late active snapshots and a later empty public refresh.
The plain JSON fixtures exercise genuine first-valid selection and stored/current
report precedence. Existing repeated runtime guard remains untouched.
Terreni silent terminal response opens its real modal while manual loading hides
rows; later active manual rows make the existing modal display the current job
as in corso. Manual active success and silent terminal success do not produce
the other families' manual completion notices.

Each family renders through its own `initialSection`. Tests assert exact interval
boundary before dispatch, all four initial API calls and no unrelated monitor
polling. Existing inCASS100/101job20s/45s checks, visibility/single-flight/unmount,
manual completion and command tests remain in the unchanged eighteen-spec union.
No duplicate new threshold suite or functional race fix was added.

## Original metrics and selected design provenance

Fresh read-only AST scan of both original runtime files reproduces author
readiness `files`, `callables`, `violations` and `summary` objects exactly.

| Metric | Actual original, unchanged | Frozen selected inline design, external only |
| --- | ---: | ---: |
| Principal cognitive / cyclomatic / LOC |455 /404 /2625 |391 /360 /2534 |
| Combined cognitive |1022 |902 |
| Combined decisions |872 |788 |
| Combined raw cyclomatic |1129 |1047 |
| Combined callable LOC |4789 |4651 |
| Combined file LOC |3140 |3138 |
| Combined callables |257 |259 |
| Error / warning findings |22 /19 |17 /16 |
| Workspace state / effect / reducer |31 /2 /0 |31 /2 /0 |

Actual workspace:3105LOC251callables1019cognitive1120cyclomatic869decisions;
R10policy35LOC6callables3cognitive9cyclomatic. Loader cognitive/cyclomatic/LOC:
Terreni21/15/47, Particelle21/15/42, History25/18/46, inCASS21/15/42;
all nesting2/params1. No metric changes in this characterization phase.

Selected source hash2a2199cc is unchanged, as are both readiness reports.
Candidate proof is previously accepted independent readiness evidence:
external full-context comparatorPASS0, all new helpers below thresholds,
independent3920trace replay and protected-other-source equality. It is **not**
an actual implementation/main ratchet or candidate rendered certification.
The shared private refresh requires `silent:boolean`; original wrappers retain
defaultfalse. No source helper or export was added here. Rejected adjacentFAIL4
and initial-inlineLOC regression remain documented in the frozen readiness.

## Gates and attempted failures

Standalone original rendered test passed58/58 before any implementation;
the final typed version also passed58/58. Original union passed396/19specs
with full-file100%. Coordinator subsequently requested removal of five newly
added comments; behavior was unchanged and the comment-free spec was frozen
for the final union/type/lint replay below.

Frozen comment-free replay: **PASS**,396tests/19specs, zero skips,51.50s.
The new spec contributes58passing cases; original eighteen contribute338.

| Actual complete file | Statements | Branches | Functions | Lines |
| --- | ---: | ---: | ---: | ---: |
| Workspace |857/857 |873/873 |251/251 |748/748 |
| R10 fraction policy |9/9 |6/6 |6/6 |8/8 |
| Union |866/866 |879/879 |257/257 |756/756 |

All four dimensions100%, no skipped coverage. Raw statementMap/fnMap/branchMap
objects exactly reproduce original readiness maps for both files; additional
hits do not alter the file scope. `frozen-coverage-audit.log` independently
checks raw maps, exact two-file scope and per-file dimension summaries.
Project TypeScript PASS (`project-typecheck.log`); explicit new-spec plus test
setup/project runtime TypeScript PASS zero diagnostics (`frozen-test-typecheck.log`);
both runtime files and all nineteen campaign specs ESLint PASS (`frozen-lint.log`).

Processes terminal exit0: frozen union session95191, frozen explicit test
TypeScript62407, frozen lint64138; earlier project TypeScript71266,
typed standalone58case original replay12805. No heavy process remains running;
the exclusive focused slot is **released for independent original replay**.
Logs/JUnit/full coverage live in `frozen-union.log`, `frozen-union-junit.xml`,
`frozen-union-coverage/coverage-final.json`; earlier isolated replay evidence
is `new-original.log`/`new-original-junit.xml` and `final-new.log`/`final-new-junit.xml`.

Earlier attempts are retained honestly in external evidence:

- `attempt1.log`:48PASS/10FAIL. Five inCASS initial-order expectations ignored
  its running-first presentation; two Terreni close queries matched both header
  and footer buttons; three Particelle terminal-card queries assumed active-card
  styling. Corrected only new spec selectors/expected initial presentation.
- `attempt2.log`:55PASS/3FAIL; remaining Particelle completed cards use20px
  rounding while active cards use24px. Corrected nearest rendered card selector.
- `test-typecheck.log`:one TS2322, fixture result parameter `unknown` too wide
  for the API union. Changed only annotation to `Job["result_json"]`;
  `test-typecheck-final.log` has zero diagnostics.
- Initial package metadata probe hit SheetJS's blocked package.json export;
  corrected read uses public `require("xlsx").version`, no dependency change.
- Dedicated `make graphify-frontend-query` fails because this fresh corpus has
  no graph. It is not PASS. Frozen readiness records successful dedicated
  integration query. No runtime structure or corpus source changed here;
  eventual implementation must refresh frontend Graphify through Make.

No unexplained application failure remains from these corrected test harness
assumptions. Original configuration/coverage thresholds were never weakened.
No broad frontend/build/browser/backend/worker certification or actual runtime
ratchet is claimed during this original-characterization-only phase.

## Reproduction and external evidence

Evidence directory:
`/home/cbo/.cache/gaia-campaign/20261009-r11-capacitas/characterization/`.
From assigned worktree, set `E` to a fresh external evidence directory, then:

```bash
mkdir -p "$E"
cd frontend
npm run test:unit -- tests/unit/campaign-capacitas-monitor-lifecycle-r11.test.tsx \
  --maxWorkers=1 --reporter=default --reporter=junit --outputFile.junit="$E/new-junit.xml"
VITEST_COVERAGE_INCLUDE=src/components/elaborazioni/capacitas-workspace.tsx,src/components/elaborazioni/capacitas-fraction-resolution.ts \
  npm run test:coverage -- tests/unit/campaign-capacitas- --maxWorkers=1 \
  --coverage.reportsDirectory="$E/coverage" --reporter=default --reporter=junit \
  --outputFile.junit="$E/union-junit.xml"
./node_modules/.bin/tsc --noEmit --incremental false
./node_modules/.bin/eslint src/components/elaborazioni/capacitas-workspace.tsx \
  src/components/elaborazioni/capacitas-fraction-resolution.ts tests/unit/campaign-capacitas-*.test.ts*
node <<'NODE'
const ts = require('typescript');
const config = ts.readConfigFile('tsconfig.json', ts.sys.readFile);
const parsed = ts.parseJsonConfigFileContent(config.config, ts.sys, process.cwd());
const roots = [...parsed.fileNames, 'tests/setup-vitest.ts', 'tests/unit/campaign-capacitas-monitor-lifecycle-r11.test.tsx'];
const program = ts.createProgram(roots, { ...parsed.options, incremental: false, noEmit: true });
const diagnostics = [...parsed.errors, ...ts.getPreEmitDiagnostics(program)];
console.log(ts.formatDiagnosticsWithColorAndContext(diagnostics, { getCurrentDirectory: ts.sys.getCurrentDirectory, getCanonicalFileName: x => x, getNewLine: () => '\n' }));
console.log(`Explicit new-spec TypeScript diagnostics: ${diagnostics.length}`);
process.exitCode = diagnostics.length ? 1 : 0;
NODE
cd ..
python3 tools/code_quality/complexity.py report \
  frontend/src/components/elaborazioni/capacitas-workspace.tsx \
  frontend/src/components/elaborazioni/capacitas-fraction-resolution.ts \
  --json "$E/original-metrics.json" --markdown "$E/original-metrics.md"
sha256sum -c /home/cbo/.cache/gaia-campaign/20261009-r11-capacitas/author/protected.sha256
sha256sum -c /home/cbo/.cache/gaia-campaign/20261009-r11-capacitas/author/original-specs.sha256
```

Project tsc excludes tests by original configuration; the explicit program above
adds the assigned spec and test setup, with project runtime/imports/options.
No claim that all other repository tests were explicitly TypeScript-checked.
Raw coverage must contain both complete runtime files, original statement/
function/branch maps, no zero hit counters and all four dimensions100%.
No logs are stored in the repository.

## Frozen SHA256 and handoff

| Artifact | SHA256 |
| --- | --- |
| Original workspace |a409e88725f0c251df7e93560c909b4464d487f382ce8ceb74787c23b2c60b59 |
| Original R10 policy |0d635381b311c18477aeef375713cf336114329350bd74791a4d6da447c574eb |
| Selected external candidate |2a2199ccd52b942fab54a1fff0878431b1ff6b7516bcaff2c03bd875b39e60f5 |
| Comment-free lifecycle spec |85206faf9efa7d50e81da478b4af61beee6940fd64377fd15ffbbe57178880b7 |
| Frozen author readiness |6dbd6564dfc5d6945507d54722528008bb087be2fb55cfaf46bd734524fde9de |
| Frozen independent readiness |c74e515e969421b5718d5efbe0673ce798625d7c89a54f247ac6575d58ee1441 |

This report's SHA256 is delivered separately to avoid self-reference.
Next authorized action is independent **original-source replay/review** of the
exact comment-free test and this report. Runtime implementation, commit and
candidate source custody remain stopped pending separate phase authorization.
Do not reinterpret this original100% result as final refactoring certification
or global complexity completion; actual principal remains455cognitive.
