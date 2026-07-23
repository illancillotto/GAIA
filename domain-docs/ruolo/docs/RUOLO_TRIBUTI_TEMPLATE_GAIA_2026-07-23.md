# Template GAIA avviso/sollecito tributi

Aggiornamento del 2026-07-23.

## Scopo

Il template GAIA propone una resa grafica formale per la preview e la stampa degli avvisi/solleciti di pagamento tributi. Il template legacy resta supportato nel codice, ma non viene esposto nella preview utente.

## Asset

Gli asset grafici sono versionati nel modulo `ruolo`:

- `backend/app/modules/ruolo/assets/cbo-logo.png`
- `backend/app/modules/ruolo/assets/pagopa-logo.png`

Il renderer non usa percorsi locali del PC, cartelle `Downloads` o file temporanei per i loghi.

## Layout GAIA

- Pagina 1: intestazione con logo CBO a sinistra e pagoPA a destra, entrambi in riquadro `39mm x 23mm`.
- Pagina 1: titolo avviso su due righe, senza trattino tra numero avviso e oggetto ruoli.
- Pagina 1: riepilogo pagamento, dati ente, destinatario, tabella importi, informativa privacy e revisione `Rev.2026/01`.
- Pagina 2: comunicazioni amministrative complete derivate dal template originale, con interlinea compatta ma leggibile.
- Pagina 3 e successive: dettaglio partitario allegato con font monospace ingrandito, wrapping controllato e formato raw preservato.

## Vincoli di regressione

- La stampa deve restare A4; il numero pagine può crescere quando il partitario reale è lungo.
- I loghi devono essere caricati dagli asset interni al progetto.
- Il testo amministrativo non deve essere sintetizzato o rimosso.
- Il partitario deve mantenere spaziatura e allineamenti del formato raw.
- Il partitario non deve contenere script o frammenti UI Capacitas come `mstrAvvisoDlgPartitarioKUI`, `btnScaricaPartitarioDlgPartitarioKUI` o `exportExcel.aspx`.
- Il partitario non deve causare scaling globale del PDF: pagina 1 e pagina 2 devono mantenere le dimensioni tipografiche GAIA anche con partitari lunghi.
- La preview utente deve generare solo il template GAIA; il template legacy non deve comparire come tab o opzione visibile.
