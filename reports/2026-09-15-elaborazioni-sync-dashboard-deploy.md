# Rilascio dashboard sincronizzazioni Elaborazioni

Data: 2026-09-15, ore 11:42 Europe/Rome.
Target: `serverCed`, `/opt/gaia`, `http://gaia.lan/elaborazioni`.
Base: `3596c36d369d6f3a6c3db4fecfbb20e6bdfee846` con overlay dei soli file
della dashboard, test e documentazione del dominio. Nessun commit o push.

## Risultato

Dashboard con 15 servizi, ricerca, refresh ogni 30 secondi a pagina visibile,
errori di lettura isolati, ultimo sync per flusso Capacitas/inCass e controlli
di pianificazione conservati. Contratto in
`domain-docs/elaborazioni/docs/SYNC_DASHBOARD.md`.

## Verifiche

- Vitest: 33 test passati, tre suite della dashboard e degli overview.
- Coverage full-file dei sette runtime: statement 153/153, branch 134/134,
  funzioni 54/54, righe 127/127, tutto 100%. Nessuna soglia modificata.
- TypeScript, ESLint mirato, `git diff --check`: pass.
- `make complexity-ratchet BASE_REF=3596c36d`: findings vuoti.
- La baseline globale resta non riproducibile per debito preesistente fuori
  perimetro; nessun aggiornamento della baseline per assorbire regressioni.
- Build Docker/Next.js produzione: pass, 155 pagine generate. Warning lint
  legacy fuori perimetro, nessun errore bloccante.
- Playwright sull'immagine candidata e poi su `gaia.lan`: due test passati
  per ogni esecuzione, viewport 1440px e 390px, API simulate, nessun pageerror
  o overflow, catalogo di 15 servizi e un solo ultimo sync inCass.
- Smoke autenticato sulle API reali CED: tutte le 16 letture rispondono 200;
  la lista inCass con `limit=1` restituisce un elemento. Nessun job avviato.
- Dopo il deploy: `/elaborazioni` HTTP 200, `/api/health` restituisce
  `status=ok`, `environment=production`; frontend healthy.
- Graphify frontend aggiornato tramite target dedicato con pruning.
- Graphify Elaborazioni docs: `chunk 1/1 done`, nessun chunk semantico fallito;
  263 nodi, 393 archi, 24 community. Repeat finale: cache completa.

Coverage e log locali: `/tmp/gaia-dashboard-release-coverage` e
`/tmp/gaia-dashboard-release-*.log`.

## Deploy e rollback

Release: `/opt/gaia/releases/dashboard-sync-20260915-3596c36d`.
Immagine: `gaia-frontend:dashboard-sync-20260915-3596c36d`.
Digest: `sha256:12fd357599ad3677fa829c7881be138279f2d06f72dbb850902b60f6bacfbf67`.
Il tag `gaia-frontend:latest` punta alla stessa immagine verificata.

Ricreato soltanto `frontend` tramite Compose con `--no-deps --no-build`.
Nessun riavvio di backend, scheduler, worker o database. Le sorgenti della
change sono riportate nel checkout CED tramite `source-overlay.tar.gz`, cosi
una build successiva include il codice effettivamente rilasciato.

Immagine precedente conservata come
`gaia-frontend:before-dashboard-sync-20260915`, digest
`sha256:959216bcb3778c7ee91c4e72760ba08fe980c638b2027b11a9c84a75e193c7dc`.
`source-before.tar.gz` conserva la pagina e il README precedenti.

Rollback del runtime, soltanto se necessario:

```bash
cd /opt/gaia
docker tag gaia-frontend:before-dashboard-sync-20260915 gaia-frontend:latest
docker compose -f docker-compose.yml up -d --no-deps --no-build --force-recreate frontend
```

Prima di una successiva build dopo un rollback, riconciliare anche le sorgenti
con gli archivi della release. Il rollback del tag non modifica il checkout.
