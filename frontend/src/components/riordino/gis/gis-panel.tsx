"use client";

import dynamic from "next/dynamic";
import { useEffect, useMemo, useState } from "react";

import { ParticellaGisDialog } from "@/components/catasto/gis/ParticellaGisDialog";
import { EmptyState } from "@/components/ui/empty-state";
import { GridIcon } from "@/components/ui/icons";
import { formatRiordinoDate, formatRiordinoLabel } from "@/components/riordino/shared/format";
import { catastoGetParticellaGeojson } from "@/lib/api/catasto";
import { createRiordinoGisLink, updateRiordinoGisLink } from "@/lib/riordino-api";
import type { CatAnagraficaMatch, GeoJSONFeature } from "@/types/catasto";
import type { GisMapOverlayLayer } from "@/types/gis";
import type { RiordinoGisLink, RiordinoParcelLink } from "@/types/riordino";

const MapContainer = dynamic(() => import("@/components/catasto/gis/MapContainer"), {
  ssr: false,
  loading: () => (
    <div className="flex h-[420px] items-center justify-center rounded-2xl bg-gray-100 text-sm text-gray-500">
      Caricamento GIS...
    </div>
  ),
});

type RiordinoGisPanelProps = {
  token: string;
  practiceId: string;
  links: RiordinoGisLink[];
  parcels: RiordinoParcelLink[];
  onUpdated: () => Promise<void>;
};

const SYNC_STATUSES = ["manual", "pending", "synced"];

function extractLonLat(feature: GeoJSONFeature | null): { lon: number; lat: number } | null {
  const centroid = feature?.properties?.["centroid"];
  if (!centroid || typeof centroid !== "object" || !("coordinates" in centroid)) return null;
  const coords = (centroid as { coordinates?: unknown }).coordinates;
  if (!Array.isArray(coords) || coords.length < 2) return null;
  const lon = Number(coords[0]);
  const lat = Number(coords[1]);
  if (!Number.isFinite(lon) || !Number.isFinite(lat)) return null;
  return { lon, lat };
}

function buildParcelMatch(parcel: RiordinoParcelLink): CatAnagraficaMatch | null {
  if (!parcel.cat_particella_id) return null;
  return {
    particella_id: parcel.cat_particella_id,
    unit_id: null,
    comune_id: null,
    comune: parcel.cat_particella_nome_comune,
    cod_comune_capacitas: null,
    codice_catastale: null,
    foglio: parcel.foglio,
    particella: parcel.particella,
    subalterno: parcel.subalterno,
    num_distretto: parcel.cat_particella_num_distretto,
    nome_distretto: null,
    superficie_mq: null,
    superficie_grafica_mq: null,
    utenza_latest: null,
    cert_com: null,
    cert_pvc: null,
    cert_fra: null,
    cert_ccs: null,
    stato_ruolo: null,
    stato_cnc: null,
    intestatari: [],
    anomalie_count: 0,
    anomalie_top: [],
    note: null,
  };
}

function buildFeatureCollection(entries: Array<{ parcel: RiordinoParcelLink; geojson: GeoJSONFeature }>): GeoJSON.FeatureCollection | null {
  const features = entries
    .filter((entry) => entry.geojson.geometry)
    .map((entry) => ({
      type: "Feature" as const,
      geometry: entry.geojson.geometry as GeoJSON.Geometry,
      properties: {
        ...(entry.geojson.properties ?? {}),
        id: entry.parcel.cat_particella_id,
        riordino_parcel_id: entry.parcel.id,
      },
    }));

  return features.length > 0 ? { type: "FeatureCollection", features } : null;
}

