# Filtri saldo e annualita Tributi — 2026-10-19

## Comportamento implementato

Stato locale aggiornato al 12 novembre 2026. La pubblicazione resta subordinata
alle verifiche finali riportate in fondo; le evidenze del 19 ottobre descrivono
le release precedenti.

In `/ruolo/tributi`, `Elenco tributi` presenta `Anno tributario`,
`Solo non pagati (anche parziali)` e i pulsanti dello stato pagamento.
L'anno e il filtro principale: quattro cifre applicano una singola annualita;
il campo vuoto comprende tutti gli anni e tutte le tipologie. I caratteri non
numerici sono rimossi e un valore incompleto non avvia una nuova ricerca.
La modifica del filtro riporta alla pagina 1 e mantiene gli altri criteri.

I pulsanti dei periodi gestore e le scorciatoie riservate a Consorzio/GAIA sono
rimossi. Il riepilogo delle regole conserva le etichette configurate, fra cui:

- fino al 2017: Agenzia delle Entrate;
- 2018–2021: STEP - Agenzia recupero crediti;
- 2021: Anno 2021 - avvisi non notificati;
- dal 2022: Consorzio/GAIA.

Ogni avviso conserva la propria `annuality_manager_label` restituita dal
backend. Il frontend non deduce la tipologia dall'anno: avvisi STEP e avvisi
2021 non notificati possono comparire nella stessa ricerca.

Lista e KPI condividono anno, ricerca, comune, stato pagamento, workflow,
filtro saldo e collegamento anagrafico. La pagina non legge piu `manager_key`
dai link legacy e non lo invia alle API; una successiva modifica dei filtri
lo elimina dall'URL. Anche candidati e generazione del wizard usano gli anni
selezionati senza ereditare un filtro gestore invisibile. L'API conserva il
parametro opzionale per gli altri client; nessun contratto backend cambia.

`open_only` resta attivo per default: include non pagati, parziali e saldi
indeterminati da verificare; esclude saldati ed eccedenze. Attivandolo vengono
rimossi gli stati incompatibili (es. `paid`), preservando `unpaid` o `partial`
se scelti esplicitamente. I pulsanti `Tutti gli stati`, `Non pagati` e
`Pagamenti parziali` restano indipendenti dall'anno.

`list-filters.tsx` contiene anno e controlli di pagamento; la pagina mantiene
stato, debounce, richieste e autorizzazioni. Regole dei gestori, calcoli,
permessi e dati di produzione non vengono modificati.

## Evidenze storiche — 19 ottobre 2026

Le sezioni seguenti documentano i precedenti filtri per periodo, sostituiti
dal comportamento sopra descritto. Non sono prove della candidata di novembre.

## Prove pertinenti

- Tre scenari UI, uno per gestore: anno e filtro saldo, rimozione dello stato
  pagamento incompatibile, mantenimento ricerca, prima pagina, parametri
  lista/KPI e cambio periodo con cancellazione anno anche nelle richieste.
- Test UI esistenti preservati: digitazione incompleta, pulizia caratteri,
  selezione periodo, reset, storico, paginazione, gestori e dettagli.
- Tre scenari API con avvisi non pagati, parziali, saldati, in eccedenza e
  da verificare: confini 2017/2018 e 2021/2022, anno singolo, periodo completo,
  storico, residuo parziale e conteggi/importi KPI. Usano database SQLite
  isolato e API reali, senza contatti con dati di produzione.
- Sei regressioni API preesistenti su inCASS, filtri effettivi e gestori:
  nove test API complessivi PASS. Ruff check e format del nuovo test PASS.
- Suite tooling `tests/code_quality`: 270 PASS.

Comandi di verifica (frontend in directory isolata, dipendenze da lockfile):

```sh
npm ci
npm test
VITEST_COVERAGE_INCLUDE=src/app/ruolo/tributi/page.tsx,src/app/ruolo/tributi/list-filters.tsx npm run test:coverage -- --maxWorkers=2
npm run build
make complexity-ratchet BASE_REF=origin/main
make complexity-ratchet BASE_REF=f4dc144b
make complexity-baseline
make complexity-baseline-verify
make lint-backend QUALITY_PYTHON=/tmp/gaia-tributi-test-env/bin/python BASE_REF=HEAD
PYTHONPATH=backend /tmp/gaia-tributi-test-env/bin/python -m pytest -q backend/tests/ruolo/test_tributi_balance_filters.py backend/tests/ruolo/test_tributi_api.py -k 'balance_filters or year_managers_are_configurable or rateized_incass_paid or non_rateized_incass_paid or effective_payment_filter or marks_missing_due'
/tmp/gaia-tributi-test-env/bin/python -m pytest -q tests/code_quality
```

