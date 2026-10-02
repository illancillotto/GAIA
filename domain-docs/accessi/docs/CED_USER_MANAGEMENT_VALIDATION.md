# CED: verifica finale del ciclo di sviluppo

Esito finale: **FINAL QUALITY GATE — FAIL**. Implementazione, coverage, E2E CED,
build isolata e Graphify verificati; ratchet, lint backend globale e suite
frontend completa ancora rossi. La sezione "Preparazione commit CED" riporta
la verifica della selezione isolata; le riverifiche precedenti riguardano il
checkout condiviso.

Data: 2026-10-02. Checkout iniziale: `main@af768d77`, con modifiche concorrenti
gia presenti e preservate. Contratto funzionale in `ARCHITECTURE.md`, sezione
"Gestione delegata utenti GAIA: CED". Nessun commit o deploy effettuato.

## Perimetro

- Backend: `app/models/application_user.py`, `app/schemas/users.py`,
  `app/api/router.py`, `app/services/permission_resolver.py`,
  `app/modules/accessi/router.py`, `app/modules/accessi/user_management_policy.py`,
  `app/modules/accessi/routes/admin_users.py` e `section_permissions.py`.
- Frontend: `src/app/gaia/users/page.tsx`, `src/components/layout/navigation.ts`,
  `src/components/layout/sidebar.tsx`, `src/lib/user-management-policy.ts`.
- Test: policy CED nuova; estensione delle suite utenti, sezioni, navigazione
  e pagina utenti. Gli account CED non vengono creati automaticamente.

## Verifiche iniziali di implementazione

- Backend: suite `test_ced_policy.py`, `test_user_management.py` e
  `test_section_permissions.py`: 57 test verdi, piu il successivo test dei
  confini amministrativi delle sezioni, verde. Coverage cumulativa al 100%
  statement e branch per tutti gli otto file runtime backend modificati.
- Frontend: quattro suite (policy, pagina utenti, navigazione, sidebar),
  53 test verdi; 100% statement, branch, funzioni e linee per i quattro file
  runtime modificati. Nessuna esclusione coverage aggiunta.
- Typecheck senza incremental, ESLint mirato e Ruff su runtime/test toccati:
  passati. Formatter dei due file Python nuovi: passato. Diff whitespace pulito.
- `make quality-test QUALITY_PYTHON=backend/.venv/bin/python`: 90 test verdi.
- Il TestClient nella sandbox resta in attesa del risveglio del selector.
  La verifica backend usa `/tmp/gaia-ced-run-tests.py`, che limita l'attesa del
  selector a 1 ms; nessuna modifica al runtime o al runner versionato.
  Coverage acquisita con `--cov=backend/app --cov-branch`, evitando import
  prematuri causati dalla selezione di singoli moduli tramite pytest-cov.

## Complessita e limiti globali

- Metriche della pagina prima/dopo: `GaiaUsersPage` cognitiva 188 -> 178,
  ciclomatica 169 -> 161, LOC 1118 -> 1115. Il renderer resta 64/65/425.
  Le policy di assegnazione e di amministrazione sono responsabilita esplicite;
  nessuna nuova violation error-level nei file aggiunti.
- La PATCH moduli mantiene nomi, default e requisiti dei parametri query usando
  uno schema Pydantic; i parametri del callable passano da 13 a 4.
- Ratchet mirato contro `origin/main`, merge-base `6b61fd27`: restano tre
  finding preesistenti della pagina (LOC di una callback `useEffect`, cognitiva
  e ciclomatica del renderer), gia sopra la baseline prima della feature.
  Il confronto non e dichiarato globalmente verde. Baseline ed esclusioni
  invariate; `baseline-verify` globale restituisce `false` sul checkout concorrente.
- `make lint-backend`, con cache Python in `/tmp`, trova un errore di import
  in una suite Presenze estranea alla feature; Ruff del perimetro CED passa.
- Graphify backend e frontend aggiornati con i target dedicati. Refresh docs
  piattaforma e dominio tentati; chunk semantici falliti con `Connection error`.
  Gli exit code zero di Graphify non sono considerati prova di arricchimento.

