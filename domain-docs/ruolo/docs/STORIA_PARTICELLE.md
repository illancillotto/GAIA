# Storia delle particelle

Rilascio CED attivo dal **12 novembre 2026, 18:40:57 CET**, commit applicativo
**`c99669b0`** pubblicato su `chore/split-changes-20261109`. Backend e frontend
healthy; schema e impostazioni degli invii invariati. Il registro Produzione
riporta le verifiche effettivamente concluse.

## Consultazione

`/ruolo/particelle` apre la storia in sola lettura (`vista=storia`). La ricerca
per comune, foglio, particella oppure contribuente/avviso restituisce schede
paginate con prima e ultima annualita disponibile. Cercare un vecchio
contribuente seleziona la particella e conserva tutta la sua storia, anche gli
anni intestati ad altri contribuenti. I filtri restano nell'URL e si conservano
tornando dal dettaglio ai risultati.

Il dettaglio separa due schede, navigabili anche da tastiera:

- **Tributi nel tempo**: righe per annualita, contribuente dell'avviso,
  eventuale CF diverso della partita, cointestazione, componenti del tributo,
  superfici e collegamenti al dettaglio tributo e all'avviso originale.
- **Proprieta catastale**: eventi storici estratti, decorrenza, atto, diritto,
  quota e documento fonte; separatamente gli intestatari rilevati nelle visure.

La consultazione annuale resta in `vista=annuale`, inclusi i vecchi URL con
filtri annuali. Il flusso istruttorio con indice persistente, analisi e pratiche
resta in `vista=all`; non e un prerequisito della nuova consultazione.

## Fonti e limiti probatori

La storia tributaria legge `ruolo_particelle -> ruolo_partite -> ruolo_avvisi`
per tutte le annualita effettivamente importate, senza limite fisso 2011–2025.
Identifica le righe usando comune nome/codice, foglio, particella e subalterno
normalizzati; gli zeri iniziali dei riferimenti numerici sono equivalenti.
La sezione deriva dagli hint gia usati dal parser del comune. Riferimenti
incompleti restano separati per riga, senza inferenze o fusioni automatiche.

Gli importi sono le tre componenti della **singola riga particella**, non il
totale dell'avviso. Il totale e disponibile soltanto se tutte le componenti
sono valorizzate; un valore mancante non diventa zero. Pagamenti e rettifiche
si consultano nel dettaglio tributo: non vengono ripartiti arbitrariamente
dall'avviso alla particella.

La prima presenza non certifica la registrazione originaria; l'ultima non
certifica la cessazione. Gli anni intermedi senza righe sono esplicitamente
non verificabili. Non essendoci una fonte strutturata di cessazione tributaria
in questo flusso, la pagina mostra **Cessazione tributaria: Non documentata**.
Una soppressione catastale documentata e mostrata separatamente e non equivale
alla cessazione del tributo.

## Archivio catastale e SISTER

Si consultano i documenti gia collegati tramite `cat_particella_id` oppure
`ade_scan_document_id`, limitati ai documenti accessibili all'utente secondo
il vincolo esistente `CatastoDocument.user_id`. Non si effettua matching per
somiglianza e non si espongono percorsi filesystem.

Gli eventi di `CatastoSisterHistoryEvent` appartengono all'estrazione, non a
una singola particella. Per estrazioni con zero o piu particelle non si
attribuiscono automaticamente eventi/intestatari o soppressione; la pagina
segnala l'ambiguita e rimanda all'originale. Estrazioni assenti o fallite
restano consultabili come documenti, senza inventare dati.

La catena e sempre **da verificare sui documenti** (`completeness=not_certified`):
gli eventi disponibili non certificano tutti i periodi e non generano date
di fine possesso dedotte. Una visura attuale non prova i proprietari precedenti.
La pagina segnala assenza di visure collegate, mancanza di eventi estratti e
ambiguita. Il collegamento «Apri Catasto e visure SISTER» apre il flusso
esistente per acquisire le visure mancanti; non crea o avvia richieste.
Non e implementato un calcolo automatico dei periodi di titolarita scoperti
o della genealogia fra particelle derivate da fusioni/frazionamenti.

## Contratto API e sicurezza

- `GET /ruolo/particelle/storia`: `comune`, `foglio`, `particella`, `search`,
  `page` (da 1), `page_size` (1–100, default 25). Paginazione e aggregazione SQL.
