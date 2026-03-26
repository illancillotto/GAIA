# Prompt Codex — GAIA Catasto

> Regola strutturale vincolante
> GAIA usa un backend monolitico modulare. Il codice backend del dominio Catasto va creato in `backend/app/modules/catasto/`. Il frontend del modulo vive in `frontend/src/app/catasto/`. Il worker browser-based e un servizio tecnico separato, ma non un backend applicativo autonomo.

> Da usare come system prompt o primo messaggio in una sessione di sviluppo dedicata al modulo Catasto.

---

## Contesto del progetto

Stai sviluppando **GAIA Catasto**, il modulo di integrazione con i servizi dell'Agenzia delle Entrate della piattaforma **GAIA**.

GAIA e una piattaforma multi-modulo con backend e frontend condivisi. I moduli applicativi convivono nello stesso monolite:

- **Accessi**
- **Network**
- **Inventory**
- **Catasto**

Il repository adotta una struttura canonica in cui il backend applicativo vive sotto `backend/` e i moduli di dominio sotto `backend/app/modules/`.

---

## Stack obbligatorio

**Backend**
- FastAPI
- SQLAlchemy
- Alembic
- PostgreSQL
- Pydantic
- cryptography per credential vault
- pandas per validazione import CSV

**Worker**
- Playwright async + Chromium
- Pillow + pytesseract per OCR CAPTCHA
- asyncio + polling loop su PostgreSQL o coda equivalente basata sull'infrastruttura GAIA

**Frontend**
- Next.js
- React
- TypeScript
- TailwindCSS
- TanStack Table
- react-hook-form
- WebSocket o stream realtime coerente con lo stack gia adottato dal progetto

**Infrastructure**
- Docker Compose esistente
- backend e database condivisi con gli altri moduli
- servizio tecnico `catasto-worker` separato per automazione browser
- volume dati dedicato per PDF e asset transitori del worker

---

## Principi architetturali

- Il backend resta un **monolite modulare**: nuove feature del dominio Catasto vanno sviluppate nel modulo canonico `backend/app/modules/catasto/`
- Il punto di integrazione backend e il router di modulo `backend/app/modules/catasto/router.py`, incluso in `backend/app/api/router.py`
- Il modulo puo usare un file `routes.py` o una struttura a package di route, ma `router.py` resta l'entrypoint del modulo
- I path legacy fuori da `backend/app/modules/` vanno trattati come area di compatibilita, non come destinazione primaria per nuove feature
- Il frontend del modulo vive in `frontend/src/app/catasto/` nel frontend condiviso
- Non creare un frontend separato o un backend applicativo separato per Catasto
- Il browser worker gira come container/processo tecnico separato e comunica con il backend tramite database condiviso, coda applicativa e canali realtime gia previsti
- Auth, sessione DB, logging, config e dipendenze FastAPI vanno riutilizzati dall'app esistente
- Alembic resta unico: nuove migration in `backend/alembic/versions/`
- Le credenziali SISTER vanno cifrate; la master key deve vivere solo in configurazione sicura, non nel codice
- Le credenziali decriptate devono restare in memoria solo per il tempo strettamente necessario e non devono finire in log, response o persistenza non cifrata

---

## Modello dati da implementare

Entita principali del modulo:

```text
catasto_credentials
catasto_batches
catasto_visure_requests
catasto_documents
catasto_captcha_log
catasto_comuni
```

Riferimento funzionale e campi iniziali: `modules/catasto/docs/PRD_catasto.md`, sezione modello dati.

Linee guida:

- una credenziale SISTER per utente applicativo, cifrata a riposo
- batch e richieste separate per tracciare avanzamento, errori e retry
- documenti persistiti con metadata chiari e path relativi
- log CAPTCHA ammesso solo se giustificato e compatibile con i vincoli di sicurezza e privacy del progetto

---

## API da implementare

Tutti gli endpoint del modulo devono essere esposti dal backend condiviso sotto prefisso `/catasto`.

Pattern architetturale:

- route del modulo nel package `backend/app/modules/catasto/`
- business logic in `services.py`
- schemi request/response in `schemas.py`
- modelli SQLAlchemy in `models.py`
- eventuale realtime tramite WebSocket o meccanismo equivalente integrato nel backend condiviso

Riferimento endpoint: `modules/catasto/docs/PRD_catasto.md`, sezione API.

Se previsti canali realtime, devono essere pubblicati dal backend condiviso e non da un servizio applicativo parallelo.

---

## Pagine frontend da implementare

```text
/catasto
/catasto/new-batch
/catasto/new-single
/catasto/batches
/catasto/batches/[id]
/catasto/documents
/catasto/documents/[id]
/catasto/settings
```

Linee guida frontend:

- usare App Router nella struttura esistente di `frontend/src/app/`
- mantenere coerenza con auth flow, layout e componenti condivisi del progetto
- trattare avanzamento batch, errori e richiesta CAPTCHA come flussi operativi, non come demo tecniche
- tabelle con sorting, filtri e paginazione lato server quando il dataset lo richiede

---

## Requisiti UI/UX

- UI amministrativa sobria, leggibile, coerente con gli altri moduli GAIA
- stati richiesta ben distinguibili e stabili
- dialog CAPTCHA chiaro, rapido e focalizzato sul completamento del task
- progress batch immediatamente leggibile
- archivio documenti orientato a ricerca e download
- responsive desktop-first; mobile secondario

---

## Priorita di sviluppo

1. Modello dati, migration Alembic e seed dei comuni
2. Credential vault cifrato
3. Batch service con upload CSV e validazione
4. Router di modulo `backend/app/modules/catasto/router.py`
5. API `/catasto`
6. Worker base con login e navigazione
7. Worker visura e download PDF
8. Gestione CAPTCHA e realtime
9. Frontend settings, new-batch e batch detail
10. Archivio documenti e dashboard

---

## Vincoli tecnici

- non creare un backend separato per Catasto
- non introdurre nuovi path primari fuori da `backend/app/modules/catasto/` per il codice backend di dominio
- il worker deve usare configurazione condivisa e persistenza coordinata con il backend monolitico
- la master key per cifratura credenziali deve arrivare da environment/config sicura
- i path dei documenti devono essere relativi e compatibili con i volumi Docker del progetto
- il worker deve gestire retry, resume e shutdown in modo robusto
- i selettori e il DOM di SISTER possono cambiare: i dettagli operativi del portale vanno verificati in fase di sviluppo

---

## Flusso operativo SISTER

Usa `modules/catasto/docs/PRD_catasto.md` come riferimento funzionale per:

- formato CSV atteso
- stati batch e richieste
- selettori del portale
- gestione CAPTCHA
- download documenti

I dettagli del DOM di SISTER sono intrinsecamente instabili: trattali come riferimento operativo da verificare, non come verita permanente.

---

## Istruzioni operative per Codex

Quando implementi o modifichi il modulo Catasto:

- verifica prima la struttura reale del repository e segui i pattern gia presenti in `backend/app/modules/catasto/`
- usa `backend/app/modules/catasto/` come superficie primaria del backend
- aggiungi o modifica integrazioni backend passando sempre da `backend/app/api/router.py` e dal router di modulo
- mantieni separati router HTTP, modelli, schemi, servizi e logica del worker
- non spostare la logica di automazione browser nel backend HTTP se puo restare nel worker tecnico
- preserva compatibilita con il monolite condiviso, con Alembic unico e con il database unico
- usa `modules/catasto/docs/PRD_catasto.md` come riferimento funzionale, ma fai prevalere l'architettura canonica del repository quando trovi indicazioni obsolete nei documenti piu vecchi
