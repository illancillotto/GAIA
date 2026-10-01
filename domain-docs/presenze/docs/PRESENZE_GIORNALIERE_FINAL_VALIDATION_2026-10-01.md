# Presenze giornaliere — verifica finale

Stato corrente: riesame della sezione 11 su `65f69cd5`. Le sezioni 1–10
conservano le evidenze storiche e non rappresentano il risultato attuale.

Data: 2026-10-01. Checkout di riferimento: `main@6b61fd27d325459866259c4b7cba133e661ea38f`.

## 1. Scope e implementazione

Il ciclo caratterizza il comportamento esistente di
`frontend/src/app/presenze/giornaliere/page.tsx`: nessuna nuova funzionalita,
modifica runtime, dipendenza, configurazione coverage, API, migration o schema DB.
Il vincolo confermato dall'utente e **solo test**. Le modifiche concorrenti del
working tree non fanno parte della verifica di questa change.

La suite `frontend/tests/unit/presenze-giornaliere-page.test.tsx` passa da 14 a
182 casi nella prima verifica e a 186 nel riesame dei residui, conservando il
mock preesistente di `WhatsAppReminderAlert`.
La verifica finale corregge il nome di una prova con timbratura di entrata senza
orario e rende deterministico il mese della fixture nei due E2E gerarchici,
in `frontend/tests/e2e/presenze-hierarchy.spec.ts`: agosto 2026 viene selezionato
esplicitamente, anziche dipendere dal mese corrente.

## 2. Matrice comportamento → test

I nomi seguenti identificano prove della suite unitaria; i casi parametrizzati
verificano varianti di dati e failure reali, non alterazioni artificiali del runtime.

| Funzionalita caratterizzata | Comportamento atteso | Test pertinente |
| --- | --- | --- |
| Periodo operativo | Limiti API reali del mese, incluso cambio anno | `changes months across year boundaries and requests their actual date bounds` |
| Filtri operativi | KM, trasferte, straordinari e reperibilita sui totali mensili; toggle reversibile | `toggles %s using monthly operational totals (%j)` |
| Intersezione filtri | Combinazione AND; nessun risultato non azzera i totali mensili | `intersects operational filters and keeps month totals when no collaborators match` |
| Ricerca | Nome, matricola e azienda; trim e case-insensitivity; reset | `searches names, employee codes and company labels: %s`; `clears the collaborator search with the inline X button` |
| Profili e orari | Toggle profili, ripristino esplicito, orario dominante, pareggi e codici vuoti | `toggles profile filters and restores all profiles explicitly`; `uses the dominant monthly schedule and combines schedule, profile and search`; `uses raw schedules, ignores whitespace schedule codes and keeps the first tied schedule` |
| Focus giornaliero | Anomalie/richieste selezionabili e rimovibili; filtro fail-closed dopo validazione | `toggles and removes the daily %s focus`; `keeps an active daily anomaly filter fail-closed when validation clears the last anomaly` |
| Riepiloghi | Somma ordinario, extra, KM, trasferte, assenze su piu giorni; sabati ordinati per data e causale | `aggregates monthly ordinary, extra, km, travel and absences across multiple days`; `sorts monthly Saturdays chronologically and retains each absence cause` |
| Mese vuoto e dati incompleti | Totali zero, opzioni assenti, causali ignote e metriche null senza crash | `renders an empty month with zero summaries and no profile or schedule options`; `displays absent metrics, null absence causes and fallback raw overtime safely`; `uses unknown absence causes in both matrix and collaborator summaries` |
| Classificazione e anomalie | Priorita di ferie, malattia, permessi, richieste, festivi e severita; pannello vuoto | `renders the matrix classification for %j`; `filters and groups blocking and analysis cases without changing the matrix`; `shows an empty anomaly panel when the month has no critical days` |
| Dettaglio e timbrature | Apertura/chiusura modali, navigazione senza interferire con input, ordine e metadata timbrature | `navigates adjacent days with buttons and keyboard, preserving input editing`; `returns to the collaborator modal after closing a selected day`; `uses detail punches when no paired punch exists and includes anomaly metadata`; `renders a single detail entry punch with missing time and no paired authorization fallback` |
| Sessione e permessi | Nessun caricamento senza token; token scaduto blocca tutte le scritture; supervisor valida ma non modifica extra | `does not load data without an access token`; `does not submit %s after the access token expires`; `renders the monthly matrix, opens the day modal and lets a supervisor validate only` |
| Scritture e validazione | Payload KM/reperibilita/rettifiche coerenti, aggiornamento UI, note vuote null, rimozione validazione | `edits KM directly in the matrix and exits KM mode`; `toggles reperibilita in the collaborator list and restores it`; `allows users with full access to save operational overrides`; `removes validation and records an empty validation note as null` |
| Input e profilo contrattuale | Rifiuto gruppo operaio vuoto; salvataggio profilo admin; valori non validi non inviati | `requires an operaio group and saves an unset contract with empty minutes`; `allows admins to change the collaborator contract profile from the modal`; casi parametrizzati di validazione input nella suite |
| Failure API | Errori leggibili sia per Error sia per rejection non-Error: sessione, matrice, dettaglio, KM, reperibilita, editor, validazione, profilo, polling | `shows session load failures (%s)`; `shows monthly matrix failures (%s)`; `shows detail load failures (%s)`; `reports failures when saving inline KM (%s)`; `reports reperibilita save failures (%s)`; `reports editor save failures (%s)`; `reports validation failures (%s)`; `reports contract profile save failures (%s)`; `reports INAZ polling failures (%s)` |
| Refresh INAZ | Accodamento, polling running/completed/failed, conflitto job, annullamento e record sostituito | `continues polling a running INAZ job and applies its completed daily record`; `cancels an in-flight INAZ poll when the day modal closes`; `explains when targeted INAZ refresh is blocked by another sync job`; `replaces an imported record with a new id using collaborator and date identity` |
| Paginazione, rendering e race | Fine su pagina vuota, espansione idle/timeout, callback cancellate, reload concorrenti StrictMode | `loads all matrix pages and stops on an empty page even if the reported total is larger`; `renders large matrices progressively using %s callbacks`; `ignores a cancelled progressive-render callback after unmount`; `closes stale collaborator details when a concurrent session load removes that collaborator`; `closes an editor whose record was replaced during an in-flight detail request` |
| Permessi nel browser | Read-only senza approve; dirigente con validazione ma senza extra editabili | E2E `capo reparto read-only vede solo il subordinato senza azioni approve`; `dirigente con approve vede il subordinato e le azioni di validazione` |
| Rendering gia completato | Un salvataggio KM ricalcola le righe senza perdere collaboratori, duplicare espansioni o rischedulare inutilmente | `preserves a fully expanded matrix when saving KM recalculates its rows` |
| Autorizzazione senza timbrature | Etichetta entrata/uscita autorizzata presente, nessuna riga/orario inventato | `shows an authorized %s punch without inventing missing INAZ rows` (E/U) |
| Risposta mensile concorrente | Una risposta di un mese precedente chiude il dettaglio; l'input KM ancora montato non conserva o invia modifiche obsolete | `does not retain KM edits when an earlier month response closes the selected day` |

