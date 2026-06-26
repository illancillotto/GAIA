# Piano Implementazione

> Regola di implementazione
> Il modulo self-service utente va introdotto come dominio dedicato e leggero, che orchestra dati gia presenti in `presenze`, `operazioni` e `network` senza duplicare logica di business.

## 1. Obiettivo Operativo

Creare un modulo `me` che permetta a ogni utente di consultare in autonomia la propria operativita quotidiana, le presenze, i mezzi utilizzati, i km percorsi, le segnalazioni create e le dotazioni assegnate.

## 2. Namespace Canonico

### Backend

```text
backend/app/modules/me/
  __init__.py
  router.py
  schemas.py
  services/
    summary_service.py
    presenze_service.py
    operazioni_service.py
    assets_service.py
```

### Frontend

```text
frontend/src/app/me/
  page.tsx
  layout.tsx

frontend/src/components/me/
frontend/src/lib/me-api.ts
```

### Documentazione

```text
domain-docs/utente/docs/
```

## 3. Strategia Tecnica

Il modulo `me` non deve diventare un secondo dominio applicativo pieno.

Deve invece:

- esporre endpoint self-service ad alto valore
- comporre dati da moduli esistenti
- applicare filtri di ownership e autorizzazione centralizzati
- ridurre la logica nel frontend

## 4. Fasi

### Fase 1. Fondazioni e Permessi

- introdurre il modulo runtime `me`
- decidere il modello di abilitazione:
  - flag dedicato `module_me`
  - oppure abilitazione implicita per tutti gli utenti attivi
- aggiungere route `/me`
- aggiornare sidebar e navigazione

Deliverable:

- route backend e frontend vuote ma protette
- accesso solo utenti autenticati attivi

Stato 06/06/2026: completata

### Fase 2. Correzione Perimetro Presenze Self-Service

- introdurre servizi o endpoint dedicati self-service Presenze
- filtrare i dati Presenze per `application_user_id == current_user.id`
- non riusare in modo ambiguo le sole logiche admin fondate su `owner_user_id`

Attivita tecniche:

- aggiungere endpoint tipo:
  - `GET /me/presenze/summary`
  - `GET /me/presenze/daily-records`
  - `GET /me/presenze/daily-records/{id}`
- riusare serializer esistenti di `presenze` dove possibile

Rischio da gestire:

- utenti non ancora mappati a collaboratore Presenze

Fallback:

- stato informativo chiaro: "profilo Presenze non ancora associato"

Stato 06/06/2026: completata

### Fase 3. Aggregazione Operazioni Personali

- introdurre endpoint self-service per dati operativi:
  - attivita
  - segnalazioni
  - pratiche assegnate
  - mezzi usati
  - km percorsi

Attivita tecniche:

- servizio backend che compone:
  - `OperatorActivity`
  - `FieldReport`
  - `InternalCase`
  - `VehicleUsageSession`
  - eventuali `VehicleFuelLog` se utili

Endpoint target:

- `GET /me/operazioni/summary`
- `GET /me/operazioni/activities`
- `GET /me/operazioni/reports`
- `GET /me/operazioni/cases`
- `GET /me/operazioni/vehicle-sessions`

Stato 06/06/2026: completata

### Fase 4. Dotazioni Personali

- esporre elenco dispositivi assegnati all'utente
- opzionalmente esporre anche eventuale storico minimo o stato ultimo visto

Endpoint target:

- `GET /me/assets/devices`
- `GET /me/assets/vehicle-assignments`

Fonte:

- modulo `network`

Stato 06/06/2026: completata

### Fase 5. Dashboard Aggregata

- creare endpoint dashboard unico con KPI di periodo

Endpoint target:

- `GET /me/summary?from=YYYY-MM-DD&to=YYYY-MM-DD`

Payload suggerito:

- ore ordinarie
- straordinari
- giorni con anomalie
- km percorsi
- mezzi usati
- attivita concluse
- segnalazioni create
- pratiche aperte/assegnate
- numero dispositivi assegnati

Stato 06/06/2026: completata

### Fase 6. Frontend `/me`

- creare una pagina con hero, KPI e tab principali
- tab:
  - `Panoramica`
  - `Presenze`
  - `Operativita`
  - `Dotazioni`

Linee guida UI:

- evitare look amministrativo
- priorita alla leggibilita personale
- timeline, card sintetiche e calendario
- period filter semplice e visibile

Stato 06/06/2026: completata

### Fase 7. Export e Storico

- aggiungere export periodo
- aggiungere periodi rapidi:
  - mese corrente
  - mese precedente
- export CSV client-side per presenze, operativita e dotazioni
- export XLSX client-side per presenze, operativita e dotazioni
- valutare PDF e XLSX in iterazione successiva

