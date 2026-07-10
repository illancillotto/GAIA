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
- le API LAN restano il contratto trusted per applicare eventi verso GAIA
- il job outbound verso gateway pubblico serve solo a proiettare snapshot da GAIA al cloud
- per il pilot corrente il perimetro outbound pubblicato include `operators` e Presenze: `presenze_teams`, `presenze_months`, `presenze_giornaliere`, `presenze_anomalie`, `presenze_rules`, `presenze_pending_actions`

## Variabili ambiente produzione

Da impostare in `/opt/gaia/.env` senza committare il token nel repository:

```dotenv
GATE_MOBILE_GATEWAY_BASE_URL=https://static.186.92.233.167.clients.your-server.de
GATE_MOBILE_CONNECTOR_TOKEN=<token GAIA del gateway>
GATE_MOBILE_SYNC_ENABLED=true
GATE_MOBILE_SYNC_TIMEOUT_SECONDS=20
```

Nota operativa:

- `GATE_MOBILE_CONNECTOR_TOKEN` resta il valore canonico condiviso con il team Gate
- lato backend GAIA il token LAN `/api/mobile-sync/*` usa `MOBILE_CONNECTOR_TOKEN` se presente, altrimenti fa fallback su `GATE_MOBILE_CONNECTOR_TOKEN`
- quindi nel setup attuale `MOBILE_CONNECTOR_TOKEN` puo restare vuoto se si vuole gestire un solo segreto
- il job viene eseguito con `docker compose exec` dentro il container `backend`
- dopo ogni modifica a `/opt/gaia/.env` il container `backend` va ricreato, altrimenti il nuovo token non entra nel processo

Comando di riallineamento container:

```bash
cd /opt/gaia
docker compose --env-file /opt/gaia/.env up -d backend
```

## Installazione timer systemd

Modalita preferita: `systemd timer` ogni 5 minuti.

File repository:

- `deploy/systemd/gaia-gate-mobile-sync.service.tpl`
- `deploy/systemd/gaia-gate-mobile-sync.timer`
- `scripts/install_gate_mobile_sync_timer.sh`

Installazione sul server CED:

```bash
cd /opt/gaia
sudo CED_PROJECT_DIR=/opt/gaia ENV_FILE=/opt/gaia/.env ./scripts/install_gate_mobile_sync_timer.sh
```

Il service generato esegue:

```bash
docker compose --env-file /opt/gaia/.env exec -T backend python -m app.scripts.gate_mobile_sync
```

## Verifica manuale

Verifica health gateway:

```bash
curl -fsS https://static.186.92.233.167.clients.your-server.de/health
```

Run manuale:

```bash
cd /opt/gaia
docker compose --env-file /opt/gaia/.env exec -T backend python -m app.scripts.gate_mobile_sync
```

Esito atteso nel log:

```text
gate-mobile sync completed: tasks=<n> operators_pushed=<n>
```

Verifica timer:

```bash
systemctl status gaia-gate-mobile-sync.timer --no-pager
systemctl list-timers gaia-gate-mobile-sync.timer --all
journalctl -u gaia-gate-mobile-sync.service -n 50 --no-pager
```

Evidenza del primo run automatico riuscito:

- salvare l'output di `journalctl -u gaia-gate-mobile-sync.service -n 20 --no-pager`
- confermare la presenza della riga `gate-mobile sync completed`
- annotare `operators_pushed=<n>` e timestamp del run

## Rotazione token

Procedura consigliata:

1. Generare o recuperare il nuovo connector token dal lato gateway con canale sicuro del CED.
2. Aggiornare `GATE_MOBILE_CONNECTOR_TOKEN` in `/opt/gaia/.env`.
3. Ricreare il backend:

```bash
cd /opt/gaia
docker compose --env-file /opt/gaia/.env up -d backend
```

4. Eseguire un run manuale:

```bash
docker compose --env-file /opt/gaia/.env exec -T backend python -m app.scripts.gate_mobile_sync
```

5. Se il run e corretto, lasciare proseguire il timer.
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
