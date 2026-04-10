# GAIA Operazioni – Schema DB completo (PostgreSQL)

## 1. Obiettivo

Questo documento definisce lo schema dati completo del modulo **GAIA Operazioni** per PostgreSQL.

Il modulo copre:
- gestione mezzi
- attività operatori
- segnalazioni trasformate in pratiche interne
- allegati multimediali
- workflow approvativi
- integrazione GPS con valore di consuntivazione
- monitoraggio storage allegati

L'obiettivo è fornire una base coerente per implementazione FastAPI + SQLAlchemy + Alembic nel monolite GAIA.

---

## 2. Convenzioni generali

### 2.1 Naming
- Tabelle in `snake_case`
- Chiavi primarie con campo `id` di tipo `UUID`
- Foreign key con suffisso `_id`
- Timestamp in UTC

### 2.2 Campi audit standard
Quasi tutte le tabelle applicative devono includere:
- `created_at TIMESTAMPTZ NOT NULL`
- `updated_at TIMESTAMPTZ NOT NULL`
- `created_by_user_id UUID NULL`
- `updated_by_user_id UUID NULL`

### 2.3 Soft delete
Per le entità configurative e master data usare:
- `is_active BOOLEAN NOT NULL DEFAULT TRUE`

### 2.4 Tipi PostgreSQL consigliati
- `UUID`
- `TEXT`
- `VARCHAR(n)` solo quando serve un limite formale
- `NUMERIC(12,2)` per importi/carburanti/ore se necessario
- `NUMERIC(12,3)` per km o valori metrici più precisi
- `TIMESTAMPTZ`
- `JSONB`
- `BOOLEAN`

---

## 3. Dipendenze con moduli GAIA esistenti

Il modulo Operazioni deve integrarsi con utenti applicativi già esistenti in GAIA, coerentemente con il backend monolite modulare e database condiviso già definiti nell'architettura di progetto. Il nuovo dominio va quindi modellato come modulo interno e non come servizio separato. fileciteturn0file0 fileciteturn0file2 fileciteturn0file3

Assunzioni:
- esiste già una tabella utenti applicativi del core/auth
- eventuali riferimenti a utenti saranno fatti verso `application_user(id)` o tabella equivalente del core
- eventuali squadre possono stare nel modulo Operazioni

Nel documento, per semplicità, il riferimento è indicato come:
- `application_user(id)`

---

# 4. Enumerazioni logiche

Le enumerazioni possono essere implementate in uno di questi modi:
- tabelle lookup
- enum PostgreSQL dove stabile
- stringhe validate a livello applicativo

Per GAIA consiglio:
- lookup tables per categorie e cataloghi modificabili
- stringhe controllate per stati interni stabili

Valori suggeriti:

## 4.1 Vehicle status
- `available`
- `assigned`
- `in_use`
- `maintenance`
- `out_of_service`

## 4.2 Assignment target type
- `operator`
- `team`

## 4.3 Activity status
- `draft`
- `in_progress`
- `submitted`
- `under_review`
- `approved`
- `rejected`
- `rectified`

## 4.4 Case status
- `open`
- `assigned`
- `acknowledged`
- `in_progress`
- `waiting`
- `resolved`
- `closed`
- `cancelled`
- `reopened`

## 4.5 Attachment type
- `image`
- `audio`
- `video`
- `document`

## 4.6 Attachment sync/source status
- `uploaded`
- `compressed`
- `failed`
- `pending_sync`

## 4.7 GPS source
- `device_app`
- `vehicle_provider`
- `manual`
- `derived`

## 4.8 Approval decision
- `approved`
- `rejected`
- `needs_integration`

---

# 5. Schema relazionale – area organizzativa

## 5.1 `team`
Rappresenta una squadra operativa.

| Campo | Tipo | Vincoli | Note |
|---|---|---|---|
| id | UUID | PK | |
| code | VARCHAR(50) | UNIQUE NOT NULL | Codice interno squadra |
| name | VARCHAR(150) | NOT NULL | |
| description | TEXT | NULL | |
| supervisor_user_id | UUID | FK -> application_user(id) NULL | Responsabile di riferimento |
| is_active | BOOLEAN | NOT NULL DEFAULT TRUE | |
| created_at | TIMESTAMPTZ | NOT NULL | |
| updated_at | TIMESTAMPTZ | NOT NULL | |
| created_by_user_id | UUID | FK NULL | |
| updated_by_user_id | UUID | FK NULL | |

Indici:
- `idx_team_name`
- `idx_team_supervisor_user_id`

## 5.2 `team_membership`
Relazione operatori ↔ squadre con storicizzazione.

| Campo | Tipo | Vincoli | Note |
|---|---|---|---|
| id | UUID | PK | |
| team_id | UUID | FK NOT NULL | |
| user_id | UUID | FK -> application_user(id) NOT NULL | |
| role_in_team | VARCHAR(100) | NULL | es. operatore, autista, caposquadra |
| valid_from | TIMESTAMPTZ | NOT NULL | |
| valid_to | TIMESTAMPTZ | NULL | |
| is_primary | BOOLEAN | NOT NULL DEFAULT FALSE | |
| created_at | TIMESTAMPTZ | NOT NULL | |
| updated_at | TIMESTAMPTZ | NOT NULL | |

Vincoli:
- `CHECK (valid_to IS NULL OR valid_to >= valid_from)`

Indici:
- `idx_team_membership_team_id`
- `idx_team_membership_user_id`
- `idx_team_membership_validity`

