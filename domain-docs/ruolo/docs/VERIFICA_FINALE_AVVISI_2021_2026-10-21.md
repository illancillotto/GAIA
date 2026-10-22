# Verifica finale: gestori sovrapposti e avvisi 2021

Data: 2026-10-21. Checkout iniziale `main`, HEAD `16a0e710`.
Perimetro: ciclo locale Ruolo/Tributi; nessun commit, push, rilascio o invio.
La fase di consolidamento aggiunge test e documentazione, senza modificare
ulteriormente il runtime implementato nel ciclo.

## 1. Scope e funzionalita

Runtime modificato:

- `backend/app/modules/ruolo/tributi_repositories.py`: gestori sovrapposti,
  validazione del range, risoluzione deterministica e supporto dal 2021.
- `frontend/src/app/ruolo/tributi/page.tsx`: anno 2021 nel wizard e istruzioni
  per configurare il gestore e la Regola ruolo.

Una regola attiva 2021 puo convivere con STEP 2018-2021. L'attribuzione segue
`year_from DESC NULLS LAST`, `year_to ASC NULLS LAST`, `updated_at DESC`,
`id DESC`. I filtri per gestore includono il suo intero intervallo: due
periodi possono selezionare le stesse posizioni. Inattivazione/cancellazione
ripristina la regola precedente. Restano vietati i range invertiti.

Wizard, preview rapida e batch ammettono il 2021. La generazione richiede
saldo aperto, gestione `internal_gaia` e le regole operative esistenti.
La selezione dei non notificati usa una Regola ruolo con `only_unnotified`:
una ricezione postale documentata o una ricevuta PEC di consegna esclude
la posizione. Un precedente invio senza consegna non equivale a notifica;
la modifica non implementa un filtro "mai inviati".

## 2. API, servizi, modelli e dipendenze

Il contratto usa gli endpoint esistenti:

- `GET/POST /ruolo/tributi/year-managers`;
- `PUT/DELETE /ruolo/tributi/year-managers/{id}`;
- `GET /ruolo/tributi/avvisi`, relativo dettaglio e `summary`;
- `GET /ruolo/tributi/solleciti/candidates`;
- `POST /ruolo/tributi/solleciti/batches` e generazione dalla singola posizione;
- CRUD `calculation-policies`, invariato, per `only_unnotified`.

Riutilizzati `RuoloTributiYearManager`, `RuoloAvviso`, policy di calcolo,
raccomandate, dati inCASS, registry e generatore documentale esistenti.
Nessuna nuova API, colonna, tabella, migration, dipendenza o servizio parallelo.
`package.json` e lockfile restano invariati. Autenticazione, sezione
`ruolo.tributi.manage_status`, audit `updated_by`, commit e rollback mantengono
il contratto corrente. La generazione PDF nei test API usa un sostituto locale;
non vengono contattati NAS, PEC, Poste o contribuenti reali.

## 3. Matrice funzionalita → comportamento → test

I nomi senza percorso si riferiscono a `backend/tests/ruolo/`.

