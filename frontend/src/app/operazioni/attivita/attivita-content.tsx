"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";

import {
  OperazioniCollectionHero,
  OperazioniCollectionPanel,
  OperazioniHeroNotice,
  OperazioniList,
  OperazioniListLink,
  OperazioniMetricStrip,
  OperazioniToolbar,
} from "@/components/operazioni/collection-layout";
import { MetricCard } from "@/components/ui/metric-card";
import { EmptyState } from "@/components/ui/empty-state";
import { RefreshIcon } from "@/components/ui/icons";
import { getActivities, getOperators } from "@/features/operazioni/api/client";

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

type LinkedMeterReadingSummary = {
  id: string;
  punto_consegna: string;
  matricola: string | null;
  lettura_finale: string | null;
  data_lettura: string | null;
  photo_url: string | null;
  source: string;
  record_kind: string | null;
};

function asLinkedMeterReading(value: unknown): LinkedMeterReadingSummary | null {
  if (!value || typeof value !== "object") return null;
  if (typeof (value as { id?: unknown }).id !== "string") return null;
  if (typeof (value as { punto_consegna?: unknown }).punto_consegna !== "string") return null;
  return value as LinkedMeterReadingSummary;
}

const scopeOptions = [
  { id: "all", label: "Tutte le attività" },
  { id: "mobile_meter", label: "Solo contatori mobile" },
] as const;

type ScopeFilter = (typeof scopeOptions)[number]["id"];

type AttivitaContentProps = {
  initialScopeFilter?: ScopeFilter;
  initialOperatorUserId?: string | null;
  title?: string;
  description?: string;
};

type OperatorOption = {
  id: string;
  gaia_user_id: number | null;
  username: string | null;
  first_name: string | null;
  last_name: string | null;
  email: string | null;
};

function operatorDisplayName(operator: OperatorOption): string {
  const fullName = [operator.first_name, operator.last_name].filter(Boolean).join(" ").trim();
  return fullName || operator.username || operator.email || `Operatore ${operator.id.slice(0, 8)}`;
}

