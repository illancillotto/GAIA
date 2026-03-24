# Prompt Codex — GAIA Catasto (Servizi Agenzia delle Entrate)

> Da usare come system prompt o primo messaggio in una sessione di sviluppo dedicata.

---

## Contesto del progetto

Stai sviluppando **GAIA Catasto**, il modulo di integrazione con i servizi dell'Agenzia delle Entrate della piattaforma **GAIA** per il Consorzio di Bonifica dell'Oristanese.

GAIA è una piattaforma IT governance con quattro moduli:
- **GAIA Accessi** — NAS Audit (completato)
- **GAIA Rete** — Network Monitor (in sviluppo)
- **GAIA Inventario** — IT Inventory (in sviluppo)
- **GAIA Catasto** — Servizi AdE (questo modulo)

Il repository si trova su `github.com/illancillotto/GAIA`.

---

## Stack obbligatorio

**Backend**
- FastAPI, SQLAlchemy, Alembic, PostgreSQL
- cryptography (Fernet per credential vault)
- pandas (validazione CSV import)

**Worker (container separato)**
- Playwright (async) + Chromium
- Pillow + pytesseract (OCR CAPTCHA)
- asyncio + polling loop su PostgreSQL

**Frontend**
- Next.js, React, TypeScript, TailwindCSS
- TanStack Table
- react-hook-form (form visura singola)
- WebSocket nativo per aggiornamenti real-time

**Infrastructure**
- Docker Compose — aggiunta servizio `catasto-worker` con Playwright preinstallato
- Volume Docker `catasto-data` per PDF e immagini CAPTCHA

---

## Principi architetturali

- Il modulo si aggiunge al backend e frontend **esistenti** come router/sezione aggiuntiva
- **NON** creare un backend separato: aggiungere `app/routers/catasto.py` al FastAPI esistente
- **NON** creare un frontend separato: aggiungere `frontend/src/app/catasto/` al Next.js esistente
- Il browser worker gira come **container Docker separato** con Chromium
- Auth JWT condivisa: riutilizzare il middleware esistente senza modifiche
- Alembic: creare nuove migration in `alembic/versions/` senza toccare quelle esistenti
- Le credenziali SISTER sono crittografate con Fernet; la master key è SOLO in env var
- La password decriptata vive SOLO in memoria nel worker, mai in log/response/DB
- Job queue basata su PostgreSQL (polling sulla tabella `catasto_visure_requests`)
- Comunicazione worker → frontend via WebSocket per progress e CAPTCHA

---

## Modello dati da implementare

```
catasto_credentials       — credenziali SISTER crittografate (1 per utente)
catasto_batches           — batch di richieste visure
catasto_visure_requests   — singole richieste (righe del CSV)
catasto_documents         — PDF scaricati con metadati
catasto_captcha_log       — log immagini CAPTCHA per training futuro
catasto_comuni            — dizionario comuni con codici SISTER
```

Schema completo in `modules/catasto/docs/PRD_catasto.md` sezione 3.

---

## API da implementare

Tutti gli endpoint sotto il prefisso `/catasto`.  
Lista completa in `modules/catasto/docs/PRD_catasto.md` sezione 4.

Endpoint WebSocket: `ws://.../catasto/ws/{batch_id}` per aggiornamenti real-time.

---

## Pagine frontend da implementare

```
/catasto                    — dashboard
/catasto/new-batch          — upload CSV + preview + avvia
/catasto/new-single         — form visura singola
/catasto/batches            — storico batch
/catasto/batches/[id]       — dettaglio batch con progress + CAPTCHA dialog
/catasto/documents          — archivio documenti con ricerca
/catasto/documents/[id]     — dettaglio documento + PDF viewer
/catasto/settings           — gestione credenziali SISTER
```

---

## Requisiti UI/UX

- Stile coerente con GAIA Accessi: professionale, orientato alla lettura amministrativa, no effetti decorativi
- Badge stato richiesta: verde (completed), arancione (awaiting_captcha), blu (processing), grigio (pending), rosso (failed)
- CAPTCHA dialog: modal con immagine grande, campo di testo, pulsanti "Invia" e "Salta"
- Progress bar batch: barra con percentuale + contatore "15/50" + label operazione corrente
- Upload CSV: wizard a step con preview mapping colonne e validazione prima dell'avvio
- Archivio documenti: TanStack Table con filtri comuni, foglio, particella, data, download inline
- PDF viewer: embed nel dettaglio documento, con pulsante download
- Settings credenziali: form con username/password + pulsante "Testa connessione" con feedback live
- Responsive desktop-first; mobile non prioritario

