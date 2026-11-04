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
