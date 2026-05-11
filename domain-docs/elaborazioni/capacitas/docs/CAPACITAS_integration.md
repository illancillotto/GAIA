# CAPACITAS Integration — Note operative

> Stato documento
> Documento importato e riallineato al repository GAIA il 2 aprile 2026.
> La sorgente primaria resta il codice runtime in `backend/app/...`.
> Per la guida operativa completa di recupero dati, parsing, persistenza e manutenzione continua usare anche `domain-docs/elaborazioni/capacitas/docs/CAPACITAS_DATA_RECOVERY.md`.

## Stato

- Modulo: `backend/app/modules/elaborazioni/capacitas/`
- Registry app Capacitas: `backend/app/modules/elaborazioni/capacitas/apps/registry.py`
- Macro-moduli verticali: `backend/app/modules/elaborazioni/capacitas/apps/<app>/`
- Service: `backend/app/services/elaborazioni_capacitas.py`
- Runtime services job-aware:
  - `backend/app/services/elaborazioni_capacitas_particelle_sync.py`
  - `backend/app/services/elaborazioni_capacitas_terreni.py`
  - `backend/app/services/elaborazioni_capacitas_anagrafica_history.py`
- Routes: `backend/app/modules/elaborazioni/capacitas_routes.py`
- Bootstrap recovery: `backend/app/main.py` -> `resume_capacitas_runtime_jobs_on_startup()`
- Migration: `backend/alembic/versions/20260402_0027_capacitas_credentials.py`

## Struttura runtime

- `session.py` gestisce solo login SSO, token, cookie applicativi e keep-alive
- `apps/registry.py` centralizza chiave logica app, host, alias e nomi cookie
- ogni macro-modulo Capacitas vive sotto `apps/<app>/` e contiene i client e i sottomoduli specifici del servizio
- `client.py` al root resta come shim di compatibilita per gli import esistenti di `InVoltureClient`
- il link diretto a `rptCertificato.aspx` per le schede particella restituisce al frontend solo i parametri certificato (`CCO/COM/PVC/FRA/CCS`) e usa la sessione Capacitas gia presente nel browser; l'aggiunta di `token/app/tenant` puo forzare un rientro SSO e produrre "Sessione scaduta"
- i job monitorabili Capacitas (`Terreni`, sync progressiva particelle e `Storico anagrafica`) sono record persistenti con stato su DB, avviati dalle route e schedulati come runtime task tracciati nel backend API
- il backend esegue startup recovery: marca stale/orfani, converte i job recuperabili in `queued_resume` e li rilancia automaticamente quando la policy del job lo consente
- la scadenza della sessione GAIA ferma solo il monitor frontend; non e sinonimo di stop del task backend

Macro-moduli registrati ad oggi:

- `involture` → host `involture1.servizicapacitas.com`, alias `visure`, `invisure`
- `incass` → host `incass3.servizicapacitas.com`
- `inbollettini` → host `inbollettini.servizicapacitas.com`

Questa struttura consente di aggiungere nuovi moduli Capacitas senza estendere `session.py` con logica applicativa dedicata.

## Ambito funzionale implementato al 23 aprile 2026

Oltre al supporto gia presente per login SSO, attivazione app e ricerca anagrafica AJAX, il runtime ora include il primo blocco operativo `Terreni`.

Implementato:

- client e parser per:
  - lookup frazioni `ajaxFrazioni.aspx`
  - lookup sezioni `ajaxSezioni.aspx`
  - lookup fogli `ajaxFogli.aspx`
  - ricerca terreni `ajaxGrid.aspx` modulo `terreni_ricerca`
  - apertura e parsing `rptCertificato.aspx`
  - apertura e parsing `dettaglioTerreno.aspx`
