"use client";

import { useEffect, useMemo, useState } from "react";

import type { CatAnagraficaMatch, CatParticellaDetail, CatUtenzaIrrigua, GeoJSONFeature } from "@/types/catasto";
import { getStoredAccessToken } from "@/lib/auth";
import { catastoGetParticella, catastoGetParticellaGeojson, catastoGetParticellaUtenze } from "@/lib/api/catasto";

function formatHaFromMq(value: string | number | null | undefined): string {
  if (value == null) return "—";
  const mq = typeof value === "number" ? value : Number(value);
  const ha = (Number.isFinite(mq) ? mq : 0) / 10_000;
  return `${new Intl.NumberFormat("it-IT", { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(ha)} ha`;
}

function formatRef(m: Pick<CatAnagraficaMatch, "foglio" | "particella" | "subalterno">): string {
  return `Fg.${m.foglio} Part.${m.particella}${m.subalterno ? ` Sub.${m.subalterno}` : ""}`;
}

function extractLonLat(feature: GeoJSONFeature | null): { lon: number; lat: number } | null {
  if (!feature || !feature.properties) return null;
  const centroid = (feature.properties["centroid"] as unknown) ?? null;
  if (!centroid || typeof centroid !== "object") return null;
  if (!("type" in centroid) || !("coordinates" in centroid)) return null;
  const coords = (centroid as { coordinates?: unknown }).coordinates;
  if (!Array.isArray(coords) || coords.length < 2) return null;
  const lon = Number(coords[0]);
  const lat = Number(coords[1]);
  if (!Number.isFinite(lon) || !Number.isFinite(lat)) return null;
  return { lon, lat };
}

