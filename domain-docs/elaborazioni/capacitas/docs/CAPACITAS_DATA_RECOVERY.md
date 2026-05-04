# Capacitas Data Recovery Guide

> Stato documento
> Guida operativa canonica per il recupero dati da Capacitas nel runtime GAIA.
> Questo documento va aggiornato ogni volta che cambiano flow, endpoint, parser, modelli, persistenza, scheduler o UX operativa collegata a Capacitas.

## 1. Scopo

Questo documento descrive come GAIA recupera, decodifica, normalizza e persiste i dati provenienti da Capacitas, con focus su:

- autenticazione SSO e attivazione applicazioni
- ricerca anagrafica inVOLTURE
- storico anagrafico remoto
- lookup territoriali `frazioni -> sezioni -> fogli`
- ricerca Terreni
- apertura certificati e dettagli terreno
- mapping verso i modelli interni GAIA
- persistenza nel catasto consortile e nell'anagrafica GAIA
- punti di manutenzione da aggiornare a ogni variazione futura

Il documento e operativo: privilegia il comportamento reale della codebase rispetto a note storiche o ipotesi di analisi.

## 2. Sorgenti canoniche

Quando questo documento e in conflitto con il codice, prevale il codice runtime. Le sorgenti canoniche da leggere insieme sono:

- sessione e SSO: `backend/app/modules/elaborazioni/capacitas/session.py`
- registry app Capacitas: `backend/app/modules/elaborazioni/capacitas/apps/registry.py`
- client inVOLTURE: `backend/app/modules/elaborazioni/capacitas/apps/involture/client.py`
- parser HTML/payload: `backend/app/modules/elaborazioni/capacitas/apps/involture/parsers.py`
- DTO e modelli payload: `backend/app/modules/elaborazioni/capacitas/models.py`
- API pubbliche backend: `backend/app/modules/elaborazioni/capacitas_routes.py`
- runtime job worker: `backend/app/services/elaborazioni_capacitas_runtime.py`
- poller operativo: `modules/elaborazioni/worker/worker.py`
- persistenza e sync Terreni: `backend/app/services/elaborazioni_capacitas_terreni.py`
- note di dominio catasto consortile: `domain-docs/catasto/docs/CATASTO_CONSORTILE.md`
- regole anagrafiche collegate allo storico Capacitas: `domain-docs/utenze/docs/PRD_anagrafica.md`

## 3. Perimetro applicativo attuale

App Capacitas registrate nel runtime:

- `involture`
- `incass`
- `inbollettini`

Per il recupero dati documentato qui, il perimetro attivo e soprattutto `involture`, con host:

- `https://involture1.servizicapacitas.com`

Funzioni effettivamente implementate oggi:

- login SSO e attivazione app
- ricerca anagrafica
- apertura scheda anagrafica corrente da certificato/intestatario
- storico anagrafico remoto
- lookup `frazioni`, `sezioni`, `fogli`
- ricerca Terreni
- apertura `rptCertificato.aspx`
- apertura `dettaglioTerreno.aspx`
- sync singola e massiva verso persistenza GAIA

I job monitorabili di sync massiva (`Terreni`, sync progressiva particelle e
import `Storico anagrafica`) vengono creati dalle API come record `pending` e
prelevati dal container `elaborazioni-worker`. Il backend web resta responsabile
di auth, validazione, creazione job e monitoraggio; l'esecuzione lunga con
sessioni Capacitas e scritture DB avviene fuori dai worker Uvicorn.

## 4. Mappa endpoint esterni Capacitas

### 4.1 SSO e bootstrap

- `GET/POST https://sso.servizicapacitas.com/pages/login.aspx`
- `POST https://sso.servizicapacitas.com/pages/ajax/ajaxTiles.aspx`

### 4.2 inVOLTURE anagrafica e storico

- `POST /pages/ajax/ajaxRicerca.aspx`
- `GET /pages/dettaglioAnagrafica.aspx?IDXANA=...&IDXEsa=...`
- `GET /pages/ajax/ajaxStorico.aspx?op=ana&IDXAna=...`
- `GET /pages/dialog/dlgStoricoAnag.aspx?IDXana=...`
- `GET /pages/dialog/dlgNuovaAnagrafica.aspx?ID=...&storica=1`

