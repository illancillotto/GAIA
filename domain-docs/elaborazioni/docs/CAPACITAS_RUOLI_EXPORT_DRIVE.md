# Export settimanale ruoli Capacitas su Google Drive

Data: 2026-10-30

Due worker autonomi salvano ogni settimana su Google Drive gli export Excel dei
ruoli dai portali Capacitas, replicando via HTTP i pulsanti "Esporta" usati a
mano. Nessuna modifica a schema DB o API.

## Cosa viene esportato

| Worker | File su Drive | Origine sul portale | Chiavi |
| --- | --- | --- | --- |
| `elaborazioni-worker-ruoli-incass` | `incass_ricerca_avvisi_<anno>.xlsx` | inCASS > Ricerca avvisi, filtro anno, Esporta | tutti i valori del filtro anno (`ContentMain_ddlAnno`, oggi 9926 ... 2011) |
| `elaborazioni-worker-ruoli-incass` | `incass_avvisi_minuta_<anno>.xlsx` | inCASS > Situazione Economica > Elenchi Avvisi > Avvisi Minuta | i 20 ruoli proposti dal form (anno corrente e i 19 precedenti) |
| `elaborazioni-worker-ruoli-inbollettini` | `inbollettini_registro_bollettini_<esercizio>.xlsx` | inBOLLETTINI > Registro Bollettini Manuali, esercizio, Cerca, Esporta | tutti gli esercizi del filtro (`ContentMain_ddlEsercizio`) |

Struttura su Drive (cartella `CAPACITAS_RUOLI_EXPORT_DRIVE_FOLDER_ID`):

```text
<cartella radice>/
  inCASS/<AAAA-MM-GG>/        export inCASS + manifest.json
  inBOLLETTINI/<AAAA-MM-GG>/  export inBOLLETTINI + manifest.json
```

La data e quella dello slot settimanale (default domenica 07:00 Europe/Rome),
non quella di completamento: una ripresa nella stessa settimana scrive nella
stessa cartella. Gli export con zero righe non vengono caricati e risultano
`empty` nel manifest.

## Flussi HTTP (ricognizione 2026-10-30)

- **Ricerca avvisi**: `POST pages/ajax/ajaxRicerca.aspx` con `op=avvisi`,
  `isExport=true`, `anno=<anno>` (risposta `SI`), poi
  `GET pages/exportExcel.aspx?op=ricerca-avvisi` restituisce l'xlsx del
  portale, salvato cosi com'e. L'ultima riga del file contiene solo un a-capo
  nella colonna "Reso" e non conta come dato.
