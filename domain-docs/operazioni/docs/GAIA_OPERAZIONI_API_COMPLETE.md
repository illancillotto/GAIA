# GAIA Operazioni – API Complete (FastAPI / REST)

## 1. Obiettivo

Questo documento definisce le API REST complete del modulo **GAIA Operazioni**.

Ambito:
- mezzi
- assegnazioni
- sessioni utilizzo
- carburante e manutenzioni
- attività operatori
- approvazioni
- segnalazioni
- pratiche interne
- allegati
- storage monitoring
- lookup e cataloghi

---

## 2. Convenzioni API

### 2.1 Base path

```text
/api/operazioni
```

### 2.2 Formato risposta

Risposta standard successo:

```json
{
  "data": {},
  "meta": {},
  "error": null
}
```

Risposta errore standard:

```json
{
  "data": null,
  "meta": {},
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Payload non valido",
    "details": {
      "field": "started_at"
    }
  }
}
```

### 2.3 Error codes suggeriti
- `VALIDATION_ERROR`
- `NOT_FOUND`
- `CONFLICT`
- `FORBIDDEN`
- `UNAUTHORIZED`
- `INVALID_STATE`
- `QUOTA_WARNING`
- `QUOTA_EXCEEDED`
- `GPS_DATA_MISSING`
- `OFFLINE_DUPLICATE`

### 2.4 Paginazione

Query params standard:
- `page`
- `page_size`
- `sort_by`
- `sort_order`

`meta` standard:

```json
{
  "page": 1,
  "page_size": 25,
  "total_items": 120,
  "total_pages": 5
}
```

---

# 3. Lookup / cataloghi

## 3.1 GET `/api/operazioni/lookups/activity-catalog`
Restituisce catalogo attività attive.

### Response 200
```json
{
  "data": [
    {
      "id": "uuid",
      "code": "MANUT_CANALE",
      "name": "Manutenzione canale",
      "category": "rete",
      "requires_vehicle": true,
      "requires_note": false,
      "sort_order": 10,
      "is_active": true
    }
  ],
  "meta": {},
  "error": null
}
```

## 3.2 GET `/api/operazioni/lookups/report-categories`

## 3.3 GET `/api/operazioni/lookups/report-severities`

## 3.4 GET `/api/operazioni/lookups/maintenance-types`

## 3.5 GET `/api/operazioni/lookups/teams`

---

# 4. Mezzi

## 4.1 GET `/api/operazioni/vehicles`
Lista mezzi con filtri.

### Query params
- `status`
- `vehicle_type`
- `team_id`
- `assigned_user_id`
- `search`
- `page`
- `page_size`

### Response 200
```json
{
  "data": [
    {
      "id": "uuid",
      "code": "MZ-001",
      "plate_number": "AB123CD",
      "name": "Pickup Isuzu",
      "vehicle_type": "pickup",
      "brand": "Isuzu",
      "model": "D-Max",
      "fuel_type": "diesel",
      "current_status": "available",
      "has_gps_device": true,
      "gps_provider_code": "GPS-9911",
      "is_active": true,
      "current_assignment": {
        "assignment_target_type": "team",
        "team_id": "uuid",
        "team_name": "Squadra Nord"
      },
      "last_odometer_km": 42115.4,
      "created_at": "2026-04-03T08:00:00Z",
      "updated_at": "2026-04-03T08:00:00Z"
    }
  ],
  "meta": {
    "page": 1,
    "page_size": 25,
    "total_items": 1,
    "total_pages": 1
  },
  "error": null
}
```

## 4.2 POST `/api/operazioni/vehicles`
Crea mezzo.

### Request
```json
{
  "code": "MZ-001",
  "plate_number": "AB123CD",
  "asset_tag": "ASSET-0001",
  "name": "Pickup Isuzu",
  "vehicle_type": "pickup",
  "brand": "Isuzu",
  "model": "D-Max",
  "year_of_manufacture": 2022,
  "fuel_type": "diesel",
  "ownership_type": "owned",
  "gps_provider_code": "GPS-9911",
  "has_gps_device": true,
  "notes": "Mezzo ufficio tecnico"
}
```