- endpoint:
  - `GET /elaborazioni/capacitas/involture/frazioni`
  - `GET /elaborazioni/capacitas/involture/sezioni`
  - `GET /elaborazioni/capacitas/involture/fogli`
  - `POST /elaborazioni/capacitas/involture/terreni/search`
  - `POST /elaborazioni/capacitas/involture/terreni/sync`
  - `POST /elaborazioni/capacitas/involture/terreni/sync-batch`
  - `POST /elaborazioni/capacitas/involture/terreni/jobs`
  - `GET /elaborazioni/capacitas/involture/terreni/jobs`
  - `GET /elaborazioni/capacitas/involture/terreni/jobs/{id}`
  - `POST /elaborazioni/capacitas/involture/terreni/jobs/{id}/run`
  - `DELETE /elaborazioni/capacitas/involture/terreni/jobs/{id}`
  - `POST /elaborazioni/capacitas/involture/particelle/jobs`
  - `GET /elaborazioni/capacitas/involture/particelle/jobs`
  - `GET /elaborazioni/capacitas/involture/particelle/jobs/{id}`
  - `POST /elaborazioni/capacitas/involture/particelle/jobs/{id}/run`
  - `DELETE /elaborazioni/capacitas/involture/particelle/jobs/{id}`
  - `GET /elaborazioni/capacitas/involture/link/rpt-certificato?cco=...`
  - `POST /elaborazioni/capacitas/involture/anagrafica/storico/import`
  - `POST /elaborazioni/capacitas/involture/anagrafica/storico/import-file`
  - `POST /elaborazioni/capacitas/involture/anagrafica/storico/jobs`
  - `GET /elaborazioni/capacitas/involture/anagrafica/storico/jobs`
  - `GET /elaborazioni/capacitas/involture/anagrafica/storico/jobs/{id}`
  - `POST /elaborazioni/capacitas/involture/anagrafica/storico/jobs/{id}/run`
  - `DELETE /elaborazioni/capacitas/involture/anagrafica/storico/jobs/{id}`
  - `POST /elaborazioni/capacitas/involture/certificati/refetch-empty`
  - `GET /elaborazioni/capacitas/involture/particelle/anomalie`
  - `POST /elaborazioni/capacitas/involture/particelle/{id}/resolve-frazione`
- persistenza nel layer catasto consortile:
  - `cat_consorzio_units`
  - `cat_consorzio_unit_segments`
  - `cat_consorzio_occupancies`
  - `cat_capacitas_terreni_rows`
  - `cat_capacitas_certificati`
  - `cat_capacitas_intestatari`
  - `cat_utenza_intestatari`
  - `cat_capacitas_terreno_details`
  - `capacitas_terreni_sync_jobs`
  - `capacitas_particelle_sync_jobs`
  - `capacitas_anagrafica_history_import_jobs`
- frontend workspace in `frontend/src/components/elaborazioni/capacitas-workspace.tsx` con:
  - ricerca anagrafica
  - sync progressiva delle particelle GAIA con progress bar e monitor job
  - monitor `Storico anagrafica` con job persistenti, rerun, delete e auto-resume
  - dashboard `/elaborazioni` con vista aggregata delle esecuzioni attive, inclusi i job aperti della sync progressiva particelle
  - lookup guidato `frazioni -> sezioni -> fogli`
  - preview risultati Terreni
  - avvio job Terreni in background
  - tab `Massiva da file` con import `.xlsx/.csv` locale e creazione job batch
  - template scaricabile `Excel` / `CSV` con colonne umane `comune, sezione, foglio, particella, sub`
  - risoluzione backend `comune -> frazione_id Capacitas` durante il batch
  - se un comune ha piu frazioni candidate con match sul nome (`Arborea`, `Santa Giusta`, ecc.), il batch prova prima tutte le frazioni con una ricerca leggera (probe) e:
    - se una sola frazione ha risultati → sync automatico su quella
    - se piu frazioni hanno risultati → anomalia `frazione_ambigua` salvata sulla particella, nessun dato scritto
  - le particelle in anomalia compaiono nel tab **Anomalie** del workspace Capacitas; l'operatore sceglie la frazione corretta tramite modal e avvia il sync manuale
  - flag globali di avvio job per `fetch_certificati` e `fetch_details`, non piu richiesti per ogni riga file
  - monitor job con refresh, avanzamento incrementale in `result_json`, rerun manuale, eliminazione dei job terminati e segnalazione esplicita di sessione frontend scaduta

Limitazioni deliberate di questo step:

- i job massivi sono persistiti ma non usano ancora una coda esterna; l'esecuzione vive nel processo backend tramite runtime task tracciati e recovery su restart
- la risoluzione `comune testuale -> frazione Capacitas` resta separata tramite endpoint lookup
- il matching automatico con `ana_subjects` e ora introdotto solo per gli intestatari proprietari con `codice_fiscale` disponibile
- quando e disponibile lo storico anagrafico Capacitas, il sync usa il dettaglio storico come fonte per aggiornare `ana_persons` e scrivere `ana_person_snapshots`
- non e ancora presente una deduplica multi-sorgente avanzata oltre al match su CF e al fallback su `IDXANA`

Regola speciale implementata:

- se Capacitas restituisce una particella su `Arborea` o `Terralba` ma in GAIA la stessa combinazione `foglio/particella/sub` esiste sull'altro comune, il sistema mantiene come comune canonico quello reale di GAIA
- il comune sorgente Capacitas viene comunque salvato in `cat_consorzio_units` (`source_*`, `comune_resolution_mode`) per mostrare all'utente che la particella era storicamente censita su un comune diverso

## Ambito funzionale da estendere

Questo non e sufficiente per il dominio Catasto del Consorzio.

Estensione ulteriore richiesta:

- navigazione e scrape della sezione `Ricerche -> Terreni`
- recupero storico risultati per `comune/frazione/sezione/foglio/particella`
- apertura e parsing delle schede `rptCertificato.aspx`
- apertura e parsing del dettaglio terreno `dettaglioTerreno.aspx`
- acquisizione dei dati di riordino fondiario e delle porzioni irrigue operative

Obiettivo applicativo:

- alimentare il catasto consortile reale, distinto dalla sola particella catastale ufficiale

## Decoder risposta

Le risposte di `ajaxRicerca.aspx` (e altri endpoint AJAX) sono Base64 + compressione
custom decodificata lato browser da:

```
/script/js-deflate/jquery.base64.min.js
/script/js-deflate/rawinflate.js
/script/custom.js   ← funzione Ajax() e Grid.LoadV2()
```

Lo step di decoder non e piu bloccante: il decoder e stato portato nel progetto in:

`backend/app/modules/elaborazioni/capacitas/decoder.py`

### Payload di test

```
SZ7VLLbtswEPwV3nwJYfEhkepNlptCgGMbihMEKAqUIlcpAVsMaLmHFP2yHvpJ/YVyHdvpNUWP3YM0uzucXSzm14+fH8m3Zv6OTLiShQPGqAGlqOz6nppOldQJ6wxnrtCynFyRZv5QLavEz/qyE6UD6nTeU6nyjHagLe1sntnCaa7AJP7taMaA9ITXZox+FwaPBfoSK0qxEx9TSSQ09wnIBDbrBPCPwwiOXt/XKFSqhOvVDe6s8Uldr7BeZbrgRYmDrqN5Rj2OC9gvgG2MlM5g2/sQsfS+VEiow+4wYH5Tte3drLnDLWAIOz+YZx+OrXWI9kCqLez3ZnAxIMWMZmn21o/meL0py6as1Ki4OITH8Nqrqw+Lpmqb4yznLVz7vTXbo25bL26XmrdczUQuZ0iBOFab08XmYMEd/jhgHJNm8xVlyWvgmfwYtoGhZgxP0cNoPhM2lZfWwnfsdNFzzl/y5QZihAEPP/l+RU5+kHkOwDOgQjhGpbZAu1L2NNdCFpmUJn3/pR829BwXP/CzH/hf+kHlgov/frj4gU/FW/1APv0G
```

Ricerca effettuata: CF `PRCLSN82R27B354B` (tipo=2), risultato atteso: 2 righe (Porcu Alessandro).

## Flusso SSO — riepilogo

