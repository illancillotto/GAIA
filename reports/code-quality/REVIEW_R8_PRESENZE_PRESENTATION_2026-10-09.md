# R8 Presenze record presentation — Independent Review

## Ownership

Reviewer branch `review/complexity-r8-presenze-presentation`, dedicated worktree
`GAIA-campaign-20261009-r8-presenze-review`, initially clean at
`6a005f1a95ca212e56bcc4648ca430f0936a75e1`. Main/authoritative merge-base
`55a1b1d35911451e018b662c2acc450bf5994ea2`. Sole reviewer deliverable is this
report. Runtime/test snapshot is explicitly Coordinator-authorized for independent
verification, never an additional implementation to integrate. Main concurrent
work is not input and remains untouched.

## Design Review

One coherent finite daily-record primary/secondary label and badge vocabulary.
Typed Map/Set policies remove repeated comparison chains; small domain-named
selectors preserve actual precedence. The Formula GAIA variant/text pair belongs
to this bounded vocabulary but remains distinct from the detail status badge.
No component, hook, file relocation, giant presentation context or JSX move.
Technical absence, header badges, classification, arithmetic, tooltip, permissions
and commands remain outside the exact whitelist.

Inherited cause keys such as `constructor`, `__proto__` and `toString` must remain
unknown; Map avoids accidental inherited-object lookup. Detail variant table is
safe because its classifier is unchanged and exhaustively returns known kinds.
Status fragments retain ordered perm/fer/anom/malatt/rich precedence; replacing
the short-string conditional with `slice(0, 4)` preserves UTF-16 semantics.

## Independent Original Characterization

Original page SHA256
`06d0bec08f2f521d888e61fd2fdc892047333289d242382ce8f3da39be3c05b5` frozen
before runtime edits. Reviewer independently executes the original six focused
suites: **424 PASS**, exit0, complete page1048/1048statements,
1189/1189branches,288/288functions,852/852lines,100% all metrics.

Original44 new rendered cases independently replayed twice: once against the
immutable original reviewer source, then against the frozen original page through
an external alias configuration after candidate snapshot. Both **44 PASS**,
exit0; exact DOM primary/secondary text and badge text/variant are observed.
No runtime export or new helper import is used to characterize original behavior.

Independent executable oracle extracts original helpers and Formula GAIA JSX
expressions from AST before the candidate exists. Frozen expectations cover
2800 deterministic records,13 kind inputs including unknown/prototype names,
and10 formula statuses. Null/undefined/zero/negative/NaN/infinite minutes,
ordinary `||` theoretical fallback, mixed substrings, request direction/status,
authorization trimming, punches, holiday suppression and unknown causes included.

## Candidate Source Review

**APPROVED**, strictly author source commit
`79bc9969d17111a098d37bc22e4e15f7172feb7d` and its four owned files.
All four author blobs independently checked against the reviewer snapshot;
exact-source verification is durable in `exact-source-blobs.json`.
Candidate gates **PASS** for exact page SHA256
`134a8b04c1dcd28ac8dd73b4e3a94bc24fe927f863256dfd4e28da8a3a1162f4`
and test SHA256
`e4de4be0a32a6260e4416315998df2a7efd74d22d4432f767debbc60ece64557`.
Coordinator `SOURCE_FREEZE_APPROVAL.txt` authorizes exact source application and
report-only commit. Duplicate reviewer source snapshot
`1f29b917ad1ae08c89c0801d309bb595bfa83aeb` is not an integration deliverable:
integrate the author source and reviewer report-only commit, never both sources.

Original-AST differential **84020 exact output comparisons PASS**, including
10 formula variant/text pairs. Input snapshots prove no record/array mutation.
NaN/zero formatting and nullish versus truthy distinctions stay exact; no
normalization, status expansion or permission change occurs.

Protected AST **PASS**:68 other top-level helpers;75 complete hook calls with
all bodies, arguments, order and dependencies;107 principal statements;
35 original import/type/constant statements. Principal AST is byte-structure
equivalent except the two exact Formula GAIA expressions, which are masked
individually. DOM, JSX wrappers/classes/attributes, state/effects, lifecycle,
commands, mappings and API behavior outside those expressions stay identical.
Only the three assigned helper implementations, five new small policy helpers,
their ordered lookup callback and eight finite constants are changed/added.

Independent candidate seven focused suites **468 PASS**, zero skipped/failed/
error cases, exit0 and JUnit inspected. Complete page1033/1033statements,
1143/1143branches,294/294functions,846/846lines,100% each; every raw coverage
counter is positive and no coverage skip or configuration change is added.

### Behavioral Matrix

| Behavior | Existing tests | Added | Independent check | Result |
|---|---|---|---|---|
| Primary cause/status precedence | original page suites |32 combined matrix cases|Frozen original replay + AST oracle|PASS|
| Holiday and ordinary/theoretical fallback | original page suites |R8 NaN/zero/punch cases|All13 kinds per adversarial fixture|PASS|
| Authorization/extra/travel/KM/request priority | page/R6 suites |R8 competing supplements|Exact primary/secondary outputs|PASS|
| Detail badge regolare/classifier precedence | page suites |5 rendered cases|Original replay +2800 fixtures|PASS|
| Formula vocabulary and unknown statuses | page suites |7 rendered cases|10 original JSX variant/text pairs|PASS|
| Lifecycle, permissions, commands, DOM | original424 cases |No changes permitted|75 complete hooks + protected principal AST|PASS|

