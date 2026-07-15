# GAIA GIS Platform Milestones

> Data: 2026-07-14.
> Documento operativo per pianificare e verificare il completamento incrementale
> della piattaforma GIS.

## M0 - Fondazione Backend

Stato: completato.

Deliverable:

- modulo `backend/app/modules/gis`;
- migration tabelle GIS;
- router `/gis`;
- catalogo layer;
- permessi layer;
- annotazioni;
- change request;
- export metadata;
- audit log;
- bootstrap Catasto PostGIS/Martin read-only.

Exit criteria:

- `/gis/layers` disponibile;
- Catasto registrato come workspace, senza sostituire `/catasto/gis`;
- default viewer read-only;
- coverage 100% sul perimetro GIS.

## M1 - Catalogo Operativo

Stato: completato.

Obiettivo:

- rendere il catalogo ispezionabile da UI e amministrabile in modo limitato.

Deliverable:

- filtri backend catalogo;
- update metadata admin-only;
- disattivazione/riattivazione layer;
- pagina frontend read-only catalogo GIS;
- link contestuale verso workspace dominio, ad esempio `/catasto/gis`.

Implementato:

- `GET /gis/layers` filtra per `workspace`, `domain_module`, `source_type`, `official_source`, `is_active`;
- `PATCH /gis/layers/{layer_id}/metadata` aggiorna solo metadata descrittivi e scrive audit;
- `POST /gis/layers/{layer_id}/activate` e `/deactivate` governano la visibilita catalogo;
- `/gis/catalogo` espone il catalogo read-only in frontend;
- `/catasto/gis` resta workspace operativo Catasto separato.

Exit criteria:

- utenti vedono layer autorizzati e metadata QGIS/PostGIS/Martin;
- admin puo aggiornare descrizioni/metadata non critici;
- nessuna modifica alle geometrie ufficiali.
- viewer vede solo layer attivi e autorizzati;
- admin puo filtrare e recuperare nel catalogo anche layer inattivi.

## M2 - Permessi Layer Completi

Stato: completato.

Obiettivo:

- rendere gestibile l'accesso per ruolo e utente.

Deliverable:

- revoke/delete permission;
- validazione ruoli;
- policy di precedenza role/user;
- audit completo grant/update/revoke;
- UI admin permessi.

Implementato:

- revoke permission con `DELETE /gis/layers/{layer_id}/permissions/{permission_id}`;
- validazione principal `role` contro i ruoli applicativi GAIA;
- audit separati `permission.granted`, `permission.updated`, `permission.revoked`;
- policy user-over-role: l'override `user` prevale sul permesso `role`;
- pannello permessi admin su `/gis/catalogo` per layer con `can_manage`.

Exit criteria:

- permessi verificabili da API e UI;
- viewer non puo annotare/editare;
- editor non puo approvare;
- approver non puo gestire permessi salvo `admin`.
- revoca e override utente sono testati con coverage 100% sui runtime toccati.

## M3 - Annotazioni Governate

Stato: completato.

Obiettivo:

- separare note/segnalazioni dal dato ufficiale.

Deliverable:

- lifecycle annotazioni `open`, `in_review`, `closed`, `rejected`;
- update annotazione e transizioni `in-review`, `close`, `reject`;
- query per status, feature e layer;
- allegati come riferimenti metadata `attachment_refs`;
- UI note per layer/feature in `/gis/catalogo`;
- audit per create, update e ogni cambio stato.

Implementato:

- `GET /gis/layers/{layer_id}/annotations` filtra per `status` e `feature_id`;
- `PATCH /gis/layers/{layer_id}/annotations/{annotation_id}` aggiorna title, body, geometry e attachment refs;
- `POST /gis/layers/{layer_id}/annotations/{annotation_id}/in-review` richiede `can_annotate`;
- `POST /gis/layers/{layer_id}/annotations/{annotation_id}/close` richiede `can_approve`;
- `POST /gis/layers/{layer_id}/annotations/{annotation_id}/reject` richiede `can_approve`;
- annotazioni `closed` e `rejected` sono terminali e non accettano update o
  ulteriori transizioni;
- pannello `Annotazioni` su `/gis/catalogo` con filtro, create/update e transizioni stato.

Exit criteria:

- nessuna nota scritta negli shapefile;
- audit per ogni cambio stato;
- annotator puo creare note, viewer solo leggere.
- approver puo chiudere o rigettare note;
- coverage 100% sui runtime backend e frontend toccati.

