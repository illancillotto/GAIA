# GAIA GIS Platform - OGC Decision Record

> Data: 2026-07-14.
> Milestone: M7.
> Stato: decisione architetturale iniziale, nessun runtime OGC introdotto.

## Decisione

GAIA non introduce subito un server OGC nel runtime di produzione. La piattaforma
mantiene PostGIS + Martin + API GAIA come baseline operativa.

Se emerge un bisogno concreto di WMS/WFS/WMTS oltre a Martin e API GAIA, il primo
POC raccomandato e QGIS Server in modalita read-only, per riusare progetti,
stili e competenze QGIS gia previste in M6. GeoServer resta l'opzione da
preferire se il requisito principale diventa governance OGC multi-dominio con
workspace, sicurezza per layer e amministrazione OGC granulare.

## Fonti Primarie

- QGIS Server documenta servizi OGC WMS, WFS, OGC API Features, WCS e WMTS:
  https://docs.qgis.org/3.44/en/docs/server_manual/services.html
- GeoServer documenta workspace/store/layer nel web admin:
  https://docs.geoserver.org/main/en/user/data/webadmin/layers/
- GeoServer documenta sicurezza per layer e ruoli:
  https://docs.geoserver.org/main/en/user/security/layer/

## Contesto GAIA

- PostGIS e sorgente ufficiale.
- Martin serve gia tile vettoriali Catasto.
- `/gis` governa catalogo, permessi, annotazioni, change request, export e
  policy QGIS Desktop.
- `/catasto/gis` resta workspace Catasto separato.
- QGIS Desktop e governato da M6 tramite ruoli DB e view read-only.
- Gli shapefile NAS restano export/backup, non dato vivo.

## Criteri Di Valutazione

| Criterio | QGIS Server | GeoServer |
| --- | --- | --- |
| Riuso progetti QGIS | Forte | Debole/indiretto |
| Riuso stili QGIS | Forte | Richiede conversione/SLD o setup separato |
| WMS read-only | Buono | Buono |
| WFS read-only | Buono | Buono |
| OGC API Features | Disponibile | Disponibile secondo configurazione/versione |
| Sicurezza layer/workspace | Da progettare con proxy/auth esterni | Nativa e granulare nel modello GeoServer |
| UI amministrativa OGC | Limitata | Forte |
| Multi-dominio enterprise | Medio | Forte |
| Costo operativo iniziale GAIA | Basso/medio | Medio/alto |
| Coerenza con M6 QGIS Desktop | Alta | Media |
| WFS-T/editing remoto | Non baseline GAIA | Possibile, ma da bloccare finche non integrato con workflow GAIA |

## Raccomandazione

1. Non attivare server OGC in produzione nella baseline M7.
2. Se serve pubblicazione mappa standard, avviare POC QGIS Server read-only.
3. Limitare il POC a WMS/WFS read-only, dietro proxy autenticato.
4. Usare solo layer/view pubblicabili da `GET /gis/qgis/governance`.
5. Non abilitare WFS-T o editing OGC finche change request/apply ufficiale non
   ha policy dominio esplicita.
6. Riesaminare GeoServer se i requisiti diventano multi-tenant, workspace
   cross-dominio, sicurezza OGC nativa o amministrazione tramite console.

## POC QGIS Server

Scope:

- container separato non incluso nel runtime produzione di default;
- progetto `.qgz` minimale generato da layer `gis_qgis`;
- servizi WMS e WFS read-only;
- proxy interno con autenticazione GAIA o rete privata;
- nessun accesso diretto a tabelle Catasto ufficiali;
- test GetCapabilities, GetMap, GetFeatureInfo e GetFeature.

Exit criteria:

- pubblica solo layer consentiti dalla policy M6;
- non espone credenziali DB owner/backend;
- non permette transazioni WFS-T;
- latenza GetMap accettabile sui layer target;
- runbook deploy/rollback documentato.

## POC GeoServer

Scope:

- container separato non incluso nel runtime produzione di default;
- workspace per dominio GAIA;
- datastore PostGIS read-only verso view `gis_qgis`;
- layer security per ruolo;
- WMS/WFS read-only;
- valutazione UI admin, backup config e promozione ambienti.

Exit criteria:

- workspace e layer security verificati;
- nessun anonymous access non voluto;
- nessun WFS-T o write access;
- effort operativo accettabile per CED;
- piano backup/restore `GEOSERVER_DATA_DIR`.

## Sicurezza E Proxy

- Ogni server OGC deve stare dietro proxy autenticato o rete privata.
- Le credenziali DB devono essere ruoli QGIS/OGC dedicati, mai backend owner.
- I layer Catasto restano read-only.
- WFS-T e write operations sono disabilitati nella baseline.
- Capabilities pubblicate devono essere testate per evitare leak di layer non
  autorizzati.
- Log accesso e audit proxy devono essere conservati secondo policy CED.

## Piano Rollout Se Il POC Passa

1. Decisione esplicita su QGIS Server o GeoServer.
2. Branch dedicato con compose/profile separato, non default.
3. Secret DB dedicati per OGC.
4. Smoke test automatici su capabilities e layer ammessi.
5. Runbook deploy/rollback.
6. Abilitazione progressiva prima in ambiente interno.
7. Aggiornamento catalogo `/gis` con URL OGC per layer pubblicati.

## Decisione Da Riesaminare

Riesaminare entro una milestone successiva se:

- piu domini chiedono servizi WMS/WFS stabili;
- utenti esterni a QGIS Desktop richiedono OGC;
- Martin/API GAIA non coprono piu i casi d'uso mappa;
- serve amministrazione OGC granulare non gestibile con QGIS Server e proxy.
