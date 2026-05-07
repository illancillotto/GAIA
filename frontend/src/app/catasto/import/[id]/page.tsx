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
import {
  catastoCreateDistrettiExcelGisLayer,
  catastoExportDistrettiExcelBatch,
  catastoGetDistrettiExcelAnalysis,
  catastoGetImportReport,
  catastoGetImportStatus,
} from "@/lib/api/catasto";
import { getStoredAccessToken } from "@/lib/auth";
import type { CatAnomaliaListResponse, CatDistrettiExcelAnalysisItem, CatImportBatch } from "@/types/catasto";

type DistrettoCounter = {
  tipo: string;
  label: string;
  description: string;
  count: number;
  analysisTipo?: string;
};

type DistrettoAnalysisOutcomeMeta = {
  label: string;
  description: string;
};

function safeNumber(value: unknown): number {
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
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

function getDistrettiCounterDefinitions(payload: Record<string, unknown>): DistrettoCounter[] {
  return [
    {
      tipo: "DIST-PARTICELLA-NOT-FOUND",
      label: "Particella non trovata",
      description: "Comune, sezione, foglio e particella sono validi nel file ma non esiste una particella corrente corrispondente in archivio.",
      count: safeNumber(payload["righe_senza_match_particella"]),
      analysisTipo: "NOT_FOUND",
    },
    {
      tipo: "DIST-COMUNE-NOT-FOUND",
      label: "Comune non risolto",
      description: "Il valore del comune nel file non e stato ricondotto a un comune canonico del database.",
      count: safeNumber(payload["righe_scartate_comune_non_risolto"]),
      analysisTipo: "COMUNE_NOT_FOUND",
    },
    {
      tipo: "DIST-ROW-MISSING",
      label: "Campi obbligatori mancanti",
      description: "La riga Excel non contiene uno o piu campi necessari per il match della particella.",
      count: safeNumber(payload["righe_scartate_campi_mancanti"]),
      analysisTipo: "INVALID_ROW",
    },
    {
      tipo: "DIST-DUPLICATE-CONFLICT",
      label: "Duplicati in conflitto",
      description: "Nel file ci sono piu righe per la stessa particella logica ma con distretti diversi.",
      count: safeNumber(payload["righe_duplicate_conflitto"]),
      analysisTipo: "DUPLICATE_CONFLICT",
    },
  ].filter((item) => item.count > 0);
}

function getDistrettiAnalysisOutcomeMeta(esito: string): DistrettoAnalysisOutcomeMeta {
  switch (esito) {
    case "ALREADY_ALIGNED":
      return {
        label: "Gia allineata",
        description: "La particella e stata trovata e il distretto presente in archivio coincide gia con quello del file.",
      };
    case "MATCHED":
      return {
        label: "Da aggiornare",
        description: "La particella e stata trovata, ma il distretto presente in archivio e diverso da quello del file.",
      };
    case "NOT_FOUND":
      return {
        label: "Particella non trovata",
        description: "Comune, sezione, foglio e particella sono validi nel file ma non esiste una particella corrente corrispondente in archivio.",
      };
    case "COMUNE_NOT_FOUND":
      return {
        label: "Comune non risolto",
        description: "Il valore del comune nel file non e stato ricondotto a un comune canonico del database.",
      };
    case "INVALID_ROW":
      return {
        label: "Campi obbligatori mancanti",
        description: "La riga Excel non contiene uno o piu campi necessari per il match della particella.",
      };
    case "DUPLICATE_CONFLICT":
      return {
        label: "Duplicati in conflitto",
        description: "Nel file ci sono piu righe per la stessa particella logica ma con distretti diversi.",
      };
    default:
      return {
        label: esito,
        description: esito,
      };
  }
}

export default function CatastoImportDetailPage() {
  const params = useParams<{ id: string }>();
  const batchId = params.id;

  const [batch, setBatch] = useState<CatImportBatch | null>(null);
  const [reportTipo, setReportTipo] = useState<string>("");
  const [reportPage, setReportPage] = useState(1);
  const [report, setReport] = useState<CatAnomaliaListResponse | null>(null);
  const [distrettiAnalysisItems, setDistrettiAnalysisItems] = useState<CatDistrettiExcelAnalysisItem[]>([]);
  const [distrettiAnalysisTotal, setDistrettiAnalysisTotal] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [actionBusy, setActionBusy] = useState<"export" | "gis" | null>(null);

  const reportJson = batch?.report_json ?? null;
  const anomalieCounters = useMemo<DistrettoCounter[]>(() => {
    if (!reportJson || typeof reportJson !== "object") return [];
    if (batch?.tipo === "distretti_excel") {
      const payload = reportJson as Record<string, unknown>;
      return getDistrettiCounterDefinitions(payload);
    }
    const anomalies = (reportJson as Record<string, unknown>)["anomalie"];
    if (!anomalies || typeof anomalies !== "object") return [];
    return Object.entries(anomalies as Record<string, unknown>)
      .map(([tipo, payload]) => {
        const count =
          payload && typeof payload === "object" && "count" in payload ? safeNumber((payload as Record<string, unknown>).count) : 0;
        return { tipo, label: tipo, description: tipo, count, analysisTipo: undefined };
      })
      .sort((a, b) => b.count - a.count);
  }, [batch?.tipo, reportJson]);

  const selectedCounter = useMemo(() => anomalieCounters.find((item) => item.tipo === reportTipo) ?? null, [anomalieCounters, reportTipo]);

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
    setReportTipo("");
    setReportPage(1);
    setReport(null);
    setDistrettiAnalysisItems([]);
    setDistrettiAnalysisTotal(0);
    setError(null);
  }, [batchId]);

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
    if (!batch) {
      return;
    }

    if (batch?.tipo === "distretti_excel") {
      async function loadDistrettiAnalysis(): Promise<void> {
        const token = getStoredAccessToken();
        if (!token) return;
        try {
          const analysisTipo =
            batch?.tipo === "distretti_excel"
              ? anomalieCounters.find((item) => item.tipo === reportTipo)?.analysisTipo
              : undefined;
          const payload = await catastoGetDistrettiExcelAnalysis(token, batchId, {
            tipo: analysisTipo,
            page: reportPage,
            pageSize: 50,
          });
          setDistrettiAnalysisItems(payload.items);
          setDistrettiAnalysisTotal(payload.total);
          setReport(null);
        } catch (e) {
          setError(e instanceof Error ? e.message : "Errore caricamento analisi distretti Excel");
        }
      }

      void loadDistrettiAnalysis();
      return;
    }

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
        setDistrettiAnalysisItems([]);
        setDistrettiAnalysisTotal(0);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Errore caricamento report batch");
      }
    }

    void loadReport();
  }, [anomalieCounters, batch, batchId, reportPage, reportTipo]);

  async function exportBatchExcel(scope: "all" | "matched" | "without_match" | "unresolved"): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) {
      setError("Sessione non disponibile. Accedi di nuovo.");
      return;
    }
    setActionBusy("export");
    try {
      const blob = await catastoExportDistrettiExcelBatch(token, batchId, scope);
      const url = URL.createObjectURL(blob);
      const anchor = window.document.createElement("a");
      anchor.href = url;
      anchor.download = `${batch?.filename?.replace(/\.(xlsx|xls)$/i, "") ?? "distretti"}_${scope}.xlsx`;
      anchor.click();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Export Excel fallito");
    } finally {
      setActionBusy(null);
    }
  }

  async function openBatchInGis(): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) {
      setError("Sessione non disponibile. Accedi di nuovo.");
      return;
    }
    setActionBusy("gis");
    try {
      const saved = await catastoCreateDistrettiExcelGisLayer(token, batchId);
      window.location.href = `/catasto/gis?selection=${encodeURIComponent(saved.id)}`;
    } catch (e) {
      setError(e instanceof Error ? e.message : "Creazione layer GIS fallita");
      setActionBusy(null);
    }
  }

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
            <div className="flex flex-wrap items-center gap-2">
              {batch?.tipo === "distretti_excel" ? (
                <>
                  <button type="button" className="btn-secondary" disabled={actionBusy !== null} onClick={() => void exportBatchExcel("all")}>
                    {actionBusy === "export" ? "Export…" : "Esporta Excel"}
                  </button>
                  <button type="button" className="btn-secondary" disabled={actionBusy !== null} onClick={() => void openBatchInGis()}>
                    {actionBusy === "gis" ? "Creazione layer…" : "Apri nel GIS"}
                  </button>
                </>
              ) : null}
              {batch ? <ImportStatusBadge status={batch.status} /> : null}
            </div>
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

        <div className="grid gap-6">
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
                    <span>
                      <span className="block text-sm font-medium text-gray-900">{c.label}</span>
                      <span className="mt-0.5 block text-xs text-gray-500">{c.description}</span>
                    </span>
                    <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600">{c.count}</span>
                  </button>
                ))}
              </div>
            )}
          </article>
        </div>

        <article className="panel-card">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <div className="flex items-center gap-2">
                <p className="text-sm font-medium text-gray-900">Anomalie</p>
                <DocumentIcon className="h-5 w-5 text-gray-400" />
              </div>
              <p className="mt-1 text-sm text-gray-500">
                {batch?.tipo === "distretti_excel" ? (
                  <>
                    Per i batch `Distretti Excel` non vengono creati record `CatAnomalia`: qui vedi l&apos;analisi completa del file sorgente.
                    Filtro tipo: <span className="font-medium text-gray-800">{selectedCounter?.label ?? "tutti"}</span>
                  </>
                ) : (
                  <>
                    Filtro tipo: <span className="font-medium text-gray-800">{selectedCounter?.label ?? reportTipo ?? "tutti"}</span>
                  </>
                )}
              </p>
            </div>
            {batch?.tipo === "distretti_excel" ? null : (
              <div className="flex items-center gap-2">
                <button className="btn-secondary" type="button" disabled={reportPage <= 1} onClick={() => setReportPage((p) => Math.max(1, p - 1))}>
                  Prev
                </button>
                <button className="btn-secondary" type="button" onClick={() => setReportPage((p) => p + 1)}>
                  Next
                </button>
              </div>
            )}
            {batch?.tipo === "distretti_excel" ? (
              <div className="flex items-center gap-2">
                <button className="btn-secondary" type="button" disabled={reportPage <= 1} onClick={() => setReportPage((p) => Math.max(1, p - 1))}>
                  Prev
                </button>
                <button
                  className="btn-secondary"
                  type="button"
                  disabled={reportPage * 50 >= distrettiAnalysisTotal}
                  onClick={() => setReportPage((p) => p + 1)}
                >
                  Next
                </button>
                <span className="text-sm text-gray-500">{distrettiAnalysisTotal.toLocaleString("it-IT")} record</span>
              </div>
            ) : null}
          </div>

          {batch?.tipo === "distretti_excel" ? (
            distrettiAnalysisItems.length === 0 ? (
              <div className="mt-4">
                <EmptyState icon={SearchIcon} title="Nessuna anomalia" description="Non ci sono record per i filtri correnti." />
              </div>
            ) : (
              <div className="mt-4 max-h-[32rem] overflow-auto rounded-xl border border-gray-100">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Riga</th>
                      <th>Esito</th>
                      <th>Comune</th>
                      <th>Sezione</th>
                      <th>Foglio</th>
                      <th>Particella</th>
                      <th>Dettagli</th>
                    </tr>
                  </thead>
                  <tbody>
                    {distrettiAnalysisItems.map((item) => (
                      <tr key={`${item.esito}-${item.row_number}-${item.foglio_input}-${item.particella_input}`}>
                        <td className="text-sm text-gray-600">{item.row_number}</td>
                        <td className="text-sm font-medium text-gray-900">{selectedCounter?.label ?? getDistrettiAnalysisOutcomeMeta(item.esito).label}</td>
                        <td className="text-sm text-gray-600">{item.comune_resolved ?? item.comune_input ?? "—"}</td>
                        <td className="text-sm text-gray-600">{item.sezione_resolved ?? item.sezione_input ?? "—"}</td>
                        <td className="text-sm text-gray-600">{item.foglio_input ?? "—"}</td>
                        <td className="text-sm text-gray-600">{item.particella_input ?? "—"}</td>
                        <td className="text-sm text-gray-600">{selectedCounter?.description ?? getDistrettiAnalysisOutcomeMeta(item.esito).description}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )
          ) : !report ? (
            <div className="mt-4 rounded-xl border border-gray-100 bg-gray-50 p-4 text-sm text-gray-500">Caricamento lista anomalie…</div>
          ) : report.items.length === 0 ? (
            <div className="mt-4">
              <EmptyState icon={SearchIcon} title="Nessuna anomalia" description="Non ci sono anomalie per i filtri correnti." />
            </div>
          ) : (
            <div className="mt-4 max-h-[32rem] overflow-auto rounded-xl border border-gray-100">
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
