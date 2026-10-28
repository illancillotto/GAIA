# Rilascio avvisi, portale e pagatore sul CED

## Stato operativo

Il 28 ottobre 2026, alle 10:43 Europe/Rome, e stato completato il rilascio
delle modifiche Ruolo del commit `b7cbc31a` su `http://gaia.lan`.
Backend e frontend sono healthy; maintenance disattivata. Il database e alla
revision `20261028_0900`.

Release e ricevute riservate sul server:
`/opt/gaia/releases/avvisi-final-20261028-b7cbc31a/`.
Il manifest autorevole di questo rilascio mirato e `release-manifest.json`
in tale directory; `current-release.txt` della root descrive il precedente
rilascio completo dello stack.

## Perimetro e conservazione degli hotfix

Sono aggiornati soltanto i servizi `backend` e `frontend`, mediante immagini
`gaia-backend:avvisi-final-20261028-b7cbc31a` e
`gaia-frontend:avvisi-final-20261028-b7cbc31a` costruite sulle immagini attive.
Sono preservati configurazione Compose effettiva, ambiente, volumi, porte,
comandi e servizi concorrenti. Il checkout storico `/opt/gaia` non viene
riallineato a main e non sono stati eseguiti push o deploy di altri moduli.

I sorgenti della feature provengono dal commit verificato. In `app/db/base.py`
e nel router Ruolo si aggiungono soltanto le registrazioni dei nuovi modelli
e delle route pagatore ai file attivi: restano escluse le superfici del
controllo particelle non comprese nel precedente rilascio server.
Il frontend usa i sorgenti dell'ultima release, sovrapponendo i nove file
della feature; i quattro file preesistenti coincidono con il parent testato.

## Migrazioni e dati

Le migration `20261027_0900` e `20261027_1100` erano gia applicate.
Sono applicate `20261027_1300` (termine di notifica) e `20261028_0900`
(trigger di revisione pagatore). I due trigger pagatore sono `ALWAYS`.

Le cinque regole esistenti conservano modalita `fixed_date` e date precedenti.
Non viene impostato automaticamente un termine a 60 giorni: la scelta e
disponibile nelle Regole ruolo; con bollettino richiede una data fissa.
I PDF gia generati non sono riscritti.

Le **12.353** righe di accesso al portale sono conservate e verificate mediante
decifratura senza esporre PIN o codici identificativi nei log. Le **sei**
utenze ambigue restano sospese, con invito a contattare gli uffici.
Nessuna nuova importazione Excel o assegnazione pagatore reale in questo ciclo.
Resta il limite documentato del DOCX singolo legacy: il pagatore assegnato e
applicato dal flusso a lotti della pagina Tributi, anche per anteprima singola.

Sono conservati anche i parametri postali preesistenti:
`TD896_SAMPLE_MODE=true`, senza `TD896_PRINT_AUTHORIZATION` configurata.
Il bollettino v1 mantiene quindi il segnaposto di campionatura; per l'invio
occorre la sua autorizzazione di stampa. V2 conserva invece l'autorizzazione
fissa del modello originale fornito, come richiesto dall'ufficio.

## Verifiche

- Build frontend di produzione completata, comprese lint, TypeScript e
  generazione di 164 pagine; restano warning legacy.
- **277 test superati** nell'immagine candidata, incluso il rendering reale
  PDF/QR. Un solo skip SQLite con equivalente PostgreSQL superato.
- Upgrade/downgrade/upgrade sulla copia isolata dello schema di produzione
  completati, fino all'unico head `20261028_0900`.
- Health, home, login e pagina Tributi HTTP 200; verifica dal PC verso il
  virtual host `gaia.lan` sul CED. Letture autenticate delle regole e del
  nuovo endpoint pagatore superate.
- PDF sintetico generato dal backend in produzione: quattro pagine, blocco
  Irrighiamo e termine di notifica, entrambi i tagliandi con
  `30/11/2026 - Rata Unica`. Nessun avviso o numero reale creato.
- Hash dei sorgenti distribuiti verificati; ambiente e working tree server
  invariati, servizi concorrenti preservati.

Gli strumenti PyMuPDF/zxing/Pillow necessari alle verifiche sono installati
soltanto nell'immagine di test. La prima esecuzione aveva tre failure per
assenza di PyMuPDF; dopo aver completato l'ambiente di validazione e stata
rieseguita l'intera selezione, senza modificare il runtime candidato.

Il primo tentativo di deploy ha superato gli smoke applicativi ma ha attivato
il rollback per un confronto troppo ampio del controllo operativo: Compose
aveva rimosso il vecchio container gia fermo
`gaia-backend-before-resume-20261027`, relativo allo stesso servizio.
Il confronto e stato corretto per verificare tutti i servizi attivi estranei
al rilascio. Il ripristino a `20261027_1100` e il successivo rilascio sono
entrambi completati; nessuna regressione applicativa rilevata.

## Backup e rollback

Backup riservati: `backup/schema-before.sql` e
`backup/affected-tables.dump` nella directory release. Contengono schema e
tabelle interessate; non sono versionati o pubblicati.
Le immagini precedenti sono conservate. L'immagine di rollback backend
include le due migration gia presenti nel filesystem del vecchio container.

In caso di ripristino operativo:

```bash
/opt/gaia/releases/avvisi-final-20261028-b7cbc31a/rollback.sh
```

Lo script abilita maintenance, ferma il backend, esegue il downgrade a
`20261027_1100` con l'immagine nuova, ripristina le immagini precedenti e
verifica health e login prima di disattivare maintenance. Il downgrade
rimuove la nuova colonna di modalita: dopo nuove modifiche alle regole,
acquisire prima un backup aggiornato dei relativi valori.

Evidenze locali di orchestrazione: `/tmp/gaia-deploy-avvisi-20261028/`.
Le verifiche locali complete del codice restano nel riepilogo finale di
`PROGRESS_ruolo.md` (1.295 test backend e 156 frontend, coverage runtime 100%).