```
GET  sso.servizicapacitas.com/pages/login.aspx?op=&codCons=<CODCONS>&app=&tenant=
  → estrai __VIEWSTATE, __EVENTVALIDATION

POST sso.servizicapacitas.com/pages/login.aspx?op=&codCons=<CODCONS>&app=&tenant=
  body: username + password + viewstate
  → redirect a /pages/main.aspx?token=<UUID>

POST sso.servizicapacitas.com/pages/ajax/ajaxTiles.aspx
  body: op=tiles&key=root
  → restituisce le tile SSO con data-url, data-codcons, data-idrun

GET  <tile.data-url>?token=<UUID>&codConsApp=<tile.data-codcons>&idRun=<tile.data-idrun>
  → redirect a involture1/.../pages/main.aspx?token=<UUID>&app=involture&tenant=
  → imposta cookie/sessione validi per l'app

POST involture1.servizicapacitas.com/pages/ajax/ajaxRicerca.aspx
  body: q=<CF_urlenc>&tipo=ricanag&soloConBeni=false&opz=2
  headers: X-Requested-With: XMLHttpRequest
  → risposta Base64+compress

POST */pages/handler/handlerKeepSessionAlive.ashx  ogni 25s
```

Nota implementativa:

- l'attivazione di un'app non usa piu host hardcoded in `session.py`
- `CapacitasSessionManager.activate_app()` risolve la configurazione tramite registry e tile SSO
- per `inVOLTURE` il launch corretto parte da `login.aspx?token=...&codConsApp=...&idRun=...`, non da `main.aspx?...&app=involture`
- alias applicativi come `visure` o `invisure` vengono normalizzati alla chiave canonica `involture`

## Flusso Terreni da supportare

Sequenza osservata dai file HTML di riferimento:

1. login SSO su `https://sso.servizicapacitas.com/pages/login.aspx?op=&codCons=...&app=&tenant=`
2. redirect su `main.aspx?token=...`
3. lookup tile SSO `involture` via `ajaxTiles.aspx`
4. attivazione app su `login.aspx?token=...&codConsApp=...&idRun=...`
5. apertura:
   - `https://involture1.servizicapacitas.com/pages/ricerche.aspx?...`
   - `https://involture1.servizicapacitas.com/pages/ricercaTerreni.aspx?...`
5. ricerca per:
   - comune/frazione
   - sezione
   - foglio
   - particella
6. acquisizione griglia risultati
7. drill-down:
   - su `CCO` -> `rptCertificato.aspx`
   - su `ID terreno` -> `dettaglioTerreno.aspx`
8. dal dettaglio anagrafica:
   - pulsante `Storico`
   - lista storica `dialog/dlgStoricoAnag.aspx`
   - dettaglio storico `dialog/dlgNuovaAnagrafica.aspx?ID=<history_id>&storica=1`

## Storico anagrafico Capacitas

Flusso osservato in `dettaglioAnagrafica.aspx`:

- il menu `Storico` chiama `StoricoAnagrafiche()`
- il portale verifica prima se esistono righe via `ajax/ajaxStorico.aspx?op=n_ana&IDXAna=...`
- se non c'e storico, mostra un toast e non apre nessuna modal
- se esiste una sola riga apre direttamente `dlgNuovaAnagrafica.aspx?ID=...&storica=1`
- se esistono piu righe apre `dlgStoricoAnag.aspx?IDXana=...`, da cui poi si apre il dettaglio storico selezionato

Uso in GAIA:

- il client Terreni recupera lo storico via `ajaxStorico.aspx?op=ana&IDXAna=...`
- per ogni riga storica rilevante per l'annualita apre `dlgNuovaAnagrafica.aspx?ID=...&storica=1`
- il dettaglio storico alimenta:
  - `ana_persons` come anagrafica corrente consolidata
  - `ana_person_snapshots` quando il profilo cambia
  - `cat_utenza_intestatari` per collegare tutti gli intestatari proprietari alla singola `cat_utenze_irrigue` dell'anno
- se Capacitas non espone storico per quel soggetto, il sync usa il dato sintetico del certificato come fallback e non fallisce
- gli snapshot `cat_capacitas_intestatari` non crescono piu su sync identiche dello stesso certificato: se il payload dell'ultimo snapshot per lo stesso contesto (`CCO`, `COM`, `PVC`, `FRA`, `CCS`) non cambia, GAIA riusa quello esistente
- i link annuali `cat_utenza_intestatari` usano policy `replace` per `utenza_id + anno_riferimento`, cosi i residui di sync precedenti vengono rimossi prima di inserire il set ricostruito
- il matching verso `cat_utenze_irrigue` non usa mai il solo `CCO`: senza `COM` Capacitas valido non viene risolta alcuna utenza target
- se il certificato non individua una sola utenza target nel contesto corrente, GAIA conserva lo snapshot del certificato ma non persiste link annuali verso `cat_utenze_irrigue`

