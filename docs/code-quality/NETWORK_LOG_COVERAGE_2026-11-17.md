# Riepilogo copertura log firewall — 2026-11-17

Esito **IMPROVED**: due Error e un Warning eliminati in
`backend/app/modules/network/router/helpers/firewalls.py`.

## Modifica e invarianti

`_build_firewall_log_coverage_summary` mantiene query e risposta pubblica.
Tre helper separano aggregazione delle righe SQL, aggiornamento del singolo
bucket e costruzione delle famiglie attese/aggiuntive. L'accumulo del bucket
esce dal ciclo principale: diminuisce l'annidamento effettivo, senza duplicare
rami o trasferire violation. Classificazione e sei altri callable sono invariati
nell'AST; tutte le sette firme preesistenti restano identiche.

Restano invariati filtro firewall/finestra, proiezione aggregata e streaming
`yield_per=1000`, due letture del clock, ordine delle letture delle righe,
conversione dei conteggi e propagazione degli errori. Le somme includono anche
zero e valori negativi come prima. Timestamp massimo, primi tre esempi distinti
in ordine input, ordine delle cinque famiglie attese, ordinamento stabile delle
aggiuntive e top sei event type mantengono la stessa semantica. Nessuna modifica
a API, schema, auth o transazioni.

## Metriche

| Metrica | Prima | Dopo |
| --- | ---: | ---: |
| Riepilogo: cognitiva | 22 | 2 |
| Riepilogo: ciclomatica | 16 | 3 |
| Riepilogo: LOC | 84 | 35 |
| Riepilogo: nesting | 2 | 0 |
| Cognitiva aggregata file | 68 | 64 |
| Ciclomatica aggregata file | 62 | 65 |
| Somma cyclomatic meno 1 | 55 | 55 |
| LOC file | 235 | 253 |
| Callable | 7 | 10 |
| Error | 4 | 2 |
| Warning | 1 | 0 |

I tre helper hanno cyclomatic/cognitive/LOC/nesting rispettivamente
4/4/24/1, 7/8/12/1 e 5/4/30/0, tutti sotto soglia. I tre punti ciclomatici
aggiunti corrispondono ai tre callable: le decisioni aggregate restano 55.
La cognitiva aggregata diminuisce di quattro punti. Restano due Error nel
classificatore Sophos (cyc 33, cog 38), fuori da questa slice e invariato.

## Verifiche

Artefatti: `/tmp/gaia-network-log-coverage-refactor-20261117/`.
Test nuovo: `backend/tests/test_network_log_coverage.py`.

- 84 test PASS prima/dopo, zero skip/failure/error: 18 helper originali,
  tutti i 50 test API Network, 16 nuove caratterizzazioni.
- Coverage full-file statement/branch 100%: 77/77 statement prima, 86/86
  dopo; branch 20/20 prima/dopo. Zero esclusioni, missing o branch parziali.
- Anche i soli 68 test preesistenti passano sul codice originale con
  coverage full-file 100%; i nuovi casi fissano i contratti del riepilogo.
- Differenziale deterministico su 12000 sequenze di righe: 3863 risultati e
  8137 eccezioni, zero differenze. Confrontati risposta, tipo/testo eccezioni,
  SQL e parametri, opzioni streaming, clock/ID, ordine iterazione/letture e
  assenza di mutazioni. Include righe duplicate, conteggi malformati,
  timestamp incompatibili ed errori durante la lettura della riga.
- Tre mutanti in memoria respinti dai nuovi test: quattro esempi ammessi,
  ordinamento crescente delle famiglie e timestamp minimo invece del massimo.
  Nessun mutante applicato al runtime su disco.
- Ratchet mirato `origin/main` PASS prima/dopo, merge-base `686e529e`.
- Ruff runtime/test e format-check del nuovo test PASS; lint-backend PASS
  su 224 file cambiati. Nessun test preesistente modificato o indebolito.
- Graphify Network aggiornato tramite Make: 447 nodi, 1132 archi,
  18 comunita. Aggiornamento della documentazione piattaforma registrato
  nel checkpoint della slice.

Comandi principali dalla root, con file coverage distinti per prima/dopo:

```bash
COVERAGE_FILE=/tmp/gaia-network-log-coverage-refactor-20261117/.coverage-after DATABASE_URL=sqlite:////tmp/gaia-network-log-coverage-refactor-20261117/test.db backend/.venv/bin/python -m coverage run --branch -m pytest -q backend/tests/test_network_router_helpers.py backend/tests/test_network_api.py backend/tests/test_network_log_coverage.py
COVERAGE_FILE=/tmp/gaia-network-log-coverage-refactor-20261117/.coverage-after backend/.venv/bin/python -m coverage json --include='*/network/router/helpers/firewalls.py' -o /tmp/gaia-network-log-coverage-refactor-20261117/coverage-after.json --fail-under=100
backend/.venv/bin/python /tmp/gaia-network-log-coverage-refactor-20261117/differential.py
python3 tools/code_quality/complexity.py ratchet --base-ref origin/main backend/app/modules/network/router/helpers/firewalls.py
make lint-backend QUALITY_PYTHON=backend/.venv/bin/python
make graphify-network-code
make graphify-platform-docs
```

## Stato del checkout

HEAD iniziale `82bda86882d9fd8c29955a8f750c54abca8fdb20`. Sorgente originale,
report, log, XML e hash sono conservati negli artefatti della slice.
Baseline, soglie, scope ed eccezioni intatti; baseline non sincronizzata
nel checkout concorrente e baseline-verify non eseguito. I report condivisi
preesistenti non sono stati sovrascritti. Nessun commit, push, merge o deploy.

Report globali prima/dopo: 1960 file; Error 1914→1912, Warning 2966→2965,
callable 22596→22599. Unico path con metriche variate `firewalls.py`.
Ratchet globale exit 2 per l'identica ambiguita preesistente di
`useEffect[0]<callback>` in `frontend/src/app/ruolo/tributi/page.tsx`, dieci
candidati. Nessuna certificazione del gate globale o del completamento del
programma. Dalla ripresa, sei slice hanno eliminato complessivamente sei
Error e otto Warning, riducendo di 25 la cognitiva aggregata dei file.
