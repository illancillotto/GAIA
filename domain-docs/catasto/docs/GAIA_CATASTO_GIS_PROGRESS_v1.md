# GAIA — Modulo Catasto GIS
## Progress Tracker v1

---

## Stato generale

| Fase | Descrizione | Status | Note |
|---|---|---|---|
| **GIS-1** | Infrastruttura: Martin + nginx + view DB | 🔴 Non iniziato | |
| **GIS-2** | Backend API GIS: route + service + schemas | 🔴 Non iniziato | Dipende da GIS-1 |
| **GIS-3** | Frontend base: mappa + layer MVT + popup | 🔴 Non iniziato | Dipende da GIS-1, GIS-2 |
| **GIS-4** | Drawing tools + selezione + analisi live | 🔴 Non iniziato | Dipende da GIS-3 |
| **GIS-5** | Export + filtri + rifinitura navigazione | 🔴 Non iniziato | Dipende da GIS-4 |

Legend: 🔴 Non iniziato · 🟡 In corso · 🟢 Completato · ⚫ Bloccato

---

## GIS-1 — Infrastruttura

| # | Task | Status | File | Note |
|---|---|---|---|---|
| 1.1 | View `cat_particelle_current` (migration Alembic) | 🔴 | `backend/alembic/versions/xxxx_catasto_gis_view.py` | |
| 1.2 | Servizio Martin in `docker-compose.yml` | 🔴 | `docker-compose.yml` | |
| 1.3 | `config/martin.toml` | 🔴 | `config/martin.toml` | |
| 1.4 | Proxy nginx `/tiles/` | 🔴 | `nginx/nginx.conf` | |
| 1.5 | Verifica Martin avviato e tile endpoint raggiungibile | 🔴 | — | Test manuale |

---

## GIS-2 — Backend API GIS

| # | Task | Status | File | Note |
|---|---|---|---|---|
| 2.1 | `gis_schemas.py` — Pydantic schemas | 🔴 | `backend/app/modules/catasto/schemas/gis_schemas.py` | |
| 2.2 | `gis_service.py` — logica PostGIS | 🔴 | `backend/app/modules/catasto/services/gis_service.py` | |
| 2.3 | `gis.py` — route FastAPI | 🔴 | `backend/app/modules/catasto/routes/gis.py` | |
| 2.4 | Registrazione router GIS nel modulo | 🔴 | File router aggregatore catasto | |
| 2.5 | Verifica endpoint in Swagger UI | 🔴 | — | Test manuale |

---

## GIS-3 — Frontend base

| # | Task | Status | File | Note |
|---|---|---|---|---|
| 3.1 | `npm install maplibre-gl @mapbox/maplibre-gl-draw` | 🔴 | `frontend/package.json` | |
| 3.2 | CSS import MapLibre + Draw | 🔴 | `globals.css` o `layout.tsx` | |
| 3.3 | `next.config.js` update (se necessario) | 🔴 | `frontend/next.config.js` | Solo se SSR errori |
| 3.4 | `frontend/src/types/gis.ts` | 🔴 | `frontend/src/types/gis.ts` | |
| 3.5 | `useGisSelection.ts` hook | 🔴 | `frontend/src/hooks/useGisSelection.ts` | |
| 3.6 | `MapContainer.tsx` | 🔴 | `frontend/src/components/catasto/gis/MapContainer.tsx` | |
| 3.7 | Pagina `/catasto/mappa` (base, senza draw) | 🔴 | `frontend/src/app/catasto/mappa/page.tsx` | |
| 3.8 | Verifica mappa carica e layer visibili | 🔴 | — | Test manuale |

---

## GIS-4 — Drawing + Analisi

| # | Task | Status | File | Note |
|---|---|---|---|---|
| 4.1 | `DrawingTools.tsx` | 🔴 | `frontend/src/components/catasto/gis/DrawingTools.tsx` | |
| 4.2 | `AnalysisPanel.tsx` | 🔴 | `frontend/src/components/catasto/gis/AnalysisPanel.tsx` | |
| 4.3 | `SelectionPanel.tsx` | 🔴 | `frontend/src/components/catasto/gis/SelectionPanel.tsx` | |
| 4.4 | Integrazione draw → POST /catasto/gis/select → risultati | 🔴 | `page.tsx` + `MapContainer.tsx` | |
| 4.5 | Highlight particelle selezionate su mappa | 🔴 | `MapContainer.tsx` | |
| 4.6 | Popup particella con fetch popup endpoint | 🔴 | `MapContainer.tsx` | |
| 4.7 | Test E2E: draw → analisi → popup | 🔴 | — | Test manuale |

---

## GIS-5 — Export + Rifinitura

| # | Task | Status | File | Note |
|---|---|---|---|---|
| 5.1 | Export CSV da `AnalysisPanel` | 🔴 | `AnalysisPanel.tsx` + `gis_service.py` | |
| 5.2 | Export GeoJSON da `AnalysisPanel` | 🔴 | `AnalysisPanel.tsx` + `gis_service.py` | |
| 5.3 | Link "Mappa GIS" nella sidebar catasto | 🔴 | Sidebar catasto | |
| 5.4 | Verifica sezione in catalogo permessi GAIA | 🔴 | Bootstrap backend | Solo se necessario |
| 5.5 | Test performance: selezione distretto < 1s | 🔴 | — | Test con DB popolato |
| 5.6 | `npm run build` pulito | 🔴 | — | Nessun errore TS/ESLint |

---

## Domande aperte

| ID | Domanda | Status | Risposta |
|---|---|---|---|
| GIS-OQ-01 | Shapefile particelle è già stato importato in produzione? | ❓ Aperto | — |
| GIS-OQ-02 | La view `geometry_columns` è necessaria per Martin o Martin usa info_schema? | ❓ Aperto | Da verificare con Martin |
| GIS-OQ-03 | Il proxy Next.js per le API usa `/api/` come prefisso? | ❓ Aperto | Adattare path nel hook |
| GIS-OQ-04 | Come viene recuperato il JWT nel frontend? (cookie httpOnly, localStorage, Zustand?) | ❓ Aperto | Adattare hook auth |

---

## Note tecniche

- Martin rileva automaticamente tabelle e view con colonna `geometry` — non richiede dichiarazione esplicita in `geometry_columns`
- `ST_Transform(geometry, 32632)` per aree in ha usa UTM zone 32N (corretto per Sardegna)
- `@mapbox/maplibre-gl-draw` richiede alias webpack `'mapbox-gl': 'maplibre-gl'` in alcuni ambienti Next.js — testare prima di aggiungere
- La view `cat_particelle_current` include `ha_anomalie` come subquery: aggiungere indice su `cat_anomalie(particella_id, status)` se le performance popup sono lente
- Se DB vuoto in sviluppo, Martin risponde 204 (No Content) per tile senza dati — comportamento atteso, non errore
