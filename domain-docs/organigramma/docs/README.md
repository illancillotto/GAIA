# GAIA Organigramma

## Stato

Modulo canonico implementato su:

- backend: `backend/app/modules/organigramma/`
- frontend: `frontend/src/app/organigramma/page.tsx`
- controller mutazioni frontend: `frontend/src/features/organigramma/organigramma-mutations.ts`
- controller snapshot, viewport e selezione: `frontend/src/features/organigramma/organigramma-{snapshot,viewport,selection}-controller.ts`
- controller layout/persistenza e caricamento: `frontend/src/features/organigramma/organigramma-{layout,loading}-controller.ts`
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

- `org_unit`: albero unita organizzative (`direzione|distretto|settore|reparto|squadra`)
- `org_assignment`: assegnazione `application_user -> org_unit` con manager diretto e title operativo
- `org_visibility_override`: eccezioni esplicite di visibilita
- `org_source_link`: mapping idempotente con sorgenti WhiteCompany

Vincoli chiave:

- `application_users.id` resta `Integer` e tutte le FK verso utenti usano `Integer`
- PK canoniche `org_*` in `Uuid`
- `title` operativo non coincide con ruolo RBAC
- `position_code` normalizza le posizioni `dirigente|capo_settore|capo_operai|capo_reparto|collaboratore`
- nell'Organigramma canonico solo `super_admin` bypassa la visibilita; il dominio Presenze applica anche il bypass concordato per `admin` e `hr_manager`

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
- gli scope `read`, `approve` e `full` restano distinti; la gerarchia manageriale concede `approve`

Nel dominio Presenze il resolver aggiunge le eccezioni applicative concordate:

- `admin`, `super_admin` e `hr_manager` vedono tutti i dati delle giornaliere
- dirigenti e capi vedono soltanto le persone nel proprio sottoalbero canonico
- gli override `read` non consentono la validazione; `approve` e `full` la consentono
- la visibilita delle giornaliere usa `PresenzeCollaborator.application_user_id`
- `owner_user_id` identifica chi ha importato il dato e non propaga visibilita ai suoi responsabili
- le assegnazioni supervisore e la gerarchia Accessi legacy restano lette durante la migrazione

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
- `POST /sync/inaz/preview`

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
- sync assegnazioni operatori e posizioni normalizzate implementato
- il job WhyCompany `org_charts` aggiorna prima lo staging Accessi e poi, nello
  stesso flusso, il livello canonico letto da `/presenze/organigramma`

Regole MVP:

- mapping idempotente via `org_source_link`
- righe con `is_manual_locked=True` non sovrascritte
- `last_synced_at` aggiornato sui link processati

## Sync INAZ

La vista INAZ `Organigramma con Responsabile` viene acquisita come snapshot
completo e firmata con checksum semantico. Il recupero usa credenziali e
sessione dedicate, separate da quelle delle Giornaliere.

Il `Kint` esposto dall'Organigramma non coincide necessariamente con
`presenze_collaborators.kint`. Lo scraper apre quindi la scheda personale INAZ
di ogni risorsa e produce uno snapshot schema `2` contenente la relazione
tecnica fra `Kint`, codice azienda e codice dipendente:

```json
{
  "schema_version": 2,
  "source_system": "inaz",
  "source_view": "Organigramma con Responsabile",
  "units": [
    {
      "members": [
        {
          "kint": "<kint organigramma>",
          "kkint": "<token volatile>",
          "company_code": "<azienda INAZ>",
          "employee_code": "<codice dipendente INAZ>"
        }
      ]
    }
  ]
}
```

La preview risolve ogni persona esclusivamente tramite:

```text
(company_code, employee_code) dello snapshot
  -> presenze_collaborators
  -> presenze_collaborators.application_user_id
  -> application_users.id
```

Il checksum include `company_code` ed `employee_code`, ma esclude `KKint`
perche volatile. Non sono ammessi fallback tramite nome, email, matricola,
`WCOperator.employee_code`, uguaglianza dei Kint o uguaglianze numeriche. Una
risorsa senza codice, senza collaboratore Presenze univoco, senza mapping o con
utente inesistente resta fail-closed. La preview e sempre read-only e non
modifica `presenze_collaborators.application_user_id`.

Workflow obbligatorio:

1. acquisire lo snapshot completo con la sessione INAZ Organigramma dedicata;
2. verificare checksum, conteggi e unicita delle identita dipendente;
3. inviare lo snapshot a `POST /sync/inaz/preview`;
4. risolvere nel dominio Presenze ogni issue restituita;
5. richiedere `ready=true` prima di pianificare l'import di unita e assegnazioni.

### Onboarding delle identita mancanti

Il comando `backend/scripts/onboard_inaz_organization.py` prepara le identita
GAIA necessarie allo snapshot. Il default e sempre dry-run e l'applicazione
richiede `--apply`, un utente GAIA autore reale e un motivo di audit.

La classificazione e fail-closed:

- la coppia `(company_code, employee_code)` gia associata a un collaboratore
  mappato risolve esclusivamente il mapping canonico gia attestato e resta
  invariata;
- un `Kint` univoco gia conservato su un collaboratore mappato puo attestare lo
  stesso riferimento tecnico INAZ, ma non sovrascrive i campi posseduti dalla
  sincronizzazione Presenze;
- candidati ottenuti da nome o altri dati anagrafici restano
  `REVIEW_REQUIRED` e non vengono applicati;
- riferimenti tecnici duplicati, collaboratori esistenti ma non mappati e
  risorse senza codice dipendente restano bloccati;