- **Avvisi Minuta** (tile tipo 7, stored procedure `spElencoAvvisi_Anno`):
  il tile viene risolto a runtime dal livello `elenchi_avvisi`; poi
  `dialog/dlgTileTipo7.aspx` (sessione di elaborazione),
  `ajaxCheckProgress op=op_in_progress_v2` (se `InProgress != 0` c'e
  un'elaborazione aperta: retry), `ajaxTiles op=esegui-sp mode=async-tile7`
  con `params=Anno_input=Ruolo+<anno>&Anno=<anno>` codificato (senza
  `Anno_input` la procedura risponde "expects parameter '@Anno'"), polling di
  `check_status_v2` fino a `fine elaborazioni`/`fine processo` (una riga
  `ERRORE:` fallisce lo step), `clear_check_v2` ("Ok, prosegui") e lettura della
  griglia `ajaxGenericGridKUI op=get-data-grid-tile-6`. Se la griglia e troncata
  (`__TotRighe` maggiore delle righe ricevute) si usa l'export server
  `download.aspx op=export-grd-tile6`, come fa il browser.
  Il messaggio "La ricerca ha selezionato N record" del log NON e il numero di
  righe della griglia (ruolo 2025: log 3.269, griglia 12.353): non usarlo come
  controllo.
- **Registro Bollettini**: `POST pages/ajax/ajaxRicerca.aspx` con
  `op=registroBoll`, `esercizio=<esercizio>` e filtri vuoti (JSON
  `results/total/err`, tutti i conti correnti, nessuna paginazione server).

Per Avvisi Minuta e Registro Bollettini "Esporta" e il `saveAsExcel()` di Kendo
nel browser: il worker scrive l'xlsx dai dati JSON della griglia con tutte le
colonne restituite dal portale (nomi di campo originali, date `/Date(ms)/`
convertite in data Excel ora di Roma).

Verifica live del 2026-10-30 (credenziale 1): Avvisi Minuta 2025 = 12.353
righe, Registro Bollettini 2525 = 1.294 righe, Ricerca avvisi 2025 = 12.353
righe, coerenti con le griglie del portale.

## Errori e retry

- Ogni file ha `CAPACITAS_RUOLI_EXPORT_MAX_ATTEMPTS` tentativi con backoff
  esponenziale da `CAPACITAS_RUOLI_EXPORT_RETRY_BASE_SECONDS`. Sono ritentati:
  errori di rete e timeout, HTTP 408/429/5xx, sessione scaduta (con nuovo login
  prima del tentativo), elaborazione Avvisi Minuta gia in corso o non conclusa
  entro `CAPACITAS_RUOLI_EXPORT_PROGRESS_TIMEOUT_SECONDS`, risposte incomplete.
  Non sono ritentati: tile o filtro non trovati, Drive non configurato o refresh
  token rifiutato.
- Un file fallito non ferma gli altri: resta `failed` nello stato e nel
  manifest. Lo snapshot resta `partial` e viene ripreso dopo un'ora,
  riesportando solo i file non completati, fino all'arrivo dello slot
  successivo.
- Login: usa `pick_credential` (credenziale attiva e in fascia oraria) e
  aggiorna `mark_credential_used` / `mark_credential_error`, quindi un login
  fallito conta verso l'auto-disable dopo 5 errori consecutivi come per gli
  altri job Capacitas. Le richieste passano dal client "polite" (5 s fra le
  richieste, pause crescenti sugli errori) con un file di stato proprio,
  `/runtime-data/capacitas/request-policy-ruoli-export.json`: i due worker ruoli
  si serializzano fra loro ma non con il worker runtime. Scelta del 2026-10-31:
  il file condiviso era in pausa di 3600 s a ogni richiesta del runtime con
  sessione involture scaduta (ripresa Capacitas) e l'export non avanzava.
- Prima di caricare un file il worker cerca un file con lo stesso nome nella
  cartella dello snapshot: una ripresa dopo un crash non crea duplicati.

## Attivazione

1. Ottenere il refresh token Google con l'account proprietario della cartella
   Drive (client OAuth tipo "Desktop app", oppure client web con redirect
   `http://localhost` registrato):

   ```bash
   docker compose exec backend python scripts/google_drive_authorize.py
   # CED: lo script e solo nell'immagine dei worker ruoli
   docker compose --project-directory /opt/gaia -p gaia \
     -f releases/ruoli-export-20261031-544ac5a8/compose.ruoli.yml \
     run --rm elaborazioni-worker-ruoli-incass python /app/scripts/google_drive_authorize.py
   ```

   Aprire l'URL stampato, autorizzare, incollare l'indirizzo
   `http://localhost/?code=...` su cui atterra il browser (la pagina non
   carica, e normale). Scope richiesto: `drive` completo, perche la cartella
   esiste gia e non e stata creata dall'app.
2. In `.env`: `GOOGLE_DRIVE_REFRESH_TOKEN=...`, eventualmente
   `GOOGLE_DRIVE_CLIENT_ID/SECRET` se diversi dal login Google,
   `CAPACITAS_RUOLI_EXPORT_ENABLED=true`, opzionale
   `CAPACITAS_RUOLI_EXPORT_CREDENTIAL_ID`.
3. Avvio:
   `docker compose up -d elaborazioni-worker-ruoli-incass elaborazioni-worker-ruoli-inbollettini`.
4. Prima esecuzione manuale, senza attendere la domenica:

   ```bash
   docker compose run --rm elaborazioni-worker-ruoli-inbollettini \
     python /app/worker/ruoli_export_runner.py inbollettini --once
   ```

## Monitoraggio e recovery

- Stato: `runtime-data/ruoli-export/incass.json` e `inbollettini.json`
  (`snapshot`, `status`, esito per file). Lo stesso contenuto e in
  `manifest.json` nella cartella Drive dello snapshot.
- Heartbeat: `runtime-data/worker-health/elaborazioni-worker-ruoli-<gruppo>.json`.
- Forzare un nuovo export della settimana: cancellare il file di stato del
  gruppo e i file da rifare su Drive, poi `--once`.
- "un'altra elaborazione Avvisi Minuta e in corso": un operatore ha
  un'elaborazione aperta sullo stesso utente; il retry riprova da solo.
- `Refresh token Google Drive rifiutato`: token revocato o scaduto (client in
  stato "Testing" su Google Cloud scade dopo 7 giorni: pubblicare l'app OAuth o
  usare un client interno), ripetere il passo 1.

## Rilascio sul CED (2026-10-31)

Commit `544ac5a8`, rilascio mirato `ruoli-export-20261031-544ac5a8`: immagine
`gaia-elaborazioni-worker-ruoli` costruita su `gaia-backend:year-notices-20261030-024eeadf`
con i soli file della feature, compose dedicato
`/opt/gaia/releases/ruoli-export-20261031-544ac5a8/compose.ruoli.yml` (da usare
con `--project-directory /opt/gaia -p gaia`). Backend, frontend, altri worker,
schema DB e checkout `/opt/gaia` invariati.

- 107 test superati nell'immagine candidata, rete disattivata.
- Google: client "App desktop" del progetto `gaia-499807`, autorizzato da
  ced.cbo@gmail.com (proprietario di `jobData`); client, secret e refresh token
  in `/opt/gaia/.env` (sul CED e il file attivo, diverso da `.env.production`;
  copia precedente `env.before-drive` nella directory del rilascio).
- Prova `--once` inBOLLETTINI: snapshot `2026-10-25` completato, 12 esercizi
  caricati (2525 = 1.294 righe).
- `CAPACITAS_RUOLI_EXPORT_ENABLED=true` dalle 11:20 circa; lo snapshot inCASS
  della settimana e partito all'accensione.
- Ripristino: `/opt/gaia/releases/ruoli-export-20261031-544ac5a8/rollback.sh`
  (rimuove i due worker; stato e file su Drive restano).
