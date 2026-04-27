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
  getOperatorDetail,
  type OperatorDetailResponse,
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
  total_fuel_cost: number; total_work_hours: number; work_hours_source?: string;
  active_sessions: number; anomaly_count: number; avg_consumption_l_per_100km: number | null;
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
      if (d.operator_name) chips.push({ label: "Ultimo operatore", value: String(d.operator_name) });
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

function InlineHelp({ text }: { text: string }) {
  return (
    <span
      title={text}
      className="inline-flex h-4 w-4 items-center justify-center rounded-full border border-gray-300 bg-white text-[10px] font-semibold text-gray-500 cursor-help"
    >
      ?
    </span>
  );
}

function formatOperatorMetricNumber(value: string | null | undefined, suffix?: string): string {
  if (value == null || value === "") {
    return "—";
  }
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) {
    return "—";
  }
  const formatted = parsed.toLocaleString("it-IT", {
    minimumFractionDigits: Number.isInteger(parsed) ? 0 : 1,
    maximumFractionDigits: Number.isInteger(parsed) ? 0 : 1,
  });
  return suffix ? `${formatted} ${suffix}` : formatted;
}

function formatOperatorCurrency(value: string | null | undefined): string {
  if (value == null || value === "") {
    return "—";
  }
  const parsed = Number(value);
  return Number.isFinite(parsed)
    ? new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR", maximumFractionDigits: 2 }).format(parsed)
    : "—";
}

