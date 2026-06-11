"use client";

import { useEffect, useMemo, useState } from "react";

import { FilterPillGroup } from "@/components/network/filter-pill-group";
import { EmptyState } from "@/components/ui/empty-state";
import { MetricCard } from "@/components/ui/metric-card";
import { SearchIcon } from "@/components/ui/icons";
import { getWikiSupportAnalyticsClusters, getWikiSupportAnalyticsInsights, getWikiSupportAnalyticsSeries, getWikiSupportAnalyticsSummary } from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import type {
  WikiSupportAnalyticsCount,
  WikiSupportCluster,
  WikiSupportInsight,
  WikiSupportAnalyticsSeriesPoint,
  WikiSupportAnalyticsSummary,
} from "@/types/api";

const DAY_OPTIONS = [14, 30, 60, 90] as const;
const ANALYTICS_DELIVERY_FILTERS = [
  { value: "all", label: "Tutto il delivery" },
  { value: "missing", label: "Delivery mancante" },
  { value: "discovery", label: "Discovery" },
  { value: "planned", label: "Planned" },
  { value: "in_progress", label: "In progress" },
  { value: "released", label: "Released" },
  { value: "wont_do", label: "Won't do" },
] as const;
const ANALYTICS_TICKET_FILTERS = [
  { value: "all", label: "Tutti i ticket" },
  { value: "linked", label: "Con ticket" },
  { value: "unlinked", label: "Senza ticket" },
] as const;
const DAY_PILL_OPTIONS = DAY_OPTIONS.map((option) => ({ value: String(option), label: `${option}g` })) as ReadonlyArray<{
  value: string;
  label: string;
}>;

function humanizeRequestType(value: string | null | undefined): string {
  if (!value || value === "n/d") return "Tipo non dichiarato";
  if (value === "help_request") return "Supporto operativo";
  if (value === "bug_report") return "Problema / anomalia";
  if (value === "feature_request") return "Nuova funzionalità";
  if (value === "access_issue") return "Problema di accesso";
  if (value === "data_issue") return "Problema dati";
  if (value === "other_request") return "Altro";
  return value;
}

function humanizeStatus(value: string | null | undefined): string {
  if (!value || value === "n/d") return "Stato non dichiarato";
  if (value === "new") return "Nuova";
  if (value === "triaged") return "Triaged";
  if (value === "investigating") return "Investigating";
  if (value === "waiting_user") return "Waiting user";
  if (value === "planned") return "Planned";
  if (value === "resolved") return "Resolved";
  if (value === "duplicate") return "Duplicate";
  if (value === "rejected") return "Rejected";
  return value;
}

function humanizeSeverity(value: string | null | undefined): string {
  if (!value || value === "n/d") return "Severità non dichiarata";
  if (value === "low") return "Bassa";
  if (value === "medium") return "Media";
  if (value === "high") return "Alta";
  if (value === "critical") return "Critica";
  return value;
}

function humanizeDeliveryStatus(value: string | null | undefined): string {
  if (!value || value === "Delivery non dichiarato" || value === "n/d") return "Delivery non dichiarato";
  if (value === "discovery") return "Discovery";
  if (value === "planned") return "Planned";
  if (value === "in_progress") return "In progress";
  if (value === "released") return "Released";
  if (value === "wont_do") return "Won't do";
  return value;
}

function humanizeModule(value: string | null | undefined): string {
  if (!value || value === "Modulo non dichiarato" || value === "n/d") return "Modulo non dichiarato";
  if (value === "rete") return "Rete";
  if (value === "wiki") return "Wiki";
  if (value === "accessi") return "Accessi";
  if (value === "catasto") return "Catasto";
  if (value === "ruolo") return "Ruolo";
  if (value === "operazioni") return "Operazioni";
  return value;
}

function humanizeImpact(value: string | null | undefined): string {
  if (!value || value === "Impatto non dichiarato" || value === "n/d") return "Impatto non dichiarato";
  if (value === "single_user") return "Utente singolo";
  if (value === "team") return "Team";
  if (value === "office") return "Ufficio";
  if (value === "global") return "Globale";
  return value;
}

