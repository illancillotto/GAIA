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
