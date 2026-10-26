# Mini manuale di verifica bollettini TD 896 GAIA

Aggiornamento del 2026-10-26.

## Scopo

Questa procedura permette di verificare, prima della consegna o del pagamento,
che il bollettino postale allegato a un avviso GAIA contenga i dati dello stesso
avviso. In caso di una sola difformita non procedere al pagamento e segnalare il
PDF all'amministratore GAIA.

## Scelta della versione nella regola ruolo

In `Ruolo > Tributi > Gestisci regole calcolo`, il campo `Versione bollettino`
salva la scelta per le stampe e le anteprime successive:

- `Versione 1 - modello attuale`: mantiene la stampa GAIA esistente. E il
  valore iniziale anche per tutte le regole precedenti alla migrazione
  `20261026_0900`.
- `Versione 2 - modello Poste`: riproduce la pagina del riferimento fornito
  `avviso026267010014169.pdf`, conservando grafica, testi fissi, loghi, conto,
  IBAN e autorizzazione postale del riferimento. Contribuente, indirizzo,
  scadenza, esercizio, causale, importo e codici di pagamento provengono
  dall'avviso GAIA. Non richiede l'autorizzazione configurabile della versione 1.

Negli avvisi con piu annualita, la versione segue la regola dell'anno piu
recente, come causale, esercizio e data di pagamento. `Stampa bollettino
postale` continua a escludere l'intera pagina se anche una sola annualita
non prevede il bollettino. Prima pagina e partitario non cambiano.
Le nuove impostazioni si applicano ai PDF generati successivamente, senza
modificare i documenti gia archiviati.

## Verifica visiva

1. Da `Ruolo > Tributi`, aprire l'avviso e generare la preview o il PDF del
   sollecito GAIA.
2. Annotare dalla prima pagina il numero avviso, il contribuente, l'importo da
   pagare e la scadenza.
3. Andare all'ultima pagina, che deve contenere il bollettino `TD 896`.
4. Controllare che entrambe le ricevute riportino lo stesso importo della prima
   pagina, inclusi i centesimi.
5. Controllare denominazione del contribuente, scadenza, causale ed esercizio.
   Se nella `Regola ruolo` sono stati configurati `Causale bollettino` ed
   `Esercizio bollettino`, la ricevuta di versamento deve mostrare esattamente i
   codici di tre e quattro cifre inseriti. La ricevuta di accredito riserva la
   zona cliente esclusivamente ai dati del versante nella versione 1. La
   versione 2 conserva le posizioni del riferimento, con i dettagli sotto
   l'indirizzo anche sulla ricevuta di accredito.
   Se la causale non e configurata, la riga `Causale` non deve comparire:
   GAIA non ricava piu una causale dal numero avviso. Se l'esercizio non e
   configurato, vale l'anno di emissione ripetuto, per esempio `2626` per un
   avviso emesso nel 2026.
   La denominazione nel campo `eseguito da` deve essere completa, senza `...`:
   nella versione 1, se e lunga va a capo e il font si riduce fino a `6pt`.
   La versione 2 riduce il font nella riga disponibile fino a `6pt`; se non
   basta, segnala un errore di generazione senza troncare il nominativo.
6. Verificare i dati fissi del Consorzio:
   - conto corrente postale `1007214826`;
   - conto a 12 cifre nella codeline `001007214826`;
   - IBAN `IT15L0760117400001007214826`;
   - tipo documento `896`.
7. Verificare che il codice cliente sulla ricevuta di accredito contenga
   esattamente 18 cifre. Non deve necessariamente coincidere graficamente con il
   numero avviso: e l'identificativo postale derivato dall'avviso e termina con
   due cifre di controllo modulo 93. Le cifre finali possono ripetersi tra
   avvisi diversi: l'identificativo da confrontare e sempre il codice completo
   di 18 cifre, mai il solo suffisso.
8. Verificare che il numero avviso abbia al massimo 15 cifre. Per avvisi con tre
   o piu annualita il numero riporta solo la prima e l'ultima annualita, per
   esempio `12026222500001` per `2022-2025`: l'elenco completo delle annualita
   va controllato nel riepilogo per anno e nel partitario, non nel numero.

