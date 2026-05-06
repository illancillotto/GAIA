# GAIA — Modulo Catasto GIS
## Product Requirements Document v1

> Collocazione: estensione del modulo esistente `backend/app/modules/catasto/`
> Documentazione: `domain-docs/catasto/docs/`
> Prerequisito: Catasto Fase 1 completata (🟢), Catasto Fase 2 (GIS base) non iniziata (🔴)

---

## 1. Contesto e obiettivi

### 1.1 Contesto operativo

Il modulo Catasto di GAIA gestisce circa 300.000–500.000 particelle catastali relative ai distretti irrigui del Consorzio di Bonifica dell'Oristanese. Le tabelle `cat_particelle` e `cat_distretti` con geometrie PostGIS sono già presenti nel database dopo l'import dello shapefile (Catasto Fase 1). Martin tile server è pianificato ma non ancora deployato.

Il flusso attuale consente di consultare particelle e distretti solo in forma tabellare. Non esiste strumento per:
- navigare spazialmente il territorio
- disegnare aree di interesse e interrogarle
- calcolare aggregazioni live su selezioni arbitrarie
- correlare la distribuzione geografica delle particelle con anomalie e tributi

### 1.2 Obiettivi del modulo GIS

**Obiettivo primario**: dotare GAIA di un motore di analisi spaziale interattivo, integrato nel modulo Catasto esistente, senza introdurre nuovi moduli backend o duplicazioni del modello dati.

**Obiettivi specifici**:
- Visualizzazione mappa interattiva con layer particelle, fogli e distretti
- Selezione spaziale: click singolo, selezione multipla, selezione per area disegnata
- Disegno geometrie libere (poligono, rettangolo) per selezioni e analisi
- Calcoli live server-side: superficie totale, conteggio, aggregazione per foglio/distretto
- Filtri alfanumerici integrati con la mappa (comune, foglio, distretto)
- Export dei risultati di selezione (GeoJSON, CSV)
- Popup particella con collegamento alla scheda esistente

### 1.3 Vincoli di dominio

| Vincolo | Descrizione |
|---|---|
| Nessun nuovo modulo backend | Il GIS è un'estensione di `catasto`, non un modulo separato |
| Nessun nuovo schema DB | Le tabelle `cat_particelle` e `cat_distretti` esistenti sono le sorgenti dati |
| Stack frontend invariato | MapLibre GL JS (già pianificato per Catasto Fase 2), niente OpenLayers |
| Tile server | Martin (già previsto nel progetto), niente GeoServer |
| SRID | DB in EPSG:4326, tiles servite da Martin in EPSG:3857 (automatico) |
| Query server-side obbligatorie | Nessuna elaborazione geometrica lato frontend |
| Auth GAIA | JWT esistente, ruoli `admin` / `reviewer` / `viewer` |

---

## 2. Utenti e casi d'uso

### 2.1 Operatore tecnico (viewer / reviewer)
- Naviga la mappa e consulta i dati catastali
- Seleziona particelle singole o per area
- Visualizza calcoli aggregati (superficie, conteggio)
- Esporta selezioni in CSV o GeoJSON

### 2.2 Responsabile / amministratore (admin)
- Accesso completo a tutte le funzionalità
- Esporta dati completi per distretto o foglio
- Accesso alla scheda particella con azioni sulle anomalie

---

## 3. Funzionalità

### RF-01 — Visualizzazione mappa

**Basemap**: OpenStreetMap raster (tile pubbliche, nessuna dipendenza da servizi a pagamento)

**Layer disponibili**:
- Distretti: poligoni MVT da Martin, colorati per status anomalie
- Particelle: MVT da Martin, caricamento dinamico per viewport
- Fogli mappali: MVT da Martin (se geometrie disponibili nello shapefile)

**Comportamento**:
- Zoom adattivo con generalizzazione automatica (gestita da Martin via semplificazione MVT)
- Toggle on/off per ogni layer
- Legenda colori (distretto status, particella anomalie)

