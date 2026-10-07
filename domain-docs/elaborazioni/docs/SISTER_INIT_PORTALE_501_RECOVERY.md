# SISTER initPortale HTTP 501

Il `501` restituito da `/portale-rest/rs/initPortale` e un errore HTTP reale,
ma non implica sempre che il login SISTER sia fallito. Il worker distingue i
seguenti casi:

- Se la pagina e la Home dei Servizi e mostra `Consultazioni e Certificazioni`,
  il `501` e non bloccante: il worker continua senza refresh.
- Se il `501` interrompe il login e la pagina non segnala sessione bloccata o
  credenziali rifiutate, il worker aggiorna **una sola volta** la pagina. Prosegue
  solo se dopo il refresh la Home o l'informativa privacy sono pronte e l'area
  visure si apre correttamente.
- Se il `501` arriva sulla pagina `Utente bloccato / gia' in sessione`, non
  viene fatto refresh: il worker usa il recupero sessione gia' esistente
  (chiusura sessione, attesa e un solo nuovo login). Un secondo blocco fallisce
  come `SISTER_SESSION_LOCKED`, senza ulteriori recovery.
- Se il refresh scade o la pagina resta non pronta, resta valido l'errore
  originale e il normale cooldown/retry del worker decide quando riprovare.
  Non viene inviata alcuna visura durante il recupero del login.

La prova controllata del 2026-09-27 ha osservato 15 login con `501` non
bloccante; un refresh sulla Home ha mantenuto accessibile l'area visure. Non e
stata ancora osservata dal probe una sessione bloccante recuperata dal refresh.
La regola di recupero e quindi prudenziale e limitata a un solo tentativo.

## Osservabilita e cinque interventi (2026-10-07)

Stato: implementati e verificati localmente; **non deployati** da questo intervento.
Nessuna modifica a database, credenziali, scheduling o policy di retry.

1. La risposta 501 viene conservata: durante `ensure_authenticated` la
   classificazione e differita fino all'esito. Solo un login completato dal
   flusso esistente produce `http_warning/non_blocking/warning`; login fallito
   o risposta fuori dal login restano `http_error/error/error`. La classificazione
   riguarda esclusivamente il path esatto `/portale-rest/rs/initPortale` su host AdE.
2. La Home valida continua senza refresh/retry: questa regola esistente non
   cambia. I recovery per login realmente bloccante restano attivi.
3. Il messaggio dettagliato del caso non bloccante passa da warning a debug.
   Gli eventi individuali rimangono nel DB per audit; il report efficienza aggiunge
   `accounts[].init_portale_hourly`, aggregato per credenziale/ora UTC, senza
   stampe di username, query URL, cookie o segreti. Non si eliminano eventi storici.
4. `duration_ms` delle risposte HTTP misura `responseStart - requestStart`
   da Playwright: attesa degli header, **non** download del body o tempo perso
   complessivo. Timing assente, negativo, non finito o non leggibile resta null.
   Sessione, credenziale, run e richiesta usano il binding corrente; prima di
   conoscere una richiesta il suo ID resta null, non viene inventato.
5. L'alert API `sister-http-5xx` esclude solo i 501 confermati non bloccanti.
   Il report orario segnala un 501 soltanto con login fallito nella stessa
   sessione (anche tra ore diverse), invii assenti/falliti con lavoro presente,
   oppure download sotto il 50% dell'ora precedente a domanda sufficiente.
   Gli indicatori sono correlazioni operative, non dimostrano causalita.

### Report e limiti

```bash
PYTHONPATH=backend backend/.venv/bin/python scripts/sister_autosync_efficiency.py --user-id ID --hours 24
```

Il comando usa una transazione read-only. Invii e download sono deduplicati
per request ID, o event ID se ignoto. Per gli invii contano solo gli step
`prepare_download`, `captcha_submit`, `subject_search`: `waiting` e un esito
funzionale, la compilazione del form non dimostra un invio remoto.
L'indicatore assenza invii richiede tentativi di invio o esecuzioni, senza
download riusciti; le esecuzioni di solo polling non generano questo allarme.

