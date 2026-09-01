# GAIA GIS Platform - QGIS Desktop Runbook

> Data: 2026-07-15.
> Scope: uso sicuro di QGIS Desktop con PostGIS come sorgente ufficiale.

## Principio Operativo

QGIS Desktop e un client tecnico. La sorgente ufficiale resta PostGIS; gli
shapefile NAS sono solo export/backup versionati e non devono essere modificati
come dato vivo.

## Ruoli Database

La piattaforma GIS genera una policy SQL da:

```http
GET /gis/qgis/governance
```

L'endpoint e admin-only e restituisce:

- schema pubblicabile `gis_qgis`;
- ruoli gruppo NOLOGIN `gaia_gis_qgis_reader`, `gaia_gis_qgis_editor`,
  `gaia_gis_qgis_admin`;
- view read-only per layer PostGIS attivi;
- grant edit solo su layer non Catasto con metadata QGIS `editable=true` e
  `edit_policy=controlled`;
- SQL completo da revisionare ed eseguire sul database PostgreSQL.

I ruoli LOGIN reali non vengono creati automaticamente da GAIA. Devono essere
creati per ambiente e assegnati a uno dei ruoli gruppo:

```sql
CREATE ROLE qgis_nomeutente LOGIN PASSWORD '<password-temporanea>';
GRANT gaia_gis_qgis_reader TO qgis_nomeutente;
```

Per utenze operative autorizzate all'editing controllato:

```sql
GRANT gaia_gis_qgis_editor TO qgis_nomeutente;
```

## Connessione QGIS

1. Aprire QGIS Desktop.
2. Creare una connessione PostgreSQL/PostGIS verso il database GAIA.
3. Usare un ruolo LOGIN dedicato `qgis_*`, mai l'utente applicativo backend.
4. Caricare i layer dallo schema `gis_qgis`.
5. Verificare che i layer Catasto risultino read-only.
6. Salvare eventuali progetti `.qgz` in percorso controllato e referenziabile
   dal catalogo layer, non dentro export NAS shapefile.

## Progetto QGIS Unico

La GIS Platform genera un progetto `.qgz` unico per l'utente corrente:

```http
GET /gis/qgis/project
```

La UI espone lo stesso download nella scheda `QGIS Desktop in un colpo` di
`/gis/catalogo`, dentro la sezione richiudibile `Strumenti per utenti esperti`.

L'archivio `.qgz` contiene:

- `gaia-gis-platform.qgs`, progetto QGIS con gruppi per workspace;
- `manifest.json`, elenco dei layer inclusi e policy di esclusione;
- `README_QGIS.txt`, istruzioni operative per aprire il progetto.

Regole di inclusione:

- solo layer attivi e visibili all'utente;
- layer PostGIS con colonna geometrica e layer territoriali esterni WMS;
- solo layer con colonna geometrica configurata;
- esclusione di layer `postgis_staging`, registry applicativi e metadata
  `qgis.mode=not_published`;
- connessione PostGIS tramite servizio client `gaia_gis`;
- layer Catasto read-only;
- eventuali layer editabili solo se il dominio ha policy `controlled` e ruoli
  DB coerenti.

### Layer Territoriali Via Proxy GAIA

I layer del workspace `territorio` sono inseriti come provider WMS che punta a
`GIS_QGIS_PROXY_BASE_URL`, mai agli endpoint remoti RAS o AdE. Il valore deve
essere la base URL HTTPS di GAIA raggiungibile dalle postazioni QGIS, per
esempio `https://gaia.example.local`.

Il progetto usa `authcfg=gaia_oauth` e non contiene token o password. Prima di
aprire il progetto:

1. creare in QGIS una configurazione di autenticazione con ID `gaia_oauth`;
2. configurarla con una credenziale GAIA personale abilitata al modulo GIS;
3. verificare che QGIS raggiunga `GIS_QGIS_PROXY_BASE_URL` via HTTPS;
4. non esportare o condividere il database autenticazioni QGIS.

L'endpoint `/gis/external/{layer_id}/qgis-wms` accetta da QGIS solo `LAYERS`
uguale al layer locale atteso e delega al proxy governato M21. Permessi,
allowlist, cache, timeout e audit degli errori restano quindi applicati.

## Pubblicazione OGC Read-Only

QGIS Server resta sulla rete interna e non deve essere pubblicato direttamente
su internet. Il solo endpoint supportato dai client e il proxy GAIA:

```text
GET /gis/ogc/layers/{layer_id}?SERVICE=WMS&REQUEST=GetCapabilities
GET /gis/ogc/layers/{layer_id}?SERVICE=WMS&REQUEST=GetMap&...
GET /gis/ogc/layers/{layer_id}?SERVICE=WFS&REQUEST=GetCapabilities
GET /gis/ogc/layers/{layer_id}?SERVICE=WFS&REQUEST=GetFeature&...
```

Il client passa un `layer_id` del catalogo, mai l'URL QGIS Server, il path del
progetto o un URL remoto. GAIA verifica autenticazione, `module_gis`,
`can_view`, stato attivo, sorgente PostGIS e `qgis.mode` pubblicabile. Le
capabilities vengono ridotte al solo layer autorizzato. `POST` e WFS-T sono
sempre rifiutati con `400`.

Configurazione ambiente:

```dotenv
GIS_QGIS_SERVER_INTERNAL_URL=http://qgis-server/ows/
GIS_QGIS_SERVER_TIMEOUT_SECONDS=12
GIS_QGIS_PROXY_BASE_URL=https://gaia.example.local
```

