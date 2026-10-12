# R38 AUTHOR — Complexity Slice Report

## Ownership

CANDIDATE V2 AUTHOR GATES TERMINAL PASS; independent final/root admission pending. Dedicated `author-worktree`, branch
`refactor/complexity-r38-settings-hydration`, HEAD
`114fbf7196382c6446a7963c34bd89e4c9795ef5`, main/merge-base
`55a1b1d35911451e018b662c2acc450bf5994ea2`. Registry read before source
analysis. Coordinator granted exact candidate activation after independent V2
static admission. All four serial native stage tokens have been released.
Only runtime ownership is
`frontend/src/components/elaborazioni/settings-workspace.tsx`; only new test
ownership is `frontend/tests/unit/campaign-settings-hydration-r38.test.tsx`.
No existing test, sibling hook, configuration or shared-file ownership.

## Baseline

Fresh original runtime SHA256:
`ddb7113ba1586ffca6cb31de52f14dbba511d1f42fb9faec68dfb3ca98121a63`.
Preflight clean; latest owned-path commit `b0dd9228`.
R37-original metrics are orientation ONLY: workspace296cognitive/265cyclomatic/
1358LOC; file509cognitive/551cyclomatic/1702LOC/119callables/11state/2effects.
Fresh R38 native measurement matches these orientation values exactly.

## Target callable

`loadCredentials`20cognitive/12cyclomatic/42LOC and its functional updater
16cognitive/9cyclomatic/31LOC. Single responsibility: refresh loaded SISTER
form fields, selected credential first, default fallback only when blank.

## Behavioral invariants

- Token is obtained once at entry; no token performs no API request/state update.
- Successful GET updates credential status before queuing form refresh; error
  clearing follows updater scheduling. Error handling and messages unchanged.
- Functional updater reads current form at React evaluation time, not the form
  captured when the GET started. Projection must remain inside that updater.
- Non-null selected id searches credentials using strict equality and first-match
  semantics. Selected credentials win even when username is blank/default differs.
- Null id does not search credentials. Missing selected id may use default only
  if the current username trims to empty. Without default, trim is not evaluated.
- No refresh returns the same current object, preserving identity and all fields.
- Selected refresh preserves current id. Default refresh assigns default id.
- Both branches overwrite exactly seven fields: label, username, convention,
  request code, office, active, default. Only convention/request code use `?? ""`.
- Password, scheduling enabled, schedule object and any existing extra fields
  survive. Do not use `sisterCredentialFormFromCredential`, which resets password
  and schedule and would change behavior.
- JSX, event handlers, state/effect declarations, lifecycle and API contracts
  outside this refresh responsibility remain untouched.

## Characterization tests

| Behavior | Existing test | Missing | Added | Result |
| --- | --- | --- | --- | --- |
| Initial default projection | settings-sister integration | Explicit seven-field refresh check | NEW mounted default test | PASS original |
| Selected refresh wins over changed default | Responsive pool + nullable test | Deferred refresh with current selected id | NEW mounted selected-blank test | PASS original |
| Selected removed/nonempty draft unchanged | Non-selected delete coverage | Explicit no-overwrite refresh assertion | NEW mounted removed/nonempty test | PASS original |
| Selected removed/blank username default fallback | Existing updater branch coverage | Explicit removed-id/whitespace case | NEW mounted empty + whitespace cases | PASS original |
| Fallback assigns actual default id | Existing ordinary save id check | Real save after fallback | NEW fallback public update payload assertions | PASS original V2 |
| Removed selection without default | Existing branch coverage | Explicit blank/no-default check | NEW mounted no-default test | PASS original |
| New credential nonempty draft preserved | Create/update tests | Async initial GET race | NEW mounted initial-pending test | PASS original |
| Selection changes during GET | Existing socket races | Release GET/current selection race | NEW mounted deferred-selection test | PASS original |
| Password/schedule preserved across reload | Nullable + schedule tests | Deferred refresh of unsaved fields | NEW mounted selected-blank test | PASS original |
| Reverse completion/current password | Existing socket races | Two simultaneous GET completion order | NEW mounted reverse-completion test | PASS original |
| GET failure/token missing | Existing error tests | None identified | Existing tests immutable | PASS original |
| Failed reload followed by selected/default recovery | Initial-load error tests only | Preserved drafts/schedule + recovered projection/error clearing | NEW Error/raw recovery tests | PASS original V2 |
| Same-object return/no eager trim | Source-level invariant | Not observable through normal DOM | Independent exact-source/differential review4224cases/6mutants | PASS supplementary, not native coverage |