## 3. Coverage reale

Misurazione V8 dell'intera pagina, **senza l'esclusione file-wide preesistente**:

| Metrica | Coperti / totali | Coverage |
| --- | --- | --- |
| Statement | 1181 / 1185 | 99,66% |
| Branch | 1379 / 1417 | 97,31% |
| Funzioni | 306 / 306 | 100% |
| Linee | 979 / 979 | 100% |

Il gate con tutte e quattro le soglie a 100 esce **1**. Nessun runtime e nuovo
o modificato nel ciclo; cio non equivale al raggiungimento dell'obiettivo
full-file richiesto per questa pagina.
Misura aggiornata su 186 test; la precedente era statement 1180/1185 e branch
1376/1417. Denominatori identici: nessuna esclusione o riduzione del perimetro.

Metodo: copia temporanea del sorgente, alias esatto dell'import della pagina e
config che estende il Vitest reale. La copia differisce esclusivamente per la
rimozione dei due commenti V8 e dello spazio finale associato; le posizioni del
codice eseguibile restano identiche. Confronto sorgente/copia verificato dopo il
run. Nessuna esclusione di branch, riduzione soglie o mock di primitive per
fabbricare percorsi irraggiungibili. La configurazione versionata non cambia.

Comando eseguito da `frontend/` (config temporanea conservata nelle evidenze):

```bash
./node_modules/.bin/vitest run tests/unit/presenze-giornaliere-page.test.tsx \
  --config /tmp/gaia-presenze-coverage-PUNSFa/vitest.config.ts \
  --coverage --coverage.reportsDirectory=/tmp/gaia-presenze-residual-audit/coverage \
  --coverage.thresholds.statements=100 --coverage.thresholds.branches=100 \
  --coverage.thresholds.functions=100 --coverage.thresholds.lines=100
```

Statement scoperti in `frontend/src/app/presenze/giornaliere/page.tsx`:

| Linea | Motivo / valutazione |
| --- | --- |
| 158 | `formatDayFocusLabel(null)` non chiamata: il JSX richiede focus truthy. Non manca una normale interazione UI. |
| 1163 | Guardia `!totals`: gli ID visibili provengono dallo stesso ciclo che crea i totali. Nessun dato API valido permette il percorso. |
| 1451 | Ref scroll nullo in handler di drag del nodo montato; non esercitato da interazioni normali. Nessun test artificiale aggiunto. |
| 1550 | No-op reperibilita irraggiungibile dall'unico chiamante: `none` diventa `days`, ogni altra unita diventa `none`. |

