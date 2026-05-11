"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import type {
  CatAnagraficaMatch,
  CatCapacitasIntestatario,
  CatConsorzioOccupancy,
  CatConsorzioUnit,
  CatParticellaConsorzio,
  CatParticellaDetail,
  CatUtenzaIrrigua,
  GeoJSONFeature,
} from "@/types/catasto";
import { UtenzeSubjectQuickViewDialog } from "@/components/utenze/utenze-subject-quick-view-dialog";
import { getStoredAccessToken } from "@/lib/auth";
import { searchAnagraficaSubjects } from "@/lib/api";
import {
  capacitasGetRptCertificatoLink,
  catastoGetParticella,
  catastoGetParticellaConsorzio,
  catastoGetParticellaGeojson,
  catastoGetParticellaUtenze,
  catastoSyncParticellaCapacitas,
} from "@/lib/api/catasto";

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

function formatDateTime(value: string | null | undefined): string {
  if (!value) return "Mai";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("it-IT");
}

function padCapacitasCode(value: string | number | null | undefined, length: number): string | null {
  if (value == null) return null;
  const normalized = String(value).trim();
  if (!normalized) return null;
  return normalized.padStart(length, "0");
}

function normalizeIdentifier(value: string | null | undefined): string | null {
  if (!value) return null;
  const normalized = value.replace(/\s+/g, "").trim().toUpperCase();
  return normalized || null;
}

function resolveUtenzaCertContext(
  consorzio: CatParticellaConsorzio | null,
  utenza: CatUtenzaIrrigua,
): { com?: string; pvc?: string; fra?: string; ccs?: string } {
  if (!consorzio) return {};

  const candidates = consorzio.units
    .flatMap((unit) => unit.occupancies)
    .filter(
      (occupancy) =>
        occupancy.utenza_id === utenza.id && Boolean(occupancy.com) && Boolean(occupancy.pvc) && Boolean(occupancy.fra),
    )
    .sort((left, right) => {
      if (left.is_current !== right.is_current) return left.is_current ? -1 : 1;
      const leftValid = left.valid_from ?? "";
      const rightValid = right.valid_from ?? "";
      if (leftValid !== rightValid) return rightValid.localeCompare(leftValid);
      return (right.updated_at ?? "").localeCompare(left.updated_at ?? "");
    });

  const best = candidates[0];
  if (!best) return {};
  return {
    com: best.com ?? undefined,
    pvc: best.pvc ?? undefined,
    fra: best.fra ?? undefined,
    ccs: best.ccs ?? undefined,
  };
}

function formatUtenzaPartita(consorzio: CatParticellaConsorzio | null, utenza: CatUtenzaIrrigua): string | null {
  const cco = padCapacitasCode(utenza.cco, 9);
  if (!cco) return null;
  const context = resolveUtenzaCertContext(consorzio, utenza);
  const fra = padCapacitasCode(context.fra ?? utenza.cod_frazione, 2);
  const ccs = padCapacitasCode(context.ccs ?? "00000", 5);
  if (!fra || !ccs) return cco;
  return `${cco}/${fra}/${ccs}`;
}

