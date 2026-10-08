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

Stato delle altre slice comunicato dal Coordinator al checkpoint; non sono
review o gate eseguiti dall'Integration Agent:

| Agent | Stato | Evidenza e limite |
| --- | --- | --- |
| P2 Capacitas | BLOCKED_COVERAGE runtime; characterization integrata | 28 test pertinenti PASS; coverage full-file branch 28,31%; nessuna riduzione runtime |
| P3 Analytics | Characterization pronta; runtime non integrato | Commit test-only `48de12ef`; attesa suite backend iniziale prima di eventuale cherry-pick |
| P4 Catasto anomalie | BLOCKED_COVERAGE runtime; characterization pronta | 27 nuovi test UI significativi; coverage circa 59% statement / 40% branch |
| P5 Utenze detail | Characterization in corso | Nessun runtime candidato approvato al checkpoint |
| B4 Network traffic | Readiness per slice isolata Wave 2 | Coordinator: 19 test PASS; 283 statement e 92 branch al 100%; non ancora refactor integrato |
| B6 Bonifica | BLOCKED_COVERAGE runtime | Coordinator: 14 test PASS; coverage circa 34% statement / 28% branch |
| B5 Wiki | Readiness in corso | Nessun runtime approvato al checkpoint |

I numeri parziali non equivalgono a coverage conforme. Non vengono integrate
slice runtime prive di 100% full-file, né dichiarati risolti gli hotspot intatti.

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

## Follow-up — Characterization P3/P4/P5 integrata

Review indipendente e cherry-pick sequenziali dei tre candidati **test-only**.
Nessuno modifica runtime, configurazioni, matcher, soglie o baseline.
Il checkpoint runtime P1/P6 resta valido per gli stessi blob già verificati;
non viene rieseguita la loro coverage dopo aggiunte che non li modificano.

| Agent | Commit candidato | Commit integration | Classificazione runtime |
| --- | --- | --- | --- |
| P3 | `48de12ef5f0baf1068c1f9df8e3fca5c8dde1918` | `5efac219ef5f930cc221c361d35d271642c6531e` | NO_CHANGE / BLOCKED_COVERAGE |
| P4 | `764d31586f4e10c218adc6a8eeb39c0f2a6194e9` | `a205a50879a77295b681e11ef292c23e1053e3c3` | NO_CHANGE / BLOCKED_COVERAGE |
| P5 | `3cb1b6e379dadc4df84d08d957afaf8f2ea75843` | `71b817b9c03c09411857359b43f8832c7be3a651` | NO_CHANGE / BLOCKED_COVERAGE |

Ownership dei test disgiunta: un file nuovo backend analytics, un file nuovo
frontend anomalie e un file nuovo frontend dettaglio Utenze; report dedicati.
Nessun test esistente rimosso, skipped o indebolito. Nessun callable runtime
trasferito e nessuna riduzione metrica attribuita alle caratterizzazioni.

P3 usa SQLAlchemy con database SQLite in-memory isolato per verificare risultati
delle route reali: precedenza classificazione veicoli, coefficienti/rounding,
attribuzione operatori, fallback, storni, costi null e periodi/date. Gli helper
fixture originali sono riusati, senza sostituire il comportamento con mock
dell'algoritmo. Il rerun usa un processo e database diversi da quelli della
suite completa del Coordinator, senza interferire col suo engine.

P4 importa la pagina reale e mocka solo API/navigation e confini esterni.
Verifica URL/paginazione, selezione/draft, filtri locali/backend, token assente,
ordine creazione report→collegamento→refresh, busy durante promise pendenti,
failure parziali e retry. Il contratto props di accesso è verificato, senza
spacciarlo per enforcement autorizzativo live. I wizard non caratterizzati
rimangono esplicitamente fuori dalla prontezza runtime.

P5 importa la pagina reale e verifica caricamento/autorizzazione, modalità
lettura/modifica, payload e fallback di salvataggio, errori API, identità/token
delegati alle sezioni e comportamento persona/azienda. Le sezioni figlie mockate
non sono dichiarate coperte. Documenti, preview e comandi NAS/race restano
responsabilità non ancora caratterizzate al 100%.

### Verifiche nel checkout integration

- P3: originali + nuovi **50 PASS**, zero skip; JSON indipendente
  `/tmp/gaia-integration-p3-coverage.json` conferma 600/688 statement e
  253/332 branch (83,63% combinata), quattro esclusioni legacy invariate.
  Il comando pytest con reporting coverage passa; ciò **non è PASS del gate
  coverage100%**, che resta non raggiunto e blocca il refactor runtime.
- P4: nuova suite + utility originale **116 PASS**, due file, zero skip;
  `/tmp/gaia-integration-p4-tests.log`.
- P5: nuova suite **21 PASS**, un file, zero skip;
  `/tmp/gaia-integration-p5-tests.log`.