I 38 esiti branch scoperti ricadono nelle linee seguenti (il JSON riporta le
singole locations, anche quando piu esiti condividono una linea):

- Guardie, parsing, fallback dati: 158, 164, 247, 274, 365, 412, 435, 443,
  506, 507, 668, 1163, 1451, 1550, 1629.
- Totali e modali: 2256, 2931, 2973, 2977, 2981, 2985.
- Updater con stato editor gia nullo: 2620, 2635, 2656, 2667, 2862, 2879,
  2883, 2891, 3042, 3066, 3091.
- Fallback colore della legenda: 3147.

Ulteriori impedimenti dimostrabili: a 1623 una guardia rifiuta il gruppo operaio
vuoto prima del fallback `operaiGroup || null` a 1629; a 412 il confronto
`"DOM"` non corrisponde alle etichette weekday minuscole costruite dalla pagina.
Gli altri fallback difensivi non sono tutti dimostrati irraggiungibili: possono
richiedere ulteriori test pertinenti o una successiva revisione runtime
autorizzata. Il vincolo test-only impedisce la pulizia dei rami dimostrati morti;
non si dichiara 100% e non si considera completato l'obiettivo integrale.

Riesame contratti: `frontend/src/types/api/presenze-base.ts` e
`backend/app/modules/presenze/schemas.py` definiscono minuti mancanti e MPE
operativi come numeri non-null e `detail_punch_rows` come lista non-null.
Per questo i fallback a 247, 443, 506, 507 e 668 non vengono esercitati con
payload inventati fuori contratto. A 435 il ramo absence richiede gia
`absence_minutes > 0`; a 365 il chiamante richiede un codice orario ottenuto
da schedule/programmed schedule prima di leggere l'etichetta, escludendo il
fallback con entrambi null. Il fallback colore a 3147 non serve con la mappa
costante attuale, che assegna un token `bg-` a ogni CellKind.
Gli updater null restano non coperti; la race mensile reale aggiunta verifica
la chiusura senza scritture ma non dimostra l'esecuzione di questi esiti.

## 4. Regression gate e code quality

Evidenze della prima verifica: `/tmp/gaia-presenze-final-audit-AHZlEA/`.
I risultati globali rossi della tabella sono superati dal follow-up della sezione 7.

| Controllo eseguito | Risultato |
| --- | --- |
| Suite pagina finale | 182 / 182 passati (`scoped-final.log`) |
| Pagina con coverage e soglie 100 | 182 / 182 passati; gate coverage fallito (`coverage.log`) |
| Tutte le suite frontend, `npm run test:unit -- --maxWorkers=2` | 2861 passati, 1 fallito; 243 file passati, 1 fallito (`unit.log`) |
| `cd frontend && npm test` | 12 passati, 6 falliti (`smoke.log`) |
| `npm run lint` | Exit 0, warning legacy (`lint.log`) |
| ESLint entrambi i test modificati | Exit 0, senza warning (`scoped-lint-final.log`) |
| `npm run typecheck` | Exit 0, ripetuto sul diff finale (`typecheck-final.log`) |
| `npm run build:clean` | Exit 0, build produzione Next 15.5.25 (`build.log`) |
| E2E gerarchici Chromium sul build locale | 2 / 2 passati dopo selezione esplicita del mese (`e2e-final.log`) |
| Ratchet `--base-ref origin/main` sulla pagina | Nessun finding; baseline del merge-base, nessuna baseline riscritta (`ratchet.log`) |

Il build pulito e eseguito in una copia temporanea del frontend con dipendenze
locali condivise: non elimina `.next` del checkout e non ferma servizi Docker.
Gli E2E usano il server di produzione isolato su porta 3107 e API mockate;
il backend reale, la persistenza PostgreSQL, INAZ e i provider WhatsApp non sono
verificati da queste prove. Suite backend/worker e integrazioni live non sono
applicabili a un diff esclusivamente test frontend/documentazione.

Failure globali non corrette fuori scope:

- `ruolo-tributi-placeholder-pages.test.tsx`, `renders reminders placeholder`:
  `SollecitiAccess` chiama `useRouter` senza App Router montato.
- Quattro smoke falliscono con ENOENT per `frontend/src/lib/api.ts`, assente
  anche nel commit HEAD; il client attuale e una directory. Altri due hanno
  assertion obsolete sulla dashboard Elaborazioni e sulla copy del template
  Catasto. I test smoke e le sorgenti interessate non avevano diff nella prima
  verifica; la diagnosi dettagliata e stata consolidata nel follow-up test-only.
- Gli E2E iniziali fallivano aspettando la cella 2026-08-16 mentre era aperto
  ottobre. Correzione solo test; nessuna modifica del runtime.

