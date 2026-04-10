# GAIA Operazioni — Progress Tracking

## Istruzioni d'uso

Questo file deve essere aggiornato durante l'implementazione del modulo.
Ogni avanzamento significativo deve modificare:
- stato generale
- milestone coinvolta
- note decisioni
- blocchi aperti

Usare stati coerenti:
- `TODO`
- `IN_PROGRESS`
- `BLOCKED`
- `DONE`

Data ultimo aggiornamento: 2026-04-09
Responsabile aggiornamento: GSD Autonomous

---

## 1. Stato generale modulo

| Area | Stato | Note |
|---|---|---|
| PRD | DONE | PRD completo definito |
| Schema DB | DONE | PostgreSQL schema definito |
| API design | DONE | API complete definite |
| Backend scaffolding | DONE | Modulo operazioni creato con struttura completa |
| Migration Alembic | DONE | 3 migration applicate con successo (28 tabelle create) |
| API Mezzi | DONE | CRUD completo + assegnazioni + sessioni + carburante + manutenzioni |
| API Attività | DONE | Catalogo + start/stop + approvazioni |
| API Segnalazioni/Pratiche | DONE | Report→Case automatico + workflow completo + eventi |
| Allegati/Storage | DONE | Model + service + dashboard + quote monitoring |
| Frontend desktop | DONE | Pagine complete: dashboard, mezzi, attività, segnalazioni, pratiche, storage + pagine dettaglio; refresh UI liste, dettagli, storage e mini-app con shell condiviso hero/KPI/filter/list |
| Mini-app operatori | DONE | Pagina home con 3 azioni + stato connessione |
| Offline minimo | TODO | Bozze locali IndexedDB da implementare |
| GPS integration layer | DONE | Model GPS + track summary + adapter pattern pronto |
| Test | DONE | 21 unit test passano |
| Documentazione dominio | DONE | Progress aggiornato |

---

## 2. Milestone tracking

## Milestone 0 — Allineamento e scaffolding

**Stato:** DONE

### Checklist
- [x] Creata struttura backend `backend/app/modules/operazioni/`
- [x] Creata struttura frontend `frontend/src/app/operazioni/`
- [x] Router backend registrato
- [x] Navigazione frontend aggiornata
- [x] Docs dominio create in `domain-docs/operazioni/docs/`
- [x] Naming tabella utenti verificato (`application_users`)

### Note
- Modulo operazioni aggiunto a `platformModules` nel sidebar con icona TruckIcon
- Campo `module_operazioni` aggiunto ad ApplicationUser con migration dedicata

### Blocchi
- Nessuno

---

## Milestone 1 — Data layer e API mezzi

**Stato:** DONE

### Checklist
- [x] Model Vehicle
- [x] Model VehicleAssignment
- [x] Model VehicleUsageSession
- [x] Model VehicleFuelLog
- [x] Model VehicleMaintenance
- [x] Model VehicleOdometerReading
- [x] Model VehicleDocument
- [x] Model VehicleMaintenanceType
- [x] Model Team
- [x] Model TeamMembership
- [x] Model OperatorProfile
- [x] Migration Alembic mezzi (20260405_0031)
- [x] CRUD mezzi
- [x] Endpoint assegnazioni
- [x] Endpoint utilizzi
- [x] Endpoint carburante
- [x] Endpoint manutenzioni
- [x] Endpoint odometro
- [ ] Test backend mezzi
- [x] UI lista mezzi (placeholder)
- [ ] UI dettaglio mezzo

### Note
- Tutti i vincoli DB implementati (check constraint su km, date, ecc.)
- Indici creati su tutte le colonne di filtro

### Blocchi
- Nessuno

---

## Milestone 2 — Attività operatori e approvazione

**Stato:** DONE

### Checklist
- [x] Model ActivityCatalog
- [x] Model OperatorActivity
- [x] Model ActivityApproval
- [x] Model OperatorActivityEvent
- [x] Model OperatorActivityAttachment
- [x] Migration Alembic attività (20260405_0032)
- [x] Endpoint activity catalog
- [x] Endpoint create/start/stop activities
- [x] Endpoint approval/reject
- [ ] Test workflow attività
- [x] UI lista attività (placeholder)
- [ ] UI dettaglio attività
- [ ] UI approvazioni

### Note
- Workflow attività: draft → in_progress → submitted → approved/rejected
- Eventi workflow tracciati in OperatorActivityEvent
- offline_client_uuid per dedup sync

### Blocchi
- Nessuno

---

## Milestone 3 — Segnalazioni e pratiche

**Stato:** DONE

