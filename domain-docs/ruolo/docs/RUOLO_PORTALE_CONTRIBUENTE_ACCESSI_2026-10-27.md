# Accessi personali al portale del contribuente

Stato: 2026-10-27. Il blocco della prima pagina del template GAIA precede il
paragrafo con contatti degli uffici e informazioni sul sito del Consorzio, quindi i due riquadri affiancati WhatsApp e Irrighiamo Insieme. Riporta il percorso
`www.bonificaoristanese.it > Cartella contribuenza >`, la spiegazione del servizio
e una sola coppia **Codice ditta / PIN** per utenza del destinatario. Il percorso mantiene il link
al portale inCatasto `cons=090`. Il QR portale non viene più stampato.

Quando le credenziali mancano o il codice fiscale identifica piu utenze senza
un collegamento verificato con l'avviso, viene stampato:

> Per ottenere i dati di accesso contattare gli uffici del Consorzio.

La regola confermata dall'ufficio e: **un avviso -> un'utenza -> un Codice ditta/PIN**.
I sei CF con due utenze restano sospesi in attesa del riscontro dei colleghi.
Non viene scelta la prima coppia e non si stampano entrambe. Anche la
rigenerazione da snapshot storici con piu coppie usa il messaggio uffici.
Il CF univoco consente la stampa dell'unica coppia disponibile. Il QR WhatsApp resta accompagnato dalla spiegazione e
dall'invito a inquadrarlo; il secondo QR apre `https://login.bonificaoristanese.it/`
per accedere a Irrighiamo Insieme, senza usare il PIN inCatasto come credenziale
dell'applicazione. La dicitura «Apri il canale WhatsApp» è eliminata.

## Fonte e associazione

- File fornito dall'ufficio: `incass-pin-password.xlsx`, foglio attivo.
- Colonne richieste e univoche: `CodFisc`, `Utenza`, `PIN`.
- `Utenza` è il Codice ditta da stampare. Il codice utenza tecnico dei tracciati
  di ruolo non è usato per dedurre le credenziali.
- Il codice fiscale viene normalizzato con trim e maiuscole. Il confronto è
  esatto; nessun collegamento per nominativo, indirizzo o somiglianza.
- Gli zeri iniziali dei testi e dei numeri con formato Excel `000...` sono
  conservati. Non vengono inventati zeri per valori numerici in formato General.
- Le righe senza le tre chiavi sono saltate, compresa la riga totale del file.
  Un codice fiscale mancante con credenziali presenti blocca l'importazione.
- Intestazioni mancanti/duplicate, valori non validi, formule nelle credenziali
  e coppie discordanti per lo stesso Codice ditta bloccano tutto prima della
  scrittura. Duplicati identici vengono conteggiati e accorpati.
- Più Codici ditta per lo stesso codice fiscale sono ammessi. Un Codice ditta
  già associato nel DB a un altro codice fiscale blocca l'importazione.

## Persistenza e generazione

`ruolo_taxpayer_portal_access` ha Codice ditta come chiave primaria, codice
fiscale indicizzato, PIN cifrato Fernet, hash SHA-256 della fonte e data import.
Usa la `CREDENTIAL_MASTER_KEY` già configurata per le credenziali GAIA.
Il PIN deve poter essere decifrato per la stampa: non è un hash password.

L'importazione aggiorna PIN variati ed è idempotente. Non elimina gli accessi
assenti in un successivo file parziale e non crea anagrafiche. Le righe con PIN
invariato mantengono cifrato, hash fonte e data della precedente acquisizione.
L'invalidazione delle revisioni di generazione usa i trigger PostgreSQL ALWAYS
installati dalla migration `20261027_1100`.

`notice_candidates.batch_candidates` acquisisce gli accessi **dopo** l'eventuale
riassegnazione del pagatore. Il payload persistito contiene il Codice ditta e
il PIN ancora cifrato; la decifratura avviene solo durante il rendering HTML.
Il pagatore non riceve le credenziali dell'intestatario originario. I documenti
gia generati e gli snapshot persistiti restano invariati, anche se il PIN viene aggiornato.
La rigenerazione HTML da uno snapshot storico multi-utenza applica invece
l'attuale regola di sospensione, senza decifrare quelle credenziali.
Un cifrato corrotto o una chiave non valida blocca la stampa, senza inventare
un PIN. La chiave va conservata anche per ristampare gli snapshot storici.