Le failure Ruolo e smoke sono riprodotte anche su una copia `git archive HEAD`
del frontend: stesso errore App Router e stesse sei failure smoke (`head-ruolo.log`,
`head-smoke.log`). Dipendenze locali condivise, nessun test modificato nella
copia di controllo. Non sono regressioni introdotte dalla caratterizzazione.

Nessuna nuova failure osservata nella suite Presenze. Non si estende questa
conclusione a regressioni backend o all'intero working tree concorrente.

Metriche runtime invariate prima/dopo: componente principale cognitiva 573,
ciclomatica 478, LOC 2284, nesting 3; file LOC 3016, 308 callable, 9 import,
21 useState e 13 useEffect. Snapshot: 59 violation legacy (26 error, 33 warning).
Nessun miglioramento di complessita dichiarato, refactoring o debt transfer.
Il lint segnala nella pagina `isLoadingRecordDetail` inutilizzato e dependency
array legacy incompleti: conservati nel rispetto del vincolo runtime.

Revisione manuale: helper fixture condivisi, nessun servizio duplicato o nuova
responsabilita runtime; test di payload, errori, cancellazione e token scaduto.
Nessun nuovo logging, segreto, dipendenza o superficie di sicurezza. La
type-safety passa tsc, ma il cast della fixture `matrixRecord` resta un limite
dei test, non una prova di validita dei payload restituiti dal backend.
Non eseguito uno scanner dedicato di duplicazioni o un audit di sicurezza live.

## 5. Architettura e documentazione

La pagina rimane nel dominio `frontend/src/app/presenze/`; il backend di dominio
rimane `backend/app/modules/presenze/`. Sono caratterizzati i confini esistenti:
sessione/access-context, collaboratori, matrix/detail, update record/profilo e
job INAZ. Nessun nuovo router, modello, servizio, mapping identita, tabella,
transazione o architettura parallela. I test verificano payload e consistenza
dello stato UI, non la persistenza DB o l'enforcement dei permessi server.

Aggiornati questo report, `PROGRESS_PRESENZE.md`, il piano operativo
`IMPLEMENTATION_PRESENZE_COLLABORATORI_GIORNALIERE.md` e
`docs/TEST_COVERAGE_100_PLAN.md`. PRD, README, API e architettura non richiedono
nuovi contratti: nessun comportamento prodotto e cambiato. Il piano storico
non viene riscritto come se tutte le sue attivita fossero completate.

## 6. Graphify e working tree

`make graphify-frontend` eseguito: nessun cambio di topologia runtime.
`make graphify-presenze-docs` e `make graphify-platform-docs` completati con
`gpt-reserve`: verificati `chunk 1/1 done`, assenza di semantic chunk failed
ed exit 0 in entrambi i log. Primo refresh: Presenze 817 nodi / 1543 edge,
piattaforma 2215 nodi / 5060 edge; costo stimato complessivo $0,0208.
La documentazione Presenze viene risincronizzata dopo il consolidamento del
report. Nessun grafo generato entra nel diff versionato; nessun simbolo runtime
rimosso che richieda pruning forzato.

File della prima verifica: i due test frontend e i quattro documenti sopra
elencati; il follow-up aggiunge i due file di test elencati nella sezione 7.
Modifiche concorrenti Makefile, Wiki/MCP, GATE/Presenze backend, Ruolo,
Elaborazioni e programma code-quality preservate, non validate come parte di
questa change, incluse ulteriori modifiche MCP apparse durante i controlli.
Log, coverage, build ed E2E artifacts rimangono in `/tmp`; server E2E isolato
arrestato dopo la verifica.
nessun commit, deploy o grafo generato aggiunto al diff del ciclo.

## 7. Follow-up autorizzato — ripristino gate frontend

L'utente ha autorizzato il primo passo della proposta successiva: correggere
i test globali obsoleti, mantenendo il vincolo solo test. Nessuna modifica a
runtime, API, database, dipendenze, configurazioni, soglie o esclusioni.

| Test modificato | Comportamento verificato dopo il riallineamento |
| --- | --- |
| `frontend/tests/smoke.test.mjs` | Base same-origin in `api/core.ts`; riepilogo/download/delete-password Utenze in `api/utenze.ts`; creazione richiesta in `api/elaborazioni-jobs.ts`. |
| Smoke Catasto/Elaborazioni | Dashboard collegata a registro servizi e hook; route Capacitas/AdE e loader GATE nei moduli proprietari; componenti GIS montati e callback refresh cache collegata; etichette e progress nel pannello AdE. |
| Smoke template Catasto | Colonne CF/P.IVA e alias identificati dal parser, distinzione fiscale/catastale, requisiti minimi catastali ed export ancora verificati. |
| `frontend/tests/unit/ruolo-tributi-placeholder-pages.test.tsx` | Sostituita l'aspettativa del placeholder rimosso con registro solleciti vuoto per operatore read-only: chiamata API con token/pagina/limite, pager disabilitato e nessuna conferma esposta. Bootstrap sessione mockato al confine; componente reale renderizzato. |