### Validazioni
- `code` obbligatorio e univoco
- `plate_number` univoca se valorizzata
- `year_of_manufacture` plausibile

### Response 201
Restituisce oggetto mezzo creato.

## 4.3 GET `/api/operazioni/vehicles/{vehicle_id}`
Dettaglio mezzo.

## 4.4 PATCH `/api/operazioni/vehicles/{vehicle_id}`
Aggiorna mezzo.

## 4.5 POST `/api/operazioni/vehicles/{vehicle_id}/deactivate`
Disattiva mezzo.

### Response 409
Se esiste sessione utilizzo aperta.

---

# 5. Assegnazioni mezzo

## 5.1 GET `/api/operazioni/vehicles/{vehicle_id}/assignments`
Storico assegnazioni.

## 5.2 POST `/api/operazioni/vehicles/{vehicle_id}/assignments`
Crea assegnazione.

### Request – assegnazione a operatore
```json
{
  "assignment_target_type": "operator",
  "operator_user_id": "uuid",
  "start_at": "2026-04-03T08:00:00Z",
  "reason": "Assegnazione temporanea",
  "notes": "Per attività canali"
}
```

### Request – assegnazione a squadra
```json
{
  "assignment_target_type": "team",
  "team_id": "uuid",
  "start_at": "2026-04-03T08:00:00Z",
  "reason": "Dotazione squadra"
}
```

### Response 409
- assegnazione sovrapposta già aperta

## 5.3 POST `/api/operazioni/vehicles/{vehicle_id}/assignments/{assignment_id}/close`
Chiude assegnazione.

### Request
```json
{
  "end_at": "2026-04-10T17:00:00Z",
  "notes": "Fine assegnazione"
}
```

---

# 6. Sessioni utilizzo mezzo

## 6.1 GET `/api/operazioni/vehicle-usage-sessions`
Lista sessioni con filtri.

### Query params
- `vehicle_id`
- `driver_user_id`
- `team_id`
- `status`
- `date_from`
- `date_to`

## 6.2 POST `/api/operazioni/vehicle-usage-sessions/start`
Avvia sessione utilizzo mezzo.

### Request
```json
{
  "vehicle_id": "uuid",
  "actual_driver_user_id": "uuid",
  "team_id": "uuid",
  "related_assignment_id": "uuid",
  "started_at": "2026-04-03T08:10:00Z",
  "start_odometer_km": 42115.4,
  "start_latitude": 39.9031234,
  "start_longitude": 8.5923456,
  "gps_source": "device_app",
  "notes": "Partenza da sede"
}
```

### Regole
- il mezzo non deve avere sessioni aperte
- `start_odometer_km` obbligatorio
- se il mezzo richiede GPS e dato assente, possibile warning o blocco in base a policy

### Response 201
```json
{
  "data": {
    "id": "uuid",
    "vehicle_id": "uuid",
    "status": "open",
    "started_at": "2026-04-03T08:10:00Z",
    "start_odometer_km": 42115.4
  },
  "meta": {},
  "error": null
}
```

## 6.3 POST `/api/operazioni/vehicle-usage-sessions/{session_id}/stop`
Chiude sessione.

### Request
```json
{
  "ended_at": "2026-04-03T12:45:00Z",
  "end_odometer_km": 42166.7,
  "end_latitude": 39.9111111,
  "end_longitude": 8.6011111,
  "gps_source": "vehicle_provider",
  "route_distance_km": 50.8,
  "engine_hours": 4.2,
  "notes": "Rientro sede"
}
```

### Response 409
- sessione già chiusa
- `end_odometer_km < start_odometer_km`

## 6.4 GET `/api/operazioni/vehicle-usage-sessions/{session_id}`
Dettaglio sessione.

## 6.5 POST `/api/operazioni/vehicle-usage-sessions/{session_id}/validate`
Valida sessione mezzo.

