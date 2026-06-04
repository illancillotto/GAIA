"use client";

import { useEffect, useState } from "react";

import { ProtectedPage } from "@/components/app/protected-page";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { MetricCard } from "@/components/ui/metric-card";
import { SyncButton } from "@/components/ui/sync-button";
import { SearchIcon } from "@/components/ui/icons";
import { cancelSyncJob, createSyncJob, getSyncCapabilities, getSyncJobs, getSyncRuns, retrySyncJob } from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import { formatDateTime, formatDuration } from "@/lib/presentation";
import type { SyncCapabilities, SyncJob, SyncRun } from "@/types/api";

function getSyncStatusBadge(status: string) {
  if (status === "succeeded") {
    return <Badge variant="success">Completato</Badge>;
  }

  if (status === "pending") {
    return <Badge variant="warning">In coda</Badge>;
  }

  if (status === "running") {
    return <Badge className="animate-pulse" variant="info">In corso</Badge>;
  }

  if (status === "cancelled") {
    return <Badge variant="neutral">Annullato</Badge>;
  }

  return <Badge variant="danger">Errore</Badge>;
}

export default function SyncPage() {
  const [capabilities, setCapabilities] = useState<SyncCapabilities | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [syncJobs, setSyncJobs] = useState<SyncJob[]>([]);
  const [syncRuns, setSyncRuns] = useState<SyncRun[]>([]);
  const [activeProfile, setActiveProfile] = useState<"quick" | "full" | null>(null);

  useEffect(() => {
    void loadSyncContext();
  }, []);

  useEffect(() => {
    if (!syncJobs.some((job) => job.status === "pending" || job.status === "running")) {
      return;
    }
    const handle = window.setInterval(() => {
      void loadSyncContext();
    }, 5000);
    return () => window.clearInterval(handle);
  }, [syncJobs]);

  async function loadSyncContext(): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) return;

    try {
      const [capabilitiesResult, syncRunsResult, syncJobsResult] = await Promise.all([
        getSyncCapabilities(token),
        getSyncRuns(token),
        getSyncJobs(token),
      ]);
      setCapabilities(capabilitiesResult);
      setSyncRuns(syncRunsResult);
      setSyncJobs(syncJobsResult);
      setError(null);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Errore caricamento sync");
    }
  }

  async function handleSync(profile: "quick" | "full"): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) return;

    setActiveProfile(profile);
    try {
      const job = await createSyncJob(token, profile);
      await loadSyncContext();
      setStatusMessage(
        profile === "full"
          ? `Job #${job.id} accodato per full scan del NAS.`
          : `Job #${job.id} accodato per sincronizzazione rapida.`,
      );
      setError(null);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Errore sync NAS");
      setStatusMessage(null);
    } finally {
      setActiveProfile(null);
    }
  }

  async function handleRetry(jobId: number): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) return;
    try {
      await retrySyncJob(token, jobId);
      await loadSyncContext();
      setStatusMessage(`Job #${jobId} rimesso in coda.`);
      setError(null);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Errore riavvio job NAS");
    }
  }

  async function handleCancel(jobId: number): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) return;
    try {
      await cancelSyncJob(token, jobId);
      await loadSyncContext();
      setStatusMessage(`Job #${jobId} annullato.`);
      setError(null);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Errore annullamento job NAS");
    }
  }

  const latestJob = syncJobs[0] ?? null;

  return (
    <ProtectedPage
      title="Sincronizzazione"
      description="Controllo operativo del connector Synology, esecuzione manuale e storico delle run."
      breadcrumb="Panoramica"
      topbarActions={
        <div className="flex items-center gap-2">
          <button
            className="btn-secondary"
            disabled={activeProfile != null}
            onClick={() => void handleSync("full")}
            type="button"
          >
            {activeProfile === "full" ? "Full scan..." : "Full scan"}
          </button>
          <SyncButton
            loading={activeProfile === "quick"}
            disabled={activeProfile != null && activeProfile !== "quick"}
            label="Sync rapida"
            onClick={() => void handleSync("quick")}
          />
        </div>
      }
    >
      {error ? <p className="text-sm text-red-600">{error}</p> : null}

      {capabilities ? (
        <div className="surface-grid">
          <MetricCard label="Host NAS" value={capabilities.host} sub={`${capabilities.username}@${capabilities.host}:${capabilities.port}`} />
          <MetricCard label="Retry" value={capabilities.retry_max_attempts} sub={`${capabilities.retry_strategy} · max ${capabilities.retry_max_delay_seconds}s`} />
          <MetricCard label="Jitter" value={capabilities.retry_jitter_enabled ? "Attivo" : "Disattivo"} sub={`${Math.round(capabilities.retry_jitter_ratio * 100)}%`} />
          <MetricCard label="Run registrate" value={syncRuns.length} sub="Storico audit delle sincronizzazioni" />
        </div>
      ) : null}

      <article className="panel-card">
        <div className="mb-4 flex items-center justify-between gap-3">
          <div>
            <p className="section-title">Stato connector</p>
            <p className="section-copy">Configurazione live sync e parametri runtime del backend.</p>
          </div>
          <button className="btn-secondary" type="button" onClick={() => void loadSyncContext()}>
            Aggiorna
          </button>
        </div>
        {capabilities ? (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <div className="rounded-lg border border-gray-100 bg-gray-50 p-4">
              <p className="label-caption">SSH</p>
              <p className="mt-2 text-sm font-medium text-gray-900">
                {capabilities.ssh_configured ? "Configurato" : "Non configurato"}
              </p>
              <p className="mt-1 text-xs text-gray-400">Autenticazione: {capabilities.auth_mode}</p>
            </div>
            <div className="rounded-lg border border-gray-100 bg-gray-50 p-4">
              <p className="label-caption">Live sync</p>
              <p className="mt-2 text-sm font-medium text-gray-900">
                {capabilities.supports_live_sync ? "Disponibile" : "Non disponibile"}
              </p>
              <p className="mt-1 text-xs text-gray-400">
                Profili {capabilities.live_sync_profiles.join(" / ")} · Timeout {capabilities.timeout_seconds}s
              </p>
            </div>
            <div className="rounded-lg border border-gray-100 bg-gray-50 p-4">
              <p className="label-caption">Backoff</p>
              <p className="mt-2 text-sm font-medium text-gray-900">{capabilities.retry_strategy}</p>
              <p className="mt-1 text-xs text-gray-400">Base {capabilities.retry_base_delay_seconds}s</p>
            </div>
            <div className="rounded-lg border border-gray-100 bg-gray-50 p-4">
              <p className="label-caption">Jitter</p>
              <p className="mt-2 text-sm font-medium text-gray-900">
                {capabilities.retry_jitter_enabled ? "Attivo" : "Disattivo"}
              </p>
              <p className="mt-1 text-xs text-gray-400">{Math.round(capabilities.retry_jitter_ratio * 100)}%</p>
            </div>
          </div>
        ) : (
          <EmptyState
            icon={SearchIcon}
            title="Capabilities non disponibili"
            description="Impossibile leggere lo stato del connector dal backend."
          />
        )}
      </article>

      {statusMessage ? (
        <article className="panel-card">
          <div className="mb-4">
            <p className="section-title">Ultimo aggiornamento</p>
            <p className="section-copy">{statusMessage}</p>
          </div>
          {latestJob ? (
            <div className="surface-grid">
              <MetricCard label="Job" value={`#${latestJob.id}`} sub={`${latestJob.profile} · ${latestJob.status}`} />
              <MetricCard label="Snapshot" value={latestJob.snapshot_id ?? "—"} sub="Disponibile a completamento job" />
              <MetricCard label="Utenti" value={latestJob.persisted_users} sub="Persistiti nell'ultimo job" />
              <MetricCard label="Share" value={latestJob.persisted_shares} sub="Persistite nell'ultimo job" />
            </div>
          ) : null}
        </article>
      ) : null}

      <article className="panel-card overflow-hidden p-0">
        <div className="border-b border-gray-100 px-5 py-4">
          <p className="section-title">Coda e storico job</p>
          <p className="section-copy">Job asincroni eseguiti dal worker NAS con stato, durata e snapshot associato.</p>
        </div>
        {syncJobs.length === 0 ? (
          <div className="p-5">
            <EmptyState
              icon={SearchIcon}
              title="Nessun job registrato"
              description="Avvia una sincronizzazione per popolare la coda e lo storico dei job."
            />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Job</th>
                  <th>Data avvio</th>
                  <th>Stato</th>
                  <th>Durata</th>
                  <th>Modalità</th>
                  <th>Trigger</th>
                  <th>Source</th>
                  <th>Snapshot</th>
                  <th>Dettaglio</th>
                  <th>Azioni</th>
                </tr>
              </thead>
              <tbody>
                {syncJobs.map((job) => {
                  const durationMs =
                    job.started_at && job.finished_at
                      ? new Date(job.finished_at).getTime() - new Date(job.started_at).getTime()
                      : null;
                  return (
                  <tr key={job.id}>
                    <td>#{job.id}</td>
                    <td>{formatDateTime(job.started_at ?? job.created_at)}</td>
                    <td>{getSyncStatusBadge(job.status)}</td>
                    <td>{formatDuration(durationMs)}</td>
                    <td>{job.profile}</td>
                    <td>{job.trigger_type}</td>
                    <td>{job.source_label ?? "—"}</td>
                    <td>{job.snapshot_id ?? "—"}</td>
                    <td className="text-xs text-gray-400">
                      Tentativi {job.attempt_count}/{job.max_attempts}
                      <br />
                      {job.error_detail ?? "Nessun errore"}
                    </td>
                    <td className="text-xs">
                      <div className="flex flex-wrap gap-2">
                        {(job.status === "pending" || job.status === "running") ? (
                          <button className="btn-secondary !px-2 !py-1" type="button" onClick={() => void handleCancel(job.id)}>
                            Annulla
                          </button>
                        ) : null}
                        {(job.status === "failed" || job.status === "cancelled" || job.status === "succeeded") ? (
                          <button className="btn-secondary !px-2 !py-1" type="button" onClick={() => void handleRetry(job.id)}>
                            Riprova
                          </button>
                        ) : null}
                      </div>
                    </td>
                  </tr>
                )})}
              </tbody>
            </table>
          </div>
        )}
      </article>

      <article className="panel-card overflow-hidden p-0">
        <div className="border-b border-gray-100 px-5 py-4">
          <p className="section-title">Storico audit snapshot</p>
          <p className="section-copy">Run consolidate persistite a completamento del job worker.</p>
        </div>
        {syncRuns.length === 0 ? (
          <div className="p-5">
            <EmptyState icon={SearchIcon} title="Nessuna run audit registrata" description="Le run vengono registrate quando un job termina." />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Data avvio</th>
                  <th>Stato</th>
                  <th>Durata</th>
                  <th>Modalità</th>
                  <th>Trigger</th>
                  <th>Source</th>
                  <th>Snapshot</th>
                </tr>
              </thead>
              <tbody>
                {syncRuns.map((syncRun) => (
                  <tr key={syncRun.id}>
                    <td>{formatDateTime(syncRun.started_at)}</td>
                    <td>{getSyncStatusBadge(syncRun.status)}</td>
                    <td>{formatDuration(syncRun.duration_ms)}</td>
                    <td>{syncRun.mode}</td>
                    <td>{syncRun.trigger_type}</td>
                    <td>{syncRun.source_label ?? "—"}</td>
                    <td>{syncRun.snapshot_id ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </article>
    </ProtectedPage>
  );
}
