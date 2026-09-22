# Export XLSM ore.minuti — verifica del 22 settembre 2026

## Comportamento

Per 390 minuti, `Archivio` conserva 6,50 ore decimali mentre `Archivio2`
scrive 6,30 ore.minuti. Il dettaglio di `Giornaliera2` legge ore.minuti;
i totali mensili e le colonne di calcolo restano decimali. La conversione vale
anche per le trasferte numeriche, preservando il marcatore montano `X`.
Quantita, KM, matricole e codici non sono convertiti.

Le somme convertono il dettaglio prima del calcolo: 0,40 + 0,40 corrisponde a
80 minuti, cioe 1,333… ore decimali. Nel compilatore GATE anche il totale del
giorno e convertito in ore.minuti, mantenendo cache coerenti e selezione del
lavoratore. In GAIA restano le formule ore.minuti del modello HR; il totale
trasferte AJ22 converte ogni cella e ignora i marcatori testuali.

## Perimetro GAIA–GATE

Sono aggiornati entrambi i compilatori autonomi. Il builder canonico GAIA
`gate_mobile_payloads._canonical_export_values` continua a emettere minuti
numerici; la route LAN e il job outbound riusano
`gate_mobile_sync.build_presenze_giornaliere_push_payload`.
Nessuna modifica a payload, versioni di sincronizzazione, schema DB o regole
INAZ. Non sono necessari backfill o risincronizzazione per questa conversione.

## Test e copertura

- GATE: `npm run test:coverage`, tutti i quattro workspace: **729 test**.
  **100%** di statement, branch, funzioni e righe nel perimetro gia configurato;
  le esclusioni esistenti non sono state modificate. Il solo compilatore XLSM
  copre **540/540 statement, 378/378 branch, 110/110 funzioni, 464/464 righe**.
  Il file di test XLSM da solo non esercita la preview e alcuni errori API:
  il risultato full-file al 100% include anche i test delle route.
- GAIA: suite `test_presenze_schedule_engine.py`, `test_presenze_xlsm_hours_minutes.py`,
  `test_gate_mobile_sync.py`, `test_operazioni_mobile_sync_api.py`: **157 test**;
  `xlsm_export.py` al **100%**, **321/321 statement e 130/130 branch**, zero
  esclusioni. Non e una dichiarazione di coverage al 100% dell'intero backend.
- GAIA: **17 test** di regressione API export/job con
  `test_presenze_api.py -k 'export or xlsm'`.
- GATE: typecheck e build di tutti i workspace superati; lint dei runtime
  modificati e Ruff dei file Python modificati superati.
- LibreOffice: ricalcolo da formule senza cache del dettaglio GATE, somme,
  trasferte e cambio selettore fra due lavoratori (26 celle); verifica della
  formula GAIA AJ22 con 0,40 + 0,40 + `X` e delle conversioni del modello HR.
  Questo non sostituisce un collaudo interattivo delle macro in Microsoft Excel.
- Copia del file di agosto: 1.476 celle di durata verificate, totali delle otto
  categorie concordanti per tutti i 35 collaboratori; `Archivio`, VBA e le
  altre parti non interessate sono byte-identiche all'originale.

Comando coverage GAIA dalla root (usare un virtualenv con le dipendenze backend):

```bash
PYTHONPATH=backend COVERAGE_FILE=/tmp/gaia-hm.coverage backend/.venv/bin/python -m pytest -c backend/pytest.ini backend/tests/test_presenze_schedule_engine.py backend/tests/test_presenze_xlsm_hours_minutes.py backend/tests/test_gate_mobile_sync.py backend/tests/test_operazioni_mobile_sync_api.py --cov=app.modules.presenze.services.xlsm_export --cov-branch --cov-report=term-missing --cov-fail-under=100
```

## Complessita GAIA e limiti dei gate

La scrittura giornaliera usa un mapping unico delle bande invece di ripetere
azzeramenti e assegnazioni condizionali: valori assenti e codici restano coperti.
Sono rimossi tre controlli irraggiungibili: estremita vuote dopo `strip()` e
split sul delimitatore `" - "`, e assenza di un sabato selezionato dalle chiavi
dello stesso dizionario. I test coprono fallback legacy e soglie 2.279/2.280/2.281
minuti per il riposo, senza fabricare input impossibili per la coverage.

Metriche del file prima/dopo: LOC **583 → 577**, complessita cognitiva
aggregata **275 → 254**, ciclomatica aggregata
**201 → 193**. Nessuna nuova violation error-level.
Il ratchet autorevole contro `3ee0e5ee` resta **non verde** per il solo drift
file-level gia presente: baseline LOC 570, valore iniziale 583 (+13), finale
577 (+7). Il finding e stato riprodotto sul report pre-modifica e si riduce;
non e stato assorbito aggiornando baseline, soglie o esclusioni.
Le modifiche concorrenti del modulo Ruolo sono escluse da questa change.

## Documentazione, mappa e rilascio

Guide operative GATE aggiornate in Markdown, HTML e PDF; contratto Presenze
GAIA aggiornato. Mappe Graphify locali aggiornate con i target dei progetti;
i risultati generati sono ignorati e non vanno committati.
Questa verifica riguarda i checkout locali. Nessun comando di deploy, push,
backfill o sincronizzazione operativa e incluso.