| Funzionalita | Comportamento atteso | Test pertinente |
| --- | --- | --- |
| Creazione sovrapposta | POST 2021 accettato senza modificare STEP | `test_tributi_api.py::test_tributi_year_managers_are_configurable_and_filter_avvisi`; `test_tributi_year_manager_overlap.py::test_overlapping_2021_manager_generates_only_unnotified_notices` |
| Precedenza | Inizio, fine, modifica e UUID risolvono anche i pareggi | `test_overlapping_manager_precedence_is_deterministic_and_reversible` |
| Limiti aperti e inattivi | NULL ordinati dopo limiti definiti; inattivi esclusi | Stesso test di precedenza; `test_tributi_api.py::test_tributi_year_manager_helper_edges` |
| Nessuna regola applicabile | Attribuzione vuota; fallback iniziale preservato | `test_tributi_year_manager_helper_edges`; test API gestori |
| Persistenza PostgreSQL | Selezione 2017/2020/2021/2022 corretta tra sessioni e dopo DELETE | `test_year_manager_overlap_postgres.py::test_year_manager_overlap_persists_and_orders_null_bounds_on_postgres` |
| Normalizzazione e audit | Chiave normalizzata, `updated_by` salvato | `test_overlapping_manager_update_rollback_and_delete_persist_across_sessions` |
| Update non valido | 422, dati e numero di regole invariati dopo rollback | Stesso test di persistenza; test API gestori |
| Disattivazione e DELETE | Modifica persistita; STEP torna applicabile | Test di persistenza SQLite e PostgreSQL; precedenza reversibile |
| ID/chiave/range invalidi | 404 o 422 secondo il contratto | `test_tributi_year_managers_are_configurable_and_filter_avvisi` |
| Autorizzazioni | POST/PUT/DELETE: 401 senza login, 403 al viewer, dati invariati | `test_overlapping_manager_mutations_require_manage_permission`, due casi |
| Gestione esterna 2021 | STEP non abilita candidati o generazione | `test_2021_external_management_stays_ineligible_for_generation` |
| Batch 2021 | Anno preservato, nessun avviso 2020 o consegnato incluso | `test_overlapping_2021_manager_generates_only_unnotified_notices`, due casi `policy_group` |
| Evidenze postali/PEC | Notificati esclusi; accettazione/fallimento non equivalgono a consegna | `test_tributi_unnotified_policy.py::test_only_unnotified_policy_uses_delivery_evidence_across_read_paths`, sette canali; test batch 2021 |
| Ricevute cumulative/estranee | Solo gli avvisi effettivamente associati sono esclusi | `test_cumulative_documented_receipt_excludes_all_associated_annualities`; `test_unrelated_registered_delivery_does_not_exempt_an_unnotified_notice` |
| UI gestore 2021 | Payload `internal_gaia`, range 2021, opzione wizard selezionabile | `frontend/tests/unit/ruolo-tributi-page.test.tsx`: `creates an overlapping 2021 manager and offers 2021 in the reminder wizard` |
| UI errore e retry | Errore visibile, form preservato, retry e filtro funzionanti | `frontend/tests/e2e/ruolo-2021-overlap.spec.ts`, 1440/390 px; unit `handles annuality manager loading and mutation errors` |
| UI sola lettura | Gestione non disponibile al viewer | Unit `shows rules read-only for non admin users`; API permessi |
| Errori wizard/preview | Errori candidati, generazione e download gestiti senza esporre documenti privati | Unit `handles reminder wizard empty, candidate error and generation error states`; E2E `ruolo-tributi-draft-preview.spec.ts` |
| Regressione 2022 e regole | Bozze private, download marcato, date italiane e scorrimento preservati | E2E `ruolo-tributi-draft-preview.spec.ts` e `ruolo-policy-scroll.spec.ts`, desktop/mobile |

## 4. Test aggiunti e modificati

- `test_tributi_api.py`: attesa del nuovo contratto 200 sulle sovrapposizioni;
  rimossi soltanto gli assert dell'helper di etichetta eliminato dal runtime.
- `test_tributi_year_manager_overlap.py`: sette casi API/dominio, inclusi
  quattro casi aggiunti durante la verifica su permessi, rollback e gestione esterna.
- `test_year_manager_overlap_postgres.py`: nuovo test su PostgreSQL reale,
  con schema temporaneo e sessioni distinte.
- `ruolo-tributi-page.test.tsx`: caso creazione/selezione 2021 e istruzioni UI.
- `ruolo-2021-overlap.spec.ts`: due nuovi E2E desktop/mobile, con API simulate.

Nessun test preesistente disabilitato, nessun nuovo skip, mock documentale
limitato al confine PDF gia presente nella suite. Gli E2E verificano la UI
compilata; API, transazioni e SQL sono verificati separatamente nei test backend.

## 5. Risultati e comandi

