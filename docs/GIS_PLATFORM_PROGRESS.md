# GAIA GIS Platform Progress

> Ultimo aggiornamento: 2026-07-14.
> Branch corrente: `feature/gis-platform-ogc-decision-m7`.

## Stato Sintetico

La fondazione backend della piattaforma GIS e completata. Le milestone M1, M2,
M3, M4, M5, M6 e M7 sono implementate con:

- commit `5405713 feat(gis): add governed catalog operations`;
- commit `a6edcb1 feat(gis): complete layer permission governance`;
- modulo `backend/app/modules/gis`;
- migration `20260713_0900_gis_platform_governance`;
- router `/gis`;
- bootstrap catalogo Catasto read-only;
- filtri catalogo backend;
- patch metadata admin-only;
- activate/deactivate layer con audit;
- pagina frontend read-only `/gis/catalogo`;
- revoke permission;
- validazione ruoli principal;
- policy user-over-role;
- audit `permission.granted`, `permission.updated`, `permission.revoked`;
- pannello permessi admin in `/gis/catalogo`;
- lifecycle annotazioni `open`, `in_review`, `closed`, `rejected`;
- filtri annotazioni per `status` e `feature_id`;
- update annotazioni e transizioni `in-review`, `close`, `reject`;
- audit `annotation.created`, `annotation.updated`, `annotation.in_review`,
  `annotation.closed`, `annotation.rejected`;
- pannello annotazioni in `/gis/catalogo`;
- stati change request `submitted`, `needs_changes`, `approved`, `rejected`,
  `applied`;
- payload change request formalizzati per attribute, geometry, create e delete;
- update/resubmit draft, request-changes, approve, reject e apply no-op;
- validator pluggable per layer, dominio o workspace;
- audit `change_request.submitted`, `change_request.updated`,
  `change_request.needs_changes`, `change_request.approved`,
  `change_request.rejected`, `change_request.applied`;
- pannello change request in `/gis/catalogo`;
- export shapefile ZIP reale con manifest JSON e checksum SHA-256;
- publish atomico su path NAS/local;
- stati export `completed` e `failed`;
- audit `export.requested`, `export.completed`, `export.failed`;
- governance QGIS Desktop con endpoint admin-only `/gis/qgis/governance`;
- policy SQL per schema `gis_qgis`, ruoli DB read-only/edit controllato e view
  pubblicabili;
- runbook operativo `docs/GIS_QGIS_DESKTOP_RUNBOOK.md`;
- decision record OGC `docs/GIS_OGC_DECISION_RECORD.md`;
- scelta M7: nessun runtime OGC default, POC QGIS Server read-only se serve
  pubblicazione standard;
- test e coverage 100% sul perimetro GIS backend e sui runtime frontend del
  catalogo, permessi, annotazioni, change request, export e QGIS governance.

Restano fuori dal commit GIS e non sono parte del perimetro:

- `backend/gaia_compute.py`;
- `backend/gen_export.py`;
- `backend/instrument.py`.

## Avanzamento Per Milestone

| Milestone | Stato | Note |
| --- | --- | --- |
| M0 Fondazione Backend | completato | Catalogo, permessi, annotazioni, change request, export metadata, audit e bootstrap Catasto. |
| M1 Catalogo Operativo | completato | Filtri, patch metadata admin-only, toggle active, audit e UI `/gis/catalogo`. |
| M2 Permessi Layer Completi | completato | Revoke/delete, validazione ruoli, precedenza user-over-role, audit e UI admin. |
| M3 Annotazioni Governate | completato | Lifecycle note, filtri, update, transizioni stato, audit e UI `/gis/catalogo`. |
| M4 Change Request Workflow | completato | Stati estesi, update/resubmit, request changes, approve/reject/apply no-op, diff e validator pluggable. |
| M5 Export NAS Reale | completato | ZIP shapefile, manifest, checksum SHA-256, publish atomico, status completed/failed e audit. |
| M6 Governance QGIS Desktop | completato | Endpoint policy SQL, ruoli DB reader/editor, view read-only, runbook QGIS. |
| M7 Decisione OGC | completato | Decision record: no runtime OGC default, POC QGIS Server read-only, GeoServer come opzione multi-dominio. |
| M8 Integrazione Multi-Dominio | futuro | Onboarding domini non Catasto. |

