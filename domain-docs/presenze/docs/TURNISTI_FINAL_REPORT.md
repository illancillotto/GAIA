> Report storico del3ottobre: non certifica il checkout attuale. La verifica
> coordinata corrente è in [TURNISTI_COORDINATED_VERIFICATION_2026-10-05.md](TURNISTI_COORDINATED_VERIFICATION_2026-10-05.md).
> Il precedente residuo coverage GATE è stato chiuso; il ratchet GAIA corrente
> presenta19regressioni attribuite al ciclo e il rilascio reale resta precedente.

# Verifica finale turnisti e autorità GATE — 2026-10-03

## 1. Scope e stato

Ciclo locale GAIA/GATE: turnisti e protezione degli inserimenti manuali KM,
reperibilità e buoni. Review, test, coverage, qualità, architettura, documenti,
grafi e working tree. Nessun deploy, restart, sync produttivo, commit o push.
Nessuna funzionalità aggiunta nella fase finale. Il database usato è stato un
PostgreSQL temporaneo dedicato su localhost, con schema isolato per ogni suite.
Container di test e server Next temporaneo sono stati arrestati/rimossi al
termine; nessun servizio preesistente è stato toccato.

## 2. Funzionalità e confini

Tipologie `acquaiolo`, `telecontrollo`, revoca `none`, intervalli persistenti
per giorno/mese, teorico 420 minuti, timbrature INAZ come evidenza del turno,
un buono per turno nella giornaliera, precedenza GATE indipendente da ACK/errori/import.
Coperti turni notturni e spezzati, incompletezza, overlap, riposi, assenze
riconosciute, bucket festivi/notturni, errori di invio e revoche.
Le due tipologie condividono le regole comunicate. Nessun calendario di
alternanza attestato; nessuna eccezione o pluralità di turni/giornata introdotta.

## 3. Matrice funzionalità → comportamento → test