No private helper exports/invocations, hook mocks, counter fabrication or fake
coverage. Mount actual workspace with API/auth boundary mocks, trigger
refresh through the existing release button, resolve deferred requests and assert
actual editor fields/transitions. Existing spec remains immutable.

## Changes

Exact proposal `author-evidence/candidate-proposal.patch` applied through
`apply_patch` ONLY after independent reviewer V2 static admission and separate
Coordinator runtime grant. Installed source SHA256:
`ea946b881c5dd5b1cc613de91340d2645901bd8c7d93399532729b45e30a5a7d`.
NEW mounted V2 spec remains exact
`eb1f1b6e28aa3207e1504ff6fb91350f30a6da289f558c6bd33b190e2c812d52`.
Typed seven-field projection shared by selected/default branches;
pure refresh guard keeps fallback and no-change identity explicit. Actual duplicate
null-coalescing mapping decisions removed (four original to two physical).
Nested selected check becomes a flat guard. This is not JSX relocation or an
unchanged updater moved verbatim. Both helpers remain below thresholds with
zero violations; aggregate native reduction is measured below.

## Metric before / after / delta

| Metric | Before | After | Delta |
| --- | ---: | ---: | ---: |
| Workspace cognitive | 296 | 280 | -16 |
| Workspace cyclomatic | 265 | 257 | -8 |
| Workspace callable LOC | 1358 | 1328 | -30 |
| loadCredentials cognitive | 20 | 4 | -16 |
| loadCredentials cyclomatic | 12 | 4 | -8 |
| loadCredentials callable LOC | 42 | 12 | -30 |
| loadCredentials nesting | 2 | 1 | -1 |
| Form updater cognitive | 16 | 0 | -16 |
| Form updater cyclomatic | 9 | 1 | -8 |
| Form updater callable LOC | 31 | 1 | -30 |
| File cognitive sum | 509 | 468 | -41 |
| File cyclomatic sum | 551 | 535 | -16 |
| File callable LOC sum | 2416 | 2355 | -61 |
| File effective LOC | 1702 | 1702 | 0 |
| File callables | 119 | 121 | +2 |
| File imports/dependency_count | 15 | 16 | +1 |
| File useState | 11 | 11 | 0 |
| File useEffect | 2 | 2 | 0 |
| File maximum nesting | 2 | 2 | 0 |
| File maximum parameters | 3 | 3 | 0 |
| Callable findings in owned file | 13 | 10 | -3 |

New `loadedSisterCredentialFields`: cognitive2/cyclomatic3/LOC14/nesting0/params1.
New `refreshSisterCredentialForm`: cognitive5/cyclomatic5/LOC15/nesting1/params2.
Their combined cognitive7 is lower than the removed updater cognitive16;
physical nullish mapping decisions are deduplicated rather than transferred.
The native scanner counts nested callable complexity in enclosing functions;
the file sums are its reported aggregates, not independent problem counts.
The additional type-only import references an already imported sibling module:
one extra declaration, no new external dependency or runtime module relationship.
Unchanged file LOC and growth in callable/import counts are explicitly retained.

Global native report:1673files unchanged;20323→20325callables (+2),1922errors
unchanged,2739→2736warnings (-3),4661→4658findings (-3). All1672other file
records and every other runtime callable record match the original native report.
No aggregate delta credited to the campaign before independent final/root gates.

## Tests / coverage / ratchet

Original-only token was granted and released after unified session35253 terminated
with exit0. Actual original commands/logs/exits reside in author-evidence. Exactly
69 tests in the two existing settings specs PASS; zero skipped/pending/todo.
Raw full-file coverage:455/455statements,556/556branches,118/118functions,
402/402lines, all100. Complete native report1673files/20323callables/1922errors/
2739warnings/4661findings. Actual main55a ratchet exit0/findings[]. Independent
auditor confirms raw map keys/counter correspondence, all counters positive,
all3667tracked input hashes and HEAD/main/merge-base/status unchanged.
Original audit SHA256
`028f44d5ee1249119efc4741968daf124fc2404a145822881d27bf1ff2d1a659`.
No runtime/test/config edit or candidate application. No gate retried.

Distinct characterization-only session53987 TERMINAL exit0:78tests/3specs PASS
including9new mounted cases, zero skipped. Same full-file455statements/556branches/
118functions/402lines all100. Types0/lint0. Independent raw-map/counter audit0;
3668inputs (tracked plus new test) unchanged and originalfreeze35members rehashed0.
NEW test SHA256
`13d7bda46b449c286ab6f647fa6f46cf6ba158ac1bd51fcd6f8f32187f9da4d8`.
Original-only native69/report/ratchet were NOT rerun. No failure/retry.
Runtime remains exactddb7113b; candidate gates NOT RUN. Runtime source grant still
required after independent review. Original and characterization evidence distinct.

