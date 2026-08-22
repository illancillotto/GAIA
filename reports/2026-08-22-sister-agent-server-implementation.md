# GAIA/SISTER — CAPTCHA Agent server-side implementation

Data: 2026-08-22

## Scope

Implementazione del solver CAPTCHA SISTER via Cursor Agent direttamente nel runtime server/container, senza watcher Hermes esterno.

## Modifiche principali

- `modules/elaborazioni/worker/llm_captcha_solver.py`
  - usa Agent in headless ask mode con modello `auto`;
  - accetta output `text` oltre al JSON legacy;
  - legge `CURSOR_AUTH_TOKEN_FILE` e passa `CURSOR_AUTH_TOKEN` al subprocess senza loggare il token;
  - normalizza solo token CAPTCHA alfanumerici.
- `docker-compose.yml`
  - parametrizza `CAPTCHA_AGENT_HOME`, `CAPTCHA_LLM_AGENT_CMD`, `CAPTCHA_LLM_AGENT_MODEL`, `CAPTCHA_LLM_AGENT_OUTPUT_FORMAT`, `CURSOR_AUTH_TOKEN_FILE`;
  - monta home/config Cursor Agent in modo server-specifico.
- `.env.example` e `.env.production.example`
  - documentano i valori richiesti per dev e server CED.
- `domain-docs/wiki/operational/pages/elaborazioni__visure.md`
  - aggiunge runbook operativo CAPTCHA Agent.

## Verifiche eseguite

- Unit solver CAPTCHA con coverage file-level 100%:

```text
20 passed
llm_captcha_solver.py: 100%
```

- Regression worker mirate:

```text
100 passed
```

- Backend regression mirate:

```text
21 passed
```

- Frontend unit mirate con Vitest:

```text
2 files passed, 56 tests passed
```

- Graphify:

```text
make graphify-backend: PASS
make graphify-frontend: PASS
make graphify-wiki-docs: PASS
```

## Nota coverage

Il nuovo solver CAPTCHA ha coverage 100%. I gate globali repository/frontend restano non rappresentativi sul subset mirato perché includono molto codice legacy non eseguito dalla suite selezionata.

## Sicurezza

Nessun token Cursor/SISTER o password viene stampato. `CURSOR_AUTH_TOKEN_FILE` viene letto dal worker e trasformato in variabile ambiente solo nel subprocess Agent.
