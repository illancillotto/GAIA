# GAIA GIS Platform - Piano Territorio Esterno (M21-M25)

> Data: 2026-08-27.
> Scope: estensione della GIS Platform ai layer territoriali esterni, alla
> interrogazione puntuale multi-sorgente e alla scheda territoriale.
> Non e un refactor di `/catasto/gis` ne della governance M1-M20.
>
> Riferimento dati: `docs/GIS_PLATFORM_TERRITORIO_CATALOGO.md`.
> Stato lavori: `docs/GIS_PLATFORM_TERRITORIO_PROGRESS.md`.
> Prompt operativi: `docs/GIS_PLATFORM_TERRITORIO_PROMPTS.md`.

## Stato Di Partenza

Completato su `main` fino a M20:

- modulo `backend/app/modules/gis` con catalogo, permessi, annotazioni, change
  request, import/export shapefile, governance QGIS, POC OGC read-only;
- bootstrap idempotente `ensure_gis_platform_catalog` e
  `ensure_catasto_gis_catalog`;
- dashboard health catalogo deterministico e `runtime_health` con probe
  PostGIS, Martin, QGIS Server e NAS;
- frontend `/gis/catalogo`, `/gis/catalogo/[layerId]`, `/gis/amministrazione`,
  `/gis/strumenti`;
- mappa Catasto `/catasto/gis` su MapLibre con tile Martin serviti da nginx su
  `/tiles/`;
- sincronizzazione AdE via WFS INSPIRE in
  `backend/app/modules/catasto/services/ade_wfs.py`.

## Obiettivo

Portare in GAIA il modello di consultazione territoriale stratificata: layer
esterni governati dal catalogo, interrogazione puntuale che aggrega dato interno
e dato esterno, e una scheda territoriale della particella generabile in PDF.

Il valore non e la cartografia in se - quella e gia pubblicata gratuitamente da
RAS e Agenzia delle Entrate - ma la normalizzazione in un catalogo unico, il
motore di intersezione e il documento di sintesi.

## Principi Di Implementazione

Valgono i principi M1-M20, piu i seguenti.

- Nessun dato esterno viene copiato in PostGIS. Si consuma via proxy GAIA.
- I layer esterni sono sempre read-only: niente change request, niente
  controlled edit, niente export shapefile.
- Ogni sorgente esterna ha timeout proprio e fallisce isolata. La mappa e il
  pannello di interrogazione devono restare usabili con tutte le fonti esterne
  irraggiungibili.
- Lo stato per sorgente e sempre esplicito in risposta: mai un silenzio
  interpretabile come "nessun risultato".
- La licenza e l'attribuzione sono metadata obbligatori, non opzionali.
- GAIA resta autorevole per particelle, distretti, punti di consegna, rete e
  ruolo. Le sorgenti esterne restano autorevoli per il proprio dato.
- Ogni file runtime nuovo o modificato resta al 100% di coverage, secondo la
  policy in `AGENTS.md` e `docs/TEST_COVERAGE_100_PLAN.md`.
- Quality ratchet attivo: il perimetro toccato non puo peggiorare le metriche di
  complessita. `backend/app/modules/gis/services.py` e gia oltre le 3400 righe:
  il codice nuovo va in moduli dedicati, non aggiunto li dentro.

## Fuori Scope

- Riscrittura di `/catasto/gis`.
- Copia locale o mirroring dei dataset regionali.
- Certificati di destinazione urbanistica, pratiche edilizie, tributi comunali,
  usi civici.
- Visure SISTER on-demand dalla mappa: gia coperte dalla pipeline Elaborazioni.
- Copertura nazionale oltre il comprensorio consortile.
- Editing o proposta di modifica su dati di terzi.

---

## M21 - Fondazione Layer Esterni

Stato: da implementare.

Obiettivo: rendere i layer esterni cittadini di prima classe del catalogo, senza
introdurre ancora dati nel seed ne UI di consultazione.

### Backend

Nuovo file `backend/app/modules/gis/external_sources.py`:

- registro delle sorgenti esterne configurate, con `source_key`, base URL,
  servizio (`wms` / `wfs`), versione, timeout e abilitazione;
- validazione degli identificativi remoti e dei parametri ammessi;
- costruzione delle URL remote a partire da layer e richiesta.

Nuovo file `backend/app/modules/gis/external_proxy.py`:

- proxy HTTP verso la sorgente remota con `httpx`, gia dipendenza;
- allowlist rigida di operazioni: `GetMap`, `GetLegendGraphic`,
  `GetFeatureInfo`, `GetCapabilities`, `GetFeature`;
