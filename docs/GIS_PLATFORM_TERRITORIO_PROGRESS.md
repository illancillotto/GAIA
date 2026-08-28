# GAIA GIS Platform - Progress Territorio Esterno

> Ultimo aggiornamento: 2026-08-28.
> Branch corrente: `feature/gis-territorio-interrogazione-m23`.
>
> Piano tecnico: `docs/GIS_PLATFORM_TERRITORIO_PLAN.md`.
> Riferimento dati: `docs/GIS_PLATFORM_TERRITORIO_CATALOGO.md`.
> Prompt operativi: `docs/GIS_PLATFORM_TERRITORIO_PROMPTS.md`.

## Stato Sintetico

P0 e completato. Licenze, attribuzioni, disponibilita e tempi delle sorgenti
sono stati verificati; il seed documentale e stato ristretto a `21` layer
ammissibili (`14` RAS vettoriali, `4` RAS raster, `3` AdE).

P1 e implementato: registro sorgenti, proxy governato, cache, health, nuovi
source type e divieti backend sono coperti al `100%`. La change quality separata
e stata integrata in `main` a `3d373f28`; M21 e stata riallineata, congelata nel
commit `07d9f7c4` e chiusa con ratchet verde.

P2 e completato sul branch `feature/gis-territorio-catalog-seed-m22`: il seed
idempotente registra i `21` layer ammessi e `GET /gis/territorio/layers`
restituisce solo quelli attivi e visibili, raggruppati per tema.

P3 e completato sul branch `feature/gis-territorio-layer-panel-m22`: pannello,
opacita, legende autenticate, attribuzioni e selettore ortofoto sono integrati
nelle mappe Catasto senza modificare l'hotspot `MapContainer.tsx`.

P4/M23a e completato sul branch
`feature/gis-territorio-interrogazione-m23`: `POST /gis/interroga` aggrega le
sonde GAIA e le sorgenti remote nei livelli `gaia`, `catasto_ufficiale` e
`territorio`. M23b-M25 non sono ancora avviate.

La base M1-M20 della GIS Platform e in esercizio e non richiede modifiche
preliminari: `source_type` e gia una colonna `String(32)` libera in `GisLayer` e
`metadata_json` e gia `JSON`, quindi M21 non necessita di migration dello
schema catalogo.

## Milestone

| milestone | contenuto | stato | branch |
| --- | --- | --- | --- |
| P0 | Verifica licenze e disponibilita sorgenti | completato il 2026-08-27 | - |
| M21 | Fondazione layer esterni: source type, proxy, cache, health | completata il 2026-08-28 con ratchet verde | `feature/gis-territorio-external-layers-m21` |
| M22a | Seed catalogo `territorio` e `GET /gis/territorio/layers` | completata il 2026-08-28 con ratchet verde | `feature/gis-territorio-catalog-seed-m22` |
| M22b | Pannello strati e ortofoto storiche in mappa | completata il 2026-08-28 con ratchet verde | `feature/gis-territorio-layer-panel-m22` |
| M23a | Interrogazione puntuale multi-sorgente, backend | completata il 2026-08-28 con ratchet verde | `feature/gis-territorio-interrogazione-m23` |
| M23b | Pannello interrogazione, frontend | da implementare | `feature/gis-territorio-interrogazione-ui-m23` |
| M24 | Scheda territoriale particella in PDF | da implementare | `feature/gis-territorio-scheda-m24` |
| M25 | Strumenti di campo e propagazione QGIS | da implementare | `feature/gis-territorio-strumenti-m25` |

## Analisi Preliminare Completata

Data: 2026-08-27.

Censimento sorgenti eseguito interrogando direttamente i documenti
GetCapabilities:

- RAS SITR GeoServer vettoriale: `379` layer nel namespace `dbu:`, WMS 1.3.0 e
  WFS 1.1.0 sullo stesso endpoint;
- RAS SITR GeoServer raster: ortofoto storiche dal volo 1940-45 al 2022, DTM e
  DSM da rilievo LiDAR a 1m e 10m, CTR, mosaici DBGT;
- Agenzia delle Entrate Cartografia Catastale INSPIRE: `CP.CadastralParcel`,
  `CP.CadastralZoning`, `fabbricati`, `acque`, `strade`, `vestizioni`,
  `province`, `codice_plla`, `simbolo_graffa`.

