# GAIA GIS Platform - QGIS Desktop Runbook

> Data: 2026-07-14.
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

Il percorso target M12 e un progetto `.qgz` unico generato dalla GIS Platform
per l'utente corrente. Il progetto deve includere:

- solo layer visibili all'utente nel catalogo `/gis/catalogo`;
- connessione PostGIS verso schema governato, preferibilmente `gis_qgis`;
- gruppi per workspace o dominio;
- stili e nomi layer comprensibili;
- layer Catasto read-only;
- eventuali layer editabili solo se il dominio ha policy `controlled`.

Finche l'endpoint di generazione non e implementato, l'operatore usa il catalogo
per individuare i layer e configura manualmente il progetto seguendo questa
stessa struttura.

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

## Editing Controllato

L'editing diretto da QGIS e ammesso solo quando tutte le condizioni sono vere:

- layer non Catasto;
- layer attivo e sorgente PostGIS;
- metadata catalogo `qgis.editable=true`;
- metadata catalogo `qgis.edit_policy=controlled`;
- operatore assegnato a ruolo DB editor dedicato;
- dominio proprietario ha definito rollback e audit operativo.

Se una condizione manca, si usa il workflow change request GAIA.

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
- Testare accesso reader su view `gis_qgis`.
- Testare che Catasto sia read-only.
- Documentare eventuali layer non Catasto abilitati a controlled edit.
