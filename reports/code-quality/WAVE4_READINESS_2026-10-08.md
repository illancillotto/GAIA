# GAIA — Wave 4 readiness 2026-10-08

## Esito e stop

I cinque hotspot worker assegnati hanno **readiness coverage full-file100%**
nelle evidenze finali della campagna: statement2233/2233 e branch654/654.
Le metriche AST sono riprodotte indipendentemente su runtime immutato.
Una futura slice worker può essere proposta alla review con ownership e
caratterizzazione mirate; questo report **non implementa né autorizza da solo
un refactor**, e non considera chiusi i cinque hotspot.

Il runtime worker complessivo resta sotto100% (statement6072/6077,
branch1624/1630). I gap sono in altri due file e non vengono occultati o
attribuiti ai cinque candidati. Gli altri domini Wave4 hanno ranking misurato
nel report corrente ma readiness behavior/coverage **NOT_MEASURED** in questa
assegnazione. Nessuna deduzione automatica che siano READY o BLOCKED.

STOP dopo report e commit documentale, senza test aggiunti, implementazione,
branch aggiuntive, integration, baseline update o modifica del runtime finale.

## Ownership e snapshot

- Assegnazione read-only dopo checkpoint B4/B5 GREEN e readiness C2.
- Worktree `/home/cbo/CursorProjects/GAIA-campaign-20261008-catasto-backend`.
- Branch report-only esistente `refactor/complexity-catasto-ade-readiness`,
  riusata su autorizzazione del Coordinator.
- HEAD iniziale `2f07c91be3c43de3a93df1d68d0af4d61a469cc2`; merge-base main
  `55a1b1d35911451e018b662c2acc450bf5994ea2`.
- Working tree iniziale pulito; ownership scrittura esclusivamente questo report.
- Worker, test, scripts, shared, soglie, eccezioni e baseline read-only.

Ranking corrente: `/tmp/gaia-complexity-final.json`, generated_at
`2026-10-08T15:45:07.067328+00:00`, source_commit
`897dddeadbd93aa3dc849c14cefa491c68e4315a`, runtime integration P1/P6/B4/B5.
Non usa il report del7/10. Worker non ha diff fra main55a e integration; le
metriche dei cinque file della worktree readiness coincidono con il report finale.

Coverage finale riusata: `/tmp/gaia-campaign-worker-final-coverage.json`,
Coverage7.14.0, branch_coverage true, timestamp `2026-10-08T17:32:33.766502`.
Suite finale `/tmp/gaia-campaign-worker-final-tests3.log`, già eseguita dal
verifier: **778 PASS, 1 SKIPPED, 52 file test**. Non viene rieseguita qui.
Il JSON non contiene source_commit/hash: la provenance è corroborata dal
checkout worker immutato, dalla suite finale e dalla concordanza delle misure;
non si attribuisce al JSON una firma delle sorgenti che non possiede.

## Graphify e metodo

Orientamento tramite corpus worker dedicato nel checkout principale, sola query:

```bash
make graphify-elaborazioni-worker-query \
  Q='autodoc sync visura BrowserSession login posta online retry timeout download lifecycle'
```

PASS, log `/tmp/w4-worker-graphify-query.log`. Il grafo orienta su login,
CAPTCHA, ciclo browser, visura e correlazione richieste; non dimostra equivalenza
funzionale né complessità. Nessuna estrazione dalla root grezza e nessun refresh
runtime necessario, poiché sorgenti/dipendenze restano invariate.

Scanner indipendente dei cinque file:
`/tmp/w4-worker-runtime-readiness.json` e `.md`, 5 file,172 callable,
28 error e47 warning. Le metriche file sono identiche al report finale;
nessun parse error. I finding non sono problemi indipendenti e i cinque file
sono un sottoinsieme del worker runtime ufficiale, non il suo totale.

## Ranking corrente dei target

Il rank è globale fra i callable dello scanner ufficiale, test worker inclusi,
ordinando cognitive desc, cyclomatic desc, path/name asc per tie-break.
È orientativo, non una misura della sicurezza del refactor.

| Rank | File | Callable | Cognitive | Cyclomatic | LOC | Nesting | Params |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| 45 | autodoc_sync.py | run_autodoc_sync_job_by_id | 122 | 46 | 145 | 6 | 2 |
| 96 | posta_online_client.py | PostaOnlineBrowserClient.scrape_registered_mails | 73 | 41 | 80 | 5 | 3 |
| 100 | visura_flow.py | execute_visura_flow | 71 | 30 | 168 | 5 | 12 |
| 108 | posta_online_sync.py | run_posta_online_registered_mail_job_by_id | 68 | 39 | 124 | 4 | 4 |
| 204 | browser_session.py | BrowserSession.login | 47 | 19 | 56 | 5 | 4 |

