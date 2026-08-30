# Sincronizzazione Catastale Continua

## Obiettivo e SLA

Il planner mantiene aggiornate le visure mediante micro-batch finiti e idempotenti. Non promette consistenza istantanea: SISTER non espone eventi push e applica CAPTCHA, finestre operative e limiti di sessione. Il significato operativo di "tempo reale" e quindi copertura continua entro gli SLA configurati.

Le sorgenti sono ordinate stabilmente:

| Priorita | Scope | Default refresh | Richiesta |
| --- | --- | --- | --- |
| 10 | particelle presenti a ruolo | 168 ore | storica per immobile |
| 20 | soggetti presenti a ruolo | 168 ore | attuale per soggetto |
| 30 | particelle correnti del consorzio | 2160 ore | storica per immobile |
| 40 | soggetti presenti in anagrafe | 2160 ore | attuale per soggetto |

La UI consente di modificare i quattro SLA, abilitare separatamente priorita primaria e secondaria e limitare il numero di righe per micro-batch.

## Coordinamento

- `platform-scheduler` verifica il planner ogni minuto.
- Le sorgenti vengono materializzate al massimo ogni 15 minuti; i cicli intermedi riconciliano richieste e scadenze senza ripetere il full scan.
- `catasto_perpetual_sync_items` conserva scope, chiave deduplicata, priorita, prossimo aggiornamento, tentativi, batch/richiesta collegati ed errore.
- Un micro-batch `perpetual_sync` gia `pending` o `processing` impedisce di crearne un altro.
- Il lock advisory PostgreSQL per utente rende single-flight scheduler, refresh manuale e `run-now`.
- Un esito `completed` o `not_found` pianifica il prossimo SLA; `failed`/`skipped` applicano retry a 15 minuti oppure 6 ore quando e presente un codice di blocco.

## Pool SISTER

La configurazione salva una allowlist di credenziali. Il super admin puo usare account appartenenti a utenti GAIA diversi; gli altri utenti restano limitati al proprio pool. Una credenziale entra nel micro-batch solo se:

- e attiva;
- e dentro la propria finestra settimanale;
- non esiste una lease globale non scaduta sullo stesso `sister_username`.

Il worker continua a rivalutare disponibilita, cooldown e lease. Un batch manuale puo quindi proseguire con credenziali diverse da quelle momentaneamente usate dal planner.

## API e osservabilita

- `GET/PUT /elaborazioni/ruolo-autosync/config`: configurazione compatibile, estesa con pool, scope, SLA e dimensione micro-batch.
- `GET /elaborazioni/ruolo-autosync/status`: stato compatibile, conteggi per scope, credenziali disponibili e dashboard operativa aggregata.
- `POST /elaborazioni/ruolo-autosync/refresh-source`: full refresh manuale; usa le quattro sorgenti quando e configurata l'allowlist continua.
- `POST /elaborazioni/ruolo-autosync/run-now`: riconcilia e tenta l'avvio di un micro-batch; mantiene il comportamento v1 sulle configurazioni legacy a credenziale singola.

Per diagnosi verificare `last_source_refresh_at`, `last_planner_at`, `last_batch_started_at`, `last_error_message`, i conteggi `scope_counts` e il batch `perpetual_sync` piu recente. Un `run-now` senza batch non e un errore: puo indicare assenza di item scaduti, pool fuori orario/occupato o micro-batch gia attivo.

### Dashboard operativa AutoSync

La schermata **Attivita AutoSync** e collocata sopra la configurazione e tratta la sincronizzazione continua come il dettaglio aggregato di un job permanente. Espone:

- visure scaricate da SISTER, comprovate da record persistiti in `catasto_documents`;
- richieste totali, completate, fallite e bloccate;
- velocita oraria sul periodo osservato e durata media dei batch conclusi;
- andamento UTC delle ultime 24 ore con completate, fallite e documenti prodotti;
- stato delle quattro fasi: refresh sorgenti, planner/coda, micro-batch e archiviazione;
- credenziali selezionate/disponibili e postura del worker derivata dal batch attivo;
- ultimi batch AutoSync con avanzamento e link a `/elaborazioni/batches/<ID>`;
- eventi strutturati, errori, CAPTCHA e altri blocchi con collegamento al batch.

Le metriche sono calcolate esclusivamente sui batch `ruolo_autosync` e `perpetual_sync` dell'utente corrente. I log Docker non vengono analizzati dalla UI. La voce worker indica soltanto `in elaborazione` o `in attesa` in base alla presenza di un batch attivo e non equivale a un healthcheck del container. Analogamente, `Lock / concorrenza` indica batch attivo/libero e non pretende di rappresentare una lettura live degli advisory lock PostgreSQL.

Il throughput usa le richieste completate nel periodo divise per l'intervallo realmente osservato, con denominatore minimo di un'ora. Le durate medie includono soltanto batch con `started_at` e `completed_at`. I conteggi degli intervalli `168` e `2160` restano ore, non quantita di record.

## Validazione prima del rollout

- Eseguire i test mirati backend con coverage al 100% su `elaborazioni_perpetual_sources`, `elaborazioni_perpetual_sync`, `elaborazioni_ruolo_autosync` e `autosync_scheduler`.
- Eseguire il test del pannello continuo con coverage al 100% e il typecheck TypeScript dell'intero frontend.
- Sul branch perpetual isolato, verificare che `python -m alembic heads`
  restituisca `20260828_0900`. Dopo l'integrazione GIS completa, la merge
  migration deve produrre una sola head `20260901_1000`.
- Eseguire il round-trip della migrazione su PostgreSQL impostando `GAIA_TEST_POSTGRES_URL`; il test SQLite valida il contratto di base ma non sostituisce la prova sul database di produzione.
- Eseguire il quality ratchet contro il merge-base prima dell'integrazione.

## Rollback

Disattivare il toggle nella UI. Gli item persistiti restano disponibili per la ripresa; i batch gia in lavorazione non vengono cancellati implicitamente. Il downgrade schema rimuove `catasto_perpetual_sync_items` e le estensioni della configurazione, quindi deve essere preceduto da backup se lo storico operativo va conservato.

## Evidenza integrazione 2026-08-29

- Suite backend combinata GIS e perpetual-sync verde; coverage dei quattro runtime perpetual `675/675`, `100%`.
- Pannello continuo incluso nella suite frontend completa: `184` file e `1654` test verdi; typecheck e build verdi.
- Round-trip della migration perpetual passato su PostgreSQL effimero isolato.
- Catena Alembic unificata dalla revision `20260901_1000`; `alembic heads` restituisce una sola head.
- Quality ratchet contro `origin/main@840c0100` verde, senza finding e senza aggiornare la baseline.