| Funzionalità | Comportamento atteso | Test pertinente |
| --- | --- | --- |
| Due tipologie | Acquaiolo/telecontrollo hanno 420 minuti teorici e un buono; `none` revoca | GAIA `test_shift_entitlement_and_export`; GATE `recognizes morning, evening and overnight...` |
| Mattina/sera | Orario dalle timbrature, senza entrata o pausa inventata | Gli stessi test parametrizzati 06–13, 14–21 |
| Notte | Turno attraverso mezzanotte, anche spezzato; sovrapposizioni respinte | GAIA `test_split_overnight_shift_and_midnight_overlap`; GATE `aligns split overnight shifts...` |
| Timbrature invalide | Nessun buono automatico per timbrature assenti/incomplete/sovrapposte | GAIA `test_invalid_punches_never_grant_automatic_voucher`; GATE `detects short and incomplete shifts...` |
| Turno breve | Buono per turno lavorato, minuti mancanti evidenziati | GAIA `test_short_extra_rest_and_partial_absence`; GATE `detects short...` |
| Eccedenze/notturno/festivo | Primi 420 minuti ordinari, eccedenza distinta, bucket preservati | GAIA `test_shift_entitlement_and_export`, `test_short_extra_rest_and_partial_absence`; GATE shift rules |
| Riposo | SAB/DOM/RIPTURN/SMONTO senza timbrature: zero teorico e zero buono | GAIA `test_short_extra_rest_and_partial_absence`; GATE `detects short...` |
| Assenze | Solo copertura riconosciuta INAZ riduce il debito; no giustificazione arbitraria | GAIA `test_short_extra_rest_and_partial_absence`; suite union-leave; GATE shift rules |
| Voucher | Manuale OR turno produce massimo 1; turno incompleto non usa fallback straordinario | GAIA `test_shift_voucher_exports_and_incomplete_shift_never_uses_overtime_fallback`; GATE shift rules/meal-voucher/export |
| Validazione range | Giorno/mese validi; date inesistenti, ordine, mesi diversi e tipo ignoto respinti | GAIA `test_assignment_validation`; shared `dated shift command contract`; GATE `rejects malformed ranges...` |
| Contratto trasporti | Metadati completi, command ID obbligatorio, timestamp aware, nessun comando misto | GAIA `test_gate_shift_command_requires_id`, `test_gate_rejects_orphan_assignment_metadata`, `test_gate_rejects_combined_assignment_and_manual_values` |
| Identità | Il server attesta soggetto/record/timestamp; spoofing non cambia il soggetto | GATE `keeps ... range through snapshots...`, `rejects malformed ranges...`; regressioni auth/identity |
| Permessi API | 401/403/404/409/422 coerenti; nessuna scrittura fuori scope | GAIA `test_shift_route_security_and_ranges`, `test_route_enforces_edit_permission`; GATE malformed ranges/auth/permissions |
| Precedenza GATE | GAIA non modifica intervalli GATE, inclusa revoca; import futuri ereditano il flag | GAIA `test_gate_dated_assignment_persists_and_overrides_gaia[lan/outbound]`; GATE shift authority |
| Ordine/idempotenza | Ritentare lo stesso comando non duplica; ultima modifica prevale anche nello stesso millisecondo | GAIA dated authority e PostgreSQL concorrente; GATE `orders simultaneous authoritative edits...` |
| Persistenza GATE | ACK, failure, snapshot successivo e nuova istanza non cancellano | GATE PostgreSQL `survives ACK, a new import and repository restart...`; manual-authority integration |
| Revoca | Rimuove diritto automatico, conserva manuale, invalida calcoli snapshot turnista fino a GAIA | GATE `ignores unattributed commands and invalidates stale GAIA shift results...` e PostgreSQL |
| Migrazione GAIA | Upgrade/downgrade/upgrade con vincoli e dati giornalieri preservati | GAIA `test_shift_migration_round_trip`; `test_shift_migration_and_concurrent_retry_preserve_gate_authority` PostgreSQL |
| Retry concorrente GAIA | Lock sul collaboratore, una sola assegnazione, conflitto GAIA dopo comando GATE | Nuovo test PostgreSQL shift workers |
| UI GAIA | Tipo, date, tutto mese, prevenzione doppio submit, errori/sessione/viewer e badge | `presenze-shift-workers.test.tsx` (7 casi); pagina `saves a shift assignment...` |
| UI GAIA reale | Conflitto visibile, retry, aggiornamento mese e assegnazione GATE non editabile | E2E `shift assignment reports conflicts...` |
| UI GATE | Dialogo usa selezione caricata; range/tipo/headers corretti; annulla/errori/retry | Nuovo `admin-console-shift-workers.test.ts` (5 casi); E2E `shift-workers.spec.ts` desktop/mobile |
| Stato invio | Badge tipo e failure separati; escaping HTML, nessun errore obsoleto | `admin-console-daily-sync-status.test.ts`, JavaScript emesso strumentato |
| Inserimenti manuali | KM=0/reperibilità rimossa/buono false persistono; UUID cache nuovo non perde il valore | `presenze-daily-record-values`, `presenze-manual-authority`, `presenze-meal-voucher`, integration PostgreSQL |
| Letture/export | Scope autorizzato e registro completo, senza troncamento 5000; valori GATE nell'XLSM | manual-authority export, export-routes, admin-auth, daily loading/paging regressioni |
| Compatibilità | Snapshot precedenti senza flag = non turnista; profili e altri campi aggiornabili | GAIA frontend `defaults records from an older snapshot...`; GATE daily-record-values/profile overlay |

## 4. Test consolidati nella verifica finale

- Shared: nuovo `shift-worker-schema.test.ts`, contratti per tipi, giorno/mese,
  leap day, date invalide/mancanti, intervallo inverso e mesi diversi.
- GATE: nuovo `admin-console-shift-workers.test.ts`, 5 comportamenti del dialogo;
  `admin-console-daily-sync-status.test.ts` esteso ai turnisti e strumentato.
  Il JavaScript realmente emesso è misurato con Istanbul, oltre a V8.
- GAIA: nuovo `test_presenze_shift_workers_postgres.py`, migrazione reale,
  retry simultanei, lock, idempotenza, precedenza e rollback.
- GAIA E2E: conflitto, retry, aggiornamento mensile e blocco assegnazione GATE.
- Pagina GAIA: test del salvataggio mensile e riapertura del dettaglio aggiornato.
- Timeout degli export XLSM riallineato a 120 secondi sotto coverage, dopo una
  prova fallita a 30 secondi con build/test concorrenti. Assertion e filtri invariati.

## 5. Regression gate ed evidenze

