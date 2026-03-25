"use client";

import { useEffect, useState } from "react";

import { ProtectedPage } from "@/components/app/protected-page";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { MetricCard } from "@/components/ui/metric-card";
import { SyncButton } from "@/components/ui/sync-button";
import { SearchIcon } from "@/components/ui/icons";
import { applyLiveSync, getSyncCapabilities, getSyncRuns } from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import { formatDateTime, formatDuration } from "@/lib/presentation";
import type { SyncApplyResult, SyncCapabilities, SyncRun } from "@/types/api";

function getSyncStatusBadge(status: string) {
  if (status === "succeeded") {
    return <Badge variant="success">Completato</Badge>;
  }

  if (status === "running") {
    return <Badge className="animate-pulse" variant="info">In corso</Badge>;
  }

  return <Badge variant="danger">Errore</Badge>;
}

export default function SyncPage() {
  const [capabilities, setCapabilities] = useState<SyncCapabilities | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [applyResult, setApplyResult] = useState<SyncApplyResult | null>(null);
  const [syncRuns, setSyncRuns] = useState<SyncRun[]>([]);
  const [activeProfile, setActiveProfile] = useState<"quick" | "full" | null>(null);

  useEffect(() => {
    void loadSyncContext();
  }, []);

  async function loadSyncContext(): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) return;

    try {
      const [capabilitiesResult, syncRunsResult] = await Promise.all([
        getSyncCapabilities(token),
        getSyncRuns(token),
      ]);
      setCapabilities(capabilitiesResult);
      setSyncRuns(syncRunsResult);
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
      const result = await applyLiveSync(token, profile);
      const syncRunsResult = await getSyncRuns(token);
      setApplyResult(result);
      setSyncRuns(syncRunsResult);
      setStatusMessage(
        profile === "full"
          ? "Sincronizzazione completa terminata con scansione estesa dell'albero NAS."
          : "Sincronizzazione rapida completata leggendo dati reali dal NAS.",
      );
      setError(null);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Errore sync NAS");
      setStatusMessage(null);
    } finally {
      setActiveProfile(null);
    }
  }

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

      {statusMessage && applyResult ? (
        <article className="panel-card">
          <div className="mb-4">
            <p className="section-title">Ultima sincronizzazione</p>
            <p className="section-copy">{statusMessage}</p>
          </div>
          <div className="surface-grid">
            <MetricCard label="Snapshot" value={applyResult.snapshot_id} sub={applyResult.snapshot_checksum.slice(0, 12)} />
            <MetricCard label="Utenti" value={applyResult.persisted_users} sub="Persistiti nella run corrente" />
            <MetricCard label="Gruppi" value={applyResult.persisted_groups} sub="Persistiti nella run corrente" />
            <MetricCard label="Share" value={applyResult.persisted_shares} sub="Persistite nella run corrente" />
          </div>
        </article>
      ) : null}

      <article className="panel-card overflow-hidden p-0">
        <div className="border-b border-gray-100 px-5 py-4">
          <p className="section-title">Storico snapshot</p>
          <p className="section-copy">Esecuzioni in ordine cronologico inverso con stato, durata e snapshot associato.</p>
        </div>
        {syncRuns.length === 0 ? (
          <div className="p-5">
            <EmptyState
              icon={SearchIcon}
              title="Nessuna sincronizzazione registrata"
              description="Avvia una sincronizzazione per popolare lo storico delle run."
            />
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
                  <th>Dettaglio</th>
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
                    <td className="text-xs text-gray-400">
                      Tentativi {syncRun.attempts_used}
                      <br />
                      {syncRun.error_detail ?? "Nessun errore"}
                    </td>
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
