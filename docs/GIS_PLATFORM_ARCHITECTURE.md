# GAIA GIS Platform

> Data: 2026-07-15.
> Stato: M15 preview staging import shapefile su branch `feature/gis-platform-shapefile-preview-m15`.

## Obiettivo

GAIA introduce una piattaforma GIS centralizzata per governare layer, permessi,
annotazioni, workflow di modifica, audit ed export, mantenendo QGIS come client
tecnico quotidiano e PostGIS come sorgente operativa ufficiale.

Architettura target:

```text
NAS shapefile = backup/export versionato
PostGIS = sorgente operativa ufficiale
QGIS Desktop = client tecnico utenti
QGIS Server o GeoServer = pubblicazione OGC da valutare
GAIA GIS Platform = catalogo, permessi, note, workflow, audit, import/export
GIS Catasto = primo dominio/client integrato
GIS Riordino = primo dominio non Catasto registrato nel catalogo centrale
```

## Confini Architetturali

### Catasto

Il GIS Catasto esistente resta proprietario di:

- pagina `/catasto/gis`;
- popup, ricerca, selezioni e workspace operativo Catasto;
- logiche AdE WFS, allineamento particelle, Martin tiles e viste PostGIS
  `cat_*`;
- regole di dominio Catasto su particelle, distretti, punti di consegna,
  anomalie, ruolo e utenze.

Il nuovo modulo GIS non duplica queste logiche. Catasto registra o esporra i suoi
layer nel catalogo GIS centrale quando serve governance trasversale.

### Riordino

Il dominio Riordino resta proprietario di:

- route operative `/riordino/practices/{practice_id}/gis-links`;
- tabella `riordino_gis_links`;
- CRUD dei link manuali tra pratica, layer esterno, feature e riferimento
  geometrico testuale;
- eventi di dominio Riordino generati da create/update dei link GIS.

La GIS Platform registra `riordino_gis_links` come registry read-only nel
workspace `riordino`, con `source_type=domain_registry` e
`official_source=riordino`. Non lo tratta come layer geometrico PostGIS, non lo
pubblica in QGIS governance e non ne consente export shapefile.

### Nuovo Modulo GIS

Il backend `backend/app/modules/gis` governa:

- catalogo layer per workspace;
- permessi per layer con livelli `viewer`, `annotator`, `editor`, `approver`,
  `admin`;
- annotazioni collegate a layer e feature, fuori dagli shapefile;
- change request per modifiche proposte prima della pubblicazione ufficiale;
- metadati di export shapefile su NAS;
- audit log delle operazioni critiche.

Le API MVP sono esposte sotto `/gis` e non sostituiscono `/catasto/gis`.

### Catalogo Operativo M1

Il catalogo centrale espone la vista read-only `/gis/catalogo` e le API:

- `GET /gis/layers` con filtri opzionali `workspace`, `domain_module`,
  `source_type`, `official_source`, `is_active`;
- `GET /gis/workspaces/{workspace}/layers`;
- `PATCH /gis/layers/{layer_id}/metadata`;
- `POST /gis/layers/{layer_id}/activate`;
- `POST /gis/layers/{layer_id}/deactivate`.

La gestione M1 non modifica geometrie, attributi ufficiali, workspace, nome
layer, tabelle PostGIS, sorgente ufficiale o source type. Gli admin possono
aggiornare solo metadata descrittivi e stato catalogo, con audit. I viewer
continuano a vedere solo layer attivi e autorizzati.

La UI `GIS Platform / Catalogo` mostra layer, workspace, source type, sorgente
ufficiale, metadata QGIS/tile dove presenti e permesso effettivo. Per i layer
Catasto espone solo un link contestuale verso `/catasto/gis`, che resta la
console dominio.

### Integrazione Multi-Dominio M8

Lo startup backend chiama `ensure_gis_platform_catalog`, che registra in modo
idempotente i layer/registry governati dalla piattaforma:

- workspace `catasto`, dominio `catasto`, layer PostGIS/Martin read-only;
- workspace `riordino`, dominio `riordino`, registry `riordino_gis_links`
  read-only e non geometrico.
- workspace `rete`, dominio `network`, layer PostGIS geometrico `rete_condotte`
  con opt-in QGIS controlled edit.

Regole di onboarding multi-dominio:

- `workspace` deve identificare il dominio o la famiglia operativa esposta in
  `/gis`;
- `domain_module` deve restare uguale al modulo proprietario quando esiste;
- i layer geometrici pubblicabili usano `source_type=postgis` e metadati QGIS o
  Martin espliciti;
- i registri applicativi non geometrici usano `source_type=domain_registry` e
  metadati `export.shapefile=false`;
- l'edit QGIS diretto richiede metadata `qgis.editable=true` e
  `qgis.edit_policy=controlled`; M18 applica questo primo opt-in al layer Rete
  `rete_condotte`;
- il CRUD di dominio resta nel modulo proprietario; la GIS Platform governa
  catalogo, visibilita, permessi, annotazioni, change request e audit
  trasversali.

### Dashboard Stato Catalogo M9

L'endpoint `GET /gis/catalog/dashboard` espone una vista health del catalogo
GIS. Il calcolo e deterministico e usa solo metadata/permessi nel database GAIA:
non effettua probe runtime verso PostGIS, Martin, QGIS Server o NAS.

Metriche:

- layer visibili totali, attivi e inattivi;
- numero workspace;
- distribuzione per `source_type` e `official_source`;
- layer pubblicabili dalla governance QGIS;
- layer esportabili come shapefile;
- stato aggregato `ok`, `warning`, `critical`;
- riepilogo health per workspace.

Issue rilevate:

- layer attivi senza permessi di visualizzazione;
- layer PostGIS senza tabella o colonna geometria;
- layer con opt-in edit QGIS senza `qgis.edit_policy=controlled`;
- registry di dominio senza `qgis.mode=not_published`;
- registry di dominio senza `export.shapefile=false`.

La UI `/gis/catalogo` mostra il pannello `Health catalogo GIS` sopra i filtri
catalogo. Gli admin vedono tutto il catalogo; gli utenti non admin vedono solo
layer attivi per cui hanno `can_view`.

M10 aggiunge al dashboard il blocco `latest_exports`, con ultimo export per
layer visibile, stato, path NAS, trigger manuale/schedulato e versione.

### UX Catalogo M12

La pagina `/gis/catalogo` e la superficie trasversale per capire il catalogo GIS
prima di entrare nei workspace di dominio. M12 non introduce nuovi endpoint di
upload o download: migliora la guida operativa e rende espliciti i percorsi che
verranno automatizzati.

La UI spiega:

- layer come dataset geografico governato;
- workspace come contenitore operativo;
- dominio come modulo responsabile delle regole del dato;
- source type come tecnologia o registry che alimenta il layer;
- official source come sistema autorevole del dato;
- permesso effettivo come azioni realmente consentite all'utente.

Le schede operative chiariscono due domande utente ricorrenti:

- import shapefile: ZIP con `.shp`, `.shx`, `.dbf`, `.prj`, validazione,
  staging PostGIS, anteprima e pubblicazione governata;
- QGIS Desktop in un colpo: progetto `.qgz` unico con layer visibili,
  connessione PostGIS governata, stili/gruppi preconfigurati e pacchetto offline
  solo se il PC non raggiunge il database.

### Permessi Layer M2

I permessi GIS sono gestibili per principal `role` e `user`.

Policy:

- `role` deve essere uno dei ruoli applicativi GAIA;
- se esiste un permesso `user` sul layer, prevale sul permesso `role`;
- in assenza di override `user`, vale il permesso `role`;
- gli admin applicativi mantengono privilegi gestionali globali.

Le operazioni grant, update e revoke scrivono audit dedicati. Il pannello
`Gestisci permessi` e disponibile su `/gis/catalogo` solo quando il layer
restituisce `can_manage=true`.