## Verifica formato di stampa - versione 1

L'ultima pagina del PDF deve essere A4 orizzontale. Stampare al `100%` o con
`Dimensioni effettive`, mai con `Adatta alla pagina`. Il modulo da ritagliare
deve misurare `297 x 102 mm`, con ricevuta di versamento da `132 mm`, ricevuta
di accredito da `165 mm`, corpo da `83 mm` e zona OCR inferiore da `19 mm`.

I dati significativi e la codeline devono usare il font incorporato
`OCRB-Regular` e il colore nero. Il barcode deve misurare circa `93 x 12 mm`;
il Data Matrix utile `45 x 15 mm`, esclusa la quiet zone di due celle per lato.
Le due aree per il bollo postale devono iniziare a `49 mm` dal bordo superiore
del modulo e misurare `55 x 34 mm`; sulla ricevuta di versamento l'area e alta
`33.2 mm` per lasciare libera la zona di rispetto del Data Matrix. Sopra il
modulo devono comparire le istruzioni di stampa.

## Verifica formato di stampa - versione 2

La pagina ha `MediaBox` e `CropBox` di `595 x 841 pt`, rotazione PDF `0`,
come il riferimento. Il contenuto e orizzontale e ruotato di 90 gradi dentro
la pagina verticale. Non impostare un secondo adattamento o una seconda
rotazione: stampare al `100%` / `Dimensioni effettive`.

Le coordinate seguenti sono riferite al contenuto letto orizzontalmente,
con origine nell'angolo superiore sinistro, in punti PDF:

| Elemento | Posizione / dimensione |
| --- | --- |
| Base del modulo originale | x `12`, y `306.3`, larghezza `815.5`, altezza `283.2` |
| Separazione delle ricevute | x circa `369.5` |
| Codice cliente | x `389.3`, baseline y `433.5` |
| Codeline | x `389.3`, baseline y `571.8`, OCR-B `9.75pt`, avanzamento `6.747pt` |
| Barre Code 128 | x `532.1`, y `485.3`, `263.5 x 30.4pt`, numero subito sotto |
| Riquadro Data Matrix | x `222.7`, y `533.3`, `129.25 x 45.95pt` |

La grafica fissa e incorporata nel PDF; i dati del contribuente dell'esempio
non sono presenti nell'asset riutilizzato. I due codici vengono rigenerati,
con lo stesso contratto TD 896 della versione 1. La correzione della
quantizzazione Chromium ripristina le dimensioni esatte della pagina senza
ridimensionare il contenuto.

## Verifica con lettore codici

Usare un lettore che supporti sia `Data Matrix` sia `Code 128`, per esempio
ZXing Barcode Scanner. Scansionare i due simboli dal PDF a schermo oppure da una
stampa eseguita al 100%, senza l'opzione `Adatta alla pagina`.

I due simboli devono restituire la stessa sequenza numerica di 50 cifre:

```text
18 + codice cliente (18) + 12 + conto (12) + 10 + importo (10) + 3 + 896
```

Interpretazione del risultato:

| Posizioni | Contenuto | Controllo |
| --- | --- | --- |
| 1-2 | Lunghezza codice cliente | deve essere `18` |
| 3-20 | Codice cliente | 18 cifre, ultime due = prime 16 modulo 93 |
| 21-22 | Lunghezza conto | deve essere `12` |
| 23-34 | Conto corrente | deve essere `001007214826` |
| 35-36 | Lunghezza importo | deve essere `10` |
| 37-46 | Importo senza separatore | 8 cifre euro + 2 cifre centesimi |
| 47 | Lunghezza tipo documento | deve essere `3` |
| 48-50 | Tipo documento | deve essere `896` |

Esempio: per `1,00 EUR` il campo importo deve essere `0000000100`; per
`120,67 EUR` deve essere `0000012067`.

## Verifica automatica della campionatura

Lo script `scripts/ruolo/verify_td896_pdf.py` verifica le misure della
**versione 1**: i suoi controlli geometrici A4 orizzontale e modulo `297 x
102 mm` non si applicano alla versione 2. Per la versione 2 verificare le
misure sopra e leggere entrambi i simboli come descritto nella sezione
`Verifica con lettore codici`.