export function ParticellaDetailDialog({
  open,
  match,
  onClose,
}: {
  open: boolean;
  match: CatAnagraficaMatch | null;
  onClose: () => void;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [particella, setParticella] = useState<CatParticellaDetail | null>(null);
  const [utenze, setUtenze] = useState<CatUtenzaIrrigua[]>([]);
  const [geojson, setGeojson] = useState<GeoJSONFeature | null>(null);

  const reference = useMemo(() => (match ? formatRef(match) : "Particella"), [match]);
  const centroid = useMemo(() => extractLonLat(geojson), [geojson]);

  useEffect(() => {
    if (!open || !match) return;
    const currentMatch = match;

    async function load(): Promise<void> {
      const token = getStoredAccessToken();
      if (!token) return;

      setBusy(true);
      setError(null);
      try {
        const [p, u, g] = await Promise.all([
          catastoGetParticella(token, currentMatch.particella_id),
          catastoGetParticellaUtenze(token, currentMatch.particella_id),
          catastoGetParticellaGeojson(token, currentMatch.particella_id),
        ]);
        setParticella(p);
        setUtenze(u);
        setGeojson(g);
      } catch (e) {
        setParticella(null);
        setUtenze([]);
        setGeojson(null);
        setError(e instanceof Error ? e.message : "Errore caricamento dettagli particella");
      } finally {
        setBusy(false);
      }
    }

    void load();
  }, [open, match]);

  if (!open || !match) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-gray-900/45 px-4"
      role="dialog"
      aria-modal="true"
      aria-label={`Dettaglio ${reference}`}
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="w-full max-w-3xl rounded-2xl border border-gray-200 bg-white p-6 shadow-2xl">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="text-sm font-semibold text-gray-900">{reference}</p>
            <p className="mt-1 text-sm text-gray-500">
              Comune: <span className="font-medium text-gray-800">{match.comune ?? "—"}</span>{" "}
              <span className="text-gray-400">·</span> Codice Capacitas: <span className="font-medium text-gray-800">{match.cod_comune_capacitas ?? "—"}</span>{" "}
              <span className="text-gray-400">·</span> Distretto: <span className="font-medium text-gray-800">{match.num_distretto ?? "—"}</span>
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button type="button" className="btn-secondary" onClick={onClose}>
              Chiudi
            </button>
          </div>
        </div>

        {error ? (
          <div className="mt-4 rounded-xl border border-red-100 bg-red-50 p-4 text-sm text-red-800">
            <p className="font-medium">Errore</p>
            <p className="mt-1">{error}</p>
          </div>
        ) : null}

        <div className="mt-4 grid gap-3 md:grid-cols-3">
          <div className="rounded-xl border border-gray-100 bg-white p-3">
            <p className="text-[10px] font-medium uppercase tracking-widest text-gray-400">Catasto</p>
            <div className="mt-2 space-y-1 text-sm text-gray-700">
              <p>
                <span className="text-gray-500">Sup. catastale:</span> {formatHaFromMq(match.superficie_mq)}
              </p>
              <p>
                <span className="text-gray-500">Sup. grafica:</span> {formatHaFromMq(particella?.superficie_grafica_mq ?? match.superficie_grafica_mq)}
              </p>
              <p>
                <span className="text-gray-500">Fonte:</span> {particella?.source_type ?? "—"}
              </p>
              <p>
                <span className="text-gray-500">Fuori distretto:</span> {particella ? (particella.fuori_distretto ? "Sì" : "No") : "—"}
              </p>
            </div>
          </div>

          <div className="rounded-xl border border-gray-100 bg-white p-3">
            <p className="text-[10px] font-medium uppercase tracking-widest text-gray-400">Proprietà / possesso</p>
            <div className="mt-2 space-y-2 text-sm text-gray-700">
              {(match.intestatari ?? []).length === 0 ? (
                <p className="text-gray-500">Nessun intestatario disponibile (non presente in `cat_intestatari`).</p>
              ) : (
                <ul className="list-disc pl-5">
                  {(match.intestatari ?? []).slice(0, 10).map((i) => (
                    <li key={i.id}>
                      <span className="font-medium">
                        {(i.denominazione ?? i.ragione_sociale ?? [i.cognome, i.nome].filter(Boolean).join(" ")) || "—"}
                      </span>{" "}
                      <span className="text-gray-500">({i.codice_fiscale})</span>
                    </li>
                  ))}
                </ul>
              )}
              <p className="text-xs text-gray-500">
                Nota: il “titolo di possesso” puntuale non è ancora esposto come dato strutturato; qui mostriamo gli intestatari rilevati da CF presenti nelle utenze.
              </p>
            </div>
          </div>

          <div className="rounded-xl border border-gray-100 bg-white p-3">
            <p className="text-[10px] font-medium uppercase tracking-widest text-gray-400">Geometria / mappa</p>
            <div className="mt-2 space-y-2 text-sm text-gray-700">
              <p>
                <span className="text-gray-500">Tipo:</span>{" "}
                <span className="font-medium text-gray-900">
                  {busy ? "Caricamento…" : (geojson?.properties?.["geometry_type"] as string | undefined) ?? "—"}
                </span>
              </p>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  className="btn-secondary !px-3 !py-1.5 text-xs"
                  disabled={!geojson}
                  onClick={() => {
                    if (!geojson) return;
                    const blob = new Blob([JSON.stringify(geojson, null, 2)], { type: "application/geo+json" });
                    const url = URL.createObjectURL(blob);
                    window.open(url, "_blank", "noopener,noreferrer");
                    setTimeout(() => URL.revokeObjectURL(url), 30_000);
                  }}
                >
                  Apri GeoJSON
                </button>
                <a
                  className="btn-secondary !px-3 !py-1.5 text-xs"
                  href={centroid ? `https://www.openstreetmap.org/?mlat=${centroid.lat}&mlon=${centroid.lon}#map=18/${centroid.lat}/${centroid.lon}` : "#"}
                  target="_blank"
                  rel="noreferrer"
                  aria-disabled={!centroid}
                  onClick={(e) => {
                    if (!centroid) e.preventDefault();
                  }}
                >
                  Visualizza su mappa
                </a>
              </div>
              {!centroid && !busy ? <p className="text-xs text-gray-500">Centroid non disponibile (geometria assente o non calcolabile).</p> : null}
            </div>
          </div>
        </div>

        <div className="mt-4 rounded-xl border border-gray-100 bg-gray-50 p-3 text-sm text-gray-700">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="font-medium text-gray-900">Utenze collegate</p>
              <p className="mt-1 text-sm text-gray-500">Elenco sintetico (ultime 10 per anno campagna).</p>
            </div>
            <p className="text-sm text-gray-500">{busy ? "Caricamento…" : `${utenze.length} righe`}</p>
          </div>
          <div className="mt-3 overflow-auto">
            {busy ? (
              <p className="text-sm text-gray-500">Caricamento…</p>
            ) : utenze.length === 0 ? (
              <p className="text-sm text-gray-500">Nessuna utenza trovata per la particella.</p>
            ) : (
              <table className="w-full border-separate border-spacing-y-1">
                <thead>
                  <tr className="text-left text-[10px] font-medium uppercase tracking-widest text-gray-400">
                    <th className="pr-4">Anno</th>
                    <th className="pr-4">CCO</th>
                    <th className="pr-4">CF</th>
                    <th className="pr-4">Denominazione</th>
                    <th className="pr-4">Sup. irrigabile</th>
                  </tr>
                </thead>
                <tbody>
                  {utenze.slice(0, 10).map((u) => (
                    <tr key={u.id} className="rounded-lg bg-white">
                      <td className="py-1 pr-4 text-sm text-gray-700">{u.anno_campagna ?? "—"}</td>
                      <td className="py-1 pr-4 text-sm text-gray-700">{u.cco ?? "—"}</td>
                      <td className="py-1 pr-4 text-sm text-gray-700">{u.codice_fiscale ?? "—"}</td>
                      <td className="py-1 pr-4 text-sm text-gray-700">{u.denominazione ?? "—"}</td>
                      <td className="py-1 pr-4 text-sm text-gray-700">{formatHaFromMq(u.sup_irrigabile_mq)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        <div className="mt-4 flex flex-wrap items-center justify-end gap-2">
          <a className="btn-secondary" href={`/catasto/particelle/${match.particella_id}`}>
            Apri scheda completa
          </a>
        </div>
      </div>
    </div>
  );
}