## Evidenze locali

Log e report in `/tmp/gaia-ced-*`: `backend-final.json`, `backend-final.log`,
`permissions-final.log`, `frontend-final.log`, `frontend-final/coverage-final.json`,
`before.json`, `after.json`, `ratchet-final.log`, `quality.log`,
`lint-backend-final.log`, `lint-frontend.log` e `graph-*.log`.

## Verifica finale — scope e architettura

Il ciclo comprende gli otto runtime backend e i quattro runtime frontend
elencati sopra. Backend di dominio in `app/modules/accessi/`; enum, schemi e
resolver esistenti condivisi dal monolite. Pagina applicativa in
`src/app/gaia/users/`, policy UI condivisa in `src/lib/user-management-policy.ts`.
Nessun nuovo servizio, dipendenza, migration, tabella o architettura parallela.
`application_users.role` resta una stringa; utenti creati solo su richiesta.

API coinvolte: lista/dettaglio/create/update/inviti e PATCH moduli sotto
`/admin/users`, catalogo `/sections`, consultazione permessi utente,
`/auth/me` e `/auth/my-permissions`. Le intere superfici Network e NAS
audit/permessi/sync negano CED tramite dependency autenticata. I mutating endpoint
di override/sezioni, QGIS Desktop e delete mantengono le policy amministrative.
Le letture API degli account privilegiati restano consentite come documentato;
la UI CED presenta soltanto account standard. SMTP e QGIS usano i servizi esistenti.

Consolidamento circoscritto: rimosso il parametro DB inutilizzato nell'handler
inviti; la policy UI di modifica override ammette esplicitamente solo
Admin/Super Admin. Nessuna funzionalita aggiunta durante questa verifica.

## Matrice funzionalita → comportamento → test

| Funzionalita | Comportamento atteso | Test pertinente |
| --- | --- | --- |
| Accesso gestione utenti | CED ammesso senza NAS; admin richiede Accessi; altri negati | `test_user_management_authorized`, `test_user_management_denied`, unit `management is independent of NAS for CED and preserves admin module checks` |
| Account standard | Create/update/invito consentiti; nessun delete CED | `test_ced_user_management_api_boundaries` |
| Ruoli ordinari | Solo operator/viewer/reviewer/hr_manager assegnabili | `test_ced_can_manage_standard_users`, unit `CED manages only standard accounts and cannot assign privileged roles` |
| Delega moduli | Ogni modulo della lista esplicita ammesso; futuri esclusi | `test_ced_can_delegate_each_explicit_standard_module` (10 casi), `test_ced_cannot_change_reserved_modules`, unit `network, NAS and future modules are excluded from delegation` |
| NAS/Rete degli utenti | Flag riservati esistenti preservati; cambi in entrambe le direzioni negati | `test_ced_cannot_change_reserved_modules` (6 casi), `test_ced_user_management_api_boundaries` |
| Account privilegiati e proprio account | Nessuna modifica o invito a CED/Admin/Super Admin | `test_ced_cannot_manage_privileged_or_unknown_accounts`, `test_self_and_admin_hierarchy`, `test_ced_user_management_api_boundaries` |
| Escalation e input ruoli | Ruoli privilegiati, ignoti e null rifiutati | `test_ced_cannot_assign_privileged_roles`, `test_admin_cannot_promote_standard_user_to_super_admin`, `test_ced_user_management_api_boundaries` |
| Accesso NAS/Network | API negate anche con flag residui nell'account CED | `test_ced_has_no_network_or_nas_even_with_stale_flags`, `test_ced_denials_are_atomic_and_inactive_sessions_are_rejected` |
| Autenticazione | Anonimo e account disattivato ricevono 401, token precedente inutilizzabile | `test_ced_denials_are_atomic_and_inactive_sessions_are_rejected`, regressione `test_auth.py`/`test_auth_service.py` |
| Persistenza e atomicita | Una richiesta negata non salva nome/stato/moduli; create negato non lascia utenti | `test_ced_denials_are_atomic_and_inactive_sessions_are_rejected`, regressione repository in `test_user_management.py` |
| PATCH moduli | Stessi query parameter/default; rifiuto dei moduli riservati e dei target privilegiati | `test_ced_user_management_api_boundaries`, `test_admin_users_lifecycle_and_module_flags` |
| Permessi di sezione | Catalogo/risolti leggibili; override e modifiche sezioni riservati agli admin | `test_section_management_preserves_admin_boundaries_for_ced`, unit `section permissions and QGIS credentials remain administrative` |
| QGIS e stato account | Credenziali non gestibili da CED; disabilitazione GIS/account revoca accesso esistente | `test_ced_user_management_api_boundaries`, `test_qgis_desktop_access_revoked_when_gis_or_account_is_disabled` |
| Inviti/errori/validazione | Attivazione e URL pubblico invariati; duplicati/not-found/invalidi gestiti | `test_user_invite_activation_flow`, `test_user_invite_uses_configured_public_frontend_url_even_with_internal_origin`, `test_admin_user_error_paths`, `test_user_schema_validators_reject_invalid_input_and_accept_optional_update_email`, suite pagina utenti |
| UI e navigazione | Account privilegiati filtrati; NAS/Rete e ruoli privilegiati assenti dall'editor; override readonly e QGIS nascosto | unit `CED manages standard users without NAS, Network or privileged roles`, `CED can manage GAIA users without NAS or network access` |
| Browser E2E | CED apre/crea standard senza NAS; viewer non apre la gestione | `gaia-users-ced.spec.ts` (2 casi): aggiunti, ma NON verificati per errore di lancio Chromium |

