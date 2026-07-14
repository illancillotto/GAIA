# GAIA GIS Platform - Shapefile Import Runbook

> Data: 2026-07-14.
> Scope: percorso governato per importare shapefile nella GIS Platform.

## Stato M13

M13 implementa il backend per upload ZIP, validazione e staging non distruttivo.
La UI `/gis/catalogo` resta informativa finche non viene collegata agli endpoint
runtime. Il publish automatico nel catalogo GIS non e ancora implementato.

## Input Richiesto

L'utente deve preparare uno ZIP con almeno:

- `.shp`: geometrie;
- `.shx`: indice geometrie;
- `.dbf`: attributi;
- `.prj`: sistema di riferimento;
- `.cpg`, se disponibile, per dichiarare encoding.

Il nome dei file deve essere coerente. Esempio valido:

```text
rete_condotte.shp
rete_condotte.shx
rete_condotte.dbf
rete_condotte.prj
rete_condotte.cpg
```

## Validazioni

La pipeline backend M13 blocca o segnala:

- ZIP incompleto;
- ZIP con path non sicuri;
- piu shapefile nello stesso ZIP;
- geometrie o DBF non leggibili da pyshp;
- SRID assente o minore di `1`;
- feature count nullo;
- assenza di workspace, nome layer o titolo layer.

Il report M13 salva geometry type, bbox, campi DBF, feature count, warning
encoding e checksum SHA-256. La coerenza semantica del `.prj` e i limiti
dimensionali configurabili restano hardening successivo.

## Staging PostGIS

Il caricamento avviene prima in staging non distruttivo:

- schema `gis_staging` e tabella `import_<uuid>` su PostgreSQL;
- tabella `gis_staging_import_<uuid>` in SQLite/test;
- nessuna scrittura immediata sui layer ufficiali;
- attributi e geometrie salvati come JSON testuale per anteprima tecnica;
- report di validazione scaricabile o visibile da UI;
- pulizia dello staging con `reject`.

## Pubblicazione Catalogo

Dopo la validazione l'operatore sceglie:

- workspace;
- dominio proprietario;
- `source_type`, di norma `postgis`;
- `official_source`;
- titolo e descrizione layer;
- permessi iniziali;
- metadata QGIS, Martin/export e policy read-only/edit.

Se lo shapefile crea un nuovo layer non ufficiale, il publish puo registrare un
nuovo record nel catalogo GIS. Se modifica dati ufficiali gia esistenti, deve
aprire una change request o seguire la policy applicativa del dominio.

## Regole Di Governance

- Gli shapefile importati non diventano sorgente viva: dopo il publish la
  sorgente operativa e PostGIS.
- Gli export NAS restano copie versionate, non area di editing.
- Catasto resta governato dal team Catasto: import che impattano Catasto non
  devono bypassare `/catasto/gis` o le policy di dominio.
- Annotazioni e change request restano in GAIA, non nel file shapefile.

## Endpoint Disponibili In M13

Upload:

```http
POST /gis/imports/shapefile
Content-Type: multipart/form-data
```

Campi richiesti:

- `file`: ZIP shapefile;
- `workspace`;
- `target_layer_name`;
- `target_layer_title`;
- `source_srid`.

Campi opzionali:

- `domain_module`;
- `official_source`, default `shapefile_upload`;
- `encoding`, default `utf-8`.

L'endpoint e admin-only. Se la validazione passa, il record torna in stato
`validated` e contiene staging table, feature count, geometry type, bbox, campi,
report e checksum.

Lettura e lifecycle:

```http
GET /gis/imports/{import_id}
POST /gis/imports/{import_id}/validate
POST /gis/imports/{import_id}/reject
```

`validate` e idempotente per import non rigettati. `reject` marca l'import come
`rejected`, scrive audit e prova a rimuovere la staging table.

## Endpoint Futuri

```http
GET /gis/imports/{import_id}/preview
POST /gis/imports/{import_id}/publish
```

Il publish dovra creare un layer catalogo o una change request, applicando
permessi GIS, audit e policy di dominio prima di abilitare l'upload in UI.
