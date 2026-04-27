# GAIA — Modulo Catasto GIS
## Frontend Implementation Codex v1
### Per Claude Code / Cursor / GSD CLI

---

## Contesto

Stai lavorando su **GAIA**, frontend Next.js 14 + TailwindCSS.
Repository: `github.com/illancillotto/GAIA`
Frontend path: `frontend/src/`

Il modulo catasto ha Fase 1 completata:
- Pagine `/catasto/`, `/catasto/distretti/`, `/catasto/particelle/`, `/catasto/anomalie/` ✅
- Layout e sidebar catasto esistenti ✅
- Pattern componenti, fetch API con JWT, tipi TypeScript stabiliti ✅

Stai **aggiungendo** la pagina GIS mappa e i suoi componenti.

**Non modificare** componenti o pagine esistenti che non siano citati esplicitamente in questo codex.

---

## STEP F1 — Installazione dipendenze

```bash
cd frontend
npm install maplibre-gl @mapbox/maplibre-gl-draw
npm install -D @types/mapbox__maplibre-gl-draw
```

Se `maplibre-gl` genera errori di import SSR in Next.js, aggiungere a `next.config.js`:

```javascript
// next.config.js
const nextConfig = {
  // ... configurazione esistente ...
  webpack: (config, { isServer }) => {
    if (isServer) {
      // Evita bundling maplibre-gl lato server
      config.externals = [...(config.externals || []), 'maplibre-gl'];
    }
    return config;
  },
  // Se @mapbox/maplibre-gl-draw importa mapbox-gl, aggiungi alias
  webpack: (config) => {
    config.resolve.alias = {
      ...config.resolve.alias,
      'mapbox-gl': 'maplibre-gl'  // Solo se necessario
    };
    return config;
  }
};
```

**Aggiungere CSS MapLibre** in `frontend/src/app/globals.css` o in `layout.tsx`:

```css
@import 'maplibre-gl/dist/maplibre-gl.css';
```

Oppure in `layout.tsx`:
```typescript
import 'maplibre-gl/dist/maplibre-gl.css';
import '@mapbox/maplibre-gl-draw/dist/maplibre-gl-draw.css';
```

**Acceptance**:
- `npm run build` senza errori di import
- CSS mappa caricato (controlli zoom visibili)

---

## STEP F2 — Tipi TypeScript GIS

**File**: `frontend/src/types/gis.ts`

```typescript
export interface GisFilters {
  comune?: string;
  foglio?: string;
  num_distretto?: string;
  solo_anomalie?: boolean;
}

export interface GisSelectRequest {
  geometry: GeoJSON.Geometry;
  filters?: GisFilters;
}

export interface ParticellaGisSummary {
  id: string;
  cfm?: string;
  cod_comune_istat?: string;
  foglio?: string;
  particella?: string;
  subalterno?: string;
  superficie_mq?: number;
  num_distretto?: string;
  nome_distretto?: string;
  ha_anomalie: boolean;
}

export interface FoglioAggr {
  foglio: string;
  n_particelle: number;
  superficie_ha: number;
}

export interface DistrettoAggr {
  num_distretto: string;
  nome_distretto?: string;
  n_particelle: number;
  superficie_ha: number;
}

export interface GisSelectResult {
  n_particelle: number;
  superficie_ha: number;
  per_foglio: FoglioAggr[];
  per_distretto: DistrettoAggr[];
  particelle: ParticellaGisSummary[];
  truncated: boolean;
}

export interface ParticellaPopupData {
  id: string;
  cfm?: string;
  cod_comune_istat?: string;
  foglio?: string;
  particella?: string;
  subalterno?: string;
  superficie_mq?: number;
  num_distretto?: string;
  nome_distretto?: string;
  n_anomalie_aperte: number;
}
```

Installare tipi GeoJSON se non presenti:
```bash
npm install -D @types/geojson
```

---

## STEP F3 — Hook useGisSelection

**File**: `frontend/src/hooks/useGisSelection.ts`

