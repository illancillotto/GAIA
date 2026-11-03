# Manuale operativo

## Amministrazione

Aprire /gaia/communications come admin/super_admin. Creare account disabilitato/
in pausa: canale/provider, indirizzo/display name, endpoint TLS, username,
metodo auth e secret_ref. Non incollare password nei campi. Impostare utenti
autorizzati, default Ruolo/canale, priorità, dimensione MIME e limite orario.

Guide ufficiali consultate il 2026-11-03, HTTP200:

- [Aruba PEC, client e dispositivi](https://guide.aruba.it/pec/configurazione-programmi-di-posta/client-posta-e-dispositivi-mobili):
  imaps.pec.aruba.it:993, smtps.pec.aruba.it:465, SSL/TLS.
- [Aruba email, parametri](https://guide.aruba.it/hosting-e-domini/email/configurazione-posta/parametri-configurazione-posta):
  imaps.aruba.it:993, smtps.aruba.it:465, SSL/TLS.

Verificare contratto/prodotto/dominio e autenticazione forte/password applicativa
della casella effettiva. Le guide elencano anche alternative: non copiarle
indistintamente. Nessun account reale collaudato. account.example.json usa
example.org e non è un preset per invii.

Montare file secret con nome secret_ref, leggibile da UID10001. Provisionare
CA/pin PEC approvati, mai certificati sintetici. I due seed template 2021
sono draft: serve approvazione competente. Modifiche creano nuove versioni.

Test e Acquisisci ricevute accodano job. Trasporto false = nessuna connessione.
Il test SMTP/IMAP non invia messaggi; la connessione reale richiede autorizzazione.

## Operatore Tributi

1. Solleciti → PEC/Email. Filtrare e paginare candidati 2021.
2. Aprire una riga, verificare recapito, account e template/testo. Creare snapshot.
3. Esaminare ogni pagina di tutti i PDF a sinistra: zoom/fit/navigazione/fullscreen
   e nuova scheda autenticata. Verificare nome, versione, dimensione e hash.
4. Verificare dati attuali; confermare gli otto controlli e approvare.
5. Invia PEC/Email accoda il worker. Monitorare stati e ricevute, senza
   interpretare submitted come consegna o perfezionamento legale.
6. Modifiche prima di queued richiedono nuova approvazione. Sorgente rigenerata:
   annullare prima di sending e creare nuova revisione. Snapshot inviato immutabile.

## Incidenti

- uncertain: non azzerare job/active_key né creare un nuovo invio. Conservare
  MIME/Message-ID, acquisire IMAP e aprire istruttoria con gestore.
- failed: esaminare codice/eventi; massimo tre retry sicuri. Nessun reinvio
  terminale automatico; procedura autorizzata separata.
- Ricevute non correlate/non verificate: conservare EML; verificare account,
  Message-ID/destinatario/CA/pin/formato. Non correggere stati tramite SQL.
- IMAP indisponibile: backoff poi failed; admin può accodare nuova acquisizione.
  UIDVALIDITY cambiata: rilettura readonly con deduplica hash. Messaggio oltre
  32 MiB blocca il cursore: triage autorizzato, senza eliminazione automatica.
- Worker fermo: health per processo e heartbeat DB. Lease prima di sending
  recuperabile; dopo sending uncertain. Riavvio solo dopo diagnosi.
- Emergenza: pausa globale/account, trasporto false e arresto servizio.
  Nessuna pausa può richiamare un DATA già iniziato.

Una operazione per account; più processi consentono parallelismo fra account.
Non si configurano più invii simultanei nella stessa casella nella v1.

I metadati completi della riga sorgente sono inclusi nel fingerprint: anche\ncambi di nominativo, soggetto, CF o importi senza rigenerazione bloccano il job.\n