Gli allarmi di throughput richiedono due ore complete, entrambe interamente
disponibili nel calendario corrente. Ore parziali/fuori fascia e bassa domanda
non attivano il confronto. Il login fallito resta segnalabile nelle ore parziali.
I calendari storici e la reale occupazione delle lease non sono ricostruiti.
Il report non introduce un daemon, notifiche esterne o monitoraggi pianificati.

I 716 eventi storici osservati erano risposte HTTP reali, ma non equivalgono
a 716 visure fallite. Non hanno timing: il tempo perso storico resta
**non misurabile**, non zero. Il report li lascia nel conteggio
`unclassified_or_blocking`, senza riclassificarli retroattivamente come soft.
`response_wait_ms` somma solo i campioni misurati, con il relativo
`measured_responses`: non e una stima del rallentamento della lavorazione.

### Matrice di verifica

| Comportamento | Test |
| --- | --- |
| 501 recuperato soft, errore bloccante conservato, un solo tentativo, correlazione | `test_init_portale_501_is_classified_after_login_without_retry` |
| Home valida senza errore/recovery; utente bloccato resta errore | `test_init_portale_501_validates_home_before_ignoring_http_error` e suite browser esistente |
| Endpoint esatto; timing invalido/mancante resta null | `test_soft_warning_is_limited_to_exact_init_portale_endpoint`, `test_response_duration_does_not_invent_missing_or_invalid_timings` |
| Persistenza/API: warning non nei failure/alert, 501 bloccanti restano allarmi | `test_confirmed_non_blocking_init_portale_responses_do_not_raise_server_alerts`, `test_soft_warning_filter_does_not_suppress_other_endpoints_or_statuses` |
| Aggregazione, deduplica, calendario, domanda, polling, sessioni tra ore | `tests/test_sister_http_health.py` |
| Report read-only e compatibilita misure precedenti | `tests/test_sister_efficiency.py` |

Residui operativi: commit/deploy e osservazione sul CED richiedono un'autorizzazione
separata. Nessun tempo perso storico viene attribuito automaticamente ai 501.

### Evidenze locali

- 85 test mirati worker/report e 5 test API/persistenza PASS.
- Tutti i cinque file runtime nuovi/modificati hanno coverage full-file 100%:
  796 statement e 184 branch, nessuna exclusion aggiunta. Evidenze:
  `/tmp/sister-501-coverage.json`, `/tmp/sister-501-backend-coverage.json`.
- Ruff sui file della slice, format-check dei due file nuovi e diff-check PASS.
  Il `make lint-backend` globale fallisce su 19 violazioni nella modifica
  concorrente di `mobile_sync.py`, fuori scope: non sono state corrette qui.
- Ratchet di complessita PASS contro merge-base `703f8411` (`origin/main`),
  nessun finding e nessuna modifica di baseline. Le responsabilita di timing,
  classificazione HTTP e indicatori orari sono separate; il nuovo aggregatore
  ha cognitive 17/cyclomatic 10, un warning non bloccante. Il riepilogo orario
  interno ha sei parametri, altro warning non bloccante. Nessun nuovo errore.
- Graphify worker, backend e dominio docs aggiornati; estrazione semantica
  docs completata (`chunk 1/1 done`), senza warning di chunk falliti.
- Nessun frontend, migration, schema REST, autenticazione o permesso modificato.
  Il report resta read-only; i test API preservano l'isolamento per utente.
- Il primo `make test-worker` senza root nel PYTHONPATH non trova il modulo
  `scripts` importato da un test gia esistente. La suite isolata va lanciata
  con `PYTHONPATH="$PWD" make test-worker`, senza modificare il Makefile
  concorrente. Un warning runpy gia presente resta nella suite mirata.