Nessuna assertion rimossa per rendere verde un comportamento scorretto: i
controlli sono trasferiti alle responsabilita estratte e al comportamento
attualmente implementato. Le altre tre prove di import pagamenti restano
intatte. Le suite solleciti gia esistenti continuano a verificare accesso,
conferma ed error handling; non viene duplicato quel perimetro.

Evidenze follow-up: `/tmp/gaia-frontend-gates-followup/`.

| Comando | Esito |
| --- | --- |
| `npm test` | 18/18 passati, nessuno skipped |
| `vitest run tests/unit/ruolo-tributi-placeholder-pages.test.tsx tests/unit/notice-solleciti-page.test.tsx` | 27/27 passati |
| `npm run test:unit -- --maxWorkers=2` | 244/244 file, 2862/2862 test passati |
| ESLint sui due test modificati | Exit 0, nessun warning |
| `npm run typecheck` | Exit 0 |
| `npm run lint` | Exit 0, warning legacy invariati |
| `npm run build:clean` | Exit 0, ripetuto nella copia isolata con i test aggiornati |

La suite globale contiene anche i 182 test Presenze. Rimangono messaggi jsdom
legacy `Not implemented: navigation to another Document`, senza failure;
nessuno viene soppresso. Gli E2E Presenze restano i due passati nella prima
verifica, non rieseguiti in questo follow-up: nessun runtime o E2E modificato.
Il build inizialmente invocato dalla directory temporanea padre non trovava
`package.json`; ripetuto dalla directory frontend corretta, e passato.

La coverage Presenze della sezione 3 e la misura precedente: non viene
rimisurata o presentata come nuova nel ripristino dei gate. Il codice runtime
versionato della pagina e invariato. Il riesame dei percorsi ancora copribili
e una tranche successiva, non avviata automaticamente insieme ai fix globali.

## 8. Riesame residui test-only

Secondo passo autorizzato completato nel perimetro test-only. Aggiunti quattro
casi pertinenti: espansione completa dopo salvataggio KM, autorizzazione senza
timbrature per entrata e uscita, risposta di un mese precedente concorrente
con l'editor KM. Quest'ultima prova controlla che l'input sia ancora connesso al
DOM prima dell'evento, senza invocare handler su nodi staccati; usa sempre un
mese diverso dal mese iniziale, senza dipendere dal calendario della macchina.

- Pagina originale: 186/186 passati; stessa suite sulla copia misurata: 186/186.
- Coverage aggiornata: statement 1181/1185 (99,66%), branch 1379/1417 (97,31%),
  funzioni 306/306 e linee 979/979 (100%). Gate 100 exit 1, denominatori invariati.
- Suite globale: 244 file e 2866 test tutti passati; smoke 18/18 passati.
- ESLint mirato e TypeScript: exit 0. Runtime e metriche di complessita invariati;
  nessuna baseline, dipendenza, soglia o esclusione modificata.
- Build pulito, lint globale ed E2E: ultime verifiche passate nelle tranche
  precedenti, non rieseguite nel riesame dei quattro test. Nessun runtime o
  E2E modificato; non sono dichiarate nuove esecuzioni di quei controlli.

Evidenze: `/tmp/gaia-presenze-residual-audit/`, inclusi `page-final.log`,
`coverage.log`, `coverage/coverage-final.json`, `unit-final.log`, `smoke.log`,
`lint.log` e `typecheck.log`. La guardia a 1210 e i due branch a 2797/2820 sono
ora coperti. I quattro statement residui sono 158, 1163, 1451 e 1550.
La race KM e utile per il comportamento osservabile, ma non copre l'updater
null a 2620: non viene ampliata artificialmente per forzarne l'esecuzione.

### Difetto rilevato: mese cancellato

Il selettore month accetta il valore vuoto. Un test esplorativo che cancella
il mese dopo il caricamento riproduce `RangeError: Invalid time value` da
`formatMonthLabel` (`page.tsx:150`, chiamata nel JSX a 1673). Il render fallisce
prima di poter mostrare il normale errore API: non e corretto considerare
questo percorso un happy path o i fallback mensili a 274 sicuramente morti.

Il runtime e invariato. La prova negativa non e inclusa tra i 186 test verdi:
e conservata in `month-empty.log` e nel riproduttore
`REPRO_EMPTY_MONTH.patch` (applicabile a una copia isolata). I run esplorativi
rosso con 187 casi, incluso il primo globale, restano nei log; il run finale
verde verifica il diff test-only consolidato. Nessun `skip`, `test.fails`,
soppressione errori o esclusione coverage aggiunti. Il difetto resta aperto e
contribuisce al FAIL; correggerlo richiede una decisione esplicita sul runtime.

