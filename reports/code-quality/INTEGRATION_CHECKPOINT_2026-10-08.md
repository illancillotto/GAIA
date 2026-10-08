# GAIA — Integration checkpoint 2026-10-08

## Esito e perimetro

**GREEN per le due slice runtime ammesse P1/P6**: review indipendente positiva,
nessun overlap, integrazione sequenziale, ratchet completo PASS con zero finding
dopo ciascun cherry-pick, 479 test pertinenti PASS, coverage full-file statement
e branch 100% su entrambi i runtime, smoke e typecheck PASS.

Questo checkpoint non certifica tutte le suite finali o il completamento della
campagna. Le riduzioni sono concrete ma limitate: i callable estremi restano
525 cognitive per Presenze e 366 per Settings. Il target Presenze iniziale
(-50% oppure sotto 250) non è raggiunto dalla slice circoscritta autorizzata.
Le altre slice senza runtime approvato non contribuiscono alla riduzione.

## Snapshot, ownership e branch

- Base autorevole: `55a1b1d35911451e018b662c2acc450bf5994ea2`.
- Worktree: `/home/cbo/CursorProjects/GAIA-campaign-20261008-integration`.
- Branch: `refactor/complexity-campaign-20261008`.
- HEAD alla conclusione dei gate runtime: `0861f811293f1acef6ddaff7d3de42ea990d9a88`.
- HEAD iniziale integration: `55082ef213db0c7b06b0d67d5206acf69cd3cdb8`.
- Il merge-base con main resta lo snapshot autorevole.
- Ownership INTEGRATION: branch integration e questo report; runtime read-only
  per review, modificato esclusivamente tramite cherry-pick dei due candidati.
- Main, lavoro concorrente nel checkout principale e branch originali invariati.
- Nessuna modifica backend durante la suite backend del Coordinator.

## Review indipendente

| Slice | Commit candidato | Commit integration | Esito |
| --- | --- | --- | --- |
| P1 card anomalie mensili | `c14eb8bd19d5645d1cb57442379c771d789730e2` | `b37d7ec56da139073901fcb781b6ab8877d7005f` | APPROVED / IMPROVED |
| P6 mapping verifica SISTER | `d92d39aa463ec998e26d83cbe01a25342c1cfeb7` | `0861f811293f1acef6ddaff7d3de42ea990d9a88` | APPROVED / IMPROVED |

P1 possiede soltanto pagina giornaliere, relativo test e report. P6 possiede
soltanto workspace settings e report. Gli insiemi di file sono disgiunti;
nessun file lib/hooks/UI/layout, configurazione, tooling, baseline o shared
modificato. Nessun import nuovo, ciclo di import o aumento delle dipendenze:
i presenter P1 sono privati al file, l'helper P6 è privato al workspace.

### P1 — Card anomalie

La modifica consolida due copie quasi identiche della stessa card di dominio.
Mantiene differenze intenzionali tra raggruppamento giorno e collaboratore:
titolazione, sottotitolo, presenza dell'orario nel corpo, profilo, severità,
richieste, fallback di stato e testo operativo. Mantiene ordine dei record,
key React e ordine delle due azioni del click (azzeramento ritorno modal,
selezione record). Nessuna modifica a loader, chiamate API, stato, effect,
dependency array, cleanup, permessi o editor.

`operationalRuleHint` è puro: valuta campi scalari e formatta minuti. Calcolarlo
una sola volta anziché due non modifica side effect o ordine delle mutazioni.
Il nuovo presenter riceve `onOpen(): void`; il record resta nella closure del
parent come nell'originale. Due componenti privati delimitano card e badge
senza creare wrapper duplicati o trasferire un mega-callable altrove.

I due nuovi test parametrizzati verificano contenuto concreto nelle due viste,
assenza del nome nella vista collaboratore, chiamata dettaglio con record
corretto e navigazione del modal. Non cambiano né indeboliscono test esistenti.
Le suite precedenti coprono ulteriori fallback, filtri, errori, race e permessi.

### P6 — Verifica credenziali SISTER

Consolidamento effettivo di due mapping identici, applicati da refresh HTTP
e messaggio WebSocket. La lista usa fallback all'id del default; gli alias
default/legacy usano fallback al proprio id. Questi fallback restano distinti.
Identità dello stato assente e delle credenziali non modificate preservata.
L'helper continua a essere chiamato soltanto con `verified_at` truthy;
busy/error, refresh successivo, cleanup e dipendenze degli effect invariati.

