# Mini manuale di verifica bollettini TD 896 GAIA

Aggiornamento del 2026-08-24.

## Scopo

Questa procedura permette di verificare, prima della consegna o del pagamento,
che il bollettino postale allegato a un avviso GAIA contenga i dati dello stesso
avviso. In caso di una sola difformita non procedere al pagamento e segnalare il
PDF all'amministratore GAIA.

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
   zona cliente esclusivamente ai dati del versante, come richiesto dal manuale
   Poste. Se i campi sono vuoti, GAIA applica i valori automatici derivati dal
   numero avviso e dall'annualita piu recente.
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

## Verifica formato di stampa

L'ultima pagina del PDF deve essere A4 orizzontale. Stampare al `100%` o con
`Dimensioni effettive`, mai con `Adatta alla pagina`. Il modulo da ritagliare
deve misurare `297 x 102 mm`, con ricevuta di versamento da `132 mm`, ricevuta
di accredito da `165 mm`, corpo da `83 mm` e zona OCR inferiore da `19 mm`.

I dati significativi e la codeline devono usare il font incorporato
`OCRB-Regular` e il colore nero. Il barcode deve misurare circa `93 x 12 mm`;
il Data Matrix utile `45 x 15 mm`, esclusa la quiet zone di due celle per lato.
Le due aree per il bollo postale devono misurare `55 x 34 mm` e iniziare a
`49 mm` dal bordo superiore del modulo.

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

## Esito accettabile

Il bollettino e verificato solo se:

- importo della prima pagina, delle due ricevute, della codeline e dei due
  codici ottici coincide;
- Code 128 e Data Matrix restituiscono lo stesso valore di 50 cifre;
- codice cliente, conto e tipo documento rispettano lunghezze e valori sopra
  indicati;
- causale ed esercizio coincidono con la `Regola ruolo` applicata oppure, se
  non configurati, con i fallback automatici;
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