- allowlist di parametri per operazione, per evitare che il proxy diventi un
  open relay;
- timeout per sorgente, con default configurabile;
- cache su filesystem con chiave derivata da layer, operazione e parametri
  normalizzati, e TTL differenziato per categoria di layer;
- audit degli errori, non delle singole tile.

Estensione `backend/app/modules/gis/models.py`:

- nessuna nuova colonna. `source_type` e gia `String(32)` libera e
  `metadata_json` e gia `JSON`. La configurazione del layer esterno vive nei
  metadata.

Estensione `backend/app/modules/gis/schemas.py`:

- `source_type` accetta `wms_external` e `wfs_external`;
- schema `GisExternalLayerConfig` per validare la sezione
  `metadata_json.external`.

Struttura richiesta di `metadata_json.external`:

```json
{
  "source_key": "ras_sitr_vector",
  "service": "wms",
  "version": "1.3.0",
  "remote_layer": "dbu:areebonifica",
  "format": "image/png",
  "transparent": true,
  "srid": 3857,
  "queryable": "wfs_queryable",
  "info_format": "application/json",
  "cache_ttl_seconds": 86400,
  "license": "...",
  "attribution": "..."
}
```

### API

- `GET /gis/external/{layer_id}/wms` - proxy `GetMap`, `GetLegendGraphic`,
  `GetFeatureInfo`;
- `GET /gis/external/{layer_id}/wfs` - proxy `GetFeature`;
- `GET /gis/external/sources` - elenco sorgenti configurate e stato, admin-only.

Entrambi i proxy richiedono `can_view` sul layer e rifiutano layer non attivi.

### Configurazione

Nuove impostazioni in `backend/app/core/config.py`, allineate al pattern
`GIS_*` esistente:

- `GIS_EXTERNAL_LAYERS_ENABLED`, default `false`;
- `GIS_EXTERNAL_CACHE_DIR`;
- `GIS_EXTERNAL_CACHE_MAX_MB`, default `2048`;
- `GIS_EXTERNAL_DEFAULT_TIMEOUT_SECONDS`, default `12`;
- `GIS_EXTERNAL_RAS_VECTOR_URL`;
- `GIS_EXTERNAL_RAS_RASTER_URL`;
- `GIS_EXTERNAL_ADE_WMS_URL`.

Aggiornare `.env.example` con i valori di default e il flag disabilitato.

### Regole

- Con `GIS_EXTERNAL_LAYERS_ENABLED=false` gli endpoint proxy rispondono `503`
  governato e il bootstrap non registra layer esterni.
- Il proxy non inoltra mai header di autenticazione GAIA verso l'esterno.
- Il proxy non accetta URL arbitrarie dal client: la destinazione e determinata
  esclusivamente da `layer_id` e dal registro sorgenti.
- Un layer esterno non puo essere target di change request: il controllo va nel
  punto in cui M4 valida il layer target.
- Un layer esterno non e esportabile: `export.shapefile=false` obbligatorio.
- Un layer esterno non entra nella governance QGIS come tabella
  (`qgis.mode=not_published` per la policy SQL M6).

### Health

Estendere `backend/app/modules/gis/runtime_health.py` con una chiave
`external_sources`. A differenza del dashboard catalogo, che resta
deterministico, qui il probe e reale: `GetCapabilities` con timeout corto e
risultato cachato per almeno 5 minuti, per non trasformare l'apertura della
pagina in un carico verso RAS.

### Test

- `backend/tests/test_gis_external_sources.py`: registro, validazione config,
  costruzione URL.
- `backend/tests/test_gis_external_proxy.py`: allowlist operazioni e parametri,
  cache hit/miss, TTL, timeout, degradazione, rifiuto layer non attivo, rifiuto
  senza `can_view`, comportamento con flag disabilitato.
- Estendere `backend/tests/test_gis_platform_api.py` per i nuovi `source_type` e
  per i divieti su change request ed export.

### Exit Criteria

- `wms_external` e `wfs_external` accettati dal catalogo con validazione della
  sezione `external`.
- Proxy funzionante con cache, timeout e allowlist.
- Nessun layer esterno registrato ancora nel seed.
- Divieti su change request, export shapefile e QGIS governance verificati da
  test.
- Coverage 100% sui file nuovi e modificati.

---

## M22 - Catalogo Territorio E Pannello Strati

Stato: da implementare.

Obiettivo: popolare il catalogo con le sorgenti censite e renderle consultabili
dalla mappa.

