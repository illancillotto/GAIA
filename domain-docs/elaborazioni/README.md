# GAIA Elaborazioni

Area documentale dedicata al runtime operativo delle lavorazioni catastali.

Ambito runtime attuale:
- visure per immobile
- visure per soggetto PF/PNF
- gestione CAPTCHA
- report e artifact diagnostici batch/richiesta
- pool credenziali SISTER con profilo default per worker e test connessione
- diagnostica login Capacitas con dump HTML/metadata del tentativo quando il token SSO non viene estratto
- provider `Bonifica Oristanese` con pool credenziali cifrato, test login HTTP su `https://login.bonificaoristanese.it/login`, helper DataTables condiviso, bootstrap `apps/registry.py` per le entity del portale e orchestratore di sync persistito su `wc_sync_job`
- provider `Poste Online` per recupero worker-only delle raccomandate online 2022-2023 da `posta-online.it`, con credenziali cifrate, test login accodato e import verso `ruolo/tributi`

## Dashboard operativa

La pagina `/elaborazioni` usa una struttura a sezioni stabili:
- barra superiore con azioni rapide in linea
- card rapide dedicate a `Visure` e `Pool operativo dedicato`, allineate visivamente agli altri ingressi del modulo
- provider `Bonifica Oristanese` gestito nello stesso workspace `Credenziali`, con CRUD account e test autenticazione Laravel
- il provider `Bonifica Oristanese` espone anche `POST /elaborazioni/bonifica/sync/run` e `GET /elaborazioni/bonifica/sync/status`; sul runtime attuale sono abilitate le entity `report_types`, `reports`, `vehicles`, `refuels`, `taken_charge`, `users` (solo ruoli operativi), `areas`, `warehouse_requests`, `org_charts` e `consorziati`
- `GET /elaborazioni/bonifica/sync/status` restituisce anche il `params_json` dell'ultimo job per entity, usato dal frontend per mostrare range data e `source_total` letto dalla sorgente White
- i job Bonifica rimasti in stato `running` oltre la soglia `WC_SYNC_STALE_JOB_MINUTES` vengono marcati automaticamente come `failed` alla successiva lettura stato o al successivo avvio sync
- per `users` e `consorziati` il runtime applica una soglia stale dedicata (`WC_SYNC_USER_STALE_JOB_MINUTES`) e fetch dettagli concorrente controllato (`WC_SYNC_USER_DETAIL_CONCURRENCY`), cosi la sincronizzazione dei volumi piu alti non viene chiusa prematuramente come `failed`; `users` usa una query role-based sui ruoli configurati in `WC_SYNC_USERS_ROLE_IDS` invece del full scan globale e `consorziati` usa `WC_SYNC_CONSORZIATI_ROLE_ID`, con deduplica per `wc_id`, default a `16` richieste dettaglio concorrenti, timeout stale a `360` minuti e delay ridotti (`WC_SYNC_REQUEST_DELAY_MS=100`, `WC_SYNC_DETAIL_DELAY_MS=25`) per smaltire piu velocemente i dataset utenti ad alto volume
- se il backend viene riavviato mentre una sync WhiteCompany e in corso, i job rimasti `running` vengono marcati automaticamente come `failed` alla prima lettura dello stato, con dettaglio di job orfano; in questo modo la UI puo usare subito il pulsante `Rilancia` senza aspettare la scadenza stale
- il runtime blocca l'avvio di `refuels` e `taken_charge` se non esiste una base mezzi locale e il run non include anche `vehicles`, cosi evita import a cascata con errori prevedibili sui riferimenti veicolo
- la sync `vehicles` riallinea anche record gia presenti per `plate_number` o `wc_vehicle_id`, e isola gli errori per-record con savepoint per non lasciare la sessione SQLAlchemy in stato `PendingRollback`
- la sync `refuels` risolve prima l'id mezzo White via `GET /vehicles/search`, poi interroga `GET /vehicles/refuel/datatable` con `filter_code[]` per ogni mezzo locale gia sincronizzato; il runtime evita cosi il fetch massivo dei dettagli `edit/{id}` che faceva scadere i job piu lunghi
- la datatable WhiteCompany dei rifornimenti espone solo mezzo, operatore, data e km: la sync salva quindi eventi operativi parziali in `wc_refuel_event` invece di creare `vehicle_fuel_log` incompleti
- il completamento dei campi carburante mancanti passa dal dominio Operazioni tramite `POST /api/operazioni/vehicles/fuel-logs/import-fleet-transactions`, che importa il file Excel transazioni flotte, risolve la carta su `fuel_card.codice` (`Identificativo`) e riconcilia evento White, carta e fuel log GAIA
- il runtime Bonifica usa ora bootstrap test-safe in `backend/tests/conftest.py`: se l'ambiente locale contiene placeholder (`change_me`) per `DATABASE_URL` o `JWT_SECRET_KEY`, la suite pytest forza default sicuri di sessione senza richiedere override manuali per i test del provider
- il workspace `WhiteCompany Sync` in `/elaborazioni` espone progress bar e log operativo locale della run corrente, costruiti sui job restituiti da `sync/run` e sul polling di `sync/status`, per rendere leggibile l'avanzamento entity per entity durante l'esecuzione
- il workspace `GAIA Mobile Sync` in `/elaborazioni/gaia-mobile-sync` monitora il canale outbound GAIA -> gateway pubblico `gaia-mobile`, mostrando configurazione, ultimo run e storico audit dei push operatori senza toccare il contratto LAN `/api/mobile-sync/*`
- il workspace `Poste Online` in `/elaborazioni/posta-online` gestisce username/password del portale Poste, test login e job di recupero raccomandate; il backend salva e accoda, mentre il browser Playwright gira solo nel worker elaborazioni
- i job Poste vengono persistiti in `posta_online_registered_mail_sync_jobs` con `mode='credential_test'` per la verifica login e `mode='registered_mails'` per l'import raccomandate; gli esiti restano nella stessa cronologia operativa mostrata dalla UI
- l'import raccomandate Poste usa annualita fisse `2022` e `2023`, recupera contatti, id archivio e dettagli HTML con delay randomizzati configurabili (`min_delay_ms`/`max_delay_ms`), poi passa il payload al modulo `ruolo/tributi` per parsing, match indirizzo e anomalie
- per il portale Poste il flusso di ingresso valido parte da `https://corrispondenza.poste.it/`, apre `https://corrispondenza.poste.it/col/archivio.do?callback_url=https://corrispondenza.poste.it:443/col/archivio.do`, lascia che Poste reindirizzi verso `https://idp-business.poste.it/jod-idp-business/cas/login.html`, compila il form IdP e rientra sull'archivio `corrispondenza.poste.it/col/archivio.do`; il login diretto su IdP o da `www.posta-online.it` puo perdere payload/sessione e in caso di errore puo rientrare su `business.poste.it`
- `max_pages` e `max_details` non sono parametri anti-rate-limit: `null` significa sync completa di tutte le pagine archivio e tutti gli invii trovati; valori numerici servono solo per debug, test o recuperi parziali controllati
- la protezione anti-rate-limit e temporale: il worker aspetta tra contatti, pagine archivio e dettagli, inserisce una pausa lunga dopo blocchi di richieste e applica retry con backoff esponenziale e jitter su `429`, `500`, `502`, `503` e `504`; gli errori permanenti come `403` non vengono mascherati
- il dettaglio raccomandata viene scaricato con `POST https://corrispondenza.poste.it/col/dettaglio.do` e payload multipart `idInvio`, `numrows=""`, `controller="archivio.do"`; l'HTML di risposta viene decodificato rispettando il charset, con fallback `iso-8859-1`
- `POSTA_ONLINE_STORAGE_STATE_PATH` puo salvare cookie/sessione Playwright tra run e `POSTA_ONLINE_CDP_URL` puo collegare il worker a un Chromium gia aperto per debug; in produzione il percorso normale resta headless con nuovo context Playwright, user-agent Chrome desktop, locale `it-IT` e viewport desktop
- il worker Poste non usa codice fiscale dal portale Poste: il collegamento all'utenza viene demandato alla logica Tributi tramite normalizzazione nominativo/indirizzo e classificazione `matched`, `ambiguous`, `unmatched` o `error`
- il workspace `Allineamento AdE` in `/elaborazioni/ade-alignment` governa il run comprensorio Agenzia Entrate fuori dal GIS; il backend accoda il run in `cat_ade_sync_runs` e il container `gaia-elaborazioni-worker-visure` esegue il download WFS aggiornando fase, messaggio operativo, `tiles_completed` e contatori live delle particelle/geometrie rilevate
- il corpo della dashboard è stato semplificato: sotto le azioni rapide restano solo l'elenco dei batch recenti e una vista aggregata delle operazioni in corso (batch runtime + sync WhiteCompany attive)
- nella tabella `Batch recenti` la dashboard mostra anche la sintesi esiti per lotto (`ok`, `ko`, `n.d.`, `skip`) cosi i batch grandi risultano leggibili senza aprire subito il dettaglio
- l'ingresso `Visure` sostituisce i due accessi separati `Visura singola` e `Import batch`: apre il workspace unico `ElaborazioneRequestWorkspace`, che gestisce entrambe le modalità
- spazio riservato all'aggiunta futura di altri provider/processi senza rimescolare i flussi esistenti
- i workspace rapidi della dashboard si aprono in modale, con fallback a pagina completa quando serve approfondire o condividere il link
- anche i punti di uscita frequenti nei workspace interni (`archivio batch/documenti`, `Capacitas`) riusano il pattern modale per ridurre i salti di pagina
- i workspace principali (`nuova richiesta`, `archivio batch`, `dettaglio batch`, `Capacitas`) sono renderizzati nativamente in overlay React; l'`iframe` resta solo come fallback per percorsi non ancora convertiti
- anche `Credenziali` e il viewer dei documenti catastali sono ora componenti nativi riusabili, quindi l'overlay non dipende piu dall'`iframe` nei percorsi operativi principali del modulo
- nel workspace `Credenziali` i blocchi `SISTER` e `Capacitas` sono collassabili, cosi la modale puo comprimere i pannelli non necessari senza perdere il contesto operativo
- il workspace `Credenziali` gestisce ora piu credenziali SISTER per utente: ogni profilo puo essere attivo/disattivo, editabile e impostato come `default`; il worker usa il profilo default attivo, oppure il primo profilo attivo disponibile
- le credenziali SISTER sono isolate per utente GAIA: `GET /elaborazioni/credentials` restituisce solo il pool del `current_user`; il vincolo DB e `UNIQUE (user_id, sister_username)`, quindi lo stesso username SISTER puo esistere su utenti GAIA diversi ma non due volte nello stesso pool utente
- il retry dei batch falliti rimette in coda solo le richieste `failed` e aggiorna il riferimento temporale del lotto, evitando che un batch rilanciato venga marcato subito come scaduto dalla pulizia dei `pending` orfani
- il worker visure usa tutte le credenziali SISTER attive dell'utente come pool concorrente: una sessione browser per credenziale, claim atomico delle richieste e prosecuzione del batch anche quando una singola utenza entra in cooldown
- gli errori transitori `SISTER_SESSION_LOCKED`, timeout login/menu e `HTTP 500` del portale non falliscono subito il lotto: la richiesta viene differita, la credenziale entra in cooldown e il runner passa alla richiesta successiva disponibile
- la dashboard `/elaborazioni` mostra KPI runtime aggregati letti da `GET /elaborazioni/metrics`: throughput ultime 24h, volumetria 7 giorni, success rate, tempo medio richiesta/batch, ultimo processato e stato finestra operativa
- in alto la dashboard espone la sezione `Autosync automatici`, che centralizza i toggle operativi per `Visure NAS`, `ANPR batch`, `AutoSync visure a ruolo`, `WhiteCompany daily` e `WhiteCompany Operazioni live`
- `GET /elaborazioni/auto-job-controls` restituisce l’elenco aggregato dei controlli automatici mostrati in dashboard, mentre `PUT /elaborazioni/auto-job-controls/{control_key}` permette agli admin di attivare o disattivare ogni job dalla stessa sezione
- per `Visure NAS`, `WhiteCompany daily` e `WhiteCompany Operazioni live` il toggle dashboard viene persistito su tabella `elaborazione_auto_job_configs` e prevale sul default ambiente dopo il primo salvataggio, cosi il backend puo fermare o riattivare il job senza cambiare `.env`
- `WhiteCompany Operazioni live` sincronizza automaticamente `reports`, `taken_charge`, `warehouse_requests` e `refuels` ogni 60 minuti nella finestra `06:00`-`21:00` locale di default; la schedulazione usa `WC_SYNC_OPERAZIONI_LIVE_START_HOUR`, `WC_SYNC_OPERAZIONI_LIVE_END_HOUR`, `WC_SYNC_OPERAZIONI_LIVE_TIMEZONE` e `WC_SYNC_OPERAZIONI_LIVE_LOOKBACK_DAYS`
- gli scheduler `ANPR`, `Visure NAS`, `WhiteCompany daily` e `WhiteCompany Operazioni live` restano registrati al boot ma verificano il flag effettivo a runtime: il cambio stato da dashboard ha quindi effetto diretto sul giro successivo dello scheduler senza richiedere restart del backend