```typescript
'use client';
import { useState, useCallback } from 'react';
import { GisSelectResult, GisFilters } from '@/types/gis';
import { useAuth } from '@/hooks/useAuth'; // adatta al hook auth esistente

interface UseGisSelectionReturn {
  result: GisSelectResult | null;
  isLoading: boolean;
  error: string | null;
  runSelection: (geometry: GeoJSON.Geometry, filters?: GisFilters) => Promise<void>;
  clearSelection: () => void;
}

export function useGisSelection(): UseGisSelectionReturn {
  const [result, setResult] = useState<GisSelectResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { token } = useAuth(); // adatta al sistema auth esistente

  const runSelection = useCallback(async (
    geometry: GeoJSON.Geometry,
    filters?: GisFilters
  ) => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch('/api/catasto/gis/select', {  // o path diretto backend
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ geometry, filters })
      });

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || 'Errore selezione spaziale');
      }

      const data: GisSelectResult = await response.json();
      setResult(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Errore sconosciuto');
    } finally {
      setIsLoading(false);
    }
  }, [token]);

  const clearSelection = useCallback(() => {
    setResult(null);
    setError(null);
  }, []);

  return { result, isLoading, error, runSelection, clearSelection };
}
```

---

## STEP F4 — MapContainer.tsx

**File**: `frontend/src/components/catasto/gis/MapContainer.tsx`

Questo componente è importato con `dynamic(..., { ssr: false })` dalla pagina.

