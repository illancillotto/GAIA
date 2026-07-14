# GAIA GIS Platform Implementation Plan

> Data: 2026-07-14.
> Scope: piattaforma GIS trasversale GAIA, non refactor del GIS Catasto.

## Stato Corrente

M12 e completata su branch `feature/gis-platform-ux-import-qgis-m12`: il modulo
GIS e accessibile come modulo nativo, il catalogo `/gis/catalogo` e integrato
nella navigazione e la pagina spiega import shapefile e QGIS Desktop senza
attivare endpoint non ancora implementati.

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
- voce separata `GIS Platform` nella navigazione, nella home e nel module
  switcher/sidebar come modulo frontend `gis`;
- flag backend/frontend nativo `module_gis`, gestibile da `Utenti GAIA`;
- migration M11 con backfill `module_gis=true` per profili legacy gia abilitati
  al Catasto;
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

Stato: implementata su branch `feature/gis-platform-change-requests-m4`.

Obiettivo: permettere proposte di modifica senza aggiornare subito il layer ufficiale.

Backend:

- formalizzare payload change request per geometry/attribute/create/delete;
- aggiungere stati `submitted`, `needs_changes`, `approved`, `rejected`, `applied`;
- aggiungere endpoint reject/request-changes;
- aggiungere validazioni layer-specifiche pluggable senza duplicare logiche Catasto;
- preparare servizio apply astratto, inizialmente no-op per layer Catasto.

API implementate:

- `GET /gis/change-requests?status=&layer_id=`;
- `POST /gis/layers/{layer_id}/change-requests`;
- `PATCH /gis/change-requests/{change_request_id}`;
- `POST /gis/change-requests/{change_request_id}/request-changes`;
- `POST /gis/change-requests/{change_request_id}/approve`;
- `POST /gis/change-requests/{change_request_id}/reject`;
- `POST /gis/change-requests/{change_request_id}/apply`.

Regole implementate:

- `attribute_update` richiede `feature_id` e `payload.after`;
- `geometry_update` richiede `feature_id` e `payload.geometry`;
- `feature_create` richiede `payload.geometry` e `payload.properties`;
- `feature_delete` richiede `feature_id` e `payload.before`;
- `can_edit` consente submit e update delle richieste non terminali;
- `can_approve` consente request-changes, approve, reject e apply;
- `rejected` e `applied` sono terminali;
- `approved` blocca ulteriori update editor;
- apply Catasto resta no-op auditato finche il dominio non definisce una policy
  di scrittura ufficiale.

Frontend:

- elenco change request;
- dettaglio diff leggibile;
- azioni approver.

UI implementata:

- pannello `Change request` su `/gis/catalogo` per layer con `can_view`;
- form JSON per submit/update visibile solo con `can_edit`;
- filtro per status e layer;
- diff payload leggibile per attribute/geometry/create/delete;
- note revisione e azioni `request-changes`, `approve`, `reject`, `apply no-op`
  visibili solo con `can_approve`.

Test:

- editor submit;
- approver approve/reject;
- request changes, update/resubmit e apply no-op;
- validazione payload per tutti i tipi;
- validator pluggable;
- audit stato per stato;
- blocchi per permessi insufficienti.

Exit criteria:

- draft/change request pronto per layer generici;
- apply reale ancora opt-in per dominio/layer.
- `/catasto/gis` resta separato e non riceve scritture ufficiali da M4.

## Fase 5 - Export NAS Versionato

Stato: implementata su branch `feature/gis-platform-export-m5`.

Obiettivo: trasformare il contratto export in job reale.

Backend:

- introdurre job export shapefile da PostGIS a staging locale;
- scrivere zip shapefile e manifest JSON;
- calcolare checksum SHA-256;
- pubblicare su NAS in path versionato atomico;
- salvare stato job in `gis_layer_exports`;
- aggiungere retry sicuro e failure reason.

API implementata:

- `POST /gis/layers/{layer_id}/export-shapefile`.

Regole implementate:

- il runner legge il layer da PostGIS tramite catalogo `postgis_schema`,
  `postgis_table` e `geometry_column`;
- in test SQLite la stessa pipeline usa geometrie GeoJSON per coprire il runner
  senza dipendere da PostGIS reale;
- lo ZIP contiene `.shp`, `.shx`, `.dbf`, `.cpg` e `manifest.json`;
- il manifest include layer, workspace, sorgente, SRID, geometry type, mapping
  campi DBF, metadata richiesta e conteggio record;
- la pubblicazione avviene scrivendo uno ZIP temporaneo nella directory finale e
  poi usando replace atomico sul path NAS/local;
- il checksum SHA-256 viene calcolato dal file ZIP pubblicato;
- `gis_layer_exports.status` passa a `completed` o `failed`;
- `metadata_json.error` conserva tipo e messaggio dell'errore in caso di
  fallimento.

Config:

- definire root NAS GIS dedicata, ad esempio `/volume1/Backups/GAIA/gis`;
- usare credenziali NAS gia gestite dal progetto o nuovo secret dedicato;
- documentare retention.

Test:

- unit test path/version/checksum;
- integration test con filesystem temporaneo;
- test export ZIP con tabella sorgente SQLite e geometria GeoJSON;
- test fallimento su tabella sorgente mancante;
- audit export requested/completed/failed.

Exit criteria:

- export versionato ripetibile;
- shapefile NAS resta copia di sicurezza, non sorgente operativa.
- coverage 100% sui runtime backend toccati.

## Fase 6 - QGIS Desktop Governance

Stato: implementata su branch `feature/gis-platform-qgis-governance-m6`.

Obiettivo: rendere QGIS sicuro come client tecnico.

Database:

- ruoli PostGIS read-only per layer pubblicati;
- eventuali ruoli edit controllati per layer non Catasto;
- viste dedicate per layer pubblicabili;
- policy di connessione e rotazione credenziali.

API implementata:

- `GET /gis/qgis/governance`.

Regole implementate:

- endpoint admin-only, senza applicazione automatica dei grant;
- schema pubblicabile `gis_qgis`;
- ruoli gruppo NOLOGIN `gaia_gis_qgis_reader`, `gaia_gis_qgis_editor`,
  `gaia_gis_qgis_admin`;
- view read-only per layer PostGIS attivi;
- Catasto sempre read-only;
- grant edit solo per layer non Catasto con metadata `qgis.editable=true` e
  `qgis.edit_policy=controlled`;
- SQL completo restituito per revisione/esecuzione manuale da operatore DB.

Documentazione:

- runbook QGIS Desktop;
- convenzioni naming workspace/layer;
- regole "non modificare shapefile NAS".
- `docs/GIS_QGIS_DESKTOP_RUNBOOK.md`.

Exit criteria:

- utenti tecnici possono connettersi a PostGIS in read-only;
- eventuale editing e separato da apply ufficiale GAIA;
- coverage 100% sui runtime backend toccati.

## Fase 7 - Valutazione OGC

Stato: implementata su branch `feature/gis-platform-ogc-decision-m7`.

Obiettivo: decidere se introdurre QGIS Server o GeoServer.

POC QGIS Server:

- riuso progetti/stili QGIS;
- WMS/WFS read-only;
- integrazione auth/proxy da valutare.

POC GeoServer:

- workspace multi-dominio;
- policy OGC piu granulari;
- WFS-T solo se compatibile con workflow GAIA.

Decisione implementata:

- nessun server OGC introdotto nel runtime produzione di default;
- baseline confermata: PostGIS + Martin + API GAIA;
- POC raccomandato: QGIS Server read-only, se serve pubblicazione OGC;
- GeoServer resta opzione per governance OGC multi-dominio piu granulare;
- WFS-T e operazioni write escluse dalla baseline;
- decision record in `docs/GIS_OGC_DECISION_RECORD.md`.

