# Hotspot backlog

Backlog preparato dopo Checkpoint 2 con i dati AST correnti del motore
`tools/code_quality/complexity.py`.

Snapshot di preparazione: `main` a
`2ded321cd99aeb59c02865e5e7f2bc158804e4b9`, 2026-08-19.

## FIRST_REFACTOR_HOTSPOT

- Stato: `IMPROVED` after `P3-I3-CATASTO-GIS-DISTRETTI-PANEL-2026-08-19`.
- Path: `frontend/src/app/catasto/gis/page.tsx`
- Qualified symbol: `CatastoGisPage`
- Module/domain: `catasto / GIS frontend`
- Priority: `64`
- Before P3-I1: cognitive `591`, cyclomatic `538`, LOC `3007`, nesting `4`, density `0.748144`, churn 90d `26`.
- After P3-I1: cognitive `569`, cyclomatic `516`, LOC `2974`, nesting `4`, density `0.718267`.
- After P3-I2: cognitive `540`, cyclomatic `487`, LOC `2865`, nesting `4`, density `0.703518`.
- After P3-I3: cognitive `503`, cyclomatic `450`, LOC `2761`, nesting `4`, density `0.673807`.
- Delta P3-I2: cognitive `-29`, cyclomatic `-29`, LOC `-109`, density `-0.014749`; global violations `4138 -> 4135`, errors `2028 -> 2025`, warnings unchanged `2110`.
- Delta P3-I3: cognitive `-37`, cyclomatic `-37`, LOC `-104`, density `-0.029711`; global violations `4135 -> 4132`, errors `2025 -> 2022`, warnings unchanged `2110`.
- Slices completed: P3-I1 XLSX import mapping / draft overlay construction; P3-I2 WhiteCompany reports panel extracted to `frontend/src/components/catasto/gis/WhiteCompanyReportsPanel.tsx` with 100% targeted coverage and 0 violations; P3-I3 Distretti panel extracted to `frontend/src/components/catasto/gis/DistrettiPanel.tsx` with 100% targeted coverage and 0 violations.
- Checkpoint: `CHECKPOINT 3 — HOTSPOT ITERATION P3-I3 PASS`; Gate backend changes classified as `USER_WORK_UNRELATED` / `PREEXISTING_UNRELATED` by provenance audit and excluded from Catasto/GIS review boundary.
- Residual risk/debt: still a major hotspot; continue only after review with another single same-hotspot slice, not a second hotspot.

## Prioritized candidates

| Priority | Stato | Path | Symbol | Domain | Cog | Cyc | LOC | Nest | Density | Churn90 | Risk/Testability note |
| ---: | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 64 | IMPROVED | `frontend/src/app/catasto/gis/page.tsx` | `CatastoGisPage` | catasto/GIS | 503 | 450 | 2761 | 4 | 0.674 | 26 | P3-I3 passed; residual hotspot, next same-hotspot slice only after review |
| 64 | candidate | `frontend/src/app/presenze/giornaliere/page.tsx` | `PresenzeGiornalierePage` | presenze | 577 | 482 | 2314 | 3 | 0.458 | 18 | Business-critical timekeeping UI |
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