```typescript
'use client';
import { useEffect, useRef, useCallback } from 'react';
import maplibregl from 'maplibre-gl';
import MapboxDraw from '@mapbox/maplibre-gl-draw';
import { ParticellaPopupData, GisFilters } from '@/types/gis';

interface MapContainerProps {
  onGeometryDrawn: (geometry: GeoJSON.Geometry) => void;
  onSelectionCleared: () => void;
  selectedIds: string[];  // IDs da evidenziare sulla mappa
  filters: GisFilters;
}

// Centro Sardegna
const SARDINIA_CENTER: [number, number] = [8.85, 40.1];
const SARDINIA_ZOOM = 9;

export default function MapContainer({
  onGeometryDrawn,
  onSelectionCleared,
  selectedIds,
  filters
}: MapContainerProps) {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const drawRef = useRef<InstanceType<typeof MapboxDraw> | null>(null);
  const popupRef = useRef<maplibregl.Popup | null>(null);

  // Inizializzazione mappa
  useEffect(() => {
    if (!mapContainerRef.current || mapRef.current) return;

    const map = new maplibregl.Map({
      container: mapContainerRef.current,
      style: {
        version: 8,
        sources: {
          'osm': {
            type: 'raster',
            tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
            tileSize: 256,
            attribution: '© OpenStreetMap contributors'
          }
        },
        layers: [{
          id: 'osm-tiles',
          type: 'raster',
          source: 'osm',
          minzoom: 0,
          maxzoom: 19
        }]
      },
      center: SARDINIA_CENTER,
      zoom: SARDINIA_ZOOM,
    });

    // Controlli navigazione
    map.addControl(new maplibregl.NavigationControl(), 'top-right');
    map.addControl(new maplibregl.ScaleControl({ unit: 'metric' }), 'bottom-right');

    // MapLibre Draw
    const draw = new MapboxDraw({
      displayControlsDefault: false,  // usiamo toolbar custom
      styles: [
        // Stile poligono in disegno
        {
          id: 'gl-draw-polygon-fill',
          type: 'fill',
          filter: ['all', ['==', '$type', 'Polygon']],
          paint: { 'fill-color': '#F59E0B', 'fill-opacity': 0.2 }
        },
        {
          id: 'gl-draw-polygon-stroke',
          type: 'line',
          filter: ['all', ['==', '$type', 'Polygon']],
          paint: { 'line-color': '#F59E0B', 'line-width': 2 }
        }
      ]
    });
    map.addControl(draw as unknown as maplibregl.IControl, 'top-left');
    drawRef.current = draw;

    map.on('load', () => {
      // Sorgente tiles distretti
      map.addSource('distretti-source', {
        type: 'vector',
        tiles: [`${window.location.origin}/tiles/cat_distretti/{z}/{x}/{y}`],
        minzoom: 7,
        maxzoom: 16
      });

      // Layer fill distretti
      map.addLayer({
        id: 'distretti-fill',
        type: 'fill',
        source: 'distretti-source',
        'source-layer': 'cat_distretti',
        minzoom: 7,
        paint: {
          'fill-color': '#3B82F6',
          'fill-opacity': 0.15
        }
      });

      // Layer bordi distretti
      map.addLayer({
        id: 'distretti-outline',
        type: 'line',
        source: 'distretti-source',
        'source-layer': 'cat_distretti',
        minzoom: 7,
        paint: {
          'line-color': '#1D4ED8',
          'line-width': 1.5
        }
      });

      // Sorgente tiles particelle
      map.addSource('particelle-source', {
        type: 'vector',
        tiles: [`${window.location.origin}/tiles/cat_particelle_current/{z}/{x}/{y}`],
        minzoom: 13,
        maxzoom: 20
      });

      // Layer fill particelle
      map.addLayer({
        id: 'particelle-fill',
        type: 'fill',
        source: 'particelle-source',
        'source-layer': 'cat_particelle_current',
        minzoom: 13,
        paint: {
          'fill-color': [
            'case',
            ['==', ['get', 'ha_anomalie'], true], '#EF4444',
            '#6366F1'
          ],
          'fill-opacity': 0.4
        }
      });

      // Layer bordi particelle
      map.addLayer({
        id: 'particelle-outline',
        type: 'line',
        source: 'particelle-source',
        'source-layer': 'cat_particelle_current',
        minzoom: 14,
        paint: {
          'line-color': '#4338CA',
          'line-width': 0.5
        }
      });

      // Sorgente GeoJSON per selezione highlight (aggiornata dinamicamente)
      map.addSource('selection-source', {
        type: 'geojson',
        data: { type: 'FeatureCollection', features: [] }
      });

      map.addLayer({
        id: 'selection-fill',
        type: 'fill',
        source: 'selection-source',
        paint: {
          'fill-color': '#F59E0B',
          'fill-opacity': 0.7
        }
      });

      // Click su particelle → popup
      map.on('click', 'particelle-fill', async (e) => {
        if (!e.features?.[0]) return;
        const feature = e.features[0];
        const id = feature.properties?.id;
        if (!id) return;

        const coordinates = e.lngLat;

        // Chiudi popup precedente
        popupRef.current?.remove();

        // Fetch dati popup
        try {
          const res = await fetch(`/api/catasto/gis/particella/${id}/popup`, {
            headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
          });
          if (!res.ok) return;
          const data: ParticellaPopupData = await res.json();

          const popup = new maplibregl.Popup({ maxWidth: '300px' })
            .setLngLat(coordinates)
            .setHTML(buildPopupHtml(data))
            .addTo(map);
          popupRef.current = popup;
        } catch {
          // Silenzioso — popup non critico
        }
      });

      // Cursore pointer su hover particelle/distretti
      ['particelle-fill', 'distretti-fill'].forEach(layerId => {
        map.on('mouseenter', layerId, () => { map.getCanvas().style.cursor = 'pointer'; });
        map.on('mouseleave', layerId, () => { map.getCanvas().style.cursor = ''; });
      });
    });

    // Listener eventi Draw
    map.on('draw.create', (e) => {
      const geometry = e.features[0]?.geometry;
      if (geometry) onGeometryDrawn(geometry);
    });
    map.on('draw.update', (e) => {
      const geometry = e.features[0]?.geometry;
      if (geometry) onGeometryDrawn(geometry);
    });
    map.on('draw.delete', () => onSelectionCleared());

    mapRef.current = map;

    return () => {
      popupRef.current?.remove();
      map.remove();
      mapRef.current = null;
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Aggiornamento highlight selezione
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.isStyleLoaded()) return;

    // Non possiamo filtrare MVT per ID direttamente in modo efficiente.
    // Usiamo una sorgente GeoJSON separata per l'highlight (aggiornata con dati da API).
    // Per ora, il feedback visivo viene dal pannello risultati.
    // TODO: Se necessario, fetch geometrie selezionate e aggiorna 'selection-source'.
  }, [selectedIds]);

  return (
    <div
      ref={mapContainerRef}
      className="w-full h-full rounded-lg overflow-hidden"
      style={{ minHeight: '500px' }}
    />
  );
}

// Helper per costruire HTML popup (no React per semplicità nel contesto MapLibre)
function buildPopupHtml(data: ParticellaPopupData): string {
  const superficie = data.superficie_mq
    ? `${data.superficie_mq.toLocaleString('it-IT')} mq`
    : '—';
  const anomalieBadge = data.n_anomalie_aperte > 0
    ? `<span style="color:#EF4444;font-weight:bold">● ${data.n_anomalie_aperte} anomalie</span>`
    : '<span style="color:#10B981">✓ Nessuna anomalia</span>';

  return `
    <div style="font-family:sans-serif;font-size:13px;line-height:1.5">
      <div style="font-weight:bold;margin-bottom:4px">${data.cfm || 'N/D'}</div>
      <div>Comune: ${data.cod_comune_istat || '—'}</div>
      <div>Foglio: ${data.foglio || '—'} — Part.: ${data.particella || '—'}${data.subalterno ? ` Sub: ${data.subalterno}` : ''}</div>
      <div>Superficie: ${superficie}</div>
      <div>Distretto: ${data.num_distretto || '—'}${data.nome_distretto ? ` (${data.nome_distretto})` : ''}</div>
      <div style="margin-top:4px">${anomalieBadge}</div>
      <div style="margin-top:8px">
        <a href="/catasto/particelle/${data.id}"
           style="color:#6366F1;text-decoration:none;font-weight:bold"
           target="_blank">
          Apri scheda completa →
        </a>
      </div>
    </div>
  `;
}
```