Percorsi relativi a `modules/elaborazioni/worker/`.

| File | Effective LOC | Callable | Cognitive sum | Cyclomatic sum |
| --- | ---: | ---: | ---: | ---: |
| autodoc_sync.py | 434 | 13 | 200 | 111 |
| posta_online_client.py | 577 | 39 | 262 | 204 |
| visura_flow.py | 480 | 21 | 147 | 109 |
| posta_online_sync.py | 502 | 18 | 212 | 180 |
| browser_session.py | 1254 | 81 | 435 | 376 |

Nessun delta runtime: i valori restano quelli dello snapshot e delle sorgenti
finali. L'hotspot122 è di valore nella coda >100, ma i callable estremi frontend
ancora >300 rimangono prioritari nel ranking globale della campagna.

## Full-file coverage e invarianti

Valori estratti e verificati direttamente per percorso nel JSON finale;
zero missing line/branch e partial branch per tutti i cinque runtime.

| Runtime | Statement | Branch | Excluded lines | Readiness coverage |
| --- | ---: | ---: | ---: | --- |
| autodoc_sync.py | 300/300 | 86/86 | 0 | 100% |
| posta_online_client.py | 425/425 | 130/130 | 0 | 100% |
| visura_flow.py | 281/281 | 88/88 | 2 legacy | 100% secondo tooling invariato |
| posta_online_sync.py | 311/311 | 70/70 | 0 | 100% |
| browser_session.py | 916/916 | 280/280 | 0 | 100% |

Le due righe legacy visura18–19 sono `if TYPE_CHECKING` e import del tipo
BrowserSession; nessuna exclusion nuova. Il worker completo registra21 righe
escluse preesistenti, non eliminate o ampliate dalla campagna. Nessuna copertura
globale100% dichiarata e nessun gate ridotto per ottenere readiness.

| Target | Test esistenti significativi | Invarianti per futura slice |
| --- | --- | --- |
| Autodoc job | test_autodoc_sync.py: job missing/wrong/empty, skip/discovery/sync/error/cleanup, all attempts failed | Query e ordine veicoli, force refresh, URL discovery, enrichment, contatori/status, commit progress e finali, chiusura browser/DB |
| Poste scrape | test_posta_online_client.py e branch_closure: timeout retry bounded/transient, consecutive failures, target IDs, archive pagination, success/errors | Login/storage state, throttling, lista e dettagli, stop/retry, partial results, ordine richieste e session lifecycle |
| Visura flow | test_visura_flow.py: LLM/external/manual retry, queued request resume, no duplicate submission, timeout/non-evadibile, callbacks | Precedenza solver, numero tentativi, CAPTCHA/manual skip, correlazione, progress, download, error terminali e callback |
| Poste sync job | test_posta_online_sync_branch_closure.py e cooldown: missing job, persist failure, partial checkpoint/resume, circuit breaker, import counters | Progress parziale, checkpoint, cooldown/retry_not_before, DB commit/rollback, ripresa senza perdita/duplica e payload import |
| Browser login | test_browser_session.py e lifecycle/forms/correlation suites: locked/existing sessions, credentials, final logout, valid PDF/atomic replace, correlation fail-closed | Error classification, session recovery, login/logout, CAPTCHA selector, timeout, request identity e cleanup |

Questi test esercitano comportamenti reali delle funzioni contro mock browser/
network ai confini; non sono prove live dei portali o provider CAPTCHA. La sola
copertura non dimostra ogni possibile race o compatibilità futura del portale:
ogni runtime change richiede una matrice di caratterizzazione specifica.

## Slice futura suggerita, non avviata

Primo candidato worker: `run_autodoc_sync_job_by_id`, responsabilità coerente
**classificazione dell'esito per veicolo e consolidamento progress**. Preservare
precedenza missing URL→already_synced→snapshot/error, timestamp, enrichment
solo se campi vuoti, ultimi10 risultati, primi20 errori, stato failed solo se
zero successi con errori, tutti i commit e final cleanup.

La proposta deve essere ristretta prima dell'implementazione a una singola
responsabilità e validata dal Coordinator, senza spostare145 righe in un helper.
Usare test esistenti più equivalenza degli esiti e ordine dei side effect dove
manca una prova puntuale; misurare il file completo dopo. Stop se richiede
mutare politica retry, ordine DB/browser o contratti esterni. Il risultato deve
ridurre gli aggregati, avere coverage100% e ratchet0 prima della review.

Non proporre subito un refactor del login SISTER o della gerarchia solver,
che hanno rischi semantici maggiori rispetto alla slice di esiti già testata.
Nessuna implementazione è iniziata né branch di refactor worker creata.

## Altri domini Wave4 — Ranking e readiness distinta

