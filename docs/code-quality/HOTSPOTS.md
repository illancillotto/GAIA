# Hotspot backlog

Questo elenco non e una coda automatica di refactoring. Il quality ratchet opera
prima sul codice realmente toccato dagli sviluppi; un hotspot di questa lista si
apre solo quando ostacola feature, test o manutenzione e dopo una decisione
esplicita. Una iterazione neutra non autorizza il candidato successivo.

Questo elenco e un seed derivato da una ricognizione del repository. Non e la
baseline autorevole. Hermes deve sostituire dimensioni e priorita con i risultati
del motore AST e con la frequenza di modifica Git.

Snapshot di preparazione: `main` a
`2ded321cd99aeb59c02865e5e7f2bc158804e4b9`, 2026-08-19.

## FIRST_REFACTOR_HOTSPOT

- Stato: `IMPROVED_WITH_RESIDUAL_DEBT` and closed after `P3-I6-CATASTO-GIS-ARCHIVE-LIST-2026-08-19`.
- Path: `frontend/src/app/catasto/gis/page.tsx`
- Qualified symbol: `CatastoGisPage`
- Module/domain: `catasto / GIS frontend`
- Priority: `64`
- Before P3-I1: cognitive `591`, cyclomatic `538`, LOC `3007`, nesting `4`, density `0.748144`, churn 90d `26`.
- After P3-I1: cognitive `569`, cyclomatic `516`, LOC `2974`, nesting `4`, density `0.718267`.
- After P3-I2: cognitive `540`, cyclomatic `487`, LOC `2865`, nesting `4`, density `0.703518`.
- After P3-I3: cognitive `503`, cyclomatic `450`, LOC `2761`, nesting `4`, density `0.673807`.
- After P3-I4: cognitive `481`, cyclomatic `428`, LOC `2667`, nesting `4`, density `0.662740`.
- After P3-I5: cognitive `466`, cyclomatic `413`, LOC `2615`, nesting `4`, density `0.650309`.
- After P3-I6: cognitive `453`, cyclomatic `400`, LOC `2525`, nesting `4`, density `0.638938`.
- Delta P3-I2: cognitive `-29`, cyclomatic `-29`, LOC `-109`, density `-0.014749`; global violations `4138 -> 4135`, errors `2028 -> 2025`, warnings unchanged `2110`.
- Delta P3-I3: cognitive `-37`, cyclomatic `-37`, LOC `-104`, density `-0.029711`; global violations `4135 -> 4132`, errors `2025 -> 2022`, warnings unchanged `2110`.
- Delta P3-I4: cognitive `-22`, cyclomatic `-22`, LOC `-94`, density `-0.011067`; global violations `4132 -> 4129`, errors `2022 -> 2020`, warnings `2110 -> 2109`.
- Delta P3-I5: cognitive `-15`, cyclomatic `-15`, LOC `-52`, density `-0.012431`; global violations `4129 -> 4126`, errors `2020 -> 2019`, warnings `2109 -> 2107`.
- Delta P3-I6: cognitive `-13`, cyclomatic `-13`, LOC `-90`, density `-0.011371`; global violations `4126 -> 4122`, errors `2019 -> 2016`, warnings `2107 -> 2106`.
- Slices completed: P3-I1 XLSX import mapping / draft overlay construction; P3-I2 WhiteCompany reports panel extracted to `frontend/src/components/catasto/gis/WhiteCompanyReportsPanel.tsx` with 100% targeted coverage and 0 violations; P3-I3 Distretti panel extracted to `frontend/src/components/catasto/gis/DistrettiPanel.tsx` with 100% targeted coverage and 0 violations; P3-I4 AdE alignment status panel extracted to `frontend/src/components/catasto/gis/AdeAlignmentPanel.tsx` with 100% targeted coverage and 0 violations; P3-I5 delivery point quick filters extracted to `frontend/src/components/catasto/gis/DeliveryPointQuickFilters.tsx` with 100% targeted coverage and 0 violations; P3-I6 archive list extracted to `frontend/src/components/catasto/gis/ArchiveList.tsx` with 100% targeted coverage and 0 violations.
- Checkpoint: `CHECKPOINT 3 — HOTSPOT ITERATION P3-I6 PASS`; Gate backend changes classified as `USER_WORK_UNRELATED` / `PREEXISTING_UNRELATED` by provenance audit and excluded from Catasto/GIS review boundary.
- Residual risk/debt: current hotspot closed with residual legacy debt because remaining significant slices are increasingly GIS/API/popup coupled with lower marginal return. Next step is second-hotspot review, not automatic refactoring.



## SECOND_REFACTOR_HOTSPOT

- Stato: `IMPROVED` after `H2-I1-PRESENZE-GIORNALIERE-CELL-DISPLAY-2026-08-20`.
- Path: `frontend/src/app/presenze/giornaliere/page.tsx`.
- Qualified symbol: `PresenzeGiornalierePage`.
- Module/domain: `presenze / giornaliere frontend`.
- Baseline reconciliation prerequisite: `da12c46a06692847de80eb9af6a7bee117f922ee`.
- Before H2-I1: callable cognitive `577`, cyclomatic `482`, LOC `2314`, nesting `3`; file LOC `3045`, cognitive_sum `1612`, cyclomatic_sum `1602`, density `1.055501`.
- After H2-I1: callable cognitive `577`, cyclomatic `482`, LOC `2314`, nesting `3`; file LOC `2902`, cognitive_sum `1448`, cyclomatic_sum `1483`, density `1.009993`.
- Delta H2-I1: callable cognitive/cyclomatic/LOC unchanged; file aggregate cognitive_sum `-164`, cyclomatic_sum `-119`, LOC `-143`, callables `-14`, density `-0.045508`; global violations/errors/warnings unchanged.
- Slice completed: daily matrix cell display/classification helpers extracted to `frontend/src/lib/presenze-giornaliere-cell-display.ts` with `100%` targeted coverage.
- Residual debt: extracted helper file still carries the legacy display-branch violations (`dailyMatrixCellPrimaryLabel`, `dailyMatrixCellSecondaryLabel`, `classifyDailyMatrixCell`); this is visible in the baseline and should be handled by a dedicated follow-up if selected.
- H2-I2 preview: prefer `recordInsights:useMemo[0]<callback>` as the next review candidate; alternatives are collaborator row rendering and day modal/editor rendering, both with higher UI/state risk.
- H2-I2: `NOT_STARTED`.
- Phase 4 full: `NOT_STARTED`.