## Riproducibilita e complessita

La baseline globale precedente falliva anche sul checkout pulito `5e158913`
con `ambiguous_identity` nella pagina utenti. Recupero documentato in
`docs/code-quality/PROGRESS.md`, commit separato `f4dc144b`, generato soltanto
dal runtime gia committato. La feature passa il ratchet sia contro
`origin/main` originale sia contro `f4dc144b`, zero finding. La sincronizzazione
successiva modifica i record metrici soltanto dei due file Tributi.

`RuoloTributiPageContent`: cognitiva `204 -> 204`, ciclomatica `173 -> 173`,
LOC `1064 -> 1052`. Il nuovo componente ha cognitiva `1`, ciclomatica `2`,
LOC `60`: warning dimensionale, nessuna nuova violation error-level.
Si tratta di una feature con riorganizzazione locale, non di una riduzione
certificata della complessita globale.

L'installazione pulita ha rilevato due incompatibilita gia presenti nel
manifest: Vitest 5 con provider coverage 4 e Tailwind 4 con plugin PostCSS 3.
La release fissa runner/provider `4.1.6` e Tailwind `3.4.13`, coerenti con
configurazione e Node 20 della CI. `npm ci` passa senza forzature. Next resta
alla versione del lockfile `15.5.27`. Le prove con Vitest 5/Tailwind 4 fallite
sono diagnostiche di una configurazione scartata, non prove della release.

La prima suite sulle dipendenze locali passa 5241 test e 18 smoke; la suite
pulita eseguita insieme alla build incontra due timeout in GIS/Presenze.
Gli stessi due file, con concorrenza ridotta e timeout invariati, passano
tutti i 235 test. La verifica finale completa con due worker passa 5241 test
in 322 file, senza skip o failure, e 18 smoke test. Coverage full-file dei due
runtime: statement 678/678, branch 654/654, funzioni 216/216 e linee 616/616,
tutte al 100%. Nessuna nuova esclusione o riduzione delle soglie.
Build pulita: compilazione, lint, tipi e generazione di 163 pagine PASS.

Restano warning ESLint preesistenti. `npm audit` della toolchain compatibile
segnala 24 dipendenze (15 high, 9 moderate), incluse dipendenze di sviluppo
delle versioni compatibili. In produzione restano le stesse cinque
segnalazioni della base (2 high, 3 moderate), senza variazioni. Nessun audit
fix automatico o migrazione maggiore e incluso; questo rilascio non certifica
l'assenza di vulnerabilita dell'intero repository.

## Rilascio

Immagine candidata `gaia-frontend:tributi-filters-20261019`, costruita da
sorgenti isolati e lockfile verificato. Directory server
`/opt/gaia/releases/tributi-filters-20261019`: sorgenti, build log, snapshot
riservato del container precedente e script di deploy/rollback solo frontend.
Il checkout sporco `/opt/gaia`, gli overlay, l'ambiente e gli altri servizi
sono preservati. Immagine di rollback `gaia-frontend:55a1b1d3`.

L'immagine candidata supera lo smoke su porta loopback 3301: home, login e
`/ruolo/tributi` HTTP 200; il bundle servito contiene anno, filtro non pagati
e descrizione del saldo. Immagine verificata:
`sha256:ceb05843cbd380e11cb2f7da71c0990d0adfd1193ee2b2c02e01e62ee7f0ddb2`.
Archivio sorgenti locale/remoto con SHA256 identico:
`465f17ff7502db5f615adc48709c66e11d72992a86f3f1af0ba944e455cd0248`.

Deploy completato il 2026-10-19 dopo il commit applicativo `837ae49c`.
Container `gaia-frontend` healthy, immagine corrispondente al digest candidato.
Smoke dal server e dalla workstation: home, login e Tributi HTTP 200,
bundle dei nuovi controlli effettivamente servito da `gaia.lan`;
`/api/health` restituisce backend production `ok`.
Il confronto degli ID conferma nessun altro container ricreato. Il container
temporaneo candidato e stato rimosso; rollback conservato nella directory release.

