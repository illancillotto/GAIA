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
import { ParticellaGisDialog } from "@/components/catasto/gis/ParticellaGisDialog";
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

function formatCoordinate(value: number | null | undefined): string {
  if (value == null || !Number.isFinite(value)) return "—";
  return value.toLocaleString("it-IT", { minimumFractionDigits: 6, maximumFractionDigits: 6 });
}

function formatIndice(value: string | number | null | undefined): string {
  if (value == null) return "—";
  const parsed = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(parsed)) return "—";
  return parsed.toLocaleString("it-IT", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function formatHectares(value: string | number | null | undefined): string {
  if (value == null) return "—";
  const parsed = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(parsed)) return "—";
  return `${parsed.toLocaleString("it-IT", { minimumFractionDigits: 2, maximumFractionDigits: 4 })} ha`;
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

function DetailKeyValue({
  label,
  value,
  emphasized = false,
}: {
  label: string;
  value: string;
  emphasized?: boolean;
}) {
  return (
    <div className="flex items-start justify-between gap-3 border-b border-[#eef2ef] py-2 last:border-b-0 last:pb-0">
      <span className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[#7b877f]">{label}</span>
      <span className={`text-right text-sm ${emphasized ? "font-semibold text-[#173426]" : "text-gray-700"}`}>{value}</span>
    </div>
  );
}

function DetailPanel({
  eyebrow,
  title,
  children,
  tone = "default",
}: {
  eyebrow: string;
  title: string;
  children: React.ReactNode;
  tone?: "default" | "soft";
}) {
  const className =
    tone === "soft"
      ? "rounded-2xl border border-[#d9e7dc] bg-[#f8fbf8] p-4"
      : "rounded-2xl border border-[#e7ece8] bg-white p-4";
  return (
    <section className={className}>
      <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-[#7b877f]">{eyebrow}</p>
      <h3 className="mt-1 text-sm font-semibold text-[#173426]">{title}</h3>
      <div className="mt-3">{children}</div>
    </section>
  );
}

function SummaryTile({
  label,
  value,
  accent = "default",
}: {
  label: string;
  value: string;
  accent?: "default" | "success" | "info";
}) {
  const tone =
    accent === "success"
      ? "border-[#dbeadc] bg-[#f6fbf6] text-[#173426]"
      : accent === "info"
        ? "border-[#dfe7f2] bg-[#f8fbff] text-[#173426]"
        : "border-[#e7ece8] bg-white text-[#173426]";
  return (
    <div className={`rounded-2xl border px-4 py-3 ${tone}`}>
      <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-[#7b877f]">{label}</p>
      <p className="mt-2 text-lg font-semibold">{value}</p>
    </div>
  );
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
  const [copiedUtenzaId, setCopiedUtenzaId] = useState<string | null>(null);
  const [gisOpen, setGisOpen] = useState(false);

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
      setGisOpen(false);
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

  const copyUtenzaIdentifier = useCallback(async (utenza: CatUtenzaIrrigua): Promise<void> => {
    const identifier = normalizeIdentifier(utenza.codice_fiscale);
    if (!identifier) return;

    try {
      await navigator.clipboard.writeText(identifier);
      setCopiedUtenzaId(utenza.id);
      window.setTimeout(() => {
        setCopiedUtenzaId((current) => (current === utenza.id ? null : current));
      }, 1800);
    } catch {
      setSubjectLookupError("Impossibile copiare il codice fiscale negli appunti.");
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
      className="fixed inset-0 z-[70] overflow-y-auto bg-black/45 px-3 py-5 backdrop-blur-sm xl:px-5"
      role="dialog"
      aria-modal="true"
      aria-label={`Dettaglio ${reference}`}
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="mx-auto flex max-h-[95vh] w-full max-w-[min(1600px,98vw)] flex-col overflow-hidden rounded-[28px] border border-gray-200 bg-white shadow-[0_30px_90px_rgba(15,23,42,0.24)]">
        <div className="border-b border-gray-100 px-6 py-5">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0">
              <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#6b7b70]">Dettaglio particella</p>
              <p className="mt-1 text-xl font-semibold text-[#173426]">{reference}</p>
              <div className="mt-3 flex flex-wrap gap-2 text-xs">
                <span className="rounded-full border border-[#d8e4da] bg-[#f6fbf7] px-2.5 py-1 font-medium text-[#1d4e35]">
                  {match.comune ?? "Comune —"}
                </span>
                <span className="rounded-full border border-[#e5e7eb] bg-white px-2.5 py-1 font-medium text-gray-600">
                  Capacitas {match.cod_comune_capacitas ?? "—"}
                </span>
                <span className="rounded-full border border-[#e5e7eb] bg-white px-2.5 py-1 font-medium text-gray-600">
                  Distretto {match.num_distretto ?? "—"}
                </span>
                {particella?.fuori_distretto ? (
                  <span className="rounded-full border border-amber-200 bg-amber-50 px-2.5 py-1 font-medium text-amber-800">Fuori distretto</span>
                ) : null}
              </div>
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
        <div className="min-h-0 overflow-y-auto bg-[#f4f7f5] px-6 py-5 xl:px-5">
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

        <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <SummaryTile label="Sup. grafica" value={formatHaFromMq(particella?.superficie_grafica_mq ?? match.superficie_grafica_mq)} />
          <SummaryTile label="Coltura ruolo" value={particella?.indice_irriguo_coltura ?? "—"} />
          <SummaryTile
            label="Tariffa finale"
            value={`${formatIndice(particella?.indice_irriguo_finale)} €/ha`}
            accent="success"
          />
          <SummaryTile
            label="Costo stimato"
            value={`${formatIndice(particella?.indice_irriguo_importo_stimato)} €`}
            accent="info"
          />
        </div>

        <div className="mt-4 grid gap-3 xl:grid-cols-[1.2fr_1.2fr_1fr]">
          <DetailPanel eyebrow="Catasto" title="Riferimenti territoriali" tone="soft">
            <div>
              <DetailKeyValue label="Sup. catastale" value={formatHaFromMq(match.superficie_mq)} />
              <DetailKeyValue label="Sup. grafica" value={formatHaFromMq(particella?.superficie_grafica_mq ?? match.superficie_grafica_mq)} />
              <DetailKeyValue label="Fonte" value={particella?.source_type ?? "—"} />
              <DetailKeyValue label="Fuori distretto" value={particella ? (particella.fuori_distretto ? "Sì" : "No") : "—"} />
            </div>
          </DetailPanel>

          <DetailPanel eyebrow="Tariffa irrigua" title="Preview da delibera 2025">
            <div>
              <DetailKeyValue label="Coltura" value={particella?.indice_irriguo_coltura ?? "—"} emphasized />
              <DetailKeyValue label="Sup. irrigata ruolo" value={formatHectares(particella?.indice_irriguo_sup_irrigata_ha)} />
              <DetailKeyValue label="Tariffa base IB 1,00" value={`${formatIndice(particella?.indice_irriguo_base)} €/ha`} />
              <DetailKeyValue label="IB territoriale" value={formatIndice(particella?.indice_irriguo_moltiplicatore)} />
              <DetailKeyValue label="Tariffa finale" value={`${formatIndice(particella?.indice_irriguo_finale)} €/ha`} emphasized />
              <DetailKeyValue label="Tariffa contatore" value={`${formatIndice(particella?.indice_irriguo_euro_mc)} €/mc`} />
              <DetailKeyValue label="Costo stimato" value={`${formatIndice(particella?.indice_irriguo_importo_stimato)} €`} emphasized />
              <DetailKeyValue label="Anno indice" value={String(particella?.indice_irriguo_anno_riferimento ?? "—")} />
            </div>
          </DetailPanel>

          <DetailPanel eyebrow="Geometria" title="Mappa e coordinate">
            <div className="space-y-3 text-sm text-gray-700">
              <div className="grid gap-2">
                <DetailKeyValue
                  label="Tipo"
                  value={busy ? "Caricamento…" : ((geojson?.properties?.["geometry_type"] as string | undefined) ?? "—")}
                />
                <DetailKeyValue label="Latitudine" value={formatCoordinate(centroid?.lat)} />
                <DetailKeyValue label="Longitudine" value={formatCoordinate(centroid?.lon)} />
              </div>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  className="btn-secondary !px-3 !py-1.5 text-xs"
                  disabled={!geojson}
                  onClick={() => {
                    if (!geojson) return;
                    setGisOpen(true);
                  }}
                >
                  Apri GeoJSON
                </button>
                <button
                  type="button"
                  className="btn-secondary !px-3 !py-1.5 text-xs"
                  disabled={!geojson}
                  onClick={() => {
                    if (!geojson) return;
                    const blob = new Blob([JSON.stringify(geojson, null, 2)], { type: "application/geo+json" });
                    const url = URL.createObjectURL(blob);
                    const anchor = window.document.createElement("a");
                    anchor.href = url;
                    anchor.download = `particella-${match.foglio}-${match.particella}${match.subalterno ? `-${match.subalterno}` : ""}.geojson`;
                    anchor.click();
                    setTimeout(() => URL.revokeObjectURL(url), 30_000);
                  }}
                >
                  Scarica GeoJSON
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
          </DetailPanel>
        </div>

        <div className="mt-4 grid gap-3 xl:grid-cols-[0.95fr_2.05fr]">
          <DetailPanel eyebrow="Proprietà" title="Intestatari e possesso" tone="soft">
            <div className="space-y-2 text-sm text-gray-700">
              {(match.intestatari ?? []).length === 0 ? (
                <p className="text-gray-500">Nessun intestatario disponibile nel dataset proprietari oggi collegato.</p>
              ) : (
                <ul className="space-y-2">
                  {(match.intestatari ?? []).slice(0, 10).map((i) => (
                    <li key={i.id} className="rounded-xl border border-[#e7ece8] bg-white px-3 py-2">
                      <span className="block font-medium text-[#173426]">
                        {(i.denominazione ?? i.ragione_sociale ?? [i.cognome, i.nome].filter(Boolean).join(" ")) || "—"}
                      </span>
                      <span className="mt-1 block text-xs text-gray-500">{i.codice_fiscale ?? "CF non disponibile"}</span>
                    </li>
                  ))}
                </ul>
              )}
              <p className="text-xs text-gray-500">
                Nota: il “titolo di possesso” puntuale non è ancora esposto come dato strutturato; qui mostriamo gli intestatari rilevati da CF presenti nelle utenze.
              </p>
            </div>
          </DetailPanel>
        </div>

        <div className="mt-4 rounded-2xl border border-[#e7ece8] bg-white p-4 text-sm text-gray-700">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-[#7b877f]">Catasto consortile</p>
              <p className="mt-1 text-sm font-semibold text-[#173426]">Unità e occupazioni collegate</p>
              <p className="mt-1 text-sm text-gray-500">Vista operativa del Consorzio: separa utilizzatore/pagatore annuale dagli intestatari proprietari rilevati in Capacitas.</p>
            </div>
            <p className="rounded-full border border-[#e7ece8] bg-[#f8fbf8] px-2.5 py-1 text-xs font-medium text-[#4c5d52]">{busy ? "Caricamento…" : `${consorzio?.units.length ?? 0} unità`}</p>
          </div>
          <div className="mt-3 space-y-3">
            {busy ? (
              <p className="text-sm text-gray-500">Caricamento…</p>
            ) : !consorzio || consorzio.units.length === 0 ? (
              <p className="text-sm text-gray-500">Nessun dato consortile disponibile per questa particella.</p>
            ) : (
              consorzio.units.map((unit: CatConsorzioUnit) => (
                <div key={unit.id} className="rounded-2xl border border-[#e7ece8] bg-[#fbfcfb] p-4">
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div>
                      <p className="font-medium text-[#173426]">
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
                    <DetailKeyValue label="Belfiore sorgente" value={unit.source_codice_catastale ?? "—"} />
                    <DetailKeyValue label="Occupazioni" value={String(unit.occupancies.length)} />
                    {unit.occupancies.length > 0 ? (
                      <DetailKeyValue
                        label="CCO"
                        value={unit.occupancies
                          .slice(0, 3)
                          .map((occ: CatConsorzioOccupancy) => occ.cco ?? "—")
                          .join(", ")}
                      />
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

        <div className="mt-4 rounded-2xl border border-[#e7ece8] bg-white p-4 text-sm text-gray-700">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-[#7b877f]">Utenze annuali</p>
              <p className="mt-1 text-sm font-semibold text-[#173426]">Utilizzatore / pagatore annualità</p>
              <p className="mt-1 text-sm text-gray-500">Elenco sintetico delle righe `cat_utenze_irrigue`: soggetto operativo della campagna annuale.</p>
            </div>
            <p className="rounded-full border border-[#e7ece8] bg-[#f8fbf8] px-2.5 py-1 text-xs font-medium text-[#4c5d52]">{busy ? "Caricamento…" : `${utenze.length} righe`}</p>
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
                    const canCopyIdentifier = Boolean(normalizeIdentifier(u.codice_fiscale));
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
                          <div className="flex max-w-[320px] items-start gap-2">
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
                            {canCopyIdentifier ? (
                              <button
                                type="button"
                                className="mt-1 inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-[#D9E8DF] bg-white text-[#1D4E35] transition hover:border-[#B7D2C1] hover:bg-[#EEF6F1]"
                                aria-label={`Copia codice fiscale ${u.codice_fiscale ?? ""}`}
                                title={copiedUtenzaId === u.id ? "Copiato" : "Copia CF"}
                                onClick={() => void copyUtenzaIdentifier(u)}
                              >
                                {copiedUtenzaId === u.id ? (
                                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4">
                                    <path fillRule="evenodd" d="M16.704 5.29a1 1 0 0 1 .006 1.414l-7.25 7.312a1 1 0 0 1-1.42-.005L3.29 9.17a1 1 0 1 1 1.42-1.408l4.04 4.077 6.54-6.544a1 1 0 0 1 1.414-.006Z" clipRule="evenodd" />
                                  </svg>
                                ) : (
                                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4">
                                    <path d="M6 2.75A1.75 1.75 0 0 0 4.25 4.5v8c0 .966.784 1.75 1.75 1.75h6A1.75 1.75 0 0 0 13.75 12.5v-8A1.75 1.75 0 0 0 12 2.75H6Z" />
                                    <path d="M8 15.25a.75.75 0 0 1 0-1.5h4A3.25 3.25 0 0 0 15.25 10.5v-4a.75.75 0 0 1 1.5 0v4A4.75 4.75 0 0 1 12 15.25H8Z" />
                                  </svg>
                                )}
                              </button>
                            ) : null}
                          </div>
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

      <ParticellaGisDialog
        open={gisOpen}
        match={match}
        geojson={geojson}
        centroid={centroid}
        onClose={() => setGisOpen(false)}
      />
    </div>
  );
}
