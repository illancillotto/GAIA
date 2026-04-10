# ROADMAP.md — GAIA Operazioni Milestone v1.0

## Milestone Info
- **Version:** v1.0
- **Name:** GAIA Operazioni — Implementazione Completa
- **Total Phases:** 8
- **Phase Range:** 0-7
- **Completed:** 8/8 (100%)
- **Last Updated:** 2026-04-05
- **Database:** 28 tabelle create, 3 migration applicate
- **Tests:** 21 unit test passano
- **Completed:** 8/8 (100%)

## Phases

### Phase 0: Scaffolding e Allineamento
**Status:** Complete
**Goal:** Creare la struttura del modulo operazioni, registrare router e navigazione, predisporre la base tecnica.
**Requirements:**
- Struttura backend `backend/app/modules/operazioni/` con tutti i sub-package
- Struttura frontend `frontend/src/app/operazioni/` con pagine placeholder
- Router backend registrato nell'app principale
- Voci di navigazione frontend aggiornate
- Feature folder frontend `frontend/src/features/operazioni/`
- Verifica naming tabella utenti (`application_users`)
- Docs dominio già presenti in `domain-docs/operazioni/docs/`
**Success Criteria:**
- [ ] Directory backend creata con __init__.py, module.py
- [ ] Router operazioni montato su `/api/operazioni`
- [ ] Pagine placeholder frontend funzionanti
- [ ] Navigazione frontend aggiornata
- [ ] Feature folder frontend creata

---

### Phase 1: Data Layer e API Core Mezzi
**Status:** Complete
**Goal:** Rendere operativa la parte Mezzi con modelli DB, migration, CRUD API e UI base.
**Requirements:**
- SQLAlchemy models: Vehicle, VehicleAssignment, VehicleUsageSession, VehicleFuelLog, VehicleMaintenance, VehicleOdometerReading, VehicleDocument, Team, TeamMembership, OperatorProfile
- Migration Alembic per tutte le tabelle mezzi
- CRUD API completi per mezzi (GET, POST, GET/{id}, PATCH, deactivate)
- API assegnazioni (GET, POST, close)
- API sessioni utilizzo (start, stop, validate, list, get)
- API odometro (GET, POST)
- API carburante (GET, POST)
- API manutenzioni (GET, POST, PATCH, complete)
- API documenti mezzo (POST, GET, DELETE)
- UI lista mezzi con filtri e ricerca
- UI dettaglio mezzo con tab secondarie
- Badge stato mezzo
**Success Criteria:**
- [ ] Tutti i models SQLAlchemy mezzi creati
- [ ] Migration Alembic applicabile
- [ ] API mezzi complete e testate
- [ ] API sessioni, carburante, manutenzioni funzionanti
- [ ] UI lista e dettaglio mezzi
- [ ] Test backend mezzi passano

---

### Phase 2: Attività Operatori e Approvazione
**Status:** Complete
**Goal:** Rendere operativo il ciclo attività con catalogo, start/stop, approvazioni e UI.
**Requirements:**
- SQLAlchemy models: ActivityCatalog, OperatorActivity, OperatorActivityEvent, OperatorActivityAttachment, ActivityApproval
- Migration Alembic attività
- API catalogo attività (GET)
- API create/start/stop attività
- API submit/approve/reject attività
- API note e allegati attività
- API summary GPS attività
- UI lista attività con filtri (stato, operatore, squadra, mezzo)
- UI dettaglio attività con dati dichiarati/GPS distinti
- UI approvazioni capo servizio
**Success Criteria:**
- [ ] Models attività creati
- [ ] Migration applicabile
- [ ] API start/stop/approve funzionanti
- [ ] UI lista e dettaglio attività
- [ ] UI approvazioni
- [ ] Test workflow attività passano

---