Layer ammessi nel seed verificati esistenti con titolo confermato dalla
sorgente. P0 ha corretto tre `remote_layer` DTM che erano nomi di stile WMS e ha
escluso tre layer PAI e sette ortofoto senza licenza accertabile per GAIA. Il
dettaglio e in `docs/GIS_PLATFORM_TERRITORIO_CATALOGO.md`.

Constatazione rilevante per il dominio: il GeoServer RAS pubblica
`agr_consorzi_irrigui_bonif_comprensori`, `agr_consorzi_irrigui_bonif_distretti`
e `areebonifica`, cioe la delimitazione regionale degli stessi oggetti che GAIA
governa internamente. La sovrapposizione e utile come controllo, ma richiede una
decisione esplicita di autorevolezza prima del seed.

## Verifiche

Verifiche P4 eseguite il 2026-08-28:

- tre suite obbligatorie: `13 passed` su sonde locali, sonde remote e servizio;
- suite integrata con config, sorgenti esterne e API GIS: `91 passed`;
- coverage sui runtime modificati: `1129` statement, `0` mancanti, totale
  `100%`;
- `make lint-backend`: exit `0`;
- `make quality-test`: `46 passed`;
- `make complexity-ratchet
  BASE_REF=feature/gis-territorio-layer-panel-m22`: exit `0`, baseline commit
  `2b6f5651`, nessun finding;
- `make graphify-backend`: exit `0`, `7209` nodi, `17448` archi e `427`
  community;
- `make graphify-platform-docs`: exit `0`, `388` nodi, `480` archi e `54`
  community;
- `git diff --check`: exit `0`.

Il primo ratchet P4 ha rilevato una sola regressione file-level in
`backend/app/core/config.py`, LOC `653 -> 661`. La baseline non e stata
aggiornata. Le impostazioni GIS esterne M21 e le nuove impostazioni M23 sono
state riallocate nel mixin esistente `app/core/gis_settings.py`, senza cambiare
alias, default o validazioni; il ratchet successivo e verde. `services.py`, il
popup Catasto e il frontend sono invariati.

Decisioni M23a:

- ogni sonda restituisce `ok`, `empty`, `failed` o `skipped`, durata, dati e
  messaggio; solo il fallimento del livello locale GAIA produce errore API;
- le sonde WFS usano un filtro spaziale `BBOX`, le sonde WMS usano
  `GetFeatureInfo`; JSON e testo/HTML sono normalizzati;
- `wms_visual_only` non genera HTTP e i layer interrogabili oltre il limite
  restano visibili come `skipped`, senza omissioni silenziose;
- AdE confluisce in `catasto_ufficiale`; gli altri layer ammessi confluiscono
  in `territorio`; i layer senza `can_view` non compaiono;
- `ST_DWithin` misura in EPSG:32632 e usa un pre-filtro bbox 4326 per attivare
  gli indici GiST esistenti.

Verifiche P3 eseguite il 2026-08-28:

- `npm run typecheck`: exit `0`;
- `npm run lint`: exit `0`; restano solo warning preesistenti fuori dal
  perimetro P3;
- suite unit frontend completa: `178` file e `1626` test verdi, inclusa la
  regressione `gis-tools-workspace.test.tsx`;
- coverage sui runtime P3: `211/211` statement, `106/106` branch, `82/82`
  funzioni e `171/171` linee, totale `100%`;
- `npm run build`: exit `0`, `154` pagine generate; il chunk compilato contiene
  il registry `territorio-source-`, confermando l'integrazione nella build;
- `make complexity-ratchet
  BASE_REF=feature/gis-territorio-catalog-seed-m22`: exit `0`, baseline commit
  `d7861d06`, nessun finding;
- `git diff --check`: exit `0`.

Il primo ratchet P3 ha rifiutato correttamente callable nuove oltre soglia e un
inserimento nel client GIS legacy che alterava il matching. La versione finale
separa catalogo, sincronizzazione MapLibre, errori, legende e cleanup in hook
sotto soglia, usa `frontend/src/lib/api/territorio.ts` e non modifica
`MapContainer.tsx`, `page.tsx` o `api/gis.ts`.