- `GET /ruolo/particelle/storia/{uuid}`: riferimenti, annualita, righe tributo
  e prove catastali. UUID non valido: 422; riga inesistente: 404.

Entrambe richiedono modulo `ruolo` e sezione `ruolo.avvisi` e restituiscono
`Cache-Control: private, no-store`. Nessuna scrittura, migrazione, ricalcolo
dell'indice o collegamento a servizi esterni. I caratteri wildcard nelle
ricerche testuali sono trattati letteralmente. Il frontend distingue errori
di servizio da risultati vuoti, offre «Riprova» e ignora risposte obsolete.

## Verifiche e rilascio

Il ciclo e verificato localmente su fixture sintetiche; non certifica la
completezza dell'archivio operativo. Test backend in
`backend/tests/ruolo/test_parcel_history.py`, regressioni in
`backend/tests/ruolo/test_parcel_control.py`; frontend in
`frontend/tests/unit/parcel-history*.test.*`, `parcel-control.test.tsx` ed
E2E in `frontend/tests/e2e/parcel-history.spec.ts`.

I test verificano storia completa dopo ricerca per contribuente, paginazione,
identificativi incompleti, importi Decimal/null, permessi e isolamento documenti,
eventi con fonte, estrazioni ambigue/fallite, navigazione e gestione errori.
Il test PostgreSQL richiede un database sintetico isolato chiamato
`parcel_history_test` tramite `PARCEL_HISTORY_TEST_POSTGRES_URL`; verifica le
query effettive senza attestare migrazioni o vincoli di scrittura di altri domini.

La funzionalita richiede il rilascio coordinato di backend e frontend. Un
backend privo della nuova API mostra un messaggio di servizio non aggiornato,
non un falso archivio vuoto. La disponibilita del controllo istruttorio in
produzione resta distinta dalla nuova consultazione storica.

### Esito locale del 12 novembre 2026

- Backend: **79 test PASS**, nuove storie e regressioni controllo incluse;
  PostgreSQL isolato effettivamente eseguito. Coverage dei quattro runtime
  backend toccati: **100% statement/branch** (156 statement, 20 rami).
- Frontend: **31 test PASS** su tre suite; sei runtime eseguibili toccati
  coperti al **100% statement/branch/function/line** (180 statement, 196 rami,
  61 funzioni, 144 righe). I tipi TypeScript sono verificati dal typecheck.
- Browser Chromium: **3 E2E PASS** su build produzione locale, larghezze
  1440 e 390 px e servizio non disponibile con retry. Verifica visiva delle
  schermate tributi/proprieta, nessun overflow orizzontale, errore JavaScript
  o richiesta di scrittura. Le risposte API E2E sono fixture sintetiche.
- Il primo collaudo browser ha rilevato il riuso della risposta elenco durante
  l'apertura del dettaglio: correzione tramite associazione risposta/URL e
  test di regressione elenco → dettaglio → altra particella → elenco.
- Ruff/formatter sui nuovi Python, ratchet stile backend contro `HEAD`,
  ESLint Ruolo/API, typecheck, build e `git diff --check`: PASS. La build
  conserva warning preesistenti di altri moduli.
- Complessita: scansione globale completa, confronto del perimetro della
  feature contro le baseline immutabili dei merge-base `HEAD` (`5f50a349`)
  e `origin/main` (`686e529e`) e contro lo snapshot prima della feature:
  **zero finding**. La navigazione delle viste preesistenti e posseduta da
  `ParcelControlViews`, distinta dall'instradamento del workspace.
  `ParcelControlWorkspace`: Cyc/Cog/LOC 5/4/11 → 4/3/7; nessuna riduzione
  hotspot dichiarata. Totali perimetro prima → dopo: 2 → 11 file,
  26 → 77 callable, Cyc 80 → 260, Cog 59 → 207, LOC file 193 → 723;
  warning 4 → 8 e zero error-level. I quattro warning aggiuntivi riguardano
  `cadastral_history` (Cyc 13, Cog 18), `TaxEntry` (Cyc 10) e
  `useParcelHistory` (Cyc 10), tutti sotto la soglia di errore.
- Il ratchet globale del branch contro `origin/main` conserva **20 finding
  Presenze**, identici allo snapshot precedente alla feature. Non sono
  regressioni della storia particelle e non vengono assorbiti aggiornando
  la baseline. Baseline, soglie, eccezioni e policy coverage restano invariate.
