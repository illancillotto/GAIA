# Template GAIA avviso/sollecito tributi

Aggiornamento del 2026-10-28.

## Scopo

Il template GAIA propone una resa grafica formale per la preview e la stampa degli avvisi/solleciti di pagamento tributi. Dal 2026-07-27 e il default operativo sia per l'azione rapida `Avviso sollecito` sia per il wizard batch `Genera PDF nel NAS`.

Il template legacy `Avviso_Sollecito_Template.docx` resta supportato nel codice solo se viene passato un `template_path` esplicito, ma non viene esposto nella preview utente e non e piu il fallback del batch quando il frontend non specifica un template.

## Palette corrente

Dal 2026-10-27 la variante locale usa il blu `#2b5793`, con gradiente titolo
verso `#3e72b3` e fondi azzurri coordinati. Bordi, titoli, importo, riquadro
termine, accessi, note, tabella comunicazioni e titolo partitario sono coordinati.
La prima pagina usa ora un'unica famiglia Arial/Helvetica/sans-serif, anche
per titolo ente e importo, con dimensioni e pesi differenziati. Loghi e
bollettino mantengono il contratto precedente. Non e una nuova versione del bollettino o un nuovo campo regola.
Palette e provenienza: [grafica istituzionale](../../../backend/app/modules/ruolo/assets/notice-branding.md).
Anteprima dimostrativa blu: `output/pdf/avviso-2021-anteprima-blu.pdf`;
la precedente anteprima verde rimane disponibile per confronto.

## Asset

Gli asset grafici sono versionati nel modulo `ruolo`:

- `backend/app/modules/ruolo/assets/cbo-logo.png`
- `backend/app/modules/ruolo/assets/pagopa-logo.png`
- `backend/app/modules/ruolo/assets/bollettino-v2-base.svg` (grafica fissa Poste
  sanitizzata; provenienza in `bollettino-v2-base.md`)
- Prima pagina: `notice-cbo-logo.png`, `notice-anbi-logo.png`,
  `notice-whatsapp-qr.png`, `notice-irrighiamo-qr.png`, `notice-taxpayer-portal-qr.png`, con provenienza,
  trasformazioni e destinazioni in `assets/notice-branding.md`.

Il renderer non usa percorsi locali del PC, cartelle `Downloads` o file temporanei per i loghi.

## Layout GAIA

- Pagina 1: intestazione con logo CBO Pantone a sinistra e ANBI a destra,
  in aree `39mm x 18mm`, senza ritagliare o deformare i loghi. `notice_branding.py`
  incorpora i nuovi asset; i vecchi loghi restano disponibili per compatibilita
  e per il bollettino v1.
- Pagina 1: titolo avviso su due righe, senza trattino tra numero avviso e oggetto ruoli.
- Pagina 1: riepilogo pagamento, dati ente, destinatario, tabella importi, informativa privacy e revisione `Rev.2026/01`.
- Pagina 1: la richiesta di diversa dilazione compare sotto la scadenza nel
  blocco `Quanto e quando pagare`, senza duplicazione nel testo a pie pagina.
  `Come pagare` riporta `effettuato anche mediante` e l'etichetta `intestato a:`
  minuscola e il nome `Consorzio di Bonifica dell'Oristanese - Riscossione quote associative`.
  La tabella mostra `Spese Notifica`, senza il codice tecnico `SN01`;
  il relativo importo non cambia. La colonna Interessi viene eliminata da
  intestazione, colonne e righe quando tutti gli importi annuali visualizzati
  sono zero; un importo non nullo la mantiene, anche negativo o compensato
  da un'altra annualita. Spese e totali non cambiano.
- Pagina 1, subito prima dei contatti degli uffici e del testo sul sito: blocco
  `PER CONSULTARE LA PROPRIA POSIZIONE`, con percorso
  `www.bonificaoristanese.it > Cartella contribuenza >`, spiegazione del servizio
  e una sola coppia Codice ditta/PIN per utenza del destinatario. Senza dati
  o con piu utenze ambigue compare l'invito a contattare gli uffici: i sei CF
  ambigui sono sospesi in attesa del riscontro dei colleghi.
  I valori provengono da snapshot cifrati: vedi
  [importazione accessi](RUOLO_PORTALE_CONTRIBUENTE_ACCESSI_2026-10-27.md).
