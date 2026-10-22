# Template GAIA avviso/sollecito tributi

Aggiornamento del 2026-08-24.

## Scopo

Il template GAIA propone una resa grafica formale per la preview e la stampa degli avvisi/solleciti di pagamento tributi. Dal 2026-07-27 e il default operativo sia per l'azione rapida `Avviso sollecito` sia per il wizard batch `Genera PDF nel NAS`.

Il template legacy `Avviso_Sollecito_Template.docx` resta supportato nel codice solo se viene passato un `template_path` esplicito, ma non viene esposto nella preview utente e non e piu il fallback del batch quando il frontend non specifica un template.

## Asset

Gli asset grafici sono versionati nel modulo `ruolo`:

- `backend/app/modules/ruolo/assets/cbo-logo.png`
- `backend/app/modules/ruolo/assets/pagopa-logo.png`

Il renderer non usa percorsi locali del PC, cartelle `Downloads` o file temporanei per i loghi.

## Layout GAIA

- Pagina 1: intestazione con logo CBO a sinistra e pagoPA a destra, entrambi in riquadro `39mm x 23mm`.
- Pagina 1: titolo avviso su due righe, senza trattino tra numero avviso e oggetto ruoli.
- Pagina 1: riepilogo pagamento, dati ente, destinatario, tabella importi, informativa privacy e revisione `Rev.2026/01`.
- Pagina 1: nella colonna `Numero avviso` del riepilogo annuale il template mostra il codice avviso senza il prefisso tecnico `01.`; il valore persistito `codice_cnc` resta invariato.
- Pagina 2: comunicazioni amministrative complete derivate dal template originale, con interlinea compatta ma leggibile.
- Pagina 2: i riferimenti dipendenti dall'annualita (delibere di emissione/approvazione con data albo, dilazione, minimi, riscossione coattiva, anno di bilancio) sono ricostruiti per gli anni dell'avviso da `backend/app/modules/ruolo/services/tributi_legal_text.py` (`ROLE_YEAR_RESOLUTIONS`, 2021-2025); un anno non configurato blocca la generazione.
- Pagina 3 e successive: dettaglio partitario allegato con font monospace ingrandito, wrapping controllato, formato raw preservato e titolo `Dettaglio partitario allegato - pagina X di N`.
- Ultima pagina: bollettino postale TD 896 precompilato in A4 orizzontale nativo, inserito dopo il partitario e stampabile al `100%` senza rotazioni o riduzioni.

## Bollettino TD 896

La pagina bollettino usa i dati dell'avviso GAIA: numero avviso, codice fiscale, denominazione contribuente, importo saldo, scadenza, esercizio e anni di riferimento. Il numero avviso visibile resta quello GAIA, mentre il codice cliente postale e un identificativo distinto di 18 cifre derivato deterministicamente dall'avviso e completato con controcodice modulo 93. La causale stampata nei riquadri del bollettino usa il codice a tre cifre derivato dal numero avviso, con override possibile tramite payload dedicato; la causale bonifico resta invece nel formato completo `A <numero avviso> CF <codice fiscale>`.

Il layout recepisce le misure principali del modello CH8/Bis TD 896 indicate nei manuali Poste forniti localmente:

- bollettino standard `297mm x 102mm`;
- ricevuta di versamento `132mm`;
- ricevuta di accredito `165mm`;
- zona di codifica OCR/codeline alta `19mm`;
- IBAN in 27 caselle sulla stessa riga, con ABI Poste `07601`;
- barcode su ricevuta di accredito a circa `64mm` dal bordo superiore, largo `93mm` e alto `12mm`;
- Data Matrix ECC 200 rettangolare `16 x 48`, con quiet zone di due celle per lato, generato dai dati dell'avviso e posizionato nella zona inferiore della ricevuta di versamento.
- dati significativi e codeline nel font incorporato `OCRB-Regular`, nero puro;
- elementi guida non significativi in grigio laserizzato al `20%`;
- due aree bollo da `55mm x 34mm`, posizionate a `49mm` dal bordo superiore.

Posizionamenti sulla ricevuta di accredito (aggiornamento 2026-10-20, misurati sul PDF
finale e conformi a `Caratteristiche del bollettino` Ed. 2020):