## 5.3 `operator_profile`
Estensione operativa dell'utente applicativo.

| Campo | Tipo | Vincoli | Note |
|---|---|---|---|
| id | UUID | PK | |
| user_id | UUID | FK -> application_user(id) UNIQUE NOT NULL | |
| employee_code | VARCHAR(50) | UNIQUE NULL | |
| phone | VARCHAR(50) | NULL | |
| can_drive_vehicles | BOOLEAN | NOT NULL DEFAULT FALSE | |
| notes | TEXT | NULL | |
| is_active | BOOLEAN | NOT NULL DEFAULT TRUE | |
| created_at | TIMESTAMPTZ | NOT NULL | |
| updated_at | TIMESTAMPTZ | NOT NULL | |

---

# 6. Schema relazionale – area mezzi

## 6.1 `vehicle`
Anagrafica principale mezzo.

| Campo | Tipo | Vincoli | Note |
|---|---|---|---|
| id | UUID | PK | |
| code | VARCHAR(50) | UNIQUE NOT NULL | Codice interno mezzo |
| plate_number | VARCHAR(20) | UNIQUE NULL | Targa |
| asset_tag | VARCHAR(100) | UNIQUE NULL | |
| name | VARCHAR(150) | NOT NULL | Nome leggibile |
| vehicle_type | VARCHAR(100) | NOT NULL | auto, escavatore, trattore, furgone... |
| brand | VARCHAR(100) | NULL | |
| model | VARCHAR(100) | NULL | |
| year_of_manufacture | INTEGER | NULL | |
| fuel_type | VARCHAR(50) | NULL | diesel, benzina, elettrico... |
| current_status | VARCHAR(50) | NOT NULL DEFAULT 'available' | |
| ownership_type | VARCHAR(50) | NULL | owned, leased, rented |
| notes | TEXT | NULL | |
| gps_provider_code | VARCHAR(100) | NULL | codice esterno provider |
| has_gps_device | BOOLEAN | NOT NULL DEFAULT FALSE | |
| is_active | BOOLEAN | NOT NULL DEFAULT TRUE | |
| created_at | TIMESTAMPTZ | NOT NULL | |
| updated_at | TIMESTAMPTZ | NOT NULL | |
| created_by_user_id | UUID | FK NULL | |
| updated_by_user_id | UUID | FK NULL | |

Indici:
- `idx_vehicle_name`
- `idx_vehicle_current_status`
- `idx_vehicle_vehicle_type`

## 6.2 `vehicle_assignment`
Storico assegnazioni del mezzo a operatore o squadra.

| Campo | Tipo | Vincoli | Note |
|---|---|---|---|
| id | UUID | PK | |
| vehicle_id | UUID | FK NOT NULL | |
| assignment_target_type | VARCHAR(20) | NOT NULL | operator/team |
| operator_user_id | UUID | FK NULL | se target = operator |
| team_id | UUID | FK NULL | se target = team |
| assigned_by_user_id | UUID | FK -> application_user(id) NOT NULL | |
| start_at | TIMESTAMPTZ | NOT NULL | |
| end_at | TIMESTAMPTZ | NULL | |
| reason | TEXT | NULL | |
| notes | TEXT | NULL | |
| created_at | TIMESTAMPTZ | NOT NULL | |
| updated_at | TIMESTAMPTZ | NOT NULL | |

Vincoli:
- `CHECK (assignment_target_type IN ('operator','team'))`
- `CHECK ((assignment_target_type = 'operator' AND operator_user_id IS NOT NULL AND team_id IS NULL) OR (assignment_target_type = 'team' AND team_id IS NOT NULL AND operator_user_id IS NULL))`
- `CHECK (end_at IS NULL OR end_at >= start_at)`

Indici:
- `idx_vehicle_assignment_vehicle_id`
- `idx_vehicle_assignment_operator_user_id`
- `idx_vehicle_assignment_team_id`
- `idx_vehicle_assignment_start_at`

Nota applicativa:
- evitare sovrapposizioni temporali aperte sullo stesso mezzo con validazione applicativa o exclusion constraint avanzata

## 6.3 `vehicle_odometer_reading`
Letture contachilometri.

| Campo | Tipo | Vincoli | Note |
|---|---|---|---|
| id | UUID | PK | |
| vehicle_id | UUID | FK NOT NULL | |
| reading_at | TIMESTAMPTZ | NOT NULL | |
| odometer_km | NUMERIC(12,3) | NOT NULL | |
| source_type | VARCHAR(30) | NOT NULL | manual/device/provider |
| usage_session_id | UUID | FK NULL | opzionale |
| recorded_by_user_id | UUID | FK NULL | |
| notes | TEXT | NULL | |
| created_at | TIMESTAMPTZ | NOT NULL | |
| updated_at | TIMESTAMPTZ | NOT NULL | |

Vincoli:
- `CHECK (odometer_km >= 0)`

Indici:
- `idx_vehicle_odometer_vehicle_id`
- `idx_vehicle_odometer_reading_at`

## 6.4 `vehicle_usage_session`
Sessione di utilizzo del mezzo.

