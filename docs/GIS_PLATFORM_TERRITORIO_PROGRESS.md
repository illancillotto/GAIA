# GAIA GIS Platform - Progress Territorio Esterno

> Ultimo aggiornamento: 2026-08-29.
> Branch corrente: `integration/gis-platform-complete`.
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
e stata integrata nella catena GIS a `3d373f28`; M21 e stata riallineata,
congelata nel commit `07d9f7c4` e chiusa con ratchet verde. Il branch e stato
ripulito il 2026-08-29 e contiene soltanto commit M21; la guardia morta rimossa
in `6563cc1b` e inclusa nell'integrazione.

P2 e completato sul branch `feature/gis-territorio-catalog-seed-m22`: il seed
idempotente registra i `21` layer ammessi e `GET /gis/territorio/layers`
restituisce solo quelli attivi e visibili, raggruppati per tema.

P3 e completato sul branch `feature/gis-territorio-layer-panel-m22`: pannello,
opacita, legende autenticate, attribuzioni e selettore ortofoto sono integrati
nelle mappe Catasto senza modificare l'hotspot `MapContainer.tsx`.

P4/M23a e completato sul branch
`feature/gis-territorio-interrogazione-m23`: `POST /gis/interroga` aggrega le
sonde GAIA e le sorgenti remote nei livelli `gaia`, `catasto_ufficiale` e
`territorio`.

P5/M23b e completato sul branch
`feature/gis-territorio-interrogazione-ui-m23`: il pannello istruttorio si
apre con una azione esplicita e aggiorna GAIA e ogni sorgente remota senza
attendere la piu lenta.

P6/M24 e completato sul branch `feature/gis-territorio-scheda-m24`: la scheda
PDF raccoglie i dati della particella e le sorgenti territoriali autorizzate,
persiste lo snapshot, dichiara le esclusioni e gestisce audit e retention.

P7/M25 e completato sul branch `feature/gis-territorio-strumenti-m25`:
misure geodetiche, confronto ortofoto, stampa e propagazione QGIS via proxy
GAIA sono implementati senza modificare `MapContainer.tsx`.

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
| M23b | Pannello interrogazione, frontend | completata il 2026-08-28 con ratchet verde | `feature/gis-territorio-interrogazione-ui-m23` |
| M24 | Scheda territoriale particella in PDF | completata il 2026-08-28 con ratchet verde | `feature/gis-territorio-scheda-m24` |
| M25 | Strumenti di campo e propagazione QGIS | completata il 2026-08-28 con ratchet verde | `feature/gis-territorio-strumenti-m25` |

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

Verifiche integrazione completa eseguite il 2026-08-29:

- M21 integrata in `8044b4a4`, M22-M25 in `1f5dbbad` e perpetual-sync in
  `e25ba695`; i tre branch sorgente restano invariati;
- suite combinata backend GIS e perpetual-sync: exit `0`; i quattro runtime
  perpetual hanno coverage `675/675`, totale `100%`;
- suite unit frontend completa: `184` file e `1654` test verdi;
- `npm run typecheck`, `npm run build`, `npm run lint` e `make lint-backend`:
  exit `0`; lint segnala soltanto warning preesistenti fuori perimetro;
- `make quality-test`: `46 passed`;
- `make complexity-ratchet BASE_REF=origin/main`: exit `0`, baseline commit
  `840c0100`, nessun finding e baseline invariata;
- `make complexity-baseline-verify`: restituisce correttamente `false` perche
  il checkout integrato contiene codice funzionale non assorbito dalla baseline
  di `origin/main`; la baseline non e stata rigenerata o ampliata;
- Alembic espone una sola head `20260901_1000`, merge di `20260901_0900` e
  `20260828_0900`;
- round-trip PostgreSQL reale della migration perpetual: verde su database
  effimero isolato;
- l'upgrade dell'intera storia su database vuoto si ferma alla migration
  storica `20260612_0900` per assenza della tabella `org_unit`; la stessa
  failure e riprodotta su `origin/main` e non deriva dall'integrazione GIS.
