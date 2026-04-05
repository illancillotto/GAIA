"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { OperazioniModulePage } from "@/components/operazioni/operazioni-module-page";
import { MetricCard } from "@/components/ui/metric-card";
import { EmptyState } from "@/components/ui/empty-state";
import { RefreshIcon, ChevronRightIcon } from "@/components/ui/icons";
import { getActivities } from "@/features/operazioni/api/client";

const statusLabels: Record<string, string> = {
  draft: "Bozza",
  in_progress: "In corso",
  submitted: "Inviata",
  under_review: "In revisione",
  approved: "Approvata",
  rejected: "Respinta",
};

const statusTone: Record<string, string> = {
  draft: "bg-gray-100 text-gray-600",
  in_progress: "bg-sky-50 text-sky-700",
  submitted: "bg-amber-50 text-amber-700",
  under_review: "bg-purple-50 text-purple-700",
  approved: "bg-emerald-50 text-emerald-700",
  rejected: "bg-rose-50 text-rose-700",
};

function BadgeCount({ value }: { value: number }) {
  return (
    <span className="rounded-full bg-[#EAF3E8] px-2.5 py-1 text-xs font-semibold text-[#1D4E35]">
      {value}
    </span>
  );
}

function AttivitaContent({ token }: { token: string }) {
  const [activities, setActivities] = useState<Record<string, unknown>[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState("");

  const loadData = useCallback(async () => {
    try {
      const params: Record<string, string> = { page_size: "50" };
      if (statusFilter) params.status = statusFilter;
      const data = await getActivities(params);
      setActivities(data.items ?? []);
      setTotal(data.total ?? 0);
      setLoadError(null);
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : "Errore nel caricamento attività");
    } finally {
      setIsLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const inProgressCount = activities.filter((a) => a.status === "in_progress").length;
  const submittedCount = activities.filter((a) => a.status === "submitted").length;
  const approvedCount = activities.filter((a) => a.status === "approved").length;

  return (
    <div className="page-stack">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-gray-500">
          Catalogo attività, avvio e chiusura da parte degli operatori, workflow di approvazione del capo servizio.
        </p>
      </div>

      {loadError ? (
        <article className="panel-card">
          <p className="text-sm font-medium text-red-700">Caricamento non riuscito</p>
          <p className="mt-2 text-sm text-gray-600">{loadError}</p>
        </article>
      ) : null}

      <div className="surface-grid">
        <MetricCard label="Attività totali" value={total} sub="Tutte le attività registrate" />
        <MetricCard label="In corso" value={inProgressCount} sub="Attività attualmente aperte" variant="warning" />
        <MetricCard label="In attesa approvazione" value={submittedCount} sub="Da revisionare" variant="warning" />
        <MetricCard label="Approvate" value={approvedCount} sub="Attività validate" variant="success" />
      </div>

      <article className="panel-card">
        <div className="mb-4 flex items-center justify-between gap-3">
          <div>
            <p className="section-title">Elenco attività</p>
            <p className="section-copy">Tutte le attività operatori con stato e dettagli.</p>
          </div>
          <BadgeCount value={activities.length} />
        </div>

        <div className="mb-4">
          <select
            className="form-control"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="">Tutti gli stati</option>
            <option value="in_progress">In corso</option>
            <option value="submitted">Inviata</option>
            <option value="under_review">In revisione</option>
            <option value="approved">Approvata</option>
            <option value="rejected">Respinta</option>
          </select>
        </div>

        {isLoading ? (
          <p className="text-sm text-gray-500">Caricamento attività in corso.</p>
        ) : activities.length === 0 ? (
          <EmptyState
            icon={RefreshIcon}
            title="Nessuna attività trovata"
            description="Non risultano attività con i filtri correnti."
          />
        ) : (
          <div className="max-h-[32rem] space-y-3 overflow-y-auto pr-1">
            {activities.map((activity) => (
              <Link
                key={String(activity.id)}
                href={`/operazioni/attivita/${activity.id as string}`}
                className="flex w-full items-center justify-between rounded-lg border border-gray-100 px-4 py-3 text-left transition hover:bg-gray-50"
              >
                <div>
                  <p className="text-sm font-medium text-gray-900">
                    Attività {String(activity.id).substring(0, 8)}...
                  </p>
                  <p className="mt-1 text-xs text-gray-500">
                    Operatore ID: {String(activity.operator_user_id ?? "—")}
                    {activity.started_at ? ` · ${new Date(activity.started_at as string).toLocaleDateString("it-IT")}` : ""}
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${statusTone[String(activity.status)] || "bg-gray-100 text-gray-600"}`}>
                    {statusLabels[String(activity.status)] || String(activity.status)}
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

export default function AttivitaPage() {
  return (
    <OperazioniModulePage
      title="Attività"
      description="Avvio e chiusura attività operatori, approvazioni e catalogo."
      breadcrumb="Lista"
    >
      {({ token }) => <AttivitaContent token={token} />}
    </OperazioniModulePage>
  );
}
