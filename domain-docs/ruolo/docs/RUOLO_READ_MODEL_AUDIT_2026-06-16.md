# Audit Consumatori `ruolo_*` — 2026-06-16

> Stato documento: archivio storico.
> Questo audit fotografa la fase di transizione successiva alla dismissione `.dmp/.pdf`.
> I consumatori runtime correnti vanno letti sul codice attivo e sul PRD Ruolo aggiornato.

## Obiettivo

Mappare i punti del codice che leggono ancora `ruolo_avvisi`, `ruolo_partite`, `ruolo_particelle` dopo la dismissione del flusso `.dmp`, distinguendo tra:

- `ok`: lettura coerente con il nuovo modello `ruolo_*` come read-model storico materializzato da `inCASS`
- `da_adattare`: lettura oggi funzionante ma con semantica o naming da riallineare
- `legacy`: codice nato per il vecchio import file `.dmp/.pdf`, non più da evolvere come percorso principale

## Decisione di riferimento

Decisione già presa:

- `ruolo_*` resta in vita come read-model storico operativo
- la fonte primaria non è più il parser `.dmp`
- la fonte primaria è `ana_payment_notices` + `raw_detail_json.partitario`
- la materializzazione canonica è [materialize_ruolo_from_incass.py](/home/cbo/CursorProjects/GAIA/backend/scripts/materialize_ruolo_from_incass.py)

## Classificazione

### `ok`

Questi consumatori sono coerenti con il nuovo assetto e possono restare su `ruolo_*`.

- [backend/app/modules/ruolo/repositories.py](/home/cbo/CursorProjects/GAIA/backend/app/modules/ruolo/repositories.py)
  - Usa `RuoloAvviso`, `RuoloPartita`, `RuoloParticella` come dataset consultabile del modulo Ruolo.
  - I controlli importi vs Capacitas non leggono più `RuoloAvviso` come fonte economica primaria: usano `ana_payment_notices`.
  - Le viste lista/dettaglio/statistiche ruolo continuano correttamente a leggere il read-model materializzato.

- [backend/app/modules/ruolo/routes/query_routes.py](/home/cbo/CursorProjects/GAIA/backend/app/modules/ruolo/routes/query_routes.py)
  - È solo esposizione API del repository.
  - Non introduce assunzioni `.dmp`.

- [backend/app/modules/catasto/routes/particelle.py](/home/cbo/CursorProjects/GAIA/backend/app/modules/catasto/routes/particelle.py)
  - Usa `RuoloParticella` come storico ruolo di particella.
  - È esattamente il caso d’uso per cui conviene mantenere `ruolo_particelle` materializzata.

- [backend/app/modules/catasto/services/gis_service.py](/home/cbo/CursorProjects/GAIA/backend/app/modules/catasto/services/gis_service.py)
  - Usa `RuoloParticella` per riepilogo popup GIS, fallback storico e aggregazioni ruolo per particella.
  - Dipendenza corretta da mantenere sul read-model.

- [backend/app/modules/catasto/services/ade_status_scan.py](/home/cbo/CursorProjects/GAIA/backend/app/modules/catasto/services/ade_status_scan.py)
  - Usa `RuoloParticella` come backlog operativo delle particelle non collegate.
  - Coerente con lo scopo storico/diagnostico di `ruolo_particelle`.

- [backend/app/modules/wiki/services/ruolo_utenze_read_models.py](/home/cbo/CursorProjects/GAIA/backend/app/modules/wiki/services/ruolo_utenze_read_models.py)
  - Legge `RuoloAvviso` solo come read-model soggetto.
  - Nessuna assunzione su import file.

- [backend/app/modules/utenze/anpr/service.py](/home/cbo/CursorProjects/GAIA/backend/app/modules/utenze/anpr/service.py)
  - Usa `RuoloAvviso.subject_id` per derivare il perimetro “soggetti a ruolo”.
  - Corretto finché `RuoloAvviso` resta il read-model storico dell’annualità.

- [backend/app/modules/elaborazioni/runtime_routes.py](/home/cbo/CursorProjects/GAIA/backend/app/modules/elaborazioni/runtime_routes.py)
  - Stessa logica del perimetro ANPR: usa i soggetti presenti in `RuoloAvviso`.
  - Coerente con il read-model.

- [backend/app/services/elaborazioni_capacitas_incass.py](/home/cbo/CursorProjects/GAIA/backend/app/services/elaborazioni_capacitas_incass.py)
  - Usa `RuoloAvviso.subject_id` per costruire la coda di harvest `inCASS`.
  - Dopo la migrazione 2025, questa dipendenza è coerente.

- [backend/scripts/materialize_ruolo_from_incass.py](/home/cbo/CursorProjects/GAIA/backend/scripts/materialize_ruolo_from_incass.py)
  - È il meccanismo canonico di build del read-model.
  - Da mantenere.

- [backend/scripts/compare_ruolo_incass_partitario.py](/home/cbo/CursorProjects/GAIA/backend/scripts/compare_ruolo_incass_partitario.py)
  - Utile per audit tra read-model e fonte `inCASS`.
  - Coerente con il nuovo assetto.

- [backend/scripts/backfill_ruolo_particelle_from_incass.py](/home/cbo/CursorProjects/GAIA/backend/scripts/backfill_ruolo_particelle_from_incass.py)
  - Script di manutenzione del read-model.
  - Coerente come tooling secondario.

- [backend/scripts/repair_ruolo_catasto_parcels.py](/home/cbo/CursorProjects/GAIA/backend/scripts/repair_ruolo_catasto_parcels.py)
  - Ripara l’aggancio catasto del read-model storico.
  - Coerente con l’architettura target.

