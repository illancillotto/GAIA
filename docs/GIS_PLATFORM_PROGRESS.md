# GAIA GIS Platform Progress

> Ultimo aggiornamento: 2026-07-14.
> Branch corrente: `feature/gis-platform-shapefile-import-m13`.

## Stato Sintetico

La fondazione backend della piattaforma GIS e completata. Le milestone M1, M2,
M3, M4, M5, M6, M7, M8, M9, M10, M11, M12 e M13 sono implementate con:

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
- integrazione M8 del dominio Riordino nel catalogo centrale tramite registry
  read-only `riordino_gis_links`;
- guard export shapefile per limitare la generazione ZIP ai soli layer PostGIS
  geometrici;
- dashboard M9 `GET /gis/catalog/dashboard` con metriche catalogo e health
  issue deterministiche;
- pannello `Health catalogo GIS` in `/gis/catalogo`;
- scheduler M10 opt-in per export shapefile NAS;
- retention M10 sui soli export `trigger=scheduled`;
- `latest_exports` nel dashboard e nella UI catalogo;
- integrazione frontend post-M10 del modulo `GIS Platform` nella home e nel
  module switcher/sidebar come modulo autonomo `gis`;
- flag nativo M11 `application_users.module_gis`, esposto da API auth/admin,
  gestibile dalla pagina `Utenti GAIA` e backfillato dalla migration per gli
  utenti gia abilitati al modulo Catasto;
- UX guidata M12 del catalogo `/gis/catalogo`, con spiegazione di layer,
  workspace, source ufficiale, permesso effettivo, import shapefile e apertura
  QGIS Desktop in progetto unico;
- workflow shapefile M12 documentato come percorso guidato: ZIP con `.shp`,
  `.shx`, `.dbf`, `.prj`, validazione, staging PostGIS, anteprima, scelta
  workspace/dominio e pubblicazione governata;
- percorso QGIS Desktop M12 documentato come progetto `.qgz` unico con layer
  visibili, connessione PostGIS governata, stili/gruppi e pacchetto offline solo
  quando il PC non raggiunge il database;
- backend import shapefile M13 con tabella `gis_shapefile_imports`, upload ZIP
  admin-only, validazione componenti `.shp/.shx/.dbf/.prj`, SRID esplicito,
  encoding, feature count, geometry type, bbox, schema campi, checksum SHA-256,
  staging table non distruttiva e audit;
- endpoint M13 `POST /gis/imports/shapefile`, `GET /gis/imports/{import_id}`,
  `POST /gis/imports/{import_id}/validate` e
  `POST /gis/imports/{import_id}/reject`;
- UI M13 su `/gis/catalogo` collegata agli endpoint import per upload ZIP,
  validazione staging, visualizzazione report sintetico e reject cleanup;
- test e coverage 100% sul perimetro GIS backend e sui runtime frontend del
  catalogo, permessi, annotazioni, change request, export, QGIS governance e
  dashboard health/scheduling, navigazione home/sidebar, UX catalogo M12 e
  import shapefile M13.

Restano fuori dal commit GIS e non sono parte del perimetro:

- `domain-docs/presenze/docs/PRESENZE_VALIDAZIONE_REFERENTI_CAPI_SQUADRA.md`;
- `domain-docs/presenze/docs/PRESENZE_VALIDAZIONE_REFERENTI_CAPI_SQUADRA_BREVE.html`.

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
| M8 Integrazione Multi-Dominio | completato | Riordino registrato come registry read-only non geometrico, escluso da QGIS/export shapefile. |
| M9 Dashboard Stato Catalogo | completato | Endpoint `/gis/catalog/dashboard` e pannello health in `/gis/catalogo`. |
| M10 Scheduling E Retention Export NAS | completato | Scheduler opt-in, retention scheduled-only e ultimi export nel dashboard. |
| M11 Accesso Modulo GIS Nativo | completato | `module_gis` backend/frontend, migration con backfill Catasto legacy e admin UI. |
| M12 UX Import Shapefile E QGIS Desktop | completato | Catalogo piu guidato, schede import shapefile, progetto QGIS unico e spiegazioni utente. |
| M13 Import Shapefile Governato | completato | Upload ZIP da UI, validazione pyshp, staging table, audit e reject cleanup. |

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
  - card home `GIS Platform` e voce nel module switcher filtrate come modulo
    `gis`, non come Catasto;
  - accesso frontend basato sul modulo nativo `gis`, non piu su Catasto;
  - client frontend `frontend/src/lib/api/gis.ts`.
- Implementata governance accesso M11:
  - colonna `application_users.module_gis`;
  - migration `20260714_1100_add_gis_module_flag` con backfill `module_gis`
    per utenti che avevano gia `module_catasto`;
  - `enabled_modules` include `gis` per utenti abilitati e super admin;
  - API auth/admin e pagina `Utenti GAIA` espongono il toggle `GIS Platform`.
