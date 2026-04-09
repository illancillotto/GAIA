"use client";

import { useCallback, useEffect, useState } from "react";

import {
  OperazioniCollectionHero,
  OperazioniCollectionPanel,
  OperazioniHeroNotice,
  OperazioniList,
  OperazioniListLink,
  OperazioniMetricStrip,
} from "@/components/operazioni/collection-layout";
import { OperazioniModulePage } from "@/components/operazioni/operazioni-module-page";
import { MetricCard } from "@/components/ui/metric-card";
import { EmptyState } from "@/components/ui/empty-state";
import { AlertTriangleIcon } from "@/components/ui/icons";
import { getReports } from "@/features/operazioni/api/client";

function SegnalazioniContent() {
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
      <OperazioniCollectionHero
        eyebrow="Field reports"
        icon={<AlertTriangleIcon className="h-3.5 w-3.5" />}
        title="Gestione segnalazioni dal campo con priorità visiva sul collegamento alle pratiche."
        description="Questa vista evidenzia il volume delle segnalazioni, il legame con le pratiche interne e la necessità di presidio sulle voci ancora scollegate."
      >
        {loadError ? (
          <OperazioniHeroNotice title="Caricamento non riuscito" description={loadError} tone="danger" />
        ) : (
          <OperazioniHeroNotice
            title="Situazione attuale"
            description={`${reports.filter((r) => r.internal_case_id).length} segnalazioni già collegate a pratica, ${reports.filter((r) => !r.internal_case_id).length} ancora da agganciare.`}
          />
        )}
        <div className="rounded-2xl border border-white/80 bg-white/75 px-4 py-3">
          <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-gray-500">Lettura consigliata</p>
          <p className="mt-2 text-sm font-medium text-gray-900">Parti dalle segnalazioni senza pratica</p>
          <p className="mt-1 text-sm text-gray-600">Sono quelle che richiedono la prossima azione amministrativa o tecnica.</p>
        </div>
      </OperazioniCollectionHero>

      <OperazioniMetricStrip>
        <MetricCard label="Segnalazioni totali" value={total} sub="Tutte le segnalazioni registrate" />
        <MetricCard label="Con pratica" value={reports.filter((r) => r.internal_case_id).length} sub="Segnalazioni con pratica collegata" variant="success" />
        <MetricCard label="Senza pratica" value={reports.filter((r) => !r.internal_case_id).length} sub="Da collegare a pratica" variant="warning" />
      </OperazioniMetricStrip>

      <OperazioniCollectionPanel
        title="Registro segnalazioni"
        description="Elenco operativo con numero segnalazione, data e stato di presa in carico amministrativa."
        count={reports.length}
      >
        <div className="mt-1">
          {isLoading ? (
            <p className="text-sm text-gray-500">Caricamento segnalazioni in corso.</p>
          ) : reports.length === 0 ? (
            <EmptyState
              icon={AlertTriangleIcon}
              title="Nessuna segnalazione"
              description="Non risultano segnalazioni registrate."
            />
          ) : (
            <OperazioniList>
              {reports.map((report) => (
                <OperazioniListLink
                  key={String(report.id)}
                  href={`/operazioni/segnalazioni/${report.id as string}`}
                  title={String(report.title ?? "Senza titolo")}
                  meta={`${String(report.report_number ?? "Segnalazione senza numero")}${report.created_at ? ` · ${new Date(report.created_at as string).toLocaleDateString("it-IT")}` : ""}`}
                  status={report.internal_case_id ? "Con pratica" : "Senza pratica"}
                  statusTone={report.internal_case_id ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-700"}
                  aside={
                    <span className="rounded-full border border-[#e2e6e1] bg-[#f6f7f4] px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-[#5d695f]">
                      {String(report.status ?? "submitted")}
                    </span>
                  }
                />
              ))}
            </OperazioniList>
          )}
        </div>
      </OperazioniCollectionPanel>
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
      {() => <SegnalazioniContent />}
    </OperazioniModulePage>
  );
}