| Controllo | Risultato |
| --- | --- |
| Nuovi casi API/dominio | 7 PASS |
| Nuovo test PostgreSQL | 1 PASS |
| Suite Ruolo completa con PostgreSQL e coverage | FAIL: 1162 PASS, 9 skip SQLite, 1 failure causata dalla migration concorrente STEP |
| Suite frontend completa, dipendenze locali | 5269 PASS, 323 file |
| Suite frontend completa da lockfile con coverage | FAIL: 5268 PASS, 1 timeout estraneo in Utenze; dettaglio sotto |
| Rerun isolato Utenze + pagina Tributi da lockfile | 84 PASS, pagina Tributi al 100% anche sui branch |
| Smoke frontend da lockfile | 18 PASS, nessuno skip |
| E2E Chromium pertinenti | 6 PASS, desktop 1440 px e mobile 390 px |
| Build pulita da lockfile | PASS, Next 15.5.27, 163/163 pagine |
| Lint Python, Ruff e format dei due nuovi test Python | PASS |
| Lint e typecheck frontend | PASS, warning preesistenti |
| Ratchet mirato dei due runtime, `BASE_REF=HEAD` | PASS, zero finding |
| Ratchet autorevole globale, `BASE_REF=origin/main` | FAIL, due finding preesistenti |
| Audit dipendenze di produzione | FAIL, 2 high e 3 moderate gia nelle dipendenze esistenti |

Comandi principali:

```sh
GAIA_TEST_POSTGRES_URL='<PostgreSQL locale isolato>' \
  COVERAGE_FILE=/tmp/gaia-2021-audit-backend.coverage \
  backend/.venv/bin/python -m pytest backend/tests/ruolo \
  --cov=app.modules.ruolo.tributi_repositories --cov-branch \
  --cov-report=json:/tmp/gaia-2021-audit-backend-coverage.json --cov-fail-under=100 -ra

cd frontend
npm ci --prefer-offline
npm test
VITEST_COVERAGE_INCLUDE=src/app/ruolo/tributi/page.tsx \
  npm run test:coverage -- --maxWorkers=2
npm run typecheck
npm run lint
npm run build:clean
PLAYWRIGHT_BASE_URL=http://127.0.0.1:3451 npm run test:e2e -- \
  tests/e2e/ruolo-2021-overlap.spec.ts \
  tests/e2e/ruolo-policy-scroll.spec.ts \
  tests/e2e/ruolo-tributi-draft-preview.spec.ts --workers=1
npm audit --omit=dev --json
```

Build, installazione e browser lavorano in una copia isolata sotto `/tmp`,
confrontata con i 675 file sorgente frontend del checkout: zero differenze.
Le dipendenze locali avevano Next 15.5.25, mentre il lockfile richiede
15.5.27: per build ed E2E e stata usata l'installazione pulita da lockfile.
Il container PostgreSQL dedicato non usa dati applicativi; gli schemi sono
temporanei e rimossi dalle fixture.

La suite completa da lockfile e terminata in 421,36 secondi con un timeout
di 5000 ms in `campaign-utenze-detail-page.test.tsx:182`, caso
`shows load error without edit controls`. File del test e runtime Utenze
non sono modificati nel ciclo. La precedente esecuzione completa con le
dipendenze locali aveva superato tutti i 5269 test. Il fallimento resta
registrato: non viene trasformato in PASS ne corretto allargando timeout o
modificando un dominio estraneo. Il rerun mirato serve a distinguere una
failure riproducibile da un timeout intermittente, non sostituisce il gate
completo fallito. Il rerun dei due file da lockfile con un worker ha superato
tutti gli 84 test in 22,37 secondi, senza riprodurre il timeout: nessuna causa
funzionale dimostrata e nessuna modifica ai test per nasconderlo. Il report
coverage non viene emesso dall'esecuzione completa fallita; la misura della
pagina e acquisita separatamente da questo rerun.