## Test aggiunti/modificati e risultati finali

- Estesi `test_ced_policy.py` con ciascun modulo delegabile e
  `test_user_management.py` con atomicita, create negati, flag residui,
  autenticazione anonima e disattivazione. Corretta l'aspettativa del nuovo test:
  GAIA rifiuta gli inattivi con 401, non 403.
- Estesa la policy UI con verifica di rifiuto reviewer/viewer negli override;
  aggiunto `frontend/tests/e2e/gaia-users-ced.spec.ts` con due flussi sintetici.
- Core CED: **69 passed** nelle tre suite policy/utenti/sezioni, comando completo
  con coverage e gate 100% superato, 75,77 s.
- Regressione backend: **102 passed** in auth, auth service, permissions API/service,
  bootstrap admin e Network API, 92,52 s. Totale finale distinto: **171 test**.
- Frontend globale sullo snapshot verificato: **257 suite, 3361 test passati**,
  321,63 s. Regressione mirata successiva: **10 suite, 106 passati**, 10,99 s.
- `npm test`: smoke passato. Tooling qualità: **90 passed**.
- Due tentativi backend estesi in un singolo comando sono terminati in timeout;
  non conteggiati come successi. La verifica finale usa le suite separate sopra,
  completate. Il runner temporaneo con selector limitato resta esterno al repo.
- Warning backend: chiave JWT breve della fixture esistente; nessun nuovo
  warning applicativo introdotto. Nessun servizio SMTP reale o dato di produzione
  usato dai test; integrazioni email/QGIS caratterizzate con mock esistenti.

## Coverage finale

Misura per intero dei file runtime del ciclo, non solo delle righe aggiunte.

| Runtime backend | Statement | Branch |
| --- | ---: | ---: |
| `app/api/router.py` | 50/50 | 0/0 |
| `app/models/application_user.py` | 53/53 | 2/2 |
| `app/modules/accessi/router.py` | 21/21 | 0/0 |
| `app/modules/accessi/routes/admin_users.py` | 109/109 | 14/14 |
| `app/modules/accessi/routes/section_permissions.py` | 76/76 | 14/14 |
| `app/modules/accessi/user_management_policy.py` | 41/41 | 26/26 |
| `app/schemas/users.py` | 130/130 | 8/8 |
| `app/services/permission_resolver.py` | 72/72 | 22/22 |
| **Totale** | **552/552 (100%)** | **86/86 (100%)** |