Workflow batch aggiuntivo disponibile nel modulo `elaborazioni`:

- input:
  - body JSON con lista di `subject_id` e/o `idxana`
  - upload `.csv` / `.xlsx` con colonne `subject_id` e/o `idxana`
- comportamento:
  - se parte da `subject_id`, GAIA tenta prima `subject.source_external_id`, poi fallback `search_by_cf`
  - per ogni `IDXANA` recupera la lista storico e il dettaglio di ogni `history_id`
  - importa in modo idempotente gli snapshot remoti in `ana_person_snapshots`
  - se il soggetto GAIA non esiste ancora ma Capacitas espone un CF valido, crea automaticamente `ana_subjects` + `ana_persons`
- output:
  - report con `processed`, `imported`, `skipped`, `failed`
  - contatore `snapshot_records_imported`
  - dettaglio riga per riga con soggetto risolto e numero di record storici importati
- modalita runtime attuale:
  - oltre alla route sincrona storica esiste un job persistente dedicato in `capacitas_anagrafica_history_import_jobs`
  - il monitor frontend mostra progress percent, ultimi item processati, rerun, delete e stato `queued_resume`
  - dopo restart backend i job con `auto_resume=true` vengono riconciliati e rilanciati automaticamente

## Sync progressiva particelle GAIA

Flusso applicativo aggiunto nel workspace `Elaborazioni / Capacitas`:

- il job legge `cat_particelle` correnti (`is_current = true`, non soppresse)
- ordina le particelle per `capacitas_last_sync_at` crescente, quindi aggiorna prima quelle mai sincronizzate o piu vecchie
- usa la stessa logica Terreni gia presente per:
  - risolvere `comune -> frazione Capacitas`
  - interrogare `ricercaTerreni.aspx`
  - aprire eventuali `rptCertificato.aspx`
  - aprire eventuali `dettaglioTerreno.aspx`
- salva su `cat_particelle` i metadati di tracking:
  - `capacitas_last_sync_at`
  - `capacitas_last_sync_status`
  - `capacitas_last_sync_error`
  - `capacitas_last_sync_job_id`
- persiste il job in `capacitas_particelle_sync_jobs` con progressi incrementali in `result_json`
- i job progressivi sono recoverable di default (`auto_resume=true`) e al restart backend vengono rimessi in coda come `queued_resume`

Politica anti-aggressiva:

- fascia diurna: throttle di default `900 ms` tra particelle e riesame dei record solo se non sincronizzati nelle ultime `24h`
- fascia serale dopo le `19:00` Europe/Rome: throttle ridotto a `350 ms` e riesame delle particelle gia dopo `6h`
- il workspace espone un pulsante `Doppia velocita` per il singolo job: il payload salva `double_speed=true` e dimezza la pausa calcolata (`450 ms` di giorno, `175 ms` in fascia serale)
- il workspace espone anche `Parallelo x2`: il payload salva `parallel_workers=2`, il backend apre due sessioni Capacitas dedicate e divide la coda particelle tra due worker con progresso condiviso sul job
- il job puo comunque essere lanciato manualmente dall'operatore, con `only_due=true` come default per evitare re-scrape inutili

## Policy runtime job

- tutti i processi Capacitas monitorabili da frontend devono usare job persistenti con stato su DB
- evitare `BackgroundTasks` o thread daemon come scheduler principale per processi lunghi
- ogni job monitorabile deve prevedere:
  - progress persistito in `result_json`
  - cleanup stale/orfani dopo restart o inattivita prolungata
  - distinzione esplicita tra stop del monitor frontend e stop del task backend
  - policy di recovery coerente con il dominio:
    - `particelle`: auto-resume attivo di default
    - `terreni`: auto-resume opzionale via payload job
    - `storico anagrafica`: auto-resume attivo di default

### Evidenze dai file locali

