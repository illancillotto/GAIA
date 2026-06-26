# GAIA Organigramma

## Stato

Modulo canonico implementato su:

- backend: `backend/app/modules/organigramma/`
- frontend: `frontend/src/app/organigramma/page.tsx`
- migration principale: `backend/alembic/versions/20260608_0134_organigramma_canonical_layer.py`

## Obiettivo

Fornire una verita canonica per la struttura organizzativa di GAIA senza
trasformare WhiteCompany nella fonte di verita applicativa.

Decisione architetturale adottata:

- nuove tabelle canoniche GAIA come fonte primaria
- WhiteCompany come sorgente esterna
- bridge verso dati legacy `operazioni` e `wc_*`
- override manuali non sovrascritti dal sync se il link sorgente e bloccato

## Modello dati canonico

Tabelle principali:

- `org_unit`: albero unita organizzative (`direzione|distretto|settore|squadra`)
- `org_assignment`: assegnazione `application_user -> org_unit` con manager diretto e title operativo
- `org_visibility_override`: eccezioni esplicite di visibilita
- `org_source_link`: mapping idempotente con sorgenti WhiteCompany

Vincoli chiave:

- `application_users.id` resta `Integer` e tutte le FK verso utenti usano `Integer`
- PK canoniche `org_*` in `Uuid`
- `title` operativo non coincide con ruolo RBAC
- solo `super_admin` bypassa la visibilita; `admin` no

## RBAC e visibilita

Sono due layer distinti.

RBAC sezione/modulo:

- flag utente `module_organigramma`
- sezione `organigramma.read`
- sezione `organigramma.manage`

Visibilita dati:

- base gerarchica: un viewer vede le unita dove e manager diretto dei membri e tutti i discendenti
- override: un viewer puo ricevere visibilita aggiuntiva su un utente o su un sottoalbero
- la provenienza della visibilita e tracciata come `gerarchia` oppure `override`

## API principali

Prefix modulo: `/organigramma`

Read:

- `GET /units/tree`
- `GET /units`
- `GET /units/{id}`
- `GET /assignments`
- `GET /visibility/{user_id}`

Manage:

- `POST|PUT|DELETE /units`
- `POST|PUT|DELETE /assignments`
- `GET|POST|PUT|DELETE /overrides`
- `POST /sync/whitecompany`

Il router applica:

- `require_module("organigramma")` a livello modulo
- `require_section("organigramma.read")` o `require_section("organigramma.manage")` per route

## Frontend

La pagina canonica e `/organigramma` (esposta anche come `/presenze/organigramma` nel contesto del modulo Presenze);
il componente condiviso e `frontend/src/features/organigramma/organigramma-workspace.tsx`.
Include:

- albero ricorsivo espandibile
- dettaglio unita con responsabile e assegnazioni
- evidenza della provenienza `manuale|whitecompany|bridge_team`
- pannello override
- simulatore "Chi vede chi"
- vista Schema: lavagna a canvas libero con zoom/fit e snap griglia

### Lavagna schema

Interazioni della vista Schema (modifiche riservate a `Abilita modifica`):

- pan con tasto sinistro sullo sfondo, sempre attivo anche in sola lettura
- connettori con freccia direzionale padre -> figlio
- `↓` su una card: modalita "aggancia figli", click in sequenza sui blocchi da
  collegare sotto la card (piu di uno); si esce con Esc, click a vuoto o di
  nuovo `↓`
- `↑` su una card: scelta del padre (singolo, si chiude al primo click)
- tasto destro su una card: menu rapido con "Scollega da <padre>", aggancia
  figli, sposta sotto un altro blocco, scheda responsabile
- multiselezione con `Ctrl/Cmd+click` (toggle) e `Shift+click` (aggiunta);
  il drag di una card selezionata sposta tutto il gruppo
- selezione ad area: `Shift+trascina` sullo sfondo disegna un rettangolo e
  seleziona tutti i blocchi al suo interno
- tasto destro su una card con figli: "Seleziona sottoalbero (N blocchi)"
  seleziona il blocco e tutti i discendenti (es. per spostare un ramo intero)
- raggruppamento: il pulsante "Raggruppa" sulla card (o la voce contestuale
  "Raggruppa sottoalbero") nasconde l'intero sotto-albero dentro il blocco,
  mostrato con bordo tratteggiato ed effetto pila; "Esplodi (+N)" lo riapre e
  "Esplodi tutto" in toolbar riapre tutti i gruppi. Solo visualizzazione:
  gerarchia e posizioni non vengono toccate
- auto-raggruppamento (stile MyHeritage): se i blocchi visibili superano la
  soglia (12), i livelli sotto radici+figli partono compressi; l'espansione e
  progressiva, un livello alla volta. Hover su un gruppo compresso: tooltip
  con recap (unita, persone, prime unita figlie) e pulsante "Esplodi". La
  soglia/profondita sono `SCHEMA_AUTO_GROUP_THRESHOLD` e
  `SCHEMA_AUTO_GROUP_DEPTH` nel workspace
- ogni blocco ha un solo padre; un padre puo avere n figli
- dopo le mutazioni il refresh e silenzioso (albero, assegnazioni e dettaglio
  aggiornati in place, pan/zoom preservati)

Pannello laterale "Blocchi e operatori" (sidebar dedicata, non sovrapposta
alla lavagna):

- collegamenti rapidi Sopra/Sotto dal blocco selezionato verso gli altri blocchi
- lista operatori con tutti gli `application_users` attivi, con badge
  `assegnato|da assegnare`, ricerca e drag&drop sui nodi (modalita persona o
  responsabile)

Nota build: il `content` di `frontend/tailwind.config.ts` deve includere
`./src/features/**/*.{ts,tsx}`, altrimenti le classi usate solo dal workspace
(es. `xl:*`) non vengono generate e la sidebar resta nascosta.

Tipi frontend:

- `frontend/src/types/api.ts`
- `frontend/src/types/organigramma.ts`

Client API:

- `frontend/src/lib/api.ts`

## Sync WhiteCompany

Stato attuale:

- sync unita da `wc_area` implementato
- sync assegnazioni operatori lasciato come follow-up documentato

Regole MVP:

- mapping idempotente via `org_source_link`
- righe con `is_manual_locked=True` non sovrascritte
- `last_synced_at` aggiornato sui link processati

## Test e verifica

Backend:

- `backend/tests/organigramma/test_visibility_service.py`
- `backend/tests/organigramma/test_schemas.py`
- `backend/tests/organigramma/test_api.py`
- `backend/tests/test_bootstrap_admin.py`
- `backend/tests/test_section_permissions.py`

Frontend:

- `frontend/tests/unit/organigramma-helpers.test.ts`
- `frontend/tests/unit/organigramma-page.test.tsx`

Comandi usati per la verifica locale:

```bash
cd backend && pytest tests/organigramma tests/test_bootstrap_admin.py tests/test_section_permissions.py -q
cd frontend && npm run typecheck
cd frontend && npm run test:unit -- tests/unit/organigramma-helpers.test.ts tests/unit/organigramma-page.test.tsx
cd backend && ./.venv/bin/python -m alembic heads
docker compose exec -T backend sh -lc 'python -m alembic current && python -m alembic upgrade head'
```

Esito di riferimento alla chiusura:

- head Alembic corrente: `20260608_0135`
- catena rilevante: `20260608_0133 -> 20260608_0134 -> 20260608_0135`