## Struttura

- `docs/`: documentazione canonica del modulo `elaborazioni`
- `docs/RUOLO_VISURE_AUTOSYNC_PLAN.md`: piano di implementazione dell'autosync visure per le particelle presenti a ruolo
- `capacitas/docs/CAPACITAS_DATA_RECOVERY.md`: guida operativa completa per recupero dati, storico anagrafico, Terreni e persistenza Capacitas
- `GAIA_VISURE_PROMPT_1_ANALISI.md`
- `GAIA_VISURE_PROMPT_2_IMPLEMENTAZIONE.md`
- `GAIA_VISURE_PROMPT_3_REVIEW.md`

## Nota operativa

I tre file `GAIA_VISURE_PROMPT_*` restano volutamente nella root di `domain-docs/elaborazioni/`:

- non sono ancora consolidati come documentazione canonica
- restano input di lavoro e implementazione ancora da completare
- non devono essere spostati o riscritti finché la relativa implementazione non è chiusa

La documentazione stabile del modulo vive invece in `domain-docs/elaborazioni/docs/`.

## Configurazione operativa

Variabili principali del runtime visure:

- `ELABORAZIONI_PENDING_START_TIMEOUT_MINUTES`: scadenza dei batch `pending` mai avviati
- `ELABORAZIONI_CREDENTIAL_LOCK_COOLDOWN_SEC`: cooldown base dopo lock/sessione bloccata
- `ELABORAZIONI_REQUEST_RETRY_DEFER_SEC`: defer della richiesta quando viene rimessa in coda
- `ELABORAZIONI_SISTER_500_COOLDOWN_SEC`: cooldown base per `HTTP 500` SISTER
- `ELABORAZIONI_SISTER_500_MAX_COOLDOWN_SEC`: tetto massimo del cooldown progressivo sui `500`
- `ELABORAZIONI_SISTER_500_GLOBAL_PAUSE_SEC`: pausa globale breve quando tutte le credenziali stanno colpendo `500`
- `ELABORAZIONI_OPERATION_WINDOW_ENABLED`: abilita la finestra operativa oraria
- `ELABORAZIONI_OPERATION_START_HOUR`: ora locale di inizio finestra
- `ELABORAZIONI_OPERATION_END_HOUR`: ora locale di fine finestra
- `ELABORAZIONI_OPERATION_TIMEZONE`: timezone usata per finestra e KPI giornalieri
- `ELABORAZIONI_WORKER_FAMILIES_RUNTIME`: famiglie gestite dal worker runtime; default compose `runtime,poste`, necessario per processare i job Poste Online
- `ELABORAZIONI_WORKER_FAMILIES_VISURE`: famiglie gestite dal worker visure; default `visure`
- `ELABORAZIONI_WORKER_FAMILIES_AUTODOC`: famiglie gestite dal worker AUTODOC; default `autodoc`
- `POSTA_ONLINE_STORAGE_STATE_PATH`: path opzionale dove il worker salva/riusa lo storage state Playwright per Poste Online
- `POSTA_ONLINE_CDP_URL`: URL opzionale di Chrome DevTools Protocol per collegare il worker a un Chromium gia aperto durante debug operativo

