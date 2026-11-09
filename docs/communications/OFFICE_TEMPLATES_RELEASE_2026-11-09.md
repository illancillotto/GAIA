# Modelli ufficio — rilascio del 9 novembre 2026

Rilascio mirato autorizzato dall'utente e attivato alle **14:58:35 CET** del 9 novembre 2026. Commit applicativo **`06f6597c`**, branch `feat/communications-office-templates-20261109`. Catalogo PEC/email del 7 novembre; nessun fallback PIN, modifica tributaria o abilitazione dei trasporti.

Il commit include solo il delta dei modelli e relativa documentazione/test su worktree isolato. Le funzionalita Communications gia pubblicate (registro recapiti, anteprima PDF, eliminazione template) sono preservate nel rilascio sopra le immagini effettive del CED, ma non assorbite dal commit. Le altre modifiche locali restano escluse.

L'immagine frontend precedente aveva 127 livelli Docker: il primo tentativo di build candidata ha rilevato `max depth exceeded`. La base viene consolidata con export/import preservando filesystem e configurazione; nessun container operativo viene modificato per questo passaggio.

## Verifiche prima dell'attivazione

| Perimetro | Risultato |
| --- | --- |
| Commit isolato su `c55dcf9f` | 207 backend PASS, zero skip, inclusi test PostgreSQL; cinque runtime 313 statement/82 branch al 100% |
| UI del commit isolato | 41 test PASS; due componenti 39 statement/24 branch, coverage 100% |
| Immagine backend candidata | 262 PASS, dieci PG skip intenzionali in rete disabilitata; cinque runtime 327 statement/86 branch al 100% |
| PG con sorgenti destinati al server | Dieci test PASS su database locale effimero `communications_test` |
| UI della candidata | 70 unit PASS; due componenti 48 statement/28 branch/21 funzioni/37 righe, coverage 100% |
| Typecheck, lint mirato, smoke | PASS, 18 smoke |
| Browser sulla candidata ottimizzata | Otto E2E PASS desktop/mobile, zero skip/failure/flaky; API e PDF sintetici |
| Preservazione sorgenti | Sei file backend nuovi/modificati, 1.009 file preservati; due componenti frontend nuovi/modificati, 770 file preservati; tutte le 196 route conservate |
| Gate del commit contro HEAD | Ratchet PASS senza finding; `make lint-backend BASE_REF=HEAD` PASS su sei file Python |

Il ratchet autorevole contro `main` consulta la baseline immutabile del merge-base `686e529e`: 18 finding Presenze esterni al delta office, nessuno nei runtime del catalogo. Non viene dichiarato PASS globale e nessuna baseline/soglia/esclusione viene aggiornata. Il confronto con il checkout pulito di `c55dcf9f` riproduce esattamente tutti i 18 finding: nessuna regressione introdotta dal catalogo. Nuovo mapping dei campi invariato dal freeze: massimi cognitive15/cyclomatic13; catalogo UI cognitive7/cyclomatic7, sotto soglia errore. Nessun refactoring aggiuntivo.

Il primo test nell'immagine candidata non trovava `/deploy/communications/worker-grants.sql`: corretto il solo mount read-only del test e ripetuta la suite completa. Nessun sorgente o grant reale modificato. Il primo avvio del test precedente alla preparazione del delta nel worktree non certifica il freeze; contano solo i report `commit-final-tests.xml` e `backend-image.xml`.

Graphify codice backend/Ruolo/frontend aggiornati con i target dedicati. Grafi docs piattaforma e Ruolo aggiornati nel corpus del worktree isolato, entrambi chunk1/1 completato senza semantic chunk falliti. Grafi non versionati.

## Attivazione e rollback

Release CED `/opt/gaia/releases/office-templates-20261109`; evidenze locali `/tmp/gaia-office-release-20261109`. Configurazioni precedenti e rollback backend/frontend congelati. Prima dell'attivazione vengono controllati ID container, configurazione effettiva, commit, hash degli otto runtime e risultati della candidata. Attivazione solo dei due servizi con `--no-deps --no-build --pull never`; rollback automatico in caso di health/probe/configurazione non valida. Worker e altri servizi esclusi.

GET autenticati verificano catalogo, account, template e monitoraggio; hash integrale delle righe template, conteggi, schema e stato trasporti devono restare invariati. Nessun template reale creato o approvato dal rilascio; catalogo e salvataggio bozza restano azioni distinte. Nessun invio. Stato finale registrato dopo i controlli live.

## Esito dell'attivazione

Backend `ab9e8c1bac26` e frontend `9f0e956c7e8b` healthy. Ambiente, mount, comandi, risorse, reti e healthcheck effettivi coincidono con i precedenti. Trentacinque container permanenti estranei preservati; worker Communications invariato. Nove GET verificati attraverso nginx: sette HTTP200 e due API anonime HTTP401. Catalogo autenticato HTTP200 con due proposte e hash corrispondente al sorgente; accesso anonimo HTTP401. Il bundle pubblicato contiene il nuovo catalogo.

Schema `20261106_1000` invariato; due account e quattro righe template con hash integrale invariato, zero messaggi/autorizzazioni/ricevute, cinque job invariati. Pausa globale true e trasporto false, invariati. Nessuna migrazione o modifica dei dati personali/tributari. I modelli sono disponibili in **Communications → Template versionati → Modelli di partenza 2021 e variabili**; il rilascio non crea o approva versioni reali nel database.

Il commit contiene il solo delta del catalogo sopra `c55dcf9f`; le immagini distribuite conservano i prerequisiti gia operativi non ancora committati in quel checkout. Per ricostruire il runtime effettivo usare i manifest e le basi della release CED, non soltanto il commit o il vecchio checkout del server. Rollback applicativo conservato con le configurazioni `backend.rollback.json` e `frontend.rollback.json`; prima di usarle verificare eventuali rilasci successivi. Nessun ripristino dati necessario.

Collaudo browser sulla versione pubblicata: **otto E2E PASS**, zero skip/failure/flaky, desktop e mobile. I test intercettano tutte le API con dati sintetici e non creano messaggi o template reali. I GET effettivi autenticati sono verificati separatamente dal probe in sola lettura.

Evidenza versionata senza segreti: [OFFICE_TEMPLATES_RELEASE_2026-11-09.json](evidence/OFFICE_TEMPLATES_RELEASE_2026-11-09.json).