### Request
```json
{
  "validated_at": "2026-04-03T17:00:00Z",
  "note": "Sessione valida"
}
```

---

# 7. Letture km / odometro

## 7.1 POST `/api/operazioni/vehicles/{vehicle_id}/odometer-readings`
Inserisce lettura km.

### Request
```json
{
  "reading_at": "2026-04-03T08:00:00Z",
  "odometer_km": 42115.4,
  "source_type": "manual",
  "usage_session_id": "uuid",
  "notes": "Lettura prima uscita"
}
```

## 7.2 GET `/api/operazioni/vehicles/{vehicle_id}/odometer-readings`
Storico letture.

---

# 8. Carburante

## 8.1 POST `/api/operazioni/vehicles/{vehicle_id}/fuel-logs`
Registra rifornimento.

### Request
```json
{
  "usage_session_id": "uuid",
  "fueled_at": "2026-04-03T10:30:00Z",
  "liters": 35.5,
  "total_cost": 62.8,
  "odometer_km": 42140.0,
  "station_name": "Q8 Oristano",
  "notes": "Rifornimento operativo"
}
```

## 8.2 GET `/api/operazioni/vehicles/{vehicle_id}/fuel-logs`
Lista rifornimenti.

---

# 9. Manutenzioni

## 9.1 GET `/api/operazioni/vehicles/{vehicle_id}/maintenances`
Lista manutenzioni.

## 9.2 POST `/api/operazioni/vehicles/{vehicle_id}/maintenances`
Crea manutenzione.

### Request
```json
{
  "maintenance_type_id": "uuid",
  "title": "Tagliando annuale",
  "description": "Cambio filtri e olio",
  "status": "planned",
  "opened_at": "2026-04-03T09:00:00Z",
  "scheduled_for": "2026-04-12T09:00:00Z",
  "odometer_km": 42166.7,
  "supplier_name": "Officina Rossi",
  "cost_amount": 0,
  "notes": "Da eseguire"
}
```

## 9.3 PATCH `/api/operazioni/maintenances/{maintenance_id}`
Aggiorna manutenzione.

## 9.4 POST `/api/operazioni/maintenances/{maintenance_id}/complete`
Completa manutenzione.

### Request
```json
{
  "completed_at": "2026-04-12T15:30:00Z",
  "cost_amount": 280.5,
  "notes": "Intervento completato"
}
```

---

# 10. Documenti mezzo

## 10.1 POST `/api/operazioni/vehicles/{vehicle_id}/documents`
Carica documento mezzo.

### Request multipart
Campi form-data:
- `document_type`
- `title`
- `document_number`
- `issued_at`
- `expires_at`
- `file`
- `notes`

## 10.2 GET `/api/operazioni/vehicles/{vehicle_id}/documents`
Lista documenti.

## 10.3 GET `/api/operazioni/vehicle-documents/{document_id}`
Dettaglio documento.

## 10.4 DELETE `/api/operazioni/vehicle-documents/{document_id}`
Rimozione logica documento.

---

# 11. Attività operatori

## 11.1 GET `/api/operazioni/activities`
Lista attività con filtri.

### Query params
- `operator_user_id`
- `team_id`
- `vehicle_id`
- `status`
- `catalog_id`
- `date_from`
- `date_to`
- `search`

## 11.2 POST `/api/operazioni/activities/start`
Avvia attività.

### Request
```json
{
  "activity_catalog_id": "uuid",
  "operator_user_id": "uuid",
  "team_id": "uuid",
  "vehicle_id": "uuid",
  "vehicle_usage_session_id": "uuid",
  "started_at": "2026-04-03T08:20:00Z",
  "start_latitude": 39.9031234,
  "start_longitude": 8.5923456,
  "text_note": "Inizio lavorazione settore ovest",
  "offline_client_uuid": "uuid",
  "client_created_at": "2026-04-03T08:20:00Z"
}
```

### Regole
- una stessa attività non può partire due volte con stesso `offline_client_uuid`
- se `activity_catalog.requires_vehicle = true`, `vehicle_id` obbligatorio