Le suite UI esistenti hanno casi HTTP/WebSocket, id null, stato indisponibile,
default e alias assenti, parsing fallito e cleanup. Nessun test rimosso o
modificato. Come controverifica indipendente sono stati confrontati i due
callback originali a main con il nuovo helper, estraendo AST TypeScript e
transpilando solamente queste funzioni pure in memoria: **1512 confronti PASS**,
sia sul valore serializzato sia sull'identità di stato/lista/alias. Combinazioni:
stato null, liste vuote/multiple, default e alias null o distinti, id null/
undefined/vuoto/abbinato/non abbinato e timestamp presente o null.
Script `/tmp/gaia-integration-settings-differential.cjs`, log dedicato sotto.

## Metriche verificate

Scansione AST indipendente post-integrazione dei due file, confrontata con le
misure prima sullo stesso snapshot committed. Le somme includono il traversal
annidato dello scanner e non sono conteggi di decisioni uniche.

| Metrica | P1 prima | P1 dopo | P6 prima | P6 dopo | Delta combinato |
| --- | ---: | ---: | ---: | ---: | ---: |
| Principal cognitive | 550 | 525 | 402 | 366 | -61 |
| Principal cyclomatic | 457 | 432 | 334 | 316 | -43 |
| Principal LOC | 2275 | 2194 | 1565 | 1527 | -119 |
| File cognitive sum | 1530 | 1472 | 718 | 621 | -155 (-6,90%) |
| File cyclomatic sum | 1526 | 1470 | 689 | 634 | -111 (-5,01%) |
| File effective LOC | 3009 | 2994 | 1887 | 1869 | -33 (-0,67%) |
| Error finding | 26 | 22 | 9 | 6 | -7 |
| Warning finding | 29 | 24 | 16 | 11 | -10 |
| Callable count | 310 | 312 | 127 | 128 | +3 |
| useState | 21 | 21 | 11 | 11 | 0 |
| useEffect | 13 | 13 | 2 | 2 | 0 |

Aggregato perimetro P1/P6: 80→63 finding (-21,25%), 35→28 error (-20%),
45→35 warning (-22,22%). Non usare questo delta scoped come delta globale.
I finding nuovi dei piccoli presenter sono inclusi negli aggregati: il warning
cyclomatic P1 non viene occultato. Nessun helper nuovo ha error-level debt.
Il calo degli aggregati e della duplicazione sostiene `IMPROVED`, non soltanto
il calo dei callable principali. Nessun finding equivale automaticamente a
un problema indipendente.

## Test, coverage e gate

| Gate | Esito | Evidenza |
| --- | --- | --- |
| Ratchet completo dopo P1 | PASS, 0 finding | `/tmp/gaia-integration-p1-ratchet-2026-10-08.log` |
| Ratchet completo dopo P6 | PASS, 0 finding | `/tmp/gaia-integration-p6-ratchet-2026-10-08.log` |
| Unit pertinenti combinati | PASS, 479 test / 5 file, zero skipped | `/tmp/gaia-integration-p1-p6-tests.log` |
| Coverage full-file P1 | Statement 1186/1186; branch 1336/1336; function 310/310 | JSON combinato |
| Coverage full-file P6 | Statement 477/477; branch 658/658; function 127/127 | JSON combinato |
| Coverage combinata | Statement 1663/1663; branch 1994/1994; function 437/437; line 1396/1396 | JSON combinato |
| Smoke frontend | PASS, 18 test, zero skipped | `/tmp/gaia-integration-smoke-2026-10-08.log` |
| Typecheck | PASS | `/tmp/gaia-integration-typecheck-2026-10-08.log` |
| Settings differenziale | PASS, 1512 confronti / 2 callback originali | `/tmp/gaia-integration-settings-differential.log` |
| Diff check e integrità scope | PASS | `git diff --check`; nessun diff backend/baseline/tooling |