| Campo | Tipo | Vincoli | Note |
|---|---|---|---|
| id | UUID | PK | |
| vehicle_id | UUID | FK NOT NULL | |
| started_by_user_id | UUID | FK -> application_user(id) NOT NULL | utente che apre sessione |
| actual_driver_user_id | UUID | FK -> application_user(id) NULL | guidatore effettivo |
| team_id | UUID | FK NULL | squadra operativa |
| related_assignment_id | UUID | FK NULL | riferimento assegnazione |
| started_at | TIMESTAMPTZ | NOT NULL | |
| ended_at | TIMESTAMPTZ | NULL | |
| start_odometer_km | NUMERIC(12,3) | NOT NULL | |
| end_odometer_km | NUMERIC(12,3) | NULL | |
| start_latitude | NUMERIC(10,7) | NULL | |
| start_longitude | NUMERIC(10,7) | NULL | |
| end_latitude | NUMERIC(10,7) | NULL | |
| end_longitude | NUMERIC(10,7) | NULL | |
| gps_source | VARCHAR(30) | NULL | |
| route_distance_km | NUMERIC(12,3) | NULL | dal provider GPS o app |
| engine_hours | NUMERIC(12,2) | NULL | opzionale per mezzi speciali |
| notes | TEXT | NULL | |
| status | VARCHAR(30) | NOT NULL DEFAULT 'open' | open/closed/validated/cancelled |
| validated_by_user_id | UUID | FK NULL | |
| validated_at | TIMESTAMPTZ | NULL | |
| created_at | TIMESTAMPTZ | NOT NULL | |
| updated_at | TIMESTAMPTZ | NOT NULL | |

Vincoli:
- `CHECK (ended_at IS NULL OR ended_at >= started_at)`
- `CHECK (start_odometer_km >= 0)`
- `CHECK (end_odometer_km IS NULL OR end_odometer_km >= start_odometer_km)`

Indici:
- `idx_vehicle_usage_session_vehicle_id`
- `idx_vehicle_usage_session_started_by_user_id`
- `idx_vehicle_usage_session_actual_driver_user_id`
- `idx_vehicle_usage_session_team_id`
- `idx_vehicle_usage_session_started_at`
- `idx_vehicle_usage_session_status`

## 6.5 `vehicle_fuel_log`
Rifornimenti e consumi.

| Campo | Tipo | Vincoli | Note |
|---|---|---|---|
| id | UUID | PK | |
| vehicle_id | UUID | FK NOT NULL | |
| usage_session_id | UUID | FK NULL | opzionale |
| recorded_by_user_id | UUID | FK -> application_user(id) NOT NULL | |
| fueled_at | TIMESTAMPTZ | NOT NULL | |
| liters | NUMERIC(10,3) | NOT NULL | |
| total_cost | NUMERIC(12,2) | NULL | |
| odometer_km | NUMERIC(12,3) | NULL | |
| station_name | VARCHAR(150) | NULL | |
| receipt_attachment_id | UUID | FK NULL | allegato scontrino |
| notes | TEXT | NULL | |
| created_at | TIMESTAMPTZ | NOT NULL | |
| updated_at | TIMESTAMPTZ | NOT NULL | |

Vincoli:
- `CHECK (liters > 0)`
- `CHECK (total_cost IS NULL OR total_cost >= 0)`

Indici:
- `idx_vehicle_fuel_log_vehicle_id`
- `idx_vehicle_fuel_log_fueled_at`

## 6.6 `vehicle_maintenance_type`
Lookup tipi manutenzione.

| Campo | Tipo | Vincoli |
|---|---|---|
| id | UUID | PK |
| code | VARCHAR(50) | UNIQUE NOT NULL |
| name | VARCHAR(150) | NOT NULL |
| description | TEXT | NULL |
| is_active | BOOLEAN | NOT NULL DEFAULT TRUE |
| created_at | TIMESTAMPTZ | NOT NULL |
| updated_at | TIMESTAMPTZ | NOT NULL |

## 6.7 `vehicle_maintenance`
Eventi manutentivi.

| Campo | Tipo | Vincoli | Note |
|---|---|---|---|
| id | UUID | PK | |
| vehicle_id | UUID | FK NOT NULL | |
| maintenance_type_id | UUID | FK NULL | |
| title | VARCHAR(200) | NOT NULL | |
| description | TEXT | NULL | |
| status | VARCHAR(30) | NOT NULL DEFAULT 'planned' | planned/in_progress/completed/cancelled |
| opened_at | TIMESTAMPTZ | NOT NULL | |
| scheduled_for | TIMESTAMPTZ | NULL | |
| completed_at | TIMESTAMPTZ | NULL | |
| odometer_km | NUMERIC(12,3) | NULL | |
| supplier_name | VARCHAR(150) | NULL | officina/fornitore |
| cost_amount | NUMERIC(12,2) | NULL | |
| notes | TEXT | NULL | |
| created_at | TIMESTAMPTZ | NOT NULL | |
| updated_at | TIMESTAMPTZ | NOT NULL | |
| created_by_user_id | UUID | FK NULL | |
| updated_by_user_id | UUID | FK NULL | |

Vincoli:
- `CHECK (completed_at IS NULL OR completed_at >= opened_at)`

Indici:
- `idx_vehicle_maintenance_vehicle_id`
- `idx_vehicle_maintenance_status`
- `idx_vehicle_maintenance_scheduled_for`

## 6.8 `vehicle_document`
Documenti del mezzo.