function getUtenzaSubjectLabel(utenza: CatUtenzaIrrigua): string | null {
  return utenza.subject_display_name?.trim() || utenza.denominazione?.trim() || null;
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
  const [syncBusy, setSyncBusy] = useState(false);
  const [syncMessage, setSyncMessage] = useState<string | null>(null);
  const [subjectQuickView, setSubjectQuickView] = useState<{ id: string; label: string | null } | null>(null);
  const [subjectLookupBusyId, setSubjectLookupBusyId] = useState<string | null>(null);
  const [subjectLookupError, setSubjectLookupError] = useState<string | null>(null);

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
    if (!open) {
      setSubjectQuickView(null);
      setSubjectLookupBusyId(null);
      setSubjectLookupError(null);
    }
  }, [open]);

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

  const openCapacitasCertificato = useCallback(
    async (utenza: CatUtenzaIrrigua): Promise<void> => {
      const token = getStoredAccessToken();
      const cco = utenza.cco?.trim();
      if (!token || !cco || !match) return;

      setCapacitasLinkBusy(true);
      setCapacitasLinkError(null);
      try {
        const context = resolveUtenzaCertContext(consorzio, utenza);
        const { url } = await capacitasGetRptCertificatoLink(token, cco, context);
        window.open(url, "_blank", "noopener,noreferrer");
      } catch (e) {
        setCapacitasLinkError(e instanceof Error ? e.message : "Errore generazione link Capacitas");
      } finally {
        setCapacitasLinkBusy(false);
      }
    },
    [consorzio, match],
  );

  const openSubjectQuickView = useCallback(async (utenza: CatUtenzaIrrigua): Promise<void> => {
    const label = getUtenzaSubjectLabel(utenza);
    if (utenza.subject_id) {
      setSubjectLookupError(null);
      setSubjectQuickView({ id: utenza.subject_id, label });
      return;
    }

    const token = getStoredAccessToken();
    const identifier = normalizeIdentifier(utenza.codice_fiscale);
    if (!token || !identifier) {
      setSubjectLookupError("Nessun soggetto GAIA collegato a questa utenza.");
      return;
    }

    setSubjectLookupBusyId(utenza.id);
    setSubjectLookupError(null);
    try {
      const result = await searchAnagraficaSubjects(token, identifier, 20);
      const matches = result.items.filter((item) => {
        const itemCf = normalizeIdentifier(item.codice_fiscale);
        const itemPiva = normalizeIdentifier(item.partita_iva);
        return itemCf === identifier || itemPiva === identifier;
      });
      if (matches.length === 1) {
        setSubjectQuickView({ id: matches[0].id, label: matches[0].display_name ?? label });
        return;
      }
      if (matches.length > 1) {
        setSubjectLookupError("Identificatore fiscale associato a più soggetti GAIA. Apri la scheda utenze per disambiguare.");
        return;
      }
      setSubjectLookupError("Nessun soggetto GAIA trovato per questo identificatore fiscale.");
    } catch (e) {
      setSubjectLookupError(e instanceof Error ? e.message : "Errore apertura dettaglio soggetto");
    } finally {
      setSubjectLookupBusyId(null);
    }
  }, []);

  async function reloadCurrentParticella(): Promise<void> {
    if (!match) return;
    const token = getStoredAccessToken();
    if (!token) return;

    setBusy(true);
    setError(null);
    try {
      const [p, c, u, g] = await Promise.all([
        catastoGetParticella(token, match.particella_id),
        catastoGetParticellaConsorzio(token, match.particella_id),
        catastoGetParticellaUtenze(token, match.particella_id),
        catastoGetParticellaGeojson(token, match.particella_id),
      ]);
      setParticella(p);
      setConsorzio(c);
      setUtenze(u);
      setGeojson(g);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Errore caricamento dettagli particella");
    } finally {
      setBusy(false);
    }
  }

  async function handleSyncParticella(): Promise<void> {
    if (!match) return;
    const token = getStoredAccessToken();
    if (!token) return;

    setSyncBusy(true);
    setSyncMessage(null);
    setError(null);
    try {
      const response = await catastoSyncParticellaCapacitas(token, match.particella_id);
      setParticella(response.particella);
      setSyncMessage(response.message);
      await reloadCurrentParticella();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Errore sync particella Capacitas");
    } finally {
      setSyncBusy(false);
    }
  }

  if (!open || !match) return null;

  return (
    <div
      className="fixed inset-0 z-50 overflow-y-auto bg-gray-900/45 px-4 py-6"
      role="dialog"
      aria-modal="true"
      aria-label={`Dettaglio ${reference}`}
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="mx-auto flex w-full max-w-4xl flex-col overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-2xl">
        <div className="border-b border-gray-100 px-6 py-5">
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
              <a className="btn-secondary" href={`/catasto/particelle/${match.particella_id}`} target="_blank" rel="noreferrer">
                Apri scheda completa
              </a>
              <button type="button" className="btn-primary" disabled={busy || syncBusy} onClick={() => void handleSyncParticella()}>
                {syncBusy ? "Sincronizzazione…" : "Sincronizza con Capacitas"}
              </button>
              <button type="button" className="btn-secondary" onClick={onClose}>
                Chiudi
              </button>
            </div>
          </div>
        </div>

        <div className="max-h-[calc(100vh-7rem)] overflow-y-auto px-6 py-5">
        <div className="rounded-xl border border-[#d9e7dc] bg-[#f5faf5] px-4 py-3 text-sm text-gray-700">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-medium text-gray-900">Ultimo aggiornamento Capacitas:</span>
            <span>{formatDateTime(particella?.capacitas_last_sync_at)}</span>
            {particella?.capacitas_last_sync_status ? (
              <span className="rounded-full bg-white px-2 py-0.5 text-xs font-medium text-[#1D4E35]">{particella.capacitas_last_sync_status}</span>
            ) : null}
          </div>
          {syncMessage ? <p className="mt-1 text-sm text-[#1D4E35]">{syncMessage}</p> : null}
          {particella?.capacitas_last_sync_error ? <p className="mt-1 text-sm text-amber-700">{particella.capacitas_last_sync_error}</p> : null}
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
              consorzio.units.map((unit: CatConsorzioUnit) => (
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
                          .map((occ: CatConsorzioOccupancy) => occ.cco ?? "—")
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
                        {unit.intestatari_proprietari.slice(0, 5).map((owner: CatCapacitasIntestatario) => (
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
          {subjectLookupError ? (
            <div className="mt-3 rounded-xl border border-amber-100 bg-amber-50 p-3 text-sm text-amber-800">
              {subjectLookupError}
            </div>
          ) : null}
          <div className="mt-3 overflow-auto">
            {busy ? (
              <p className="text-sm text-gray-500">Caricamento…</p>
            ) : utenze.length === 0 ? (
              <p className="text-sm text-gray-500">Nessuna utenza trovata per la particella.</p>
            ) : (
              <table className="w-full min-w-[640px] border-separate border-spacing-y-1">
                <thead>
                  <tr className="text-left text-[10px] font-medium uppercase tracking-widest text-gray-400">
                    <th className="pr-4">Anno</th>
                    <th className="pr-4">CCO</th>
                    <th className="pr-4">CF / soggetto</th>
                    <th className="pr-4">0648 (€)</th>
                    <th className="pr-4">0985 (€)</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {utenze.map((u: CatUtenzaIrrigua) => {
                    const partita = formatUtenzaPartita(consorzio, u);
                    const label = getUtenzaSubjectLabel(u);
                    const canOpenSubject = Boolean(u.subject_id || u.codice_fiscale);
                    const isBusy = subjectLookupBusyId === u.id;
                    const blockClass =
                      "w-full max-w-[280px] rounded-xl border border-[#D9E8DF] bg-[#F5FAF7] px-3 py-2 text-left transition hover:border-[#B7D2C1] hover:bg-[#EEF6F1] disabled:cursor-wait disabled:opacity-70";
                    return (
                      <tr key={u.id} className="rounded-lg bg-white align-top">
                        <td className="py-2 pr-4 text-sm text-gray-700">{u.anno_campagna ?? "—"}</td>
                        <td className="py-2 pr-4 text-sm text-gray-700">
                          <div className="space-y-0.5">
                            <div>{u.cco ?? "—"}</div>
                            <div className="text-xs text-gray-500">{partita ? `Partita ${partita}` : "Partita n/d"}</div>
                          </div>
                        </td>
                        <td className="py-2 pr-4">
                          {canOpenSubject ? (
                            <button type="button" className={blockClass} disabled={isBusy} onClick={() => void openSubjectQuickView(u)}>
                              <span className="block text-sm font-semibold tracking-[0.01em] text-[#1D4E35]">
                                {isBusy ? "Apertura…" : u.codice_fiscale ?? "—"}
                              </span>
                              <span className="mt-1 block text-xs font-medium text-gray-600">{label ?? "Apri dettaglio soggetto"}</span>
                            </button>
                          ) : (
                            <div className="max-w-[280px] rounded-xl border border-gray-200 bg-gray-50 px-3 py-2 text-left">
                              <div className="text-sm font-semibold tracking-[0.01em] text-gray-800">{u.codice_fiscale ?? "—"}</div>
                              <div className="mt-1 text-xs font-medium text-gray-500">{label ?? "Nessun soggetto collegato"}</div>
                            </div>
                          )}
                        </td>
                        <td className="py-2 pr-4 text-sm text-gray-700">{u.importo_0648 ?? "—"}</td>
                        <td className="py-2 pr-4 text-sm text-gray-700">{u.importo_0985 ?? "—"}</td>
                        <td className="py-2 text-sm">
                          {u.cco ? (
                            <button
                              type="button"
                              className="flex items-center gap-1 text-xs font-medium text-[#1D4E35] hover:underline"
                              disabled={capacitasLinkBusy}
                              onClick={() => void openCapacitasCertificato(u)}
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
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>
        </div>
        </div>
      </div>

      {subjectQuickView ? (
        <UtenzeSubjectQuickViewDialog
          subjectId={subjectQuickView.id}
          subjectLabel={subjectQuickView.label}
          onClose={() => setSubjectQuickView(null)}
        />
      ) : null}
    </div>
  );
}