---

## STEP F5 — DrawingTools.tsx

**File**: `frontend/src/components/catasto/gis/DrawingTools.tsx`

```typescript
'use client';

interface DrawingToolsProps {
  onDrawPolygon: () => void;
  onClearDrawing: () => void;
  isLoading: boolean;
  hasSelection: boolean;
  n_particelle?: number;
}

export default function DrawingTools({
  onDrawPolygon,
  onClearDrawing,
  isLoading,
  hasSelection,
  n_particelle
}: DrawingToolsProps) {
  return (
    <div className="flex items-center gap-2 p-2 bg-white border rounded-lg shadow-sm">
      <button
        onClick={onDrawPolygon}
        className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium
                   bg-indigo-50 text-indigo-700 rounded hover:bg-indigo-100
                   border border-indigo-200 transition-colors"
      >
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
        </svg>
        Disegna area
      </button>

      {hasSelection && (
        <button
          onClick={onClearDrawing}
          className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium
                     bg-red-50 text-red-700 rounded hover:bg-red-100
                     border border-red-200 transition-colors"
        >
          ✕ Cancella selezione
        </button>
      )}

      <div className="ml-2 text-sm text-gray-600">
        {isLoading && (
          <span className="flex items-center gap-1">
            <span className="w-3 h-3 border border-indigo-400 border-t-transparent rounded-full animate-spin" />
            Analisi in corso...
          </span>
        )}
        {!isLoading && hasSelection && n_particelle !== undefined && (
          <span className="font-medium text-indigo-700">
            {n_particelle.toLocaleString('it-IT')} particelle selezionate
          </span>
        )}
        {!isLoading && !hasSelection && (
          <span className="text-gray-400">Disegna un'area sulla mappa</span>
        )}
      </div>
    </div>
  );
}
```

---

## STEP F6 — AnalysisPanel.tsx

**File**: `frontend/src/components/catasto/gis/AnalysisPanel.tsx`

