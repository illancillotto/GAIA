"use client";

import { useEffect, useMemo, useState } from "react";

import type { CatAnagraficaMatch, CatParticellaConsorzio, CatParticellaDetail, CatUtenzaIrrigua, GeoJSONFeature } from "@/types/catasto";
import { getStoredAccessToken } from "@/lib/auth";
import { capacitasGetRptCertificatoLink, catastoGetParticella, catastoGetParticellaConsorzio, catastoGetParticellaGeojson, catastoGetParticellaUtenze } from "@/lib/api/catasto";

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

function renderResolutionLabel(mode: string | null | undefined): string {
  switch (mode) {
    case "swapped_arborea_terralba":
      return "Comune corretto da GAIA (Arborea/Terralba)";
    case "source_match":
      return "Comune sorgente confermato";
    case "resolved_from_particella":
      return "Comune risolto dalla particella GAIA";
    case "source_only":
      return "Solo sorgente Capacitas";
    default:
      return mode ?? "—";
  }
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
  const [consorzio, setConsorzio] = useState<CatParticellaConsorzio | null>(null);
  const [utenze, setUtenze] = useState<CatUtenzaIrrigua[]>([]);
  const [geojson, setGeojson] = useState<GeoJSONFeature | null>(null);
  const [capacitasLinkBusy, setCapacitasLinkBusy] = useState(false);
  const [capacitasLinkError, setCapacitasLinkError] = useState<string | null>(null);

  const reference = useMemo(() => (match ? formatRef(match) : "Particella"), [match]);
  const centroid = useMemo(() => extractLonLat(geojson), [geojson]);

  useEffect(() => {
    if (!open) return;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose, open]);

  useEffect(() => {
    if (!open || !match) return;
    const currentMatch = match;

    async function load(): Promise<void> {
      const token = getStoredAccessToken();
      if (!token) return;

      setBusy(true);
      setError(null);
      try {
        const [p, c, u, g] = await Promise.all([
          catastoGetParticella(token, currentMatch.particella_id),
          catastoGetParticellaConsorzio(token, currentMatch.particella_id),
          catastoGetParticellaUtenze(token, currentMatch.particella_id),
          catastoGetParticellaGeojson(token, currentMatch.particella_id),
        ]);
        setParticella(p);
        setConsorzio(c);
        setUtenze(u);
        setGeojson(g);
      } catch (e) {
        setParticella(null);
        setConsorzio(null);
        setUtenze([]);
        setGeojson(null);
        setError(e instanceof Error ? e.message : "Errore caricamento dettagli particella");
      } finally {
        setBusy(false);
      }
    }

    void load();
  }, [open, match]);

  async function openCapacitasCertificato(cco: string): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) return;
    setCapacitasLinkBusy(true);
    setCapacitasLinkError(null);
    try {
      const { url } = await capacitasGetRptCertificatoLink(token, cco);
      window.open(url, "_blank", "noopener,noreferrer");
    } catch (e) {
      setCapacitasLinkError(e instanceof Error ? e.message : "Errore generazione link Capacitas");
    } finally {
      setCapacitasLinkBusy(false);
    }
  }

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
                <p className="text-gray-500">Nessun intestatario disponibile nel dataset proprietari oggi collegato.</p>
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
              <p className="font-medium text-gray-900">Catasto consortile</p>
              <p className="mt-1 text-sm text-gray-500">Vista operativa del Consorzio: separa utilizzatore/pagatore annuale dagli intestatari proprietari rilevati in Capacitas.</p>
            </div>
            <p className="text-sm text-gray-500">{busy ? "Caricamento…" : `${consorzio?.units.length ?? 0} unità`}</p>
          </div>
          <div className="mt-3 space-y-3">
            {busy ? (
              <p className="text-sm text-gray-500">Caricamento…</p>
            ) : !consorzio || consorzio.units.length === 0 ? (
              <p className="text-sm text-gray-500">Nessun dato consortile disponibile per questa particella.</p>
            ) : (
              consorzio.units.map((unit) => (
                <div key={unit.id} className="rounded-lg border border-white bg-white p-3">
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div>
                      <p className="font-medium text-gray-900">
                        Unità {unit.foglio ?? "—"}/{unit.particella ?? "—"}{unit.subalterno ? `/${unit.subalterno}` : ""}
                      </p>
                      <p className="mt-1 text-sm text-gray-600">
                        Reale: <span className="font-medium text-gray-800">{unit.comune_label ?? unit.cod_comune_capacitas ?? "—"}</span>
                        {" · "}
                        Sorgente: <span className="font-medium text-gray-800">{unit.source_comune_resolved_label ?? unit.source_comune_label ?? unit.source_cod_comune_capacitas ?? "—"}</span>
                      </p>
                    </div>
                    <span className="rounded-full bg-[#eef5f1] px-2.5 py-1 text-xs font-medium text-[#1D4E35]">
                      {renderResolutionLabel(unit.comune_resolution_mode)}
                    </span>
                  </div>
                  <div className="mt-2 space-y-1 text-sm text-gray-700">
                    <p>
                      <span className="text-gray-500">Belfiore sorgente:</span> {unit.source_codice_catastale ?? "—"}
                    </p>
                    <p>
                      <span className="text-gray-500">Occupazioni:</span> {unit.occupancies.length}
                    </p>
                    {unit.occupancies.length > 0 ? (
                      <p>
                        <span className="text-gray-500">CCO:</span>{" "}
                        {unit.occupancies
                          .slice(0, 3)
                          .map((occ) => occ.cco ?? "—")
                          .join(", ")}
                      </p>
                    ) : null}
                  </div>
                  <div className="mt-3 rounded-lg border border-gray-100 bg-gray-50 p-3">
                    <p className="text-xs font-medium uppercase tracking-widest text-gray-400">Intestatari Proprietari</p>
                    {unit.intestatari_proprietari.length === 0 ? (
                      <p className="mt-2 text-sm text-gray-500">Nessun intestatario strutturato ancora disponibile.</p>
                    ) : (
                      <div className="mt-2 space-y-2">
                        {unit.intestatari_proprietari.slice(0, 5).map((owner) => (
                          <div key={owner.id} className="rounded-lg border border-white bg-white px-3 py-2 text-sm text-gray-700">
                            <p className="font-medium text-gray-900">
                              {owner.denominazione ?? "—"}
                              {owner.deceduto ? <span className="ml-2 text-xs font-medium text-rose-700">Deceduto</span> : null}
                            </p>
                            <p className="mt-1 text-xs text-gray-500">
                              CF: <span className="font-medium text-gray-700">{owner.codice_fiscale ?? "—"}</span>
                              {" · "}Titolo: <span className="font-medium text-gray-700">{owner.titoli ?? "—"}</span>
                            </p>
                            {owner.person ? (
                              <div className="mt-2 rounded-md border border-emerald-100 bg-emerald-50 px-2 py-1.5">
                                <p className="text-xs font-medium text-emerald-800">Anagrafica GAIA corrente</p>
                                <p className="mt-1 text-xs text-emerald-700">
                                  {owner.person.cognome} {owner.person.nome} · {owner.person.codice_fiscale}
                                </p>
                                <p className="mt-1 text-xs text-emerald-700">
                                  Storico anagrafica: {owner.person_snapshots.length} snapshot
                                </p>
                              </div>
                            ) : null}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="mt-4 rounded-xl border border-gray-100 bg-gray-50 p-3 text-sm text-gray-700">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="font-medium text-gray-900">Utilizzatore / pagatore annualità</p>
              <p className="mt-1 text-sm text-gray-500">Elenco sintetico delle righe `cat_utenze_irrigue`: soggetto operativo della campagna annuale.</p>
            </div>
            <p className="text-sm text-gray-500">{busy ? "Caricamento…" : `${utenze.length} righe`}</p>
          </div>
          {capacitasLinkError ? (
            <div className="mt-3 rounded-xl border border-red-100 bg-red-50 p-3 text-sm text-red-800">
              {capacitasLinkError}
            </div>
          ) : null}
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
                    <th></th>
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
                      <td className="py-1 text-sm">
                        {u.cco ? (
                          <button
                            type="button"
                            className="flex items-center gap-1 text-xs font-medium text-[#1D4E35] hover:underline"
                            disabled={capacitasLinkBusy}
                            onClick={() => void openCapacitasCertificato(u.cco!)}
                          >
                            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" className="h-3.5 w-3.5">
                              <path d="M6.22 8.72a.75.75 0 0 0 1.06 1.06l5.22-5.22v1.69a.75.75 0 0 0 1.5 0v-3.5a.75.75 0 0 0-.75-.75h-3.5a.75.75 0 0 0 0 1.5h1.69L6.22 8.72Z" />
                              <path d="M3.5 6.75c0-.69.56-1.25 1.25-1.25H7A.75.75 0 0 0 7 4H4.75A2.75 2.75 0 0 0 2 6.75v4.5A2.75 2.75 0 0 0 4.75 14h4.5A2.75 2.75 0 0 0 12 11.25V9a.75.75 0 0 0-1.5 0v2.25c0 .69-.56 1.25-1.25 1.25h-4.5c-.69 0-1.25-.56-1.25-1.25v-4.5Z" />
                            </svg>
                            {capacitasLinkBusy ? "Apertura…" : "Visualizza su Capacitas"}
                          </button>
                        ) : null}
                      </td>
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
