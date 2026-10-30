# Rigenerazione dei PDF dei solleciti

## Problema

Il 29 ottobre 2026 l'anteprima di un lotto generato rispondeva «Documento
sollecito non trovato». I PDF delle anteprime e dei solleciti singoli erano
salvati in `/tmp/gaia_ruolo_tributi_reminders` dentro il container backend:
ogni rilascio o riavvio li cancellava, mentre il DB conservava il percorso.
I PDF ufficiali nella cartella NAS dell'utenza (`/volume1/.../solleciti/`) non
erano coinvolti.

## Cosa fa GAIA

- **Archivio permanente.** I PDF fuori dal NAS vanno in
  `RUOLO_REMINDER_STORAGE_PATH`, predefinito `<repo>/runtime-data/ruolo/solleciti`.
  Nel container è `/runtime-data/ruolo/solleciti`, su `/opt/gaia/runtime-data`,
  che sopravvive ai rilasci. Non serve modificare `.env`.
- **Un PDF mancante si ricostruisce.** Se il file locale di un sollecito
  generato non c'è più, il backend lo rigenera dai dati salvati alla generazione
  (`payload_json`) e lo scrive nell'archivio permanente. Vale per:
  - anteprima e download del sollecito di un lotto;
  - download del sollecito singolo (DOCX);
  - creazione di un lotto Posta Online, che copia il PDF.

  Il PDF ricostruito usa il layout attuale. Se la ricostruzione fallisce, il
  download risponde 503 «PDF non ricostruibile» e il lotto Poste rifiuta il
  sollecito.
- **Rigenerazione su richiesta.** Nella pagina **Invio solleciti**, scheda
  «Solleciti generati», riquadro **Rigenera PDF**, solo con
  `ruolo.tributi.manage_status`:
  - *Quali solleciti:* tutti i lotti oppure il lotto selezionato.
  - *Solo template:* stessi dati salvati, layout attuale. Serve dopo una
    modifica al template.
  - *Ricalcola dati e regole:* importi, pagamenti e regole del ruolo di oggi,
    con lo stesso numero avviso, progressivo e anni di riferimento. Aggiorna
    anche importi e `payload_json` del sollecito. Se le posizioni sono saldate
    o cambiate, il sollecito viene saltato: va generato un nuovo sollecito.

  La pagina elabora un sollecito per richiesta, in ordine. Mostra
  l'avanzamento e i saltati o falliti con il motivo, e si può fermare tra due
  PDF. Deve restare aperta fino alla fine. Rilanciare è sicuro: ogni
  rigenerazione è indipendente.

## Regole decise con l'ufficio

- Si rigenerano anche i solleciti già caricati su Poste, spediti o notificati.
  Un lotto Posta Online già creato conserva la propria copia del PDF, quella
  caricata su Poste.
- La copia ufficiale sul NAS viene sovrascritta, senza conservare la versione
  precedente.
- Ogni rigenerazione di un documento presente nel Registro avvisi aggiunge un
  evento di audit `regenerate_document`, con operatore, modalità, numero avviso
  e percorso prima e dopo, e incrementa la versione del documento. Il documento
  originale del Registro non viene modificato. Le anteprime non sono nel
  Registro e non hanno audit.
- Le bozze 2022/2023 sono escluse: il loro PDF sta nel DB (`NoticeDraft`), non
  si perde, e rigenerarlo invaliderebbe conferme ed export già fatti. Il report
  le conta come escluse.
- Non si rigenerano i solleciti falliti o senza PDF definitivo.

## Limiti

- Un file sul NAS che non si riesce a leggere non viene ricostruito in
  automatico, perché l'errore può essere di rete. Si usa la rigenerazione su
  richiesta.
- Il ricalcolo riconosce la posizione solo se gli avvisi del sollecito
  coincidono con quelli calcolati oggi.

## Codice e test

- Backend: `services/notice_pdf_regeneration.py`, route
  `routes/notice_regeneration_routes.py`
  (`GET /ruolo/tributi/solleciti/regeneration-targets`,
  `POST /ruolo/tributi/solleciti/items/{id}/regenerate`). I due download
  (`/ruolo/tributi/solleciti/items/{id}/download` e
  `/ruolo/tributi/reminders/{id}/download`) sono stati spostati senza cambiare
  percorsi e permessi da `routes/tributi_routes.py` a
  `routes/reminder_document_routes.py`. Inoltre: lettura del PDF in
  `services/poste_dispatch.py`, `notice_drafts.publishable`, impostazione in
  `app/core/ruolo_settings.py`.
- Frontend: `components/ruolo/solleciti/regeneration-panel.tsx`,
  `lib/ruolo-regeneration-api.ts`.