- [backend/scripts/backfill_ruolo_company_subjects.py](/home/cbo/CursorProjects/GAIA/backend/scripts/backfill_ruolo_company_subjects.py)
  - Fa solo riallineamento identità su `RuoloAvviso.subject_id`.
  - Ancora utile finché esiste storico da ripulire.

### `da_adattare`

Questi punti funzionano, ma conviene riallinearli per chiarezza o robustezza.

- [backend/app/modules/ruolo/repositories.py](/home/cbo/CursorProjects/GAIA/backend/app/modules/ruolo/repositories.py)
  - `get_stats` e parte delle statistiche continuano a leggere i totali monetari da `RuoloAvviso.importo_totale_*`.
  - Ora quei campi sono alimentati dal materializer `inCASS`, quindi funzionano.
  - Però la semantica del modulo è cambiata: va esplicitato in UI/docs che le stats sono del read-model ruolo, non “import file ruolo”.

- [backend/app/services/elaborazioni_capacitas_incass.py](/home/cbo/CursorProjects/GAIA/backend/app/services/elaborazioni_capacitas_incass.py)
  - `load_incass_ruolo_subject_ids` deriva i soggetti da `RuoloAvviso`.
  - È corretto, ma il naming `ruolo harvest` porta ancora l’eredità del vecchio flusso.
  - Azione consigliata: chiarire in docs e API che il perimetro è il read-model ruolo materializzato.

- [backend/app/modules/utenze/anpr/service.py](/home/cbo/CursorProjects/GAIA/backend/app/modules/utenze/anpr/service.py)
  - Usa `max(RuoloAvviso.anno_tributario)` come “ultimo anno ruolo”.
  - Corretto oggi, ma dipende dal fatto che tutte le annualità rilevanti siano materializzate.
  - Azione consigliata: aggiungere una nozione esplicita di “annualità ruolo attiva/materializzata” se il modulo crescerà.

- [backend/app/modules/elaborazioni/runtime_routes.py](/home/cbo/CursorProjects/GAIA/backend/app/modules/elaborazioni/runtime_routes.py)
  - Stessa osservazione del punto sopra sul calcolo dell’ultimo anno.

### `legacy`

Questi punti appartengono al vecchio percorso import file e non dovrebbero più guidare l’evoluzione del modulo.

- [backend/app/modules/ruolo/services/import_service.py](/home/cbo/CursorProjects/GAIA/backend/app/modules/ruolo/services/import_service.py)
  - È il cuore dell’import `.dmp/.pdf`.
  - Il percorso runtime è già dismesso via API/UI.
  - Da mantenere solo come riferimento temporaneo o da rimuovere in una fase successiva.

- [backend/app/modules/ruolo/services/parser.py](/home/cbo/CursorProjects/GAIA/backend/app/modules/ruolo/services/parser.py)
  - Parser DMP/PDF storico.
  - Non più fonte primaria.
  - Alcune utility di normalizzazione sono ancora riusate; se si vuole eliminare davvero il legacy, vanno estratte in un modulo neutro.

- [backend/app/modules/ruolo/routes/import_routes.py](/home/cbo/CursorProjects/GAIA/backend/app/modules/ruolo/routes/import_routes.py)
  - È già dismesso a `410`.
  - Rimane solo come endpoint legacy esplicitamente spento.

- [frontend/src/app/ruolo/import/page.tsx](/home/cbo/CursorProjects/GAIA/frontend/src/app/ruolo/import/page.tsx)
  - È già una pagina storica/informativa, non un workflow vivo.
  - Fa parte del perimetro legacy da non espandere.

## Conclusioni operative

### Cosa NON fare

- Non droppare `ruolo_avvisi`, `ruolo_partite`, `ruolo_particelle`.
- Non riscrivere `Catasto/GIS` per leggere `ana_payment_notices` direttamente.
- Non riaprire il percorso `.dmp`.

### Cosa fare adesso

1. Trattare `ruolo_*` come read-model stabile materializzato da `inCASS`.
2. Aggiornare naming e docs dove compare ancora “import ruolo” in senso file-based.
3. Estrarre dal parser legacy solo le utility riusate davvero, per poter isolare meglio il codice `.dmp`.
4. Pianificare una seconda fase eventuale di cleanup del perimetro `import_service/parser/import_routes`.

## Checklist sintetica

- `ok` mantenere:
  - `backend/app/modules/ruolo/repositories.py`
  - `backend/app/modules/ruolo/routes/query_routes.py`
  - `backend/app/modules/catasto/routes/particelle.py`
  - `backend/app/modules/catasto/services/gis_service.py`
  - `backend/app/modules/catasto/services/ade_status_scan.py`
  - `backend/app/modules/wiki/services/ruolo_utenze_read_models.py`
  - `backend/app/modules/utenze/anpr/service.py`
  - `backend/app/modules/elaborazioni/runtime_routes.py`
  - `backend/app/services/elaborazioni_capacitas_incass.py`
  - `backend/scripts/materialize_ruolo_from_incass.py`

- `da_adattare`:
  - semantics/naming stats ruolo
  - semantics/naming `ruolo harvest`
  - nozione esplicita di annualità materializzata

- `legacy`:
  - `backend/app/modules/ruolo/services/import_service.py`
  - `backend/app/modules/ruolo/services/parser.py`
  - `backend/app/modules/ruolo/routes/import_routes.py`
  - `frontend/src/app/ruolo/import/page.tsx`