### Backend

Nuovo file `backend/app/modules/gis/territorio_bootstrap.py`:

- `ensure_territorio_gis_catalog`, idempotente, sullo stesso pattern di
  `ensure_gis_platform_catalog`;
- definizioni layer prese da `docs/GIS_PLATFORM_TERRITORIO_CATALOGO.md`;
- workspace `territorio`, `domain_module=gis`, `official_source=ras_sitr` o
  `agenzia_entrate`;
- gruppo tematico in `metadata_json.theme`;
- permesso default `viewer` read-only, come per il seed Catasto;
- rifiuto esplicito di una definizione priva di `license` e `attribution`.

Registrare la chiamata in `backend/app/main.py` accanto ai bootstrap esistenti,
condizionata a `GIS_EXTERNAL_LAYERS_ENABLED`.

### API

- `GET /gis/territorio/layers` - elenco layer esterni visibili raggruppati per
  tema, con configurazione client-side gia risolta (URL proxy, opacita default,
  ordine, categoria di interrogabilita).

L'endpoint esiste per non costringere il frontend a ricostruire la
configurazione dai metadata grezzi.

### Frontend

Nuovo componente `frontend/src/components/catasto/gis/TerritorioLayerPanel.tsx`:

- pannello strati richiudibile sulla mappa `/catasto/gis`;
- gruppi tematici in italiano piano, coerenti con la semplificazione UX del
  luglio 2026;
- toggle per layer, slider di opacita, legenda via `GetLegendGraphic`;
- badge esplicito "solo consultazione" e sorgente in evidenza su ogni layer;
- attribuzione visibile in mappa quando almeno un layer esterno e acceso.

Nuovo componente
`frontend/src/components/catasto/gis/OrtofotoStoricheSelector.tsx`:

- selettore anno ortofoto come basemap alternativa;
- confronto a tendina o swipe tra due annate;
- disattivazione automatica quando si torna a OSM o satellite.

Modifiche a `frontend/src/components/catasto/gis/MapContainer.tsx`:

- registrazione dinamica di sorgenti raster WMS puntando al proxy GAIA;
- ordinamento dei layer esterni sotto i layer GAIA, che restano sempre sopra;
- il file e gia a 1552 righe: estrarre la gestione dei layer esterni in un hook
  dedicato invece di gonfiarlo ulteriormente.

### Regole

- I layer esterni non compaiono mai sopra particelle, distretti, punti di
  consegna, canali o rete: il dato GAIA resta leggibile.
- Lo stato acceso/spento e l'opacita sono preferenze utente locali, non stato
  condiviso.
- Un layer esterno irraggiungibile mostra un avviso sul singolo layer, non un
  errore di pagina.
- La descrizione in catalogo di `ras_distretti_irrigui` deve dichiarare che la
  fonte autorevole per il distretto resta GAIA.

### Test

- `backend/tests/test_gis_territorio_bootstrap.py`: idempotenza, rifiuto senza
  licenza, permessi default, raggruppamento tematico.
- `frontend/tests/unit/territorio-layer-panel.test.tsx`: toggle, opacita, stato
  di errore per singolo layer, badge sola consultazione.
- `frontend/tests/unit/ortofoto-storiche-selector.test.tsx`: selezione anno,
  confronto, reset.

### Exit Criteria

- Catalogo `territorio` popolato e visibile in `/gis/catalogo` con i filtri
  esistenti.
- Pannello strati operativo su `/catasto/gis`.
- Ortofoto storiche selezionabili e confrontabili.
- Attribuzione visibile.
- Nessuna regressione sui layer GAIA esistenti.

---

## M23 - Interrogazione Puntuale Multi-Sorgente

Stato: da implementare.

Obiettivo: rispondere alla domanda "cosa insiste su questo punto" aggregando
dato GAIA, dato catastale e dato regionale in una risposta unica e
gerarchizzata.

E la fase che porta il valore centrale del modello. Va progettata, non
configurata.

### Backend

Nuovo package `backend/app/modules/gis/interrogazione/`:

- `__init__.py`;
- `models.py` - dataclass della risposta, per livello e per sorgente;
- `local_probes.py` - interrogazione PostGIS locale;
- `remote_probes.py` - interrogazione WFS e WMS `GetFeatureInfo`;
- `service.py` - orchestrazione, timeout, aggregazione, degradazione.

Il package separato tiene il codice fuori da `services.py`, gia sopra soglia.

Livelli della risposta:

1. `gaia` - particella da `cat_particelle_current`, distretto, punto di consegna
   piu vicino entro raggio configurabile, tratti di `network.rete_condotte`
   entro raggio, DUI da `cat_dui_2026_current`, posizione a ruolo e utenze
   collegate;
2. `catasto_ufficiale` - foglio, mappale, subalterno e zona censuaria da AdE;
3. `territorio` - layer esterni interrogabili abilitati, per gruppo tematico.

Regole di esecuzione:

- le sonde locali usano `ST_Intersects` e `ST_DWithin` con indici gia presenti;
- le sonde remote girano in parallelo con timeout individuale;
- una sonda che fallisce produce un risultato con `status=failed` e messaggio,
  mai un'eccezione che interrompe la risposta;
- il raggio di ricerca per punti di consegna e condotte e un parametro, con
  default configurabile;
- il livello `gaia` non e mai opzionale: se fallisce, la richiesta fallisce.

### API

- `POST /gis/interroga` - corpo con `lon`, `lat`, `srid` opzionale, elenco
  opzionale di layer da interrogare, raggio opzionale;
- risposta con i tre livelli, lo stato per sorgente e il tempo di risposta per
  sorgente.

Restituire sempre `200` con stati per sorgente, tranne quando fallisce il
livello `gaia`.

### Configurazione

- `GIS_INTERROGAZIONE_ENABLED`, default `false`;
- `GIS_INTERROGAZIONE_REMOTE_TIMEOUT_SECONDS`, default `8`;
- `GIS_INTERROGAZIONE_DEFAULT_RADIUS_M`, default `150`;
- `GIS_INTERROGAZIONE_MAX_REMOTE_LAYERS`, default `12`.

### Frontend

Nuovo componente
`frontend/src/components/catasto/gis/InterrogazionePanel.tsx`:

- pannello laterale aperto dal clic su mappa;
- sezioni collassabili per livello, con il livello GAIA sempre aperto;
- stato per sorgente visibile: caricamento, risultato, non disponibile;
- nessuna sezione vuota silenziosa;
- azione verso la scheda territoriale M24 quando la particella e identificata.

Il pannello affianca `ParticellaGisDialog.tsx` esistente, non lo sostituisce: il
popup particella resta il percorso rapido, l'interrogazione e il percorso
istruttorio.

### Test

- `backend/tests/test_gis_interrogazione_local.py`;
- `backend/tests/test_gis_interrogazione_remote.py`, con client HTTP simulato;
- `backend/tests/test_gis_interrogazione_service.py`: parallelismo, timeout,
  degradazione per sorgente, fallimento del livello GAIA, limite layer remoti;
- `frontend/tests/unit/interrogazione-panel.test.tsx`: rendering per stato,
  sezioni collassabili, sorgente non disponibile.

### Exit Criteria

- Un clic su mappa restituisce i tre livelli in un'unica risposta.
- Ogni sorgente esterna ha stato esplicito.
- Con tutte le sorgenti esterne irraggiungibili il pannello resta utile e
  mostra il livello GAIA completo.
- Nessuna regressione su popup particella e selezioni.

---

## M24 - Scheda Territoriale Particella

Stato: da implementare.

Obiettivo: produrre in PDF la sintesi che oggi richiede l'apertura di piu
schermate.

### Backend

Nuovo package `backend/app/modules/gis/scheda_territoriale/`:

- `collector.py` - raccolta dati riusando le sonde M23 sul centroide e
  sull'estensione della particella;
- `renderer.py` - template HTML e resa PDF;
- `service.py` - orchestrazione, permessi, audit.

Resa PDF con Chromium via `playwright`, gia dipendenza usata dalla pipeline
SISTER. Assemblaggio ed eventuale merge con `pypdf`, gia dipendenza. Nessuna
nuova libreria.

Contenuto della scheda:

- identificativi catastali, superficie reale e grafica, comune, distretto;
- intestatari, posizione a ruolo, utenze e punti di consegna serventi;
- coltura dichiarata in DUI a confronto con uso del suolo e colture regionali;
- vincoli e classi di pericolosita intersecanti, con la fonte e la data del
  dato;
- estratto di mappa su ortofoto, con scala e riferimenti;
- attribuzione delle sorgenti;
- disclaimer in chiaro nella prima pagina.

### Disclaimer

Testo obbligatorio, in evidenza e non in nota:

> Documento prodotto da GAIA a fini istruttori interni. Non ha valore
> certificativo. I dati di fonte esterna sono riportati alla data di
> consultazione indicata e restano di titolarita dell'ente che li pubblica.