```typescript
'use client';
import { GisSelectResult } from '@/types/gis';

interface AnalysisPanelProps {
  result: GisSelectResult | null;
  isLoading: boolean;
  onExport: (format: 'geojson' | 'csv') => void;
}

export default function AnalysisPanel({ result, isLoading, onExport }: AnalysisPanelProps) {
  if (isLoading) {
    return (
      <div className="p-4 space-y-3 animate-pulse">
        <div className="h-4 bg-gray-200 rounded w-3/4" />
        <div className="h-8 bg-gray-200 rounded" />
        <div className="h-4 bg-gray-200 rounded w-1/2" />
        <div className="h-24 bg-gray-200 rounded" />
      </div>
    );
  }

  if (!result) {
    return (
      <div className="p-4 text-center text-gray-400 text-sm">
        <div className="text-2xl mb-2">🗺️</div>
        <div>Disegna un'area sulla mappa per avviare l'analisi</div>
      </div>
    );
  }

  return (
    <div className="p-4 space-y-4 overflow-y-auto">
      {/* KPI principali */}
      <div>
        <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
          Selezione attiva
        </h3>
        <div className="grid grid-cols-2 gap-2">
          <div className="bg-indigo-50 rounded-lg p-3">
            <div className="text-xl font-bold text-indigo-700">
              {result.n_particelle.toLocaleString('it-IT')}
            </div>
            <div className="text-xs text-indigo-500">Particelle</div>
          </div>
          <div className="bg-green-50 rounded-lg p-3">
            <div className="text-xl font-bold text-green-700">
              {result.superficie_ha.toLocaleString('it-IT', {
                minimumFractionDigits: 1,
                maximumFractionDigits: 1
              })}
            </div>
            <div className="text-xs text-green-500">Ettari totali</div>
          </div>
        </div>
        {result.truncated && (
          <div className="mt-1 text-xs text-amber-600 bg-amber-50 rounded px-2 py-1">
            ⚠️ Preview limitata a 200 particelle. Tutti i calcoli includono l'area completa.
          </div>
        )}
      </div>

      {/* Per foglio */}
      {result.per_foglio.length > 0 && (
        <div>
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
            Per foglio mappale
          </h3>
          <div className="text-xs overflow-hidden rounded border border-gray-100">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="text-left px-2 py-1 font-medium text-gray-600">Foglio</th>
                  <th className="text-right px-2 py-1 font-medium text-gray-600">N.</th>
                  <th className="text-right px-2 py-1 font-medium text-gray-600">Ha</th>
                </tr>
              </thead>
              <tbody>
                {result.per_foglio.slice(0, 8).map(f => (
                  <tr key={f.foglio} className="border-t border-gray-50">
                    <td className="px-2 py-1 font-mono">{f.foglio}</td>
                    <td className="px-2 py-1 text-right">{f.n_particelle.toLocaleString('it-IT')}</td>
                    <td className="px-2 py-1 text-right">{f.superficie_ha.toFixed(1)}</td>
                  </tr>
                ))}
                {result.per_foglio.length > 8 && (
                  <tr className="border-t border-gray-50 bg-gray-50">
                    <td colSpan={3} className="px-2 py-1 text-gray-400 text-center">
                      e altri {result.per_foglio.length - 8} fogli...
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Per distretto */}
      {result.per_distretto.length > 0 && (
        <div>
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
            Per distretto
          </h3>
          <div className="text-xs space-y-1">
            {result.per_distretto.map(d => (
              <div key={d.num_distretto}
                   className="flex justify-between items-center bg-gray-50 rounded px-2 py-1.5">
                <div>
                  <span className="font-mono font-medium">{d.num_distretto}</span>
                  {d.nome_distretto && (
                    <span className="text-gray-400 ml-1">— {d.nome_distretto}</span>
                  )}
                </div>
                <div className="text-right text-gray-600">
                  {d.n_particelle.toLocaleString('it-IT')} part. · {d.superficie_ha.toFixed(1)} ha
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Export */}
      <div className="pt-2 border-t border-gray-100">
        <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
          Esporta selezione
        </h3>
        <div className="flex gap-2">
          <button
            onClick={() => onExport('csv')}
            className="flex-1 px-3 py-1.5 text-xs font-medium bg-white border border-gray-200
                       rounded hover:bg-gray-50 transition-colors text-gray-700"
          >
            ↓ CSV
          </button>
          <button
            onClick={() => onExport('geojson')}
            className="flex-1 px-3 py-1.5 text-xs font-medium bg-white border border-gray-200
                       rounded hover:bg-gray-50 transition-colors text-gray-700"
          >
            ↓ GeoJSON
          </button>
        </div>
      </div>
    </div>
  );
}
```

