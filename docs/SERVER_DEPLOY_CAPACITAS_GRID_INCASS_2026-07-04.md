# Server Deploy Runbook — Capacitas Grid 2026 + inCass Parser

Data: `2026-07-04`

Obiettivo:

- portare su server i commit:
  - `d121809` `Stabilize Capacitas consorzio grid import`
  - `e0d20a9` `Fix inCass partitario parsing and reparse docs`
- eseguire in sicurezza l'import controllato del file Excel Capacitas `catasto consortile` 2026
- deployare il fix parser `inCass`
- non lanciare reparse/materialization massiva `inCass` senza approvazione esplicita

Vincoli operativi:

- `cat_particelle` non deve essere modificata
- l'import Excel deve scrivere solo su:
  - `cat_consorzio_units`
  - `cat_consorzio_occupancies`
  - `cat_capacitas_grid_snapshots`
  - `cat_capacitas_grid_rows`
- prima di qualsiasi `--apply` fare backup DB
- se il deploy server usa questo repository, non includere altre modifiche sporche non collegate

## 1. Allineamento codice

Nel path del repository server:

```bash
git status --short
git log --oneline -n 5
```

Portare i commit validati:

```bash
git fetch --all --tags
git cherry-pick d121809
git cherry-pick e0d20a9
```

Se i commit sono già presenti nel branch server:

```bash
git log --oneline --decorate -n 10
```

Verificare che i commit attesi compaiano:

- `d121809 Stabilize Capacitas consorzio grid import`
- `e0d20a9 Fix inCass partitario parsing and reparse docs`

## 2. Migration DB

Migration attesa:

- `20260704_0900_capacitas_grid_snapshot.py`

Verifica:

```bash
cd backend
alembic current
alembic heads
```

Se il DB non è già a head:

```bash
alembic upgrade head
```

## 3. Test minimi obbligatori

Eseguire nel repository server:

```bash
cd backend
python3 -m pytest tests/test_capacitas_consorzio_grid_import.py -q
python3 -m pytest tests/test_incass_parsers.py tests/elaborazioni/capacitas/test_incass_partitario_parsing.py -q
```

Se il runtime server gira via container e i test vanno eseguiti nel container:

```bash
docker compose exec -T backend python -m pytest tests/test_capacitas_consorzio_grid_import.py -q
docker compose exec -T backend python -m pytest tests/test_incass_parsers.py tests/elaborazioni/capacitas/test_incass_partitario_parsing.py -q
```

## 4. Backup DB prima dell'import Excel

Eseguire backup completo del database prima di qualunque `--apply`.

Il comando dipende dall'infrastruttura server. Esempio PostgreSQL:

```bash
pg_dump "$DATABASE_URL" > /path/to/backup/gaia_pre_capacitas_grid_2026_$(date +%Y%m%d_%H%M%S).sql
```

Se il DB gira in container, usare la procedura standard del server. Non proseguire con `--apply` senza backup riuscito.

## 5. Prerequisito file Excel

Rendere disponibile sul server il file reale, per esempio:

```bash
/path/to/uploads/ct0902026_grid.xlsx
```

Verifica:

```bash
ls -lh /path/to/uploads/ct0902026_grid.xlsx
```

## 6. Dry-run import Capacitas grid 2026

Prima verificare che non esistano processi import attivi:

```bash
docker compose exec -T backend pgrep -af import_capacitas_consorzio_grid.py
```

Dry-run:

```bash
docker compose exec -T backend python scripts/import_capacitas_consorzio_grid.py \
  --xlsx-path '/path/to/uploads/ct0902026_grid.xlsx' \
  --snapshot-year 2026 \
  --source-file 'ct0902026_grid.xlsx' \
  --output-dir /tmp/gaia_capacitas_grid_import_server \
  --dry-run
```

Verifiche attese:

- il comando termina senza errori
- `cat_particelle_unchanged=True`
- il summary JSON viene prodotto in `/tmp/gaia_capacitas_grid_import_server/`

Controllare anche il summary completo:

```bash
docker compose exec -T backend python - <<'PY'
import json
from pathlib import Path
path = Path('/tmp/gaia_capacitas_grid_import_server/capacitas_grid_2026_dry-run_summary.json')
summary = json.loads(path.read_text())
print(summary["mode"])
print(summary["cat_particelle_unchanged"])
print(summary["counters"])
PY
```

## 7. Apply import Capacitas grid 2026

Solo dopo validazione del dry-run:

```bash
docker compose exec -T backend python scripts/import_capacitas_consorzio_grid.py \
  --xlsx-path '/path/to/uploads/ct0902026_grid.xlsx' \
  --snapshot-year 2026 \
  --source-file 'ct0902026_grid.xlsx' \
  --output-dir /tmp/gaia_capacitas_grid_import_server \
  --apply
```

Verificare:

- `cat_particelle_unchanged=True`
- il summary `apply` è stato generato

## 8. Secondo apply per idempotenza piena

Rilanciare subito lo stesso comando:

```bash
docker compose exec -T backend python scripts/import_capacitas_consorzio_grid.py \
  --xlsx-path '/path/to/uploads/ct0902026_grid.xlsx' \
  --snapshot-year 2026 \
  --source-file 'ct0902026_grid.xlsx' \
  --output-dir /tmp/gaia_capacitas_grid_import_server_idempotency \
  --apply
```

Conferme obbligatorie sul secondo apply:

- `unit_action_created=0`
- `occupancy_created=0`
- `cat_particelle_unchanged=True`

Verifica esplicita del summary:

```bash
docker compose exec -T backend python - <<'PY'
import json
from pathlib import Path
path = Path('/tmp/gaia_capacitas_grid_import_server_idempotency/capacitas_grid_2026_apply_summary.json')
summary = json.loads(path.read_text())
print("cat_particelle_unchanged", summary["cat_particelle_unchanged"])
print("occupancy_created", summary["counters"].get("occupancy_created", 0))
print("raw_rows_inserted", summary["counters"].get("raw_rows_inserted", 0))
print("unit_action_unit_created", summary["counters"].get("unit_action_unit_created", 0))
PY
```

La validazione è positiva solo se:

- `cat_particelle_unchanged=True`
- `occupancy_created=0`
- `raw_rows_inserted=0`
- `unit_action_unit_created=0`

## 9. Deploy fix parser `inCass`

Il deploy codice del parser è coperto dai commit sopra. Non richiede azioni dati immediate.

Il reparse/materialization massiva non va eseguito automaticamente.

Comando disponibile, ma da eseguire solo dopo approvazione esplicita:

```bash
docker compose stop backend elaborazioni-worker-autodoc elaborazioni-worker-runtime \
  elaborazioni-worker-visure presenze-worker

docker compose run --rm --no-deps backend python scripts/materialize_ruolo_from_incass.py \
  --from-year 2025 --to-year 2025 --replace-year --reparse-partitario --apply \
  --commit-every 1 --purge-batch-size 2000

docker compose up -d backend elaborazioni-worker-autodoc elaborazioni-worker-runtime \
  elaborazioni-worker-visure presenze-worker
```

Nota:

- questo comando riallinea i dati storici `ruolo` derivati da `inCass`
- prima di eseguirlo serve una finestra operativa definita e una stima impatto condivisa
- il purge va eseguito con i servizi applicativi fermi per evitare deadlock su
  `catasto_ruolo_autosync_items`
- dopo il fix 2026-07-09 verificare che su `ruolo_particelle` 2025 `over_1000=0`,
  `eq_are=0` e `max(sup_irrigata_ha)=49.7000`

## 10. Graphify

Se il server o l'ambiente operativo prevede aggiornamento Graphify:

```bash
make graphify-catasto-code
```

Solo se la key funziona:

```bash
make graphify-patch-openai-base-url
make graphify-catasto-docs
```

Se `graphify-catasto-docs` si blocca o fallisce lato OpenAI/codex-lb, segnalarlo ma non bloccare il deploy.

## 11. Report finale da produrre

Al termine riportare:

- esito deploy codice
- esito migration
- esito test
- esito dry-run
- esito primo apply
- esito secondo apply idempotenza
- conferma:
  - `cat_particelle_unchanged=True`
  - `occupancy_created=0`
  - `raw_rows_inserted=0`
- stato parser `inCass` deployato
- conferma che il reparse massivo `inCass` non è stato eseguito, salvo approvazione esplicita

## 12. Esito esecuzione reale del 4 luglio 2026

Deploy server completato:

- patch applicate sul server per:
  - import Capacitas grid 2026
  - fix parser `inCass` partitario
- backend inizialmente bloccato da chain Alembic incompleta
- migration aggiunte sul server per sbloccare l'entrypoint:
  - `20260703_1000_catasto_ade_alignment_audit.py`
  - `20260703_1900_presenze_operai_rule_configs.py`
- dopo rebuild:
  - `docker compose exec -T backend alembic current` -> `20260704_0900 (head)`
  - backend `healthy`

Test server eseguiti con esito verde:

```bash
docker compose exec -T backend python -m pytest tests/test_capacitas_consorzio_grid_import.py -q
docker compose exec -T backend python -m pytest tests/test_incass_parsers.py tests/elaborazioni/capacitas/test_incass_partitario_parsing.py -q
```

File Excel reale usato sul server:

- host: `/opt/gaia/runtime-data/imports/ct0902026_grid.xlsx`
- container: `/runtime-data/imports/ct0902026_grid.xlsx`

Backup DB completato prima del primo apply:

- `/opt/gaia/backups/db/gaia-20260704-141119-pre-capacitas-grid-20260704.dump`

Dry-run server eseguito:

- `rows_total=186017`
- `unit_action_unit_created=151251`
- `unit_action_unit_existing_exact=34025`
- `unit_resolution_unit_swapped_arborea_terralba=1296`
- `occupancy_created=34754`
- `raw_rows_inserted=0`
- `cat_particelle_unchanged=True`

Primo apply server eseguito:

- `rows_total=186017`
- `unit_action_unit_created=131807`
- `unit_action_unit_existing_exact=53311`
- `unit_resolution_unit_swapped_arborea_terralba=1296`
- `occupancy_created=159732`
- `occupancy_existing_current=26246`
- `raw_rows_inserted=186017`
- `cat_particelle_unchanged=True`

Secondo apply server eseguito per idempotenza:

- `rows_total=186017`
- `unit_action_unit_created=0`
- `unit_action_unit_existing_exact=184716`
- `unit_resolution_unit_swapped_arborea_terralba=1296`
- `occupancy_created=0`
- `occupancy_existing_current=185978`
- `raw_rows_inserted=0`
- `cat_particelle_unchanged=True`

Conferme finali:

- `cat_particelle` non e stata modificata
- l'import server e idempotente sul file reale 2026
- il parser `inCass` corretto e stato deployato
- non e stato eseguito alcun reparse massivo `inCass`

Verifica coverage locale del 6 luglio 2026:

```bash
cd backend
coverage erase
coverage run --rcfile=/dev/null -m pytest tests/test_capacitas_consorzio_grid_import.py -q
coverage report --rcfile=/dev/null --include='app/services/capacitas_consorzio_grid_import.py,scripts/import_capacitas_consorzio_grid.py,tests/test_capacitas_consorzio_grid_import.py'
```

Esito:

- `app/services/capacitas_consorzio_grid_import.py` -> `100%`
- `scripts/import_capacitas_consorzio_grid.py` -> `100%`