Le tile e le legende usano sempre il proxy GAIA con bearer token; nessun URL
remoto e inviato dal browser. Ogni raster e inserito prima del primo layer GAIA
e una failure aggiorna solo lo stato del layer coinvolto. Il selettore supporta
il confronto tra piu annate, ma segnala correttamente che il seed corrente ne
contiene una sola perche P0 ha escluso le altre per licenza.

Verifiche P2 eseguite il 2026-08-28:

- bootstrap eseguito due volte nei test: `21` layer creati alla prima
  esecuzione, `0` alla seconda;
- suite GIS, bootstrap e lifespan: verde;
- coverage selettiva sui runtime modificati: `745` statement, `0` mancanti,
  totale `100%`;
- `main.py`: `74/74`, `router.py`: `153/153`, `schemas.py`: `432/432`,
  `territorio_bootstrap.py`: `60/60`, `territorio_catalog.py`: `26/26`;
- `make lint-backend`: exit `0`;
- `make quality-test`: `46 passed`;
- `make complexity-ratchet
  BASE_REF=feature/gis-territorio-external-layers-m21`: exit `0`, baseline
  commit `dddbbe58`, nessun finding;
- `git diff --check`: exit `0`.

Il primo ratchet P2 ha correttamente rifiutato un conditional aggiunto alla
callable legacy `_ensure_gis_catalog_on_startup` e un factory con `11`
parametri. Il bootstrap territorio e stato quindi isolato in una callable
nuova e il factory ridotto a cinque campi obbligatori piu opzioni; il ratchet
finale e verde senza aggiornare la baseline.

Verifiche P1 eseguite il 2026-08-28:

- `make lint-backend`: exit `0`;
- suite M21 mirata su config, runtime health, sorgenti, proxy e API GIS: verde;
- coverage selettiva sui runtime modificati: `2403` statement, `0` mancanti,
  totale `100%`;
- `external_sources.py`: `98/98`, `100%`;
- `external_proxy.py`: `202/202`, `100%`;
- `config.py`: `283/283`, `schemas.py`: `412/412`, `router.py`: `150/150`,
  `runtime_health.py`: `132/132`, `services.py`: `1126/1126`;
- `make complexity-ratchet BASE_REF=main`: exit `0`, merge-base
  `3d373f28dbabeb475efbc5dfd41d53f4d8066586`, nessun finding;
- `make quality-test`: `46 passed`;
- `git diff --check`: exit `0`.

### Audit Del Drift E Chiusura Ratchet, 2026-08-28

Il primo ratchet rosso non e stato risolto rigenerando la baseline. P1 e rimasta
congelata mentre il drift preesistente e stato analizzato sul branch separato
`quality/gis-services-baseline-drift-20260828`, a partire dalla baseline sorgente
`b1d4a988`.

Evidenze:

- tutto il drift GIS preesistente deriva da `268234f9`;
- `services.py` era cresciuto da `2304` a `3145` LOC: `+841`, non `+834`;
- `74` callable, per `521` LOC aggiunte, hanno fingerprint AST identico e sono
  state classificate come sola riformattazione;
- `_default_export_path` aveva una regressione reale di `+1` cyclomatic, `+1`
  cognitive e `+6` LOC;
- nove callable erano nuove, per `301` LOC; le nuove violation reali erano in
  `_feature_selector_columns` e `list_layer_features`;
- non sono emersi errori di matching.

La change quality ha separato settings, query, costruzione delle response e
supporto, ripristinando la formattazione AST-equivalente e creando headroom
reale. I commit `691bec1d`, `be143751` e `3d373f28` sono stati integrati in
`main`; la baseline `config/code-quality/complexity-baseline.json` e rimasta
invariata.

`make complexity-baseline` e stato tentato soltanto dopo il ratchet verde, ma
ha rifiutato correttamente l'aggiornamento per oltre cento regressioni non
classificate fuori dal perimetro GIS. Nessun JSON e stato modificato
manualmente. Dopo il riallineamento, M21 e stata congelata in `07d9f7c4` e il
ratchet autorevole contro `main` e passato senza finding.

Comando coverage eseguito:

```bash
cd backend && .venv/bin/python -m pytest -q \
  tests/test_config.py tests/test_gis_runtime_health.py \
  tests/test_gis_external_sources.py tests/test_gis_external_proxy.py \
  tests/test_gis_platform_api.py \
  --cov=app.core.config --cov=app.modules.gis.schemas \
  --cov=app.modules.gis.router --cov=app.modules.gis.runtime_health \
  --cov=app.modules.gis.services --cov=app.modules.gis.external_sources \
  --cov=app.modules.gis.external_proxy --cov-report=term-missing
```

Verifiche di sorgente eseguite il 2026-08-27:

- GetCapabilities WMS RAS vettoriale: risposta valida, `379` layer.
- GetCapabilities WMS RAS raster: risposta valida, serie ortofoto e DTM
  presenti.
- GetCapabilities WMS AdE Cartografia Catastale: risposta valida, layer INSPIRE
  presenti.

Verifiche P0 eseguite il 2026-08-27:

- GetCapabilities WMS RAS vettoriale: HTTP valido, `379` layer `dbu:`; tutti i
  `14` layer ammessi presenti;
- GetCapabilities WMS RAS raster: HTTP valido, `52` layer; tutti i `4` layer
  ammessi presenti dopo la correzione dei tre nomi DTM;
- GetCapabilities WMS AdE: HTTP valido, `13` layer nominati; tutti i `3` layer
  ammessi presenti;
- controllo metadati GeoNetwork per tutti i candidati RAS: `14` vettoriali,
  ortofoto 1977-78 e tre DTM con CC BY 4.0; tre record PAI in `404`; sette
  ortofoto con autorizzazione del proprietario richiesta o copyright;
- condizioni AdE: CC BY 4.0, titolarita AdE da citare, limite concorrente non
  quantificato e possibile limitazione dell'accesso per uso disturbante;
- condizioni RAS WFS: massimo `100000` feature per richiesta; nessun rate limit
  WMS numerico pubblicato.

Comandi di evidenza, eseguiti dalla root del repository:

```bash
curl -sS "https://webgis.regione.sardegna.it/geoserver/ows?service=WMS&version=1.3.0&request=GetCapabilities"
curl -sS "https://webgis.regione.sardegna.it/geoserverraster/ows?service=WMS&request=GetCapabilities"
curl -sS "https://wms.cartografia.agenziaentrate.gov.it/inspire/wms/ows01.php?service=WMS&request=GetCapabilities&version=1.3.0"
```

Confronto dei `Name` figli diretti di `Layer` dopo l'applicazione delle
decisioni P0: RAS vettoriale `seed=14 missing=0`, RAS raster `seed=4 missing=0`,
AdE `seed=3 missing=0`.

Tempi misurati con tre richieste seriali per riga; valori mediani, con tutte le
risposte HTTP 200:

| layer | GetMap | GetFeature |
| --- | --- | --- |
| `dbu:areebonifica` | `0.732 s` | `0.276 s` |
| `dbu:agr_consorzi_irrigui_bonif_comprensori` | `0.427 s` | `0.600 s` |
| `dbu:usosuolo2008_areali` | `0.273 s` | `0.304 s` |
| `raster:ortofoto_1977_1978` | `0.545 s` | non applicabile |
| `CP.CadastralParcel` | `0.223 s` | non misurato in P0 |

Intervalli, payload e metodologia sono registrati nella sezione "Licenze" del
catalogo. Le misure supportano il default M21 di `12 s`, senza costituire SLA.
Non e stato eseguito un test concorrente: P0 doveva rilevare, non sollecitare, i
servizi pubblici e AdE dichiara esplicitamente un limite concorrente.

## Decisioni P0

- RAS SITR vettoriale: `ammessa con vincoli`. Entrano solo i `14` layer con
  metadato CC BY 4.0; attribuzione RAS obbligatoria e massimo `100000` feature
  per richiesta WFS.
- RAS SITR raster: `ammessa con vincoli`. Entrano ortofoto 1977-78 e i tre DTM
  corretti, tutti CC BY 4.0. Restano escluse le ortofoto 2022, 2019, 2013,
  2006, 1997, 1954-55 e 1940-45 per autorizzazione mancante o copyright.
