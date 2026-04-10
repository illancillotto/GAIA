"use client";

import { Fragment } from "react";
import Link from "next/link";
import { useEffect, useState } from "react";

import {
  OperazioniBreadcrumb,
  OperazioniCollectionHero,
  OperazioniCollectionPanel,
  OperazioniHeroNotice,
  OperazioniMetricStrip,
} from "@/components/operazioni/collection-layout";
import { ImportWhiteModal } from "@/components/operazioni/import-white-modal";
import { OperazioniModulePage } from "@/components/operazioni/operazioni-module-page";
import { MetricCard } from "@/components/ui/metric-card";
import { GridIcon } from "@/components/ui/icons";
import { getReportsDashboard } from "@/features/operazioni/api/client";

type DashboardEvent = {
  event_type: string;
  event_at: string | null;
  note: string | null;
};

type DashboardItem = {
  id: string;
  external_code: string | null;
  report_number: string;
  title: string;
  description: string | null;
  status: string;
  area_code: string | null;
  reporter_name: string | null;
  latitude: number | null;
  longitude: number | null;
  assigned_responsibles: string | null;
  completion_time_text: string | null;
  completion_time_minutes: number | null;
  created_at: string | null;
  resolved_at: string | null;
  source_system: string | null;
  case_id: string | null;
  case_status: string | null;
  events_count: number;
  events: DashboardEvent[];
};

type DashboardAggregateItem = {
  area?: string;
  name?: string;
  count: number;
};

type DashboardResponse = {
  items: DashboardItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  aggregates: {
    by_status: Record<string, number>;
    by_area: DashboardAggregateItem[];
    by_reporter: DashboardAggregateItem[];
    avg_completion_minutes: number | null;
    total_with_events: number;
    total_without_events: number;
  };
};

type SortKey =
  | "code"
  | "status"
  | "title"
  | "area"
  | "reporter"
  | "created_at"
  | "events_count"
  | "completion_time_minutes";

function formatDate(value: string | null): string {
  if (!value) {
    return "—";
  }
  return new Date(value).toLocaleString("it-IT");
}

function formatStatusLabel(value: string): string {
  if (value === "open") return "Non presa in carico";
  if (value === "in_progress") return "In lavorazione";
  if (value === "resolved") return "Completata";
  if (value === "archived") return "Archiviata";
  return value;
}

function statusTone(value: string): string {
  if (value === "open") return "bg-red-50 text-red-700 border-red-100";
  if (value === "in_progress") return "bg-sky-50 text-sky-700 border-sky-100";
  if (value === "resolved") return "bg-emerald-50 text-emerald-700 border-emerald-100";
  return "bg-gray-100 text-gray-700 border-gray-200";
}