- Implementata UX catalogo M12:
  - hero guidata e schede "come usare questa pagina";
  - glossario operativo per layer, workspace, source ufficiale e permesso
    effettivo;
  - scheda `Import shapefile` con componenti ZIP obbligatori e pipeline
    governata fino a staging PostGIS e pubblicazione catalogo;
  - scheda `QGIS Desktop in un colpo` con progetto `.qgz` unico, connessione
    PostGIS governata e pacchetto offline come eccezione;
  - copy esplicita sui filtri e sulle fact card layer;
  - nessuna simulazione di upload o download QGIS finche gli endpoint dedicati
    non sono implementati.
- Implementato backend import shapefile M13:
  - migration `20260714_1700_gis_shapefile_imports`;
  - modello `GisShapefileImport`;
  - validazione ZIP sicura contro path traversal;
  - requisito di un solo shapefile per ZIP con `.shp`, `.shx`, `.dbf`, `.prj`;
  - lettura pyshp di feature, campi, bbox, geometry type e record;
  - staging table dinamica non distruttiva in SQLite/test o schema
    `gis_staging` su PostgreSQL;
  - endpoint get, validate idempotente e reject con drop staging;
  - audit `shapefile_import.uploaded`, `shapefile_import.validated`,
    `shapefile_import.rejected`;
  - ordinamento dashboard `latest_exports` stabilizzato su `completed_at`.
- Implementata UI import shapefile M13:
  - form `/gis/catalogo` per ZIP, workspace, dominio, nome/titolo layer, SRID,
    fonte ufficiale ed encoding;
  - upload multipart verso `POST /gis/imports/shapefile`;
  - visualizzazione stato `validated/rejected`, feature count, geometry type,
    staging table e checksum;
  - azione `Rigetta import` collegata a cleanup staging;
  - publish catalogo ancora marcato come in preparazione.
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
- Implementata integrazione multi-dominio M8:
  - bootstrap unico `ensure_gis_platform_catalog`;
  - registry Riordino `riordino_gis_links` registrato in workspace `riordino`;
  - `source_type=domain_registry`, `official_source=riordino`;
  - metadata read-only con `qgis.mode=not_published` e
    `export.shapefile=false`;
  - default role `viewer` read-only idempotente e riparabile;
  - export shapefile bloccato per registry non geometrici;
  - QGIS governance limitata ai soli layer `source_type=postgis`.
- Implementato dashboard stato catalogo M9:
  - endpoint `GET /gis/catalog/dashboard`;
  - metriche totali, attivi/inattivi, workspace, source type, official source;
  - conteggi QGIS publishable ed export shapefile;
  - health status `ok`, `warning`, `critical`;
  - issue deterministiche su permessi, PostGIS, QGIS edit policy e registry;
  - UI `Health catalogo GIS` in `/gis/catalogo`.
