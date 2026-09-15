# Elaborazioni: panoramica e modali

## Risultato

Card uniformi, stato sintetico su tutti i flussi, ricerca e filtri per stato.
Dettagli, monitor, pianificazioni, configurazioni e richieste si aprono in
modale conservando ricerca e filtro. Focus contenuto, Escape e ritorno al
pulsante iniziale verificati nel browser. Monitor esistenti riutilizzati;
API, permessi, polling e avvio delle lavorazioni invariati.

Modifiche applicate sopra la dashboard gia presente nel working tree.
Commit e deploy frontend autorizzati dall'utente dopo la revisione locale.
Il rilascio usa un archivio del commit, senza le modifiche Presenze e GIS
presenti nel working tree. Esito operativo nel rapporto di rilascio UX.

## Perimetro

- `frontend/src/app/elaborazioni/page.tsx`
- `frontend/src/components/elaborazioni/sync-service-card.tsx`
- `frontend/src/components/elaborazioni/sync-service-details.tsx`
- `frontend/src/components/elaborazioni/sync-dashboard-dialog.tsx`
- `frontend/src/components/elaborazioni/sync-schedules.tsx`
- `frontend/src/components/elaborazioni/workspace-modal.tsx`
- `frontend/src/lib/sync-dashboard-model.ts`
- Test unitari dashboard/workspace, E2E e contratto `SYNC_DASHBOARD.md`.

## Verifiche

- Vitest: 47 test passati. Repeat finale con coverage dei 10 runtime al 100%,
  inclusi hook e adattatori: statement 296/296, branch 238/238,
  funzioni 93/93, righe 246/246.
- Playwright Chromium: 2 test passati, desktop 1440px e mobile 390px;
  API simulate, monitor Capacitas reale, dimensioni card confrontate,
  focus, Escape, filtri, errori su piu flussi, nessun pageerror o overflow.
- `npm run typecheck`, ESLint mirato e `git diff --check`: pass.
- `python3 tools/code_quality/complexity.py ratchet --base-ref 3596c36d`
  con i sette file runtime come argomenti: `findings: []`.
- `complexity.py baseline-verify`: false, coerente con il disallineamento
  globale gia documentato. Baseline non modificata o sincronizzata per
  assorbire debito preesistente.
- `make graphify-frontend GRAPHIFY_CODE_FLAGS=--force`: completato.
- `make graphify-elaborazioni-docs`: `chunk 1/1 done`, nessun chunk fallito.

Metriche prima/dopo (ciclomatica/cognitiva): pagina 3/2 -> 6/5,
card 7/6 -> 5/4, pianificazioni 12/11 -> 12/11. I dettagli conservano
la responsabilita di visualizzazione degli snapshot. Nessuna nuova violation
error-level; il renderer legacy resta sopra soglia, senza regressione.
Modalita quality ratchet ordinario, nessun hotspot dedicato.

Log e coverage finali: `/tmp/gaia-ux-final-*`. Screenshot desktop/mobile:
`/tmp/gaia-dashboard-1440.png`, `/tmp/gaia-dashboard-390.png` e
`/tmp/gaia-dashboard-details-390.png`.

Limiti: verifiche su server Next locale; non effettuati build di produzione
o smoke sulle API reali CED. Il server dev segnala permessi della cache webpack
preesistente; compilazione e test browser sono comunque riusciti.
