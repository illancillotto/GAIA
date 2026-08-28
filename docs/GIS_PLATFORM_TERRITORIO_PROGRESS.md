# GAIA GIS Platform - Progress Territorio Esterno

> Ultimo aggiornamento: 2026-08-28.
> Branch corrente: `feature/gis-territorio-external-layers-m21`.
>
> Piano tecnico: `docs/GIS_PLATFORM_TERRITORIO_PLAN.md`.
> Riferimento dati: `docs/GIS_PLATFORM_TERRITORIO_CATALOGO.md`.
> Prompt operativi: `docs/GIS_PLATFORM_TERRITORIO_PROMPTS.md`.

## Stato Sintetico

P0 e completato. Licenze, attribuzioni, disponibilita e tempi delle sorgenti
sono stati verificati; il seed documentale e stato ristretto a `21` layer
ammissibili (`14` RAS vettoriali, `4` RAS raster, `3` AdE).

P1 e implementato: registro sorgenti, proxy governato, cache, health, nuovi
source type e divieti backend sono coperti al `100%`. M21 non e dichiarata
chiusa perche il ratchet di complessita fallisce, ma la verifica del 2026-08-28
attribuisce il fallimento a una baseline stale rispetto a `main`, non alla
slice. M22-M25 non sono avviate.

Attenzione allo stato del codice: il lavoro M21 e presente solo nel working tree
e non e committato. Non si trova ne su `main` ne sul branch
`feature/gis-territorio-external-layers-m21`, che punta a `09160b81` e non
contiene `external_sources.py` ne `external_proxy.py`.

La base M1-M20 della GIS Platform e in esercizio e non richiede modifiche
preliminari: `source_type` e gia una colonna `String(32)` libera in `GisLayer` e
`metadata_json` e gia `JSON`, quindi M21 non necessita di migration dello
schema catalogo.

## Milestone

| milestone | contenuto | stato | branch |
| --- | --- | --- | --- |
| P0 | Verifica licenze e disponibilita sorgenti | completato il 2026-08-27 | - |
| M21 | Fondazione layer esterni: source type, proxy, cache, health | implementata, verifica complexity bloccata il 2026-08-28 | `feature/gis-territorio-external-layers-m21` |
| M22a | Seed catalogo `territorio` e `GET /gis/territorio/layers` | da implementare | `feature/gis-territorio-catalog-seed-m22` |
| M22b | Pannello strati e ortofoto storiche in mappa | da implementare | `feature/gis-territorio-layer-panel-m22` |
| M23a | Interrogazione puntuale multi-sorgente, backend | da implementare | `feature/gis-territorio-interrogazione-m23` |
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

Verifiche P1 eseguite il 2026-08-28:

- `make lint-backend`: exit `0`;
- `pytest` mirato su config, runtime health, sorgenti, proxy e API GIS: `112`
  test verdi;
- coverage selettiva sui runtime modificati: `2529` statement, `0` mancanti,
  totale `100%`;
- `external_sources.py`: `98/98`, `100%`;
- `external_proxy.py`: `202/202`, `100%`;
- `config.py`: `306/306`, `schemas.py`: `412/412`, `router.py`: `150/150`,
  `runtime_health.py`: `132/132`, `services.py`: `1229/1229`;
- `make complexity-changed BASE_REF=origin/main`: exit `1`;
- `make complexity-ratchet BASE_REF=origin/main`: exit `1`, merge-base
  `840c010001e0aa45434539c4cf96065de61bdc41`.
- `make graphify-backend`: exit `0`, `7584` nodi, `18685` archi, `442`
  community;
- `make graphify-platform-docs`: exit `0`, `112` file da cache, `4`
  riestratti, `1466` nodi, `3185` archi, `107` community.

Il ratchet segnala aumenti su callable non modificate dal diff M21, tra cui
`services._validate_shapefile_zip` (`loc 63 -> 97`) e funzioni legacy del
router. La baseline non e stata rigenerata o aggiornata, in conformita al
quality ratchet.

