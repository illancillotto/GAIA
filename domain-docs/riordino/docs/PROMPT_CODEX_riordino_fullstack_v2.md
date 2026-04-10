# Prompt Codex — Fullstack modulo GAIA Riordino v2

Implementa il modulo **Riordino** dentro GAIA. Questo prompt è il riferimento unico per implementazione completa.

## Vincoli architetturali
- Backend monolite modulare FastAPI in `backend/app/modules/riordino/`
- Frontend unico Next.js in `frontend/src/app/riordino/`
- Database PostgreSQL condiviso, tabelle `riordino_*`
- Docs in `domain-docs/riordino/docs/`
- Auth: tabella `application_users`, PK **Integer** (non UUID!). FK user → `ForeignKey("application_users.id")` tipo int
- Soggetti: tabella `ana_subjects`, PK **UUID**. FK soggetto → `ForeignKey("ana_subjects.id")` tipo uuid
- Storage documenti: filesystem locale `/data/gaia/riordino/`
- Niente microservizi, niente import cross-modulo

## Documenti di riferimento
Leggi TUTTI prima di scrivere codice:
1. `PRD_riordino_v2.md` — requisiti, step template, regole business
2. `ARCHITECTURE_riordino_v2.md` — modello dati, struttura, indici, permessi
3. `EXECUTION_PLAN_riordino_v2.md` — ordine implementazione, done criteria

## Contesto dominio
Digitalizzazione riordino catastale. Gerarchia: Comune → Maglia → Lotto → Particelle.
Due fasi sequenziali: Approvazione Decreto (13 step) → Attuazione Decreto (12 step).
Branching: tutti step generati, rami non pertinenti marcati `skipped`.
Ricorsi: entità dedicata `RiordinoAppeal`.
Scadenze: calcolo automatico + notifiche in-app.
GIS: solo link manuali per MVP.

## Sequenza di lavoro OBBLIGATORIA

### Step 1 — Enum e modelli
1. Crea `enums.py` con tutti gli enum
2. Crea 14 modelli SQLAlchemy (vedi ARCHITECTURE v2 sezione 5)
3. Crea migration Alembic con seed 25 step template

### Step 2 — Repository e schemas
4. Crea schemas Pydantic per tutte le entità (input/output)
5. Crea 4 repository (practice, workflow, appeal, issue)

### Step 3 — Services
6. `PracticeService`: CRUD + generazione fasi/step da template + code generation
7. `WorkflowService`: advance_step (con branching), skip, reopen, phase transitions
8. `AppealService`: CRUD ricorsi + resolve
9. `IssueService`: CRUD + close
10. `DocumentService`: upload filesystem + CRUD record + validazione MIME/size
11. `NotificationService`: check scadenze + CRUD notifiche
12. `DashboardService`: aggregazioni conteggi

### Step 4 — Routes
13. Implementa TUTTE le route da PRD v2 sezione 14
14. Registra nel router principale via `bootstrap.py`

### Step 5 — Test backend
15. Scrivi i 18 test da PROMPT_CODEX_backend_v2 sezione 9
16. Esegui `pytest` e verifica tutti verdi

### Step 6 — Frontend
17. API client tipizzato + types TypeScript
18. Layout modulo + route
19. Dashboard → Lista pratiche → Workspace pratica
20. Pannelli: workflow, step, ricorsi, issue, documenti, GIS, timeline, notifiche
21. Configurazione admin

### Step 7 — Verifica
22. `npm run lint` + `npx tsc --noEmit`
23. Test manuale flusso completo: crea pratica → Fase 1 → ricorso → Fase 2 → branching → chiusura

### Step 8 — Docs
24. Aggiorna PROGRESS_riordino.md con checklist completate

## Regole workflow critiche (da implementare esattamente)

### advance_step
- Step `todo` o `in_progress` → verifica prerequisiti → `done`
- Decisionale senza outcome → 422
- Documento richiesto senza doc → 422
- Issue blocking → 403
- Checklist blocking non checked → 403
- Se `F2_VERIFICA` outcome=`conforme` → auto-skip step branch=`anomalia`
- Genera evento audit

### complete_phase
- Tutti step obbligatori done/skipped
- Fase 1: nessun appeal open/under_review
- Nessuna issue blocking
- Genera evento audit
- Solo manager/admin

### start_phase (Fase 2)
- Fase 1 deve essere completed
- Solo manager/admin

### Code generation pratica
- `RIO-{ANNO}-{PROG:04d}` con lock per unicità

## Definition of done
- [ ] Pratica creabile con 2 fasi e 25 step generati
- [ ] Fase 1 percorribile con ricorsi
- [ ] Fase 2 percorribile con branching condizionale
- [ ] Scadenze calcolate con notifiche
- [ ] Documenti caricabili/scaricabili/versionati
- [ ] Issue/anomalie gestibili
- [ ] GIS link manuali
- [ ] Timeline eventi completa
- [ ] Dashboard con conteggi
- [ ] Frontend workspace operativo
- [ ] Permessi per ruolo
- [ ] Test backend verdi
- [ ] Lint + typecheck frontend verdi
- [ ] Audit trail completo