### RF-02 — Selezione particelle

**Modalità**:
- Click singolo: seleziona la particella clickata
- Shift+click: aggiunge alla selezione corrente
- Disegna poligono: seleziona tutte le particelle intersecanti
- Disegna rettangolo (bounding box): selezione rapida su area

**Output selezione**:
- Lista particelle selezionate nel pannello laterale destro
- Evidenziazione su mappa (colore selezione distinto)
- Conteggio live e superficie totale calcolati server-side
- Link alla scheda particella per ogni record

### RF-03 — Disegno geometrie

**Strumenti** (via MapLibre Draw):
- Poligono libero
- Rettangolo (box)
- Reset / cancella selezione

**Uso**:
- Il poligono disegnato viene inviato al backend come GeoJSON per la query spaziale
- La geometria NON viene persistita (sessione corrente only per il MVP)

### RF-04 — Analisi live (core feature)

Tutti i calcoli vengono eseguiti server-side su `POST /catasto/gis/select`.

**Calcoli obbligatori**:

Superficie totale delle particelle selezionate:
```sql
SELECT SUM(ST_Area(ST_Transform(p.geometry, 32632))) / 10000 AS superficie_ha
FROM cat_particelle p
WHERE ST_Intersects(p.geometry, ST_GeomFromGeoJSON(:geojson))
  AND p.is_current = TRUE
```

Conteggio particelle:
```sql
SELECT COUNT(*) FROM cat_particelle
WHERE ST_Intersects(geometry, ST_GeomFromGeoJSON(:geojson))
  AND is_current = TRUE
```

Aggregazione per foglio:
```sql
SELECT foglio, COUNT(*) as n_particelle,
       SUM(ST_Area(ST_Transform(geometry, 32632))) / 10000 AS sup_ha
FROM cat_particelle
WHERE ST_Intersects(geometry, ST_GeomFromGeoJSON(:geojson))
  AND is_current = TRUE
GROUP BY foglio ORDER BY foglio
```

Aggregazione per distretto:
```sql
SELECT num_distretto, nome_distretto, COUNT(*), SUM(superficie_mq)/10000
FROM cat_particelle
WHERE ST_Intersects(geometry, ST_GeomFromGeoJSON(:geojson))
  AND is_current = TRUE
GROUP BY num_distretto, nome_distretto
```

**Pannello risultati** (sidebar destra):
- Superficie totale in ha
- N. particelle
- Tabella aggregazione per foglio
- Tabella aggregazione per distretto
- Lista particelle (paginata, max 200 in preview)

### RF-05 — Filtri alfanumerici integrati

Filtri applicabili che riducono il dataset interrogato prima dell'analisi spaziale:
- Comune (cod_comune_istat)
- Foglio
- Distretto (num_distretto)
- Solo particelle con anomalie

I filtri si combinano con la selezione spaziale: l'analisi considera solo le particelle che soddisfano entrambi i criteri.

### RF-06 — Interrogazione attributi (popup particella)

Click su particella nella mappa → popup con:
- CFM (codice foglio mappale)
- Comune
- Foglio / Particella / Subalterno
- Superficie (mq)
- Distretto
- N. anomalie aperte

### RF-07 — Import Excel riferimenti catastali

L'upload Excel nella vista GIS accetta un file con colonne `comune`, `sezione`, `foglio`, `particella`, `sub`.

Regole di risoluzione del campo `comune`:
- nome comune testuale, confrontato case-insensitive
- `cod_comune_capacitas` numerico
- `codice catastale`/Belfiore del comune (es. `G286`)

Le righe vengono risolte sulle particelle correnti (`is_current = TRUE`); i match univoci possono essere restituiti anche come GeoJSON per la visualizzazione immediata in mappa.

Comportamento layer:
- ogni import Excel genera un layer logico distinto nel workspace GIS
- il client puo mantenere piu layer contemporaneamente in mappa, con colore e visibilita indipendenti
- ogni layer importato puo essere salvato in modo persistente come selezione GIS personale
- i layer salvati possono essere ricaricati successivamente anche in combinazione con altri layer salvati o appena importati
- Link → `/catasto/particelle/{id}` (scheda completa esistente)

