# Dotazioni — verifica finale

Esito corrente della change isolata al 2026-10-03: **PASS**, documentato in
`GATE_CLOSURE_2026-10-03.md`. Le failure globali riportate sotto sono evidenze
storiche; la baseline globale Wiki/MCP resta un limite distinto non assorbito.

Data: 2026-10-01. Scope: MVP Dotazioni, piattaforma, permessi, UI, migration
e docs. Inventory invariato. Working tree e HEAD cambiano anche per lavoro
concorrente: questo report non certifica modifiche estranee.

Aggiornamento 2026-10-02: cruscotto operatori ora integrato; il rinvio
descritto nelle evidenze storiche sotto e superato dall'implementazione e
caratterizzazione documentate in `CRUSCOTTO_VALIDATION.md`. Il gate globale
non viene automaticamente certificato dal superamento dei test mirati.

## Implementato e architettura

Asset del Consorzio, codice immutabile, tipologia estensibile, assegnazione
OrgUnit, presa/restituzione/passaggio atomici, storico/audit append-only,
filtri persona/unita, link Network/Vehicle e rotta QR autenticata.
Backend in `backend/app/modules/dotazioni/`, frontend in
`frontend/src/app/dotazioni/` con componenti in `frontend/src/features/dotazioni/`.
Riutilizzati OrgUnit/ApplicationUser; nessun Team o database parallelo.
Network non implica custodia; operativita mezzi in Operazioni.
Nessuna dipendenza nuova, nessun dato Inventory migrato.

## Matrice funzionalita → comportamento → test

Backend: `backend/tests/dotazioni/`, salvo indicazione.
UI: `frontend/tests/unit/`; browser: `frontend/tests/e2e/`.

| Funzionalita | Comportamento atteso | Test |
| --- | --- | --- |
| Creazione/modifica/assegnazione | Persistenza, audit, OrgUnit canonica | `test_api.py::test_lifecycle_and_audit`; `dotazioni-components.test.tsx` |
| Codice/tipo | Normalizzazione prima del pattern | `test_regressions.py::test_code_normalization_and_inactive_unit` |
| Input/riferimenti | 422 senza scritture | `test_regressions.py::test_create_rejects_invalid_input_without_writes`; `test_api.py::test_links_and_validation` |
| Presa | Utente/asset attivi, una custodia | `test_api.py::test_lifecycle_and_audit`; `test_conflicts_and_permissions` |
| Restituzione | Storico conservato, stato fisico preservato | `test_api.py::test_lifecycle_and_audit`; `test_missing_inactive_and_history` |
| Passaggio | Transazione unica e precedente custode | `test_api.py::test_lifecycle_and_audit`; `test_regressions.py::test_server_failure_rolls_back_transfer_and_audit` |
| Concorrenza/migration | Prese concorrenti 200/409, vincolo DB, upgrade/downgrade | `test_postgres.py::test_migration_and_concurrent_take` |
| Asset libero/conflitti | 409 per azioni incoerenti | `test_api.py::test_no_open_custody`; `test_conflicts_and_permissions` |
| Permessi | Deny override, assign distinto | `test_regressions.py::test_user_override_denies_read`; `test_reassignment_requires_distinct_permission` |
| Membership | Appartenenza attiva e valida temporalmente | `test_regressions.py::test_expired_future_or_disabled_membership_cannot_take` |
| Storico/persistenza | Paginazione, gestione custode inattivo | `test_regressions.py::test_persistence_closed_holder_and_history_pagination` |
| Viste persona/unita | Filtri e conteggi coerenti | `test_api.py::test_filters_and_database_constraint`; `dotazioni-pages.test.tsx`; `dotazioni-workflows.test.tsx` |
| Network/Vehicle | FK valide, no custodia tecnica/mezzo duplicata | `test_api.py::test_links_and_validation`; `dotazioni-pages.test.tsx` |
| Client API/errori | Token, URL codificati, errori HTTP/JSON | `dotazioni-api.test.ts`; `dotazioni-workflows.test.tsx` |
| UI amministrativa | Creazione/edit/disattivazione, loading/errori | `dotazioni-components.test.tsx`; `dotazioni-pages.test.tsx` |
| UI operatore/QR | Conflitto, presa/passaggio/restituzione, storico e QR | `dotazioni.spec.ts::custody lifecycle and stable QR route preserve history` |
| Browser fail-closed | Senza permesso nessuna API asset/azione | `dotazioni.spec.ts::missing section permission blocks custody and asset reads` |
| Piattaforma | Flag utenti, bootstrap, navigazione | `backend/tests/test_user_management.py`, `test_bootstrap_admin.py`, `test_section_permissions.py`; UI `gaia-users-page.test.tsx`, `layout-navigation.test.ts`, `sidebar-mobile-drawer.test.tsx` |