## Comandi di importazione

Applicare prima le migration fino a `20261027_1100`. La dipendenza
`20261027_0900` crea anche la tabella delle assegnazioni pagatore.

Dal backend configurato per il DB di destinazione:

```bash
python -m app.scripts.import_taxpayer_portal_access /percorso/incass-pin-password.xlsx
python -m app.scripts.import_taxpayer_portal_access /percorso/incass-pin-password.xlsx --apply
```

Il primo comando esegue un dry run con rollback. `--apply` conferma un'unica
transazione. Un errore causa rollback; non esistono commit per singola riga.
L'output contiene soltanto conteggi, stato apply e hash fonte, senza PIN o
codici fiscali. Non versionare il file, estrazioni o anteprime con accessi reali.

## Importazione sul server degli uffici

Destinazione verificata: `serverCed`, stack `/opt/gaia`, DB del backend attivo.
Importazione eseguita il 2026-10-27, con backup dello schema e dei metadati
versione/revisione prima delle due migration additive. Nessun avviso viene
modificato. Le migration sono disponibili anche nel repository server e
nell'immagine attiva, affinché la revisione resti risolvibile.

| Controllo | Esito |
| --- | --- |
| Righe di accesso | 12.353 |
| Codici fiscali distinti | 12.347 |
| Codici fiscali con due coppie | 6 |
| Riga totale saltata | 1 |
| Nuovi record confermati | 12.353 |
| Differenze dopo confronto Excel/DB con decifratura | 0 |
| Ripetizione dry run | 12.353 invariati, 0 nuovi, 0 aggiornati |
| Codici fiscali già presenti negli avvisi | 12.339 |
| Codici fiscali senza avvisi attuali | 8, conservati per stampe future |
| Avvisi prima/dopo | 176.114, invariati |
| Revisione finale | `20261027_1100` |
| Trigger di revisione | entrambi ALWAYS |

Hash fonte: `bfb0f82972b1989c7703aec015a7b9651bdf7b653f2d8cbd11d54084f2a5ec8a`.
Ricevute e backup riservati: `/opt/gaia/runtime-data/portal-import-20261027/`.
La sorgente originale sul PC dell'ufficio resta intatta.

L'importazione dati è attiva sul server. La nuova grafica e il collegamento
degli accessi alla generazione sono nel checkout di sviluppo: il backend attivo
non è stato sostituito con le altre modifiche concorrenti presenti nel repository.
Occorre il rilascio del codice verificato per usarli nelle nuove stampe dell'app.

## Verifiche

I test coprono lettura Excel, zeri e formati, errori e duplicati, cifratura,
upsert, rollback, idempotenza CLI, snapshot storici, destinatario riassegnato,
mancanza di dati, sospensione delle utenze ambigue, snapshot storici multi-utenza,
escape HTML e cifrato corrotto. La migration e i
trigger sono esercitati anche su PostgreSQL reale in uno schema temporaneo.
Verifica finale del ciclo accessi/riepilogo: **221 PASS, zero skip**, coverage
statement/branch **100%** su 14 runtime (1469 statement, 390 branch), senza
esclusioni. Comprende testi, scadenze, bollettini v1/v2, importazione,
transazioni PostgreSQL reali e regressioni degli accessi.
Ruff/formatter, lint backend e ratchet sul merge-base superati. La verifica
della baseline riguarda il perimetro modificato, senza certificare altri
sviluppi concorrenti. Le stampe Chromium coprono 2021, due e cinque annualita,
una coppia per utenza e fallback degli snapshot storici ambigui, QR WhatsApp
decodificato dal PDF a 144 dpi e distanza QR/privacy contenuta.
L'anteprima 2021 usa esclusivamente dati dimostrativi, indicati su ogni pagina.
Non è stata eseguita una prova con stampante fisica o l'accesso al portale con
le credenziali dei contribuenti.
