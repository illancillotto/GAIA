# SISTER Debug Runbook

> Nota infrastrutturale
> Il worker Catasto e un servizio tecnico separato, ma il dominio applicativo Catasto resta parte del backend monolite condiviso.

## Scopo

Questo documento raccoglie il comportamento reale osservato del portale SISTER durante l'automazione Catasto, le contromisure implementate nel worker e i prossimi punti da verificare.

Va trattato come riferimento operativo permanente per:

- debug del worker `elaborazioni-worker-visure`
- aggiornamento dei selettori o del flusso browser
- gestione nuovi casi del sito SISTER
- futura automazione di altri servizi sullo stesso portale

## Contesto tecnico

Componenti coinvolti:

- backend API: `backend`
- worker browser: `modules/elaborazioni/worker`
- frontend Catasto: `frontend/src/app/catasto`

File principali del flusso:

- `modules/elaborazioni/worker/worker.py`
- `modules/elaborazioni/worker/browser_session.py`
- `modules/elaborazioni/worker/visura_flow.py`
- `modules/elaborazioni/worker/sister_browser_reliability.py`
- `modules/elaborazioni/worker/sister_captcha_wait.py`
- `modules/elaborazioni/worker/sister_request_rows.py`
- `modules/elaborazioni/worker/sister_worker_reliability.py`
- `modules/elaborazioni/worker/sister_worker_files.py`
- `modules/elaborazioni/worker/sister_observability.py`
- `modules/elaborazioni/worker/sister_telemetry.py`
- `modules/elaborazioni/worker/sister_retention.py`
- `modules/elaborazioni/worker/sister_selectors.json`

Comando utile per rebuild worker:

```bash
docker compose up -d --build --force-recreate elaborazioni-worker-visure
```

Comando utile per i log:

```bash
docker compose logs -f elaborazioni-worker-visure
```

## Telemetria operativa

La superficie `/elaborazioni/portal-health` usa eventi strutturati append-only
salvati in `sister_portal_events`. La strumentazione avvolge il worker e la
sessione browser senza cambiare retry, timeout, concorrenza o transazioni del
flusso visure. La scrittura e fail-open: un errore DB viene loggato e ignorato,
quindi non puo fermare una visura.

Eventi principali:

- inizio e conclusione di ogni tentativo, correlati con batch, richiesta, sessione e run
- durata di login, navigazione, submit, polling, download, logout e tracing browser
- risposte HTTP `5xx` dei soli host `agenziaentrate.gov.it`
- retry richieste, cooldown credenziali e pause globali gia decisi dal worker
- esito persistito della richiesta e stato operativo per credenziale

Sicurezza dei dati:

- l'endpoint conserva solo il path, senza schema, host o query string
- il contesto accetta soltanto chiavi operative predefinite
- password, testo o immagine CAPTCHA, nominativi e riferimenti catastali non vengono registrati
- API e dashboard filtrano sempre gli eventi per `current_user`
- gli eventi recenti espongono `credential_label`, risolta dalla credenziale associata all'evento; username SISTER e segreti non fanno parte della risposta

Superfici:

```text
GET /elaborazioni/portal-health?hours=24
GET /elaborazioni/portal-health/events?hours=24&limit=100
```

La dashboard calcola stato `healthy`, `degraded`, `critical` o `unknown`, tempi
medi/P95, errori raggruppati e alert per risposte `5xx` ripetute, tasso di
errore elevato, P95 oltre 120 secondi e cooldown attivi. La risposta health
include anche `downloads`, con `total`, `by_visura_type` e `by_request_type`.
Il conteggio legge i documenti da `catasto_documents`, usa `created_at` per la
finestra richiesta e applica lo scope del `current_user`; non e quindi un
contatore globale né un'approssimazione ricavata dagli eventi. Ogni elemento
di `credentials` espone inoltre `downloads`: il valore e attribuito tramite la
richiesta collegata al documento e il relativo `sister_credential_id`. Un
documento senza richiesta o credenziale associata contribuisce al totale ma
non a una card del pool. Il refresh
automatico e ogni 30 secondi; le finestre UI sono 24 ore, 7 giorni e 30 giorni.

Retention:

- eventi DB: `ELABORAZIONI_SISTER_EVENT_RETENTION_DAYS`, default `30`
- debug artifact e report: `ELABORAZIONI_SISTER_ARTIFACT_RETENTION_DAYS`, default `14`
- simulazione senza cancellazione: `ELABORAZIONI_SISTER_RETENTION_DRY_RUN=true`
- la pulizia parte al massimo una volta al giorno durante l'attivita del worker
- sono ammesse solo le root debug/report configurate e i link simbolici non vengono seguiti