- codeline allineata alla griglia Poste a decimi di pollice, con i quattro campi ancorati
  al bordo destro: codice cliente a `106.68mm`, importo a `60.96mm`, conto a `22.86mm` e
  tipo documento a `7.62mm`; i delimitatori cadono quindi nel 4°, 10°, 25° e 43° decimo;
- simbolo `€` `7mm x 7mm` a `7.5mm` dall'alto e dalla divisione, con `TD 896` sotto;
- conto corrente a circa `34.5mm` dalla divisione e importo a circa `116mm`, entrambi a
  `10mm` dall'alto; nella ricevuta di versamento il conto parte da `42.9mm` e l'importo e
  allineato a `3mm` dal bordo destro;
- etichetta `Intestato a` a `21.3mm` e intestazione su due righe a `24.1mm` dall'alto,
  senza sovrapporsi al riquadro `eseguito da`;
- numero sotto il barcode in `7.9pt`, dettagli della ricevuta di versamento in `8pt`;
- confronto con l'Allegato 8 del manuale: logo beneficiario a `5.5mm` dall'alto, caselle IBAN
  a `16.5mm` (misurate `16.6mm`, arrotondamento al pixel di Chromium), codice cliente a `42mm`
  dall'alto e `7.5mm` dalla divisione, mezzeria della codeline a `8.5mm` dal bordo inferiore.
  Le regole CSS compensano lo spazio sopra i glifi (`top` del codice cliente `40.9mm`, della
  codeline `91.25mm`, delle caselle IBAN `16.1mm`);
- riquadro bollo della ricevuta di versamento alto `33.2mm` invece di `34mm`: con il
  Data Matrix a `84.75mm` la zona di rispetto di due celle (`1.875mm`) resta libera dal
  bordo tratteggiato (distanza misurata `2.14mm`). Il manuale chiede il bollo fino a
  `83mm` e il Data Matrix a circa `84.5mm`, quindi le due misure nominali non lasciano
  spazio sufficiente;
- sopra il bollettino, fuori dal modulo, la pagina riporta le istruzioni di stampa
  raccomandate da Poste per i PDF (cap. 6): stampa come immagine, A4 orizzontale al
  100%, solo fronte, carta bianca non riciclata da 80-100 g/m², ritaglio lungo il bordo
  superiore e retro bianco.

La verifica di questi posizionamenti e stata eseguita con PyMuPDF e con la decodifica
`zxing` di Code 128 e Data Matrix sui campioni preparati per la richiesta di
autorizzazione alla stampa in proprio.

Per la stampa PDF con Chromium il renderer usa tre job separati: avviso/comunicazioni,
partitario e bollettino. I documenti vengono poi uniti con `pypdf` nell'ordine
`avviso + comunicazioni -> partitario -> bollettino`. Questa separazione evita che un
partitario reale molto lungo faccia scattare lo shrink-to-fit di Chromium sulla pagina
bollettino, mantenendo al tempo stesso il bollettino come ultima pagina del documento.

Il bollettino viene renderizzato direttamente su una pagina A4 landscape
`297mm x 210mm`. Il modulo CH8/Bis e ancorato al bordo inferiore con dimensioni
reali `297mm x 102mm`; non sono applicati `transform`, rotazioni o
`shrink-to-fit`. Le altre pagine restano A4 portrait e `pypdf` conserva i
formati pagina differenti durante l'unione.

Valori fissi configurati nel renderer:

- conto corrente postale `1007214826`;
- IBAN `IT15L0760117400001007214826`;
- intestazione `CONSORZIO DI BONIFICA DELL'ORISTANESE - RISCOSSIONE QUOTE ASSOCIATIVE`;
- tipo documento `896`;
- codice di autorizzazione alla stampa `AUT.DB/SISB/XXXXX DEL XX/XX/2026`, segnaposto
  in attesa del codice che Poste rilascera per la stampa in proprio in PDF (dal
  2026-10-20; prima era stampato `AUT.DB/SISB/36211 DEL 5/9/2012`).

La codeline usa il codice cliente postale di 18 cifre. Le prime 16 cifre incorporano il numero avviso GAIA e un discriminante interno; le ultime due sono il resto della divisione delle prime 16 per 93. L'importo usa il formato Poste `00000000+00` e il conto corrente viene normalizzato a 12 cifre.