La suite backend termina in 968,16 secondi con 1162 test superati, nove skip
espliciti delle varianti SQLite che richiedono concorrenza/row lock PostgreSQL
e una failure in
`test_unnotified_policy_migration.py::test_isolated_release_and_future_merge_have_safe_upgrade_paths`.
Il test si aspetta la head `20261019_1500`, ma trova `20261021_1200`, revision
del nuovo file STEP apparso durante questa verifica. Si tratta di un effetto
dimostrato del lavoro concorrente, non di una migration introdotta dagli
Avvisi 2021. Non vengono rimossi file altrui o indebolito l'assert per ottenere
un PASS. Le prove PostgreSQL, incluse le nuove verifiche del gestore, passano.
Gli skip non sono conteggiati come test superati. Sono emessi 780 warning
legacy sulle chiavi JWT di test corte. Il comando esce 1 per la failure, non
per il coverage, che supera il gate del 100%.

## 6. Coverage

Misura mirata rinnovata sulla pagina, anche con dipendenze pulite da lockfile:
statement `641/641`, branch `618/618`, funzioni `202/202`, linee `585/585`,
tutte al 100%.
La misura conclusiva corrente del runtime backend, nella suite completa con
PostgreSQL, e statement `1822/1822`, branch `694/694`, zero branch parziali,
100%. Nessuna linea o branch strumentati restano scoperti nei due runtime.

Non sono state introdotte esclusioni. Restano due righe backend escluse
preesistenti (`3300-3301`): guardia su avviso mancante gia protetta dal chiamante
e dalla FK, con motivazione inline. Nessun comportamento aggiunto e privo
di un test pertinente. Il 100% riguarda il perimetro strumentato, con le
esclusioni ereditate: non certifica i rami esclusi come eseguiti.

Annotazioni UI preesistenti in `frontend/src/app/ruolo/tributi/page.tsx`,
invariate nel diff del ciclo:

| Linee/annotazioni | Motivo e valutazione |
| --- | --- |
| 197-207 | Fallback difensivi per payload API malformati; non modificati |
| 263 | Fallback temporale prima della finestra minima di anni disponibili; non pertinente alla data corrente |
| 620, 631, 689, 723, 753, 791, 809, 839, 846, 870, 886, 904, 982, 984, 1028, 1037, 1039 | Guardie token/selezione/azioni non esposte dalla UI montata; nessuna nuova esclusione |
| 783-787, 801-805 | Catch di rete delle regole di calcolo, gia esclusi e dichiarati coperti dai test client API nelle annotazioni; non sono rami nuovi o modificati e non se ne dichiara la copertura UI |
| 1088 | Fallimento parziale di una futura preview multi-template; funzionalita non attiva |
| 1828-1874 | Stati loading/empty del modal, duplicati del pannello compatto secondo l'annotazione esistente |
| 2859-2884 | Tab multi-template inattive con il solo template GAIA |

Queste esclusioni restano debito del perimetro legacy, non nuovi test mancanti
sui comportamenti introdotti. Non sono state ampliate per superare il gate.

## 7. Code quality, complessita e architettura

| Perimetro | Prima → dopo |
| --- | --- |
| Repository Tributi, LOC effettive file | 3688 → 3636 |
| Repository Tributi, somma ciclomatica/cognitiva | 1187/1393 → 1164/1367 |
| `get_year_manager_for_year`, ciclomatica/cognitiva/LOC | 5/4/21 → 3/2/21 |
| `upsert_year_manager`, ciclomatica/cognitiva/LOC | 10/10/39 → 9/9/33 |
| Pagina Tributi, LOC file | 2909 → 2909 |
| `RuoloTributiPageContent`, ciclomatica/cognitiva/LOC | 169/195/1041 → 169/195/1041 |
| Dipendenze importate backend/frontend | 42/22 → 42/22 |

Eliminati gli helper usati esclusivamente dal divieto di sovrapposizione;
nessun riferimento runtime/test residuo. Nessuna duplicazione runtime,
wrapper artificiale, nuova esclusione, variazione di responsabilita o API.
Gli helper esistenti continuano a governare calcolo, evidenze e generazione.
La selezione SQL resta parametrizzata tramite SQLAlchemy; permessi, rendering
React dei testi e validazione UUID mantengono le protezioni correnti.
Non sono aggiunti log di dati personali o credenziali.