Il logging Docker del worker visure usa rotazione `json-file`, `10m` per file e
massimo `5` file. Per una diagnosi rapida:

```bash
docker compose logs --since=30m elaborazioni-worker-visure
docker compose exec backend alembic current
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost/api/elaborazioni/portal-health?hours=24"
```

### Verifica automatizzata

I file runtime nuovi o modificati della telemetria devono restare al `100%` sia
su statement sia su branch. I gate sono separati per evitare che gli stub di
`test_worker.py` contaminino gli altri processi:

```bash
cd backend
.venv/bin/python -m pytest tests/test_sister_portal_telemetry.py \
  --cov=app.db.base --cov=app.modules.elaborazioni.router \
  --cov=app.modules.elaborazioni.telemetry_models \
  --cov=app.modules.elaborazioni.telemetry_routes \
  --cov=app.modules.elaborazioni.telemetry_schemas \
  --cov=app.modules.elaborazioni.telemetry_service \
  --cov-branch --cov-fail-under=100
```

Per worker e frontend usare le suite mirate `test_sister_observability.py`,
`test_sister_retention.py`, `test_sister_telemetry.py`, i tre file
`test_worker*.py` e i quattro test `portal-health`/navigazione. Il gate frontend
deve impostare `VITEST_COVERAGE_INCLUDE` sul runtime Portal Health e richiedere
le quattro soglie Vitest al `100%`.

## Stato attuale del debug

Il worker oggi:

- logga in italiano i passaggi principali
- salva screenshot e HTML nei passaggi critici
- aggiorna `current_operation` con fasi più parlanti
- gestisce l'informativa privacy
- nel test credenziali di `/elaborazioni/settings`, considera riuscita la prova solo se dopo l'autenticazione viene eseguito anche il logout applicativo SISTER
- a fine batch/richiesta operativa, prima di chiudere Playwright, tenta il logout applicativo SISTER per ridurre il rischio di sessioni server-side appese
- consente di usare `Pausa e libera` sulla singola card credenziale: persiste `active=false`, completa al massimo la richiesta gia in corso e al checkpoint successivo esegue il logout applicativo e chiude soltanto quel browser
- isola normalmente il pool credenziali SISTER per utente GAIA: il DB accetta lo stesso `sister_username` su utenti diversi, ma lo rende univoco dentro il singolo pool tramite `UNIQUE (user_id, sister_username)`; una batch condivisa del `super_admin` costituisce l'unica eccezione e aggrega tutte le credenziali attive disponibili per fascia
- serializza comunque l'uso reale dell'account SISTER tramite `catasto_credential_leases`: la chiave e `sister_username`, quindi due pool GAIA non possono aprire sessioni simultanee dello stesso account
- quando un batch fallito viene rilanciato, il backend aggiorna il riferimento temporale della rimessa in coda per evitare che la routine di expiry dei `pending` lo consideri subito orfano
- prova a chiudere una sessione SISTER già attiva
- aspetta alcuni secondi dopo `CloseSessionsSis` prima di ritentare il login
- usa OCR locale Tesseract per i CAPTCHA testuali
- può fare fallback su Anti-Captcha se configurato in `.env`

## Pausa e rilascio di una singola sessione

Nel pool credenziali di `/elaborazioni/settings`, il comando `Pausa e libera`
agisce sulla sola card selezionata. Il frontend aggiorna la credenziale con
`PATCH /elaborazioni/credentials/{credential_id}` e payload `active=false`.
Non si tratta di un toggle temporaneo in memoria: per riutilizzare l'account e
necessario modificarlo e riattivarlo esplicitamente.

Il worker rilegge lo stato persistito prima di acquisire una nuova richiesta e
dopo ogni richiesta completata. Quando rileva la pausa:

- rimuove la credenziale dal pool disponibile del batch;
- non acquisisce altre richieste per quell'account;
- completa il blocco `finally`, tenta il logout applicativo SISTER e chiude la sola sessione Playwright interessata;
- lascia operative le altre credenziali attive del pool.

Le richieste remote conservano sempre l'affinita con la credenziale SISTER che
le ha create. La pausa non autorizza un altro account a riprenderle: vengono
marcate non disponibili secondo il contratto `sister_credential_unavailable`.
Se non resta alcuna credenziale attiva o autenticabile, il worker rilascia il
batch; dopo aver riattivato o aggiornato il pool, usare la normale azione di
ripresa senza ricreare il lotto.

## Fasce orarie per credenziale