Graphify frontend aggiornato con pruning forzato; corpus docs Ruolo e piattaforma
aggiornati con `gpt-reserve`, chunk completati senza failure semantiche.
I grafi restano ignorati da Git. Le segnalazioni npm audit, i warning ESLint e
il warning gia legato all'avvio `next start` con output standalone restano
limiti dichiarati; non sono emerse regressioni funzionali nei controlli finali.

## Follow-up: pulsanti annuali Consorzio/GAIA

Estensione del 2026-10-19, successiva al rilascio `837ae49c`:

- Un test UI per ciascun pulsante 2022–2025 verifica selezione, campo anno,
  ricerca preservata, pagina 1, URL e parametri lista/KPI con non pagati attivo.
- Un ulteriore scenario verifica anno da URL, digitazione manuale anche fuori
  scorciatoie, `Tutti gli anni` con richieste senza anno, storico preservato,
  scomparsa nei due altri periodi e ricomparsa tornando a GAIA.
- Le query dei test del wizard e della configurazione gestori sono circoscritte
  alla rispettiva UI per non confondere pulsanti con le stesse etichette.
- Suite mirata: 52 test PASS, coverage full-file `list-filters.tsx` 100%:
  statement 34/34, branch 24/24, funzioni 15/15, linee 28/28.
- ESLint dei due file toccati e typecheck PASS, dipendenze installate da lockfile.
- Ratchet contro `86ac8643`: zero finding. `TributiListFilters` mantiene
  cognitiva 1/ciclomatica 2, LOC 60 -> 43. Il controllo anno e scorciatoie e
  un componente coeso (`AnnualityYearFilter`: cognitiva 2, ciclomatica 3,
  LOC 37). Nel file non restano warning o violation; nessun cambio di soglie,
  esclusioni o runtime backend. La crescita funzionale non viene presentata
  come riduzione della complessita globale.
- Aggregati file: cognitiva 12 -> 15, ciclomatica 23 -> 29, LOC 141 -> 161,
  coerenti con l'aggiunta delle scorciatoie. Baseline sincronizzata solo dopo
  il ratchet e verificata riproducibile; cambia soltanto il file runtime toccato
  oltre ai metadati di generazione.

Comandi del follow-up:

```sh
VITEST_COVERAGE_INCLUDE=src/app/ruolo/tributi/list-filters.tsx npm run test:coverage -- tests/unit/ruolo-tributi-page.test.tsx
VITEST_COVERAGE_INCLUDE=src/app/ruolo/tributi/list-filters.tsx npm run test:coverage -- --maxWorkers=2
npm test
./node_modules/.bin/eslint src/app/ruolo/tributi/list-filters.tsx tests/unit/ruolo-tributi-page.test.tsx
npm run typecheck
make complexity-ratchet BASE_REF=86ac8643
make complexity-baseline
make complexity-baseline-verify
make graphify-patch-force-pruning
make graphify-frontend GRAPHIFY_CODE_FLAGS=--force
```

Verifica finale follow-up: 5246 test in 322 file e 18 smoke PASS, senza skip
o failure; coverage full-file invariata al 100% su tutte le metriche.
Build Docker isolata con Node 20 e lockfile: compilazione, lint, tipi e
generazione di 163 pagine PASS. Nessuna dipendenza modificata in questo ciclo.
Restano i warning e le segnalazioni audit del rilascio precedente.

Graphify frontend aggiornato con pruning: 6690 nodi, 15929 edge. JSON e report
sono correnti; HTML omesso dal limite automatico di 5000 nodi. Docs Ruolo
aggiornati tramite il target dedicato con `gpt-reserve`, `chunk 1/1 done`
senza failure semantiche. Nessun output Graphify viene committato.

Immagine candidata del follow-up `gaia-frontend:tributi-year-buttons-20261019`,
digest `sha256:0f1f124e8a92c403edfe5cf92c2099ca615db59c45f8be7817eee72888b5f2ca`.
Directory isolata `/opt/gaia/releases/tributi-year-buttons-20261019`, con
snapshot e rollback alla release `gaia-frontend:tributi-filters-20261019`.
SHA256 archivio sorgenti locale/remoto:
`f8ebb5a5856a9d4a97135bbdf713fe2c3b16428b91023174c8d68b3fba300aa4`.
Smoke candidato sulla porta loopback 3301 PASS: home, login, Tributi e bundle
contenente il gruppo `Anni Consorzio/GAIA`, le quattro annualita e il reset.
Le interazioni autenticate sono verificate nei test UI montati; lo smoke
HTTP di rilascio non sostituisce una verifica visuale autenticata nel browser.