function OperatorQuickModal({
  open,
  operatorId,
  operatorName,
  onClose,
}: {
  open: boolean;
  operatorId: string | null;
  operatorName: string | null;
  onClose: () => void;
}) {
  const [detail, setDetail] = useState<OperatorDetailResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open || !operatorId) {
      setDetail(null);
      setError(null);
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    void getOperatorDetail(operatorId)
      .then((payload) => setDetail(payload))
      .catch((currentError) => {
        setError(currentError instanceof Error ? currentError.message : "Errore nel caricamento operatore");
      })
      .finally(() => setLoading(false));
  }, [open, operatorId]);

  useEffect(() => {
    if (!open) {
      return;
    }
    function handleKeyDown(event: KeyboardEvent): void {
      if (event.key === "Escape") {
        onClose();
      }
    }
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", handleKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [open, onClose]);

  if (!open) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-[80] flex items-center justify-center bg-black/40 p-4 backdrop-blur-sm">
      <div className="flex w-full max-w-3xl flex-col overflow-hidden rounded-[24px] border border-gray-200 bg-white shadow-xl">
        <div className="flex items-start justify-between gap-4 border-b border-gray-100 px-6 py-5">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#1D4E35]">Operatore collegato</p>
            <h2 className="mt-2 text-xl font-semibold text-gray-900">{operatorName || "Operatore"}</h2>
            <p className="mt-1 text-sm text-gray-500">Dettaglio rapido dalla lista anomalie.</p>
          </div>
          <button className="btn-secondary" type="button" onClick={onClose}>
            Chiudi
          </button>
        </div>

        <div className="bg-[#f7faf7] px-6 py-6">
          {loading ? (
            <div className="rounded-2xl border border-[#e4e8e2] bg-white px-4 py-5 text-sm text-gray-500">Caricamento operatore.</div>
          ) : error ? (
            <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-5 text-sm text-rose-700">{error}</div>
          ) : !detail ? (
            <div className="rounded-2xl border border-[#e4e8e2] bg-white px-4 py-5 text-sm text-gray-500">Dettaglio non disponibile.</div>
          ) : (
            <div className="space-y-4">
              <div className="grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
                <div className="rounded-2xl border border-[#e4e8e2] bg-white p-4">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#667267]">Profilo</p>
                  <div className="mt-3 space-y-2 text-sm text-gray-600">
                    <p><span className="font-medium text-gray-900">Ruolo:</span> {detail.operator.role ?? "—"}</p>
                    <p><span className="font-medium text-gray-900">Email:</span> {detail.operator.email ?? "—"}</p>
                    <p><span className="font-medium text-gray-900">Username:</span> {detail.operator.username ?? "—"}</p>
                    <p><span className="font-medium text-gray-900">Stato:</span> {detail.operator.enabled ? "Abilitato" : "Disabilitato"}</p>
                  </div>
                  <div className="mt-4 flex flex-wrap gap-2">
                    {detail.current_fuel_cards.length > 0 ? detail.current_fuel_cards.map((card) => (
                      <span key={card.id} className="rounded-full border border-[#d5e2d8] bg-[#edf5f0] px-3 py-1 text-xs font-semibold text-[#1D4E35]">
                        {card.codice || card.pan}
                      </span>
                    )) : (
                      <span className="text-xs text-gray-500">Nessuna fuel card assegnata.</span>
                    )}
                  </div>
                </div>

                <div className="rounded-2xl border border-[#e4e8e2] bg-white p-4">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#667267]">Sintesi</p>
                  <div className="mt-3 grid gap-3 sm:grid-cols-2">
                    <div className="rounded-xl border border-[#eef2ec] bg-[#fafbf8] px-3 py-2.5">
                      <p className="text-[10px] uppercase tracking-[0.14em] text-gray-500">Km</p>
                      <p className="mt-1 text-lg font-semibold text-gray-900">{formatOperatorMetricNumber(detail.stats.total_km_travelled, "km")}</p>
                    </div>
                    <div className="rounded-xl border border-[#eef2ec] bg-[#fafbf8] px-3 py-2.5">
                      <p className="text-[10px] uppercase tracking-[0.14em] text-gray-500">Litri</p>
                      <p className="mt-1 text-lg font-semibold text-gray-900">{formatOperatorMetricNumber(detail.stats.total_liters, "L")}</p>
                    </div>
                    <div className="rounded-xl border border-[#eef2ec] bg-[#fafbf8] px-3 py-2.5">
                      <p className="text-[10px] uppercase tracking-[0.14em] text-gray-500">Costo</p>
                      <p className="mt-1 text-lg font-semibold text-gray-900">{formatOperatorCurrency(detail.stats.total_fuel_cost)}</p>
                    </div>
                    <div className="rounded-xl border border-[#eef2ec] bg-[#fafbf8] px-3 py-2.5">
                      <p className="text-[10px] uppercase tracking-[0.14em] text-gray-500">Mezzo più usato</p>
                      <p className="mt-1 text-sm font-semibold text-gray-900">{detail.stats.most_used_vehicle?.vehicle_label ?? "—"}</p>
                    </div>
                  </div>
                </div>
              </div>

              <div className="flex items-center justify-end gap-3">
                <Link
                  href={`/operazioni/operatori?operatorId=${operatorId}&from=analisi`}
                  onClick={onClose}
                  className="btn-primary text-sm"
                >
                  Apri pagina operatore
                </Link>
              </div>
            </div>
          )}
        </div>
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

function formatLiters(value: number | null | undefined): string {
  return value == null ? "—" : `${Number(value).toLocaleString("it-IT", { maximumFractionDigits: 2 })} L`;
}

function formatKilometers(value: number | null | undefined): string {
  return value == null
    ? "—"
    : `${Number(value).toLocaleString("it-IT", { minimumFractionDigits: 1, maximumFractionDigits: 1 })} km`;
}

function formatEuro(value: number | null | undefined, digits = 2): string {
  return value == null ? "—" : `€ ${Number(value).toLocaleString("it-IT", { minimumFractionDigits: digits, maximumFractionDigits: digits })}`;
}

function formatConsumption(value: number | null | undefined): string {
  return value == null ? "—" : Number(value).toLocaleString("it-IT", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function consumptionTone(judgement: string | null | undefined): string {
  if (judgement === "OK") return "border-emerald-200 bg-emerald-50 text-emerald-700";
  if (judgement === "Alto") return "border-amber-200 bg-amber-50 text-amber-700";
  if (judgement) return "border-rose-200 bg-rose-50 text-rose-700";
  return "border-gray-200 bg-white text-gray-500";
}

function asNumber(value: number | null | undefined): number {
  return value ?? Number.NEGATIVE_INFINITY;
}

function VehicleConsumptionExplorer({ rows }: { rows: FuelTopItem[] }) {
  const [showAll, setShowAll] = useState(false);
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const [search, setSearch] = useState("");
  const [sortBy, setSortBy] = useState("liters_desc");

  if (rows.length === 0) {
    return <p className="py-4 text-center text-sm text-gray-400">Nessun dato disponibile</p>;
  }

  const normalizedSearch = search.trim().toLowerCase();
  const filteredRows = normalizedSearch
    ? rows.filter((row) => row.label.toLowerCase().includes(normalizedSearch))
    : rows;
  const sortedRows = [...filteredRows].sort((a, b) => {
    switch (sortBy) {
      case "name_asc":
        return a.label.localeCompare(b.label, "it");
      case "km_desc":
        return asNumber((b.total_km as number | null | undefined) ?? null) - asNumber((a.total_km as number | null | undefined) ?? null);
      case "cost_desc":
        return asNumber(b.total_cost) - asNumber(a.total_cost);
      case "refuels_desc":
        return b.refuel_count - a.refuel_count;
      case "consumption_desc":
        return asNumber((b.avg_consumption_l_per_100km as number | null | undefined) ?? null) - asNumber((a.avg_consumption_l_per_100km as number | null | undefined) ?? null);
      case "liters_desc":
      default:
        return asNumber(b.total_liters) - asNumber(a.total_liters);
    }
  });
  const visibleRows = showAll || normalizedSearch ? sortedRows : sortedRows.slice(0, 6);

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-3">
        <p className="flex items-center gap-2 text-xs text-gray-500">
          <span>Ogni riga mostra il riepilogo consumo; espandi per vedere le stazioni più usate.</span>
          <InlineHelp text="L/100km indica i litri consumati ogni 100 km. Consumo confronta il valore rilevato con un riferimento atteso per quel tipo di mezzo. €/L è il costo medio per litro, € medio il costo medio per rifornimento, L medi i litri medi per rifornimento." />
        </p>
        {rows.length > 6 ? (
          <button
            type="button"
            onClick={() => setShowAll((current) => !current)}
            className="rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-700 transition hover:bg-gray-200"
          >
            {showAll ? "Mostra meno" : `Mostra tutti (${rows.length})`}
          </button>
        ) : null}
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3 rounded-[18px] border border-[#e8ede7] bg-[#f8faf8] px-3 py-3">
        <label className="min-w-[220px] flex-1">
          <span className="sr-only">Cerca veicolo</span>
          <input
            type="text"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Cerca targa o mezzo"
            className="w-full rounded-full border border-gray-200 bg-white px-3 py-2 text-sm text-gray-700 outline-none transition focus:border-[#9db7a5] focus:ring-2 focus:ring-[#dbe9de]"
          />
        </label>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-xs text-gray-500">
            <span>Ordina</span>
            <select
              value={sortBy}
              onChange={(event) => setSortBy(event.target.value)}
              className="rounded-full border border-gray-200 bg-white px-3 py-2 text-xs text-gray-700 outline-none transition focus:border-[#9db7a5] focus:ring-2 focus:ring-[#dbe9de]"
            >
              <option value="liters_desc">Litri ↓</option>
              <option value="km_desc">Km ↓</option>
              <option value="consumption_desc">L/100km ↓</option>
              <option value="cost_desc">Costo ↓</option>
              <option value="refuels_desc">Rifornimenti ↓</option>
              <option value="name_asc">Nome A-Z</option>
            </select>
          </label>
          <span className="text-xs text-gray-500">
            {filteredRows.length} risultati
          </span>
        </div>
      </div>

      <div className="space-y-2">
        {visibleRows.map((row, index) => {
          const stationRows = (row.top_stations ?? []).map((station) => ({
            station: station.station_name,
            total_liters: station.total_liters,
            total_cost: station.total_cost,
            refuel_count: station.refuel_count,
          }));
          const isExpanded = Boolean(expanded[row.id]);
          return (
            <div key={row.id} className="overflow-hidden rounded-[20px] border border-[#e4e8e2] bg-[linear-gradient(180deg,_#ffffff,_#fafcf9)] shadow-sm">
              <button
                type="button"
                onClick={() => setExpanded((current) => ({ ...current, [row.id]: !current[row.id] }))}
                className="w-full px-3.5 py-2.5 text-left transition hover:bg-[#f7faf7]"
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-[#edf5f0] px-1.5 text-[10px] font-semibold text-[#1D4E35]">
                        {index + 1}
                      </span>
                      <p className="truncate text-[13px] font-semibold text-gray-900">{row.label}</p>
                      <span className={`rounded-full border px-1.5 py-0.5 text-[10px] font-medium ${consumptionTone(row.consumption_judgement as string | null | undefined)}`}>
                        {row.consumption_judgement ?? "—"}
                      </span>
                    </div>
                    <div className="mt-1.5 flex flex-wrap gap-1 text-[10px] text-gray-500">
                      <span title="Litri totali riforniti dal mezzo nel periodo selezionato." className="rounded-full border border-gray-200 bg-white px-1.5 py-0.5">{formatLiters(row.total_liters)}</span>
                      <span title="Chilometri percorsi dal mezzo nel periodo, stimati dalle sessioni chiuse." className="rounded-full border border-gray-200 bg-white px-1.5 py-0.5">{formatKilometers((row.total_km as number | null | undefined) ?? null)}</span>
                      <span title="Consumo medio espresso in litri ogni 100 chilometri." className="rounded-full border border-gray-200 bg-white px-1.5 py-0.5">L/100km {formatConsumption((row.avg_consumption_l_per_100km as number | null | undefined) ?? null)}</span>
                      <span className="rounded-full border border-gray-200 bg-white px-1.5 py-0.5">{formatEuro(row.total_cost)}</span>
                      <span title="Numero totale di rifornimenti registrati per il mezzo nel periodo." className="rounded-full border border-gray-200 bg-white px-1.5 py-0.5">{row.refuel_count} riforn.</span>
                    </div>
                  </div>
                  <div className="grid shrink-0 grid-cols-2 gap-1 text-right text-[10px] text-gray-500 sm:grid-cols-3">
                    <div className="rounded-lg border border-[#eef2ec] bg-white px-2 py-1">
                      <p className="flex items-center justify-end gap-1">€/L <InlineHelp text="Costo medio per litro calcolato sui rifornimenti del mezzo nel periodo." /></p>
                      <p className="mt-0.5 font-semibold text-gray-900">{formatEuro(row.avg_price_per_liter ?? null, 3)}</p>
                    </div>
                    <div className="rounded-lg border border-[#eef2ec] bg-white px-2 py-1">
                      <p className="flex items-center justify-end gap-1">€ medio <InlineHelp text="Costo medio di ciascun rifornimento del mezzo nel periodo." /></p>
                      <p className="mt-0.5 font-semibold text-gray-900">{formatEuro(row.avg_refuel_cost ?? null)}</p>
                    </div>
                    <div className="col-span-2 rounded-lg border border-[#eef2ec] bg-white px-2 py-1 sm:col-span-1">
                      <p className="flex items-center justify-end gap-1">L medi <InlineHelp text="Litri medi caricati per ogni rifornimento del mezzo nel periodo." /></p>
                      <p className="mt-0.5 font-semibold text-gray-900">{formatLiters(row.avg_liters_per_refuel ?? null)}</p>
                    </div>
                  </div>
                </div>
              </button>

              {isExpanded ? (
                <div className="border-t border-[#eef2ec] bg-[#f8fbf8] px-4 py-4">
                  <div className="mb-3 flex items-center justify-between gap-3">
                    <p className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-[#667267]">
                      <span>Stazioni di servizio più usate</span>
                      <InlineHelp text="Mostra i distributori più frequenti per il mezzo selezionato, ordinati per utilizzo nel periodo." />
                    </p>
                    <span className="text-xs text-gray-500">{stationRows.length} stazioni</span>
                  </div>
                  {stationRows.length === 0 ? (
                    <p className="text-sm text-gray-400">Nessuna stazione associata nel periodo.</p>
                  ) : (
                    <TopTable
                      rows={stationRows}
                      columns={[
                        { key: "station", label: "Stazione" },
                        { key: "total_liters", label: "Litri", align: "right", format: (v) => formatLiters(Number(v)) },
                        { key: "total_cost", label: "Costo", align: "right", format: (v) => formatEuro(Number(v)) },
                        { key: "refuel_count", label: "Riforn.", align: "right" },
                      ]}
                    />
                  )}
                </div>
              ) : null}
            </div>
          );
        })}
        {visibleRows.length === 0 ? (
          <div className="rounded-[18px] border border-dashed border-[#d8dfd8] bg-[#f8faf8] px-4 py-6 text-center text-sm text-gray-500">
            Nessun veicolo trovato con il filtro corrente.
          </div>
        ) : null}
      </div>
    </div>
  );
}

function OperatorConsumptionExplorer({
  rows,
  onResolveClick,
}: {
  rows: FuelTopItem[];
  onResolveClick: () => void;
}) {
  const [showAll, setShowAll] = useState(false);
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const [search, setSearch] = useState("");
  const [sortBy, setSortBy] = useState("liters_desc");

  if (rows.length === 0) {
    return <p className="py-4 text-center text-sm text-gray-400">Nessun dato disponibile</p>;
  }

  const normalizedSearch = search.trim().toLowerCase();
  const filteredRows = normalizedSearch
    ? rows.filter((row) => row.label.toLowerCase().includes(normalizedSearch))
    : rows;
  const sortedRows = [...filteredRows].sort((a, b) => {
    switch (sortBy) {
      case "name_asc":
        return a.label.localeCompare(b.label, "it");
      case "km_desc":
        return asNumber((b.total_km as number | null | undefined) ?? null) - asNumber((a.total_km as number | null | undefined) ?? null);
      case "cost_desc":
        return asNumber(b.total_cost) - asNumber(a.total_cost);
      case "refuels_desc":
        return b.refuel_count - a.refuel_count;
      case "consumption_desc":
        return asNumber((b.avg_consumption_l_per_100km as number | null | undefined) ?? null) - asNumber((a.avg_consumption_l_per_100km as number | null | undefined) ?? null);
      case "liters_desc":
      default:
        return asNumber(b.total_liters) - asNumber(a.total_liters);
    }
  });
  const visibleRows = showAll || normalizedSearch ? sortedRows : sortedRows.slice(0, 6);

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-3">
        <p className="flex items-center gap-2 text-xs text-gray-500">
          <span>Righe espandibili con il riepilogo consumo e il dettaglio mezzi usati per ciascun operatore.</span>
          <InlineHelp text="Relazioni uso mostra i mezzi associati all'operatore nel periodo e i relativi consumi. Le metriche L/100km, €/L, € medio e L medi sono calcolate sui rifornimenti attribuiti all'operatore." />
        </p>
        {rows.length > 6 ? (
          <button
            type="button"
            onClick={() => setShowAll((current) => !current)}
            className="rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-700 transition hover:bg-gray-200"
          >
            {showAll ? "Mostra meno" : `Mostra tutti (${rows.length})`}
          </button>
        ) : null}
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3 rounded-[18px] border border-[#e8ede7] bg-[#f8faf8] px-3 py-3">
        <label className="min-w-[220px] flex-1">
          <span className="sr-only">Cerca operatore</span>
          <input
            type="text"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Cerca operatore"
            className="w-full rounded-full border border-gray-200 bg-white px-3 py-2 text-sm text-gray-700 outline-none transition focus:border-[#9db7a5] focus:ring-2 focus:ring-[#dbe9de]"
          />
        </label>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-xs text-gray-500">
            <span>Ordina</span>
            <select
              value={sortBy}
              onChange={(event) => setSortBy(event.target.value)}
              className="rounded-full border border-gray-200 bg-white px-3 py-2 text-xs text-gray-700 outline-none transition focus:border-[#9db7a5] focus:ring-2 focus:ring-[#dbe9de]"
            >
              <option value="liters_desc">Litri ↓</option>
              <option value="km_desc">Km ↓</option>
              <option value="consumption_desc">L/100km ↓</option>
              <option value="cost_desc">Costo ↓</option>
              <option value="refuels_desc">Rifornimenti ↓</option>
              <option value="name_asc">Nome A-Z</option>
            </select>
          </label>
          <span className="text-xs text-gray-500">
            {filteredRows.length} risultati
          </span>
        </div>
      </div>

      <div className="space-y-2">
        {visibleRows.map((row, index) => {
          const isUnknown = row.id === "unknown";
          const relatedRows = (row.related ?? []).map((related) => ({
            label: related.label,
            total_liters: related.total_liters,
            total_cost: related.total_cost,
            avg_price_per_liter: related.avg_price_per_liter ?? null,
            avg_liters_per_refuel: related.avg_liters_per_refuel ?? null,
            refuel_count: related.refuel_count,
          }));
          const isExpanded = Boolean(expanded[row.id]);
          return (
            <div key={row.id} className="overflow-hidden rounded-[20px] border border-[#e4e8e2] bg-[linear-gradient(180deg,_#ffffff,_#fafcf9)] shadow-sm">
              <button
                type="button"
                onClick={() => setExpanded((current) => ({ ...current, [row.id]: !current[row.id] }))}
                className="w-full px-3.5 py-2.5 text-left transition hover:bg-[#f7faf7]"
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-[#eef2ff] px-1.5 text-[10px] font-semibold text-[#3650a6]">
                        {index + 1}
                      </span>
                      {isUnknown ? (
                        <span className="inline-flex flex-wrap items-baseline gap-1.5">
                          <span className="text-sm font-semibold italic text-gray-500">Non identificato</span>
                          <span
                            role="button"
                            tabIndex={0}
                            onClick={(event) => {
                              event.stopPropagation();
                              onResolveClick();
                            }}
                            onKeyDown={(event) => {
                              if (event.key === "Enter" || event.key === " ") {
                                event.preventDefault();
                                event.stopPropagation();
                                onResolveClick();
                              }
                            }}
                            className="text-[11px] text-amber-600 underline underline-offset-2 hover:text-amber-800"
                          >
                            risolvi anomalie
                          </span>
                        </span>
                      ) : (
                        <p className="truncate text-[13px] font-semibold text-gray-900">{row.label}</p>
                      )}
                      <span className={`rounded-full border px-1.5 py-0.5 text-[10px] font-medium ${consumptionTone(row.consumption_judgement as string | null | undefined)}`}>
                        {row.consumption_judgement ?? "—"}
                      </span>
                    </div>
                    <div className="mt-1.5 flex flex-wrap gap-1 text-[10px] text-gray-500">
                      <span title="Litri totali attribuiti all'operatore nel periodo selezionato." className="rounded-full border border-gray-200 bg-white px-1.5 py-0.5">{formatLiters(row.total_liters)}</span>
                      <span title="Chilometri associati all'operatore nel periodo, stimati dalle sessioni chiuse." className="rounded-full border border-gray-200 bg-white px-1.5 py-0.5">{formatKilometers((row.total_km as number | null | undefined) ?? null)}</span>
                      <span title="Consumo medio espresso in litri ogni 100 chilometri per l'operatore." className="rounded-full border border-gray-200 bg-white px-1.5 py-0.5">L/100km {formatConsumption((row.avg_consumption_l_per_100km as number | null | undefined) ?? null)}</span>
                      <span className="rounded-full border border-gray-200 bg-white px-1.5 py-0.5">{formatEuro(row.total_cost)}</span>
                      <span title="Numero totale di rifornimenti attribuiti all'operatore nel periodo." className="rounded-full border border-gray-200 bg-white px-1.5 py-0.5">{row.refuel_count} riforn.</span>
                    </div>
                  </div>
                  <div className="grid shrink-0 grid-cols-2 gap-1 text-right text-[10px] text-gray-500 sm:grid-cols-3">
                    <div className="rounded-lg border border-[#eef2ec] bg-white px-2 py-1">
                      <p className="flex items-center justify-end gap-1">€/L <InlineHelp text="Costo medio per litro dei rifornimenti attribuiti all'operatore." /></p>
                      <p className="mt-0.5 font-semibold text-gray-900">{formatEuro(row.avg_price_per_liter ?? null, 3)}</p>
                    </div>
                    <div className="rounded-lg border border-[#eef2ec] bg-white px-2 py-1">
                      <p className="flex items-center justify-end gap-1">€ medio <InlineHelp text="Costo medio per rifornimento attribuito all'operatore nel periodo." /></p>
                      <p className="mt-0.5 font-semibold text-gray-900">{formatEuro(row.avg_refuel_cost ?? null)}</p>
                    </div>
                    <div className="col-span-2 rounded-lg border border-[#eef2ec] bg-white px-2 py-1 sm:col-span-1">
                      <p className="flex items-center justify-end gap-1">Mezzi <InlineHelp text="Numero di mezzi associati all'operatore nel dettaglio espandibile." /></p>
                      <p className="mt-0.5 font-semibold text-gray-900">{relatedRows.length}</p>
                    </div>
                  </div>
                </div>
              </button>

              {isExpanded ? (
                <div className="border-t border-[#eef2ec] bg-[#f8fbf8] px-4 py-4">
                  <div className="mb-3 flex items-center justify-between gap-3">
                    <p className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-[#667267]">
                      <span>Relazioni uso (operatore → mezzi)</span>
                      <InlineHelp text="Dettaglio dei mezzi usati dall'operatore con consumi, prezzo medio e frequenza rifornimenti nel periodo." />
                    </p>
                    <span className="text-xs text-gray-500">{relatedRows.length} mezzi</span>
                  </div>
                  {relatedRows.length === 0 ? (
                    <p className="text-sm text-gray-400">Nessun mezzo associabile nel periodo.</p>
                  ) : (
                    <TopTable
                      rows={relatedRows}
                      columns={[
                        { key: "label", label: "Mezzo" },
                        { key: "total_liters", label: "Litri", align: "right", format: (v) => formatLiters(Number(v)) },
                        { key: "total_cost", label: "Costo", align: "right", format: (v) => formatEuro(Number(v)) },
                        { key: "avg_price_per_liter", label: "€/L", align: "right", format: (v) => (v == null ? "—" : formatEuro(Number(v), 3)) },
                        { key: "avg_liters_per_refuel", label: "L medi", align: "right", format: (v) => (v == null ? "—" : formatLiters(Number(v))) },
                        { key: "refuel_count", label: "Riforn.", align: "right" },
                      ]}
                    />
                  )}
                </div>
              ) : null}
            </div>
          );
        })}
        {visibleRows.length === 0 ? (
          <div className="rounded-[18px] border border-dashed border-[#d8dfd8] bg-[#f8faf8] px-4 py-6 text-center text-sm text-gray-500">
            Nessun operatore trovato con il filtro corrente.
          </div>
        ) : null}
      </div>
    </div>
  );
}

// ─── Tab panels ───────────────────────────────────────────────────────────────

function CarburantePanel({ params }: { params: { from_date?: string; to_date?: string; granularity: "day" | "week" | "month" } }) {
  const [data, setData] = useState<FuelData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showUnresolved, setShowUnresolved] = useState(false);
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

      {/* ── Nota storica rettifiche PAIROFF Q8 ─────────────────────────────────
           Il 27/04/2026 sono state rimosse 518 righe (259 coppie neg+pos) marcate
           N.Fatt.="PAIROFF" importate da file Excel Q8 dei trimestri 2025–Q1 2026.
           Queste righe erano rettifiche inter-periodo di prezzo: ogni coppia aveva
           effetto netto zero sui litri e sui costi (confermato: delta = 0,00 L e 0,00 €).
           L'import è stato corretto per ignorare i PAIROFF dai file futuri.
      ─────────────────────────────────────────────────────────────────────────── */}
      <div className="rounded-[20px] border border-[#d9dfd6] bg-[#f7f9f6] px-4 py-3">
        <div className="flex flex-wrap items-start gap-3">
          <div className="flex-1 min-w-0">
            <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-[#5f6d61]">
              Nota — Rettifiche PAIROFF Q8 rimosse il 27/04/2026
            </p>
            <p className="mt-1 text-xs leading-5 text-gray-600">
              Eliminati 518 fuel log (259 coppie negativo/positivo, periodo feb&nbsp;2025 – gen&nbsp;2026)
              prodotti dal sistema Q8 come rettifiche di prezzo inter-trimestre (<em>N.&nbsp;Fatt.&nbsp;= PAIROFF</em>).
              Ogni coppia aveva effetto netto zero su litri e costi — i totali non sono variati.
              L&apos;import è stato aggiornato: i PAIROFF vengono ora ignorati automaticamente.
            </p>
          </div>
          <div className="shrink-0 grid grid-cols-3 gap-3 text-center">
            <div>
              <p className="text-base font-semibold text-gray-800">518</p>
              <p className="text-[10px] text-gray-500">righe rimosse</p>
            </div>
            <div>
              <p className="text-base font-semibold text-gray-800">259</p>
              <p className="text-[10px] text-gray-500">coppie PAIROFF</p>
            </div>
            <div>
              <p className="text-base font-semibold text-[#1D4E35]">0,00 L</p>
              <p className="text-[10px] text-gray-500">delta netto</p>
            </div>
          </div>
        </div>
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
        <SectionShell title="Top veicoli per consumo e stazioni di servizio">
          <VehicleConsumptionExplorer rows={data.top_vehicles} />
          {data.top_vehicles.some((v) => v.total_km == null) && (
            <p className="mt-2 text-xs text-gray-400">
              I mezzi con «—» km non hanno sessioni di utilizzo chiuse nel periodo selezionato.
            </p>
          )}
        </SectionShell>

        <SectionShell title="Top operatori per consumo e relazioni uso">
          <OperatorConsumptionExplorer rows={data.top_operators} onResolveClick={() => setShowUnresolved(true)} />
          {data.top_operators.some((o) => o.total_km == null) && (
            <p className="mt-2 text-xs text-gray-400">
              Gli operatori con «—» km non hanno sessioni di utilizzo abbinate nel periodo selezionato.
            </p>
          )}
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
  const [operatorModal, setOperatorModal] = useState<{ id: string; name: string | null } | null>(null);
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
              const details = item.details as Record<string, unknown>;
              const linkedOperatorId = typeof details.operator_id === "string" && details.operator_id ? details.operator_id : null;
              const linkedOperatorName = typeof details.operator_name === "string" ? details.operator_name : null;
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
                    {(chips.length > 0 || (item.type === "orphan_session" && linkedOperatorId)) && (
                      <div className="mt-2 flex flex-wrap items-center gap-1.5">
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
                        {item.type === "orphan_session" && linkedOperatorId ? (
                          <button
                            type="button"
                            onClick={() => setOperatorModal({ id: linkedOperatorId, name: linkedOperatorName })}
                            className="rounded-full border border-[#d5e2d8] bg-white px-3 py-1 text-xs font-semibold text-[#1D4E35] transition hover:bg-[#edf5f0]"
                          >
                            Visualizza operatore
                          </button>
                        ) : null}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </SectionCard>

      <OperatorQuickModal
        open={operatorModal != null}
        operatorId={operatorModal?.id ?? null}
        operatorName={operatorModal?.name ?? null}
        onClose={() => setOperatorModal(null)}
      />
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
            <MetricCard
              label="Ore lavoro"
              value={`${summary.total_work_hours.toLocaleString("it-IT")} h`}
              sub={summary.work_hours_source === "session" ? "Da sessioni veicolo" : undefined}
            />
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
