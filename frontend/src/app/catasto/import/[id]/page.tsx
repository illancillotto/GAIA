"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { AnomaliaStatusBadge } from "@/components/catasto/AnomaliaStatusBadge";
import { CatastoPage } from "@/components/catasto/catasto-page";
import { ImportStatusBadge } from "@/components/catasto/ImportStatusBadge";
import { AlertBanner } from "@/components/ui/alert-banner";
import { EmptyState } from "@/components/ui/empty-state";
import { MetricCard } from "@/components/ui/metric-card";
import { DocumentIcon, SearchIcon } from "@/components/ui/icons";
import { catastoGetImportReport, catastoGetImportStatus } from "@/lib/api/catasto";
import { getStoredAccessToken } from "@/lib/auth";
import type { CatAnomaliaListResponse, CatImportBatch } from "@/types/catasto";

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

export default function CatastoImportDetailPage() {
  const params = useParams<{ id: string }>();
  const batchId = params.id;

  const [batch, setBatch] = useState<CatImportBatch | null>(null);
  const [reportTipo, setReportTipo] = useState<string>("");
  const [reportPage, setReportPage] = useState(1);
  const [report, setReport] = useState<CatAnomaliaListResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

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

  useEffect(() => {
    async function loadBatch(): Promise<void> {
      const token = getStoredAccessToken();
      if (!token) return;
      try {
        const payload = await catastoGetImportStatus(token, batchId);
        setBatch(payload);
        setError(null);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Errore caricamento batch");
      }
    }

    void loadBatch();
  }, [batchId]);

  useEffect(() => {
    async function loadReport(): Promise<void> {
      const token = getStoredAccessToken();
      if (!token) return;
      try {
        const payload = await catastoGetImportReport(token, batchId, {
          tipo: reportTipo || undefined,
          page: reportPage,
          pageSize: 50,
        });
        setReport(payload);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Errore caricamento report batch");
      }
    }

    void loadReport();
  }, [batchId, reportPage, reportTipo]);

  return (
    <CatastoPage
      title="Dettaglio import"
      description="Vista dedicata di un batch import Catasto con metadati, contatori e anomalie."
      breadcrumb="Catasto / Import / Dettaglio"
      requiredModule="catasto"
      requiredRoles={["admin", "super_admin"]}
    >
      <div className="page-stack">
        {error ? (
          <AlertBanner variant="danger" title="Errore caricamento">
            {error}
          </AlertBanner>
        ) : null}

        <article className="panel-card">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <p className="text-sm font-medium text-gray-900">Batch import</p>
              <p className="mt-1 text-sm text-gray-500">{batch?.filename ?? "Caricamento…"}</p>
            </div>
            {batch ? <ImportStatusBadge status={batch.status} /> : null}
          </div>

          <div className="mt-4 grid gap-3 md:grid-cols-4">
            <MetricCard label="Creato" value={formatDateTime(batch?.created_at ?? null)} />
            <MetricCard label="Completato" value={formatDateTime(batch?.completed_at ?? null)} />
            <MetricCard label="Importate" value={batch?.righe_importate ?? "—"} />
            <MetricCard label="Anomalie" value={batch?.righe_anomalie ?? "—"} />
          </div>
        </article>

        <article className="panel-card">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-sm font-medium text-gray-900">Sintesi batch</p>
              <p className="mt-1 text-sm text-gray-500">Snapshot da `report_json` del batch selezionato.</p>
            </div>
            <Link className="text-sm font-medium text-[#1D4E35] underline underline-offset-2" href="/catasto/import">
              Torna allo storico import
            </Link>
          </div>

          {!reportSummary ? (
            <div className="mt-4">
              <EmptyState icon={SearchIcon} title="Sintesi non disponibile" description="Il batch non contiene metadati di riepilogo nel report JSON." />
            </div>
          ) : (
            <>
              <div className="mt-4 grid gap-3 md:grid-cols-4">
                <MetricCard label="Anno campagna" value={reportSummary.annoCampagna ?? "—"} />
                <MetricCard label="Righe totali" value={reportSummary.righeTotali} />
                <MetricCard label="Righe importate" value={reportSummary.righeImportate} />
                <MetricCard label="Con anomalie" value={reportSummary.righeConAnomalie} />
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

        <div className="grid gap-6 xl:grid-cols-2">
          <article className="panel-card">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-sm font-medium text-gray-900">Contatori anomalie</p>
                <p className="mt-1 text-sm text-gray-500">Filtra il report per tipo anomalia.</p>
              </div>
              {batch ? <ImportStatusBadge status={batch.status} /> : null}
            </div>

            {anomalieCounters.length === 0 ? (
              <div className="mt-4">
                <EmptyState icon={SearchIcon} title="Nessun contatore disponibile" description="Il batch non espone contatori anomalie." />
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
              </div>
            )}
          </article>

          <article className="panel-card">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-sm font-medium text-gray-900">Preview (prime 50)</p>
                <p className="mt-1 text-sm text-gray-500">Estratto dal report JSON del batch.</p>
              </div>
              <DocumentIcon className="h-5 w-5 text-gray-400" />
            </div>

            {previewAnomalie.length === 0 ? (
              <div className="mt-4">
                <EmptyState icon={SearchIcon} title="Nessuna preview" description="Il batch non contiene anomalie in preview." />
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
        </div>

        <article className="panel-card">
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
    </CatastoPage>
  );
}
