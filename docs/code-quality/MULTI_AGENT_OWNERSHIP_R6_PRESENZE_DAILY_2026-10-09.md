# R6 Presenze daily UI — exclusive ownership

Integration starts at `afebd6154fa1f2c0f76693f39f2e4d5fea6ae271`; authoritative
merge-base/main is `55a1b1d35911451e018b662c2acc450bf5994ea2`.
Main's dirty concurrent work is not an input and must remain untouched.
The previous goal turn revalidated the already integrated GIS fix; it made
no source change. The global campaign is ACTIVE/INCOMPLETE.

| Agent | Domain | File/paths | Slice | Worktree | Branch | Status |
|---|---|---|---|---|---|---|
| Coordinator | Governance | This registry; docs/code-quality/PROGRESS.md; reports/code-quality/MULTI_AGENT_COMPLEXITY_CAMPAIGN_2026-10-08.md | Scope approval, exclusive ownership, integration gates | GAIA-campaign-20261008-integration | refactor/complexity-campaign-20261008 | MERGED |
| R6 author | Presenze frontend | frontend/src/app/presenze/giornaliere/page.tsx; frontend/src/app/presenze/giornaliere/daily-cell-model.ts; frontend/tests/unit/presenze-giornaliere-r6.test.tsx; reports/code-quality/SLICE_R6_PRESENZE_DAILY_2026-10-09.md; domain-docs/presenze/docs/DAILY_CELL_REFACTOR_2026-10-09.md | Ordered indicators and shared KM initial/disabled presentation; commands and lifecycle retained | GAIA-campaign-20261009-r6-presenze-daily | refactor/complexity-r6-presenze-daily | MERGED |
| R6 reviewer | Independent integration review | reports/code-quality/REVIEW_R6_PRESENZE_DAILY_2026-10-09.md only; all source read-only | Verify design, invariants, aggregate reduction and exact source before authorized integration | GAIA-campaign-20261009-r6-presenze-review | review/complexity-r6-presenze-daily | MERGED |
| R6 verifier | Independent final verification | reports/code-quality/VERIFICATION_R6_PRESENZE_DAILY_2026-10-09.md only; all source read-only | Frozen-source full-file coverage, focused/full frontend gates, ratchet | GAIA-campaign-20261009-r6-presenze-verification | verify/complexity-r6-presenze-daily | MERGED |

## Gates and stop condition

Prioritize the remaining extreme frontend queue rather than easier backend
work. Initial principal cognitive437/cyclomatic385/LOC2080 is provisional
until the current AST report confirms it. Choose one real responsibility with
actual aggregate simplification, not a moved mega JSX block. Stop once that
responsibility is simplified, all affected runtime reaches100% full-file
statement/branch coverage, pertinent tests pass, ratchet/main passes with0
findings and independent review approves. Do not start another responsibility.

No shared frontend lib/hooks/UI/config, backend identity mapping, API,
authorization, worker, tooling, thresholds, baseline, exclusions or ignores
may be modified. No main commit/merge, push or PR. Campaign branch commits
and exact reviewed cherry-picks only. Source/helper ownership belongs solely
to the author; reviewer/verifier may not edit them. Retain evidence under
`/home/cbo/.cache/gaia-campaign/20261009-r6-presenze/`.

Before modification inspect dirty paths and logs in relevant current worktrees;
concurrent source edits block this slice. Missing invariants, unsafe scope,
unexplained failures or inability to prove genuine reduction also block it.
Existing Capacitas coverageFAIL and global30 divergence remain separate.

## Preflight evidence

Both author/reviewer worktrees start clean at the integration snapshot, main
merge-base55a. Coordinator found no dirty owned frontend path in main,
campaign Presenze/R2/R3, the separate minuti-riconosciuti branch or complexity
ratchet worktree. Other branches contain older committed page changes, not
an observed active edit. Backend Presenze concurrent work remains out of scope.
Dedicated Presenze Graphify query lacks its backend graph; the frontend corpus
query succeeds and exposes the page/helper call relationships. Author owns
the initial coverage process; reviewer must not start a conflicting full suite.

## Coordinator design approval

Author independently reproduced baseline388PASS/page100% statements and
branches before edits. Current AST confirms page437/385/2080, file2858LOC,
aggregate1273cognitive/1350cyclomatic. Reviewer finds the ordered daily-record
indicator model conditionally safe. Coordinator authorizes this bounded
presentation model and the duplicated KM default/disabled projection only;
no component or whole-cell relocation. Keep classes/order, authorization
precedence over request icon, zero/null distinctions and uncontrolled inputs
unchanged. Matrix uses global canEdit; modal supplies rowCanEdit. Parent
retains all DOM/lifecycle/commands/API and helpers outside this responsibility.

Adjacent `daily-cell-model.ts` and the assigned R6 test are authorized. Add
characterization before runtime edits; reject if meaningful aggregate
cognitive/cyclomatic improvement cannot be measured without debt transfer.
This slice is not the original50% Presenze target or global goal completion;
the extreme principal remains open after any modest verified reduction.

## Frozen author source

Source `56c46570f48c3281ba2db2b3e8220338b29c8e88`, clean author worktree,
five exclusive files. Characterization15PASS on original; final413PASS with
page/model100% statements/branches. Principal437→420; affected aggregate
1273→1230cognitive/1350→1319cyclomatic, fileLOC+19/callableLOC+12 disclosed.
RatchetmainPASS0/typecheckPASS/smoke18PASS/lint0errors3unchangedwarnings.
Independent reviewer reproduced15 original tests and differentially checked
24192indicator/288KM inputs; all72 named helpers and75hook AST calls unchanged.
Final exact-source review/verification and full frontend gates still pending.
Author Graphify code6003nodes12568edges226communities; Presenze docs54nodes
56edges9communities, chunk1/2and2/2done, zero semantic failures.

Source reviewed APPROVED by independent report-only `c1475bb2`, integrated
as `cdfb8f96`; report integrated as `fb3e8b08`. Five source files exact.
MERGED means campaign-only, never main. Final verifier source `c03ee32f`
matches author, focused coverage process started08:21:36UTC/npmPID370800,
session46003; completion not inferred until terminal evidence. Full frontend
unit/build/browser gates belong only to verifier and are pending.

## Terminal closure — supersedes pending notes above

Independent verifier report-only source `3486b24e` approved and integrated,
never its duplicate source `c03ee32f`. Full frontend4417PASS/0skip, smoke18PASS,
typecheck/lintPASS3legacywarnings, freshbuildPASS, pertinentE2E7PASS and
fullE2E54PASS7existingSKIP0failure/flaky/retries. Both modified runtime files
100% statements/branches. Root finalreport objects match frozen source,
ratchetmainPASS0; globalcheckFAIL30Makeexit2 exact historical finding objects.
All agents/processes terminal, overlap0, owned stack stopped and credentials
removed. Ports18090/13010 free. No baseline/threshold/scope inflation.
This is one modest IMPROVED slice, not global completion or50% Presenze target.