- Ruff del nuovo test backend PASS; ESLint dei due test frontend PASS, nessun
  warning/error nel log `/tmp/gaia-integration-gap-eslint.log`.
- Ratchet completo dopo P3 e dopo P4 **PASS, zero finding**, entrambi contro
  `55a1b1d35911451e018b662c2acc450bf5994ea2`. Log
  `/tmp/gaia-integration-p3-ratchet-2026-10-08.log` e
  `/tmp/gaia-integration-p4-ratchet-2026-10-08.log`.
- Ratchet completo dopo P5 **PASS, zero finding**, stessa baseline autorevole;
  `/tmp/gaia-integration-p5-ratchet-2026-10-08.log`.
- Typecheck finale dopo i tre cherry-pick PASS, smoke finale **18 PASS**,
  zero skipped; `/tmp/gaia-integration-gap-typecheck.log` e
  `/tmp/gaia-integration-gap-smoke.log`.
- Diff check PASS; nessun diff runtime introdotto dopo `72228cce` e baseline/
  tooling invariati contro main. Working tree contiene soltanto gli aggiornamenti
  di questo report e registro prima del commit documentale.

I JSON coverage dei candidati P4/P5 sono stati controllati direttamente e
confermano i gap full-file: P4 380/643 statement, 261/645 branch; P5 209/576
statement, 229/610 branch. Non sono rieseguiti qui con gate abbassati: sono
evidenze della readiness insufficiente, non copertura conforme. Tutti i tre
runtime restano byte-identici rispetto al checkpoint P1/P6 precedente.

Registro ownership integration sincronizzato dalla copia aggiornata dal
Coordinator nel checkout principale, senza scrivere quel checkout. P1/P6
MERGED, P2–P5 runtime BLOCKED; B4 Network e B5 Wiki ACTIVE in worktree isolate,
B3 Terreni/B6 Bonifica BLOCKED secondo le misure di readiness. Le integrazioni
test-only sono esplicitamente distinte dagli stati dei refactor runtime.
Nessun runtime Wave 2 viene integrato da questo follow-up.

**Checkpoint test-only GREEN**: review, test pertinenti e tre ratchet sequenziali
completati. Questo esito non supera i gate coverage mancanti dei runtime né
certifica le suite finali della campagna. La suite backend completa iniziale del
Coordinator è ancora attiva (circa 72% nel log osservato) con almeno una failure
già visibile; nessun tentativo di correggere quella failure non correlata.

## Follow-up Wave 2 — B4 Network statistics

Review indipendente del candidato `664df72fed88bc803032532179b9cb4148855908`;
cherry-pick sulla branch integration come
`69c15454af84d2b474c73ae4a88093cec44594c2`, dopo HEAD iniziale
`2b2190c167de72bff3cb383686d4fa02ac935871`. Merge-base autorevole invariato:
`55a1b1d35911451e018b662c2acc450bf5994ea2`.

Ownership esclusiva: `backend/app/modules/network/router/helpers/traffic.py`,
nuovo `backend/tests/test_network_traffic_campaign.py`, report B4. Nessun overlap
con le slice frontend, test-only o B5 Wiki ancora isolata. Nessun file core/shared,
API route, configurazione, soglia, esclusione, baseline o tooling modificato.
Il registro integration segna B4 MERGED; main non viene modificato.

### Equivalenza e review architetturale

La slice sostituisce quattro conversioni identiche con un helper locale puro
di cinque LOC. L'espressione `max(int(str(parsed.get(field, 0)).strip()), 0)`
e le eccezioni `TypeError`/`ValueError` sono identiche all'originale; il getter
resta dentro il try. Le due letture sent/received rimangono nei due rami active/
non-active e nello stesso ordine rispetto a lookup, lifecycle e confronti IP.
Non si anticipa una lettura IP né si crea uno snapshot che alteri i fallback.
Query, iterazione, filtri, ordinamenti, aggregazioni, payload e side effect DB
non cambiano. Nessun nuovo import o dipendenza: assenti import ciclici,
component explosion e astrazioni generiche.

I test di caratterizzazione sono significativi: matrice di byte validi/invalidi
su sorgente active/retired/assente, propagazione ai totali/top/timeline, contatori
non-zero con proprietà IP dinamica e ordine degli accessi, eventi assenti.
Non modificano i test originali né introducono skip o suppressioni. I mock
simulano il risultato delle query ai confini; il parser e l'aggregatore reali
sono eseguiti. I test di ordine proteggono un'invariante già caratterizzata
dalla suite storica, senza introdurre seam nel runtime.

### Metriche indipendenti dopo integrazione

Lo scanner del checkout integration riproduce esattamente `files` e `callables`
del JSON B4 approvato. Sono confrontati gli aggregati comprendenti il helper,
non soltanto il callable principale.

