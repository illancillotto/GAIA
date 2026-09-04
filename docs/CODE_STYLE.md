# GAIA Code Style

Data di adozione: `2026-09-02`

Questa e la policy di stile del repository. Non sostituisce coverage, complexity
ratchet o architettura: governa formattazione, lint e convenzioni di scrittura.

Fonti autorevoli:

- questo documento
- `.editorconfig`
- `ruff.toml`
- `frontend/.eslintrc.json`

## Principi

- Nessuna riformattazione di massa del codice legacy.
- Il debito di stile esistente puo restare, ma il perimetro toccato non puo
  introdurre nuovo debito rispetto alle regole sotto.
- `noqa`, `ruff: noqa` e `eslint-disable` sono ammessi solo con commento di
  motivazione sulla stessa riga o sulla riga precedente.
- Lo stile non giustifica cambi di comportamento, API, schema dati o UI.

## Perimetro Python

File `.py` sotto:

- `backend/app/`
- `backend/tests/`
- `backend/alembic/` escluso `backend/alembic/versions/`
- `modules/elaborazioni/worker/`
- `scripts/`
- `tools/`
- `tests/code_quality/`

Le revisioni Alembic restano fuori dal gate: non vanno riformattate per
allineamento stilistico.

## Python

- Linguaggio: Python 3.11.
- Formatter e linter: Ruff `0.16.0`, configurazione esplicita in `ruff.toml`.
- Indentazione: 4 spazi.
- Lunghezza riga: 100 caratteri, applicata dal formatter sui file nuovi. `E501`
  non e un errore di lint, per non duplicare il wrapping.
- Import: ordinati da Ruff isort; first-party `app`.
- Quote del formatter: doppie, solo sui file Python **nuovi**.
- FastAPI: `B008` e ignorato perche `Depends()` / `Query()` nei default e
  idiomatico.
- Modelli: `RUF012` e ignorato perche default mutabili di classe sono comuni su
  SQLAlchemy/Pydantic.

Il default evolutivo di Ruff non e la policy GAIA. `ruff.toml` deve tenere
`select` e `ignore` espliciti.

### Date nei test

Un test che semina dati dentro una finestra temporale relativa a oggi non deve
usare una data fissa: passa il tempo e il dato esce dalla finestra, il test
fallisce mesi dopo e la causa non ha niente a che vedere con l'ultima modifica.
Le date vanno ancorate a `date.today()` con lo scostamento che serve.

Vale per le analytics con finestra a `90` giorni, per i nomi file derivati dal
periodo esportato (`build_straordinari_filename`) e per le ricerche con budget
di chiamate come l'inferenza data decesso ANPR, dove la data fissa fa crescere
lo spazio di ricerca fino a esaurire il budget.

### Ratchet Python

Stesso modello della coverage sui file cambiati:

- file **modificati** nel perimetro: `ruff check` deve essere verde sul file
- file **aggiunti** (incluso untracked in locale): `ruff check` e
  `ruff format --check`
- file non toccati: nessun obbligo di pulizia

Toccando un file si sistemano le violation Ruff di quel file, senza
riformattare il resto del modulo o dell'albero.

## Frontend

- TypeScript / React / Next.js App Router.
- Indentazione: 2 spazi.
- Linter: `next lint` con `next/core-web-vitals` e `next/typescript`.
- Prettier non e adottato. Non introdurre un format-on-save di massa.
- Convenzioni UI di piattaforma restano in `docs/ARCHITECTURE.md`.

## Altri file

`.editorconfig` resta il minimo comune:

- UTF-8, newline LF, newline finale, trim degli spazi finali
- indent 2 spazi, 4 per `.py`, tab per `Makefile`

`git diff --check` resta valido come controllo whitespace.

## Comandi

Il Python del Make deve avere Ruff installato (`backend/requirements.txt`).
Esempio locale: `make lint-backend QUALITY_PYTHON=backend/.venv/bin/python`.

| Comando | Scopo |
| --- | --- |
| `make lint` | sintassi Python, ratchet Ruff, ESLint frontend |
| `make lint-backend` | `compileall` e ratchet Ruff contro `BASE_REF` (default `origin/main`) |
| `make style-ratchet` | solo il ratchet Ruff sui file Python toccati |
| `make lint-backend-all` | `ruff check` sull'intero perimetro; diagnostico, non e il gate CI |
| `make format-backend` | `ruff format` sull'intero perimetro; non eseguirlo per allineare il legacy |
| `make lint-frontend` | `next lint` |

CI backend esegue il ratchet con `--base-sha` / `--head-sha` sullo stesso
perimetro. I test del gate vivono in `tests/code_quality/test_python_style_gate.py`.

## Relazione con gli altri programmi

| Programma | Documento | Ruolo |
| --- | --- | --- |
| Stile | questo file | lint, formatter, convenzioni di scrittura |
| Coverage | `docs/TEST_COVERAGE_100_PLAN.md` | `100%` sui file runtime toccati |
| Complessita | `docs/code-quality/` | ratchet di ciclomatica/cognitiva |

I tre gate sono indipendenti: uno verde non assolve gli altri.

## Copertura dei requisiti

| Requisito | Dove vive | Come si verifica |
| --- | --- | --- |
| Policy di stile unica | questo file | review documentale |
| Config Python esplicita, niente default Ruff | `ruff.toml` | `ruff check --show-settings` dal repo root |
| Ratchet sui file Python toccati | `scripts/check_changed_python_style.py` | `make lint-backend` / CI backend |
| File nuovi anche formattati | stesso script, `ruff format --check` | CI e untracked locale |
| Nessun format di massa del legacy | principi di questo file | review del diff |
| Test del gate | `tests/code_quality/test_python_style_gate.py` | `make quality-test` |
| Lint frontend | `frontend/.eslintrc.json` | `make lint-frontend` |
| Convenzioni minime editor | `.editorconfig` | `git diff --check` |
| Routing per agenti | `AGENTS.md`, `docs/AGENTS.md` | change di stile aggiorna questo file |
