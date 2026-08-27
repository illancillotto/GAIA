# GAIA -> Gate Mobile Gateway Sync Runbook

## Obiettivo

Rendere persistente sul server CED la sincronizzazione outbound GAIA -> gateway pubblico:

- gateway: `https://static.186.92.233.167.clients.your-server.de`
- comando applicativo: `python -m app.scripts.gate_mobile_sync`
- handshake:
  - `POST /api/mobile/connector/sync/plan`
  - `POST /api/mobile/connector/operators/push` se richiesto dal piano

Decisione architetturale corrente:

- questo job non sostituisce le API LAN ` /api/mobile-sync/* `
- le API LAN restano il contratto trusted per applicare eventi verso GAIA e per leggere snapshot quando lavora un connector LAN separato
- il job outbound verso gateway pubblico serve solo a proiettare snapshot da GAIA al cloud
- per il pilot corrente il perimetro outbound pubblicato include `operators` e Presenze: `presenze_teams`, `presenze_months`, `presenze_giornaliere`, `presenze_anomalie`, `presenze_rules`, `presenze_pending_actions`
- il push `operators` include anche i campi console GATE `gate_mobile_console_enabled` e `gate_mobile_console_role`; il gateway deve usarli per distinguere operatori sincronizzati da operatori effettivamente abilitati alla console
- le pending action Presenze includono anche `propose_team_change`: GAIA crea,
  aggiorna o fa upsert delle squadre proposte da GaTe dopo validazione di
  utente, payload, scope e codice squadra
- per abilitazioni progressive, GAIA puo selezionare i candidati da `presenze_daily_records` collegati a `presenze_collaborators` con `contract_kind` `operaio` o `impiegato`, poi abilitarli su `wc_operator` con limite operativo prima del massivo
- GATE cloud non chiama mai GAIA LAN/intranet: o GAIA pubblica direttamente verso `/api/mobile/connector/presenze/*/snapshot`, oppure il connector LAN legge da `/api/mobile-sync/presenze/{teams,months,giornaliere,anomalie,rules}` e ripubblica verso GATE in outbound. Gli URL legacy `/api/mobile-sync/presenze/*/snapshot` restano alias compatibili.
- GAIA espone anche `POST /api/mobile-sync/mobile-devices` per accettare in modo idempotente le registrazioni device provenienti dal connector GATE.
- Gli snapshot mensili giornaliere/anomalie letti dal connector LAN sono serializzati in batch per evitare timeout su mesi pieni.
- compatibilita gateway: se `POST /api/mobile/connector/sync/plan` accetta ancora solo `operators` e `presenze_teams`, GAIA riprova con il piano legacy e aggiunge localmente i task snapshot Presenze per mese corrente e mese precedente
- compatibilita payload: gli snapshot giornaliere espongono sia `records` sia `giornaliere`; gli snapshot anomalie espongono sia `anomalies` sia `anomalie`

## Variabili ambiente produzione

Da impostare in `/opt/gaia/.env` senza committare il token nel repository:

```dotenv
GATE_MOBILE_GATEWAY_BASE_URL=https://static.186.92.233.167.clients.your-server.de
GATE_MOBILE_CONNECTOR_TOKEN=<token GAIA del gateway>
GATE_MOBILE_SYNC_ENABLED=true
GATE_MOBILE_SYNC_TIMEOUT_SECONDS=20
GATE_MOBILE_SYNC_INTERVAL_SECONDS=300
```

Nota operativa:

- `GATE_MOBILE_CONNECTOR_TOKEN` resta il valore canonico condiviso con il team Gate
- lato backend GAIA il token LAN `/api/mobile-sync/*` usa `MOBILE_CONNECTOR_TOKEN` se presente, altrimenti fa fallback su `GATE_MOBILE_CONNECTOR_TOKEN`
- quindi nel setup attuale `MOBILE_CONNECTOR_TOKEN` puo restare vuoto se si vuole gestire un solo segreto
- il job e posseduto dal servizio Compose singleton `gate-mobile-sync`
- dopo una modifica alle variabili Gate va ricreato `gate-mobile-sync`, non il backend HTTP

Comando di riallineamento container:

```bash
cd /opt/gaia
docker compose --env-file /opt/gaia/.env up -d gate-mobile-sync
```

## Migrazione dal timer systemd

Prima di avviare il servizio Compose disabilitare l'eventuale ownership host:

```bash
sudo systemctl disable --now gaia-gate-mobile-sync.timer
sudo systemctl disable --now gaia-gate-mobile-sync.service
cd /opt/gaia
docker compose --env-file /opt/gaia/.env up -d gate-mobile-sync
```

Timer host e servizio Compose non devono essere attivi contemporaneamente.

## Verifica manuale

Verifica health gateway:

```bash
curl -fsS https://static.186.92.233.167.clients.your-server.de/health
```

Run manuale:

```bash
cd /opt/gaia
docker compose --env-file /opt/gaia/.env run --rm --no-deps gate-mobile-sync python -m app.scripts.gate_mobile_sync
```

Preview candidati console GATE da giornaliere, senza modificare il DB:

```bash
docker compose --env-file /opt/gaia/.env exec -T backend python - <<'PY'
from app.core.database import SessionLocal
from app.services.gate_mobile_sync import enable_gate_mobile_console_for_giornaliere_workers

with SessionLocal() as db:
    result = enable_gate_mobile_console_for_giornaliere_workers(db, limit=1, dry_run=True)
    print(result)
PY
```

Abilitazione controllata di un solo candidato, ruolo `viewer`:

```bash
docker compose --env-file /opt/gaia/.env exec -T backend python - <<'PY'
from app.core.database import SessionLocal
from app.services.gate_mobile_sync import enable_gate_mobile_console_for_giornaliere_workers

with SessionLocal() as db:
    result = enable_gate_mobile_console_for_giornaliere_workers(db, limit=1, role="viewer", dry_run=False)
    print(result)
PY
```

Esito atteso nel log:

```text
gate-mobile sync completed: tasks=<n> operators_pushed=<n>
```

Verifica servizio:

```bash
docker compose ps gate-mobile-sync
docker compose logs --tail 50 gate-mobile-sync
```

Evidenza del primo run automatico riuscito:

- salvare l'output di `docker compose logs --tail 20 gate-mobile-sync`
- confermare la presenza della riga `gate-mobile sync completed`
- annotare `operators_pushed=<n>` e timestamp del run

## Rotazione token

Procedura consigliata:

1. Generare o recuperare il nuovo connector token dal lato gateway con canale sicuro del CED.
2. Aggiornare `GATE_MOBILE_CONNECTOR_TOKEN` in `/opt/gaia/.env`.
3. Ricreare il servizio Gate Mobile:

```bash
cd /opt/gaia
docker compose --env-file /opt/gaia/.env up -d gate-mobile-sync
```

4. Eseguire un run manuale:

```bash
docker compose --env-file /opt/gaia/.env run --rm --no-deps gate-mobile-sync python -m app.scripts.gate_mobile_sync
```

5. Se il run e corretto, lasciare proseguire il runner Compose.
6. Revocare il token precedente sul gateway.

Regole:

- non inserire il token in file versionati
- non stampare il token nei log
- se il token e conservato in password manager o vault CED, aggiornare anche la voce documentale corrispondente

## Logging operativo

Lo script applicativo logga:

- skip esplicito se `GATE_MOBILE_SYNC_ENABLED=false`
- successo con `operators_pushed`
- errore di configurazione mancante
- errore HTTP con status, metodo e path
- errore di trasporto senza esporre header o token

## Stato admin in GAIA

Il backend espone anche un endpoint amministrativo autenticato:

```text
GET /operazioni/mobile-gateway-sync/status
```

Contenuto:

- presenza configurazione gateway
- presenza token outbound
- timeout configurato
- ultimo run
- storico recente dei run
- riferimento esplicito al canale LAN `/api/mobile-sync`

## Vincoli business confermati

In questa fase non cambiano:

- `WCOperator.id` -> `operator_id`
- `ApplicationUser.id` -> `gaia_user_id`
- `OperatorProfile.id` -> `gaia_operator_profile_id` quando presente
- `operator.enabled && user.is_active` -> `ACTIVE`, altrimenti `DISABLED`
