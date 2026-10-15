# R90 — Catasto drill-down: preparazione test-only della readiness

## Autorizzazione e snapshot

«Prepara e revisiona la correzione dei test, senza nuovi E2E».
Checkout esclusivo `/home/cbo/CursorProjects/GAIA-campaign-20261008-integration`;
branch `refactor/complexity-campaign-20261008`, HEAD
`7f39510ab1ef1d4e531d8b12a4eb6b36f556cee4`, main/merge-base
`a51a48dc4caefbdd1aea82fe4d749054b9465970`. Nessun commit, servizio,
browser, nuovo E2E, modifica DB, driver, autenticazione o main. Goal incompleto.

## Problema e modifica circoscritta

Il titolo precede il caricamento list/history/KPI; count immediato può leggere
zero righe prima della pubblicazione del modello. La causa precisa del precedente
R89 SKIP resta non dimostrata: non riclassificarlo come PASS o errore runtime.

Solo nei due casi, sostituita la sequenza goto/titolo/count con un helper test-only
che osserva le vere richieste fetch/XHR, preserva redirect e attende un DOM coerente
con lista e anno importato. Nessun mock API nell'E2E, sleep, nuovo skip o aumento
timeout. Poll usa il timeout expect già configurato di 20s, test 90s invariato.
Solo il vuoto confermato permette il precedente skip; errori e timeout non
restituiscono zero. KPI opzionali conservano il fallback runtime.

Il boundary del cambio anno è acquisito dopo lettura del primo body history:
richiede nuove richieste list/history iniziate dopo quel boundary. Non bastano
due risposte da effetti iniziali duplicati, neppure avviate tra header e body.
Il browser può consumare history prima dell'osservatore Node: in quel caso un
reload già iniziato viene conservativamente escluso e il gate può scadere.
Questo limite fail-closed richiede verifica nativa distinta; non è una prova
universale della sincronizzazione React. Richieste duplicate arbitrariamente
tardive oltre il body non sono identificate semanticamente come generazioni React.

Snapshot DOM unico: article del titolo, stato loading, totale, righe paginate,
empty-state, anno e banner errore. Status/rows non bastano senza risposte richieste
valide. Attesa KPI body governata anche da isLoading/setRows del runtime: la sola
ricezione degli header KPI non dimostra readiness.

## Invarianti e provenienza

Spec precedente congelata prima delle modifiche. Controllo byte-exact dimostra
solo import helper e due sostituzioni readiness rispetto al freeze; tutte le
asserzioni downstream, login, timeout, skip legittimi e candidato iframe/click
precedente invariati. Quel candidato era NOT_ADMITTED e resta tale nel nuovo
insieme. Runtime/config hash invariati. Nessuna baseline, soglia, esclusione,
policy coverage o file runtime modificato. Nessuna riduzione di complessità
applicativa rivendicata; ratchet/scanner non eseguiti in questa preparazione.

## Matrice di caratterizzazione

| Behavior | Existing test | Missing | Added | Result |
| --- | --- | --- | --- | --- |
| List/history/KPI tardivi, righe non ancora rese | Spec contava immediatamente | Gate readiness | Unit osservatore e DOM | PASS unit |
| Cambio anno, vuoto transitorio | Nessuna matrice nel vecchio spec | Reload riconosciuto | Unit reload e duplicati header/body | PASS unit; limite ordering sopra |
| Vuoto reale, solo FD, history vuota | Skip originario | Distinzione da loading | Unit payload/empty-state | PASS unit |
| Liste paginate e import non completati | Runtime preservato | Conteggio/coerenza anno | Unit 20 record / 12 righe | PASS unit |
| HTTP401/500, JSON errato, payload invalidi | Nessun gate specifico | Errori non diventano skip | Unit failure | PASS unit |
| Redirect307→slash e fetch/XHR | R89 sole evidenze status | Documento HTML da escludere | Unit redirect/resource type | PASS unit |
| KPI failure/fallback e body/render tardivo | Runtime già tollera KPI failure | Readiness distinta | Unit fallback/loading | PASS unit; non browser proof |
| Token assente, timeout, navigation failure | Non caratterizzato | Nessun false empty | Unit pending/rejection/cleanup | PASS unit; poll mock, timeout reale non misurato |
| Dettaglio iframe/particella/anomalie | Due E2E originali | Nuovo snapshot nativo | Nessun E2E autorizzato | NOT_RUN |