- solo quando non esiste alcun riferimento tecnico o candidato GAIA viene
  creata una nuova identita inattiva, collegata a un collaboratore Presenze e
  a un `WCOperator` tecnico disabilitato.

Gli account creati non acquisiscono accesso o credenziali utilizzabili: hanno
ruolo `viewer`, sono inattivi e non sono inclusi nei payload operatori GATE. Il
mapping canonico viene registrato tramite
`presenze_collaborators.application_user_id` e relativo audit.

Esecuzione:

```bash
python backend/scripts/onboard_inaz_organization.py \
  /percorso/snapshot-v2.json \
  /percorso/review-required.json \
  --changed-by-gaia-user-id <ID_AUTORE_GAIA> \
  --reason "Onboarding Organigramma INAZ YYYY-MM-DD"

# Solo dopo backup verificato e dry-run approvato:
python backend/scripts/onboard_inaz_organization.py \
  /percorso/snapshot-v2.json \
  /percorso/review-required.json \
  --changed-by-gaia-user-id <ID_AUTORE_GAIA> \
  --reason "Onboarding Organigramma INAZ YYYY-MM-DD" \
  --apply
```

Dopo l'applicazione, rieseguire il dry-run: `new_users` ed
`exact_kint_updates` devono essere zero. Verificare inoltre audit, duplicati,
orfani, divergenze di mapping e impronta dei mapping preesistenti secondo il
runbook Presenze. Le righe `REVIEW_REQUIRED` e `blocked` non autorizzano alcun
fallback e devono restare escluse finche non sono risolte esplicitamente.

## Test e verifica

Il workspace delega spostamento/collegamento dei blocchi, assegnazioni,
creazione e cancellazione al controller mutazioni. Il contesto tipizzato
contiene il token, i permessi e lo stato della render corrente: non conserva
snapshot persistenti e non introduce cache o retry. Le guardie rimangono nel
controller anche quando la UI nasconde l'azione. Payload, `structureKind`,
ordine delle chiamate API/refresh, messaggi, cleanup del drag e conferma di
cancellazione restano invariati. La creazione con responsabile non introduce
rollback dell'unita se l'assegnazione fallisce, come nel comportamento originale.

Snapshot, import/export, sincronizzazione e override sono delegati al controller
snapshot; pan, marquee e zoom al controller viewport; selezione, drag delle
schede e avvio dei collegamenti al controller selection. I contesti sono solo
tipi: gli adapter passano lo stato corrente, mantenendo dipendenze hook,
listener DOM, cleanup e comportamento degli handler originali. Il drawer
persona e testabile separatamente sul suo contratto di token nullable e dati
persona/override parziali, senza duplicarne il rendering o modificarne il corpo.

Layout, compattazione e riallineamento conservano la distinzione fra coordinate
locali e salvataggio autorizzato; caricamento iniziale e refresh leggero mantengono
la pubblicazione dei cataloghi solo dopo il successo delle letture parallele.
Il lifecycle viewport conserva listener, cleanup e lettura della foresta corrente
al rilascio: un nodo eliminato da refresh concorrente non viene salvato.

Backend:

- `backend/tests/organigramma/test_visibility_service.py`
- `backend/tests/organigramma/test_schemas.py`
- `backend/tests/organigramma/test_api.py`
- `backend/tests/test_elaborazioni_bonifica_oristanese.py`
- `backend/tests/test_bootstrap_admin.py`
- `backend/tests/test_section_permissions.py`

Frontend:

- `frontend/tests/unit/organigramma-helpers.test.ts`
- `frontend/tests/unit/organigramma-page.test.tsx`
- `frontend/tests/unit/organigramma-modals.test.tsx`
- `frontend/tests/unit/organigramma-mutations.test.ts`
- `frontend/tests/unit/organigramma-snapshot-controller.test.ts`
- `frontend/tests/unit/organigramma-viewport-controller.test.ts`
- `frontend/tests/unit/organigramma-selection-controller.test.ts`
- `frontend/tests/unit/organigramma-geometry.test.ts`
- `frontend/tests/unit/organigramma-layout-controller.test.ts`
- `frontend/tests/unit/organigramma-loading-controller.test.ts`
- `frontend/tests/unit/organigramma-viewport-lifecycle.test.ts`
- `frontend/tests/unit/organigramma-presentation.test.tsx`
- `frontend/tests/unit/organigramma-schema-fit.test.ts`

Workspace, sei controller e helper in `src/lib/organigramma.ts` sono coperti
al 100% su statement, branch, funzioni e linee, anche file per file.
L'ultima verifica comprende 434 test pertinenti: `1626/1626` statement,
`1339/1339` branch, `452/452` funzioni e `1448/1448` linee. Il gate full-file
e verde senza esclusioni coverage o mock di stati impossibili. Ratchet
contro `main`, typecheck ed ESLint passano; restano due warning hook legacy.
Evidenze aggiornate in `docs/code-quality/PROGRESS.md`.

Il gate verde riguarda il runtime frontend Organigramma, non l'intero
repository. La slice tooling successivamente autorizzata porta anche
`tools/code_quality/complexity.py` al 100% full-file: 702 statement e 270
branch, includendo i test CLI in subprocess. I 144 test tooling passano;
il precedente blocco coverage del commit e risolto.
Restano due warning hook legacy; nessuna regressione osservata
nelle suite eseguite. API/DB live ed E2E non sono stati rieseguiti in questa
tranche: le API dei controller sono verificate tramite mock dei contratti.
Graphify codice e aggiornato; l'arricchimento semantico della documentazione
di dominio e parziale per un errore di connessione, non un refresh completo.

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