Evidenze complete nei log `/tmp/final-*`; i risultati definitivi sono riportati
sotto dopo il completamento dei comandi. I tentativi falliti restano documentati.

| Gate eseguito | Risultato definitivo | Evidenza |
| --- | --- | --- |
| GAIA backend Presenze/GATE (54 file di test) | 1134 passati, 10 skip PG iniziali; PG recuperati separatamente | `/tmp/final-gaia-backend-tests.log` |
| GAIA PostgreSQL (5 suite) | 11 passati, zero skip | `/tmp/final-gaia-pg2.log` |
| GAIA turnisti + migrazione coverage append | 29 casi superati; copertura aggregata 15 file 100% | `/tmp/final-gaia-complete-coverage.log` |
| GAIA frontend unit globale | 271 file, 3828 test passati | `/tmp/final-gaia-frontend-tests.log` |
| GAIA smoke `npm test` | 18 passati | `/tmp/final-gaia-smoke.log` |
| GAIA browser Chromium | 2 gerarchia passati nel run globale; 2 operational/shift passati nel rerun corretto | `/tmp/final-gaia-browser.log`, `/tmp/final-gaia-browser3.log` |
| GAIA typecheck/lint/build clean isolato | Superati; warning lint legacy | `/tmp/final-gaia-typecheck2.log`, `/tmp/final-gaia-lint.log`, `/tmp/final-gaia-build.log` |
| GAIA style ratchet Python | 155 file passati; nuovo test PG Ruff/format passato separatamente | `/tmp/final-gaia-style.log` |
| GAIA complexity ratchet globale | FAIL: 26 finding fuori scope turnisti | `/tmp/final-gaia-quality.log` |
| GATE gateway unit + PostgreSQL coverage | 81 file, 600 test passati; FAIL sulle soglie coverage della route legacy | `/tmp/final-gate-tests2.log` |
| GATE shift rules dopo rimozione helper | 9 test, 100% di tutte le metriche | `/tmp/final-gate-shift-rules.log` |
| GATE shared | 32 test, 100% di tutte le metriche | `/tmp/final-gate-shared2.log` |
| GATE connector | 97 test, 100% di tutte le metriche | `/tmp/final-gate-connector.log` |
| GATE operator-app regressione | 199 test passati | `/tmp/final-gate-operator.log` |
| GATE PostgreSQL separato | 38 test passati | `/tmp/final-gate-pg.log` |
| GATE E2E connector → GAIA simulato | 3 test passati | `/tmp/final-gate-e2e2.log` |
| GATE console browser reale | 1 scenario desktop/mobile passato | `/tmp/final-gate-browser.log` |
| GATE JS emesso dialogo/sync-status | 8 test passati, Istanbul 100% | `/tmp/final-gate-browser-unit.log` |
| GATE typecheck/lint/build/complexity ratchet | Superati dopo consolidamento runtime | `/tmp/final-gate-typecheck3.log`, `/tmp/final-gate-lint3.log`, `/tmp/final-gate-build2.log`, `/tmp/final-gate-quality2.log` |

Tentativi iniziali non verdi: shared non copriva i nuovi contratti (ora 100%);
connector E2E non aveva ricevuto il DB URL (rerun corretto verde); nuova fixture
E2E GAIA aveva una risposta credentials non-array e un selettore alert ambiguo
(corretti senza runtime); export XLSM superava il timeout 30s sotto coverage
(ora 120s, suite intera verde). Nessuna failure funzionale del ciclo resta nascosta.


## 6. Coverage e perimetro

GAIA: 15 file backend compresa la migrazione; cinque file frontend runtime.
GATE: 24 file gateway, comprese route precedentemente escluse dal comando
standard, e tre file shared. Il config temporaneo usa `exclude: []` nel
perimetro gateway; non modifica soglie o configurazioni versionate.
JavaScript dentro template string: misurato anche con Istanbul nei test di
loading, bulk-entry, sync-status e dialogo turnisti, perché V8 vede solo la
costruzione della stringa. Type-only schemas non hanno istruzioni eseguibili.
Il precedente 100% GATE del comando standard non dimostrava il 100% di tutte
le route modificate; questa verifica distingue i due perimetri.

