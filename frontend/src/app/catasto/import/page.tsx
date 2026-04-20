"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import { ProtectedPage } from "@/components/app/protected-page";
import { CatastoPhase1Nav } from "@/components/catasto/phase1-nav";
import { ImportStatusBadge } from "@/components/catasto/ImportStatusBadge";
import { AnomaliaStatusBadge } from "@/components/catasto/AnomaliaStatusBadge";
import { AlertBanner } from "@/components/ui/alert-banner";
import { EmptyState } from "@/components/ui/empty-state";
import { RefreshIcon, DocumentIcon, SearchIcon } from "@/components/ui/icons";
import {
  catastoGetImportReport,
  catastoGetImportStatus,
  catastoUploadCapacitas,
} from "@/lib/api/catasto";
import { getStoredAccessToken } from "@/lib/auth";
import type { CatAnomaliaListResponse, CatImportBatch, UUID } from "@/types/catasto";

type StepKey = "upload" | "progress" | "report";

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

export default function CatastoImportPage() {
  const [step, setStep] = useState<StepKey>("upload");
  const [file, setFile] = useState<File | null>(null);
  const [force, setForce] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);

  const [batchId, setBatchId] = useState<UUID | null>(null);
  const [batch, setBatch] = useState<CatImportBatch | null>(null);
  const [reportTipo, setReportTipo] = useState<string>("");
  const [reportPage, setReportPage] = useState(1);
  const [report, setReport] = useState<CatAnomaliaListResponse | null>(null);

  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const pollTimer = useRef<number | null>(null);

  const reportJson = batch?.report_json ?? null;
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

  async function startUpload(): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) return;
    if (!file) return;

    setBusy(true);
    setError(null);
    setUploadProgress(0);
    try {
      const result = await catastoUploadCapacitas(token, file, {
        force,
        onProgress: (p) => setUploadProgress(p),
      });
      setBatchId(result.batch_id);
      setStep("progress");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Errore upload");
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

  return (
    <ProtectedPage
      title="Import"
      description="Wizard import Capacitas (Ruoli) con polling stato e report anomalie."
      breadcrumb="Catasto / Import"
      requiredModule="catasto"
      requiredRoles={["admin", "super_admin"]}
    >
      <div className="page-stack">
        <CatastoPhase1Nav />

        {error ? (
          <AlertBanner variant="danger" title="Errore">
            {error}
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

        {step === "upload" ? (
          <article className="panel-card">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-sm font-medium text-gray-900">Carica file</p>
                <p className="mt-1 text-sm text-gray-500">Solo admin/super admin.</p>
              </div>
            </div>
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

            <div className="mt-4 flex flex-wrap items-center gap-3">
              <button className="btn-primary" type="button" disabled={busy || !file} onClick={() => void startUpload()}>
                <RefreshIcon className="h-4 w-4" />
                {busy ? "Upload…" : "Avvia import"}
              </button>
              <p className="text-sm text-gray-500">
                Upload: {uploadProgress}%
              </p>
            </div>
          </article>
        ) : null}

        {step === "progress" ? (
          <article className="panel-card">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-sm font-medium text-gray-900">Stato import</p>
                <p className="mt-1 text-sm text-gray-500">Batch: {batchId ?? "—"}</p>
              </div>
              {batch ? <ImportStatusBadge status={batch.status} /> : null}
            </div>

            {!batch ? (
              <div className="mt-4 rounded-xl border border-gray-100 bg-gray-50 p-4 text-sm text-gray-500">Caricamento stato…</div>
            ) : (
              <div className="mt-4 grid gap-3 md:grid-cols-4">
                <div className="rounded-xl border border-gray-100 bg-white p-4">
                  <p className="text-xs uppercase tracking-wide text-gray-400">Righe totali</p>
                  <p className="mt-1 text-lg font-semibold text-gray-900">{batch.righe_totali}</p>
                </div>
                <div className="rounded-xl border border-gray-100 bg-white p-4">
                  <p className="text-xs uppercase tracking-wide text-gray-400">Importate</p>
                  <p className="mt-1 text-lg font-semibold text-gray-900">{batch.righe_importate}</p>
                </div>
                <div className="rounded-xl border border-gray-100 bg-white p-4">
                  <p className="text-xs uppercase tracking-wide text-gray-400">Con anomalie</p>
                  <p className="mt-1 text-lg font-semibold text-gray-900">{batch.righe_anomalie}</p>
                </div>
                <div className="rounded-xl border border-gray-100 bg-white p-4">
                  <p className="text-xs uppercase tracking-wide text-gray-400">File</p>
                  <p className="mt-1 truncate text-sm font-medium text-gray-900">{batch.filename}</p>
                </div>
              </div>
            )}
          </article>
        ) : null}

        {step === "report" ? (
          <div className="grid gap-6 xl:grid-cols-2">
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
    </ProtectedPage>
  );
}