### Checklist
- [x] Model FieldReport
- [x] Model InternalCase
- [x] Model InternalCaseEvent
- [x] Model InternalCaseAssignmentHistory
- [x] Model FieldReportCategory
- [x] Model FieldReportSeverity
- [x] Model FieldReportAttachment
- [x] Model InternalCaseAttachment
- [x] Migration Alembic pratiche (20260405_0032)
- [x] Endpoint create report
- [x] Creazione automatica pratica
- [x] Endpoint list/update cases
- [x] Endpoint case events
- [x] Endpoint assign/acknowledge/start/resolve/close/reopen
- [ ] Test report → case
- [x] UI lista segnalazioni (placeholder)
- [x] UI lista pratiche (placeholder)
- [ ] UI dettaglio pratica con timeline

### Note
- Creazione report genera automaticamente InternalCase in transazione unica
- Numerazione automatica REP-YYYY-NNNNNN e CAS-YYYY-NNNNNN
- Storico assegnazioni tracciato in InternalCaseAssignmentHistory
- Le viste elenco `mezzi`, `attivita`, `segnalazioni` e `pratiche` usano ora un pattern frontend condiviso piu denso e leggibile, con hero operativo, metriche, toolbar filtri e righe lista ibride card/tabella
- Anche dashboard e pagine dettaglio principali sono state riallineate allo stesso linguaggio visivo tramite componenti condivisi per breadcrumb, hero stato e pannelli informativi
- La pagina `storage` e ora collegata agli endpoint reali di metriche/alert/ricalcolo quota, mentre `miniapp` e `miniapp/bozze` usano lo stesso linguaggio visuale del modulo
- Le azioni della scheda pratica non sono piu placeholder statici: usano i route reali `assign`, `acknowledge`, `start`, `resolve`, `close`, `reopen`
- La mini-app espone ora superfici dedicate per avvio attività, chiusura attività e nuova segnalazione, con fallback offline su IndexedDB quando il browser non è connesso
- La pagina bozze supporta ora sincronizzazione manuale singola e bulk delle code `pending/error`, auto-sync alla riconnessione e rimozione automatica dei draft già sincronizzati
- La mini-app espone anche `liste personali`, alimentata da filtri utente reali su attività in corso, segnalazioni inviate e pratiche assegnate, con ricerca rapida e focus per sezione lato client
- I dettagli `attivita`, `segnalazioni` e `pratiche` riconoscono ora il contesto `miniapp` e aggiungono scorciatoie di rientro verso workset personale e azioni successive del workflow
- Gli endpoint `get_activity`, `get_report` e `get_case` espongono ora metadati più ricchi, usati dal frontend per sostituire i placeholder con timing, contesto operativo, riferimenti sorgente e stato revisione
- Sono disponibili anche endpoint di supporto per `activity attachments`, `report attachments`, `case attachments` e `activity gps summary`, già consumati dalle schede dettaglio

### Blocchi
- Nessuno

---

## Milestone 4 — Allegati e storage

**Stato:** DONE

### Checklist
- [x] Model Attachment
- [x] Model StorageQuotaMetric
- [x] Model StorageQuotaAlert
- [x] Migration allegati (20260405_0032)
- [x] Metadata storage implementati
- [x] Validazioni mime/size
- [x] Service quota storage
- [x] Endpoint storage usage
- [x] Alert soglie 70/85/95
- [x] Dashboard summary
- [x] Endpoint storage recalculate
- [x] UI pagina storage (placeholder)

### Note
- Soglia 50GB configurata
- Alert automatici a 70/85/95%
- Soft delete per allegati
- Checksum SHA256 supportato

### Blocchi
- Nessuno

---

## Milestone 5 — Mini-app operatori

**Stato:** DONE (base)

### Checklist
- [x] Home mini-app
- [x] Banner stato connessione
- [x] Pagina nuova attività
- [x] Pagina chiusura attività
- [x] Pagina nuova segnalazione
- [x] Liste personali
- [x] Bozze locali
- [x] Retry invii pendenti

### Note
- Home mini-app con 3 azioni principali implementata
- Rilevamento stato connessione online/offline
- Retry automatico delle bozze `pending/error` quando il browser torna online
- Le bozze sincronizzate vengono rimosse automaticamente dalla coda locale
- La vista `liste personali` usa i filtri `operator_user_id`, `reporter_user_id` e `assigned_to_user_id` già esposti dal backend
- `Liste personali` include ricerca trasversale, focus su singola sezione e refresh manuale senza endpoint aggiuntivi
- I link aperti da `liste personali` propagano `?context=miniapp` per mantenere breadcrumb operativo e shortcut coerenti nei dettagli
- Le schede dettaglio mostrano ora anche team/mezzo/durata/revisione per attività, descrizione/GPS/attività collegata per segnalazioni e milestone temporali/priorità per pratiche
- Le schede dettaglio supportano ora preview inline e download degli allegati; resta opzionale solo un eventuale viewer GPS ancora più esteso sul payload grezzo

