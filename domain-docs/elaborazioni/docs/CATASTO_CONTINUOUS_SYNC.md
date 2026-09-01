# Sincronizzazione Catastale Continua

## Obiettivo e SLA

Il planner mantiene un'unica campagna permanente per il Ruolo, articolata nelle fasi **Particelle a ruolo** e **Anagrafiche a ruolo**. Entrambe derivano esclusivamente dall'ultimo `ruolo_import_jobs` completato: viene selezionato l'anno tributario più alto e, a parità di anno, il job creato più recentemente. Job `pending`, `processing` o `failed` non modificano il perimetro finché non risultano `completed`. Gli item sono persistenti e idempotenti; il worker può prelevarne un numero limitato per ciclo tecnico senza creare nuove campagne visibili. SISTER non espone eventi push e applica CAPTCHA, finestre operative e limiti di sessione, quindi il significato operativo di "tempo reale" è copertura progressiva.

Le sorgenti sono ordinate stabilmente:

| Priorita | Scope | Default refresh | Richiesta |
| --- | --- | --- | --- |
| 10 | particelle presenti a ruolo | 168 ore | storica per immobile |
| 20 | soggetti presenti a ruolo | 168 ore | attuale per soggetto |
| 30 | particelle correnti del consorzio | 2160 ore | storica per immobile |
| 40 | soggetti presenti in anagrafe | 2160 ore | attuale per soggetto |

La UI mostra separatamente l'avanzamento delle due fasi e consente di modificare i quattro intervalli e abilitare separatamente priorità primaria e secondaria. La dimensione dei prelievi tecnici non è esposta: dal punto di vista operativo esiste una sola campagna persistente.

## Coordinamento

- `platform-scheduler` verifica il planner ogni minuto.
- Le sorgenti vengono materializzate al massimo ogni 15 minuti; i cicli intermedi riconciliano richieste e scadenze senza ripetere il full scan. La materializzazione usa iteratori e blocchi da 1.000 target, evitando di caricare in memoria l'intero storico del Ruolo o l'intera coda persistente.
- `catasto_perpetual_sync_items` conserva scope, chiave deduplicata, priorita, prossimo aggiornamento, tentativi, batch/richiesta collegati ed errore.
- Le fasi a ruolo sono elaborate in ordine rigido nella stessa campagna: prima `ruolo_particella`, poi `ruolo_soggetto`. Gli scope secondari restano successivi e distinti.
- Un'esecuzione tecnica `perpetual_sync` già `pending` o `processing` impedisce di crearne un'altra.
- Il lock advisory PostgreSQL per utente rende single-flight scheduler, refresh manuale e `run-now`.
- `completed` e `not_found` sono terminali e tornano in coda soltanto se la sorgente cambia; `skipped` è terminale.
- Gli errori tecnici usano backoff e massimo tre tentativi complessivi nel worker. Dopo il terzo tentativo l'item resta `failed` fino al retry manuale della campagna.

## Pool SISTER

Quando AutoSync è `ON`, la configurazione mostra e salva una allowlist di profili dedicati. Ogni credenziale può essere attivata singolarmente o insieme alle altre e può avere una propria finestra settimanale AutoSync, separata dagli orari globali usati dalle elaborazioni manuali. Il super admin può usare account appartenenti a utenti GAIA diversi; gli altri utenti restano limitati al proprio pool. Una credenziale entra nell'esecuzione tecnica solo se:

- e attiva;
- e dentro la finestra settimanale del proprio profilo AutoSync, se configurata;
- non esiste una lease globale non scaduta sullo stesso `sister_username`.

Il worker rivaluta disponibilita, profilo AutoSync, cooldown e lease tra due visure. Quando AutoSync viene portato su `OFF`, o una singola credenziale viene disabilitata, la visura già avviata termina; poi il worker esegue logout e rilascia la lease senza interrompere batch manuali.

Per le ricerche immobiliari, il flusso batch esistente per comune, foglio e particella resta autorevole: esegue integralmente l'attesa e la classificazione del primo submit. Soltanto quando quel flusso termina con lo specifico errore `Submit visura non avanzato per richiesta ...` e SISTER segnala che la sezione catastale è obbligatoria, il worker applica una recovery circoscritta. Se il menu contiene esattamente un solo elemento `<option>` valido e non vuoto, seleziona quel valore, ripete una sola volta il submit e rientra nello stesso flusso batch. Opzioni duplicate sono considerate multiple. Con zero o più sezioni disponibili, in presenza di qualsiasi altro errore batch o se l'ispezione DOM fallisce, non effettua scelte arbitrarie e conserva integralmente l'errore originale.

## API e osservabilita

