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

## Dashboard operativa

La pagina `/elaborazioni` usa una struttura a sezioni stabili:
- barra superiore con azioni rapide in linea
- card rapide dedicate a `Visure` e `Pool operativo dedicato`, allineate visivamente agli altri ingressi del modulo
- provider `Bonifica Oristanese` gestito nello stesso workspace `Credenziali`, con CRUD account e test autenticazione Laravel
- il provider `Bonifica Oristanese` espone anche `POST /elaborazioni/bonifica/sync/run` e `GET /elaborazioni/bonifica/sync/status`; sul runtime attuale sono abilitate le entity `report_types`, `reports`, `vehicles`, `refuels`, `taken_charge`, `users` (solo ruoli operativi), `areas`, `warehouse_requests`, `org_charts` e `consorziati`
- `GET /elaborazioni/bonifica/sync/status` restituisce anche il `params_json` dell'ultimo job per entity, usato dal frontend per mostrare range data e `source_total` letto dalla sorgente White
- i job Bonifica rimasti in stato `running` oltre la soglia `WC_SYNC_STALE_JOB_MINUTES` vengono marcati automaticamente come `failed` alla successiva lettura stato o al successivo avvio sync
- per `users` e `consorziati` il runtime applica una soglia stale dedicata (`WC_SYNC_USER_STALE_JOB_MINUTES`) e fetch dettagli concorrente controllato (`WC_SYNC_USER_DETAIL_CONCURRENCY`), cosi la sincronizzazione dei volumi piu alti non viene chiusa prematuramente come `failed`
- il runtime blocca l'avvio di `refuels` e `taken_charge` se non esiste una base mezzi locale e il run non include anche `vehicles`, cosi evita import a cascata con errori prevedibili sui riferimenti veicolo
- la sync `vehicles` riallinea anche record gia presenti per `plate_number` o `wc_vehicle_id`, e isola gli errori per-record con savepoint per non lasciare la sessione SQLAlchemy in stato `PendingRollback`
- la sync `refuels` non fallisce piu per singoli dettagli White orfani: se il dettaglio di un rifornimento non e piu leggibile perche il mezzo sorgente e stato cancellato nel portale, il record viene saltato come `skipped` e la sync continua sugli altri rifornimenti
- il runtime Bonifica usa ora bootstrap test-safe in `backend/tests/conftest.py`: se l'ambiente locale contiene placeholder (`change_me`) per `DATABASE_URL` o `JWT_SECRET_KEY`, la suite pytest forza default sicuri di sessione senza richiedere override manuali per i test del provider
- il workspace `WhiteCompany Sync` in `/elaborazioni` espone progress bar e log operativo locale della run corrente, costruiti sui job restituiti da `sync/run` e sul polling di `sync/status`, per rendere leggibile l'avanzamento entity per entity durante l'esecuzione
- il corpo della dashboard è stato semplificato: sotto le azioni rapide restano solo l'elenco dei batch recenti e una vista aggregata delle operazioni in corso (batch runtime + sync WhiteCompany attive)
- l'ingresso `Visure` sostituisce i due accessi separati `Visura singola` e `Import batch`: apre il workspace unico `ElaborazioneRequestWorkspace`, che gestisce entrambe le modalità
- spazio riservato all'aggiunta futura di altri provider/processi senza rimescolare i flussi esistenti
- i workspace rapidi della dashboard si aprono in modale, con fallback a pagina completa quando serve approfondire o condividere il link
- anche i punti di uscita frequenti nei workspace interni (`archivio batch/documenti`, `Capacitas`) riusano il pattern modale per ridurre i salti di pagina
- i workspace principali (`nuova richiesta`, `archivio batch`, `dettaglio batch`, `Capacitas`) sono renderizzati nativamente in overlay React; l'`iframe` resta solo come fallback per percorsi non ancora convertiti
- anche `Credenziali` e il viewer dei documenti catastali sono ora componenti nativi riusabili, quindi l'overlay non dipende piu dall'`iframe` nei percorsi operativi principali del modulo
- nel workspace `Credenziali` i blocchi `SISTER` e `Capacitas` sono collassabili, cosi la modale puo comprimere i pannelli non necessari senza perdere il contesto operativo
- il workspace `Credenziali` gestisce ora piu credenziali SISTER per utente: ogni profilo puo essere attivo/disattivo, editabile e impostato come `default`; il worker usa il profilo default attivo, oppure il primo profilo attivo disponibile

## Struttura

- `docs/`: documentazione canonica del modulo `elaborazioni`
- `GAIA_VISURE_PROMPT_1_ANALISI.md`
- `GAIA_VISURE_PROMPT_2_IMPLEMENTAZIONE.md`
- `GAIA_VISURE_PROMPT_3_REVIEW.md`

## Nota operativa

I tre file `GAIA_VISURE_PROMPT_*` restano volutamente nella root di `domain-docs/elaborazioni/`:

- non sono ancora consolidati come documentazione canonica
- restano input di lavoro e implementazione ancora da completare
- non devono essere spostati o riscritti finché la relativa implementazione non è chiusa

La documentazione stabile del modulo vive invece in `domain-docs/elaborazioni/docs/`.
