# Base grafica del bollettino versione 2

Riferimento fornito dall'utente: `avviso026267010014169.pdf`, una pagina
Crystal Reports, `595 x 841 pt`, rotazione PDF zero.

- SHA-256 del riferimento: `87b3ca77bad4b7e91e101b4a05548bb268ab8faa269f08f383fe5a96d3f7827f`.
- Asset: `bollettino-v2-base.svg`.
- SHA-256 dell'asset: `342d54cb96c512c31851fc1278721724cda8793ece917d28cd591c605dd7fa65`.

L'asset e stato ricavato con PyMuPDF, portando il contenuto su un piano
orizzontale di `841 x 595 pt` (`show_pdf_page`, `rotate=-90`). Prima
dell'esportazione SVG sono stati rimossi con redazioni applicate:

- tutti gli span CourierNew (versante, indirizzo, localita, scadenza e dettagli);
- codice cliente e codeline dell'avviso di esempio;
- i due importi OCR-B;
- la causale variabile del bonifico, compresi numero avviso e codice fiscale;
- le immagini Code 128 e Data Matrix con il relativo numero leggibile.

La redazione ha usato `images=2, graphics=0` per conservare la base prestampata
e rimuovere i pixel dei vecchi simboli. Il testo fisso residuo e stato
esportato come tracciati (`text_as_path=True`), con le immagini originali
incorporate. Il PDF contenente i dati del contribuente non viene versionato.

Conto `1007214826`, IBAN `IT15L0760117400001007214826`, intestazione,
loghi, istruzioni e autorizzazione originale restano fissi, come richiesto
esplicitamente dall'utente. Il renderer rigenera tutti i dati variabili;
riusa il font completo `OCRB.otf.b64` del progetto, con avanzamento orizzontale
misurato sul riferimento (`6.747 pt` a `9.75 pt`). Non si usa il font subset
del PDF, che non e adatto a nuovi dati.

Il formato della pagina finale resta verticale `595 x 841 pt`. L'HTML
posiziona il piano orizzontale tramite `translateY(841pt) rotate(-90deg)`;
`notice_html_pdf.py` ripristina i box PDF esatti dopo la quantizzazione di
Chromium, senza scalare la grafica. Nessun accesso al Desktop e necessario
durante la generazione.