## M4 - Change Request Workflow

Stato: completato.

Obiettivo:

- introdurre draft editing prima di aggiornare layer ufficiali.

Deliverable:

- stati estesi change request;
- reject/request changes;
- update/resubmit draft;
- diff leggibile geometry/attribute/create/delete;
- validazioni pluggable per dominio;
- apply no-op sicuro per layer Catasto finche non esiste policy dominio.

Implementato:

- stati `submitted`, `needs_changes`, `approved`, `rejected`, `applied`;
- payload formalizzati per `attribute_update`, `geometry_update`,
  `feature_create`, `feature_delete`;
- `GET /gis/change-requests?status=&layer_id=`;
- `PATCH /gis/change-requests/{change_request_id}`;
- `POST /gis/change-requests/{change_request_id}/request-changes`;
- `POST /gis/change-requests/{change_request_id}/approve`;
- `POST /gis/change-requests/{change_request_id}/reject`;
- `POST /gis/change-requests/{change_request_id}/apply`;
- validator pluggable registrabili per layer, dominio o workspace;
- apply Catasto no-op con audit `change_request.applied`;
- pannello `Change request` su `/gis/catalogo` con form JSON, diff payload e
  azioni approver.

Exit criteria:

- editor propone;
- approver valida o respinge;
- nessun apply automatico su Catasto senza accordo dominio.
- coverage 100% sui runtime backend e frontend toccati.

## M5 - Export NAS Reale

Stato: completato.

Obiettivo:

- produrre shapefile versionati da PostGIS verso NAS.

Deliverable:

- job export;
- zip shapefile;
- manifest JSON;
- checksum;
- pubblicazione atomica su NAS;
- stato export e audit.

Implementato:

- runner `app.modules.gis.exporter` riusabile da API o futuro worker;
- generazione ZIP shapefile con `.shp`, `.shx`, `.dbf`, `.cpg` e
  `manifest.json`;
- manifest con layer, sorgente PostGIS, SRID, geometry type, field mapping e
  row count;
- publish atomico tramite file temporaneo e replace sul path finale;
- checksum SHA-256 calcolato sullo ZIP pubblicato;
- stati `completed` e `failed` su `gis_layer_exports`;
- audit `export.requested`, `export.completed`, `export.failed`;
- failure reason salvata in `metadata.error`.

Exit criteria:

- export ripetibile e versionato;
- path NAS e checksum salvati;
- NAS non diventa sorgente operativa.
- coverage 100% sui runtime backend toccati.

## M6 - Governance QGIS Desktop

Stato: completato.

Obiettivo:

- standardizzare l'uso quotidiano di QGIS.

Deliverable:

- ruoli DB read-only;
- eventuali profili edit controllati;
- runbook QGIS;
- convenzioni layer/workspace;
- istruzioni per connessione PostGIS.

Implementato:

- endpoint admin-only `GET /gis/qgis/governance`;
- generatore SQL deterministico da `gis_layers`;
- schema `gis_qgis` e ruoli gruppo NOLOGIN `gaia_gis_qgis_reader`,
  `gaia_gis_qgis_editor`, `gaia_gis_qgis_admin`;
- view read-only per layer PostGIS attivi;
- Catasto sempre read-only;
- grant edit solo per layer non Catasto con opt-in metadata
  `qgis.editable=true` e `qgis.edit_policy=controlled`;
- runbook `docs/GIS_QGIS_DESKTOP_RUNBOOK.md`.

Exit criteria:

- QGIS usa PostGIS o servizi OGC;
- shapefile NAS non vengono editati come dato vivo;
- credenziali e privilegi sono documentati.
- coverage 100% sui runtime backend toccati.

## M7 - Decisione OGC

Stato: completato.

Obiettivo:

- scegliere se introdurre QGIS Server o GeoServer.

Deliverable:

- POC QGIS Server;
- POC GeoServer;
- decision record;
- piano sicurezza/proxy/auth;
- piano rollout o decisione di non introdurre OGC server.

Implementato:

- decision record `docs/GIS_OGC_DECISION_RECORD.md`;
- confronto QGIS Server vs GeoServer;
- decisione di non introdurre runtime OGC in produzione di default;
- raccomandazione POC QGIS Server read-only se serve WMS/WFS;
- GeoServer mantenuto come opzione per workspace/sicurezza OGC multi-dominio;
- piano sicurezza/proxy/auth;
- piano rollout se il POC passa;
- esclusione WFS-T/write OGC dalla baseline.

