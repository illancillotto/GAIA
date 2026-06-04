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
