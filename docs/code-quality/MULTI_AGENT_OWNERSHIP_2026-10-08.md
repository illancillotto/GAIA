# GAIA — Campaign ownership 2026-10-08

Coordinator: Codex root. Snapshot/merge-base: `55a1b1d35911451e018b662c2acc450bf5994ea2`.
Audit: `reports/code-quality/COMPLEXITY_AUDIT_2026-10-08.md`.
Il checkout main contiene lavoro concorrente Presenze/Ruolo/Elaborazioni:
nessun reset, copia automatica o commit di quel lavoro nello swarm.
Integrazione su branch dedicata; main non viene spostato durante la campagna.
Baseline, soglie, esclusioni e tooling complexity sono read-only.

## Ownership attiva e sequenza

| Agent | Domain | File/paths | Slice | Worktree | Branch | Status |
| --- | --- | --- | --- | --- | --- | --- |
| Coordinator | Governance | Questo registro, progress e report finale | Sequencing e gate | GAIA | main | ACTIVE |
| BASELINE | Provenance | reports/code-quality/BASELINE_PROVENANCE_2026-10-08.md | 30 divergenze; sorgenti read-only | GAIA-campaign-20261008-baseline | refactor/complexity-baseline-provenance | ACTIVE |
| P1 | Presenze UI | frontend/src/app/presenze/giornaliere/page.tsx; helper locali nuovi e test Presenze esclusivi | Filtri/selezione/transizioni: una responsabilità; target cognitiva <250 o -50% | GAIA-campaign-20261008-presenze | refactor/complexity-presenze-ui | ACTIVE |
| P2 | Capacitas UI | frontend/src/components/elaborazioni/capacitas-workspace.tsx; helper locali nuovi e test Capacitas esclusivi | Controller/modello batch coerente | GAIA-campaign-20261008-capacitas | refactor/complexity-capacitas-ui | ACTIVE |
| P3 | Operazioni | backend/app/modules/operazioni/routes/analytics.py; helper analytics locali nuovi; backend/tests/test_operazioni_analytics.py e test nuovi esclusivi | fuel_analytics aggregazione; poi anomalies soltanto dopo gate | GAIA-campaign-20261008-analytics | refactor/complexity-operazioni-analytics | ACTIVE |
| P4 | Catasto UI | frontend/src/app/catasto/anomalie/page.tsx; helper locali nuovi e test anomalie esclusivi | Modello lista/azioni coerente | GAIA-campaign-20261008-catasto-ui | refactor/complexity-catasto-anomalie-ui | PLANNED |
| P5 | Utenze UI | frontend/src/app/utenze/[id]/page.tsx; helper locali nuovi e test detail esclusivi | Modello derivato/azioni dettaglio | GAIA-campaign-20261008-utenze-ui | refactor/complexity-utenze-detail-ui | PLANNED |
| P6 | Elaborazioni UI | frontend/src/components/elaborazioni/settings-workspace.tsx; helper locali nuovi e test settings esclusivi | Validazione/configurazione coerente | GAIA-campaign-20261008-settings-ui | refactor/complexity-elaborazioni-settings-ui | ACTIVE |
| INTEGRATION | Integration | Branch integration, report integration esclusivo; runtime read-only per review | Review e merge sequenziali di slice verdi | GAIA-campaign-20261008-integration | refactor/complexity-campaign-20261008 | PLANNED |
| FINAL | Verification | Report final verification esclusivo; runtime read-only | Suite e gate finali | GAIA-campaign-20261008-integration | refactor/complexity-campaign-20261008 | PLANNED |

Capacità disponibile: quattro agenti inclusa root. BASELINE parte prima;
gli agenti successivi sono avviati in batch, massimo tre child simultanei.
INTEGRATION e FINAL usano la stessa branch in momenti diversi, mai due owner
scriventi sugli stessi percorsi. Ogni agent ha report esclusivo in
`reports/code-quality/SLICE_<AGENT>_2026-10-08.md`.
Modifiche a lib/hooks/UI/layout condivisi richiedono ownership esplicita del
Coordinator. Nessun agente modifica PROGRESS o baseline condivise.
Copertura full-file statement/branch 100% obbligatoria per runtime toccati:
un candidato privo di questo gate resta BLOCKED/REJECTED, non viene integrato.

## Planning wave successive

