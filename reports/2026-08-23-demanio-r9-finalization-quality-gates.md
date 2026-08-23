# GAIA/SISTER — Demanio_R9 finalizzazione codice e quality gates

Data: 2026-08-23
Branch: `main`
Scope: fix CAPTCHA manuale rigenerato da SISTER, docs operative, Graphify, test/coverage, commit locale.

## Modifiche incluse

- `modules/elaborazioni/worker/visura_flow.py`
  - Se SISTER rifiuta un CAPTCHA manuale, il worker ricarica il CAPTCHA e richiede una nuova verifica manuale invece di fallire subito la richiesta.
  - Il numero massimo di tentativi manuali viene letto da `CAPTCHA_MANUAL_ATTEMPTS`, default `5`.
- `modules/elaborazioni/worker/tests/test_visura_flow.py`
  - Test per CAPTCHA errato che viene rigenerato e poi completato.
  - Test per esaurimento dei tentativi manuali configurati.
  - Test per default letto da environment.
- `modules/elaborazioni/worker/tests/test_posta_online_client.py`
  - Stabilizzato il mock Playwright nei test: il modulo fake sovrascrive sempre `sys.modules`, evitando mismatch con `TimeoutError` reale quando Playwright è installato nel venv.
- `backend/tests/test_coverage_small_runtime.py`
  - Aggiornati fixture legacy ai campi richiesti dagli schemi correnti (`sister_*`, `retry_not_before`, `last_error_code`, `sha256`).
- `.env.example`, `.env.production.example`, `docker-compose.yml`
  - Documentati/propagati `CAPTCHA_MANUAL_ATTEMPTS=5`, `CAPTCHA_MANUAL_TIMEOUT_SEC=900`, `ELABORAZIONI_MAX_REQUEST_ATTEMPTS=50`.
- `domain-docs/elaborazioni/README.md`
  - Aggiornata documentazione runtime SISTER/CAPTCHA.

## Verifiche eseguite

### Backend full suite

Comando:

```bash
cd backend && .venv/bin/python -m pytest -q
```

Esito: PASS, exit code `0`.

Note: output con warning legacy già presenti su `runpy` e `InsecureKeyLengthWarning` nei test; nessun failure finale.

### Worker full suite

Comando:

```bash
PYTHONPATH=/home/cbo/CursorProjects/GAIA/backend:/home/cbo/CursorProjects/GAIA/modules/elaborazioni/worker \
  ./.venv/bin/python -m pytest modules/elaborazioni/worker/tests -q
```

Esito:

```text
354 passed in 38.38s
```

### Coverage 100% file runtime modificato

Comando:

```bash
PYTHONPATH=/home/cbo/CursorProjects/GAIA/backend:/home/cbo/CursorProjects/GAIA/modules/elaborazioni/worker \
  ./.venv/bin/python -m coverage run --branch --include='*/modules/elaborazioni/worker/visura_flow.py' \
  -m pytest modules/elaborazioni/worker/tests/test_visura_flow.py -q
./.venv/bin/python -m coverage report --show-missing --fail-under=100 modules/elaborazioni/worker/visura_flow.py
```

Esito:

```text
37 passed in 0.10s
Name                                         Stmts   Miss Branch BrPart  Cover
----------------------------------------------------------------------------------------
modules/elaborazioni/worker/visura_flow.py     224      0     68      0   100%
TOTAL                                          224      0     68      0   100%
```

### Frontend smoke

Comando:

```bash
cd frontend && npm test
```

Esito:

```text
18 passed
```

### Frontend typecheck e coverage globale

Comandi:

```bash
cd frontend && npm run typecheck
cd frontend && npm run test:coverage
```

Esito: FAIL non legato alla change CAPTCHA.

- `npm run typecheck` fallisce su numerosi test/unit legacy con tipi API aggiornati.
- `npm run test:coverage` esegue i test Vitest con successo (`149` file, `1447` test), ma fallisce sulla soglia globale `100%` del frontend: coverage globale circa `42.28%` statements / `38.32%` branches / `43.03%` lines.
- Nessun file runtime frontend è stato modificato in questa change.

## Graphify

Eseguito:

```bash
make graphify-patch-openai-base-url
make graphify-docs
cd modules/elaborazioni/worker && graphify update .
```

Esito docs:

```text
1179 nodes, 1802 edges, 117 communities
189 files cached/unchanged, 11 re-extracted
```

Esito worker code:

```text
1145 nodes, 2753 edges, 47 communities
```

## Audit

- `git diff --check`: PASS prima dello staging.
- Secret scan su file candidati: nessun segreto reale rilevato; presenti solo placeholder/nomi variabili negli example file e docs (`PASSWORD=`, `SECRET=`, `TOKEN=`, `API_KEY=`, `CREDENTIAL_MASTER_KEY`).
- Staging previsto a file espliciti; niente `git add .`.

## Stato qualità

PASS per la change SISTER/CAPTCHA:

- backend full suite PASS;
- worker full suite PASS;
- coverage 100% su `visura_flow.py` PASS;
- frontend smoke PASS;
- Graphify aggiornato.

Limitazione nota non introdotta da questa change:

- frontend typecheck globale FAIL;
- frontend coverage globale FAIL rispetto al gate repository-wide 100%.