### Annotazioni Governate M3

Le annotazioni sono note operative collegate a layer e, opzionalmente, a una
feature. Vivono in tabelle GAIA/PostGIS dedicate e non modificano geometrie,
attributi ufficiali o shapefile NAS.

Lifecycle:

- `open`: nota creata e ancora lavorabile;
- `in_review`: nota inviata a revisione da un utente con `can_annotate`;
- `closed`: nota chiusa da un utente con `can_approve`;
- `rejected`: nota respinta da un utente con `can_approve`.

API governate:

- `GET /gis/layers/{layer_id}/annotations?status=&feature_id=`;
- `POST /gis/layers/{layer_id}/annotations`;
- `PATCH /gis/layers/{layer_id}/annotations/{annotation_id}`;
- `POST /gis/layers/{layer_id}/annotations/{annotation_id}/in-review`;
- `POST /gis/layers/{layer_id}/annotations/{annotation_id}/close`;
- `POST /gis/layers/{layer_id}/annotations/{annotation_id}/reject`.

Policy:

- `can_view` consente la lettura delle annotazioni del layer;
- `can_annotate` consente create, update e passaggio a `in_review`;
- `can_approve` consente `closed` e `rejected`;
- `closed` e `rejected` sono stati terminali e bloccano ulteriori update o
  transizioni;
- gli allegati restano riferimenti metadata in `attachment_refs`, non file
  incorporati nel layer ufficiale.

Audit:

- `annotation.created`;
- `annotation.updated`;
- `annotation.in_review`;
- `annotation.closed`;
- `annotation.rejected`.

La UI `/gis/catalogo` espone il pannello `Annotazioni` per i layer con
`can_view`, il form di creazione/modifica solo per `can_annotate`, e le azioni
approvative solo per `can_approve`.

### Change Request E Draft Editing M4

Le change request sono proposte di modifica ai dati ufficiali. Vivono nel modulo
GIS e non scrivono direttamente su PostGIS di dominio finche non esiste una
policy esplicita per quel layer o dominio.

Tipi payload supportati:

- `attribute_update`: richiede `feature_id` e `payload.after`;
- `geometry_update`: richiede `feature_id` e `payload.geometry`;
- `feature_create`: richiede `payload.geometry` e `payload.properties`;
- `feature_delete`: richiede `feature_id` e `payload.before`.

Lifecycle:

- `submitted`: proposta aperta dall'editor;
- `needs_changes`: l'approver richiede integrazioni;
- `approved`: proposta validata e pronta per apply;
- `rejected`: proposta respinta, terminale;
- `applied`: apply eseguito dal workflow, oggi no-op per Catasto.

API governate:

- `GET /gis/change-requests?status=&layer_id=`;
- `POST /gis/layers/{layer_id}/change-requests`;
- `PATCH /gis/change-requests/{change_request_id}`;
- `POST /gis/change-requests/{change_request_id}/request-changes`;
- `POST /gis/change-requests/{change_request_id}/approve`;
- `POST /gis/change-requests/{change_request_id}/reject`;
- `POST /gis/change-requests/{change_request_id}/apply`.

Policy:

- `can_edit` consente submit e update delle richieste non terminali;
- `can_approve` consente request-changes, approve, reject e apply;
- `rejected` e `applied` sono stati terminali;
- `approved` non e piu modificabile dall'editor;
- i validator pluggable possono essere registrati per layer, dominio o workspace;
- l'apply su Catasto scrive audit `change_request.applied` con risultato
  `no_op`, senza aggiornare le tabelle ufficiali Catasto.

La UI `/gis/catalogo` espone il pannello `Change request` per i layer visibili,
con form JSON per gli editor, diff payload leggibile e azioni approvative.

### Bootstrap Catalogo Catasto