- Implementato scheduling/retention export M10:
  - settings `GIS_EXPORT_SCHEDULER_*`, `GIS_EXPORT_RETENTION_COUNT`,
    `GIS_EXPORT_MAX_LAYERS_PER_RUN`;
  - scheduler `gis_shapefile_export_schedule` disabilitato di default;
  - runner `run_scheduled_shapefile_exports`;
  - audit `export.scheduled` e `export.retention_applied`;
  - retention per layer sui soli export scheduled;
  - blocco `latest_exports` in `/gis/catalog/dashboard` e `/gis/catalogo`.
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
.venv/bin/python -m pytest tests/test_gis_platform_api.py tests/test_gis_export_scheduler.py tests/test_bootstrap_admin.py tests/test_main_lifespan_scheduler.py --cov=app.modules.gis --cov=app.main --cov-report=term-missing --cov-fail-under=100 -q
```

Esito:

- `45 passed`;
- coverage `100%`.

Backend config M10:

```bash
cd backend
.venv/bin/python -m pytest tests/test_config.py --cov=app.core.config --cov-report=term-missing --cov-fail-under=100 -q
```

Esito:

- `5 passed`;
- coverage `100%` su `app.core.config`.

Backend M13:

```bash
cd backend
.venv/bin/python -m pytest tests/test_gis_platform_api.py -q
.venv/bin/python -m pytest tests/test_gis_platform_api.py tests/test_gis_export_scheduler.py tests/test_bootstrap_admin.py tests/test_main_lifespan_scheduler.py --cov=app.modules.gis --cov=app.main --cov-report=term-missing --cov-fail-under=100 -q
.venv/bin/python -m pytest tests/test_app_metadata.py tests/test_alembic.py -q
.venv/bin/alembic heads
```

Esito:

- GIS API: `31 passed`;
- coverage backend GIS/main: `48 passed`, `100%`;
- metadata/alembic: `11 passed`;
- head Alembic: `20260714_1700`.

Frontend M10:

```bash
cd frontend
npm run test:unit -- --run tests/unit/gis-api-client.test.ts tests/unit/gis-catalog-page.test.tsx
npm run typecheck
VITEST_COVERAGE_INCLUDE=src/lib/api/gis.ts,src/app/gis/catalogo/page.tsx npm run test:coverage -- --run tests/unit/gis-api-client.test.ts tests/unit/gis-catalog-page.test.tsx
```

Esito:

- `23 passed`.
- typecheck pulito;
- coverage frontend runtime GIS modificati: `100%`.

Frontend M12:

```bash
cd frontend
npm run test:unit -- --run tests/unit/gis-catalog-page.test.tsx
npm run typecheck
VITEST_COVERAGE_INCLUDE=src/app/gis/catalogo/page.tsx npm run test:coverage -- --run tests/unit/gis-catalog-page.test.tsx
```

Esito:

- unit mirato: `15 passed`;
- typecheck pulito;
- coverage `100%` su `frontend/src/app/gis/catalogo/page.tsx`.

Frontend M13:

```bash
cd frontend
npm run test:unit -- --run tests/unit/gis-api-client.test.ts tests/unit/gis-catalog-page.test.tsx
npm run typecheck
VITEST_COVERAGE_INCLUDE=src/lib/api/gis.ts,src/app/gis/catalogo/page.tsx npm run test:coverage -- --run tests/unit/gis-api-client.test.ts tests/unit/gis-catalog-page.test.tsx
```

Esito:

- unit mirati: `27 passed`;
- typecheck pulito;
- coverage `100%` su `frontend/src/lib/api/gis.ts` e
  `frontend/src/app/gis/catalogo/page.tsx`.

Graphify M10:

```bash
make graphify-backend
make graphify-frontend
make graphify-docs
```

Esito:

- backend graph aggiornato: `6053` nodi, `14386` edge;
- frontend graph aggiornato: `4170` nodi, `10582` edge;
- domain-docs graph aggiornato: `746` nodi, `1074` edge, `0` file
  riestratti.

Graphify M12:

```bash
make graphify-frontend
make graphify-docs
```

Esito:

- frontend graph aggiornato: `4181` nodi, `10602` edge, `159` communities;
- domain-docs graph aggiornato: `765` nodi, `1103` edge, `60` communities,
  `0` file riestratti.

Graphify M13:

```bash
make graphify-backend
make graphify-docs
```

Esito:

- backend graph aggiornato: `6075` nodi, `14445` edge, `378` communities;
- frontend graph aggiornato: `4191` nodi, `10627` edge, `174` communities;
- domain-docs graph aggiornato: `765` nodi, `1104` edge, `56` communities,
  `0` file riestratti.

Graphify M8:

```bash
make graphify-backend
make graphify-docs
```

Esito:

- backend graph aggiornato: `6019` nodi, `14305` edge;
- domain-docs graph aggiornato: `734` nodi, `1023` edge, `3` file
  riestratti.

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

- Se servono ruoli LOGIN QGIS personali o per postazione.
- Se e quando avviare il POC QGIS Server read-only raccomandato da M7.
- Quale dominio geometrico non Catasto onboardare dopo il registry Riordino, se
  serve provare edit/QGIS controllato fuori Catasto.
- Se implementare prima publish catalogo da import validato o generazione
  progetto QGIS unico.

## Rischi

- L'export NAS reale usa il path configurato sul layer o sulla richiesta: in
  produzione serve garantire permessi filesystem coerenti sul mount NAS.
- Lo scheduler export GIS e disabilitato di default: va abilitato solo dopo aver
  verificato mount NAS, spazio disponibile e finestra operativa.
- Le change request arrivano fino a `applied`, ma l'apply Catasto e no-op
  auditato: non modifica le tabelle ufficiali finche il dominio non abilita una
  policy esplicita.
- La policy QGIS genera SQL ma non lo applica automaticamente: serve esecuzione
  controllata da operatore DB e gestione sicura dei ruoli LOGIN.
- I registry non geometrici, come `riordino_gis_links`, sono visibili nel
  catalogo ma non sono pubblicabili come QGIS layer ne esportabili come
  shapefile.
- Le CTA M12 per import shapefile e progetto QGIS restano informative: abilitarle
  senza integrazione frontend dedicata creerebbe falsa operativita.
- M13 carica in staging non distruttivo e registra l'import da UI, ma non
  pubblica ancora un layer ufficiale nel catalogo e non sostituisce workflow di
  dominio.

## Prossima Azione Raccomandata

Chiudere M13 e scegliere il prossimo incremento runtime:

1. implementare publish governato da import validato a catalogo o change request;
2. implementare preview dettagliata dello staging import;
3. implementare generazione/scarico progetto QGIS `.qgz` per layer visibili;
4. onboarding di un dominio geometrico non Catasto con opt-in QGIS controlled
   edit;
5. eventuale POC QGIS Server read-only se serve pubblicazione OGC standard.
