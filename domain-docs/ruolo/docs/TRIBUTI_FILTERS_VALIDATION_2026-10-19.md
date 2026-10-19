# Filtri saldo e annualita Tributi — 2026-10-19

## Comportamento implementato

In `/ruolo/tributi`, `Elenco tributi` presenta insieme i periodi dei gestori,
il campo `Anno tributario` e `Solo non pagati (anche parziali)`:

- fino al 2017: Agenzia delle Entrate;
- 2018–2021: STEP;
- dal 2022: Consorzio/GAIA, selezione iniziale.

I periodi provengono dalle regole gestori attive; le date non sono duplicate
nel nuovo componente. Anno vuoto significa intero periodo. Un anno completo
restringe il periodo; cambiarlo riparte dalla prima pagina. Se si cambia
gestore, l'anno viene svuotato per evitare intersezioni involontariamente vuote.

Il filtro saldo riusa `open_only`, attivo per default. Include non pagati,
parziali e saldi non determinabili da verificare; esclude saldati ed eccedenze.
La nota accanto al controllo esplicita i casi da verificare. Attivandolo si
azzera `payment_status`, per non mantenere un precedente filtro `paid` o
`unpaid` che escluderebbe gli altri scoperti. Disattivandolo si torna allo
storico del periodo. Gli altri filtri restano disponibili.

URL, paginazione e KPI utilizzano gli stessi parametri API. Il componente
`list-filters.tsx` riunisce la UI dei periodi e i due controlli; la pagina
mantiene stato, debounce, richieste e autorizzazioni. Nessuna modifica a schema,
calcolo del saldo, backend runtime o scrittura di dati di produzione.

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

Gate finali superati; attivazione di produzione successiva al commit e
verifica live da registrare dopo lo switch. Le segnalazioni npm audit e i
warning preesistenti sopra restano limiti dichiarati del rilascio.
