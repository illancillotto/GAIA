"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";

import { CatastoPage } from "@/components/catasto/catasto-page";
import { ImportStatusBadge } from "@/components/catasto/ImportStatusBadge";
import { AnomaliaStatusBadge } from "@/components/catasto/AnomaliaStatusBadge";
import { AlertBanner } from "@/components/ui/alert-banner";
import { EmptyState } from "@/components/ui/empty-state";
import { RefreshIcon, DocumentIcon, SearchIcon } from "@/components/ui/icons";
import {
  catastoGetImportHistory,
  catastoGetImportReport,
  catastoGetImportStatus,
  catastoGetImportSummary,
  catastoUploadCapacitas,
  catastoUploadShapefile,
} from "@/lib/api/catasto";
import { ApiError, isAuthError } from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import type { CatAnomaliaListResponse, CatImportBatch, CatImportSummary, UUID } from "@/types/catasto";

type StepKey = "upload" | "progress" | "report";
type ImportType = "capacitas" | "shapefile";

type PreviewAnomalia = {
  riga?: number;
  tipo?: string;
} & Record<string, unknown>;

function safeNumber(value: unknown): number {
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}

function safeString(value: unknown): string {
  return typeof value === "string" ? value : "";
}

function safeStringArray(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string" && item.length > 0) : [];
}

function formatDateTime(value: string | null): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("it-IT", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(date);
}