Independent reviewer initially HOLD: enabled button did not prove fallback id,
and initial-load error tests did not prove reload recovery. Coordinator authorized
NEW-spec-only V2. Public saves now assert update API idprimary after empty and
whitespace fallback. Two new Error/raw reload cases preserve unsaved label,
blank username, password, enabled schedule/hour and pool before selected/default
recovery; real UI projection/error clearing verified. Existing assertions retained.
Distinct session59052 TERMINAL0:80tests/3specs/11new, zero skipped, same full-file
455/556/118/402four100, types0/lint0/rawaudit0. All3668inputs unchanged, both
old freezes35+33members rehashed0. Exact V1 test preserved externally13d7bda4;
V2 new testeb1f1b6e28aa3207e1504ff6fb91350f30a6da289f558c6bd33b190e2c812d52.
No native gate retry or source edit. One report-only administrative apply_patch
failed on an incorrect lowercase context; it made no changes and was corrected
with verified exact context. Candidate still external/pending separate grant.
Proposed commands from author frontend:
`VITEST_COVERAGE_INCLUDE=src/components/elaborazioni/settings-workspace.tsx
./node_modules/.bin/vitest run tests/unit/elaborazioni-settings-sister.test.tsx
tests/unit/elaborazioni-settings-presenze-tab.test.tsx
tests/unit/campaign-settings-hydration-r38.test.tsx --coverage
--coverage.reportsDirectory=<author-evidence>/original-coverage`
and distinct candidate directory after authorized refactor. Native four-dimension
full-file100 required before and after. Raw map denominators/counters must agree.
Types: `./node_modules/.bin/tsc -p tsconfig.json --noEmit --incremental false`.
Lint: `./node_modules/.bin/eslint src/components/elaborazioni/settings-workspace.tsx
tests/unit/campaign-settings-hydration-r38.test.tsx`.
Root native report and `make complexity-ratchet BASE_REF=main` use fresh source
and immutable main55a. No baseline tooling update, exclusions or ignore permitted.
Graphify code/domain maintenance is Coordinator-owned after admission.

### Candidate V2 terminal receipt

Unified session50116 TERMINAL exit0; serial heavy token RELEASED. Distinct
`candidate-v2-*` commands/native logs/exits preserve all original and
characterization35/33/33frozen members. Candidate80tests/3specs PASS including
11new, zero failed/skipped/pending/todo. Raw full-file coverage456/456statements,
552/552branch arms,120/120functions,401/401lines, all100; denominator changes
follow real source edits, not config/ignore/exclusion changes. Maps and raw
counters correspond, every counter positive, exactly one full runtime included.
Types0/lint0/report0/actual main55a ratchet0/findings[]/raw custody audit0/
diff-check0. No native retry or failure. Protected3668inputs exact except the
authorized runtime source; installed candidate/spec hashes match grant and
all101old frozen members rehashed without changes. Baseline/tooling/configuration
and HEAD/main/merge-base remain exact.

Independent reviewer supplementary4224case/6mutant proof binds the same source
and proposal hashes, establishes no-op/new-object identity, extra/reference
preservation, strict-id/find-first and conditional malformed plain DTO behavior.
That proof is NOT native test coverage; getters/proxies and arbitrary exotic DTOs
are not universally certified. Native mounted tests protect React/API ordering,
functional current-state timing, deferred transitions and recovery.

## Classification

IMPROVED — author native metrics prove real bounded cognitive/cyclomatic reduction
without transfer of debt or new helper violations. Independent candidate/final/
root review and integration remain REQUIRED; this is not accepted campaign credit.

## Files changed / commit

Owned settings runtime, this report and NEW mounted characterization spec.
Existing tests/configuration unchanged; exterior proposal/old evidence preserved.
No commit, integration, main merge or push.

## Residual risks / recommended next slice

Original and exact candidate full-file100/native ratchet proven in this fresh
worktree; await independent final/root confirmation before integration. R37
positional-matcher issue remains separate, its runtime candidate not installed
or certified here. Settings parent280cognitive/file1702LOC remain legacy debt.
Graphify code/domain maintenance belongs to the Coordinator after admission.
Stop after this responsibility; no next slice started. Recommended next slice:
evaluate another independently characterizable Settings responsibility only
after this candidate is reviewed/admitted, not by expanding this change.