function TopList({
  title,
  items,
  formatter,
}: {
  title: string;
  items: WikiSupportAnalyticsCount[];
  formatter?: (key: string) => string;
}) {
  return (
    <article className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">{title}</p>
      <div className="mt-3 space-y-2">
        {items.length > 0 ? items.map((item) => (
          <div key={`${title}-${item.key}`} className="flex items-center justify-between rounded-xl bg-[#f7f8f5] px-3 py-2 text-sm">
            <span className="truncate font-medium text-[#1D4E35]">{formatter ? formatter(item.key) : item.key}</span>
            <span className="text-gray-500">{item.count}</span>
          </div>
        )) : <p className="text-sm text-gray-500">Nessun dato disponibile.</p>}
      </div>
    </article>
  );
}

function TrendList({
  title,
  items,
  valueKey,
}: {
  title: string;
  items: WikiSupportAnalyticsSeriesPoint[];
  valueKey: keyof Pick<
    WikiSupportAnalyticsSeriesPoint,
    "created_count" | "resolved_count" | "open_count" | "feature_request_count" | "bug_report_count" | "urgent_count" | "high_severity_count"
  >;
}) {
  return (
    <article className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">{title}</p>
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

function formatPercent(numerator: number, denominator: number): string {
  if (!denominator) return "0%";
  return `${Math.round((numerator / denominator) * 100)}%`;
}

export function WikiSupportAnalyticsPage() {
  const [days, setDays] = useState<(typeof DAY_OPTIONS)[number]>(30);
  const [deliveryFilter, setDeliveryFilter] = useState<(typeof ANALYTICS_DELIVERY_FILTERS)[number]["value"]>("all");
  const [ticketFilter, setTicketFilter] = useState<(typeof ANALYTICS_TICKET_FILTERS)[number]["value"]>("all");
  const [summary, setSummary] = useState<WikiSupportAnalyticsSummary | null>(null);
  const [series, setSeries] = useState<WikiSupportAnalyticsSeriesPoint[]>([]);
  const [clusters, setClusters] = useState<WikiSupportCluster[]>([]);
  const [insights, setInsights] = useState<WikiSupportInsight[]>([]);
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
        const analyticsParams = {
          days,
          deliveryStatus: deliveryFilter === "all" ? null : deliveryFilter,
          ticketLinked: ticketFilter === "all" ? null : ticketFilter === "linked",
        };
        const [summaryResponse, seriesResponse, clustersResponse, insightsResponse] = await Promise.all([
          getWikiSupportAnalyticsSummary(token, analyticsParams),
          getWikiSupportAnalyticsSeries(token, analyticsParams),
          getWikiSupportAnalyticsClusters(token, { ...analyticsParams, limit: 8 }),
          getWikiSupportAnalyticsInsights(token, analyticsParams),
        ]);
        setSummary(summaryResponse);
        setSeries(seriesResponse.items);
        setClusters(clustersResponse.items);
        setInsights(insightsResponse.items);
        setError(null);
      } catch (loadError) {
        setSummary(null);
        setSeries([]);
        setClusters([]);
        setInsights([]);
        setError(loadError instanceof Error ? loadError.message : "Errore caricamento analytics supporto");
      } finally {
        setLoading(false);
      }
    }
    void load();
  }, [days, deliveryFilter, ticketFilter]);

  const latest = useMemo(() => series[series.length - 1] ?? null, [series]);
  const resolutionRate = formatPercent(summary?.resolved_requests ?? 0, summary?.total_requests ?? 0);
  const assignmentRate = formatPercent(summary?.assigned_requests ?? 0, summary?.total_requests ?? 0);
  const urgencyRate = formatPercent(summary?.urgent_requests ?? 0, summary?.total_requests ?? 0);
  const dominantModule = humanizeModule(summary?.top_modules[0]?.key);
  const dominantType = humanizeRequestType(summary?.top_request_types[0]?.key);
  const dominantImpact = humanizeImpact(summary?.top_impact_scopes[0]?.key);
  const duplicatePressure = formatPercent(summary?.duplicate_requests ?? 0, summary?.total_requests ?? 0);
  const noMatchRate = formatPercent(summary?.no_match_origin_requests ?? 0, summary?.total_requests ?? 0);
  const linkedTicketRate = formatPercent(summary?.linked_ticket_requests ?? 0, summary?.total_requests ?? 0);

  function insightTone(value: WikiSupportInsight["severity"]): string {
    if (value === "critical") return "border-rose-200 bg-rose-50 text-rose-900";
    if (value === "warning") return "border-amber-200 bg-amber-50 text-amber-950";
    return "border-sky-200 bg-sky-50 text-sky-950";
  }

  if (error && !loading && !summary) {
    return <EmptyState icon={SearchIcon} title="Analytics supporto non disponibili" description={error} />;
  }

  return (
    <div className="space-y-6">
      <section className="overflow-hidden rounded-[28px] border border-[#d7dfd6] bg-[radial-gradient(circle_at_top_left,_rgba(221,238,227,0.95),_rgba(248,246,239,0.98)_55%,_rgba(255,255,255,0.99))] p-6 shadow-sm">
        <div className="grid gap-6 xl:grid-cols-[minmax(0,1.45fr)_minmax(340px,0.95fr)]">
          <div className="space-y-5">
            <div className="inline-flex items-center rounded-full border border-white/70 bg-white/75 px-4 py-1 text-[11px] font-semibold uppercase tracking-[0.24em] text-[#1D4E35] shadow-sm">
              Support Analytics
            </div>
            <div className="space-y-3">
              <h2 className="max-w-3xl text-3xl font-semibold tracking-tight text-[#1b3126]">
                Trend supporto, anomalie e bisogni prodotto nati dal Wiki.
              </h2>
              <p className="max-w-3xl text-sm leading-7 text-[#3f5a4d]">
                Vista amministrativa unica per leggere frizioni operative, richieste funzionali e segnali reali degli utenti
                durante l’utilizzo di GAIA.
              </p>
            </div>
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
              <div className="rounded-2xl border border-white/70 bg-white/82 px-4 py-4 shadow-sm">
                <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-[#6b7f74]">Resolution rate</p>
                <p className="mt-3 text-3xl font-semibold text-[#183126]">{resolutionRate}</p>
                <p className="mt-1 text-sm text-[#61756a]">{(summary?.resolved_requests ?? 0).toLocaleString("it-IT")} casi risolti</p>
              </div>
              <div className="rounded-2xl border border-white/70 bg-white/82 px-4 py-4 shadow-sm">
                <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-[#6b7f74]">Coverage ownership</p>
                <p className="mt-3 text-3xl font-semibold text-[#183126]">{assignmentRate}</p>
                <p className="mt-1 text-sm text-[#61756a]">{(summary?.assigned_requests ?? 0).toLocaleString("it-IT")} casi assegnati</p>
              </div>
              <div className="rounded-2xl border border-white/70 bg-white/82 px-4 py-4 shadow-sm">
                <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-[#6b7f74]">Urgency pressure</p>
                <p className="mt-3 text-3xl font-semibold text-[#183126]">{urgencyRate}</p>
                <p className="mt-1 text-sm text-[#61756a]">{(summary?.urgent_requests ?? 0).toLocaleString("it-IT")} casi urgenti</p>
              </div>
              <div className="rounded-2xl border border-white/70 bg-white/82 px-4 py-4 shadow-sm">
                <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-[#6b7f74]">Severità alta</p>
                <p className="mt-3 text-3xl font-semibold text-[#183126]">{summary?.high_severity_requests ?? 0}</p>
                <p className="mt-1 text-sm text-[#61756a]">high + critical nella finestra</p>
              </div>
            </div>
          </div>

          <div className="space-y-3">
            <div className="rounded-3xl border border-sky-200 bg-sky-50/70 p-4">
              <p className="text-sm font-semibold text-sky-900">Finestra osservazione</p>
              <p className="mt-2 text-sm text-sky-800">
                Perimetro corrente: <span className="font-semibold">ultimi {days} giorni</span>.
              </p>
            </div>
            <div className="rounded-3xl border border-emerald-200 bg-emerald-50/70 p-4">
              <p className="text-sm font-semibold text-emerald-900">Segnale rapido</p>
              <div className="mt-2 space-y-2 text-sm text-emerald-900">
                <p>Modulo dominante: <span className="font-semibold">{dominantModule}</span></p>
                <p>Richiesta dominante: <span className="font-semibold">{dominantType}</span></p>
                <p>Impatto prevalente: <span className="font-semibold">{dominantImpact}</span></p>
                <p>Duplicate pressure: <span className="font-semibold">{duplicatePressure}</span></p>
                <p>Ticket collegati: <span className="font-semibold">{linkedTicketRate}</span></p>
                <p>Snapshot più recente: <span className="font-semibold">{latest?.period_label ?? "n/d"}</span></p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="rounded-[28px] border border-[#e3e6dc] bg-white p-5 shadow-sm">
        <div className="space-y-2">
          <p className="text-sm font-semibold text-[#223d30]">Contesto analisi</p>
          <p className="text-sm text-[#5f6e67]">Cambia la finestra temporale per rileggere pressione supporto, feature richieste e qualità della presa in carico.</p>
        </div>
        <div className="mt-4 grid gap-4 xl:grid-cols-[minmax(0,220px)_minmax(0,220px)_minmax(0,220px)_minmax(0,1fr)] xl:items-end">
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
          <label className="space-y-2">
            <span className="text-xs font-medium uppercase tracking-wide text-gray-400">Delivery</span>
            <select
              className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm text-gray-700 outline-none transition focus:border-[#1D4E35] focus:ring-2 focus:ring-[#1D4E35]/10"
              value={deliveryFilter}
              onChange={(event) => setDeliveryFilter(event.target.value as (typeof ANALYTICS_DELIVERY_FILTERS)[number]["value"])}
            >
              {ANALYTICS_DELIVERY_FILTERS.map((option) => (
                <option key={option.value} value={option.value}>{option.label}</option>
              ))}
            </select>
          </label>
          <label className="space-y-2">
            <span className="text-xs font-medium uppercase tracking-wide text-gray-400">Ticket</span>
            <select
              className="w-full rounded-xl border border-gray-200 px-3 py-2 text-sm text-gray-700 outline-none transition focus:border-[#1D4E35] focus:ring-2 focus:ring-[#1D4E35]/10"
              value={ticketFilter}
              onChange={(event) => setTicketFilter(event.target.value as (typeof ANALYTICS_TICKET_FILTERS)[number]["value"])}
            >
              {ANALYTICS_TICKET_FILTERS.map((option) => (
                <option key={option.value} value={option.value}>{option.label}</option>
              ))}
            </select>
          </label>
          <FilterPillGroup options={DAY_PILL_OPTIONS} value={String(days)} onChange={(value) => setDays(Number(value) as (typeof DAY_OPTIONS)[number])} />
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-6">
        <MetricCard label="Richieste totali" value={(summary?.total_requests ?? 0).toLocaleString("it-IT")} sub={`Ultimo snapshot ${latest?.period_label ?? "n/d"}`} />
        <MetricCard label="Aperte" value={(summary?.open_requests ?? 0).toLocaleString("it-IT")} sub="da lavorare o seguire" />
        <MetricCard label="Feature" value={(summary?.feature_requests ?? 0).toLocaleString("it-IT")} sub="bisogni prodotto" />
        <MetricCard label="Bug / anomalie" value={(summary?.bug_reports ?? 0).toLocaleString("it-IT")} sub="malfunzionamenti segnalati" />
        <MetricCard label="Accessi / dati" value={((summary?.access_issues ?? 0) + (summary?.data_issues ?? 0)).toLocaleString("it-IT")} sub="frizioni operative" />
        <MetricCard label="Help request" value={(summary?.help_requests ?? 0).toLocaleString("it-IT")} sub="richieste di supporto" />
        <MetricCard label="Duplicati" value={(summary?.duplicate_requests ?? 0).toLocaleString("it-IT")} sub={`${summary?.canonical_cases ?? 0} casi canonici`} />
        <MetricCard label="Riaperture" value={(summary?.reopened_requests ?? 0).toLocaleString("it-IT")} sub="feedback non risolto" />
        <MetricCard label="Origine no match" value={(summary?.no_match_origin_requests ?? 0).toLocaleString("it-IT")} sub={`${noMatchRate} del totale`} variant="warning" />
        <MetricCard label="Origine guardrail" value={(summary?.guardrail_origin_requests ?? 0).toLocaleString("it-IT")} sub="richieste bloccate dal router" variant="warning" />
        <MetricCard label="Ticket collegati" value={(summary?.linked_ticket_requests ?? 0).toLocaleString("it-IT")} sub={`${linkedTicketRate} del backlog`} />
        <MetricCard label="Delivery attivo" value={(summary?.delivery_started_requests ?? 0).toLocaleString("it-IT")} sub={`${summary?.released_requests ?? 0} rilasciate · ${summary?.wont_do_requests ?? 0} won't do`} />
      </section>

      <section className="rounded-[28px] border border-[#e3e6dc] bg-white p-5 shadow-sm">
        <div className="space-y-2">
          <p className="text-sm font-semibold text-[#223d30]">Insight automatici</p>
          <p className="text-sm text-[#5f6e67]">
            Segnali già interpretati per admin e prodotto: dove il Wiki non copre, dove il supporto si ripete e dove conviene intervenire prima.
          </p>
        </div>
        <div className="mt-4 grid gap-3 xl:grid-cols-2">
          {insights.length > 0 ? (
            insights.map((insight) => (
              <article key={`${insight.insight_type}-${insight.title}`} className={`rounded-2xl border p-4 shadow-sm ${insightTone(insight.severity)}`}>
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold">{insight.title}</p>
                    <p className="mt-1 text-xs opacity-80">
                      {insight.metric_value != null ? `Segnale: ${String(insight.metric_value)}` : "Segnale qualitativo"}
                    </p>
                  </div>
                  <span className="rounded-full border border-current/15 bg-white/60 px-2 py-1 text-[11px] uppercase tracking-[0.18em]">
                    {insight.severity}
                  </span>
                </div>
                <p className="mt-3 text-sm leading-relaxed opacity-90">{insight.description}</p>
                {insight.related_key ? (
                  <p className="mt-3 text-xs opacity-80">
                    Riferimento: <span className="font-medium">{insight.related_key}</span>
                  </p>
                ) : null}
                {insight.action_hint ? (
                  <div className="mt-4 rounded-xl border border-current/10 bg-white/60 px-3 py-3 text-sm">
                    <span className="font-medium">Azione consigliata:</span> {insight.action_hint}
                  </div>
                ) : null}
              </article>
            ))
          ) : (
            <EmptyState icon={SearchIcon} title="Insight non disponibili" description="Non ci sono abbastanza segnali per sintetizzare suggerimenti automatici nella finestra selezionata." />
          )}
        </div>
      </section>

      <section className="grid gap-4 xl:grid-cols-3">
        <TrendList title="Nuove richieste per giorno" items={series} valueKey="created_count" />
        <TrendList title="Casi risolti per giorno" items={series} valueKey="resolved_count" />
        <TrendList title="Pressione aperti per giorno" items={series} valueKey="open_count" />
        <TrendList title="Feature richieste per giorno" items={series} valueKey="feature_request_count" />
        <TrendList title="Bug / anomalie per giorno" items={series} valueKey="bug_report_count" />
        <TrendList title="Urgenze per giorno" items={series} valueKey="urgent_count" />
      </section>

      <section className="grid gap-4 xl:grid-cols-3">
        <TopList title="Top tipi richiesta" items={summary?.top_request_types ?? []} formatter={humanizeRequestType} />
        <TopList title="Top moduli" items={summary?.top_modules ?? []} formatter={humanizeModule} />
        <TopList title="Top stati" items={summary?.top_statuses ?? []} formatter={humanizeStatus} />
        <TopList title="Top severità" items={summary?.top_severities ?? []} formatter={humanizeSeverity} />
        <TopList title="Top delivery" items={summary?.top_delivery_statuses ?? []} formatter={humanizeDeliveryStatus} />
        <TopList title="Top impatto" items={summary?.top_impact_scopes ?? []} formatter={humanizeImpact} />
        <TopList title="Top priorità" items={summary?.top_priorities ?? []} />
        <TopList title="Canali di origine" items={summary?.top_source_channels ?? []} />
        <TopList title="Top assegnatari" items={summary?.top_assignees ?? []} />
        <TopList title="Top autori" items={summary?.top_creators ?? []} />
        <TopList title="Pagine più segnalate" items={summary?.top_pages ?? []} />
      </section>

      <section className="rounded-[28px] border border-[#e3e6dc] bg-white p-5 shadow-sm">
        <div className="space-y-2">
          <p className="text-sm font-semibold text-[#223d30]">Cluster richieste</p>
          <p className="text-sm text-[#5f6e67]">
            Raggruppamento pragmatico per deduplica, modulo, pagina e lessico ricorrente. Serve a capire dove il Wiki e il prodotto generano attrito ripetuto.
          </p>
        </div>
        <div className="mt-4 grid gap-3 xl:grid-cols-2">
          {clusters.length > 0 ? (
            clusters.map((cluster) => (
              <article key={cluster.cluster_key} className="rounded-2xl border border-gray-200 bg-[#fafbf8] p-4 shadow-sm">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold text-[#1D4E35]">{cluster.title}</p>
                    <p className="mt-1 text-xs text-gray-500">
                      {humanizeRequestType(cluster.request_type)}
                      {cluster.module_key ? ` · ${humanizeModule(cluster.module_key)}` : ""}
                      {cluster.page_path ? ` · ${cluster.page_path}` : ""}
                    </p>
                  </div>
                  <span className="rounded-full border border-gray-200 bg-white px-2 py-1 text-[11px] text-gray-600">
                    {cluster.total_requests} casi
                  </span>
                </div>
                <div className="mt-4 grid gap-3 sm:grid-cols-4">
                  <div className="rounded-xl border border-gray-200 bg-white px-3 py-3">
                    <p className="text-[11px] uppercase tracking-[0.18em] text-gray-400">Aperti</p>
                    <p className="mt-2 text-xl font-semibold text-gray-900">{cluster.open_requests}</p>
                  </div>
                  <div className="rounded-xl border border-gray-200 bg-white px-3 py-3">
                    <p className="text-[11px] uppercase tracking-[0.18em] text-gray-400">Duplicati</p>
                    <p className="mt-2 text-xl font-semibold text-gray-900">{cluster.duplicate_requests}</p>
                  </div>
                  <div className="rounded-xl border border-gray-200 bg-white px-3 py-3">
                    <p className="text-[11px] uppercase tracking-[0.18em] text-gray-400">Utenti</p>
                    <p className="mt-2 text-xl font-semibold text-gray-900">{cluster.affected_users}</p>
                  </div>
                  <div className="rounded-xl border border-gray-200 bg-white px-3 py-3">
                    <p className="text-[11px] uppercase tracking-[0.18em] text-gray-400">Canonici</p>
                    <p className="mt-2 text-xl font-semibold text-gray-900">{cluster.canonical_case_count}</p>
                  </div>
                </div>
                <div className="mt-4 space-y-2">
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Esempi reali</p>
                  {cluster.sample_questions.map((question) => (
                    <div key={`${cluster.cluster_key}-${question}`} className="rounded-xl border border-gray-100 bg-white px-3 py-2 text-sm text-gray-700">
                      {question}
                    </div>
                  ))}
                </div>
              </article>
            ))
          ) : (
            <EmptyState icon={SearchIcon} title="Cluster non disponibili" description="Non ci sono abbastanza richieste per costruire gruppi utili nella finestra selezionata." />
          )}
        </div>
      </section>
    </div>
  );
}