Exit criteria:

- decision record con pro/contro, costi operativi, sicurezza e piano rollout;
- nessun runtime OGC introdotto senza decisione esplicita.

## Fase 8 - Integrazione Multi-Dominio

Stato: implementata su branch `feature/gis-platform-multidomain-m8`.

Obiettivo: provare il catalogo GIS come piattaforma trasversale oltre Catasto,
senza spostare CRUD o logiche del dominio proprietario.

Dominio onboardato:

- `riordino`, tramite registry `riordino_gis_links`;
- route dominio proprietaria: `/riordino/practices/{practice_id}/gis-links`;
- catalogo piattaforma: `/gis/layers?workspace=riordino&domain_module=riordino`.

Regole implementate:

- bootstrap unico `ensure_gis_platform_catalog`;
- Catasto resta workspace geometrico PostGIS/Martin read-only;
- Riordino e registrato come `source_type=domain_registry`;
- metadata Riordino: `read_only=true`, `qgis.mode=not_published`,
  `export.shapefile=false`;
- default permission role `viewer` read-only;
- export shapefile bloccato per registry o layer non geometrici;
- QGIS governance continua a pubblicare solo layer `source_type=postgis`.

Exit criteria:

- almeno un dominio non Catasto registrato nel catalogo;
- confini dominio/GIS rispettati;
- permessi read-only idempotenti e riparabili;
- coverage 100% sui runtime backend toccati.

## Fase 9 - Dashboard Stato Catalogo

Stato: implementata su branch `feature/gis-platform-catalog-health-m9`.

Obiettivo: fornire una vista sintetica e riproducibile dello stato catalogo GIS,
senza dipendere da probe runtime verso PostGIS, Martin, QGIS o NAS.

API implementata:

- `GET /gis/catalog/dashboard`.

Metriche:

- totale layer visibili;
- layer attivi/inattivi;
- numero workspace;
- distribuzione `source_type` e `official_source`;
- layer pubblicabili in QGIS governance;
- layer esportabili come shapefile;
- stato aggregato `ok`, `warning`, `critical`;
- riepilogo per workspace.

Health issue implementate:

- `no_view_permission`: layer attivo senza permessi di visualizzazione;
- `postgis_table_missing`: layer PostGIS senza tabella;
- `geometry_column_missing`: layer PostGIS senza colonna geometria;
- `qgis_edit_policy_missing`: opt-in edit QGIS senza policy `controlled`;
- `registry_qgis_policy_missing`: registry dominio non marcato `not_published`;
- `registry_export_policy_missing`: registry dominio senza
  `export.shapefile=false`.

Regole di sicurezza:

- admin applicativi vedono tutto il catalogo;
- utenti non admin vedono solo layer attivi con `can_view`;
- la UI `/gis/catalogo` mostra il pannello `Health catalogo GIS` con metriche,
  issue principali e stato per workspace.

Exit criteria:

- dashboard disponibile da API e UI;
- warning/critical calcolati in modo deterministico;
- coverage 100% sui runtime backend/frontend toccati.

## Fase 10 - Scheduling E Retention Export NAS

Stato: implementata su branch `feature/gis-platform-export-schedule-m10`.

Obiettivo: rendere operativo l'export NAS periodico dei layer GIS senza
affidarsi a esecuzioni manuali, mantenendo retention controllata e auditabile.

Configurazione:

- `GIS_EXPORT_SCHEDULER_ENABLED`, default `false`;
- `GIS_EXPORT_SCHEDULER_CRON`, default `30 2 * * *`;
- `GIS_EXPORT_SCHEDULER_TIMEZONE`, default `Europe/Rome`;
- `GIS_EXPORT_RETENTION_COUNT`, default `5`;
- `GIS_EXPORT_MAX_LAYERS_PER_RUN`, default `50`.

