"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import {
  BarChart, Bar, LineChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, PieChart, Pie,
} from "recharts";

import { OperazioniModulePage } from "@/components/operazioni/operazioni-module-page";
import { MetricCard } from "@/components/ui/metric-card";
import {
  AlertTriangleIcon,
  TruckIcon,
  UsersIcon,
} from "@/components/ui/icons";
import {
  getAnalyticsSummary,
  getAnalyticsFuel,
  getAnalyticsKm,
  getAnalyticsWorkHours,
  getAnalyticsAnomalies,
  getAnalyticsAvailablePeriods,
  getUnresolvedTransactions,
  type PersistedUnresolvedRow,
} from "@/features/operazioni/api/client";

// ─── Period types ─────────────────────────────────────────────────────────────

interface QuarterPeriod { year: number; quarter: number; label: string; from_date: string; to_date: string }
interface MonthPeriod { year: number; month: number; label: string; from_date: string; to_date: string }
interface AvailablePeriods { years: number[]; quarters: QuarterPeriod[]; months: MonthPeriod[] }

// ─── Types ────────────────────────────────────────────────────────────────────

interface TimeSeriesPoint { period: string; value: number }
interface FuelStationUsageItem { station_name: string; refuel_count: number; total_liters: number; total_cost: number }
interface FuelRelatedUsageItem { id: string; label: string; refuel_count: number; total_liters: number; total_cost: number; avg_price_per_liter?: number | null; avg_refuel_cost?: number | null; avg_liters_per_refuel?: number | null; [key: string]: unknown }
interface FuelTopItem {
  id: string;
  label: string;
  total_liters: number;
  total_cost: number;
  refuel_count: number;
  total_km?: number | null;
  avg_consumption_l_per_100km?: number | null;
  consumption_coefficient?: number | null;
  consumption_judgement?: string | null;
  avg_price_per_liter?: number | null;
  avg_refuel_cost?: number | null;
  avg_liters_per_refuel?: number | null;
  top_stations?: FuelStationUsageItem[];
  related?: FuelRelatedUsageItem[];
  [key: string]: unknown
}
interface KmTopItem { id: string; label: string; total_km: number; session_count: number; avg_km_per_session?: number | null; [key: string]: unknown }
interface WorkHoursOperatorItem { operator_id: string; operator_name: string; total_hours: number; activity_count: number; [key: string]: unknown }
interface WorkHoursTeamItem { team_id: string; team_name: string; total_hours: number; operator_count: number; [key: string]: unknown }
interface WorkHoursCategoryItem { category: string; total_hours: number; activity_count: number; [key: string]: unknown }
interface AnomalyItem { id: string; type: string; severity: string; description: string; entity_id: string | null; entity_label: string | null; detected_at: string; details: Record<string, unknown> }

interface Summary {
  period_label: string; total_km: number; total_liters: number;
  total_fuel_cost: number; total_work_hours: number; active_sessions: number;
  anomaly_count: number; avg_consumption_l_per_100km: number | null;
}
interface FuelData { time_series: TimeSeriesPoint[]; cost_series: TimeSeriesPoint[]; top_vehicles: FuelTopItem[]; top_operators: FuelTopItem[]; total_liters: number; total_cost: number; avg_liters_per_refuel: number; storno_count?: number; storno_liters?: number; storno_cost?: number }
interface KmSessionExtremeItem { session_id: string; vehicle_label: string; operator_label?: string | null; started_at: string; ended_at: string; duration_minutes: number; km: number }
interface KmData {
  time_series: TimeSeriesPoint[];
  top_vehicles: KmTopItem[];
  top_operators: KmTopItem[];
  total_km: number;
  avg_km_per_session: number;
  longest_session?: KmSessionExtremeItem | null;
  shortest_session?: KmSessionExtremeItem | null;
}
interface WorkHoursData { time_series: TimeSeriesPoint[]; top_operators: WorkHoursOperatorItem[]; by_team: WorkHoursTeamItem[]; by_category: WorkHoursCategoryItem[]; total_hours: number; avg_hours_per_operator: number }
interface AnomaliesData { items: AnomalyItem[]; total: number; by_type: Record<string, number>; by_severity: Record<string, number> }

// ─── Constants ────────────────────────────────────────────────────────────────

const CHART_COLORS = ["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#06b6d4"];

const ANOMALY_LABELS: Record<string, string> = {
  orphan_session: "Sessione non chiusa",
  driver_mismatch: "Guidatore non autorizzato",
  excessive_fuel: "Rifornimento eccessivo",
  unmatched_refuel: "Rifornimento non abbinato",
  hours_discrepancy: "Discrepanza ore",
  inactive_vehicle: "Mezzo dismesso",
  inactive_operator: "Operatore non più attivo",
  orphan_fuel_card: "Tessera orfana",
};
const SEVERITY_BADGE: Record<string, string> = {
  high: "bg-rose-100 text-rose-700 border border-rose-200",
  medium: "bg-amber-100 text-amber-700 border border-amber-200",
  low: "bg-sky-100 text-sky-700 border border-sky-200",
};
const SEVERITY_LABEL: Record<string, string> = { high: "Alta", medium: "Media", low: "Bassa" };

