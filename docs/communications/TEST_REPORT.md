# Report di collaudo — 2026-11-03

Le evidenze sono locali e sintetiche: nessun messaggio reale, credenziale
provider, dato tributario di produzione o deployment. Non equiparare i mock
alla verifica di una casella reale.

## Prove già eseguite

| Perimetro | Esito |
| --- | --- |
| Communications backend e registrazione API/ORM, incluse sette prove PostgreSQL | 123 PASS, statement/branch100%,1548statement/316branch |
| Frontend nuovo e workspace Solleciti, Vitest | 89 PASS, statement/branch/function/line100%, 548statement,355branch,204funzioni,378righe |
| Suite frontend completa | 349file,5468test PASS, maxWorkers2 |
| Regressione backend Ruolo | 1090PASS,407SKIP; skip preesistenti richiedono servizi/fixture PostgreSQL specializzate |
| Chromium PDF.js reale, API sintetiche | 4PASS, PEC/email desktop1440/mobile390, tre pagine, zoom, checklist, approvazione e dispatch simulato, zero pageerror/overflow |
| Build Next produzione | PASS,169pagine; warning legacy separati, nessun errore nuovo |
| Docker Compose overlay config --quiet | PASS con valori sintetici, nessun avvio |
| Ratchet contro merge-base main | PASS, finding0; baseline non ancora sincronizzata |
| Graphify codice backend/frontend/Ruolo | Aggiornato con target dedicati |

## Copertura e integrazioni

Test backend: snapshot/hash e MIME identici, sorgente rigenerata/pagamenti/
annualità/storico/Poste bloccanti, review/checklist/versione/RBAC, account e
template, TLS/password/OAuth2, CMS sintetico realmente firmato e verificato con
OpenSSL, PEC fuori ordine/duplicate/non correlate, DSN/bounce, errori sicuri,
timeout incerti, crash/recovery/lease, pause/rate/heartbeat. La verifica CMS con
certificato sintetico non verifica trust o formato effettivo di un gestore.

PostgreSQL usa esclusivamente DB communications_test e schemi usa-e-getta:
compare_metadata ORM/migration, roundtrip vuoto, trigger immutabili, mutex reale,
claim/fence, gara con Poste. SQLite non viene usato per dimostrare lock PG.

Frontend unit: renderer con contratti PDF.js mockati, lifecycle/cleanup, controlli,
errori e permessi. E2E: PDF.js reale dalla build, PDF sintetico tre pagine,
API intercettate. Non è un test CED o end-to-end SMTP/provider.

## Tentativi falliti e correzioni

I primi test avevano copertura incompleta (80–95%). Nuove prove hanno completato
statement e branch, senza esclusioni. Fixture di scheduling/flush corrette;
un test PG aveva account_id rinominato erroneamente durante il lint, poi
corretto e da ricertificare nella corsa finale. Tentativi di esecuzione con cwd
errata o dipendenza ReportLab assente non sono considerati PASS; il PDF fixture
è prodotto con pypdf già disponibile. Prime URL provider404, poi guide ufficiali
aggiornate HTTP200, riportate in OPERATIONS.

## Limiti

Suite globale backend fuori Ruolo non ancora eseguita; nessuna dichiarazione
di regressione dell'intero monorepo. Skip Ruolo non diventano PASS. Warning
JWT dei secret sintetici e runpy dei test CLI non indicano uso di credenziali
reali. Per la produzione: collaudo provider, restore, grants/NAS/firewall,
carico, CA/pin e decisioni dell'ufficio restano obbligatori.

## Riproduzione

Dalla directory backend: pytest tests/communications con
COMMUNICATIONS_TEST_POSTGRES_URL verso DB isolato denominato communications_test,
pytest-cov branch e soglia100, source app e report limitato ai file Communications,
app/api/router.py e app/db/base.py. SQLite temporaneo per API; PG reale per lock.

Dalla directory frontend: VITEST_COVERAGE_INCLUDE con tutti i runtime
components/communications, lib/communications-api.ts, tre pagine nuove e
components/ruolo/solleciti/workspace.tsx; vitest tests/unit/communications
tests/unit/notice-solleciti-page.test.tsx --maxWorkers=2 --coverage.
Nessuna esclusione aggiunta alla configurazione versionata.

Playwright: communications.spec.ts contro Next build su127.0.0.1:3407, tutte
le API intercettate; fixture communications-multipage.pdf contiene solo testo
sintetico. Build finale ripetuta dopo gli ultimi filtri UI e verificata in Chromium.

Evidenze temporanee: /tmp/gaia-comm-backend-frozen.log,
/tmp/gaia-communications-coverage-frozen.json,
/tmp/gaia-comm-ui-frozen.log, /tmp/gaia-comm-ui-coverage-frozen,
/tmp/gaia-comm-e2e-final.log, /tmp/gaia-comm-build-frozen.log,
/tmp/gaia-comm-ui-regression.log, /tmp/gaia-comm-ruolo-regression.log.
Questi log non sono artefatti da committare e non sono un archivio permanente.

Ultima revisione: fingerprint completo della riga sorgente, errore NAS\nsanitizzato, annullamento dei soli failed sicuri per nuova revisione,\nblocco di annullamento con evidenze sending/submitted/uncertain.\n