Le metriche seguenti sono sole letture del report AST corrente. Il prefix
indicato delimita il sottoinsieme: non deve essere interpretato come un intero
dominio quando componenti/servizi vivono altrove. Per tutti questi sottoinsiemi
la readiness coverage/invarianti è **NOT_MEASURED**, non BLOCKED o READY.

| Dominio / prefix | File | Max cognitive | Error | Warning | Readiness |
| --- | ---: | ---: | ---: | ---: | --- |
| Presenze backend: backend/app/modules/presenze/ | 105 | 87 | 93 | 240 | NOT_MEASURED |
| Organigramma: frontend/src/features/organigramma/ | 15 | 167 | 32 | 39 | NOT_MEASURED |
| Utenze import/ANPR e resto modulo: backend/app/modules/utenze/ | 36 | 67 | 65 | 111 | NOT_MEASURED |
| Riordino backend: backend/app/modules/riordino/ | 71 | 47 | 34 | 51 | NOT_MEASURED |
| Wiki pages: frontend/src/app/wiki/ | 14 | 6 | 0 | 1 | NOT_MEASURED |
| Operazioni pages: frontend/src/app/operazioni/ | 24 | 144 | 98 | 48 | NOT_MEASURED |
| Network pages: frontend/src/app/network/ | 13 | 183 | 56 | 29 | NOT_MEASURED |
| Me pages: frontend/src/app/me/ | 8 | 271 | 15 | 12 | NOT_MEASURED |
| GAIA users pages: frontend/src/app/gaia/users/ | 4 | 162 | 26 | 24 | NOT_MEASURED |
| Accessi backend: backend/app/modules/accessi/ | 19 | 28 | 3 | 18 | NOT_MEASURED |
| NAS control pages: frontend/src/app/nas-control/ | 11 | 56 | 20 | 12 | NOT_MEASURED |

La ricognizione considera le priorità richieste senza refactorizzare moduli solo
perché esistono. Frontend Me/Network/Organigramma hanno picchi rilevanti da
caratterizzare prima di interventi; il piccolo prefix Wiki pages non esclude
debito in componenti Wiki esterni al prefix. GAIA users non viene cercato sotto
un modulo backend inventato `gaia_users`: il perimetro effettivo qui è frontend.
Ruolo, gate-mobile sync e legacy elaborazioni restano nello scope/prerequisiti
già gestiti dal Coordinator, senza assegnazioni aggiuntive di questa readiness.

## Limiti della suite worker globale

Esito già eseguito dal verifier:778 PASS e1 SKIPPED per test PostgreSQL recovery
migration con `GAIA_TEST_POSTGRES_URL` assente. La riga Coverage `Combined51
files, skipped1` riguarda file dati Coverage, distinta dallo skip del test.
Coverage runtime globale:6072/6077 statement,1624/1630 branch; mancano5 statement
e6 branch in `sister_credential_pool.py` e `sister_retry_metadata.py`.
Quel gap non è una regressione della campagna, che non modifica worker runtime.
Nuove slice che toccassero tali file dovrebbero colmare il relativo full-file
coverage; questo report non modifica o esclude quei file.

## Riproduzione e integrità

```bash
git status --short
git rev-parse HEAD
git merge-base HEAD main
python3 tools/code_quality/complexity.py report \
  modules/elaborazioni/worker/autodoc_sync.py \
  modules/elaborazioni/worker/posta_online_client.py \
  modules/elaborazioni/worker/visura_flow.py \
  modules/elaborazioni/worker/posta_online_sync.py \
  modules/elaborazioni/worker/browser_session.py \
  --json /tmp/w4-worker-runtime-readiness.json \
  --markdown /tmp/w4-worker-runtime-readiness.md
```

Coverage/report hanno SHA-256:

- Worker final coverage:
  `7b01f0d0aa698db05829dcba9000559f98cf83865781766fca1b2492c710a2dd`.
- Complexity final:
  `ef80329ea4e7a2fd574fef789b70c23ea688d41181bc640293e405f77dc083a7`.
- Autodoc source:
  `222c011c21921139a4d828bfdcb417c829c13572609813570380d858cb700d80`.
- Poste client source:
  `16fbbecdcad41f2efc439f82e55d0e19c296de1e54d6614ba7e897b6a5a4fd57`.
- Visura source:
  `02d79b6c8435fcc3e70f567b123bf466ad8bf8c9267633807bb2b1ce23f5c7ed`.
- Poste sync source:
  `e93d65294be7ceaa9b0fcd644b68329dde264b55c6015be52bb59e75a6974945`.
- Browser source:
  `7f5e4d99c6d5df95e041906ff1060feb987b41119c3c4c494694f762f02d8a76`.

Nessun rerun della suite totale, nessun test/runtime/script/shared/baseline
modificato. Diff-check e diff worker/config/tooling contro55a PASS. Commit
esclusivamente di questo report nella branch report-only già assegnata.