| Campo | Tipo | Vincoli | Note |
|---|---|---|---|
| id | UUID | PK | |
| vehicle_id | UUID | FK NOT NULL | |
| document_type | VARCHAR(50) | NOT NULL | insurance, registration, inspection, lease, other |
| title | VARCHAR(200) | NOT NULL | |
| document_number | VARCHAR(100) | NULL | |
| issued_at | DATE | NULL | |
| expires_at | DATE | NULL | |
| attachment_id | UUID | FK NOT NULL | file associato |
| notes | TEXT | NULL | |
| created_at | TIMESTAMPTZ | NOT NULL | |
| updated_at | TIMESTAMPTZ | NOT NULL | |

Indici:
- `idx_vehicle_document_vehicle_id`
- `idx_vehicle_document_expires_at`
- `idx_vehicle_document_document_type`

---

# 7. Schema relazionale – area attività

## 7.1 `activity_catalog`
Catalogo attività fisso selezionabile dagli operatori.

| Campo | Tipo | Vincoli | Note |
|---|---|---|---|
| id | UUID | PK | |
| code | VARCHAR(50) | UNIQUE NOT NULL | |
| name | VARCHAR(150) | NOT NULL | |
| description | TEXT | NULL | |
| category | VARCHAR(100) | NULL | |
| requires_vehicle | BOOLEAN | NOT NULL DEFAULT FALSE | |
| requires_note | BOOLEAN | NOT NULL DEFAULT FALSE | |
| sort_order | INTEGER | NOT NULL DEFAULT 0 | |
| is_active | BOOLEAN | NOT NULL DEFAULT TRUE | |
| created_at | TIMESTAMPTZ | NOT NULL | |
| updated_at | TIMESTAMPTZ | NOT NULL | |

Indici:
- `idx_activity_catalog_category`
- `idx_activity_catalog_sort_order`

## 7.2 `operator_activity`
Attività operativa svolta dall'operatore.

| Campo | Tipo | Vincoli | Note |
|---|---|---|---|
| id | UUID | PK | |
| activity_catalog_id | UUID | FK NOT NULL | |
| operator_user_id | UUID | FK -> application_user(id) NOT NULL | |
| team_id | UUID | FK NULL | |
| vehicle_id | UUID | FK NULL | |
| vehicle_usage_session_id | UUID | FK NULL | opzionale |
| status | VARCHAR(30) | NOT NULL DEFAULT 'draft' | |
| started_at | TIMESTAMPTZ | NOT NULL | |
| ended_at | TIMESTAMPTZ | NULL | |
| duration_minutes_declared | INTEGER | NULL | |
| duration_minutes_calculated | INTEGER | NULL | |
| start_latitude | NUMERIC(10,7) | NULL | |
| start_longitude | NUMERIC(10,7) | NULL | |
| end_latitude | NUMERIC(10,7) | NULL | |
| end_longitude | NUMERIC(10,7) | NULL | |
| gps_track_summary_id | UUID | FK NULL | |
| text_note | TEXT | NULL | |
| audio_note_attachment_id | UUID | FK NULL | |
| submitted_at | TIMESTAMPTZ | NULL | |
| reviewed_by_user_id | UUID | FK NULL | |
| reviewed_at | TIMESTAMPTZ | NULL | |
| review_outcome | VARCHAR(30) | NULL | approved/rejected/needs_integration |
| review_note | TEXT | NULL | |
| rectified_from_activity_id | UUID | FK NULL | eventuale duplicato rettificato |
| offline_client_uuid | UUID | NULL | per dedup sync offline |
| client_created_at | TIMESTAMPTZ | NULL | timestamp device |
| server_received_at | TIMESTAMPTZ | NULL | |
| created_at | TIMESTAMPTZ | NOT NULL | |
| updated_at | TIMESTAMPTZ | NOT NULL | |
| created_by_user_id | UUID | FK NULL | |
| updated_by_user_id | UUID | FK NULL | |

Vincoli:
- `CHECK (ended_at IS NULL OR ended_at >= started_at)`
- `CHECK (duration_minutes_declared IS NULL OR duration_minutes_declared >= 0)`
- `CHECK (duration_minutes_calculated IS NULL OR duration_minutes_calculated >= 0)`

Indici:
- `idx_operator_activity_operator_user_id`
- `idx_operator_activity_team_id`
- `idx_operator_activity_vehicle_id`
- `idx_operator_activity_status`
- `idx_operator_activity_started_at`
- `idx_operator_activity_activity_catalog_id`
- `idx_operator_activity_offline_client_uuid`

## 7.3 `operator_activity_event`
Storico eventi di workflow dell'attività.

| Campo | Tipo | Vincoli |
|---|---|---|
| id | UUID | PK |
| operator_activity_id | UUID | FK NOT NULL |
| event_type | VARCHAR(50) | NOT NULL |
| event_at | TIMESTAMPTZ | NOT NULL |
| actor_user_id | UUID | FK NULL |
| payload_json | JSONB | NULL |
| notes | TEXT | NULL |
| created_at | TIMESTAMPTZ | NOT NULL |
| updated_at | TIMESTAMPTZ | NOT NULL |

Indici:
- `idx_operator_activity_event_activity_id`
- `idx_operator_activity_event_event_type`
- `idx_operator_activity_event_event_at`

## 7.4 `operator_activity_attachment`
Allegati direttamente collegati all'attività.

| Campo | Tipo | Vincoli |
|---|---|---|
| id | UUID | PK |
| operator_activity_id | UUID | FK NOT NULL |
| attachment_id | UUID | FK NOT NULL |
| created_at | TIMESTAMPTZ | NOT NULL |
| updated_at | TIMESTAMPTZ | NOT NULL |

