# SISTER Debug Runbook

> Nota infrastrutturale
> Il worker Catasto e un servizio tecnico separato, ma il dominio applicativo Catasto resta parte del backend monolite condiviso.

## Scopo

Questo documento raccoglie il comportamento reale osservato del portale SISTER durante l'automazione Catasto, le contromisure implementate nel worker e i prossimi punti da verificare.

Va trattato come riferimento operativo permanente per:

- debug del worker `catasto-worker`
- aggiornamento dei selettori o del flusso browser
- gestione nuovi casi del sito SISTER
- futura automazione di altri servizi sullo stesso portale

## Contesto tecnico

Componenti coinvolti:

- backend API: `backend`
- worker browser: `modules/catasto/worker`
- frontend Catasto: `frontend/src/app/catasto`

File principali del flusso:

- `modules/catasto/worker/worker.py`
- `modules/catasto/worker/browser_session.py`
- `modules/catasto/worker/visura_flow.py`
- `modules/catasto/worker/sister_selectors.json`

Comando utile per rebuild worker:

```bash
docker compose up -d --build --force-recreate catasto-worker
```

Comando utile per i log:

```bash
docker compose logs -f catasto-worker
```

## Stato attuale del debug

Il worker oggi:

- logga in italiano i passaggi principali
- salva screenshot e HTML nei passaggi critici
- aggiorna `current_operation` con fasi più parlanti
- gestisce l'informativa privacy
- prova a chiudere una sessione SISTER già attiva
- aspetta alcuni secondi dopo `CloseSessionsSis` prima di ritentare il login
- usa OCR locale Tesseract per i CAPTCHA testuali
- può fare fallback su Anti-Captcha se configurato in `.env`

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
- click automatico su `Chiudi` oppure `goto` diretto a `CloseSessionsSis`
- attesa post chiusura sessione
- nuovo tentativo di login una sola volta
- stop immediato del flusso menu se il post-login e' gia' classificato come sessione bloccata

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

- il fallback esterno è inserito in `modules/catasto/worker/visura_flow.py`
- il client API è in `modules/catasto/worker/anti_captcha_client.py`
- i log CAPTCHA distinguono `ocr`, `external`, `manual`
- se Anti-Captcha fallisce o restituisce un testo non accettato da SISTER, il flusso continua comunque verso il CAPTCHA manuale

Riferimenti ufficiali usati per l'integrazione:

- `createTask`: `https://anti-captcha.com/it/apidoc/methods/createTask`
- `getTaskResult`: `https://anti-captcha.com/it/apidoc/methods/getTaskResult`
- `ImageToTextTask`: `https://anti-captcha.com/it/apidoc/task-types/ImageToTextTask`
- errori API: `https://anti-captcha.com/it/apidoc/errors`

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
2. Salvare anche un file strutturato di timeline per batch/request.
3. Tradurre in italiano eventuali residui messaggi inglesi ancora visibili in DB/UI.

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
