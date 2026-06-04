"use client";

import { useEffect, useMemo, useState, type ReactNode } from "react";
import Link from "next/link";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ComposedChart,
  Legend,
  Line,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import {
  ModuleWorkspaceHero,
  ModuleWorkspaceKpiRow,
  ModuleWorkspaceKpiTile,
  ModuleWorkspaceNoticeCard,
} from "@/components/layout/module-workspace-hero";
import { RuoloModulePage } from "@/components/ruolo/module-page";
import { EmptyState } from "@/components/ui/empty-state";
import { AlertTriangleIcon, CalendarIcon, LockIcon, SearchIcon } from "@/components/ui/icons";
import { getStoredAccessToken } from "@/lib/auth";
import { ApiError } from "@/lib/api";
import { getRuoloParticelleSummary, getRuoloStats, getRuoloStatsAnalytics, getRuoloStatsComuni } from "@/lib/ruolo-api";
import type {
  RuoloStatsAnalyticsResponse,
  RuoloStatsByAnnoResponse,
  RuoloStatsComuneItem,
  RuoloStatsCountBreakdownItem,
} from "@/types/ruolo";

const PIE_COLORS = ["#1d4e35", "#8cb39d", "#f59e0b", "#ef4444", "#3b82f6", "#8b5cf6"];
const BAR_COLOR = "#1d4e35";
const BAR_ACCENT = "#8cb39d";
const WARNING_COLOR = "#f59e0b";

function formatEuro(value: number | null): string {
  if (value == null) return "—";
  return new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR" }).format(value);
}