| Metrica | Prima | Dopo | Delta |
| --- | ---: | ---: | ---: |
| Statistics cognitive | 209 | 181 | -28 (-13,40%) |
| Statistics cyclomatic | 109 | 101 | -8 |
| Statistics callable LOC | 226 | 214 | -12 |
| File cognitive sum | 322 | 297 | -25 |
| File cyclomatic sum | 181 | 176 | -5 |
| Decisioni aggregate `sum(cyclomatic-1)` | 175 | 169 | -6 |
| File effective LOC | 456 | 449 | -7 |
| Callable count | 6 | 7 | +1 |
| Error/warning finding | 8/4 | 8/4 | 0/0 |

Nuovo helper: cognitive3, cyclomatic3, LOC5, nesting2, params2, nessun finding.
Dipendenze/import invariati a20. I finding invariati non nascondono il calo reale
delle metriche: è eliminata la duplicazione e diminuisce anche il debito aggregato.
Classificazione **IMPROVED**; statistics passa sotto cognitive200 ma rimane
181, sopra la soglia25. `run_network_scan` rimane invariato e non è risolto.

Perimetro runtime integrato P1/P6/B4: cognitive sum2570→2390 (-180; -7,00%),
cyclomatic sum2396→2280 (-116; -4,84%), effective LOC5352→5312 (-40; -0,75%),
error43→36 (-7), warning49→39 (-10). Questi sono delta scoped sulle tre slice,
non percentuali globali del repository né metriche di problemi indipendenti.

### Verifiche integration B4

- Suite helper/nuova caratterizzazione rieseguita **45 PASS**, zero skipped:
  `/tmp/gaia-integration-b4-tests.log`.
- Coverage full-file reale `traffic.py`: **276/276 statement e92/92 branch**,
  zero missing, partial branch o excluded statement. JSON indipendente
  `/tmp/gaia-integration-b4-coverage.json`, verificato direttamente per percorso.
  `coverage report --fail-under=100` PASS.
- Ruff runtime e nuovo test PASS; Ruff format-check nuovo test PASS.
- Scanner indipendente PASS: `/tmp/gaia-integration-b4-complexity.json` e `.md`.
- Diff-check e integrità baseline/tooling PASS; nessun altro runtime modificato
  in questo follow-up.
- Suite API Network indipendente **50 PASS**, zero skipped;
  `/tmp/gaia-integration-b4-api-tests.log`. Insieme ai45 helper sono95 test
  pertinenti rieseguiti senza duplicare le suite complete globali. I98 warning
  JWT test-key già esistenti sono conservati, nessuna failure.
- Ratchet completo post-cherry-pick **PASS, zero finding**, baseline autorevole
  `55a1b1d35911451e018b662c2acc450bf5994ea2`;
  `/tmp/gaia-integration-b4-ratchet.log`.

**Checkpoint B4 GREEN** per la slice integrata: review, test95, coverage100%,
misure indipendenti e ratchet completo conformi. Non certifica il completamento
di Network o il successo delle suite globali ancora in verifica.

Il file misurato è quello completo nell'integration, non un report copiato
dalla worktree B4. La source-directory di Coverage evita l'eager-import dotted
già diagnosticato senza restringere righe/branch o modificare policy/config.
Graphify Network del candidato è aggiornato mediante target Make dedicato;
il blob runtime integrato è identico e non introduce ulteriori relazioni.
Grafi generati non versionati. SHA-256 runtime:
`50f514858de2b3a997496648932416c67342c5c358e079626ed43cb0c86fd717`.

Comandi dal backend per coverage e regressione API separata:

```bash
COVERAGE_FILE=/tmp/gaia-integration-b4.coverage APP_ENV=test \
  DATABASE_URL=sqlite:////tmp/gaia-integration-b4.db \
  .venv/bin/python -m coverage run --branch \
  --source=app/modules/network/router/helpers -m pytest -q \
  tests/test_network_router_helpers.py tests/test_network_traffic_campaign.py \
  -o cache_dir=/tmp/gaia-integration-b4-cache
COVERAGE_FILE=/tmp/gaia-integration-b4.coverage .venv/bin/python -m coverage json \
  --include='*/traffic.py' -o /tmp/gaia-integration-b4-coverage.json
COVERAGE_FILE=/tmp/gaia-integration-b4.coverage .venv/bin/python -m coverage report \
  --include='*/traffic.py' --fail-under=100
APP_ENV=test DATABASE_URL=sqlite:////tmp/gaia-integration-b4-api.db \
  .venv/bin/python -m pytest -q tests/test_network_api.py \
  -o cache_dir=/tmp/gaia-integration-b4-api-cache
```

Nessuna suite globale è duplicata dall'Integration Agent; i rispettivi esiti
sono di responsabilità del verifier. B5 rimane isolata, non viene cherry-picked
prima della review e dei suoi gate completi.