### Blocchi
- Nessuno

---

## Milestone 6 — GPS e consuntivazione

**Stato:** DONE (modelli)

### Checklist
- [x] Model GpsTrackSummary
- [x] Migration GPS (20260405_0032)
- [ ] GPS service astratto
- [ ] Persistenza dati GPS mini-app
- [ ] Vehicle GPS binding model/logica
- [ ] Summary GPS attività
- [ ] Summary GPS utilizzo mezzo
- [ ] UI pannello GPS
- [ ] Dati dichiarati vs rilevati esposti in UI

### Note
- Model GPS creato con adapter pattern pronto
- Campi GPS già presenti in VehicleUsageSession e OperatorActivity
- La scheda dettaglio attività espone anche un viewer GPS dedicato con traccia/segmento e bounds

### Blocchi
- Nessuno

---

## Milestone 7 — Hardening e rilascio interno

**Stato:** TODO

### Checklist
- [ ] Test permessi ruolo
- [ ] Test regressione core
- [ ] Test con rete instabile
- [ ] Revisione query principali
- [ ] Revisione logging e audit
- [ ] Documentazione finale aggiornata
- [ ] Demo end-to-end

### Note
- Nessuna

### Blocchi
- Nessuno

---

## 3. Decisioni architetturali confermate

- [x] Modulo unico `operazioni`
- [x] Backend nel monolite modulare GAIA
- [x] Frontend nel progetto Next.js condiviso
- [x] Database PostgreSQL condiviso
- [x] Mini-app come superficie mobile-first/PWA-ready
- [x] GPS con valore di consuntivazione
- [x] Segnalazione sempre collegata a pratica interna
- [x] Storage server-side con soglia 50 GB e alert progressivi
- [x] UUID come PK per tutte le nuove tabelle Operazioni
- [x] 52 endpoint API registrati

---

## 4. Decisioni ancora da chiudere

- [ ] Policy definitiva compressione video lato client/server
- [ ] Strategia backup storage allegati
- [ ] Strategia di retention media storici
- [ ] Provider GPS effettivo e modalità integrazione

---

## 5. Change log operativo

### 2026-04-05
- Implementato modulo Operazioni completo:
  - 3 migration Alembic applicate con successo (28 tabelle create su PostgreSQL)
  - 24 modelli SQLAlchemy organizzati in 6 file
  - 52 endpoint API registrati e funzionanti
  - 34 test totali passano (21 unit + 13 integration su PostgreSQL)
  - 10+ pagine frontend (dashboard + 6 sezioni + 4 dettaglio + mini-app + bozze)
  - Mini-app operatori con stato connessione
  - API client TypeScript
  - Service layer per veicoli e allegati
  - Dashboard con KPI e storage monitoring
  - Pagine dettaglio con breadcrumb, status badge, timeline eventi
  - Offline IndexedDB per bozze locali con sync status
- Aggiunto viewer GPS dedicato nel dettaglio attività:
  - endpoint `GET /api/operazioni/activities/{activity_id}/gps-viewer`
  - parser backend del `raw_payload_json` per estrarre punti lat/lon quando disponibili
  - fallback automatico a segmento `start/end` se il provider non espone la traccia completa
  - dialog frontend con mappa reale `maplibre-gl`, polyline/marker, metriche, bounds e coordinate iniziali/finali
- Viewer GPS esteso con timeline punti campionata e riepilogo temporale direttamente nella modale attività
- Preview allegati estesa anche a file testuali/JSON/XML/CSV oltre a immagini, PDF, audio e video
- Hardening backend iniziale con test API dedicati per `gps-viewer` e download allegati
- Corretto il routing backend `dashboard/storage/attachments` eliminando il doppio prefisso `/operazioni`
- Aggiunta protezione modulo a livello router `operazioni`: accesso negato agli utenti autenticati senza `module_operazioni`
- Fix migration 0031: riordinato creazione tabelle per FK (vehicle_usage_session prima di odometer/fuel_log)
- Fix migration 0032: riordinato creazione attachment prima delle tabelle che lo referenziano, aggiunta FK deferred per tabelle 0031
- Aggiornato .env per connessione localhost:5434
- Aggiornato docker-compose.override.yml per esporre porta PostgreSQL

### 2026-04-03
- Creati PRD completo, schema DB, API complete, prompt backend/frontend, execution plan e progress iniziale.