- Pagina 1, in fondo: due blocchi affiancati con QR `18mm`: WhatsApp
  (canale `0029Vb9tZLzDJ6H3keAt9h24`) e Irrighiamo Insieme
  (`https://login.bonificaoristanese.it/`), con spiegazione e invito a inquadrarli.
  Irrighiamo Insieme riporta: «L'applicazione del Consorzio per segnalare guasti
  o rotture e richiedere l'autorizzazione all'irrigazione.»
  Eliminata la dicitura «Apri il canale WhatsApp»; il QR portale resta un asset
  di provenienza ma non viene stampato. L'informativa privacy segue i due servizi
  con margine `1.5mm`, corpo `7.8pt` e interlinea `1.15`.
  Corpo prima pagina `10.2pt`, interlinea `1.24`, spazi verticali compattati per
  mantenere accessi, QR e privacy sulla prima pagina anche con cinque annualita,
  una coppia di accesso o messaggio uffici e note di residuo. Tutta la prima pagina usa Arial/Helvetica/sans-serif, incluso il titolo ente `19.5pt`;
  i margini verticali della prima pagina sono `10mm`.
- Pagina 1: nella colonna `Numero avviso` del riepilogo annuale il template mostra il codice avviso senza il prefisso tecnico `01.`; il valore persistito `codice_cnc` resta invariato.
- Pagina 2: comunicazioni amministrative complete derivate dal template originale, con interlinea compatta ma leggibile.
- Pagina 2: i riferimenti dipendenti dall'annualita (delibere di emissione/approvazione con data albo, dilazione, minimi, riscossione coattiva, anno di bilancio) sono ricostruiti per gli anni dell'avviso da `backend/app/modules/ruolo/services/tributi_legal_text.py` (`ROLE_YEAR_RESOLUTIONS`, 2021-2025); un anno non configurato blocca la generazione.
- Pagina 2: subito dopo la tabella delle dilazioni e prima di `Scadenza del
  Pagamento`, un paragrafo chiarisce che l'avviso non sostituisce un piano di
  rateizzazione gia sottoscritto e non saldato, ne modifica le decorrenze degli
  interessi, e che il residuo tiene conto dei versamenti effettuati. Lo stesso
  testo compare nel fallback delle comunicazioni senza DOCX sorgente.
- Pagina 3 e successive: dettaglio partitario allegato con font monospace ingrandito, wrapping controllato, formato raw preservato e titolo `Dettaglio partitario allegato - pagina X di N`.
- Ultima pagina, se abilitata dalle regole: bollettino postale TD 896 nella versione
  salvata, inserito dopo il partitario e stampabile al `100%`.

### Riquadro 2021: data e termine dalla notifica

Nel solo riquadro `Quanto e quando pagare` degli avvisi del solo ruolo 2021,
se lo snapshot contiene `due_date` o `deadline`, si stampa
`entro il gg/mm/aaaa e comunque entro 60 giorni dalla data di notifica`.
Senza data esplicita si stampa soltanto `entro 60 giorni dalla data di notifica`,
senza inventare una data dalla generazione. Le altre annualita e i gruppi
multiannualita mantengono il termine della regola. Questa dicitura riguarda
la prima pagina; i bollettini usano la data fissa e i campi DOCX restano invariati.

### Termine di pagamento dalla notifica

Dal 2026-10-27 la regola puo salvare `payment_deadline_mode=notification_60_days`,
in alternativa al termine a data fissa. Il riepilogo e i campi DOCX `Scadenza`
e `Pagamento_entro` riportano il termine relativo `60 giorni dalla data di notifica`.
Dal 2026-10-28 i bollettini v1/v2 stampano invece `gg/mm/aaaa - Rata Unica`
su entrambi i tagliandi. La data fissa resta visibile e salvata nelle Regole ruolo
anche nella modalita a 60 giorni ed e obbligatoria con bollettino abilitato.
Salvataggio e generazione da vecchie regole/snapshot senza data sono bloccati
con invito a impostarla nelle Regole ruolo. Senza bollettino il solo termine
relativo e ammesso. Non viene inventata una data dalla stampa per la modalita
a 60 giorni; il fallback legacy della modalita a data fissa resta invariato.