Unique:
- `(operator_activity_id, attachment_id)`

## 7.5 `gps_track_summary`
Riepilogo del tracciato GPS associabile a sessioni mezzo o attività.

| Campo | Tipo | Vincoli | Note |
|---|---|---|---|
| id | UUID | PK | |
| source_type | VARCHAR(30) | NOT NULL | device_app / vehicle_provider / derived |
| provider_name | VARCHAR(100) | NULL | |
| provider_track_id | VARCHAR(100) | NULL | id esterno |
| started_at | TIMESTAMPTZ | NOT NULL | |
| ended_at | TIMESTAMPTZ | NULL | |
| start_latitude | NUMERIC(10,7) | NULL | |
| start_longitude | NUMERIC(10,7) | NULL | |
| end_latitude | NUMERIC(10,7) | NULL | |
| end_longitude | NUMERIC(10,7) | NULL | |
| total_distance_km | NUMERIC(12,3) | NULL | |
| total_duration_seconds | INTEGER | NULL | |
| raw_payload_json | JSONB | NULL | payload provider/app |
| created_at | TIMESTAMPTZ | NOT NULL | |
| updated_at | TIMESTAMPTZ | NOT NULL | |

Indici:
- `idx_gps_track_summary_source_type`
- `idx_gps_track_summary_provider_track_id`
- `idx_gps_track_summary_started_at`

---

# 8. Schema relazionale – area segnalazioni e pratiche

## 8.1 `field_report_category`
Categorie segnalazioni.

| Campo | Tipo | Vincoli |
|---|---|---|
| id | UUID | PK |
| code | VARCHAR(50) | UNIQUE NOT NULL |
| name | VARCHAR(150) | NOT NULL |
| description | TEXT | NULL |
| is_active | BOOLEAN | NOT NULL DEFAULT TRUE |
| sort_order | INTEGER | NOT NULL DEFAULT 0 |
| created_at | TIMESTAMPTZ | NOT NULL |
| updated_at | TIMESTAMPTZ | NOT NULL |

## 8.2 `field_report_severity`
Gradi/priorità della segnalazione.

| Campo | Tipo | Vincoli |
|---|---|---|
| id | UUID | PK |
| code | VARCHAR(50) | UNIQUE NOT NULL |
| name | VARCHAR(100) | NOT NULL |
| rank_order | INTEGER | NOT NULL |
| color_hex | VARCHAR(7) | NULL |
| is_active | BOOLEAN | NOT NULL DEFAULT TRUE |
| created_at | TIMESTAMPTZ | NOT NULL |
| updated_at | TIMESTAMPTZ | NOT NULL |

## 8.3 `field_report`
Segnalazione generata dall'operatore. Genera sempre una pratica.
Dal 2026-04-10 supporta anche import da sistema esterno White Company con codice sorgente, segnalatore testuale, area irrigua e tempi di completamento.

| Campo | Tipo | Vincoli | Note |
|---|---|---|---|
| id | UUID | PK | |
| report_number | VARCHAR(50) | UNIQUE NOT NULL | numerazione interna |
| external_code | VARCHAR(50) | UNIQUE NULL | codice sorgente White |
| reporter_user_id | UUID | FK -> application_user(id) NOT NULL | |
| team_id | UUID | FK NULL | |
| vehicle_id | UUID | FK NULL | |
| operator_activity_id | UUID | FK NULL | segnalazione da attività |
| category_id | UUID | FK NOT NULL | |
| severity_id | UUID | FK NOT NULL | |
| title | VARCHAR(200) | NOT NULL | |
| description | TEXT | NULL | |
| reporter_name | VARCHAR(200) | NULL | segnalatore testuale esterno |
| area_code | VARCHAR(200) | NULL | distretto irriguo / area libera |
| latitude | NUMERIC(10,7) | NULL | |
| longitude | NUMERIC(10,7) | NULL | |
| assigned_responsibles | TEXT | NULL | CSV responsabili importati |
| completion_time_text | VARCHAR(200) | NULL | testo originale White |
| completion_time_minutes | INTEGER | NULL | valore normalizzato per ordinamenti/KPI |
| source_system | VARCHAR(50) | NULL DEFAULT 'gaia' | `gaia` oppure `white` |
| gps_accuracy_meters | NUMERIC(10,2) | NULL | |
| gps_source | VARCHAR(30) | NULL | |
| status | VARCHAR(30) | NOT NULL DEFAULT 'submitted' | submitted/linked/invalidated |
| offline_client_uuid | UUID | NULL | dedup sync |
| client_created_at | TIMESTAMPTZ | NULL | |
| server_received_at | TIMESTAMPTZ | NULL | |
| internal_case_id | UUID | UNIQUE NULL | pratica generata |
| created_at | TIMESTAMPTZ | NOT NULL | |
| updated_at | TIMESTAMPTZ | NOT NULL | |
| created_by_user_id | UUID | FK NULL | |
| updated_by_user_id | UUID | FK NULL | |

Indici:
- `idx_field_report_reporter_user_id`
- `idx_field_report_category_id`
- `idx_field_report_severity_id`
- `idx_field_report_vehicle_id`
- `idx_field_report_operator_activity_id`
- `idx_field_report_created_at`
- `idx_field_report_offline_client_uuid`
- `idx_field_report_external_code`
- `idx_field_report_area_code`

## 8.4 `field_report_attachment`
Allegati della segnalazione.