All'avvio backend `ensure_catasto_gis_catalog` registra in modo idempotente i
layer Catasto gia pubblicati da PostGIS/Martin nel catalogo centrale:
`cat_particelle_current`, `cat_distretti`, `cat_distretti_boundaries`,
`cat_delivery_points_current`, `cat_irrigation_canals_current` e
`cat_dui_2026_current`.

Il seed usa `workspace=catasto`, `domain_module=catasto`, `source_type=postgis`,
`official_source=postgis` e `martin_layer_id` uguale al `layer_id` in
`config/martin.toml`. I metadati marcano i layer come read-only per QGIS e come
tile layer Martin; il NAS resta indicato solo come backup/export versionato.

La permission default viene assicurata solo per il ruolo `viewer` con accesso in
lettura. Le capacita `annotate`, `edit`, `approve` e `manage` restano false; gli
admin continuano ad avere privilegi gestionali tramite ruolo applicativo, non
tramite il seed Catasto.

### QGIS Desktop

QGIS resta il client tecnico. L'uso raccomandato e:

- connessione a PostGIS con account read-only per consultazione;
- account edit controllati solo per layer autorizzati;
- eventuale consumo di servizi OGC quando saranno introdotti;
- nessuna modifica diretta agli shapefile NAS come sorgente viva.

M16 rende operativo il progetto QGIS unico: `GET /gis/qgis/project` genera un
`.qgz` per l'utente corrente, filtrato sui layer visibili e pubblicabili,
raggruppato per workspace e collegato a PostGIS tramite servizio client
`gaia_gis`. Il progetto esclude `postgis_staging`, registry applicativi e layer
con `qgis.mode=not_published`.

### Governance QGIS Desktop M6

L'endpoint admin-only `GET /gis/qgis/governance` genera una policy SQL
deterministica a partire dal catalogo `gis_layers`.

La policy include:

- schema pubblicabile `gis_qgis`;
- ruoli gruppo NOLOGIN `gaia_gis_qgis_reader`, `gaia_gis_qgis_editor`,
  `gaia_gis_qgis_admin`;
- view read-only per layer PostGIS attivi;
- `GRANT SELECT` sulle view per reader/editor;
- `REVOKE INSERT, UPDATE, DELETE` per layer read-only;
- `GRANT SELECT, INSERT, UPDATE, DELETE` sulle tabelle base solo per layer non
  Catasto con metadata `qgis.editable=true` e `qgis.edit_policy=controlled`.

M18 registra `rete_condotte` come primo layer non Catasto con controlled edit:
viewer resta read-only nel catalogo, mentre il ruolo applicativo `operator`
riceve capability GIS `editor` e la governance QGIS genera grant editor sulla
tabella `network.rete_condotte`.

GAIA non crea ruoli LOGIN e non applica automaticamente la policy al database:
l'operatore DB revisiona lo SQL, crea ruoli LOGIN `qgis_*` per ambiente e li
assegna ai ruoli gruppo. Il runbook operativo e in
`docs/GIS_QGIS_DESKTOP_RUNBOOK.md`.

### QGIS Server o GeoServer

Nessun server OGC viene introdotto automaticamente nel runtime GAIA.

Valutazione:

- QGIS Server e preferibile se la priorita e riusare progetti, stili e abitudini
  QGIS gia presenti in azienda.
- GeoServer e preferibile se servono console amministrativa matura, workspace
  multipli, policy OGC granulari, WFS-T o integrazioni enterprise piu ampie.
- Martin resta adeguato per tiles vettoriali Catasto gia operative, ma non copre
  tutto il governo WMS/WFS/WMTS.

Decisione M7: mantenere PostGIS + Martin + API GAIA come baseline. Se serve
pubblicazione OGC, avviare prima un POC QGIS Server read-only per riusare
progetti/stili QGIS e la policy M6. Riesaminare GeoServer se emergono requisiti
multi-dominio, workspace OGC, sicurezza layer nativa o amministrazione OGC piu
granulare. Il dettaglio e in `docs/GIS_OGC_DECISION_RECORD.md`.

M19 rende il POC valutabile da API/UI senza introdurre un server OGC in
produzione:

- `GET /gis/ogc/poc` elenca layer visibili e pubblicabili come WMS/WFS
  read-only;
- WFS-T resta sempre disabilitato;
- gli snippet `qgis_server_env` e `reverse_proxy` sono materiale operativo per
  un futuro deployment controllato;
- `/gis/catalogo` mostra il pannello `POC OGC read-only` per verificare layer,
  proxy path e warning di sicurezza.

### Export NAS Shapefile M5

Il NAS conserva export e backup versionati prodotti da PostGIS:

- layer;
- versione;
- path NAS;
- autore o job;
- timestamp;
- checksum SHA-256;
- manifest JSON con layer, sorgente, mapping campi DBF, SRID e conteggio record.

L'API `POST /gis/layers/{layer_id}/export-shapefile` crea un record
`gis_layer_exports`, genera uno ZIP shapefile tramite staging locale, pubblica il
file in modo atomico sul path finale e aggiorna lo stato a `completed` o
`failed`. Gli audit `export.requested`, `export.completed` ed `export.failed`
tracciano richiesta, checksum, conteggio record ed eventuale errore.

L'export shapefile e consentito solo per layer PostGIS geometrici. Registry di
dominio non geometrici, come `riordino_gis_links`, sono catalogabili ma non
esportabili come shapefile.

Gli shapefile non sono la sorgente operativa primaria e non contengono note,
change request o workflow applicativi.

### Import Shapefile Governato M12-M15

L'import shapefile previsto dalla piattaforma non usa il NAS come sorgente viva.
Il percorso target e:

1. upload ZIP contenente almeno `.shp`, `.shx`, `.dbf` e `.prj`;
2. validazione di geometria, SRID, encoding, campi e feature count;
3. caricamento in staging PostGIS non distruttivo;
4. anteprima e scelta di workspace, dominio, source ufficiale e permessi;
5. pubblicazione nel catalogo GIS o apertura di change request se il dato
   modifica layer ufficiali.

M12 documenta e mostra questo percorso nella UI. M13 implementa il backend per i
passi 1-3:

- tabella `gis_shapefile_imports`;
- endpoint `POST /gis/imports/shapefile`;
- endpoint `GET /gis/imports/{import_id}`;
- endpoint `POST /gis/imports/{import_id}/validate`;
- endpoint `POST /gis/imports/{import_id}/reject`;
- validazione ZIP e componenti shapefile obbligatori;
- staging table non distruttiva in schema `gis_staging` su PostgreSQL;
- audit upload, validate e reject.

M14 implementa il publish governato per il caso sicuro: un import validato puo
creare un nuovo record `gis_layers` come staging read-only, non come dato
ufficiale del dominio:

- endpoint `POST /gis/imports/{import_id}/publish`;
- status import `published`, `published_layer_id` e `published_at`;
- layer catalogo `source_type=postgis_staging` collegato alla staging table;
- metadata `qgis.mode=not_published`, `qgis.editable=false`,
  `tiles.published=false` ed `export.shapefile=false`;
- permesso default `viewer` read-only;
- audit `shapefile_import.published` e
  `layer.created_from_shapefile_import`;
- blocco publish per import non validati, rigettati o target gia esistenti.

La UI `/gis/catalogo` e collegata a upload, visualizzazione del risultato
validato, reject cleanup e publish catalogo. Il layer pubblicato resta staging:
non entra nella governance QGIS, non viene esportato come shapefile e non
sostituisce change request o policy applicative quando l'import modifica dati
ufficiali.

M15 aggiunge la preview read-only dello staging:

- endpoint `GET /gis/imports/{import_id}/preview`;
- query `limit/offset` per campionare le feature;
- output con attributi DBF, geometria GeoJSON testuale, feature sequence,
  geometry type, SRID, bbox e schema campi;
- UI `Vedi anteprima staging` in `/gis/catalogo`;
- errore governato `409` se l'import non e validato/pubblicato o se la staging
  table non e piu disponibile.

