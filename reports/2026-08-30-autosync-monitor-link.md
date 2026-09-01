# Report — collegamento monitor AutoSync Elaborazioni

**Data verifica:** 2026-08-30 11:16 CEST  
**Ambito:** dashboard `/elaborazioni`, quadro **Operazioni in corso**.

## Cosa è stato realizzato

- Aggiunto il collegamento **`Apri monitor attività`** nel quadro operativo
  principale, visibile anche quando non ci sono lavorazioni attive.
- Il collegamento apre la nuova rotta diretta **`/elaborazioni/autosync`**.
- La rotta riusa il workspace AutoSync esistente in modalità `autosync`, quindi espone già:
  - stato ON/OFF e configurazione;
  - throughput, visure scaricate, code e batch attivi;
  - andamento delle ultime 24 ore;
  - blocchi/errori ed eventi recenti;
  - gestione pool credenziali, intervalli e micro-batch.
- Aggiornata la documentazione del dominio Elaborazioni con il nuovo percorso.

## File della change

- `frontend/src/components/elaborazioni/active-operations-overview.tsx`
- `frontend/src/components/elaborazioni/autosync-monitor-link.tsx`
- `frontend/src/app/elaborazioni/autosync/page.tsx`
- `frontend/tests/unit/autosync-monitor-link.test.tsx`
- `frontend/tests/unit/elaborazioni-autosync-page.test.tsx`
- `domain-docs/elaborazioni/README.md`

## Verifiche eseguite

| Verifica | Esito |
| --- | --- |
| Test unitari mirati (3 file, 4 test) | PASS |
| Coverage mirata su quadro operativo, nuova rotta e link | PASS — 100% statement, branch, funzioni e linee |
| TypeScript `tsc -p tsconfig.json --noEmit` | PASS |
| Build production Next.js | PASS — rotta `/elaborazioni/autosync` generata |
| `git diff --check` | PASS |
| `make complexity-ratchet BASE_REF=main` | PASS — `findings: []` |
| `make graphify-frontend` | PASS — 5.536 nodi, 13.689 archi, 195 community |
| `make graphify-docs` | PASS — 1.368 nodi, 2.299 archi, 126 community |

## Deploy produzione CED

**Autorizzazione:** esplicita di Ale il 2026-08-30.

È stato effettuato un deploy chirurgico su `serverCed` (`192.168.1.110`), limitato ai tre file runtime necessari:

- `frontend/src/app/elaborazioni/page.tsx` — inserita l'azione nella card **Autosync automatici**;
- `frontend/src/components/elaborazioni/autosync-monitor-link.tsx` — nuovo link, aggiornato con stile primario verde (`btn-primary`);
- `frontend/src/app/elaborazioni/autosync/page.tsx` — nuova rotta monitor.

Prima della copia è stato creato il backup della dashboard CED in:

`/opt/gaia/backups/hotfixes/2026-08-30-autosync-monitor-entrypoint/elaborazioni-page.tsx.predeploy`

Dopo la copia è stato riavviato soltanto `gaia-frontend`.

| Verifica post-deploy | Esito |
| --- | --- |
| `gaia-frontend` | **healthy** |
| CED interno `/elaborazioni` | **HTTP 200** |
| CED interno `/elaborazioni/autosync` | **HTTP 200** |
| LAN `192.168.1.110:8080/elaborazioni` | **HTTP 200** |
| LAN `192.168.1.110:8080/elaborazioni/autosync` | **HTTP 200** |
| Log Next | route `/elaborazioni/autosync` compilata senza errori |

Non sono stati copiati gli altri file modificati o non tracciati nei checkout locale/CED. Non sono stati creati commit o push.

## Verifica incidente ChunkLoadError (post-deploy)

Dopo il deploy, il browser ha segnalato `ChunkLoadError` per:

`/_next/static/chunks/app/elaborazioni/autosync/page.js`

### Evidenza e causa

- Il frontend CED è in esecuzione in modalità **`next dev`**, che compila le route on demand.
- Alla prima verifica il chunk AutoSync ha risposto **404** dal frontend e da nginx, mentre la route `/elaborazioni/autosync` aveva già risposta HTML `200`.
- Il file chunk era presente sotto `/app/.next/...`, ma non era ancora esposto dal dev server durante la compilazione a freddo: è quindi una race di asset/compilazione del server Next in sviluppo, **non un errore del backend AutoSync**.

### Ripristino e verifica finale

È stata aperta internamente la route AutoSync per completarne la compilazione. Senza ulteriori modifiche al codice, le verifiche successive hanno dato:

| Endpoint | Esito |
| --- | --- |
| frontend CED `:3000/_next/static/chunks/app/elaborazioni/autosync/page.js` | **200**, JavaScript, 2.590.283 byte |
| nginx CED `:8080/_next/static/chunks/app/elaborazioni/autosync/page.js` | **200**, JavaScript, 2.590.283 byte |
| LAN `192.168.1.110:8080/_next/static/chunks/app/elaborazioni/autosync/page.js` | **200**, JavaScript, 2.590.283 byte |
| `gaia-frontend` | **healthy** |

La pagina può essere ricaricata ora: il chunk richiesto è disponibile. Il rischio di ricorrenza alla prima apertura dopo un nuovo restart rimane finché la produzione usa `next dev`; la conversione a `next start` richiede una change operativa dedicata e separata.

## Limiti e note

- Il deploy CED del 2026-08-30 conserva storicamente la prima collocazione del
  link nella card `Autosync automatici`. La chiusura quality locale del
  2026-08-31 lo sposta nel quadro `Operazioni in corso`; questo delta non e
  stato distribuito dal presente commit workflow.
- La build Next completa è verde; ha emesso warning ESLint già presenti in file estranei alla change, senza bloccare la compilazione.
- La destinazione e il link sono stati verificati con unit test, checksum, compilazione Next e smoke HTTP. Non è stata effettuata una verifica visuale autenticata del click sul CED, perché non c'era una sessione browser pilotabile.
- Il checkout `main` locale e il checkout CED hanno modifiche concorrenti; tali modifiche sono state preservate. Il deploy ha toccato soltanto i tre file sopra elencati.

## Prossimo passo consigliato

Aprire `/elaborazioni` e usare **Apri monitor attività** nel quadro
**Operazioni in corso**: porta a `/elaborazioni/autosync`.