Un unico oggetto validato alimenta codeline, Code 128-C e Data Matrix. Il payload ottico contiene sempre 50 cifre con struttura: `18` + codice cliente di 18 cifre + `12` + conto corrente a 12 cifre + `10` + importo a 10 cifre senza separatore + `3` + tipo documento `896`. Il renderer genera il Code 128-C con checksum modulo 103 e il Data Matrix con 49 codeword dati e 28 codeword Reed-Solomon.

La `Regola ruolo` puo configurare i campi opzionali `bollettino_causale` e
`bollettino_esercizio`, rispettivamente di tre e quattro cifre. Durante la
generazione del sollecito GAIA usa la policy attiva relativa all'annualita piu
recente inclusa nell'avviso e copia i valori configurati nel payload del
documento. La stessa configurazione si applica quindi alla preview rapida e al
batch salvato nel NAS.

Causale, esercizio e scadenza sono stampati nella ricevuta di versamento. La
zona cliente della ricevuta di accredito contiene esclusivamente denominazione
e indirizzo del versante; questa separazione evita l'inserimento di dati
amministrativi nell'area riservata dal modello Poste.

Se la policy non valorizza i campi, il comportamento resta automatico: la
causale e derivata dal numero avviso e `Esercizio` dall'anno di emissione
dell'avviso (`notice_emission_year`), secondo la convenzione Capacitas degli
avvisi accorpati: un avviso emesso nel `2026`, anche se relativo alle annualita
`2024-2025`, riporta `2626` (aggiornamento 2026-10-20; prima GAIA duplicava
l'annualita piu alta, producendo `2525`). Un payload senza anno di emissione
lascia il campo vuoto.

Nota operativa: la pagina rende un facsimile precompilato per stampa e pagamento manuale/online tramite dati, codeline e barcode. La piena omologazione di stampa in proprio Poste richiede verifica specialistica di posizionamenti OCR e Data Matrix secondo le specifiche ufficiali.

Il Data Matrix non usa piu un asset statico o una matrice grafica simulata. Viene generato per ogni avviso dallo stesso payload del Code 128 e puo essere verificato seguendo `MANUALE_VERIFICA_BOLLETTINI_TD896.md`.

Per i campi `eseguito da` delle due ricevute il bollettino usa una denominazione abbreviata e
clampata su due righe. La denominazione completa resta nella pagina 1 dell'avviso; nel bollettino
il vincolo primario e non sovrapporre codice cliente, scadenza, barcode e codeline.

## Vincoli di regressione

- La stampa deve restare A4; il numero pagine può crescere quando il partitario reale è lungo.
- I loghi devono essere caricati dagli asset interni al progetto.
- Il testo amministrativo non deve essere sintetizzato o rimosso.
- Il wizard batch e il fallback backend devono generare il template GAIA `__gaia_proposal__`, non il DOCX legacy, per includere sempre il bollettino postale.
- Il bollettino TD 896 deve restare dopo il partitario, come ultima pagina, e deve usare codeline coerente con codice cliente, importo, conto corrente e tipo documento.
- Code 128 e Data Matrix devono decodificare lo stesso payload numerico di 50 cifre.
- Causale ed esercizio configurati nella `Regola ruolo` devono comparire nella ricevuta di versamento; se assenti devono restare attivi i fallback automatici.
- Il partitario deve mantenere spaziatura e allineamenti del formato raw.
- Il partitario non deve contenere script o frammenti UI Capacitas come `mstrAvvisoDlgPartitarioKUI`, `btnScaricaPartitarioDlgPartitarioKUI` o `exportExcel.aspx`.
- Il partitario non deve stampare azioni di modale Capacitas come `Chiudi` o `Scarica` in coda.
- Ogni pagina del partitario deve riportare `Dettaglio partitario allegato - pagina X di N`, senza titolo generico `continua`.
- Il partitario non deve causare scaling globale del PDF: pagina 1, pagina 2 e bollettino devono
  mantenere dimensioni e posizione anche con partitari lunghi.
- Il caso `00050540384_avviso_sollecito_2024-2025` deve mantenere il bollettino dopo il
  partitario e nessuna sovrapposizione fra denominazione, codice cliente, barcode e
  codeline.
- La preview utente deve generare solo il template GAIA; il template legacy non deve comparire come tab o opzione visibile.