- Graphify Ruolo codice/documenti, backend, frontend e documentazione
  piattaforma aggiornati con i target dedicati. Gli artefatti restano locali;
  la UI HTML dei grafi backend/frontend e omessa automaticamente per dimensione,
  mentre JSON e report sono aggiornati.

Log, coverage, screenshot e confronti completi della verifica iniziale sono
locali in `/tmp/gaia-parcel-history-20261112/`. Il successivo collaudo operativo
e il rilascio sono registrati nelle sezioni seguenti; le prove sintetiche
non certificano la completezza della catena documentale.

## Verifica finale e preparazione del rilascio

Verifica ripetuta il 12 novembre 2026 sullo stesso runtime congelato, in un
worktree dedicato per escludere le modifiche concorrenti a Tributi, Presenze e
Poste. **79 test backend PASS** con PostgreSQL isolato, **31 test frontend PASS**
con coverage full-file al 100%, **11 regressioni aggiuntive PASS** su vista
annuale e API del controllo. Ruff, ESLint, typecheck e confronto di complessita
del perimetro contro entrambi i merge-base: PASS. I 20 rilievi globali Presenze
restano preesistenti e separati dalla change; nessun aggiornamento della baseline.

### Corrispondenza comportamenti e test

| Comportamento | Test pertinente |
| --- | --- |
| Ricerca per contribuente conserva tutta la storia; nessuna creazione di pratica | `test_search_groups_full_history_and_never_creates_a_case` |
| Identificativi numerici, paginazione, wildcard letterali e validazione filtri | `test_pagination_empty_identifiers_literal_wildcards_and_invalid_filters`; test PostgreSQL reale |
| Importi della riga e dati mancanti distinti dallo zero | `test_tax_amounts_are_per_parcel_and_missing_is_not_zero`; test UI dei valori mancanti |
| Fonte, quote e diritti senza trasferimenti dedotti o cessazioni implicite | `test_history_owners_and_suppression_have_sources_but_no_inferred_transfer`; test UI storico catastale |
| Archivio limitato ai documenti accessibili e collegamenti canonici | `test_document_access_and_canonical_links_are_preserved` |
| Estrazioni assenti/fallite e documenti ambigui non inventano intestatari | `test_missing_failed_and_ambiguous_extractions_do_not_invent_owners` |
| Eventi da piu visure ordinati cronologicamente e prove senza data in fondo | `test_events_from_multiple_surveys_are_chronological_with_undated_evidence_last` |
| Consultazione in sola lettura e permessi | `test_read_only_user_can_consult_but_no_module_access_is_denied`; test API frontend autenticazione/no-cache |
| Ricerca predefinita, filtri nell'URL, pagine, dettaglio, tab da tastiera e ritorno | suite UI `parcel-history.test.tsx`; E2E desktop/mobile |
| Errori distinti dall'archivio vuoto, retry e risposte obsolete | test UI retry/stale response; test navigazione elenco/dettaglio; E2E servizio indisponibile |
| Viste controllo e annuale ancora raggiungibili esplicitamente | `parcel-control.test.tsx`, `parcel-control-annual.test.tsx`, `parcel-control-api.test.ts` |

### Prestazioni e ambito operativo

Probe prospettico in sola lettura sul database operativo, con timeout SQL di
25 secondi: **132.099 riferimenti raggruppati**, prima pagina senza filtri
**7,066 s**, dettaglio **0,416 s**, ricerca puntuale **0,842 s**. Sono misure
puntuali, non un benchmark di concorrenza: l'elenco generale resta piu lento
della ricerca filtrata. Nessun indice o dato operativo viene modificato.

Il rilascio e stato preparato in `/opt/gaia/releases/parcel-history-20261112` partendo
dalle immagini effettivamente attive. Si sostituiscono soltanto backend e
frontend, con configurazione effettiva e rollback congelati. Il router remoto
riceve soltanto l'inclusione della nuova API: non vengono attivati il vecchio
controllo istruttorio e le sue migrazioni, che non sono presenti nel runtime
operativo. Viene riusato il modulo di identita gia versionato nel repository.
I worker, gli invii e le loro impostazioni restano fuori dal rilascio.

Le prove delle immagini candidate e l'esito di attivazione sono registrati
separatamente: la sola preparazione non costituisce un deploy riuscito.
Evidenze locali di questo passaggio in `/tmp/gaia-parcel-release-20261112/`.

### Candidate collaudate prima dell'attivazione

