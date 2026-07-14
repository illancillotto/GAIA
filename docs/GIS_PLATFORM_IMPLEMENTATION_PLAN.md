# GAIA GIS Platform Implementation Plan

> Data: 2026-07-14.
> Scope: piattaforma GIS trasversale GAIA, non refactor del GIS Catasto.

## Stato Di Partenza

Gia completato su branch `feature/gis-platform-qgis-governance`:

- modulo backend `backend/app/modules/gis`;
- catalogo layer, permessi layer, annotazioni, change request, export metadata e audit;
- migration `20260713_0900_gis_platform_governance`;
- bootstrap idempotente dei layer Catasto PostGIS/Martin nel catalogo centrale;
- test backend con coverage 100% sul perimetro GIS e wiring runtime;
- documentazione architetturale in `docs/GIS_PLATFORM_ARCHITECTURE.md`.

Fuori scope immediato:

- riscrittura `/catasto/gis`;
- introduzione runtime QGIS Server o GeoServer;
- uso shapefile NAS come sorgente viva;
- editing diretto dei layer ufficiali senza workflow/audit.

## Principi Di Implementazione

- PostGIS e la sorgente operativa ufficiale.
- NAS shapefile e solo export/backup versionato.
- QGIS Desktop resta client tecnico tramite PostGIS o futuri servizi OGC.
- Il modulo GIS governa catalogo, permessi, note, workflow, audit e export.
- I domini verticali, a partire da Catasto, mantengono la logica specialistica.
- Ogni file runtime nuovo o modificato deve restare al 100% di coverage.

## Fase 1 - Catalogo Governato Read-Only

Stato: implementata su branch `feature/gis-platform-catalog-m1`.

Obiettivo: rendere il catalogo GIS usabile senza introdurre nuove superfici di editing.

Backend:

- mantenere `/gis/layers` e `/gis/workspaces/{workspace}/layers` come sorgenti canonicali del catalogo;
- aggiungere filtri opzionali read-only per `workspace`, `domain_module`, `source_type`, `official_source`, `is_active`;
- aggiungere endpoint admin-safe per aggiornare solo metadata descrittivi del layer, senza toccare tabelle PostGIS;
- aggiungere endpoint per disattivare/riattivare layer catalogo, con audit.

API implementate:

- `GET /gis/layers?workspace=&domain_module=&source_type=&official_source=&is_active=`;
- `PATCH /gis/layers/{layer_id}/metadata`;
- `POST /gis/layers/{layer_id}/activate`;
- `POST /gis/layers/{layer_id}/deactivate`.

Regole implementate:

- i viewer continuano a vedere solo layer attivi e con `can_view`;
- gli admin vedono anche layer inattivi nel catalogo e possono filtrare per `is_active`;
- il patch metadata rifiuta campi critici come workspace, name, PostGIS table, source type e official source;
- ogni patch/toggle produce audit `layer.metadata_updated`, `layer.activated` o `layer.deactivated`.

Frontend:

- creare una pagina read-only `GIS Platform / Catalogo`;
- mostrare layer, workspace, source, Martin layer, metadata QGIS e permesso effettivo;
- non incorporare la mappa Catasto in questa fase;
- aggiungere link contestuale verso `/catasto/gis` solo per layer Catasto.

UI implementata:

- pagina `/gis/catalogo`;
- redirect `/gis` verso `/gis/catalogo`;
- voce separata `GIS Platform` nella navigazione;
- link a `/catasto/gis` solo come workspace dominio Catasto.

Test:

- API list/detail/filter;
- update metadata admin-only;
- audit su update/disable;
- frontend unit/smoke se la pagina viene introdotta.

Exit criteria:

- utenti autorizzati vedono i layer Catasto nel catalogo centrale;
- viewer resta read-only;
- nessun cambio comportamento su `/catasto/gis`.

## Fase 2 - Permessi Operativi Per Layer

Stato: implementata su branch `feature/gis-platform-permissions-m2`.

Obiettivo: rendere i permessi GIS amministrabili e verificabili.

