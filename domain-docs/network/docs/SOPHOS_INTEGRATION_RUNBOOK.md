# GAIA Rete — Runbook integrazione Sophos XGS87

## Scopo

Questo runbook descrive i passi operativi per collegare un firewall Sophos XGS87 al modulo GAIA Rete gia predisposto per:

- ingestione `syslog` UDP
- polling `SNMP`
- correlazione eventi verso `network_alerts`
- esposizione dashboard e pagina `/network/firewalls`

## Componenti GAIA coinvolti

- backend API: `gaia-backend`
- collector syslog: `gaia-sophos-syslog`
- poller SNMP: `gaia-sophos-snmp`

## Variabili ambiente

Impostare almeno:

```env
NETWORK_SOPHOS_FIREWALL_DEFAULT_NAME=Sophos XGS87
NETWORK_SOPHOS_FIREWALL_MANAGEMENT_IP=192.168.1.1

NETWORK_SOPHOS_SYSLOG_ENABLED=true
NETWORK_SOPHOS_SYSLOG_BIND_HOST=0.0.0.0
NETWORK_SOPHOS_SYSLOG_PORT=5514
NETWORK_SOPHOS_SYSLOG_WORKER_COUNT=4
NETWORK_SOPHOS_SYSLOG_QUEUE_SIZE=2000

NETWORK_SOPHOS_SNMP_ENABLED=true
NETWORK_SOPHOS_SNMP_HOST=192.168.1.1
NETWORK_SOPHOS_SNMP_PORT=161
NETWORK_SOPHOS_SNMP_COMMUNITY=REPLACE_WITH_REAL_SNMP_COMMUNITY
NETWORK_SOPHOS_SNMP_INTERVAL_SECONDS=300
NETWORK_SOPHOS_SNMP_CUSTOM_OIDS=[]
```

Template pronto:

- `docs/examples/sophos.env.template`
- `docs/examples/sophos.env.cbo-current` per lo stack CBO corrente, gia valorizzato con `GAIA-dev`

## Avvio servizi

Avviare:

```bash
docker compose up -d backend sophos-syslog sophos-snmp
```

Verificare:

```bash
docker compose ps
docker compose logs --tail=100 sophos-syslog
docker compose logs --tail=100 sophos-snmp
./scripts/check-sophos-integration.sh
./scripts/smoke-network-vpn-bypass.sh
```

## Configurazione Sophos — Syslog

Sul firewall Sophos configurare un server syslog remoto verso l’host Docker/VM che esegue GAIA:

- protocollo: `UDP`
- porta: `5514`
- destinazione: IP del server GAIA

Tipi di log consigliati per il primo rilascio:

- firewall
- system
- vpn
- ips
- authentication

Risultato atteso in GAIA:

- creazione record in `network_firewall_events`
- apertura alert `FIREWALL_EVENT` per severita `danger` o `critical`
- visibilita nella pagina `/network/firewalls`
- coverage log visibile in:
  - dashboard rete come warning rapido
  - pagina `/network/firewalls` come dettaglio `coverage log Sophos`

## Robustezza collector syslog

Il collector `gaia-sophos-syslog` usa:

- coda bounded interna
- worker fissi configurabili
- ingest asincrono rispetto al socket UDP

Variabili di tuning:

- `NETWORK_SOPHOS_SYSLOG_WORKER_COUNT`
- `NETWORK_SOPHOS_SYSLOG_QUEUE_SIZE`

Obiettivo operativo:

- evitare saturazione del pool DB quando il Sophos invia burst di syslog
- mantenere attivo il listener anche con traffico elevato

## Configurazione Sophos — SNMP

Abilitare l’agente SNMP sul firewall e consentire il polling dall’IP del server GAIA.

Parametri minimi:

- versione: `SNMPv2c`
- community: quella impostata in `NETWORK_SOPHOS_SNMP_COMMUNITY`
- host consentito: IP del server/container GAIA
- porta UDP: `161`

Risultato atteso in GAIA:

