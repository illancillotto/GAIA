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
- `GET /elaborazioni/ruolo-autosync/status`: stato compatibile, conteggi per scope e credenziali disponibili ora.
- `POST /elaborazioni/ruolo-autosync/refresh-source`: full refresh manuale; usa le quattro sorgenti quando e configurata l'allowlist continua.
- `POST /elaborazioni/ruolo-autosync/run-now`: riconcilia e tenta l'avvio di un micro-batch; mantiene il comportamento v1 sulle configurazioni legacy a credenziale singola.

Per diagnosi verificare `last_source_refresh_at`, `last_planner_at`, `last_batch_started_at`, `last_error_message`, i conteggi `scope_counts` e il batch `perpetual_sync` piu recente. Un `run-now` senza batch non e un errore: puo indicare assenza di item scaduti, pool fuori orario/occupato o micro-batch gia attivo.

## Rollback

Disattivare il toggle nella UI. Gli item persistiti restano disponibili per la ripresa; i batch gia in lavorazione non vengono cancellati implicitamente. Il downgrade schema rimuove `catasto_perpetual_sync_items` e le estensioni della configurazione, quindi deve essere preceduto da backup se lo storico operativo va conservato.
