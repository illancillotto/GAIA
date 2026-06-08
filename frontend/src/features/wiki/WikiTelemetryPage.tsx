"use client";

import { useEffect, useMemo, useState } from "react";

import { FilterPillGroup } from "@/components/network/filter-pill-group";
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

const DAY_PILL_OPTIONS = DAY_OPTIONS.map((option) => ({ value: String(option), label: `${option}g` })) as ReadonlyArray<{
  value: string;
  label: string;
}>;

const GRANULARITY_PILL_OPTIONS = [
  { value: "day", label: "Day" },
  { value: "week", label: "Week" },
  { value: "month", label: "Month" },
] as const;

function formatLatency(value: number): string {
  return `${Math.round(value)} ms`;
}

function humanizeModule(moduleKey: string | null | undefined): string {
  if (!moduleKey || moduleKey === "n/d") return "Modulo non dichiarato";
  if (moduleKey === "rete") return "Rete";
  if (moduleKey === "accessi") return "Accessi";
  return moduleKey;
}

function humanizeFallback(value: string | null | undefined): string {
  if (!value || value === "n/d") return "Nessun fallback";
  if (value === "docs_only") return "Docs only";
  if (value === "docs_insufficient_context") return "Docs insufficient context";
  if (value === "unsupported_access_request") return "Access request blocked";
  if (value === "unsupported_action_request") return "Action request blocked";
  if (value === "unsupported_external_live") return "External live blocked";
  return value;
}

function humanizeMode(value: string | null | undefined): string {
  if (!value || value === "n/d") return "Mode non dichiarata";
  if (value === "docs_only") return "Docs";
  if (value === "live_data") return "Live";
  if (value === "logic") return "Logic";
  if (value === "hybrid") return "Hybrid";
  return value;
}

