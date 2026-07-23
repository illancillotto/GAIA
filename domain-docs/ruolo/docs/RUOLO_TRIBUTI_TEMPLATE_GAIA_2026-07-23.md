# Template GAIA avviso/sollecito tributi

Aggiornamento del 2026-07-23.

## Scopo

Il template GAIA propone una resa grafica formale per la preview e la stampa degli avvisi/solleciti di pagamento tributi. Il template legacy resta disponibile in parallelo per confronto operativo.

## Asset

Gli asset grafici sono versionati nel modulo `ruolo`:

- `backend/app/modules/ruolo/assets/cbo-logo.png`
- `backend/app/modules/ruolo/assets/pagopa-logo.png`

Il renderer non usa percorsi locali del PC, cartelle `Downloads` o file temporanei per i loghi.

## Layout GAIA

- Pagina 1: intestazione con logo CBO a sinistra e pagoPA a destra, entrambi in riquadro `39mm x 23mm`.
- Pagina 1: titolo avviso su due righe, senza trattino tra numero avviso e oggetto ruoli.
- Pagina 1: riepilogo pagamento, dati ente, destinatario, tabella importi e informativa privacy.
- Pagina 2: comunicazioni amministrative complete derivate dal template originale.
- Pagina 3: dettaglio partitario allegato con font monospace ingrandito e formato raw preservato.

## Vincoli di regressione

- La stampa deve restare A4 e su tre pagine per il campione di prova corrente.
- I loghi devono essere caricati dagli asset interni al progetto.
- Il testo amministrativo non deve essere sintetizzato o rimosso.
- Il partitario deve mantenere spaziatura e allineamenti del formato raw.
