# GAIA — Goal globale persistente

Fonte: allegato utente `/home/cbo/.codex/attachments/e49b8632-971c-489a-a541-e527356a2d9b/pasted-text-1.txt`.
Stato: ACTIVE. Il checkpoint R1 certifica cinque slice, non l'intera missione.
Il turno precedente produceva progresso verificato; non dimostrava completamento.

## Stato corrente Round3

Nuove prove dopo richiesta «continua»: GIS applicativo confrontato con clean55a,
race native-gesture/center-click indipendentemente preesistente in entrambi,
report `46c6f872`. Attribution storica R3 ancora UNKNOWN. Modal keyboard race
provata da sei browser witness/nove V8 null executions:3214/3217/3220 REACHABLE,
guard necessari, solo3166/3206 UNKNOWN, report `b0a4ac2a`. C12 characterization
test-only in corso, Integration6 before306PASS903/929branchesFAIL100. Runtime
invariato; decisione specifica ripresa nonGIS e cleanup separato chiesta utente,
non ancora registrata. Missione globale immutata ACTIVE/INCOMPLETE.

Verifica indipendente conclusa: report source `7f0c6f0a`,306 PASS/15 spec,
903/929 branch (97,20%), gate100% FAIL; ratchet PASS0, globalcheck30 finding
storici esattamente identici a R3, AST/protetti invariati. Coordinator ha
eseguito la nuova suite frontend completa:4386 PASS/297 spec,exit0; smoke18
PASS/zero skip. Log `/tmp/gaia-capacitas-characterization-final-unit.log` e
`/tmp/gaia-capacitas-characterization-final-smoke.log`. Nessuna nuova suite
backend/worker/build/E2E dichiarata: le prove R3 riguardano runtime invariato.
Test-only continuation verificata, non completa la campagna globale.
Decisioni GIS e cleanup difese ancora pendenti; nessuna nuova wave runtime.
Le diciture in esecuzione/attivo nei checkpoint sottostanti sono storiche.

Ultimo checkpoint: Integration5 `7c7dcc0c`, source congelata `df86527b`,
frontend tree `1ddc7041881a24259e30dd81491aafba44fdb104`. C10/C11 integrate
come `ffeafafd`/`df86527b`; 306 test PASS/15 spec/zero skip, ratchet0 dopo
ciascuna. Coverage combinata:857/857 statement,903/929 branch (97,20%),
251/251 funzioni,748/748 linee. Restano26 arms:21 candidati condizionalmente
irraggiungibili e5 modal arms UNKNOWN. Gate100% FAIL, runtime immutato.
Verifier indipendente attivo; suite frontend completa in esecuzione sul tree
congelato. Nessuna wave runtime autorizzata: decisioni GIS e difese ridondanti
richieste all'utente, nessuna risposta/accettazione implicita registrata.
Gli aggiornamenti Integration4 e precedenti sottostanti sono storia.

Aggiornamento autorevole Integration4 `ae440459`: dodici nuove slice test-only
integrate, 294 test PASS/13 spec/zero skip. Coverage reale combinata: statement
857/857, branch 890/929 (95,80%), funzioni 251/251, linee 748/748. Gate full-file
100% FAIL: 39 branch arms residui, 21 candidati condizionalmente irraggiungibili,
5 modal arms UNKNOWN e 13 arms raggiungibili assegnati a C10/C11. Runtime
Capacitas byte-identico/cognitive472; nessuna riduzione attribuita ai test.
Le due slice test-only sono ACTIVE; Integration5 indipendente prenotata.
Runtime wave sospesa per decisione GIS ancora pendente. Backend R3 già
concluso: i riferimenti RUNNING più avanti sono esclusivamente storici.

Test-only continuation integratedC6/C7/C0 with independent67PASS0skip,
ratchet0 and frozen runtime; coverage401/857statements371/929arms, gate100FAIL.
Capacitas472 unchanged; C1/C8/C2a/C3 characterization next, not another runtime
wave. GIS offline diagnosis proves a library camera-interruption mechanism,
not original failure attribution; user risk decision pending. Global mission
still ACTIVE/INCOMPLETE, not completed by characterization or local checkpoints.

Aggiornamento finale gatebackend:6608PASS449skip2272warnings/exit0/1554,96s
su runtime0b1a0d37. Browser confirmation52PASS7skip dopo primoFAIL51/7/1:
rootcauseGISUNKNOWN, decisione richiesta prima prossima runtimewave.
La campagna globale rimaneACTIVE/INCOMPLETE; nessun blocco attribuito alle
30divergenze baseline storiche. StatoIN_PROGRESS sottostante e storico.

Tre nuove slice integrate e revisionate indipendentemente a `c7d79229`:
Presenze `fbd4172d`, Settings `b0dd9228`, fuel `0b1a0d37`.
617 test mirati PASS, sei runtime full-file statement/branch100%, ratchet0
dopo ogni integrazione. Cognitive aggregata Round3−166, cyclomatic−60,
error−5, warning0, LOC+27 dichiarate. Cumulativo clean55a:1938error,
2749warning,4687finding; cognitive81400,cyclomatic83377. Coda7>300/17>200/
55>100: goal globale ancora INCOMPLETE, nessuna ridefinizione del target.
Presenze550→437, Settings402→296, fuel366→322. Settings esce dalla coda>300,
ma non da quella>200; le altre responsabilità estreme restano aperte.