Solo con questa modalita, prima del portale, compare `Pagamento entro 60 giorni
dalla data di notifica`, senza ripetere l'importo del riepilogo, seguito dalle avvertenze sul rinvio
di sabati/festivi al primo giorno lavorativo e sugli interessi oltre i 60 giorni.
Nel footer, dopo gli accessi portale e sopra i due QR, compare un punto
esclamativo rosso dentro un triangolo vettoriale con il testo d'intimazione riferito al Consorzio e alle
procedure di riscossione coattiva nei casi e con le modalita previsti dalla legge.
La frase richiesta e: «In caso di mancato pagamento, il Consorzio di Bonifica
dell'Oristanese tramite l'agente di riscossione attiverà le procedure di
riscossione coattiva previste dalla legge.»

Il CSS `notice_payment_deadline.py` compatta soltanto questa modalita:
margini verticali `8mm`, corpo `9.2pt`, riquadro intimazione `8.3pt`;
da tre annualita il riepilogo e gli spazi si riducono ulteriormente.
QR WhatsApp/Irrighiamo Insieme `18mm`, accessi e privacy restano sulla prima pagina nelle prove
con una, due e cinque annualita, nomi lunghi e una coppia di accesso per utenza.
Gli spazi liberi vengono distribuiti tra termine, accessi portale, contatti e sito, e
footer: distacco minimo `1mm`, senza un vuoto concentrato sopra l'intimazione.
In entrambe le modalita, subito dopo il portale compaiono prima giorni/orari e
telefono degli uffici, poi la frase sul sito. Il paragrafo usa `8.5pt`,
interlinea `1.12`, margine e padding superiore `1mm`.
Stato locale e verifiche: [scadenza dalla notifica](RUOLO_SCADENZA_NOTIFICA_2026-10-27.md).

## Versione salvata nella regola

`Gestisci regole calcolo` salva `bollettino_version`: `v1` (modello esistente,
default anche per regole migrate e snapshot precedenti) o `v2` (modello Poste).
Preview e batch usano la versione della regola attiva dell'anno piu recente;
`print_bollettino=false` in una qualsiasi regola coinvolta esclude la pagina.
Il payload del batch conserva la scelta: cambiare una regola non riscrive
snapshot e PDF gia generati.

V2 riproduce il riferimento `avviso026267010014169.pdf`: box MediaBox/CropBox
`595 x 841 pt`, grafica orizzontale ruotata internamente alla pagina, senza
scaling. Mantiene testi, loghi, conto, IBAN e autorizzazione del riferimento;
rigenera versante, indirizzo, importo, scadenza, esercizio/causale e codici da
GAIA. Entrambe le ricevute riportano scadenza, esercizio e importo. Il font dei
dati del versante si riduce fino a `6pt`; oltre tale limite la generazione
fallisce con errore esplicito, senza troncare i dati. L'autorizzazione v2 e
quella nell'asset, indipendente dalle impostazioni `TD896_*` riservate a v1.
`services/notice_html_pdf.py` ripristina i box esatti dopo l'arrotondamento di
Chromium, senza spostare la grafica; le altre pagine restano invariate.

Le misure, le posizioni e la configurazione AUT descritte sotto si riferiscono
a v1; codifica TD 896, dati della regola e ordine dei documenti sono condivisi.
La procedura di verifica v2 e nel manuale: il verificatore geometrico v1 non
valida le coordinate del modello Poste. I test di integrazione generano PDF
con Chromium e decodificano Code 128 e Data Matrix di entrambe le versioni.

## Bollettino TD 896: v1 e codifica condivisa

La pagina bollettino usa i dati dell'avviso GAIA: numero avviso, codice fiscale, denominazione contribuente, importo saldo, scadenza, esercizio e anni di riferimento. Il numero avviso visibile resta quello GAIA, mentre il codice cliente postale e un identificativo distinto di 18 cifre derivato deterministicamente dall'avviso e completato con controcodice modulo 93. La causale stampata nei riquadri del bollettino e solo quella configurata nella `Regola ruolo` (`bollettino_causale`) o presente nel payload (`payment_reason_code`, `causale`); se manca, la riga `Causale` non viene stampata (dal 2026-10-22; prima GAIA stampava come fallback le cifre 7-9 del numero avviso, un frammento di annualita/progressivo e non una causale). La causale bonifico resta invece nel formato completo `A <numero avviso> CF <codice fiscale>`.

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
- codice di autorizzazione alla stampa in proprio, configurato e non piu hardcoded
  (dal 2026-10-22). Il codice `AUT.DB/SISB/36211 DEL 5/9/2012` non copre il layout
  GAIA e non viene piu stampato. Le variabili `Settings` sono:
  - `TD896_SAMPLE_MODE=true`: stampa il segnaposto `AUT.DB/SISB/XXXXX DEL XX/XX/XXXX`
    per la campionatura da inviare a Poste;
  - `TD896_SAMPLE_MODE=false` (default): stampa `TD896_PRINT_AUTHORIZATION`; se il
    valore e vuoto o contiene `X` la generazione del bollettino fallisce con
    `Codice autorizzazione Poste TD 896 non configurato` e l'item batch risulta
    `failed`. La sola pagina avviso senza bollettino non richiede il codice.

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