Frontend: **459/459 statement, 481/481 branch, 184/184 funzioni, 404/404 linee**,
tutti al 100% sui quattro file runtime CED. Nessuna linea runtime o branch
scoperto. Le due righe escluse dal default coverage Python sono le preesistenti
righe 10–11 `TYPE_CHECKING` del modello, solo typing e non runtime; nessuna
nuova esclusione o direttiva ignore aggiunta. Per limitare il costo del report
backend si usa una configurazione temporanea con i soli otto file del gate;
misurazione branch e soglia 100%, configurazione versionata invariata.

## Code quality, build e regressioni

- Ruff runtime/test CED e formatter dei due Python nuovi: PASS; naming, errori
  espliciti 401/403/404/409/422 e controllo prima dei side effect verificati.
  Nessun dead code nuovo; parametro DB inutilizzato rimosso. Liste frontend/backend
  rispecchiano lo stesso contratto; il backend e l'autorita di autorizzazione.
- Typecheck completo senza incremental: PASS. ESLint mirato: PASS.
  ESLint globale: exit 0 con **36 warning preesistenti fuori scope**.
- `npm run build:clean` nel workspace: FAIL per EACCES nella cache `.next`.
  La stessa build pulita in copia isolata `/tmp`, con configurazione PostCSS e
  dipendenze identiche, **PASS**, incluse le route `/gaia/users`.
  I quattro runtime frontend CED sono stati confrontati byte per byte con la copia.
- E2E: **2 falliti prima delle asserzioni**, al lancio Chromium: `shutdown:
  Operation not permitted`, SIGTRAP. Non costituiscono verifica del comportamento
  browser; non e stata modificata la sandbox o la configurazione Playwright.
- Ratchet autorevole contro `origin/main`, merge-base `6b61fd27`: FAIL per i
  tre rilievi preesistenti documentati sopra. Nessuna nuova violation error-level
  nel codice nuovo. `check_user_payload`: ciclomatica 13, cognitiva 16;
  `check_delegated_modules`: 7/13; `check_managed_user`: 9/11.
  Pagina utenti: 161/178; renderer: 65/64; `getModuleSections`: 26/49.
  Resta debito legacy; nessun refactoring esteso o trasferimento di violation.
- `make lint-backend`: compilazione PASS, ratchet Ruff FAIL per import I001 in
  `backend/tests/test_presenze_operations_postgres.py:3`, estraneo al ciclo.
  `baseline-verify`: false sul checkout concorrente; baseline non aggiornata
  per assorbire debito. Non dichiarata conformita globale.
- Nessuna regressione funzionale rilevata nelle suite completate. Le modifiche
  concorrenti successive allo snapshot non sono incluse in questa garanzia.

## Documentazione, Graphify e working tree

Aggiornati README, PRD e implementation plan di piattaforma; PRD, implementation
plan, execution plan, PROGRESS, architettura e questo report del dominio Accessi.
Le attivita implementative sono marcate completate; gate globale e deploy restano
residui. La documentazione tecnica descrive API, limiti di delega e persistenza.

Graphify code aggiornato con i target dedicati e `--force` per pruning dei
riferimenti rimossi. Snapshot misurato: backend 9861 nodi/25121 archi;
frontend 7270/17519. Gli ultimi refresh code forzati terminano con exit 0,
senza ulteriori cambiamenti di topologia. Refresh finali docs tramite target
piattaforma e dominio: **1/1 e 2/2 chunk semantici falliti**, rispettivamente,
con `Connection error` e warning di risultati parziali, pur con exit 0.
I grafi risultanti hanno 2297/5248 e 1651/2954 nodi/archi, ma non costituiscono
un aggiornamento semantico completo. Artefatti ignorati e non versionati.