Suite frontend R3 completa4099PASS/283file, cleanbuildPASS; worker778PASS1skip,
52file. R2 backend6589PASS449skip concluso, ma il nuovo backend R3 richiede
la sua suite: `/tmp/gaia-r3-backend-full-tests.log` IN_PROGRESS, session30021.
Browser R3 e verifica indipendente finale IN_PROGRESS. Nessun PASS esteso a
runtime non ancora verificato, skip o provider live. Solo planning R4, nessuna
autorizzazione runtime prima del checkpoint completo verde.

La tabella seguente conserva l'audit storico del riavvio R1; questo stato
corrente e i report Round3 lo aggiornano senza dichiarare chiusa la missione.

## Missione invariata

Semplificare strutturalmente l'intero backend, frontend e worker senza alterare
comportamento, API, schema dati, autenticazione, autorizzazione, transazioni,
concorrenza, portali esterni o UI. Priorità alle metriche estreme e al rischio
reale, non al conteggio dei finding o al semplice spostamento di codice.

Baseline audit8/10:1665file,20261callable,1956error,2758warning,4714finding.
Snapshot Git operativo iniziale55a1b1d3; stato clean/R1 distinto dall'audit dirty.
Avanzamento R1:1944error,2751warning,4695finding;8callable>300,17>200 ancora aperti.

## Requisiti e prove di completamento

| Requisito originale | Evidenza autorevole richiesta | Stato al riavvio |
| --- | --- | --- |
| 0 regressioni complexity | Ratchet completo su ogni slice e integrazione contro merge-base55a | R1 PASS, ogni R2 da verificare |
| 0 regressioni funzionali | Invarianti, characterization prima/dopo, suite finali contro codice finale | R1 verificato nel perimetro testato; R2 aperto |
| Error -50% o migliore | Audit AST globale comparabile; target978 o meno senza inflation | INCOMPLETE,1944 |
| Warning -25% o migliore | Audit AST globale comparabile; target2068 o meno senza inflation | INCOMPLETE,2751 |
| Cognitive>300→0 | Ranking completo tutti runtime, nessun trasferimento debito | INCOMPLETE,8 |
| Cognitive>200→0 | Ranking completo tutti runtime, nessun trasferimento debito | INCOMPLETE,17 |
| Cognitive>100 fortemente ridotti | Confronto coda/distribuzione e rischio degli hotspot | INCOMPLETE,55 |
| Callable grandi/cyclomatic/nesting/params | Metriche prima/dopo e aggregate inclusi nuovi helper/file | R1 progresso locale, obiettivo globale aperto |
| Full coverage modificati | 100% full-file statement/branch secondo tooling invariato | R1 sei runtime PASS; nuovi R2 da verificare |
| Moduli localmente comprensibili | Review responsabilità, layering, API, dipendenze e interleaving | Mega-callable residui, INCOMPLETE |
| Nessun laundering | Somme/max/findings/LOC e review diff, non move o wrapper artificiali | R1 verificato, gate permanente |
| Soglie/scope/esclusioni immutati | Diff/hash dei file protetti rispetto snapshot55a | R1 verificato, gate permanente |
| Baseline non gonfiata | Diff/hash baseline, nessun baseline/repair per rendere verde | R1 verificato, gate permanente |
| Suite finali PASS | Backend/frontend/worker/build/E2E sul runtime definitivo, skip registrati | R1 PASS, da ripetere al nuovo checkpoint |
| Audit globale migliore | Report completo reproducibile e domini/delta/percentuali | R1 delta-19finding insufficiente al goal globale |
| Provenance30 divergenze storiche | Report per callable/metric/commit e nuova verifica non attribuita a R2 | R1 classificato, nessun assorbimento |
| Ownership/branch/worktree/commit | Registry preventivo esclusivo, integrazione revisionata per slice | Permanente, R2 pianificato |
| Graphify/domanda architetturale | Query/refresh tramite target modulo e docs, risultati verificati | Da mantenere per ogni topology change |

Le percentuali non giustificano refactoring insicuri. La correttezza prevale
sulla metrica e la reviewability sulla velocità. Nessun traguardo locale
ridefinisce la North Star: aree critiche modificabili senza comprendere
simultaneamente migliaia di righe o centinaia di decisioni.

## Prossima unità di progresso

Tre slice indipendenti: modello derivato Presenze, configurazione provider
Settings, characterization completa prima della prima fase fuel analytics.
Una responsabilità revisionabile per agente; integration dopo gates verdi.
Se una slice è bloccata, scegliere una prossima azione sicura sul goal globale,
non dichiarare conclusa la campagna per la sola difficoltà di quella slice.
