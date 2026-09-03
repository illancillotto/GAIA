# Snapshot GATE Presenze: Giornaliere

## Endpoint e trasporto

GAIA espone lo snapshot mensile delle giornaliere al connector con:

```text
GET /api/mobile-sync/presenze/giornaliere?month=YYYY-MM
```

L'alias compatibile `GET /api/mobile-sync/presenze/giornaliere/snapshot` ha lo
stesso payload. Durante una sincronizzazione pianificata, GAIA invia il
medesimo payload al connector con:

```text
POST /api/mobile/connector/presenze/giornaliere/snapshot
```

Lo snapshot include anche i mesi storici richiesti dal connector quando le
giornaliere INAZ sono presenti in GAIA.

## Timbrature di dettaglio

Ogni elemento in `records` e `giornaliere` mantiene i campi esistenti e
aggiunge `detail_punch_rows`:

```json
{
  "record_id": "...",
  "work_date": "2026-08-10",
  "has_complete_punches": true,
  "detail_punch_rows": [
    {
      "entry_time": "08:05",
      "exit_time": "12:00",
      "terminal_label": "Sede"
    },
    {
      "entry_time": "12:30",
      "exit_time": "16:35",
      "terminal_label": "Sede"
    }
  ]
}
```

- Le righe sono ordinate cronologicamente sull'orario disponibile; a parita
  prevale la sequenza INAZ persistita da GAIA.
- `entry_time` e `exit_time` sono orari locali Europe/Rome, nel formato
  `HH:mm`.
- Ogni riga contiene entrambi i campi; il lato non disponibile e `null`, senza
  valori inventati.
- `terminal_label` e opzionale e descrive il terminale/origine quando INAZ lo
  fornisce.
- In assenza di timbrature `detail_punch_rows` e `[]`.
- `has_complete_punches` resta invariato ed e `true` soltanto quando esiste
  almeno una riga e tutte le sue coppie entrata/uscita sono complete.

Il connector deve trattare `record_id` come identita stabile della giornata e
sostituire lo snapshot di quel record in modo idempotente: il refresh di un
mese non deve accumulare righe di timbratura duplicate.
