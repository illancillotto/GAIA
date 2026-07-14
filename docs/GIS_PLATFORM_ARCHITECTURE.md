# GAIA GIS Platform

> Data: 2026-07-14.
> Stato: M7 decisione OGC su branch `feature/gis-platform-ogc-decision-m7`.

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

La UI `GIS Platform / Catalogo` mostra layer, workspace, sorgente PostGIS,
Martin layer, metadata QGIS e permesso effettivo. Per i layer Catasto espone
solo un link contestuale verso `/catasto/gis`, che resta la console dominio.

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

Gli shapefile non sono la sorgente operativa primaria e non contengono note,
change request o workflow applicativi.

## Roadmap Incrementale

1. MVP backend: catalogo, permessi layer, annotazioni, change request, export
   metadata e audit.
2. Registrazione iniziale dei layer Catasto nel catalogo centrale senza spostare
   logiche Catasto.
3. Catalogo operativo `/gis/catalogo`, governance permessi layer, annotazioni
   governate, change request workflow, export NAS reale, governance QGIS Desktop
   e decisione OGC. Completati in M1, M2, M3, M4, M5, M6 e M7.
4. Retention e scheduling export NAS, se serve oltre alla richiesta manuale.
5. Eventuale hardening dei profili edit QGIS per domini non Catasto.
6. Workflow editing completo: draft, validazione, apply su layer ufficiale,
   audit geometrie/attributi e rollback/versioning.
7. Valutazione POC QGIS Server vs GeoServer per pubblicazione WMS/WFS/WMTS.

## Documenti Operativi

- `docs/GIS_PLATFORM_IMPLEMENTATION_PLAN.md`: dettaglio tecnico delle fasi.
- `docs/GIS_PLATFORM_MILESTONES.md`: milestone e criteri di uscita.
- `docs/GIS_PLATFORM_PROGRESS.md`: stato corrente, verifiche e prossima azione.
- `docs/GIS_QGIS_DESKTOP_RUNBOOK.md`: istruzioni operative QGIS Desktop.
- `docs/GIS_OGC_DECISION_RECORD.md`: decisione QGIS Server vs GeoServer.