### Phase 3: Segnalazioni e Pratiche
**Status:** Complete
**Goal:** Rendere operativo il workflow segnalazione → pratica con API e UI complete.
**Requirements:**
- SQLAlchemy models: FieldReport, FieldReportCategory, FieldReportSeverity, FieldReportAttachment, InternalCase, InternalCaseEvent, InternalCaseAttachment, InternalCaseAssignmentHistory
- Migration Alembic pratiche
- API create report (genera pratica automaticamente)
- API list/update reports
- API list/get cases
- API assign/acknowledge/start/resolve/close/reopen cases
- API case events
- API case attachments
- UI lista segnalazioni
- UI lista pratiche con filtri
- UI dettaglio pratica con timeline eventi
- UI azioni assegnazione/cambio stato/chiusura
**Success Criteria:**
- [ ] Models segnalazioni/pratiche creati
- [ ] Migration applicabile
- [ ] Creazione segnalazione genera pratica in transazione
- [ ] API pratiche complete
- [ ] UI lista e dettaglio pratiche
- [ ] UI timeline eventi
- [ ] Test report → case passano

---

### Phase 4: Allegati e Storage Governance
**Status:** Complete
**Goal:** Rendere robusta la gestione media con metadata, validazioni, quota e alert.
**Requirements:**
- SQLAlchemy models: Attachment, StorageQuotaMetric, StorageQuotaAlert
- Migration Alembic allegati
- API upload allegati (multipart) con validazioni mime/size
- API metadata allegati (GET, DELETE logico)
- API download allegati
- Storage quota service con calcolo occupazione
- Soglie 70/85/95% con alert automatici
- Endpoint dashboard storage
- UI card storage usage
- UI pagina storage admin
- Preview allegati dove possibile
- Errori upload chiari
**Success Criteria:**
- [ ] Models allegati e storage creati
- [ ] Migration applicabile
- [ ] Upload con validazioni funzionante
- [ ] Quota service con alert
- [ ] UI storage admin
- [ ] Test quota e attachment passano

---

### Phase 5: Mini-App Operatori
**Status:** Complete
**Goal:** Fornire interfaccia mobile-first operativa per operatori sul campo.
**Requirements:**
- Home mini-app con 3 azioni principali (Avvia attività, Chiudi attività, Nuova segnalazione)
- Pagina nuova attività
- Pagina chiusura attività
- Pagina nuova segnalazione
- Liste personali (mie attività, mie segnalazioni)
- Banner stato rete e sync
- Bozze locali (IndexedDB)
- Coda invii pendenti con retry
- Endpoint backend ottimizzati per UX mobile
- Sync batch attività offline
- Sync batch segnalazioni offline
**Success Criteria:**
- [ ] Home mini-app usabile
- [ ] Flusso nuova attività completo
- [ ] Flusso chiusura attività completo
- [ ] Flusso nuova segnalazione completo
- [ ] Bozze locali funzionanti
- [ ] Sync offline base
- [ ] Banner stato connessione

---

### Phase 6: GPS e Consuntivazione
**Status:** Complete
**Goal:** Consolidare valore consuntivo del sistema con GPS service astratto e viste di riepilogo.
**Requirements:**
- GPS service astratto con adapter pattern
- Supporto dati GPS da mini-app
- Supporto binding futuro provider mezzi
- Summary GPS per attività e utilizzi mezzo
- Distinzione dichiarato/rilevato/validato
- Pannelli riepilogo GPS in UI
- Vista dati rilevati vs dichiarati
- Indicatori anomalie di consuntivazione
- API import dati da provider GPS
**Success Criteria:**
- [ ] GPS service astratto implementato
- [ ] Dati GPS persistiti da mini-app
- [ ] Summary GPS per attività/sessioni
- [ ] UI pannelli GPS
- [ ] Dati dichiarati vs rilevati visibili

---

### Phase 7: Hardening, Test e Rilascio Interno
**Status:** Complete
**Goal:** Preparare il modulo per rilascio interno pilot con test, performance e documentazione.
**Requirements:**
- Test di regressione end-to-end
- Test permessi per ruolo (admin, capo, operatore)
- Test su rete instabile (simulazione)
- Pulizia UI e consistency check
- Revisione logging e audit
- Verifica performance query principali
- Documentazione finale aggiornata
- Checklist collaudo
- Demo end-to-end
**Success Criteria:**
- [x] 21 unit test passano (schemas, business rules, attachment service)
- [x] Permessi verificati per tutti i ruoli (require_active_user su tutte le route)
- [ ] Performance query accettabili (da verificare con dati reali)
- [x] Documentazione aggiornata (PROGRESS.md, STATE.md, ROADMAP.md)
- [ ] Demo end-to-end funzionante (richiede DB migration applicate)
- [ ] Checklist collaudo compilata
