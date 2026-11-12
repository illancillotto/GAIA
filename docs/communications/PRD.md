# GAIA Communications — PRD

## Editor implementato — 12 novembre 2026

L’amministratore compone template con logo ufficiale, titoli, paragrafi, elenchi,
link o pulsanti HTTPS; aggiunge, sposta o rimuove blocchi, inserisce campi
catalogati e vede l’anteprima. Salvataggio bozza e approvazione sono separati.
I modelli esistenti restano modificabili e convertibili. Nel compositore
operativo un solo template approvato viene preselezionato e compilato;
anteprima messaggio e modifica sono apribili senza sottrarre spazio al PDF.
Stato implementato, collaudo e rilascio: [Template grafici e verifica finale](RICH_TEMPLATES_2026-11-12.md).


Stato aggiornato al 9 novembre 2026: i modelli ufficio sono stati pubblicati alle 14:58:35 CET; le indicazioni precedenti «locale/non rilasciato» descrivono lo stato del 7 novembre. Verifiche e limiti correnti: [rapporto di rilascio](OFFICE_TEMPLATES_RELEASE_2026-11-09.md). Nessuna abilitazione degli invii reali.

Piattaforma pubblicata sul CED; collaudo dei trasporti ancora sintetico e invii
reali disabilitati. Il rilascio della UI non abilita le caselle. Primo utilizzatore: Ruolo/Tributi, solleciti definitivi
esclusivamente 2021. I criteri software non certificano atti o recapiti.

## Operatori e funzioni

Il gestore offre modelli di partenza PEC/email adattati all'esempio dell'ufficio,
con dati del singolo avviso, totale/termine del PDF, portale, codice utenza e
PIN verificabili. La scelta popola un form modificabile; salvataggio draft e
approvazione restano distinti. Fonti, audit PIN e limiti nel
[report modelli ufficio](OFFICE_TEMPLATES_2026-11-07.md). Modelli pubblicati il 9 novembre;
controlli inCASS e revisione PDF con accessi aggiunti il 12 novembre (COMPOSITION_CHECKS_2026-11-12.md).

- Permesso ruolo.tributi.view: elenco, storico, snapshot e ricevute del dominio.
- Permesso ruolo.tributi.manage_status: composizione, allegati PDF, validazione,
  approvazione individuale, accodamento e annullamento consentito.
- Admin/super_admin: account, endpoint, utenti autorizzati, template versionati,
  test asincroni, pause e monitoraggio. Secret provisionati fuori da DB/UI.
- Ogni versione template può essere eliminata dall'amministratore dopo una
  conferma che identifica nome, canale, codice e versione. Scompare dalle
  selezioni future; testi e messaggi già creati, altre versioni e audit restano
  conservati. Cancellazione logica, senza invii o nuove migrazioni.

Solleciti offre Generati, Posta Online, PEC ed Email. Nessuna spedizione HTTP.
La pagina PEC/email divide lo spazio desktop in due colonne: elenco
più stretto a sinistra e composizione più ampia a destra. Il clic sulla riga carica i campi dell’avviso
selezionato; nella sidebar i campi precedono il PDF e la checklist. Su mobile
i pannelli sono verticali. Il PDF sorgente compare subito alla selezione; la creazione della bozza ne
verifica l’hash e crea lo snapshot immutabile. La revisione UI del 4 novembre è pubblicata sul CED dopo la risoluzione del
quality gate; verifiche e stato in SIDEBAR_RELEASE_2026-11-04.md.
Ogni allegato deve essere renderizzato integralmente e controllato esplicitamente
con otto conferme. La modifica incrementa la versione e invalida l'approvazione.
Elenco paginato/filtrato dal server; nessuna approvazione massiva.
All’apertura PEC, Presenza PEC è Presente; all’apertura Email, Presenza email
è Presente. Il vincolo del canale è inviato già nella prima richiesta; l’altro
canale non viene escluso. L’operatore può scegliere Tutti o Assente.

## Vincoli

Solo righe generated, annualità esattamente [2021], numero definitivo GAIA
riservato oppure identità inCASS verificata e documento Registro coerente. Pagamenti, STEP, storico non chiarito, notifiche
e prenotazioni Poste/Communications bloccano. Riutilizzo delle regole Registro,
nessuna nuova formula tributaria.

Snapshot e MIME/EML nel DB protetto. Limiti: 32 MiB, 200 pagine complessive,
dieci PDF; limite MIME inferiore configurabile. Primo allegato obbligatorio.
Rendering e lettura umana sono distinti; la checklist registra una dichiarazione.

Email solo cortesia. Sono supportati testo semplice e template grafici a blocchi
con alternativa testuale; CC/CCN e HTML libero restano esclusi. Accettazione SMTP = submitted, mai notifica legale. PEC classificata
come certificata solo con verifica CMS, CA e pin approvati.

## Accettazione

Evidenze riproducibili in TEST_REPORT.md. Mock e certificati sintetici verificano
il software, non i provider reali. Testi, trust, conservazione, recapiti e collaudo
provider restano all'ente (OPEN_DECISIONS.md). Nessun reinvio automatico di
incerti/terminali. Il completamento locale non autorizza il rilascio.

## Verifica conclusiva dello sviluppo

La matrice in FINAL_REVIEW.md collega i comportamenti implementati alle prove
automatizzate; PROGRESS.md registra le attività completate e quelle esterne
residue. La chiusura aggiunge test di integrazione senza nuove funzionalità.
L'operatività2021 resta subordinata alle regole reali di gestione Ruolo/STEP.

Il gate finale complessivo resta FAIL per i limiti della regressione generale
dettagliati in FINAL_REVIEW.md; il100% locale non equivale a PASS globale.

## Chiarimento recapiti — 04/11/2026

La disponibilità dei due canali deve comprendere aziende e persone fisiche,
tramite recapiti tipizzati collegati all'anagrafica esistente. Indirizzi non
classificati, in revisione o revocati non devono diventare destinatari suggeriti;
più indirizzi attivi del medesimo canale richiedono revisione. Non inferire PEC
dal solo dominio. L'API amministrativa versionata e il resolver sono implementati
nel checkout, con migrazione ancora da rilasciare; UI Utenze e automatismi di sync
non inclusi. Stato e verifica 2021: CONTACT_CLASSIFICATION_2026-11-04.md.

## Anteprima immediata — 4 novembre 2026

Il clic sulla riga e la checkbox devono mostrare subito il PDF reale sotto i campi, senza creare una bozza o richiedere un account. Tutte le pagine devono essere renderizzate prima di creare lo snapshot; hash sorgente verificato server-side.

Dettagli: [SOURCE_PREVIEW_2026-11-04](SOURCE_PREVIEW_2026-11-04.md).

## Revisione righe PEC/email — 2026-11-06

Il pulsante Componi è sostituito dall’attivazione della riga, con clic o
Invio/Spazio da tastiera. Si apre lo storico quando esiste una comunicazione,
altrimenti il compositore con PDF. Permessi invariati: sola lettura ammessa
solo per lo storico, nuova bozza riservata agli operatori autorizzati.
La checkbox e Nuova revisione non propagano il clic alla riga; durante un
caricamento i comandi di apertura sono bloccati. Nessuna creazione o spedizione
automaticamente provocata dal clic. Verifiche e rilascio nel
[report Ruolo](../../domain-docs/ruolo/docs/SOLLECITI_WORKSPACE_2026-11-06.md).