export default function CatastoImportPage() {
  const [step, setStep] = useState<StepKey>("upload");
  const [importType, setImportType] = useState<ImportType>("capacitas");
  const [file, setFile] = useState<File | null>(null);
  const [force, setForce] = useState(false);
  const [sourceSrid, setSourceSrid] = useState(4326);
  const [uploadProgress, setUploadProgress] = useState(0);

  const [batchId, setBatchId] = useState<UUID | null>(null);
  const [batch, setBatch] = useState<CatImportBatch | null>(null);
  const [history, setHistory] = useState<CatImportBatch[]>([]);
  const [summary, setSummary] = useState<CatImportSummary | null>(null);
  const [historyStatus, setHistoryStatus] = useState<string>("");
  const [historyLimit, setHistoryLimit] = useState<number>(5);
  const [reportTipo, setReportTipo] = useState<string>("");
  const [reportPage, setReportPage] = useState(1);
  const [report, setReport] = useState<CatAnomaliaListResponse | null>(null);

  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const pollTimer = useRef<number | null>(null);

  const reportJson = batch?.report_json ?? null;
  const batchFailureMessage =
    batch?.status === "failed"
      ? batch.errore ?? "Il batch di import e terminato in errore."
      : null;
  const previewAnomalie = useMemo<PreviewAnomalia[]>(() => {
    if (!reportJson || typeof reportJson !== "object") return [];
    const value = (reportJson as Record<string, unknown>)["preview_anomalie"];
    return Array.isArray(value) ? (value as PreviewAnomalia[]).slice(0, 50) : [];
  }, [reportJson]);

  const anomalieCounters = useMemo(() => {
    if (!reportJson || typeof reportJson !== "object") return [];
    const anomalies = (reportJson as Record<string, unknown>)["anomalie"];
    if (!anomalies || typeof anomalies !== "object") return [];
    return Object.entries(anomalies as Record<string, unknown>)
      .map(([tipo, payload]) => {
        const count =
          payload && typeof payload === "object" && "count" in payload ? safeNumber((payload as Record<string, unknown>).count) : 0;
        return { tipo, count };
      })
      .sort((a, b) => b.count - a.count);
  }, [reportJson]);
  const reportSummary = useMemo(() => {
    if (!reportJson || typeof reportJson !== "object") return null;
    const payload = reportJson as Record<string, unknown>;
    return {
      annoCampagna: safeNumber(payload["anno_campagna"]) || null,
      righeTotali: safeNumber(payload["righe_totali"]),
      righeImportate: safeNumber(payload["righe_importate"]),
      righeConAnomalie: safeNumber(payload["righe_con_anomalie"]),
      distrettiRilevati: safeStringArray(payload["distretti_rilevati"]).length
        ? safeStringArray(payload["distretti_rilevati"])
        : Array.isArray(payload["distretti_rilevati"])
          ? (payload["distretti_rilevati"] as unknown[]).map((item) => String(item))
          : [],
      comuniRilevati: safeStringArray(payload["comuni_rilevati"]),
    };
  }, [reportJson]);

  async function startUpload(): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) {
      setError("Sessione non disponibile o scaduta. Accedi di nuovo.");
      return;
    }
    if (!file) return;

    setBusy(true);
    setError(null);
    setUploadProgress(0);
    try {
      const result =
        importType === "shapefile"
          ? await catastoUploadShapefile(token, file, {
              sourceSrid,
              onProgress: (p) => setUploadProgress(p),
            })
          : await catastoUploadCapacitas(token, file, {
              force,
              onProgress: (p) => setUploadProgress(p),
            });
      setBatchId(result.batch_id);
      setBatch(null);
      setReport(null);
      setReportTipo("");
      setReportPage(1);
      setStep("progress");
    } catch (e) {
      if (isAuthError(e)) {
        setError(
          e.status === 403
            ? "Permessi insufficienti: l’import richiede ruolo admin/super_admin."
            : "Sessione scaduta o non valida. Accedi di nuovo e riprova.",
        );
      } else if (e instanceof ApiError) {
        setError(e.message);
      } else {
        setError(e instanceof Error ? e.message : "Errore upload");
      }
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    async function poll(): Promise<void> {
      const token = getStoredAccessToken();
      if (!token) return;
      if (!batchId) return;

      try {
        const status = await catastoGetImportStatus(token, batchId);
        setBatch(status);
        setError(null);

        if (status.status === "completed" || status.status === "failed") {
          if (pollTimer.current) {
            window.clearInterval(pollTimer.current);
            pollTimer.current = null;
          }
          setStep("report");
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : "Errore polling");
      }
    }

    if (step !== "progress" || !batchId) return;
    void poll();
    pollTimer.current = window.setInterval(() => void poll(), 2000);
    return () => {
      if (pollTimer.current) {
        window.clearInterval(pollTimer.current);
        pollTimer.current = null;
      }
    };
  }, [batchId, step]);

  useEffect(() => {
    async function loadSummary(): Promise<void> {
      const token = getStoredAccessToken();
      if (!token) return;
      try {
        const payload = await catastoGetImportSummary(token, { tipo: "capacitas_ruolo" });
        setSummary(payload);
      } catch {
        // best-effort summary
      }
    }

    void loadSummary();
  }, []);

  useEffect(() => {
    async function loadHistory(): Promise<void> {
      const token = getStoredAccessToken();
      if (!token) return;
      try {
        const batches = await catastoGetImportHistory(token, {
          status: historyStatus || undefined,
          tipo: "capacitas_ruolo",
          limit: historyLimit,
        });
        setHistory(batches);
      } catch {
        // keep history panel best-effort; primary error surface stays on active flow
      }
    }

    void loadHistory();
  }, [historyLimit, historyStatus]);

  useEffect(() => {
    async function loadReport(): Promise<void> {
      const token = getStoredAccessToken();
      if (!token) return;
      if (!batchId) return;
      if (step !== "report") return;
      try {
        const data = await catastoGetImportReport(token, batchId, {
          tipo: reportTipo || undefined,
          page: reportPage,
          pageSize: 50,
        });
        setReport(data);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Errore caricamento report anomalie");
      }
    }

    void loadReport();
  }, [batchId, reportPage, reportTipo, step]);

  async function reopenBatch(selectedBatch: CatImportBatch): Promise<void> {
    setBatchId(selectedBatch.id);
    setBatch(selectedBatch);
    setReport(null);
    setReportTipo("");
    setReportPage(1);
    setStep("report");
  }

  const shapefileSteps = useMemo<{ ts: string; msg: string }[]>(() => {
    if (!batch?.report_json || typeof batch.report_json !== "object") return [];
    const s = (batch.report_json as Record<string, unknown>)["steps"];
    return Array.isArray(s) ? (s as { ts: string; msg: string }[]) : [];
  }, [batch?.report_json]);

  const uploadPercent = Math.min(100, Math.max(0, uploadProgress));
  const processPercent =
    batch && batch.righe_totali > 0
      ? Math.min(100, Math.round((batch.righe_importate / batch.righe_totali) * 100))
      : 0;

  return (
    <>
      {busy ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="w-full max-w-sm rounded-2xl bg-white p-8 shadow-2xl">
            <p className="text-sm font-semibold text-gray-900">
              {importType === "shapefile" ? "Caricamento shapefile…" : "Caricamento Excel…"}
            </p>
            <p className="mt-1 truncate text-sm text-gray-400">{file?.name ?? ""}</p>
            <div className="mt-6">
              <div className="h-2.5 w-full overflow-hidden rounded-full bg-gray-100">
                <div
                  className="h-full rounded-full bg-[#1D4E35] transition-all duration-300"
                  style={{ width: `${uploadPercent}%` }}
                />
              </div>
              <p className="mt-2 text-right text-sm font-semibold tabular-nums text-gray-700">
                {uploadPercent}%
              </p>
            </div>
            <p className="mt-4 text-center text-xs text-gray-400">
              Al termine il sistema elaborerà i dati in background
            </p>
          </div>
        </div>
      ) : null}
    <CatastoPage
      title="Import"
      description="Wizard import Capacitas (Ruoli) con polling stato e report anomalie."
      breadcrumb="Catasto / Import"
      requiredModule="catasto"
      requiredRoles={["admin", "super_admin"]}
    >
      <div className="page-stack">
        {error ? (
          <AlertBanner variant="danger" title="Errore">
            {error}
          </AlertBanner>
        ) : null}
        {batchFailureMessage ? (
          <AlertBanner variant="danger" title="Import fallito">
            {batchFailureMessage}
          </AlertBanner>
        ) : null}

        <div className="grid gap-4 md:grid-cols-3">
          <article className={`panel-card ${step === "upload" ? "ring-2 ring-[#1D4E35]/15" : ""}`}>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-gray-400">Step 1</p>
            <p className="mt-2 text-sm font-medium text-gray-900">Upload</p>
            <p className="mt-1 text-sm text-gray-500">Carica l’Excel Capacitas “Ruoli …”.</p>
          </article>
          <article className={`panel-card ${step === "progress" ? "ring-2 ring-[#1D4E35]/15" : ""}`}>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-gray-400">Step 2</p>
            <p className="mt-2 text-sm font-medium text-gray-900">Progress</p>
            <p className="mt-1 text-sm text-gray-500">Polling ogni 2s fino a completamento.</p>
          </article>
          <article className={`panel-card ${step === "report" ? "ring-2 ring-[#1D4E35]/15" : ""}`}>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-gray-400">Step 3</p>
            <p className="mt-2 text-sm font-medium text-gray-900">Report</p>
            <p className="mt-1 text-sm text-gray-500">Contatori e lista anomalie.</p>
          </article>
        </div>

        <article className="panel-card">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-sm font-medium text-gray-900">Audit import</p>
              <p className="mt-1 text-sm text-gray-500">Snapshot operativo dei batch Capacitas registrati.</p>
            </div>
          </div>

          {!summary ? (
            <div className="mt-4">
              <EmptyState icon={SearchIcon} title="Audit non disponibile" description="Il backend non ha restituito un riepilogo dei batch import." />
            </div>
          ) : (
            <>
              <div className="mt-4 grid gap-3 md:grid-cols-4">
                <div className="rounded-xl border border-gray-100 bg-white p-4">
                  <p className="text-xs uppercase tracking-wide text-gray-400">Batch totali</p>
                  <p className="mt-1 text-lg font-semibold text-gray-900">{summary.totale_batch}</p>
                </div>
                <div className="rounded-xl border border-gray-100 bg-white p-4">
                  <p className="text-xs uppercase tracking-wide text-gray-400">Processing</p>
                  <p className="mt-1 text-lg font-semibold text-gray-900">{summary.processing_batch}</p>
                </div>
                <div className="rounded-xl border border-gray-100 bg-white p-4">
                  <p className="text-xs uppercase tracking-wide text-gray-400">Completed</p>
                  <p className="mt-1 text-lg font-semibold text-gray-900">{summary.completed_batch}</p>
                </div>
                <div className="rounded-xl border border-gray-100 bg-white p-4">
                  <p className="text-xs uppercase tracking-wide text-gray-400">Failed</p>
                  <p className="mt-1 text-lg font-semibold text-gray-900">{summary.failed_batch}</p>
                </div>
              </div>
              <div className="mt-4 rounded-xl border border-gray-100 bg-white p-4">
                <p className="text-xs uppercase tracking-wide text-gray-400">Ultimo completato</p>
                <p className="mt-1 text-sm font-medium text-gray-900">{formatDateTime(summary.ultimo_completed_at)}</p>
              </div>
            </>
          )}
        </article>

        <article className="panel-card">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-sm font-medium text-gray-900">Storico import recenti</p>
              <p className="mt-1 text-sm text-gray-500">Ultimi batch Capacitas eseguiti dal modulo Catasto.</p>
            </div>
            <p className="text-sm text-gray-500">{history.length} batch</p>
          </div>

          <div className="mt-4 grid gap-3 md:grid-cols-2">
            <label className="text-sm font-medium text-gray-700">
              Stato
              <select className="form-control mt-1" value={historyStatus} onChange={(e) => setHistoryStatus(e.target.value)}>
                <option value="">Tutti</option>
                <option value="processing">Processing</option>
                <option value="completed">Completed</option>
                <option value="failed">Failed</option>
                <option value="replaced">Replaced</option>
              </select>
            </label>
            <label className="text-sm font-medium text-gray-700">
              Limite
              <select className="form-control mt-1" value={String(historyLimit)} onChange={(e) => setHistoryLimit(Number(e.target.value))}>
                <option value="5">5</option>
                <option value="10">10</option>
                <option value="20">20</option>
              </select>
            </label>
          </div>

          {history.length === 0 ? (
            <div className="mt-4">
              <EmptyState icon={SearchIcon} title="Nessuno storico disponibile" description="Non risultano import recenti per il modulo Catasto." />
            </div>
          ) : (
            <div className="mt-4 overflow-x-auto">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Creato</th>
                    <th>File</th>
                    <th>Stato</th>
                    <th>Importate</th>
                    <th>Anomalie</th>
                    <th>Azioni</th>
                  </tr>
                </thead>
                <tbody>
                  {history.map((item) => (
                    <tr key={item.id}>
                      <td className="text-sm text-gray-600">{formatDateTime(item.created_at)}</td>
                      <td className="text-sm font-medium text-gray-900">{item.filename}</td>
                      <td>
                        <ImportStatusBadge status={item.status} />
                      </td>
                      <td className="text-sm text-gray-600">{item.righe_importate}</td>
                      <td className="text-sm text-gray-600">{item.righe_anomalie}</td>
                      <td>
                        <div className="flex flex-wrap gap-2">
                          <button
                            type="button"
                            className="btn-secondary"
                            onClick={() => void reopenBatch(item)}
                          >
                            Apri report
                          </button>
                          <Link className="btn-secondary" href={`/catasto/import/${item.id}`}>
                            Dettaglio
                          </Link>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </article>

        {step === "upload" ? (
          <article className="panel-card">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-sm font-medium text-gray-900">Carica file</p>
                <p className="mt-1 text-sm text-gray-500">Solo admin/super admin.</p>
              </div>
            </div>

            <div className="mt-4 flex gap-1 rounded-xl border border-gray-100 bg-gray-50 p-1">
              <button
                type="button"
                className={`flex-1 rounded-lg px-4 py-2 text-sm font-medium transition ${importType === "capacitas" ? "bg-white text-gray-900 shadow-sm" : "text-gray-500 hover:text-gray-700"}`}
                onClick={() => { setImportType("capacitas"); setFile(null); }}
              >
                Capacitas (Excel)
              </button>
              <button
                type="button"
                className={`flex-1 rounded-lg px-4 py-2 text-sm font-medium transition ${importType === "shapefile" ? "bg-white text-gray-900 shadow-sm" : "text-gray-500 hover:text-gray-700"}`}
                onClick={() => { setImportType("shapefile"); setFile(null); }}
              >
                Catasto (Shapefile ZIP)
              </button>
            </div>

            {importType === "capacitas" ? (
              <div className="mt-4 grid gap-4 md:grid-cols-2">
                <label className="text-sm font-medium text-gray-700">
                  File Excel
                  <input
                    className="form-control mt-1"
                    type="file"
                    accept=".xlsx,.xls"
                    onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                  />
                </label>
                <label className="flex items-center gap-2 rounded-xl border border-gray-100 bg-white px-4 py-3 text-sm text-gray-700">
                  <input type="checkbox" checked={force} onChange={(e) => setForce(e.target.checked)} />
                  Force re-import (sostituisce batch precedente con stesso hash)
                </label>
              </div>
            ) : (
              <div className="mt-4 grid gap-4 md:grid-cols-2">
                <label className="text-sm font-medium text-gray-700">
                  Archivio ZIP
                  <input
                    className="form-control mt-1"
                    type="file"
                    accept=".zip"
                    onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                  />
                  <p className="mt-1 text-xs text-gray-400">ZIP contenente .shp, .dbf e .shx</p>
                </label>
                <label className="text-sm font-medium text-gray-700">
                  SRID sorgente
                  <select className="form-control mt-1" value={String(sourceSrid)} onChange={(e) => setSourceSrid(Number(e.target.value))}>
                    <option value="4326">4326 — WGS 84 (default)</option>
                    <option value="3003">3003 — Monte Mario / Italy zone 1</option>
                    <option value="32632">32632 — WGS 84 / UTM zone 32N</option>
                    <option value="6707">6707 — RDN2008 / Italy zone 12</option>
                  </select>
                </label>
              </div>
            )}

            <div className="mt-4 flex flex-wrap items-center gap-3">
              <button className="btn-primary" type="button" disabled={busy || !file} onClick={() => void startUpload()}>
                <RefreshIcon className="h-4 w-4" />
                {busy ? "Upload…" : "Avvia import"}
              </button>
              <p className="text-sm text-gray-500">Upload: {uploadProgress}%</p>
            </div>
          </article>
        ) : null}

        {step === "progress" ? (
          <article className="panel-card">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-sm font-medium text-gray-900">Elaborazione in corso</p>
                <p className="mt-1 truncate text-sm text-gray-500">{batch?.filename ?? batchId ?? "—"}</p>
              </div>
              {batch ? <ImportStatusBadge status={batch.status} /> : null}
            </div>

            {!batch ? (
              <div className="mt-4 rounded-xl border border-gray-100 bg-gray-50 p-4 text-sm text-gray-500">
                Caricamento stato…
              </div>
            ) : (
              <>
                <div className="mt-5">
                  <div className="flex items-baseline justify-between gap-2">
                    <p className="text-xs font-medium uppercase tracking-wide text-gray-400">
                      Particelle elaborate
                    </p>
                    <p className="tabular-nums text-sm font-semibold text-gray-800">
                      {batch.righe_importate.toLocaleString("it-IT")}
                      {batch.righe_totali > 0 ? (
                        <span className="font-normal text-gray-400">
                          {" "}/ {batch.righe_totali.toLocaleString("it-IT")}
                        </span>
                      ) : null}
                    </p>
                  </div>
                  <div className="mt-2 h-2.5 w-full overflow-hidden rounded-full bg-gray-100">
                    <div
                      className="h-full rounded-full bg-[#1D4E35] transition-all duration-500"
                      style={{ width: batch.righe_totali > 0 ? `${processPercent}%` : "0%" }}
                    />
                  </div>
                  {batch.righe_totali > 0 ? (
                    <p className="mt-1 text-right text-xs text-gray-400">{processPercent}%</p>
                  ) : null}
                </div>

                {shapefileSteps.length > 0 ? (
                  <div className="mt-5">
                    <p className="text-xs font-medium uppercase tracking-wide text-gray-400">
                      Log operazioni
                    </p>
                    <div className="mt-2 max-h-56 overflow-y-auto rounded-xl border border-gray-100 bg-gray-50 p-3 font-mono text-xs leading-relaxed text-gray-600">
                      {shapefileSteps.map((s, i) => (
                        <div key={i} className="flex gap-2">
                          <span className="shrink-0 text-gray-400">{s.ts}</span>
                          <span>{s.msg}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : null}

                <div className="mt-4 grid gap-3 md:grid-cols-3">
                  <div className="rounded-xl border border-gray-100 bg-white p-4">
                    <p className="text-xs uppercase tracking-wide text-gray-400">Totale righe</p>
                    <p className="mt-1 text-lg font-semibold text-gray-900">
                      {batch.righe_totali.toLocaleString("it-IT")}
                    </p>
                  </div>
                  <div className="rounded-xl border border-gray-100 bg-white p-4">
                    <p className="text-xs uppercase tracking-wide text-gray-400">Elaborate</p>
                    <p className="mt-1 text-lg font-semibold text-gray-900">
                      {batch.righe_importate.toLocaleString("it-IT")}
                    </p>
                  </div>
                  <div className="rounded-xl border border-gray-100 bg-white p-4">
                    <p className="text-xs uppercase tracking-wide text-gray-400">Anomalie</p>
                    <p className="mt-1 text-lg font-semibold text-gray-900">{batch.righe_anomalie}</p>
                  </div>
                </div>
              </>
            )}
          </article>
        ) : null}

        {step === "report" && batch?.tipo === "shapefile" ? (
          <article className="panel-card">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-sm font-medium text-gray-900">Risultato import shapefile</p>
                <p className="mt-1 text-sm text-gray-500">{batch.filename}</p>
              </div>
              <ImportStatusBadge status={batch.status} />
            </div>
            <div className="mt-4 grid gap-3 md:grid-cols-4">
              <div className="rounded-xl border border-gray-100 bg-white p-4">
                <p className="text-xs uppercase tracking-wide text-gray-400">Righe staging</p>
                <p className="mt-1 text-lg font-semibold text-gray-900">
                  {safeNumber((batch.report_json as Record<string, unknown> | null)?.["righe_staging"])}
                </p>
              </div>
              <div className="rounded-xl border border-gray-100 bg-white p-4">
                <p className="text-xs uppercase tracking-wide text-gray-400">Particelle inserite</p>
                <p className="mt-1 text-lg font-semibold text-gray-900">
                  {safeNumber((batch.report_json as Record<string, unknown> | null)?.["records_inserted_current"])}
                </p>
              </div>
              <div className="rounded-xl border border-gray-100 bg-white p-4">
                <p className="text-xs uppercase tracking-wide text-gray-400">Storico aggiornato</p>
                <p className="mt-1 text-lg font-semibold text-gray-900">
                  {safeNumber((batch.report_json as Record<string, unknown> | null)?.["records_history_written"])}
                </p>
              </div>
              <div className="rounded-xl border border-gray-100 bg-white p-4">
                <p className="text-xs uppercase tracking-wide text-gray-400">Distretti upserted</p>
                <p className="mt-1 text-lg font-semibold text-gray-900">
                  {safeNumber((batch.report_json as Record<string, unknown> | null)?.["distretti_upserted"])}
                </p>
              </div>
            </div>
            <div className="mt-3 flex">
              <button
                type="button"
                className="btn-secondary"
                onClick={() => { setStep("upload"); setFile(null); }}
              >
                Nuovo import
              </button>
            </div>
          </article>
        ) : null}

        {step === "report" && batch?.tipo !== "shapefile" ? (
          <div className="grid gap-6 xl:grid-cols-2">
            <article className="panel-card xl:col-span-2">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-sm font-medium text-gray-900">Sintesi batch</p>
                  <p className="mt-1 text-sm text-gray-500">Metadati principali estratti da `report_json`.</p>
                </div>
                {batch ? <ImportStatusBadge status={batch.status} /> : null}
              </div>

              {!reportSummary ? (
                <div className="mt-4">
                  <EmptyState icon={SearchIcon} title="Sintesi non disponibile" description="Il backend non ha prodotto metadati di riepilogo per questo batch." />
                </div>
              ) : (
                <>
                  <div className="mt-4 grid gap-3 md:grid-cols-4">
                    <div className="rounded-xl border border-gray-100 bg-white p-4">
                      <p className="text-xs uppercase tracking-wide text-gray-400">Anno campagna</p>
                      <p className="mt-1 text-lg font-semibold text-gray-900">{reportSummary.annoCampagna ?? "—"}</p>
                    </div>
                    <div className="rounded-xl border border-gray-100 bg-white p-4">
                      <p className="text-xs uppercase tracking-wide text-gray-400">Righe totali</p>
                      <p className="mt-1 text-lg font-semibold text-gray-900">{reportSummary.righeTotali}</p>
                    </div>
                    <div className="rounded-xl border border-gray-100 bg-white p-4">
                      <p className="text-xs uppercase tracking-wide text-gray-400">Righe importate</p>
                      <p className="mt-1 text-lg font-semibold text-gray-900">{reportSummary.righeImportate}</p>
                    </div>
                    <div className="rounded-xl border border-gray-100 bg-white p-4">
                      <p className="text-xs uppercase tracking-wide text-gray-400">Con anomalie</p>
                      <p className="mt-1 text-lg font-semibold text-gray-900">{reportSummary.righeConAnomalie}</p>
                    </div>
                  </div>

                  <div className="mt-4 grid gap-4 md:grid-cols-2">
                    <div className="rounded-xl border border-gray-100 bg-white p-4">
                      <p className="text-xs uppercase tracking-wide text-gray-400">Distretti rilevati</p>
                      <p className="mt-2 text-sm text-gray-700">
                        {reportSummary.distrettiRilevati.length ? reportSummary.distrettiRilevati.join(", ") : "—"}
                      </p>
                    </div>
                    <div className="rounded-xl border border-gray-100 bg-white p-4">
                      <p className="text-xs uppercase tracking-wide text-gray-400">Comuni rilevati</p>
                      <p className="mt-2 text-sm text-gray-700">
                        {reportSummary.comuniRilevati.length ? reportSummary.comuniRilevati.join(", ") : "—"}
                      </p>
                    </div>
                  </div>
                </>
              )}
            </article>

            <article className="panel-card">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-sm font-medium text-gray-900">Contatori anomalie</p>
                  <p className="mt-1 text-sm text-gray-500">Da `batch.report_json.anomalie`.</p>
                </div>
                {batch ? <ImportStatusBadge status={batch.status} /> : null}
              </div>

              {anomalieCounters.length === 0 ? (
                <div className="mt-4">
                  <EmptyState icon={SearchIcon} title="Nessun contatore disponibile" description="Il report JSON non contiene contatori anomalie o non è stato generato." />
                </div>
              ) : (
                <div className="mt-4 space-y-2">
                  {anomalieCounters.map((c) => (
                    <button
                      key={c.tipo}
                      type="button"
                      className={`flex w-full items-center justify-between rounded-xl border px-4 py-3 text-left transition ${
                        reportTipo === c.tipo ? "border-[#1D4E35] bg-[#eef6f0]" : "border-gray-100 bg-white hover:border-gray-200"
                      }`}
                      onClick={() => {
                        setReportTipo(c.tipo);
                        setReportPage(1);
                      }}
                    >
                      <span className="text-sm font-medium text-gray-900">{c.tipo}</span>
                      <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600">{c.count}</span>
                    </button>
                  ))}
                  <button
                    type="button"
                    className="btn-secondary mt-2"
                    onClick={() => {
                      setReportTipo("");
                      setReportPage(1);
                    }}
                  >
                    Mostra tutte
                  </button>
                </div>
              )}
            </article>

            <article className="panel-card">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-sm font-medium text-gray-900">Preview (prime 50)</p>
                  <p className="mt-1 text-sm text-gray-500">Da `report_json.preview_anomalie`.</p>
                </div>
                <DocumentIcon className="h-5 w-5 text-gray-400" />
              </div>

              {previewAnomalie.length === 0 ? (
                <div className="mt-4">
                  <EmptyState icon={SearchIcon} title="Nessuna preview" description="Non ci sono anomalie in preview o il backend non ha popolato la lista." />
                </div>
              ) : (
                <div className="mt-4 overflow-x-auto">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Riga</th>
                        <th>Tipo</th>
                        <th>Dettagli</th>
                      </tr>
                    </thead>
                    <tbody>
                      {previewAnomalie.map((a, idx) => (
                        <tr key={idx}>
                          <td>{safeNumber(a.riga) || "—"}</td>
                          <td className="font-medium text-gray-900">{safeString(a.tipo) || "—"}</td>
                          <td className="text-sm text-gray-600">
                            {Object.entries(a)
                              .filter(([k]) => k !== "riga" && k !== "tipo")
                              .slice(0, 3)
                              .map(([k, v]) => `${k}=${typeof v === "string" ? v : JSON.stringify(v)}`)
                              .join(" · ") || "—"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </article>

            <article className="panel-card xl:col-span-2">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-sm font-medium text-gray-900">Lista anomalie</p>
                  <p className="mt-1 text-sm text-gray-500">
                    Filtro tipo: <span className="font-medium text-gray-800">{reportTipo || "tutti"}</span>
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <button className="btn-secondary" type="button" disabled={reportPage <= 1} onClick={() => setReportPage((p) => Math.max(1, p - 1))}>
                    Prev
                  </button>
                  <button className="btn-secondary" type="button" onClick={() => setReportPage((p) => p + 1)}>
                    Next
                  </button>
                </div>
              </div>

              {!report ? (
                <div className="mt-4 rounded-xl border border-gray-100 bg-gray-50 p-4 text-sm text-gray-500">Caricamento lista anomalie…</div>
              ) : report.items.length === 0 ? (
                <div className="mt-4">
                  <EmptyState icon={SearchIcon} title="Nessuna anomalia" description="Non ci sono anomalie per i filtri correnti." />
                </div>
              ) : (
                <div className="mt-4 overflow-x-auto">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Severità</th>
                        <th>Tipo</th>
                        <th>Descrizione</th>
                        <th>Anno</th>
                      </tr>
                    </thead>
                    <tbody>
                      {report.items.map((item) => (
                        <tr key={item.id}>
                          <td>
                            <AnomaliaStatusBadge severita={item.severita} />
                          </td>
                          <td className="text-sm font-medium text-gray-900">{item.tipo}</td>
                          <td className="text-sm text-gray-600">{item.descrizione ?? "—"}</td>
                          <td className="text-sm text-gray-600">{item.anno_campagna ?? "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </article>
          </div>
        ) : null}
      </div>
    </CatastoPage>
    </>
  );
}