### Response 201
```json
{
  "data": {
    "id": "uuid",
    "status": "in_progress",
    "started_at": "2026-04-03T08:20:00Z"
  },
  "meta": {},
  "error": null
}
```

## 11.3 POST `/api/operazioni/activities/{activity_id}/stop`
Chiude attività.

### Request
```json
{
  "ended_at": "2026-04-03T11:45:00Z",
  "end_latitude": 39.9111111,
  "end_longitude": 8.6011111,
  "duration_minutes_declared": 205,
  "text_note": "Attività conclusa",
  "submit_for_review": true
}
```

### Effetti
- calcolo `duration_minutes_calculated`
- stato `submitted` se `submit_for_review = true`, altrimenti `draft`

## 11.4 GET `/api/operazioni/activities/{activity_id}`
Dettaglio attività.

### Response 200
```json
{
  "data": {
    "id": "uuid",
    "activity_catalog": {
      "id": "uuid",
      "code": "MANUT_CANALE",
      "name": "Manutenzione canale"
    },
    "operator": {
      "id": "uuid",
      "full_name": "Mario Rossi"
    },
    "team": {
      "id": "uuid",
      "name": "Squadra Nord"
    },
    "vehicle": {
      "id": "uuid",
      "code": "MZ-001",
      "name": "Pickup Isuzu"
    },
    "status": "submitted",
    "started_at": "2026-04-03T08:20:00Z",
    "ended_at": "2026-04-03T11:45:00Z",
    "duration_minutes_declared": 205,
    "duration_minutes_calculated": 205,
    "text_note": "Attività conclusa",
    "audio_note_attachment": null,
    "attachments": [],
    "approvals": []
  },
  "meta": {},
  "error": null
}
```

## 11.5 PATCH `/api/operazioni/activities/{activity_id}`
Aggiornamento attività in stato modificabile.

### Regole
- operatore può modificare solo `draft` o `rejected` se policy lo consente
- capi possono rettificare senza cancellare storico

## 11.6 POST `/api/operazioni/activities/{activity_id}/submit`
Invia in approvazione.

### Request
```json
{
  "note": "Pronta per verifica"
}
```

## 11.7 POST `/api/operazioni/activities/{activity_id}/approve`
Approva attività.

### Request
```json
{
  "decision": "approved",
  "note": "Consuntivo corretto"
}
```

### Request alternativa
```json
{
  "decision": "rejected",
  "note": "Mancano dettagli percorso"
}
```

### Request alternativa
```json
{
  "decision": "needs_integration",
  "note": "Integrare foto"
}
```

### Effetti
- inserimento `activity_approval`
- aggiornamento `operator_activity.status`
- tracciamento evento workflow

## 11.8 POST `/api/operazioni/activities/{activity_id}/attachments`
Carica allegato attività.

### Multipart form-data
- `file`
- `attachment_type`
- `note` opzionale

## 11.9 POST `/api/operazioni/activities/{activity_id}/audio-note`
Carica nota audio.

### Validazioni
- un solo audio note principale per attività
- dimensione massima configurabile

---

# 12. Sync offline mini-app

## 12.1 POST `/api/operazioni/mobile/sync/activities`
Sync batch attività create offline.

### Request
```json
{
  "items": [
    {
      "offline_client_uuid": "uuid",
      "activity_catalog_id": "uuid",
      "operator_user_id": "uuid",
      "team_id": "uuid",
      "vehicle_id": "uuid",
      "started_at": "2026-04-03T08:20:00Z",
      "ended_at": "2026-04-03T11:45:00Z",
      "text_note": "Bozza offline",
      "client_created_at": "2026-04-03T08:20:00Z"
    }
  ]
}
```

### Response 200
```json
{
  "data": {
    "processed": 1,
    "created": 1,
    "duplicates": 0,
    "items": [
      {
        "offline_client_uuid": "uuid",
        "server_id": "uuid",
        "status": "created"
      }
    ]
  },
  "meta": {},
  "error": null
}
```

