"use client";

import { useEffect, useMemo, useState } from "react";

import { EmptyState } from "@/components/ui/empty-state";
import { MetricCard } from "@/components/ui/metric-card";
import { SearchIcon } from "@/components/ui/icons";
import { getWikiConversationMetricsSeries, getWikiConversationMetricsSummary } from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import type {
  WikiConversationMetricsSeriesPoint,
  WikiConversationMetricsSummary,
} from "@/types/api";

const DAY_OPTIONS = [14, 30, 60, 90] as const;

function MiniTrend({
  title,
  items,
  valueKey,
}: {
  title: string;
  items: WikiConversationMetricsSeriesPoint[];
  valueKey: keyof Pick<
    WikiConversationMetricsSeriesPoint,
    "created_count" | "closed_count" | "open_count" | "in_review_count" | "waiting_user_count" | "resolved_count" | "needs_review_count"
  >;
}) {
  return (
    <article className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">{title}</p>
      <div className="mt-3 space-y-2">
        {items.map((item) => (
          <div key={`${title}-${item.metric_date}`} className="flex items-center justify-between rounded-xl bg-[#f7f8f5] px-3 py-2 text-sm">
            <span className="font-medium text-[#1D4E35]">{item.period_label}</span>
            <span className="text-gray-500">{item[valueKey].toLocaleString("it-IT")}</span>
          </div>
        ))}
      </div>
    </article>
  );
}

function TopList({ title, items }: { title: string; items: Array<{ key: string; count: number }> }) {
  return (
    <article className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">{title}</p>
      <div className="mt-3 space-y-2">
        {items.map((item) => (
          <div key={`${title}-${item.key}`} className="flex items-center justify-between rounded-xl bg-[#f7f8f5] px-3 py-2 text-sm">
            <span className="font-medium text-[#1D4E35]">{item.key}</span>
            <span className="text-gray-500">{item.count}</span>
          </div>
        ))}
      </div>
    </article>
  );
}

