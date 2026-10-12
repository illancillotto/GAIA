# GAIA — Ownership del checkpoint di pausa

Supersede gli stati ACTIVE dei registri storici soltanto per l'arresto corrente.
Tutti gli agenti sono terminali; nessuna nuova ownership di refactor viene
assegnata. I registri storici restano immutati. MERGED qui significa ammissione
nel checkout dedicato, non merge su main. Nessuno swarm agent puo modificare
runtime o test durante il consolidamento.

| Agent | Domain | File/paths | Slice | Worktree | Branch | Status |
|---|---|---|---|---|---|---|
| Coordinator consolidation | Governance | Nuovo report/manifest/ricevute pausa; PROGRESS e sommario globale | Solo inventario, documentazione e commit selettivi | GAIA-campaign-20261008-integration | refactor/complexity-campaign-20261008 | READY_FOR_REVIEW |
| R39 terminal | Matcher | tools/code_quality/complexity.py; tests/code_quality/test_complexity_positional_provenance.py | Positional provenance gia verificata | Integration | Branch dedicata | MERGED |
| R40 terminal | Bonifica | backend/app/services/elaborazioni_bonifica_sync.py; nuovo test date guard | Sola guardia irraggiungibile | Integration | Branch dedicata | MERGED |
| R38 terminal | Settings | settings-workspace.tsx; test hydration R38 | Hydration gia verificata | Integration | Branch dedicata | MERGED |
| Consolidation R41/R53 | Capacitas | capacitas-workspace.tsx; test activity R53 | Un solo owner per snapshot combinato verificato | Integration | Branch dedicata | MERGED |
| Consolidation R52/R58 | Operazioni | analytics.py; inactive_vehicle_anomalies.py; tre test pertinenti | Un solo owner per snapshot emissione verificato | Integration | Branch dedicata | MERGED |
| R57 terminal | Catasto GIS | gis/page.tsx; parcel-popup-presentation.ts; test R57 | Presentazione popup verificata | Integration | Branch dedicata | MERGED |
| R50 terminal | Worker tests | test_sister_pool_r50_characterization.py | Test-only, runtime invariato | Integration | Branch dedicata | MERGED |
| R59 terminal | Capacitas tests | campaign-capacitas-operation-errors-r59.test.tsx | Test-only sul runtime originale | Integration | Branch dedicata | MERGED |
| R63 terminal | Catasto CF | Spec esterna R63; evidenze author/reviewer | TS2345; nessuna ammissione | SSD r63 separato | Branch test/review R63 | BLOCKED |
| R43/R51 terminal | Presenze/fuel | Candidati esterni | Decisioni test/fixture mancanti | Worktree esterni | Branch proprie | BLOCKED |
| R42/R59-runtime terminal | Candidati respinti | Runtime esterno, mai importato | Regressioni dimostrate | Worktree esterni | Branch proprie | REJECTED |

Il manifest per-file lega documenti e test ai rispettivi owner/prove. La sola
inclusione Git di report respinti non trasferisce ownership o autorizza runtime.
Nessun overlapping agent attivo, nessun file shared assegnato in concorrenza.
Pausa richiesta dall'utente, goal globale incompleto, ripresa solo esplicita.
