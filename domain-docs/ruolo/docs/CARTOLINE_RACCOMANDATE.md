# Cartoline scansionate: Raccomandate e Utenze

Il PDF e un documento canonico `ana_documents` del contribuente. La tabella
`ruolo_registered_mail_documents` lo collega alla raccomandata senza creare
una seconda copia applicativa. La gestione locale e l'eventuale copia nella
cartella NAS riusano le primitive documentali Utenze.

## Uso

In Ruolo, tabella Raccomandate, aprire **Cartoline scansionate**. La finestra
mostra i PDF, la data di scansione, l'anteprima e il download autenticato.
Il medesimo documento compare nel dettaglio del soggetto Utenze con tipo
`cartolina_raccomandata` e tracking nelle note.

Per caricare: associazione confermata senza anomalie, avvisi tutti dello stesso
soggetto, PDF fino a 20 MiB, data scansione e verifica operatore del tracking
e del destinatario sulla cartolina. Il tracking dichiarato deve coincidere
con quello della raccomandata: si eliminano solo spazi e trattini, senza
correggere cifre o aggiungere zeri. Riordino fondiario escluso.

Il controllo server del file verifica estensione e firma PDF, non esegue OCR
ne determina automaticamente il tracking stampato. La verifica visiva resta
responsabilita dell'operatore. Nome, indirizzo o data scansione da soli non
autorizzano l'attribuzione a un soggetto.

## Contratti

- `GET /ruolo/tributi/raccomandate/{mail_id}/cartoline`: elenco e metadati.
- `POST /ruolo/tributi/raccomandate/{mail_id}/cartoline`: multipart con `file`,
  `tracking_number`, `scanned_on`, `source_reference` opzionale (max 1024).
- `GET /ruolo/tributi/raccomandate/{mail_id}/cartoline/{card_id}/download`:
  download del documento canonico, con recupero locale/NAS Utenze.

Lettura: modulo Ruolo e sezione `ruolo.tributi.view`. Scrittura: anche sezione
`ruolo.tributi.manage_status` e modulo Utenze. In Utenze valgono i permessi
documentali gia esistenti; nessun endpoint file pubblico o URL NAS diretto.

Upload idempotente per raccomandata/SHA256, serializzato tramite lock della
raccomandata e vincolo univoco SQL. Ripetere lo stesso PDF restituisce il
documento esistente, senza cambiare metadati o duplicare file/audit. PDF
diversi restano documenti separati. Documento, collegamento e audit del
soggetto vengono persistiti in una sola transazione.

Il salvataggio NAS non e una transazione SQL: se la scrittura NAS fallisce,
il file locale provvisorio e rimosso e nessun documento viene collegato.
Se fallisce il commit SQL dopo una copia NAS riuscita, il locale viene
rimosso e la copia NAS puo restare senza collegamento: va verificata prima
di ritentare, senza cancellazioni NAS automatiche.

Una cartolina non determina annualita, notifica, consegna o pagamento e non
cambia `sent_at`, `status_label`, `annualita_json` o le associazioni agli avvisi.
La data del riepilogo Cartoline.xlsx e **data scansione**, confermata
dall'operatore, non data di invio.

La riassociazione manuale a un contribuente diverso, o la rimozione del
contribuente, e bloccata con 409 se sono presenti cartoline. Le letture
falliscono con 409 se dati esterni alterano il soggetto rendendolo incoerente
con il documento: nessun trasferimento automatico. Cancellazione del documento
Utenze e reset documentale sono bloccati con 409; le FK RESTRICT proteggono
anche la cancellazione SQL diretta. Una rimozione/correzione richiede revisione
esplicita separata, non un pulsante di cancellazione silenziosa.

## Rollout

Migration `20261002_1030`, successiva all'head corrente `20261001_1600`.
Prima del deploy verificare la catena delle migration del checkout, incluse
quelle gia presenti per altri lavori; non applicare migration incomplete o
estranee implicitamente in produzione. Applicare lo schema prima delle route
nuove e della guardia di associazione; poi distribuire backend e frontend.

Non sono inclusi deploy, import massivo dal NAS o nuove associazioni delle
residue. Il backfill richiede manifest validato per tracking, identita,
documento e provenienza; i casi senza contribuente confermato restano esclusi.
