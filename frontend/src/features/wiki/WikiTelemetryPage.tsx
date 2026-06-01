"use client";

import { useEffect, useMemo, useState } from "react";

import { EmptyState } from "@/components/ui/empty-state";
import { MetricCard } from "@/components/ui/metric-card";
import { SearchIcon } from "@/components/ui/icons";
import {
  exportWikiTelemetrySeries,
  getWikiTelemetryRetention,
  getWikiTelemetrySchedule,
  getWikiTelemetrySeries,
  getWikiTelemetrySummary,
  pruneWikiTelemetry,
  refreshWikiTelemetry,
} from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import type {
  WikiTelemetryRetention,
  WikiTelemetrySchedule,
  WikiTelemetrySeriesPoint,
  WikiTelemetrySummary,
} from "@/types/api";
import { buildWikiContextHref } from "./context-links";

const DAY_OPTIONS = [14, 30, 60, 90] as const;
const GRANULARITY_OPTIONS = [
  { value: "day", label: "Giornaliera" },
  { value: "week", label: "Settimanale" },
  { value: "month", label: "Mensile" },
] as const;

function formatLatency(value: number): string {
  return `${Math.round(value)} ms`;
}

function TrendList({
  title,
  items,
  valueKey,
  href,
}: {
  title: string;
  items: WikiTelemetrySeriesPoint[];
  valueKey: keyof Pick<
    WikiTelemetrySeriesPoint,
    "total" | "denied_count" | "no_match_count" | "docs_only_count" | "live_count" | "logic_count" | "hybrid_count"
  >;
  href?: string | null;
}) {
  return (
    <article className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between gap-3">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">{title}</p>
        {href ? <a href={href} className="text-xs font-medium text-[#1D4E35] underline underline-offset-2">Apri contesto</a> : null}
      </div>
      <div className="mt-3 space-y-2">
        {items.length > 0 ? items.map((item) => (
          <div key={`${title}-${item.metric_date}`} className="flex items-center justify-between rounded-xl bg-[#f7f8f5] px-3 py-2 text-sm">
            <span className="font-medium text-[#1D4E35]">{item.period_label}</span>
            <span className="text-gray-500">{item[valueKey].toLocaleString("it-IT")}</span>
          </div>
        )) : <p className="text-sm text-gray-500">Nessun dato disponibile.</p>}
      </div>
    </article>
  );
}

function TopList({
  title,
  items,
  hrefBuilder,
}: {
  title: string;
  items: Array<{ key: string; count: number }>;
  hrefBuilder?: (key: string) => string | null;
}) {
  return (
    <article className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">{title}</p>
      <div className="mt-3 space-y-2">
        {items.length > 0 ? items.map((item) => (
          <div key={`${title}-${item.key}`} className="flex items-center justify-between rounded-xl bg-[#f7f8f5] px-3 py-2 text-sm">
            {hrefBuilder?.(item.key) ? (
              <a href={hrefBuilder(item.key) ?? "#"} className="truncate font-medium text-[#1D4E35] underline underline-offset-2">
                {item.key}
              </a>
            ) : (
              <span className="truncate font-medium text-[#1D4E35]">{item.key}</span>
            )}
            <span className="text-gray-500">{item.count}</span>
          </div>
        )) : <p className="text-sm text-gray-500">Nessun dato disponibile.</p>}
      </div>
    </article>
  );
}