| Perimetro | Statement | Branch | Funzioni | Righe |
| --- | --- | --- | --- | --- |
| GAIA backend + migrazione (15 file) | 1175/1175 | 248/248 | n/a Python | 100% |
| GAIA frontend (5 file) | 1228/1228 | 1383/1383 | 319/319 | 1010/1010 |
| GATE shared | 141/141 | 77/77 | 18/18 | 135/135 |
| GATE gateway 24 file, incl. admin.ts | 2292/2397 (95,61%) | 2071/2212 (93,62%) | 599/602 (99,50%) | 1999/2051 (97,46%) |
| GATE gateway senza il solo admin.ts (23 file) | 100% | 100% | 100% | 100% |
| GATE dialogo/sync-status JS emesso | 100% | 100% | 100% | 100% |

La misura gateway aggrega il run unit+PG con il report della versione finale
`presenze-shift-worker-rules.ts`: il run globale aveva caricato la versione
prima della rimozione del helper. Il report completo conserva tutti i 24 file;
nessun file viene sottratto per la decisione del gate.

Unico file scoperto: `apps/gateway-api/src/routes/admin.ts`, 52 righe, 105 statement,
141 esiti branch, tre funzioni (`anonymous_7`, `anonymous_11`, `currentMonthValue`).
Righe prive di hit (full-file):

```text
288, 315, 367, 385, 404, 430, 434, 442, 513, 566, 573, 580, 647, 652, 696, 745, 752, 774, 777, 786, 793, 832, 835, 840, 843, 872, 956, 991, 1208, 1214, 1224, 1253, 1264, 1268, 1278, 1283, 1300, 1301, 1308, 1315, 1321, 1342, 1345, 1351, 1464, 1499, 1500, 1501, 1502, 1545, 1560, 1569
```

Anche branch di righe parzialmente eseguite rimangono scoperti:

```text
227, 241, 276, 287, 291, 366, 378, 388, 398, 403, 428, 429, 433, 441, 498, 512, 553, 563, 565, 571, 572, 577, 579, 594, 626, 630, 645, 646, 651, 695, 720, 736, 744, 751, 760, 773, 776, 785, 789, 792, 831, 834, 839, 842, 871, 891, 892, 893, 902, 909, 910, 911, 913, 915, 938, 939, 940, 942, 944, 947, 949, 955, 977, 978, 979, 981, 983, 988, 990, 1014, 1016, 1024, 1033, 1043, 1044, 1048, 1082, 1090, 1122, 1129, 1163, 1164, 1165, 1172, 1173, 1174, 1185, 1186, 1187, 1189, 1198, 1199, 1200, 1207, 1212, 1213, 1223, 1252, 1263, 1266, 1267, 1277, 1282, 1300, 1314, 1320, 1332, 1341, 1344, 1347, 1349, 1350, 1362, 1373, 1379, 1386, 1388, 1403, 1404, 1413, 1414, 1415, 1447, 1448, 1449, 1463, 1498, 1500, 1502, 1544, 1545, 1549, 1550, 1551, 1559
```

Motivo: il file include altre API amministrative, auth, asset/mappe, device,
privacy ed export legacy, non coperte integralmente dalle suite correnti.
Mancano test pertinenti a quei failure path e fallback; non sono esclusioni
motivate, quindi il target full-file NON è raggiunto. La riga modificata che
rimuove il limite overlay e i servizi estratti sono verificati; questo non
sostituisce l'obbligo full-file. Non vengono creati test artificiali che chiamano
callback soltanto per incrementare i contatori. Residuo da affrontare con una
tranche di caratterizzazione delle API amministrative, senza refactor massivo.
Evidenze machine-readable `/tmp/final-gate-merged-coverage.json`,
`/tmp/final-gate-merged-summary.json`, `/tmp/final-gate-uncovered.json`.


## 7. Code quality e complessità

Rimosso `shiftMealVoucher`, helper export interno usato solo dai test:
la produzione usa il calcolo canonico del voucher, ora verificato direttamente.
Nessun wrapper fittizio, nuovo pacchetto, esclusione o baseline indebolita.
GATE ratchet superato contro il merge-base `82e2fab0`.
GAIA ratchet globale: 26 finding sul checkout misto, nessuno attribuito ai file
runtime del ciclo turnisti. Esempi fuori scope: `retry_sync_job` cyclomatic 17,
`import_collaborator_payload` LOC 116→126, `count_operai_paid_rest_days` params 1→2,
API core `request` cyclomatic 20 e modifiche accessi/GIS/incassi/organigramma.
Non sono assorbiti nella baseline né corretti alterando lavoro concorrente.