- AdE Cartografia Catastale WMS: `ammessa con vincoli`. CC BY 4.0, citazione
  della titolarita AdE obbligatoria, concorrenza limitata dal servizio e
  sospensione possibile in caso di uso disturbante.
- Layer PAI RAS: `esclusi`. I tre layer sono pubblicati, ma i record GeoNetwork
  referenziati dalle capabilities restituiscono `404`; la licenza non e quindi
  accertabile. Possono rientrare solo dopo ripristino dei metadati o evidenza
  ufficiale equivalente.
- Autorevolezza dei distretti irrigui: GAIA resta autorevole per
  `cat_distretti`; il layer RAS e solo confronto informativo e la descrizione
  M22 deve dichiararlo.
- Timeout M21: mantenere il default pianificato di `12 s`, probe piu corto,
  cache, backoff e degradazione governata. Le fonti non pubblicano SLA.

## Decisioni P1

- Le sorgenti fisiche configurate sono tre. `ras_sitr_vector` supporta WMS
  `1.3.0` e WFS `1.1.0` sullo stesso endpoint; raster RAS e AdE espongono WMS
  `1.3.0` nel registro M21.
- La destinazione proxy deriva solo da `layer_id`, `source_key` registrata e
  `remote_layer` validato. `url`, `service`, `version`, `layer` e `typename`
  client sono rifiutati.
- Il proxy usa timeout default `12 s`, cache filesystem atomica, TTL per layer
  e pruning al limite configurato. Non inoltra `Authorization` o altri header
  GAIA.
- Gli errori sono auditati; tile e richieste riuscite non generano audit.
- Il probe health usa `GetCapabilities`, il minimo tra timeout sorgente e
  timeout health, e cache `300 s`.
- Nessun layer esterno e stato aggiunto al bootstrap. Il flag resta disabilitato
  per default.

## Decisioni Aperte

- Se il programma Territorio Esterno debba essere numerato come continuazione
  della GIS Platform (M21-M25, ipotesi adottata nei documenti) o come modulo
  affiancato con numerazione propria.
- Se il precaricamento delle ortofoto sulla bounding box del comprensorio vada
  fatto subito o solo dopo aver misurato le prestazioni reali del proxy in
  esercizio.
- Se la scheda territoriale M24 debba essere accessibile anche dall'anagrafica
  particella oltre che dalla mappa.
- Politica di aggiunta di nuovi layer al catalogo dopo il seed: chi approva la
  richiesta e con quale evidenza di caso d'uso.

## Rischi

- Le sorgenti RAS e AdE non hanno SLA verso GAIA. Ogni funzione che le usa deve
  restare utile con le sorgenti irraggiungibili. Il criterio di accettazione di
  M23 lo verifica esplicitamente.
- I WMS raster storici sono pesanti. Senza cache con TTL lungo l'apertura della
  mappa puo diventare lenta e generare carico non necessario verso la Regione.
- Rischio di uso improprio da parte di utenti non tecnici: un operatore potrebbe
  credere di poter proporre una change request su un vincolo regionale. I
  divieti vanno applicati lato API, non solo nascondendo i controlli in UI.
- Le revisioni PAI cambiano nel tempo. Un aggiornamento di revisione va trattato
  come nuovo layer, non come modifica silenziosa di quello esistente, altrimenti
  le schede territoriali gia generate diventano non ricostruibili.
- Espansione incontrollata del catalogo: con `379` layer disponibili ogni
  ufficio ne vorra uno. Senza una regola di governo il catalogo diventa
  ingestibile e il pannello strati illeggibile.
- Crescita di file gia sopra soglia di complessita:
  `backend/app/modules/gis/services.py` a `3441` righe e
  `frontend/src/components/catasto/gis/MapContainer.tsx` a `1552` righe. Il
  piano prescrive package e hook dedicati; se questa regola viene aggirata il
  ratchet fallisce.
- Il disclaimer della scheda territoriale non e una formalita: senza, un
  documento istruttorio interno puo essere usato impropriamente come
  certificazione.

## Prossima Azione Raccomandata

Aprire P4 sul branch `feature/gis-territorio-interrogazione-m23`, partendo dal
branch P3 verificato. Implementare esclusivamente l'interrogazione puntuale
backend M23a; non anticipare il pannello P5 dentro la stessa change.
