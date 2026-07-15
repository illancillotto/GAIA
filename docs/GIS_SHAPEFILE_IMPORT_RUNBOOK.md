# GAIA GIS Platform - Shapefile Import Runbook

> Data: 2026-07-15.
> Scope: percorso governato per importare shapefile nella GIS Platform.

## Stato M17

M13 implementa upload ZIP, validazione e staging non distruttivo. M14 aggiunge
il publish admin-only degli import validati nel catalogo GIS come layer staging
read-only. Il publish M14 non ufficializza dati di dominio, non abilita export
shapefile e non pubblica il layer in QGIS governance. M15 aggiunge la preview
read-only dello staging da UI e API. M17 aggiunge il percorso governato per
creare change request da import quando lo shapefile impatta un layer ufficiale
esistente.

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
- SRID manuale minore di `1`, oppure SRID assente e `.prj` senza autorita EPSG
  riconoscibile;
- feature count nullo;
- assenza di workspace, nome layer o titolo layer.

Il report M13 salva geometry type, bbox, campi DBF, feature count, warning
encoding, SRID risolto, origine dello SRID (`form` o `prj`) e checksum SHA-256.
La coerenza semantica completa del `.prj` e i limiti dimensionali configurabili
restano hardening successivo.

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
basta: M17 permette di creare change request sul layer ufficiale target. Il
publish M14 serve a rendere consultabile un nuovo layer importato, non a
sostituire le tabelle ufficiali.

## Change Request Da Import M17

Per import `validated` o `published`, l'operatore puo creare change request da
staging verso un layer ufficiale PostGIS:

```http
POST /gis/imports/{import_id}/change-requests
```

Payload:

- `target_layer_id`: layer ufficiale PostGIS da aggiornare;
- `limit`: numero feature da trasformare in change request, da `1` a `100`;
- `offset`: posizione iniziale nel batch staging;
- `justification`: motivazione leggibile per approvatori.

La pipeline M17:

- richiede accesso all'import e permesso `can_edit` sul layer target;
- accetta solo import `validated` o `published`;
- accetta solo target `source_type=postgis` con geometria configurata;
- legge attributi e geometria dalla staging table;
- crea change request `feature_create` con payload `geometry`, `properties` e
  `source_import`;
- evita duplicati per coppia `import_id` + `feature_seq`;
- salta feature senza geometria;
- scrive audit `change_request.submitted`;
- non modifica il layer ufficiale.

La risposta indica quante richieste sono state create, quante erano gia
presenti, quante feature sono state saltate e se esiste un batch successivo.
L'apply resta governato dal workflow change request: per Catasto resta no-op,
mentre layer ufficiali non Catasto con opt-in controlled edit possono essere
aggiornati realmente da M20 dopo approvazione.

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

## UI Disponibile In M17

Da `/gis/catalogo`, nella scheda `Import shapefile`, l'utente admin carica lo ZIP
e lascia che GAIA proponga i metadati operativi quando possibile:

- ZIP shapefile;
- workspace e dominio dal layer PostGIS riconosciuto nel catalogo;
- nome layer target e titolo visibile dal nome file o dal layer riconosciuto;
- fonte ufficiale default `shapefile_upload`;
- SRID sorgente automatico dal `.prj` quando contiene `AUTHORITY["EPSG", ...]`,
  `ID["EPSG", ...]` o `EPSG:<codice>`; compila il campo solo se GAIA non lo
  riconosce;
- encoding automatico: campo vuoto inviato come valore vuoto intenzionale, quindi
  il backend usa `.cpg` se presente e poi fallback `utf-8`.

I campi tecnici restano modificabili per admin/power user, ma l'utente operativo
non deve compilarli a mano se la proposta e corretta. La UI mostra stato import,
feature count, geometry type, staging table e checksum. Il pulsante `Rigetta
import` chiama il cleanup dello staging finche l'import non e pubblicato.

Subito dopo un upload validato, la UI richiede automaticamente la preview delle
prime 5 feature. Per import `validated` o `published`, resta disponibile anche
`Vedi anteprima staging` per ricaricare manualmente il campione. La preview
mostra:

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

Per import `validated` o `published`, la UI mostra anche `Impatta un layer
ufficiale?`. L'utente sceglie un layer PostGIS editabile, indica batch/offset e
motivazione, poi usa `Crea change request da import`. La UI mostra richieste
create, richieste gia presenti e feature saltate.

## Endpoint Disponibili In M17

Upload:

```http
POST /gis/imports/shapefile
Content-Type: multipart/form-data
```

Campi richiesti:

- `file`: ZIP shapefile;
- `workspace`;
- `target_layer_name`;
- `target_layer_title`.

Campi opzionali:

- `domain_module`;
- `official_source`, default `shapefile_upload`;
- `source_srid`; se omesso, il backend prova a inferirlo dal `.prj`;
- `encoding`; se omesso o inviato vuoto, il validatore usa `.cpg` se presente e
  poi fallback `utf-8`.

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
POST /gis/imports/{import_id}/change-requests
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
- `409` se si prova a creare change request da import non validato o senza
  staging table disponibile;
- `422` se il target non e un layer ufficiale PostGIS geometrico;
- publish ripetuto su import gia `published` torna lo stesso record import.
