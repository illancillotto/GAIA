# GAIA CED
## Implementation Plan

> Regola repository
> L'iniziativa `GAIA CED` e una convergenza frontend e di navigazione.
> Nella prima fase non introduce un nuovo modulo backend dedicato.

## 1. Obiettivo

Realizzare un modulo `GAIA CED` che aggreghi `NAS Control` e `Rete` in una
superficie utente unica, mantenendo inizialmente invariati backend, API e
permessi di dominio.

## 2. Assunzioni operative

- il backend `accessi` resta il backend di riferimento per le superfici NAS
- il backend `network` resta il backend di riferimento per le superfici Rete
- le route frontend legacy `/nas-control/*` e `/network/*` restano disponibili
  almeno per una fase transitoria
- i permessi applicativi restano `module_accessi` e `module_rete`

## 3. Fasi di implementazione

### Fase 0 — Preparazione documentale

Output:

- PRD dedicato `GAIA CED`
- piano di implementazione
- prompt operativo per Codex
- progress file iniziale
- aggiornamento docs root e struttura docs

### Fase 1 — Shell frontend CED

Output:

- nuovo namespace `frontend/src/app/ced`
- dashboard iniziale `/ced`
- riconoscimento `currentModuleKey = "ced"` in sidebar
- nuovo tile home `GAIA CED`
- nuova voce sidebar piattaforma `CED`

File primari da toccare:

- `frontend/src/app/page.tsx`
- `frontend/src/app/login/page.tsx`
- `frontend/src/components/layout/platform-sidebar.tsx`
- `frontend/src/components/layout/sidebar.tsx`
- `frontend/src/components/layout/module-sidebar.tsx`
- `frontend/src/app/ced/page.tsx`

### Fase 2 — Aree NAS e Rete sotto CED

Output:

- nuove route `ced/nas/*`
- nuove route `ced/rete/*`
- wrapper o riuso dei componenti/pagine esistenti

Route target:

- `/ced`
- `/ced/nas`
- `/ced/nas/sync`
- `/ced/nas/users`
- `/ced/nas/groups`
- `/ced/nas/shares`
- `/ced/nas/effective-permissions`
- `/ced/nas/reviews`
- `/ced/nas/reports`
- `/ced/rete`
- `/ced/rete/devices`
- `/ced/rete/alerts`
- `/ced/rete/scans`
- `/ced/rete/floor-plan`

### Fase 3 — Migrazione link interni

Output:

- tutti i link interni puntano a `/ced/...`
- le pagine legacy restano compatibili o reindirizzano

Strategie ammesse:

- aggiornare tutti i link interni e tenere i path legacy vivi
- aggiungere redirect progressivi lato frontend

### Fase 4 — Hardening permessi e accessi

Output:

- `/ced` accessibile se `accessi OR rete`
- `/ced/nas/*` protetto da regole accessi
- `/ced/rete/*` protetto da regole rete

### Fase 5 — Valutazione unificazione permessi

Output opzionale:

- analisi per `module_ced`
- eventuale migration DB
- decisione su convivenza o deprecazione di `module_accessi` e `module_rete`

Questa fase non e parte del primo rilascio.

## 4. Dettaglio tecnico per area

### 4.1 Home e login

- sostituire la presentazione separata di `GAIA NAS Control` e `GAIA Rete`
  con una card/voce primaria `GAIA CED`
- dove utile, mantenere descrizione interna delle due aree

### 4.2 Sidebar piattaforma e modulo

- aggiungere un nuovo modulo logico `ced`
- la module sidebar `ced` deve includere due gruppi espliciti:
  - `NAS`
  - `Rete`

### 4.3 Backend e API

Nessuna modifica richiesta nella fase 1 salvo:

- eventuali guardie di accesso lato frontend/backend per l'entrypoint `/ced`
- eventuali helper di compatibilita se servono redirect

### 4.4 Permessi

Decisione raccomandata:

- non introdurre subito `module_ced`
- usare combinazione dei permessi esistenti

## 5. Acceptance criteria

- esiste il nuovo modulo frontend `CED`
- home e sidebar mostrano `CED` come entrypoint primario
- l'utente con `accessi` vede l'area NAS
- l'utente con `rete` vede l'area Rete
- l'utente con entrambi vede l'intero modulo
- le superfici legacy non smettono di funzionare senza piano esplicito di redirect

## 6. Rischi

- regressioni su navigation e breadcrumbs
- disallineamento tra etichette modulo e permessi reali
- doppia manutenzione temporanea tra route legacy e route `CED`
- scope creep verso una prematura fusione backend

## 7. Mitigazioni

- introdurre `CED` prima come contenitore sottile
- non toccare le API nella prima fase
- mantenere i permessi attuali
- aggiornare progressivamente la navigazione interna
- testare esplicitamente i casi:
  - utente solo accessi
  - utente solo rete
  - utente con entrambi

## 8. Verifiche suggerite

- smoke frontend su route `/ced`
- verifica rendering sidebar per modulo `ced`
- verifica visibilita condizionata delle sezioni NAS/Rete
- verifica che `nas-control` e `network` restino raggiungibili finche previsti

## 9. Deliverable attesi

- documentazione `domain-docs/ced/docs/*`
- implementazione frontend incrementale
- aggiornamento root docs
- eventuali redirect e test
