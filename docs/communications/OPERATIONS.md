# Manuale operativo

## Amministrazione

Aprire /gaia/communications come admin/super_admin. Creare account disabilitato/
in pausa: canale/provider, indirizzo/display name, endpoint TLS, username,
metodo auth e secret_ref. Non incollare password nei campi. Impostare utenti
autorizzati, default Ruolo/canale, priorità, dimensione MIME e limite orario.

### Eliminazione di una versione template

In **Template versionati**, premere **Elimina** sulla versione da rimuovere.
La conferma mostra nome, canale, codice e versione: **Annulla** lascia tutto
invariato; confermando viene eliminata solo quella versione. Le altre versioni
restano disponibili. Durante la richiesta i comandi sono disabilitati; in caso
di errore il messaggio resta visibile ed è possibile riprovare.

Il template eliminato sparisce dall'elenco e dalla selezione per nuove
comunicazioni. Testi, PDF e messaggi già creati restano conservati, insieme
all'audit della cancellazione. La numerazione non riparte da uno se si crea
un'altra versione dello stesso codice. Azione riservata a admin/super_admin.
Dettagli e verifiche: [TEMPLATE_DELETION_2026-11-07.md](TEMPLATE_DELETION_2026-11-07.md).


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

1. Solleciti → PEC/Email. La presenza del recapito del canale è preselezionata
   su Presente: PEC mostra inizialmente gli avvisi con PEC, Email quelli con
   email. Per consultare anche gli altri avvisi scegliere Tutti nel filtro
   corrispondente. Filtrare e paginare candidati 2021.
2. Cliccare la riga dell’avviso (oppure raggiungerla con Tab e premere Invio
   o Spazio): il pannello destro mostra l’avviso e il PDF. Se una comunicazione
   esiste già, si apre il suo storico. Il pulsante Componi non è più presente. Verificare
   recapito, account e template/testo, quindi creare bozza e snapshot.
3. Nel pannello destro, sotto i campi, esaminare ogni pagina di tutti i PDF: zoom/fit/navigazione/fullscreen
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

I metadati completi della riga sorgente sono inclusi nel fingerprint: anche
cambi di nominativo, soggetto, CF o importi senza rigenerazione bloccano il job.

Il rilascio mirato CED del 4 novembre è attivo: pagine PEC/email, amministrazione
e worker healthy. Pausa globale e trasporti disabilitati; zero caselle configurate.
Gli operatori accedono da Invio solleciti alle schede Invio PEC e Invio Email;
l'amministrazione è in `/gaia/communications`. Prima della composizione/invio
occorrono account utilizzabile, template approvato e collaudo autorizzato di
documenti, caselle e trust. Nessun invio reale eseguito dal rilascio.
Immagini, configurazione effettiva, backup/restore, verifiche e residui sono nel
[report operativo](DEPLOYMENT_REPORT_2026-11-04.md); il rollback usa gli artefatti
specifici di quella release. Non avviare lo stack intero e non riprendere Poste
come effetto collaterale di un riavvio Communications.

Layout sidebar pubblicato il 4 novembre alle 11:50 CET: elenco e composizione
a metà desktop, campi sopra PDF. Solo frontend sostituito; backend, worker e
stato effettivo di Posta Online preservati. Dettagli, collaudo e rollback in
[SIDEBAR_RELEASE_2026-11-04](SIDEBAR_RELEASE_2026-11-04.md).

## Classificazione PEC/email per le persone fisiche — predisposta, non rilasciata

Prima dell'uso applicare la migrazione `20261104_1400` in una finestra coordinata
backend/worker, con backup e trasporti disabilitati. Rieseguire il confronto dei
recapiti 2021 prima del backfill: lo snapshot Excel/JSON del 04/11 non autorizza
sovrascritture successive. L'API admin GET/PUT dei contatti usa soggetto canonico,
tipo e stato espliciti, riferimento alla fonte e `expected_version` (0 per creare).
Non automatizzare una scelta fra indirizzi multipli, attivare revocati o dedurre
PEC dal dominio. I 14 discordanti restano ai colleghi per revisione.

La tabella di classificazione è condivisa da aziende e persone; l'ordinaria email
storica non prova il tipo di canale. Applicare anche le righe `unclassified/review`
del piano validato per evitare che il vecchio campo venga usato come fallback.
Nessun trasporto di prova è necessario alla classificazione. L'indirizzo con sintassi
invalida va corretto o rimosso solo dopo verifica, non attivato dal piano.
Guida e report: CONTACT_CLASSIFICATION_2026-11-04.md.

## Anteprima immediata — 4 novembre 2026

Il PDF si carica subito cliccando la riga o selezionando la checkbox, anche senza account. Per un errore usare Riprova anteprima. Se la creazione restituisce PDF modificato, riaprire l’avviso e ricontrollare il documento. La consultazione non sostituisce la checklist individuale.

Dettagli: [SOURCE_PREVIEW_2026-11-04](SOURCE_PREVIEW_2026-11-04.md).

## Registro recapiti operativo dal 05/11/2026

Il filtro Presente usa persone e aziende: al rilascio 47 righe PEC e una email.
Quattro valori invalidi sono in quarantena e non sono proposti. Il report
ufficio consente di annotare recapito, canale, fonte/data ed esito; non applica
correzioni da Excel. I 14 discordanti richiedono verifica documentata.
Prima degli invii restano account e trasporti disabilitati: [CONTACT_RELEASE_2026-11-05](CONTACT_RELEASE_2026-11-05.md).