- `ricercaTerreni.aspx` usa `ajax/ajaxRicerca.aspx` per popolare la griglia risultati
- i risultati contengono gia campi strutturati utili:
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
- la pagina `rptCertificato.aspx` contiene:
  - partita/scheda
  - utenza
  - soggetti/anagrafica
  - titoli (`Proprieta 1/1`, `1/9`, ecc.)
  - elenco terreni
  - riferimenti `Riordino`, `Maglia`, `Lotto`
- `dettaglioTerreno.aspx` espone:
  - estremi del terreno
  - parametri tecnici
  - dati di riordino (`RIORDINO_F`, `MAGLIA_RF`, `LOTTO_RF`)
  - segnali e azioni di porzione irrigua
  - operazioni di voltura/frazionamento/affitto

## Gestione comuni e frazioni

La ricerca Terreni non usa solo il comune amministrativo “piatto”.

Nei casi osservati:

- lo stesso comune puo avere voci multiple in autocomplete, ad esempio:
  - `04 DONIGALA FENUGHEDU*ORISTANO`
  - `05 MASSAMA*ORISTANO`
- casi simili sono attesi anche per Cabras e Simaxis

Regola implementativa:

- non usare il solo testo comune come chiave di ricerca
- salvare sia il valore scelto nella combo/autocomplete sia i codici tecnici correlati (`COM`, `FRA`, eventuale voce completa mostrata)
- distinguere sempre:
  - comune amministrativo
  - frazione/localita Capacitas
  - codice Capacitas della ricerca selezionata

## Casi di risposta da modellare

### Caso A — singola riga

Esempio osservato:

- comune `URAS`
- foglio `14`
- particella `1695`
- una sola riga risultato

Flusso:

- la griglia identifica un solo `CCO`
- il click su `Contrib.` apre la scheda `rptCertificato.aspx`
- tutti i dati della scheda vanno persistiti

### Caso B — piu righe storiche

Esempio osservato:

- comune `URAS`
- foglio `1`
- particella `680`
- cinque record per anni/volture differenti

Interpretazione:

- i record rappresentano storico consortile del terreno
- possono esserci piu righe per lo stesso anno
- possono esserci variazioni di scheda, voltura o utilizzatore reale
- il record “corrente” tende a essere la riga nera; le righe rosse rappresentano stati precedenti o storicizzati

Regola implementativa:

- non tenere solo la riga “attuale”
- salvare tutte le righe restituite dalla ricerca Terreni
- aprire e persistere le schede correlate per tutte le righe ritenute rilevanti
- salvare attributi di ordinamento/stato visuale per ricostruire il “current snapshot” senza perdere lo storico

## Modello tecnico minimo da supportare

La pipeline Capacitas Terreni deve produrre almeno tre livelli di dato:

1. `search result snapshot`
   - ogni riga della griglia ricerca Terreni
   - chiave naturale: `COM/FRA/PVC/CCO/CCS/ID/Anno/Voltura`
2. `scheda certificato snapshot`
   - contenuto completo di `rptCertificato.aspx`
   - soggetti, titoli, terreni, utenza, stato ruolo
   - per ogni intestatario: `IDXANA`, `IDXESA`, CF, dati di nascita, residenza, titoli, flag `deceduto`
3. `terreno detail snapshot`
   - contenuto completo di `dettaglioTerreno.aspx`
   - riordino, parametri, porzione irrigua, metadati terreno

Persistenza consigliata:

- salvare sia campi normalizzati sia `raw_html`/`raw_json` di audit
- usare snapshot storicizzati, non semplice overwrite
- per gli intestatari proprietari rilevati in Capacitas usare `cat_capacitas_intestatari` come snapshot sorgente e `cat_utenza_intestatari` come legame annuale verso `cat_utenze_irrigue`
- il link verso `ana_subjects` deve essere opzionale e derivare da match su `codice_fiscale` o fallback `source_external_id=IDXANA`
- il primo scrape valido costituisce la baseline iniziale del profilo in GAIA; gli scrape successivi aggiornano `ana_persons` solo dopo aver scritto uno snapshot in `ana_person_snapshots` quando i dati cambiano