Deploy del follow-up completato il 2026-10-19, commit `320f1b86`. L'archivio
frontend del commit e identico file per file ai sorgenti dell'immagine candidata.
Container healthy e digest corrispondente; smoke dal server e dalla workstation
PASS su home, login, Tributi e nuovi asset. `/api/health`: production `ok`.
Solo `gaia-frontend` ricreato; tutti gli altri ID container invariati, candidato
temporaneo rimosso e rollback conservato. Il checkout remoto sporco non e stato
modificato. Nessuna nuova failure o parte runtime modificata non coperta nei
controlli finali; rimangono i limiti preesistenti gia dichiarati.

## Verifica finale candidata — 12 novembre 2026

Perimetro: `frontend/src/app/ruolo/tributi/page.tsx`, `list-filters.tsx`,
la suite unit della pagina e le prove browser anno/gestori sovrapposti.
Checkout isolato da `5f50a349`, con overlay dei soli file del ciclo e
collegamento all'installazione locale delle dipendenze. Le modifiche
concorrenti alle particelle e alla configurazione non sono incluse.

### Comportamenti verificati

- Anno completo/incompleto, pulizia input, annualita 2017/2019/2021/2024/2026,
  anno da URL, cancellazione anno e ritorno alla pagina 1.
- Ricerca e stato pagamento preservati; stato incompatibile rimosso quando
  si riattiva il filtro saldo. Lista e KPI ricevono gli stessi criteri.
- Link legacy STEP/GAIA/AdE senza restrizioni nascoste su lista e KPI;
  il cambio filtri rimuove `manager_key` dall'URL.
- Due avvisi 2021 con etichette STEP e non notificati restano distinguibili;
  le etichette non diventano pulsanti di selezione della tipologia.
- Candidati e batch wizard non ereditano il gestore dal vecchio URL.
- Configurazione gestore 2021: errore salvataggio, form preservato, retry,
  etichetta aggiornata e selezione anno nel wizard.
- Anteprima privata PDF 2022 preservata, compreso errore/retry e download
  esplicito, senza invio di comunicazioni reali.

I nuovi test verificano interazioni e richieste osservabili; nessun test
aggiunto soltanto per incrementare la coverage e nessuna nuova esclusione.

### Esiti

| Verifica | Esito |
| --- | --- |
| Intera suite unit frontend | 5.711 PASS in 367 file, zero failure/skip |
| Smoke frontend | 18 PASS |
| E2E Chromium, 1440 e 390 px | 6 PASS; screenshot ispezionati |
| Build produzione | PASS, 196 route generate |
| TypeScript | PASS |
| ESLint perimetro | 0 errori; un warning hook preesistente |
| Coverage statement | 646/646, 100% |
| Coverage branch | 626/626, 100% |
| Coverage funzioni | 204/204, 100% |
| Coverage righe | 586/586, 100% |
| Ratchet autorevole contro `main` | BLOCCATO: `ambiguous_identity` |
| Diff whitespace | PASS |

La coverage misura entrambi i file runtime interi secondo la configurazione
esistente, incluse le direttive `c8 ignore` legacy gia presenti nella pagina;
non certifica quei rami esclusi. Tutto il codice di questo delta e esercitato;
non sono state introdotte o ampliate esclusioni. Restano i warning ESLint
legacy della build e quello sulle dipendenze di `refreshCalculationPolicies`
e `refreshYearManagers`, riprodotto nel sorgente precedente.

La prima corsa E2E ha avuto 4 PASS e 2 failure nel nuovo test: il selettore
per assenza dei vecchi pulsanti gestore includeva anche la riga avviso
cliccabile, che contiene l'etichetta STEP. Il test ora identifica i nomi
completi dei periodi. Ripetizione dei sei scenari: 6 PASS, runtime invariato.
I messaggi jsdom `Not implemented: navigation to another Document` nella suite
completa non hanno prodotto failure. Il server di verifica e stato avviato con
`next start`; il warning relativo a `output: standalone` resta distinto dalla
build di produzione superata.

### Complessita e blocco di rilascio

| Unita | Cognitiva prima/dopo | Ciclomatica prima/dopo | LOC prima/dopo |
| --- | --- | --- | --- |
| `RuoloTributiPageContent` | 195 / 193 | 169 / 167 | 1041 / 1027 |
| `TributiListFilters` | 0 / 0 | 1 / 1 | 27 / 14 |
| `AnnualityYearFilter` | 2 / 0 | 3 / 1 | 37 / 22 |
| Callback autoapplicazione filtri | 13 / 12 | 12 / 11 | 29 / 27 |