function formatPercent(numerator: number, denominator: number): string {
  if (!denominator) return "0%";
  return `${Math.round((numerator / denominator) * 100)}%`;
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
  formatter,
}: {
  title: string;
  items: Array<{ key: string; count: number }>;
  hrefBuilder?: (key: string) => string | null;
  formatter?: (key: string) => string;
}) {
  return (
    <article className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">{title}</p>
      <div className="mt-3 space-y-2">
        {items.length > 0 ? items.map((item) => (
          <div key={`${title}-${item.key}`} className="flex items-center justify-between rounded-xl bg-[#f7f8f5] px-3 py-2 text-sm">
            {hrefBuilder?.(item.key) ? (
              <a href={hrefBuilder(item.key) ?? "#"} className="truncate font-medium text-[#1D4E35] underline underline-offset-2">
                {formatter ? formatter(item.key) : item.key}
              </a>
            ) : (
              <span className="truncate font-medium text-[#1D4E35]">{formatter ? formatter(item.key) : item.key}</span>
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
  const successRate = formatPercent(summary?.success_count ?? 0, summary?.total ?? 0);
  const noMatchRate = formatPercent(summary?.no_match_count ?? 0, summary?.total ?? 0);
  const docsOnlyRate = formatPercent(summary?.docs_only_count ?? 0, summary?.total ?? 0);
  const topModuleLabel = humanizeModule(summary?.top_modules[0]?.key);
  const topFallbackLabel = humanizeFallback(summary?.top_fallback_reasons[0]?.key);
  const topModeLabel = summary?.top_modes[0]?.key === "n/d" || !summary?.top_modes[0]?.key
    ? "Nessuna mode dominante"
    : summary.top_modes[0].key === "docs_only"
      ? "Docs"
      : summary.top_modes[0].key === "live_data"
        ? "Live"
        : summary.top_modes[0].key === "logic"
          ? "Logic"
          : summary.top_modes[0].key === "hybrid"
            ? "Hybrid"
            : summary.top_modes[0].key;
  const dominantFallbackCount = summary?.top_fallback_reasons[0]?.count ?? 0;
  const dominantModuleCount = summary?.top_modules[0]?.count ?? 0;
  const schedulerStatus = schedule?.enabled ? "Job attivo" : "Job disattivo";

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
      <section className="overflow-hidden rounded-[28px] border border-[#d7dfd6] bg-[radial-gradient(circle_at_top_left,_rgba(221,238,227,0.95),_rgba(248,246,239,0.98)_55%,_rgba(255,255,255,0.99))] p-6 shadow-sm">
        <div className="grid gap-6 xl:grid-cols-[minmax(0,1.45fr)_minmax(340px,0.95fr)]">
          <div className="space-y-5">
            <div className="inline-flex items-center rounded-full border border-white/70 bg-white/75 px-4 py-1 text-[11px] font-semibold uppercase tracking-[0.24em] text-[#1D4E35] shadow-sm">
              Osservabilità Wiki
            </div>
            <div className="space-y-3">
              <h2 className="max-w-3xl text-3xl font-semibold tracking-tight text-[#1b3126]">
                Telemetria operativa su volumi, fallback e qualità delle risposte del Wiki Agent.
              </h2>
              <p className="max-w-3xl text-sm leading-7 text-[#3f5a4d]">
                Vista storica per capire dove il Wiki risponde bene, dove degrada su docs only o no match e come si muovono
                moduli, mode operative e latenza percepita.
              </p>
            </div>
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
              <div className="rounded-2xl border border-white/70 bg-white/82 px-4 py-4 shadow-sm">
                <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-[#6b7f74]">Success rate</p>
                <p className="mt-3 text-3xl font-semibold text-[#183126]">{successRate}</p>
                <p className="mt-1 text-sm text-[#61756a]">{(summary?.success_count ?? 0).toLocaleString("it-IT")} risposte utili</p>
              </div>
              <div className="rounded-2xl border border-white/70 bg-white/82 px-4 py-4 shadow-sm">
                <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-[#6b7f74]">Top modulo</p>
                <p className="mt-3 text-xl font-semibold text-[#183126]">{topModuleLabel}</p>
                <p className="mt-1 text-sm text-[#61756a]">{dominantModuleCount.toLocaleString("it-IT")} ricorrenze osservate</p>
              </div>
              <div className="rounded-2xl border border-white/70 bg-white/82 px-4 py-4 shadow-sm">
                <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-[#6b7f74]">Fallback docs</p>
                <p className="mt-3 text-3xl font-semibold text-[#183126]">{docsOnlyRate}</p>
                <p className="mt-1 text-sm text-[#61756a]">{(summary?.docs_only_count ?? 0).toLocaleString("it-IT")} casi docs only</p>
              </div>
              <div className="rounded-2xl border border-white/70 bg-white/82 px-4 py-4 shadow-sm">
                <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-[#6b7f74]">No match</p>
                <p className="mt-3 text-3xl font-semibold text-[#183126]">{noMatchRate}</p>
                <p className="mt-1 text-sm text-[#61756a]">latenza media {formatLatency(summary?.avg_latency_ms ?? 0)}</p>
              </div>
            </div>
          </div>

          <div className="space-y-3">
            <div className="rounded-3xl border border-sky-200 bg-sky-50/70 p-4">
              <p className="text-sm font-semibold text-sky-900">Finestra osservazione</p>
              <p className="mt-2 text-sm text-sky-800">
                Perimetro corrente: ultimi <span className="font-semibold">{days}</span> giorni con granularità{" "}
                <span className="font-semibold">
                  {GRANULARITY_OPTIONS.find((item) => item.value === granularity)?.label.toLowerCase() ?? granularity}
                </span>.
              </p>
            </div>
            <div className="rounded-3xl border border-emerald-200 bg-emerald-50/70 p-4">
              <p className="text-sm font-semibold text-emerald-900">Segnale rapido</p>
              <div className="mt-2 space-y-2 text-sm text-emerald-900">
                <p>{schedulerStatus}{schedule ? ` · ${schedule.cron} · ${schedule.timezone}` : ""}</p>
                <p>Mode dominante: <span className="font-semibold">{topModeLabel}</span></p>
                <p>Fallback prevalente: <span className="font-semibold">{topFallbackLabel}</span>{dominantFallbackCount ? ` · ${dominantFallbackCount} casi` : ""}</p>
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-2 pt-1">
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
          </div>
        </div>
      </section>

      <section className="rounded-[28px] border border-[#e3e6dc] bg-white p-5 shadow-sm">
        <div className="space-y-2">
          <p className="text-sm font-semibold text-[#223d30]">Contesto analisi</p>
          <p className="text-sm text-[#5f6e67]">Scegli finestra e granularità per rileggere trend, moduli dominanti e breakdown fallback.</p>
        </div>
        <div className="mt-4 grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
          <div className="space-y-3">
            <label className="space-y-2">
              <span className="text-xs font-medium uppercase tracking-wide text-gray-400">Finestra</span>
              <select
                className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm text-gray-700 outline-none transition focus:border-[#1D4E35] focus:ring-2 focus:ring-[#1D4E35]/10"
                value={days}
                onChange={(event) => setDays(Number(event.target.value) as (typeof DAY_OPTIONS)[number])}
              >
                {DAY_OPTIONS.map((option) => (
                  <option key={option} value={option}>{option} giorni</option>
                ))}
              </select>
            </label>
            <FilterPillGroup
              options={DAY_PILL_OPTIONS}
              value={String(days)}
              onChange={(value) => setDays(Number(value) as (typeof DAY_OPTIONS)[number])}
            />
          </div>
          <div className="space-y-3">
            <label className="space-y-2">
              <span className="text-xs font-medium uppercase tracking-wide text-gray-400">Granularità</span>
              <select
                className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm text-gray-700 outline-none transition focus:border-[#1D4E35] focus:ring-2 focus:ring-[#1D4E35]/10"
                value={granularity}
                onChange={(event) => setGranularity(event.target.value as (typeof GRANULARITY_OPTIONS)[number]["value"])}
              >
                {GRANULARITY_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>{option.label}</option>
                ))}
              </select>
            </label>
            <FilterPillGroup options={GRANULARITY_PILL_OPTIONS} value={granularity} onChange={setGranularity} />
          </div>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Scheduler" value={schedule?.enabled ? "Attivo" : "Disattivo"} sub={schedule ? `${schedule.cron} · ${schedule.timezone}` : "Config non disponibile"} />
        <MetricCard label="Lookback job" value={(schedule?.lookback_days ?? 0).toLocaleString("it-IT")} sub="Giorni ricostruiti dal job" />
        <MetricCard label="Granularità" value={GRANULARITY_OPTIONS.find((item) => item.value === granularity)?.label ?? granularity} sub="Serie corrente" />
        <MetricCard label="Contesto dominante" value={topModuleLabel} sub={topModuleHref ?? "Nessun contesto"} />
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
        <MetricCard label="Top modulo" value={topModuleLabel} sub={`Ricorrenze ${summary?.top_modules[0]?.count ?? 0}`} />
        <MetricCard label="Top fallback" value={topFallbackLabel} sub={`Ricorrenze ${summary?.top_fallback_reasons[0]?.count ?? 0}`} />
      </section>

      <section className="grid gap-4 xl:grid-cols-4">
        <TopList title="Top tool" items={summary?.top_tools ?? []} />
        <TopList title="Top moduli" items={summary?.top_modules ?? []} hrefBuilder={(key) => buildWikiContextHref(null, key)} formatter={humanizeModule} />
        <TopList title="Top mode" items={summary?.top_modes ?? []} formatter={humanizeMode} />
        <TopList title="Top fallback" items={summary?.top_fallback_reasons ?? []} formatter={humanizeFallback} />
      </section>

      <section className="grid gap-4 xl:grid-cols-3">
        <TrendList title="Trend richieste" items={globalSeries} valueKey="total" />
        <TrendList title="Trend denied" items={globalSeries} valueKey="denied_count" />
        <TrendList title="Trend no match" items={globalSeries} valueKey="no_match_count" />
      </section>

      <section className="grid gap-4 xl:grid-cols-2">
        <TrendList title="Trend docs only" items={globalSeries} valueKey="docs_only_count" />
        <TrendList
          title={`Trend top modulo${summary?.top_modules[0]?.key ? `: ${humanizeModule(summary.top_modules[0].key)}` : ""}`}
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