### RF-08 — Export selezione

Dalla sidebar risultati, pulsanti export:
- **GeoJSON**: geometrie + attributi delle particelle selezionate
- **CSV**: attributi tabulari (senza geometria)

Endpoint: `GET /catasto/gis/export?ids=...&format=geojson|csv`

### RF-09 — Integrazione con modulo Catasto esistente

- Click su distretto nella mappa → apre pannello KPI distretto (riusa componente esistente)
- Popup particella → link alla scheda `/catasto/particelle/{id}` (già implementata in Fase 1)
- Filtro anomalie nella mappa → colorazione basata su `cat_anomalie` (join già disponibile)

---

## 4. Non obiettivi (Fase 1 GIS)

- Editing geometrie (WFS-T o API PATCH)
- Versioning/storico delle geometrie disegnate
- Overlay Sentinel-2 / NDVI (rinviato a Catasto Fase 4)
- Integrazione Network layer / overlay rete
- Editing multiutente o lock ottimistico
- GeoServer (non necessario con Martin)
- Salvataggio persistente delle selezioni disegnate

---

## 5. Performance — vincoli critici

| Requisito | Target |
|---|---|
| Caricamento mappa iniziale | < 2s |
| Risposta `POST /catasto/gis/select` su area < 1 distretto | < 1s |
| Risposta `POST /catasto/gis/select` su area intera AOI | < 3s |
| Supporto particelle | ≥ 300.000 |
| Rendering tiles viewport | < 500ms |

**Garanzie tecniche**:
- Indice GIST su `cat_particelle.geometry` (già presente dalla Fase 1)
- Query con `ST_Intersects` (usa indice) + filtro `is_current = TRUE`
- MVT serviti da Martin con cache automatica
- Frontend: nessuna elaborazione geometrica client-side

---

## 6. Sicurezza

- Autenticazione JWT GAIA esistente (nessuna nuova infrastruttura auth)
- Ruolo `viewer`: accesso read-only a mappa, selezioni, export
- Ruolo `reviewer`: come viewer
- Ruolo `admin`: come reviewer + accesso azioni anomalie dalla scheda
- Tiles Martin esposte solo via nginx proxy (non accessibili direttamente dall'esterno)
- Rate limit su `POST /catasto/gis/select`: max 30 req/min per utente (nginx)

---

## 7. KPI di accettazione

- Mappa carica e mostra layer distretti in < 2s su LAN interna
- Selezione per poligono su 1 distretto completo restituisce risultati in < 1s
- Export GeoJSON di 1000 particelle selezionate si completa in < 5s
- Nessun crash frontend su dataset di 300.000 particelle (tile-based, non GeoJSON full load)
- Popup particella si apre in < 300ms dopo click

---

## 8. Dipendenze e prerequisiti

| Dipendenza | Stato | Note |
|---|---|---|
| Catasto Fase 1 completata | 🟢 | Tabelle, modelli, routes esistenti |
| Shapefile importato in `cat_particelle` | Da verificare | Può essere vuoto in sviluppo |
| Martin container | 🔴 Da aggiungere | `docker-compose.yml` |
| `maplibre-gl` npm | 🔴 Da installare | Frontend |
| `@mapbox/maplibre-gl-draw` npm | 🔴 Da installare | Drawing tools |
| Proxy nginx `/tiles/` | 🔴 Da configurare | |
| `shapely` Python | Da verificare | Già in requirements? |

---

## 9. Evoluzioni future

- Salvataggio selezioni come "sessioni di lavoro" con nome
- Integrazione overlay NDVI / Sentinel-2 (Catasto Fase 4)
- Editing geometrie distretto (WFS-T o PATCH API)
- Storico modifiche geometrie
- Layer rete (overlay con modulo Network)
- Analisi predittiva su base spaziale
- Integrazione drone / immagini aeree