## Prioritized candidates

| Priority | Stato | Path | Symbol | Domain | Cog | Cyc | LOC | Nest | Density | Churn90 | Risk/Testability note |
| ---: | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 64 | closed | `frontend/src/app/catasto/gis/page.tsx` | `CatastoGisPage` | catasto/GIS | 453 | 400 | 2525 | 4 | 0.639 | 26 | P3-I6 passed; improved with residual GIS/API-coupled debt; close current hotspot |
| 64 | reduced | `frontend/src/app/presenze/giornaliere/page.tsx` | `PresenzeGiornalierePage` | presenze | 577 | 482 | 2314 | 3 | 1.010 | 18 | H2-I1 extracted daily matrix cell display helpers; file aggregate cognitive_sum `1612 -> 1448`, cyclomatic_sum `1602 -> 1483`, LOC `3045 -> 2902`; component callable unchanged; H2-I2 review required |
| 63 | candidate | `backend/app/modules/catasto/routes/anagrafica.py` | `execute_bulk_search_payload` | catasto | 363 | 68 | 320 | 10 | 1.347 | 5 | Backend route; preserve query/export contracts |
| 60 | candidate | `frontend/src/features/organigramma/organigramma-workspace.tsx` | `OrganigrammaWorkspace` | organigramma | 484 | 369 | 1807 | 3 | 0.472 | 12 | Complex workspace state |
| 58 | candidate | `frontend/src/components/elaborazioni/capacitas-workspace.tsx` | `ElaborazioniCapacitasWorkspace` | elaborazioni | 473 | 417 | 2635 | 2 | 0.338 | 7 | Integration-heavy UI |
| 56 | candidate | `frontend/src/app/utenze/[id]/page.tsx` | `DetailContent` | utenze | 393 | 306 | 1909 | 2 | 0.366 | 14 | User detail UI; auth/permission sensitive |
| 56 | candidate | `frontend/src/app/presenze/collaboratori/[id]/page.tsx` | `PresenzeCollaboratoreDetailPage` | presenze | 233 | 212 | 1600 | 2 | 0.278 | 7 | Payroll/timekeeping domain risk |
| 54 | candidate | `frontend/src/app/elaborazioni/page.tsx` | `ElaborazioniPage` | elaborazioni | 355 | 294 | 1560 | 2 | 0.416 | 10 | Cross-module orchestration UI |
| 53 | candidate | `frontend/src/components/catasto/gis/MapContainer.tsx` | `MapContainer` | catasto/GIS | 252 | 173 | 967 | 3 | 0.440 | 20 | Map integration and side effects |
| 52 | candidate | `backend/app/modules/catasto/routes/anagrafica.py` | `_build_bulk_export_rows` | catasto | 281 | 135 | 114 | 3 | 3.649 | 5 | High density; export semantics critical |
| 52 | candidate | `backend/app/services/elaborazioni_bonifica_sync.py` | `_run_bonifica_sync_background` | elaborazioni | 269 | 47 | 232 | 13 | 1.362 | 3 | Background job/retry/concurrency risk |
| 52 | candidate | `frontend/src/app/ruolo/tributi/page.tsx` | `RuoloTributiPageContent` | ruolo | 212 | 181 | 1100 | 3 | 0.357 | 29 | Fiscal domain; high churn |

## Selection formula

Derived from `docs/code-quality/PLAN.md`:

```text
priority = severity * 4 + change_frequency * 3 + defect_risk * 3
           + domain_criticality * 2 + testability
```

Scoring inputs:

- severity: AST cognitive/cyclomatic/nesting/LOC/density;
- change_frequency: `git log --since=90 days ago --name-only` touches, capped 0-5;
- defect_risk: function size, branching and side-effect likelihood;
- domain_criticality: Catasto/Ruolo/Presenze highest, Network/Elaborazioni high;
- testability: availability of nearby unit/e2e characterization paths.

## Rules for Phase 3

1. Only one hotspot may move to `in_progress` per goal.
2. Acquire before metrics immediately before the refactor.
3. Add or identify characterization tests before changing runtime code.
4. Preserve API, auth, DB schema, transaction semantics, UI behavior and business logic.
5. No wrapper/split solely to game metrics.
6. Update baseline only to remove debt that was actually reduced.
7. Stop after one reviewable slice.

## States

- `candidate`: measured but not ready for work;
- `ready`: invariants and tests identified enough to start a dedicated goal;
- `in_progress`: one active refactor goal;
- `reduced`: metrics reduced, residual debt remains;
- `closed`: below threshold or responsibility split accepted;
- `blocked`: human decision or missing characterization required;
- `exception-review`: likely declarative/generated code requiring explicit exception review.