Runtime:

- scheduler APScheduler `gis_shapefile_export_schedule`;
- wrapper con consumo sicuro di `get_db`;
- runner `run_scheduled_shapefile_exports`;
- selezione layer attivi, `source_type=postgis`, geometrici ed exportable;
- version label `scheduled-YYYYMMDDTHHMMSSZ`;
- metadata export `trigger=scheduled`.

Retention:

- applicata per layer;
- mantiene gli ultimi `GIS_EXPORT_RETENTION_COUNT` export completati scheduled;
- non elimina export manuali;
- prova a cancellare il file ZIP dal path NAS/local;
- scrive audit `export.retention_applied` per ogni record pruned.

Dashboard/UI:

- `GET /gis/catalog/dashboard` espone `latest_exports`;
- `/gis/catalogo` mostra ultimi export con layer, versione, stato e trigger.

Exit criteria:

- job schedulato opt-in;
- export e retention auditati;
- ultimo export visibile da API e UI;
- coverage 100% sui runtime backend/frontend toccati.

## Fase 11 - Accesso Modulo GIS Nativo

Stato: implementata su branch `feature/gis-platform-native-module-m11`.

Obiettivo: separare il modulo `GIS Platform` dal Catasto anche nel gating
applicativo e nella gestione utenti.

Runtime implementato:

- migration `20260714_1100_add_gis_module_flag`;
- colonna `application_users.module_gis`;
- backfill `module_gis=true` per utenti legacy gia abilitati a Catasto;
- `enabled_modules` include `gis` per super admin e utenti abilitati;
- API auth/admin users espongono il flag `module_gis`;
- home, sidebar/module switcher e pagina `Utenti GAIA` usano `GIS Platform`
  come modulo autonomo.

Exit criteria:

- utente con `module_gis=true` accede a `/gis` senza dipendere da
  `module_catasto`;
- utente con solo Catasto non abilita automaticamente il modulo GIS dopo il
  backfill iniziale;
- `/catasto/gis` resta workspace dominio separato.

## Fase 12 - UX Import Shapefile E QGIS Desktop

Stato: implementata su branch `feature/gis-platform-ux-import-qgis-m12`.

Obiettivo: rendere il catalogo GIS comprensibile e operativo per utenti che
devono importare shapefile o aprire i layer in QGIS Desktop.

Frontend implementato:

- hero e onboarding della pagina `/gis/catalogo`;
- schede guida per catalogo layer, import shapefile, QGIS Desktop e governance;
- spiegazioni su `workspace`, `domain_module`, `source_type`,
  `official_source` e permesso effettivo;
- scheda `Import shapefile` con componenti ZIP `.shp`, `.shx`, `.dbf`, `.prj`;
- pipeline descritta: validazione, staging PostGIS, anteprima, scelta
  workspace/dominio e pubblicazione catalogo;
- scheda `QGIS Desktop in un colpo` con progetto `.qgz` unico e pacchetto
  offline come eccezione;
- CTA informative/disabilitate finche non vengono implementati endpoint backend
  per upload/import e generazione progetto QGIS.

Backend futuro:

- `POST /gis/imports/shapefile` per caricare ZIP in staging;
- validatore asincrono geometry/SRID/encoding/campi/feature count;
- preview non distruttiva dello staging;
- publish governato nel catalogo o creazione change request;
- endpoint progetto QGIS per generare/scaricare `.qgz` filtrato dai layer
  visibili e dai permessi utente.

Exit criteria:

- il catalogo spiega cosa sono layer, workspace, source e permessi;
- gli utenti vedono chiaramente come verra gestito l'import shapefile;
- il percorso QGIS chiarisce che PostGIS resta sorgente ufficiale;
- nessuna falsa promessa di upload/download attivo senza endpoint reali;
- coverage 100% su `frontend/src/app/gis/catalogo/page.tsx`.

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
