# Esito ripopolamento ruolo 2025 da inCASS

Data esecuzione: 2026-07-03.

Comando finale:

```bash
docker compose exec -T backend python scripts/materialize_ruolo_from_incass.py \
  --from-year 2025 --to-year 2025 --replace-year --reparse-partitario --apply \
  --purge-batch-size 1000
```

## Pre-flight

- Test locali parser: `26 passed`.
- Test Docker parser + ruolo: `49 passed`.
- Backend Docker: healthy.
- Dry-run senza `--apply`: completato in `3m22s`.
- Dry-run: `notices=12348`, `processed=12348`, `without_partite=0`, `errors=0`.

## Backup

Il target `make backup-db-to-nas` e stato interrotto durante la copia locale per evitare
filesystem pieno: il dump completo aveva gia portato il disco al 99%.

Backup usato per il ripopolamento:

```text
/tmp/ruolo_backup_2026-07-03.sql
```

Dimensione: `171M`.

Tabelle incluse:

- `ruolo_avvisi`
- `ruolo_partite`
- `ruolo_particelle`
- `ruolo_import_jobs`

## Esecuzione

Il primo `--apply` con batch purge default `10000` ha incontrato un deadlock dopo il
primo batch committato:

- particelle eliminate prima del deadlock: `10000`
- causa: concorrenza su `catasto_ruolo_autosync_items`, via FK cascade da
  `ruolo_particelle`
- blocker osservato: connessioni idle del backend (`172.21.0.2`)

Ripresa:

- terminate 12 connessioni idle del backend;
- rilanciato lo stesso job con `--purge-batch-size 1000`;
- purge residuo e rebuild completati senza ulteriori errori.

Durata rilancio completo: `44m36s`.

Riepilogo finale script:

```text
anno=2025 notices=12348 processed=12348 purged_avvisi=12348 purged_partite=16420
purged_particelle=90945 purged_jobs=1 without_partite=0 without_payload=0
created_avvisi=12348 created_partite=16420 created_particelle=99848
existing_particelle=2271 errors=0
```

## Numeri Prima/Dopo

| Metrica | Prima | Dopo |
| --- | ---: | ---: |
| Avvisi | 12348 | 12348 |
| Partite | 16420 | 16420 |
| Particelle | 100945 | 99848 |
| Righe con `importo_manut = 1` | 4594 | 646 |
| Totale manut | 9439335509.00 | 109696874.00 |
| Totale irrig | 338875.00 | 51104969.00 |
| Totale ist | 30358365.00 | 79251072.00 |
| Fogli fantasma `2024/2025/2026` | 936 | 0 |

Le 646 righe residue con `importo_manut = 1` sono distribuite su 470 avvisi e non
sono piu l'anomalia massiva del parser precedente.

## Verifiche

- Fogli fantasma da blocchi consumi: `0`.
- Smoke API autenticato: `GET /ruolo/stats?anno=2025` OK, con totali non nulli.
- Linking catastale: `96926` particelle `matched`, `2922` `unmatched`.
- Riconciliazione campione 0648: solo 3 avvisi riconciliati entro `0.50`, tutti da
  contributo minimo `30.00`; sugli avvisi non minimi permangono delta da analizzare
  nella fase di riconciliazione dominio, non nel parser.
- Totali per comune post-run esportati in:
  `/tmp/ruolo_totali_per_comune_2025_post_reparse.csv`.

Top comuni post-run per manut:

| Comune | Manut | Irrig | Ist | Particelle |
| --- | ---: | ---: | ---: | ---: |
| ARBOREA | 23530740.00 | 14809546.00 | 16772678.00 | 4609 |
| ORISTANO | 11552551.00 | 9924708.00 | 8244267.00 | 8740 |
| SAN VERO MILIS | 10829328.00 | 1487344.00 | 7722639.00 | 8806 |
| MARRUBIU | 8608347.00 | 1884329.00 | 6113984.00 | 13723 |
| URAS | 5220990.00 | 666913.00 | 3718884.00 | 8611 |

## Esito

Ripopolamento 2025 completato. Le anomalie parser note sono rientrate: `0668` e
`0985` risultano valorizzati, il totale manut non e piu gonfiato dal parse errato,
e i fogli derivati dagli anni dei blocchi consumi sono azzerati.