## Correzioni di verifica

- Corretto `schemas.py`: Pydantic controllava pattern prima di trasformazione
  maiuscolo/minuscolo, rifiutando input validi documentati.
- Aggiunti 18 casi backend regressione (rollback dopo flush, permessi,
  membership, persistenza/input) e package test per import helper condivisi.
- Aggiunti due E2E Chromium con API simulate, senza dati operativi: non
  sostituiscono integrazione DB reale.
- Formattata e ordinati import della sola migration Dotazioni.
- Nessuna feature nuova, baseline/ignore nuovi o refactoring esteso.

## Risultati

- Backend dominio PostgreSQL incluso: 26 casi passati, 100% statement
  (445/445) e branch (78/78), zero esclusioni o linee mancanti.
- Backend piattaforma: 54 test passati, nove file runtime modificati al 100%
  statement (533/533) e branch (56/56), nessuna linea o branch mancante.
- Migration Dotazioni: coverage 100% statement (27/27) e branch (6/6)
  nel rerun PostgreSQL dopo la formattazione; nessuna esclusione.
- Frontend dominio/piattaforma: 86 passati, 100% statement (643/643),
  branch (621/621), funzioni (262/262), linee (551/551).
- Suite frontend completa ripetuta: 252 file, 3098 test passati. Primo run:
  un errore `protected-page.test.tsx`, non riprodotto nei 20 test isolati
  ne nel rerun completo senza modifiche: possibile flakiness, non prova
  di failure preesistente.
- `npm test`: passato. Typecheck/ESLint mirato passati. Browser: 2/2 passati.
- Build pulita via `./scripts/frontend_clean_build.sh`: passata. Build locale
  bloccata da cache root-owned; lo script costruisce in container e avvia
  frontend/backend e dipendenze. Nessuna migration operativa applicata.
- Ruff mirato e format-check file nuovi/migration: passati.
- Alembic unica head `20261001_1600`, parent `20261001_1400`.
  Upgrade/downgrade/re-upgrade provati in schema PostgreSQL temporaneo.
- Suite backend globale: FAIL e non completata. Primo run invalido per
  plugin anyio non caricato; ripetizione corretta con `-p anyio` interrotta
  esplicitamente dopo il fallimento osservato, circa al 35% del run.
  `test_anpr_service.py::test_get_stats_reports_deceased_kpis` fallisce per
  `app.modules.utenze.router.settings` assente. Riprodotto sia isolatamente
  nel working tree sia su archivio pulito di HEAD `11325336`: preesistente
  alla change non committata Dotazioni. Non corretto il dominio estraneo.
  L'assenza di ulteriori regressioni backend globali NON e certificata.
- `git diff --check`: passato. Nessun nuovo warning significativo Dotazioni;
  nei test piattaforma/globali compare `InsecureKeyLengthWarning` JWT (chiave
  locale 21 byte, minimo raccomandato 32). Non modificate credenziali/config.

Coverage aggregata `--cov=backend/app` non equivale alla coverage del perimetro:
i file runtime modificati sono verificati separatamente. Log completi in
`/tmp/dotazioni-final-*.log`, JSON coverage/ratchet nello stesso percorso.

## Code quality

Ratchet nuovo dominio: zero finding contro merge-base `6b61fd27`, scanner
completo e indice Git temporaneo per file nuovi. Indice reale invariato.
Ambiguita precedenti dipendevano da scansione parziale/untracked, non risolte
rinominando callback o cambiando baseline.

Ratchet piattaforma: FAIL, 13 finding. Direttamente collegati al ciclo:
`create_application_user` LOC 28→29; `ensure_default_sections` ciclomatica
3→4/cognitiva 3→5/LOC 13→19; `ensure_bootstrap_admin` LOC 44→46; callback
editor utenti LOC 29→30. Altri confronti includono differenze storiche dopo
merge-base: non tutti attribuiti a Dotazioni. Nessuna baseline aggiornata.
UI nuova: massimi ciclomatica 13/cognitiva 12, quattro warning sotto soglia
error; non equivale a PASS piattaforma. Nessuna evidenza di architettura
parallela o duplicazione di domini. Sicurezza testata con permessi/override
e fail-closed, non con penetration test dedicato.