Lo script controlla uno o piu PDF gia
generati (avviso completo o solo bollettino). Le dipendenze `pymupdf` e
`zxing-cpp` (versioni fissate in `scripts/ruolo/requirements-verify-td896.txt`)
servono solo allo sviluppo e alla CI e non entrano nell'immagine backend:

```bash
python3 -m venv /tmp/td896-verify
/tmp/td896-verify/bin/pip install -r scripts/ruolo/requirements-verify-td896.txt
/tmp/td896-verify/bin/python scripts/ruolo/verify_td896_pdf.py campionatura_TD896_5_bollettini.pdf
```

Ogni pagina con una codeline TD 896 e trattata come un bollettino. Per ciascuna
lo script stampa una tabella `OK`/`KO`:

| Controllo | Criterio |
| --- | --- |
| Pagina A4 orizzontale | `297 x 210 mm` (tolleranza 1 mm) |
| Modulo `297 x 102 mm` | bordo superiore nero del modulo, tolleranza `0.5 mm` |
| Divisione a `132 mm` | linea verticale nera fra le ricevute, `132 +/- 0.5 mm` |
| Codeline e controcodice | regex `<\d{18}> \d{8}\+\d{2}> \d{12}< 896>`, ultime due cifre del codice cliente = prime 16 modulo 93 |
| Code 128 e Data Matrix | rasterizzazione a 600 dpi con zxing-cpp; entrambi uguali al payload di 50 cifre ricavato dalla codeline; Data Matrix `16x48` |
| Importo | tutti gli importi del corpo del modulo uguali all'importo in codeline |
| IBAN | uguale sulle due ricevute, mod 97 valido, ABI `07601` nelle posizioni 6-10 |
| Font codeline | `FontDescriptor` con `FontFamily` `OCR B` |
| Nome versante | riga `eseguito da` presente e senza `...` |
| Codice AUT | presente; `CAMPIONATURA` se contiene `XXXXX` |

L'uscita e `0` se nessun controllo e `KO`. `CAMPIONATURA` non e un errore: va
risolto prima della produzione configurando `TD896_PRINT_AUTHORIZATION` e
`TD896_SAMPLE_MODE=false`. Le misure geometriche si basano sui tratti neri del
PDF e non sostituiscono la verifica a stampa al 100%.

Lo script ha test propri in `tests/ruolo/test_verify_td896_pdf.py`, con una
pagina campione sintetica in `tests/ruolo/fixtures/td896_su_campu_sample.pdf`
(nominativo lungo Su Campu, AUT segnaposto). Si eseguono con
`make test-verify-td896` (venv `backend/.venv` con le dipendenze sopra), che
richiede il 100% di statement e branch; il job CI `backend.yml` installa le
stesse dipendenze ed esegue lo stesso target.

## Esito accettabile

Il bollettino e verificato solo se:

- importo della prima pagina, delle due ricevute, della codeline e dei due
  codici ottici coincide;
- Code 128 e Data Matrix restituiscono lo stesso valore di 50 cifre;
- codice cliente, conto e tipo documento rispettano lunghezze e valori sopra
  indicati;
- causale ed esercizio coincidono con la `Regola ruolo` applicata; senza
  causale configurata la riga non compare e l'esercizio segue l'anno di
  emissione;
- il codice `AUT.DB/SISB/...` e quello rilasciato da Poste; il segnaposto
  `AUT.DB/SISB/XXXXX DEL XX/XX/XXXX` e ammesso solo per la campionatura;
- il PDF mantiene formato, font, colori e misure descritti nella verifica di
  stampa, senza riduzioni automatiche;
- il Data Matrix viene letto senza ritagliare o alterare le aree bianche che lo
  circondano.

Questa verifica controlla la coerenza dei dati prodotti da GAIA. L'omologazione
formale della stampa in proprio e dei posizionamenti OCR resta soggetta alla
procedura di autorizzazione di Poste Italiane.

## Fonti archiviate

Le copie dei manuali Poste Italiane consultati, con edizione e checksum, sono
elencate in [`riferimenti-td896/README.md`](riferimenti-td896/README.md).