function anomalyDetailChips(item: AnomalyItem): { label: string; value: string; href?: string }[] {
  const d = item.details as Record<string, unknown>;
  const chips: { label: string; value: string; href?: string }[] = [];
  switch (item.type) {
    case "orphan_session":
      if (d.hours_open != null) chips.push({ label: "Aperta da", value: `${Number(d.hours_open).toFixed(0)}h` });
      if (d.wc_id != null) chips.push({ label: "WC", value: String(d.wc_id), href: `https://login.bonificaoristanese.it/vehicles/taken-charge/edit/${d.wc_id}` });
      break;
    case "driver_mismatch":
      if (d.actual_driver) chips.push({ label: "Guidatore", value: String(d.actual_driver) });
      break;
    case "excessive_fuel":
      if (d.liters != null) chips.push({ label: "Litri", value: `${Number(d.liters).toLocaleString("it-IT", { maximumFractionDigits: 1 })} L` });
      if (d.cost != null) chips.push({ label: "Costo", value: `€ ${Number(d.cost).toLocaleString("it-IT", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` });
      if (d.station) chips.push({ label: "Stazione", value: String(d.station) });
      break;
    case "unmatched_refuel":
      if (d.operator) chips.push({ label: "Operatore", value: String(d.operator) });
      if (d.wc_id != null) chips.push({ label: "ID WC", value: String(d.wc_id) });
      break;
    case "hours_discrepancy":
      if (d.declared_min != null) chips.push({ label: "Dichiarate", value: `${Math.round(Number(d.declared_min) / 60 * 10) / 10}h` });
      if (d.calculated_min != null) chips.push({ label: "Calcolate", value: `${Math.round(Number(d.calculated_min) / 60 * 10) / 10}h` });
      if (d.diff_min != null) chips.push({ label: "Scarto", value: `${d.diff_min} min` });
      break;
    case "inactive_vehicle":
      if (d.vehicle_code) chips.push({ label: "Codice", value: String(d.vehicle_code) });
      if (d.liters != null) chips.push({ label: "Litri", value: `${Number(d.liters).toLocaleString("it-IT", { maximumFractionDigits: 1 })} L` });
      break;
    case "inactive_operator":
      if (d.vehicle) chips.push({ label: "Mezzo", value: String(d.vehicle) });
      if (d.liters != null) chips.push({ label: "Litri", value: `${Number(d.liters).toLocaleString("it-IT", { maximumFractionDigits: 1 })} L` });
      break;
    case "orphan_fuel_card":
      if (d.operator) chips.push({ label: "Operatore", value: String(d.operator) });
      if (Array.isArray(d.reasons) && d.reasons.length > 0) chips.push({ label: "Motivo", value: (d.reasons as string[]).join(", ") });
      break;
  }
  return chips;
}

type Tab = "carburante" | "km" | "ore" | "anomalie";

// ─── Sub-components ───────────────────────────────────────────────────────────

function SectionCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
      <h3 className="mb-4 text-sm font-semibold text-gray-800">{title}</h3>
      {children}
    </div>
  );
}

function SectionCardHeader({
  title,
  actions,
}: {
  title: string;
  actions?: React.ReactNode;
}) {
  return (
    <div className="mb-4 flex items-center justify-between gap-3">
      <h3 className="text-sm font-semibold text-gray-800">{title}</h3>
      {actions ? <div className="shrink-0">{actions}</div> : null}
    </div>
  );
}

function SectionShell({
  title,
  actions,
  children,
}: {
  title: string;
  actions?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
      <SectionCardHeader title={title} actions={actions} />
      {children}
    </div>
  );
}