Metriche dei dieci nuovi file GAIA: 30 callable, zero errori e 9 warning.
`shift_punch_intervals`: cyclomatic 14, cognitive 24, LOC 20;
`useShiftWorkerAssignment`: cyclomatic 13, cognitive 20, LOC 24;
`save`: cyclomatic 12, cognitive 19, LOC 11;
`record_shift_assignment`: cyclomatic 9, cognitive 11, LOC 47.
Restano sotto le soglie di errore 15/25/80. Nessun refactor esteso avviato.
Duplicazione cross-repository del calcolo: necessaria per l'overlay immediato
GATE con trasporto indisponibile; stessi casi di contratto parametrizzati,
`shift-v1` e copertura assenze canonica GAIA. Da mantenere allineata.

## 8. Architettura GAIA e dipendenze

Backend nel dominio `app/modules/presenze`: modello/schema, servizio
assegnazioni, regole pure, adapter GATE condiviso e route nella facade esistente.
Frontend nella pagina `app/presenze/giornaliere`, con componenti Presenze e
client API tipizzato. Alembic nella catena centrale, nessuno stack parallelo.
GATE usa l'esistente `presenze_pending_action` e il repository PostgreSQL,
senza nuova migrazione gateway. SQLAlchemy/FastAPI/Pydantic e Zod sono già presenti.
Le timbrature importate restano immutabili; gli intervalli sono separati.

## 9. Errori, sicurezza, dati e regressioni

Stato API e frontend verificato localmente; nessuna regressione funzionale
rilevata nelle suite eseguite. Il gate coverage resta rosso come sopra.
API protette dai permessi di modulo/record/pagina/team; soggetto GATE attestato
server-side e risoluzione canonica GAIA. Query parametrizzate, date/type validate,
command ID unico, lock collaborator, commit dopo assegnazione e invalidazione cache.
Failure conserva il valore e pubblica lo stato di invio; UI fa escaping del testo.
Nessun token o payload personale stampato; nessun dato reale usato come fixture.
I warning JWT delle fixture di test hanno chiavi sintetiche corte; non sono
una nuova configurazione di produzione. Lint GAIA conserva warning legacy
(page hook/unused state e altri domini), senza nuove soppressioni.

## 10. Build, lint e type safety

Build GATE workspace e typecheck/lint rieseguiti dopo la sola rimozione del
helper inutilizzato. GAIA smoke, unit globali, typecheck, lint e Python style.
`npm run build:clean` GAIA eseguito in copia temporanea completa src/public/config
con dipendenze condivise: la `.next` originale contiene file di proprietà dei
container e non viene cancellata. Lo script Compose di clean-build farebbe
stop/start dei servizi; non eseguito per rispettare il divieto di restart/deploy.

## 11. Documentazione

Specifiche turnisti in entrambi i repository: comportamento, API/status,
priorità, schema, migrazione, piano completato/residui. PRD, piani, README,
indice documenti, progress Presenze e architettura GAIA rimandano al presente
report. Piano execution GATE storico preservato con link al ciclo corrente.
Programma code-quality non modificato: questo è un ratchet ordinario, non un hotspot.

## 12. Graphify

Aggiornati `npm run graphify:code-map`, `make graphify-presenze-code` e
`make graphify-frontend`. Verificati nel JSON nodi shift schema, servizi,
route/API, modello e componenti: GAIA backend 39 nodi turnisti, frontend 11,
GATE 66 alla prima verifica. Artefatti locali ignorati, non committati.
Il grafo GATE supera il limite HTML di 5000 nodi: JSON e report restano disponibili.

Arricchimento semantico GAIA Presenze e piattaforma completato con
`gpt-reserve`: entrambi i log riportano `chunk 1/1 done`, nessuna failure
semantica. Grafi risultanti 938 nodi/1799 edge e 2426 nodi/5594 edge alla
prima estrazione; aggiornamento finale ripetuto dopo il consolidamento docs.
L'helper GATE rimosso non compare più nel grafo. Nessun output generato versionato.

## 13. Working tree