- Graphify aggiornato sui corpus coinvolti: backend `7290` nodi, `17609`
  archi, `439` community; frontend `4966/11963/190`; documentazione Catasto
  `120/202/11`; corpus aggregato `domain-docs` `530/708/37`; refresh della
  documentazione piattaforma completato con esito `PASS`.

Verifiche P7 eseguite il 2026-08-28:

- suite backend GIS integrata: `182 passed`; coverage runtime modificati
  `1476/1476`, totale `100%`;
- test frontend P7: `17 passed`; coverage `171/171` statement, `103/103`
  branch, `49/49` funzioni e `125/125` linee;
- caso geodetico noto: arco equatoriale di un grado circa `111.195 km`;
- `make lint-backend`: exit `0`; `make quality-test`: `46 passed`;
- `npm run typecheck`: exit `0`; `npm run lint`: exit `0`, con soli warning
  preesistenti fuori perimetro;
- suite unit frontend completa: `183` file e `1647` test verdi;
- `npm run build`: exit `0`;
- `make complexity-ratchet BASE_REF=feature/gis-territorio-scheda-m24`:
  exit `0`, baseline commit `d678b7e9`, nessun finding;
- `make graphify-backend`: exit `0`, `7258` nodi, `17534` archi e `450`
  community;
- `make graphify-frontend`: exit `0`, `4935` nodi, `11919` archi e `184`
  community;
- `make graphify-platform-docs`: exit `0`, `519` nodi, `747` archi e `66`
  community;
- il primo ratchet P7 ha rifiutato due nuove violation nei moduli QGIS. La
  baseline non e stata aggiornata; datasource e validazione parametri sono
  stati separati per responsabilita e il ratchet successivo e verde.

Decisioni M25:

- distanze e aree usano coordinate WGS84 e calcolo geodetico, non distanza
  euclidea sul piano Web Mercator;
- il confronto ortofoto bilancia simultaneamente opacita della annata
  principale e della annata di confronto;
- la stampa cattura la canvas e genera un layout con scala, legenda,
  intestazione consortile e attribuzioni deduplicate;
- `GIS_QGIS_PROXY_BASE_URL` definisce la base HTTPS raggiungibile dai desktop;
  il progetto usa `authcfg=gaia_oauth` e non incorpora credenziali;
- l'endpoint QGIS WMS accetta solo il nome locale esatto del layer nel path e
  delega a M21, preservando allowlist e destinazione governata;
- `services.py` e stato ridotto estraendo il builder in `qgis_project.py`;
  `MapContainer.tsx` resta invariato.

Verifiche P6 eseguite il 2026-08-28:

- suite backend GIS integrata: `176 passed`;
- coverage sui runtime backend modificati: `1157` statement, `0` mancanti,
  totale `100%`;
- test frontend P6: `13 passed`; coverage `76/76` statement, `63/63` branch,
  `35/35` funzioni e `63/63` linee;
- `make lint-backend`: exit `0`; `make quality-test`: `46 passed`;
- `npm run typecheck`: exit `0`; `npm run lint`: exit `0`, con soli warning
  preesistenti fuori dal perimetro;
- suite unit frontend completa: `180` file e `1636` test verdi;
- `npm run build`: exit `0`;
- `make complexity-ratchet
  BASE_REF=feature/gis-territorio-interrogazione-ui-m23`: exit `0`, baseline
  commit `24e6c04d`, nessun finding;
- `make graphify-backend`: exit `0`, `7241` nodi, `17507` archi e `444`
  community;
- `make graphify-frontend`: exit `0`, `4913` nodi, `11872` archi e `188`
  community;
- `make graphify-platform-docs`: exit `0`, `471` nodi, `671` archi e `59`
  community;
- `git diff --check`: exit `0` prima dell'aggiornamento documentale.

La migration M24 e verificata direttamente invocando `upgrade()` e
`downgrade()` nel test dedicato. La generazione Alembic offline dell'intera
catena non e utilizzabile come ulteriore prova: la migration storica
`20260529_0094_wiki_conversation_governance.py` esegue inspection del database
ed e incompatibile con `--sql`. Non e stata dichiarata una applicazione
end-to-end su PostgreSQL reale in questa change.

Decisioni M24:

- la richiesta crea un record `queued`; raccolta remota e resa Chromium sono
  eseguite fuori dalla risposta HTTP con una sessione database propria;
