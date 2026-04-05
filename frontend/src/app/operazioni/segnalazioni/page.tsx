"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { OperazioniModulePage } from "@/components/operazioni/operazioni-module-page";
import { MetricCard } from "@/components/ui/metric-card";
import { EmptyState } from "@/components/ui/empty-state";
import { AlertTriangleIcon, ChevronRightIcon } from "@/components/ui/icons";
import { getReports } from "@/features/operazioni/api/client";

function BadgeCount({ value }: { value: number }) {
  return (
    <span className="rounded-full bg-[#EAF3E8] px-2.5 py-1 text-xs font-semibold text-[#1D4E35]">
      {value}
    </span>
  );
}

function SegnalazioniContent({ token }: { token: string }) {
  const [reports, setReports] = useState<Record<string, unknown>[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    try {
      const data = await getReports({ page_size: "50" });
      setReports(data.items ?? []);
      setTotal(data.total ?? 0);
      setLoadError(null);
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : "Errore nel caricamento segnalazioni");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  return (
    <div className="page-stack">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-gray-500">
          Segnalazioni dal campo con generazione automatica di pratiche interne per il tracciamento.
        </p>
      </div>

      {loadError ? (
        <article className="panel-card">
          <p className="text-sm font-medium text-red-700">Caricamento non riuscito</p>
          <p className="mt-2 text-sm text-gray-600">{loadError}</p>
        </article>
      ) : null}

      <div className="surface-grid">
        <MetricCard label="Segnalazioni totali" value={total} sub="Tutte le segnalazioni registrate" />
        <MetricCard label="Con pratica" value={reports.filter((r) => r.internal_case_id).length} sub="Segnalazioni con pratica collegata" variant="success" />
        <MetricCard label="Senza pratica" value={reports.filter((r) => !r.internal_case_id).length} sub="Da collegare a pratica" variant="warning" />
      </div>

      <article className="panel-card">
        <div className="mb-4 flex items-center justify-between gap-3">
          <div>
            <p className="section-title">Elenco segnalazioni</p>
            <p className="section-copy">Tutte le segnalazioni dal campo con stato e dettagli.</p>
          </div>
          <BadgeCount value={reports.length} />
        </div>

        {isLoading ? (
          <p className="text-sm text-gray-500">Caricamento segnalazioni in corso.</p>
        ) : reports.length === 0 ? (
          <EmptyState
            icon={AlertTriangleIcon}
            title="Nessuna segnalazione"
            description="Non risultano segnalazioni registrate."
          />
        ) : (
          <div className="max-h-[32rem] space-y-3 overflow-y-auto pr-1">
            {reports.map((report) => (
              <Link
                key={String(report.id)}
                href={`/operazioni/segnalazioni/${report.id as string}`}
                className="flex w-full items-center justify-between rounded-lg border border-gray-100 px-4 py-3 text-left transition hover:bg-gray-50"
              >
                <div>
                  <p className="text-sm font-medium text-gray-900">{String(report.title ?? "Senza titolo")}</p>
                  <p className="mt-1 text-xs text-gray-500">
                    {String(report.report_number ?? "")}
                    {report.created_at ? ` · ${new Date(report.created_at as string).toLocaleDateString("it-IT")}` : ""}
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${report.status === "linked" ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-700"}`}>
                    {String(report.status ?? "submitted")}
                  </span>
                  <ChevronRightIcon className="h-4 w-4 text-gray-300" />
                </div>
              </Link>
            ))}
          </div>
        )}
      </article>
    </div>
  );
}

export default function SegnalazioniPage() {
  return (
    <OperazioniModulePage
      title="Segnalazioni"
      description="Segnalazioni dal campo e collegamento alle pratiche interne."
      breadcrumb="Lista"
    >
      {({ token }) => <SegnalazioniContent token={token} />}
    </OperazioniModulePage>
  );
}