---

## STEP F7 — SelectionPanel.tsx

**File**: `frontend/src/components/catasto/gis/SelectionPanel.tsx`

```typescript
'use client';
import Link from 'next/link';
import { ParticellaGisSummary } from '@/types/gis';

interface SelectionPanelProps {
  particelle: ParticellaGisSummary[];
  truncated: boolean;
  n_totale: number;
}

export default function SelectionPanel({ particelle, truncated, n_totale }: SelectionPanelProps) {
  if (particelle.length === 0) return null;

  return (
    <div className="border-t border-gray-100 overflow-y-auto max-h-64">
      <div className="px-4 py-2 bg-gray-50 text-xs font-semibold text-gray-500 uppercase tracking-wider flex justify-between">
        <span>Particelle</span>
        <span>{Math.min(particelle.length, 200)} / {n_totale.toLocaleString('it-IT')}</span>
      </div>
      <div className="divide-y divide-gray-50">
        {particelle.map(p => (
          <div key={p.id} className="px-4 py-2 hover:bg-gray-50 flex items-center justify-between">
            <div className="text-xs">
              <div className="font-mono font-medium text-gray-800">
                {p.cfm || `${p.foglio}/${p.particella}`}
              </div>
              <div className="text-gray-400">
                {p.superficie_mq?.toLocaleString('it-IT')} mq · {p.num_distretto || '—'}
              </div>
            </div>
            <div className="flex items-center gap-2">
              {p.ha_anomalie && (
                <span className="w-2 h-2 bg-red-400 rounded-full" title="Anomalie aperte" />
              )}
              <Link
                href={`/catasto/particelle/${p.id}`}
                className="text-xs text-indigo-600 hover:text-indigo-800"
                target="_blank"
              >
                →
              </Link>
            </div>
          </div>
        ))}
      </div>
      {truncated && (
        <div className="px-4 py-2 text-xs text-amber-600 bg-amber-50 text-center">
          Showing 200 of {n_totale.toLocaleString('it-IT')} — usa export per lista completa
        </div>
      )}
    </div>
  );
}
```

---

## STEP F8 — Pagina /catasto/mappa

**File**: `frontend/src/app/catasto/mappa/page.tsx`