function splitResponsibles(value: string | null): string[] {
  if (!value) {
    return [];
  }
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function buildPageParams(state: {
  selectedStatuses: string[];
  areaCode: string;
  reporterName: string;
  search: string;
  dateFrom: string;
  dateTo: string;
  page: number;
}): Record<string, string> {
  const params: Record<string, string> = {
    page: String(state.page),
    page_size: "25",
  };
  if (state.selectedStatuses.length > 0) {
    params.status_filter = state.selectedStatuses.join(",");
  }
  if (state.areaCode) {
    params.area_code = state.areaCode;
  }
  if (state.reporterName) {
    params.reporter_name = state.reporterName;
  }
  if (state.search) {
    params.search = state.search;
  }
  if (state.dateFrom) {
    params.date_from = state.dateFrom;
  }
  if (state.dateTo) {
    params.date_to = state.dateTo;
  }
  return params;
}

function SortButton({
  active,
  label,
  onClick,
}: {
  active: boolean;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      className={`text-left text-[11px] font-semibold uppercase tracking-[0.18em] ${
        active ? "text-[#1D4E35]" : "text-[#667267]"
      }`}
      onClick={onClick}
    >
      {label}
    </button>
  );
}

function SegnalazioniCruscottoContent() {
  const [data, setData] = useState<DashboardResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedStatuses, setSelectedStatuses] = useState<string[]>([]);
  const [areaCode, setAreaCode] = useState("");
  const [reporterName, setReporterName] = useState("");
  const [search, setSearch] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [viewMode, setViewMode] = useState<"list" | "map">("list");
  const [page, setPage] = useState(1);
  const [expandedRows, setExpandedRows] = useState<Record<string, boolean>>({});
  const [sortKey, setSortKey] = useState<SortKey>("created_at");
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("desc");
  const [importOpen, setImportOpen] = useState(false);
  const [reloadToken, setReloadToken] = useState(0);

  useEffect(() => {
    let cancelled = false;

    async function loadDashboard(): Promise<void> {
      setLoading(true);
      try {
        const response = (await getReportsDashboard(
          buildPageParams({
            selectedStatuses,
            areaCode,
            reporterName,
            search,
            dateFrom,
            dateTo,
            page,
          }),
        )) as DashboardResponse;
        if (!cancelled) {
          setData(response);
          setError(null);
        }
      } catch (currentError) {
        if (!cancelled) {
          setError(currentError instanceof Error ? currentError.message : "Errore caricamento cruscotto");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void loadDashboard();
    return () => {
      cancelled = true;
    };
  }, [selectedStatuses, areaCode, reporterName, search, dateFrom, dateTo, page, reloadToken]);

  const areaOptions = (data?.aggregates.by_area ?? []).map((item) => ({
    value: item.area ?? "",
    label: `${item.area ?? "Area non definita"} (${item.count})`,
  }));
  const reporterOptions = (data?.aggregates.by_reporter ?? []).map((item) => ({
    value: item.name ?? "",
    label: `${item.name ?? "Segnalatore non definito"} (${item.count})`,
  }));

  const items = [...(data?.items ?? [])].sort((left, right) => {
    const leftValue =
      sortKey === "code"
        ? left.external_code ?? left.report_number
        : sortKey === "status"
          ? left.status
          : sortKey === "title"
            ? left.title
            : sortKey === "area"
              ? left.area_code ?? ""
              : sortKey === "reporter"
                ? left.reporter_name ?? ""
                : sortKey === "created_at"
                  ? left.created_at ?? ""
                  : sortKey === "events_count"
                    ? left.events_count
                    : left.completion_time_minutes ?? -1;
    const rightValue =
      sortKey === "code"
        ? right.external_code ?? right.report_number
        : sortKey === "status"
          ? right.status
          : sortKey === "title"
            ? right.title
            : sortKey === "area"
              ? right.area_code ?? ""
              : sortKey === "reporter"
                ? right.reporter_name ?? ""
                : sortKey === "created_at"
                  ? right.created_at ?? ""
                  : sortKey === "events_count"
                    ? right.events_count
                    : right.completion_time_minutes ?? -1;

    if (leftValue < rightValue) {
      return sortDirection === "asc" ? -1 : 1;
    }
    if (leftValue > rightValue) {
      return sortDirection === "asc" ? 1 : -1;
    }
    return 0;
  });

  function toggleStatus(status: string): void {
    setPage(1);
    setSelectedStatuses((current) =>
      current.includes(status) ? current.filter((item) => item !== status) : [...current, status],
    );
  }

  function applySingleStatus(status: string): void {
    setPage(1);
    setSelectedStatuses([status]);
  }

  function clearFilters(): void {
    setSelectedStatuses([]);
    setAreaCode("");
    setReporterName("");
    setSearch("");
    setDateFrom("");
    setDateTo("");
    setPage(1);
  }

  function toggleSort(nextKey: SortKey): void {
    if (sortKey === nextKey) {
      setSortDirection((current) => (current === "asc" ? "desc" : "asc"));
      return;
    }
    setSortKey(nextKey);
    setSortDirection(nextKey === "created_at" ? "desc" : "asc");
  }

  return (
    <div className="page-stack">
      <OperazioniBreadcrumb
        items={[
          { label: "Operazioni", href: "/operazioni" },
          { label: "Segnalazioni", href: "/operazioni/segnalazioni" },
          { label: "Cruscotto" },
        ]}
      />

      <OperazioniCollectionHero
        eyebrow="Cruscotto segnalazioni"
        icon={<GridIcon className="h-3.5 w-3.5" />}
        title="Vista operativa per verificare carico, aree, tempi e sotto-azioni delle segnalazioni White."
        description="Il cruscotto consolida import Excel, triage delle segnalazioni e timeline tecnica in un’unica pagina pensata per il presidio quotidiano."
      >
        {error ? (
          <OperazioniHeroNotice title="Caricamento non riuscito" description={error} tone="danger" />
        ) : (
          <OperazioniHeroNotice
            title="Quadro operativo"
            description={`${data?.aggregates.total_with_events ?? 0} segnalazioni con sotto-azioni, ${data?.aggregates.total_without_events ?? 0} senza avanzamenti registrati.`}
          />
        )}
        <div className="flex flex-wrap gap-3">
          <button className="btn-primary" type="button" onClick={() => setImportOpen(true)}>
            Importa Excel White
          </button>
          <Link href="/operazioni/segnalazioni" className="btn-secondary">
            Torna alla lista base
          </Link>
        </div>
      </OperazioniCollectionHero>

      <OperazioniMetricStrip>
        <button type="button" className="text-left" onClick={() => setSelectedStatuses([])}>
          <MetricCard label="Totale segnalazioni" value={data?.total ?? 0} sub="Dataset filtrato corrente" />
        </button>
        <button type="button" className="text-left" onClick={() => applySingleStatus("open")}>
          <MetricCard
            label="Non prese in carico"
            value={data?.aggregates.by_status.open ?? 0}
            sub="Click per filtrare la lista"
            variant="danger"
          />
        </button>
        <button type="button" className="text-left" onClick={() => applySingleStatus("in_progress")}>
          <MetricCard
            label="In lavorazione"
            value={data?.aggregates.by_status.in_progress ?? 0}
            sub="Segnalazioni in gestione"
            variant="info"
          />
        </button>
        <button type="button" className="text-left" onClick={() => applySingleStatus("resolved")}>
          <MetricCard
            label="Completate"
            value={data?.aggregates.by_status.resolved ?? 0}
            sub="Segnalazioni concluse"
            variant="success"
          />
        </button>
      </OperazioniMetricStrip>

      <OperazioniCollectionPanel
        title="Filtri e azioni"
        description="Stato, area, segnalatore, periodo e ricerca testuale sul dataset importato o nativo."
        count={items.length}
      >
        <div className="grid gap-4 lg:grid-cols-[1.3fr,1fr,1fr,0.8fr,0.8fr,1.2fr]">
          <div className="rounded-2xl border border-[#e4e8e2] bg-[#fbfcfa] p-4">
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#667267]">Filtro stato</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {[
                ["open", "Non presa in carico"],
                ["in_progress", "In lavorazione"],
                ["resolved", "Completata"],
              ].map(([value, label]) => (
                <button
                  key={value}
                  type="button"
                  className={`rounded-full border px-3 py-1.5 text-xs font-semibold ${
                    selectedStatuses.includes(value)
                      ? "border-[#1D4E35] bg-[#edf5f0] text-[#1D4E35]"
                      : "border-[#d9dfd6] bg-white text-gray-600"
                  }`}
                  onClick={() => toggleStatus(value)}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

          <label className="rounded-2xl border border-[#e4e8e2] bg-[#fbfcfa] p-4">
            <span className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#667267]">Area</span>
            <select
              className="form-control mt-3"
              value={areaCode}
              onChange={(event) => {
                setPage(1);
                setAreaCode(event.target.value);
              }}
            >
              <option value="">Tutte le aree</option>
              {areaOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>

          <label className="rounded-2xl border border-[#e4e8e2] bg-[#fbfcfa] p-4">
            <span className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#667267]">Segnalatore</span>
            <input
              className="form-control mt-3"
              list="reporter-options"
              value={reporterName}
              onChange={(event) => {
                setPage(1);
                setReporterName(event.target.value);
              }}
              placeholder="Cerca per nome"
            />
            <datalist id="reporter-options">
              {reporterOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </datalist>
          </label>

          <label className="rounded-2xl border border-[#e4e8e2] bg-[#fbfcfa] p-4">
            <span className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#667267]">Dal</span>
            <input
              className="form-control mt-3"
              type="date"
              value={dateFrom}
              onChange={(event) => {
                setPage(1);
                setDateFrom(event.target.value);
              }}
            />
          </label>

          <label className="rounded-2xl border border-[#e4e8e2] bg-[#fbfcfa] p-4">
            <span className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#667267]">Al</span>
            <input
              className="form-control mt-3"
              type="date"
              value={dateTo}
              onChange={(event) => {
                setPage(1);
                setDateTo(event.target.value);
              }}
            />
          </label>

          <label className="rounded-2xl border border-[#e4e8e2] bg-[#fbfcfa] p-4">
            <span className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#667267]">Ricerca</span>
            <input
              className="form-control mt-3"
              value={search}
              onChange={(event) => {
                setPage(1);
                setSearch(event.target.value);
              }}
              placeholder="Note, codice, segnalatore"
            />
          </label>
        </div>

        <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              className={`rounded-full border px-3 py-1.5 text-sm font-semibold ${
                viewMode === "list" ? "border-[#1D4E35] bg-[#edf5f0] text-[#1D4E35]" : "border-[#d9dfd6] bg-white text-gray-600"
              }`}
              onClick={() => setViewMode("list")}
            >
              Vista lista
            </button>
            <button
              type="button"
              className={`rounded-full border px-3 py-1.5 text-sm font-semibold ${
                viewMode === "map" ? "border-[#1D4E35] bg-[#edf5f0] text-[#1D4E35]" : "border-[#d9dfd6] bg-white text-gray-600"
              }`}
              onClick={() => setViewMode("map")}
            >
              Vista mappa
            </button>
          </div>
          <button className="btn-secondary" type="button" onClick={clearFilters}>
            Azzera filtri
          </button>
        </div>
      </OperazioniCollectionPanel>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.45fr),360px]">
        <OperazioniCollectionPanel
          title={viewMode === "list" ? "Vista lista" : "Vista mappa"}
          description={
            viewMode === "list"
              ? "Righe ordinabili con espansione inline su note, timeline, coordinate e responsabili."
              : "Vista geografica delle segnalazioni con marker per stato."
          }
          count={items.length}
        >
          {loading ? (
            <p className="text-sm text-gray-500">Caricamento cruscotto in corso.</p>
          ) : viewMode === "map" ? (
            <div className="rounded-[24px] border border-[#e4e8e2] bg-[linear-gradient(135deg,_rgba(236,244,238,0.96),_rgba(249,247,240,0.96))] p-8 text-center">
              <p className="text-lg font-semibold text-[#183325]">Vista mappa in arrivo</p>
              <p className="mt-2 text-sm leading-6 text-gray-600">
                Il primo rilascio del cruscotto copre la vista lista completa. Le coordinate GPS sono già disponibili nell&apos;espansione di riga.
              </p>
            </div>
          ) : (
            <div className="overflow-hidden rounded-[24px] border border-[#e6ebe5]">
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-[#edf1eb] text-sm">
                  <thead className="bg-[#f7faf7]">
                    <tr>
                      <th className="px-4 py-3"><SortButton active={sortKey === "code"} label="Codice" onClick={() => toggleSort("code")} /></th>
                      <th className="px-4 py-3"><SortButton active={sortKey === "status"} label="Stato" onClick={() => toggleSort("status")} /></th>
                      <th className="px-4 py-3"><SortButton active={sortKey === "title"} label="Titolo / categoria" onClick={() => toggleSort("title")} /></th>
                      <th className="px-4 py-3"><SortButton active={sortKey === "area"} label="Area" onClick={() => toggleSort("area")} /></th>
                      <th className="px-4 py-3"><SortButton active={sortKey === "reporter"} label="Segnalatore" onClick={() => toggleSort("reporter")} /></th>
                      <th className="px-4 py-3"><SortButton active={sortKey === "created_at"} label="Data" onClick={() => toggleSort("created_at")} /></th>
                      <th className="px-4 py-3"><SortButton active={sortKey === "events_count"} label="Azioni" onClick={() => toggleSort("events_count")} /></th>
                      <th className="px-4 py-3"><SortButton active={sortKey === "completion_time_minutes"} label="Tempo" onClick={() => toggleSort("completion_time_minutes")} /></th>
                      <th className="px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-[0.18em] text-[#667267]">Responsabili</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#edf1eb] bg-white">
                    {items.map((item) => {
                      const responsibles = splitResponsibles(item.assigned_responsibles);
                      const expanded = Boolean(expandedRows[item.id]);
                      return (
                        <Fragment key={item.id}>
                          <tr
                            className="cursor-pointer transition hover:bg-[#fbfcfa]"
                            onClick={() =>
                              setExpandedRows((current) => ({
                                ...current,
                                [item.id]: !current[item.id],
                              }))
                            }
                          >
                            <td className="px-4 py-4 font-semibold text-[#183325]">{item.external_code ?? item.report_number}</td>
                            <td className="px-4 py-4">
                              <span className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-semibold ${statusTone(item.status)}`}>
                                {formatStatusLabel(item.status)}
                              </span>
                            </td>
                            <td className="px-4 py-4">
                              <p className="font-medium text-gray-900">{item.title}</p>
                              <p className="mt-1 text-xs text-gray-500">{item.source_system === "white" ? "Import White" : "Segnalazione GAIA"}</p>
                            </td>
                            <td className="max-w-[220px] px-4 py-4 text-gray-600">
                              <span className="line-clamp-2">{item.area_code ?? "—"}</span>
                            </td>
                            <td className="px-4 py-4 text-gray-600">{item.reporter_name ?? "—"}</td>
                            <td className="px-4 py-4 text-gray-600">{formatDate(item.created_at)}</td>
                            <td className="px-4 py-4 text-gray-600">{item.events_count} azioni</td>
                            <td className="px-4 py-4 text-gray-600">{item.completion_time_text ?? "—"}</td>
                            <td className="px-4 py-4 text-gray-600">
                              <div className="flex flex-wrap gap-1">
                                {responsibles.slice(0, 2).map((name) => (
                                  <span key={name} className="rounded-full border border-[#d9dfd6] bg-[#fbfcfa] px-2.5 py-1 text-xs">
                                    {name}
                                  </span>
                                ))}
                                {responsibles.length > 2 ? (
                                  <span className="rounded-full border border-[#d9dfd6] bg-[#edf5f0] px-2.5 py-1 text-xs font-semibold text-[#1D4E35]">
                                    +{responsibles.length - 2}
                                  </span>
                                ) : null}
                              </div>
                            </td>
                          </tr>
                          {expanded ? (
                            <tr className="bg-[#fbfcfa]">
                              <td colSpan={9} className="px-4 py-5">
                                <div className="grid gap-5 lg:grid-cols-[1.05fr,0.95fr]">
                                  <div className="space-y-4">
                                    <div>
                                      <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#667267]">Note complete</p>
                                      <p className="mt-2 text-sm leading-6 text-gray-700">{item.description ?? "Nessuna nota disponibile."}</p>
                                    </div>
                                    <div>
                                      <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#667267]">Responsabili</p>
                                      <div className="mt-2 flex flex-wrap gap-2">
                                        {responsibles.length > 0 ? responsibles.map((name) => (
                                          <span key={name} className="rounded-full border border-[#d9dfd6] bg-white px-3 py-1 text-xs">
                                            {name}
                                          </span>
                                        )) : <span className="text-sm text-gray-500">Nessun responsabile indicato.</span>}
                                      </div>
                                    </div>
                                    <div>
                                      <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#667267]">Coordinate GPS</p>
                                      {item.latitude != null && item.longitude != null ? (
                                        <a
                                          className="mt-2 inline-flex text-sm font-medium text-[#1D4E35] hover:underline"
                                          href={`https://www.google.com/maps?q=${item.latitude},${item.longitude}`}
                                          target="_blank"
                                          rel="noreferrer"
                                        >
                                          {item.latitude}, {item.longitude}
                                        </a>
                                      ) : (
                                        <p className="mt-2 text-sm text-gray-500">Coordinate non disponibili.</p>
                                      )}
                                    </div>
                                  </div>
                                  <div>
                                    <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#667267]">Timeline sotto-azioni</p>
                                    <div className="mt-3 space-y-3">
                                      {item.events.length > 0 ? item.events.map((event, index) => (
                                        <div key={`${item.id}-${event.event_type}-${index}`} className="rounded-2xl border border-[#e4e8e2] bg-white px-4 py-3">
                                          <div className="flex flex-wrap items-center justify-between gap-2">
                                            <p className="text-sm font-semibold text-gray-900">{event.event_type.replaceAll("_", " ")}</p>
                                            <span className="text-xs text-gray-500">{formatDate(event.event_at)}</span>
                                          </div>
                                          <p className="mt-2 text-sm leading-6 text-gray-600">{event.note ?? "Nessuna nota associata."}</p>
                                        </div>
                                      )) : (
                                        <p className="text-sm text-gray-500">Nessuna sotto-azione registrata.</p>
                                      )}
                                    </div>
                                  </div>
                                </div>
                                <div className="mt-4 flex flex-wrap gap-3">
                                  <Link href={`/operazioni/segnalazioni/${item.id}`} className="btn-secondary">
                                    Apri dettaglio segnalazione
                                  </Link>
                                  {item.case_id ? (
                                    <Link href={`/operazioni/pratiche/${item.case_id}`} className="btn-secondary">
                                      Apri pratica collegata
                                    </Link>
                                  ) : null}
                                </div>
                              </td>
                            </tr>
                          ) : null}
                        </Fragment>
                      );
                    })}
                  </tbody>
                </table>
              </div>
              <div className="flex items-center justify-between gap-3 border-t border-[#edf1eb] bg-[#f7faf7] px-4 py-4">
                <p className="text-sm text-gray-500">
                  Pagina {data?.page ?? 1} di {data?.total_pages ?? 1}
                </p>
                <div className="flex gap-2">
                  <button className="btn-secondary" type="button" disabled={(data?.page ?? 1) <= 1} onClick={() => setPage((current) => Math.max(1, current - 1))}>
                    Precedente
                  </button>
                  <button
                    className="btn-secondary"
                    type="button"
                    disabled={(data?.page ?? 1) >= (data?.total_pages ?? 1)}
                    onClick={() => setPage((current) => current + 1)}
                  >
                    Successiva
                  </button>
                </div>
              </div>
            </div>
          )}
        </OperazioniCollectionPanel>

        <OperazioniCollectionPanel
          title="Statistiche"
          description="Sintesi delle concentrazioni per area, segnalatore e tempo medio di completamento."
          count={(data?.aggregates.by_area.length ?? 0) + (data?.aggregates.by_reporter.length ?? 0)}
        >
          <div className="space-y-6">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#667267]">Top aree</p>
              <div className="mt-3 space-y-3">
                {(data?.aggregates.by_area ?? []).slice(0, 10).map((item) => (
                  <div key={item.area} className="space-y-1">
                    <div className="flex items-center justify-between gap-3 text-sm">
                      <span className="truncate text-gray-700">{item.area}</span>
                      <span className="font-semibold text-[#183325]">{item.count}</span>
                    </div>
                    <div className="h-2 rounded-full bg-[#edf1eb]">
                      <div
                        className="h-2 rounded-full bg-[#1D4E35]"
                        style={{ width: `${Math.max(10, ((item.count ?? 0) / Math.max((data?.aggregates.by_area[0]?.count ?? 1), 1)) * 100)}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#667267]">Top segnalatori</p>
              <div className="mt-3 space-y-3">
                {(data?.aggregates.by_reporter ?? []).slice(0, 10).map((item) => (
                  <div key={item.name} className="flex items-center justify-between gap-3 rounded-2xl border border-[#e4e8e2] bg-[#fbfcfa] px-4 py-3 text-sm">
                    <span className="truncate text-gray-700">{item.name}</span>
                    <span className="font-semibold text-[#183325]">{item.count}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-[24px] border border-[#e4e8e2] bg-[#fbfcfa] p-4">
              <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#667267]">Distribuzione stati</p>
              <div className="mt-3 space-y-3">
                {["open", "in_progress", "resolved"].map((status) => (
                  <div key={status} className="space-y-1">
                    <div className="flex items-center justify-between gap-3 text-sm">
                      <span className="text-gray-700">{formatStatusLabel(status)}</span>
                      <span className="font-semibold text-[#183325]">{data?.aggregates.by_status[status] ?? 0}</span>
                    </div>
                    <div className="h-2 rounded-full bg-white">
                      <div
                        className={`h-2 rounded-full ${status === "open" ? "bg-red-500" : status === "in_progress" ? "bg-sky-500" : "bg-emerald-500"}`}
                        style={{ width: `${Math.max(6, (((data?.aggregates.by_status[status] ?? 0) / Math.max(data?.total ?? 1, 1)) * 100))}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-[24px] border border-[#e4e8e2] bg-[#fbfcfa] p-4">
              <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#667267]">Tempo medio completamento</p>
              <p className="mt-2 text-2xl font-semibold text-[#183325]">
                {data?.aggregates.avg_completion_minutes != null ? `${data.aggregates.avg_completion_minutes} min` : "—"}
              </p>
              <p className="mt-1 text-sm text-gray-500">Calcolato sulle segnalazioni completate del dataset filtrato.</p>
            </div>
          </div>
        </OperazioniCollectionPanel>
      </div>

      <ImportWhiteModal
        open={importOpen}
        onClose={(didImport) => {
          setImportOpen(false);
          if (didImport) {
            setPage(1);
            setReloadToken((current) => current + 1);
          }
        }}
      />
    </div>
  );
}

export default function SegnalazioniCruscottoPage() {
  return (
    <OperazioniModulePage
      title="Cruscotto segnalazioni"
      description="Vista operativa arricchita per import White, filtri avanzati e timeline delle sotto-azioni."
      breadcrumb="Cruscotto"
    >
      {() => <SegnalazioniCruscottoContent />}
    </OperazioniModulePage>
  );
}
