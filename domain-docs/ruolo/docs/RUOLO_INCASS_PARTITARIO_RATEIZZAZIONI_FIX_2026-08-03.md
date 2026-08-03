# Ruolo inCASS - fix partitario con rateizzazioni duplicate

Data: `2026-08-03`

## Caso guida

Soggetto: `PNNPTR47A16L122D` (`PINNA PIETRO`)

Avviso inCASS: `020240001139720`

Anno ruolo: `2024`

La pagina principale Capacitas riporta:

| Tributo | Importo |
| --- | ---: |
| `0648` | `429,41` |
| `0668` | `1.273,37` |
| `0985` | `306,83` |
| Totale carico | `2.009,61` |

Prima della correzione GAIA materializzava:

| Tributo | Importo |
| --- | ---: |
| `0648` | `429,41` |
| `0668` | `821,64` |
| `0985` | `306,83` |
| Totale ruolo GAIA | `1.557,88` |

Delta: `451,73`, tutto sul tributo `0668`.

## Causa

Nel raw del partitario l'avviso contiene piu' righe dello stesso tributo `0668`
nella stessa partita:

```text
2006 0668 ... 270,64 euro
2007 0668 ... 591,91 euro
2008 0668 ... 410,82 euro
```

Il parser precedente assegnava il valore al campo `importo_0668_euro` e lo
sovrascriveva a ogni riga. Restava quindi solo l'ultimo importo: `410,82`.

Lo stesso raw contiene poi una sezione finale:

```text
L'importo totale dell'avviso e' comprensivo di rateizzazioni.
2006 0668 Rateizzazione ... 270,64 euro
2007 0668 Rateizzazione ... 591,91 euro
2008 0668 Rateizzazione ... 410,82 euro
```

Queste righe sono riepilogo duplicato della rateizzazione, non una nuova partita
contabile. Il parser precedente le agganciava alla partita corrente e lasciava
ancora `410,82`.

Risultato errato: `410,82 + 410,82 = 821,64`.

## Correzione

File runtime:

- `backend/app/modules/elaborazioni/capacitas/apps/incass/parsers.py`
- `backend/scripts/materialize_ruolo_from_incass.py`

Regole applicate:

- piu' righe dello stesso tributo nella stessa partita vengono sommate;
- la sezione finale "importo totale dell'avviso comprensivo di rateizzazioni" non
  viene interpretata come tributi di partita;
- la materializzazione confronta il totale partitario con
  `ana_payment_notices.importo_carico`, cioe' il totale Carico della pagina
  principale Capacitas;
- se il confronto non torna, il job incrementa `notice_carico_mismatch`.
- se una particella espone una superficie fuori range per `catasto_parcels`
  (`Numeric(10,4)`), il rebuild salta solo l'upsert/linking catasto della
  particella e continua a materializzare l'avviso ruolo.

Sul raw reale `020240001139720`, il re-parse corretto produce:

```text
000000263/00000: 0668 = 1.273,37
0A1249983/00000: 0648 = 429,41, 0985 = 306,83
Totale = 2.009,61
```

## Policy di quadratura

La fonte primaria per la scomposizione `0648/0668/0985` resta il partitario,
perche' e' la sorgente che espone le partite e le particelle.

La pagina principale Capacitas va usata come guardrail contabile:

- se `sum(partitario 0648+0668+0985) == importo_carico`, il rebuild e' coerente;
- se non torna, il rebuild deve segnalare mismatch e il caso va analizzato;
- non si deve forzare automaticamente la ripartizione per tributo usando solo il
  totale Carico, perche' il totale non contiene la distribuzione per codice.

La griglia tributi della pagina principale e' utile per un confronto per-codice,
ma nel raw dettaglio attualmente salvato e' presente solo la configurazione jqGrid,
non le righe dati. Per usare quella griglia come confronto automatico per-codice,
GAIA deve salvare anche il payload/export della griglia `grdRisTrib`.

## Comandi di verifica

Test mirati:

```bash
python3 -m pytest \
  backend/tests/test_incass_parsers.py \
  backend/tests/elaborazioni/capacitas/test_incass_partitario_parsing.py \
  backend/tests/test_materialize_ruolo_from_incass.py \
  backend/tests/ruolo/test_tributi_api.py \
  backend/tests/ruolo/test_repositories_helpers.py -q
```

Coverage runtime toccati:

```bash
python3 -m pytest \
  backend/tests/test_incass_parsers.py \
  backend/tests/elaborazioni/capacitas/test_incass_partitario_parsing.py \
  backend/tests/test_materialize_ruolo_from_incass.py \
  backend/tests/ruolo/test_tributi_api.py \
  backend/tests/ruolo/test_repositories_helpers.py \
  --cov=app.modules.elaborazioni.capacitas.apps.incass.parsers \
  --cov=scripts.materialize_ruolo_from_incass \
  --cov=app.modules.ruolo.tributi_repositories \
  --cov-report=term-missing:skip-covered \
  --cov-fail-under=100 -q
```

## Ripopolamento dati

Il DB esistente resta errato finche' l'anno non viene ripopolato dal raw:

```bash
python3 backend/scripts/materialize_ruolo_from_incass.py \
  --from-year 2024 --to-year 2024 --replace-year --reparse-partitario

python3 backend/scripts/materialize_ruolo_from_incass.py \
  --from-year 2024 --to-year 2024 --replace-year --reparse-partitario --apply
```

Prima di eseguire `--apply` su ambienti condivisi, fare backup DB e verificare il
dry-run.
