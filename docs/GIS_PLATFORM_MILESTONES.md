# GAIA GIS Platform Milestones

> Data: 2026-07-15.
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

## M14 - Publish Import Validato

Stato: completato su branch `feature/gis-platform-shapefile-publish-m14`.

Obiettivo:

- rendere operativo il publish governato degli import shapefile validati nel
  catalogo GIS, senza promuoverli a dato ufficiale di dominio e senza bypassare
  Catasto o altri workflow verticali.

Deliverable:

- migration `20260715_0900_gis_shapefile_import_publish`;
- campi `published_layer_id` e `published_at` su `gis_shapefile_imports`;
- status import `published`;
- endpoint admin-only `POST /gis/imports/{import_id}/publish`;
- creazione layer catalogo da import validato con `source_type=postgis_staging`;
- permesso default `viewer` read-only sul layer creato;
- metadata di sicurezza `qgis.mode=not_published`, `qgis.editable=false`,
  `tiles.published=false` ed `export.shapefile=false`;
- audit `shapefile_import.published` e
  `layer.created_from_shapefile_import`;
- UI `/gis/catalogo` con pulsante `Pubblica nel catalogo`, refresh catalogo e
  visualizzazione del layer creato.

Implementato:

- publish consentito solo per import in stato `validated`;
- publish idempotente se l'import e gia `published`;
- errore `409` per import rigettati, non validati o target catalogo gia
  esistente;
- reject bloccato dopo publish;
- validate resta idempotente anche su import gia pubblicati;
- i layer pubblicati restano staging read-only, non QGIS-publishable e non
  esportabili come shapefile;
- coverage 100% su backend GIS/main e runtime frontend modificati.

Exit criteria:

- un import validato puo creare un layer catalogo consultabile dai viewer;
- il layer creato non diventa fonte ufficiale di dominio;
- non viene modificato `/catasto/gis`;
- conflitti target e race di integrita tornano `409`;
- Alembic ha una sola head;
- coverage 100% sui runtime backend/frontend modificati.

## M15 - Preview Staging Import

Stato: completato su branch `feature/gis-platform-shapefile-preview-m15`.

Obiettivo:

- permettere all'operatore di ispezionare un campione dello staging shapefile
  prima o dopo il publish catalogo, senza scrivere su layer ufficiali e senza
  usare QGIS/NAS come area di verifica manuale.

Deliverable:

- endpoint read-only `GET /gis/imports/{import_id}/preview`;
- query param `limit` e `offset` con limiti API;
- response con `feature_seq`, attributi DBF, geometria GeoJSON testuale,
  geometry type, SRID, bbox, campi, contatori e `has_more`;
- blocco `409` per import non validati/rejected o staging table mancante;
- client frontend `previewGisShapefileImport`;
- UI `/gis/catalogo` con pulsante `Vedi anteprima staging`;
- pannello preview con campione attributi/geometria e gestione errori dedicata.

Implementato:

- preview consentita per import `validated` e `published`;
- accesso coerente con lettura import: admin GIS o uploader autorizzato;
- nessuna modifica allo staging durante la preview;
- reset della preview dopo reject;
- coverage 100% su backend GIS/main e runtime frontend modificati.

Exit criteria:

- un import validato mostra almeno un campione leggibile di attributi e
  geometria;
- viewer non autorizzati non leggono preview di import altrui;
- preview di staging rimosso torna `409`;
- Catasto non viene toccato;
- nessuna nuova migration richiesta;
- coverage 100% sui runtime backend/frontend modificati.

## M16 - Progetto QGIS Unico

Stato: completato su branch `feature/gis-platform-m16-m19`.

Obiettivo:

- permettere all'utente di scaricare in un unico colpo un progetto QGIS
  governato, filtrato dai permessi e senza includere staging o registry non
  pubblicabili.

Deliverable:

- endpoint `GET /gis/qgis/project`;
- archivio `.qgz` con `gaia-gis-platform.qgs`, `manifest.json` e
  `README_QGIS.txt`;
- filtro runtime su layer attivi, visibili, `source_type=postgis` e
  `qgis.mode != not_published`;
- esclusione di layer `postgis_staging`, registry applicativi e layer senza
  geometria configurata;
- client frontend `downloadGisQgisProject`;
- UI `/gis/catalogo` con CTA reale `Scarica progetto QGIS`, stato di download,
  errore governato e spiegazione per utenti poco digitali.

Implementato:

- generazione XML QGIS con gruppi per workspace e datasource PostGIS tramite
  servizio client `gaia_gis`;
- manifest deterministico con policy di inclusione/esclusione;
- `409` quando l'utente non ha layer QGIS pubblicabili;
- download browser `.qgz` da catalogo;
- coverage 100% su backend GIS/main e runtime frontend modificati.

Exit criteria:

- viewer scarica solo layer visibili e pubblicabili;
- staging import shapefile pubblicati nel catalogo non entrano nel progetto;
- registry dominio non entrano nel progetto;
- UI spiega cosa fare sul PC QGIS;
- nessuna nuova migration richiesta;
- coverage 100% sui runtime backend/frontend modificati.

## M17 - Change Request Da Import Shapefile

Stato: completato su branch `feature/gis-platform-m16-m19`.

Obiettivo:

- quando uno shapefile impatta un layer ufficiale esistente, creare change
  request governate invece di pubblicare o sovrascrivere dati ufficiali.

Deliverable:

- schema `GisShapefileImportChangeRequestCreate`;
- schema `GisShapefileImportChangeRequestResponse`;
- endpoint `POST /gis/imports/{import_id}/change-requests`;
- creazione batch di change request `feature_create` da staging import;
- deduplica per `import_id` + `feature_seq`;
- blocco target non PostGIS o senza geometria;
- UI `/gis/catalogo` con pannello `Impatta un layer ufficiale?`, selezione
  layer target, batch/offset e motivazione;
