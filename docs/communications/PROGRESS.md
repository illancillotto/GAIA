# Avanzamento Communications

## 2026-11-09 — Modelli ufficio pubblicati

Rilascio mirato autorizzato e attivato alle **14:58:35 CET**; commit applicativo `06f6597c` sul branch `feat/communications-office-templates-20261109`. Catalogo PEC/email disponibile in Communications, backend/frontend healthy. Otto E2E candidata e otto live PASS; coverage runtime del perimetro 100%. Nessun fallback PIN, template reale creato/approvato o invio. Dati, schema e stato trasporti invariati. [Rapporto completo](OFFICE_TEMPLATES_RELEASE_2026-11-09.md).

## 2026-11-07 — Modelli dell'ufficio e verifica PIN

- [x] Modelli PEC/email modificabili con dati specifici avviso, bonifico, fasce e termine confermati.
- [x] Composizione con formule/termini PDF e accessi univoci; variabili mancanti bloccano senza salvataggi parziali.
- [x] 268 backend (dieci PostgreSQL), 67 unit frontend, 18 smoke, otto E2E sintetici PASS; runtime del ciclo 100% statement/branch.
- [x] Typecheck, build clean isolata e lint mirato PASS.
- [x] Audit PIN su tutti i 1.195 file: 138 coincidenti con GAIA/snapshot, zero discordanti; 1.057 senza PIN nel testo, nessun errore di lettura.
- [ ] Decisione sui 726 accessi univoci presenti solo in archivio; 330 documenti senza utenza GAIA e uno con due utenze da verificare.
- Nessun fallback all'archivio, deployment, commit o invio reale. [Analisi e matrice](OFFICE_TEMPLATES_2026-11-07.md).

## 2026-11-07 — Eliminazione template con conferma

- [x] Elimina per versione draft/approved, conferma con identità e gestione errori.
- [x] DELETE solo amministratori, conferma backend, lock, cancellazione logica e audit idempotente.
- [x] Messaggi/PDF e altre versioni conservati; versionamento monotono.
- [x] 197 backend, 63 unit frontend, 18 smoke e sei E2E PASS; coverage runtime modificati 100% statement/branch.
- [x] Build clean isolata, typecheck e lint del perimetro PASS; nessun finding Communications nel ratchet completo.
- [x] Rilascio mirato autorizzato il 7 novembre, 09:42:21 CET: backend/frontend healthy, sei E2E candidata e sei live PASS, dati/schema/trasporti invariati. [Report](TEMPLATE_DELETION_RELEASE_2026-11-07.md).
- Gate globale ancora FAIL per 17 finding Presenze estranei. Baseline invariata; nessuna riclassificazione del gate globale.
- Matrice, file, metriche e limiti: [TEMPLATE_DELETION_2026-11-07.md](TEMPLATE_DELETION_2026-11-07.md).

## 2026-11-06 — Apertura avviso dalla riga

- [x] Clic/Invio/Spazio sostituiscono Componi/Apri comunicazione.
- [x] Permessi, checkbox, revisione, errore e caricamento verificati: 15 test specifici PASS, coverage statement/branch 100%.
- [x] Ratchet del runtime PASS, senza nuove deroghe; regressione combinata 143 test PASS.
- Stato del rilascio frontend e verifiche nel [report Ruolo](../../domain-docs/ruolo/docs/SOLLECITI_WORKSPACE_2026-11-06.md); nessun invio reale autorizzato dalla revisione.

- [x] Audit e contratti del checkout verificato.
- [x] Modello dati, migrazione e API.
- [x] Snapshot/revisione/autorizzazione individuale.
- [x] Worker, trasporti, esiti e integrazione Registro/Poste.
- [x] Frontend PEC/email/admin e PDF multipagina reale.
- [x] Test mirati backend/frontend con coverage 100%, migrazione inclusa.
- [x] Test contabile reale: STEP/default 2021 e pagamento dopo revisione.
- [x] Build pulita, smoke, frontend completo, type-check, lint ed E2E.
- [x] Regressione backend8022 PASS/471 SKIP, baseline riproducibile e grafi codice/Ruolo.
- [x] Refresh semantico Graphify piattaforma; controllo conclusivo dei file prima del commit.
- [x] Regressione PG per file:428 PASS/9 SKIP intenzionali,38 processi senza errori.
- [x] Hardening pre-rilascio: ruolo worker senza hash/recapiti utenti, 132 test e coverage statement/branch 100% sull'immagine aggiornata.
- [x] Regressione backend dopo il hardening in checkout isolato: 8.030 PASS/472 SKIP, zero failure/error; `make lint-backend` PASS.
- [ ] Gate complessivo: FAIL per regressione PG collettiva e prove generali non verificate.
- [ ] Collaudo autorizzato provider/NAS/carico/trust e decisioni ufficio.
- [x] Preparazione CED: backup/checksum/restore integrale, migrazione ripetuta/RBAC sul clone e nove GET autenticati PASS.
- [x] Rilascio mirato CED su nuova autorizzazione: migrazione, ruolo ristretto, backend/frontend/worker healthy; nove GET autenticati e tre 401 PASS, pagine e PDF.js HTTP 200.
- [ ] Abilitazione trasporti e collaudo reale: non autorizzati da questo rilascio.