Working tree inizialmente con 107 entry; snapshot finale intermedio con 122
e controllo conclusivo con 123 (`gaia-ced-final-status-close.txt`),
comprendenti molte modifiche concorrenti estranee. HEAD e avanzato tramite
commit esterni da `af768d77` a `655c6e78` e `6bddef61`; questo ciclo non crea
commit. Escluse dalla responsabilita CED le modifiche di Presenze, Dotazioni,
Organigramma, Wiki, cruscotto operatori, sicurezza HTTPS e tooling concorrente.
Il package-lock era gia modificato; nessun install o cambio di dipendenze,
configurazioni coverage/lint/Next/Playwright/CI effettuato. Il controllo
`git diff --check` del perimetro CED passa; nessun artefatto generato non
tracciato trovato nelle directory coverage/Graphify/Next/Playwright.
Log, build isolata,
runner, report e trace temporanei restano sotto `/tmp/gaia-ced-close-*`.

Evidenze autorevoli: `close-core.log/json`, `close-regression.log`,
`close-frontend.log`, `close-frontend/coverage-final.json`, `close-scoped.log`,
`close-build-isolated.log`, `close-e2e.log`, `close-ratchet-final.json`,
`close-lint-backend.log`, `close-lint-all.log`, `close-types-final.log`,
`close-quality.log`, `close-graph-*.log` e snapshot
`gaia-ced-final-status-*.txt` sotto `/tmp`.

## Residui e criterio di chiusura

1. Eseguire i due E2E CED in un ambiente che consenta il lancio Chromium.
2. Risolvere ownership/cache `.next` per la build canonica del workspace.
3. Chiudere i rilievi di lint e ratchet con interventi separati e ownership
   appropriata; non incorporare modifiche concorrenti o rigenerare baseline qui.
4. Completare arricchimento Graphify docs con provider raggiungibile e verificare
   `chunk N/N done`, senza warning di risultati parziali.
5. La distribuzione e la verifica operativa su `gaia.lan` restano fuori scope.

## Riesecuzione finale — 2026-10-02

Checkout `c4fa269c`, 158 entry nel working tree condiviso. I quattro file
runtime frontend CED risultano byte per byte identici alla precedente build
isolata; nessuna feature, dipendenza, esclusione coverage o configurazione
versionata modificata in questa riesecuzione. Matrice, API e contratto di
architettura sopra restano validi. Nuovi componenti concorrenti restano fuori
scope; gli esiti storici non sostituiscono i controlli seguenti.

- Backend CED: **69 passed**, 552/552 statement e 86/86 branch (**100%**).
  Regressione auth/permessi/bootstrap/Network: **102 passed**. Stesso runner
  temporaneo esterno al repository, senza cambiamenti al runtime.
- Frontend CED e regressioni mirate: **10 suite, 106 passed**, 459/459 statement,
  481/481 branch, 184/184 funzioni e 404/404 linee (**100%**). Il primo comando
  senza `VITEST_COVERAGE_INCLUDE` ha eseguito correttamente i 106 test ma fallito
  la soglia su moduli estranei selezionati dal merge-base; ripetuto usando la
  variabile di scope gia prevista dalla configurazione, senza modificarla.
- Suite frontend completa: **3661 passed, 3 failed**, 266 suite verdi e 3 rosse.
  I tre errori sono timeout a 5000 ms in `catasto-gis-page.test.tsx:261`,
  `presenze-giornaliere-page.test.tsx:949` e `ruolo-tributi-page.test.tsx:1657`.
  Sono test fuori scope CED: non corretti ne considerati regressioni escluse
  per assunzione. Il regression gate completo resta rosso.
  Riesecuzione delle sole tre suite con `--maxWorkers=1`: **264 passed** in
  38,94 s, senza aumentare timeout o cambiare test. Questo caratterizza la
  sensibilita al carico/concorrenza, ma non rende verde il comando completo.
- `npm test`, typecheck completo senza incremental, ESLint mirato e Ruff
  sugli esatti file CED: **PASS**. Lint frontend globale: exit 0, **36 warning**.
  Tooling qualita: **90 passed**. Un controllo Ruff esteso per errore all'intero
  dominio Accessi ha trovato 37 rilievi legacy fuori scope; il successivo
  controllo esatto del perimetro CED e passato, senza modificare quei file.