```typescript
'use client';
import dynamic from 'next/dynamic';
import { useState, useCallback, useRef } from 'react';
import { GisSelectResult, GisFilters } from '@/types/gis';
import { useGisSelection } from '@/hooks/useGisSelection';
import DrawingTools from '@/components/catasto/gis/DrawingTools';
import AnalysisPanel from '@/components/catasto/gis/AnalysisPanel';
import SelectionPanel from '@/components/catasto/gis/SelectionPanel';

// Import dinamico — obbligatorio per MapLibre GL con Next.js (no SSR)
const MapContainer = dynamic(
  () => import('@/components/catasto/gis/MapContainer'),
  {
    ssr: false,
    loading: () => (
      <div className="w-full h-full bg-gray-100 animate-pulse flex items-center justify-center">
        <span className="text-gray-400 text-sm">Caricamento mappa...</span>
      </div>
    )
  }
);

export default function CatastoMappaPage() {
  const { result, isLoading, error, runSelection, clearSelection } = useGisSelection();
  const [activeFilters] = useState<GisFilters>({});
  const [hasDrawing, setHasDrawing] = useState(false);
  const drawRef = useRef<{ startDraw: () => void; clearDraw: () => void } | null>(null);

  const handleGeometryDrawn = useCallback(async (geometry: GeoJSON.Geometry) => {
    setHasDrawing(true);
    await runSelection(geometry, activeFilters);
  }, [runSelection, activeFilters]);

  const handleClearSelection = useCallback(() => {
    setHasDrawing(false);
    clearSelection();
  }, [clearSelection]);

  const handleExport = useCallback(async (format: 'geojson' | 'csv') => {
    if (!result || result.particelle.length === 0) return;
    const ids = result.particelle.map(p => p.id).join(',');
    const url = `/api/catasto/gis/export?ids=${ids}&format=${format}`;

    try {
      const response = await fetch(url, {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
      });
      if (!response.ok) throw new Error('Export fallito');
      const blob = await response.blob();
      const downloadUrl = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = downloadUrl;
      a.download = `selezione_catasto.${format === 'geojson' ? 'geojson' : 'csv'}`;
      a.click();
      URL.revokeObjectURL(downloadUrl);
    } catch (e) {
      console.error('Export error:', e);
    }
  }, [result]);

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b bg-white">
        <div>
          <h1 className="text-lg font-semibold text-gray-900">Catasto GIS</h1>
          <p className="text-xs text-gray-500">Analisi spaziale particelle catastali</p>
        </div>
        <DrawingTools
          onDrawPolygon={() => {/* Trigger draw mode via ref o context */}}
          onClearDrawing={handleClearSelection}
          isLoading={isLoading}
          hasSelection={hasDrawing}
          n_particelle={result?.n_particelle}
        />
      </div>

      {/* Errore */}
      {error && (
        <div className="mx-4 mt-2 px-3 py-2 bg-red-50 border border-red-200 rounded text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Body: mappa + pannello risultati */}
      <div className="flex flex-1 overflow-hidden">
        {/* Mappa */}
        <div className="flex-1 relative">
          <MapContainer
            onGeometryDrawn={handleGeometryDrawn}
            onSelectionCleared={handleClearSelection}
            selectedIds={result?.particelle.map(p => p.id) ?? []}
            filters={activeFilters}
          />
        </div>

        {/* Pannello risultati */}
        <div className="w-80 border-l bg-white flex flex-col overflow-hidden">
          <AnalysisPanel
            result={result}
            isLoading={isLoading}
            onExport={handleExport}
          />
          {result && (
            <SelectionPanel
              particelle={result.particelle}
              truncated={result.truncated}
              n_totale={result.n_particelle}
            />
          )}
        </div>
      </div>
    </div>
  );
}
```

---

## STEP F9 — Aggiungere link mappa nella sidebar catasto

Localizza il file di navigazione/sidebar del modulo catasto (es. `frontend/src/app/catasto/layout.tsx` o il componente sidebar catasto) e aggiungi:

```typescript
{
  href: '/catasto/mappa',
  label: 'Mappa GIS',
  icon: <MapIcon />  // usa l'icona appropriata dal set icons già usato
}
```

**Acceptance globale**:
- `/catasto/mappa` accessibile da sidebar catasto
- Mappa carica senza errori console
- Layer distretti visibile a zoom 9 (se DB popolato)
- Layer particelle visibile a zoom 14 (se DB popolato)
- Click "Disegna area" → cursore diventa croce
- Dopo disegno → spinner → risultati nel pannello
- Export CSV/GeoJSON → download file
- Popup particella → link funzionante verso scheda
- Mobile: layout responsivo (mappa full-width, pannello collassato)

---

## Note critiche

**MapLibre Draw e `as unknown as`**: Il cast `draw as unknown as maplibregl.IControl` è necessario perché i tipi TS di MapboxDraw non sono allineati con MapLibre. È pattern consolidato.

**`localStorage.getItem('token')`**: Adatta al meccanismo di recupero token esistente nel progetto (potrebbe essere cookie httpOnly, Zustand store, React context ecc.). Cerca come le altre pagine catasto recuperano il token JWT.

**`/api/catasto/gis/...` vs `/catasto/gis/...`**: Adatta il base URL al pattern usato dal resto del frontend. Se il frontend proxya via `next.config.js`, usa `/api/...`. Se chiama direttamente il backend, usa l'URL del backend.

**Draw trigger esterno**: Il pulsante "Disegna area" in `DrawingTools` deve triggerare `draw.changeMode('draw_polygon')` sul ref MapLibre Draw. Usa `useImperativeHandle` su `MapContainer` o uno shared ref per esporre il metodo. Implementa il pattern che più si allinea con quello esistente nel progetto.