Backend:

- completare gestione permessi per principal `role` e `user`;
- aggiungere endpoint delete/revoke permission;
- aggiungere audit per grant, update e revoke;
- aggiungere validazione principal role contro ruoli applicativi noti;
- definire policy di precedenza tra permessi role e user.

API implementate:

- `DELETE /gis/layers/{layer_id}/permissions/{permission_id}`;
- `POST /gis/layers/{layer_id}/permissions` ora distingue audit `permission.granted` e `permission.updated`;
- `DELETE` scrive audit `permission.revoked`.

Policy implementata:

- i ruoli validi sono quelli applicativi GAIA: `viewer`, `operator`, `reviewer`, `hr_manager`, `admin`, `super_admin`;
- se esiste un permesso `user` per il layer, quello prevale sul permesso `role`;
- se non esiste override `user`, viene usato il permesso `role`;
- gli admin applicativi mantengono privilegi GIS admin globali.

Frontend:

- pannello admin permessi layer;
- vista read-only dei permessi per non admin;
- affordance chiara per `viewer`, `annotator`, `editor`, `approver`, `admin`.

UI implementata:

- pannello `Gestisci permessi` su `/gis/catalogo` per layer con `can_manage`;
- grant/update per principal `role` e `user`;
- revoke permission dalla lista layer;
- utenti senza `can_manage` vedono solo affordance read-only del loro livello effettivo.

Test:

- revoca permesso;
- override user vs role;
- non-admin forbidden;
- audit completo.

Exit criteria:

- permessi gestibili senza accesso DB manuale;
- nessun editor ottiene approve/manage per errore;
- coverage 100% sui runtime toccati.

## Fase 3 - Annotazioni Governate

Stato: implementata su branch `feature/gis-platform-annotations-m3`.

Obiettivo: rendere le note GIS usabili senza contaminare i dati ufficiali.

Backend:

- estendere annotazioni con status lifecycle: `open`, `in_review`, `closed`, `rejected`;
- collegare allegati solo tramite riferimenti metadata `attachment_refs`;
- aggiungere update e transizioni di stato con audit;
- consentire query per layer, feature e status.

API implementate:

- `GET /gis/layers/{layer_id}/annotations?status=&feature_id=`;
- `POST /gis/layers/{layer_id}/annotations`;
- `PATCH /gis/layers/{layer_id}/annotations/{annotation_id}`;
- `POST /gis/layers/{layer_id}/annotations/{annotation_id}/in-review`;
- `POST /gis/layers/{layer_id}/annotations/{annotation_id}/close`;
- `POST /gis/layers/{layer_id}/annotations/{annotation_id}/reject`.

Regole implementate:

- `can_view` consente la lettura delle annotazioni del layer autorizzato;
- `can_annotate` consente create, update e passaggio a `in_review`;
- `can_approve` consente `closed` e `rejected`;
- annotazioni `closed` o `rejected` non sono piu modificabili;
- update vuoti, `title=null` e `body=null` sono rifiutati;
- ogni modifica scrive audit `annotation.created`, `annotation.updated`,
  `annotation.in_review`, `annotation.closed` o `annotation.rejected`.

Frontend:

- pannello annotazioni in `/gis/catalogo` per layer visibili;
- filtro note per `status` e `feature_id`;
- creazione note associate o meno a feature;
- modifica note non terminali;
- transizioni `in_review`, `closed`, `rejected` in base alle capability del layer.

UI implementata:

- bottone `Annotazioni` su ogni layer con `can_view`;
- form creazione/modifica visibile solo con `can_annotate`;
- comandi approvativi visibili solo con `can_approve`;
- fallback esplicito per annotazioni senza feature associata.

Test:

- create/list/update/status lifecycle;
- filtri `status` e `feature_id`;
- permessi `annotator` e `approver`;
- viewer senza annotate forbidden;
- blocchi su layer errato, annotazione inesistente e update terminale;
- audit;
- client e UI frontend con coverage 100% sui runtime toccati.

Exit criteria:

