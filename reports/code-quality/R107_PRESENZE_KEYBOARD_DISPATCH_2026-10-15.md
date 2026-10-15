# R107 — Presenze selected-day keyboard dispatch

Status: exact runtime independently admitted after post-copy verification.
Full campaign ACTIVE / INCOMPLETE; this is not final campaign certification.

## Ownership and scope

- Integration: `GAIA-campaign-20261008-integration`, HEAD `7f39510a`, actual
  main merge-base `a51a48dc`; main checkout untouched.
- Author r104_author owns one page in the dedicated R107 author worktree;
  coordinator owns serialized gates/integration/docs; independent reviewer
  campaign_requirements_recovery owns additive review directories. Original
  reviewer provider502 failures were not treated as application failures.
- Only runtime file: `frontend/src/app/presenze/giornaliere/page.tsx`.
  Original `deb4e9a0`, candidate `daad670d`; exact diff3added/5removed.
- R103–R106 sealed evidence remains immutable. R42 remains REJECTED and
  R43/R63 excluded; no candidate/test reuse from those rounds.

## Responsibility and invariants

Selected-day keyboard handling had an editable-target guard nested around a
second non-Escape comparison. Evaluate the same optional `closest` lookup once
into `editingTarget`, still before reading the key; keep Escape dispatch first,
then return for editable targets, then execute the unchanged arrow branches.

Preserve optional/null target behavior, lookup errors and order, Escape
preventDefault/close/return order, editable-target arrow protection, neighbor
guards, setter order, listener registration and hook dependencies. No helper,
wrapper, setter combination, new state, effect scheduling, DOM, API, identity,
authorization, persistence or test/config change. Native KeyboardEvent keys are
stable strings; no claim of equivalence for adversarial key-property getters.

## Current-input characterization and custody

Historical original evidence was insufficient for a complete current-tool
rebind. A fresh reviewed original run therefore preceded the runtime grant:
496 PASS/seven unchanged mounted specs, no skipped/todo/failed or unhandled
errors;1040statements/1106branches/306functions/853lines all100%.
Original82.17s/2719stable pins. Initial foreign-Jest refusal remains preserved;
the additive launcher waited for verified termination and fresh preflight.

Corrected PLAN and actual preparation independently accepted before candidate
gates. Actual preparation binds32220inputs/30311required, original before/after/
terminal/audit receipts, source proof, deterministic executables/child PATH and
configured types/lint closure513packages/29539files. Optional absences and
ancestor ESLint config presence, including target directories, are recorded;
generated Next types remain absent rather than being fabricated or copied.

Candidate native496PASS/seven specs,1040statements/1104branches/306functions/
852lines all100%,78.99s/32222stable gate inputs. No skipped maps or weakened
thresholds. Provider/native/tests coverage maps agree; seven actual raw V8
page-bearing payloads are preserved for each native run. No independent raw
V8-to-Istanbul replay is claimed. Exact whole-file diff and480 finite
action/exception traces PASS as supplemental source evidence, not UI coverage.

## Measured reduction

| Scope | Cognitive | Cyclomatic | Effective LOC | Nesting |
| --- | --- | --- | --- | --- |
| PresenzeGiornalierePage |360→358|316→315|1945→1942|unchanged|
| owning useEffect callback |11→9|9→8|27→24|2→1|
| onKeyDown |10→8|8→7|22→19|2→1|
| whole file |1048→1042|1191→1188|2803→2800|no regression|

One physical redundant decision is removed; the three scanner owners overlap.
The aggregate cognitive delta is not six independent domain improvements.
All other305callable metric records are unchanged;308callables,20imports,
21useState,13useEffect and30findings (11error/19warning) remain. No transfer to
another file/callable or new abstraction. Classification: **IMPROVED** locally.

## Validation and integration boundary

- Native, configured strict TypeScript, one-file ESLint, scoped metrics and
  author main ratchet all terminal0 with stable temporal pins and unchanged
  configured-input closure. TypeScript tests exclusions are preserved.
- ESLint has zero errors, two existing hook-dependency warnings and one
  existing unused-variable warning (`isLoadingRecordDetail`);
  dependencies were not altered to silence them. Ratchet findings are empty.
- Fresh full integration BEFORE report0/44.74s:1681files/20361callables,
  1918errors/2739warnings/4657findings. This is a current measurement, not a
  claim that the repository is free of existing debt.
- Before-copy preservation verifies all3952initial tracked/untracked members;
  only coordinator registry/PROGRESS changed, page still original. No baseline,
  thresholds, exclusions, coverage policy, commit, push or merge change.
- Independent final ACCEPT_CANDIDATE `9d3fb803`, followed by exact apply_patch
  integration and source equality to author/snapshot. Post-copy main ratchet
  terminal0/44.98s/findings[] and full AFTER report0/44.28s, stable inputs.
  Independent post-copy ACCEPT_INTEGRATED_RUNTIME `e4bc78c1` verifies all671
  frontend runtime files equal to the validated author worktree.
- Full AFTER summary remains1681files/20361callables/1918errors/2739warnings/
  4657findings. All1680other file metric records and20053other callable records
  are exact. Overlapping callable sums cognitive80552→80546,
  cyclomatic83015→83012,LOC327752→327743 are not physical LOC or independent
  problems. Scope and engines unchanged; no parse/exception errors.
- Preservation verifies all3952initial members, only authorized coordinator
  docs/page changes and two new R107 documents. R103220/R104167/R105156/R106151
  sealed members independently rehashed and preserved. A summary-parser
  failure on an echoed Make recipe was explained and preserved; only metadata
  parsing was corrected, no successful application gate repeated.
- Dedicated Graphify frontend/Presenze-docs/platform-docs receipts and terminal
  custody are authoritative in the external handoff/manifest. Do not infer
  semantic graph success from native or ratchet results alone.

## Residual scope

Presenze principal358 remains extreme and above the original P1 target.
Utenze391 and Catasto390 coverage prerequisites remain separate; this small
runtime reduction neither completes P1 nor the whole campaign. Continue one
reviewable responsibility at a time after this round is closed and sealed.

Evidence root:
`/media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-resume-20261012/r107-presenze-runtime/`.
Current handoff: `coordinator-evidence/HANDOFF_CURRENT.md`; detailed actual
results: `coordinator-evidence/candidate-results.json`; independent reviews:
`review/`. Prior failed/refused/conditional evidence is not overwritten.