### 4.3 inVOLTURE lookup e Terreni

- `POST /pages/ajax/ajaxFrazioni.aspx`
- `POST /pages/ajax/ajaxSezioni.aspx`
- `POST /pages/ajax/ajaxFogli.aspx`
- `POST /pages/ajax/ajaxGrid.aspx`
- `GET /pages/rptCertificato.aspx`
- `GET /pages/dettaglioTerreno.aspx`

## 5. Flusso di autenticazione

Sequenza reale:

1. `CapacitasSessionManager.login()` apre la pagina SSO.
2. Estrae `__VIEWSTATE`, `__EVENTVALIDATION` e i nomi reali dei campi form.
3. Esegue il `POST` credenziali.
4. Estrae il `token` dal redirect o dall'HTML risultante.
5. `activate_app("involture")` carica le tiles SSO.
6. Risolve host, alias e metadati tramite `apps/registry.py`.
7. Lancia l'app corretta e acquisisce cookie/sessione applicativa.

Regole operative:

- non hardcodare host o alias fuori dal registry
- non saltare il passaggio tile SSO
- non aprire direttamente `main.aspx?app=involture` come strategia primaria
- ogni nuova app Capacitas va registrata nel registry prima di aggiungere logica client dedicata

## 6. Decoder payload AJAX

Diversi endpoint AJAX Capacitas non restituiscono JSON puro ma payload compressi/base64.

GAIA usa:

- `backend/app/modules/elaborazioni/capacitas/decoder.py`

Il decoder va applicato prima del parsing per:

- ricerca anagrafica
- lookup territoriali
- ricerca Terreni
- storico anagrafico quando il payload arriva in forma compressa

Regole operative:

- mai parsare direttamente `response.text` senza passare dal decoder quando l'endpoint usa il formato Capacitas
- se il payload decodificato non e del tipo atteso, loggare snippet e URL finale
- mantenere test di regressione sui payload reali osservati

## 7. Ricerca anagrafica

Client:

- `InVoltureClient.search_anagrafica()`
- helper: `search_by_cf()`, `search_by_cco()`

Endpoint GAIA:

- `POST /elaborazioni/capacitas/involture/search`

Input principali:

- `q`
- `tipo_ricerca`
- `solo_con_beni`
- `credential_id`

Output:

- `CapacitasSearchResult`
- righe `CapacitasAnagrafica`

Campi rilevanti in risposta:

- `IDXANA`
- `CCO`
- `Denominazione`
- `CodiceFiscale`
- `Comune`
- `DataNascita`
- `LuogoNascita`

Uso tipico:

- identificazione soggetto
- aggancio a flussi catasto/utenze
- avvio del recupero storico tramite `IDXANA`

## 7.b Apertura anagrafica corrente da certificato Terreni

Flusso osservato sui certificati `rptCertificato.aspx`:

- ogni riga intestatario espone `data-idxana`, `data-idxesa` e spesso il `codice_fiscale`
- il click sul codice fiscale o sulla riga apre `dettaglioAnagrafica.aspx?IDXANA=...&IDXEsa=...`
- la pagina corrente anagrafica contiene il profilo completo aggiornato del soggetto, distinto dal dettaglio storico `dlgNuovaAnagrafica.aspx?storica=1`

Implementazione runtime:

- parser certificato: `parse_certificato_html()`
- parser anagrafica corrente: `parse_anagrafica_detail_html()`
- client live: `InVoltureClient.fetch_current_anagrafica_detail(idxana=..., idxesa=...)`

Uso in GAIA:

- il flusso massivo `POST /catasto/elaborazioni-massive/particelle` resta locale-first
- se la particella/utenza esiste ma l'intestatario non e risolto in `ana_persons`, il backend prova a ricostruire i parametri del certificato da `cat_capacitas_certificati`, `cat_consorzio_occupancies` o `cat_capacitas_terreni_rows`
- apre `rptCertificato.aspx`, legge gli intestatari reali, poi per i soggetti mancanti apre `dettaglioAnagrafica.aspx`
- aggiorna o crea `ana_subjects` e `ana_persons` con i dati live dell'intestatario
- se il profilo locale cambia, salva anche uno snapshot differenziale in `ana_person_snapshots`

