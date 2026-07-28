# Template GAIA avviso/sollecito tributi

Aggiornamento del 2026-07-27.

## Scopo

Il template GAIA propone una resa grafica formale per la preview e la stampa degli avvisi/solleciti di pagamento tributi. Dal 2026-07-27 e il default operativo sia per l'azione rapida `Avviso sollecito` sia per il wizard batch `Genera PDF nel NAS`.

Il template legacy `Avviso_Sollecito_Template.docx` resta supportato nel codice solo se viene passato un `template_path` esplicito, ma non viene esposto nella preview utente e non e piu il fallback del batch quando il frontend non specifica un template.

## Asset

Gli asset grafici sono versionati nel modulo `ruolo`:

- `backend/app/modules/ruolo/assets/cbo-logo.png`
- `backend/app/modules/ruolo/assets/pagopa-logo.png`
- `backend/app/modules/ruolo/assets/bollo-ufficio-postale.png`

Il renderer non usa percorsi locali del PC, cartelle `Downloads` o file temporanei per i loghi.

## Layout GAIA

- Pagina 1: intestazione con logo CBO a sinistra e pagoPA a destra, entrambi in riquadro `39mm x 23mm`.
- Pagina 1: titolo avviso su due righe, senza trattino tra numero avviso e oggetto ruoli.
- Pagina 1: riepilogo pagamento, dati ente, destinatario, tabella importi, informativa privacy e revisione `Rev.2026/01`.
- Pagina 2: comunicazioni amministrative complete derivate dal template originale, con interlinea compatta ma leggibile.
- Pagina 3: bollettino postale TD 896 precompilato in A4 verticale con contenuto ruotato, allineato al formato Crystal Reports di riferimento e inserito prima del partitario.
- Pagina 4 e successive: dettaglio partitario allegato con font monospace ingrandito, wrapping controllato e formato raw preservato.

## Bollettino TD 896

La pagina bollettino usa i dati dell'avviso GAIA: numero avviso, codice fiscale, denominazione contribuente, importo saldo, scadenza, esercizio e anni di riferimento. La causale stampata nei riquadri del bollettino usa il codice a tre cifre derivato dal numero avviso, con override possibile tramite payload dedicato; la causale bonifico resta invece nel formato completo `A <numero avviso> CF <codice fiscale>`.

Il layout recepisce le misure principali del modello CH8/Bis TD 896 indicate nei manuali Poste forniti localmente:

- bollettino standard `297mm x 102mm`;
- ricevuta di versamento `132mm`;
- ricevuta di accredito `165mm`;
- zona di codifica OCR/codeline alta `19mm`;
- IBAN in 27 caselle sulla stessa riga, con ABI Poste `07601`;
- barcode su ricevuta di accredito a circa `64mm` dal bordo superiore, largo `93mm` e alto `12mm`;
- bollo/Data Matrix su ricevuta di versamento tramite asset PNG del modulo, posizionato nella zona inferiore del riquadro.

Per la stampa PDF con Chromium il renderer usa due job separati: avviso/comunicazioni/bollettino
in un PDF principale e partitario in un PDF dedicato, poi unisce i documenti con `pypdf`. Questa
separazione evita che un partitario reale molto lungo faccia scattare lo shrink-to-fit di Chromium
sulla pagina bollettino.

Il bollettino viene renderizzato con un wrapper A4 portrait `210mm x 297mm` e un canvas interno
landscape `297mm x 210mm` assoluto, ruotato di `-90deg` e scalato a `.968`. Il canvas e traslato
verticalmente per mantenere il margine visivo del riferimento `/tmp/gaia_sollecito_bollettino_896_prova.pdf`
anche con importi a sei cifre e denominazioni societarie lunghe.

Valori fissi configurati nel renderer:

- conto corrente postale `1007214826`;
- IBAN `IT15L0760117400001007214826`;
- intestazione `CONSORZIO DI BONIFICA DELL'ORISTANESE - RISCOSSIONE QUOTE ASSOCIATIVE`;
- tipo documento `896`.

La codeline viene costruita con codice cliente a 18 cifre: 16 cifre base derivate dal numero avviso e controcodice modulo 93 sulle prime 16 cifre. L'importo in codeline usa il formato Poste `00000000+00` e il conto corrente viene normalizzato a 12 cifre.

Il payload del barcode Code 128-C usa la struttura a 50 cifre prevista dal manuale: `18` + codice cliente a 18 cifre + `12` + conto corrente a 12 cifre + `10` + importo a 10 cifre senza separatore + `3` + tipo documento `896`. Il renderer genera un SVG Code 128-C con checksum modulo 103.

Nota operativa: la pagina rende un facsimile precompilato per stampa e pagamento manuale/online tramite dati, codeline e barcode. La piena omologazione di stampa in proprio Poste richiede verifica specialistica di posizionamenti OCR e Data Matrix secondo le specifiche ufficiali.

Il bollo `BOLLO DELL'UFFICIO POSTALE` della ricevuta di versamento usa l'asset versionato `bollo-ufficio-postale.png`, così la resa grafica coincide con il modello fornito. Se l'asset non fosse disponibile, il renderer mantiene un fallback SVG rettangolare derivato in modo deterministico dai dati del bollettino. La matrice resta una resa grafica del template e non sostituisce una codifica Data Matrix ECC 200 certificata Poste.

Per i campi `eseguito da` delle due ricevute il bollettino usa una denominazione abbreviata e
clampata su due righe. La denominazione completa resta nella pagina 1 dell'avviso; nel bollettino
il vincolo primario e non sovrapporre codice cliente, scadenza, barcode e codeline.

## Vincoli di regressione

- La stampa deve restare A4; il numero pagine può crescere quando il partitario reale è lungo.
- I loghi devono essere caricati dagli asset interni al progetto.
- Il testo amministrativo non deve essere sintetizzato o rimosso.
- Il wizard batch e il fallback backend devono generare il template GAIA `__gaia_proposal__`, non il DOCX legacy, per includere sempre il bollettino postale.
- Il bollettino TD 896 deve restare prima del partitario e deve usare codeline coerente con codice cliente, importo, conto corrente e tipo documento.
- Il partitario deve mantenere spaziatura e allineamenti del formato raw.
- Il partitario non deve contenere script o frammenti UI Capacitas come `mstrAvvisoDlgPartitarioKUI`, `btnScaricaPartitarioDlgPartitarioKUI` o `exportExcel.aspx`.
- Il partitario non deve causare scaling globale del PDF: pagina 1, pagina 2 e bollettino devono
  mantenere dimensioni e posizione anche con partitari lunghi.
- Il caso `00050540384_avviso_sollecito_2024-2025` deve mantenere bollettino a pagina 3,
  partitario da pagina 4 e nessuna sovrapposizione fra denominazione, codice cliente, barcode e
  codeline.
- La preview utente deve generare solo il template GAIA; il template legacy non deve comparire come tab o opzione visibile.
