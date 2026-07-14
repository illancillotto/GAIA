# GAIA GIS Platform - Shapefile Import Runbook

> Data: 2026-07-14.
> Scope: percorso governato per importare shapefile nella GIS Platform.

## Stato M12

M12 documenta e mostra il workflow nella UI `/gis/catalogo`. Non esistono ancora
endpoint backend attivi per upload, staging o publish automatico dello shapefile:
le CTA frontend restano informative/disabilitate finche la pipeline runtime non
viene implementata.

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

La pipeline backend futura deve bloccare o segnalare:

- ZIP incompleto;
- geometrie invalide o miste non dichiarate;
- SRID assente o incoerente con `.prj`;
- encoding non determinabile;
- campi DBF duplicati, troncati o incompatibili con PostGIS;
- feature count nullo o superiore alla soglia configurata;
- assenza di workspace o dominio proprietario.

## Staging PostGIS

Il caricamento deve avvenire prima in staging PostGIS non distruttivo:

- schema o tabella temporanea dedicata all'import;
- nessuna scrittura immediata sui layer ufficiali;
- anteprima attributi/geometrie prima del publish;
- report di validazione scaricabile o visibile da UI;
- pulizia dello staging dopo publish, reject o scadenza.

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

## Endpoint Futuri

La pipeline backend puo essere introdotta con:

```http
POST /gis/imports/shapefile
GET /gis/imports/{import_id}
POST /gis/imports/{import_id}/validate
POST /gis/imports/{import_id}/publish
POST /gis/imports/{import_id}/reject
```

Gli endpoint devono applicare permessi GIS, audit e limiti dimensionali prima di
abilitare l'upload in UI.