function TopTable<T extends Record<string, unknown>>({
  rows,
  columns,
}: {
  rows: T[];
  columns: { key: keyof T; label: string; align?: "left" | "right"; format?: (v: T[keyof T]) => string }[];
}) {
  if (rows.length === 0) {
    return <p className="py-4 text-center text-sm text-gray-400">Nessun dato disponibile</p>;
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-100">
            {columns.map((col) => (
              <th key={String(col.key)} className={`pb-2 text-xs font-medium text-gray-500 ${col.align === "right" ? "text-right" : "text-left"}`}>
                {col.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="border-b border-gray-50 last:border-0">
              {columns.map((col) => (
                <td key={String(col.key)} className={`py-2 text-gray-700 ${col.align === "right" ? "text-right tabular-nums" : ""}`}>
                  {col.format ? col.format(row[col.key]) : String(row[col.key] ?? "—")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function LoadingCard() {
  return (
    <div className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
      <div className="animate-pulse space-y-3">
        <div className="h-4 w-1/3 rounded bg-gray-100" />
        <div className="h-32 w-full rounded bg-gray-100" />
      </div>
    </div>
  );
}

// ─── Unresolved transactions modal ────────────────────────────────────────────

function UnresolvedTransactionsModal({ onClose }: { onClose: () => void }) {
  const [items, setItems] = useState<PersistedUnresolvedRow[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getUnresolvedTransactions({ status_filter: "pending", page: 1, page_size: 10 })
      .then((d) => { setItems(d.items); setTotal(d.total); })
      .catch(() => null)
      .finally(() => setLoading(false));
  }, []);

  function fmtDate(iso: string | null) {
    if (!iso) return "—";
    return new Date(iso).toLocaleDateString("it-IT", { day: "2-digit", month: "2-digit", year: "numeric" });
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4">
      <div className="flex w-full max-w-2xl flex-col rounded-[20px] bg-white shadow-xl" style={{ maxHeight: "80vh" }}>
        <div className="flex items-center justify-between border-b border-[#e8ede7] px-6 py-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-500">Carburante</p>
            <p className="mt-0.5 text-sm font-semibold text-gray-900">
              Transazioni non identificate
              {total > 0 && (
                <span className="ml-2 rounded-full bg-amber-100 px-2 py-0.5 text-[11px] font-semibold text-amber-700">
                  {total} in attesa
                </span>
              )}
            </p>
          </div>
          <button onClick={onClose} className="rounded-full p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600">
            <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" /></svg>
          </button>
        </div>

        <div className="overflow-y-auto px-6 py-4">
          {loading ? (
            <p className="py-4 text-center text-sm text-gray-500">Caricamento...</p>
          ) : items.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-[#d8dfd8] bg-[#f8faf8] p-6 text-center text-sm text-gray-500">
              Nessuna transazione in attesa.
            </div>
          ) : (
            <div className="space-y-2">
              <p className="mb-3 text-xs text-gray-500">
                Queste righe sono state importate ma non è stato possibile identificare l&apos;operatore automaticamente.
                {total > 10 && ` Mostrate le prime 10 di ${total}.`}
              </p>
              <div className="overflow-x-auto rounded-[16px] border border-[#e6ebe5]">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-[#e6ebe5] bg-[#f9faf8]">
                      {["Targa", "Data", "Litri", "Motivo"].map((h) => (
                        <th key={h} className="px-3 py-2.5 text-left text-[10px] font-semibold uppercase tracking-[0.18em] text-gray-500">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#f0f3ef]">
                    {items.map((row) => (
                      <tr key={row.id} className="bg-white hover:bg-[#f9faf8]">
                        <td className="px-3 py-2 font-mono text-xs text-gray-700">{row.targa ?? "—"}</td>
                        <td className="px-3 py-2 text-xs text-gray-500 whitespace-nowrap">{fmtDate(row.fueled_at_iso)}</td>
                        <td className="px-3 py-2 font-mono text-xs text-gray-900">{row.liters ? `${row.liters} L` : "—"}</td>
                        <td className="px-3 py-2 max-w-[200px]">
                          <p className="truncate text-xs text-gray-400">{row.reason_detail}</p>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>

        <div className="flex items-center justify-between border-t border-[#e8ede7] px-6 py-4">
          <button onClick={onClose} className="btn-secondary text-sm">Chiudi</button>
          <Link
            href="/operazioni/mezzi/transazioni-non-risolte"
            onClick={onClose}
            className="btn-primary text-sm"
          >
            Vai alla coda di revisione →
          </Link>
        </div>
      </div>
    </div>
  );
}

// ─── Fuel operators table (with "Non identificato" special row) ────────────────

function FuelOperatorsTable({
  rows,
  onResolveClick,
}: {
  rows: FuelTopItem[];
  onResolveClick: () => void;
}) {
  if (rows.length === 0) {
    return <p className="py-4 text-center text-sm text-gray-400">Nessun dato disponibile</p>;
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-100">
            <th className="pb-2 text-left text-xs font-medium text-gray-500">Operatore</th>
            <th className="pb-2 text-right text-xs font-medium text-gray-500">Litri</th>
            <th className="pb-2 text-right text-xs font-medium text-gray-500">Km</th>
            <th className="pb-2 text-right text-xs font-medium text-gray-500">L/100km</th>
            <th className="pb-2 text-right text-xs font-medium text-gray-500">Consumo</th>
            <th className="pb-2 text-right text-xs font-medium text-gray-500">Costo</th>
            <th className="pb-2 text-right text-xs font-medium text-gray-500">€/L</th>
            <th className="pb-2 text-right text-xs font-medium text-gray-500">€ medio</th>
            <th className="pb-2 text-right text-xs font-medium text-gray-500">L medi</th>
            <th className="pb-2 text-right text-xs font-medium text-gray-500">Riforn.</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => {
            const isUnknown = row.id === "unknown";
            const price = row.avg_price_per_liter ?? null;
            const avgCost = row.avg_refuel_cost ?? null;
            const avgLiters = row.avg_liters_per_refuel ?? null;
            const km = (row.total_km as number | null | undefined) ?? null;
            const cons = (row.avg_consumption_l_per_100km as number | null | undefined) ?? null;
            const judge = (row.consumption_judgement as string | null | undefined) ?? null;
            return (
              <tr key={i} className="border-b border-gray-50 last:border-0">
                <td className="py-2 text-gray-700">
                  {isUnknown ? (
                    <span className="inline-flex flex-wrap items-baseline gap-1.5">
                      <span className="text-gray-400 italic">Non identificato</span>
                      <button
                        onClick={onResolveClick}
                        className="text-[11px] text-amber-600 underline underline-offset-2 hover:text-amber-800"
                      >
                        (risolvi anomalie)
                      </button>
                    </span>
                  ) : (
                    row.label
                  )}
                </td>
                <td className="py-2 text-right tabular-nums text-gray-700">
                  {Number(row.total_liters).toLocaleString("it-IT")} L
                </td>
                <td className="py-2 text-right tabular-nums text-gray-700">
                  {km !== null ? `${Number(km).toLocaleString("it-IT")} km` : "—"}
                </td>
                <td className="py-2 text-right tabular-nums text-gray-700">
                  {cons !== null ? `${Number(cons).toLocaleString("it-IT", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : "—"}
                </td>
                <td className="py-2 text-right text-xs">
                  {judge ? (
                    <span className={`rounded-full px-2 py-0.5 font-medium ${
                      judge === "OK" ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                      : judge === "Alto" ? "bg-amber-50 text-amber-700 border border-amber-200"
                      : "bg-rose-50 text-rose-700 border border-rose-200"
                    }`}>
                      {judge}
                    </span>
                  ) : "—"}
                </td>
                <td className="py-2 text-right tabular-nums text-gray-700">
                  € {Number(row.total_cost).toLocaleString("it-IT", { minimumFractionDigits: 2 })}
                </td>
                <td className="py-2 text-right tabular-nums text-gray-700">
                  {price !== null ? `€ ${Number(price).toLocaleString("it-IT", { minimumFractionDigits: 3, maximumFractionDigits: 3 })}` : "—"}
                </td>
                <td className="py-2 text-right tabular-nums text-gray-700">
                  {avgCost !== null ? `€ ${Number(avgCost).toLocaleString("it-IT", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : "—"}
                </td>
                <td className="py-2 text-right tabular-nums text-gray-700">
                  {avgLiters !== null ? `${Number(avgLiters).toLocaleString("it-IT", { maximumFractionDigits: 2 })} L` : "—"}
                </td>
                <td className="py-2 text-right tabular-nums text-gray-700">
                  {String(row.refuel_count)}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ─── Tab panels ───────────────────────────────────────────────────────────────

function CarburantePanel({ params }: { params: { from_date?: string; to_date?: string; granularity: "day" | "week" | "month" } }) {
  const [data, setData] = useState<FuelData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showUnresolved, setShowUnresolved] = useState(false);
  const [showAllStations, setShowAllStations] = useState(false);
  const [showAllRelations, setShowAllRelations] = useState(false);
  const { from_date, to_date, granularity } = params;

  useEffect(() => {
    setLoading(true);
    getAnalyticsFuel({ from_date, to_date, granularity })
      .then(setData)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [from_date, to_date, granularity]);

  if (loading) return <div className="grid gap-4 md:grid-cols-2"><LoadingCard /><LoadingCard /></div>;
  if (error || !data) return <p className="text-sm text-rose-600">{error ?? "Errore caricamento"}</p>;

  return (
    <div className="space-y-4">
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <MetricCard label="Litri netti" value={`${data.total_liters.toLocaleString("it-IT")} L`} sub="Rifornimenti − storni" />
        <MetricCard label="Costo netto" value={`€ ${data.total_cost.toLocaleString("it-IT", { minimumFractionDigits: 2 })}`} sub="Spesa carburante netta" variant="info" />
        <MetricCard label="Media per rifornimento" value={`${data.avg_liters_per_refuel} L`} sub="Litri medi (solo positivi)" />
      </div>

      {(data.storno_count ?? 0) > 0 && (
        <div className="grid gap-4 md:grid-cols-3">
          <div className="rounded-[20px] border border-amber-200 bg-amber-50 px-4 py-3">
            <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-amber-700">Storni</p>
            <p className="mt-1.5 text-2xl font-semibold text-amber-900">{data.storno_count}</p>
            <p className="mt-0.5 text-xs text-amber-700">transazioni di rettifica</p>
          </div>
          <div className="rounded-[20px] border border-amber-200 bg-amber-50 px-4 py-3">
            <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-amber-700">Litri stornati</p>
            <p className="mt-1.5 text-2xl font-semibold text-amber-900">{(data.storno_liters ?? 0).toLocaleString("it-IT")} L</p>
            <p className="mt-0.5 text-xs text-amber-700">volume rettificato</p>
          </div>
          <div className="rounded-[20px] border border-amber-200 bg-amber-50 px-4 py-3">
            <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-amber-700">Costo stornato</p>
            <p className="mt-1.5 text-2xl font-semibold text-amber-900">€ {(data.storno_cost ?? 0).toLocaleString("it-IT", { minimumFractionDigits: 2 })}</p>
            <p className="mt-0.5 text-xs text-amber-700">importo rettificato</p>
          </div>
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-2">
        <SectionCard title="Consumi carburante (litri)">
          {data.time_series.length === 0 ? (
            <p className="py-8 text-center text-sm text-gray-400">Nessun dato nel periodo</p>
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={data.time_series} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="period" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip formatter={(v: unknown) => [`${v} L`, "Litri"]} />
                <Bar dataKey="value" fill="#3b82f6" radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </SectionCard>

        <SectionCard title="Spesa carburante (€)">
          {data.cost_series.length === 0 ? (
            <p className="py-8 text-center text-sm text-gray-400">Nessun dato nel periodo</p>
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={data.cost_series} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="period" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip formatter={(v: unknown) => [`€ ${v}`, "Costo"]} />
                <Line type="monotone" dataKey="value" stroke="#10b981" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          )}
        </SectionCard>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <SectionCard title="Top veicoli per consumo">
          <TopTable
            rows={data.top_vehicles}
            columns={[
              { key: "label", label: "Targa / Mezzo" },
              { key: "total_liters", label: "Litri", align: "right", format: (v) => `${Number(v).toLocaleString("it-IT")} L` },
              { key: "total_km", label: "Km", align: "right", format: (v) => (v == null ? "—" : `${Number(v).toLocaleString("it-IT")} km`) },
              { key: "avg_consumption_l_per_100km", label: "L/100km", align: "right", format: (v) => (v == null ? "—" : `${Number(v).toLocaleString("it-IT", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`) },
              { key: "consumption_judgement", label: "Consumo", align: "right", format: (v) => (v == null ? "—" : String(v)) },
              { key: "total_cost", label: "Costo", align: "right", format: (v) => `€ ${Number(v).toLocaleString("it-IT", { minimumFractionDigits: 2 })}` },
              { key: "avg_price_per_liter", label: "€/L", align: "right", format: (v) => (v == null ? "—" : `€ ${Number(v).toLocaleString("it-IT", { minimumFractionDigits: 3, maximumFractionDigits: 3 })}`) },
              { key: "avg_refuel_cost", label: "€ medio", align: "right", format: (v) => (v == null ? "—" : `€ ${Number(v).toLocaleString("it-IT", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`) },
              { key: "avg_liters_per_refuel", label: "L medi", align: "right", format: (v) => (v == null ? "—" : `${Number(v).toLocaleString("it-IT", { maximumFractionDigits: 2 })} L`) },
              { key: "refuel_count", label: "Riforn.", align: "right" },
            ]}
          />
          {data.top_vehicles.some((v) => v.total_km == null) && (
            <p className="mt-2 text-xs text-gray-400">
              I mezzi con «—» km non hanno sessioni di utilizzo chiuse nel periodo selezionato.
            </p>
          )}
        </SectionCard>

        <SectionCard title="Top operatori per consumo">
          <FuelOperatorsTable rows={data.top_operators} onResolveClick={() => setShowUnresolved(true)} />
          {data.top_operators.some((o) => o.total_km == null) && (
            <p className="mt-2 text-xs text-gray-400">
              Gli operatori con «—» km non hanno sessioni di utilizzo abbinate nel periodo selezionato.
            </p>
          )}
        </SectionCard>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <SectionShell
          title="Stazioni di servizio più usate"
          actions={(
            <button
              onClick={() => setShowAllStations((s) => !s)}
              className="rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-700 hover:bg-gray-200"
            >
              {showAllStations ? "Mostra meno" : "Mostra tutti"}
            </button>
          )}
        >
          <TopTable
            rows={(showAllStations ? data.top_vehicles : data.top_vehicles.slice(0, 5)).flatMap((v) =>
              (v.top_stations ?? []).map((s) => ({
                vehicle: v.label,
                station: s.station_name,
                refuel_count: s.refuel_count,
                total_liters: s.total_liters,
                total_cost: s.total_cost,
              }))
            )}
            columns={[
              { key: "vehicle", label: "Mezzo" },
              { key: "station", label: "Stazione" },
              { key: "total_liters", label: "Litri", align: "right", format: (v) => `${Number(v).toLocaleString("it-IT")} L` },
              { key: "total_cost", label: "Costo", align: "right", format: (v) => `€ ${Number(v).toLocaleString("it-IT", { minimumFractionDigits: 2 })}` },
              { key: "refuel_count", label: "Riforn.", align: "right" },
            ]}
          />
          <p className="mt-2 text-xs text-gray-400">
            Mostra le stazioni più usate per ciascun mezzo (top mezzi nel periodo selezionato).
          </p>
        </SectionShell>

        <SectionShell
          title="Relazioni uso (operatore → mezzi)"
          actions={(
            <button
              onClick={() => setShowAllRelations((s) => !s)}
              className="rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-700 hover:bg-gray-200"
            >
              {showAllRelations ? "Mostra meno" : "Mostra tutti"}
            </button>
          )}
        >
          <div className="space-y-3">
            {(showAllRelations ? data.top_operators : data.top_operators.slice(0, 5)).map((op) => (
              <details key={op.id} className="group rounded-xl border border-gray-100 bg-gray-50">
                <summary className="flex cursor-pointer items-center justify-between gap-3 px-3 py-2 text-sm">
                  <div className="min-w-0">
                    <p className="truncate font-semibold text-gray-800">{op.label}</p>
                    <p className="mt-0.5 text-xs text-gray-500">
                      {Number(op.total_liters).toLocaleString("it-IT")} L · € {Number(op.total_cost).toLocaleString("it-IT", { minimumFractionDigits: 2 })} · {op.refuel_count} riforn.
                    </p>
                  </div>
                  <span className="rounded-full bg-white px-2 py-0.5 text-[11px] font-medium text-gray-600 border border-gray-200">
                    {(op.related?.length ?? 0) || 0} mezzi
                  </span>
                </summary>
                <div className="px-3 pb-3">
                  {(op.related?.length ?? 0) === 0 ? (
                    <p className="mt-1 text-xs text-gray-400">Nessun mezzo associabile nel periodo.</p>
                  ) : (
                    <TopTable
                      rows={(op.related ?? [])}
                      columns={[
                        { key: "label", label: "Mezzo" },
                        { key: "total_liters", label: "Litri", align: "right", format: (v) => `${Number(v).toLocaleString("it-IT")} L` },
                        { key: "total_cost", label: "Costo", align: "right", format: (v) => `€ ${Number(v).toLocaleString("it-IT", { minimumFractionDigits: 2 })}` },
                        { key: "avg_price_per_liter", label: "€/L", align: "right", format: (v) => (v == null ? "—" : `€ ${Number(v).toLocaleString("it-IT", { minimumFractionDigits: 3, maximumFractionDigits: 3 })}`) },
                        { key: "avg_liters_per_refuel", label: "L medi", align: "right", format: (v) => (v == null ? "—" : `${Number(v).toLocaleString("it-IT", { maximumFractionDigits: 2 })} L`) },
                        { key: "refuel_count", label: "Riforn.", align: "right" },
                      ]}
                    />
                  )}
                </div>
              </details>
            ))}
          </div>
          <p className="mt-2 text-xs text-gray-400">
            Clicca su un operatore per espandere il dettaglio dei mezzi e consumi nel periodo selezionato.
          </p>
        </SectionShell>
      </div>

      {showUnresolved && <UnresolvedTransactionsModal onClose={() => setShowUnresolved(false)} />}
    </div>
  );
}

function KmPanel({ params }: { params: { from_date?: string; to_date?: string; granularity: "day" | "week" | "month" } }) {
  const [data, setData] = useState<KmData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { from_date, to_date, granularity } = params;

  useEffect(() => {
    setLoading(true);
    getAnalyticsKm({ from_date, to_date, granularity })
      .then(setData)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [from_date, to_date, granularity]);

  if (loading) return <div className="grid gap-4 md:grid-cols-2"><LoadingCard /><LoadingCard /></div>;
  if (error || !data) return <p className="text-sm text-rose-600">{error ?? "Errore caricamento"}</p>;

  function fmtDuration(min: number) {
    const h = Math.floor(min / 60);
    const m = min % 60;
    if (h <= 0) return `${m} min`;
    if (m === 0) return `${h} h`;
    return `${h} h ${m} min`;
  }

  return (
    <div className="space-y-4">
      <div className="grid gap-4 md:grid-cols-2">
        <MetricCard label="Km totali" value={`${data.total_km.toLocaleString("it-IT")} km`} sub="Nel periodo selezionato" />
        <MetricCard label="Media per sessione" value={`${data.avg_km_per_session} km`} sub="Km medi per uscita" variant="info" />
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <SectionCard title="Sessione più lunga">
          {!data.longest_session ? (
            <p className="py-6 text-center text-sm text-gray-400">Nessun dato disponibile</p>
          ) : (
            <div className="space-y-1 text-sm text-gray-700">
              <p><span className="text-gray-400">Mezzo</span> {data.longest_session.vehicle_label}</p>
              <p><span className="text-gray-400">Operatore</span> {data.longest_session.operator_label ?? "—"}</p>
              <p><span className="text-gray-400">Durata</span> {fmtDuration(data.longest_session.duration_minutes)}</p>
              <p><span className="text-gray-400">Km</span> {Number(data.longest_session.km).toLocaleString("it-IT")} km</p>
            </div>
          )}
        </SectionCard>

        <SectionCard title="Sessione più corta">
          {!data.shortest_session ? (
            <p className="py-6 text-center text-sm text-gray-400">Nessun dato disponibile</p>
          ) : (
            <div className="space-y-1 text-sm text-gray-700">
              <p><span className="text-gray-400">Mezzo</span> {data.shortest_session.vehicle_label}</p>
              <p><span className="text-gray-400">Operatore</span> {data.shortest_session.operator_label ?? "—"}</p>
              <p><span className="text-gray-400">Durata</span> {fmtDuration(data.shortest_session.duration_minutes)}</p>
              <p><span className="text-gray-400">Km</span> {Number(data.shortest_session.km).toLocaleString("it-IT")} km</p>
            </div>
          )}
        </SectionCard>
      </div>

      <SectionCard title="Chilometri percorsi per periodo">
        {data.time_series.length === 0 ? (
          <p className="py-8 text-center text-sm text-gray-400">Nessun dato nel periodo</p>
        ) : (
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={data.time_series} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="period" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip formatter={(v: unknown) => [`${v} km`, "Km"]} />
              <Bar dataKey="value" fill="#8b5cf6" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </SectionCard>

      <div className="grid gap-4 lg:grid-cols-2">
        <SectionCard title="Top veicoli per km">
          <TopTable
            rows={data.top_vehicles}
            columns={[
              { key: "label", label: "Targa / Mezzo" },
              { key: "total_km", label: "Km", align: "right", format: (v) => `${Number(v).toLocaleString("it-IT")} km` },
              { key: "avg_km_per_session", label: "Km/sessione", align: "right", format: (v) => (v == null ? "—" : `${Number(v).toLocaleString("it-IT")} km`) },
              { key: "session_count", label: "Sessioni", align: "right" },
            ]}
          />
        </SectionCard>

        <SectionCard title="Top operatori per km">
          <TopTable
            rows={data.top_operators}
            columns={[
              { key: "label", label: "Operatore" },
              { key: "total_km", label: "Km", align: "right", format: (v) => `${Number(v).toLocaleString("it-IT")} km` },
              { key: "avg_km_per_session", label: "Km/sessione", align: "right", format: (v) => (v == null ? "—" : `${Number(v).toLocaleString("it-IT")} km`) },
              { key: "session_count", label: "Sessioni", align: "right" },
            ]}
          />
        </SectionCard>
      </div>
    </div>
  );
}

function OrePanel({ params }: { params: { from_date?: string; to_date?: string; granularity: "day" | "week" | "month" } }) {
  const [data, setData] = useState<WorkHoursData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { from_date, to_date, granularity } = params;

  useEffect(() => {
    setLoading(true);
    getAnalyticsWorkHours({ from_date, to_date, granularity })
      .then(setData)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [from_date, to_date, granularity]);

  if (loading) return <div className="grid gap-4 md:grid-cols-2"><LoadingCard /><LoadingCard /></div>;
  if (error || !data) return <p className="text-sm text-rose-600">{error ?? "Errore caricamento"}</p>;

  return (
    <div className="space-y-4">
      <div className="grid gap-4 md:grid-cols-2">
        <MetricCard label="Ore totali" value={`${data.total_hours.toLocaleString("it-IT")} h`} sub="Nel periodo selezionato" />
        <MetricCard label="Media per operatore" value={`${data.avg_hours_per_operator} h`} sub="Ore medie registrate" variant="info" />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <SectionCard title="Ore lavoro per periodo">
          {data.time_series.length === 0 ? (
            <p className="py-8 text-center text-sm text-gray-400">Nessun dato nel periodo</p>
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={data.time_series} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="period" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip formatter={(v: unknown) => [`${v} h`, "Ore"]} />
                <Line type="monotone" dataKey="value" stroke="#f59e0b" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          )}
        </SectionCard>

        <SectionCard title="Distribuzione per categoria">
          {data.by_category.length === 0 ? (
            <p className="py-8 text-center text-sm text-gray-400">Nessun dato disponibile</p>
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie
                  data={data.by_category.map((item, i) => ({ ...item, fill: CHART_COLORS[i % CHART_COLORS.length] }))}
                  dataKey="total_hours"
                  nameKey="category"
                  cx="50%" cy="50%" outerRadius={80}
                  label={(entry) => `${String(entry.name ?? "")} ${((entry.percent ?? 0) * 100).toFixed(0)}%`}
                  labelLine={false}
                />
                <Tooltip formatter={(v: unknown) => [`${v} h`, "Ore"]} />
              </PieChart>
            </ResponsiveContainer>
          )}
        </SectionCard>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <SectionCard title="Top operatori per ore">
          <TopTable
            rows={data.top_operators}
            columns={[
              { key: "operator_name", label: "Operatore" },
              { key: "total_hours", label: "Ore", align: "right", format: (v) => `${Number(v).toLocaleString("it-IT")} h` },
              { key: "activity_count", label: "Attività", align: "right" },
            ]}
          />
        </SectionCard>

        <SectionCard title="Ore per team">
          {data.by_team.length === 0 ? (
            <p className="py-4 text-center text-sm text-gray-400">Nessun dato team disponibile</p>
          ) : (
            <TopTable
              rows={data.by_team}
              columns={[
                { key: "team_name", label: "Team" },
                { key: "total_hours", label: "Ore", align: "right", format: (v) => `${Number(v).toLocaleString("it-IT")} h` },
                { key: "operator_count", label: "Operatori", align: "right" },
              ]}
            />
          )}
        </SectionCard>
      </div>
    </div>
  );
}

function AnomaliePanel({ params }: { params: { from_date?: string; to_date?: string } }) {
  const [data, setData] = useState<AnomaliesData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [typeFilter, setTypeFilter] = useState("");
  const { from_date, to_date } = params;

  const load = useCallback((filter: string) => {
    setLoading(true);
    getAnalyticsAnomalies({ from_date, to_date, ...(filter ? { type: filter } : {}) })
      .then(setData)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [from_date, to_date]);

  useEffect(() => { load(typeFilter); }, [load, typeFilter]);

  if (loading) return <LoadingCard />;
  if (error || !data) return <p className="text-sm text-rose-600">{error ?? "Errore caricamento"}</p>;

  const sevData = Object.entries(data.by_severity).map(([k, v]) => ({
    name: SEVERITY_LABEL[k] ?? k,
    value: v,
    color: k === "high" ? "#ef4444" : k === "medium" ? "#f59e0b" : "#3b82f6",
  }));

  return (
    <div className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-3">
        <MetricCard label="Totale anomalie" value={data.total} sub="Nel periodo selezionato" variant={data.total > 0 ? "warning" : "success"} />
        <MetricCard label="Alta severità" value={data.by_severity.high ?? 0} sub="Richiedono attenzione immediata" variant={data.by_severity.high > 0 ? "danger" : "default"} />
        <MetricCard label="Media severità" value={data.by_severity.medium ?? 0} sub="Da verificare" variant={data.by_severity.medium > 0 ? "warning" : "default"} />
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <SectionCard title="Anomalie per severità">
          {sevData.length === 0 ? (
            <p className="py-8 text-center text-sm text-gray-400">Nessuna anomalia</p>
          ) : (
            <ResponsiveContainer width="100%" height={180}>
              <PieChart>
                <Pie
                  data={sevData.map((d) => ({ ...d, fill: d.color }))}
                  dataKey="value"
                  nameKey="name"
                  cx="50%" cy="50%" outerRadius={70}
                />
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          )}
        </SectionCard>

        <div className="lg:col-span-2">
          <SectionCard title="Distribuzione per tipo">
            <div className="space-y-2">
              {Object.entries(data.by_type).map(([type, count]) => (
                <div key={type} className="flex items-center justify-between text-sm">
                  <span className="text-gray-700">{ANOMALY_LABELS[type] ?? type}</span>
                  <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600">{count}</span>
                </div>
              ))}
              {Object.keys(data.by_type).length === 0 && (
                <p className="py-4 text-center text-sm text-gray-400">Nessuna anomalia rilevata</p>
              )}
            </div>
          </SectionCard>
        </div>
      </div>

      <SectionCard title="Lista anomalie rilevate">
        {/* Filter */}
        <div className="mb-4 flex flex-wrap gap-2">
          {["", "orphan_session", "driver_mismatch", "excessive_fuel", "unmatched_refuel", "hours_discrepancy"].map((t) => (
            <button
              key={t}
              onClick={() => setTypeFilter(t)}
              className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${typeFilter === t ? "bg-gray-800 text-white" : "bg-gray-100 text-gray-600 hover:bg-gray-200"}`}
            >
              {t ? ANOMALY_LABELS[t] ?? t : "Tutte"}
            </button>
          ))}
        </div>

        {data.items.length === 0 ? (
          <div className="flex flex-col items-center py-10 text-center">
            <span className="material-symbols-outlined text-4xl text-emerald-400">check_circle</span>
            <p className="mt-2 text-sm font-medium text-gray-700">Nessuna anomalia nel periodo</p>
            <p className="text-xs text-gray-400">Il sistema non ha rilevato usi anomali nel periodo selezionato.</p>
          </div>
        ) : (
          <div className="space-y-2">
            {data.items.map((item) => {
              const chips = anomalyDetailChips(item);
              return (
                <div key={item.id} className="flex items-start gap-3 rounded-xl border border-gray-100 bg-gray-50 p-3">
                  <AlertTriangleIcon className={`mt-0.5 h-4 w-4 shrink-0 ${item.severity === "high" ? "text-rose-500" : item.severity === "medium" ? "text-amber-500" : "text-sky-500"}`} />
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-sm font-medium text-gray-800">{item.description}</span>
                      <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${SEVERITY_BADGE[item.severity] ?? ""}`}>
                        {SEVERITY_LABEL[item.severity] ?? item.severity}
                      </span>
                    </div>
                    <p className="mt-0.5 text-xs text-gray-500">
                      {ANOMALY_LABELS[item.type] ?? item.type}
                      {item.entity_label ? ` · ${item.entity_label}` : ""}
                      {" · "}{new Date(item.detected_at).toLocaleDateString("it-IT")}
                    </p>
                    {chips.length > 0 && (
                      <div className="mt-2 flex flex-wrap gap-1.5">
                        {chips.map((chip) =>
                          chip.href ? (
                            <a
                              key={chip.label}
                              href={chip.href}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center gap-1 rounded-md border border-sky-200 bg-sky-50 px-2 py-0.5 text-[11px] text-sky-700 hover:bg-sky-100"
                            >
                              <span className="font-medium text-sky-400">{chip.label}</span>
                              {chip.value} ↗
                            </a>
                          ) : (
                            <span key={chip.label} className="inline-flex items-center gap-1 rounded-md border border-gray-200 bg-white px-2 py-0.5 text-[11px] text-gray-600">
                              <span className="font-medium text-gray-400">{chip.label}</span>
                              {chip.value}
                            </span>
                          )
                        )}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </SectionCard>
    </div>
  );
}

// ─── Main page content ────────────────────────────────────────────────────────

type QuickFilterType = "year" | "quarter" | "month";
interface ActiveQuickFilter { type: QuickFilterType; key: string }

function AnalisiContent() {
  const today = new Date();
  const defaultFrom = new Date(today.getFullYear(), today.getMonth() - 2, 1).toISOString().split("T")[0];
  const defaultTo = today.toISOString().split("T")[0];

  const [fromDate, setFromDate] = useState(defaultFrom);
  const [toDate, setToDate] = useState(defaultTo);
  const [granularity, setGranularity] = useState<"day" | "week" | "month">("month");
  const [activeTab, setActiveTab] = useState<Tab>("carburante");
  const [summary, setSummary] = useState<Summary | null>(null);
  const [summaryLoading, setSummaryLoading] = useState(true);
  const [periods, setPeriods] = useState<AvailablePeriods | null>(null);
  const [activeQuickFilter, setActiveQuickFilter] = useState<ActiveQuickFilter | null>(null);
  const [quickFilterType, setQuickFilterType] = useState<QuickFilterType>("month");

  const params = { from_date: fromDate, to_date: toDate, granularity };

  useEffect(() => {
    getAnalyticsAvailablePeriods()
      .then((data) => setPeriods(data as AvailablePeriods))
      .catch(() => null);
  }, []);

  useEffect(() => {
    setSummaryLoading(true);
    getAnalyticsSummary({ from_date: fromDate, to_date: toDate })
      .then(setSummary)
      .catch(() => null)
      .finally(() => setSummaryLoading(false));
  }, [fromDate, toDate]);

  function applyQuickFilter(from: string, to: string, key: string, type: QuickFilterType, gran: "day" | "week" | "month") {
    setFromDate(from);
    setToDate(to);
    setGranularity(gran);
    setActiveQuickFilter({ type, key });
  }

  function handleManualDateChange(field: "from" | "to", value: string) {
    if (field === "from") setFromDate(value);
    else setToDate(value);
    setActiveQuickFilter(null);
  }

  const tabs: { id: Tab; label: string; icon: React.FC<{ className?: string }> }[] = [
    { id: "carburante", label: "Carburante", icon: TruckIcon },
    { id: "km", label: "Chilometri", icon: TruckIcon },
    { id: "ore", label: "Ore lavoro", icon: UsersIcon },
    { id: "anomalie", label: "Anomalie", icon: AlertTriangleIcon },
  ];

  return (
    <div className="page-stack">
      {/* Header / filters */}
      <div className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
        {/* Row 1: title + date controls */}
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h2 className="text-base font-semibold text-gray-900">Analisi operazioni</h2>
            {summary && !summaryLoading && (
              <p className="mt-0.5 text-xs text-gray-500">{summary.period_label}</p>
            )}
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-2 text-sm">
              <label className="text-gray-500">Dal</label>
              <input
                type="date"
                value={fromDate}
                onChange={(e) => handleManualDateChange("from", e.target.value)}
                className="rounded-lg border border-gray-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div className="flex items-center gap-2 text-sm">
              <label className="text-gray-500">Al</label>
              <input
                type="date"
                value={toDate}
                onChange={(e) => handleManualDateChange("to", e.target.value)}
                className="rounded-lg border border-gray-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <select
              value={granularity}
              onChange={(e) => setGranularity(e.target.value as "day" | "week" | "month")}
              className="rounded-lg border border-gray-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="day">Giornaliero</option>
              <option value="week">Settimanale</option>
              <option value="month">Mensile</option>
            </select>
          </div>
        </div>

        {/* Row 2: quick filters */}
        {periods && (periods.years.length > 0 || periods.quarters.length > 0 || periods.months.length > 0) && (
          <div className="mt-4 border-t border-gray-100 pt-4">
            {/* Type selector */}
            <div className="mb-3 flex items-center gap-1">
              {(["year", "quarter", "month"] as QuickFilterType[]).map((t) => (
                <button
                  key={t}
                  onClick={() => setQuickFilterType(t)}
                  className={`rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
                    quickFilterType === t
                      ? "bg-gray-800 text-white"
                      : "text-gray-500 hover:text-gray-800"
                  }`}
                >
                  {t === "year" ? "Anno" : t === "quarter" ? "Trimestre" : "Mese"}
                </button>
              ))}
            </div>

            {/* Period chips */}
            <div className="flex flex-wrap gap-1.5">
              {quickFilterType === "year" && periods.years.map((y) => {
                const key = `year-${y}`;
                const isActive = activeQuickFilter?.key === key;
                return (
                  <button
                    key={key}
                    onClick={() => applyQuickFilter(`${y}-01-01`, `${y}-12-31`, key, "year", "month")}
                    className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                      isActive
                        ? "bg-blue-600 text-white"
                        : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                    }`}
                  >
                    {y}
                  </button>
                );
              })}

              {quickFilterType === "quarter" && periods.quarters.map((q) => {
                const key = `q-${q.year}-${q.quarter}`;
                const isActive = activeQuickFilter?.key === key;
                return (
                  <button
                    key={key}
                    onClick={() => applyQuickFilter(q.from_date, q.to_date, key, "quarter", "month")}
                    className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                      isActive
                        ? "bg-blue-600 text-white"
                        : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                    }`}
                  >
                    {q.label}
                  </button>
                );
              })}

              {quickFilterType === "month" && periods.months.map((m) => {
                const key = `m-${m.year}-${m.month}`;
                const isActive = activeQuickFilter?.key === key;
                return (
                  <button
                    key={key}
                    onClick={() => applyQuickFilter(m.from_date, m.to_date, key, "month", "day")}
                    className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                      isActive
                        ? "bg-blue-600 text-white"
                        : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                    }`}
                  >
                    {m.label}
                  </button>
                );
              })}
            </div>
          </div>
        )}

      </div>

      {/* KPI strip */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-7">
        {summaryLoading ? (
          Array.from({ length: 7 }).map((_, i) => (
            <div key={i} className="h-20 animate-pulse rounded-2xl border border-gray-200 bg-white" />
          ))
        ) : summary ? (
          <>
            <MetricCard label="Km totali" value={`${summary.total_km.toLocaleString("it-IT")} km`} />
            <MetricCard label="Litri totali" value={`${summary.total_liters.toLocaleString("it-IT")} L`} />
            <MetricCard label="Spesa carburante" value={`€ ${summary.total_fuel_cost.toLocaleString("it-IT", { minimumFractionDigits: 0 })}`} variant="info" />
            <MetricCard label="Ore lavoro" value={`${summary.total_work_hours.toLocaleString("it-IT")} h`} />
            <MetricCard label="Sessioni attive" value={summary.active_sessions} variant={summary.active_sessions > 0 ? "warning" : "default"} />
            <MetricCard label="Anomalie" value={summary.anomaly_count} variant={summary.anomaly_count > 0 ? "danger" : "success"} />
            <MetricCard
              label="L/100km"
              value={summary.avg_consumption_l_per_100km !== null ? `${summary.avg_consumption_l_per_100km}` : "—"}
              sub="Consumo medio"
              variant="info"
            />
          </>
        ) : null}
      </div>

      {/* Tabs */}
      <div className="rounded-2xl border border-gray-200 bg-white shadow-sm">
        <div className="flex border-b border-gray-100">
          {tabs.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setActiveTab(id)}
              className={`flex items-center gap-2 px-5 py-3 text-sm font-medium transition-colors ${
                activeTab === id
                  ? "border-b-2 border-blue-600 text-blue-600"
                  : "text-gray-500 hover:text-gray-800"
              }`}
            >
              <Icon className="h-3.5 w-3.5" />
              {label}
              {id === "anomalie" && summary && summary.anomaly_count > 0 && (
                <span className="rounded-full bg-rose-100 px-1.5 py-0.5 text-[10px] font-semibold text-rose-700">
                  {summary.anomaly_count}
                </span>
              )}
            </button>
          ))}
        </div>
        <div className="p-5">
          {activeTab === "carburante" && <CarburantePanel params={params} />}
          {activeTab === "km" && <KmPanel params={params} />}
          {activeTab === "ore" && <OrePanel params={params} />}
          {activeTab === "anomalie" && <AnomaliePanel params={{ from_date: fromDate, to_date: toDate }} />}
        </div>
      </div>
    </div>
  );
}

// ─── Page export ──────────────────────────────────────────────────────────────

export default function AnalisiPage() {
  return (
    <OperazioniModulePage
      title="Analisi operazioni"
      description="Consumi carburante, chilometri, ore lavoro e anomalie operative per operatore e team."
      breadcrumb="Analisi"
    >
      {() => <AnalisiContent />}
    </OperazioniModulePage>
  );
}