Graphify codice frontend invariato; corpus docs Presenze e piattaforma
risincronizzati tramite i target dedicati. Log del refresh in questa directory.

## 9. Stato storico prima dell'autorizzazione runtime

- Completati: caratterizzazione, misura reale, test pagina, E2E pertinenti,
  type-check, lint, build pulito e ratchet mirato.
- Residui: 4 statement e 38 esiti branch scoperti; obiettivo full-file 100%
  non raggiunto. Esclusione V8 preesistente ancora nel runtime, non usata nella misura.
- Gate globali frontend ripristinati dal follow-up autorizzato: unit e smoke
  tutti verdi. Nessuna estensione a fix runtime o al working tree concorrente.
- Debito: monolite UI complesso, guardie/fallback morti o non dimostrati
  raggiungibili, warning hook legacy e copertura end-to-end reale non provata.
  Difetto runtime riprodotto cancellando il mese, non corretto nel vincolo corrente.
- Il vincolo solo test resta attivo; eventuale pulizia runtime richiede una
  decisione distinta. Il ciclo non autorizza refactoring o nuove feature.

## 10. Risoluzione runtime autorizzata

La richiesta successiva **risolvi 1 e 2** autorizza a correggere coverage e
mese vuoto, supersedendo il vincolo solo test per questo perimetro. Checkout
di verifica `dc66972813970573ec5d1dd8d0b3426fa6c56116`, distinto dal riferimento
iniziale. All'avvio della chiusura il working tree conteneva gia correzione,
pulizia runtime e ulteriori feature Presenze concorrenti. Non vengono rimossi
o attribuiti a questa tranche i nuovi controlli INAZ/buoni pasto, backend,
schema e migration, pagina individuale o modifiche Wiki/MCP.

### Correzione e invarianti

- Il selettore mantiene un mese valido: cancellare l'input non aggiorna
  `selectedMonth`, non chiude il dettaglio e non lancia query con date invalide.
  Un successivo mese valido funziona e carica i limiti corretti.
- La pulizia presente nel runtime elimina guardie dimostrate ridondanti,
  fallback incompatibili con i contratti non-null e il confronto weekday
  mai corrispondente. Totali garantiti dal ciclo di aggregazione e gruppi operai
  validati restano invarianti; autorizzazioni, salvataggi e calcoli non cambiano.
- Il drag usa il nodo dell'evento montato, senza guardia ref nulla non
  esercitabile. `patchPresenzeEditor` preserva uno stato gia chiuso ed evita
  duplicazione degli updater; prove dedicate verificano merge immutabile e
  no-op su null. Non vengono forzate race su nodi DOM staccati.
- Rimossa l'esclusione V8 file-wide della pagina. Nessun ignore nuovo, mock di
  primitive, trasformazione sorgente per coverage o soglia ridotta.

Matrice delle nuove verifiche:

| Comportamento | Test |
| --- | --- |
| Mese cancellato conserva mese/dettaglio/query; successivo mese valido carica giugno | `preserves the operative month and the open day when the month input is cleared` |
| Cancellazione reale nel browser conserva agosto e permette apertura giornata | Entrambi gli E2E di `presenze-hierarchy.spec.ts`, assertion dopo `fill("")` |
| Editor aperto aggiorna solo i campi richiesti senza mutare lo stato precedente | `merges an input change without mutating the other pending edits` |
| Input precedente non riapre un editor gia chiuso | `keeps a dismissed editor closed when a previous input event arrives` |
| Race, filtri, riepiloghi, permessi, errori e polling conservati | Suite pagina originale e matrice di sezione 2, mantenute |

### Misura reale finale

| File | Statement | Branch | Funzioni |
| --- | --- | --- | --- |
| `frontend/src/app/presenze/giornaliere/page.tsx` | 1188/1188 | 1351/1351 | 309/309 |
| `frontend/src/lib/presenze-editor-state.ts` | 1/1 | 2/2 | 1/1 |
| Totale | 1189/1189 | 1353/1353 | 310/310 |

Line coverage totale **979/979**, tutte le metriche **100%**, gate exit **0**.
191/191 test mirati: 189 pagina e 2 helper. Misura sul sorgente reale del
checkout; il JSON conferma entrambi i percorsi e ogni contatore coperto.
Il denominatore runtime e cambiato per pulizia e sviluppi concorrenti: i
conteggi della tranche test-only restano evidenza storica, non il gate attuale.

```bash
cd frontend
VITEST_COVERAGE_INCLUDE=src/app/presenze/giornaliere/page.tsx,src/lib/presenze-editor-state.ts \
  ./node_modules/.bin/vitest run tests/unit/presenze-giornaliere-page.test.tsx \
  tests/unit/presenze-editor-state.test.ts --coverage \
  --coverage.reportsDirectory=/tmp/gaia-presenze-close/coverage
```