## Script di verifica manuale

`backend/test_fix_verification.py` — tool operativo per testare sync e persistenza su una singola particella direttamente nel container backend.

```bash
docker exec -w /app gaia-backend python test_fix_verification.py <comune> <foglio> <particella>
# es: docker exec -w /app gaia-backend python test_fix_verification.py Cabras 24 37
```

Mostra stato DB pre/post sync, report sync (righe, certificati, unità, occupancies), intestatari con flag `deceduto` e collegamento `utenza_id` sulle occupancies.

Documentazione completa in `domain-docs/elaborazioni/capacitas/docs/CAPACITAS_DATA_RECOVERY.md` sezione 15.1.

## TODO successivi

## Credenziali — gestione

- Tabella: `capacitas_credentials`
- Cifratura: `CREDENTIAL_MASTER_KEY` (stessa del vault SISTER)
- Rotazione: `pick_credential()` seleziona la meno usata di recente, attiva, nella fascia oraria
- Fascia oraria: `allowed_hours_start`–`allowed_hours_end` (ora locale server)
- Auto-disable: dopo `_MAX_CONSECUTIVE_FAILURES` (default 5) fallimenti consecutivi

## Endpoints esposti

```
POST   /elaborazioni/capacitas/credentials
GET    /elaborazioni/capacitas/credentials
GET    /elaborazioni/capacitas/credentials/{id}
PATCH  /elaborazioni/capacitas/credentials/{id}
DELETE /elaborazioni/capacitas/credentials/{id}
POST   /elaborazioni/capacitas/credentials/{id}/test

POST   /elaborazioni/capacitas/involture/search
GET    /elaborazioni/capacitas/involture/frazioni?q=...
GET    /elaborazioni/capacitas/involture/sezioni?frazione_id=...
GET    /elaborazioni/capacitas/involture/fogli?frazione_id=...&sezione=...
POST   /elaborazioni/capacitas/involture/terreni/search
POST   /elaborazioni/capacitas/involture/terreni/sync
POST   /elaborazioni/capacitas/involture/terreni/sync-batch
POST   /elaborazioni/capacitas/involture/terreni/jobs         -> crea il job e avvia subito il background run
GET    /elaborazioni/capacitas/involture/terreni/jobs
GET    /elaborazioni/capacitas/involture/terreni/jobs/{id}
POST   /elaborazioni/capacitas/involture/terreni/jobs/{id}/run -> rerun manuale esplicito
```

## Mount in router.py

In `backend/app/modules/elaborazioni/router.py` aggiungere:

```python
from app.modules.elaborazioni.capacitas_routes import router as capacitas_router
router.include_router(capacitas_router)
```

## TODO successivi

- [ ] Verificare nomi campi form login (`Capacitas$ContentMain$txtUsername` ecc.)
- [ ] Estrarre i client di `incass` in `apps/incass/`
- [ ] Estrarre i client di `inbollettini` in `apps/inbollettini/`
- [ ] Organizzare ogni macro-modulo in sottopackage per servizi AJAX, parser e mapping risposta
- [ ] Aggiungere endpoint `/involture/search` con paginazione/cache opzionale
- [ ] Frontend: pagina `/elaborazioni/settings` → sezione "Capacitas" con gestione credenziali
- [x] Aggiungere client `TerreniClient` per `ricercaTerreni.aspx`, `rptCertificato.aspx`, `dettaglioTerreno.aspx`
- [x] Parser HTML strutturati per:
  - griglia ricerca terreni
  - scheda certificato
  - dettaglio terreno / riordino
- [x] Persistenza dei dati grezzi e normalizzati per il catasto consortile
- [x] Sync batch applicativo su piu particelle con report per-item
- [x] Job persistito e rilanciabile per batch Terreni
- [ ] Job di acquisizione massiva “Terreni Capacitas” in `elaborazioni`
- [ ] Lookup guidato `frazioni -> sezioni -> fogli` lato frontend
- [~] Matching automatico con `ana_subjects` e deduplica snapshot
  stato attuale: match su CF/fallback `IDXANA` per intestatari proprietari, con update di `ana_persons` storicizzato tramite `ana_person_snapshots`