Questo flusso non importa lo storico remoto completo: serve solo a risolvere e aggiornare gli intestatari correnti durante la ricerca massiva.

## 8. Storico anagrafico remoto

### 8.1 Comportamento funzionale osservato

Dalla pagina `dettaglioAnagrafica.aspx` il portale presenta tre casi:

- nessuno storico: toast "nessun storico presente"
- un solo record: apertura diretta del dettaglio storico
- piu record: apertura modal elenco e drill-down sul record scelto

### 8.2 Modellazione GAIA

GAIA usa il flusso canonico:

`IDXANA -> storico -> history_id -> dettaglio storico`

Implementazione:

- lista storico: `InVoltureClient.fetch_anagrafica_history(idxana=...)`
- dettaglio storico: `InVoltureClient.fetch_anagrafica_detail(history_id=...)`

Endpoint GAIA:

- `GET /elaborazioni/capacitas/involture/anagrafica/{idxana}/storico`
- `GET /elaborazioni/capacitas/involture/anagrafica/storico/{history_id}`

Modelli:

- `CapacitasStoricoAnagraficaRow`
- `CapacitasAnagraficaDetail`

Regole operative:

- `IDXANA` identifica il soggetto Capacitas
- `history_id` identifica il singolo snapshot storico
- ogni record storico ha un `ID` proprio e non va confuso con `IDXANA`
- assenza storico va trattata come lista vuota, non come errore bloccante di sync

### 8.3 Uso nel sync GAIA

Il servizio `elaborazioni_capacitas_terreni.py` usa lo storico per:

- arricchire il profilo soggetto oltre il certificato sintetico
- aggiornare `ana_persons`
- salvare ogni `history_id` remoto in `ana_person_snapshots` con `is_capacitas_history = true` e `source_ref = history_id`
- scrivere anche uno snapshot differenziale in `ana_person_snapshots` quando il profilo corrente cambia
- popolare `cat_utenza_intestatari` per annualita

Fallback:

- se lo storico manca o non e leggibile, il sistema usa il dato sintetico del certificato

## 9. Lookup territoriali

Client:

- `search_frazioni()`
- `load_sezioni()`
- `load_fogli()`

Endpoint GAIA:

- `GET /elaborazioni/capacitas/involture/frazioni`
- `GET /elaborazioni/capacitas/involture/sezioni`
- `GET /elaborazioni/capacitas/involture/fogli`

Modello:

- `CapacitasLookupOption`

Regole operative:

- non usare solo il nome comune come chiave di ricerca
- distinguere sempre comune amministrativo, frazione/localita Capacitas e codice tecnico selezionato
- nei batch massivi il backend puo risolvere `comune -> frazione_id` e provare candidati multipli se il nome e ambiguo

## 10. Ricerca Terreni

Client:

- `InVoltureClient.search_terreni()`

Endpoint GAIA:

- `POST /elaborazioni/capacitas/involture/terreni/search`

Input:

- `frazione_id`
- `sezione`
- `foglio`
- `particella`
- `sub`
- filtri opzionali tecnici

Output:

- `CapacitasTerreniSearchResult`
- righe `CapacitasTerrenoRow`

Campi importanti:

- `ID`
- `PVC`
- `COM`
- `CCO`
- `FRA`
- `CCS`
- `Foglio`
- `Partic`
- `Sub`
- `Superficie`
- `Anno`
- `Voltura`
- `Opcode`
- `DataReg`
- `BacDescr`
- `Ta_ext`

La normalizzazione runtime deriva anche `row_visual_state` per distinguere righe correnti e storiche.

## 11. Certificato e dettaglio terreno

### 11.1 Certificato

Client:

- `fetch_certificato()`

Parser:

- `parse_certificato_html()`

Output:

- `CapacitasTerrenoCertificato`

Sezioni estratte:

- partita
- utenza
- intestatari
- titoli
- terreni collegati
- riordino `R.F.`, `Maglia`, `Lotto`

