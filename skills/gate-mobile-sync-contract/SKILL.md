---
name: gate-mobile-sync-contract
description: Contratto e invarianti degli endpoint mobile-sync che GAIA serve al connector GaTe Mobile. Usala quando tocchi gate_mobile_sync.py, le route mobile_sync, gli schemi operatori/presenze, o quando le Presenze non arrivano su GaTe Mobile.
metadata:
  short-description: GAIA -> GaTe Mobile: non rompere la pipeline
---

# GATE Mobile Sync Contract (lato GAIA)

GAIA e la source of truth di GaTe Mobile. Il connector `gaia-lan-1` gira sulla
LAN GAIA, legge gli endpoint `mobile-sync` e replica il payload **verbatim**
nella cache di GaTe Mobile. Il consumatore non trasforma nulla: se il dato e
sbagliato o vecchio su GATE, e sbagliato o vecchio qui.

## Invariante critica

Il ciclo del connector e **tutto-o-niente**, in quest'ordine:

```
handshake -> catalogs -> mobile-operators -> device-registrations -> worksets -> presenze/*
```

**Il primo endpoint che risponde non-2xx aborta l'intero ciclo.** Un 500 su
`GET /api/mobile-sync/mobile-operators` congela **tutte** le Presenze su GATE
(giornaliere, anomalie, teams, months, rules), non solo gli operatori. Da fuori
sembra "GATE non aggiorna" o "GAIA non manda i dati": in realta e un endpoint
che 500-a.

## Endpoint serviti (contratto)

`backend/app/modules/operazioni/routes/mobile_sync.py`:

| Endpoint | Builder |
|---|---|
| `GET /api/mobile-sync/connector/handshake` | — |
| `GET /api/mobile-sync/catalogs` | `get_mobile_catalogs` |
| `GET /api/mobile-sync/mobile-operators` | `build_mobile_operator_push_payload` (`app/services/gate_mobile_sync.py`) |
| `GET /api/mobile-sync/worksets` | `get_mobile_worksets` |
| `GET /api/mobile-sync/presenze/{rules,months,teams}` | `build_presenze_*_push_payload` |
| `GET /api/mobile-sync/presenze/giornaliere?month=` | `build_presenze_giornaliere_push_payload` |
| `GET /api/mobile-sync/presenze/anomalie?month=` | `build_presenze_anomalie_push_payload` |

Header connector: `X-GAIA-Connector-Token`.

## Trappola `mobile-operators` (fail-hard voluto)

`build_mobile_operator_push_payload` -> per ogni `WCOperator` con email chiama
`required_personnel_area(operator.personnel_area, ...)` che alza `ValueError`
se il valore non e in `{AGRARIO, IMPIANTI}` (quindi anche `NULL`). E un
**500 non gestito** sull'endpoint.

- `wc_operator.personnel_area` e nullable (migration `20260902_1100`) e si
  popola **solo** con `apply_canonical_identity_manifest`
  (`backend/scripts/backfill_presenze_canonical_identities.py`).
- Ogni operatore con email creato o non incluso nel manifest fa 500-are
  l'endpoint -> pipeline GATE congelata.
- Il fail-hard e coperto da un test apposito
  (`backend/tests/test_gate_mobile_sync.py::test_gate_mobile_payloads_reject_missing_or_invalid_personnel_area`):
  **non ammorbidirlo**. Il payload operatori e canonico o niente. Si sistema il
  **dato**, con la skill `gaia-presenze-identity-mapping`.
- Lato GATE `packages/shared` `mobileOperatorPushSchema` richiede
  `personnel_area` non-null: non si puo aggirare mandando `null`.

Diagnosi / fix identita: `skills/gaia-presenze-identity-mapping/SKILL.md`.

## Checklist prima di fare merge

Se tocchi `gate_mobile_sync.py`, le route `mobile_sync`, o la forma di un
payload/enum verso GATE:

1. Un builder non deve poter alzare un'eccezione non gestita su dato di
   produzione plausibile. Se una precondizione manca, decidi esplicitamente:
   escludere la riga (con log) oppure fallire — ma se fallisci, sappi che
   congeli TUTTE le Presenze GATE, non solo quel pezzo.
2. Enum e campi obbligatori devono restare in lockstep con
   `packages/shared` di GaTe Mobile (`mobileOperatorPushSchema`,
   `presenze*SnapshotSchema`). Uno stringimento qui senza il rilascio del
   connector = `GAIA_OPERATOR_SYNC_INVALID` e pipeline ferma.
3. Aggiungi/aggiorna i test in `test_gate_mobile_sync.py` e
   `test_operazioni_mobile_sync_api.py` (coverage 100% runtime, vedi AGENTS.md).
4. Se il campo influenza la classificazione console (stati, `missing_minutes`,
   `special_day`, `absence_cause`, `export_*`), annota il cambiamento: il
   colore/anomalia della cella su GATE dipende da quei campi.

## Verifica end-to-end

Dal repo GaTe Mobile (`/home/cbo/CursorProjects/GaTe-mobile`):

```
.claude/skills/presenze-sync-alignment/scripts/diagnose.sh
```

Isola quale endpoint rompe il ciclo, la freschezza della cache GATE, e il
verdetto. Per un singolo record: `scripts/compare-giornaliera.py`.

## Stop condition

Non ammorbidire il fail-hard di `required_personnel_area`. Non stringere un
enum verso GATE senza coordinare il rilascio del connector. Non dedurre
`personnel_area` da nome/squadra: serve l'attestazione canonica.