Il codice resta nel backend di dominio `backend/app/modules/ruolo/` e nel
frontend `frontend/src/app/ruolo/`. Compatibilita con il monolite modulare
preservata; nessuna nuova architettura o servizio. Le grandi unita legacy
restano debito noto: massimi file backend ciclomatica/cognitiva `39/59`,
pagina `169/195`, `upsert_year_manager` ancora con 10 parametri.

## 8. Gate complessita e regressioni

Il confronto autorevole con il merge-base di `origin/main` fallisce per:

1. `frontend/src/app/ruolo/tributi/page.tsx`, `Program<anonymous>`, parametro
   `0 → 1`: finding identico sul report acquisito prima delle modifiche e
   sul report finale; intero multinsieme delle metriche/fingerprint frontend
   invariato nel ciclo.
2. `backend/app/modules/ruolo/repositories.py`, LOC file `1885 → 1889`:
   modifica locale estranea gia presente all'avvio e preservata.

Il ratchet mirato dei due runtime contro HEAD passa. Non sostituisce quello
autorevole. Baseline, matcher, soglie ed esclusioni non vengono riscritti
per assorbire i finding. Non sono emerse regressioni funzionali nei gate
applicativi completati. Le eventuali limitazioni della suite backend sono
riportate nei risultati finali, senza trattare gli skip come test superati.

## 9. Sicurezza e limiti di integrazione

L'audit di produzione rileva cinque segnalazioni nella toolchain esistente:
`next` e `sharp` high; `mammoth`, `argparse` e `sprintf-js` moderate.
Manifest e lockfile non sono cambiati nel ciclo. Nessun upgrade automatico
e incluso in questa verifica. Restano warning ESLint legacy e il warning
sulla chiave JWT corta delle fixture di test, senza nuove segnalazioni runtime
introdotte dalla modifica. La suite frontend emette inoltre warning legacy
React `act`/NaN e limiti jsdom sulla navigazione; non vengono nascosti o
trattati come una verifica di navigazione browser reale.

Non sono certificati consegna PEC/Poste, accesso NAS reale, dati di produzione,
autorizzazione Poste alla stampa o deploy su `gaia.lan`. I confini documentali
usano i mock previsti; il database PostgreSQL della prova e reale e isolato.

## 10. Documentazione, Graphify e working tree

Aggiornati PRD, execution plan, PROGRESS e documento tecnico/API del dominio
Ruolo. Il README e le note architetturali di piattaforma sono stati verificati:
nessun cambiamento trasversale richiede una modifica di quei documenti.
Il piano storico resta distinto dalla checklist del ciclo corrente.

Graphify codice aggiornato con `make graphify-ruolo-code` e
`make graphify-frontend`, entrambi exit 0. Nessun nuovo cambiamento topologico
rispetto al grafo gia aggiornato durante l'implementazione: rispettivamente
1154 e 6713 nodi. Verificata l'assenza di `_year_ranges_overlap` e
`_manager_range_label` nei nodi; query dedicata conferma le relazioni tra
resolver, upsert e validatore ancora presenti.

Applicata la patch locale `make graphify-patch-openai-base-url`.
`make graphify-ruolo-docs` ha completato l'estrazione con `gpt-6-luna`:
29 cache hit, cinque file riestratti, `chunk 1/1 done`, nessun warning di
fallimento semantico. Prima sincronizzazione: 1445 nodi, 3189 archi,
83 comunita, 21522 token input e 2420 output, costo stimato $0,0125.
Il medesimo target viene rieseguito dopo il consolidamento del report per
allineare anche i risultati conclusivi; nessun nuovo artefatto Graphify e
incluso nel ciclo.
Log della sincronizzazione conclusiva:
`/tmp/gaia-2021-final-graph-ruolo-docs-sync.log`, inclusi token/costo della
riestrazione e conferma dei chunk semantici.