Exit criteria:

- scelta motivata;
- costi operativi e rischi documentati;
- nessun server OGC introdotto senza decisione.

## M8 - Integrazione Multi-Dominio

Stato: implementata su branch `feature/gis-platform-multidomain-m8`.

Obiettivo:

- estendere il catalogo oltre Catasto.

Deliverable:

- onboarding Riordino come primo dominio non Catasto;
- workspace `riordino` e naming `riordino_gis_links`;
- registry non geometrico con `source_type=domain_registry`;
- metadata read-only, `export.shapefile=false`, `qgis.mode=not_published`;
- bootstrap piattaforma `ensure_gis_platform_catalog`;
- guard export shapefile limitato a layer PostGIS geometrici.

Implementato:

- registrazione idempotente `riordino_gis_links` nel catalogo `/gis`;
- permesso role `viewer` read-only riparato a ogni bootstrap;
- filtri `/gis/layers?workspace=riordino&domain_module=riordino`;
- esclusione da `/gis/qgis/governance`;
- errore `422` su export shapefile dei registry non geometrici;
- separazione mantenuta tra CRUD Riordino e governance GIS Platform.

Exit criteria:

- almeno un dominio non Catasto registrato;
- confini dominio/GIS rispettati;
- permessi e audit coerenti.

## M9 - Dashboard Stato Catalogo

Stato: implementata su branch `feature/gis-platform-catalog-health-m9`.

Obiettivo:

- rendere osservabile lo stato del catalogo GIS e la qualita delle policy layer.

Deliverable:

- endpoint `GET /gis/catalog/dashboard`;
- metriche per layer totali, attivi, inattivi, workspace, source type e
  official source;
- conteggi layer pubblicabili QGIS e layer esportabili shapefile;
- health issue deterministiche su permessi, PostGIS, registry dominio e policy
  QGIS edit;
- pannello UI `Health catalogo GIS` in `/gis/catalogo`.

Implementato:

- dashboard filtrato dai permessi dell'utente: admin vede tutto, utenti non
  admin vedono solo layer attivi con `can_view`;
- stato aggregato `ok`, `warning`, `critical`;
- riepilogo per workspace con issue count;
- issue `no_view_permission`, `postgis_table_missing`,
  `geometry_column_missing`, `qgis_edit_policy_missing`,
  `registry_qgis_policy_missing`, `registry_export_policy_missing`;
- test backend e frontend con coverage 100% sui runtime toccati.

Exit criteria:

- stato catalogo visibile da API e UI;
- warning/critical riproducibili senza interrogare sorgenti esterne;
- permessi rispettati nel dashboard;
- coverage 100% sui runtime backend/frontend toccati.

## M10 - Scheduling E Retention Export NAS

Stato: implementata su branch `feature/gis-platform-export-schedule-m10`.

Obiettivo:

- automatizzare gli export shapefile dei layer PostGIS governati e mantenere
  una retention controllata su NAS.

Deliverable:

- scheduler APScheduler opzionale `gis_shapefile_export_schedule`;
- settings `GIS_EXPORT_SCHEDULER_*`, `GIS_EXPORT_RETENTION_COUNT`,
  `GIS_EXPORT_MAX_LAYERS_PER_RUN`;
- runner `run_scheduled_shapefile_exports`;
- audit `export.scheduled` e `export.retention_applied`;
- retention per layer sui soli export `trigger=scheduled`;
- ultimi export esposti nel dashboard catalogo e nella UI `/gis/catalogo`.

Implementato:

- scheduler disabilitato di default;
- export schedulato solo per layer attivi, PostGIS, geometrici ed exportable;
- riuso della pipeline M5 per publish atomico, checksum e manifest;
- prune dei vecchi ZIP schedulati senza toccare export manuali;
- dashboard `latest_exports` con stato, versione, trigger e path NAS;
- test backend/frontend con coverage 100% sui runtime toccati.

Exit criteria:

- job registrabile e sicuro con opt-in esplicito;
- export schedulati auditati;
- retention idempotente e limitata agli export scheduled;
- ultimo export visibile da API e UI;
- coverage 100% sui runtime backend/frontend toccati.

## M11 - Accesso Modulo GIS Nativo

Stato: completato.

Obiettivo: rendere `GIS Platform` un modulo applicativo nativo, separato da
Catasto anche nella gestione utenti.

Deliverable:

- colonna `application_users.module_gis`;
- `enabled_modules` include `gis` per super admin e utenti abilitati;
- migration con backfill `module_gis=true` per utenti legacy con
  `module_catasto=true`;
- API auth/admin users espongono `module_gis`;
- pagina `Utenti GAIA` permette di abilitare/disabilitare `GIS Platform`;
- frontend home/sidebar/protected pages usano il modulo `gis` in modo nativo.

Exit criteria:

- un utente con `module_gis=true` vede `GIS Platform` senza `module_catasto`;
- un utente con solo Catasto non passa piu il gating frontend del modulo GIS,
  salvo backfill migration gia applicato;
- `/catasto/gis` resta workspace di dominio separato.

## M12 - UX Import Shapefile E QGIS Desktop

Stato: completato su branch `feature/gis-platform-ux-import-qgis-m12`.

Obiettivo:

- rendere `/gis/catalogo` comprensibile anche a utenti non tecnici e rispondere
  esplicitamente ai percorsi operativi piu richiesti: import shapefile e apertura
  dei layer in QGIS Desktop.

Deliverable:

- hero catalogo piu leggibile e visivamente distinta;
- schede guida su layer, import shapefile, QGIS Desktop e governance;
- spiegazione di `workspace`, `domain_module`, `source_type`,
  `official_source` e permesso effettivo;
- scheda `Import shapefile` con ZIP richiesto, validazione, staging PostGIS,
  anteprima e pubblicazione governata;
- scheda `QGIS Desktop in un colpo` con progetto `.qgz` unico, connessione
  PostGIS governata e opzione pacchetto offline;
- aggiornamento documentazione operativa.

Implementato:

- UI `/gis/catalogo` con onboarding, glossario e fact card descrittive;
- CTA import e QGIS lasciate informative/disabilitate finche non esistono
  endpoint backend dedicati;
- test frontend mirato con coverage 100% su `src/app/gis/catalogo/page.tsx`;
- runbook import shapefile e ampliamento runbook QGIS Desktop.

Exit criteria:

- un utente capisce che un layer e un dataset geografico governato;
- gli shapefile sono descritti come input da validare e importare in staging,
  non come sorgente viva;
- QGIS Desktop usa PostGIS e progetti controllati, non copie manuali del NAS;
- nessuna regressione su permessi, annotazioni, change request e health
  dashboard del catalogo;
- coverage 100% sul runtime frontend modificato.

## M13 - Import Shapefile Governato

Stato: completato su branch `feature/gis-platform-shapefile-import-m13`.

Obiettivo:

- rendere reale il primo tratto runtime dell'import shapefile da UI, mantenendo
  staging non distruttivo e nessuna pubblicazione automatica sui layer ufficiali.

Deliverable:

- migration `20260714_1700_gis_shapefile_imports`;
- tabella `gis_shapefile_imports`;
- endpoint admin-only `POST /gis/imports/shapefile`;
- endpoint `GET /gis/imports/{import_id}`;
- endpoint admin-only `POST /gis/imports/{import_id}/validate`;
- endpoint admin-only `POST /gis/imports/{import_id}/reject`;
- validazione ZIP sicura, componenti shapefile obbligatori, SRID esplicito,
  encoding, feature count, geometry type, bbox e campi DBF;
- staging table non distruttiva per anteprima tecnica;
- audit upload, validate e reject.
- form `/gis/catalogo` collegato agli endpoint M13;
- visualizzazione stato import, staging table, feature count, geometry type e
  checksum;
- azione reject import da UI.

Implementato:

- upload ZIP multipart con `workspace`, `target_layer_name`,
  `target_layer_title`, `source_srid`, `domain_module`, `official_source` ed
  `encoding`;
- blocco path traversal, ZIP non validi, shapefile multipli, componenti mancanti,
  feature count nullo e shapefile corrotti;
- staging table `gis_staging.import_<uuid>` su PostgreSQL e fallback
  `gis_staging_import_<uuid>` su SQLite/test;
- reject con cleanup staging;
- dashboard `latest_exports` ordinato in modo stabile su `completed_at`;
- client/frontend import shapefile su `/gis/catalogo`;
- coverage 100% su runtime backend e frontend toccati.

Exit criteria:

- nessuno shapefile viene pubblicato come dato ufficiale in automatico;
- import e staging sono tracciati e auditati;
- il reject rimuove lo staging;
- la UI permette upload/validazione e reject;
- Catasto non viene toccato;
- Alembic ha una sola head;
- coverage 100% sui runtime backend/frontend modificati.
