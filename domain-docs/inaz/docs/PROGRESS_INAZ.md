# Progress Inaz

Data aggiornamento: 2026-06-03

## Stato attuale

Implementato un MVP collaboratori/giornaliere coerente con il documento
`IMPLEMENTATION_INAZ_COLLABORATORI_GIORNALIERE.md`.

### Backend

- aggiunto `module_inaz` a `application_users`;
- aggiunte sezioni bootstrap `inaz.*` nel catalogo permessi;
- introdotto vault credenziali `inaz_credentials` con cifratura via `CREDENTIAL_MASTER_KEY`;
- introdotto data model collaboratori-centrico:
  - `inaz_collaborators`
  - `inaz_daily_records`
  - `inaz_daily_punches`
  - `inaz_event_summaries`
  - `inaz_import_jobs`
- introdotto modello calendari/template orari:
  - `inaz_holidays`
  - `inaz_schedule_templates`
  - `inaz_schedule_rules`
  - `inaz_collaborator_schedule_assignments`
- import JSON compatibile con l'output dello scraper `inaz-collaboratori`;
- import JSON che normalizza e persiste anche i campi ricchi del dettaglio giorno Inaz:
  - orario programmato/effettivo
  - fasce orarie
  - ore teoriche / ore assenza
  - riepilogo giornata
  - totali giornata
  - richieste / anomalie;
- mapping collaboratore -> `application_users`;
- endpoint calendario collaboratore;
- endpoint riepilogo eventi collaboratore;
- endpoint elenco giornaliere;
- endpoint admin per bootstrap festivita locali/mobili e assegnazione template orari ai collaboratori;
- export `.xlsm` dal DB con preservazione macro via `openpyxl(..., keep_vba=True)`.
- classificazione export `.xlsm` non piu solo `sabato/domenica`: adesso usa festivita, sabati alternati, primo sabato del mese e rientri stagionali se presenti nei template.
- precedenza logica classificazione giornaliera:
  - `detail` Inaz se presente e strutturato;
  - fallback su valori importati dalla griglia/cartellino;
  - fallback finale su template orari GAIA.

### Frontend

- dashboard `/inaz`;
- pagina `/inaz/settings` per gestione credenziali Inaz;
- lista `/inaz/collaboratori`;
- dettaglio `/inaz/collaboratori/[id]` con:
  - cartellino periodo;
  - riepilogo eventi;
  - mapping verso utente GAIA per admin;
- pagina `/inaz/giornaliere`;
- pagina `/inaz/giornaliere` con dettaglio operativo della singola giornata:
  - orario Inaz;
  - stato giornata;
  - riepilogo e totali;
  - richieste e anomalie;
- pagina `/inaz/import` con preview e conferma import;
- pagina `/inaz/export` con download `.xlsm`;
- pagina `/inaz/export` con preview dataset del mese, perimetro collaboratori e KPI di righe/giorni speciali;
- pagina `/inaz/sync` con avvio job live, polling stato, retry e storico run;
- navigazione modulo aggiornata in sidebar e module switcher.

### Sync live

- introdotta tabella `inaz_sync_jobs` per orchestrare le run live;
- aggiunto worker Python separato avviato fuori dal processo FastAPI;
- integrazione con lo scraper esterno `inaz-scraper` tramite worker dedicato;
- login automatico con credenziali cifrate selezionate dal vault `Inaz`;
- ogni run live produce artefatto JSON persistito su filesystem e poi riusa il normale import GAIA;
- retry applicativo disponibile fino al limite configurato;
- cancel e delete dei job falliti/storici disponibili da UI.

### Test e verifica

- aggiornati test backend `backend/tests/test_inaz_api.py` sul nuovo flusso collaboratori JSON/XLSM;
- aggiunti test unitari backend `backend/tests/test_inaz_schedule_engine.py` per:
  - Martedi della Sartiglia e Pasquetta;
  - sabato alternato operai catasto;
  - rientro del lunedi stagionale;
  - scrittura corretta delle colonne speciali in `Archivio2`;
- aggiunti test per la precedenza `detail Inaz > template fallback`;
- aggiunti test frontend iniziali `frontend/tests/unit/inaz-pages.test.tsx`;
- typecheck frontend completato con successo;
- verifica smoke backend eseguita su parser JSON e compilazione XLSM.

## Gap aperti

- UI frontend ancora essenziale:
  - niente calendario visuale mensile dedicato;
  - niente preview differenziale/import duplicati avanzata;
  - niente selector template assistito lato filesystem;
- manca ancora la UI dedicata per gestione festivita/template orari e assegnazioni collaboratore;
- sync live ancora minimale:
  - nessuna policy di retry automatica schedulata;
  - nessuna orchestrazione multi-worker o schedulazione periodica;
- resta solo un warning non bloccante nei test export `openpyxl/zipfile`;
- test end-to-end con credenziali reali e run live su mese completo ancora da consolidare come procedura operativa.

## Prossimi passi consigliati

1. calendario mensile dedicato nel dettaglio collaboratore;
2. gestione UI festivita/template orari/assegnazioni;
3. preview differenziale import e duplicate handling piu ricco;
4. preset template export e selector filesystem assistito;
5. run end-to-end documentata su credenziale reale e validazione `.xlsm` su mese completo.