Snapshot iniziali: `/tmp/final-gate-initial-status.txt`, `/tmp/final-gaia-initial-status.txt`.
GAIA aveva ampio lavoro concorrente su accessi, GIS, Ruolo, Wiki, incassi,
organigramma, tooling, dipendenze e documenti; preservato. Rilevato anche un
worker concorrente GATE di consolidamento API/docs: non incluso automaticamente
nello scope turnisti. Nessun reset, stash, commit o pulizia generale da questo ciclo.
GATE HEAD è avanzato a `e691a66` durante la verifica per lavoro concorrente;
GAIA è rimasto `e33d5c69`. Nel delta working tree sono presenti anche
`docs/openapi/gateway-api.openapi.json`, `quality/complexity-baseline.json` e
documenti/test MCP GAIA aggiornati da altri worker: non appartengono a questo
ciclo e non sono ripristinati né assorbiti come modifiche turnisti.
La baseline non è stata modificata dall'agente di questa verifica.
Config di review e report grezzi in `/tmp`, artefatti coverage/build/Graphify ignorati.
Il file temporaneo di config GATE è stato rimosso dopo i controlli; i soli nuovi
file applicativi/documentali e test pertinenti restano reviewabili.

## 14. Residui e verifiche non effettuate

- Ratchet generale GAIA rosso sul diff concorrente: gate obbligatorio non superato.
- Coverage GATE full-file `admin.ts`: 52 righe/105 statement/141 esiti branch/3 funzioni residue; nessuna esclusione per renderlo verde.
- Catena Alembic locale risolta fino all'unico head `20261003_1200`; dipendenza
  `20261002_1030` ancora locale non tracciata: includere entrambe nel rilascio.
- Smoke produzione/INAZ, migrazioni produttive e recupero dei dati citati nella
  telefonata non eseguiti e non implicati dalla verifica locale.
- Calendario mattina/sera, future eccezioni e più turni/giornata richiedono
  requisiti espliciti, non sono attività incomplete di questo ciclo.

## 15. Debito tecnico ed esito

Debito esplicito: warning di complessità sotto soglia, monoliti legacy di
repository/console e duplicazione controllata delle regole fra GAIA/GATE.
Non è dichiarato PASS in presenza di gate obbligatori falliti o non verificati.

FINAL QUALITY GATE — FAIL

Impedimenti: coverage full-file GATE admin.ts sotto il 100% e ratchet globale
GAIA non superato. I test locali della funzionalità passano; questo non
autorizza a dichiarare PASS del ciclo integrale.

## Appendice: perimetro gateway/shared

```text
apps/gateway-api/src/db/presenze-manual-values-repository.ts
apps/gateway-api/src/db/sync-event-repository.ts
apps/gateway-api/src/routes/admin-console/daily-report-controls.ts
apps/gateway-api/src/routes/admin-console/daily-report-entry-toolbar.ts
apps/gateway-api/src/routes/admin-console/daily-report-icons.ts
apps/gateway-api/src/routes/admin-console/script-daily-bulk-entry.ts
apps/gateway-api/src/routes/admin-console/script-daily-entry-buttons.ts
apps/gateway-api/src/routes/admin-console/script-daily-report-loading.ts
apps/gateway-api/src/routes/admin-console/script-daily-sync-status.ts
apps/gateway-api/src/routes/admin-console/script-dashboard.ts
apps/gateway-api/src/routes/admin-console/script-shift-workers.ts
apps/gateway-api/src/routes/admin-presenze-pending-actions.ts
apps/gateway-api/src/routes/admin.ts
apps/gateway-api/src/services/presenze-admin-scope.ts
apps/gateway-api/src/services/presenze-daily-record-value-overlay.ts
apps/gateway-api/src/services/presenze-daily-record-values.ts
apps/gateway-api/src/services/presenze-manual-value-identity.ts
apps/gateway-api/src/services/presenze-meal-voucher.ts
apps/gateway-api/src/services/presenze-reperibilita-overlay.ts
apps/gateway-api/src/services/presenze-shift-worker-command.ts
apps/gateway-api/src/services/presenze-shift-worker-overlay.ts
apps/gateway-api/src/services/presenze-shift-worker-rules.ts
apps/gateway-api/src/services/presenze-snapshot-target.ts
apps/gateway-api/src/services/presenze-xlsm-export.ts
packages/shared/src/presenze-daily-patch-validation.ts
packages/shared/src/presenze-pending-action-create-schema.ts
packages/shared/src/shift-worker-schema.ts
```
