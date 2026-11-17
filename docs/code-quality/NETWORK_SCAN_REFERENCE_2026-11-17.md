# Riferimento dispositivo scansione Network — 2026-11-17

Esito **IMPROVED** sulla ciclomatica del serializzatore: eliminato il Warning
di `backend/app/modules/network/router/helpers/scans.py`, senza trasferirlo.
Tutti i callable del file sono sotto soglia. Cognitiva e decisioni aggregate
restano invariate; nessuna riduzione aggregata rivendicata.

## Modifica e invarianti

`_find_scan_reference_device` isola la ricerca del dispositivo di riferimento,
prima per ID truthy e poi per IP truthy soltanto se il riferimento e None.
Il serializzatore conserva risoluzione label, costruzione di tutti i campi
del payload e validazione Pydantic. `_serialize_scan` ha AST identico;
le due firme preesistenti sono preservate.

IDzero continua a saltare il lookup ID. Un riferimento falsey ma non None
blocca il fallback IP e viene risolto per il nome, ma non legge assigned_user_id.
Letture ripetute di ID/IP mantengono ordine e valori, inclusi attributi che
cambiano dopo la prima lettura. Query, errori e priorita della label restano
identici: dispositivo corrente se trovato, altrimenti display_name/hostname/IP
dello snapshot. Tutti gli altri campi provengono ancora dallo snapshot, anche
quando il dispositivo corrente ha dati diversi. Nessuna modifica a API,
schema, autenticazione, autorizzazione o transazioni; nessun commit/flush introdotto.

## Metriche

| Metrica | Prima | Dopo |
| --- | ---: | ---: |
| Serializzatore: cognitiva | 12 | 7 |
| Serializzatore: ciclomatica | 12 | 8 |
| Serializzatore: LOC | 36 | 32 |
| Serializzatore: nesting | 1 | 0 |
| Cognitiva aggregata file | 12 | 12 |
| Ciclomatica aggregata file | 13 | 14 |
| Somma cyclomatic meno 1 | 11 | 11 |
| LOC file | 55 | 58 |
| Callable | 2 | 3 |
| Error | 0 | 0 |
| Warning | 1 | 0 |

Helper lookup cognitive/cyclomatic/LOC/nesting5/5/7/1, sotto tutte le soglie.
Il punto ciclomatico aggiunto corrisponde al nuovo callable; le decisioni
aggregate non crescono e nessuna violation viene trasferita.

## Verifiche

Artefatti `/tmp/gaia-network-scan-reference-refactor-20261117/`.
Nuovo test `backend/tests/test_network_scan_reference.py`.

- 89test PASS prima/dopo:18helper router,50API Network e21nuove caratterizzazioni;
  zero skip/failure/error nei due XML. Test confrontano tutti i campi risposta.
- Full-file statement/branch100%:19/19→22/22statement,4/4branch invariati;
  zero esclusioni, missing o branch parziali. Hash sorgente finale verificato.
- Differenziale16000scenari equivalente per intero payload Pydantic, errori,
  SQL e trace lookup/attributi/label/metadata. Include IDzero, riferimenti falsey,
  letture ID/IP variabili, metadati malformati e failure iniettate alle operazioni.
- Cinque mutanti in memoria respinti: lookup IDzero, fallback IP sopra ID valido,
  falsey trattato come assente, caching ID e caching IP. Nessun mutante applicato
  al runtime su disco; nessun test preesistente modificato, rimosso o indebolito.
- Ratchet mirato origin/main PASS prima/dopo contro baseline autorevole merge-base
  `686e529ee011487e0764b9f91d023be063dbdf55`. Globale exit2 per la stessa ambiguita
  Tributi preesistente: `useEffect[0]<callback>`, dieci candidati. Nessun PASS globale.
- Report completi1960file: Error1903 invariati, Warning2955→2954,
  callable22619→22620; solo scans.py varia metriche, nessun errore di parsing.
- Ruff runtime/test, format nuovo test, lint-backend238file e diff-check PASS.
- Graphify Network Make468nodi/1179archi; aggiornamento platform docs e verifica
  del completamento semantico registrati nel checkpoint.

Comandi principali dalla root, con coverage distinta prima/dopo:

```bash
COVERAGE_FILE=/tmp/gaia-network-scan-reference-refactor-20261117/.coverage-after DATABASE_URL=sqlite:////tmp/gaia-network-scan-reference-refactor-20261117/test.db backend/.venv/bin/python -m coverage run --branch -m pytest -q backend/tests/test_network_router_helpers.py backend/tests/test_network_api.py backend/tests/test_network_scan_reference.py
COVERAGE_FILE=/tmp/gaia-network-scan-reference-refactor-20261117/.coverage-after backend/.venv/bin/python -m coverage json --include='*/network/router/helpers/scans.py' -o /tmp/gaia-network-scan-reference-refactor-20261117/coverage-after.json --fail-under=100
backend/.venv/bin/python /tmp/gaia-network-scan-reference-refactor-20261117/differential.py
backend/.venv/bin/python /tmp/gaia-network-scan-reference-refactor-20261117/mutations.py
backend/.venv/bin/python tools/code_quality/complexity.py ratchet --base-ref origin/main backend/app/modules/network/router/helpers/scans.py
make lint-backend QUALITY_PYTHON=backend/.venv/bin/python
make graphify-network-code
make graphify-platform-docs
```

## Stato del checkout

HEAD `ce9968b65a1b8a6fe94d061f265df2623e9a4555`; baseline/soglie/scope/eccezioni
intatti, nessuna sincronizzazione o baseline-verify nel checkout concorrente.
Hash delle slice precedenti e report condivisi preservati. Dalla ripresa sedici
slice: -15Error/-19Warning/-98cognitiva aggregata; nessuna percentuale storica
di completamento dedotta. Nessun commit, push, merge o deploy. Obiettivo generale
ancora attivo; prossima azione: selezione del successivo hotspot dal report corrente.
