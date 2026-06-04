"use client";

import { useMemo, useEffect, useState } from "react";
import Link from "next/link";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import {
  ModuleWorkspaceHero,
  ModuleWorkspaceKpiRow,
  ModuleWorkspaceKpiTile,
  ModuleWorkspaceMiniStat,
  ModuleWorkspaceNoticeCard,
} from "@/components/layout/module-workspace-hero";
import { RuoloModulePage } from "@/components/ruolo/module-page";
import { RuoloWorkspaceModal } from "@/components/ruolo/workspace-modal";
import { EmptyState } from "@/components/ui/empty-state";
import { AlertTriangleIcon, CalendarIcon, DocumentIcon, FolderIcon, LockIcon, RefreshIcon, SearchIcon } from "@/components/ui/icons";
import { getStoredAccessToken } from "@/lib/auth";
import { getRuoloParticelleSummary, getRuoloStats, listImportJobs } from "@/lib/ruolo-api";
import type { RuoloParticelleSummaryResponse, RuoloStatsByAnnoResponse, RuoloImportJobResponse } from "@/types/ruolo";

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

function formatInteger(value: number): string {
  return new Intl.NumberFormat("it-IT").format(value);
}

function normalizeTooltipValue(value: unknown): number {
  if (Array.isArray(value)) {
    const first = value[0];
    return Number(first ?? 0);
  }
  return Number(value ?? 0);
}

function formatTooltipEuro(value: unknown): [string, string] {
  return [formatEuro(normalizeTooltipValue(value)), "Totale euro"];
}

function formatTooltipInteger(value: unknown, label: string): [string, string] {
  return [formatInteger(normalizeTooltipValue(value)), label];
}

function formatRuoloJobLabel(job: RuoloImportJobResponse): string {
  const raw = (job.filename ?? "").trim();
  if (!raw) {
    return `Import ruolo ${job.anno_tributario}`;
  }

  const normalized = raw.toLowerCase();
  const yearFromName = normalized.match(/(20\d{2})/)?.[1] ?? String(job.anno_tributario);

  if (normalized.includes("incass_backfill")) {
    return `Recupero storico InCass ${yearFromName}`;
  }
  if (normalized.includes("ruolo_harvest") || normalized.includes("ruolo-harvest")) {
    return `Raccolta partitario InCass ${yearFromName}`;
  }
  if (normalized.includes("backfill") && normalized.includes("ruolo")) {
    return `Completamento dati ruolo ${yearFromName}`;
  }
  if (normalized.includes("repair") && normalized.includes("ruolo")) {
    return `Bonifica collegamenti ruolo ${yearFromName}`;
  }
  if (normalized.endsWith(".dmp")) {
    return `Import file ruolo ${yearFromName}`;
  }
  if (normalized.endsWith(".pdf")) {
    return `Import PDF ruolo ${yearFromName}`;
  }
  return raw.replace(/[_-]+/g, " ");
}

function formatRuoloJobStatus(status: string): string {
  const labels: Record<string, string> = {
    pending: "In attesa",
    running: "In corso",
    completed: "Completato",
    failed: "Con errori",
  };
  return labels[status] ?? status;
}