## Verifiche e failure conservate

- Prima invocazione Vitest: FAIL CLI `Unknown option --minWorkers`, prima della
  collection; Vitest4.1.6 non supporta quell'opzione. Log conservato.
- Invocazione corretta con solo `--maxWorkers=1`: 24 PASS / 2 FAIL. Fixture
  `it.each` espandeva gli array come argomenti, passando undefined/oggetto anziché
  una lista; typecheck corroborava l'errore. Failure conservate, non PASS.
- Correzione della sola tabella unit a oggetti `{ rows }`, più controcaso della
  review sul boundary body: nuova invocazione distinta, **27 PASS**, 804ms.
- Typecheck mirato dei tre file con strict/noEmit: nuova invocazione PASS.
  Primo typecheck FAIL correlato alla fixture conservato.
- Controllo preservazione byte-exact e runtime/config checksum: PASS.
- `git diff --check`: PASS al candidato. Nessuna suite completa ripetuta.
- Coverage runtime non rimisurata: nessun runtime modificato. Unit con eventi e
  DOM jsdom non certifica browser, quota device, DB, servizi, auth o full-stack.

Comandi finali dalla directory frontend:
`node_modules/.bin/vitest run tests/unit/distretti-readiness.test.ts --maxWorkers=1`;
`node_modules/.bin/tsc --noEmit --target ES2022 --module ESNext --moduleResolution Bundler --strict --skipLibCheck --esModuleInterop tests/e2e/helpers/distretti-readiness.ts tests/e2e/catasto-drilldown.spec.ts tests/unit/distretti-readiness.test.ts`.

## Review e ammissione

Reviewer indipendente possiede solo la directory esterna `review/`, checkout
read-only; nessun E2E/test aggiuntivo affidato. Review preliminare ha trovato
l'intercettazione errata del documento HTML, corretta con filtro fetch/XHR;
ulteriore controcaso header/body corretto con boundary dopo parsing.
Review finale **SOURCE_PREPARATION_ACCEPTED_WITH_ORDERING_LIMIT_NO_NATIVE_ADMISSION**:
105/105 controlli indipendenti di sorgente/provenienza, seal di 36 file verificato.
Questi sono controlli ispettivi, non ulteriori test applicativi. Stato
**PREPARED / NOT_ADMITTED**: nessuna autorizzazione
nativa ereditata dalla precedente R89, ormai consumata. Le identità di riga e
hash dei casi cambiano; occorrono nuovo binding/review/autorizzazione separati.

## Evidenze e handoff

Root durevole:
`/media/cbo/ARCHIVIO_SSD/.codex-gaia-campaign-resume-20261012/r90-drilldown-readiness/`.
`before/` conserva spec, PROGRESS, refs, status e runtime/config hash;
`candidate/` conserva i tre file finali e il diff completo contro HEAD;
`checks/` conserva ogni log/failure, exit code e programma preservazione.
Manifest candidate verificato senza auto-inclusione; freeze storico non riscritto.
Ricevute R89, working failure DB e manifest storico difettoso intatti.

Review finale `review/INDEPENDENT_FINAL_REVIEW.md`, SHA256
`042294aac63b4875ee38da2d5e11650ec01a0cdbaff3cb29ff6968254b08d047`;
seal `review/REVIEW_SHA256SUMS`, SHA256
`fdc3f79708f86648a3a83ec8d887f71c3a655c6ed34b4db83b32201c20636f42`.
Seal candidate `candidate/SHA256SUMS`, SHA256
`89d8a9eac193d7cf1a1ddd15617c46b14df4000d07cdf039dc7ca271ef574f8f`.

Graphify platform-docs aggiornato tramite target make dopo osservazione quiet:
exit0, chunk1/1 done, 1013 nodi/1315 edge/161 comunità, nessun semantic warning.
Log `checks/graphify-docs.log`; output generato non staged. Annotazioni finali di
chiusura aggiunte dopo tale refresh non rivendicate come semanticamente indicizzate.
Documenti mutabili congelati in `pre-closure-docs/` prima di queste annotazioni.

Handoff finale `HANDOFF.md`, manifest durevole `FINAL_SHA256SUMS` senza
auto-inclusione. Nessun commit o ammissione automatica. Prossima eventuale fase:
decisione separata sul nuovo binding nativo e sul limite ordering, non ripetizione
di R89 né correzione del driver. Non avviare servizi/E2E sulla base di questo report.
