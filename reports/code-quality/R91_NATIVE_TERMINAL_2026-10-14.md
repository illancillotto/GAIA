# R91 — Verifica nativa singola: FAIL / NOT_RUN

## Grant e snapshot

User «autorizzo procedi senza fermarti» risponde alla richiesta esplicita di una
sola esecuzione dei due E2E R91, senza retry, service900s/supervisor930s, dopo quiet
slot e custodia esatta. Nuova autorizzazione esterna distinta dalla preparazione
source-only storica; nessun flag/seal storico modificato. Nessun grant a riparare
runtime/driver/test o ripetere casi falliti. Global goal INCOMPLETE.

Checkout GAIA-campaign-20261008-integration, branch
refactor/complexity-campaign-20261008, HEAD7f39510ab1ef1d4e531d8b12a4eb6b36f556cee4,
main/merge-basea51a48dc4caefbdd1aea82fe4d749054b9465970; BASE_REF=main invariato.
Main concorrente non modificato, soglie/baseline/coverage policy intatte.

## Esecuzione reale

Nuovo external native-execution-20261014, cold prefixes0700empty. Preflight quiet
e full custody PASS, future paths assenti, placement host esatto. Wrapper R91
revisionato invocato **una volta**, argv/env/PID/starttime conservati. Nessun retry.
Systemd invocation48faed586a624a96b38c6acff61f42e6;
service23.503s, exit1, non timeout. Limiti3GiB/512tasks/2CPU, service900s/host930s,
case360s/native150s, test90000/expect20000 invariati.

| Caso originale R91 | Esito reale | Ammissione |
| --- | --- | --- |
| catasto-drilldown.spec.ts22:5, distretto→particella | FAIL, strict locator Particelle ambiguo; retry0, skipped0 | NOT_ADMITTED |
| catasto-drilldown.spec.ts58:5, distretto→anomalie | NOT_RUN; primo caso non accettato ferma il secondo | NOT_ADMITTED |

Raw stats: expected0/skipped0/unexpected1/flaky0, durata Playwright3746.979ms.
Collection intera e selected identity receipts conservati. Error extra-suite:
«Testing stopped early after 1 maximum allowed failures», non secondo test eseguito.

## Failure primaria e secondaria

Prima failure a spec37:68:
`workspace.getByText("Particelle", { exact: true })` risolve a tre elementi:
span etichetta, paragraph KPI, button Particelle. Playwright strict mode rifiuta
il locator prima di verificare visibilità. Timeout20s invariato; non è timeout.
La failure non dimostra assenza di dati né regressione runtime.

In questa esecuzione il gate readiness supera il vecchio count/skip, clicca il
distretto, entra nel frame e verifica «N. distretto:»; poi fallisce l'asserzione
Particelle non modificata. Questa prova è circoscritta al primo percorso, non
certifica l'intero helper, scheduling anno, caso2 o tutti gli assert downstream.

Driver registra separatamente `Unexpected owned teardown status` su namespace1,
failure secondaria già nota. Non sostituire la failure raw del locator con tale
errore driver, né classificare un FAIL come PASS perché slice risulta vuota.
Strict drain non riparato, nessuna nuova esecuzione per diagnosi.

## Custodia e contenimento

Wrapper current-inputs-before/after e runner inputs-before/after preservati.
Service failed/MainPID0/ExecMainStatus1 osservati dopo terminale; metadati unit
non resettati o cancellati. Teardown raw preservato; reviewer verifica exact
custody e populated0 senza dichiarazione universale sullo stato transitorio.
Fixture/prepared e original DB invariati; working failure DB preservato,
hash407e4a3a3ceae1ca6961bcb6335d6b62792fbd0414ba8b8acb5be6c92a744113.
Solo cleanup iniziale autorizzata, nessuna cleanup sintetica post-failure.
Nessun processo concorrente interrotto, reset, riparazione o repinning.

## Evidenze e review

Root durevole:
`/media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-resume-20261012/r91-private-environment/`.
Run effettivo in preparation/service-run e preparation/candidate-runs/native-r91.
native-execution-20261014 conserva grant, observer/preflight/invocation/terminal.
raw-terminal copia byte-esatta di receipt/DB/log/results/screenshot/video/trace,
manifest senza self-entry SHA256
6fe9577ff0f975f40c1ef151e34c09da7bab6892050a4ac62ef8343f3325e374.

Independent terminal review assegnata solo al nuovo review/, read-only su run/
checkout; nessun test/DB open/operational import. Esito finale
**ORIGINAL_CASE0_FAIL / CASE1_NOT_RUN / SECONDARY_DRAIN_FAILURE / NO_ADMISSION**,
559/559 controlli ispettivi. Reviewer confronta155 raw records con i run effettivi
e trace: readiness e frame raggiunti, failure primaria distinta dal strict-drain.
Seal121 file verificato; queste verifiche non sono559 test applicativi.
Pre-terminal docs congelate prima delle annotazioni in pre-terminal-docs/.
Old R89/R90/R91 source receipts e seals intatti. Nessun candidato ammesso o commit.

## Stop e prossima decisione

Grant nativo consumato. Nessun retry automatico, correzione silenziosa del locator
con first() o rimozione asserzioni, cambio timeout o driver. Una eventuale attività
test-only separata può disambiguare le etichette con scope semantico conservando
le asserzioni; prima richiede decisione e review. Non autorizzata da questo run.

Review `review/INDEPENDENT_TERMINAL_REVIEW.md` SHA256
`ff177e1042f0dc14ea4668aeacb119f0871bb9ebe3f0274009cdccdec3a4ff6d`;
review manifest SHA256
`5c656f74855fce7bff2b9abb7eb457eb0a516118b7935d4ebdc0c9b4754f9baa`.
Entrambi verificati dal Coordinator, reviewer fermo; nessuna ammissione.
Manifest raw155records senza self-entry verificato, zero hash failure.

Graphify platform-docs dopo quiet observation/native terminal: exit0,
chunk1/1done,1021nodes/1333edges/161communities, no semantic warning.
Output ignorato/non staged; annotazioni finali dopo refresh non rivendicate indexed.
Mutable docs frozen prima della closure in pre-final-docs/ senza riscrivere freeze.

Handoff finale esterno `native-execution-20261014/HANDOFF.md` e
`FINAL_SHA256SUMS` preservano grant/run, failure raw, source/current receipts,
seals e documenti. Residui non committati in status-final.txt; HEAD/base invariati.
Grant consumato, nessun push/main merge/commit né prosecuzione automatica.
