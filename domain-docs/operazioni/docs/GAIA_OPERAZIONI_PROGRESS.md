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

Data ultimo aggiornamento: <!-- aggiornare -->
Responsabile aggiornamento: <!-- aggiornare -->

---

## 1. Stato generale modulo

| Area | Stato | Note |
|---|---|---|
| PRD | DONE | PRD completo definito |
| Schema DB | DONE | PostgreSQL schema definito |
| API design | DONE | API complete definite |
| Backend scaffolding | TODO | |
| Migration Alembic | TODO | |
| API Mezzi | TODO | |
| API Attività | TODO | |
| API Segnalazioni/Pratiche | TODO | |
| Allegati/Storage | TODO | |
| Frontend desktop | TODO | |
| Mini-app operatori | TODO | |
| Offline minimo | TODO | |
| GPS integration layer | TODO | |
| Test | TODO | |
| Documentazione dominio | TODO | |

---

## 2. Milestone tracking

## Milestone 0 — Allineamento e scaffolding

**Stato:** TODO

### Checklist
- [ ] Creata struttura backend `backend/app/modules/operazioni/`
- [ ] Creata struttura frontend `frontend/src/app/operazioni/`
- [ ] Router backend registrato
- [ ] Navigazione frontend aggiornata
- [ ] Docs dominio create in `domain-docs/operazioni/docs/`
- [ ] Naming tabella utenti verificato

### Note
- Nessuna

### Blocchi
- Nessuno

---

## Milestone 1 — Data layer e API mezzi

**Stato:** TODO

### Checklist
- [ ] Model Vehicle
- [ ] Model VehicleAssignment
- [ ] Model VehicleUsageSession
- [ ] Model VehicleFuelLog
- [ ] Model VehicleMaintenance
- [ ] Migration Alembic mezzi
- [ ] CRUD mezzi
- [ ] Endpoint assegnazioni
- [ ] Endpoint utilizzi
- [ ] Endpoint carburante
- [ ] Endpoint manutenzioni
- [ ] Test backend mezzi
- [ ] UI lista mezzi
- [ ] UI dettaglio mezzo

### Note
- Nessuna

### Blocchi
- Nessuno

---

## Milestone 2 — Attività operatori e approvazione

**Stato:** TODO

### Checklist
- [ ] Model ActivityCatalogItem
- [ ] Model OperatorActivity
- [ ] Model ActivityApproval
- [ ] Migration Alembic attività
- [ ] Endpoint activity catalog
- [ ] Endpoint create/start/stop activities
- [ ] Endpoint approval/reject
- [ ] Test workflow attività
- [ ] UI lista attività
- [ ] UI dettaglio attività
- [ ] UI approvazioni

### Note
- Nessuna

### Blocchi
- Nessuno

---

## Milestone 3 — Segnalazioni e pratiche

**Stato:** TODO

### Checklist
- [ ] Model FieldReport
- [ ] Model InternalCase
- [ ] Model InternalCaseEvent
- [ ] Model InternalCaseAssignment
- [ ] Migration Alembic pratiche
- [ ] Endpoint create report
- [ ] Creazione automatica pratica
- [ ] Endpoint list/update cases
- [ ] Endpoint case events
- [ ] Test report → case
- [ ] UI lista segnalazioni
- [ ] UI lista pratiche
- [ ] UI dettaglio pratica con timeline

### Note
- Nessuna

### Blocchi
- Nessuno

---

## Milestone 4 — Allegati e storage

**Stato:** TODO

### Checklist
- [ ] Model Attachment
- [ ] Metadata storage implementati
- [ ] Validazioni mime/size
- [ ] Service quota storage
- [ ] Endpoint storage usage
- [ ] Alert soglie 70/85/95
- [ ] UI pagina storage
- [ ] UI storage cards dashboard

### Note
- Nessuna

### Blocchi
- Nessuno

---

## Milestone 5 — Mini-app operatori

**Stato:** TODO

### Checklist
- [ ] Home mini-app
- [ ] Pagina nuova attività
- [ ] Pagina chiusura attività
- [ ] Pagina nuova segnalazione
- [ ] Liste personali
- [ ] Banner stato sync
- [ ] Bozze locali
- [ ] Retry invii pendenti

### Note
- Nessuna

### Blocchi
- Nessuno

---

## Milestone 6 — GPS e consuntivazione

**Stato:** TODO

### Checklist
- [ ] GPS service astratto
- [ ] Persistenza dati GPS mini-app
- [ ] Vehicle GPS binding model/logica
- [ ] Summary GPS attività
- [ ] Summary GPS utilizzo mezzo
- [ ] UI pannello GPS
- [ ] Dati dichiarati vs rilevati esposti in UI

### Note
- Nessuna

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

---

## 4. Decisioni ancora da chiudere

- [ ] Nome reale tabella utenti applicativi nel database GAIA
- [ ] Policy definitiva compressione video lato client/server
- [ ] Strategia backup storage allegati
- [ ] Strategia di retention media storici
- [ ] Provider GPS effettivo e modalità integrazione
- [ ] Eventuale anagrafica squadre già esistente o da creare nel modulo

---

## 5. Change log operativo

### 2026-04-03
- Creati PRD completo, schema DB, API complete, prompt backend/frontend, execution plan e progress iniziale.
