# GAIA GIS Platform Progress

> Ultimo aggiornamento: 2026-07-14.
> Branch corrente: `feature/gis-platform-qgis-governance`.

## Stato Sintetico

La fondazione backend della piattaforma GIS e completata e committata con:

- commit `fac60f1 feat(gis): bootstrap governed catalog`;
- modulo `backend/app/modules/gis`;
- migration `20260713_0900_gis_platform_governance`;
- router `/gis`;
- bootstrap catalogo Catasto read-only;
- test e coverage 100% sul perimetro GIS.

Restano fuori dal commit GIS e non sono parte del perimetro:

- `backend/gaia_compute.py`;
- `backend/gen_export.py`;
- `backend/instrument.py`.

## Avanzamento Per Milestone

| Milestone | Stato | Note |
| --- | --- | --- |
| M0 Fondazione Backend | completato | Catalogo, permessi, annotazioni, change request, export metadata, audit e bootstrap Catasto. |
| M1 Catalogo Operativo | prossimo | Servono filtri, update metadata admin-only e UI read-only. |
| M2 Permessi Layer Completi | pianificato | Revoke/delete, precedenza role/user, UI admin. |
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
  - `make graphify-catasto-docs`.

## Verifiche Eseguite

Backend GIS:

```bash
cd backend
.venv/bin/python -m pytest tests/test_gis_platform_api.py tests/test_bootstrap_admin.py tests/test_main_lifespan_scheduler.py --cov=app.modules.gis --cov=app.main --cov=app.api.router --cov=app.db.base --cov-report=term-missing --cov-fail-under=100 -q
```

Esito:

- `23 passed`;
- coverage `100%`.

Regression leggera:

```bash
cd backend
.venv/bin/python -m pytest tests/test_app_metadata.py tests/test_alembic.py -q
.venv/bin/alembic heads
```

Esito:

- `11 passed`;
- head Alembic: `20260713_0900`.

## Decisioni Aperte

- Dove collocare la UI catalogo GIS nel menu GAIA.
- Se i metadata layer saranno modificabili solo da `admin` globale o anche da futuri `gis_admin`.
- Policy di precedenza tra permessi role e user.
- Formato definitivo manifest export NAS.
- Se e quando avviare POC QGIS Server o GeoServer.

## Rischi

- Il catalogo GIS e pronto, ma non ha ancora UI dedicata.
- Il contratto export NAS esiste, ma il job reale non e implementato.
- Le change request non applicano modifiche ufficiali: oggi sono workflow/audit, non editing effettivo.
- La governance QGIS Desktop richiede ruoli DB e runbook prima dell'uso diffuso.

## Prossima Azione Raccomandata

Implementare M1:

1. filtri catalogo backend;
2. update metadata admin-only con audit;
3. pagina frontend read-only catalogo GIS;
4. test API/UI;
5. Graphify backend/frontend/docs.