| Campo | Tipo | Vincoli |
|---|---|---|
| id | UUID | PK |
| field_report_id | UUID | FK NOT NULL |
| attachment_id | UUID | FK NOT NULL |
| created_at | TIMESTAMPTZ | NOT NULL |
| updated_at | TIMESTAMPTZ | NOT NULL |

Unique:
- `(field_report_id, attachment_id)`

## 8.5 `internal_case`
Pratica interna generata sempre da una segnalazione.

| Campo | Tipo | Vincoli | Note |
|---|---|---|---|
| id | UUID | PK | |
| case_number | VARCHAR(50) | UNIQUE NOT NULL | |
| source_report_id | UUID | FK UNIQUE NOT NULL | 1:1 con field_report |
| title | VARCHAR(200) | NOT NULL | |
| description | TEXT | NULL | |
| category_id | UUID | FK NULL | ridondanza utile per query |
| severity_id | UUID | FK NULL | ridondanza utile per query |
| status | VARCHAR(30) | NOT NULL DEFAULT 'open' | |
| assigned_to_user_id | UUID | FK NULL | assegnatario diretto |
| assigned_team_id | UUID | FK NULL | assegnazione a squadra |
| acknowledged_at | TIMESTAMPTZ | NULL | presa visione |
| started_at | TIMESTAMPTZ | NULL | in lavorazione |
| resolved_at | TIMESTAMPTZ | NULL | |
| closed_at | TIMESTAMPTZ | NULL | |
| resolution_note | TEXT | NULL | |
| closed_by_user_id | UUID | FK NULL | |
| priority_rank | INTEGER | NULL | denormalizzato/opzionale |
| created_at | TIMESTAMPTZ | NOT NULL | |
| updated_at | TIMESTAMPTZ | NOT NULL | |
| created_by_user_id | UUID | FK NULL | |
| updated_by_user_id | UUID | FK NULL | |

Indici:
- `idx_internal_case_status`
- `idx_internal_case_assigned_to_user_id`
- `idx_internal_case_assigned_team_id`
- `idx_internal_case_created_at`
- `idx_internal_case_severity_id`

## 8.6 `internal_case_event`
Storico eventi della pratica.

| Campo | Tipo | Vincoli |
|---|---|---|
| id | UUID | PK |
| internal_case_id | UUID | FK NOT NULL |
| event_type | VARCHAR(50) | NOT NULL |
| event_at | TIMESTAMPTZ | NOT NULL |
| actor_user_id | UUID | FK NULL |
| payload_json | JSONB | NULL |
| note | TEXT | NULL |
| created_at | TIMESTAMPTZ | NOT NULL |
| updated_at | TIMESTAMPTZ | NOT NULL |

Indici:
- `idx_internal_case_event_case_id`
- `idx_internal_case_event_event_type`

Event type aggiunti per import White:
- `imported`
- `richiesta_intervento`
- `richiesta_materiale`
- `assegnazione_incaricato`
- `riparazione_eseguita`
- `sopralluogo`
- `contestazione_utente`
- `idx_internal_case_event_event_at`

## 8.7 `internal_case_attachment`
Allegati aggiuntivi della pratica, anche successivi alla segnalazione iniziale.

| Campo | Tipo | Vincoli |
|---|---|---|
| id | UUID | PK |
| internal_case_id | UUID | FK NOT NULL |
| attachment_id | UUID | FK NOT NULL |
| uploaded_by_user_id | UUID | FK NULL |
| created_at | TIMESTAMPTZ | NOT NULL |
| updated_at | TIMESTAMPTZ | NOT NULL |

## 8.8 `internal_case_assignment_history`
Storico assegnazioni pratica.

| Campo | Tipo | Vincoli |
|---|---|---|
| id | UUID | PK |
| internal_case_id | UUID | FK NOT NULL |
| assigned_to_user_id | UUID | FK NULL |
| assigned_team_id | UUID | FK NULL |
| assigned_by_user_id | UUID | FK NOT NULL |
| assigned_at | TIMESTAMPTZ | NOT NULL |
| unassigned_at | TIMESTAMPTZ | NULL |
| note | TEXT | NULL |
| created_at | TIMESTAMPTZ | NOT NULL |
| updated_at | TIMESTAMPTZ | NOT NULL |

---

# 9. Schema relazionale – area allegati e storage

## 9.1 `attachment`
Archivio centralizzato degli allegati del modulo Operazioni.

| Campo | Tipo | Vincoli | Note |
|---|---|---|---|
| id | UUID | PK | |
| storage_path | TEXT | UNIQUE NOT NULL | path fisico/logico |
| original_filename | VARCHAR(255) | NOT NULL | |
| mime_type | VARCHAR(100) | NOT NULL | |
| extension | VARCHAR(20) | NULL | |
| attachment_type | VARCHAR(20) | NOT NULL | image/audio/video/document |
| file_size_bytes | BIGINT | NOT NULL | |
| checksum_sha256 | VARCHAR(64) | NULL | |
| width_px | INTEGER | NULL | immagini/video |
| height_px | INTEGER | NULL | immagini/video |
| duration_seconds | NUMERIC(10,2) | NULL | audio/video |
| was_compressed | BOOLEAN | NOT NULL DEFAULT FALSE | |
| compression_status | VARCHAR(30) | NOT NULL DEFAULT 'uploaded' | |
| uploaded_by_user_id | UUID | FK NULL | |
| source_context | VARCHAR(50) | NOT NULL | activity/report/case/vehicle |
| source_entity_id | UUID | NULL | riferimento logico opzionale |
| is_deleted | BOOLEAN | NOT NULL DEFAULT FALSE | |
| deleted_at | TIMESTAMPTZ | NULL | |
| metadata_json | JSONB | NULL | |
| created_at | TIMESTAMPTZ | NOT NULL | |
| updated_at | TIMESTAMPTZ | NOT NULL | |