### Diagnosi Del Blocco Ratchet, Verificata Il 2026-08-28

La prima registrazione attribuiva il blocco genericamente a un disallineamento
tra baseline e merge-base. La verifica successiva dimostra che una parte
preesistente del delta e gia presente su `main`; non dimostra invece, da sola,
che ogni variazione M21 sia conforme al ratchet.

Evidenze:

- la prima esecuzione usava `BASE_REF=origin/main` mentre `main` locale era
  avanti di `4` commit non correlati (worker, elaborazioni, refactor GIS-H8):
  il gate vedeva quel lavoro come parte del diff M21. Rieseguito con
  `BASE_REF=main`, i finding fuori perimetro su worker e frontend spariscono;
- `make complexity-baseline-verify` risponde
  `baseline_reproducible_ignoring_timestamp_commit: false` anche su un worktree
  di `main` pulito, senza alcun file M21 presente;
- l'aritmetica dei delta esclude M21 come causa:

| file | delta segnalato | contributo reale M21 | preesistente |
| --- | --- | --- | --- |
| `backend/app/core/config.py` | `653 -> 719` (`+66`) | `+30` | `+36` |
| `backend/app/modules/gis/services.py` | `2304 -> 3183` (`+879`) | `+45` netto | `+834` |

M21 vale circa l'`8%` del delta LOC osservato sui due file. Il resto era gia in
`main` prima della slice, ma deve essere classificato prima di qualsiasi
riallineamento della baseline.

- `services._validate_shapefile_zip` non e toccata dal diff M21: la modifica a
  `services.py` e additiva e introduce solo `resolve_external_layer_for_proxy` e
  `_ensure_change_request_target_is_internal`;
- il branch `gaia/presenze-gate-canonical-export`, in un worktree separato,
  contiene a `623ae160` una propria modifica della baseline. Questo impone di
  evitare aggiornamenti concorrenti non coordinati, ma non costituisce evidenza
  che il drift di `main` sia gia stato analizzato o approvato.

Verifica indipendente della slice, eseguita il 2026-08-28 con
`backend/.venv/bin/python -m pytest` su `test_gis_external_sources.py`,
`test_gis_external_proxy.py`, `test_gis_platform_api.py`,
`test_gis_runtime_health.py` e `test_config.py`: `112 passed`. Coverage sui due
runtime nuovi: `external_proxy.py` `202/202`, `external_sources.py` `98/98`,
totale `100%`.

Conseguenza: il gate rosso non puo essere attribuito integralmente a M21, ma
M21 non puo ancora essere dichiarata conforme. La slice resta congelata e non
chiusa finche il drift preesistente non e classificato in una change quality
separata, il branch non e riallineato e il ratchet autorevole non passa.

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

Non aprire P2.

La prossima azione e aprire da `main` una change quality dedicata che analizzi
il drift preesistente, in particolare le almeno `834` LOC di
`backend/app/modules/gis/services.py`. La baseline non deve essere rigenerata
automaticamente ne aggiornata dentro M21.

Prima di modificarla va coordinato il lavoro presente sul branch
`gaia/presenze-gate-canonical-export`, che tocca lo stesso file: due
aggiornamenti indipendenti produrrebbero un conflitto sull'artefatto che
definisce il debito accettato.

Vincoli della change quality:

- eseguire il ratchet sempre con `BASE_REF=main`, non `origin/main`, quando
  `main` locale e avanti rispetto al remoto: altrimenti il gate attribuisce alla
  slice lavoro di terzi;
- classificare ogni variazione come debito gia approvato, regressione da
  correggere oppure errore di matching;
- aggiornare la baseline solo dopo un ratchet verde e una review del diff,
  senza assorbire automaticamente il drift;
- M21 resta fuori da quella change.

Dopo l'integrazione della change quality in `main`, M21 deve essere riallineata
e il ratchet rieseguito. Solo un risultato verde consente di chiudere M21; P2
resta fermo.
