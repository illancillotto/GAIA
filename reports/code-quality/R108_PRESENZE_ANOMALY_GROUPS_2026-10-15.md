# R108 — Presenze monthly anomaly groups

Status: exact runtime independently admitted after post-copy verification.
Full campaign ACTIVE / INCOMPLETE, not final campaign certification.

## Ownership and scope

Integration worktree `GAIA-campaign-20261008-integration`, HEAD `7f39510a`,
actual main/merge-base `a51a48dc`. Main checkout remains untouched. Author
`r104_author` changed only the granted page in the dedicated R108 worktree;
coordinator owns gates/integration/reporting, and independent recovery reviewer
owns separately assigned additive review directories. Author is terminal.

Only runtime file: `frontend/src/app/presenze/giornaliere/page.tsx`.
Original `daad670d`; candidate `c726f5c4`. Tests/configuration are unchanged.
Prior R107 evidence is immutable; its 269-member master `bb6ceda2` was rehashed
before R108 selection and again before integration. R42 remains REJECTED and
R43/R63 excluded; none of their candidates or tests was reused.

## Responsibility and invariants

Deduplicate monthly day/collaborator group rendering through one ordinary
synchronous renderer. Keep host section keys/reconciliation, direct day-heading
child array, exact mode-specific copy, count badges, group/card order and card
lookup semantics. `openAnomalyPanelRecord` retains two separate ordered setters:
clear the return collaborator, then select the record. No new React component,
wrapper-only relocation, generic abstraction, hook/state/API/identity/DB change.
See the dedicated Presenze domain contract for details.

## Measured reduction

| Scope | Cognitive | Cyclomatic | Effective LOC |
| --- | --- | --- | --- |
| PresenzeGiornalierePage |358→352|315→309|1942→1870|
| whole file |1042→1034|1188→1180|2800→2786|
| shared renderer |4|5|46|

Two physical duplicate decisions are removed (six source decisions become
four). Scanner callable ownership overlaps: the aggregate delta is not eight
independent domain improvements. All 308 callables, 11 errors and 19 warnings
remain; renderer has no violations. State/effect/reducer/import/dependency
counts do not change. Local classification: **IMPROVED**; P1 remains open.

## Candidate validation

- Supplemental finite source proof: 3,888 cases, 34,891 stable inputs; exact
  canonical AST remainder and element/key/children/action/error comparison.
  Not coverage, exhaustive browser proof, or adversarial-getter equivalence.
- Native: 496 PASS / seven specifications, no skipped/pending/todo/unhandled;
  terminal0 / 77.479s, 34,910 stable temporal inputs. Complete page 1,043
  statements / 1,100 branch arms / 306 functions / 855 lines, all 100%.
- Provider/native/test maps agree; seven safe distinct raw V8 page payloads
  retained. No independent raw-to-Istanbul replay is claimed.
- Actual configured strict TypeScript terminal0 / 23.189s; scoped ESLint
  terminal0 / 1.193s, three unchanged legacy warnings. Scoped metrics0.
- Author main ratchet-v2 terminal0 / 44.827s, empty findings, actual base
  `a51a48dc`; native audit-v2 terminal0 / 4.047s. Inputs stable throughout.
- First full-ratchet/auditor preparation refusals remain immutable. Additive
  actual v2 preparations independently accepted: 38,109 scanner/Git/control
  inputs, and 34,947 auditor inputs containing all 34,910 native consumed paths.
  Only exact accepted sanitized commands ran. Foreign Jest ended naturally;
  no external job was terminated or successful same-input native repeated.

## Integration boundary

Independent source/results ACCEPT_CANDIDATE `05bfb2cc`, seal `e4491e94`.
The first integration-plan review is CORRECTIONS_REQUIRED `c3d06cb5`, seal
`f7c072b2`: unfiltered source enumeration includes 677 generated Graphify files.
Additive v2 preparation excludes only that verified generated subtree while
retaining exact 671 real-source/asset equality. Corrected plan ACCEPT_PLAN
`cedb5427`, seal `9e6774c3`; actual preparation ACCEPT_PREP `d7405ee2`, seal
`0f3f73a6`. Exact apply_patch copy is `c726f5c4`, equal to author and snapshot.
One failed numbered-hunk patch envelope changed no source; correction and
actual metadata terminal0 are preserved in the external observation.

Actual integration preparation freezes 39,077 inputs, full 1,681 scanner scope,
513-package dependency closure, 198 generated Next types and 860 strict roots.
The original R107 global AFTER is reused as BEFORE only after exact current
35,255 runtime/tool input rebind; no identical-input report/native retry.
Four serialized gates each have 39,079 stable temporal inputs and exact
post-Git/config/dependency/inventory/type-metadata checks:

- Authoritative main ratchet terminal0 / 45.535s, findings empty.
- Fresh changed-input global AFTER report terminal0 / 44.372s.
- Actual configured strict integration TypeScript terminal0 / 24.011s.
- Scoped integration ESLint terminal0 / 1.204s, three inherited warnings.

Independent post-copy ACCEPT_INTEGRATED_RUNTIME `1ab1c656`, seal `eaebc5fe`,
verifies all 671 runtime/asset bytes and 2,646 author-local consumed paths match
integration. Native full-file100 is source/spec/config/dependency rebound, not
a newly executed integration native suite. All 20 earlier review seals remain
intact; 54 result/closure checks plus 30 native custody checks pass.

Global BEFORE/AFTER: 1,681 files / 20,361 callables / 1,918 errors / 2,739
warnings / 4,657 overlapping findings, unchanged. All 1,680 other file metric
records and 20,053 other callable records are exact; page metrics equal the
validated candidate. Overlapping callable sums cognitive80,546→80,538,
cyclomatic83,012→83,004 and LOC327,743→327,622 are not physical independent
decision or line counts. Scope, engines and HEAD stay fixed; no parse errors.

After-copy preservation: all 3,954 initial tracked/untracked members preserved
outside authorized page/PROGRESS, with three new R108 documents. R103–R107
all 963 sealed members reverified. Baseline,
thresholds, exclusions, coverage policy and unrelated dirt remain untouched.
No commit, push or merge. Dedicated frontend/Presenze-docs/platform-docs graph
receipts and final seal remain required before round closure; consult the
external terminal handoff/manifest, not this runtime acceptance alone.

## Residual work

Presenze principal352 still misses the original P1 target. Utenze391/Catasto390
remain coverage-blocked. This slice does not complete extreme-tail reduction,
backend/worker requirements, final broad suites or global campaign reporting.
Continue only one reviewable responsibility after R108 custody closure.

Evidence root:
`/media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-resume-20261012/r108-presenze-anomaly-groups/`.
Current facts: `coordinator-evidence/candidate-results.json`; reviews: `review/`.
Historical refusals and earlier failed/conditional evidence are not overwritten.