Se la policy non valorizza i campi, la riga `Causale` non viene stampata e
`Esercizio` resta automatico, derivato dall'anno di emissione
dell'avviso (`notice_emission_year`), secondo la convenzione Capacitas degli
avvisi accorpati: un avviso emesso nel `2026`, anche se relativo alle annualita
`2024-2025`, riporta `2626` (aggiornamento 2026-10-20; prima GAIA duplicava
l'annualita piu alta, producendo `2525`). Un payload senza anno di emissione
lascia il campo vuoto.

Nota operativa: la pagina rende un facsimile precompilato per stampa e pagamento manuale/online tramite dati, codeline e barcode. La piena omologazione di stampa in proprio Poste richiede verifica specialistica di posizionamenti OCR e Data Matrix secondo le specifiche ufficiali.

Il Data Matrix non usa piu un asset statico o una matrice grafica simulata. Viene generato per ogni avviso dallo stesso payload del Code 128 e puo essere verificato seguendo `MANUALE_VERIFICA_BOLLETTINI_TD896.md`.

Nei campi `eseguito da` delle due ricevute la denominazione e stampata per intero, senza
troncamento con `...` (dal 2026-10-22). Posizione e dimensioni dei riquadri restano invariate
(versamento: `top 35mm`, larghezza `63.5mm`, `max-height 17mm`; accredito: `left 58.5mm`,
`max-height 27mm`), cosi il testo non invade dettagli (`58.5mm`), riquadro bollo (`49mm`) o
barcode (`64mm`). Se nome e indirizzo non entrano nel riquadro piu stretto, quello della
ricevuta di versamento, il renderer riduce per gradi il font del blocco nome (`8.25pt`,
`7.5pt`, `6.75pt`, `6pt`, classi `payer-fit-1..3`); l'indirizzo resta a `7.05pt`. La stima e
esatta perche il testo e in OCR-B monospazio (avanzamento `0.723em`) e lascia un margine di
`0.3mm`. Oltre i `6pt` il nome non viene troncato: il log registra un warning con il numero
avviso, da verificare a vista sul PDF.

## Vincoli di regressione

- La stampa deve restare A4; il numero pagine può crescere quando il partitario reale è lungo.
- I loghi devono essere caricati dagli asset interni al progetto.
- Il testo amministrativo non deve essere sintetizzato o rimosso.
- Il wizard batch e il fallback backend devono generare il template GAIA `__gaia_proposal__`, rispettando esclusione e versione del bollettino salvate nelle regole.
- Il bollettino TD 896 deve restare dopo il partitario, come ultima pagina, e deve usare codeline coerente con codice cliente, importo, conto corrente e tipo documento.
- Code 128 e Data Matrix devono decodificare lo stesso payload numerico di 50 cifre.
- Entrambi i QR devono decodificare canale WhatsApp e login Irrighiamo Insieme dal PDF finale e rimanere sulla
  prima pagina; il blocco di accesso portale precede i contatti degli uffici e il testo sul sito.
  I PIN devono essere cifrati nel DB e negli snapshot persistiti; lo stesso
  nominativo senza codice fiscale corrispondente non autorizza alcun accesso.
- Il testo sui piani gia sottoscritti deve comparire una sola volta, dopo le
  dilazioni e prima della scadenza, senza invadere la firma della pagina 2.
- Causale ed esercizio configurati nella `Regola ruolo` devono comparire nella ricevuta di versamento; senza causale configurata la riga `Causale` non compare, mentre l'esercizio resta automatico.
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