Ogni profilo SISTER puo limitare l'uso automatico del worker a un calendario
settimanale. La UI `Credenziali` espone il toggle `Usa solo fuori dall'orario
dell'operatore`, un editor giorno per giorno con un massimo di quattro fasce
giornaliere e il preset lunedi-venerdi `18:00-08:00`, sabato-domenica
`00:00-00:00`. Le fasce possono essere aggiunte e rimosse indipendentemente per
ogni credenziale; la relativa card mostra il riepilogo settimanale e lo stato di
disponibilita corrente. Un intervallo con ora iniziale uguale all'ora finale
copre l'intera giornata; quando l'inizio e successivo alla fine, la fascia
prosegue nel giorno seguente.

Regole operative:

- il calendario usa sempre `Europe/Rome`, inclusi i cambi tra ora solare e ora legale;
- una batch condivisa appartenente a un `super_admin` applica le stesse regole di calendario a tutte le credenziali GAIA e avvia un runner concorrente per ogni profilo disponibile; per gli altri ruoli la selezione resta limitata al proprietario della batch;
- `schedule_enabled=false` lascia la credenziale disponibile senza vincoli orari;
- il worker verifica la disponibilita prima di aprire la sessione e la ricontrolla almeno ogni minuto quando nessun profilo e utilizzabile;
- nei batch con pool condiviso, mentre almeno un runner mantiene il lotto in esecuzione, il worker rilegge il pool ogni `ELABORAZIONI_POLL_INTERVAL_SEC` secondi e apre un runner per ogni nuova credenziale attiva e in fascia;
- l'espansione e incrementale: le sessioni gia aperte continuano senza logout o restart e il claim atomico impedisce che due credenziali prendano la stessa richiesta;
- i batch con `credential_id` valorizzata restano vincolati al profilo scelto e non acquisiscono nuove credenziali;
- un ID gia avviato, rifiutato o messo in pausa non viene riaperto nello stesso lotto; una sua riattivazione viene applicata al batch successivo o a una ripresa esplicita;
- una sessione gia aperta non viene interrotta a meta richiesta quando termina la fascia;
- al checkpoint successivo alla richiesta, un profilo uscito dalla fascia esegue logout, chiude il browser e rilascia la lease; se la fascia riapre, il runner riacquisisce la lease prima di ricreare la sessione;
- la lease scade dopo 15 minuti solo come recovery da crash ed e rinnovata ogni minuto anche durante richieste SISTER lente; se il rinnovo fallisce, il runner chiude la propria sessione al checkpoint successivo e non acquisisce nuove richieste;
- se lo stesso account e gia in uso da un altro batch o worker, il runner resta in attesa senza aprire Playwright e riprova al poll successivo;
- se tutti i profili sono temporaneamente fuori fascia, il batch resta `processing` e riparte automaticamente senza intervento;
- `Testa` e `Testa tutte` ignorano il calendario, per consentire sempre la verifica manuale delle credenziali;
- `Pausa e libera` prevale sul calendario: una credenziale con `active=false` non viene usata neppure durante una fascia disponibile.

Persistenza e API:

- `schedule_enabled` abilita il vincolo sulla singola riga `catasto_credentials`;
- `availability_schedule` contiene timezone e mappa settimanale dei giorni `0`-`6`, da lunedi a domenica;
- `POST /elaborazioni/credentials` e `PATCH /elaborazioni/credentials/{credential_id}` validano formato `HH:MM`, giorni, struttura degli intervalli e limite di quattro fasce giornaliere;
- `GET /elaborazioni/credentials` restituisce il calendario per alimentare stato corrente e prossima fascia nella UI.

Esempio:

```json
{
  "schedule_enabled": true,
  "availability_schedule": {
    "timezone": "Europe/Rome",
    "weekly": {
      "0": [
        {"start": "06:00", "end": "08:00"},
        {"start": "18:00", "end": "23:00"}
      ],
      "5": [{"start": "00:00", "end": "00:00"}]
    }
  }
}
```

## Affidabilita richieste e Profilo A

Per il runtime visure la convenzione ammessa e:

```text
idConv=1050380
CONSORZIO DI BONIFICA DELL'ORISTANESE (CONSULTAZIONI - PROFILO A)
```

La pagina reale multi-convenzione espone lo stesso ID sul radio `name=idConv` e
la stessa label. Il worker seleziona il radio per ID, valida la label
normalizzata e fallisce senza proseguire se ID o label sono mancanti, duplicati
o inattesi. Non serve un flag sulle credenziali: la scelta avviene nella
sessione SISTER e vale anche per geometri con Profilo A e Profilo B attivi.

Il test credenziali non si ferma al login: raggiunge l'area visure dopo la
selezione del Profilo A. Una credenziale non viene quindi marcata verificata se
il profilo richiesto non e disponibile.