export function AttivitaContent({
  initialScopeFilter = "all",
  initialOperatorUserId = null,
  title = "Attività operative con stato di avanzamento, approvazioni e carico sul campo.",
  description = "La vista mette in primo piano il ritmo del lavoro operativo: aperture, invii, revisione caposervizio e chiusure approvate.",
}: AttivitaContentProps) {
  const [activities, setActivities] = useState<Record<string, unknown>[]>([]);
  const [operators, setOperators] = useState<OperatorOption[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [scopeFilter, setScopeFilter] = useState<ScopeFilter>(initialScopeFilter);
  const [operatorFilter, setOperatorFilter] = useState(initialOperatorUserId ?? "");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  useEffect(() => {
    setScopeFilter(initialScopeFilter);
  }, [initialScopeFilter]);

  useEffect(() => {
    setOperatorFilter(initialOperatorUserId ?? "");
  }, [initialOperatorUserId]);

  useEffect(() => {
    let cancelled = false;
    void getOperators({ page_size: "100" })
      .then((payload) => {
        if (cancelled) return;
        setOperators(Array.isArray(payload.items) ? (payload.items as OperatorOption[]) : []);
      })
      .catch(() => {
        if (!cancelled) {
          setOperators([]);
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const loadData = useCallback(async () => {
    try {
      setIsLoading(true);
      const params: Record<string, string> = { page_size: "50" };
      if (searchTerm.trim()) params.search = searchTerm.trim();
      if (statusFilter) params.status = statusFilter;
      if (operatorFilter) params.operator_user_id = operatorFilter;
      if (dateFrom) params.date_from = `${dateFrom}T00:00:00`;
      if (dateTo) params.date_to = `${dateTo}T23:59:59`;
      if (scopeFilter === "mobile_meter") params.mobile_meter_only = "true";
      const data = await getActivities(params);
      setActivities(data.items ?? []);
      setTotal(data.total ?? 0);
      setLoadError(null);
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : "Errore nel caricamento attività");
    } finally {
      setIsLoading(false);
    }
  }, [dateFrom, dateTo, operatorFilter, scopeFilter, searchTerm, statusFilter]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const inProgressCount = activities.filter((a) => a.status === "in_progress").length;
  const submittedCount = activities.filter((a) => a.status === "submitted").length;
  const approvedCount = activities.filter((a) => a.status === "approved").length;
  const uniqueOperatorsCount = new Set(
    activities
      .map((activity) => activity.operator_user_id)
      .filter((value): value is number => typeof value === "number"),
  ).size;
  const selectedOperator = operators.find(
    (operator) => operator.gaia_user_id != null && String(operator.gaia_user_id) === operatorFilter,
  );

  function activityOperatorLabel(activity: Record<string, unknown>): string {
    const operatorUserId = typeof activity.operator_user_id === "number" ? activity.operator_user_id : null;
    if (operatorUserId == null) {
      return "Operatore non associato";
    }
    const match = operators.find((operator) => operator.gaia_user_id === operatorUserId);
    return match ? operatorDisplayName(match) : `Operatore ID ${operatorUserId}`;
  }

  return (
    <div className="page-stack">
      <OperazioniCollectionHero
        eyebrow="Workflow operatori"
        icon={<RefreshIcon className="h-3.5 w-3.5" />}
        title={title}
        description={description}
      >
        {loadError ? (
          <OperazioniHeroNotice title="Caricamento non riuscito" description={loadError} tone="danger" />
        ) : (
          <OperazioniHeroNotice
            title="Lettura rapida del flusso"
            description={
              selectedOperator
                ? `${operatorDisplayName(selectedOperator)}: ${inProgressCount} attività in corso, ${submittedCount} in attesa revisione, ${approvedCount} approvate.`
                : `${inProgressCount} attività in corso, ${submittedCount} in attesa revisione, ${approvedCount} approvate.`
            }
          />
        )}
        <div className="rounded-2xl border border-white/80 bg-white/75 px-4 py-3">
          <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-gray-500">Stato osservato</p>
          <p className="mt-2 text-sm font-medium text-gray-900">{statusFilter ? statusLabels[statusFilter] ?? statusFilter : "Tutti gli stati"}</p>
          <p className="mt-1 text-sm text-gray-600">
            {scopeFilter === "mobile_meter"
              ? "Vista focalizzata sulle attività mobile che hanno generato una lettura contatore in Catasto."
              : operatorFilter && selectedOperator
                ? `Filtro operatore attivo su ${operatorDisplayName(selectedOperator)}.`
                : "Usa i filtri per isolare operatore, stato, data o testo libero."}
          </p>
        </div>
      </OperazioniCollectionHero>

      <OperazioniMetricStrip>
        <MetricCard label="Attività totali" value={total} sub="Tutte le attività registrate" />
        <MetricCard label="In corso" value={inProgressCount} sub="Attività attualmente aperte" variant="warning" />
        <MetricCard label="In attesa approvazione" value={submittedCount} sub="Da revisionare" variant="warning" />
        <MetricCard
          label="Operatori visibili"
          value={uniqueOperatorsCount}
          sub={operatorFilter ? "Filtro operatore attivo" : "Operatori distinti nel risultato"}
          variant="success"
        />
      </OperazioniMetricStrip>

      <OperazioniCollectionPanel
        title="Coda attività"
        description="Lista ad alta leggibilità con stato workflow, operatore, ricerca testuale e intervallo temporale."
        count={activities.length}
        action={
          <Link href="/operazioni/operatori" className="btn-secondary">
            Apri cruscotto operatori
          </Link>
        }
      >
        <OperazioniToolbar
          search={searchTerm}
          onSearchChange={setSearchTerm}
          searchPlaceholder="Cerca per catalogo, note, stato o ID"
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
        <div className="mt-4 grid gap-3 rounded-[24px] border border-[#e4e8e2] bg-[#fcfcf9] p-3 md:grid-cols-3">
          <label className="block">
            <span className="label-caption">Operatore</span>
            <select
              className="form-control mt-2"
              value={operatorFilter}
              onChange={(event) => setOperatorFilter(event.target.value)}
            >
              <option value="">Tutti gli operatori</option>
              {operators
                .filter((operator) => operator.gaia_user_id != null)
                .map((operator) => (
                  <option key={operator.id} value={String(operator.gaia_user_id)}>
                    {operatorDisplayName(operator)}
                  </option>
                ))}
            </select>
          </label>
          <label className="block">
            <span className="label-caption">Da data</span>
            <input
              className="form-control mt-2"
              type="date"
              value={dateFrom}
              onChange={(event) => setDateFrom(event.target.value)}
            />
          </label>
          <label className="block">
            <span className="label-caption">A data</span>
            <input
              className="form-control mt-2"
              type="date"
              value={dateTo}
              onChange={(event) => setDateTo(event.target.value)}
            />
          </label>
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          {scopeOptions.map((option) => (
            <button
              key={option.id}
              type="button"
              className={
                scopeFilter === option.id
                  ? "rounded-full bg-[#1D4E35] px-4 py-2 text-sm font-semibold text-white"
                  : "rounded-full border border-[#d5ddd6] bg-white px-4 py-2 text-sm font-semibold text-gray-700 transition hover:border-[#1D4E35] hover:text-[#1D4E35]"
              }
              onClick={() => setScopeFilter(option.id)}
            >
              {option.label}
            </button>
          ))}
        </div>

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
                (() => {
                  const linkedMeterReading = asLinkedMeterReading(activity.linked_meter_reading);
                  const titleValue = typeof activity.catalog_name === "string" && activity.catalog_name
                    ? activity.catalog_name
                    : `Attività ${String(activity.id).substring(0, 8)}…`;
                  const metaParts = [
                    activityOperatorLabel(activity),
                    activity.started_at ? new Date(activity.started_at as string).toLocaleDateString("it-IT") : null,
                    activity.ended_at ? `Chiusa ${new Date(activity.ended_at as string).toLocaleDateString("it-IT")}` : null,
                    linkedMeterReading ? `Contatore ${linkedMeterReading.punto_consegna}` : null,
                    linkedMeterReading?.lettura_finale ? `Lettura ${linkedMeterReading.lettura_finale}` : null,
                  ].filter(Boolean);
                  return (
                    <OperazioniListLink
                      key={String(activity.id)}
                      href={`/operazioni/attivita/${activity.id as string}`}
                      title={titleValue}
                      meta={metaParts.join(" · ")}
                      status={statusLabels[String(activity.status)] || String(activity.status)}
                      statusTone={statusTone[String(activity.status)] || "bg-gray-100 text-gray-600"}
                      aside={
                        linkedMeterReading ? (
                          <span className="rounded-full bg-emerald-100 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-emerald-800">
                            Contatore mobile
                          </span>
                        ) : undefined
                      }
                    />
                  );
                })()
              ))}
            </OperazioniList>
          )}
        </div>
      </OperazioniCollectionPanel>
    </div>
  );
}