- creazione record in `network_firewall_metrics`
- visibilita delle metriche standard nella pagina `/network/firewalls`

## Test rapidi

### Test API firewall

```bash
curl -H "Authorization: Bearer <TOKEN>" http://localhost:8080/api/network/firewalls
```

### Test poll SNMP manuale

```bash
curl -X POST -H "Authorization: Bearer <TOKEN>" http://localhost:8080/api/network/firewalls/1/metrics/poll
```

### Test ingestione syslog applicativa

```bash
curl -X POST \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  http://localhost:8080/api/network/firewalls/sophos/syslog \
  -d '{
    "firewall_id": 1,
    "message": "device_name=\"XGS87\" log_type=\"Firewall\" log_component=\"Firewall Rule\" log_subtype=\"Drop\" priority=\"Critical\" src_ip=192.168.1.10 dst_ip=1.1.1.1 message=\"Tentativo bloccato\""
  }'
```

### Smoke end-to-end listener Sophos

```bash
./scripts/smoke-network-vpn-bypass.sh
```

Lo smoke:

1. esegue login admin sul proxy `:8080`
2. invia un syslog Sophos sintetico via UDP a `127.0.0.1:5514`
3. verifica che `network_firewall_events.max(observed_at)` avanzi davvero
4. verifica `summary`, `arp-timeline`, `detection-watchlist` e `tracking`

## OID custom Sophos

Il poller SNMP usa subito OID standard:

- `sysName`
- `sysDescr`
- `sysUpTime`
- `ifNumber`

Quando si recupera il MIB reale dal firewall, aggiungere gli OID proprietari via:

```env
NETWORK_SOPHOS_SNMP_CUSTOM_OIDS=[
  {"key":"cpu_usage","oid":"1.3.6.1.x.x.x","mode":"int","unit":"percent"},
  {"key":"memory_usage","oid":"1.3.6.1.x.x.x","mode":"int","unit":"percent"}
]
```

## Check finale

L’integrazione e considerata corretta quando:

1. `/network/firewalls` mostra almeno un firewall `online`
2. la dashboard rete mostra `firewalls_online > 0`
3. arrivano eventi in pagina firewall dopo l’invio syslog
4. arrivano metriche SNMP dopo il polling manuale o schedulato
5. la dashboard rete non mostra warning di `coverage log Sophos incompleta`
6. la pagina `/network/firewalls` mostra le famiglie attese con stato `ok` o evidenzia chiaramente quelle mancanti

## Sequenza operativa consigliata

1. Copiare nel `.env` reale le variabili da `docs/examples/sophos.env.template`.
   Se lavori sullo stack CBO gia in uso, puoi partire da `docs/examples/sophos.env.cbo-current`.
   Per il server CED/produzione, usare community `GAIA-prod`.
2. Avviare i collector:
   `docker compose up -d backend sophos-syslog sophos-snmp`
3. Configurare sul Sophos l’invio syslog UDP verso il server GAIA su porta `5514`.
4. Abilitare SNMPv2c sul Sophos verso il server GAIA con la community impostata nel `.env`.
5. Eseguire:
   `./scripts/check-sophos-integration.sh`
6. Se disponibile un token GAIA admin:
   `TOKEN=<jwt> ./scripts/check-sophos-integration.sh`
7. Eseguire lo smoke end-to-end:
   `./scripts/smoke-network-vpn-bypass.sh`

## Coverage log Sophos

GAIA classifica automaticamente i log ricevuti per famiglia operativa:

- `firewall`
- `vpn`
- `ips`
- `authentication`
- `system`

La pagina `/network/firewalls` espone una card `Coverage log Sophos` che mostra:

- conteggio osservato per famiglia nelle ultime `168h`
- ultimo evento ricevuto
- esempi di `event_type`
- famiglie mancanti rispetto all’atteso
- famiglie extra osservate, ad esempio `content_filtering`

La dashboard rete mostra anche un warning sintetico quando una o piu famiglie attese non stanno arrivando.