- client frontend `createGisShapefileImportChangeRequests`.

Implementato:

- import accessibile solo ad admin GIS o uploader autorizzato;
- target richiede `can_edit`;
- import deve essere `validated` o `published`;
- payload change request contiene `geometry`, `properties` e `source_import`;
- feature senza geometria vengono saltate e conteggiate;
- audit `change_request.submitted` per ogni richiesta nuova;
- nessuna modifica al layer ufficiale durante la creazione;
- coverage 100% su backend GIS/main e runtime frontend modificati.

Exit criteria:

- shapefile che aggiorna dati ufficiali passa da approvazione change request;
- publish staging non sostituisce dati ufficiali;
- duplicati sullo stesso import/feature non vengono ricreati;
- UI comprensibile per utenti poco digitali;
- nessuna nuova migration richiesta;
- coverage 100% sui runtime backend/frontend modificati.

## M18 - Onboarding Geometrico Non Catasto

Stato: completato su branch `feature/gis-platform-m16-m19`.

Obiettivo:

- registrare un primo dominio geometrico non Catasto con opt-in QGIS controlled
  edit, mantenendo separati catalogo GIS e policy del dominio.

Deliverable:

- definizione bootstrap `NETWORK_GIS_LAYER_DEFINITIONS`;
- workspace `rete`, domain module `network`;
- layer PostGIS `rete_condotte`;
- metadata `qgis.mode=controlled_edit`, `qgis.editable=true`,
  `qgis.edit_policy=controlled`;
- permesso default `viewer` read-only;
- permesso `operator` a livello GIS `editor`;
- inclusione in QGIS governance con grant editor controllato;
- inclusione in dashboard/export shapefile come layer geometrico PostGIS.

Implementato:

- bootstrap idempotente `ensure_network_gis_catalog`;
- `ensure_gis_platform_catalog` ora registra Catasto, Riordino e Rete;
- health dashboard resta `ok` per il layer Rete grazie a policy controlled;
- QGIS governance genera `GRANT SELECT, INSERT, UPDATE, DELETE` sul target
  `network.rete_condotte` per `gaia_gis_qgis_editor`;
- coverage 100% su backend GIS/main.

Exit criteria:

- un dominio non Catasto ha un layer geometrico operativo nel catalogo GIS;
- viewer vede il layer read-only;
- operator riceve capability `editor`;
- Catasto resta read-only;
- registry Riordino resta non QGIS/non export;
- nessuna nuova migration richiesta;
- coverage 100% sui runtime backend modificati.

## M19 - POC OGC Read-Only

Stato: completato su branch `feature/gis-platform-m16-m19`.

Obiettivo:

- preparare un POC QGIS Server read-only senza introdurre runtime OGC di
  produzione e senza abilitare WFS-T.

Deliverable:

- schema `GisOgcPocResponse`;
- endpoint `GET /gis/ogc/poc`;
- elenco layer visibili e pubblicabili come WMS/WFS read-only;
- esclusione implicita di staging, registry e layer `qgis.mode=not_published`;
- snippet operativi QGIS Server e reverse proxy;
- UI `/gis/catalogo` con pannello `POC OGC read-only`;
- client frontend `getGisOgcPoc`.

Implementato:

- raccomandazione `qgis_server`;
- proxy path `/gis/ogc/`;
- policy `gaia_auth_or_vpn_required`;
- riferimento al progetto QGIS unico `/gis/qgis/project`;
- flag `wfs_transactional=false` per tutti i layer;
- warning espliciti su WFS-T disabilitato e protezione proxy;
- coverage 100% su backend GIS/main e runtime frontend modificati.

Exit criteria:

- il POC elenca solo layer che l'utente puo vedere;
- il POC non pubblica WFS-T;
- non viene avviato nessun server OGC in produzione;
- UI spiega che si tratta di verifica read-only;
- nessuna nuova migration richiesta;
- coverage 100% sui runtime backend/frontend modificati.

## M20 - Apply Controlled Edit Non Catasto

Stato: completato su branch `feature/gis-platform-m16-m19`.

Obiettivo:

- rendere operativo l'apply delle change request approvate su layer ufficiali
  non Catasto che hanno opt-in controlled edit, senza cambiare la policy
  Catasto.

Deliverable:

- adapter `postgis_controlled_edit`;
- `INSERT` per `feature_create`;
- `UPDATE` attributi per `attribute_update`;
- `UPDATE` geometria per `geometry_update`;
- `DELETE` per `feature_delete`;
- audit `change_request.applied` con `mode=applied`, adapter, operazione e
  snapshot `before`/`after` dove disponibili;
- guardrail no-op per Catasto e per layer senza opt-in;
- CTA frontend `Applica change request`.

Implementato:

- opt-in basato su `source_type=postgis`, dominio/workspace non Catasto,
  `qgis.editable=true` e `qgis.edit_policy=controlled`;
- geometria PostGIS costruita da GeoJSON con SRID del layer;
- test SQLite che verificano scrittura reale su tabella sorgente;
- target feature mancante, payload corrotto, vincoli DB, tabella fisica
  assente e layer senza tabella configurata gestiti con errori controllati.

Exit criteria:

- create/update/delete cambiano solo layer opt-in;
- Catasto continua a produrre audit no-op senza scrivere tabelle ufficiali;
- errori di apply lasciano la change request in `approved`;
- nessuna nuova migration richiesta;
- coverage 100% sui runtime backend/frontend modificati.