`GIS_QGIS_SERVER_INTERNAL_URL` e raggiungibile solo dal backend. Nella rete
Docker usa il nome servizio `qgis-server`; non pubblicare una porta host del
container. Se backend e QGIS Server sono separati, usare la rete VPN CED e una
regola firewall che ammetta solo il backend GAIA. In entrambi i casi
`GIS_QGIS_PROXY_BASE_URL` e la base HTTPS GAIA raggiungibile dai client QGIS.

Il progetto `.qgz` e le capabilities non devono contenere password, token,
credenziali DB o l'URL interno QGIS Server. L'autenticazione client resta nella
configurazione QGIS locale `gaia_oauth`; la scelta tra LOGIN personali e LOGIN
per postazione resta aperta e non e risolta da questo proxy.

Anche il progetto QGIS Server non contiene credenziali: usa
`service=gaia_gis_server`. Il bootstrap genera separatamente
`/srv/qgis/pg_service.conf` con modo `0600`; lo startup lo installa in
`/var/lib/qgis/pg_service.conf` e `PGSERVICEFILE` punta a quel file. Il file e
un secret runtime del container, non va copiato nei progetti, esportato o
committato.

Smoke minimo:

1. Eseguire GetCapabilities come utente con `can_view` e verificare un solo
   layer, con URL online sotto `GIS_QGIS_PROXY_BASE_URL`.
2. Eseguire GetMap sullo stesso `layer_id` e verificare `200` e
   `X-GAIA-OGC-Mode: read-only`.
3. Revocare `can_view` e verificare `403` senza chiamata a QGIS Server.
4. Eseguire un GetFeature WFS e verificare che il tipo sia quello governato.
5. Tentare una Transaction WFS via POST e verificare `400`.

Rollback: rimuovere l'accesso client al path `/gis/ogc/layers/` o spegnere il
servizio QGIS Server interno. PostGIS, Martin, catalogo GAIA e proxy WMS
territoriali restano indipendenti. Non applicare automaticamente lo SQL M6 per
effettuare il rollback.

## Pacchetto Offline

Il pacchetto offline ZIP e ammesso solo quando il PC non puo raggiungere il
database GAIA. Deve essere trattato come copia temporanea:

- non sostituisce PostGIS;
- non va reimportato come dato ufficiale senza workflow di validazione;
- deve indicare versione, data export e checksum;
- non contiene annotazioni o change request GAIA.

## Regole Read-Only

- I layer Catasto sono sempre read-only in QGIS.
- I layer senza opt-in esplicito restano read-only.
- Il ruolo `gaia_gis_qgis_reader` deve avere solo `SELECT` sulle view
  pubblicate.
- Le change request e le annotazioni restano in GAIA, non in shapefile.
- L'apply GAIA puo scrivere realmente solo su layer non Catasto con opt-in
  controlled edit; Catasto resta no-op auditato.

## Editing Controllato

L'editing diretto da QGIS e ammesso solo quando tutte le condizioni sono vere:

- layer non Catasto;
- layer attivo e sorgente PostGIS;
- metadata catalogo `qgis.editable=true`;
- metadata catalogo `qgis.edit_policy=controlled`;
- operatore assegnato a ruolo DB editor dedicato;
- dominio proprietario ha definito rollback e audit operativo.

Se una condizione manca, si usa il workflow change request GAIA. Da M20 il
workflow applica realmente la richiesta solo quando il layer non Catasto ha
opt-in controlled edit; negli altri casi produce no-op auditato.

### Primo Opt-In M18

Il primo layer non Catasto registrato con opt-in controlled edit e:

- workspace `rete`;
- domain module `network`;
- layer `rete_condotte`;
- tabella PostGIS `network.rete_condotte`;
- metadata `qgis.mode=controlled_edit`;
- metadata `qgis.editable=true`;
- metadata `qgis.edit_policy=controlled`.

Nel catalogo GIS, il ruolo `viewer` resta read-only. Il ruolo applicativo
`operator` riceve capability GIS `editor`. La governance QGIS genera grant
editor solo per questo layer non Catasto e continua a revocare edit sui layer
Catasto.

## Rotazione Credenziali

- Ruoli LOGIN QGIS personali o per postazione, mai condivisi genericamente.
- Rotazione password a cambio personale o almeno ogni 180 giorni.
- Revoca immediata del LOGIN quando un operatore lascia il ruolo.
- Nessuna password QGIS deve essere committata nel repository.

## Divieti

- Non editare shapefile NAS come sorgente viva.
- Non usare credenziali backend/app per QGIS.
- Non concedere privilegi su tabelle Catasto ufficiali a ruoli editor.
- Non usare `superuser`, owner DB o ruoli migration per attivita QGIS.

## Checklist Operativa

- Eseguire `GET /gis/qgis/governance` come admin.
- Revisionare SQL generato.
- Eseguire SQL in manutenzione controllata.
- Creare ruoli LOGIN `qgis_*` separati.
- Configurare sul PC QGIS il servizio PostgreSQL `gaia_gis`.
- Configurare `gaia_oauth` per i layer territoriali via proxy GAIA.
- Scaricare il progetto da `/gis/catalogo` o da `GET /gis/qgis/project`.
- Testare accesso reader su view `gis_qgis`.
- Testare che Catasto sia read-only.
- Documentare eventuali layer non Catasto abilitati a controlled edit.