Prima di ogni invio il worker acquisisce la baseline delle righe presenti in
`ConsultazioneRichieste`. Se lo snapshot non e leggibile, la richiesta viene
differita con `last_error_code=sister_correlation_error`; non e mai ammessa una
baseline vuota implicita. Dopo il submit vengono persistiti ID/URL/stato remoto
e credenziale SISTER. Poll, download ed eliminazione dei `non_evadibile`
operano soltanto sulla riga correlata; ogni ambiguita interrompe il flusso in
modo fail-closed.

Una richiesta remota ripresa dopo restart resta vincolata alla credenziale che
l'ha creata. Se quella credenziale non e piu attiva o disponibile, la richiesta
termina con `last_error_code=sister_credential_unavailable` invece di essere
presa da un altro account o restare in attesa infinita. Un retry manuale
conserva il vincolo finche lo stato remoto e attivo, cosi riprende la stessa
richiesta senza duplicarla; per richieste senza stato remoto attivo acquisisce
una nuova baseline e azzera i riferimenti remoti precedenti.

Retry e concorrenza sono persistiti su database tramite `retry_not_before`,
`last_error_code` ed `execution_token`. Il token impedisce a un'esecuzione
obsoleta di aggiornare stato o documenti dopo cancel, release, retry o nuova
presa in carico. Anche l'ingresso e il polling dell'attesa CAPTCHA manuale
verificano batch e token, quindi una cancellazione concorrente non puo
riattivare la richiesta e interrompe subito l'attesa. Gli errori temporanei
usano backoff e limite tentativi; gli outcome `not_found`, `failed` e
`non_evadibile` restano distinti.

I PDF sono scaricati in un file `.part`, validati tramite firma `%PDF-`, quindi
rinominati atomicamente. Il path include utente, batch, richiesta e token di
esecuzione; `catasto_documents.sha256` conserva l'hash del contenuto.

Naming variabili ambiente:

- i nomi canonici correnti del worker usano prefisso `ELABORAZIONI_*`
- i precedenti nomi `CATASTO_*` restano supportati come fallback di compatibilita

Artifact salvati in:

```text
/data/catasto/debug/connection-tests/<timestamp>/
```

Tipologie di artifact oggi prodotti:

- `trace-browser-started.*`
- `trace-login-page.*`
- `trace-login-after-submit.*`
- `trace-privacy-notice-detected.*`
- `trace-privacy-notice-confirmed.*`
- `trace-session-recovery-close.*`
- `visura-menu-timeout-attempt-N.*`
- `login-timeout.*`
- `login-error.*`

## Flusso reale osservato su SISTER

### 1. Login IAM

Il worker apre:

```text
https://iampe.agenziaentrate.gov.it/sam/UI/Login?realm=/agenziaentrate
```

Compila username e password e invia il form.

Nota:

- subito dopo il submit, il contenuto pagina può essere ancora in transizione
- in quel punto il dump HTML può fallire con errore Playwright su pagina in navigazione
- il flusso non è necessariamente fallito: è un effetto collaterale del tracing troppo anticipato

### 2. Informativa privacy

Caso osservato negli screenshot:

- titolo pagina: `Home dei Servizi`
- presenza box: `Informativa trattamento dei dati personali`
- presenza bottone: `Conferma`

Se non viene cliccato `Conferma`:

- il link `Visure catastali` non compare
- il worker sembra bloccarsi sul menu, ma il problema vero è la privacy notice

Gestione implementata:

- rilevazione della stringa `Informativa trattamento dei dati personali`
- click automatico su `Conferma`
- attesa del `domcontentloaded`

### 2.1 Informativa Visure

Caso osservato durante la richiesta di visura storica sintetica:

- dopo il login e il click su `Visure catastali`, SISTER apre `Visure/Informativa.do`
- il flusso puo arrivare gia in area Visure prima di `open_visura_form()`
- il comando `Conferma Lettura` puo essere renderizzato come `input submit` e non come button ARIA

Gestione implementata:

- `open_visura_form()` non ripete la navigazione menu se la pagina e gia in `/Visure/` o se il form catastale e gia disponibile
- la conferma dell'informativa Visure usa candidati multipli (`input`, `button`, `a`, testo) prima di procedere
- dopo la conferma viene atteso `domcontentloaded` e tracciato lo stato `visura-informativa-confirmed`
- dopo la scelta provincia, il form iniziale puo restare su `Persona fisica`; per le richieste immobile il worker forza il click sulla voce `Immobile` prima della compilazione
- nella pagina CAPTCHA della visura immobile il campo corrente osservato e `input[name='inCaptchaChars']`; il vecchio selettore `codSicurezza` non e piu valido per questo flusso
- nella pagina `Tipo di visura`, i valori radio osservati sono `0=Completa`, `3=Storica Analitica`, `4=Storica Sintetica`; la scansione `ade_status_scan` usa `request_type=STORICA` e `tipo_visura=Sintetica`, quindi deve selezionare valore `4`
- nelle ricerche immobile non esiste una radio separata `Storica`: la storicita e codificata esclusivamente da `tipoVisura=3` o `tipoVisura=4`; la radio `Storica` resta pertinente soltanto al form delle ricerche soggetto
- per una richiesta immobile storica il tipo `Analitica`/`Sintetica` deve essere visibile, selezionabile e confermato; il worker lo riconferma immediatamente prima di ogni `Inoltra`, compresi i retry CAPTCHA, perche SISTER puo ripristinare `Completa`
- se il tipo storico richiesto non puo essere confermato, la richiesta viene differita con `last_error_code=sister_invalid_document` senza persistere un eventuale PDF attuale
- dopo la scelta del tipo visura, SISTER puo mostrare una pagina intermedia senza CAPTCHA e senza bottone `Salva`; in questo caso il worker esegue un click preliminare su `Inoltra` e poi attende la comparsa del CAPTCHA o del download PDF
- se SISTER mostra da due a tre righe scaricabili equivalenti per la stessa particella, il worker seleziona la piu recente; oltre tre righe, oppure con descrizioni o link non equivalenti, la correlazione resta fail-closed e viene differita

### 2.2 Verifica Attualita/Storica e contenuto PDF

Il worker analizza il PDF scaricato e traccia separatamente tipo richiesto, tipo
osservato e stato della particella richiesta. Per le visure immobile il controllo
del tipo e fail-closed: un PDF difforme, non classificabile o non analizzabile
viene eliminato, non viene persistito come completato e la richiesta torna in
retry con `last_error_code=sister_invalid_document`.

Sia `sister_invalid_document` sia `sister_correlation_error` azzerano ID, URL,
stato remoto, affinita credenziale e baseline della richiesta. Il retry deve
quindi ripartire da una nuova richiesta SISTER invece di riprendere una
richiesta remota ambigua o gia associata a un documento difforme.

Log attesi per un flusso coerente:

```text
Elaborazione richiesta ... tipo_visura=Sintetica request_type=None
Audit visura PDF: request_id=... classificazione=current tipo_richiesto=STORICA tipo_osservato=STORICA ...
```

Anomalie ricercabili:

```text
Audit visura PDF: ... classificazione=suppressed ...
Audit visura PDF: ... classificazione=unknown ...
Audit visura PDF non riuscito
PDF SISTER difforme: richiesto STORICA, scaricato ATTUALITA
```

Ogni PDF analizzato genera un evento strutturato:

```text
event_type=pdf_parcel_status
step=document_audit
outcome=current|suppressed|not_found|unknown|parse_failed
```

Diagnosi rapida sul worker:

```bash
docker compose logs --since=24h elaborazioni-worker-visure 2>&1 \
  | grep -E "Audit visura PDF"
```

Per un batch di sole visure storiche, la verifica DB minima deve restituire
zero righe difformi:

```sql
SELECT COUNT(*) AS documenti_difformi
FROM catasto_documents AS document
JOIN catasto_visure_requests AS request ON request.document_id = document.id
WHERE request.batch_id = :batch_id
  AND (
    document.content_request_type IS DISTINCT FROM 'STORICA'
    OR request.request_type IS DISTINCT FROM 'STORICA'
  );
```

### 2.2.1 Regressione e coverage

La suite worker deve essere eseguita tramite il target isolato, perche
`test_worker.py` installa stub globali che possono contaminare una collection
pytest unica:

```bash
make test-worker
```

Nel checkout validato il target esegue `406` test. Gli otto runtime SISTER
modificati (`browser_session`, pool credenziali, validazione documento, righe
remote, metadata retry, selezione visura, repository affidabilita e worker)
sono coperti al 100% con `2774/2774` statement e `786/786` branch. Il totale
worker legacy resta al 93% e non sostituisce il gate per-file sui runtime
toccati.

I nuovi confini per l'allowlist batch hanno gate separati:

```bash
PYTHONPATH=backend backend/.venv/bin/python -m pytest -q \
  backend/tests/test_elaborazioni_batch_credentials.py \
  --cov=app.services.elaborazioni_batch_credentials \
  --cov-branch --cov-fail-under=100

cd frontend
VITEST_COVERAGE_INCLUDE=src/components/elaborazioni/batch-credential-selector.tsx \
  npm run test:coverage -- tests/unit/batch-credential-selector.test.tsx
```

