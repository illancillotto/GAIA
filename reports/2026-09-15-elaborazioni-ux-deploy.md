# Rilascio UX Elaborazioni

Data: 2026-09-15, 13:21 Europe/Rome.
Target: `serverCed`, `/opt/gaia`, `http://gaia.lan/elaborazioni`.
Commit applicativo: `e762ea4d`.

## Esito

Dashboard con card uniformi, filtri di stato e aperture in modale pubblicata.
Build ricavata da `git archive e762ea4d frontend`, senza cambi Presenze/GIS
non committati nel working tree locale. Sorgenti dei soli 17 file del commit
riportate nel checkout CED tramite archivio overlay; HEAD remoto resta
`3596c36d` con overlay, come nel rilascio precedente. Nessun push eseguito.

## Verifiche

- 47 test unitari, 100% full-file sui 10 runtime: statement 296/296,
  branch 238/238, funzioni 93/93, righe 246/246.
- TypeScript, lint mirato e ratchet contro `3596c36d`: pass.
- Build Docker/Next produzione: 155 pagine generate, nessun errore;
  warning lint legacy esterni alla change.
- Playwright: 2 test passati su dev locale, 2 sulla candidata di produzione,
  2 su `gaia.lan`. Viewport 1440px e 390px, API simulate, card uniformi,
  modali, tastiera, ricerca, assenza di overflow e pageerror.
- Smoke autenticato sulle API reali: 16/16 HTTP 200 prima e dopo il deploy;
  inCass con `limit=1` restituisce un elemento. Nessun job avviato.
- Backend health: `status=ok`, `environment=production`; frontend healthy.
- Inventario container prima/dopo: soltanto `gaia-frontend` ricreato.
- Graphify frontend aggiornato con target dedicato e pruning; docs
  Elaborazioni: `chunk 1/1 done`, nessun chunk semantico fallito.
- Baseline globale non sincronizzata: disallineamento preesistente;
  il ratchet dei 10 runtime non presenta finding.

## Artefatti E Rollback

Release: `/opt/gaia/releases/dashboard-ux-20260915-e762ea4d`.
Immagine: `gaia-frontend:dashboard-ux-20260915-e762ea4d`.
Digest: `sha256:10c68c005f0a8ddacb2dcf3e8427cb91bfaea7c03fa31901d5b22c7324bb8490`.
Il tag `gaia-frontend:latest` punta alla stessa immagine.

Rollback conservato: `gaia-frontend:before-dashboard-ux-20260915-e762ea4d`,
digest `sha256:12fd357599ad3677fa829c7881be138279f2d06f72dbb850902b60f6bacfbf67`.
La release contiene `source-before.tar.gz`, `source-overlay.tar.gz`,
`frontend-source.tar.gz`, `build.log`, `rollout.sh` e inventari container.

Solo se necessario, ripristinare il frontend precedente:

```bash
cd /opt/gaia
docker tag gaia-frontend:before-dashboard-ux-20260915-e762ea4d gaia-frontend:latest
docker compose -f docker-compose.yml up -d --no-deps --no-build --force-recreate frontend
```

Riconciliare anche le sorgenti con gli archivi della release prima di una
successiva build: il rollback del tag non modifica il checkout.
Log locali `/tmp/gaia-ux-final-*`, `/tmp/gaia-ux-candidate-e2e.log`,
`/tmp/gaia-ux-production-e2e.log`, `/tmp/gaia-ux-rollout.log`.