---

## Priorità di sviluppo

1. **Modello dati** + migration Alembic + seed comuni
2. **Credential vault** — API CRUD + encrypt/decrypt con Fernet
3. **Batch service** — upload CSV, validazione, creazione batch/requests
4. **Worker base** — container Docker, login SISTER, navigazione fino al form
5. **Worker visura** — compilazione form, gestione tipo visura, download PDF
6. **CAPTCHA solver** — OCR con preprocessing Pillow + pytesseract
7. **WebSocket** — progress batch + notifica CAPTCHA
8. **Frontend: settings** — form credenziali SISTER
9. **Frontend: new-batch** — upload + preview + avvio
10. **Frontend: batch detail** — progress + CAPTCHA dialog
11. **Frontend: archivio** — lista documenti + ricerca + download
12. **Frontend: dashboard** — overview con quick actions
13. **Retry logic** — retry automatico errori transitori
14. **Frontend: visura singola** — form con dropdown comuni

---

## Vincoli e note tecniche

### Worker
- Il worker polling deve avere un intervallo di 2-3 secondi (non sovraccaricare il DB)
- Un solo batch alla volta per utente (vincolo applicativo, non DB)
- Delay minimo 5 secondi tra una visura e l'altra
- Re-login proattivo ogni 28 minuti (timeout sessione SISTER)
- Il worker deve fare graceful shutdown (completare la visura corrente, poi fermarsi)
- Se Chromium crasha, il worker deve riavviarsi e riprendere dal punto in cui era

### SISTER
- Il portale è HTML classico, pochi AJAX, DOM potenzialmente instabile tra aggiornamenti
- I selettori CSS/XPath vanno verificati a runtime — usare `page.pause()` in debug
- I dropdown sono `<select>` nativi → usare `page.select_option()`
- Il CAPTCHA è un'immagine con testo distorto su sfondo rumoroso
- Dopo click "Salva", il PDF viene scaricato direttamente — intercettare con Playwright download event

### Crittografia
- Master key: generare con `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` e salvare in `.env`
- La key deve essere uguale tra backend (per encrypt) e worker (per decrypt)
- Se la key viene persa, tutte le credenziali salvate diventano irrecuperabili → backup della key

### CSV format atteso

```csv
citta,catasto,sezione,foglio,particella,subalterno,tipo_visura
MARRUBIU,Terreni,,12,603,,Sintetica
ORISTANO,Terreni e Fabbricati,,5,120,3,Completa
```

Validazione: citta obbligatoria e deve esistere in `catasto_comuni`, foglio e particella obbligatori e numerici, catasto deve essere "Terreni" o "Terreni e Fabbricati", tipo_visura deve essere "Sintetica" o "Completa".

### Docker

```yaml
# da aggiungere a docker-compose.yml
catasto-worker:
  build: ./modules/catasto/worker
  depends_on:
    - postgres
  environment:
    - DATABASE_URL=${DATABASE_URL}
    - CREDENTIAL_MASTER_KEY=${CREDENTIAL_MASTER_KEY}
  volumes:
    - catasto-data:/data/catasto
  restart: unless-stopped

volumes:
  catasto-data:
```

Dockerfile del worker basato su `mcr.microsoft.com/playwright/python:v1.40.0-jammy` che include Chromium.

---

## Flusso SISTER — Riferimento selettori

Riferimento completo dei selettori in `modules/catasto/docs/PRD_catasto.md` sezione 9.

Selettori chiave:
- Tab Sister login: `a.nav-link[href="#tab-5"]`
- Username: `#username-sister`  
- Password: `#password-sister`
- Conferma informativa: `//input[@value='Conferma']`
- Territorio dropdown: `select[name='listacom']` → value: `ORISTANO Territorio-OR`
- Catasto: `select[name='tipoCatasto']`
- Comune: `select[name='denomComune']`
- Foglio: `input[name='foglio']`
- Particella: `input[name='particella1']`
- Subalterno: `input[name='subalterno1']`
- Motivo: `select[name='motivoLista']` → value: `"Altri fini istituzionali "`
- Visura: `input[name='scelta'][value='Visura']`
- Tipo visura: `input[name='tipoVisura']` → value: `3` (Sintetica) o `2` (Completa)
- CAPTCHA field: `input[name='codSicurezza']`
- Inoltra: `input[name='inoltra'][value='Inoltra']`
- Salva PDF: `input[name='metodo'][value='Salva']`

**NOTA**: Questi selettori sono stati rilevati a marzo 2026. Il DOM di SISTER può cambiare. Verificare sempre con `page.pause()` in fase di sviluppo.