Il servizio backend copre `32/32` statement e `12/12` branch. Il selettore UI
copre `25/25` statement, `19/19` branch, `10/10` funzioni e `22/22` linee.

### 2.2.2 Statistiche per batch

`GET /elaborazioni/batches/{batch_id}` espone anche `statistics`, calcolato al
momento della richiesta senza nuove colonne o contatori denormalizzati. La UI
lo mostra nel dettaglio batch, nell'archivio tramite il dettaglio modale e in
forma compatta nella lista dei batch recenti.

Semantica dei valori:

- `duration_seconds`: dal primo evento `execution_start` disponibile, con
  fallback a `started_at`; usa `completed_at` solo per batch terminali e
  l'istante corrente per batch `pending` o `processing`, ignorando eventuali
  timestamp di chiusura rimasti da un run precedente;
- `completed_per_hour`: sole visure completate divise per la durata effettiva;
- `processed_per_hour`: tutti gli esiti terminali divisi per la durata;
- `progress_percent`: esiti terminali sul totale delle richieste;
- `success_rate_percent`: completate sul totale degli esiti terminali;
- `estimated_remaining_seconds`: durata media per esito terminale moltiplicata
  per le richieste residue; resta `null` finche non esiste un primo esito;
- `total_attempts` e `average_attempts`: tentativi persistiti sulle richieste;
- `credentials_used`: unione tra eventi `execution_start` e affinita persistita
  sulla richiesta, con numero di richieste distinte ed esecuzioni per account.

La telemetria preserva gli account impiegati prima di un retry che azzera
`sister_credential_id`. Per batch precedenti all'introduzione degli eventi il
fallback sulla richiesta identifica comunque l'account finale; in quel caso il
conteggio esecuzioni minimo coincide con il numero di richieste associate.

Coverage dei nuovi runtime:

```text
backend elaborazioni_batch_statistics: 71/71 statement, 22/22 branch
frontend batch-statistics: 24/24 statement, 22/22 branch,
                           9/9 funzioni, 19/19 linee
```

Query DB per gli eventi strutturati:

```sql
SELECT occurred_at, batch_id, request_id, outcome, severity, context_json
FROM sister_portal_events
WHERE event_type = 'pdf_parcel_status'
ORDER BY occurred_at DESC;
```

La classificazione `suppressed` richiede un indicatore riferito alla particella
richiesta: `Numero di mappa soppresso dal`, il titolo `Visura ... per immobile
soppresso` oppure `Variazione in soppressione del`. La sola parola `SOPPRESSO`
in una sezione storica non basta: puo descrivere una particella antenata mentre
la particella richiesta e corrente.

L'audit completo viene persistito su `catasto_documents` nei campi
`content_request_type`, `parcel_classification`, `parcel_suppressed_at` e
`content_metadata_json`. Per cercare i documenti soppressi:

Il tipo atteso usa `request_type` quando esplicito; per le richieste immobile
legacy lo deduce da `tipo_visura`, considerando `Sintetica` e `Analitica` come
storiche e `Completa` come attualita.

```sql
SELECT request_id, filename, parcel_suppressed_at
FROM catasto_documents
WHERE parcel_classification = 'suppressed'
ORDER BY parcel_suppressed_at DESC NULLS LAST;
```

### 2.3 Backfill dei PDF esistenti

La migration deve essere applicata prima del backfill. Il comando e dry-run per
default, accetta un batch specifico e non sovrascrive audit gia valorizzati:

```bash
docker compose exec backend alembic upgrade head
docker compose exec backend python scripts/backfill_catasto_document_audits.py \
  --batch-id UUID_BATCH
docker compose exec backend python scripts/backfill_catasto_document_audits.py \
  --batch-id UUID_BATCH --apply --commit-every 100
```

Usare `--force` soltanto per ricalcolare consapevolmente dati gia classificati.
I contatori `missing_file` e `audit_failed` restano rieseguibili e non vengono
marcati come aggiornati.

### 3. Menu servizi

Caso osservato:

- il click su `Consultazioni e Certificazioni` può andare a buon fine
- il link `Visure catastali` non sempre è disponibile immediatamente
- in alcuni run, invece di entrare nel menu corretto, il portale reindirizza a un blocco sessione

Log diagnostici aggiunti:

- click `Consultazioni e Certificazioni`
- conferma apertura link `Consultazioni e Certificazioni`
- click `Visure catastali`
- conferma apertura link `Visure catastali`

### 4. Sessione già attiva / utente bloccato

Caso osservato in pagina:

- messaggio: `Utente gia' in sessione sulla stessa o altra postazione.`
- link `Chiudi`
- href effettivo: `https://sister3.agenziaentrate.gov.it/Servizi/CloseSessionsSis`

Caso osservato anche come:

- `error_locked.jsp`
- titolo `Utente bloccato`

Gestione implementata:

- classificazione come sessione bloccata
- click automatico solo su link `Chiudi` con `href` verso `CloseSessionsSis`; il link `Esci` dell'header non viene mai cliccato dalla recovery
- fallback a `goto` diretto su `CloseSessionsSis` solo se la pagina non espone link cliccabili verso l'endpoint
- attesa post chiusura sessione
- nuovo tentativo di login una sola volta
- stop immediato del flusso menu se il post-login e' gia' classificato come sessione bloccata

Nota per `/elaborazioni/settings`:

- il test credenziali non deve limitarsi a chiudere il browser Playwright
- dopo il login deve chiamare esplicitamente il logout SISTER/`CloseSessionsSis`
- se l'autenticazione riesce ma il logout non viene confermato, il test viene marcato fallito e la credenziale non viene aggiornata come verificata

Limite noto:

- anche dopo `CloseSessionsSis`, il portale può risultare ancora bloccato se il retry parte troppo presto o se il rilascio lato SISTER non è immediato

### 5. Stato attuale del blocco

L'ultimo comportamento osservato è questo:

1. login IAM avviato
2. primo tentativo di navigazione al menu
3. redirect/blocco su sessione già attiva
4. invio richiesta `CloseSessionsSis`
5. ritorno alla login IAM
6. nuovo login
7. nuovo blocco sessione già attiva

Quindi il problema residuo non è più:

- selettore privacy
- assenza log
- bug di retry del menu

Il problema residuo è:

- tempo o modalità di rilascio della sessione remota su SISTER

## Cronologia sintetica dei casi osservati

### Caso A: timeout su menu visure

Sintomo:

- `Login timeout`
- pagina finale `Home dei Servizi`
- assenza di `Visure catastali`

Causa reale trovata:

- informativa privacy non confermata

### Caso B: crash del retry menu

Sintomo:

- `NameError: name 'asyncio' is not defined`

Causa:

- import mancante nel retry introdotto per `_goto_visura_menu_with_retry`

Risolto.

### Caso C: sessione bloccata

Sintomo:

- `Utente bloccato`
- `error_locked.jsp`
- oppure pagina `Utente gia' in sessione sulla stessa o altra postazione`

Causa:

- sessione SISTER ancora aperta o non rilasciata

Mitigazione implementata:

- chiusura sessione remota
- retry login controllato

### Caso D: credenziali rifiutate

Sintomo:

- `Credenziali errate`
- `Autenticazione fallita`
- oppure `Credenziali SISTER rifiutate dal portale`

Mitigazione implementata:

- classificazione come errore recuperabile della credenziale
- richiesta corrente differita, senza avanzare e fallire in sequenza le altre righe
- cooldown della credenziale e retry tracciato nella telemetria
- per batch grandi, rilascio resumibile fino all'aggiornamento e al test positivo della credenziale

Prima di riprendere una batch rilasciata, aggiornare la password in
`/elaborazioni/settings` ed eseguire il test della credenziale. Il rilascio con
operazione `Release requested by user` preserva le richieste e consente il
riavvio dal portale dopo il test positivo.

## Messaggi utente

Messaggio standardizzato mostrato in UI:

```text
Utente SISTER bloccato sul portale Agenzia delle Entrate. Verificare se esiste gia' una sessione attiva su un'altra postazione o browser. indirizzo link: https://sister3.agenziaentrate.gov.it/Servizi/error_locked.jsp
```

Nel frontend il link finale viene reso cliccabile.

## Strategia CAPTCHA

Ordine attuale dei tentativi:

1. OCR locale con Tesseract
2. fallback Anti-Captcha `ImageToTextTask` se `ANTI_CAPTCHA_API_KEY` è configurata
3. richiesta CAPTCHA manuale all'utente

Variabili ambiente:

```text
ANTI_CAPTCHA_API_KEY=
ANTI_CAPTCHA_POLL_INTERVAL_SEC=3
ANTI_CAPTCHA_TIMEOUT_SEC=120
```

Dettagli implementativi:

- il fallback esterno è inserito in `modules/elaborazioni/worker/visura_flow.py`
- il client API è in `modules/elaborazioni/worker/anti_captcha_client.py`
- i log CAPTCHA distinguono `ocr`, `external`, `manual`
- se Anti-Captcha fallisce o restituisce un testo non accettato da SISTER, il flusso continua comunque verso il CAPTCHA manuale

