# Report di collaudo — 2026-11-03

Le evidenze sono locali e sintetiche: nessun messaggio reale, credenziale
provider, dato tributario di produzione o deployment. Non equiparare i mock
alla verifica di una casella reale.

## Prove già eseguite

| Perimetro | Esito |
| --- | --- |
| Communications backend e registrazione API/ORM, incluse sette prove PostgreSQL | 123 PASS, statement/branch100%,1548statement/316branch |
| Frontend nuovo e workspace Solleciti, Vitest | 89 PASS, statement/branch/function/line100%, 548statement,355branch,204funzioni,378righe |
| Suite backend completa | 8015PASS,471SKIP,2736warning,1430.23s; nessuna failure |
| Suite frontend completa | 349file,5468test PASS, maxWorkers2 |
| Regressione worker Posta Online,12file in processi separati | 166PASS,0SKIP; incluse6 prove PG sul DB sintetico |
| Regressione backend Ruolo | 1090PASS,407SKIP; skip preesistenti richiedono servizi/fixture PostgreSQL specializzate |
| Chromium PDF.js reale, API sintetiche | 4PASS, PEC/email desktop1440/mobile390, tre pagine, zoom, checklist, approvazione e dispatch simulato, zero pageerror/overflow |
| Build Next produzione | PASS,169pagine; warning legacy separati, nessun errore nuovo |
| Docker Compose overlay config --quiet | PASS con valori sintetici, nessun avvio |
| Ratchet contro merge-base main | PASS, finding0 |
| Ruff/format e lint-backend contro main | PASS |
| ESLint frontend nel perimetro toccato | PASS, nessun warning/errore |
| Riproducibilità baseline globale | FAIL (exit1), baseline non aggiornata dopo il rifiuto |
| Sincronizzazione baseline complessità | RIFIUTATA:17 regressioni di metriche preesistenti nei due file worker Poste; baseline invariata |
| Graphify codice backend/frontend/Ruolo | Aggiornato con target dedicati |
| Graphify documentazione piattaforma/Ruolo | PASS; piattaforma chunk1/1done, Ruolo42cachehit/0miss, nessun semantic failed |

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
corretto; le sette prove PG della corsa finale sono passate. Tentativi di esecuzione con cwd
errata o dipendenza ReportLab assente non sono considerati PASS; il PDF fixture
è prodotto con pypdf già disponibile. Prime URL provider404, poi guide ufficiali
aggiornate HTTP200, riportate in OPERATIONS.

## Limiti

Suite globale backend completata con exit0:8015PASS/471SKIP. Gli skip
restano prove non eseguite; la corsa globale non è un collaudo di tutti i servizi
esterni. Le prove PG Communications e worker Poste sono eseguite separatamente
senza skip. Skip Ruolo non diventano PASS. Warning
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

Regressione generale backend, dalla directory backend:

```bash
SMTP_ENABLED=false SMTP_USERNAME=synthetic SMTP_PASSWORD=synthetic \
SMTP_HOST=smtp.example.org COMMUNICATIONS_TRANSPORT_ENABLED=false \
.venv/bin/python -m pytest tests
```

Regressione worker Posta Online: i dodici test_posta_online*.py sono eseguiti
uno per processo pytest, come nel target make test-worker, con PYTHONPATH del
backend/worker, DATABASE_URL SQLite temporaneo e POSTE_TEST_DATABASE_URL sul
solo communications_test sintetico. Sei prove PostgreSQL non saltate. Nessun
browser si collega al portale Poste: client e trasporti sono stub sintetici.

Playwright: communications.spec.ts contro Next build su127.0.0.1:3407, tutte
le API intercettate; fixture communications-multipage.pdf contiene solo testo
sintetico. Build finale ripetuta dopo gli ultimi filtri UI e verificata in Chromium.

Evidenze temporanee: /tmp/gaia-comm-backend-frozen.log,
/tmp/gaia-communications-coverage-frozen.json,
/tmp/gaia-comm-ui-frozen.log, /tmp/gaia-comm-ui-coverage-frozen,
/tmp/gaia-comm-e2e-frozen.log, /tmp/gaia-comm-build-frozen.log,
/tmp/gaia-comm-ui-regression.log, /tmp/gaia-comm-ruolo-regression.log,
/tmp/gaia-comm-poste-worker-regression.log,
/tmp/gaia-comm-backend-regression-all.log.
Questi log non sono artefatti da committare e non sono un archivio permanente.

Ultima revisione: fingerprint completo della riga sorgente, errore NAS
sanitizzato, annullamento dei soli failed sicuri per nuova revisione,
blocco di annullamento con evidenze sending/submitted/uncertain.

## Baseline di complessità

Il ratchet autorevole contro il merge-base main passa senza finding. Il comando
make complexity-baseline è stato eseguito dopo il gate e ha rifiutato
17 peggioramenti di metriche rispetto alla baseline corrente in
modules/elaborazioni/worker/posta_online_dispatch.py e
modules/elaborazioni/worker/tests/test_posta_online_dispatch.py. Entrambi
appartengono al precedente commit a2bd56fe e non sono modificati dai commit
Communications. Nessuna baseline/soglia/esclusione è stata alterata per assorbirli.
Il PASS del ratchet non implica riproducibilità della baseline globale.
make complexity-baseline-verify ha restituito false (exit1), come atteso dopo
il rifiuto; non viene presentato come gate passato.

Evidenze: /tmp/gaia-comm-ratchet-final.json,
/tmp/gaia-comm-baseline-final.log, /tmp/gaia-comm-baseline-verify-final.log,
/tmp/gaia-comm-ui-lint-final.log, /tmp/gaia-communications-after-final.json.
