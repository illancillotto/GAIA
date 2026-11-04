# GAIA Communications — PRD

Implementazione locale, collaudo sintetico; nessuna autorizzazione a produzione
o comunicazioni reali. Primo utilizzatore: Ruolo/Tributi, solleciti definitivi
esclusivamente 2021. I criteri software non certificano atti o recapiti.

## Operatori e funzioni

- Permesso ruolo.tributi.view: elenco, storico, snapshot e ricevute del dominio.
- Permesso ruolo.tributi.manage_status: composizione, allegati PDF, validazione,
  approvazione individuale, accodamento e annullamento consentito.
- Admin/super_admin: account, endpoint, utenti autorizzati, template versionati,
  test asincroni, pause e monitoraggio. Secret provisionati fuori da DB/UI.

Solleciti offre Generati, Posta Online, PEC ed Email. Nessuna spedizione HTTP.
La pagina PEC/email divide lo spazio desktop in due colonne uguali: elenco
a sinistra e compositore persistente a destra. Componi carica i campi dell’avviso
selezionato; nella sidebar i campi precedono il PDF e la checklist. Su mobile
i pannelli sono verticali. Il PDF compare dopo la creazione della bozza e del
suo snapshot immutabile. La revisione UI del 4 novembre è pubblicata sul CED dopo la risoluzione del
quality gate; verifiche e stato in SIDEBAR_RELEASE_2026-11-04.md.
Ogni allegato deve essere renderizzato integralmente e controllato esplicitamente
con otto conferme. La modifica incrementa la versione e invalida l'approvazione.
Elenco paginato/filtrato dal server; nessuna approvazione massiva.
All’apertura PEC, Presenza PEC è Presente; all’apertura Email, Presenza email
è Presente. Il vincolo del canale è inviato già nella prima richiesta; l’altro
canale non viene escluso. L’operatore può scegliere Tutti o Assente.

## Vincoli

Solo righe generated, annualità esattamente [2021], numero definitivo riservato
e documento Registro coerente. Pagamenti, STEP, storico non chiarito, notifiche
e prenotazioni Poste/Communications bloccano. Riutilizzo delle regole Registro,
nessuna nuova formula tributaria.

Snapshot e MIME/EML nel DB protetto. Limiti: 32 MiB, 200 pagine complessive,
dieci PDF; limite MIME inferiore configurabile. Primo allegato obbligatorio.
Rendering e lettura umana sono distinti; la checklist registra una dichiarazione.

Email solo cortesia, testo semplice; CC/CCN e HTML disabilitati nella prima
versione. Accettazione SMTP = submitted, mai notifica legale. PEC classificata
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