## 12.2 POST `/api/operazioni/mobile/sync/reports`
Sync batch segnalazioni create offline.

### Gestione duplicati
Se `offline_client_uuid` già presente:
- risposta item `status = duplicate`
- non ricrea nuova entità

---

# 13. Segnalazioni

## 13.1 GET `/api/operazioni/reports`
Lista segnalazioni.

### Query params
- `reporter_user_id`
- `team_id`
- `vehicle_id`
- `category_id`
- `severity_id`
- `date_from`
- `date_to`
- `has_case`

## 13.2 POST `/api/operazioni/reports`
Crea segnalazione e genera pratica.

### Request JSON semplice
```json
{
  "reporter_user_id": "uuid",
  "team_id": "uuid",
  "vehicle_id": "uuid",
  "operator_activity_id": "uuid",
  "category_id": "uuid",
  "severity_id": "uuid",
  "title": "Cedimento argine secondario",
  "description": "Presente erosione visibile",
  "latitude": 39.9012345,
  "longitude": 8.6012345,
  "gps_accuracy_meters": 8.5,
  "gps_source": "device_app",
  "offline_client_uuid": "uuid",
  "client_created_at": "2026-04-03T09:10:00Z"
}
```

### Effetti
- crea `field_report`
- genera `internal_case`
- collega report e case
- registra evento iniziale

### Response 201
```json
{
  "data": {
    "report": {
      "id": "uuid",
      "report_number": "REP-2026-000123",
      "status": "submitted"
    },
    "case": {
      "id": "uuid",
      "case_number": "CAS-2026-000123",
      "status": "open"
    }
  },
  "meta": {},
  "error": null
}
```

## 13.3 POST `/api/operazioni/reports/{report_id}/attachments`
Upload allegato segnalazione.

### Multipart form-data
- `file`
- `attachment_type`
- `compress_if_needed=true|false`

### Regole
- video oltre soglia → compressione automatica se configurata
- se storage quota superata → errore o blocco policy

### Response 409
```json
{
  "data": null,
  "meta": {},
  "error": {
    "code": "QUOTA_EXCEEDED",
    "message": "Spazio allegati esaurito",
    "details": {
      "quota_bytes": 53687091200,
      "used_bytes": 53687095000
    }
  }
}
```

## 13.4 GET `/api/operazioni/reports/{report_id}`
Dettaglio segnalazione.

---

# 14. Pratiche interne

## 14.1 GET `/api/operazioni/cases`
Lista pratiche con filtri.

### Query params
- `status`
- `assigned_to_user_id`
- `assigned_team_id`
- `severity_id`
- `category_id`
- `date_from`
- `date_to`
- `search`

## 14.2 GET `/api/operazioni/cases/{case_id}`
Dettaglio pratica.

### Response 200
```json
{
  "data": {
    "id": "uuid",
    "case_number": "CAS-2026-000123",
    "status": "open",
    "title": "Cedimento argine secondario",
    "description": "Presente erosione visibile",
    "severity": {
      "id": "uuid",
      "code": "HIGH",
      "name": "Alta"
    },
    "category": {
      "id": "uuid",
      "code": "ARGINI",
      "name": "Argini"
    },
    "source_report": {
      "id": "uuid",
      "report_number": "REP-2026-000123"
    },
    "assigned_to_user": null,
    "assigned_team": null,
    "events": [],
    "attachments": []
  },
  "meta": {},
  "error": null
}
```

## 14.3 POST `/api/operazioni/cases/{case_id}/assign`
Assegna pratica a utente o squadra.

### Request utente
```json
{
  "assigned_to_user_id": "uuid",
  "note": "Gestione urgente"
}
```

### Request squadra
```json
{
  "assigned_team_id": "uuid",
  "note": "In carico a squadra nord"
}
```

### Regole
- almeno uno tra `assigned_to_user_id` e `assigned_team_id`
- storico su `internal_case_assignment_history`

## 14.4 POST `/api/operazioni/cases/{case_id}/acknowledge`
Presa visione pratica.

### Request
```json
{
  "note": "Presa in carico ricevuta"
}
```