- `make lint-backend`, con interprete virtualenv nel PATH: **FAIL**, I001 in
  `backend/tests/test_presenze_operations_postgres.py:3`; compilazione passa.
  Ratchet CED contro il merge-base autorevole: **FAIL**, stessi tre rilievi:
  callback `useEffect` LOC 30, renderer ciclomatica 65 e cognitiva 64.
  Nessuna baseline aggiornata per nascondere le failure.
- `npm run build:clean`: **FAIL**, permessi della cache `.next` ancora errati.
  La precedente build isolata resta evidenza del codice CED invariato, non
  una build completa del nuovo checkout concorrente.
- E2E CED: **2 failed prima delle asserzioni**, stesso errore Chromium
  `shutdown: Operation not permitted`, SIGTRAP. Comportamento browser non
  verificato; nessuna modifica alla sandbox o ai timeout dei test.
- Graphify code forzato: **PASS**, backend **9883 nodi/25173 archi**,
  frontend **7358/17726**; include lo stato del corpus condiviso corrente.
- Graphify docs: refresh finali eseguiti tramite i target dedicati,
  **1/1 chunk piattaforma e 2/2 chunk dominio falliti** per `Connection error`.
  Exit 0 con warning `Partial results returned`, quindi **non verificato**
  l'arricchimento semantico finale. Grafi parziali: piattaforma 2297/5248
  nodi/archi, domini 1651/2953. Artefatti ignorati, non versionati.
- Working tree: snapshot in `/tmp/gaia-ced-recheck-status-final.txt`.
  Modifiche concurrent/untracked preservate; nessun commit o deploy eseguito.
  Artefatti di questa riesecuzione in `/tmp/gaia-ced-recheck-*`.
  `git diff --check` del perimetro CED passa; nessun artefatto generato non
  tracciato trovato nelle directory coverage/Graphify/Next/Playwright.

Le nuove failure della suite completa si aggiungono ai residui gia elencati;
non e possibile dichiarare assenza globale di regressioni o chiusura PASS.

## Riverifica senza sandbox — 2026-10-02

Filesystem e rete non piu limitati. Checkout iniziale `c4fa269c`, finale
`368731e9` per commit concorrente esterno; working tree da 158 a 160 e infine
158 entry. Nessun commit, deploy o intervento sui servizi Docker effettuato.
Scope, matrice funzionalita/test, contratti API e architettura sopra confermati.

### Risultati aggiornati

- Backend: **171 passed**, coverage **100% statement e branch** sugli otto
  runtime del ciclo (552/552 e 86/86), 196,49 s. Comando standard pytest
  iniziale terminato per timeout a 240 s; non contato come successo. La
  riesecuzione usa il runner temporaneo gia documentato, esterno al repository.
- Frontend mirato: **10 suite, 106 passed**, coverage **100% statement, branch,
  funzioni e linee** sui quattro runtime (459/459, 481/481, 184/184, 404/404).
- Frontend completo con `--maxWorkers=2`, senza cambiare timeout o config:
  **3677 passed, 1 failed**, 268 suite verdi/1 rossa, 401,17 s. Timeout a
  5000 ms in `ruolo-tributi-page.test.tsx:1112`, test `loads detail and submits
  payment, status and note`. Riesecuzione della suite isolata: **44 passed**,
  14,62 s. Il comando completo resta rosso; non dichiarata assenza globale
  di regressioni. Carico concorrente osservato, senza interrompere altri job.
- E2E: Chromium ora parte. Primo tentativo fallito per server assente sulla
  porta 8080. Dopo avvio di Next production dalla build isolata, viewer passa;
  CED rivela due difetti nel test: mock presenza sul path errato e locator
  della select. Corretti esclusivamente in `gaia-users-ced.spec.ts`: endpoint
  `/api/auth/presence/summary` e selezione tramite ruolo accessibile `combobox`.
  Riesecuzione finale: **2 passed**, 2,4 s, incluse creazione standard, assenza
  NAS/Rete/ruoli privilegiati e diniego viewer. API mockate, nessun dato reale
  creato; il backend e verificato separatamente. Server temporaneo arrestato.
