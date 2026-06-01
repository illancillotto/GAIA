"use client";

import { useEffect, useState } from "react";

import { EmptyState } from "@/components/ui/empty-state";
import { SearchIcon } from "@/components/ui/icons";
import {
  clearWikiConversationMetricsBackfillJobHistory,
  enqueueWikiConversationMetricsBackfill,
  getLatestWikiConversationMetricsBackfillJob,
  getWikiConversationGovernanceConfig,
  getWikiConversationMetricsBackfillJobChainDetail,
  getWikiConversationMetricsBackfillJobChainSummary,
  listWikiConversationMetricsBackfillJobChains,
  retryWikiConversationMetricsBackfillJob,
  updateWikiConversationGovernanceConfig,
} from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import type {
  WikiConversationGovernanceConfig,
  WikiConversationMetricsBackfillJob,
  WikiConversationMetricsBackfillJobChain,
  WikiConversationMetricsBackfillJobChainDetail,
  WikiConversationMetricsBackfillJobChainSummary,
} from "@/types/api";

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

function formatDateTime(value: string | null): string {
  if (!value) {
    return "n/d";
  }
  return new Intl.DateTimeFormat("it-IT", { dateStyle: "short", timeStyle: "short" }).format(new Date(value));
}

function getStatusBadgeClass(status: string): string {
  if (status === "failed") {
    return "bg-rose-100 text-rose-700";
  }
  if (status === "running") {
    return "bg-amber-100 text-amber-700";
  }
  if (status === "pending") {
    return "bg-sky-100 text-sky-700";
  }
  return "bg-emerald-100 text-emerald-700";
}

function getActiveFilters(input: {
  chainStatusFilter: string;
  chainOwnerFilter: string;
  chainActiveRetryFilter: string;
  chainSortBy: string;
}) {
  return {
    latestStatus: input.chainStatusFilter !== "all" ? input.chainStatusFilter : undefined,
    requestedBy: input.chainOwnerFilter || undefined,
    hasActiveRetry:
      input.chainActiveRetryFilter === "all" ? undefined : input.chainActiveRetryFilter === "active",
    sortBy: input.chainSortBy,
  };
}

function KpiCard({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <article className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm">
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-gray-900">{value}</p>
      {hint ? <p className="mt-1 text-xs text-gray-500">{hint}</p> : null}
    </article>
  );
}

