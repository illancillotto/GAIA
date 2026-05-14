"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import { ProtectedPage } from "@/components/app/protected-page";
import {
  ElaborazioneHero,
  ElaborazioneMiniStat,
  ElaborazioneNoticeCard,
  ElaborazionePanelHeader,
} from "@/components/elaborazioni/module-chrome";
import { ModuleWorkspaceKpiRow } from "@/components/layout/module-workspace-hero";
import { EmptyState } from "@/components/ui/empty-state";
import { GridIcon, RefreshIcon, SearchIcon } from "@/components/ui/icons";
import {
  catastoGetDashboardSummary,
  catastoGetDistrettoGeojson,
  catastoGisApplyAdeAlignment,
  catastoGisGetAdeAlignmentReport,
  catastoGisGetAdeWfsRunStatus,
  catastoGisGetLatestAdeWfsRunStatus,
  catastoGisPreviewAdeAlignmentApply,
  catastoGisSyncAdeWfsBboxAsync,
  catastoListDistretti,
} from "@/lib/api/catasto";
import { getStoredAccessToken } from "@/lib/auth";
import { formatDateTime } from "@/lib/presentation";
import type { CatDashboardSummary, CatDistretto } from "@/types/catasto";
import type {
  AdeAlignmentApplyPreviewResponse,
  AdeAlignmentApplyResponse,
  AdeAlignmentReportResponse,
  AdeWfsRunStatusResponse,
} from "@/types/gis";

const POLL_INTERVAL_MS = 2500;
const ADE_APPLY_CATEGORIES = ["nuove_in_ade", "geometrie_variate"] as const;

type AdeBboxForm = {
  minLon: string;
  minLat: string;
  maxLon: string;
  maxLat: string;
};

function geometryToBbox(geometry: GeoJSON.Geometry): AdeBboxForm | null {
  const stack: unknown[] = [];
  let minLon = Number.POSITIVE_INFINITY;
  let minLat = Number.POSITIVE_INFINITY;
  let maxLon = Number.NEGATIVE_INFINITY;
  let maxLat = Number.NEGATIVE_INFINITY;
  let hasCoordinates = false;
  if (geometry.type === "GeometryCollection") {
    for (const item of geometry.geometries) {
      stack.push("coordinates" in item ? item.coordinates : []);
    }
  } else {
    stack.push(geometry.coordinates);
  }

  while (stack.length > 0) {
    const value = stack.pop();
    if (!Array.isArray(value)) continue;
    if (value.length >= 2 && typeof value[0] === "number" && typeof value[1] === "number") {
      const lon = value[0];
      const lat = value[1];
      minLon = Math.min(minLon, lon);
      minLat = Math.min(minLat, lat);
      maxLon = Math.max(maxLon, lon);
      maxLat = Math.max(maxLat, lat);
      hasCoordinates = true;
      continue;
    }
    for (let index = 0; index < value.length; index += 1) {
      stack.push(value[index]);
    }
  }

  if (!hasCoordinates) return null;
  return {
    minLon: minLon.toFixed(6),
    minLat: minLat.toFixed(6),
    maxLon: maxLon.toFixed(6),
    maxLat: maxLat.toFixed(6),
  };
}

function featureCollectionToBbox(collection: GeoJSON.FeatureCollection): AdeBboxForm | null {
  const geometries = collection.features.map((feature) => feature.geometry).filter(Boolean) as GeoJSON.Geometry[];
  if (geometries.length === 0) return null;
  return geometryToBbox({ type: "GeometryCollection", geometries } as GeoJSON.Geometry);
}

function renderRunTone(status: string): string {
  switch (status) {
    case "completed":
      return "text-emerald-700 bg-emerald-50";
    case "failed":
      return "text-rose-700 bg-rose-50";
    case "processing":
      return "text-sky-700 bg-sky-50";
    case "queued":
      return "text-amber-700 bg-amber-50";
    default:
      return "text-slate-700 bg-slate-100";
  }
}

