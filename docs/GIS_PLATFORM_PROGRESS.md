# GAIA GIS Platform Progress

> Ultimo aggiornamento: 2026-07-14.
> Branch corrente: `feature/gis-platform-permissions-m2`.

## Stato Sintetico

La fondazione backend della piattaforma GIS e completata. Le milestone M1 e M2
sono implementate con:

- commit `fac60f1 feat(gis): bootstrap governed catalog`;
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
- test e coverage 100% sul perimetro GIS backend e sui nuovi runtime frontend del catalogo/permessi.

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
| M3 Annotazioni Governate | pianificato | Lifecycle note e allegati come riferimenti. |
| M4 Change Request Workflow | pianificato | Reject/request changes, diff, validazioni pluggable. |
| M5 Export NAS Reale | pianificato | Job export shapefile, manifest, checksum, publish atomico. |
| M6 Governance QGIS Desktop | pianificato | Ruoli DB, runbook QGIS, policy connessione. |
| M7 Decisione OGC | futuro | POC QGIS Server vs GeoServer. |
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

- `26 passed`;
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

Regression leggera:

```bash
cd backend
.venv/bin/python -m pytest tests/test_app_metadata.py tests/test_alembic.py -q
.venv/bin/alembic heads
```

Esito:

- `11 passed`;
- head Alembic: `20260713_0900`.

Graphify M2:

```bash
make graphify-backend
make graphify-frontend
make graphify-docs
```

Esito:

- completati.

## Decisioni Aperte

- Se i metadata layer saranno modificabili solo da `admin` globale o anche da futuri `gis_admin`.
- Formato definitivo manifest export NAS.
- Se e quando avviare POC QGIS Server o GeoServer.

## Rischi

- Il contratto export NAS esiste, ma il job reale non e implementato.
- Le change request non applicano modifiche ufficiali: oggi sono workflow/audit, non editing effettivo.
- La governance QGIS Desktop richiede ruoli DB e runbook prima dell'uso diffuso.

## Prossima Azione Raccomandata

Chiudere M2:

1. commit della milestone M2;
2. avvio M3 su annotazioni governate.