### 11.2 Dettaglio terreno

Client:

- `fetch_terreno_detail()`

Parser:

- `parse_terreno_detail_html()`

Output:

- `CapacitasTerrenoDetail`

Campi principali:

- `foglio`
- `particella`
- `sub`
- `riordino_code`
- `riordino_maglia`
- `riordino_lotto`
- `irridist`
- `parameters`

## 12. Persistenza in GAIA

La persistenza strutturata lato catasto consortile usa:

- `cat_consorzio_units`
- `cat_consorzio_unit_segments`
- `cat_consorzio_occupancies`
- `cat_capacitas_terreni_rows`
- `cat_capacitas_certificati`
- `cat_capacitas_intestatari`
- `cat_utenza_intestatari`
- `cat_capacitas_terreno_details`
- `capacitas_terreni_sync_jobs`

La persistenza anagrafica collegata usa:

- `ana_subjects`
- `ana_persons`
- `ana_person_snapshots`

Regola chiave:

- i dati Capacitas sono snapshot di sorgente e non devono sovrascrivere distruttivamente la traccia storica
- `ana_person_snapshots` ora puo contenere sia snapshot storici importati da Capacitas (`is_capacitas_history = true`) sia snapshot differenziali interni GAIA (`is_capacitas_history = false`)

## 13. Sync singola, batch e job

Endpoint principali GAIA:

- `POST /elaborazioni/capacitas/involture/terreni/sync`
- `POST /elaborazioni/capacitas/involture/terreni/sync-batch`
- `POST /elaborazioni/capacitas/involture/terreni/jobs`
- `GET /elaborazioni/capacitas/involture/terreni/jobs`
- `GET /elaborazioni/capacitas/involture/terreni/jobs/{id}`
- `POST /elaborazioni/capacitas/involture/terreni/jobs/{id}/run`

Servizi coinvolti:

- `sync_terreni_for_request()`
- `sync_terreni_batch()`
- `run_terreni_sync_job()`

Cache interne usate dal sync:

- cache certificati
- cache storico anagrafico per `IDXANA`
- cache dettaglio storico per `history_id`

Questo evita chiamate duplicate su record ripetuti nello stesso job.

## 14. Casi speciali e fallback

### 14.1 Assenza storico anagrafico

- non fallire il job
- ritornare lista vuota
- usare certificato sintetico come fallback

### 14.2 Comune storico Arborea/Terralba

Regola implementata:

- se il match sul comune sorgente Capacitas fallisce e il caso e nella coppia `Arborea/Terralba`, GAIA prova il comune reciproco
- il comune canonico resta quello reale GAIA
- il comune sorgente Capacitas viene conservato nei campi `source_*`

### 14.3 Multipli candidati frazione — risoluzione automatica

- nei batch il backend prova piu frazioni candidate per lo stesso comune
- il candidato utile e quello che restituisce davvero la particella cercata
- se esattamente una frazione ha risultati, il sync procede con quella senza intervento manuale

### 14.4 Frazioni ambigue — anomalia e risoluzione manuale

Si verifica quando due o piu frazioni dello stesso comune restituiscono entrambe risultati per lo stesso foglio/particella (es. Oristano foglio 8 particella 48 presente sia in `04 DONIGALA FENUGHEDU` che in `11 ORISTANO`).

Comportamento:

- `_probe_frazioni_for_item` esegue un search leggero (senza scritture DB) su tutte le frazioni candidate
- se il probe trova piu di una frazione con righe → alza `CapacitasFrazioneAmbiguaError` con l'elenco candidati (frazione_id, n_rows, CCO, stati)
- `_sync_particella_item` catcha l'errore e salva sulla particella:
  - `capacitas_last_sync_status = "anomalia"`
  - `capacitas_anomaly_type = "frazione_ambigua"`
  - `capacitas_anomaly_data.candidates` = lista frazioni con i loro metadati
- nessun dato Capacitas viene scritto in DB per la particella anomala

Risoluzione manuale:

1. L'operatore apre il workspace Capacitas → sezione **Anomalie**
2. Vede le particelle in anomalia con le frazioni candidate e i rispettivi CCO
3. Preme **Risolvi** → modal con radio button per scegliere la frazione corretta
4. Preme **Sincronizza** → `POST /elaborazioni/capacitas/involture/particelle/{id}/resolve-frazione`
5. Il backend esegue il sync con la frazione esplicita; se ok azzera `capacitas_anomaly_type/data`

Endpoints anomalie:

- `GET /elaborazioni/capacitas/involture/particelle/anomalie` — lista particelle con anomalia non risolta
- `POST /elaborazioni/capacitas/involture/particelle/{id}/resolve-frazione` — body: `{frazione_id, credential_id?, fetch_certificati, fetch_details}`

Persistenza:

- colonne aggiunte a `cat_particelle`: `capacitas_anomaly_type VARCHAR(32)`, `capacitas_anomaly_data JSON`
- migration: `20260504_0072_add_capacitas_anomaly_to_particelle.py`

## 15. Diagnostica e test

Punti di verifica principali:

- test API Capacitas: `backend/tests/test_elaborazioni_capacitas.py`
- parser HTML/payload nello stesso file di test
- logging sessione e app activation in `session.py`
- logging route in `capacitas_routes.py`
- snippet diagnostici payload nei fallimenti parser/lookup

### 15.1 Script di verifica manuale per singola particella

`backend/test_fix_verification.py` — tool operativo da eseguire nel container backend per verificare sync e persistenza su una singola particella Capacitas.

Uso:

```bash
docker exec -w /app gaia-backend python test_fix_verification.py <comune> <foglio> <particella>
```

Esempi:

```bash
docker exec -w /app gaia-backend python test_fix_verification.py Cabras 24 3
docker exec -w /app gaia-backend python test_fix_verification.py Cabras 24 37
docker exec -w /app gaia-backend python test_fix_verification.py Cabras 1 4
docker exec -w /app gaia-backend python test_fix_verification.py Uras 1 680
```

Output prodotto (nell'ordine):

1. **Stato DB pre-sync**: particelle AE, utenze irrigue, unità consorziali, righe Capacitas presenti
2. **Esecuzione sync**: chiama `sync_terreni_batch` sulla particella richiesta e stampa il report (righe, certificati, unità, occupancies)
3. **Stato DB post-sync**: righe Capacitas aggiornate, unità consorziali con `utenza_id` e `is_current`, certificati per CCO con intestatari e flag `deceduto`, utenze irrigue con intestatari collegati

Il comune viene risolto dal nome in modo case-insensitive con fallback a ricerca parziale; il script segnala esplicitamente se il comune non e trovato o se il match e ambiguo.

Quando un flusso cambia, vanno aggiornati insieme:

- parser
- modelli Pydantic
- endpoint pubblici
- test di regressione
- questa documentazione

## 16. Checklist di aggiornamento documentale

Aggiornare questo file ogni volta che cambia almeno uno dei punti seguenti:

- URL o parametri degli endpoint Capacitas
- flow SSO o attivazione app
- formato payload AJAX
- struttura HTML di storico, certificato o dettaglio terreno
- modelli `Capacitas*`
- persistenza nelle tabelle `cat_*` o `ana_*`
- endpoint backend `elaborazioni/capacitas`
- comportamento batch/job
- regole di fallback o mapping comuni/frazioni

Aggiornamenti correlati da valutare nello stesso commit:

- `domain-docs/elaborazioni/capacitas/docs/CAPACITAS_integration.md`
- `domain-docs/catasto/docs/CATASTO_CONSORTILE.md`
- `domain-docs/utenze/docs/PRD_anagrafica.md`
- `README.md`
- `DOCS_STRUCTURE.md`

## 17. Riferimenti rapidi

- documento integrazione sintetico: `domain-docs/elaborazioni/capacitas/docs/CAPACITAS_integration.md`
- modello catasto consortile: `domain-docs/catasto/docs/CATASTO_CONSORTILE.md`
- regole anagrafica/storico: `domain-docs/utenze/docs/PRD_anagrafica.md`
- API runtime: `backend/app/modules/elaborazioni/capacitas_routes.py`
- client/parsers: `backend/app/modules/elaborazioni/capacitas/apps/involture/`