`VITEST_COVERAGE_INCLUDE` usa il gate esistente: tutte le soglie a 100; nessun
file runtime del perimetro pagina/editor escluso. I componenti concorrenti
hanno suite proprie, non sono inclusi come se fossero stati integralmente
validati da questa chiusura.

### Controlli, working tree e limite del gate

Evidenze in `/tmp/gaia-presenze-close/`. Coverage diretta, 18/18 smoke,
type-check, ESLint mirato/globale, build clean isolato e due E2E Chromium
passati. Restano tre warning legacy della pagina: stato dettaglio inutilizzato
e dependency array degli effect. Nessun warning soppresso. Build nella copia
temporanea evita di eliminare `.next` o fermare servizi del checkout.

Il primo run globale passa 3058 test ma fallisce per un describe vuoto nel
file concorrente `presenze-giornaliere-regressions.test.tsx`. Eliminato solo
il contenitore vuoto, senza rimuovere uno dei 172 test o relative assertion;
repeat finale **248/248 file e 3058/3058 test passati**, exit 0 in
`unit-final.log`. La duplicazione preesistente delle
prove in quel file resta fuori scope: non viene riscritta o rimossa.

Metriche snapshot pagina: componente principale cognitiva **550**, ciclomatica
**457**, LOC **2279**, rispetto al precedente runtime 573/478/2284. Nel corso
di questa chiusura non cambiano le metriche iniziali del working tree (550/457);
non si attribuisce il delta misto a un refactoring appena eseguito. Snapshot
pagina/helper: 55 violation legacy (26 error, 29 warning).

Il ratchet autorevole `--base-ref origin/main` resta **exit 1**: sette finding
su matching `Program<anonymous>` (ciclomatica, cognitiva, nesting, LOC e
parametri) e LOC di `setEditor[0]<callback>`. Anche la diagnosi rispetto a HEAD
segnala debito della pagina mista, incluso `useState` da 21 a 22 introdotto
dal refresh INAZ concorrente. Non si riscrive la baseline per assorbire i
finding o si modifica lo scanner fuori scope. La risoluzione/ownership del
matching e degli sviluppi concorrenti richiede una change separata.

Graphify frontend aggiornato con target dedicato: 7169 nodi e 17255 edge;
HTML non rigenerato per limite 5000 nodi, JSON/report aggiornati. Corpus docs
Presenze e piattaforma aggiornati via target dedicati; verificare i chunk nei
log, non solo exit 0: entrambi exit 0, `chunk 1/1 done`, nessun semantic chunk
failed. Primo refresh finale: 878 nodi / 1655 edge Presenze, 2232 nodi / 5092
edge piattaforma, costo stimato complessivo $0,0199. Il report viene
risincronizzato dopo i conteggi finali della suite. Nessun artefatto generato
incluso nel diff versionato. Server E2E isolato arrestato; confronto diff della
pagina prima/dopo il consolidamento identico, modifiche concorrenti preservate.

**Problema 1 risolto: coverage 100% reale. Problema 2 risolto: nessun crash
cancellando il mese.** Il gate complessivo non puo diventare PASS mentre il
ratchet del working tree misto resta rosso; nessuna attestazione globale sul
backend concorrente, database o integrazioni live viene ricavata dai test UI.

Esito storico sezione 10: FINAL QUALITY GATE — FAIL.

## 11. Riesame sul checkout corrente — 2026-10-01

Riferimento: `65f69cd52be73143b3a67efb5450dae3de4ef5c5`. Il checkout e avanzato
rispetto alla sezione 10. Tutti i controlli seguenti sono rieseguiti sul sorgente
attuale; evidenze in `/tmp/gaia-presenze-recheck/`.

### Scope, matrice e architettura

Verificato il ciclo frontend di filtri/riepiloghi giornalieri, caratterizzazione,
coverage reale e regressione del mese vuoto: pagina `presenze/giornaliere` e
helper editor. Nessuna nuova feature, dipendenza, API, migration o modifica
runtime in questo riesame. Matrice completa nella sezione 2, integrata dai casi
della sezione 10; tutti i test citati rimangono nella suite.

| Verifica | Comportamento atteso | Test/esito attuale |
| --- | --- | --- |
| Filtri e riepiloghi | AND dei filtri, totali mensili conservati, mesi vuoti e confini anno | Suite pagina: 189 test passati |
| Mese cancellato | Mantiene mese valido, dettaglio e query; cambio valido ancora operativo | Regressione unitaria dedicata e 2 E2E gerarchici passati |
| Editor | Update immutabile, editor chiuso non riaperto da eventi tardivi | 2 test helper passati |
| Errori e permessi | Scritture fail-closed, rejection gestite, read-only e approve distinti | Suite pagina e 2 E2E gerarchici passati |
| Integrazione controlli UI | Buono persistente dopo refresh, sync INAZ aggiorna anomalie senza doppio conteggio | E2E operational-controls passato |
| Regressioni frontend | Suite precedenti, smoke e compilazione restano validi | 3058 unit, 18 smoke, type-check, lint, build passati |

