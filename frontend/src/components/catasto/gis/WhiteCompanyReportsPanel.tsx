"use client";

import type { Dispatch, SetStateAction } from "react";

import type { WhiteCompanyReportLayerResponse } from "@/types/gis";

export interface WhiteCompanyReportFilters {
  dateFrom: string;
  dateTo: string;
  tipologia: string;
  operatore: string;
}

export const EMPTY_WHITECOMPANY_REPORT_FILTERS: WhiteCompanyReportFilters = {
  dateFrom: "",
  dateTo: "",
  tipologia: "",
  operatore: "",
};

interface WhiteCompanyReportsPanelProps {
  isDark: boolean;
  token: string | null;
  layer: WhiteCompanyReportLayerResponse | null;
  visible: boolean;
  busy: boolean;
  error: string | null;
  filters: WhiteCompanyReportFilters;
  onVisibleChange: Dispatch<SetStateAction<boolean>>;
  onFiltersChange: Dispatch<SetStateAction<WhiteCompanyReportFilters>>;
  onLoadLayer: (filters?: WhiteCompanyReportFilters) => void | Promise<void>;
}

interface PanelTheme {
  panel: string;
  title: string;
  bodyText: string;
  visibility: string;
  input: string;
  mutedText: string;
  secondaryButton: string;
  error: string;
  warning: string;
}

const DARK_PANEL_THEME: PanelTheme = {
  panel: "border-white/15 bg-white/10",
  title: "text-rose-100",
  bodyText: "text-white/60",
  visibility: "border-white/15 bg-white/10 text-white/70",
  input: "border-white/15 bg-white/10 text-white placeholder:text-white/35 focus:border-rose-200",
  mutedText: "text-white/55",
  secondaryButton: "border-white/15 bg-white/10 text-white/70 hover:bg-white/15",
  error: "border-red-300/30 bg-red-500/20 text-red-100",
  warning: "border-amber-300/30 bg-amber-500/20 text-amber-50",
};

const LIGHT_PANEL_THEME: PanelTheme = {
  panel: "border-rose-100 bg-rose-50/30",
  title: "text-rose-700",
  bodyText: "text-slate-500",
  visibility: "border-rose-100 bg-white text-rose-700",
  input: "border-white bg-white/90 text-slate-900 placeholder:text-slate-400 focus:border-rose-200 focus:ring-2 focus:ring-rose-100",
  mutedText: "text-slate-500",
  secondaryButton: "border-gray-200 bg-white text-slate-600 hover:bg-slate-50",
  error: "border-red-100 bg-red-50 text-red-700",
  warning: "border-amber-100 bg-amber-50 text-amber-700",
};

function getPanelTheme(isDark: boolean): PanelTheme {
  return isDark ? DARK_PANEL_THEME : LIGHT_PANEL_THEME;
}

function ReportStats({ isDark, layer }: { isDark: boolean; layer: WhiteCompanyReportLayerResponse | null }) {
  const stats = layer?.stats;
  const items = [
    { label: "totali", value: stats?.total ?? 0, className: isDark ? "bg-white/10 text-white" : "bg-white/80 text-slate-800" },
    { label: "in mappa", value: stats?.mapped ?? 0, className: isDark ? "bg-rose-500/20 text-rose-50" : "bg-rose-50 text-rose-700" },
    { label: "senza GPS", value: stats?.unmapped ?? 0, className: isDark ? "bg-amber-500/20 text-amber-50" : "bg-amber-50 text-amber-700" },
  ];

  return (
    <div className="mt-3 grid grid-cols-3 gap-2 text-center text-[11px]">
      {items.map((item) => (
        <div key={item.label} className={`${item.className} rounded-xl px-2 py-2`}>
          <div className="font-semibold">{item.value.toLocaleString("it-IT")}</div>
          <div className={isDark ? "text-white/45" : item.label === "totali" ? "text-slate-400" : "text-current/60"}>{item.label}</div>
        </div>
      ))}
    </div>
  );
}

function ReportFilterFields({
  theme,
  layer,
  filters,
  onFiltersChange,
}: {
  theme: PanelTheme;
  layer: WhiteCompanyReportLayerResponse | null;
  filters: WhiteCompanyReportFilters;
  onFiltersChange: Dispatch<SetStateAction<WhiteCompanyReportFilters>>;
}) {
  const inputClass = `mt-1 w-full rounded-xl border px-3 py-2 text-xs outline-none transition ${theme.input}`;
  return (
    <>
      <div className="mt-3 grid grid-cols-2 gap-2">
        <DateFilter label="Da" value={filters.dateFrom} theme={theme} inputClass={inputClass} onChange={(dateFrom) => onFiltersChange((current) => ({ ...current, dateFrom }))} />
        <DateFilter label="A" value={filters.dateTo} theme={theme} inputClass={inputClass} onChange={(dateTo) => onFiltersChange((current) => ({ ...current, dateTo }))} />
      </div>
      <div className="mt-2 grid gap-2">
        <SelectFilter label="Tipologia" value={filters.tipologia} options={layer?.tipologie ?? []} theme={theme} inputClass={inputClass} emptyLabel="Tutte le tipologie" onChange={(tipologia) => onFiltersChange((current) => ({ ...current, tipologia }))} />
        <SelectFilter label="Operatore" value={filters.operatore} options={layer?.operatori ?? []} theme={theme} inputClass={inputClass} emptyLabel="Tutti gli operatori" onChange={(operatore) => onFiltersChange((current) => ({ ...current, operatore }))} />
      </div>
    </>
  );
}