## Completato

- Creato schema dati GIS:
  - `gis_layers`;
  - `gis_layer_permissions`;
  - `gis_annotations`;
  - `gis_change_requests`;
  - `gis_layer_exports`;
  - `gis_audit_logs`.
- Implementate API MVP:
  - `GET /gis/layers`;
  - `POST /gis/layers`;
  - `GET /gis/layers/{layer_id}`;
  - `GET /gis/workspaces/{workspace}/layers`;
  - `GET/POST /gis/layers/{layer_id}/annotations`;
  - `GET/POST /gis/layers/{layer_id}/permissions`;
  - `POST /gis/layers/{layer_id}/change-requests`;
  - `GET /gis/change-requests`;
  - `POST /gis/change-requests/{change_request_id}/approve`;
  - `POST /gis/layers/{layer_id}/export-shapefile`.
- Implementate API M1:
  - `GET /gis/layers` con filtri `workspace`, `domain_module`, `source_type`, `official_source`, `is_active`;
  - `PATCH /gis/layers/{layer_id}/metadata`;
  - `POST /gis/layers/{layer_id}/activate`;
  - `POST /gis/layers/{layer_id}/deactivate`.
- Implementata UI M1:
  - `/gis/catalogo`;
  - redirect `/gis`;
  - navigazione `GIS Platform` separata da `Catasto / GIS`;
  - client frontend `frontend/src/lib/api/gis.ts`.
- Implementate API M2:
  - `DELETE /gis/layers/{layer_id}/permissions/{permission_id}`;
  - validazione principal `role` contro ruoli applicativi GAIA;
  - policy `user` override su permesso `role`;
  - audit `permission.granted`, `permission.updated`, `permission.revoked`.
- Implementata UI M2:
  - pannello `Gestisci permessi` su `/gis/catalogo` per layer con `can_manage`;
  - grant/update/revoke per principal `role` e `user`;
  - affordance read-only per utenti senza `can_manage`.
- Implementate API M3:
  - `GET /gis/layers/{layer_id}/annotations?status=&feature_id=`;
  - `PATCH /gis/layers/{layer_id}/annotations/{annotation_id}`;
  - `POST /gis/layers/{layer_id}/annotations/{annotation_id}/in-review`;
  - `POST /gis/layers/{layer_id}/annotations/{annotation_id}/close`;
  - `POST /gis/layers/{layer_id}/annotations/{annotation_id}/reject`;
  - audit lifecycle annotazioni.
- Implementata UI M3:
  - pannello `Annotazioni` su `/gis/catalogo` per layer con `can_view`;
  - filtri `status` e `feature_id`;
  - create/update note per layer con `can_annotate`;
  - transizioni `in_review`, `closed`, `rejected` secondo capability layer;
  - gestione read-only quando manca `can_annotate`.
- Implementate API M4:
  - `GET /gis/change-requests?status=&layer_id=`;
  - `POST /gis/layers/{layer_id}/change-requests`;
  - `PATCH /gis/change-requests/{change_request_id}`;
  - `POST /gis/change-requests/{change_request_id}/request-changes`;
  - `POST /gis/change-requests/{change_request_id}/approve`;
  - `POST /gis/change-requests/{change_request_id}/reject`;
  - `POST /gis/change-requests/{change_request_id}/apply`;
  - validazioni payload per `attribute_update`, `geometry_update`,
    `feature_create`, `feature_delete`;
  - apply Catasto no-op auditato.
- Implementata UI M4:
  - pannello `Change request` su `/gis/catalogo` per layer con `can_view`;
  - filtro status e scope layer;
  - form JSON submit/update per `can_edit`;
  - diff payload leggibile;
  - note revisione e azioni approver per `can_approve`;
  - gestione read-only quando manca `can_edit`.
- Implementato M5 export:
  - runner `app.modules.gis.exporter`;
  - generazione ZIP shapefile con `.shp`, `.shx`, `.dbf`, `.cpg` e manifest;
  - manifest con sorgente PostGIS, mapping campi DBF, SRID, geometry type,
    metadata e row count;
  - checksum SHA-256 calcolato dal file pubblicato;
  - publish atomico tramite file temporaneo e replace finale;
  - stati `completed` e `failed` su `gis_layer_exports`;
  - failure reason in `metadata.error`;
  - audit `export.requested`, `export.completed`, `export.failed`.
