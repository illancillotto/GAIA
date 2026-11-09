# Eliminazione template con conferma — 7 novembre 2026

**Aggiornamento:** rilascio mirato CED completato alle 09:42:21 CET su successiva
autorizzazione dell'utente. I paragrafi seguenti registrano il collaudo locale
precedente al rilascio. Stato pubblicato, test della candidata/live e rollback:
[TEMPLATE_DELETION_RELEASE_2026-11-07.md](TEMPLATE_DELETION_RELEASE_2026-11-07.md).

## Stato e perimetro

Implementazione locale verificata. Nessun deployment, commit, cancellazione
di template reali, collegamento SMTP/IMAP o modifica di dati tributari.
Branch `feature/avvisi-solleciti-2021`, HEAD iniziale `2115dd7b`.
Le modifiche concorrenti agli altri moduli sono preservate.

Ogni versione in **GAIA Communications → Template versionati** ha il pulsante
**Elimina**. La conferma nativa del browser identifica nome, canale, codice e
versione e spiega la conservazione dello storico. Annullando non parte alcuna
richiesta. Durante la cancellazione i comandi della sezione sono disabilitati;
gli errori vengono mostrati e consentono di riprovare.

`DELETE /communications/templates/{id}` richiede un amministratore attivo e
`confirmed=true` nel body. Conserva la riga come `deleted`, la esclude dagli
elenchi e impedisce nuovi usi/approvazioni. Non modifica messaggi già composti,
PDF o autorizzazioni. Le altre versioni restano disponibili e la numerazione
include le versioni eliminate. Lock, refresh ORM e audit condividono la
transazione: richieste ripetute/concorrenti non duplicano `template_deleted`.
Nessuna migrazione o dipendenza aggiuntiva.

## File del ciclo

Runtime: `backend/app/modules/communications/{admin,registry,schemas}.py` e
`frontend/src/components/communications/admin-templates.tsx`.

Test: nuovo `backend/tests/communications/test_template_deletion.py` (17 casi),
un test concorrente in `test_postgres.py`, sei casi in
`frontend/tests/unit/communications/admin.test.tsx`, contratto DELETE in
`api.test.ts` e nuovo `frontend/tests/e2e/communications-template-deletion.spec.ts`
(desktop/mobile). Preservate le modifiche preesistenti negli stessi file.

Aggiornati PRD, API_CONTRACT, DATA_MODEL, OPERATIONS, IMPLEMENTATION_PLAN,
PROGRESS, CHANGELOG e TEST_REPORT.

## Matrice comportamento → test

| Comportamento | Test pertinente |
| --- | --- |
| Singola versione PEC/email, draft/approved, altre versioni preservate | `test_delete_hides_only_selected_version_and_is_idempotent`, quattro combinazioni |
| Conferma con identità; Annulla senza richieste | unit `asks confirmation before deleting…`, due E2E |
| DELETE confermato, azioni disabilitate, elenco aggiornato | unit `deletes only the confirmed version…`, `api.test.ts`, E2E |
| Conferma mancante/falsa/stringa o campi extra rifiutati | `test_delete_requires_explicit_confirmation_without_extra_fields` |
| Viewer, inattivo e richieste senza token rifiutati | `test_delete_requires_admin…`, `test_delete_missing_identity…` |
| Permessi amministrativi esistenti indipendenti da sezioni Ruolo | `test_delete_preserves_existing_admin_access_independent_of_ruolo_sections` |
| UUID invalido/identità assente:422/404 | `test_delete_missing_identity_invalid_uuid_and_unauthenticated` |
| Audit fallito: rollback | `test_delete_rolls_back_status_if_audit_cannot_be_saved` |
| Ripetizione/parallelismo: un evento con attore/versione/stato precedente | test API idempotenza e `test_concurrent_template_deletions_keep_one_audit_event` su PostgreSQL reale |
| Eliminato non utilizzabile/approvabile; numerazione monotona | test API idempotenza e conservazione messaggio |
| Messaggi draft/submitted e PDF byte-per-byte preservati | `test_delete_preserves_existing_message_and_exact_snapshot`, due stati |
| Errori DELETE/reload e retry | unit `keeps the template…`, `reports a failed reload…`, E2E errore409 |
| Creazione/versionamento/approvazione preesistenti | `test_outbox_api.py`, `admin.test.tsx`, suite Communications |
| PDF, checklist, dispatch sintetico PEC/email | quattro E2E preesistenti `communications.spec.ts` |