function DateFilter({ label, value, theme, inputClass, onChange }: { label: string; value: string; theme: PanelTheme; inputClass: string; onChange: (value: string) => void }) {
  return (
    <label className="text-[11px] font-semibold text-slate-500">
      <span className={theme.mutedText}>{label}</span>
      <input type="date" value={value} onChange={(event) => onChange(event.target.value)} className={inputClass} />
    </label>
  );
}

function SelectFilter({ label, value, options, theme, inputClass, emptyLabel, onChange }: { label: string; value: string; options: string[]; theme: PanelTheme; inputClass: string; emptyLabel: string; onChange: (value: string) => void }) {
  return (
    <label className="text-[11px] font-semibold">
      <span className={theme.mutedText}>{label}</span>
      <select value={value} onChange={(event) => onChange(event.target.value)} className={inputClass}>
        <option value="">{emptyLabel}</option>
        {options.map((option) => <option key={option} value={option}>{option}</option>)}
      </select>
    </label>
  );
}

function ReportActions({ token, busy, theme, onLoadLayer, onFiltersChange }: { token: string | null; busy: boolean; theme: PanelTheme; onLoadLayer: (filters?: WhiteCompanyReportFilters) => void | Promise<void>; onFiltersChange: Dispatch<SetStateAction<WhiteCompanyReportFilters>> }) {
  return (
    <div className="mt-3 grid grid-cols-[1fr_auto] gap-2">
      <button type="button" onClick={() => void onLoadLayer()} disabled={busy || !token} className="rounded-xl bg-rose-600 px-3 py-2 text-xs font-semibold text-white transition hover:bg-rose-700 disabled:cursor-not-allowed disabled:bg-gray-300">
        {busy ? "Carico..." : "Applica filtri"}
      </button>
      <button type="button" onClick={() => { onFiltersChange(EMPTY_WHITECOMPANY_REPORT_FILTERS); void onLoadLayer(EMPTY_WHITECOMPANY_REPORT_FILTERS); }} disabled={busy || !token} className={`rounded-xl border px-3 py-2 text-xs font-semibold transition disabled:opacity-50 ${theme.secondaryButton}`}>
        Azzera
      </button>
    </div>
  );
}

function ReportNotices({ theme, error, layer }: { theme: PanelTheme; error: string | null; layer: WhiteCompanyReportLayerResponse | null }) {
  const stats = layer?.stats;
  const featureCount = layer?.geojson.features.length ?? 0;
  return (
    <>
      {error ? <div className={`mt-2 rounded-xl border px-3 py-2 text-[11px] font-medium ${theme.error}`}>{error}</div> : null}
      {stats?.truncated ? <div className={`mt-2 rounded-xl border px-3 py-2 text-[11px] ${theme.warning}`}>Mostrati {featureCount.toLocaleString("it-IT")} marker su {stats.mapped.toLocaleString("it-IT")}: restringi i filtri per vedere tutto.</div> : null}
    </>
  );
}

export default function WhiteCompanyReportsPanel(props: WhiteCompanyReportsPanelProps) {
  const theme = getPanelTheme(props.isDark);
  return (
    <div className={`rounded-2xl border p-3 ${theme.panel}`}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className={`text-[10px] font-semibold uppercase tracking-widest ${theme.title}`}>Segnalazioni WhiteCompany</p>
          <p className={`mt-1 text-xs leading-5 ${theme.bodyText}`}>Layer puntuale da segnalazioni importate, filtrabile per data, tipologia e operatore.</p>
        </div>
        <label className={`inline-flex shrink-0 items-center gap-2 rounded-full border px-2.5 py-1 text-[11px] font-semibold ${theme.visibility}`}>
          <input type="checkbox" checked={props.visible} onChange={() => props.onVisibleChange((value) => !value)} className="h-3.5 w-3.5 rounded border-gray-300 text-rose-600 focus:ring-rose-500" />
          Visibile
        </label>
      </div>
      <ReportStats isDark={props.isDark} layer={props.layer} />
      <ReportFilterFields theme={theme} layer={props.layer} filters={props.filters} onFiltersChange={props.onFiltersChange} />
      <ReportActions token={props.token} busy={props.busy} theme={theme} onLoadLayer={props.onLoadLayer} onFiltersChange={props.onFiltersChange} />
      <ReportNotices theme={theme} error={props.error} layer={props.layer} />
    </div>
  );
}
