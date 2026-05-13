# GAIA Mobile — Architettura

## 1. Principio guida

GAIA Mobile deve separare nettamente:
- GAIA LAN: sistema master, dati completi, workflow amministrativi.
- Cloud mobile: canale operativo, code, stato sync e storage temporaneo.
- Connector locale: ponte sicuro outbound-only tra cloud e GAIA.

Nessun componente cloud deve accedere direttamente al database GAIA.
Nessuna porta di GAIA deve essere pubblicata su internet.

---

## 2. Componenti

```text
gaia-mobile/
  apps/mobile-web/
  apps/gateway-api/
  apps/connector/
  packages/shared/
  docs/
```

### `apps/mobile-web`

PWA mobile-first per operatori.

Responsabilita:
- UI operativa;
- IndexedDB per bozze offline;
- acquisizione GPS;
- acquisizione foto;
- invio eventi al gateway;
- visualizzazione stato sync.

### `apps/gateway-api`

API cloud pubblica.

Responsabilita:
- auth operatori;
- ricezione eventi mobile;
- validazione base payload;
- gestione code sync;
- upload allegati;
- endpoint polling connector;
- stato eventi e liste personali cache.

### `apps/connector`

Servizio installato nella LAN del Consorzio.

Responsabilita:
- autenticarsi verso gateway;
- fare polling degli eventi pendenti;
- applicare eventi a GAIA tramite API interne LAN;
- sincronizzare cataloghi e workset da GAIA verso cloud;
- inviare ack, mapping ID ed errori.

### `packages/shared`

Contratti comuni.

Responsabilita:
- DTO eventi;
- enum stati;
- schema validazione;
- tipi TypeScript condivisi;
- eventuale OpenAPI generata.

---

## 3. Flusso eventi mobile -> GAIA

```text
1. PWA crea evento locale con client_event_id.
2. Se offline, salva evento su IndexedDB.
3. Se online, invia evento a gateway.
4. Gateway valida, persiste e mette in stato RECEIVED.
5. Connector fa polling e claim evento.
6. Connector traduce payload verso API GAIA LAN.
7. GAIA crea/aggiorna record interni.
8. Connector invia ack con gaia_entity_id.
9. Gateway aggiorna stato APPLIED.
10. PWA riceve stato aggiornato.
```

---

## 4. Stati evento

```text
LOCAL_DRAFT
LOCAL_PENDING
CLOUD_RECEIVED
CLOUD_CLAIMED
APPLYING_TO_GAIA
APPLIED_TO_GAIA
FAILED_VALIDATION
FAILED_RETRYABLE
FAILED_FATAL
CANCELLED
```

Regole:
- `client_event_id` e unico per device.
- Gateway deve rifiutare duplicati incoerenti.
- Connector deve poter riapplicare un evento senza creare duplicati.
- Eventi `FAILED_RETRYABLE` restano in coda.
- Eventi `FAILED_VALIDATION` richiedono correzione utente o admin.

---

## 5. Modello dati cloud minimo

### `mobile_operator`

- `id`
- `gaia_user_id`
- `gaia_operator_profile_id`
- `display_name`
- `email`
- `phone`
- `status`
- `last_login_at`

### `mobile_device`

- `id`
- `operator_id`
- `device_label`
- `platform`
- `last_seen_at`
- `revoked_at`

### `sync_event`

- `id`
- `client_event_id`
- `device_id`
- `operator_id`
- `event_type`
- `payload_version`
- `payload_json`
- `payload_hash`
- `status`
- `retry_count`
- `last_error_code`
- `last_error_message`
- `gaia_entity_type`
- `gaia_entity_id`
- `created_at_device`
- `received_at_cloud`
- `claimed_at`
- `applied_at`

### `sync_attachment`

- `id`
- `event_id`
- `storage_key`
- `filename`
- `mime_type`
- `size_bytes`
- `sha256`
- `status`
- `gaia_attachment_id`

### `sync_catalog_snapshot`

- `id`
- `catalog_type`
- `version`
- `payload_json`
- `synced_from_gaia_at`

### `operator_workset_cache`

- `id`
- `operator_id`
- `workset_type`
- `gaia_entity_id`
- `payload_json`
- `synced_from_gaia_at`

---

## 6. API principali gateway

Base path suggerito:

```text
/api/mobile
```

### Mobile PWA

- `POST /auth/login`
- `POST /auth/refresh`
- `GET /me`
- `GET /catalogs`
- `GET /workset`
- `POST /events`
- `GET /events/{client_event_id}`
- `POST /attachments/presign`
- `POST /attachments/complete`

### Connector

- `POST /connector/auth`
- `GET /connector/events/poll`
- `POST /connector/events/{event_id}/claim`
- `POST /connector/events/{event_id}/ack`
- `POST /connector/events/{event_id}/fail`
- `POST /connector/catalogs/push`
- `POST /connector/worksets/push`
- `POST /connector/heartbeat`

---

## 7. Contratti evento MVP

### `ACTIVITY_START_REQUESTED`

Payload:
- `activity_catalog_id`
- `vehicle_id`
- `team_id`
- `notes`
- `gps_start`
- `started_at_device`

Output connector:
- `gaia_entity_type = operator_activity`
- `gaia_entity_id`

### `ACTIVITY_STOP_REQUESTED`

Payload:
- `gaia_activity_id` oppure `client_started_event_id`
- `notes`
- `odometer_km`
- `gps_end`
- `stopped_at_device`

### `FIELD_REPORT_CREATED`

Payload:
- `category_id`
- `severity_id`
- `title`
- `description`
- `gps_point`
- `linked_activity_id`
- `attachments`

Output connector:
- `gaia_entity_type = field_report`
- `gaia_entity_id`
- `gaia_case_id`

---

## 8. Sicurezza connector

Il connector deve:
- usare credenziali dedicate non riutilizzabili dagli operatori;
- supportare rotazione secret;
- identificare `tenant_id` o installazione;
- inviare heartbeat;
- non accettare connessioni inbound dal cloud;
- mantenere log locali senza dati sensibili completi.

---

## 9. Integrazione con GAIA

Nel repo GAIA servira esporre o stabilizzare endpoint interni per:
- creazione attivita da evento mobile;
- stop attivita da evento mobile;
- creazione segnalazione da evento mobile;
- upload allegati da connector;
- lettura cataloghi;
- lettura workset operatore;
- idempotency lookup per `client_event_id`.

Se endpoint esistenti sono gia sufficienti, il connector li usa direttamente.
Se mancano garanzie di idempotenza o payload mobile, creare endpoint interni dedicati sotto `/api/operazioni/mobile-sync/*`.

---

## 10. Osservabilita

Metriche minime:
- eventi ricevuti;
- eventi applicati;
- eventi falliti;
- backlog per installazione;
- eta evento piu vecchio in coda;
- heartbeat connector;
- latenza cloud -> GAIA;
- errori allegati;
- storage usato.

Log minimi:
- `client_event_id`;
- `event_id`;
- `operator_id`;
- `connector_id`;
- `status_before/status_after`;
- `error_code`;
- `gaia_entity_id`.