export function ElaborazioniAdeAlignmentWorkspace() {
  const [dashboard, setDashboard] = useState<CatDashboardSummary | null>(null);
  const [distretti, setDistretti] = useState<CatDistretto[]>([]);
  const [runStatus, setRunStatus] = useState<AdeWfsRunStatusResponse | null>(null);
  const [report, setReport] = useState<AdeAlignmentReportResponse | null>(null);
  const [preview, setPreview] = useState<AdeAlignmentApplyPreviewResponse | null>(null);
  const [applyResult, setApplyResult] = useState<AdeAlignmentApplyResponse | null>(null);
  const [confirmText, setConfirmText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const loadWorkspace = useCallback(async () => {
    const token = getStoredAccessToken();
    if (!token) return;

    try {
      const [dashboardResult, distrettiResult] = await Promise.all([
        catastoGetDashboardSummary(token),
        catastoListDistretti(token),
      ]);
      setDashboard(dashboardResult);
      setDistretti(distrettiResult);

      try {
        const latestRun = await catastoGisGetLatestAdeWfsRunStatus(token);
        setRunStatus(latestRun);
        if (latestRun.status === "completed") {
          const latestReport = await catastoGisGetAdeAlignmentReport(token, latestRun.run_id, { geometryThresholdM: 1 });
          setReport(latestReport);
        }
      } catch {
        setRunStatus(null);
        setReport(null);
      }

      setError(null);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Errore caricamento workspace AdE");
    }
  }, []);

  useEffect(() => {
    void loadWorkspace();
  }, [loadWorkspace]);

  useEffect(() => {
    const token = getStoredAccessToken();
    if (!token || !runStatus || !["queued", "processing"].includes(runStatus.status)) {
      return;
    }
    const timeout = window.setTimeout(() => {
      void catastoGisGetAdeWfsRunStatus(token, runStatus.run_id)
        .then(async (status) => {
          setRunStatus(status);
          if (status.status === "completed") {
            const nextReport = await catastoGisGetAdeAlignmentReport(token, status.run_id, { geometryThresholdM: 1 });
            setReport(nextReport);
            setBusy(false);
            setMessage(`Run AdE completato: ${status.features.toLocaleString("it-IT")} particelle scaricate.`);
          } else if (status.status === "failed") {
            setBusy(false);
            setError(status.error || "Run AdE fallito.");
          }
        })
        .catch((pollError) => {
          setBusy(false);
          setError(pollError instanceof Error ? pollError.message : "Errore polling run AdE");
        });
    }, POLL_INTERVAL_MS);

    return () => window.clearTimeout(timeout);
  }, [runStatus]);

  const activeDistretti = useMemo(
    () => distretti.filter((distretto) => distretto.attivo && distretto.num_distretto !== "FD"),
    [distretti],
  );
  const confirmationPhrase = report ? `APPLICA ${report.run_id.slice(0, 8)}` : "";
  const canApply = Boolean(
    report &&
      preview &&
      confirmText.trim() === confirmationPhrase &&
      report.counters.match_ambiguo === 0 &&
      !busy,
  );

  async function handleStartComprensorioRun(): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) return;
    if (activeDistretti.length === 0) {
      setError("Nessun distretto attivo disponibile per il comprensorio.");
      return;
    }

    setBusy(true);
    setError(null);
    setMessage("Calcolo bbox comprensorio e accodamento run AdE...");
    setPreview(null);
    setApplyResult(null);
    setConfirmText("");
    try {
      const features = await Promise.all(
        activeDistretti.map((distretto) => catastoGetDistrettoGeojson(token, distretto.id)),
      );
      const bbox = featureCollectionToBbox({
        type: "FeatureCollection",
        features: features as GeoJSON.Feature[],
      });
      if (!bbox) throw new Error("BBox comprensorio non disponibile.");

      const response = await catastoGisSyncAdeWfsBboxAsync(token, {
        min_lon: Number(bbox.minLon),
        min_lat: Number(bbox.minLat),
        max_lon: Number(bbox.maxLon),
        max_lat: Number(bbox.maxLat),
        max_tile_km2: 4,
        max_tiles: 400,
        count: 1000,
        max_pages_per_tile: 20,
      });
      setRunStatus({
        run_id: response.run_id,
        status: response.status,
        requested_bbox: response.requested_bbox,
        tiles: response.tiles,
        features: response.features,
        upserted: response.upserted,
        with_geometry: response.with_geometry,
        error: null,
        started_at: new Date().toISOString(),
        completed_at: null,
      });
      setReport(null);
      setMessage(`Run AdE accodato: ${response.tiles.toLocaleString("it-IT")} tile stimati.`);
    } catch (runError) {
      setBusy(false);
      setError(runError instanceof Error ? runError.message : "Impossibile avviare il run AdE");
    }
  }

  async function handlePreviewApply(): Promise<void> {
    const token = getStoredAccessToken();
    if (!token || !report) return;

    setBusy(true);
    setError(null);
    try {
      const nextPreview = await catastoGisPreviewAdeAlignmentApply(token, report.run_id, {
        categories: [...ADE_APPLY_CATEGORIES],
        geometry_threshold_m: report.geometry_threshold_m,
      });
      setPreview(nextPreview);
      setApplyResult(null);
      setConfirmText("");
      setMessage("Preview applicazione calcolata.");
    } catch (previewError) {
      setError(previewError instanceof Error ? previewError.message : "Errore preview applicazione");
    } finally {
      setBusy(false);
    }
  }

  async function handleApply(): Promise<void> {
    const token = getStoredAccessToken();
    if (!token || !report || !preview) return;

    setBusy(true);
    setError(null);
    try {
      const result = await catastoGisApplyAdeAlignment(token, report.run_id, {
        categories: [...ADE_APPLY_CATEGORIES],
        geometry_threshold_m: report.geometry_threshold_m,
        confirm: true,
        allow_suppress_missing: false,
      });
      setApplyResult(result);
      setPreview(null);
      setConfirmText("");
      const nextReport = await catastoGisGetAdeAlignmentReport(token, report.run_id, { geometryThresholdM: report.geometry_threshold_m });
      setReport(nextReport);
      setMessage("Apply AdE completato.");
    } catch (applyError) {
      setError(applyError instanceof Error ? applyError.message : "Errore apply AdE");
    } finally {
      setBusy(false);
    }
  }

  return (
    <ProtectedPage
      title="Allineamento AdE"
      description="Console operativa del run Agenzia Entrate: avvio comprensorio, monitoraggio asincrono, preview differenze e apply controllato."
      requiredRoles={["admin", "super_admin"]}
    >
      <div className="page-stack">
        <ElaborazioneHero
          badge="Elaborazioni / AdE"
          title="Allineamento AdE"
          description="Console operativa del run Agenzia Entrate: avvio comprensorio, monitoraggio asincrono, preview differenze e apply controllato."
          actions={(
            <div className="flex flex-wrap gap-2">
              <Link className="btn-secondary" href="/catasto/gis">
                Apri GIS
              </Link>
              <button className="btn-primary" disabled={busy} onClick={() => void loadWorkspace()} type="button">
                Aggiorna
              </button>
            </div>
          )}
        >
          <ModuleWorkspaceKpiRow>
            <ElaborazioneMiniStat
              eyebrow="Run corrente"
              value={runStatus ? runStatus.run_id.slice(0, 8) : "—"}
              description={runStatus?.status ?? "nessun run"}
            />
            <ElaborazioneMiniStat eyebrow="Tile stimati" value={runStatus?.tiles ?? 0} description="scope bbox attuale" />
            <ElaborazioneMiniStat eyebrow="Nuove AdE" value={dashboard?.ade_alignment.nuove_in_ade ?? 0} description="ultimo report disponibile" />
            <ElaborazioneMiniStat eyebrow="Geom. variate" value={dashboard?.ade_alignment.geometrie_variate ?? 0} description="ultimo report disponibile" />
          </ModuleWorkspaceKpiRow>
        </ElaborazioneHero>

        {error ? <ElaborazioneNoticeCard title="Errore workspace" description={error} tone="danger" /> : null}
        {message ? <ElaborazioneNoticeCard title="Stato run" description={message} tone="success" /> : null}

        <section className="rounded-3xl border border-[#edf1eb] bg-white shadow-[0_18px_50px_rgba(15,23,42,0.08)]">
          <ElaborazionePanelHeader
            badge="Comprensorio"
            title="Avvio e monitoraggio run"
            description="Il comprensorio AdE viene avviato come job asincrono persistito. Il polling ricarica stato e report senza lasciare la console operativa."
            actions={(
              <button className="btn-primary" disabled={busy} onClick={() => void handleStartComprensorioRun()} type="button">
                {busy && runStatus && ["queued", "processing"].includes(runStatus.status) ? "Run in corso..." : "Allinea comprensorio"}
              </button>
            )}
          />
          <div className="grid gap-4 px-6 py-6 xl:grid-cols-[1.2fr_0.8fr]">
            <div className="rounded-2xl border border-[#e6ece6] bg-[#fafcf9] p-4">
              <p className="text-sm font-semibold text-gray-900">Stato sistema AdE</p>
              <p className="mt-2 text-sm text-gray-600">{dashboard?.ade_alignment.message ?? "Nessun dato disponibile."}</p>
              <div className="mt-4 grid gap-3 sm:grid-cols-2">
                <div className="rounded-2xl bg-white p-4 shadow-sm">
                  <p className="text-xs uppercase tracking-[0.18em] text-gray-400">Ultimo update</p>
                  <p className="mt-2 text-sm font-semibold text-gray-900">{dashboard?.ade_alignment.latest_fetched_at ? formatDateTime(dashboard.ade_alignment.latest_fetched_at ?? null) : "—"}</p>
                </div>
                <div className="rounded-2xl bg-white p-4 shadow-sm">
                  <p className="text-xs uppercase tracking-[0.18em] text-gray-400">Distretti attivi</p>
                  <p className="mt-2 text-sm font-semibold text-gray-900">{activeDistretti.length}</p>
                </div>
              </div>
            </div>

            <div className="rounded-2xl border border-[#e6ece6] bg-white p-4 shadow-sm">
              <div className="flex items-center justify-between gap-3">
                <p className="text-sm font-semibold text-gray-900">Run AdE</p>
                {runStatus ? <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${renderRunTone(runStatus.status)}`}>{runStatus.status}</span> : null}
              </div>
              {runStatus ? (
                <div className="mt-3 space-y-2 text-sm text-gray-600">
                  <p>Run: <span className="font-medium text-gray-900">{runStatus.run_id}</span></p>
                  <p>Tile: <span className="font-medium text-gray-900">{runStatus.tiles}</span></p>
                  <p>Feature: <span className="font-medium text-gray-900">{runStatus.features}</span></p>
                  <p>Con geometria: <span className="font-medium text-gray-900">{runStatus.with_geometry}</span></p>
                  <p>Avviato: <span className="font-medium text-gray-900">{formatDateTime(runStatus.started_at ?? null)}</span></p>
                  <p>Completato: <span className="font-medium text-gray-900">{formatDateTime(runStatus.completed_at ?? null)}</span></p>
                  {runStatus.error ? <p className="text-rose-700">{runStatus.error}</p> : null}
                </div>
              ) : (
                <div className="mt-4">
                  <EmptyState icon={RefreshIcon} title="Nessun run AdE" description="Avvia il primo run comprensorio da questa console." />
                </div>
              )}
            </div>
          </div>
        </section>

        <section className="rounded-3xl border border-[#edf1eb] bg-white shadow-[0_18px_50px_rgba(15,23,42,0.08)]">
          <ElaborazionePanelHeader
            badge="Report"
            title="Differenze AdE / GAIA"
            description="Lettura operativa del run completato: contatori, preview apply e conferma scrittura fuori dal GIS."
            actions={report ? (
              <button className="btn-secondary" disabled={busy} onClick={() => void handlePreviewApply()} type="button">
                Preview applicazione
              </button>
            ) : null}
          />
          {!report ? (
            <div className="px-6 py-8">
              <EmptyState icon={SearchIcon} title="Nessun report disponibile" description="Completa un run AdE per vedere differenze e preview di applicazione." />
            </div>
          ) : (
            <div className="space-y-5 px-6 py-6">
              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                <div className="rounded-2xl bg-emerald-50 p-4">
                  <p className="text-xs uppercase tracking-[0.18em] text-emerald-700">Allineate</p>
                  <p className="mt-2 text-2xl font-semibold text-emerald-900">{report.counters.allineate}</p>
                </div>
                <div className="rounded-2xl bg-amber-50 p-4">
                  <p className="text-xs uppercase tracking-[0.18em] text-amber-700">Nuove AdE</p>
                  <p className="mt-2 text-2xl font-semibold text-amber-900">{report.counters.nuove_in_ade}</p>
                </div>
                <div className="rounded-2xl bg-rose-50 p-4">
                  <p className="text-xs uppercase tracking-[0.18em] text-rose-700">Geom. variate</p>
                  <p className="mt-2 text-2xl font-semibold text-rose-900">{report.counters.geometrie_variate}</p>
                </div>
                <div className="rounded-2xl bg-slate-100 p-4">
                  <p className="text-xs uppercase tracking-[0.18em] text-slate-600">Match ambigui</p>
                  <p className="mt-2 text-2xl font-semibold text-slate-900">{report.counters.match_ambiguo}</p>
                </div>
              </div>

              {preview ? (
                <div className="rounded-2xl border border-amber-100 bg-amber-50/40 p-4">
                  <div className="grid gap-4 xl:grid-cols-[1fr_auto] xl:items-start">
                    <div className="space-y-3">
                      <p className="text-sm font-semibold text-gray-900">Dry-run apply</p>
                      <p className="text-sm text-gray-600">
                        Insert previsti: <span className="font-medium text-gray-900">{preview.counters.insert_new}</span> · update geometria:{" "}
                        <span className="font-medium text-gray-900">{preview.counters.update_geometry}</span> · ambigui esclusi:{" "}
                        <span className="font-medium text-gray-900">{preview.counters.skipped_ambiguous}</span>
                      </p>
                      <p className="text-sm text-gray-600">
                        Impatto: <span className="font-medium text-gray-900">{preview.impact.utenze_collegate}</span> utenze,{" "}
                        <span className="font-medium text-gray-900">{preview.impact.consorzio_units_collegate}</span> unità consorzio,{" "}
                        <span className="font-medium text-gray-900">{preview.impact.ruolo_particelle_collegate}</span> righe ruolo.
                      </p>
                      {preview.warnings.length > 0 ? <p className="text-sm text-amber-700">{preview.warnings.join(" ")}</p> : null}
                    </div>
                    <div className="w-full max-w-sm rounded-2xl border border-amber-100 bg-white p-4">
                      {report.counters.match_ambiguo > 0 ? (
                        <p className="text-sm font-medium text-rose-700">Apply bloccato: sono presenti match ambigui.</p>
                      ) : (
                        <>
                          <label className="block text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">
                            Conferma scrittura
                            <input
                              className="form-control mt-2"
                              placeholder={confirmationPhrase}
                              value={confirmText}
                              onChange={(event) => setConfirmText(event.target.value)}
                            />
                          </label>
                          <button className="btn-primary mt-3 w-full" disabled={!canApply} onClick={() => void handleApply()} type="button">
                            Applica nuove e geometrie
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                </div>
              ) : null}

              {applyResult ? (
                <ElaborazioneNoticeCard
                  title="Apply completato"
                  description={`Inserite ${applyResult.counters.inserted_new} nuove particelle, aggiornate ${applyResult.counters.updated_geometry} geometrie.`}
                  tone="success"
                />
              ) : null}
            </div>
          )}
        </section>

        <section className="rounded-3xl border border-[#edf1eb] bg-white shadow-[0_18px_50px_rgba(15,23,42,0.08)]">
          <ElaborazionePanelHeader
            badge="Superfici"
            title="Dove leggere il risultato"
            description="Il GIS resta la superficie di lettura geografica del sistema aggiornato; questa console governa il ciclo operativo del run AdE."
          />
          <div className="grid gap-4 px-6 py-6 md:grid-cols-2">
            <Link className="rounded-2xl border border-[#dfe7dc] bg-[#fafcf9] p-5 transition hover:border-[#1D4E35] hover:shadow-sm" href="/catasto/gis">
              <div className="flex items-center gap-3">
                <GridIcon className="h-5 w-5 text-[#1D4E35]" />
                <p className="text-sm font-semibold text-gray-900">Apri GIS</p>
              </div>
              <p className="mt-2 text-sm text-gray-600">Consulta stato aggiornamento sistema, distretti e differenze cartografiche senza eseguire operazioni runtime.</p>
            </Link>
            <Link className="rounded-2xl border border-[#dfe7dc] bg-white p-5 transition hover:border-[#1D4E35] hover:shadow-sm" href="/catasto">
              <div className="flex items-center gap-3">
                <SearchIcon className="h-5 w-5 text-[#1D4E35]" />
                <p className="text-sm font-semibold text-gray-900">Apri dashboard Catasto</p>
              </div>
              <p className="mt-2 text-sm text-gray-600">Verifica alert, contatori differenze e stato complessivo dell&apos;allineamento AdE nel dominio Catasto.</p>
            </Link>
          </div>
        </section>
      </div>
    </ProtectedPage>
  );
}