`make lint-backend` con venv nel PATH e cache in /tmp: FAIL per I001 in
`backend/tests/test_presenze_operations_postgres.py`, estraneo a Dotazioni.
Senza venv/cache dedicata si aggiungono problemi ambientali. Non corretto
il file estraneo. Gate completo non chiuso; nessun refactor extra per nascondere
le regressioni di complessita.

## Working tree, file e residui

Scope: nuove cartelle backend/frontend/test/docs Dotazioni, migration,
router/metadata, modello/schema/repository utenti, bootstrap/resolver,
editor utenti, navigation/sidebar/tipi API, README/architettura/struttura docs,
export data-model, Makefile e target AGENTS.
Questa fase modifica validator, test regressioni/browser, formato migration
e documentazione. Inventory resta invariato. Il cruscotto era invariato nella
fase iniziale; e stato integrato successivamente il 2026-10-02.

Preservate modifiche concorrenti Wiki/MCP, Presenze, Ruolo, Elaborazioni,
programma code-quality e altre superfici frontend; non includerle in Dotazioni.
`frontend/package-lock.json` ha un flag dev fsevents, non una dipendenza
Dotazioni: fuori change. Artefatti Graphify/coverage/browser non versionati;
log e indice temporaneo in /tmp. Nessun commit eseguito.

Non implementati: policy capi limitata al sottoalbero, immagini QR/PDF, pagina audit
dedicata e funzioni fuori MVP. Nessuna nuova funzione introdotta in verifica.

## Graphify e chiusura

### Rifinitura UI/UX successiva

Etichette italiane per stati e tipi noti, date `Europe/Rome` (test ora legale
e solare), nomi nel passaggio (`handover_from_name`, anche per utente inattivo),
feedback busy, touch target 44px e tabelle scorrevoli/focalizzabili.
Nessuna migration, cambiamento di autorizzazioni o duplicazione del dominio.
La vista squadra resta il filtro canonico con intestazione dedicata;
pagina squadra separata non introdotta; integrazione cruscotto successiva
documentata in `CRUSCOTTO_VALIDATION.md`.

Test UI aggiornati e nuovo `dotazioni-presentation.test.ts`: 42 passati,
100% statement (208/208), branch (158/158), funzioni (89/89), linee (166/166).
Backend dominio: 26 passati nel rerun con PostgreSQL reale, 100% statement
(447/447) e branch (78/78). Nessuna nuova migration o modifica di schema DB.
Ruff/format, typecheck/ESLint mirato passati. Ratchet nuovo dominio: zero
finding contro merge-base, scanner completo e indice temporaneo.
Browser Chromium: 2 E2E passati, inclusi viewport 390px, azione via Enter,
regione storico focalizzabile e assenza di overflow orizzontale della pagina.
Screenshot mobile/desktop ispezionati; dati tecnici raggruppati in disclosure
nativo per privilegiare custode, stato e squadra. Rerun browser dopo l'ultima
rifinitura: 2/2 passati, apertura/chiusura disclosure via Enter verificata.
Build pulita via script repository passata (warning legacy estranei a
Dotazioni restano); full frontend: 253 file e 3104 test passati; smoke 18/18.
I gate piattaforma/globali precedentemente bloccanti NON sono certificati
come risolti da queste modifiche UI.

Aggiornati i target codice Dotazioni/backend/frontend con `--force`: modulo
62 nodi/131 edge; backend/frontend aggiornati tramite target dedicati.
Docs Dotazioni e piattaforma: chunk 1/1 completato, nessuna semantic failure,
costi stimati rispettivamente $0.0069 e $0.0084 per il primo refresh finale.
Il report consolidato viene risincronizzato col target docs Dotazioni.
Gli artefatti Graphify restano ignorati e non vengono committati.

Controlli bloccanti: ratchet piattaforma, lint backend globale, regression
backend globale non completo. Il risultato resta FAIL anche se il dominio
nuovo e coperto al 100% e i gate mirati passano.
Serve decisione su slice dedicata per i gate, non baseline per assorbire finding.

FINAL QUALITY GATE — FAIL
