# GAIA Mobile — Sync Protocol

## 1. Obiettivo

Definire il protocollo di sincronizzazione tra:
- PWA mobile;
- Gateway cloud;
- Connector locale;
- GAIA LAN.

Il protocollo deve garantire che eventi duplicati, retry, perdita rete o riavvio connector non producano dati doppi o incoerenti in GAIA.

---

## 2. Identificativi

### `client_event_id`

UUID generato dalla PWA al momento della creazione evento.

Regole:
- immutabile;
- unico per evento;
- usato per idempotenza end-to-end;
- deve arrivare fino a GAIA o a una tabella di mapping connector.

### `cloud_event_id`

UUID generato dal gateway.

Regole:
- identifica la riga cloud;
- usato da connector per poll/claim/ack.

### `gaia_entity_id`

UUID o ID generato da GAIA dopo applicazione.

Regole:
- restituito dal connector al gateway;
- mostrato alla PWA come conferma finale;
- usato per liste personali e link futuri.

---

## 3. Envelope evento

```json
{
  "client_event_id": "uuid",
  "event_type": "FIELD_REPORT_CREATED",
  "payload_version": 1,
  "operator_id": "uuid",
  "device_id": "uuid",
  "created_at_device": "2026-05-13T08:00:00Z",
  "timezone": "Europe/Rome",
  "payload": {},
  "attachments": [],
  "gps_context": {
    "permission": "granted",
    "accuracy_m": 8.5,
    "captured_at": "2026-05-13T08:00:00Z"
  }
}
```

---

## 4. Stato evento

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
```

Transizioni ammesse:

```text
LOCAL_DRAFT -> LOCAL_PENDING
LOCAL_PENDING -> CLOUD_RECEIVED
CLOUD_RECEIVED -> CLOUD_CLAIMED
CLOUD_CLAIMED -> APPLYING_TO_GAIA
APPLYING_TO_GAIA -> APPLIED_TO_GAIA
APPLYING_TO_GAIA -> FAILED_VALIDATION
APPLYING_TO_GAIA -> FAILED_RETRYABLE
FAILED_RETRYABLE -> CLOUD_RECEIVED
FAILED_VALIDATION -> LOCAL_DRAFT_CORRECTION
```

---

## 5. Idempotenza

### Gateway

Vincolo unico:

```text
(operator_id, device_id, client_event_id)
```

Se arriva lo stesso `client_event_id` con stesso hash payload:
- restituire lo stato esistente.

Se arriva lo stesso `client_event_id` con hash diverso:
- restituire `409 CONFLICT`.

### Connector

Prima di applicare a GAIA:
- controlla se evento gia applicato;
- se gia applicato, invia ack con mapping esistente;
- se non applicato, chiama GAIA.

### GAIA

Preferibile avere idempotenza nativa su `client_event_id`.
Se non disponibile nella prima fase, il connector mantiene una tabella locale/cloud di mapping applicato.

---

## 6. Polling connector

### Poll

```http
GET /api/mobile/connector/events/poll?limit=20
Authorization: Bearer connector_token
```

Risposta:

```json
{
  "events": [
    {
      "cloud_event_id": "uuid",
      "client_event_id": "uuid",
      "event_type": "FIELD_REPORT_CREATED",
      "payload_version": 1,
      "payload": {},
      "attachments": []
    }
  ]
}
```

### Claim

```http
POST /api/mobile/connector/events/{cloud_event_id}/claim
```

Il claim deve avere TTL.
Se il connector muore, l'evento torna disponibile dopo scadenza.

### Ack

```http
POST /api/mobile/connector/events/{cloud_event_id}/ack
```

Payload:

```json
{
  "gaia_entity_type": "field_report",
  "gaia_entity_id": "uuid",
  "extra": {
    "gaia_case_id": "uuid"
  }
}
```

### Fail

```http
POST /api/mobile/connector/events/{cloud_event_id}/fail
```

Payload:

```json
{
  "failure_type": "validation",
  "error_code": "GAIA_VALIDATION_ERROR",
  "message": "Categoria non valida",
  "retryable": false,
  "details": {}
}
```

---

## 7. Eventi MVP

### `ACTIVITY_START_REQUESTED`

```json
{
  "activity_catalog_id": "uuid",
  "team_id": "uuid",
  "vehicle_id": "uuid",
  "notes": "string",
  "started_at_device": "datetime",
  "gps_start": {
    "lat": 39.9,
    "lng": 8.6,
    "accuracy_m": 8.5
  }
}
```

### `ACTIVITY_STOP_REQUESTED`

```json
{
  "gaia_activity_id": "uuid",
  "client_started_event_id": "uuid",
  "stopped_at_device": "datetime",
  "odometer_km": 12345.6,
  "notes": "string",
  "gps_end": {
    "lat": 39.9,
    "lng": 8.6,
    "accuracy_m": 8.5
  }
}
```

### `FIELD_REPORT_CREATED`

```json
{
  "category_id": "uuid",
  "severity_id": "uuid",
  "title": "string",
  "description": "string",
  "linked_gaia_activity_id": "uuid",
  "gps_point": {
    "lat": 39.9,
    "lng": 8.6,
    "accuracy_m": 8.5
  },
  "attachments": [
    {
      "client_attachment_id": "uuid",
      "filename": "foto.jpg",
      "mime_type": "image/jpeg",
      "size_bytes": 123456,
      "sha256": "hex"
    }
  ]
}
```

---

## 8. Cataloghi e workset

Il connector sincronizza dal GAIA LAN al cloud:
- catalogo attivita;
- team;
- mezzi disponibili;
- categorie segnalazione;
- severita;
- attivita aperte per operatore;
- segnalazioni recenti;
- pratiche assegnate/collegate.

Ogni snapshot deve avere:
- `catalog_type` o `workset_type`;
- `version`;
- `synced_from_gaia_at`;
- payload.

La PWA legge sempre dal cloud, non da GAIA.

---

## 9. Errori

Classi errore:
- `VALIDATION`: payload da correggere, niente retry automatico.
- `AUTH`: utente o connector non autorizzato.
- `RETRYABLE`: rete, timeout, GAIA temporaneamente non disponibile.
- `CONFLICT`: evento duplicato incoerente o stato GAIA non compatibile.
- `FATAL`: errore non recuperabile senza intervento tecnico.

La PWA deve mostrare messaggi comprensibili e permettere correzione dove possibile.