## 14.5 POST `/api/operazioni/cases/{case_id}/start`
Inizio lavorazione.

### Request
```json
{
  "started_at": "2026-04-03T10:00:00Z",
  "note": "Avvio sopralluogo"
}
```

## 14.6 POST `/api/operazioni/cases/{case_id}/resolve`
Risoluzione pratica.

### Request
```json
{
  "resolved_at": "2026-04-03T14:30:00Z",
  "resolution_note": "Intervento eseguito"
}
```

## 14.7 POST `/api/operazioni/cases/{case_id}/close`
Chiusura pratica.

### Request
```json
{
  "closed_at": "2026-04-03T15:00:00Z",
  "resolution_note": "Pratica chiusa",
  "note": "Validata dal responsabile"
}
```

## 14.8 POST `/api/operazioni/cases/{case_id}/reopen`
Riapertura pratica.

### Request
```json
{
  "note": "Problema ricomparso"
}
```

### Response 409
Se stato non compatibile con riapertura.

## 14.9 POST `/api/operazioni/cases/{case_id}/attachments`
Upload allegato pratica.

## 14.10 GET `/api/operazioni/cases/{case_id}/events`
Storico eventi.

---

# 15. Allegati

## 15.1 GET `/api/operazioni/attachments/{attachment_id}`
Metadata allegato.

## 15.2 GET `/api/operazioni/attachments/{attachment_id}/download`
Download file.

## 15.3 DELETE `/api/operazioni/attachments/{attachment_id}`
Rimozione logica allegato.

### Regole
- solo admin/responsabile o owner secondo policy
- file non eliminato fisicamente subito, ma marcato `is_deleted = true`

---

# 16. GPS / track summary

## 16.1 GET `/api/operazioni/gps/tracks/{track_id}`
Dettaglio summary track.

## 16.1-bis GET `/api/operazioni/activities/{activity_id}/gps-viewer`
Viewer GPS per scheda attività.

### Response 200
```json
{
  "summary": {
    "id": "uuid",
    "source_type": "provider_import",
    "provider_name": "provider_x",
    "provider_track_id": "PX-778899",
    "started_at": "2026-04-03T08:00:00Z",
    "ended_at": "2026-04-03T12:00:00Z",
    "start_latitude": 39.9,
    "start_longitude": 8.59,
    "end_latitude": 39.91,
    "end_longitude": 8.60,
    "total_distance_km": 50.8,
    "total_duration_seconds": 14400
  },
  "points": [
    {
      "latitude": 39.9,
      "longitude": 8.59,
      "timestamp": "2026-04-03T08:00:00Z"
    }
  ],
  "bounds": {
    "min_latitude": 39.9,
    "max_latitude": 39.91,
    "min_longitude": 8.59,
    "max_longitude": 8.60
  },
  "viewer_mode": "track",
  "point_count": 48,
  "uses_raw_payload": true
}
```

### Uso
- usato dal dettaglio attività per viewer dedicato della traccia
- degrada a segmento start/end se il payload GPS non contiene polilinea completa

## 16.2 POST `/api/operazioni/gps/provider/import`
Import dati da provider GPS.

### Request
```json
{
  "provider_name": "provider_x",
  "vehicle_id": "uuid",
  "provider_track_id": "PX-778899",
  "started_at": "2026-04-03T08:00:00Z",
  "ended_at": "2026-04-03T12:00:00Z",
  "start_latitude": 39.90,
  "start_longitude": 8.59,
  "end_latitude": 39.91,
  "end_longitude": 8.60,
  "total_distance_km": 50.8,
  "total_duration_seconds": 14400,
  "raw_payload_json": {}
}
```

### Uso
- endpoint interno/admin/integrazione
- collega successivamente track a sessione o attività se match temporale

---

# 17. Storage monitoring

## 17.1 GET `/api/operazioni/storage/metrics/latest`
Ultima metrica quota storage.

