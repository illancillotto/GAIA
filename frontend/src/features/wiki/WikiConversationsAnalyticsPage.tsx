"use client";

import { useEffect, useMemo, useState } from "react";

import { FilterPillGroup } from "@/components/network/filter-pill-group";
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
const DAY_PILL_OPTIONS = DAY_OPTIONS.map((option) => ({ value: String(option), label: `${option}g` })) as ReadonlyArray<{
  value: string;
  label: string;
}>;

function humanizeStatus(value: string | null | undefined): string {
  if (!value || value === "n/d") return "Stato non dichiarato";
  if (value === "open") return "Open";
  if (value === "in_review") return "In review";
  if (value === "waiting_user") return "Waiting user";
  if (value === "resolved") return "Resolved";
  if (value === "closed") return "Closed";
  if (value === "needs_review") return "Needs review";
  return value;
}

function humanizePriority(value: string | null | undefined): string {
  if (!value || value === "n/d") return "Priorità non dichiarata";
  if (value === "low") return "Low";
  if (value === "medium") return "Medium";
  if (value === "high") return "High";
  if (value === "urgent") return "Urgent";
  return value;
}

function humanizeReviewReason(value: string | null | undefined): string {
  if (!value || value === "n/d") return "Nessuna motivazione";
  if (value === "no_match") return "No match";
  if (value === "access_request") return "Access request";
  if (value === "action_request") return "Action request";
  if (value === "external_live") return "External live";
  return value;
}

function humanizeEventType(value: string | null | undefined): string {
  if (!value || value === "n/d") return "Evento non dichiarato";
  return value.replaceAll("_", " ");
}

function formatPercent(numerator: number, denominator: number): string {
  if (!denominator) return "0%";
  return `${Math.round((numerator / denominator) * 100)}%`;
}

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