Working tree del ciclo: due runtime, test API esistente, test UI esistente,
due nuovi test backend, un nuovo E2E e cinque documenti Ruolo, incluso questo
report. Artefatti build, coverage, trace e log rimangono sotto `/tmp`.
`graphify-out/` resta ignorato. Nessuna configurazione o dipendenza modificata
dal ciclo; nessun commit, push, merge, rilascio o invio.
Server frontend isolato e container PostgreSQL creati per la verifica sono
stati arrestati; porte locali 3451 e 32768 libere. Gli hash dei sette file
runtime/test del ciclo risultano invariati durante il controllo conclusivo.

Modifiche estranee preservate:

- `.codex/config.toml`, SHA-256 `93348e08240c1c9b3c9379173160d2a2f425050621854bcb7d0ad4de4fb598b2`;
- `backend/app/modules/ruolo/repositories.py`, SHA-256 `e5b7375dc9411f90210aed822656e2740a8c3432c299f35846dd4f793627b03a`;
- modifiche concorrenti a `backend/app/db/base.py`,
  `backend/app/modules/elaborazioni/router.py` e `docker-compose.yml`, e nuovi percorsi
  `backend/app/modules/elaborazioni/step/`,
  `backend/app/modules/elaborazioni/step_routes.py`,
  `backend/alembic/versions/20261021_1200_elaborazioni_step_archive.py`,
  `modules/elaborazioni/worker/step_browser_scripts.py`,
  `modules/elaborazioni/worker/step_client.py`,
  `modules/elaborazioni/worker/step_rules.py`,
  `modules/elaborazioni/worker/step_sync.py`,
  `modules/elaborazioni/worker/step_worker.py`:
  non creati, modificati o inclusi nel ciclo. I gate descritti riguardano
  Avvisi 2021, non certificano questo sviluppo concorrente.

Il working tree rimane intenzionalmente dirty. Lo snapshot di chiusura e in
`/tmp/gaia-2021-final-working-tree.log`; eventuali ulteriori modifiche del
lavoro STEP concorrente restano fuori scope. `git diff --check` supera il
controllo senza errori; nessun file temporaneo di test e aggiunto al ciclo.

Evidenze principali fuori repository:

- backend e coverage: `/tmp/gaia-2021-audit-backend.log`,
  `/tmp/gaia-2021-audit-backend-coverage.json`;
- suite frontend completa da lockfile e rerun:
  `/tmp/gaia-2021-final-locked-unit-coverage.log`,
  `/tmp/gaia-2021-final-locked-targeted.log`;
- coverage frontend: `/tmp/gaia-2021-final-locked-targeted-coverage/coverage-final.json`;
- build ed E2E: `/tmp/gaia-2021-final-locked-build.log`,
  `/tmp/gaia-2021-final-e2e.log`;
- ratchet e audit: `/tmp/gaia-2021-final-ratchet.log`,
  `/tmp/gaia-2021-final-audit-prod.json`.

## 11. Residui e stato finale

Restano da risolvere separatamente i finding preesistenti del ratchet, le
segnalazioni di sicurezza delle dipendenze, il timeout della suite completa
frontend da lockfile e l'aspettativa della head Alembic resa obsoleta dalla
migration STEP concorrente. La baseline non e sincronizzata
finche il confronto autorevole non e verde. Restano il debito legacy della
pagina/repository e il rilascio applicativo non eseguito.

Limite funzionale da chiarire prima dell'uso operativo: se "non inviati nella
precedente tornata" significa escludere qualsiasi tentativo precedente,
anche non consegnato, il filtro implementato non soddisfa quella semantica.
`only_unnotified` esclude le notifiche documentate, non tutti gli invii.
Non viene aggiunta una nuova funzionalita durante questa verifica finale.

Il gate complessivo non puo essere dichiarato PASS in presenza del ratchet
autorevole e delle suite complete backend/frontend falliti, anche con test
mirati, coverage dei runtime, E2E e build applicativi verdi.

FINAL QUALITY GATE — FAIL