### Metrics

| Metric | Before | After | Delta |
|---|---:|---:|---:|
| Principal cognitive |403|399|-4|
| Principal cyclomatic |356|352|-4|
| Principal callable LOC |2020|2020|0|
| Page aggregate cognitive |1172|1109|-63|
| Page aggregate cyclomatic |1249|1230|-19|
| Page aggregate callable LOC |4326|4319|-7|
| Page effective file LOC |2778|2788|+10|
| Page callable count |290|296|+6|
| Page findings |38|33|-5|
| Page useState |21|21|0|
| Page useEffect |13|13|0|
| Primary helper cognitive |53|11|-42|
| Secondary helper cognitive |40|8|-32|
| Detail variant helper cognitive |13|3|-10|

All additional helper/callback costs are included. New helpers have cognitive
max9, cyclomatic max8, LOC max7, params max3, nesting max1; zero findings.
Modified existing primary/secondary/detail selectors also have zero findings.
Global errors1937→1933, warnings2747→2746, findings4684→4679, same1671files;
20300callables compared with20294 before. Engines and configured scope unchanged.
The cognitive−63/cyclomatic−19 aggregate decrease is genuine policy deduplication,
not debt moved to another file. File LOC+10 is disclosed, not an improvement.

### Gates

- Independent before/after full `make complexity-report`:exit0; exact engine and
  scope equality; all added helpers/callbacks counted.
- `make complexity-ratchet BASE_REF=main`:**PASS0 findings**,exit0; authoritative
  merge-base55a, no alternate base selected.
- `npm run typecheck`:exit0. Owned ESLint page/newtest:exit0, no errors; three
  original page warnings independently reproduced, same text with16line offset.
- Baseline SHA256 remains
  `38e6b7943cb4f2b214baac51290fdfc97a88c8ee1bf80d3c639642de77cd4d95`.
  No baseline generation/repair, threshold/exclusion/ignore/configuration edit.
- Author forced dedicated frontend Graphify:exit0,6027nodes12615edges225communities;
  dedicated Presenze docs:exit0,chunk1/2and2/2done,55nodes58edges9communities,
  no semantic chunk failure. Reviewer does not modify graph artifacts.
- Full frontend/build/browser certification belongs to the final verifier; this
  reviewer does not claim those fresh candidate suites were executed here.

### Technical Attempts

Author initial smoke-runner command mistake and original badge selector whitespace
failure remain documented in author evidence. Corrected selector asserts actual
header badge exact textContent/variant, not a runtime workaround or weaker test.
Reviewer external audit script initially had an extra closing parenthesis;
corrected only the external audit, then coverage/metrics/gate auditexit0.
One oversized snapshot patch transport failed before editing; a bounded exact
diff patch succeeds, candidate/source hashes independently checked afterwards.
These harness errors do not alter application code, tests, thresholds or policy.

## Classification

**IMPROVED**, strictly this bounded policy slice and reviewed author source SHA.
Real aggregate cognitive−5.38%/cyclomatic−1.52%; four callable error findings and
one warning removed without transfer. Principal399 remains extreme; neither
below300 nor original50%/under250 target is achieved. Global campaign remains
ACTIVE/INCOMPLETE. Historical30 global baseline divergences and Capacitas coverage
FAIL remain separate and unmodified.

## Files Changed

Author owns page, `frontend/tests/unit/presenze-giornaliere-r8.test.tsx`,
`domain-docs/presenze/docs/RECORD_PRESENTATION_REFACTOR_2026-10-09.md`,
and `reports/code-quality/SLICE_R8_PRESENZE_PRESENTATION_2026-10-09.md`.
Reviewer deliverable: this report only. Never integrate a second source copy.

## Commit

Author frozen source `79bc9969d17111a098d37bc22e4e15f7172feb7d`, all four blobs
verified exactly, author clean. Reviewer source-only duplicate `1f29b917` must
not be integrated. This report is a separate Coordinator-authorized report-only
commit, identifiable using `git log -1 --format=%H --` followed by this report
path. No main changes, merge, push or PR.

## Evidence

Durable root `/home/cbo/.cache/gaia-campaign/20261009-r8-presenze/reviewer/`:
original-page, original-oracle, original-invariants; oracle/differential/protected
AST scripts and JSON; before/after complete AST reports; baseline/after coverage
JSON and JUnit; both original44 replay logs/JUnit/exits; typecheck/lint/ratchet
logs/exits; `audit.json` with raw coverage and exact aggregate counts. Design,
test-matrix and gate notes preserve decision provenance; no reliance on `/tmp`.

## Residual Risks And Next Slice

Monolithic principal remains399 and all21useState/13useEffect remain. Finite
selectors are now locally understandable but do not solve orchestration debt.
No automatic extension of this ownership: after source freeze, independent final
verification and integration, Coordinator should assign a distinct coherent
principal responsibility with new characterization, ownership and gates.