- lo snapshot delle sorgenti viene persistito prima del rendering e resta
  valorizzato anche quando la raccolta fallisce prima di produrre dati;
- il richiedente e gli amministratori GIS possono leggere e scaricare la
  scheda; ogni layer territoriale richiede `can_view`, altrimenti compare tra
  le esclusioni dichiarate;
- il PDF contiene disclaimer in prima pagina, attribuzioni deduplicate,
  dettaglio degli esiti M23 ed estratto ortofoto con scala e riferimenti;
- il client usa polling a intervallo di un secondo e revoca il blob URL quando
  cambia particella o il componente viene smontato.

Verifiche P5 eseguite il 2026-08-28:

- suite mirata pannello, hook, wrapper e client API: `8 passed`;
- coverage pannello/hook: `97/97` statement, `45/45` branch, `45/45`
  funzioni e `78/78` linee; wrapper/client: `16/16` statement, `4/4` branch,
  `8/8` funzioni e `15/15` linee;
- `npm run typecheck`: exit `0`;
- `npm run lint`: exit `0`, con soli warning preesistenti fuori dal perimetro;
- suite unit frontend completa: `179` file e `1631` test verdi;
- `npm run build`: exit `0`, compilazione riuscita e `154` pagine generate;
- `make complexity-ratchet
  BASE_REF=feature/gis-territorio-interrogazione-m23`: exit `0`, baseline
  commit `352f3f23`, nessun finding.
- `make graphify-frontend`: exit `0`, `4905` nodi, `11848` archi e `186`
  community;
- `make graphify-platform-docs`: exit `0`, `454` nodi, `618` archi e `61`
  community.

Decisioni M23b:

- `Interroga punto` arma il clic successivo; il listener MapLibre dedicato non
  rimuove o sostituisce quelli del popup rapido;
- una richiesta senza layer carica subito GAIA, poi i layer interrogabili sono
  richiesti singolarmente con massimo quattro richieste client concorrenti;
- ogni completamento aggiorna solo la sorgente coinvolta; una failure non
  interrompe le altre e i visual-only non generano HTTP;
- il pannello resta overlay non modale e non modifica `MapContainer.tsx`,
  `ParticellaGisDialog.tsx` o `TerritorioLayerPanel.tsx`;
- la CTA scheda territoriale e disabilitata fino a M24.

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

### Riordino Branch E Riverifica, 2026-08-29

Il branch conteneva `5f319127 fix(search): rank linked utenza first for CF and
P.IVA`, estraneo al perimetro Territorio Esterno: toccava
`backend/app/modules/search/service.py`,
`backend/tests/test_operational_search_api.py` e `docs/ARCHITECTURE.md`.

Il commit e stato spostato su `fix/search-linked-utenza-ranking`, ramificato da
`main` a `3d373f28` e non da M21, cosi da restare mergiabile in autonomia. Il
cherry-pick `3d769709` e stato confrontato con l'originale: diff identico. La
storia precedente resta su `backup/m21-pre-cleanup-20260829`.

Il branch M21 e stato riscritto con `git rebase --onto dddbbe58 5f319127` e
contiene ora tre commit: `07d9f7c4`, `dddbbe58` e `6563cc1b`. Il diff
`main..HEAD` non presenta piu tracce della change Search, verificate a zero
righe residue, e si riduce a `16` file tutti nel perimetro M21.

Riverifica dopo il riordino, eseguita il 2026-08-29:

- working tree pulito, `0` voci;
- suite M21 mirata: `112 passed`;
- coverage per statement sui sette runtime del perimetro: `2402` statement, `0`
  mancanti, totale `100%`;
- `external_sources.py`: `98/98`, `external_proxy.py`: `202/202`,
  `config.py`: `283/283`, `schemas.py`: `412/412`, `router.py`: `150/150`,
  `runtime_health.py`: `132/132`, `services.py`: `1125/1125`;
- coverage per branch sui due runtime nuovi: `84` branch, `0` parziali,
  `100%`;
- `make lint-backend`: exit `0`;
- `make complexity-ratchet BASE_REF=main`: exit `0`, `findings: []`, `16`
  changed files.