## Verifiche eseguite

| Controllo | Risultato |
| --- | --- |
| Backend `coverage run --branch --source=app -m pytest tests/communications -q` | 197 PASS, zero skip; inclusi dieci test PostgreSQL reali |
| Tre runtime backend modificati | 267/267 statement, 36/36 branch:100%, zero righe mancanti/escluse |
| Frontend unit Communications | 63 PASS in otto file |
| Coverage intero `admin-templates.tsx` | 35/35 statement, 18/18 branch, 15/15 funzioni, 25/25 righe:100% |
| `npm test` | 18 smoke PASS |
| `npm run typecheck` | PASS |
| ESLint runtime e tre test frontend del ciclo | PASS, nessun warning sui file verificati |
| Ruff sui tre runtime backend e due test | PASS; format-check del test nuovo PASS |
| `make lint-backend QUALITY_PYTHON=backend/.venv/bin/python BASE_REF=main` | FAIL per import/style in tre file Presenze estranei; file del ciclo puliti |
| `npm run build:clean` | PASS in copia isolata, runtime UI identico al checkout |
| Playwright sulla build ottimizzata | 6 PASS: due nuovi e quattro di regressione, API sintetiche |
| Diff whitespace dei file del ciclo | PASS |
| Ratchet completo contro merge-base `main` | FAIL:17 finding Presenze concorrenti, nessuno nei quattro runtime del ciclo |

PostgreSQL usa il container dedicato `gaia-template-delete-test-20261107`,
database `communications_test` e schemi temporanei. Trasporto disabilitato,
provider mock e credenziali esclusivamente sintetiche. Due warning `runpy`
nei test worker/health preesistenti. Build con warning nei moduli estranei
e rilevamento lockfile `/tmp`; lint del perimetro pulito.

Primi tentativi conservati: corrette assunzioni dei nuovi test sul roundtrip
delle date SQLite e sui privilegi admin delle fixture. Primo avvio PG fallito
con `psycopg2` non installato: corretto a `psycopg`, già previsto dal progetto.
Due failure E2E iniziali dovute al selettore alert ambiguo con il route
announcer Next.js: selettore ristretto alla sezione template. Nessuna
correzione runtime o esclusione coverage richiesta da queste failure.

## Complessità e architettura

Admin/registry/UI:36→40 callable, zero errori prima/dopo.
`TemplateAdministration`: cognitiva9→13, ciclomatica9→12, LOC26→35;
un warning ciclomatico sotto la soglia errore15. Handler UI `remove`:4/4;
servizio `delete_template`:2/3. Responsabilità nei moduli/componenti esistenti;
nessun refactoring estraneo, cambiamento worker/trasporto o schema DB.

Il ratchet completo è autorevole. Il tentativo con corpus parziale produceva
un matching spurio di `allowed` e non viene usato come evidenza. Nel report
completo i 17 finding riguardano solo Presenze. Baseline e soglie invariate;
nessuna dichiarazione di PASS globale o di esecuzione dell'intera suite GAIA.
Il lint backend globale rileva import non ordinati in
`presenze/router/helpers/daily_records.py` e `presenze/services/gate_mobile_payloads.py`,
oltre alla formattazione di `tests/test_presenze_team_organization.py`.
Questi file erano già modificati all'inizio del ciclo e restano fuori scope.

Graphify codice backend/frontend aggiornati tramite target dedicati.
Backend: nuova funzione `registry.delete_template` e API nel grafo.
Frontend: nessun cambiamento di topologia, i callback interni non sono nodi
autonomi del parser. Artefatti `graphify-out` non versionati.
Graphify documentazione piattaforma eseguito con il target dedicato:
chunk1/1 completato, nessun semantic chunk fallito; 9 file riestratti,
17.616 token input e 3.181 output (stima costo USD0,0121).

## Evidenze e residui

Log, coverage JSON, metriche prima/dopo, build, screenshot, trace iniziali e
hash runtime: `/tmp/gaia-template-delete-20261107/`.

Rilascio non eseguito; nessuna migrazione necessaria. I 17 finding globali
estranei restano nel rispettivo ciclo. Nessun provider reale verificato.
