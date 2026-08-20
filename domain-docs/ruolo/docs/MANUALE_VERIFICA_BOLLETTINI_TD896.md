# Mini manuale di verifica bollettini TD 896 GAIA

Aggiornamento del 2026-08-20.

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
5. Controllare denominazione del contribuente, scadenza e causale.
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
- il Data Matrix viene letto senza ritagliare o alterare le aree bianche che lo
  circondano.

Questa verifica controlla la coerenza dei dati prodotti da GAIA. L'omologazione
formale della stampa in proprio e dei posizionamenti OCR resta soggetta alla
procedura di autorizzazione di Poste Italiane.

## Fonti archiviate

Le copie dei manuali Poste Italiane consultati, con edizione e checksum, sono
elencate in [`riferimenti-td896/README.md`](riferimenti-td896/README.md).
