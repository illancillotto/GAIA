# GAIA GIS Platform

> Data: 2026-07-14.
> Stato: M2 permessi layer su branch `feature/gis-platform-permissions-m2`.

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

### QGIS Server o GeoServer

Nessun server OGC viene introdotto nel runtime MVP.

Valutazione:

- QGIS Server e preferibile se la priorita e riusare progetti, stili e abitudini
  QGIS gia presenti in azienda.
- GeoServer e preferibile se servono console amministrativa matura, workspace
  multipli, policy OGC granulari, WFS-T o integrazioni enterprise piu ampie.
- Martin resta adeguato per tiles vettoriali Catasto gia operative, ma non copre
  tutto il governo WMS/WFS/WMTS.

Decisione iniziale: mantenere PostGIS + Martin + API GAIA. Avviare un proof of
concept QGIS Server solo quando il catalogo e i permessi GAIA hanno stabilizzato
quali layer pubblicare e con quali profili.

### NAS Shapefile

Il NAS conserva export e backup versionati:

- layer;
- versione;
- path NAS;
- autore o job;
- timestamp;
- checksum quando disponibile.

Gli shapefile non sono la sorgente operativa primaria e non contengono note o
workflow applicativi.

## Roadmap Incrementale

1. MVP backend: catalogo, permessi layer, annotazioni, change request, export
   metadata e audit.
2. Registrazione iniziale dei layer Catasto nel catalogo centrale senza spostare
   logiche Catasto.
3. Policy PostGIS per QGIS: ruoli DB read-only e ruoli edit controllati per
   layer autorizzati.
4. Job reale di export shapefile versionato su NAS con checksum e retention.
5. Workflow editing completo: draft, validazione, apply su layer ufficiale,
   audit geometrie/attributi e rollback/versioning.
6. Valutazione POC QGIS Server vs GeoServer per pubblicazione WMS/WFS/WMTS.
7. Integrazione frontend minima del catalogo GIS, mantenendo `/catasto/gis` come
   workspace Catasto operativo. Completata in M1 con `/gis/catalogo`.

## Documenti Operativi

- `docs/GIS_PLATFORM_IMPLEMENTATION_PLAN.md`: dettaglio tecnico delle fasi.
- `docs/GIS_PLATFORM_MILESTONES.md`: milestone e criteri di uscita.
- `docs/GIS_PLATFORM_PROGRESS.md`: stato corrente, verifiche e prossima azione.