export function WikiConversationsAnalyticsPage() {
  const [days, setDays] = useState<(typeof DAY_OPTIONS)[number]>(30);
  const [summary, setSummary] = useState<WikiConversationMetricsSummary | null>(null);
  const [series, setSeries] = useState<WikiConversationMetricsSeriesPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      const token = getStoredAccessToken();
      if (!token) {
        setError("Sessione non disponibile.");
        setLoading(false);
        return;
      }
      setLoading(true);
      try {
        const [summaryResponse, seriesResponse] = await Promise.all([
          getWikiConversationMetricsSummary(token, { days }),
          getWikiConversationMetricsSeries(token, { days, dimensionType: "global", granularity: "day" }),
        ]);
        setSummary(summaryResponse);
        setSeries(seriesResponse.items);
        setError(null);
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : "Errore caricamento analytics conversazioni");
        setSummary(null);
        setSeries([]);
      } finally {
        setLoading(false);
      }
    }
    void load();
  }, [days]);

  const latest = useMemo(() => series[series.length - 1] ?? null, [series]);

  if (error && !loading && !summary) {
    return <EmptyState icon={SearchIcon} title="Analytics conversazioni non disponibili" description={error} />;
  }

  return (
    <div className="space-y-6">
      <section className="flex items-end justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Analytics</p>
          <h2 className="mt-1 text-xl font-semibold text-gray-900">Trend backlog conversazioni</h2>
          <p className="mt-1 text-sm text-gray-500">Serie storiche e breakdown amministrativi sul ciclo di vita dei thread Wiki.</p>
          <p className="mt-1 text-xs text-gray-400">
            Dati completi da {summary?.data_complete_from ?? "data non marcata"}
            {summary?.last_backfill_at ? ` · ultimo backfill ${new Intl.DateTimeFormat("it-IT", { dateStyle: "short", timeStyle: "short" }).format(new Date(summary.last_backfill_at))}` : ""}
          </p>
        </div>
        <label className="space-y-1">
          <span className="text-xs font-medium uppercase tracking-wide text-gray-400">Finestra</span>
          <select
            className="rounded-xl border border-gray-200 px-3 py-2 text-sm text-gray-700"
            value={days}
            onChange={(event) => setDays(Number(event.target.value) as (typeof DAY_OPTIONS)[number])}
          >
            {DAY_OPTIONS.map((option) => (
              <option key={option} value={option}>{option} giorni</option>
            ))}
          </select>
        </label>
      </section>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-6">
        <MetricCard label="Thread totali" value={(summary?.total_threads ?? 0).toLocaleString("it-IT")} sub={`Ultimo snapshot ${latest?.period_label ?? "n/d"}`} />
        <MetricCard label="Creati" value={(summary?.created_count ?? 0).toLocaleString("it-IT")} sub={`Ultimi ${days} giorni`} />
        <MetricCard label="Chiusi" value={(summary?.closed_count ?? 0).toLocaleString("it-IT")} sub={`Ultimi ${days} giorni`} variant="success" />
        <MetricCard label="Backlog review" value={(summary?.needs_review_count ?? 0).toLocaleString("it-IT")} sub="Snapshot corrente" variant="warning" />
        <MetricCard label="High priority" value={(summary?.high_priority_count ?? 0).toLocaleString("it-IT")} sub="Snapshot corrente" variant="danger" />
        <MetricCard label="Tempo medio review" value={`${summary?.avg_time_to_review_hours ?? 0}h`} sub={`Resolve ${summary?.avg_time_to_resolve_hours ?? 0}h`} variant="info" />
      </section>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        <MetricCard label="Ingressi review" value={(summary?.review_entered_count ?? 0).toLocaleString("it-IT")} sub={`Ultimi ${days} giorni`} />
        <MetricCard label="Riassegnazioni" value={(summary?.reassigned_count ?? 0).toLocaleString("it-IT")} sub={`Ultimi ${days} giorni`} />
        <MetricCard label="Riaperture" value={(summary?.reopened_count ?? 0).toLocaleString("it-IT")} sub={`Ultimi ${days} giorni`} variant="warning" />
        <MetricCard label="Open → review" value={`${summary?.avg_open_to_review_hours ?? 0}h`} sub="Media transizione" />
        <MetricCard label="Waiting user" value={`${summary?.avg_waiting_user_hours ?? 0}h`} sub="Media permanenza" />
      </section>

      <section className="grid gap-4 xl:grid-cols-4">
        <TopList title="Per stato" items={summary?.top_statuses ?? []} />
        <TopList title="Per priorità" items={summary?.top_priorities ?? []} />
        <TopList title="Per owner" items={summary?.top_owners ?? []} />
        <TopList title="Per review reason" items={summary?.top_review_reasons ?? []} />
      </section>

      <section className="grid gap-4 xl:grid-cols-2">
        <TopList title="Top eventi workflow" items={summary?.top_event_types ?? []} />
        <article className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Transizioni medie</p>
          <div className="mt-3 space-y-2 text-sm text-gray-600">
            <p>Open → review: <span className="font-medium text-gray-900">{summary?.avg_open_to_review_hours ?? 0}h</span></p>
            <p>Review → resolve: <span className="font-medium text-gray-900">{summary?.avg_review_to_resolve_hours ?? 0}h</span></p>
            <p>Waiting user: <span className="font-medium text-gray-900">{summary?.avg_waiting_user_hours ?? 0}h</span></p>
          </div>
        </article>
      </section>

      <section className="grid gap-4 xl:grid-cols-3">
        <MiniTrend title="Trend creati" items={series} valueKey="created_count" />
        <MiniTrend title="Trend chiusi" items={series} valueKey="closed_count" />
        <MiniTrend title="Trend open" items={series} valueKey="open_count" />
      </section>

      <section className="grid gap-4 xl:grid-cols-3">
        <MiniTrend title="Trend in review" items={series} valueKey="in_review_count" />
        <MiniTrend title="Trend waiting user" items={series} valueKey="waiting_user_count" />
        <MiniTrend title="Trend needs review" items={series} valueKey="needs_review_count" />
      </section>

      {error ? (
        <article className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</article>
      ) : null}
    </div>
  );
}