Vincoli:
- `CHECK (file_size_bytes >= 0)`

Indici:
- `idx_attachment_attachment_type`
- `idx_attachment_created_at`
- `idx_attachment_source_context`
- `idx_attachment_source_entity_id`
- `idx_attachment_is_deleted`

## 9.2 `storage_quota_metric`
Metriche periodiche di occupazione.

| Campo | Tipo | Vincoli |
|---|---|---|
| id | UUID | PK |
| measured_at | TIMESTAMPTZ | NOT NULL |
| total_bytes_used | BIGINT | NOT NULL |
| quota_bytes | BIGINT | NOT NULL |
| percentage_used | NUMERIC(5,2) | NOT NULL |
| created_at | TIMESTAMPTZ | NOT NULL |
| updated_at | TIMESTAMPTZ | NOT NULL |

## 9.3 `storage_quota_alert`
Alert soglie storage.

| Campo | Tipo | Vincoli |
|---|---|---|
| id | UUID | PK |
| alert_level | VARCHAR(20) | NOT NULL |
| threshold_percentage | NUMERIC(5,2) | NOT NULL |
| triggered_at | TIMESTAMPTZ | NOT NULL |
| resolved_at | TIMESTAMPTZ | NULL |
| metric_id | UUID | FK NOT NULL |
| note | TEXT | NULL |
| created_at | TIMESTAMPTZ | NOT NULL |
| updated_at | TIMESTAMPTZ | NOT NULL |

Valori suggeriti `alert_level`:
- `warning_70`
- `warning_85`
- `critical_95`
- `quota_exceeded`

---

# 10. Schema relazionale – area approvazioni

## 10.1 `activity_approval`
Registro approvazioni delle attività.

| Campo | Tipo | Vincoli |
|---|---|---|
| id | UUID | PK |
| operator_activity_id | UUID | FK NOT NULL |
| reviewer_user_id | UUID | FK NOT NULL |
| decision | VARCHAR(30) | NOT NULL |
| decision_at | TIMESTAMPTZ | NOT NULL |
| note | TEXT | NULL |
| payload_json | JSONB | NULL |
| created_at | TIMESTAMPTZ | NOT NULL |
| updated_at | TIMESTAMPTZ | NOT NULL |

Indici:
- `idx_activity_approval_operator_activity_id`
- `idx_activity_approval_reviewer_user_id`
- `idx_activity_approval_decision_at`

---

# 11. Relazioni chiave

## 11.1 Mezzi
- `vehicle 1 -> N vehicle_assignment`
- `vehicle 1 -> N vehicle_usage_session`
- `vehicle 1 -> N vehicle_fuel_log`
- `vehicle 1 -> N vehicle_maintenance`
- `vehicle 1 -> N vehicle_document`
- `vehicle 1 -> N vehicle_odometer_reading`

## 11.2 Attività
- `activity_catalog 1 -> N operator_activity`
- `operator_activity 1 -> N operator_activity_event`
- `operator_activity 1 -> N operator_activity_attachment`
- `operator_activity N -> 1 vehicle` opzionale

## 11.3 Segnalazioni / pratiche
- `field_report_category 1 -> N field_report`
- `field_report_severity 1 -> N field_report`
- `field_report 1 -> 1 internal_case`
- `internal_case 1 -> N internal_case_event`
- `internal_case 1 -> N internal_case_assignment_history`
- `field_report 1 -> N field_report_attachment`
- `internal_case 1 -> N internal_case_attachment`

## 11.4 Allegati
- `attachment` è riusabile tramite tabelle ponte

---

# 12. Vincoli applicativi importanti

## 12.1 Sessione mezzo aperta unica
Un mezzo non deve avere più di una `vehicle_usage_session` aperta contemporaneamente.

Implementazione:
- controllo applicativo in service layer
- opzionale partial unique index su stato aperto se modellato in modo compatibile

## 12.2 Una segnalazione genera sempre una pratica
`field_report.internal_case_id` e `internal_case.source_report_id` devono mantenere un mapping 1:1.

## 12.3 Dedup offline
Per `operator_activity` e `field_report` usare `offline_client_uuid` con indice per deduplicare ritrasmissioni.

## 12.4 Stati approvazione attività
Solo il capo o utente autorizzato può creare una `activity_approval` finale.

## 12.5 Audit immutabile logico
Eventi in `*_event` non devono essere aggiornati a livello di business, solo inseriti.

---

# 13. Strategia storage allegati

Consigliata archiviazione file system o object storage, non BLOB in DB.

Path logico suggerito:

```text
/storage/operazioni/
  attachments/
    2026/
      04/
        <uuid>_<filename>
```

Il DB conserva:
- path
- metadata
- checksum
- dimensioni
- durata
- stato compressione

---

# 14. Migrazioni Alembic – ordine suggerito