- Test: `backend/tests/ruolo/test_notice_pdf_regeneration.py`,
  `frontend/tests/unit/ruolo-regeneration-panel.test.tsx`,
  `frontend/tests/unit/ruolo-regeneration-api.test.ts` e gli scenari nella
  pagina Invio solleciti.

## Pagina Invio solleciti e solleciti non generati

Modifiche del 2026-10-29 pomeriggio, dopo il rilascio delle 16:16.

- **Layout.** Il banner è sostituito da una nota su una riga accanto alle
  schede: INVIA lo preme sempre l'operatore su Posta Online. Il riquadro
  «Rigenera PDF» è chiuso: «Mostra opzioni» lo apre, e il resoconto resta
  visibile anche chiudendolo. La paginazione sta nella testata di «Lotti
  generati» e compare solo con più di 50 lotti. Su schermi larghi la lista
  lotti resta ferma e scorre da sola.
- **Selezione dalla lista.** Ogni lotto con solleciti in PDF ha una checkbox
  «Seleziona per Posta Online» che seleziona o toglie tutti i suoi solleciti,
  sempre entro 50. La barra «Carica su Poste» compare solo con almeno un
  sollecito selezionato e resta fissa in basso.
- **PEC.** Nella lista un lotto mostra «Inviato via PEC» se un suo avviso ha una
  spedizione PEC rilevata in inCASS. È la stessa regola del riquadro «Via PEC»
  della pagina Tributi (`mailing_delivery` presente). Nel dettaglio il
  sollecito mostra «Avviso già inviato via PEC». Un lotto con generazione fallita
  mostra «PDF non generato».
- **Anteprima aperta.** Il PDF generato si apre con il lotto, per i primi 5
  solleciti; gli altri restano su «Anteprima avviso».
- **Solleciti `failed`.** Quando chi ha `ruolo.tributi.manage_status` apre il
  lotto, GAIA rigenera subito il PDF con i dati salvati e lo mostra. Il file va
  dove sarebbe andato alla prima generazione: cartella NAS `solleciti/`
  dell'utenza, oppure archivio permanente per le anteprime. Il nome resta
  quello originale, con il numero inCASS se l'avviso lo usa. Poi il sollecito
  diventa `generated`, il numero riservato passa a `generated`, i contatori e lo
  stato del lotto si aggiornano e il documento entra nel Registro avvisi, come
  una generazione riuscita. Se fallisce ancora, la pagina mostra il motivo e
  «Riprova a generare». Chi ha solo la visualizzazione vede il motivo
  registrato.
  - Non si rigenerano i `failed` senza numero avviso, quelli 2022/2023 e quelli
    di un lotto bozza privato.
  - Senza cartella NAS dell'utenza resta `failed` con «Cartella archivio NAS
    mancante per l'utenza»: la cartella va sistemata in anagrafica e il
    sollecito rigenerato.
  - «Rigenera PDF» include anche questi solleciti.
- **API.** `GET /ruolo/tributi/solleciti/batch-overview?batch_id=…` (fino a
  100 lotti, `ruolo.tributi.view`) restituisce per lotto i solleciti con
  `status`, `sendable` e `pec_sent`.
- **Codice.** Backend: `services/reminder_batch_overview.py`,
  `routes/reminder_batch_overview_routes.py`, rigenerazione dei `failed` in
  `services/notice_pdf_regeneration.py`. Frontend in
  `components/ruolo/solleciti/`: `batch-list.tsx`, `batch-overview.tsx`,
  `notice-cards.tsx`, `failed-notice.tsx`. Lista lotti e schede avviso sono
  passate da `workspace.tsx` ai moduli nuovi, così le funzioni legacy non
  crescono.
- **Test.** `backend/tests/ruolo/test_reminder_batch_overview.py`, 5 test nuovi
  in `test_notice_pdf_regeneration.py`, scenari in
  `frontend/tests/unit/notice-solleciti-page.test.tsx` ed e2e
  `ruolo-invio-solleciti.spec.ts`.

## Rilascio

In produzione sul CED dal 2026-10-29 alle 16:16, release
`pdf-regen-20261029-428aff0d`. I PDF persi prima del rilascio si ricostruiscono
alla prima apertura dell'anteprima o con «Rigenera PDF». Ripristino:
`/opt/gaia/releases/pdf-regen-20261029-428aff0d/rollback.sh`.

Le modifiche della pagina Invio solleciti e la rigenerazione dei `failed` sono
in produzione dalle 17:08, release `solleciti-ui-20261029-f73be942`. Ripristino:
`/opt/gaia/releases/solleciti-ui-20261029-f73be942/rollback.sh`.

