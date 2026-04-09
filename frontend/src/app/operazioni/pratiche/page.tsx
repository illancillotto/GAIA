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
import { DocumentIcon } from "@/components/ui/icons";
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

function PraticheContent() {
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
      <OperazioniCollectionHero
        eyebrow="Case management"
        icon={<DocumentIcon className="h-3.5 w-3.5" />}
        title="Pratiche interne con presa in carico, lavorazione e chiusura in una sola sequenza leggibile."
        description="La pagina è orientata al governo del workflow: distingue subito le pratiche aperte da quelle in lavorazione e da quelle già chiuse o risolte."
      >
        {loadError ? (
          <OperazioniHeroNotice title="Caricamento non riuscito" description={loadError} tone="danger" />
        ) : (
          <OperazioniHeroNotice
            title="Stati sotto controllo"
            description={`${openCount} pratiche aperte o assegnate, ${inProgressCount} in lavorazione, ${closedCount} completate.`}
          />
        )}
        <div className="rounded-2xl border border-white/80 bg-white/75 px-4 py-3">
          <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-gray-500">Filtro attivo</p>
          <p className="mt-2 text-sm font-medium text-gray-900">{statusFilter ? statusLabels[statusFilter] ?? statusFilter : "Tutti gli stati"}</p>
          <p className="mt-1 text-sm text-gray-600">Mantieni la coda focalizzata su prese in carico o chiusure in sospeso.</p>
        </div>
      </OperazioniCollectionHero>

      <OperazioniMetricStrip>
        <MetricCard label="Pratiche totali" value={total} sub="Tutte le pratiche registrate" />
        <MetricCard label="Aperte / Assegnate" value={openCount} sub="Da prendere in carico" variant="warning" />
        <MetricCard label="In lavorazione" value={inProgressCount} sub="Pratiche attive" variant="warning" />
        <MetricCard label="Chiuse / Risolte" value={closedCount} sub="Pratiche completate" variant="success" />
      </OperazioniMetricStrip>

      <OperazioniCollectionPanel
        title="Coda pratiche"
        description="Vista compatta per numero pratica, data di apertura e stato di avanzamento."
        count={cases.length}
      >
        <OperazioniToolbar
          filterValue={statusFilter}
          onFilterChange={setStatusFilter}
          filterOptions={[
            { value: "", label: "Tutti gli stati" },
            { value: "open", label: "Aperta" },
            { value: "assigned", label: "Assegnata" },
            { value: "in_progress", label: "In lavorazione" },
            { value: "resolved", label: "Risolto" },
            { value: "closed", label: "Chiusa" },
          ]}
        />

        <div className="mt-4">
          {isLoading ? (
            <p className="text-sm text-gray-500">Caricamento pratiche in corso.</p>
          ) : cases.length === 0 ? (
            <EmptyState
              icon={DocumentIcon}
              title="Nessuna pratica trovata"
              description="Non risultano pratiche con i filtri correnti."
            />
          ) : (
            <OperazioniList>
              {cases.map((caseItem) => (
                <OperazioniListLink
                  key={String(caseItem.id)}
                  href={`/operazioni/pratiche/${caseItem.id as string}`}
                  title={String(caseItem.title ?? "Senza titolo")}
                  meta={`${String(caseItem.case_number ?? "Pratica senza numero")}${caseItem.created_at ? ` · ${new Date(caseItem.created_at as string).toLocaleDateString("it-IT")}` : ""}`}
                  status={statusLabels[String(caseItem.status)] || String(caseItem.status)}
                  statusTone={statusTone[String(caseItem.status)] || "bg-gray-100 text-gray-600"}
                />
              ))}
            </OperazioniList>
          )}
        </div>
      </OperazioniCollectionPanel>
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
      {() => <PraticheContent />}
    </OperazioniModulePage>
  );
}