function FormattedTopList({
  title,
  items,
  formatter,
}: {
  title: string;
  items: Array<{ key: string; count: number }>;
  formatter: (key: string) => string;
}) {
  return (
    <article className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">{title}</p>
      <div className="mt-3 space-y-2">
        {items.map((item) => (
          <div key={`${title}-${item.key}`} className="flex items-center justify-between rounded-xl bg-[#f7f8f5] px-3 py-2 text-sm">
            <span className="truncate font-medium text-[#1D4E35]">{formatter(item.key)}</span>
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
  const closeRate = formatPercent(summary?.closed_count ?? 0, summary?.created_count ?? 0);
  const reviewPressure = formatPercent(summary?.needs_review_count ?? 0, summary?.total_threads ?? 0);
  const topStatus = humanizeStatus(summary?.top_statuses[0]?.key);
  const topOwner = summary?.top_owners[0]?.key ?? "Nessun owner dominante";
  const reviewSignal = humanizeReviewReason(summary?.top_review_reasons[0]?.key);

  if (error && !loading && !summary) {
    return <EmptyState icon={SearchIcon} title="Analytics conversazioni non disponibili" description={error} />;
  }

  return (
    <div className="space-y-6">
      <section className="overflow-hidden rounded-[28px] border border-[#d7dfd6] bg-[radial-gradient(circle_at_top_left,_rgba(221,238,227,0.95),_rgba(248,246,239,0.98)_55%,_rgba(255,255,255,0.99))] p-6 shadow-sm">
        <div className="grid gap-6 xl:grid-cols-[minmax(0,1.45fr)_minmax(340px,0.95fr)]">
          <div className="space-y-5">
            <div className="inline-flex items-center rounded-full border border-white/70 bg-white/75 px-4 py-1 text-[11px] font-semibold uppercase tracking-[0.24em] text-[#1D4E35] shadow-sm">
              Conversation Analytics
            </div>
            <div className="space-y-3">
              <h2 className="max-w-3xl text-3xl font-semibold tracking-tight text-[#1b3126]">
                Trend backlog, priorità e tempi di presa in carico delle conversazioni Wiki.
              </h2>
              <p className="max-w-3xl text-sm leading-7 text-[#3f5a4d]">
                Vista amministrativa per leggere pressione sul backlog, performance del flusso review e carico sugli owner
                del Wiki Agent.
              </p>
            </div>
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
              <div className="rounded-2xl border border-white/70 bg-white/82 px-4 py-4 shadow-sm">
                <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-[#6b7f74]">Close rate</p>
                <p className="mt-3 text-3xl font-semibold text-[#183126]">{closeRate}</p>
                <p className="mt-1 text-sm text-[#61756a]">{(summary?.closed_count ?? 0).toLocaleString("it-IT")} thread chiusi</p>
              </div>
              <div className="rounded-2xl border border-white/70 bg-white/82 px-4 py-4 shadow-sm">
                <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-[#6b7f74]">Backlog review</p>
                <p className="mt-3 text-3xl font-semibold text-[#183126]">{reviewPressure}</p>
                <p className="mt-1 text-sm text-[#61756a]">{(summary?.needs_review_count ?? 0).toLocaleString("it-IT")} thread da leggere</p>
              </div>
              <div className="rounded-2xl border border-white/70 bg-white/82 px-4 py-4 shadow-sm">
                <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-[#6b7f74]">Top stato</p>
                <p className="mt-3 text-xl font-semibold text-[#183126]">{topStatus}</p>
                <p className="mt-1 text-sm text-[#61756a]">{summary?.top_statuses[0]?.count ?? 0} occorrenze</p>
              </div>
              <div className="rounded-2xl border border-white/70 bg-white/82 px-4 py-4 shadow-sm">
                <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-[#6b7f74]">Tempo review</p>
                <p className="mt-3 text-3xl font-semibold text-[#183126]">{summary?.avg_time_to_review_hours ?? 0}h</p>
                <p className="mt-1 text-sm text-[#61756a]">resolve medio {summary?.avg_time_to_resolve_hours ?? 0}h</p>
              </div>
            </div>
          </div>

          <div className="space-y-3">
            <div className="rounded-3xl border border-sky-200 bg-sky-50/70 p-4">
              <p className="text-sm font-semibold text-sky-900">Copertura dati</p>
              <p className="mt-2 text-sm text-sky-800">
                Dati completi da <span className="font-semibold">{summary?.data_complete_from ?? "data non marcata"}</span>
                {summary?.last_backfill_at
                  ? ` · ultimo backfill ${new Intl.DateTimeFormat("it-IT", { dateStyle: "short", timeStyle: "short" }).format(new Date(summary.last_backfill_at))}`
                  : ""}
              </p>
            </div>
            <div className="rounded-3xl border border-emerald-200 bg-emerald-50/70 p-4">
              <p className="text-sm font-semibold text-emerald-900">Segnale rapido</p>
              <div className="mt-2 space-y-2 text-sm text-emerald-900">
                <p>Owner dominante: <span className="font-semibold">{topOwner}</span></p>
                <p>Motivo review più frequente: <span className="font-semibold">{reviewSignal}</span></p>
                <p>Snapshot più recente: <span className="font-semibold">{latest?.period_label ?? "n/d"}</span></p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="rounded-[28px] border border-[#e3e6dc] bg-white p-5 shadow-sm">
        <div className="space-y-2">
          <p className="text-sm font-semibold text-[#223d30]">Contesto analisi</p>
          <p className="text-sm text-[#5f6e67]">Cambia la finestra temporale per rileggere backlog, velocità di chiusura e distribuzione del workflow.</p>
        </div>
        <div className="mt-4 grid gap-4 xl:grid-cols-[minmax(0,360px)_minmax(0,1fr)] xl:items-end">
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
          <FilterPillGroup options={DAY_PILL_OPTIONS} value={String(days)} onChange={(value) => setDays(Number(value) as (typeof DAY_OPTIONS)[number])} />
        </div>
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
        <FormattedTopList title="Per stato" items={summary?.top_statuses ?? []} formatter={humanizeStatus} />
        <FormattedTopList title="Per priorità" items={summary?.top_priorities ?? []} formatter={humanizePriority} />
        <TopList title="Per owner" items={summary?.top_owners ?? []} />
        <FormattedTopList title="Per review reason" items={summary?.top_review_reasons ?? []} formatter={humanizeReviewReason} />
      </section>

      <section className="grid gap-4 xl:grid-cols-2">
        <FormattedTopList title="Top eventi workflow" items={summary?.top_event_types ?? []} formatter={humanizeEventType} />
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
