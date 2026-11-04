# Avanzamento Communications

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