Lo stato corrente e la matrice comportamenti/test sono in FINAL_REVIEW.md.
TEST_REPORT.md conserva anche le evidenze del primo ciclo a6274cac.
Lo stato del rilascio successivo è in
[DEPLOYMENT_REPORT_2026-11-04](DEPLOYMENT_REPORT_2026-11-04.md).

## Revisione sidebar — 4 novembre

- [x] Elenco/compositore 50/50 su desktop; campi sopra PDF; mobile verticale.
- [x] Cambio avviso senza mantenere campi o documento della selezione precedente.
- [x] 34 test mirati, coverage runtime 100% statement/branch; 5.470 unit test e 18 smoke PASS.
- [x] Build pulita, type-check, lint, quattro E2E Chromium e verifica visiva.
- [x] Sincronizzazione baseline: gli otto incrementi iniziali sono risolti; comando ordinario e baseline-verify PASS, dettagli in SIDEBAR_RELEASE_2026-11-04.md.
- [x] Pubblicazione sidebar CED alle 11:50 CET: solo frontend, healthy; sei URL 200, tre API 401 e quattro E2E live con API simulate PASS.

Evidenze, matrice e limiti: [SIDEBAR_REVIEW_2026-11-04](SIDEBAR_REVIEW_2026-11-04.md).

## Risoluzione gate sidebar

Gli otto incrementi del commit `86fa982d` sono eliminati senza deroghe.
Ratchet completo, sincronizzazione ordinaria e verifica baseline PASS;
35 test mirati e coverage 100%, regressione frontend, build/lint/types e
quattro E2E locali più quattro sull’immagine candidata CED PASS.
Dettagli e stato di pubblicazione corrente in
[SIDEBAR_RELEASE_2026-11-04](SIDEBAR_RELEASE_2026-11-04.md).

## Default presenza recapiti — 4 novembre

- [x] PEC/email inizializzano Presente sul rispettivo canale nella prima query server.
- [x] L’altro canale resta Tutti; controlli modificabili dall’operatore.
- [x] Test su default, primo caricamento e scelta Tutti/Assente.
- [x] Pubblicazione frontend 12:13 CET e quattro flussi live sintetici PASS; backend/Poste del rilascio concorrente preservati, dettagli in CONTACT_FILTERS_2026-11-04.md.

## 2026-11-04 — Classificazione recapiti per persone e aziende

- [x] Registro Utenze per canale/stato/provenienza e API admin versionata.
- [x] Resolver comune per elenco, filtri e fingerprint Communications, entrambi i tipi di soggetto.
- [x] Verifica CED in sola lettura dei solleciti 2021 e report Excel privato completo.
- [x] 169 test Communications, inclusi nove PG reali; coverage 407 statement/72 branch al 100%.
- [ ] Rilascio/migrazione/backfill: non eseguiti. Rettifica successiva: il ratchet completo passa; i sette finding erano relativi a un corpus parziale, vedere SOURCE_PREVIEW_2026-11-04.md.
- [ ] Classificazioni non documentate e 14 discordanti da revisione umana; nessun invio.

Dettagli, matrice test, perimetro e residui in [CONTACT_CLASSIFICATION_2026-11-04.md](CONTACT_CLASSIFICATION_2026-11-04.md).

## Anteprima immediata — 4 novembre 2026

[x] Componi e checkbox caricano il PDF reale prima della bozza; rendering completo e hash obbligatori nella UI. [x] Test di byte equality, RBAC, failure path e browser. Stato del rilascio e verifica finale nel report dedicato.

Dettagli: [SOURCE_PREVIEW_2026-11-04](SOURCE_PREVIEW_2026-11-04.md).

Pubblicazione preview completata alle 16:32:01 CET: PDF reale 2021 verificato, quattro E2E live con API simulate PASS. Registro recapiti/migrazione ancora non pubblicati; elenco PEC legacy ancora 17. Vedere SOURCE_PREVIEW_2026-11-04.md per rollback, matrice e limiti del gate.

## Registro recapiti — rilascio 5 novembre 2026

- [x] Migrazione `20261104_1400`, backend e worker pubblicati sul CED, healthy.
- [x] 252 classificazioni validate e quattro valori invalidi in quarantena; 256 audit.
- [x] API autenticate: 47 righe PEC / 41 anagrafiche, una riga email.
- [x] Confronto campi legacy delle 984 anagrafiche: invariati; PDF reale verificato.
- [x] Report privato per l'ufficio: 14 soggetti discordanti e 191 altri recapiti.
- [ ] Revisione umana e configurazione/collaudo autorizzato delle caselle reali.

Questo stato supera le precedenti voci «registro non rilasciato». Nessun invio.
Evidenze, tentativi e limiti: [CONTACT_RELEASE_2026-11-05](CONTACT_RELEASE_2026-11-05.md).
