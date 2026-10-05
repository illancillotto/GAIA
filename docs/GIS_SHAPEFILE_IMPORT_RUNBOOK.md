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

Da `/gis/catalogo`, aprendo la sezione richiudibile `Strumenti per utenti
esperti` e poi la scheda `Carica shapefile da ZIP`, l'utente admin carica lo ZIP
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
prime 5 feature e apre una modal `Anteprima staging`. Per import `validated` o
`published`, resta disponibile anche `Vedi anteprima staging` per ricaricare
manualmente il campione, mentre `Apri anteprima GIS` riapre la modal gia
caricata. La preview mostra:

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

L'encoding esplicito viene ripulito dagli spazi e prevale sul CPG; un CPG
vuoto ricade su `utf-8`. Il report include `cpg_missing` solo quando manca
il componente, non quando e presente ma vuoto. Include `encoding_overridden`
solo se il CPG non vuoto differisce dall'encoding selezionato, confrontando
senza distinguere maiuscole/minuscole. I warning non bloccano l'import.
La caratterizzazione del 2026-10-02 verifica questi contratti su ZIP reali;
non introduce cambi alla validazione, agli errori o ai permessi.

### Caratterizzazione del servizio

La tranche del 2026-10-03 mantiene il runtime invariato e aggiunge contratti
su lifecycle annotazioni/change request, isolamento dei layer, input invalidi,
persistenza e audit. Le patch che ripropongono gli stessi valori non devono
inventare campi cambiati nell'audit; un reset nullable degli allegati viene
registrato come modifica e persiste una lista vuota. Gli stati terminali e
i target mancanti continuano
a rifiutare le operazioni. Una richiesta emendata torna `submitted` e azzera
il precedente review; una failure di apply non deve registrare successo.
I test usano sessioni SQLite reali e controllano i dati dopo commit/rollback,
non certificano l'integrazione live con PostGIS o QGIS Desktop.

Per misurare i file completi `app.modules.gis.services` e
`app.modules.gis.shapefile_validation`, eseguire il corpus GIS e
Catasto GIS insieme, non soltanto `test_gis_platform_api.py`:

```bash
run_dir=$(mktemp -d /tmp/gaia-gis-coverage.XXXXXX)
PYTHONPATH=backend COVERAGE_FILE="$run_dir/.coverage" backend/.venv/bin/python -m pytest \
  -q -o addopts='' backend/tests/test_gis*.py backend/tests/test_catasto_gis*.py \
  --cov=app.modules.gis.services --cov=app.modules.gis.shapefile_validation \
  --cov-branch --cov-fail-under=100 \
  --cov-report=term-missing --cov-report=json:"$run_dir/coverage.json"
```

Verificare l'exit code dei test e i branch nel JSON: la percentuale di coverage
da sola non dimostra che tutte le asserzioni siano passate. Evidenze e stato
del gate sono registrati in `docs/code-quality/PROGRESS.md`.

Esito della sola caratterizzazione del 2026-10-03: 287 test passati, statement `1076/1076` e
branch `328/328` del servizio (100% full-file), senza esclusioni.
Il requisito inizialmente bloccato dalla misura API parziale e soddisfatto
dal corpus completo; in quella tranche nessuna semplificazione runtime e
stata applicata.

La successiva slice ZIP del 2026-10-03 costruisce i warning con due condizioni
ordinate nella stessa funzione, senza helper e senza cambiare i contratti
descritti sopra. La validazione, i failure HTTP, le autorizzazioni e lo staging
rimangono invariati. Il corpus finale comprende ancora 287 test passati e
coverage full-file 100%: statement `1072/1072`, branch `324/324`.
La cognitiva del validatore scende da 25 a 23, la ciclomatica da 22 a 21;
resta debito legacy, non e un risanamento dell'intero servizio.

La seconda slice ZIP consolida il solo confronto `encoding_overridden`:
un CPG normalizzato appartenente ai valori ammessi (vuoto o encoding
selezionato normalizzato) non genera il warning; gli altri lo generano.
La matrice di nove ZIP reali verifica anche CPG vuoto con ISO-8859-1
esplicito e casing misto del CPG. Nove test passano prima e dopo.
Stato dopo la seconda slice: cognitiva `21`, ciclomatica `19`, LOC `62`; nessun helper,
guardia rimossa o cambio funzionale. Il corpus finale e di 289 test passati,
con statement `1072/1072` e branch `324/324` (100% full-file).
Resta debito legacy ciclomatico, non dichiarato chiuso.

La successiva riorganizzazione separa due responsabilita in
`shapefile_validation.py`: selezione di un unico stem completo e lettura/
normalizzazione dei record pyshp. Il serializzatore JSON condiviso conserva
l'alias `_jsonable_record` nel servizio. L'orchestratore conserva ordine degli
errori, precedenza SRID/encoding, warning, bbox, report e checksum. Nessun
controllo sugli input e rimosso. Il conteggio delle feature usa i record
normalizzati, mantenendo anche quelli con geometria NULL.

Gli 11 casi aggiuntivi su ZIP reali caratterizzano cardinalita, componenti
appartenenti a stem diversi, ordine dei componenti mancanti, DBF Latin-1,
date/numeri/null, geometrie miste o tutte NULL, header corrotto, errori di
decodifica, codec sconosciuto e shapefile vuoto. Passano anche sul validatore
originale. Per shapefile tutti NULL, pyshp restituisce una bbox di quattro
zeri: questo comportamento e preservato, non trasformato in bbox assente.

Le tre responsabilita hanno cognitiva/ciclomatica/LOC rispettivamente
`7/8/33` (orchestratore), `4/5/15` (componenti), `10/8/35` (lettura).
Nessuna supera le soglie. E una `REORGANIZED_AND_CHARACTERIZED`: le decisioni
di dominio non sono eliminate e gli aggregati cognitivi restano invariati.
Il resto del debito legacy del servizio e fuori da questa slice.

Gate finale della riorganizzazione: 300 test passati, servizio al 100%
statement `1050/1050` e branch `314/314`, modulo estratto al 100%
statement `34/34` e branch `10/10`. Nessuna esclusione o test saltato.
Ratchet e Ruff mirati verdi; i gate globali sul checkout condiviso restano
bloccati fuori GIS, come registrato in `docs/code-quality/PROGRESS.md`.

### Accesso e lifecycle

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