Il JSON coverage `/tmp/gaia-integration-p1-p6-coverage/coverage-final.json`
contiene esattamente i due percorsi runtime dell'integration, non report copiati
da altre worktree. Tutti gli hit statement, esiti branch e funzioni sono >0,
verificati direttamente per file. Nessuna suppression, ignore, exclusion o
soglia aggiunta; è una misura V8 del file completo.

Entrambi i ratchet dichiarano esplicitamente
`baseline_commit=55a1b1d35911451e018b662c2acc450bf5994ea2`.
I symlink delle dipendenze locali sono esclusi solo dal Git info/exclude
d'ambiente predisposto dal Coordinator: nessuna esclusione runtime o del
scanner modificata per superare il gate.

Il primo tentativo della scansione scoped ha usato l'opzione inesistente
`--paths` e ottenuto exit 2. Il comando corretto usa path posizionali ed è
PASS, con 440 callable / 2 file / 28 error / 35 warning; non viene confuso
il tentativo fallito con un controllo riuscito. La prima decodifica automatica
del log ratchet ha letto la parentesi della variabile Make anziché il JSON;
ripetuta dalla riga JSON corretta, conferma entrambi i PASS/0. Nessuna modifica
al codice o gate resa necessaria da questi errori di invocazione.

## Stato globale e limiti

La provenance già integrata documenta 30 divergenze globali preesistenti:
15 aumenti runtime storici e 15 finding nei test worker. Non sono introdotti
da P1/P6 e non sono assorbiti nella baseline. L'attività integration non
riesegue il confronto integrale, già riprodotto dall'agente provenance.

Il Coordinator sta eseguendo la suite completa backend nello stesso checkout,
su runtime backend invariato. Nessun cherry-pick backend viene effettuato
durante quel processo. Una failure compare nel log ancora incompleto: causa
ed esito finale sono responsabilità del gate finale e non sono dichiarati PASS.

Build clean, suite frontend completa, worker ed E2E sono demandati al verifier
finale. Gli ESLint warning legacy descritti nei report P1/P6 non vengono
corretti incidentalmente e non diventano errori introdotti dalla campagna.
Graphify frontend dei due owner è aggiornato tramite i target Make dedicati;
questa integrazione mantiene identici i blob runtime approvati e non introduce
ulteriori relazioni. Nessun graph generato è committato.

Il prossimo checkpoint può avviare una slice isolata Wave 2 con ownership
esplicita; non equivale a un'autorizzazione a integrare backend mentre la suite
iniziale è ancora attiva né ad accettare altre slice prive di coverage 100%.

## Integrità sorgenti

SHA-256 dopo i gate:

- Presenze: `1a5d508a193f06407bc2d77165443f9442c33ce991fb980c934a357d90dde71a`.
- Settings: `585a63ec421513f2162d54215fab33832307b9e3f875c28f1f5efaca1b3d59e4`.
- Baseline: `38e6b7943cb4f2b214baac51290fdfc97a88c8ee1bf80d3c639642de77cd4d95`.

Nessun diff rispetto a main nei runtime backend, test backend, worker,
`config/code-quality` o `tools/code_quality`. Working tree pulito prima
della scrittura di questo report. Il commit integration successivo contiene
soltanto questo documento e non modifica i runtime verificati.

## Riproduzione

```bash
git merge-base HEAD main
git status --short
make complexity-ratchet BASE_REF=main
python3 tools/code_quality/complexity.py report \
  frontend/src/app/presenze/giornaliere/page.tsx \
  frontend/src/components/elaborazioni/settings-workspace.tsx \
  --json /tmp/gaia-integration-p1-p6-complexity.json \
  --markdown /tmp/gaia-integration-p1-p6-complexity.md
cd frontend
VITEST_COVERAGE_INCLUDE=src/app/presenze/giornaliere/page.tsx,src/components/elaborazioni/settings-workspace.tsx \
  npm run test:unit -- \
  tests/unit/presenze-giornaliere-page.test.tsx \
  tests/unit/presenze-giornaliere-regressions.test.tsx \
  tests/unit/elaborazioni-settings-presenze-tab.test.tsx \
  tests/unit/elaborazioni-settings-sister.test.tsx \
  tests/unit/elaborazioni-workspace-modal.test.tsx \
  --maxWorkers=2 --coverage \
  --coverage.reportsDirectory=/tmp/gaia-integration-p1-p6-coverage
npm test
npm run typecheck
```
