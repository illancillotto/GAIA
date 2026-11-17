# Nomi entita RDAP Network — 2026-11-17

Esito **IMPROVED**: un Error e un Warning rimossi dal servizio
`backend/app/modules/network/router/helpers/devices.py`.

## Responsabilita e invarianti

L'estrattore originale mescolava attraversamento delle entita, struttura della
vCard e validazione dei campi nome. Il flusso ora raccoglie i nomi dell'entita
tramite `_rdap_entity_names`; `_is_rdap_name_item` riconosce un campo fn/org
valido. Gli helper hanno confini corrispondenti alla struttura del payload,
restano nello stesso file e non modificano richieste WHOIS o serializer.

Ogni entita produce zero o un nome, conservando la prima riga valida, senza
priorita speciale fra fn e org. Sono preservati tipi accettati, marker vCard
non validato, forma della lista, ordine, trimming e deduplica stabile finale.
Le eccezioni per campi non hashable non vengono mascherate. Restano identici
ordine e numero delle letture e le due strip sui valori accettati: anche un
secondo risultato falsy di una sottoclasse str resta incluso, come prima.
Per questo il risultato dell'entita e una lista, senza filtro aggiuntivo sul nome.

I quattro altri callable hanno AST invariato, comprese richieste esterne e
serializzazione. Nessun cambiamento a API, auth, schema, query o transazioni.
Query Graphify Network eseguita prima dell'implementazione.

## Metriche

| Metrica | Prima | Dopo |
| --- | ---: | ---: |
| Estrattore nomi: ciclomatica | 15 | 3 |
| Estrattore nomi: cognitiva | 24 | 2 |
| Estrattore nomi: LOC / nesting | 22 / 3 | 8 / 1 |
| Cognitiva aggregata file | 65 | 57 |
| Ciclomatica aggregata file | 51 | 53 |
| Somma di cyclomatic meno 1 | 46 | 46 |
| LOC file | 188 | 192 |
| Callable | 5 | 7 |
| Error | 3 | 2 |
| Warning | 3 | 2 |

Helper entita cyclomatic/cognitive/LOC/nesting 8/9/10/2; predicato 6/5/8/0.
Entrambi hanno un parametro e sono sotto tutte le soglie. La somma ciclomatica
aumenta dei contributi base dei due callable; non si rivendica una riduzione
delle decisioni. Migliorano cognitiva e violation, senza debito trasferito.

Residui invariati: `_summarize_ip_whois` cyc 20/cog 27/LOC 68 e
`_serialize_device` LOC 55. Due Error e due Warning fuori dalla slice.

## Verifiche

Test nuovo: `backend/tests/test_network_rdap_names.py`.
Artefatti privati: `/tmp/gaia-network-rdap-refactor-20261117/`.

- Suite originale di 68 test PASS prima della caratterizzazione, coverage
  full-file 100%. Poi 105 test PASS prima/dopo: 18 helper router, 50 API
  Network e 37 caratterizzazioni nuove, zero skip, errori o failure.
- Coverage statement/branch full-file 100%: prima 73/73 statement e 28/28
  branch; dopo 77/77 e 28/28. Zero esclusioni, missing o branch parziali.
  Coverage raccolta con `coverage run --branch` e report filtrato al file.
- 20000 payload deterministici confrontati con il sorgente originale congelato:
  zero differenze di risultati/eccezioni e zero mutazioni. Incluse forme
  malformate di entita, vCard e righe, tipi errati e campi non hashable.
- Dodici prove sul vecchio e nuovo estrattore verificano trace delle letture,
  doppia strip e sottoclassi str con seconda risposta diversa, vuota, None,
  zero o non hashable. Nessuna normalizzazione aggiuntiva introdotta.
- Due mutanti in memoria respinti: riordino dei nomi e rifiuto dei campi org.
  Runtime su disco non alterato dai controtest.
- Ratchet mirato `origin/main` PASS prima/dopo, merge-base `686e529e`.
- Ruff runtime/test, format nuovo test, lint-backend su 221 file e diff-check
  PASS. Tutti i test originali restano invariati.
- Graphify Network aggiornato via Make: 441 nodi, 1116 archi, 18 comunita.

Comandi principali dalla root, con COVERAGE_FILE e JUnit distinti prima/dopo:

```bash
COVERAGE_FILE=/tmp/gaia-network-rdap-refactor-20261117/.coverage-after backend/.venv/bin/python -m coverage run --branch -m pytest -q backend/tests/test_network_router_helpers.py backend/tests/test_network_api.py backend/tests/test_network_rdap_names.py --junitxml=/tmp/gaia-network-rdap-refactor-20261117/tests-after.xml
COVERAGE_FILE=/tmp/gaia-network-rdap-refactor-20261117/.coverage-after backend/.venv/bin/python -m coverage json --include='*/network/router/helpers/devices.py' -o /tmp/gaia-network-rdap-refactor-20261117/coverage-after.json --fail-under=100
python3 tools/code_quality/complexity.py ratchet --base-ref origin/main backend/app/modules/network/router/helpers/devices.py
make lint-backend QUALITY_PYTHON=backend/.venv/bin/python
make graphify-network-code
```

## Baseline e checkout

SHA iniziale `82bda86882d9fd8c29955a8f750c54abca8fdb20`.
Baseline, soglie, scope ed eccezioni intatti; nessuna sincronizzazione nel
checkout concorrente e baseline-verify non eseguito.

Il report globale completo conta 1960 file, 22593 callable, 1916 Error e
2967 Warning. Rispetto alla fotografia precedente cambia anche
`domande_irrigue_autosync_scheduler.py` per lavoro concorrente: un callable
aggiunto, LOC 248→252, cognitiva invariata a 56, ciclomatica 58→59; nessun
delta nei suoi finding. Le sue variazioni non sono attribuite a RDAP.
Report condivisi gia modificati nel checkout preservati.

Il ratchet globale resta exit 2 per `ambiguous_identity` preesistente su
`useEffect[0]<callback>` in `frontend/src/app/ruolo/tributi/page.tsx`, dieci
candidati. La slice non certifica il resto del checkout o il completamento
del programma. Modifiche concorrenti e slice precedenti preservate.
Nessun commit, push, merge o deploy eseguito.
