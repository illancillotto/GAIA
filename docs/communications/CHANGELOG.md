# Changelog

## 2026-11-04 — Risoluzione gate sidebar e rilascio autorizzato

- Eliminati otto incrementi senza eccezioni o modifiche al gate.
- Ridotte duplicazioni dello stato vuoto, struttura DOM e indicazioni ripetute.
- Cleanup busy con finally e nuovo test di richiesta fallita con documento precedente.
- Ratchet, sincronizzazione ordinaria e baseline riproducibile PASS.
- 35 test mirati/coverage100%, regressione5470, smoke18, build/lint/types e 4+4 E2E PASS.
- Commit correzione `9ee72287`; frontend CED `6218c83aa7da` pubblicato alle 11:50 CET.
- Sei URL200, tre API401 e quattro E2E live con API simulate PASS; 49 container preservati.
- Nessun invio reale, migrazione o modifica dei worker. Stato e rollback in SIDEBAR_RELEASE_2026-11-04.md.

## 2026-11-04 — Sidebar composizione PEC/email (locale)

- Elenco a sinistra e compositore a destra in colonne uguali su desktop.
- Campi sopra PDF, poi checklist; composizione verticale su mobile.
- Componi aggiorna il pannello; il cambio avviso pulisce la selezione precedente.
- Tabella con scroll e azioni visibili; viewer e autorizzazione esistenti preservati.
- Test, coverage e build verificati; nessun nuovo rilascio o invio reale.
- Lint esteso ai test: corretto un prefer-const preesistente; otto test composer ripetuti PASS.
- Sincronizzazione baseline rifiutata per otto incrementi UI; quality gate completo FAIL, baseline e soglie preservate.
- Evidenze in SIDEBAR_REVIEW_2026-11-04.md.

## 2026-11-04 — Hardening e rilascio mirato CED autorizzato

- Query approvatore limitata a quattro colonne; il ruolo worker non legge
  hash delle password, username o recapiti degli utenti.
- Sei test RBAC e una prova PostgreSQL effettiva sui grant aggiunti; immagine
  candidata 132 PASS, coverage statement/branch 100%, nessuno skip/esclusione.
- Baseline del solo worker sincronizzata dopo ratchet e verificata in
  checkout isolato, senza includere le modifiche concorrenti.
- Artefatti CED, configurazione congelata e rollback compatibile preparati.
  Backup/checksum/restore integrale e migrazione/RBAC sul clone PASS; nove
  GET autenticati sul clone PASS. Regressione backend 8.030 PASS/472 SKIP.
- Hardening committato in `e39cbafc`. Migrazione `20261103_1200`, ruolo ristretto
  e backend/frontend/worker distribuiti su nuova autorizzazione.
- Pagine PEC/email/admin pubblicate; nove GET autenticati e tre 401 PASS,
  sette pagine/health e asset PDF.js HTTP 200. Altri 33 container preservati.
- Pausa globale attiva, trasporti false, zero account/messaggi/job e due template
  draft. Configurazione caselle e collaudo reale restano necessari.
- Stato e residui, inclusa la rotazione delle credenziali esposte nell'output
  preparatorio, in DEPLOYMENT_REPORT_2026-11-04.md. Nessun invio reale.

## 2026-11-03 — Implementazione iniziale e collaudo isolato

- Audit del checkout e individuazione dei contratti Ruolo/Registro/Poste.
- Outbox Communications, account e template versionati, snapshot binari privati.
- Autorizzazioni individuali, ricevute di rendering, API protette e job persistenti.
- Worker indipendente con trasporti TLS, IMAP readonly, parsing PEC/DSN e audit.
- Nuove pagine PEC/email e amministrazione; viewer PDF.js e checklist.
- Suite sintetiche e regressioni descritte in TEST_REPORT; nessun invio reale o rilascio.

- Recovery: tentativi e Registro coerenti con uncertain dopo crash/eccezione;
  lease token mai restituito da dispatch.
- Health per processo, overlay senza privilegi/root filesystem scrivibile,
  grants allowlist e configurazioni prive di credenziali.
- Backend123PASS,100% statement/branch; frontend89PASS nel perimetro,100%;
  regressione frontend5468PASS e Ruolo1090PASS/407SKIP.
- Chromium reale: quattro flussi PEC/email desktop/mobile con PDF tre pagine.
- Guide provider ufficiali consultate; nessun test su casella reale.
- Documentazione completa: configurazione, operatore, collaudo, rilascio/rollback,
  decisioni esterne, integrazione Registro/Poste e limiti della conservazione.
- Fingerprint include tutti i metadati sorgente; errori PDF NAS normalizzati.
- Failed prima di effetti irreversibili annullabili con audit per nuova revisione;
  evidenze sending/submitted/uncertain impediscono comunque annullamento.
- Suite backend completa:8015PASS/471SKIP, nessuna failure; skip mantenuti visibili.
- Regressione worker Posta Online:166PASS su12file, incluse6 prove PG reali isolate.
- Ripetuti quattro flussi Chromium sull'ultima build; ESLint mirato senza errori.
- Fixture PDF classificata binaria con attributo Git specifico, senza modificarne i byte.
- Ratchet finale PASS; sincronizzazione baseline rifiutata per metriche Poste
  preesistenti fuori perimetro, senza modificare baseline o soglie.

## Commit locali

- 40b324ac: backend, migrazione, outbox, trasporti, worker e test sintetici.
- 599e1ccf: interfaccia PEC/email/amministrazione, PDF.js, test e documentazione.
- Chiusura: report finali, attributo binario fixture e limite baseline documentato.

Nessun push, PR, merge o deployment eseguito.

## Verifica finale del ciclo

- Nessuna nuova feature o modifica runtime. Nessun deployment.
- Due test reali aggiunti: roundtrip SQLite della migrazione e pagamento
  persistito dopo review attraverso il repository Ruolo reale.
- Coverage backend esteso ad Alembic:125PASS,1639statement/336branch100%.
- Frontend89PASS con coverage100%, suite5468PASS, smoke18PASS, E2E4PASS;
  ripetuti build:clean, type-check e lint.
- Worker Poste166PASS e strumenti qualità270PASS.
- Riparazione baseline già committata, verificata e revisionata separatamente
  nel commit d826c904; nessuna soglia/esclusione/engine alterato.
- Matrice e stato conclusivo in FINAL_REVIEW.md, avanzamento in PROGRESS.md.
- Regressione backend generale ripetuta:8022PASS/471SKIP,0failure/error;
  ragioni degli skip aggregate da JUnit e distinte dalle125prove dedicate.
- npm audit produzione:0vulnerabilità note; hash runtime/migrazione invariati.
- Gate finale complessivo FAIL: setup PG collettivo fallito anche sul commit
  di partenza; prove legacy/PostGIS/GIS non interamente verificabili.
- Recuperate428prove PG in38processi isolati;9skip SQLite intenzionali.
 32prove schema/PostGIS e2GIS restano non verificate.
