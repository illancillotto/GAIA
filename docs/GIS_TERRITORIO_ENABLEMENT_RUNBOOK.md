# GAIA GIS Platform - Territorio Enablement Runbook

> Data: 2026-08-31.
> Scope: attivazione per ambiente dei layer territoriali esterni e
> dell'interrogazione puntuale.

## Principi Operativi

- I flag restano `false` negli esempi del repository. Si impostano solo nella
  configurazione dell'ambiente dopo gli smoke test previsti.
- I dati RAS e AdE restano sulle sorgenti originali. Il proxy GAIA applica
  permessi, cache e timeout; nessun dato esterno viene copiato in PostGIS.
- I layer esterni sono read-only e non entrano in change request, export
  shapefile o editing QGIS.
- L'indisponibilita di una sorgente esterna degrada la consultazione ma non
  rende indisponibili i dati GAIA.
- La scheda territoriale e un supporto istruttorio con disclaimer. Non e un
  CDU e non certifica vincoli.

## Prerequisiti

1. Verificare backup, connessione database e disponibilita dello storage
   `GIS_SCHEDA_ARTIFACT_ROOT`.
2. Applicare almeno la migration `20260901_0900_gis_schede_territoriali`:

```bash
cd backend
.venv/bin/alembic upgrade 20260901_0900
.venv/bin/alembic current
```

3. Verificare che l'utente di smoke abbia `module_gis` e permesso `can_view`
   sui layer da provare.
4. Verificare che `GIS_EXTERNAL_CACHE_DIR` esista e sia scrivibile dal backend.

## Parametri Operativi

| parametro | default | comportamento |
| --- | --- | --- |
| `GIS_EXTERNAL_CACHE_DIR` | `/data/gis/external-cache` | cache filesystem atomica del proxy |
| `GIS_EXTERNAL_CACHE_MAX_MB` | `2048` | pruning quando la cache supera il limite |
| `GIS_EXTERNAL_DEFAULT_TIMEOUT_SECONDS` | `12` | timeout massimo della richiesta proxy |
| health sorgenti esterne | `300 s` | TTL interno del risultato GetCapabilities |
| TTL layer vettoriali | `3600 s` | TTL configurato nel catalogo |
| TTL layer raster | `86400 s` | TTL configurato nel catalogo |
| `GIS_INTERROGAZIONE_REMOTE_TIMEOUT_SECONDS` | `8` | timeout per singola sonda remota |
| `GIS_INTERROGAZIONE_MAX_REMOTE_LAYERS` | `12` | massimo layer remoti per interrogazione |

Non aggiungere retry ravvicinati verso AdE. Dopo un timeout o un errore remoto,
lasciare che la risposta governata e la cache health espongano la degradazione.

## Sequenza Di Attivazione

### 1. Abilitare Il Catalogo Esterno

Impostare nell'ambiente di deploy, non in `.env.example`:

```dotenv
GIS_EXTERNAL_LAYERS_ENABLED=true
GIS_INTERROGAZIONE_ENABLED=false
```

Riavviare il backend. `_ensure_gis_catalogs` esegue al boot il seed idempotente
del catalogo Territorio. Un secondo riavvio non deve creare duplicati.

### 2. Smoke Health E Proxy

Usare un token GAIA valido:

```bash
export GAIA_BASE_URL="https://gaia.example.local/api"
export GAIA_TOKEN="<token>"
curl -fsS -H "Authorization: Bearer $GAIA_TOKEN" \
  "$GAIA_BASE_URL/gis/runtime-health"
curl -fsS -H "Authorization: Bearer $GAIA_TOKEN" \
  "$GAIA_BASE_URL/gis/territorio/layers"
```

In `runtime_health.external_sources` verificare:

- `ok`: tutte le sorgenti rispondono;
- `unreachable`: almeno una sorgente non risponde; vedere
  `details.sources` prima di proseguire;
- `disabled`: il flag non e stato applicato al processo backend.

Rieseguire un GetCapabilities diretto per ciascuna sorgente configurata:

```bash
curl -fsS "$GIS_EXTERNAL_RAS_VECTOR_URL?SERVICE=WMS&REQUEST=GetCapabilities&VERSION=1.3.0" >/dev/null
curl -fsS "$GIS_EXTERNAL_RAS_RASTER_URL?SERVICE=WMS&REQUEST=GetCapabilities&VERSION=1.3.0" >/dev/null
curl -fsS "$GIS_EXTERNAL_ADE_WMS_URL?SERVICE=WMS&REQUEST=GetCapabilities&VERSION=1.3.0" >/dev/null
```

Dal catalogo scegliere un `layer_id` visibile e provare il proxy governato:

```bash
export GIS_LAYER_ID="<layer-id>"
curl -fsS -D /tmp/gaia-gis-proxy-headers \
  -H "Authorization: Bearer $GAIA_TOKEN" \
  "$GAIA_BASE_URL/gis/external/$GIS_LAYER_ID/wms?REQUEST=GetCapabilities" \
  >/dev/null
rg "X-GAIA-External-Cache" /tmp/gaia-gis-proxy-headers
```

Non abilitare l'interrogazione finche catalogo e almeno le sorgenti necessarie
allo smoke non risultano disponibili.

### 3. Abilitare L'Interrogazione

Impostare nell'ambiente:

```dotenv
GIS_EXTERNAL_LAYERS_ENABLED=true
GIS_INTERROGAZIONE_ENABLED=true
```

Riavviare il backend e provare un punto noto nel comprensorio:

```bash
curl -fsS -X POST \
  -H "Authorization: Bearer $GAIA_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"lon":8.59,"lat":39.91,"layer_ids":[]}' \
  "$GAIA_BASE_URL/gis/interroga"
```

La risposta deve contenere i tre livelli `gaia`, `catasto_ufficiale` e
`territorio`. Una tabella `rete_condotte` vuota deve produrre lo stato `empty`
con `Nessuna condotta nel raggio.`, non una failure GAIA.

Infine, dalla mappa o dall'anagrafica di una particella nota:

1. avviare `POST /gis/scheda-territoriale`;
2. verificare il polling `queued`, `processing`, `completed`;
3. scaricare il PDF;
4. verificare disclaimer, attribuzioni ed eventuali esclusioni o sorgenti non
   raggiungibili nello snapshot.

## Degradazione Governata

- Con entrambi i flag spenti, catalogo/proxy e interrogazione rispondono `503`
  con un messaggio italiano esplicito; pannello strati e health mostrano che la
  consultazione non e attiva nell'ambiente.
- Se RAS o AdE sono irraggiungibili, l'health espone `unreachable`. Proxy e
  singole sonde remote restituiscono l'errore governato gia previsto da M21 e
  M23, senza retry aggressivo.
- Le sorgenti remote falliscono in modo isolato. I risultati GAIA disponibili
  restano leggibili e la scheda dichiara le esclusioni nello snapshot.
- Se il catalogo contiene zero righe prima del primo boot con flag attivo, il
  seed viene eseguito al riavvio. Non importare manualmente `rete_condotte` come
  parte di questa procedura.

## Rollback

1. Impostare `GIS_INTERROGAZIONE_ENABLED=false` e riavviare il backend.
2. Verificare che `POST /gis/interroga` risponda `503` governato e che le
   funzioni GAIA non territoriali restino operative.
3. Impostare `GIS_EXTERNAL_LAYERS_ENABLED=false` e riavviare il backend.
4. Verificare `runtime_health.external_sources.status=disabled` e il messaggio
   esplicito nel pannello strati.

Il rollback non cancella righe catalogo, cache o schede gia generate. La cache
puo essere rimossa solo con una procedura operativa separata, dopo aver fermato
il backend e verificato il percorso configurato.

## Checklist Finale

- Migration schede applicata.
- Directory cache e artifact scrivibili.
- Seed Territorio idempotente completato al boot.
- Health esterno `ok`, oppure degradazione `unreachable` accettata e annotata.
- GetCapabilities RAS vettoriale, RAS raster e AdE verificati.
- Proxy autenticato verificato senza chiamate browser dirette alle sorgenti.
- Interrogazione e caso rete vuota verificati.
- Scheda PDF verificata con disclaimer e attribuzioni.
- Procedura di rollback provata o approvata per l'ambiente.
