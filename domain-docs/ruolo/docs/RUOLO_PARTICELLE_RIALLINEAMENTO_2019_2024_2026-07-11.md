# Riallineamento `ruolo_particelle` 2019-2024

Data operativa: 2026-07-10 / 2026-07-11

## Obiettivo

Riallineare locale e server CED per le particelle del Ruolo 2019-2024 usando la logica aggiornata del parser/materializzatore inCASS.

La modalità corretta è:

```bash
docker compose run --rm --no-deps backend python scripts/materialize_ruolo_from_incass.py \
  --from-year 2019 --to-year 2024 \
  --replace-year --reparse-partitario \
  --apply --commit-every 1 --purge-batch-size 2000
```

## Backup

Prima dell'apply sono stati creati backup mirati delle tabelle realmente impattate:

- `ruolo_avvisi`
- `ruolo_partite`
- `ruolo_particelle`
- `ruolo_import_jobs`
- `catasto_parcels`

Backup locale:

```text
backups/db/gaia-20260710-205024-pre-ruolo-2019-2024-reparse-targeted.dump
```

Backup server CED:

```text
/opt/gaia/backups/db/gaia-20260710-235349-pre-ruolo-2019-2024-reparse-targeted.dump
```

Nota: un dump completo locale era stato avviato ma interrotto prima di qualunque apply perche stava serializzando payload molto grandi da `ana_payment_notices`. Quella tabella è sorgente letta dal materializzatore, non una tabella modificata dall'operazione.

## Esito conteggi

Conteggi finali identici su locale e server CED:

| Anno | `ruolo_particelle` |
|------|--------------------|
| 2019 | 17065 |
| 2020 | 20226 |
| 2021 | 24390 |
| 2022 | 93540 |
| 2023 | 95062 |
| 2024 | 96684 |

## Verifiche qualità

Query di verifica:

```sql
SELECT anno_tributario,
       count(*) FILTER (WHERE sup_irrigata_ha > 1000) AS over_1000,
       max(sup_irrigata_ha) AS max_irr,
       count(*) FILTER (WHERE coltura IS NULL) AS coltura_null,
       count(*) FILTER (WHERE distretto IS NULL OR distretto IN ('0','2019')) AS bad_distretto
FROM ruolo_particelle
WHERE anno_tributario BETWEEN 2019 AND 2024
GROUP BY anno_tributario
ORDER BY anno_tributario;
```

Esito locale e server CED:

| Anno | `over_1000` | `max_irr` | `coltura_null` | `bad_distretto` |
|------|-------------|-----------|----------------|-----------------|
| 2019 | 0 | 15.1280 | 0 | 0 |
| 2020 | 0 | 18.0000 | 0 | 0 |
| 2021 | 0 | 18.0000 | 0 | 0 |
| 2022 | 0 | 48.3500 | 70607 | 0 |
| 2023 | 0 | 52.6500 | 73352 | 0 |
| 2024 | 0 | 49.7000 | 77121 | 0 |

`coltura_null` resta presente su 2022-2024 per assenza del dato nel payload sorgente, non per errore di materializzazione.

## Riepilogo annuale apply

| Anno | Notice | Processati | Senza partite | Errori notice | Particelle create |
|------|--------|------------|---------------|---------------|-------------------|
| 2019 | 9642 | 9633 | 0 | 9 | 17337 |
| 2020 | 10012 | 9884 | 120 | 8 | 20605 |
| 2021 | 11694 | 10312 | 1381 | 1 | 24391 |
| 2022 | 10987 | 10644 | 342 | 1 | 93541 |
| 2023 | 11269 | 11191 | 77 | 1 | 95063 |
| 2024 | 11877 | 11876 | 0 | 1 | 96686 |

I conteggi `created_particelle` possono essere maggiori dei conteggi finali perche il materializzatore conta anche duplicati già presenti nella chiave di lavoro durante la scansione (`existing_particelle`).

## Stato servizi

Dopo l'apply:

- servizi locali fermati prima dell'operazione e riavviati a fine verifica;
- servizi server CED fermati prima dell'operazione e riavviati a fine verifica;
- backend server verificato `healthy`;
- log server con risposta `/health` HTTP 200.

## Test e coverage

Test mirato materializzatore:

```bash
docker compose exec -T backend python -m pytest tests/test_materialize_ruolo_from_incass.py
```

Esito:

```text
27 passed
```

Test regressivi Ruolo eseguiti dopo l'aggiornamento documentale e dei test:

```bash
docker compose exec -T backend python -m pytest \
  tests/test_materialize_ruolo_from_incass.py \
  tests/ruolo \
  tests/test_ruolo_module_migration.py \
  tests/test_catasto_indici_ruolo_esclusi.py
```

Esito:

```text
55 passed
```

Coverage mirata sullo script:

```bash
docker compose exec -T backend python -m pytest tests/test_materialize_ruolo_from_incass.py \
  --cov=scripts.materialize_ruolo_from_incass \
  --cov-report=term-missing \
  --cov-report=json:coverage-materialize-ruolo.json \
  --cov-fail-under=0
```

Esito:

```text
scripts/materialize_ruolo_from_incass.py: 100%
```

Coverage mirata aggregata su `app/modules/ruolo` e `scripts.materialize_ruolo_from_incass`, misurata prima della richiesta di portare il materializzatore al 100%:

```text
TOTAL: 74%
```

La copertura del materializzatore è ora al 100%. Restano fuori dal gate 100% i file storici del modulo `app/modules/ruolo` non modificati da questa operazione, che richiedono una campagna separata se si vuole portare l'intero modulo Ruolo al 100%.