### API

- `POST /gis/scheda-territoriale` - genera la scheda per una particella,
  restituisce l'identificativo del documento;
- `GET /gis/scheda-territoriale/{scheda_id}` - stato e metadata;
- `GET /gis/scheda-territoriale/{scheda_id}/pdf` - download.

Generazione asincrona: la resa Chromium piu le sonde remote non sta in una
richiesta sincrona ragionevole.

### Persistenza

Nuova tabella `gis_schede_territoriali` con migration dedicata, naming
coerente: `20260901_0900_gis_schede_territoriali.py`.

Campi: id, particella di riferimento, richiedente, stato, path artifact,
checksum, snapshot JSON delle sorgenti interrogate con esito, timestamp.

Lo snapshot delle sorgenti e la parte che rende la scheda difendibile: senza,
non si puo ricostruire cosa fosse disponibile al momento della generazione.

### Regole

- Richiede `can_view` sui layer coinvolti; i layer non autorizzati sono esclusi
  dalla scheda e la esclusione e dichiarata nel documento.
- Audit `scheda_territoriale.requested`, `.completed`, `.failed`.
- Riuso dell'`artifact_storage.py` esistente per la persistenza del file.
- Retention configurabile, sullo stesso pattern della retention export M10.

### Test

- `backend/tests/test_gis_scheda_collector.py`;
- `backend/tests/test_gis_scheda_renderer.py`, con Chromium simulato;
- `backend/tests/test_gis_scheda_service.py`: permessi, esclusione layer non
  autorizzati, audit, stati, retention;
- `frontend/tests/unit/scheda-territoriale.test.tsx`.

### Exit Criteria

- Scheda generabile da mappa e da anagrafica particella.
- PDF con disclaimer, attribuzione e snapshot sorgenti.
- Layer non autorizzati esclusi e dichiarati.
- Audit completo.

---

## M25 - Strumenti Di Campo E Propagazione QGIS

Stato: da implementare.

Obiettivo: rifinitura. Nessuna di queste voci e bloccante per le precedenti.

### Frontend

- misura di distanze e aree su mappa, come estensione di
  `frontend/src/components/catasto/gis/DrawingTools.tsx`;
- confronto diacronico ortofoto con slider per annata;
- layout di stampa con scala, legenda, intestazione consortile e attribuzione.

### Backend

- inclusione dei layer esterni nel progetto QGIS generato da M16, come sorgenti
  WMS che puntano al proxy GAIA;
- il progetto resta filtrato sui layer visibili all'utente.

### Exit Criteria

- Misure disponibili e coerenti con la proiezione della mappa.
- Confronto ortofoto operativo.
- Progetto QGIS include i layer territoriali visibili.

---

## Ordine Di Esecuzione

M21 e M22 vanno eseguite come slice unica: M21 senza M22 non produce nulla di
osservabile, e M22 senza M21 non ha dove appoggiarsi.

M23 va aperta solo quando il catalogo esterno e popolato e si sa quali sorgenti
rispondono in tempi accettabili nell'uso reale.

M24 richiede M23 completa. M25 e indipendente e puo slittare.

## Decisione Preliminare Bloccante

La verifica delle licenze delle sorgenti va chiusa prima del seed M22. E l'unico
vincolo che, se scoperto tardi, obbliga a smontare lavoro gia fatto. La
decisione e le evidenze vanno registrate nel progress.

## Rischi

- Dipendenza da servizi senza SLA. Mitigazione: cache, timeout per sorgente,
  degradazione visibile, probe health cachato.
- Prestazioni dei WMS raster storici. Mitigazione: TTL lungo per dato
  immutabile, valutazione di un precaricamento limitato alla bounding box del
  comprensorio.
- Confusione per utenti non tecnici: rischio concreto che un operatore creda di
  poter proporre una change request su un vincolo regionale. Mitigazione: badge
  esplicito, linguaggio piano, divieti applicati anche lato API.
- Disallineamento tra distretti RAS e distretti GAIA. Mitigazione: dichiarare
  in catalogo che la sovrapposizione e informativa e che GAIA resta autorevole.
- Espansione incontrollata del catalogo: con 379 layer disponibili ogni ufficio
  ne vorra uno. Mitigazione: aggiunta solo su richiesta motivata con caso d'uso
  operativo dichiarato.
- Crescita di `services.py` e `MapContainer.tsx`, entrambi gia sopra soglia.
  Mitigazione: package e hook dedicati, mai aggiunta ai file esistenti.