- `GET/PUT /elaborazioni/ruolo-autosync/config`: configurazione compatibile, estesa con profili credenziale AutoSync, orari settimanali dedicati, scope e intervalli.
- `GET /elaborazioni/ruolo-autosync/status`: stato compatibile, conteggi per scope, credenziali disponibili e dashboard operativa aggregata.
- `GET /elaborazioni/ruolo-autosync/campaigns/{scope}/items`: elenco completo owner-scoped della campagna richiesta, paginato con `limit`/`offset`, `total` e `has_more`.
- `POST /elaborazioni/ruolo-autosync/refresh-source`: full refresh manuale; usa le quattro sorgenti quando e configurata l'allowlist continua.
- `POST /elaborazioni/ruolo-autosync/run-now`: riconcilia e tenta l'avvio della prossima porzione della campagna attiva.
- `POST /elaborazioni/ruolo-autosync/campaigns/{scope}/retry-failed`: rimette in coda soltanto gli item `failed` della campagna a ruolo richiesta e azzera il contatore dei tentativi manualmente riaperti.

La UI carica progressivamente le due liste con **Carica altri**. Il campione `perpetual_recent_items` resta un dato di osservabilita e non viene presentato come elenco completo della campagna.

Per diagnosi verificare `last_source_refresh_at`, `last_planner_at`, `last_batch_started_at`, `last_error_message`, i conteggi `scope_counts` e l'esecuzione `perpetual_sync` più recente. Un `run-now` senza nuova esecuzione non è un errore: può indicare assenza di item dovuti, pool fuori orario/occupato o attività già in corso.

### Dashboard operativa AutoSync

La schermata **Attivita AutoSync** e collocata sopra la configurazione e tratta la sincronizzazione continua come il dettaglio aggregato di un job permanente. Espone:

- visure scaricate da SISTER, comprovate da record persistiti in `catasto_documents`;
- richieste totali, completate, fallite e bloccate;
- velocita oraria sul periodo osservato e durata media dei batch conclusi;
- andamento UTC delle ultime 24 ore con completate, fallite e documenti prodotti;
- stato delle quattro fasi: refresh sorgenti, planner/coda, elaborazione progressiva e archiviazione;
- credenziali selezionate/disponibili e postura del worker derivata dal batch attivo;
- ultime esecuzioni AutoSync con avanzamento e link a `/elaborazioni/batches/<ID>`;
- eventi strutturati, errori, CAPTCHA e altri blocchi con collegamento al batch.

Le metriche sono calcolate esclusivamente sui batch `ruolo_autosync` e `perpetual_sync` dell'utente corrente. I log Docker non vengono analizzati dalla UI. La voce worker indica soltanto `in elaborazione` o `in attesa` in base alla presenza di un batch attivo e non equivale a un healthcheck del container. Analogamente, `Lock / concorrenza` indica batch attivo/libero e non pretende di rappresentare una lettura live degli advisory lock PostgreSQL.

Il throughput usa le richieste completate nel periodo divise per l'intervallo realmente osservato, con denominatore minimo di un'ora. Le durate medie includono soltanto batch con `started_at` e `completed_at`. I conteggi degli intervalli `168` e `2160` restano ore, non quantita di record.

## Validazione prima del rollout

- Eseguire i test mirati backend con coverage al 100% su `elaborazioni_perpetual_sources`, `elaborazioni_perpetual_sync`, `elaborazioni_ruolo_autosync` e `autosync_scheduler`.
- Eseguire il test del pannello continuo con coverage al 100% e il typecheck TypeScript dell'intero frontend.
- Verificare che `python -m alembic heads` restituisca una sola head,
  `20260901_1100`, che aggiunge i profili credenziale dedicati ad AutoSync.
- Eseguire il round-trip della migrazione su PostgreSQL impostando `GAIA_TEST_POSTGRES_URL`; il test SQLite valida il contratto di base ma non sostituisce la prova sul database di produzione.
- Eseguire il quality ratchet contro il merge-base prima dell'integrazione.

## Rollback

Disattivare il toggle nella UI. La richiesta di uscita ferma il batch AutoSync dopo la visura corrente, effettua logout e libera la lease; i batch manuali non vengono cancellati. Gli item persistiti restano disponibili e un successivo passaggio `OFF -> ON` riprende la stessa campagna dalla fase e dagli elementi ancora aperti. Il downgrade schema rimuove `catasto_perpetual_sync_items` e le estensioni della configurazione, quindi deve essere preceduto da backup se lo storico operativo va conservato.

## Evidenza integrazione 2026-08-29

- Suite backend combinata GIS e perpetual-sync verde; coverage dei quattro runtime perpetual `675/675`, `100%`.
- Pannello continuo incluso nella suite frontend completa: `184` file e `1654` test verdi; typecheck e build verdi.
- Round-trip della migration perpetual passato su PostgreSQL effimero isolato.
- Catena Alembic unificata dalla revision `20260901_1000`; `alembic heads` restituisce una sola head.
- Quality ratchet contro `origin/main@840c0100` verde, senza finding e senza aggiornare la baseline.
