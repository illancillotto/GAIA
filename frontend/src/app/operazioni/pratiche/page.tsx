"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { OperazioniModulePage } from "@/components/operazioni/operazioni-module-page";
import { MetricCard } from "@/components/ui/metric-card";
import { EmptyState } from "@/components/ui/empty-state";
import { DocumentIcon, ChevronRightIcon } from "@/components/ui/icons";
import { getCases } from "@/features/operazioni/api/client";

const statusLabels: Record<string, string> = {
  open: "Aperta",
  assigned: "Assegnata",
  acknowledged: "Presa in carico",
  in_progress: "In lavorazione",
  resolved: "Risolto",
  closed: "Chiusa",
  cancelled: "Annullata",
  reopened: "Riaperta",
};

const statusTone: Record<string, string> = {
  open: "bg-sky-50 text-sky-700",
  assigned: "bg-indigo-50 text-indigo-700",
  acknowledged: "bg-purple-50 text-purple-700",
  in_progress: "bg-amber-50 text-amber-700",
  resolved: "bg-emerald-50 text-emerald-700",
  closed: "bg-gray-100 text-gray-600",
  cancelled: "bg-rose-50 text-rose-700",
  reopened: "bg-orange-50 text-orange-700",
};

function BadgeCount({ value }: { value: number }) {
  return (
    <span className="rounded-full bg-[#EAF3E8] px-2.5 py-1 text-xs font-semibold text-[#1D4E35]">
      {value}
    </span>
  );
}

function PraticheContent({ token }: { token: string }) {
  const [cases, setCases] = useState<Record<string, unknown>[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState("");

  const loadData = useCallback(async () => {
    try {
      const params: Record<string, string> = { page_size: "50" };
      if (statusFilter) params.status = statusFilter;
      const data = await getCases(params);
      setCases(data.items ?? []);
      setTotal(data.total ?? 0);
      setLoadError(null);
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : "Errore nel caricamento pratiche");
    } finally {
      setIsLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const openCount = cases.filter((c) => ["open", "assigned"].includes(String(c.status))).length;
  const inProgressCount = cases.filter((c) => c.status === "in_progress").length;
  const closedCount = cases.filter((c) => ["closed", "resolved"].includes(String(c.status))).length;

  return (
    <div className="page-stack">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-gray-500">
          Workflow completo pratiche: assegnazione, avanzamento stati, timeline eventi e chiusura.
        </p>
      </div>

      {loadError ? (
        <article className="panel-card">
          <p className="text-sm font-medium text-red-700">Caricamento non riuscito</p>
          <p className="mt-2 text-sm text-gray-600">{loadError}</p>
        </article>
      ) : null}

      <div className="surface-grid">
        <MetricCard label="Pratiche totali" value={total} sub="Tutte le pratiche registrate" />
        <MetricCard label="Aperte / Assegnate" value={openCount} sub="Da prendere in carico" variant="warning" />
        <MetricCard label="In lavorazione" value={inProgressCount} sub="Pratiche attive" variant="warning" />
        <MetricCard label="Chiuse / Risolte" value={closedCount} sub="Pratiche completate" variant="success" />
      </div>

      <article className="panel-card">
        <div className="mb-4 flex items-center justify-between gap-3">
          <div>
            <p className="section-title">Elenco pratiche</p>
            <p className="section-copy">Tutte le pratiche interne con stato e timeline eventi.</p>
          </div>
          <BadgeCount value={cases.length} />
        </div>

        <div className="mb-4">
          <select
            className="form-control"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="">Tutti gli stati</option>
            <option value="open">Aperta</option>
            <option value="assigned">Assegnata</option>
            <option value="in_progress">In lavorazione</option>
            <option value="resolved">Risolto</option>
            <option value="closed">Chiusa</option>
          </select>
        </div>

        {isLoading ? (
          <p className="text-sm text-gray-500">Caricamento pratiche in corso.</p>
        ) : cases.length === 0 ? (
          <EmptyState
            icon={DocumentIcon}
            title="Nessuna pratica trovata"
            description="Non risultano pratiche con i filtri correnti."
          />
        ) : (
          <div className="max-h-[32rem] space-y-3 overflow-y-auto pr-1">
            {cases.map((caseItem) => (
              <Link
                key={String(caseItem.id)}
                href={`/operazioni/pratiche/${caseItem.id as string}`}
                className="flex w-full items-center justify-between rounded-lg border border-gray-100 px-4 py-3 text-left transition hover:bg-gray-50"
              >
                <div>
                  <p className="text-sm font-medium text-gray-900">{String(caseItem.title ?? "Senza titolo")}</p>
                  <p className="mt-1 text-xs text-gray-500">
                    {String(caseItem.case_number ?? "")}
                    {caseItem.created_at ? ` · ${new Date(caseItem.created_at as string).toLocaleDateString("it-IT")}` : ""}
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${statusTone[String(caseItem.status)] || "bg-gray-100 text-gray-600"}`}>
                    {statusLabels[String(caseItem.status)] || String(caseItem.status)}
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

export default function PratichePage() {
  return (
    <OperazioniModulePage
      title="Pratiche"
      description="Pratiche interne: assegnazione, stati e chiusura."
      breadcrumb="Lista"
    >
      {({ token }) => <PraticheContent token={token} />}
    </OperazioniModulePage>
  );
}