- `npm run build:clean` in copia nuova del checkout sotto `/tmp`: **PASS**,
  Next 15.5.25, incluse le route utenti; confronto byte per byte conferma
  identita dei quattro runtime CED con il checkout finale. La cache condivisa
  `.next` conserva ownership mista, incluso `root`; la build canonica in-place
  non e ripetuta per non alterare la cache dei servizi concorrenti. Il relativo
  residuo operativo non viene dichiarato risolto.
- `npm test`, typecheck senza incremental, Ruff esatto sul perimetro CED:
  **PASS**. Lint frontend globale: exit 0, **36 warning fuori scope**.
- `make lint-backend`: **FAIL**, stesso import I001 in
  `backend/tests/test_presenze_operations_postgres.py:3`; compilazione passa.
  Ratchet mirato: **FAIL**, stessi tre rilievi preesistenti: callback LOC 30,
  renderer ciclomatica 65/cognitiva 64. Nessun refactoring estraneo, nuova
  esclusione o aggiornamento baseline per aggirare il gate.
- Graphify codice: target dedicati con `--force` **PASS**, nessun ulteriore
  cambiamento di topologia. Graphify docs: **PASS**, piattaforma `chunk 1/1
  done`, dominio `chunk 1/2 done` e `chunk 2/2 done`, nessun warning di chunk
  falliti. Grafi al termine dell'estrazione: piattaforma **2306/5265** e
  dominio **1721/3091** nodi/archi. Refresh finale del report tramite target
  dominio dedicato; grafi ignorati e non committati.
- Report aggiornato, nessun nuovo runtime o dipendenza introdotto. Modifiche
  concorrenti preservate; `git diff --check` del perimetro CED passa. Nessun
  artefatto coverage/Graphify/Next/Playwright non tracciato nel working tree.
  Evidenze e snapshot: `/tmp/gaia-ced-unrestricted-*`.

### Residui attuali

E2E e connettivita Graphify non sono piu bloccanti. Restano il lint backend
globale, il ratchet, la failure della suite frontend completa e la ownership
della cache della build canonica. Coverage runtime del ciclo al 100%; debito
di complessita legacy invariato. Questi residui impediscono il PASS globale.

## Preparazione commit CED — 2026-10-02

Commit richiesto esplicitamente dall'utente, senza trasformare il gate FAIL
in PASS. Indice temporaneo separato per preservare anche le modifiche
concorrenti gia staged. Selezione di 28 file CED; dai file condivisi sono
esclusi schema, migrazione, route, UI e test Dotazioni, link Wiki MCP e note
del cruscotto operatori. I relativi cambiamenti restano nel working tree.

Le misure delle riverifiche precedenti riguardano il checkout condiviso,
comprendente anche quelle integrazioni. Per certificare il contenuto
effettivamente selezionato viene esportato l'indice in una copia isolata:
typecheck e build pulita superati; 105 test frontend mirati verdi con
coverage 100% (457 statement, 480 branch, 183 funzioni, 402 linee).
La prima selezione backend includeva ancora un test specifico Dotazioni:
rilevato durante la verifica, escluso dall'indice CED e rieseguito il gate.
Risultati conclusivi della selezione isolata: **169 test backend passati**,
coverage **546/546 statement e 86/86 branch (100%)**, **105 test frontend**
passati e **2 E2E passati** sulla build production del contenuto selezionato.
Typecheck, build pulita e Ruff mirato superati; nessun timeout aumentato o
esclusione coverage aggiunta. La differenza rispetto ai 171/106 test del
checkout condiviso deriva dall'esclusione dei test Dotazioni.
Evidenze in `/tmp/gaia-ced-commit-*`, in particolare `backend-final.log/json`,
`frontend.log`, `types.log`, `build.log`, `e2e.log` e `ruff.log`.
Nessuna dipendenza del commit CED da file non tracciati di altri domini.
Il deploy e la risoluzione dei residui globali restano fuori dal commit.

**FINAL QUALITY GATE — FAIL**