- Implementata governance QGIS M6:
  - endpoint `GET /gis/qgis/governance` admin-only;
  - generatore SQL `app.modules.gis.qgis_governance`;
  - schema `gis_qgis`;
  - ruoli gruppo NOLOGIN `gaia_gis_qgis_reader`, `gaia_gis_qgis_editor`,
    `gaia_gis_qgis_admin`;
  - view read-only per layer PostGIS attivi;
  - Catasto sempre read-only;
  - grant edit solo per layer non Catasto con opt-in metadata
    `qgis.editable=true` e `qgis.edit_policy=controlled`;
  - runbook `docs/GIS_QGIS_DESKTOP_RUNBOOK.md`.
- Implementata decisione OGC M7:
  - decision record `docs/GIS_OGC_DECISION_RECORD.md`;
  - confronto QGIS Server vs GeoServer;
  - raccomandazione POC QGIS Server read-only se serve WMS/WFS;
  - GeoServer come opzione per governance OGC multi-dominio piu granulare;
  - piano sicurezza/proxy/auth;
  - piano rollout se il POC passa;
  - WFS-T/write OGC esclusi dalla baseline.
- Registrati layer Catasto PostGIS/Martin nel catalogo centrale:
  - `cat_particelle_current`;
  - `cat_distretti`;
  - `cat_distretti_boundaries`;
  - `cat_delivery_points_current`;
  - `cat_irrigation_canals_current`;
  - `cat_dui_2026_current`.
- Garantita separazione:
  - `/gis` governa catalogo e workflow trasversali;
  - `/catasto/gis` resta console GIS Catasto.
- Graphify aggiornato:
  - `make graphify-backend`;
  - `make graphify-catasto-docs`;
  - `make graphify-frontend`;
  - `make graphify-docs`.

## Verifiche Eseguite

Backend GIS:

```bash
cd backend
.venv/bin/python -m pytest tests/test_gis_platform_api.py tests/test_bootstrap_admin.py tests/test_main_lifespan_scheduler.py --cov=app.modules.gis --cov=app.main --cov=app.api.router --cov=app.db.base --cov-report=term-missing --cov-fail-under=100 -q
```

Esito:

- `32 passed`;
- coverage `100%`.

Backend M1:

```bash
cd backend
.venv/bin/python -m pytest tests/test_gis_platform_api.py --cov=app.modules.gis --cov-report=term-missing --cov-fail-under=100 -q
```

Esito:

- `13 passed`;
- coverage `100%` su `app.modules.gis`.

Frontend M1:

```bash
cd frontend
npm run test:unit -- --run tests/unit/gis-api-client.test.ts tests/unit/gis-catalog-page.test.tsx tests/unit/gis-navigation.test.tsx tests/unit/presence-route-meta.test.ts tests/unit/app-shell.test.tsx
npm run typecheck
VITEST_COVERAGE_INCLUDE=src/lib/api/gis.ts,src/app/gis/catalogo/page.tsx npm run test:coverage -- --run tests/unit/gis-api-client.test.ts tests/unit/gis-catalog-page.test.tsx
npm test
```

Esito:

- unit mirati: `5 passed`, `17 passed`;
- typecheck pulito;
- coverage frontend nuovi runtime catalogo: `100%`.
- smoke frontend: `18 passed`.

Backend M2:

```bash
cd backend
.venv/bin/python -m pytest tests/test_gis_platform_api.py --cov=app.modules.gis --cov-report=term-missing --cov-fail-under=100 -q
```

Esito:

- `14 passed`;
- coverage `100%` su `app.modules.gis`.

Frontend M2:

```bash
cd frontend
npm run test:unit -- --run tests/unit/gis-api-client.test.ts tests/unit/gis-catalog-page.test.tsx tests/unit/gis-navigation.test.tsx tests/unit/presence-route-meta.test.ts tests/unit/app-shell.test.tsx
npm run typecheck
VITEST_COVERAGE_INCLUDE=src/lib/api/gis.ts,src/app/gis/catalogo/page.tsx npm run test:coverage -- --run tests/unit/gis-api-client.test.ts tests/unit/gis-catalog-page.test.tsx
```