### Response 200
```json
{
  "data": {
    "measured_at": "2026-04-03T09:00:00Z",
    "total_bytes_used": 21474836480,
    "quota_bytes": 53687091200,
    "percentage_used": 40.0,
    "active_alerts": []
  },
  "meta": {},
  "error": null
}
```

## 17.2 GET `/api/operazioni/storage/alerts`
Lista alert quota.

## 17.3 POST `/api/operazioni/storage/recalculate`
Forza ricalcolo metriche storage.

### Uso
- admin only
- endpoint tecnico/operativo

---

# 18. Dashboard admin / capi

## 18.1 GET `/api/operazioni/dashboard/summary`
KPI principali.

### Response 200
```json
{
  "data": {
    "vehicles": {
      "total": 32,
      "available": 18,
      "in_use": 10,
      "maintenance": 4
    },
    "activities": {
      "today_total": 41,
      "in_progress": 8,
      "submitted": 12,
      "approved_today": 15,
      "rejected_today": 2
    },
    "cases": {
      "open": 23,
      "assigned": 7,
      "in_progress": 9,
      "critical": 3
    },
    "storage": {
      "percentage_used": 81.4,
      "alert_level": "warning_70"
    }
  },
  "meta": {},
  "error": null
}
```

## 18.2 GET `/api/operazioni/dashboard/pending-approvals`
Attività da approvare.

## 18.3 GET `/api/operazioni/dashboard/open-critical-cases`
Pratiche aperte ad alta priorità.

---

# 19. Regole di autorizzazione suggerite

## Admin
Può:
- CRUD completo su tutte le entità
- gestire storage
- forzare ricalcoli
- chiudere/riaprire pratiche

## Capo servizio
Può:
- vedere mezzi/attività/pratiche del proprio ambito
- approvare o respingere attività
- assegnare e chiudere pratiche
- vedere KPI del proprio ambito

## Operatore
Può:
- vedere i propri mezzi/attività/pratiche di competenza
- creare attività
- chiudere attività
- creare segnalazioni
- caricare allegati
- non può approvare

---

# 20. Stati e transizioni consigliate

## 20.1 Activity
- `draft -> in_progress`
- `in_progress -> submitted`
- `submitted -> under_review`
- `under_review -> approved`
- `under_review -> rejected`
- `rejected -> rectified`
- `rectified -> submitted`

## 20.2 Case
- `open -> assigned`
- `assigned -> acknowledged`
- `acknowledged -> in_progress`
- `in_progress -> resolved`
- `resolved -> closed`
- `closed -> reopened`
- `open/assigned/in_progress -> cancelled`

---

# 21. Validazioni critiche

## 21.1 Mezzi
- non consentire sessione aperta doppia sullo stesso mezzo
- non consentire stop con km finali inferiori agli iniziali

## 21.2 Attività
- non consentire `ended_at < started_at`
- `vehicle_id` obbligatorio se il catalogo lo richiede
- `offline_client_uuid` usato per dedup sync

## 21.3 Segnalazioni
- categoria e gravità obbligatorie
- pratica sempre generata in transazione unica

## 21.4 Storage
- warning a soglie 70/85/95
- policy su quota superata configurabile

---

# 22. Operazioni batch / future

Endpoint opzionali futuri:
- `POST /api/operazioni/activities/bulk-approve`
- `POST /api/operazioni/cases/bulk-assign`
- `GET /api/operazioni/reports/export`
- `GET /api/operazioni/activities/export`
- `GET /api/operazioni/vehicles/export`

---

# 23. Mapping con backend FastAPI

Struttura suggerita:

```text
backend/app/modules/operazioni/
  routes/
    vehicles.py
    vehicle_usage.py
    maintenances.py
    activities.py
    reports.py
    cases.py
    attachments.py
    lookups.py
    dashboard.py
    storage.py
    gps.py
  models/
  schemas/
  services/
  repositories/
```

---

# 24. Output atteso per sviluppo

Questo documento API è pensato per essere base diretta per:
- router FastAPI
- schemi Pydantic request/response
- service layer
- autorizzazioni per ruolo
- mini-app PWA e dashboard admin
