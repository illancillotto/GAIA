# GAIA GIS Platform - Shapefile Import Runbook

> Data: 2026-07-15.
> Scope: percorso governato per importare shapefile nella GIS Platform.

## Stato M15

M13 implementa upload ZIP, validazione e staging non distruttivo. M14 aggiunge
il publish admin-only degli import validati nel catalogo GIS come layer staging
read-only. Il publish M14 non ufficializza dati di dominio, non abilita export
shapefile e non pubblica il layer in QGIS governance. M15 aggiunge la preview
read-only dello staging da UI e API.

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
- preview di un campione di feature con attributi e geometria;
- pulizia dello staging con `reject`.

## Pubblicazione Catalogo M14

Dopo la validazione l'operatore puo pubblicare l'import come nuovo layer
catalogo staging. I dati restano nella staging table creata dall'import; il
catalogo espone il layer per consultazione e governance read-only.

Il publish M14 usa i valori gia indicati in fase di upload:

- workspace;
- dominio proprietario;
- `official_source`;
- nome layer target;
- titolo layer target;
- staging schema/table;
- SRID sorgente, geometry type e campi validati.

Il layer creato ha:

- `source_type=postgis_staging`;
- `geometry_column=geometry_json`;
- `feature_id_column=feature_seq`;
- permesso default `viewer` read-only;
- metadata `qgis.mode=not_published` e `qgis.editable=false`;
- metadata `tiles.published=false`;
- metadata `export.shapefile=false`.

Se lo shapefile modifica dati ufficiali gia esistenti, il publish staging non
basta: deve aprire una change request o seguire la policy applicativa del
dominio. Il publish M14 serve a rendere consultabile un nuovo layer importato,
non a sostituire le tabelle ufficiali.

## Regole Di Governance

- Gli shapefile importati non diventano sorgente viva: dopo il publish la
  sorgente operativa del layer catalogo M14 resta la staging table PostGIS.
- Il publish M14 crea dati staging read-only, non dati ufficiali di dominio.
- Gli export NAS restano copie versionate, non area di editing.
- Catasto resta governato dal team Catasto: import che impattano Catasto non
  devono bypassare `/catasto/gis` o le policy di dominio.
- Annotazioni e change request restano in GAIA, non nel file shapefile.
- I layer `postgis_staging` non sono esportabili come shapefile e non sono
  inclusi nella governance QGIS publishable.

## UI Disponibile In M15

Da `/gis/catalogo`, nella scheda `Import shapefile`, l'utente admin puo inserire:

- ZIP shapefile;
- workspace;
- dominio;
- nome layer target;
- titolo layer target;
- SRID sorgente;
- fonte ufficiale;
- encoding.

La UI mostra stato import, feature count, geometry type, staging table e checksum.
Il pulsante `Rigetta import` chiama il cleanup dello staging finche l'import non
e pubblicato.

Per import `validated` o `published`, la UI mostra anche `Vedi anteprima
staging`. La preview mostra:

- numero feature restituite rispetto al totale;
- staging table usata;
- `feature_seq`;
- attributi DBF come JSON;
- geometria GeoJSON testuale;
- geometry type e SRID.

Per import in stato `validated`, la UI mostra `Pubblica nel catalogo`. Se il
publish riesce:

- lo stato diventa `published`;
- viene mostrato `Layer catalogo creato`;
- il catalogo viene ricaricato;
- il reject non e piu disponibile.

## Endpoint Disponibili In M15

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
GET /gis/imports/{import_id}/preview?limit=5&offset=0
POST /gis/imports/{import_id}/validate
POST /gis/imports/{import_id}/reject
POST /gis/imports/{import_id}/publish
```

`preview` e read-only. Richiede import `validated` o `published`, legge la
staging table e restituisce un campione paginato con attributi DBF, geometria
GeoJSON testuale, `feature_seq`, geometry type, SRID, bbox, schema campi,
contatori e `has_more`.

`validate` e idempotente per import non rigettati. `reject` marca l'import come
`rejected`, scrive audit e prova a rimuovere la staging table.

`publish` e admin-only. Richiede import in stato `validated`, crea il layer
catalogo staging read-only, imposta `published_layer_id` e `published_at` e
scrive audit `shapefile_import.published` e
`layer.created_from_shapefile_import`.

Errori governati:

- `409` se la preview viene chiesta su import non validato/rejected;
- `409` se la staging table della preview non e piu disponibile;
- `409` se l'import e rigettato, non validato o il target catalogo esiste gia;
- `409` se una race di integrita crea lo stesso target durante il publish;
- `409` se si tenta il reject dopo publish;
- publish ripetuto su import gia `published` torna lo stesso record import.

## Endpoint Futuri

Un flusso successivo dovra creare change request quando l'import impatta layer
ufficiali invece di creare un nuovo layer staging.