Esito:

- unit mirati: `5 passed`, `21 passed`;
- typecheck pulito;
- coverage frontend runtime catalogo/permessi: `100%`.
- smoke frontend: `18 passed`;
- lint frontend: exit `0`, con warning pre-esistenti in file non toccati.

Backend M3:

```bash
cd backend
.venv/bin/python -m pytest tests/test_gis_platform_api.py --cov=app.modules.gis --cov-report=term-missing --cov-fail-under=100 -q
```

Esito:

- `15 passed`;
- coverage `100%` su `app.modules.gis`.

Frontend M3:

```bash
cd frontend
npm run test:unit -- --run tests/unit/gis-api-client.test.ts tests/unit/gis-catalog-page.test.tsx
npm run typecheck
VITEST_COVERAGE_INCLUDE=src/lib/api/gis.ts,src/app/gis/catalogo/page.tsx npm run test:coverage -- --run tests/unit/gis-api-client.test.ts tests/unit/gis-catalog-page.test.tsx
```

Esito:

- unit mirati: `18 passed`;
- typecheck pulito;
- coverage frontend runtime catalogo/annotazioni: `100%` statement, branch,
  function e line.

Backend M4:

```bash
cd backend
.venv/bin/python -m pytest tests/test_gis_platform_api.py --cov=app.modules.gis --cov-report=term-missing --cov-fail-under=100 -q
```

Esito:

- `16 passed`;
- coverage `100%` su `app.modules.gis`.

Frontend M4:

```bash
cd frontend
npm run test:unit -- --run tests/unit/gis-api-client.test.ts tests/unit/gis-catalog-page.test.tsx
npm run typecheck
VITEST_COVERAGE_INCLUDE=src/lib/api/gis.ts,src/app/gis/catalogo/page.tsx npm run test:coverage -- --run tests/unit/gis-api-client.test.ts tests/unit/gis-catalog-page.test.tsx
```

Esito:

- unit mirati: `21 passed`;
- typecheck pulito;
- coverage frontend runtime catalogo/change request: `100%` statement, branch,
  function e line.

Backend M5:

```bash
cd backend
.venv/bin/python -m pytest tests/test_gis_platform_api.py --cov=app.modules.gis --cov-report=term-missing --cov-fail-under=100 -q
```

Esito:

- `19 passed`;
- coverage `100%` su `app.modules.gis`, incluso `app.modules.gis.exporter`.

Backend M6:

```bash
cd backend
.venv/bin/python -m pytest tests/test_gis_platform_api.py --cov=app.modules.gis --cov-report=term-missing --cov-fail-under=100 -q
```

Esito:

- `20 passed`;
- coverage `100%` su `app.modules.gis`, incluso
  `app.modules.gis.qgis_governance`.

Regression leggera:

```bash
cd backend
.venv/bin/python -m pytest tests/test_app_metadata.py tests/test_alembic.py -q
.venv/bin/alembic heads
```

Esito:

- `11 passed`;
- head Alembic: `20260713_0900`.

Graphify M6:

```bash
make graphify-backend
make graphify-frontend
make graphify-docs
```

Esito:

- completati.

Docs M7:

```bash
make graphify-docs
```

Esito:

- completato.

## Decisioni Aperte

- Retention e scheduling automatico degli export NAS, se servono oltre alla richiesta manuale.
- Se servono ruoli LOGIN QGIS personali o per postazione.
- Se e quando avviare il POC QGIS Server read-only raccomandato da M7.

## Rischi

- L'export NAS reale usa il path configurato sul layer o sulla richiesta: in
  produzione serve garantire permessi filesystem coerenti sul mount NAS.
- Le change request arrivano fino a `applied`, ma l'apply Catasto e no-op
  auditato: non modifica le tabelle ufficiali finche il dominio non abilita una
  policy esplicita.
- La policy QGIS genera SQL ma non lo applica automaticamente: serve esecuzione
  controllata da operatore DB e gestione sicura dei ruoli LOGIN.

## Prossima Azione Raccomandata

Chiudere M7 e avviare M8:

1. commit della milestone M7;
2. avvio M8 su integrazione multi-dominio;
3. onboarding di un dominio non Catasto usando catalogo, permessi, annotazioni,
   change request, export e policy QGIS gia disponibili.