function formatCompactEuro(value: number | null): string {
  if (value == null) return "—";
  return new Intl.NumberFormat("it-IT", {
    style: "currency",
    currency: "EUR",
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(value);
}

function formatInteger(value: number | null | undefined): string {
  if (value == null) return "—";
  return new Intl.NumberFormat("it-IT").format(value);
}

function coerceNumber(value: number | string | readonly (number | string)[] | undefined): number {
  if (Array.isArray(value)) {
    return coerceNumber(value[0]);
  }
  if (typeof value === "number") return value;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function SectionCard({
  title,
  description,
  children,
  action,
}: {
  title: string;
  description?: string;
  children: ReactNode;
  action?: ReactNode;
}) {
  return (
    <article className="rounded-[28px] border border-[#d8dfd3] bg-white shadow-panel">
      <div className="flex flex-wrap items-start justify-between gap-4 border-b border-[#edf1eb] bg-[linear-gradient(135deg,_rgba(29,78,53,0.06),_rgba(255,255,255,0.92))] px-6 py-5">
        <div>
          <p className="text-lg font-semibold text-gray-900">{title}</p>
          {description ? <p className="mt-2 max-w-3xl text-sm leading-6 text-gray-600">{description}</p> : null}
        </div>
        {action}
      </div>
      <div className="p-6">{children}</div>
    </article>
  );
}

function BreakdownFallback({ message }: { message: string }) {
  return <p className="py-12 text-center text-sm text-gray-400">{message}</p>;
}

function MatchLabel({ item }: { item: RuoloStatsCountBreakdownItem }) {
  return (
    <div className="flex items-center justify-between gap-4 rounded-2xl border border-[#e3e9e0] bg-[#fbfcfb] px-4 py-3 text-sm">
      <span className="font-medium text-gray-900">{item.label}</span>
      <span className="text-gray-600">{formatInteger(item.count)}</span>
    </div>
  );
}

export default function RuoloStatsPage() {
  const [token, setToken] = useState<string | null>(null);
  const [statsAnni, setStatsAnni] = useState<RuoloStatsByAnnoResponse[]>([]);
  const [selectedAnno, setSelectedAnno] = useState<number | null>(null);
  const [analytics, setAnalytics] = useState<RuoloStatsAnalyticsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingAnalytics, setLoadingAnalytics] = useState(false);
  const [isLegacyAnalyticsFallback, setIsLegacyAnalyticsFallback] = useState(false);

  useEffect(() => {
    setToken(getStoredAccessToken());
  }, []);

  useEffect(() => {
    if (!token) return;
    getRuoloStats(token)
      .then((r) => {
        const sortedItems = [...r.items].sort((left, right) => right.anno_tributario - left.anno_tributario);
        setStatsAnni(sortedItems);
        if (sortedItems.length > 0) setSelectedAnno(sortedItems[0].anno_tributario);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [token]);

  const selectedStats = useMemo(
    () => statsAnni.find((item) => item.anno_tributario === selectedAnno) ?? null,
    [statsAnni, selectedAnno],
  );

  useEffect(() => {
    if (!token || selectedAnno == null) return;
    setLoadingAnalytics(true);
    getRuoloStatsAnalytics(token, selectedAnno)
      .then((result) => {
        setAnalytics(result);
        setIsLegacyAnalyticsFallback(false);
      })
      .catch(async (error: unknown) => {
        if (!(error instanceof ApiError) || error.status !== 404) {
          console.error(error);
          return;
        }

        try {
          const [particelleSummary, comuniResponse] = await Promise.all([
            getRuoloParticelleSummary(token, selectedAnno),
            getRuoloStatsComuni(token, selectedAnno),
          ]);
          setAnalytics({
            anno_tributario: selectedAnno,
            particelle_summary: particelleSummary,
            tributi_breakdown: selectedStats ? [
              { key: "0648", label: "0648 Manutenzione", amount: selectedStats.totale_0648 ?? 0 },
              { key: "0985", label: "0985 Irrigazione", amount: selectedStats.totale_0985 ?? 0 },
              { key: "0668", label: "0668 Istituzionale", amount: selectedStats.totale_0668 ?? 0 },
            ] : [],
            match_status_breakdown: [],
            match_reason_breakdown: [],
            distretto_breakdown: [],
            coltura_breakdown: [],
            comuni: comuniResponse.items,
          });
          setIsLegacyAnalyticsFallback(true);
        } catch (fallbackError) {
          console.error(fallbackError);
        }
      })
      .finally(() => setLoadingAnalytics(false));
  }, [selectedAnno, selectedStats, token]);

  const totals = useMemo(
    () => statsAnni.reduce(
      (acc, item) => {
        acc.avvisi += item.total_avvisi;
        acc.euro += item.totale_euro ?? 0;
        return acc;
      },
      { avvisi: 0, euro: 0 },
    ),
    [statsAnni],
  );

  const trendData = useMemo(
    () => [...statsAnni]
      .sort((left, right) => left.anno_tributario - right.anno_tributario)
      .map((item) => ({
        anno: String(item.anno_tributario),
        avvisi: item.total_avvisi,
        collegati: item.avvisi_collegati,
        non_collegati: item.avvisi_non_collegati,
        totale_euro: item.totale_euro ?? 0,
      })),
    [statsAnni],
  );

  const topComuni = useMemo(
    () => [...(analytics?.comuni ?? [])]
      .sort((left, right) => (right.totale_euro ?? 0) - (left.totale_euro ?? 0))
      .slice(0, 8),
    [analytics],
  );

  const topComune = topComuni[0] ?? null;

  return (
    <RuoloModulePage
      title="Statistiche Ruolo"
      description="Vista analitica per annualità, tributi, qualità catasto e distribuzione territoriale."
      breadcrumb="Statistiche"
      requiredSection="ruolo.stats"
    >
      <div className="space-y-8">
        {loading ? (
          <p className="text-sm text-gray-400">Caricamento...</p>
        ) : (
          <>
            <ModuleWorkspaceHero
              badge={
                <>
                  <LockIcon className="h-3.5 w-3.5" />
                  Analytics Ruolo
                </>
              }
              title="Lettura operativa del ruolo per anno, comune e qualità del dato."
              description="La pagina ora separa chiaramente trend storico, peso economico dei tributi, qualità dei match catastali e cluster comunali, con accessi rapidi alle liste operative."
              actions={
                <>
              <ModuleWorkspaceNoticeCard
                    title={selectedStats ? `Anno in focus: ${selectedStats.anno_tributario}` : "Nessun anno selezionato"}
                    description={
                      selectedStats
                        ? `${selectedStats.total_avvisi} avvisi, totale ${formatEuro(selectedStats.totale_euro)} e ${formatInteger(analytics?.particelle_summary.total_particelle ?? null)} particelle.`
                        : "Carica dati Ruolo per abilitare l'analisi storica."
                    }
                    tone={selectedStats ? "info" : "warning"}
                  />
                  <ModuleWorkspaceNoticeCard
                    title={topComune ? `Comune leader: ${topComune.comune_nome}` : "Nessun dettaglio comunale"}
                    description={
                      topComune
                        ? `${topComune.num_avvisi} avvisi, ${formatInteger(topComune.num_particelle)} particelle e totale ${formatEuro(topComune.totale_euro)}.`
                        : "Il ranking dei comuni apparirà dopo la selezione di un anno con dati validi."
                    }
                    tone={topComune ? "success" : "neutral"}
                  />
                  {isLegacyAnalyticsFallback ? (
                    <ModuleWorkspaceNoticeCard
                      title="Modalita compatibile"
                      description="Il backend non espone ancora gli analytics avanzati: la pagina usa il fallback sui vecchi endpoint."
                      tone="warning"
                    />
                  ) : null}
                </>
              }
            >
              <ModuleWorkspaceKpiRow>
                <ModuleWorkspaceKpiTile label="Annualità" value={statsAnni.length} hint="Anni tributari disponibili" />
                <ModuleWorkspaceKpiTile label="Avvisi storici" value={formatInteger(totals.avvisi)} hint="Somma di tutte le annualità" />
                <ModuleWorkspaceKpiTile label="Totale storico" value={formatEuro(totals.euro)} hint="Importo complessivo del ruolo" />
                <ModuleWorkspaceKpiTile
                  label="Particelle anno"
                  value={formatInteger(analytics?.particelle_summary.total_particelle ?? null)}
                  hint={selectedAnno ? `Dataset ${selectedAnno}` : "Seleziona un anno"}
                />
                <ModuleWorkspaceKpiTile
                  label="Non collegate"
                  value={formatInteger(analytics?.particelle_summary.non_collegate_catasto ?? null)}
                  hint="Residuo verso il catasto corrente"
                  variant={(analytics?.particelle_summary.non_collegate_catasto ?? 0) > 0 ? "amber" : "default"}
                />
              </ModuleWorkspaceKpiRow>
            </ModuleWorkspaceHero>

            <SectionCard
              title="Trend storico annualità"
              description="Confronta l'andamento degli avvisi e del valore economico nel tempo. La linea mostra il totale euro, le barre la composizione anagrafica."
            >
              {trendData.length === 0 ? (
                <EmptyState
                  icon={CalendarIcon}
                  title="Nessun trend disponibile"
                  description="Importa almeno un'annualità per abilitare i grafici storici."
                />
              ) : (
                <div className="space-y-6">
                  <div className="flex flex-wrap gap-2">
                    {statsAnni.map((item) => (
                      <button
                        key={item.anno_tributario}
                        type="button"
                        onClick={() => setSelectedAnno(item.anno_tributario)}
                        className={`rounded-full px-4 py-2 text-sm font-medium transition ${
                          item.anno_tributario === selectedAnno
                            ? "bg-[#1d4e35] text-white"
                            : "border border-[#d6e5db] bg-white text-[#1d4e35] hover:bg-[#f3f8f5]"
                        }`}
                      >
                        {item.anno_tributario}
                      </button>
                    ))}
                  </div>
                  <div className="h-[320px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <ComposedChart data={trendData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#edf1eb" />
                        <XAxis dataKey="anno" tick={{ fontSize: 12 }} />
                        <YAxis yAxisId="left" tick={{ fontSize: 12 }} />
                        <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 12 }} />
                        <Tooltip
                          formatter={(value: number | string | readonly (number | string)[] | undefined, name: string | number | undefined) => (
                            name === "totale_euro"
                              ? [formatEuro(coerceNumber(value)), "Totale euro"]
                              : [formatInteger(coerceNumber(value)), name === "collegati" ? "Collegati" : name === "non_collegati" ? "Non collegati" : "Avvisi"]
                          )}
                        />
                        <Legend />
                        <Bar yAxisId="left" dataKey="collegati" name="Collegati" stackId="a" fill={BAR_COLOR} radius={[4, 4, 0, 0]} />
                        <Bar yAxisId="left" dataKey="non_collegati" name="Non collegati" stackId="a" fill={WARNING_COLOR} radius={[4, 4, 0, 0]} />
                        <Line yAxisId="right" type="monotone" dataKey="totale_euro" name="Totale euro" stroke="#3b82f6" strokeWidth={2} dot={false} />
                      </ComposedChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              )}
            </SectionCard>

            <section className="grid gap-4 xl:grid-cols-[0.82fr,1.18fr]">
              <SectionCard
                title={selectedAnno ? `Focus ${selectedAnno}` : "Focus annualità"}
                description="Indicatori rapidi e accessi diretti alle liste operative dell'anno selezionato."
              >
                <div className="grid gap-3">
                  <div className="rounded-2xl border border-[#e3e9e0] bg-[#fbfcfb] p-4">
                    <p className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">Avvisi</p>
                    <p className="mt-2 text-2xl font-semibold text-gray-900">{formatInteger(selectedStats?.total_avvisi ?? null)}</p>
                    <p className="mt-1 text-sm text-gray-600">
                      {formatInteger(selectedStats?.avvisi_collegati ?? null)} collegati, {formatInteger(selectedStats?.avvisi_non_collegati ?? null)} orfani anagrafica.
                    </p>
                  </div>
                  <div className="rounded-2xl border border-[#e3e9e0] bg-[#fbfcfb] p-4">
                    <p className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">Catasto</p>
                    <p className="mt-2 text-2xl font-semibold text-gray-900">{formatInteger(analytics?.particelle_summary.collegate_catasto ?? null)}</p>
                    <p className="mt-1 text-sm text-gray-600">
                      {formatInteger(analytics?.particelle_summary.non_collegate_catasto ?? null)} particelle non collegate e {formatInteger(analytics?.particelle_summary.soppresse_ade ?? null)} soppresse AdE.
                    </p>
                  </div>
                  <div className="rounded-2xl border border-[#e3e9e0] bg-[#fbfcfb] p-4">
                    <p className="text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">Importo</p>
                    <p className="mt-2 text-2xl font-semibold text-gray-900">{formatEuro(selectedStats?.totale_euro ?? null)}</p>
                    <p className="mt-1 text-sm text-gray-600">
                      0648: {formatCompactEuro(selectedStats?.totale_0648 ?? null)} · 0985+0668: {formatCompactEuro((selectedStats?.totale_0985 ?? 0) + (selectedStats?.totale_0668 ?? 0))}
                    </p>
                  </div>
                </div>
                <div className="mt-6 grid gap-3 sm:grid-cols-2">
                  <Link href={selectedAnno ? `/ruolo/avvisi?anno=${selectedAnno}` : "/ruolo/avvisi"} className="rounded-xl border border-[#d6e5db] bg-white px-4 py-3 text-sm font-medium text-[#1D4E35] transition hover:bg-[#f3f8f5]">
                    Apri avvisi dell&apos;anno
                  </Link>
                  <Link href={selectedAnno ? `/ruolo/avvisi?anno=${selectedAnno}&unlinked=true` : "/ruolo/avvisi?unlinked=true"} className="rounded-xl border border-[#d6e5db] bg-white px-4 py-3 text-sm font-medium text-[#1D4E35] transition hover:bg-[#f3f8f5]">
                    Apri avvisi orfani
                  </Link>
                  <Link href={selectedAnno ? `/ruolo/particelle?anno=${selectedAnno}&unmatched_only=false` : "/ruolo/particelle?unmatched_only=false"} className="rounded-xl border border-[#d6e5db] bg-white px-4 py-3 text-sm font-medium text-[#1D4E35] transition hover:bg-[#f3f8f5]">
                    Apri tutte le particelle
                  </Link>
                  <Link href={selectedAnno ? `/ruolo/particelle?anno=${selectedAnno}` : "/ruolo/particelle"} className="rounded-xl border border-[#d6e5db] bg-white px-4 py-3 text-sm font-medium text-[#1D4E35] transition hover:bg-[#f3f8f5]">
                    Apri particelle non collegate
                  </Link>
                </div>
              </SectionCard>

              <SectionCard
                title="Qualità del collegamento catastale"
                description="Legge subito quanto del ruolo è già conciliato col catasto corrente e dove si concentra il residuo."
                action={loadingAnalytics ? <span className="text-sm text-gray-500">Aggiornamento...</span> : null}
              >
                {loadingAnalytics || !analytics ? (
                  <BreakdownFallback message="Caricamento qualità catasto..." />
                ) : isLegacyAnalyticsFallback ? (
                  <BreakdownFallback message="Distribuzione di match non disponibile sul backend corrente." />
                ) : (
                  <div className="grid gap-6 lg:grid-cols-[0.9fr,1.1fr]">
                    <div className="h-[260px]">
                      <ResponsiveContainer width="100%" height="100%">
                        <PieChart>
                          <Pie
                            data={analytics.match_status_breakdown}
                            dataKey="count"
                            nameKey="label"
                            cx="50%"
                            cy="50%"
                            outerRadius={86}
                            label={({ percent = 0, name }) => `${String(name)} ${(percent * 100).toFixed(0)}%`}
                            labelLine={false}
                          >
                            {analytics.match_status_breakdown.map((entry, index) => (
                              <Cell key={entry.key} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                            ))}
                          </Pie>
                          <Tooltip formatter={(value: number | string | readonly (number | string)[] | undefined) => [formatInteger(coerceNumber(value)), "Particelle"]} />
                        </PieChart>
                      </ResponsiveContainer>
                    </div>
                    <div className="space-y-3">
                      {analytics.match_status_breakdown.map((item) => <MatchLabel key={item.key} item={item} />)}
                    </div>
                  </div>
                )}
              </SectionCard>
            </section>

            <section className="grid gap-4 xl:grid-cols-2">
              <SectionCard
                title="Peso economico dei tributi"
                description="Mostra la composizione dell'importo annuo tra manutenzione, irrigazione e voce istituzionale."
              >
                {loadingAnalytics || !analytics ? (
                  <BreakdownFallback message="Caricamento tributi..." />
                ) : (
                  <div className="h-[280px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={analytics.tributi_breakdown} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#edf1eb" />
                        <XAxis dataKey="key" tick={{ fontSize: 12 }} />
                        <YAxis tick={{ fontSize: 12 }} />
                        <Tooltip formatter={(value: number | string | readonly (number | string)[] | undefined) => [formatEuro(coerceNumber(value)), "Importo"]} />
                        <Bar dataKey="amount" fill={BAR_COLOR} radius={[4, 4, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </SectionCard>

              <SectionCard
                title="Cause principali del mancato match"
                description="Evidenzia i motivi più frequenti del residuo non ancora agganciato al catasto."
              >
                {loadingAnalytics || !analytics ? (
                  <BreakdownFallback message="Caricamento cause di mancato match..." />
                ) : isLegacyAnalyticsFallback ? (
                  <BreakdownFallback message="Le cause di mancato match richiedono l'endpoint analytics avanzato." />
                ) : analytics.match_reason_breakdown.length === 0 ? (
                  <EmptyState
                    icon={AlertTriangleIcon}
                    title="Nessun residuo aperto"
                    description="Per l'anno selezionato non risultano cause di mancato match da analizzare."
                  />
                ) : (
                  <div className="h-[280px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={[...analytics.match_reason_breakdown].reverse()} layout="vertical" margin={{ top: 8, right: 8, left: 8, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#edf1eb" />
                        <XAxis type="number" tick={{ fontSize: 12 }} />
                        <YAxis type="category" dataKey="label" tick={{ fontSize: 11 }} width={180} />
                        <Tooltip formatter={(value: number | string | readonly (number | string)[] | undefined) => [formatInteger(coerceNumber(value)), "Particelle"]} />
                        <Bar dataKey="count" fill={WARNING_COLOR} radius={[0, 4, 4, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </SectionCard>
            </section>

            <SectionCard
              title={selectedAnno ? `Top comuni ${selectedAnno}` : "Top comuni"}
              description="Classifica economica e territoriale dei comuni, con evidenza del residuo non collegato e link diretti alle liste di lavoro."
            >
              {loadingAnalytics || !analytics ? (
                <BreakdownFallback message="Caricamento ranking comuni..." />
              ) : topComuni.length === 0 ? (
                <EmptyState
                  icon={SearchIcon}
                  title="Nessuna distribuzione comunale"
                  description="L'anno selezionato non espone ancora un breakdown per comune."
                />
              ) : (
                <div className="grid gap-6 xl:grid-cols-[1.1fr,0.9fr]">
                  <div className="h-[320px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={topComuni} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#edf1eb" />
                        <XAxis dataKey="comune_nome" tick={{ fontSize: 11 }} angle={-18} textAnchor="end" height={70} />
                        <YAxis tick={{ fontSize: 12 }} />
                        <Tooltip formatter={(value: number | string | readonly (number | string)[] | undefined, name: string | number | undefined) => [name === "totale_euro" ? formatEuro(coerceNumber(value)) : formatInteger(coerceNumber(value)), name === "totale_euro" ? "Totale €" : "Residuo catasto"]} />
                        <Legend />
                        <Bar dataKey="totale_euro" name="Totale €" fill={BAR_COLOR} radius={[4, 4, 0, 0]} />
                        <Bar dataKey="non_collegate_catasto" name="Non collegate" fill={WARNING_COLOR} radius={[4, 4, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                  <div className="space-y-3">
                    {topComuni.map((comune: RuoloStatsComuneItem) => (
                      <div key={comune.comune_nome} className="rounded-2xl border border-[#e3e9e0] bg-[#fbfcfb] p-4">
                        <div className="flex items-start justify-between gap-4">
                          <div>
                            <p className="text-sm font-semibold text-gray-900">{comune.comune_nome}</p>
                            <p className="mt-1 text-sm text-gray-600">
                              {formatInteger(comune.num_avvisi)} avvisi · {formatInteger(comune.num_particelle)} particelle · {formatInteger(comune.non_collegate_catasto)} non collegate
                            </p>
                          </div>
                          <p className="text-sm font-semibold text-[#1d4e35]">{formatEuro(comune.totale_euro)}</p>
                        </div>
                        <div className="mt-3 flex flex-wrap gap-2">
                          <Link href={`/ruolo/avvisi?anno=${selectedAnno ?? ""}&comune=${encodeURIComponent(comune.comune_nome)}`} className="rounded-lg border border-[#d6e5db] bg-white px-3 py-2 text-xs font-medium text-[#1D4E35] transition hover:bg-[#f3f8f5]">
                            Avvisi
                          </Link>
                          <Link href={`/ruolo/particelle?anno=${selectedAnno ?? ""}&comune=${encodeURIComponent(comune.comune_nome)}`} className="rounded-lg border border-[#d6e5db] bg-white px-3 py-2 text-xs font-medium text-[#1D4E35] transition hover:bg-[#f3f8f5]">
                            Non collegate
                          </Link>
                          <Link href={`/ruolo/particelle?anno=${selectedAnno ?? ""}&comune=${encodeURIComponent(comune.comune_nome)}&unmatched_only=false`} className="rounded-lg border border-[#d6e5db] bg-white px-3 py-2 text-xs font-medium text-[#1D4E35] transition hover:bg-[#f3f8f5]">
                            Tutte le particelle
                          </Link>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </SectionCard>

            <section className="grid gap-4 xl:grid-cols-2">
              <SectionCard
                title="Top distretti"
                description="Aiuta a capire dove si concentra il carico particellare dell'anno selezionato."
              >
                {loadingAnalytics || !analytics ? (
                  <BreakdownFallback message="Caricamento distretti..." />
                ) : isLegacyAnalyticsFallback ? (
                  <BreakdownFallback message="La distribuzione per distretto richiede l'endpoint analytics avanzato." />
                ) : analytics.distretto_breakdown.length === 0 ? (
                  <BreakdownFallback message="Nessun distretto disponibile." />
                ) : (
                  <div className="h-[280px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={analytics.distretto_breakdown} layout="vertical" margin={{ top: 8, right: 8, left: 8, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#edf1eb" />
                        <XAxis type="number" tick={{ fontSize: 12 }} />
                        <YAxis type="category" dataKey="label" tick={{ fontSize: 11 }} width={90} />
                        <Tooltip formatter={(value: number | string | readonly (number | string)[] | undefined) => [formatInteger(coerceNumber(value)), "Particelle"]} />
                        <Bar dataKey="count" fill={BAR_ACCENT} radius={[0, 4, 4, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </SectionCard>

              <SectionCard
                title="Top colture"
                description="Offre una prima lettura tecnica della composizione agronomica del ruolo."
              >
                {loadingAnalytics || !analytics ? (
                  <BreakdownFallback message="Caricamento colture..." />
                ) : isLegacyAnalyticsFallback ? (
                  <BreakdownFallback message="La distribuzione per coltura richiede l'endpoint analytics avanzato." />
                ) : analytics.coltura_breakdown.length === 0 ? (
                  <BreakdownFallback message="Nessuna coltura disponibile." />
                ) : (
                  <div className="h-[280px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={analytics.coltura_breakdown} layout="vertical" margin={{ top: 8, right: 8, left: 8, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#edf1eb" />
                        <XAxis type="number" tick={{ fontSize: 12 }} />
                        <YAxis type="category" dataKey="label" tick={{ fontSize: 11 }} width={140} />
                        <Tooltip formatter={(value: number | string | readonly (number | string)[] | undefined) => [formatInteger(coerceNumber(value)), "Particelle"]} />
                        <Bar dataKey="count" fill="#3b82f6" radius={[0, 4, 4, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </SectionCard>
            </section>
          </>
        )}
      </div>
    </RuoloModulePage>
  );
}
