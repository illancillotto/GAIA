"use client";

import { useCallback, useEffect, useState } from "react";

import {
  OperazioniCollectionHero,
  OperazioniCollectionPanel,
  OperazioniHeroNotice,
  OperazioniList,
  OperazioniListLink,
  OperazioniMetricStrip,
  OperazioniToolbar,
} from "@/components/operazioni/collection-layout";
import { OperazioniModulePage } from "@/components/operazioni/operazioni-module-page";
import { MetricCard } from "@/components/ui/metric-card";
import { EmptyState } from "@/components/ui/empty-state";
import { RefreshIcon } from "@/components/ui/icons";
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

function AttivitaContent() {
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
      <OperazioniCollectionHero
        eyebrow="Workflow operatori"
        icon={<RefreshIcon className="h-3.5 w-3.5" />}
        title="Attività operative con stato di avanzamento, approvazioni e carico sul campo."
        description="La vista mette in primo piano il ritmo del lavoro operativo: aperture, invii, revisione caposervizio e chiusure approvate."
      >
        {loadError ? (
          <OperazioniHeroNotice title="Caricamento non riuscito" description={loadError} tone="danger" />
        ) : (
          <OperazioniHeroNotice
            title="Lettura rapida del flusso"
            description={`${inProgressCount} attività in corso, ${submittedCount} in attesa revisione, ${approvedCount} approvate.`}
          />
        )}
        <div className="rounded-2xl border border-white/80 bg-white/75 px-4 py-3">
          <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-gray-500">Stato osservato</p>
          <p className="mt-2 text-sm font-medium text-gray-900">{statusFilter ? statusLabels[statusFilter] ?? statusFilter : "Tutti gli stati"}</p>
          <p className="mt-1 text-sm text-gray-600">Usa il filtro per isolare attività aperte, da approvare o già chiuse.</p>
        </div>
      </OperazioniCollectionHero>

      <OperazioniMetricStrip>
        <MetricCard label="Attività totali" value={total} sub="Tutte le attività registrate" />
        <MetricCard label="In corso" value={inProgressCount} sub="Attività attualmente aperte" variant="warning" />
        <MetricCard label="In attesa approvazione" value={submittedCount} sub="Da revisionare" variant="warning" />
        <MetricCard label="Approvate" value={approvedCount} sub="Attività validate" variant="success" />
      </OperazioniMetricStrip>

      <OperazioniCollectionPanel
        title="Coda attività"
        description="Lista ad alta leggibilità con stato workflow, operatore e data di avvio."
        count={activities.length}
      >
        <OperazioniToolbar
          filterValue={statusFilter}
          onFilterChange={setStatusFilter}
          filterOptions={[
            { value: "", label: "Tutti gli stati" },
            { value: "in_progress", label: "In corso" },
            { value: "submitted", label: "Inviata" },
            { value: "under_review", label: "In revisione" },
            { value: "approved", label: "Approvata" },
            { value: "rejected", label: "Respinta" },
          ]}
        />

        <div className="mt-4">
          {isLoading ? (
            <p className="text-sm text-gray-500">Caricamento attività in corso.</p>
          ) : activities.length === 0 ? (
            <EmptyState
              icon={RefreshIcon}
              title="Nessuna attività trovata"
              description="Non risultano attività con i filtri correnti."
            />
          ) : (
            <OperazioniList>
              {activities.map((activity) => (
                <OperazioniListLink
                  key={String(activity.id)}
                  href={`/operazioni/attivita/${activity.id as string}`}
                  title={`Attività ${String(activity.id).substring(0, 8)}…`}
                  meta={`Operatore ID ${String(activity.operator_user_id ?? "—")}${activity.started_at ? ` · ${new Date(activity.started_at as string).toLocaleDateString("it-IT")}` : ""}`}
                  status={statusLabels[String(activity.status)] || String(activity.status)}
                  statusTone={statusTone[String(activity.status)] || "bg-gray-100 text-gray-600"}
                />
              ))}
            </OperazioniList>
          )}
        </div>
      </OperazioniCollectionPanel>
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
      {() => <AttivitaContent />}
    </OperazioniModulePage>
  );
}