function formatRuoloJobDescription(job: RuoloImportJobResponse): string {
  const raw = (job.filename ?? "").trim().toLowerCase();
  if (!raw) {
    return "Caricamento del ruolo senza nome file disponibile.";
  }
  if (raw.includes("incass_backfill")) {
    return "Recupero storico degli avvisi e del partitario da InCass.";
  }
  if (raw.includes("ruolo_harvest") || raw.includes("ruolo-harvest")) {
    return "Raccolta massiva del partitario dagli avvisi a ruolo.";
  }
  if (raw.includes("backfill") && raw.includes("ruolo")) {
    return "Completamento del dataset ruolo a partire da dati gia raccolti.";
  }
  if (raw.includes("repair") && raw.includes("ruolo")) {
    return "Bonifica dei collegamenti catastali del ruolo.";
  }
  if (raw.endsWith(".dmp")) {
    return "Import del dump ruolo originale.";
  }
  if (raw.endsWith(".pdf")) {
    return "Import del PDF testuale del ruolo.";
  }
  return "Elaborazione tecnica del modulo ruolo.";
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    pending: "bg-yellow-100 text-yellow-800",
    running: "bg-blue-100 text-blue-800",
    completed: "bg-green-100 text-green-800",
    failed: "bg-red-100 text-red-800",
  };
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${colors[status] ?? "bg-gray-100 text-gray-700"}`}>
      {formatRuoloJobStatus(status)}
    </span>
  );
}

export default function RuoloDashboardPage() {
  const [token, setToken] = useState<string | null>(null);
  const [stats, setStats] = useState<RuoloStatsByAnnoResponse[]>([]);
  const [particelleSummary, setParticelleSummary] = useState<RuoloParticelleSummaryResponse | null>(null);
  const [recentJobs, setRecentJobs] = useState<RuoloImportJobResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [workspaceModal, setWorkspaceModal] = useState<{ href: string; title: string; description?: string | null } | null>(null);

  useEffect(() => {
    setToken(getStoredAccessToken());
  }, []);

  useEffect(() => {
    if (!token) return;
    Promise.all([
      getRuoloStats(token),
      getRuoloParticelleSummary(token),
      listImportJobs(token, undefined, 1, 5),
    ])
      .then(([statsData, particelleData, jobsData]) => {
        setStats(statsData.items);
        setParticelleSummary(particelleData);
        setRecentJobs(jobsData.items);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [token]);

  const latestYearStats = useMemo(() => {
    if (stats.length === 0) {
      return null;
    }
    return [...stats].sort((left, right) => right.anno_tributario - left.anno_tributario)[0];
  }, [stats]);

  const totals = useMemo(() => {
    return stats.reduce(
      (acc, item) => {
        acc.avvisi += item.total_avvisi;
        acc.nonCollegatiAnagrafica += item.avvisi_non_collegati;
        acc.totaleEuro += item.totale_euro ?? 0;
        return acc;
      },
      { avvisi: 0, nonCollegatiAnagrafica: 0, totaleEuro: 0 },
    );
  }, [stats]);

  const runningJobs = recentJobs.filter((job) => job.status === "running" || job.status === "pending");
  const failedJobs = recentJobs.filter((job) => job.status === "failed");
  const annualTrendData = useMemo(
    () => [...stats]
      .sort((left, right) => left.anno_tributario - right.anno_tributario)
      .map((item) => ({
        anno: String(item.anno_tributario),
        avvisi: item.total_avvisi,
        orfani: item.avvisi_non_collegati,
        totaleEuro: item.totale_euro ?? 0,
      })),
    [stats],
  );
  const latestCoverage = useMemo(() => {
    if (!latestYearStats || latestYearStats.total_avvisi === 0) return 0;
    return Math.round((latestYearStats.avvisi_collegati / latestYearStats.total_avvisi) * 100);
  }, [latestYearStats]);
  const catastoCoverage = useMemo(() => {
    if (!particelleSummary || particelleSummary.total_particelle === 0) return 0;
    return Math.round((particelleSummary.collegate_catasto / particelleSummary.total_particelle) * 100);
  }, [particelleSummary]);

  function openWorkspaceModal(href: string, title: string, description?: string): void {
    setWorkspaceModal({ href, title, description });
  }

  return (
    <RuoloModulePage
      title="GAIA Ruolo"
      description="Dashboard del modulo ruolo consortile."
      requiredSection="ruolo.dashboard"
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
                  Workspace Ruolo
                </>
              }
              title="Cruscotto operativo del ruolo consortile."
              description="Monitora gli anni importati, separa gli scarti anagrafici dai mancati collegamenti catastali e apri rapidamente import, dettaglio avvisi e statistiche senza perdere il contesto del modulo."
              actions={
                <>
                  <ModuleWorkspaceNoticeCard
                    title={latestYearStats ? `Ultimo anno disponibile: ${latestYearStats.anno_tributario}` : "Nessun anno disponibile"}
                    description={
                      latestYearStats
                        ? `${latestYearStats.total_avvisi} avvisi e totale ${formatEuro(latestYearStats.totale_euro)}. I collegamenti anagrafici e catastali sono letti separatamente nel cruscotto.`
                        : "Carica il primo file Ruolo per iniziare a popolare dashboard, avvisi e statistiche."
                    }
                    tone={latestYearStats ? "info" : "warning"}
                  />
                  <ModuleWorkspaceNoticeCard
                    title={runningJobs.length > 0 ? "Import in esecuzione" : failedJobs.length > 0 ? "Ultimi import con errori" : "Pipeline import stabile"}
                    description={
                      runningJobs.length > 0
                        ? `${runningJobs.length} job in corso o in attesa di completamento.`
                        : failedJobs.length > 0
                          ? `${failedJobs.length} job recenti terminati con errori. Controlla lo storico import.`
                          : recentJobs.length > 0
                            ? "Gli ultimi job risultano completati senza criticità aperte."
                            : "Nessun job registrato finora nel workspace Ruolo."
                    }
                    tone={runningJobs.length > 0 ? "warning" : failedJobs.length > 0 ? "danger" : "success"}
                  />
                </>
              }
            >
              <ModuleWorkspaceKpiRow>
                <ModuleWorkspaceKpiTile
                  label="Avvisi totali"
                  value={totals.avvisi}
                  hint={stats.length > 0 ? `${stats.length} anni importati` : "Nessun anno"}
                />
                <ModuleWorkspaceKpiTile
                  label="Avvisi non collegati"
                  value={totals.nonCollegatiAnagrafica}
                  hint="Non mappati su soggetti GAIA"
                  variant={totals.nonCollegatiAnagrafica > 0 ? "amber" : "default"}
                />
                <ModuleWorkspaceKpiTile
                  label="Particelle non collegate"
                  value={particelleSummary?.non_collegate_catasto ?? "—"}
                  hint="Assenti in `cat_particelle`"
                  variant={(particelleSummary?.non_collegate_catasto ?? 0) > 0 ? "amber" : "default"}
                />
                <ModuleWorkspaceKpiTile
                  label="Soppresse AdE"
                  value={particelleSummary?.soppresse_ade ?? "—"}
                  hint="Classificate `suppressed`"
                  variant={(particelleSummary?.soppresse_ade ?? 0) > 0 ? "amber" : "default"}
                />
                <ModuleWorkspaceKpiTile
                  label="Importi complessivi"
                  value={formatEuro(totals.totaleEuro)}
                  hint="Somma storica degli anni importati"
                />
              </ModuleWorkspaceKpiRow>
            </ModuleWorkspaceHero>

            <section className="grid gap-4 xl:grid-cols-[1.1fr,0.9fr]">
              <article className="rounded-[28px] border border-[#d8dfd3] bg-white shadow-panel">
                <div className="border-b border-[#edf1eb] bg-[linear-gradient(135deg,_rgba(29,78,53,0.06),_rgba(255,255,255,0.92))] px-6 py-5">
                  <p className="inline-flex items-center gap-2 rounded-full bg-[#e8f2ec] px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-[#1D4E35]">
                    <DocumentIcon className="h-3.5 w-3.5" />
                    Accessi rapidi
                  </p>
                  <p className="mt-3 text-lg font-semibold text-gray-900">Apri i flussi principali del modulo.</p>
                  <p className="mt-2 max-w-2xl text-sm leading-6 text-gray-600">
                    Usa i workspace rapidi per import, consultazione avvisi, ricerca particelle a ruolo e analisi statistiche mantenendo il contesto della dashboard.
                  </p>
                </div>
                <div className="grid gap-4 p-6 md:grid-cols-2 xl:grid-cols-4">
                  <button
                    type="button"
                    onClick={() => openWorkspaceModal("/ruolo/import", "Import Ruolo", "Carica un file Ruolo senza uscire dalla dashboard.")}
                    className="rounded-2xl border border-[#d8dfd3] bg-[linear-gradient(180deg,_#ffffff,_#f6faf7)] p-5 text-left shadow-sm transition hover:border-[#8CB39D] hover:shadow"
                  >
                    <RefreshIcon className="h-5 w-5 text-[#1D4E35]" />
                    <p className="mt-4 text-sm font-semibold text-gray-900">Import</p>
                    <p className="mt-1 text-sm leading-6 text-gray-600">Carica `.dmp` o PDF testuale e monitora l&apos;avvio del job.</p>
                  </button>
                  <Link
                    href="/ruolo/avvisi"
                    className="rounded-2xl border border-[#d8dfd3] bg-[linear-gradient(180deg,_#ffffff,_#f6faf7)] p-5 shadow-sm transition hover:border-[#8CB39D] hover:shadow"
                  >
                    <SearchIcon className="h-5 w-5 text-[#1D4E35]" />
                    <p className="mt-4 text-sm font-semibold text-gray-900">Avvisi</p>
                    <p className="mt-1 text-sm leading-6 text-gray-600">Filtra per anno, CF, comune, utenza e individua gli orfani.</p>
                  </Link>
                  <Link
                    href="/ruolo/particelle"
                    className="rounded-2xl border border-[#d8dfd3] bg-[linear-gradient(180deg,_#ffffff,_#f6faf7)] p-5 shadow-sm transition hover:border-[#8CB39D] hover:shadow"
                  >
                    <FolderIcon className="h-5 w-5 text-[#1D4E35]" />
                    <p className="mt-4 text-sm font-semibold text-gray-900">Particelle a ruolo</p>
                    <p className="mt-1 text-sm leading-6 text-gray-600">Apri la vista storica del ruolo, incluse particelle non collegate o soppresse da AdE.</p>
                  </Link>
                  <Link
                    href="/ruolo/stats"
                    className="rounded-2xl border border-[#d8dfd3] bg-[linear-gradient(180deg,_#ffffff,_#f6faf7)] p-5 shadow-sm transition hover:border-[#8CB39D] hover:shadow"
                  >
                    <CalendarIcon className="h-5 w-5 text-[#1D4E35]" />
                    <p className="mt-4 text-sm font-semibold text-gray-900">Statistiche</p>
                    <p className="mt-1 text-sm leading-6 text-gray-600">Analizza distribuzione per anno e ripartizione per comune.</p>
                  </Link>
                </div>
              </article>

              <article className="rounded-[28px] border border-[#d8dfd3] bg-white p-6 shadow-panel">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div>
                    <p className="inline-flex items-center gap-2 rounded-full bg-[#eef3ec] px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-[#1D4E35]">
                      <FolderIcon className="h-3.5 w-3.5" />
                      Stato dominio
                    </p>
                    <p className="mt-3 text-lg font-semibold text-gray-900">Qualità del dataset corrente.</p>
                    <p className="mt-2 text-sm leading-6 text-gray-600">
                      Sintesi rapida per capire se il dominio è pronto per consultazione o se richiede una nuova importazione / bonifica anagrafica.
                    </p>
                  </div>
                </div>
                <div className="mt-6 grid gap-3">
                  <ModuleWorkspaceMiniStat
                    eyebrow="Anno più recente"
                    value={latestYearStats?.anno_tributario ?? "—"}
                    description={latestYearStats ? `${latestYearStats.total_avvisi} avvisi caricati nell'ultimo import utile.` : "Nessun caricamento disponibile."}
                    tone="default"
                    compact
                  />
                  <ModuleWorkspaceMiniStat
                    eyebrow="Allineamento anagrafica"
                    value={latestYearStats ? `${latestYearStats.avvisi_collegati}/${latestYearStats.total_avvisi}` : "0/0"}
                    description={latestYearStats ? `${latestYearStats.avvisi_non_collegati} avvisi dell'anno più recente richiedono ancora collegamento.` : "L'indicatore sarà disponibile dopo il primo import."}
                    tone={latestYearStats && latestYearStats.avvisi_non_collegati > 0 ? "warning" : "success"}
                    compact
                  />
                  <ModuleWorkspaceMiniStat
                    eyebrow="Allineamento catasto"
                    value={particelleSummary ? `${particelleSummary.collegate_catasto}/${particelleSummary.total_particelle}` : "0/0"}
                    description={particelleSummary ? `${particelleSummary.non_collegate_catasto} particelle ruolo non trovano un match in catasto corrente; ${particelleSummary.soppresse_ade} risultano soppresse da AdE.` : "L'indicatore sarà disponibile dopo il primo import."}
                    tone={particelleSummary && particelleSummary.non_collegate_catasto > 0 ? "warning" : "success"}
                    compact
                  />
                  <ModuleWorkspaceMiniStat
                    eyebrow="Cronologia job"
                    value={recentJobs.length}
                    description={recentJobs.length > 0 ? `${runningJobs.length} in corso, ${failedJobs.length} con errori, ${recentJobs.filter((job) => job.status === "completed").length} completati.` : "Nessun job registrato."}
                    tone={failedJobs.length > 0 ? "warning" : "default"}
                    compact
                  />
                </div>
              </article>
            </section>

            <section className="grid gap-4 xl:grid-cols-[1.05fr,0.95fr]">
              <article className="rounded-[28px] border border-[#d8dfd3] bg-white shadow-panel">
                <div className="border-b border-[#edf1eb] bg-[linear-gradient(135deg,_rgba(29,78,53,0.06),_rgba(255,255,255,0.92))] px-6 py-5">
                  <p className="inline-flex items-center gap-2 rounded-full bg-[#e8f2ec] px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-[#1D4E35]">
                    <CalendarIcon className="h-3.5 w-3.5" />
                    Trend ruolo
                  </p>
                  <p className="mt-3 text-lg font-semibold text-gray-900">Andamento di avvisi e importi nel tempo.</p>
                  <p className="mt-2 max-w-2xl text-sm leading-6 text-gray-600">
                    Due letture immediate per l&apos;operatore: quanto pesa ogni annualità e dove restano avvisi orfani da collegare.
                  </p>
                </div>
                <div className="grid gap-6 p-6 lg:grid-cols-2">
                  <div>
                    <p className="mb-3 text-sm font-semibold text-gray-900">Totale economico per annualità</p>
                    {annualTrendData.length === 0 ? (
                      <EmptyState
                        icon={CalendarIcon}
                        title="Nessun trend disponibile"
                        description="Il grafico apparirà dopo il primo caricamento del ruolo."
                      />
                    ) : (
                      <div className="h-[240px]">
                        <ResponsiveContainer width="100%" height="100%">
                          <LineChart data={annualTrendData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#edf1eb" />
                            <XAxis dataKey="anno" tick={{ fontSize: 12 }} />
                            <YAxis tick={{ fontSize: 12 }} />
                            <Tooltip formatter={formatTooltipEuro} />
                            <Line type="monotone" dataKey="totaleEuro" stroke="#1D4E35" strokeWidth={2.5} dot />
                          </LineChart>
                        </ResponsiveContainer>
                      </div>
                    )}
                  </div>
                  <div>
                    <p className="mb-3 text-sm font-semibold text-gray-900">Avvisi orfani per annualità</p>
                    {annualTrendData.length === 0 ? (
                      <EmptyState
                        icon={AlertTriangleIcon}
                        title="Nessun dato disponibile"
                        description="L&apos;indicatore sarà disponibile dopo il primo import."
                      />
                    ) : (
                      <div className="h-[240px]">
                        <ResponsiveContainer width="100%" height="100%">
                          <BarChart data={annualTrendData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#edf1eb" />
                            <XAxis dataKey="anno" tick={{ fontSize: 12 }} />
                            <YAxis tick={{ fontSize: 12 }} />
                            <Tooltip formatter={(value) => formatTooltipInteger(value, "Avvisi orfani")} />
                            <Bar dataKey="orfani" fill="#f59e0b" radius={[4, 4, 0, 0]} />
                          </BarChart>
                        </ResponsiveContainer>
                      </div>
                    )}
                  </div>
                </div>
              </article>

              <article className="rounded-[28px] border border-[#d8dfd3] bg-white p-6 shadow-panel">
                <div>
                  <p className="inline-flex items-center gap-2 rounded-full bg-[#eef3ec] px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-[#1D4E35]">
                    <FolderIcon className="h-3.5 w-3.5" />
                    Lettura rapida
                  </p>
                  <p className="mt-3 text-lg font-semibold text-gray-900">Indicatori utili per partire da qui.</p>
                  <p className="mt-2 text-sm leading-6 text-gray-600">
                    Sintesi leggibile dell&apos;ultimo anno disponibile e della qualità del dominio corrente.
                  </p>
                </div>
                <div className="mt-6 grid gap-3">
                  <ModuleWorkspaceMiniStat
                    eyebrow="Ultimo anno"
                    value={latestYearStats?.anno_tributario ?? "—"}
                    description={latestYearStats ? `${formatInteger(latestYearStats.total_avvisi)} avvisi per ${formatCompactEuro(latestYearStats.totale_euro)}.` : "Nessun anno disponibile."}
                    compact
                  />
                  <ModuleWorkspaceMiniStat
                    eyebrow="Copertura anagrafica"
                    value={`${latestCoverage}%`}
                    description={latestYearStats ? `${formatInteger(latestYearStats.avvisi_non_collegati)} avvisi da collegare nell&apos;anno piu recente.` : "Indicatore non disponibile."}
                    tone={latestCoverage < 100 ? "warning" : "success"}
                    compact
                  />
                  <ModuleWorkspaceMiniStat
                    eyebrow="Copertura catasto"
                    value={`${catastoCoverage}%`}
                    description={particelleSummary ? `${formatInteger(particelleSummary.non_collegate_catasto)} particelle storiche senza match sul catasto corrente.` : "Indicatore non disponibile."}
                    tone={catastoCoverage < 100 ? "warning" : "success"}
                    compact
                  />
                  <ModuleWorkspaceMiniStat
                    eyebrow="Residuo AdE"
                    value={particelleSummary ? formatInteger(particelleSummary.soppresse_ade) : "—"}
                    description="Particelle classificate come soppresse nella scansione AdE."
                    tone={(particelleSummary?.soppresse_ade ?? 0) > 0 ? "warning" : "default"}
                    compact
                  />
                </div>
                <div className="mt-6 flex flex-wrap gap-3">
                  <Link
                    href="/ruolo/stats"
                    className="rounded-xl border border-[#d6e5db] bg-white px-4 py-2 text-sm font-medium text-[#1D4E35] transition hover:bg-[#f3f8f5]"
                  >
                    Apri analisi completa
                  </Link>
                  <Link
                    href={latestYearStats ? `/ruolo/avvisi?anno=${latestYearStats.anno_tributario}&unlinked=true` : "/ruolo/avvisi?unlinked=true"}
                    className="rounded-xl border border-[#d6e5db] bg-white px-4 py-2 text-sm font-medium text-[#1D4E35] transition hover:bg-[#f3f8f5]"
                  >
                    Apri avvisi da collegare
                  </Link>
                </div>
              </article>
            </section>

            <section className="grid gap-4 xl:grid-cols-[1.05fr,0.95fr]">
              <article className="rounded-[28px] border border-[#d8dfd3] bg-white shadow-panel">
                <div className="border-b border-[#edf1eb] bg-[linear-gradient(135deg,_rgba(29,78,53,0.06),_rgba(255,255,255,0.92))] px-6 py-5">
                  <p className="inline-flex items-center gap-2 rounded-full bg-[#e8f2ec] px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-[#1D4E35]">
                    <CalendarIcon className="h-3.5 w-3.5" />
                    Riepilogo per anno
                  </p>
                  <p className="mt-3 text-lg font-semibold text-gray-900">Andamento degli import per annualità.</p>
                  <p className="mt-2 max-w-2xl text-sm leading-6 text-gray-600">
                    Ogni card riassume volume avvisi, collegamenti anagrafici e importi complessivi dell&apos;anno tributario.
                  </p>
                </div>
                <div className="p-6">
                  {stats.length === 0 ? (
                    <EmptyState
                      icon={DocumentIcon}
                      title="Nessun dato importato"
                      description="Carica il primo file Ruolo per popolare il cruscotto annuale e sbloccare le viste di analisi."
                    />
                  ) : (
                    <div className="grid gap-4 sm:grid-cols-2">
                      {stats
                        .slice()
                        .sort((left, right) => right.anno_tributario - left.anno_tributario)
                        .map((s) => (
                          <div key={s.anno_tributario} className="rounded-2xl border border-[#e3e9e0] bg-[#fbfcfb] p-5">
                            <div className="flex items-start justify-between gap-3">
                              <div>
                                <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-gray-500">Anno tributario</p>
                                <p className="mt-2 text-2xl font-semibold text-gray-900">{s.anno_tributario}</p>
                              </div>
                              <Link
                                href={`/ruolo/avvisi?anno=${s.anno_tributario}`}
                                className="rounded-full border border-[#d6e5db] bg-white px-3 py-1 text-xs font-medium text-[#1D4E35] transition hover:bg-[#f3f8f5]"
                              >
                                Vedi avvisi
                              </Link>
                            </div>
                            <dl className="mt-5 grid grid-cols-2 gap-3 text-sm">
                              <div>
                                <dt className="text-gray-500">Avvisi</dt>
                                <dd className="mt-1 font-semibold text-gray-900">{s.total_avvisi}</dd>
                              </div>
                              <div>
                                <dt className="text-gray-500">Totale</dt>
                                <dd className="mt-1 font-semibold text-gray-900">{formatEuro(s.totale_euro)}</dd>
                              </div>
                              <div>
                                <dt className="text-gray-500">Collegati</dt>
                                <dd className="mt-1 font-semibold text-emerald-700">{s.avvisi_collegati}</dd>
                              </div>
                              <div>
                                <dt className="text-gray-500">Non collegati</dt>
                                <dd className={`mt-1 font-semibold ${s.avvisi_non_collegati > 0 ? "text-amber-700" : "text-gray-900"}`}>
                                  {s.avvisi_non_collegati}
                                </dd>
                              </div>
                            </dl>
                          </div>
                        ))}
                    </div>
                  )}
                </div>
              </article>

              <article className="rounded-[28px] border border-[#d8dfd3] bg-white shadow-panel">
                <div className="border-b border-[#edf1eb] bg-[linear-gradient(135deg,_rgba(29,78,53,0.06),_rgba(255,255,255,0.92))] px-6 py-5">
                  <p className="inline-flex items-center gap-2 rounded-full bg-[#e8f2ec] px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-[#1D4E35]">
                    <RefreshIcon className="h-3.5 w-3.5" />
                    Import recenti
                  </p>
                  <p className="mt-3 text-lg font-semibold text-gray-900">Storico rapido dei job.</p>
                  <p className="mt-2 max-w-2xl text-sm leading-6 text-gray-600">
                    Verifica subito quali file sono stati eseguiti, con quale esito e quanti record sono entrati nel dominio.
                  </p>
                </div>
                <div className="p-6">
                  {recentJobs.length === 0 ? (
                    <EmptyState
                      icon={RefreshIcon}
                      title="Nessun job disponibile"
                      description="La cronologia import apparirà qui dopo il primo caricamento del file Ruolo."
                    />
                  ) : (
                    <div className="space-y-3">
                      {recentJobs.map((job) => (
                        <div key={job.id} className="rounded-2xl border border-[#e3e9e0] bg-[#fbfcfb] p-4">
                          <div className="flex flex-wrap items-start justify-between gap-3">
                            <div>
                              <p className="text-sm font-semibold text-gray-900">{formatRuoloJobLabel(job)}</p>
                              <p className="mt-1 text-sm text-gray-500">
                                Anno {job.anno_tributario} · avviato il {new Date(job.started_at).toLocaleDateString("it-IT")}
                              </p>
                              <p className="mt-1 text-sm text-gray-600">{formatRuoloJobDescription(job)}</p>
                            </div>
                            <StatusBadge status={job.status} />
                          </div>
                          <div className="mt-4 grid grid-cols-3 gap-3 text-sm">
                            <div className="rounded-xl border border-white bg-white px-3 py-2">
                              <p className="text-xs uppercase tracking-[0.16em] text-gray-400">Importati</p>
                              <p className="mt-1 font-semibold text-gray-900">{job.records_imported ?? "—"}</p>
                            </div>
                            <div className="rounded-xl border border-white bg-white px-3 py-2">
                              <p className="text-xs uppercase tracking-[0.16em] text-gray-400">Saltati</p>
                              <p className="mt-1 font-semibold text-gray-900">{job.records_skipped ?? "—"}</p>
                            </div>
                            <div className="rounded-xl border border-white bg-white px-3 py-2">
                              <p className="text-xs uppercase tracking-[0.16em] text-gray-400">Errori</p>
                              <p className={`mt-1 font-semibold ${(job.records_errors ?? 0) > 0 ? "text-red-700" : "text-gray-900"}`}>
                                {job.records_errors ?? "—"}
                              </p>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </article>
            </section>

            {stats.length === 0 ? (
              <div className="rounded-[28px] border border-dashed border-[#cfd9d0] bg-[#f8fbf8] p-6">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div className="max-w-2xl">
                    <p className="inline-flex items-center gap-2 rounded-full bg-white px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-[#1D4E35]">
                      <AlertTriangleIcon className="h-3.5 w-3.5" />
                      Stato iniziale
                    </p>
                    <p className="mt-3 text-lg font-semibold text-gray-900">Il modulo è pronto ma non ha ancora dati caricati.</p>
                    <p className="mt-2 text-sm leading-6 text-gray-600">
                      Avvia il primo import per inizializzare il dataset storico del ruolo consortile. Dopo il caricamento vedrai qui avvisi per anno, orfani e trend economici.
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-3">
                    <button
                      type="button"
                      onClick={() => openWorkspaceModal("/ruolo/import", "Import Ruolo", "Carica un file Ruolo senza uscire dalla dashboard.")}
                      className="rounded-xl bg-[#1D4E35] px-4 py-2 text-sm font-medium text-white transition hover:bg-[#163d29]"
                    >
                      Importa il primo file
                    </button>
                    <Link
                      href="/ruolo/import"
                      className="rounded-xl border border-[#d6e5db] bg-white px-4 py-2 text-sm font-medium text-[#1D4E35] transition hover:bg-[#f3f8f5]"
                    >
                      Apri pagina import
                    </Link>
                  </div>
                </div>
              </div>
            ) : null}
          </>
        )}
      </div>
      <RuoloWorkspaceModal
        description={workspaceModal?.description}
        href={workspaceModal?.href ?? null}
        onClose={() => setWorkspaceModal(null)}
        open={workspaceModal != null}
        title={workspaceModal?.title ?? "Workspace"}
      />
    </RuoloModulePage>
  );
}