Stato 06/06/2026: completata in forma leggera

### Fase 8. Test e Hardening Autorizzativo

- testare che gli endpoint `me` restino scoped allo user corrente
- verificare comportamento con moduli non abilitati
- misurare copertura del namespace

Stato 06/06/2026: completata

Esito:

- test backend mirati verdi
- copertura `backend/app/modules/me`: `94%` totale package, `89%` router

### Fase 9. Rifiniture UX e Rollout

- allineare la sidebar locale del modulo
- rendere coerenti hash route e navigazione interna
- aggiornare PRD e piano implementativo
- aggiungere vista dedicata `Anomalie`
- estendere i preset periodo a trimestre e anno

Stato 06/06/2026: completata

## 5. Schema Endpoint Proposto

### Backend `me`

- `GET /me`
  - stato modulo e capability correnti
- `GET /me/summary`
  - KPI aggregati dashboard
- `GET /me/presenze/summary`
  - riepilogo presenze periodo
- `GET /me/presenze/daily-records`
  - elenco giornaliere
- `GET /me/presenze/daily-records/{record_id}`
  - dettaglio giornata
- `GET /me/operazioni/summary`
  - KPI operativi personali
- `GET /me/operazioni/activities`
  - elenco attivita personali
- `GET /me/operazioni/reports`
  - elenco segnalazioni create
- `GET /me/operazioni/cases`
  - elenco pratiche assegnate o collegate
- `GET /me/operazioni/vehicle-sessions`
  - mezzi usati e km
- `GET /me/assets/devices`
  - dispositivi assegnati
- `GET /me/assets/vehicle-assignments`
  - assegnazioni mezzo personali

## 6. Scelte Dati e Ownership

### 6.1 Fonte di verita Presenze

Usare:

- `PresenzeCollaborator.application_user_id`
- `PresenzeDailyRecord.application_user_id`
- `PresenzeEventSummary.application_user_id`

Non usare come criterio self-service primario:

- `owner_user_id`

`owner_user_id` puo restare utile per workflow gestionali o di caposettore.

### 6.2 Fonte di verita Operazioni

Usare:

- `OperatorActivity.operator_user_id`
- `FieldReport.reporter_user_id`
- `InternalCase.assigned_to_user_id` dove disponibile nelle API esistenti
- `VehicleUsageSession.actual_driver_user_id`

Fallback da gestire con cautela:

- sessioni legacy con solo `operator_name`

### 6.3 Fonte di verita Dotazioni

Usare:

- `NetworkDevice.assigned_user_id`

## 7. Testing

### Backend

Aggiungere test per:

- un utente vede solo i propri record `Presenze`
- un utente senza mapping Presenze riceve risposta vuota coerente
- un utente vede solo le proprie attivita e segnalazioni
- un utente non puo interrogare dati di un altro tramite parametri arbitrari
- dashboard summary aggrega correttamente KPI base
- device e assegnazioni mezzo sono filtrati sul solo utente corrente

### Frontend

Verificare:

- caricamento pagina `/me`
- stati vuoti chiari
- gestione utente senza dati Presenze
- coerenza filtri periodo
- typecheck con export CSV e nuovi tab

## 8. Rischi Tecnici

- mapping Presenze incompleto
- inconsistenze tra ore Presenze e ore Operazioni
- record mezzi legacy non associati bene all'utente
- rischio di duplicare query costose se non si introduce un service layer pulito

## 9. Consuntivo Implementazione

File chiave realizzati o estesi:

- `backend/app/modules/me/router.py`
- `backend/app/modules/me/schemas.py`
- `frontend/src/app/me/page.tsx`
- `frontend/src/lib/api.ts`
- `frontend/src/types/api.ts`
- `frontend/src/components/layout/module-sidebar.tsx`
- `backend/tests/test_presenze_api.py`

Verifiche eseguite:

- `pytest -q backend/tests/test_presenze_api.py -k "me_ or application_mapping or owner_scope"`
- `pytest --cov=backend/app/modules/me --cov-report=term-missing -q backend/tests/test_presenze_api.py -k "me_"`
- `npm run typecheck`

## 10. Sequenza Raccomandata

1. creare namespace `me`
2. definire schema API del modulo
3. correggere il perimetro Inaz self-service
4. aggiungere servizi backend aggregati
5. implementare dashboard `/me`
6. implementare tab Presenze
7. implementare tab Operativita
8. implementare tab Dotazioni
9. chiudere con export e test di regressione

## 11. Deliverable Attesi

- modulo backend `me` funzionante
- route frontend `/me`
- dashboard personale
- consultazione giornaliere Inaz personali
- consultazione operativita personale
- vista dotazioni assegnate
- test backend sui confini autorizzativi