## Riepilogo traffico per dispositivo

Nel dettaglio di ogni device su `/network/devices` GAIA mostra una sintesi del traffico Sophos delle ultime 24 ore:

- traffico in ingresso e in uscita
- eventi consentiti / bloccati
- peer principali
- ultimi eventi osservati

Per i peer esterni GAIA prova a mostrare una label leggibile con questa precedenza:

1. `domain` o hostname estratto da `url` nel log Sophos
2. reverse DNS
3. fallback RDAP/organizzazione

## Convenzione IP leggibili

Nel modulo rete, quando GAIA conosce il device o il detentore associato, gli IP vengono mostrati come:

- `192.168.1.13 · Simona Frau`
- `192.168.1.83 · PC Ubuntu Server`

La precedenza del riferimento e:

1. `application_users.full_name`
2. `application_users.username`
3. `network_devices.display_name`
4. `network_devices.hostname`

La convenzione e applicata nelle viste operative principali:

- dashboard rete
- lista e dettaglio dispositivi
- modal rapida dispositivo
- planimetria
- dettaglio scansioni
- statistiche
- eventi firewall Sophos per `src_ip` e `dst_ip` quando l'IP e correlato a un device noto

## Tracking operativo di device, IP, domini e URL

GAIA permette all’operatore di marcare come `tracciato` un target di interesse e seguirne poi le attivita nella sezione dedicata `/network/tracking`.

Punti UI abilitati:

- dettaglio dispositivo: tracking del device e dei peer IP osservati
- pagina `/network/firewalls`: tracking rapido di `src_ip`, `dst_ip`, `domain` e `url`
- pagina `/network/statistics`: tracking di top domini, top destinazioni e top device sorgente

Tipi supportati:

- `device`
- `ip`
- `domain`
- `url`

Comportamento operativo:

- se un target e gia presente, il flag non crea duplicati ma riattiva il record esistente
- la pagina `/network/tracking` mostra:
  - stato attivo/disattivo
  - label e note operative
  - volume traffico in/out delle ultime 168 ore
  - conteggio eventi `allowed` e `blocked`
  - ultimi eventi correlati
  - label leggibili per gli eventi Sophos piu comuni
  - `Dettaglio IP` per IP pubblici, risolto via RDAP dal backend
  - per i target `device`, ultimi snapshot storici del PC/apparato monitorato
  - per i target `device`, il pulsante `Analizza navigazione con Gaia Wiki`, disponibile solo a `admin` e `super_admin`

API utili:

```bash
curl -H "Authorization: Bearer <TOKEN>" http://localhost:8080/api/network/tracking
```

```bash
curl -X POST \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  http://localhost:8080/api/network/tracking \
  -d '{"entity_type":"ip","value":"8.8.8.8","label":"Google DNS"}'
```

```bash
curl -H "Authorization: Bearer <TOKEN>" \
  http://localhost:8080/api/network/tracking/1/activities
```

```bash
curl -H "Authorization: Bearer <TOKEN>" \
  http://localhost:8080/api/network/ip-whois/8.8.8.8
```

## Retention e aggregati statistiche

Per sostenere volumi alti di syslog Sophos:

- la pagina `/network/statistics` legge prioritariamente da rollup orari persistiti
- il raw di `network_firewall_events` resta per drilldown, tracking e correlazione fine
- il raw vecchio viene potato automaticamente con retention configurabile

Variabili utili:

- `NETWORK_TELEMETRY_ROLLUP_ENABLED`
- `NETWORK_TELEMETRY_ROLLUP_CRON`
- `NETWORK_TELEMETRY_ROLLUP_TIMEZONE`
- `NETWORK_TELEMETRY_ROLLUP_LOOKBACK_HOURS`
- `NETWORK_FIREWALL_RAW_RETENTION_DAYS`

Linea guida operativa consigliata:

- raw eventi Sophos: `14` giorni
- rollup orari: conservazione lunga per statistiche e trend
- tracking e drilldown: continuano a usare il raw finche presente nella retention