Wave 2: Ruolo tributi/repositories, Capacitas Terreni, Network scan/statistiche,
Wiki orchestrator/metriche, Bonifica orchestration. Una responsabilità per
slice, agenti aggiunti al registro prima dello spawn. Tributi è inizialmente
BLOCKED_BY_CONCURRENT_WORK nel checkout principale.
Wave 3: Catasto backend (ADE WFS, matching, GIS, anomalie/import), frontend GIS,
GIS condiviso; ownership distinte. Wave 4: altri domini soltanto dopo checkpoint
di integrazione verde e sulla base del ranking aggiornato.

## File priority list considerata

| Path | Planning |
| --- | --- |
| backend/app/modules/ruolo/tributi_repositories.py | W2 B1; concurrent, non assegnato runtime |
| backend/app/services/elaborazioni_capacitas_terreni.py | W2 B3 |
| frontend/src/app/presenze/giornaliere/page.tsx | W1 P1 |
| backend/app/modules/ruolo/repositories.py | W2 B2 |
| frontend/src/features/organigramma/organigramma-workspace.tsx | W4 |
| frontend/src/components/elaborazioni/capacitas-workspace.tsx | W1 P2 |
| backend/app/modules/operazioni/routes/mobile_sync.py | W4; contract skill obbligatoria |
| frontend/src/app/operazioni/analisi/page.tsx | W4 |
| backend/app/services/elaborazioni_capacitas_incass.py | W2 follow-up separato |
| backend/app/modules/gis/services.py | W3 GIS backend |
| backend/app/modules/operazioni/routes/analytics.py | W1 P3 |
| frontend/src/app/ruolo/tributi/page.tsx | W4 |
| backend/app/modules/network/services.py | W2 B4 |
| frontend/src/components/catasto/gis/MapContainer.tsx | W3 GIS frontend |
| backend/app/modules/utenze/services/import_service.py | W4 |
| backend/app/modules/catasto/services/ade_wfs.py | W3 |
| backend/app/modules/riordino/services/block_service.py | W4 |
| backend/app/modules/utenze/anpr/service.py | W4 |
| backend/app/modules/catasto/routes/anagrafica/matching.py | W3 |
| backend/app/modules/catasto/services/gis_service.py | W3 |
| frontend/src/app/catasto/anomalie/page.tsx | W1 P4 |
| backend/app/modules/catasto/routes/anomalie.py | W3 |
| backend/app/modules/catasto/routes/import_routes.py | W3 |
| frontend/src/components/elaborazioni/settings-workspace.tsx | W1 P6 |
| frontend/src/components/elaborazioni/bonifica-sync-workspace.tsx | W4 |
| frontend/src/components/catasto/anagrafica/AnagraficaBulkPanel.tsx | W3 |
| backend/app/modules/operazioni/services/import_fleet_transactions.py | W4 |
| backend/app/modules/wiki/services/orchestrator.py | W2 B5 |
| backend/app/services/gate_mobile_sync.py | W4; concurrent domain e contract |
| modules/elaborazioni/worker/browser_session.py | W4 worker |

## Checkpoint iniziale

HEAD e merge-base main coincidono con lo snapshot richiesto. I runtime W1 non
risultano modificati nei working tree locali al preflight. Branch storiche
esistenti non vengono riutilizzate né integrate. Commit e merge sono autorizzati
dal brief corrente, esclusivamente nelle worktree/branch dello swarm.

## Decisioni slice iniziali

- P1: characterization esistente full-file 100% PASS. Prima slice approvata:
  consolidamento duplicazione card anomalie nelle due viste, presenter sotto
  soglia e riduzione aggregata reale. Non dichiarare raggiunto il target -50%
  con una singola slice più piccola; ulteriori slice solo dopo gate verde.
- P3: worktree preparata; prima suite analytics/coverage avviata dal Coordinator.
  Ownership temporanea Coordinator fino al passaggio esplicito all'agent P3.
- P6: readiness coverage delle tre suite settings/modal in corso dal Coordinator;
  nessuna modifica runtime prima del gate di caratterizzazione.
- Provenance preliminare: 30 valori baseline corrispondono alla sorgente storica;
  regressioni metriche runtime e divergenze test introdotte in commit successivi,
  non dal lavoro corrente. Il report BASELINE conserva commit e dettagli.