1. lookup organizzative (`team`, `operator_profile`)
2. anagrafica mezzi (`vehicle`, `vehicle_assignment`)
3. sessioni e log mezzi
4. catalogo attività e attività operative
5. categorie segnalazioni e gravità
6. `attachment`
7. `field_report`
8. `internal_case`
9. tabelle evento/ponte/approval
10. metriche storage

---

# 15. DDL SQL – esempio base PostgreSQL

## 15.1 Esempio `vehicle`

```sql
CREATE TABLE vehicle (
    id UUID PRIMARY KEY,
    code VARCHAR(50) NOT NULL UNIQUE,
    plate_number VARCHAR(20) UNIQUE,
    asset_tag VARCHAR(100) UNIQUE,
    name VARCHAR(150) NOT NULL,
    vehicle_type VARCHAR(100) NOT NULL,
    brand VARCHAR(100),
    model VARCHAR(100),
    year_of_manufacture INTEGER,
    fuel_type VARCHAR(50),
    current_status VARCHAR(50) NOT NULL DEFAULT 'available',
    ownership_type VARCHAR(50),
    notes TEXT,
    gps_provider_code VARCHAR(100),
    has_gps_device BOOLEAN NOT NULL DEFAULT FALSE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    created_by_user_id UUID,
    updated_by_user_id UUID
);

CREATE INDEX idx_vehicle_name ON vehicle(name);
CREATE INDEX idx_vehicle_current_status ON vehicle(current_status);
CREATE INDEX idx_vehicle_vehicle_type ON vehicle(vehicle_type);
```

## 15.2 Esempio `operator_activity`

```sql
CREATE TABLE operator_activity (
    id UUID PRIMARY KEY,
    activity_catalog_id UUID NOT NULL REFERENCES activity_catalog(id),
    operator_user_id UUID NOT NULL REFERENCES application_user(id),
    team_id UUID REFERENCES team(id),
    vehicle_id UUID REFERENCES vehicle(id),
    vehicle_usage_session_id UUID REFERENCES vehicle_usage_session(id),
    status VARCHAR(30) NOT NULL DEFAULT 'draft',
    started_at TIMESTAMPTZ NOT NULL,
    ended_at TIMESTAMPTZ,
    duration_minutes_declared INTEGER,
    duration_minutes_calculated INTEGER,
    start_latitude NUMERIC(10,7),
    start_longitude NUMERIC(10,7),
    end_latitude NUMERIC(10,7),
    end_longitude NUMERIC(10,7),
    gps_track_summary_id UUID REFERENCES gps_track_summary(id),
    text_note TEXT,
    audio_note_attachment_id UUID REFERENCES attachment(id),
    submitted_at TIMESTAMPTZ,
    reviewed_by_user_id UUID REFERENCES application_user(id),
    reviewed_at TIMESTAMPTZ,
    review_outcome VARCHAR(30),
    review_note TEXT,
    rectified_from_activity_id UUID REFERENCES operator_activity(id),
    offline_client_uuid UUID,
    client_created_at TIMESTAMPTZ,
    server_received_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    created_by_user_id UUID,
    updated_by_user_id UUID,
    CHECK (ended_at IS NULL OR ended_at >= started_at),
    CHECK (duration_minutes_declared IS NULL OR duration_minutes_declared >= 0),
    CHECK (duration_minutes_calculated IS NULL OR duration_minutes_calculated >= 0)
);

CREATE INDEX idx_operator_activity_operator_user_id ON operator_activity(operator_user_id);
CREATE INDEX idx_operator_activity_status ON operator_activity(status);
CREATE INDEX idx_operator_activity_started_at ON operator_activity(started_at);
CREATE INDEX idx_operator_activity_offline_client_uuid ON operator_activity(offline_client_uuid);
```

## 15.3 Esempio `field_report`

```sql
CREATE TABLE field_report (
    id UUID PRIMARY KEY,
    report_number VARCHAR(50) NOT NULL UNIQUE,
    reporter_user_id UUID NOT NULL REFERENCES application_user(id),
    team_id UUID REFERENCES team(id),
    vehicle_id UUID REFERENCES vehicle(id),
    operator_activity_id UUID REFERENCES operator_activity(id),
    category_id UUID NOT NULL REFERENCES field_report_category(id),
    severity_id UUID NOT NULL REFERENCES field_report_severity(id),
    title VARCHAR(200) NOT NULL,
    description TEXT,
    latitude NUMERIC(10,7),
    longitude NUMERIC(10,7),
    gps_accuracy_meters NUMERIC(10,2),
    gps_source VARCHAR(30),
    status VARCHAR(30) NOT NULL DEFAULT 'submitted',
    offline_client_uuid UUID,
    client_created_at TIMESTAMPTZ,
    server_received_at TIMESTAMPTZ,
    internal_case_id UUID UNIQUE,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    created_by_user_id UUID,
    updated_by_user_id UUID
);
```

---

# 16. Raccomandazioni implementative finali

- usare UUID lato backend come PK per tutte le nuove tabelle
- usare `JSONB` solo per payload dinamici, non per dati core
- evitare enum PostgreSQL per stati che potrebbero evolvere spesso
- tracciare sempre `offline_client_uuid` per mobile sync
- separare allegati da entità core con tabella `attachment`
- generare numerazioni `report_number` e `case_number` lato backend
- pianificare job periodico per `storage_quota_metric`

---

# 17. Output atteso per sviluppo

Questo schema DB è pensato per essere usato come base per:
- modelli SQLAlchemy
- migrazioni Alembic
- repository/service layer FastAPI
- API REST del modulo Operazioni