La pagina resta nel dominio `frontend/src/app/presenze/`; helper condiviso in
`frontend/src/lib/`, senza servizi duplicati o architettura parallela. Non si
modificano backend di dominio, database o autorizzazioni server. Gli E2E usano
API simulate: verificano flussi UI e reload, non persistenza PostgreSQL o sync
live INAZ/GATE. Tali controlli live non sono gate di questo ciclo frontend e
non si dichiarano eseguiti. Gli sviluppi backend/Wiki/GATE concorrenti rimangono
fuori dall'attestazione di questa tranche.

### Coverage e regression gate

Misura V8 diretta con lo stesso comando della sezione 10, report directory
`/tmp/gaia-presenze-recheck/coverage`. Include esplicito dei due runtime,
soglie esistenti tutte a 100, nessun ignore V8/Istanbul nei file misurati.

| File | Statement | Branch | Funzioni |
| --- | --- | --- | --- |
| `frontend/src/app/presenze/giornaliere/page.tsx` | 1186/1186 | 1351/1351 | 308/308 |
| `frontend/src/lib/presenze-editor-state.ts` | 1/1 | 2/2 | 1/1 |
| Totale | 1187/1187 | 1353/1353 | 309/309 |

Line coverage **978/978**. Tutte le metriche **100%**, nessuna linea o branch
residuo nel perimetro. I denominatori aggiornati sostituiscono quelli della
sezione 10; non derivano da nuove esclusioni. 191/191 test mirati passati.

| Comando | Risultato |
| --- | --- |
| `npm run test:unit -- --maxWorkers=2` | 248 file, 3058 test passati, exit 0 |
| `npm test` | 18 smoke passati, exit 0 |
| `npm run typecheck` | exit 0 |
| `npm run lint` | exit 0; warning legacy preservati |
| `npm run build:clean` | exit 0 nella copia isolata del frontend corrente |
| Playwright hierarchy + operational-controls, Chromium | 3/3 passati, exit 0 |
| `make quality-test` | 83/83 test tooling passati, exit 0 |
| Ratchet pagina/helper `--base-ref origin/main` | exit 0, `findings: []`; merge-base `6b61fd27d325459866259c4b7cba133e661ea38f` |
| `git diff --check` | exit 0 |

Build/E2E eseguiti in `/tmp/gaia-presenze-recheck/frontend`, dipendenze locali
riusate, output browser fuori dal repository. Nessuna pulizia della `.next`
del checkout e nessun servizio esistente interrotto.

### Quality, documentazione e debito residuo

Ratchet read-only superato contro il merge-base autorevole: nessuna baseline,
eccezione, soglia o scanner modificati in questo riesame. Metriche attuali
del componente principale: cognitiva **550**, ciclomatica **457**, LOC **2275**;
file pagina LOC **3009**, 21 `useState`, 13 `useEffect`, 12 import.
Helper: cognitiva 1, ciclomatica 2, LOC 3, nessuna violation. Restano 55
violation legacy nel perimetro (26 error, 29 warning), tollerate dal ratchet,
non presentate come debito eliminato. Il precedente stato aggiuntivo e i finding
callback della sezione 10 non bloccano piu il sorgente attuale.

Tre warning legacy della pagina restano visibili: stato dettaglio inutilizzato
e due dependency array. Lint/build non contengono errori collegati alla tranche;
le notifiche jsdom di navigazione non implementata e il warning Playwright
`NO_COLOR`/`FORCE_COLOR` non causano failure. Nessun nuovo logging, trattamento
di credenziali, coupling o duplicazione runtime introdotto dal riesame.
La duplicazione preesistente dei test di regressione e la complessita della
pagina restano debito separato: nessun refactoring fuori scope.

Aggiornati report, PROGRESS, piano implementazione e stato coverage piattaforma.
PRD, README, contratti API e note architetturali non richiedono modifiche:
nessuna nuova funzionalita o interfaccia introdotta. Graphify frontend verificato
con target dedicato, exit 0, nessun cambio di topologia. Corpus docs Presenze e
piattaforma aggiornati tramite target dedicati, con verifica dei chunk semantici.

Working tree misto preservato: modifiche backend/Wiki/GATE e documentazione di
altri domini non incluse nella tranche. Runtime pagina/helper identico a HEAD;
nessun commit, deploy, baseline rewrite o artefatto temporaneo aggiunto al
repository da questo riesame. Il gate attesta il perimetro frontend descritto,
non il 100% dell'intero repository o la chiusura delle change concorrenti.

FINAL QUALITY GATE — PASS
