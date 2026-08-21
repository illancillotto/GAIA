"use client";

import Link from "next/link";
import { Suspense } from "react";
import { useSearchParams } from "next/navigation";

import { CatastoPage } from "@/components/catasto/catasto-page";
import CoordinateMap from "@/components/catasto/gis/MapContainer";
import { buildCatastoGisCoordinateSearchResponse } from "@/lib/catasto-gis-coordinate-search";
import type { GisMapOverlayLayer } from "@/types/gis";

export function buildCoordinateOverlay(
  label: string,
  geojson: GeoJSON.FeatureCollection,
): { label: string; geojson: GeoJSON.FeatureCollection; layer: GisMapOverlayLayer } {
  return {
    label,
    geojson,
    layer: {
      layer_key: "coordinate-search",
      saved_selection_id: null,
      name: `Waypoint ${label}`,
      color: "#0F766E",
      outlineColor: "#F97316",
      opacity: 0.86,
      outlineOpacity: 1,
      outlineWidth: 3,
      showFill: true,
      showCentroids: true,
      visible: true,
      source_filename: null,
      geojson,
    },
  };
}

function CoordinateWorkspace() {
  const query = useSearchParams().get("coordinate") ?? "";
  const search = buildCatastoGisCoordinateSearchResponse(query);

  if (!search) {
    return (
      <CatastoPage title="Coordinate GIS" description="Apri un punto catastale partendo da latitudine e longitudine." breadcrumb="Catasto" requiredModule="catasto">
        <section className="page-body">
          <div className="rounded-[28px] border border-amber-200 bg-gradient-to-br from-amber-50 to-white p-8 shadow-sm">
            <p className="section-kicker">Waypoint non disponibile</p>
            <h2 className="mt-2 text-2xl font-semibold text-slate-950">Coordinate mancanti o non valide</h2>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-600">Inserisci nuovamente latitudine e longitudine dalla ricerca globale di GAIA.</p>
            <Link className="btn-secondary mt-6 inline-flex" href="/catasto/gis">Apri il GIS completo</Link>
          </div>
        </section>
      </CatastoPage>
    );
  }

  const overlay = buildCoordinateOverlay(search.label, search.geojson);
  return (
    <CatastoPage title="Coordinate GIS" description="Waypoint cartografico centrato sulle coordinate cercate." breadcrumb="Catasto" requiredModule="catasto">
      <section className="page-body space-y-5">
        <header className="overflow-hidden rounded-[28px] border border-teal-100 bg-[radial-gradient(circle_at_top_right,_#fed7aa,_transparent_38%),linear-gradient(135deg,_#ecfdf5,_#ffffff_58%)] p-6 shadow-sm">
          <p className="section-kicker">Waypoint Catasto</p>
          <div className="mt-2 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
            <div>
              <h2 className="font-mono text-2xl font-semibold tracking-tight text-slate-950">{overlay.label}</h2>
              <p className="mt-2 text-sm text-slate-600">Il rombo evidenzia un raggio di circa 90 metri attorno al punto esatto.</p>
            </div>
            <Link className="btn-secondary inline-flex" href="/catasto/gis">Apri strumenti GIS completi</Link>
          </div>
        </header>
        <div className="rounded-[30px] border border-slate-200 bg-white p-2 shadow-xl shadow-slate-200/60">
          <CoordinateMap
            token={null}
            onGeometryDrawn={() => undefined}
            onSelectionCleared={() => undefined}
            selectedIds={[]}
            filters={{}}
            mapLayers={{ showDistretti: true, showDistrettiFill: false, showParticelleFill: true, showParticelleTiles: true }}
            overlayLayers={[overlay.layer]}
            focusGeojson={overlay.geojson}
            focusSignal={1}
            focusOptions={{ maxZoom: 15, padding: 48, duration: 700 }}
            drawSignal={0}
            clearSignal={0}
            basemap="satellite"
            className="min-h-[68vh]"
          />
        </div>
      </section>
    </CatastoPage>
  );
}

export default function CatastoGisCoordinatePage() {
  return (
    <Suspense fallback={<div className="min-h-[560px] animate-pulse bg-slate-100" aria-label="Caricamento coordinate" />}>
      <CoordinateWorkspace />
    </Suspense>
  );
}