`services.py` passa da `1126` a `1125` statement per la rimozione della guardia
morta in `_apply_feature_create`, commit `6563cc1b`. Il conteggio totale scende
di conseguenza da `2403` a `2402`.

Nessun push e nessuna integrazione in `main`.

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

## Audit Conclusivo P0-P7

Audit eseguito il 2026-08-28 confrontando i criteri di accettazione dei prompt
con catalogo, implementazione, test e verifiche registrate sopra.

- P0: le tre sorgenti hanno licenza, URL delle condizioni, attribuzione e
  vincoli registrati; i `21` layer ammessi sono presenti nelle capabilities;
  GetMap e GetFeature sono stati misurati; PAI e ortofoto senza licenza
  accertabile hanno una motivazione esplicita. Tutti i criteri sono soddisfatti.
- P1: validazione di `wms_external` e `wfs_external`, metadati legali
  obbligatori, allowlist, cache, TTL, timeout, pruning, destinazione governata,
  flag `503` e divieti change request/export/QGIS sono coperti dai test M21.
  Coverage `2403/2403` e ratchet contro `3d373f28` sono verdi. Tutti i criteri
  sono soddisfatti.
- P2: il test idempotente crea `21` layer e nessun duplicato alla seconda
  esecuzione; licenza e attribuzione mancanti sono rifiutate; catalogo,
  raggruppamento e filtro `can_view` sono verificati. Coverage `745/745` e
  ratchet contro `dddbbe58` sono verdi. Tutti i criteri sono soddisfatti.
- P3: pannello, gruppi, toggle, opacita, legenda, ortofoto, confronto,
  attribuzioni, ordine sotto i layer GAIA e isolamento degli errori sono
  verificati dai test dedicati. Typecheck, suite unit completa, lint e ratchet
  sono verdi; `MapContainer.tsx` non e stato modificato. Tutti i criteri sono
  soddisfatti.
- P4: endpoint e servizio restituiscono i tre livelli con stato e durata per
  sorgente; i test verificano tutte le sorgenti remote fallite, livello GAIA
  completo, visual-only saltati, limite remoto e permessi. Coverage
  `1129/1129` e ratchet sono verdi. Tutti i criteri sono soddisfatti.
- P5: i test verificano apertura esplicita sul clic, tre livelli, distinzione
  tra vuoto e non disponibile e pubblicazione progressiva. La change non
  modifica popup, `MapContainer.tsx` o pannello strati; typecheck, suite unit,
  lint e ratchet sono verdi. Tutti i criteri sono soddisfatti.
- P6: i test verificano generazione e download dal pannello, disclaimer in
  prima pagina, attribuzioni, snapshot, esclusioni dichiarate, audit nei tre
  esiti, retention e migration `upgrade()`/`downgrade()`. Coverage
  `1157/1157` e ratchet sono verdi. Tutti i criteri sono soddisfatti.
- P7: i test verificano l'arco equatoriale noto, confronto ortofoto, stampa con
  scala, legenda, intestazione e attribuzioni, e progetto QGIS filtrato per
  `can_view` con WMS sul proxy GAIA. Coverage backend `1476/1476`, coverage
  frontend completa sul perimetro P7 e ratchet sono verdi. Tutti i criteri
  sono soddisfatti.

La catena verificata e lineare:
`dddbbe58 -> d7861d06 -> 2b6f5651 -> 352f3f23 -> 24e6c04d -> d678b7e9 ->
677e499c`. La fondazione M21 e attestata dal freeze `07d9f7c4` e dalla chiusura
documentale `dddbbe58`. Il branch M21 e stato ripulito dal commit Search
estraneo, termina a `b38d9ed1` e include la rimozione della guardia morta
`6563cc1b`; la change Search resta sul branch autonomo dedicato.

Non risultano criteri aperti, baseline aggiornate per assorbire regressioni o
milestone successive avviate. P0-P7 sono chiusi sui commit sopra indicati.

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

Completare i gate del branch `integration/gis-platform-complete`, inclusa la
catena Alembic unificata, e non aprire ulteriori milestone senza una nuova
decisione di prodotto. La change Search resta autonoma e fuori dal perimetro
GIS.