Le somme file diminuiscono: pagina cognitiva 636 -> 633, ciclomatica
758 -> 755; filtri 13 -> 7 e 26 -> 11. Il debito legacy della pagina resta
visibile: LOC file 2854 -> 2836, `useState` 25 -> 24, `useEffect` 10 invariati.
Nel perimetro restano 20 finding error e 11 warning gia presenti; nessuna
baseline o soglia e stata modificata per nasconderli.

Il ratchet legge la baseline del merge-base `686e529e` (sorgenti baseline
`bdb41d8a`) e si ferma su `useEffect[0]<callback>`. Il replay dei sorgenti
precedenti passa; il problema quindi non e dichiarato preesistente. I confini
della callback corrente 466–495 mappano a 473–504 e le metriche calano, ma
manca l'ancora esterna precedente richiesta dal verificatore, a causa della
rimozione del gestore dalle dipendenze dell'effetto adiacente. Anche il
confronto diagnostico con una baseline del solo stato precedente riproduce
l'ambiguita: rigenerare la baseline non risolve il problema.

La corrispondenza diagnostica non equivale al PASS del gate. Nessun cambio
al matcher, eccezione, rinomina o codice artificiale e stato introdotto per
aggirarlo. La candidata resta **BLOCCATA per commit e deploy**, in conformita
alla richiesta di pubblicare solo dopo il superamento di tutti i controlli.
Serve una decisione separata sul trattamento della provenienza nel controllo
di complessita; le verifiche funzionali non la sostituiscono.

### Riproduzione e artefatti

Nel checkout isolato `/tmp/gaia-tributi-final-20261112`, frontend:

```sh
VITEST_COVERAGE_INCLUDE=src/app/ruolo/tributi/page.tsx,src/app/ruolo/tributi/list-filters.tsx npm run test:coverage -- --maxWorkers=2
npm test
npm run build
npm run typecheck
PLAYWRIGHT_BASE_URL=http://127.0.0.1:3312 npm run test:e2e -- tests/e2e/ruolo-tributi-year-filter.spec.ts tests/e2e/ruolo-2021-overlap.spec.ts tests/e2e/ruolo-tributi-draft-preview.spec.ts --workers=1
```

Il comando E2E richiede il frontend candidato avviato sulla porta indicata;
tutte le API sono intercettate con fixture, senza letture o scritture reali.
Dalla root, controllo e aggiornamento grafi tramite i target supportati:

```sh
python3 tools/code_quality/complexity.py ratchet --base-ref main frontend/src/app/ruolo/tributi/page.tsx frontend/src/app/ruolo/tributi/list-filters.tsx
make graphify-patch-force-pruning
make graphify-frontend GRAPHIFY_CODE_FLAGS=--force
make graphify-ruolo-docs
```

Artefatti locali del ciclo: `/tmp/gaia-tributi-final-{full-tests,build,eslint,e2e-verified}.log`,
`/tmp/gaia-tributi-final-full-coverage/`, `/tmp/gaia-tributi-final-e2e-verified/`,
`/tmp/gaia-tributi-final-{ratchet,ambiguity,metrics}.json`.
Grafi ignorati da Git. Non e stato eseguito alcun commit, push o deploy;
il preflight sul CED si limita alla lettura dello stato frontend.

## Verifica nella candidata del 18 novembre 2026

La pagina usa lo stesso tipo per i filtri letti dall’URL e per quelli in
modifica. Il confronto tra le due query normalizzate decide se avviare il timer
di navigazione di 350 ms. Il cambio di filtro riparte da pagina 1.
L’autosubmit conserva le soglie per testo e anno e annulla il timer al cambio
dei parametri o allo smontaggio.

Sul target `686e529e` il ratchet dei due file Tributi passa. La verifica sui
sorgenti abbina tutti i dieci effetti della pagina ai rispettivi corpi della
baseline. I 64 test unit della pagina passano con copertura integrale di
statement, branch, funzioni e righe misurati nei due file. Passano anche i sei
E2E desktop e mobile per annualità, regole sovrapposte e anteprima del sollecito.
Il ratchet globale riporta ancora i 20 rilievi Presenze già presenti in
`743b21c1`. La candidata resta esclusa dall’integrazione.