Immagini backend `7fd488e33238` e frontend `3beebbd105ea`, costruite con delta
verificato sui runtime precedenti. Gli **11 test backend della storia** sono
stati eseguiti anche dentro l'immagine esatta, con PostgreSQL sintetico su rete
interna isolata: **100% statement/branch** sui tre nuovi runtime (117 statement,
20 rami). Il pacchetto di test riusa i test originali e solo fixture/modelli
istruttori di supporto; nessun servizio istruttorio viene aggiunto al runtime.

I **3 E2E Chromium** desktop/mobile e servizio indisponibile passano sulla
build candidata, non soltanto sulla build locale. Le API E2E sono intercettate
con dati sintetici. In parallelo i GET reali sul canary backend, con connessioni
DB obbligatoriamente read-only e lifespan disabilitato per evitare bootstrap,
restituiscono 200 per elenco/dettaglio/ricerca, 401 anonimo, 422 UUID non valido
e 404 UUID inesistente. Schema `20261106_1000`; nessuna migrazione della feature.
Il canary misura 6,558 s per l'elenco generale, 0,230 s per il dettaglio e
1,096 s per la ricerca puntuale, senza esporre nominativi o documenti nei log.

La disponibilita effettiva in produzione va letta nel registro di attivazione,
che viene scritto soltanto dopo il cambio delle immagini e i controlli finali.

## Produzione

Attivazione completata alle **18:40:57 CET** del 12 novembre 2026. Backend
`7fd488e33238`, frontend `3beebbd105ea`: entrambi healthy e identici alle
candidate collaudate, con BUILD_ID frontend verificato. Configurazione
effettiva, ambiente, comandi, mount, rete, risorse e healthcheck coincidono con
quelli precedenti. **35 container estranei invariati**, compresi i worker.
Nessuna migrazione nuova; schema sempre `20261106_1000`.

Le **891 route preesistenti** sono invariate nel contratto OpenAPI; si
aggiungono soltanto i due GET della storia. HTTP 200 per login, Particelle,
Tributi, Communications, Presenze e health; la nuova API anonima restituisce
401. Probe reali autenticati post-attivazione: elenco/dettaglio/ricerca 200,
UUID non valido 422, UUID inesistente 404. Elenco generale **5,005 s**,
dettaglio **0,116 s**, ricerca puntuale **0,756 s** nel campione rilevato.

Anche sulla pagina pubblicata in `http://gaia.lan/ruolo/particelle` i **3 E2E
Chromium PASS** verificano desktop/mobile e servizio indisponibile con retry.
Le API dei test browser sono sintetiche e intercettate; le API reali sono
verificate separatamente con GET in sola lettura. Nessun invio, creazione di
pratica, richiesta SISTER o modifica di documenti. Conteggi, hash dei template
Communications, schema, pausa e trasporto sono invariati rispetto al preflight.

Configurazioni risolte, manifest e rollback sono conservati privatamente nella
directory della release. Ripristinare soltanto backend/frontend usando i file
`*.rollback.json`, dopo aver verificato che non sia intervenuto un rilascio
successivo; nessun restore DB o riavvio globale. Non usare il checkout remoto
sporco come sorgente di un nuovo deploy indiscriminato.

Evidenza priva di segreti:
[PARCEL_HISTORY_RELEASE_2026-11-12.json](evidence/PARCEL_HISTORY_RELEASE_2026-11-12.json).

### Residui e limiti

- Nessun runtime nuovo o modificato resta privo di copertura: target 100%
  raggiunto senza esclusioni aggiuntive o test introdotti solo per coverage.
- L'elenco senza filtri richiede circa 5–7 secondi nel campione operativo;
  non e stato eseguito un benchmark di carico concorrente.
- La catena catastale resta da verificare sui documenti: periodi mancanti,
  genealogia di fusioni/frazionamenti e cessazione tributaria senza fonte non
  vengono ricostruiti per inferenza.
- Il controllo istruttorio legacy e le relative migrazioni restano fuori da
  questa release: il collegamento esplicito esiste, ma la sua API non e
  attivata nel runtime operativo. La nuova vista predefinita non la richiede.
- Restano i 20 rilievi di complessita Presenze preesistenti, non peggiorati
  dalla feature. Baseline, soglie, esclusioni e policy non vengono allargate.
- Il push riporta otto vulnerabilita sul branch predefinito (sette high, una
  moderate), gia segnalate nel rilascio precedente. E una notifica GitHub,
  non un nuovo audit; dipendenze e lockfile restano invariati in questa change.
