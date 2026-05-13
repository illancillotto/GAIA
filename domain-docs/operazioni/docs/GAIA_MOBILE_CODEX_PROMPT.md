# Prompt Codex — Nuovo progetto GAIA Mobile

Usa questo prompt nel nuovo repository `gaia-mobile`.

---

## Contesto

Stai sviluppando `gaia-mobile`, prodotto satellite del gestionale GAIA.

GAIA e un gestionale interno LAN. Il modulo Operazioni gestisce mezzi, attivita operatori, segnalazioni, pratiche, allegati e GPS.

Obiettivo di `gaia-mobile`: fornire una PWA mobile cloud per operatori sul campo senza esporre GAIA su internet.

Architettura obbligatoria:

```text
Operatore mobile
  -> PWA cloud
  -> Gateway API cloud
  -> Sync queue cloud
  <- Connector locale outbound-only
  -> GAIA LAN
```

GAIA resta sistema master.
Il cloud conserva solo dati operativi minimi e temporanei.
Il connector non deve aprire porte in ingresso.

---

## Documenti da seguire

Nel repo devono esistere e guidare l'implementazione:

- `docs/GAIA_MOBILE_PRD.md`
- `docs/GAIA_MOBILE_ARCHITECTURE.md`
- `docs/GAIA_MOBILE_EXECUTION_PLAN.md`
- `docs/GAIA_MOBILE_SYNC_PROTOCOL.md`

Se mancano, crearli partendo dai contenuti forniti.

---

## Repository target

Struttura richiesta:

```text
gaia-mobile/
  apps/
    mobile-web/
    gateway-api/
    connector/
  packages/
    shared/
  docs/
  README.md
  .env.example
```

---

## Stack consigliato

Preferenza: TypeScript end-to-end.

- Package manager: `pnpm` o `npm` workspace.
- `apps/mobile-web`: React + PWA mobile-first.
- `apps/gateway-api`: API HTTP con validazione payload, DB PostgreSQL.
- `apps/connector`: worker Node.js outbound-only.
- `packages/shared`: tipi, enum, DTO, validazioni.

Se scegli uno stack diverso, motivalo e mantieni invariati i contratti.

---

## Requisiti fondamentali

1. GAIA non deve essere esposto su internet.
2. Il connector comunica solo in uscita verso il gateway cloud.
3. Ogni evento mobile deve avere `client_event_id` UUID.
4. Il sync deve essere idempotente.
5. Retry e riavvio connector non devono creare duplicati.
6. La PWA deve salvare bozze offline in IndexedDB.
7. Gli allegati devono avere checksum, mime type e size.
8. Gli errori GAIA devono tornare visibili all'operatore.
9. Le liste personali della PWA arrivano da cache cloud aggiornata dal connector.
10. Il cloud non e fonte master dei dati operativi finali.

---

## MVP da implementare

### Mobile PWA

- Login operatore.
- Home con stato rete/sync.
- Nuova attivita.
- Chiusura attivita.
- Nuova segnalazione.
- Foto allegati.
- GPS.
- Liste personali.
- Bozze offline e retry.

### Gateway API

- Auth operatori.
- Auth connector.
- Ricezione eventi.
- Stato eventi.
- Upload allegati.
- Poll/claim/ack/fail connector.
- Cataloghi e workset cache.
- Heartbeat connector.

### Connector

- Poll outbound-only.
- Claim evento.
- Applicazione evento a GAIA LAN via REST.
- Ack/fail verso gateway.
- Sync cataloghi da GAIA a cloud.
- Sync workset operatore da GAIA a cloud.
- Backoff e logging.

### Shared

- Enum eventi.
- Enum stati sync.
- DTO payload.
- Validazioni.
- Error model.

---

## Eventi MVP

Implementare almeno:

- `ACTIVITY_START_REQUESTED`
- `ACTIVITY_STOP_REQUESTED`
- `FIELD_REPORT_CREATED`

Ogni evento deve supportare:
- `client_event_id`;
- `operator_id`;
- `device_id`;
- `created_at_device`;
- `payload_version`;
- `payload_hash`;
- stato sync;
- mapping finale `gaia_entity_id`.

---

## Qualita attesa

- Codice tipizzato.
- Test unitari su validazioni.
- Test integrazione poll/claim/ack.
- Test idempotenza duplicati.
- Test connector con GAIA mock.
- README con comandi locali.
- `.env.example` completo.
- Nessun secret committato.

---

## Prima milestone richiesta

Implementa Milestone 0 e Milestone 1:

- scaffolding monorepo;
- docs iniziali;
- package shared con enum e DTO;
- gateway DB model/migration per `sync_event`, `sync_attachment`, `mobile_operator`, `mobile_device`;
- endpoint base `POST /api/mobile/events` con idempotenza;
- test idempotenza evento.

Non implementare ancora UI avanzata prima di avere contratti e idempotenza solidi.

---

## Nota su codice GAIA esistente

Nel repo GAIA esiste gia una mini-app Operazioni interna.
Non copiarla ciecamente.

Riusa solo concetti e logica:
- flussi avvio/chiusura attivita;
- nuova segnalazione;
- bozze IndexedDB;
- liste personali;
- stati sync.

Adatta tutto all'architettura cloud + connector.
La PWA `gaia-mobile` non deve chiamare direttamente GAIA.
