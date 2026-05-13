# GAIA Mobile — Execution Plan

## 1. Strategia

Implementare GAIA Mobile come nuovo repo `gaia-mobile`, separato da GAIA.

Il primo obiettivo non e costruire una copia completa del modulo Operazioni, ma un canale operativo mobile sicuro e sincronizzato.

---

## 2. Milestone

## Milestone 0 — Scaffolding repo

### Obiettivi

- Creare monorepo `gaia-mobile`.
- Definire stack tecnico.
- Preparare ambienti locali per PWA, gateway e connector.

### Attivita

- Creare workspace:
  - `apps/mobile-web`
  - `apps/gateway-api`
  - `apps/connector`
  - `packages/shared`
  - `docs`
- Aggiungere lint, test, typecheck.
- Aggiungere README e `.env.example`.
- Definire convenzioni commit e struttura config.

### Deliverable

- Repo avviabile localmente.
- Comandi `dev`, `test`, `typecheck`, `lint`.
- Docker compose locale per gateway DB.

---

## Milestone 1 — Contratti sync e data model

### Obiettivi

- Definire tipi e schema eventi.
- Implementare persistenza cloud minima.

### Attivita

- Creare enum stati evento.
- Creare DTO evento e allegato.
- Creare migration DB gateway.
- Implementare `sync_event`, `sync_attachment`, `mobile_operator`, `mobile_device`.
- Implementare idempotenza su `client_event_id`.

### Deliverable

- Package shared con tipi e validazioni.
- DB gateway migrato.
- Test su idempotenza eventi.

---

## Milestone 2 — Gateway API cloud MVP

### Obiettivi

- Ricevere eventi mobile.
- Esporre polling connector.

### Attivita

- Auth operatori base.
- Auth connector.
- `POST /api/mobile/events`.
- `GET /api/mobile/events/{client_event_id}`.
- `GET /api/mobile/catalogs`.
- `GET /api/mobile/workset`.
- `GET /api/mobile/connector/events/poll`.
- `POST /api/mobile/connector/events/{id}/claim`.
- `POST /api/mobile/connector/events/{id}/ack`.
- `POST /api/mobile/connector/events/{id}/fail`.
- Heartbeat connector.

### Deliverable

- Gateway testato con eventi fittizi.
- Poll/claim/ack robusti.
- Errori strutturati.

---

## Milestone 3 — Connector locale MVP

### Obiettivi

- Collegare outbound-only gateway cloud e GAIA LAN.

### Attivita

- Configurare endpoint GAIA LAN.
- Implementare polling con backoff.
- Tradurre `ACTIVITY_START_REQUESTED`.
- Tradurre `ACTIVITY_STOP_REQUESTED`.
- Tradurre `FIELD_REPORT_CREATED`.
- Gestire errori retryable vs validation.
- Implementare push cataloghi da GAIA verso cloud.
- Implementare push workset operatore da GAIA verso cloud.

### Deliverable

- Connector avviabile come processo.
- Nessuna porta inbound richiesta.
- Eventi applicati a GAIA in ambiente dev.

---

## Milestone 4 — PWA mobile MVP

### Obiettivi

- Dare agli operatori una UI mobile usabile.

### Attivita

- Layout mobile-first.
- Login.
- Home operativa.
- Stato rete e stato sync.
- Avvio attivita.
- Chiusura attivita.
- Nuova segnalazione.
- Upload foto.
- GPS.
- Liste personali.
- Bozze IndexedDB.
- Retry automatico e manuale.

### Deliverable

- PWA installabile.
- Flussi core completabili da smartphone.
- Offline minimo funzionante.

---

## Milestone 5 — Allegati e hardening sync

### Obiettivi

- Rendere affidabili foto e media.

### Attivita

- Upload multipart o presigned.
- Validazione mime/size.
- Checksum SHA256.
- Compressione immagine lato client opzionale.
- Download allegati da connector.
- Ack allegati verso gateway.
- Retention cloud configurabile.

### Deliverable

- Foto segnalazione arrivano su GAIA.
- Errori allegati visibili e recuperabili.

---

## Milestone 6 — Sicurezza e osservabilita

### Obiettivi

- Preparare pilot reale.

### Attivita

- Rotazione secret connector.
- Rate limit API pubbliche.
- Audit log.
- Dashboard tecnica backlog/errori.
- Alert connector offline.
- Test rete instabile.
- Test doppio invio.
- Test spegnimento connector durante sync.

### Deliverable

- Pilot controllato con operatori selezionati.
- Runbook operativo.

---

## 3. Stack suggerito

Scelta consigliata:

- Monorepo: pnpm workspace o npm workspace.
- Mobile web: Next.js o Vite React PWA.
- Gateway API: Fastify/NestJS oppure FastAPI se si vuole allineare a GAIA.
- DB cloud: PostgreSQL.
- ORM: Prisma se stack TS full, SQLAlchemy se FastAPI.
- Shared validation: Zod se stack TS, Pydantic + OpenAPI se FastAPI.
- Connector: Node.js worker oppure Python service.

Preferenza pragmatica:
- TypeScript end-to-end per `mobile-web`, `gateway-api`, `connector`, `shared`.
- Connector chiama GAIA REST, senza importare codice Python di GAIA.

---

## 4. Test minimi

- Unit test validazione payload.
- Unit test idempotenza `client_event_id`.
- Integration test poll/claim/ack.
- Integration test retry connector.
- E2E PWA: offline -> bozza -> online -> evento cloud.
- E2E connector: evento cloud -> GAIA mock -> ack.
- Test upload allegato con checksum.

---

## 5. Dipendenze da GAIA

Prima del pilot verificare in GAIA:
- endpoint start activity idempotente;
- endpoint stop activity idempotente;
- endpoint create report idempotente;
- upload allegati da connector;
- endpoint cataloghi;
- endpoint workset operatore;
- mapping utente mobile -> utente/operatore GAIA.

Se mancano, aprire task nel repo GAIA sotto modulo Operazioni.