Riferimenti ufficiali usati per l'integrazione:

- `createTask`: `https://anti-captcha.com/it/apidoc/methods/createTask`
- `getTaskResult`: `https://anti-captcha.com/it/apidoc/methods/getTaskResult`
- `ImageToTextTask`: `https://anti-captcha.com/it/apidoc/task-types/ImageToTextTask`
- errori API: `https://anti-captcha.com/it/apidoc/errors`

## Visure storiche sintetiche per anomalie AdE

Il worker supporta anche richieste `CatastoVisuraRequest` con `purpose=ade_status_scan`.

Questo flusso è usato dal modulo Catasto > Anomalie per verificare su SISTER le `ruolo_particelle` non collegate a `cat_particelle` scaricando la visura storica sintetica:

- usa solo `search_mode=immobile`
- compila comune, catasto, sezione, foglio, particella e subalterno se presenti
- imposta `request_type=STORICA` e `tipo_visura=Sintetica`
- segue il normale flusso CAPTCHA e download PDF
- salva il PDF in `catasto_documents` e lo collega alla richiesta e a `ruolo_particelle.ade_scan_document_id`
- estrae dal PDF soppressioni, particelle originate/variate, particelle soppresse nella variazione e cronologia essenziale
- salva payload strutturato, data verifica ed errore sulle colonne `ruolo_particelle.ade_scan_*`

Il caso `SOPPRESSO` viene determinato dal contenuto della visura storica, non dalla sola pagina `Elenco immobili`, perché la pagina AdE non contiene la catena completa di frazionamento/accorpamento.

## Informazioni da tracciare sempre

Quando si aggiungono nuovi automatismi sul portale, mantenere sempre questi punti:

- URL corrente
- titolo pagina
- body excerpt
- screenshot
- HTML
- step logico corrente
- selettore che si sta cliccando
- eventuale redirect inatteso

Per ogni passaggio importante del browser, preferire:

1. log testuale
2. snapshot pagina
3. fallback o retry esplicito

## Casi che il sito può presentare

Elenco minimo da considerare:

- login IAM corretto
- login IAM con pagina ancora in navigazione
- informativa privacy da confermare
- sessione già attiva su altra postazione
- utente bloccato / `error_locked.jsp`
- menu servizi disponibile ma sottomenu assente
- menu disponibile ma elemento non cliccabile
- form visura disponibile
- CAPTCHA OCR
- CAPTCHA manuale
- download PDF

## Prossimi step consigliati

### Priorità alta

1. Verificare se 5 secondi di attesa post `CloseSessionsSis` sono sufficienti.
2. Se non bastano, aumentare l'attesa o introdurre polling sul ritorno a una pagina SISTER non bloccata.
3. Capire se dopo `CloseSessionsSis` esiste un endpoint o una pagina intermedia di conferma da attendere prima del nuovo login.
4. Valutare aumento attesa post-close o nuova sessione browser completamente pulita prima del retry.

### Priorità media

1. Evitare trace HTML nei millisecondi in cui la pagina sta navigando per ridurre rumore nei log.
2. Tradurre in italiano eventuali residui messaggi inglesi ancora visibili in DB/UI.

### Priorità bassa

1. Estrarre il tracing browser in una utility comune.
2. Introdurre livelli di debug configurabili via env.
3. Separare artifact di `trace`, `error`, `captcha`, `session-recovery`.

## Ipotesi operative per il caso sessione bloccata

Ipotesi più probabili:

- il portale rilascia la sessione con ritardo
- `CloseSessionsSis` chiude la sessione, ma la federazione IAM mantiene uno stato ancora sporco per alcuni secondi
- il nuovo login troppo ravvicinato rientra nello stato di lock

Strategie possibili se il problema persiste:

- attesa più lunga dopo `CloseSessionsSis` (es. 10-15 secondi)
- logout IAM esplicito dopo `CloseSessionsSis`
- nuova sessione browser pulita dopo il recovery
- rilevazione pagina di successo della chiusura sessione prima di ritentare

## Convenzioni per debug futuro

Quando si apre un nuovo caso SISTER:

1. annotare timestamp del run
2. salvare batch id e request id
3. indicare URL finale osservato
4. allegare screenshot/HTML rilevanti
5. classificare il caso in uno dei gruppi sopra
6. aggiornare questo documento

## Ultimo punto fermo accertato

Alla data di questo documento:

- la privacy notice è stata identificata e gestita
- il link `Chiudi` per sessione attiva è stato identificato e gestito
- resta da validare se il recovery automatico con attesa post-chiusura sia sufficiente a sbloccare il run successivo