Comportamento finestra operativa:

- un batch puo essere creato e avviato anche fuori fascia
- se il worker trova la finestra chiusa mentre il batch e `processing`, aggiorna `current_operation` con il messaggio di pausa automatica
- i runner non prendono nuove richieste finche la finestra non riapre
- alla riapertura la lavorazione riparte senza intervento manuale e senza perdere lo stato persistito del batch

Significato KPI runtime:

- `processed_requests`: richieste arrivate a stato terminale (`completed`, `failed`, `skipped`, `not_found`)
- `throughput_per_hour`: media `processed_requests / ore_finestra_analizzata`
- `success_rate`: percentuale `completed / processed_requests`
- `average_request_duration_seconds`: media tra `created_at` e `processed_at` delle richieste terminali
- `average_batch_duration_minutes`: media tra `started_at` e `completed_at` dei batch completati nella finestra analizzata

## Poste Online

Superfici principali:

- UI: `/elaborazioni/posta-online`
- credenziali: `POST/GET/PATCH/DELETE /elaborazioni/posta-online/credentials`
- test login: `POST /elaborazioni/posta-online/credentials/{credential_id}/test`
- job raccomandate: `POST/GET /elaborazioni/posta-online/raccomandate/jobs`
- rilancio job: `POST /elaborazioni/posta-online/raccomandate/jobs/{job_id}/run`

Regole operative:

- le credenziali Poste richiedono solo `username` e `password`; la password e cifrata con `CREDENTIAL_MASTER_KEY`
- il test login viene accodato come job worker e non scarica contatti, archivio o dettagli
- lo scraping non gira mai nel backend FastAPI: `posta_online_client.py` viene caricato dal worker elaborazioni tramite Playwright
- il client applica delay randomizzato tra richieste, backoff su `429/5xx` e limiti `max_pages`/`max_details`
- se il portale richiede OTP o autenticazione interattiva, il job fallisce in modo esplicito per intervento operativo
- i risultati del recupero vengono importati nei Tributi, dove sono gestite associazioni alle utenze e anomalie da indirizzo
