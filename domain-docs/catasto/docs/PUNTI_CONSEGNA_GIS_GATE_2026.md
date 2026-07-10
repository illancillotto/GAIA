# Punti di consegna 2026 - GIS e GATE

## Scopo

Questo documento descrive il flusso operativo per importare in GAIA i punti di consegna / punti di attacco da shapefile NAS, renderli consultabili nel GIS Catasto e prepararli per l'uso operativo su GATE mobile.

## Sorgente dati NAS

La sorgente operativa 2026 e la cartella:

```text
smb://nas_cbo.local/settore catasto/DOMANDE UTENZA IRRIGUA/SHP_PUNTI_CONSEGNA/PUNTI_CONSEGNA 2026_DEF/
```

La cartella contiene shapefile divisi per distretto e per tipologia:

- `Punti_Cons-Con_contatoti`: punti di consegna con contatore.
- `Punti_Cons-Con_Senza_contatoti`: punti di consegna senza contatore.

Gli shapefile contengono le coordinate dei punti. L'import backend legge le geometrie, le riproietta in `EPSG:4326` quando necessario e salva sia la geometria PostGIS sia i campi sorgente utili al dettaglio operativo.

## Configurazione e import

La configurazione della cartella NAS e modificabile solo da utenti `admin` / `super_admin` nella pagina:

```text
/catasto/punti-consegna-configurazione
```

Il backend accetta URI `smb://...` come input operatore, ma l'accesso reale avviene tramite il connettore NAS configurato lato backend (`NAS_HOST`, `NAS_USERNAME`, `NAS_PASSWORD`). I segmenti della share vengono risolti in modo case-insensitive, cosi input come `settore catasto` continuano a puntare alla cartella reale `Settore Catasto`.

Endpoint principali:

- `GET /catasto/delivery-points/import-config`: legge la configurazione corrente.
- `PATCH /catasto/delivery-points/import-config`: aggiorna il path sorgente, solo admin.
- `POST /catasto/delivery-points/import-from-config`: crea un job persistito e avvia l'import in background.
- `GET /catasto/delivery-points/import-jobs/{job_id}`: legge stato, errore e contatori finali del job.
- `POST /catasto/delivery-points/gis-cache/refresh`: genera una nuova revisione tile GIS e riavvia `gaia-martin` tramite Docker socket backend per svuotare la cache server-side dei layer punti/canali.

L'import non resta piu agganciato alla richiesta HTTP lunga: la pagina avvia il job, mostra `Import in corso...` e interroga periodicamente lo stato. Questo evita `Gateway Time-out` quando la lettura degli shapefile dal NAS o il ricollegamento delle letture richiedono piu tempo del timeout del proxy.

## Persistenza Catasto

L'import alimenta:

- `cat_delivery_points`: anagrafica georeferenziata dei punti di consegna.
- `cat_meter_reading_delivery_point_mappings`: mapping operativo tra letture contatori e punti importati.
- `cat_meter_readings.delivery_point_id`: collegamento diretto quando il punto viene risolto.
- `cat_delivery_points_import_config`: configurazione admin della cartella sorgente.
- `catasto_delivery_points_import_jobs`: storico operativo dei job di import NAS, con stato `pending/running/completed/failed`, path elaborato, utente richiedente, errore e contatori finali.

Il matching usa il distretto e il codice punto. Se necessario, gestisce codici distretto composti o normalizzati per agganciare letture storiche e punti importati.

## GIS Catasto

Nel GIS Catasto i punti sono pubblicati come layer MapLibre separati:

- `delivery-points-with-meter`: punti con contatore.
- `delivery-points-without-meter`: punti senza contatore.

La sidebar GIS espone:

- toggle `Punti consegna` per mostrare/nascondere entrambi i layer;
- filtro rapido `Tutti`, `Con contatore`, `Senza contatore`;
- filtro distretto condiviso con gli altri layer GIS.

Il click su un punto apre una scheda React di dettaglio tramite:

```text
GET /catasto/gis/delivery-points/{delivery_point_id}
```

La scheda mostra codice punto, distretto, tipologia, tipo, codice contatore, foto, file sorgente, coordinate sorgente, numero di letture collegate e payload JSON sorgente.

La pagina admin `/catasto/punti-consegna-configurazione` e la console `/catasto/gis` espongono `Aggiorna cache GIS`: l'azione salva una nuova revisione delle tile nel browser e chiede al backend di riavviare `gaia-martin`, cosi vengono rigenerate le tile Martin del GIS (`cat_distretti`, `cat_distretti_boundaries`, `cat_particelle_current`, `cat_delivery_points_current`, `cat_irrigation_canals_current`, `cat_dui_2026_current`). Il layer DUI usa un servizio applicativo generico annuale; `cat_dui_2026_current` e il nome fisico legacy del dataset corrente. Usare l'azione dopo un import o un aggiornamento cartografico se il GIS mostra ancora tile vecchie o parziali.

## GATE mobile

GATE deve consumare solo punti attivi con contatore valido per le letture campo. Il requisito operativo e:

- usare `cat_delivery_points` come sorgente georeferenziata;
- filtrare `is_active = true`, `has_meter = true` e `cod_cont` valorizzato;
- inviare coordinate, codice punto, distretto e codice contatore agli operatori;
- riportare in GAIA le letture campo agganciandole al punto tramite `delivery_point_id` o, in fallback, tramite distretto + codice punto + codice contatore.

Il progetto mobile di riferimento e:

```text
/home/cbo/CursorProjects/GaTe-mobile
```

## Verifiche minime

Prima di consegnare modifiche su questo flusso:

- eseguire test backend import/config:
  `backend/.venv/bin/pytest -q backend/tests/test_catasto_delivery_points_import.py backend/tests/test_catasto_delivery_points_admin_api.py`;
- eseguire coverage backend sui file runtime del flusso:
  `backend/.venv/bin/coverage run -m pytest -q backend/tests/test_catasto_delivery_points_import.py backend/tests/test_catasto_delivery_points_admin_api.py`
  e poi
  `backend/.venv/bin/coverage report -m --fail-under=100 backend/app/modules/catasto/services/delivery_points_import.py backend/app/modules/catasto/services/delivery_points_config.py backend/app/modules/catasto/routes/delivery_points_admin.py`;
- eseguire popup GIS punti consegna:
  `backend/.venv/bin/pytest -q backend/tests/test_catasto_phase1.py -k "gis_delivery_point_popup_returns_operational_details or gis_popup_returns_ruolo_summary_with_multiple_quote"`;
- eseguire coverage frontend sui file runtime testabili:
  `VITEST_COVERAGE_INCLUDE='src/components/catasto/gis/map-filters.ts,src/app/catasto/punti-consegna-configurazione/page.tsx' npm run test:coverage -- tests/unit/catasto-gis-map-filters.test.ts tests/unit/catasto-delivery-points-config-page.test.tsx`;
- verificare che il toggle punti consegna non generi errori MapLibre e che il filtro rapido `Tutti / Con contatore / Senza contatore` continui ad agire sui layer `delivery-points-*`;
- aggiornare `make graphify-catasto-code` e `make graphify-frontend`;
- aggiornare `make graphify-catasto-docs` se la documentazione cambia e le credenziali Graphify sono disponibili.