La preview legge solo la staging table e non modifica ne catalogo ne layer
ufficiali.

M17 aggiunge il percorso da import a change request per i casi in cui lo
shapefile impatta layer ufficiali esistenti:

- endpoint `POST /gis/imports/{import_id}/change-requests`;
- target obbligatorio `source_type=postgis` con geometria configurata;
- permesso `can_edit` richiesto sul layer target;
- creazione di change request `feature_create` con `geometry`, `properties` e
  metadati `source_import`;
- deduplica per `import_id` + `feature_seq`;
- nessuna scrittura immediata sul layer ufficiale.

Questo completa la separazione tra nuovo layer staging consultabile e modifica
di dato ufficiale: il primo passa dal publish catalogo M14, la seconda passa dal
workflow change request e dalle policy del dominio.

### Scheduling E Retention Export M10

Il modulo GIS registra uno scheduler APScheduler opzionale:

- setting `GIS_EXPORT_SCHEDULER_ENABLED=false` di default;
- cron `GIS_EXPORT_SCHEDULER_CRON`, default `30 2 * * *`;
- timezone `GIS_EXPORT_SCHEDULER_TIMEZONE`, default `Europe/Rome`;
- retention `GIS_EXPORT_RETENTION_COUNT`, default `5`;
- limite per run `GIS_EXPORT_MAX_LAYERS_PER_RUN`, default `50`.

Quando abilitato, il job `gis_shapefile_export_schedule` esporta solo layer
attivi, `source_type=postgis`, geometrici ed exportable. Ogni export schedulato
usa metadata `trigger=scheduled`, scrive audit `export.scheduled` e poi riusa la
pipeline M5 per `export.completed` o `export.failed`.

La retention elimina solo export completati con `trigger=scheduled`, per layer,
mantenendo gli ultimi `GIS_EXPORT_RETENTION_COUNT`. Gli export manuali non sono
rimossi dalla retention schedulata. Ogni prune scrive
`export.retention_applied` con path, versione, retention count e indicazione se
il file ZIP e stato eliminato.

## Roadmap Incrementale

1. MVP backend: catalogo, permessi layer, annotazioni, change request, export
   metadata e audit.
2. Registrazione iniziale dei layer Catasto nel catalogo centrale senza spostare
   logiche Catasto.
3. Catalogo operativo `/gis/catalogo`, governance permessi layer, annotazioni
   governate, change request workflow, export NAS reale, governance QGIS Desktop
   decisione OGC, primo onboarding multi-dominio, dashboard health catalogo,
   scheduling/retention export NAS, modulo GIS nativo, UX import/QGIS, backend
   import shapefile governato, publish catalogo staging, preview staging e
   download progetto QGIS unico.
   Completati in M1, M2, M3, M4, M5, M6, M7, M8, M9, M10, M11, M12, M13,
   M14, M15 e M16.
4. Creazione change request da import quando il target impatta layer ufficiali.
5. Eventuale hardening dei profili edit QGIS per domini non Catasto.
6. Workflow editing completo: draft, validazione, apply su layer ufficiale,
   audit geometrie/attributi e rollback/versioning.
7. Valutazione POC QGIS Server vs GeoServer per pubblicazione WMS/WFS/WMTS.

## Documenti Operativi

- `docs/GIS_PLATFORM_IMPLEMENTATION_PLAN.md`: dettaglio tecnico delle fasi.
- `docs/GIS_PLATFORM_MILESTONES.md`: milestone e criteri di uscita.
- `docs/GIS_PLATFORM_PROGRESS.md`: stato corrente, verifiche e prossima azione.
- `docs/GIS_QGIS_DESKTOP_RUNBOOK.md`: istruzioni operative QGIS Desktop.
- `docs/GIS_SHAPEFILE_IMPORT_RUNBOOK.md`: percorso import shapefile governato.
- `docs/GIS_OGC_DECISION_RECORD.md`: decisione QGIS Server vs GeoServer.