export function WikiTelemetryPage() {
  const [days, setDays] = useState<(typeof DAY_OPTIONS)[number]>(30);
  const [granularity, setGranularity] = useState<(typeof GRANULARITY_OPTIONS)[number]["value"]>("day");
  const [summary, setSummary] = useState<WikiTelemetrySummary | null>(null);
  const [schedule, setSchedule] = useState<WikiTelemetrySchedule | null>(null);
  const [retention, setRetention] = useState<WikiTelemetryRetention | null>(null);
  const [globalSeries, setGlobalSeries] = useState<WikiTelemetrySeriesPoint[]>([]);
  const [moduleSeries, setModuleSeries] = useState<WikiTelemetrySeriesPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadTelemetry() {
      const token = getStoredAccessToken();
      if (!token) {
        setError("Sessione non disponibile.");
        setSummary(null);
        setGlobalSeries([]);
        setModuleSeries([]);
        setLoading(false);
        return;
      }

      setLoading(true);
      try {
        const [summaryResponse, globalResponse, scheduleResponse, retentionResponse] = await Promise.all([
          getWikiTelemetrySummary(token, { days }),
          getWikiTelemetrySeries(token, { days, dimensionType: "global", granularity }),
          getWikiTelemetrySchedule(token),
          getWikiTelemetryRetention(token),
        ]);
        const topModule = summaryResponse.top_modules[0]?.key ?? null;
        const moduleResponse = topModule && topModule !== "n/d"
          ? await getWikiTelemetrySeries(token, { days, dimensionType: "module", dimensionKey: topModule, granularity })
          : { items: [] };
        setSummary(summaryResponse);
        setSchedule(scheduleResponse);
        setRetention(retentionResponse);
        setGlobalSeries(globalResponse.items);
        setModuleSeries(moduleResponse.items);
        setError(null);
      } catch (loadError) {
        setSummary(null);
        setSchedule(null);
        setRetention(null);
        setGlobalSeries([]);
        setModuleSeries([]);
        setError(loadError instanceof Error ? loadError.message : "Errore caricamento telemetria Wiki");
      } finally {
        setLoading(false);
      }
    }

    void loadTelemetry();
  }, [days, granularity]);

  const latest = useMemo(() => globalSeries[globalSeries.length - 1] ?? null, [globalSeries]);
  const topModuleHref = buildWikiContextHref(null, summary?.top_modules[0]?.key ?? null);

  async function handleManualRefresh() {
    const token = getStoredAccessToken();
    if (!token) {
      setError("Sessione non disponibile.");
      return;
    }
    setRefreshing(true);
    try {
      await refreshWikiTelemetry(token, { days });
      const [summaryResponse, globalResponse] = await Promise.all([
        getWikiTelemetrySummary(token, { days }),
        getWikiTelemetrySeries(token, { days, dimensionType: "global", granularity }),
      ]);
      setSummary(summaryResponse);
      setGlobalSeries(globalResponse.items);
      setError(null);
    } catch (refreshError) {
      setError(refreshError instanceof Error ? refreshError.message : "Errore refresh telemetria Wiki");
    } finally {
      setRefreshing(false);
    }
  }

  async function handleExportSeries() {
    const token = getStoredAccessToken();
    if (!token) {
      setError("Sessione non disponibile.");
      return;
    }
    try {
      const blob = await exportWikiTelemetrySeries(token, { days, dimensionType: "global", granularity });
      const href = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = href;
      link.download = `wiki-telemetry-global-${granularity}.csv`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(href);
    } catch (downloadError) {
      setError(downloadError instanceof Error ? downloadError.message : "Errore export telemetria Wiki");
    }
  }

  async function handlePruneTelemetry() {
    const token = getStoredAccessToken();
    if (!token) {
      setError("Sessione non disponibile.");
      return;
    }
    setRefreshing(true);
    try {
      await pruneWikiTelemetry(token);
      const [summaryResponse, globalResponse] = await Promise.all([
        getWikiTelemetrySummary(token, { days }),
        getWikiTelemetrySeries(token, { days, dimensionType: "global", granularity }),
      ]);
      setSummary(summaryResponse);
      setGlobalSeries(globalResponse.items);
      setError(null);
    } catch (pruneError) {
      setError(pruneError instanceof Error ? pruneError.message : "Errore prune telemetria Wiki");
    } finally {
      setRefreshing(false);
    }
  }

  if (error && !loading && !summary) {
    return <EmptyState icon={SearchIcon} title="Telemetria Wiki non disponibile" description={error} />;
  }

  return (
    <div className="space-y-6">
      <section className="flex items-end justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Osservabilità</p>
          <h2 className="mt-1 text-xl font-semibold text-gray-900">Telemetria storica Wiki Agent</h2>
          <p className="mt-1 text-sm text-gray-500">Trend persistenti su volumi, denial, fallback documentali e latenze aggregate.</p>
        </div>
        <div className="flex items-end gap-3">
          <label className="space-y-1">
            <span className="text-xs font-medium uppercase tracking-wide text-gray-400">Finestra</span>
            <select
              className="rounded-xl border border-gray-200 px-3 py-2 text-sm text-gray-700 outline-none transition focus:border-[#1D4E35] focus:ring-2 focus:ring-[#1D4E35]/10"
              value={days}
              onChange={(event) => setDays(Number(event.target.value) as (typeof DAY_OPTIONS)[number])}
            >
              {DAY_OPTIONS.map((option) => (
                <option key={option} value={option}>{option} giorni</option>
              ))}
            </select>
          </label>
          <label className="space-y-1">
            <span className="text-xs font-medium uppercase tracking-wide text-gray-400">Granularità</span>
            <select
              className="rounded-xl border border-gray-200 px-3 py-2 text-sm text-gray-700 outline-none transition focus:border-[#1D4E35] focus:ring-2 focus:ring-[#1D4E35]/10"
              value={granularity}
              onChange={(event) => setGranularity(event.target.value as (typeof GRANULARITY_OPTIONS)[number]["value"])}
            >
              {GRANULARITY_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>{option.label}</option>
              ))}
            </select>
          </label>
          <button
            type="button"
            className="btn-secondary"
            onClick={() => void handleManualRefresh()}
            disabled={refreshing}
          >
            {refreshing ? "Refresh..." : "Refresh metriche"}
          </button>
          <button type="button" className="btn-secondary" onClick={() => void handleExportSeries()}>
            Export CSV
          </button>
          <button type="button" className="btn-secondary" onClick={() => void handlePruneTelemetry()} disabled={refreshing}>
            Prune retention
          </button>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Scheduler" value={schedule?.enabled ? "Attivo" : "Disattivo"} sub={schedule ? `${schedule.cron} · ${schedule.timezone}` : "Config non disponibile"} />
        <MetricCard label="Lookback job" value={(schedule?.lookback_days ?? 0).toLocaleString("it-IT")} sub="Giorni ricostruiti dal job" />
        <MetricCard label="Granularità" value={GRANULARITY_OPTIONS.find((item) => item.value === granularity)?.label ?? granularity} sub="Serie corrente" />
        <MetricCard label="Top modulo link" value={summary?.top_modules[0]?.key ?? "n/d"} sub={topModuleHref ?? "Nessun contesto"} />
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        <MetricCard label="Retention audit" value={(retention?.audit_retention_days ?? 0).toLocaleString("it-IT")} sub="Giorni audit raw" />
        <MetricCard label="Retention daily" value={(retention?.daily_retention_days ?? 0).toLocaleString("it-IT")} sub="Snapshot giornalieri" />
        <MetricCard label="Retention period" value={(retention?.period_retention_days ?? 0).toLocaleString("it-IT")} sub="Aggregati week/month" />
      </section>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        <MetricCard label="Richieste" value={(summary?.total ?? 0).toLocaleString("it-IT")} sub={`Ultimi ${days} giorni`} />
        <MetricCard label="Successi" value={(summary?.success_count ?? 0).toLocaleString("it-IT")} sub="Tool/docs riusciti" variant="success" />
        <MetricCard label="Denied" value={(summary?.denied_count ?? 0).toLocaleString("it-IT")} sub="Policy o failure" variant="danger" />
        <MetricCard label="No match" value={(summary?.no_match_count ?? 0).toLocaleString("it-IT")} sub="Nessun dato utile" variant="warning" />
        <MetricCard
          label="Latenza media"
          value={formatLatency(summary?.avg_latency_ms ?? 0)}
          sub={latest ? `Ultimo periodo ${latest.period_label}` : "Nessun punto storico"}
          variant="info"
        />
      </section>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Docs only" value={(summary?.docs_only_count ?? 0).toLocaleString("it-IT")} sub="Fallback puri" />
        <MetricCard label="Live / Logic / Hybrid" value={`${summary?.live_count ?? 0} / ${summary?.logic_count ?? 0} / ${summary?.hybrid_count ?? 0}`} sub="Distribuzione mode" />
        <MetricCard label="Top modulo" value={summary?.top_modules[0]?.key ?? "n/d"} sub={`Ricorrenze ${summary?.top_modules[0]?.count ?? 0}`} />
        <MetricCard label="Top fallback" value={summary?.top_fallback_reasons[0]?.key ?? "n/d"} sub={`Ricorrenze ${summary?.top_fallback_reasons[0]?.count ?? 0}`} />
      </section>

      <section className="grid gap-4 xl:grid-cols-4">
        <TopList title="Top tool" items={summary?.top_tools ?? []} />
        <TopList title="Top moduli" items={summary?.top_modules ?? []} hrefBuilder={(key) => buildWikiContextHref(null, key)} />
        <TopList title="Top mode" items={summary?.top_modes ?? []} />
        <TopList title="Top fallback" items={summary?.top_fallback_reasons ?? []} />
      </section>

      <section className="grid gap-4 xl:grid-cols-3">
        <TrendList title="Trend richieste" items={globalSeries} valueKey="total" />
        <TrendList title="Trend denied" items={globalSeries} valueKey="denied_count" />
        <TrendList title="Trend no match" items={globalSeries} valueKey="no_match_count" />
      </section>

      <section className="grid gap-4 xl:grid-cols-2">
        <TrendList title="Trend docs only" items={globalSeries} valueKey="docs_only_count" />
        <TrendList
          title={`Trend top modulo${summary?.top_modules[0]?.key ? `: ${summary.top_modules[0].key}` : ""}`}
          items={moduleSeries}
          valueKey="total"
          href={topModuleHref}
        />
      </section>

      {error ? (
        <article className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</article>
      ) : null}
    </div>
  );
}