## PDF falliti con SIGTRAP o SIGABRT (2026-10-30)

- **Causa.** Ogni Chromium usa circa 200 thread e il container backend ne ammette
  512 (`pids_limit`). Più PDF generati insieme (lotti, anteprime, rigenerazione
  automatica dei `failed`) esaurivano il limite: Chromium moriva con `SIGTRAP` o
  `SIGABRT`, oppure restava bloccato e faceva fallire ogni PDF successivo.
- **Correzione.** `services/notice_html_pdf.py` genera un PDF alla volta in tutto
  il container (lock `fcntl` su file, valido fra i worker uvicorn), termina un
  Chromium che supera 90 secondi e passa `--disable-dev-shm-usage` (la memoria
  condivisa del container è di 64 MB). Test: `tests/ruolo/test_notice_html_pdf.py`.
- **Rilascio.** CED 2026-10-30 alle 11:09, commit `482af0aa`, release
  `pdf-lock-20261030-482af0aa`, solo backend. Prima del rilascio: 31 test e
  quattro PDF reali in parallelo superati nell'immagine candidata con limite di
  512 processi; dopo il rilascio un PDF reale nel backend attivo. Ripristino:
  `/opt/gaia/releases/pdf-lock-20261030-482af0aa/rollback.sh`.
- **Dopo il rilascio.** I solleciti falliti si ripetono con «Rigenera PDF» su
  tutti i lotti, oppure aprendo il lotto.

## Nomi lunghi sul bollettino v2 (2026-10-30)

Nome, indirizzo o città che a 6 pt non entrano nel bollettino v2 non bloccano più
il PDF. GAIA abbrevia le forme societarie (Soc. Agr., S.S., S.r.l., Soc. Coop.,
Coop., F.lli) e, se il testo è ancora lungo, lo taglia con «…». Il testo che
entra e la lettera restano invariati. Codice: `_fit` in
`services/bollettino_v2.py`. Commit `9cc5999c`.

## Avvisi da sollecitare per anno (2026-10-30)

Riquadro in cima a Invio solleciti, per chi ha `ruolo.tributi.manage_status`,
pensato per chi ha poca dimestichezza digitale: si sceglie l'anno (dal 2021),
si leggono tre numeri e si preme un pulsante.

- **Avvisi dell'anno.** Gli stessi del wizard Tributi: candidati dell'anno con le
  regole GAIA (`manager_key=gaia`), divisi per avviso come in stampa.
- **Pronto.** Un avviso è pronto quando tutti i suoi avvisi ruolo sono coperti da
  un sollecito `generated`, `generated_docx` o `draft`. I pronti non vengono
  rifatti: nessuna seconda copia.
- **Non riuscito.** L'ultimo sollecito `failed` con numero avviso: si ripete con
  la rigenerazione esistente, stesso numero e stesso file.
- **Mancante.** Tutto il resto: si crea un lotto «Solleciti {anno}» ogni 5
  avvisi, così la pagina mostra l'avanzamento e il pulsante «Ferma» agisce fra
  un gruppo e l'altro.
- **API.** `GET /ruolo/tributi/solleciti/years/{anno}/status` e
  `POST /ruolo/tributi/solleciti/years/{anno}/generate` (`avviso_ids`, massimo
  200), entrambe con `ruolo.tributi.manage_status`. Il POST rilegge lo stato e
  genera solo i mancanti: rilanciarlo non duplica.
- **Codice.** `services/year_notice_generation.py`, rotte in
  `routes/notice_regeneration_routes.py`. `generate_reminder_batch` in
  `tributi_repositories.py` è la parte di `create_reminder_batch` che genera il
  lotto dagli avvisi scelti, usata da entrambi. Frontend:
  `components/ruolo/solleciti/year-notices-panel.tsx`,
  `lib/ruolo-year-notices-api.ts`.
- **Lotti generati.** Ogni lotto elenca i primi 3 avvisi con numero, anno,
  importo stampato (saldo più spese di notifica, `notice_total_amount`) e i
  badge «Inviato via PEC» e «PDF non generato». I lotti con più di 3 avvisi
  mostrano anche i contatori.
- **Sola lettura.** Chi non ha il permesso vede il messaggio che spiega di
  chiederlo all'amministratore.
- **Test.** `backend/tests/ruolo/test_year_notice_generation.py`,
  `test_reminder_batch_overview.py`, `frontend/tests/unit/ruolo-year-notices-panel.test.tsx`,
  `ruolo-year-notices-api.test.ts`, `notice-solleciti-page.test.tsx`, e2e
  `ruolo-invio-solleciti.spec.ts`.