Backfill storico controllato:

```bash
docker compose exec backend python backend/scripts/backfill_network_firewall_rollups.py \
  --from 2026-06-01 \
  --to 2026-06-06 \
  --chunk-days 1
```

Note operative:

- usare `chunk-days=1` per popolare giornate singole su volumi alti
- aumentare a `7` solo se il carico e sostenibile
- il backfill riscrive i rollup del range selezionato senza toccare il raw fuori finestra

## Discovery ARP per device sconosciuti

Quando serve identificare host presenti sul segmento locale ma non ancora censiti o senza porte aperte evidenti, usare la modalita `ARP discovery` del modulo rete.

Caratteristiche:

- focus su presenza reale L2/LAN
- raccolta di `ip_address` e `mac_address`
- hostname best-effort via `dns`, `mdns` e `netbios`
- nessun intento di spoofing o MITM: il modulo invia solo richieste ARP di discovery

Uso applicativo:

- dashboard rete: pulsante `Discovery ARP`
- pagina `/network/scans`: pulsante `Discovery ARP`

API:

```bash
curl -X POST \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  http://localhost:8080/api/network/scans \
  -d '{"scan_type":"arp"}'
```

Risultato atteso:

- nuovo snapshot con `scan_type=arp`
- aggiornamento di `network_devices` con i device presenti sul segmento
- valorizzazione di `metadata_sources.discovery=arp`
- comparsa piu rapida dei device sconosciuti nella lista rete e nelle statistiche

## Import censimento Excel

Per popolare l’anagrafica operativa dei device dal file di censimento:

```bash
PYTHONPATH=backend DATABASE_URL='postgresql+psycopg://<user>:<password>@127.0.0.1:5434/<db>' \
python3 backend/scripts/import_network_census_xlsx.py '/percorso/CensimentoInformaticoCBO.xlsx'
```

Per applicare le modifiche:

```bash
PYTHONPATH=backend DATABASE_URL='postgresql+psycopg://<user>:<password>@127.0.0.1:5434/<db>' \
python3 backend/scripts/import_network_census_xlsx.py --apply '/percorso/CensimentoInformaticoCBO.xlsx'
```

Lo script:

- normalizza la colonna `IP` anche quando contiene solo l’ultimo ottetto
- aggiorna solo i device gia presenti in GAIA
- compila `display_name`, `location_hint`, `notes`, `is_known_device`
- registra in `notes` il marcatore `[Censimento CBO]` con interno telefonico, servizio e licenza Office se disponibile

## Sync device -> application_users

Per trasformare i label device gia presenti in mapping espliciti verso `application_users`:

```bash
PYTHONPATH=backend DATABASE_URL='postgresql+psycopg://<user>:<password>@127.0.0.1:5434/<db>' \
python3 backend/scripts/sync_network_devices_to_application_users.py
```

Per applicare le modifiche:

```bash
PYTHONPATH=backend DATABASE_URL='postgresql+psycopg://<user>:<password>@127.0.0.1:5434/<db>' \
python3 backend/scripts/sync_network_devices_to_application_users.py --apply
```

Lo script:

- cerca match esatti normalizzati tra `network_devices.display_name` e `application_users`
- assegna `network_devices.assigned_user_id` quando trova un solo match non ambiguo
- valorizza `application_users.full_name`, `office_location` e `phone_extension` se mancanti
- resta in `dry-run` di default e stampa preview dei match, dei mancati match e dei casi ambigui

## Cambio detentore e rotamazione device

Dal dettaglio device o dalla modal rapida su `/network/devices` e possibile:

- cambiare il detentore selezionando un diverso `application_users`
- sganciare completamente il device dall'utente corrente
- marcare il device come `rotamato`

Effetto della rotamazione:

- `assigned_user_id = null`
- `is_monitored = false`
- `lifecycle_state = retired`
- valorizzazione di `retired_at`
- esclusione del device dai conteggi operativi dashboard
