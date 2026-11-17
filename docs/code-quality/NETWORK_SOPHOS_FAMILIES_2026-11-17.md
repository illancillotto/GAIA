# Classificazione famiglie log Sophos — 2026-11-17

Esito **IMPROVED**: eliminati gli ultimi due Error di
`backend/app/modules/network/router/helpers/firewalls.py`, senza nuovi Warning.
Tutti i callable del file sono sotto soglia. Cognitiva aggregata64→46 e
decisioni aggregate55→38; nessuna violation trasferita.

## Modifica e invarianti

Il classificatore conserva normalizzazione iniziale e firma. La sequenza di
condizioni e rappresentata da una tabella immutabile di regole: famiglia,
prefisso evento opzionale e termini ordinati con il campo da interrogare.
Due helper risolvono la famiglia dai valori normalizzati e cercano i termini.
L'ordine resta Firewall, VPN, IPS, Authentication, System, Content filtering,
Anti-virus. Le regole conservano differenze fra startswith e contains; non
introducono matching generico su tutti i campi.

Entrambi i metadati vengono letti e normalizzati prima di event_type.lower,
anche se il primo segnale sarebbe sufficiente. Get, bool, str, strip, lower,
startswith e contains conservano numero, ordine e short-circuit; il prefisso
System resta una singola startswith con tupla. Il fallback conserva split
al primo punto, prefisso vuoto, truthiness e identita dell'evento senza punto.
Errori metadata/evento continuano a propagarsi. Nove altri callable hanno AST
identico e tutte le dieci firme preesistenti restano invariate. Nessuna modifica
a query, transazioni, API, schema o auth.

## Metriche

| Metrica | Prima | Dopo |
| --- | ---: | ---: |
| Classificatore: cognitiva | 38 | 5 |
| Classificatore: ciclomatica | 33 | 6 |
| Classificatore: LOC | 20 | 6 |
| Classificatore: nesting | 1 | 0 |
| Cognitiva aggregata file | 64 | 46 |
| Ciclomatica aggregata file | 65 | 50 |
| Somma cyclomatic meno 1 | 55 | 38 |
| LOC file | 253 | 261 |
| Callable | 10 | 12 |
| Error | 2 | 0 |
| Warning | 0 | 0 |

Helper famiglia cognitive/cyclomatic/LOC/nesting12/9/8/2; helper termini3/3/5/2.
Entrambi sotto soglia. La tabella esplicita sette regole senza duplicare rami;
le decisioni conteggiate si riducono mediante il percorso condiviso di ricerca.

## Verifiche

Artefatti `/tmp/gaia-network-sophos-family-refactor-20261117/`.
Nuovo test `backend/tests/test_network_sophos_log_family.py`.

- 136test PASS prima/dopo:18helper,50API Network,16riepilogo log e52nuove
  caratterizzazioni; zero skip/failure/error nei due XML.
- Full-file statement/branch100%:86/86statement prima/dopo e20/20→16/16branch;
  zero esclusioni, missing o branch parziali. Sorgente finale congelato con hash.
- Differenziale25000scenari equivalente per valore/tipo/identita del risultato,
  eccezioni e trace get/bool/str/lower/startswith/contains/split. Include valori
  non stringa, lower personalizzato, fallimenti alle singole operazioni,
  famiglie sovrapposte e metadati patologici.
- Cinque mutanti in memoria respinti: VPN prima Firewall, termine authentication
  del component rimosso, fallback prefisso vuoto sostituito, prefisso event.gui
  perso e lower tolto. Nessun mutante applicato al runtime su disco.
- Ratchet mirato origin/main PASS prima/dopo, baseline autorevole merge-base
  `686e529ee011487e0764b9f91d023be063dbdf55`. Il globale resta aperto sulla
  preesistente ambiguita Tributi; esito/log riportati separatamente nel checkpoint.
- Report completi1960file: Error1905→1903, Warning2955 invariati,
  callable22617→22619; solo firewalls.py varia metriche, nessun errore di parsing.
- Ruff runtime/test, format test nuovo, lint-backend236file e diff-check PASS.
  Nessun test preesistente modificato, rimosso o indebolito.
- Graphify Network force-pruned con Make dopo patch idempotente:467nodi/1177archi.
  Aggiornamento platform docs e completamento semantico registrati nel checkpoint.

Comandi principali dalla root, con coverage distinta prima/dopo:

```bash
COVERAGE_FILE=/tmp/gaia-network-sophos-family-refactor-20261117/.coverage-after DATABASE_URL=sqlite:////tmp/gaia-network-sophos-family-refactor-20261117/test.db backend/.venv/bin/python -m coverage run --branch -m pytest -q backend/tests/test_network_router_helpers.py backend/tests/test_network_api.py backend/tests/test_network_log_coverage.py backend/tests/test_network_sophos_log_family.py
COVERAGE_FILE=/tmp/gaia-network-sophos-family-refactor-20261117/.coverage-after backend/.venv/bin/python -m coverage json --include='*/network/router/helpers/firewalls.py' -o /tmp/gaia-network-sophos-family-refactor-20261117/coverage-after.json --fail-under=100
backend/.venv/bin/python /tmp/gaia-network-sophos-family-refactor-20261117/differential.py
backend/.venv/bin/python /tmp/gaia-network-sophos-family-refactor-20261117/mutations.py
backend/.venv/bin/python tools/code_quality/complexity.py ratchet --base-ref origin/main backend/app/modules/network/router/helpers/firewalls.py
make lint-backend QUALITY_PYTHON=backend/.venv/bin/python
make graphify-patch-force-pruning
make graphify-network-code GRAPHIFY_CODE_FLAGS=--force
make graphify-platform-docs
```

## Stato del checkout

HEAD `ce9968b65a1b8a6fe94d061f265df2623e9a4555`. Baseline/soglie/scope/eccezioni
intatti; nessuna sincronizzazione o baseline-verify nel checkout concorrente.
Hash endpoint precedente e report condivisi preservati. Dalla ripresa quindici
slice: -15Error/-18Warning/-98cognitiva aggregata. Nessuna percentuale storica
di completamento dedotta. Nessun commit, push, merge o deploy. Obiettivo generale
ancora attivo; selezione successiva da report corrente, in un turno separato.