- note sempre in tabelle GAIA/PostGIS dedicate;
- nessuna scrittura negli shapefile;
- workflow note tracciabile da API, UI e audit;
- `/catasto/gis` resta separato dalla piattaforma `/gis`.

## Fase 4 - Change Request E Draft Editing

Obiettivo: permettere proposte di modifica senza aggiornare subito il layer ufficiale.

Backend:

- formalizzare payload change request per geometry/attribute/create/delete;
- aggiungere stati `submitted`, `needs_changes`, `approved`, `rejected`, `applied`;
- aggiungere endpoint reject/request-changes;
- aggiungere validazioni layer-specifiche pluggable senza duplicare logiche Catasto;
- preparare servizio apply astratto, inizialmente no-op per layer Catasto.

Frontend:

- elenco change request;
- dettaglio diff leggibile;
- azioni approver.

Test:

- editor submit;
- approver approve/reject;
- audit stato per stato;
- blocchi per permessi insufficienti.

Exit criteria:

- draft/change request pronto per layer generici;
- apply reale ancora opt-in per dominio/layer.

## Fase 5 - Export NAS Versionato

Obiettivo: trasformare il contratto export in job reale.

Backend:

- introdurre job export shapefile da PostGIS a staging locale;
- scrivere zip shapefile e manifest JSON;
- calcolare checksum SHA-256;
- pubblicare su NAS in path versionato atomico;
- salvare stato job in `gis_layer_exports`;
- aggiungere retry sicuro e failure reason.

Config:

- definire root NAS GIS dedicata, ad esempio `/volume1/Backups/GAIA/gis`;
- usare credenziali NAS gia gestite dal progetto o nuovo secret dedicato;
- documentare retention.

Test:

- unit test path/version/checksum;
- integration test con filesystem temporaneo;
- test NAS client mockato;
- audit export requested/completed/failed.

Exit criteria:

- export versionato ripetibile;
- shapefile NAS resta copia di sicurezza, non sorgente operativa.

## Fase 6 - QGIS Desktop Governance

Obiettivo: rendere QGIS sicuro come client tecnico.

Database:

- ruoli PostGIS read-only per layer pubblicati;
- eventuali ruoli edit controllati per layer non Catasto;
- viste dedicate per layer pubblicabili;
- policy di connessione e rotazione credenziali.

Documentazione:

- runbook QGIS Desktop;
- convenzioni naming workspace/layer;
- regole "non modificare shapefile NAS".

Exit criteria:

- utenti tecnici possono connettersi a PostGIS in read-only;
- eventuale editing e separato da apply ufficiale GAIA.

## Fase 7 - Valutazione OGC

Obiettivo: decidere se introdurre QGIS Server o GeoServer.

POC QGIS Server:

- riuso progetti/stili QGIS;
- WMS/WFS read-only;
- integrazione auth/proxy da valutare.

POC GeoServer:

- workspace multi-dominio;
- policy OGC piu granulari;
- WFS-T solo se compatibile con workflow GAIA.

Exit criteria:

- decision record con pro/contro, costi operativi, sicurezza e piano rollout;
- nessun runtime OGC introdotto senza decisione esplicita.

## Gate Tecnici

Per ogni fase:

- `git status --short` prima/dopo, senza includere file non correlati;
- test mirati backend/frontend;
- coverage 100% su runtime nuovi/modificati;
- Alembic single head;
- Graphify aggiornato con target dedicati;
- documentazione aggiornata prima del commit.

Comandi baseline GIS:

```bash
cd backend
.venv/bin/python -m pytest tests/test_gis_platform_api.py tests/test_bootstrap_admin.py tests/test_main_lifespan_scheduler.py --cov=app.modules.gis --cov=app.main --cov=app.api.router --cov=app.db.base --cov-report=term-missing --cov-fail-under=100 -q
.venv/bin/python -m pytest tests/test_app_metadata.py tests/test_alembic.py -q
.venv/bin/alembic heads
```

Graphify:

```bash
make graphify-backend
make graphify-frontend
make graphify-docs
```