export function RiordinoGisPanel({ token, practiceId, links, parcels, onUpdated }: RiordinoGisPanelProps) {
  const [layerName, setLayerName] = useState("");
  const [featureId, setFeatureId] = useState("");
  const [geometryRef, setGeometryRef] = useState("");
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [syncStatusById, setSyncStatusById] = useState<Record<string, string>>({});
  const [parcelGeojson, setParcelGeojson] = useState<Record<string, GeoJSONFeature>>({});
  const [parcelGeojsonError, setParcelGeojsonError] = useState<string | null>(null);
  const [selectedParcel, setSelectedParcel] = useState<RiordinoParcelLink | null>(null);

  const resolvedParcels = useMemo(
    () => parcels.filter((parcel) => parcel.cat_particella_id && parcel.cat_particella_has_geometry),
    [parcels],
  );

  useEffect(() => {
    let cancelled = false;
    async function loadParcelGeojson(): Promise<void> {
      if (resolvedParcels.length === 0) {
        setParcelGeojson({});
        setParcelGeojsonError(null);
        return;
      }

      setParcelGeojsonError(null);
      const entries = await Promise.all(
        resolvedParcels.map(async (parcel) => {
          if (!parcel.cat_particella_id) return null;
          try {
            const geojson = await catastoGetParticellaGeojson(token, parcel.cat_particella_id);
            return [parcel.cat_particella_id, geojson] as const;
          } catch {
            return null;
          }
        }),
      );
      if (cancelled) return;
      const next = Object.fromEntries(entries.filter((entry): entry is readonly [string, GeoJSONFeature] => entry !== null));
      setParcelGeojson(next);
      if (Object.keys(next).length < resolvedParcels.length) {
        setParcelGeojsonError("Alcune particelle risolte non hanno una geometria GIS caricabile.");
      }
    }

    void loadParcelGeojson();
    return () => {
      cancelled = true;
    };
  }, [resolvedParcels, token]);

  const mappedEntries = useMemo(
    () =>
      resolvedParcels.flatMap((parcel) => {
        const geojson = parcel.cat_particella_id ? parcelGeojson[parcel.cat_particella_id] : null;
        return geojson ? [{ parcel, geojson }] : [];
      }),
    [parcelGeojson, resolvedParcels],
  );
  const featureCollection = useMemo(() => buildFeatureCollection(mappedEntries), [mappedEntries]);
  const overlayLayers = useMemo<GisMapOverlayLayer[]>(
    () =>
      featureCollection
        ? [
            {
              layer_key: "riordino-lotto-particelle",
              name: "Particelle lotto riordino",
              color: "#D97706",
              outlineColor: "#92400E",
              opacity: 0.5,
              showFill: true,
              visible: true,
              geojson: featureCollection,
            },
          ]
        : [],
    [featureCollection],
  );
  const selectedIds = useMemo(() => resolvedParcels.flatMap((parcel) => (parcel.cat_particella_id ? [parcel.cat_particella_id] : [])), [resolvedParcels]);
  const selectedParcelMatch = selectedParcel ? buildParcelMatch(selectedParcel) : null;
  const selectedParcelGeojson = selectedParcel?.cat_particella_id ? parcelGeojson[selectedParcel.cat_particella_id] ?? null : null;
  const selectedParcelCentroid = extractLonLat(selectedParcelGeojson);

  async function handleCreate() {
    setBusy(true);
    setError(null);
    try {
      await createRiordinoGisLink(token, practiceId, {
        layer_name: layerName,
        feature_id: featureId || null,
        geometry_ref: geometryRef || null,
        notes: notes || null,
      });
      setLayerName("");
      setFeatureId("");
      setGeometryRef("");
      setNotes("");
      await onUpdated();
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "Impossibile creare il link GIS");
    } finally {
      setBusy(false);
    }
  }

  async function handleSyncUpdate(linkId: string) {
    setBusy(true);
    setError(null);
    try {
      await updateRiordinoGisLink(token, practiceId, linkId, {
        sync_status: syncStatusById[linkId] || "manual",
      });
      await onUpdated();
    } catch (currentError) {
      setError(currentError instanceof Error ? currentError.message : "Impossibile aggiornare il link GIS");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-4">
      <article className="panel-card">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="section-title">Particelle del lotto su GIS</p>
            <p className="mt-1 text-sm text-gray-500">
              Visualizzazione operativa delle particelle Riordino risolte sul Catasto corrente.
            </p>
          </div>
          <span className="rounded-full bg-amber-50 px-3 py-1 text-xs font-semibold text-amber-800">
            {mappedEntries.length}/{parcels.length} con geometria
          </span>
        </div>
        <div className="mt-4 grid gap-4 xl:grid-cols-[minmax(0,1.35fr)_minmax(320px,0.65fr)]">
          <div className="min-h-[420px] overflow-hidden rounded-2xl border border-gray-200 bg-[#101b17]">
            {featureCollection ? (
              <MapContainer
                token={token}
                onGeometryDrawn={() => undefined}
                onSelectionCleared={() => undefined}
                selectedIds={selectedIds}
                filters={{}}
                mapLayers={{
                  showDistretti: true,
                  showDistrettiFill: false,
                  showParticelleFill: false,
                  particelleOpacity: 0.2,
                  highlightSelected: true,
                }}
                overlayLayers={overlayLayers}
                focusGeojson={featureCollection}
                focusSignal={mappedEntries.length}
                focusOptions={{ maxZoom: 17, padding: 42, duration: 0 }}
                drawSignal={0}
                clearSignal={0}
                basemap="satellite"
                className="h-[420px] rounded-2xl border-0"
              />
            ) : (
              <div className="flex h-[420px] items-center justify-center px-6 text-center text-sm text-gray-300">
                Nessuna geometria disponibile. Aggiungi particelle collegate al Catasto corrente o verifica i riferimenti foglio/particella.
              </div>
            )}
          </div>
          <div className="max-h-[420px] overflow-auto rounded-2xl border border-gray-100 bg-gray-50 p-3">
            {parcels.length === 0 ? (
              <EmptyState icon={GridIcon} title="Nessuna particella" description="Le particelle collegate alla pratica compariranno qui." />
            ) : (
              <div className="space-y-2">
                {parcels.map((parcel) => {
                  const canOpenGis = Boolean(parcel.cat_particella_id && parcelGeojson[parcel.cat_particella_id]);
                  return (
                    <div key={parcel.id} className="rounded-xl border border-gray-200 bg-white px-3 py-3">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className="text-sm font-semibold text-gray-900">
                            Fg.{parcel.foglio} Part.{parcel.particella}
                            {parcel.subalterno ? ` Sub.${parcel.subalterno}` : ""}
                          </p>
                          <p className="mt-1 text-xs text-gray-500">
                            {parcel.cat_particella_nome_comune ?? "Comune n/d"} · Distretto {parcel.cat_particella_num_distretto ?? "—"}
                          </p>
                        </div>
                        <span className="rounded-full bg-gray-100 px-2 py-0.5 text-[11px] font-semibold text-gray-600">
                          {formatRiordinoLabel(parcel.cat_particella_match_status ?? "unmatched")}
                        </span>
                      </div>
                      {parcel.cat_particella_match_reason ? <p className="mt-2 text-xs text-amber-700">{formatRiordinoLabel(parcel.cat_particella_match_reason)}</p> : null}
                      <button
                        type="button"
                        className="btn-secondary mt-3 !px-3 !py-1.5 text-xs"
                        disabled={!canOpenGis}
                        onClick={() => setSelectedParcel(parcel)}
                      >
                        Apri in mappa
                      </button>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
        {parcelGeojsonError ? <p className="mt-3 text-sm text-amber-700">{parcelGeojsonError}</p> : null}
      </article>

      <div className="grid gap-4 xl:grid-cols-[1.4fr_0.9fr]">
      <article className="panel-card">
        <p className="section-title">GIS links</p>
        <div className="mt-4 space-y-3">
          {links.length === 0 ? (
            <EmptyState icon={GridIcon} title="Nessun link GIS" description="I riferimenti GIS manuali compariranno qui." />
          ) : (
            links.map((link) => (
              <div key={link.id} className="rounded-2xl border border-gray-100 px-4 py-4">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="text-sm font-semibold text-gray-900">{link.layer_name}</p>
                  <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600">{formatRiordinoLabel(link.sync_status)}</span>
                </div>
                <p className="mt-1 text-sm text-gray-600">
                  Feature {link.feature_id || "—"} • Geometry {link.geometry_ref || "—"} • Sync {formatRiordinoDate(link.last_synced_at, true)}
                </p>
                {link.notes ? <p className="mt-2 text-sm text-gray-600">{link.notes}</p> : null}
                <div className="mt-3 flex flex-wrap gap-2">
                  <select
                    className="form-control max-w-[220px]"
                    value={syncStatusById[link.id] ?? link.sync_status}
                    onChange={(event) => setSyncStatusById((current) => ({ ...current, [link.id]: event.target.value }))}
                  >
                    {SYNC_STATUSES.map((status) => (
                      <option key={status} value={status}>{formatRiordinoLabel(status)}</option>
                    ))}
                  </select>
                  <button className="btn-secondary" disabled={busy} onClick={() => void handleSyncUpdate(link.id)} type="button">
                    Aggiorna sync
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      </article>

      <article className="panel-card">
        <p className="section-title">Nuovo link GIS</p>
        <div className="mt-4 grid gap-3">
          <input className="form-control" placeholder="Layer name" value={layerName} onChange={(event) => setLayerName(event.target.value)} />
          <input className="form-control" placeholder="Feature ID" value={featureId} onChange={(event) => setFeatureId(event.target.value)} />
          <input className="form-control" placeholder="Geometry ref" value={geometryRef} onChange={(event) => setGeometryRef(event.target.value)} />
          <textarea className="form-control min-h-24" placeholder="Note" value={notes} onChange={(event) => setNotes(event.target.value)} />
          <button className="btn-primary" disabled={busy || !layerName.trim()} onClick={() => void handleCreate()} type="button">
            Crea link GIS
          </button>
          {error ? <p className="text-sm text-red-600">{error}</p> : null}
        </div>
      </article>
      </div>

      <ParticellaGisDialog
        open={Boolean(selectedParcel && selectedParcelMatch)}
        match={selectedParcelMatch}
        geojson={selectedParcelGeojson}
        centroid={selectedParcelCentroid}
        onClose={() => setSelectedParcel(null)}
      />
    </div>
  );
}