export function WikiConversationGovernanceSettingsPage() {
  const [config, setConfig] = useState<WikiConversationGovernanceConfig | null>(null);
  const [fallbackThreshold, setFallbackThreshold] = useState("2");
  const [noMatchThreshold, setNoMatchThreshold] = useState("2");
  const [latencyThreshold, setLatencyThreshold] = useState("1000");
  const [startDate, setStartDate] = useState(todayIso());
  const [endDate, setEndDate] = useState(todayIso());
  const [dataCompleteFrom, setDataCompleteFrom] = useState(todayIso());
  const [loading, setLoading] = useState(true);
  const [savingRules, setSavingRules] = useState(false);
  const [queueingBackfill, setQueueingBackfill] = useState(false);
  const [retryingJobId, setRetryingJobId] = useState<string | null>(null);
  const [clearingHistory, setClearingHistory] = useState(false);
  const [chainStatusFilter, setChainStatusFilter] = useState("all");
  const [chainOwnerFilter, setChainOwnerFilter] = useState("");
  const [chainActiveRetryFilter, setChainActiveRetryFilter] = useState("all");
  const [chainSortBy, setChainSortBy] = useState("failed_first");
  const [backfillJob, setBackfillJob] = useState<WikiConversationMetricsBackfillJob | null>(null);
  const [backfillChains, setBackfillChains] = useState<WikiConversationMetricsBackfillJobChain[]>([]);
  const [chainSummary, setChainSummary] = useState<WikiConversationMetricsBackfillJobChainSummary | null>(null);
  const [selectedChain, setSelectedChain] = useState<WikiConversationMetricsBackfillJobChainDetail | null>(null);
  const [selectedChainId, setSelectedChainId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const filters = getActiveFilters({
    chainStatusFilter,
    chainOwnerFilter,
    chainActiveRetryFilter,
    chainSortBy,
  });

  async function loadChainConsole(token: string, selectedRootJobId?: string | null) {
    const [chainSummaryResponse, chainResponse] = await Promise.all([
      getWikiConversationMetricsBackfillJobChainSummary(token, filters),
      listWikiConversationMetricsBackfillJobChains(token, 6, filters),
    ]);
    setChainSummary(chainSummaryResponse);
    setBackfillChains(chainResponse.items);

    const detailRootId = selectedRootJobId ?? selectedChainId;
    if (!detailRootId) {
      setSelectedChain(null);
      return;
    }
    const existing = chainResponse.items.find((item) => item.root_job_id === detailRootId);
    if (!existing) {
      setSelectedChain(null);
      setSelectedChainId(null);
      return;
    }
    const detail = await getWikiConversationMetricsBackfillJobChainDetail(token, detailRootId);
    setSelectedChain(detail);
    setSelectedChainId(detailRootId);
  }

  useEffect(() => {
    async function load() {
      const token = getStoredAccessToken();
      if (!token) {
        setError("Sessione non disponibile.");
        setLoading(false);
        return;
      }
      try {
        const [configResponse, latestJobResponse] = await Promise.all([
          getWikiConversationGovernanceConfig(token),
          getLatestWikiConversationMetricsBackfillJob(token),
        ]);
        await loadChainConsole(token, selectedChainId);
        setConfig(configResponse);
        setBackfillJob(latestJobResponse);
        setFallbackThreshold(String(configResponse.fallback_heavy_threshold));
        setNoMatchThreshold(String(configResponse.no_match_repeated_threshold));
        setLatencyThreshold(String(configResponse.high_latency_ms_threshold));
        if (configResponse.data_complete_from) {
          setDataCompleteFrom(configResponse.data_complete_from);
        }
        setError(null);
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : "Errore caricamento configurazione");
      } finally {
        setLoading(false);
      }
    }
    void load();
  }, [chainActiveRetryFilter, chainOwnerFilter, chainSortBy, chainStatusFilter]);

  useEffect(() => {
    if (!backfillJob || !["pending", "running"].includes(backfillJob.status)) {
      return;
    }
    const token = getStoredAccessToken();
    if (!token) {
      return;
    }
    const intervalId = window.setInterval(() => {
      void (async () => {
        try {
          const [latestJobResponse, configResponse] = await Promise.all([
            getLatestWikiConversationMetricsBackfillJob(token),
            getWikiConversationGovernanceConfig(token),
          ]);
          await loadChainConsole(token, selectedChainId);
          setBackfillJob(latestJobResponse);
          setConfig(configResponse);
        } catch {
          // Ignore transient polling errors and keep last rendered state.
        }
      })();
    }, 1500);
    return () => window.clearInterval(intervalId);
  }, [backfillJob, selectedChainId, chainActiveRetryFilter, chainOwnerFilter, chainSortBy, chainStatusFilter]);

  async function handleSaveRules() {
    const token = getStoredAccessToken();
    if (!token) {
      setError("Sessione non disponibile.");
      return;
    }
    setSavingRules(true);
    try {
      const response = await updateWikiConversationGovernanceConfig(token, {
        fallback_heavy_threshold: Number(fallbackThreshold),
        no_match_repeated_threshold: Number(noMatchThreshold),
        high_latency_ms_threshold: Number(latencyThreshold),
      });
      setConfig(response);
      setError(null);
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Errore salvataggio soglie");
    } finally {
      setSavingRules(false);
    }
  }

  async function handleBackfill() {
    const token = getStoredAccessToken();
    if (!token) {
      setError("Sessione non disponibile.");
      return;
    }
    setQueueingBackfill(true);
    try {
      const response = await enqueueWikiConversationMetricsBackfill(token, {
        start_date: startDate,
        end_date: endDate,
        data_complete_from: dataCompleteFrom,
      });
      setBackfillJob(response);
      await loadChainConsole(token, selectedChainId);
      setError(null);
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Errore backfill metriche");
    } finally {
      setQueueingBackfill(false);
    }
  }

  async function handleRetry(jobId: string, rootJobId: string) {
    const token = getStoredAccessToken();
    if (!token) {
      setError("Sessione non disponibile.");
      return;
    }
    setRetryingJobId(jobId);
    try {
      const response = await retryWikiConversationMetricsBackfillJob(token, jobId);
      setBackfillJob(response);
      await loadChainConsole(token, rootJobId);
      setError(null);
    } catch (retryError) {
      setError(retryError instanceof Error ? retryError.message : "Errore riaccodamento job");
    } finally {
      setRetryingJobId(null);
    }
  }

  async function handleClearHistory() {
    const token = getStoredAccessToken();
    if (!token) {
      setError("Sessione non disponibile.");
      return;
    }
    setClearingHistory(true);
    try {
      await clearWikiConversationMetricsBackfillJobHistory(token);
      await loadChainConsole(token, selectedChainId);
      setError(null);
    } catch (clearError) {
      setError(clearError instanceof Error ? clearError.message : "Errore pulizia storico");
    } finally {
      setClearingHistory(false);
    }
  }

  async function handleSelectChain(rootJobId: string) {
    const token = getStoredAccessToken();
    if (!token) {
      setError("Sessione non disponibile.");
      return;
    }
    try {
      const detail = await getWikiConversationMetricsBackfillJobChainDetail(token, rootJobId);
      setSelectedChain(detail);
      setSelectedChainId(rootJobId);
    } catch (detailError) {
      setError(detailError instanceof Error ? detailError.message : "Errore caricamento chain");
    }
  }

  function handleResetFilters() {
    setChainStatusFilter("all");
    setChainOwnerFilter("");
    setChainActiveRetryFilter("all");
    setChainSortBy("failed_first");
  }

  if (error && !config && !loading) {
    return <EmptyState icon={SearchIcon} title="Configurazione governance non disponibile" description={error} />;
  }

  return (
    <div className="space-y-6">
      <section>
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Governance</p>
        <h2 className="mt-1 text-xl font-semibold text-gray-900">Impostazioni conversazioni Wiki</h2>
        <p className="mt-1 text-sm text-gray-500">Tuning soglie review e console operativa del backfill metriche conversazioni.</p>
      </section>

      <section className="grid gap-4 xl:grid-cols-2">
        <article className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Tuning soglie</p>
          <div className="mt-4 grid gap-4">
            <label className="space-y-1 text-sm text-gray-700">
              <span>Fallback heavy threshold</span>
              <input className="w-full rounded-xl border border-gray-200 px-3 py-2" value={fallbackThreshold} onChange={(event) => setFallbackThreshold(event.target.value)} />
            </label>
            <label className="space-y-1 text-sm text-gray-700">
              <span>No match repeated threshold</span>
              <input className="w-full rounded-xl border border-gray-200 px-3 py-2" value={noMatchThreshold} onChange={(event) => setNoMatchThreshold(event.target.value)} />
            </label>
            <label className="space-y-1 text-sm text-gray-700">
              <span>High latency threshold (ms)</span>
              <input className="w-full rounded-xl border border-gray-200 px-3 py-2" value={latencyThreshold} onChange={(event) => setLatencyThreshold(event.target.value)} />
            </label>
            <button type="button" onClick={() => void handleSaveRules()} className="rounded-xl bg-[#1D4E35] px-4 py-2 text-sm font-medium text-white" disabled={savingRules || queueingBackfill}>
              {savingRules ? "Salvataggio..." : "Salva soglie"}
            </button>
          </div>
        </article>

        <article className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Accoda backfill</p>
          <div className="mt-4 grid gap-4">
            <label className="space-y-1 text-sm text-gray-700">
              <span>Start date</span>
              <input type="date" className="w-full rounded-xl border border-gray-200 px-3 py-2" value={startDate} onChange={(event) => setStartDate(event.target.value)} />
            </label>
            <label className="space-y-1 text-sm text-gray-700">
              <span>End date</span>
              <input type="date" className="w-full rounded-xl border border-gray-200 px-3 py-2" value={endDate} onChange={(event) => setEndDate(event.target.value)} />
            </label>
            <label className="space-y-1 text-sm text-gray-700">
              <span>Data complete from</span>
              <input type="date" className="w-full rounded-xl border border-gray-200 px-3 py-2" value={dataCompleteFrom} onChange={(event) => setDataCompleteFrom(event.target.value)} />
            </label>
            <button type="button" onClick={() => void handleBackfill()} className="rounded-xl bg-gray-900 px-4 py-2 text-sm font-medium text-white" disabled={queueingBackfill || savingRules}>
              {queueingBackfill ? "Accodamento..." : "Accoda backfill"}
            </button>
          </div>
        </article>
      </section>

      <section className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm text-sm text-gray-600">
        <p>Data complete from: <span className="font-medium text-gray-900">{config?.data_complete_from ?? "non marcata"}</span></p>
        <p className="mt-1">Ultimo backfill: <span className="font-medium text-gray-900">{formatDateTime(config?.last_backfill_at ?? null)}</span></p>
        <p className="mt-1">Ultimo update config: <span className="font-medium text-gray-900">{config?.updated_by ?? "n/d"}</span></p>
      </section>

      {backfillJob ? (
        <section className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm text-sm text-gray-600">
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Job attuale</p>
            <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${getStatusBadgeClass(backfillJob.status)}`}>{backfillJob.status}</span>
          </div>
          <p className="mt-3">Periodo: <span className="font-medium text-gray-900">{backfillJob.start_date} → {backfillJob.end_date}</span></p>
          <p className="mt-1">Progresso: <span className="font-medium text-gray-900">{backfillJob.progress_completed_days}/{backfillJob.progress_total_days} giorni ({backfillJob.progress_percent}%)</span></p>
          <p className="mt-1">Messaggio: <span className="font-medium text-gray-900">{backfillJob.progress_message ?? "n/d"}</span></p>
          {backfillJob.queue_position ? <p className="mt-1">Posizione coda: <span className="font-medium text-gray-900">{backfillJob.queue_position}</span></p> : null}
          {backfillJob.error_detail ? <p className="mt-1 text-rose-700">Errore: {backfillJob.error_detail}</p> : null}
        </section>
      ) : null}

      <section className="space-y-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Chain summary</p>
          <h3 className="mt-1 text-lg font-semibold text-gray-900">Queue e storico backfill</h3>
        </div>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          <KpiCard label="Chain totali" value={String(chainSummary?.total_chains ?? 0)} />
          <KpiCard label="Failed" value={String(chainSummary?.failed_chains ?? 0)} />
          <KpiCard label="Retry attivo" value={String(chainSummary?.chains_with_active_retry ?? 0)} />
          <KpiCard label="Completed" value={String(chainSummary?.completed_chains ?? 0)} />
          <KpiCard label="Retry medi" value={String(chainSummary?.avg_retries_per_chain ?? 0)} />
          <KpiCard
            label="Piu vecchia attiva"
            value={chainSummary?.oldest_active_chain_created_at ? formatDateTime(chainSummary.oldest_active_chain_created_at) : "n/d"}
          />
        </div>
      </section>

      <section className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400">Chain queue</p>
            <p className="mt-1 text-sm text-gray-500">Filtri e ordinamenti lato backend, senza ricostruzioni locali.</p>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleResetFilters}
              className="rounded-lg border border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-700"
            >
              Reset filtri
            </button>
            <button
              type="button"
              onClick={() => void handleClearHistory()}
              className="rounded-lg border border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-700"
              disabled={clearingHistory || queueingBackfill || savingRules || retryingJobId !== null}
            >
              {clearingHistory ? "Pulizia..." : "Pulisci storico"}
            </button>
          </div>
        </div>

        <div className="mt-4 grid gap-3 md:grid-cols-5">
          <label className="space-y-1 text-sm text-gray-700">
            <span>Stato chain</span>
            <select className="w-full rounded-xl border border-gray-200 px-3 py-2" value={chainStatusFilter} onChange={(event) => setChainStatusFilter(event.target.value)}>
              <option value="all">Tutti</option>
              <option value="pending">pending</option>
              <option value="running">running</option>
              <option value="completed">completed</option>
              <option value="failed">failed</option>
            </select>
          </label>
          <label className="space-y-1 text-sm text-gray-700">
            <span>Owner</span>
            <input className="w-full rounded-xl border border-gray-200 px-3 py-2" value={chainOwnerFilter} onChange={(event) => setChainOwnerFilter(event.target.value)} placeholder="admin" />
          </label>
          <label className="space-y-1 text-sm text-gray-700">
            <span>Retry attivo</span>
            <select className="w-full rounded-xl border border-gray-200 px-3 py-2" value={chainActiveRetryFilter} onChange={(event) => setChainActiveRetryFilter(event.target.value)}>
              <option value="all">Tutti</option>
              <option value="active">Si</option>
              <option value="inactive">No</option>
            </select>
          </label>
          <label className="space-y-1 text-sm text-gray-700">
            <span>Ordina per</span>
            <select className="w-full rounded-xl border border-gray-200 px-3 py-2" value={chainSortBy} onChange={(event) => setChainSortBy(event.target.value)}>
              <option value="failed_first">Failed first</option>
              <option value="latest_created_desc">Piu recenti</option>
              <option value="retry_count_desc">Piu tentativi</option>
              <option value="oldest_active_first">Attive piu vecchie</option>
            </select>
          </label>
          <div className="flex items-end text-xs text-gray-500">
            <p>{backfillChains.length > 0 ? `${backfillChains.length} chain visibili` : "Nessuna chain caricata"}</p>
          </div>
        </div>

        {backfillChains.length === 0 ? (
          <div className="mt-4">
            <EmptyState
              icon={SearchIcon}
              title="Nessuna chain disponibile"
              description={chainSummary?.total_chains === 0 ? "Storico backfill vuoto o già pulito." : "Nessun risultato per i filtri correnti."}
            />
          </div>
        ) : (
          <div className="mt-4 grid gap-4 xl:grid-cols-[1.3fr_0.9fr]">
            <div className="space-y-3">
              {backfillChains.map((chain) => (
                <article key={chain.root_job_id} className="rounded-xl border border-gray-200 px-4 py-3 text-sm text-gray-600">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${getStatusBadgeClass(chain.chain_status)}`}>{chain.chain_status}</span>
                      <p className="font-medium text-gray-900">Chain {chain.items.length} tentativi</p>
                    </div>
                    <button
                      type="button"
                      onClick={() => void handleSelectChain(chain.root_job_id)}
                      className="rounded-lg border border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-700"
                    >
                      {selectedChainId === chain.root_job_id ? "Dettaglio aperto" : "Apri dettaglio"}
                    </button>
                  </div>
                  <p className="mt-2 text-xs text-gray-500">
                    Root {chain.root_job_id.slice(0, 8)} · retry {chain.retry_count_total} · owner {chain.latest_job.requested_by}
                  </p>
                  <p className="mt-1 text-xs text-gray-500">
                    Ultimo periodo {chain.latest_job.start_date} → {chain.latest_job.end_date} · creato {formatDateTime(chain.latest_job.created_at)}
                  </p>
                </article>
              ))}
            </div>

            <aside className="rounded-xl border border-dashed border-gray-300 p-4">
              {selectedChain ? (
                <div className="space-y-4 text-sm text-gray-600">
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${getStatusBadgeClass(selectedChain.chain_status)}`}>{selectedChain.chain_status}</span>
                      <p className="font-medium text-gray-900">Dettaglio chain {selectedChain.root_job_id.slice(0, 8)}</p>
                    </div>
                    <p className="mt-2 text-xs text-gray-500">
                      Retry totali {selectedChain.retry_count_total} · attiva {selectedChain.has_active_retry ? "si" : "no"}
                    </p>
                    <p className="mt-1 text-xs text-gray-500">Prima creazione {formatDateTime(selectedChain.oldest_created_at)}</p>
                  </div>

                  <div className="rounded-xl bg-gray-50 p-3">
                    <p className="font-medium text-gray-900">Ultimo tentativo</p>
                    <p className="mt-1">Periodo {selectedChain.latest_job.start_date} → {selectedChain.latest_job.end_date}</p>
                    <p className="mt-1">Creato {formatDateTime(selectedChain.latest_job.created_at)}</p>
                    <p className="mt-1">Start {formatDateTime(selectedChain.latest_job.started_at)}</p>
                    <p className="mt-1">Fine {formatDateTime(selectedChain.latest_job.finished_at)}</p>
                    <p className="mt-1">Messaggio {selectedChain.latest_job.progress_message ?? "n/d"}</p>
                    {selectedChain.latest_job.error_detail ? <p className="mt-1 text-rose-700">{selectedChain.latest_job.error_detail}</p> : null}
                    {selectedChain.latest_job.status === "failed" ? (
                      <button
                        type="button"
                        onClick={() => void handleRetry(selectedChain.latest_job.id, selectedChain.root_job_id)}
                        className="mt-3 rounded-lg border border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-700"
                        disabled={retryingJobId !== null || queueingBackfill || savingRules || clearingHistory}
                      >
                        {retryingJobId === selectedChain.latest_job.id ? "Riaccodamento..." : "Riprova ultimo tentativo"}
                      </button>
                    ) : null}
                  </div>

                  <div className="space-y-3 border-l border-gray-200 pl-4">
                    {selectedChain.items.map((item) => (
                      <div key={item.id}>
                        <p>
                          <span className="font-medium text-gray-900">Tentativo {item.retry_count + 1}</span>
                          {" · "}
                          <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${getStatusBadgeClass(item.status)}`}>{item.status}</span>
                        </p>
                        <p className="mt-1 text-xs text-gray-500">
                          {item.start_date} → {item.end_date} · {formatDateTime(item.created_at)} · {item.requested_by}
                        </p>
                        <p className="mt-1 text-xs text-gray-500">
                          {item.parent_job_id ? `retry di ${item.parent_job_id.slice(0, 8)}` : "job iniziale"}
                          {item.queue_position ? ` · coda ${item.queue_position}` : ""}
                          {item.is_latest_attempt ? " · tentativo corrente" : ""}
                        </p>
                        {item.error_detail ? <p className="mt-1 text-xs text-rose-700">{item.error_detail}</p> : null}
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <EmptyState icon={SearchIcon} title="Dettaglio chain" description="Apri una chain dalla lista per vedere i tentativi e il retry mirato." />
              )}
            </aside>
          </div>
        )}
      </section>

      {error ? <article className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">{error}</article> : null}
    </div>
  );
}
