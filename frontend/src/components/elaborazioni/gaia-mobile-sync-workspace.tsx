"use client";

import { useCallback, useEffect, useState } from "react";

import { ProtectedPage } from "@/components/app/protected-page";
import { ElaborazioneHero, ElaborazioneNoticeCard, ElaborazionePanelHeader } from "@/components/elaborazioni/module-chrome";
import { ModuleWorkspaceKpiRow, ModuleWorkspaceKpiTile } from "@/components/layout/module-workspace-hero";
import { RefreshIcon, ServerIcon } from "@/components/ui/icons";
import { ApiError, getGateMobileSyncStatus, triggerGateMobileSyncRun, type GateMobileSyncStatusResponse } from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import { formatDateTime } from "@/lib/presentation";

function formatMetricNumber(value: number | null | undefined, maximumFractionDigits = 0): string {
  if (value == null) return "—";
  return new Intl.NumberFormat("it-IT", { maximumFractionDigits }).format(value);
}

function formatDurationMs(durationMs: number | null | undefined): string {
  if (durationMs == null) return "—";
  if (durationMs < 1000) return `${durationMs} ms`;
  const seconds = durationMs / 1000;
  if (seconds < 60) return `${formatMetricNumber(seconds, 1)} s`;
  return `${formatMetricNumber(seconds / 60, 1)} min`;
}

function formatSyncStatus(status: string | null | undefined): string {
  switch (status) {
    case "running":
      return "In esecuzione";
    case "succeeded":
      return "Riuscito";
    case "failed":
      return "Fallito";
    case "skipped":
      return "Saltato";
    default:
      return status ?? "Nessun run";
  }
}

function buildMonitorMessage(status: GateMobileSyncStatusResponse | null): { title: string; description: string; tone: "info" | "danger" } {
  if (!status) {
    return {
      title: "Monitor in attesa",
      description: "Caricamento stato gateway e storico run.",
      tone: "info",
    };
  }
  if (!status.sync_enabled) {
    return {
      title: "Sync outbound disattivata",
      description: "Il job è configurato ma il flag GATE_MOBILE_SYNC_ENABLED è spento.",
      tone: "danger",
    };
  }
  if (!status.gateway_configured || !status.token_configured) {
    return {
      title: "Configurazione incompleta",
      description: "Manca la base URL del gateway pubblico o il token tecnico outbound.",
      tone: "danger",
    };
  }
  return {
    title: "Canale outbound pronto",
    description: "GAIA può proiettare snapshot operatori verso il gateway pubblico senza esporre le API LAN.",
      tone: "info",
  };
}

export function ElaborazioniGaiaMobileSyncWorkspace({ embedded = false }: { embedded?: boolean }) {
  const [status, setStatus] = useState<GateMobileSyncStatusResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [triggerBusy, setTriggerBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [runNotice, setRunNotice] = useState<{ tone: "info" | "danger"; message: string } | null>(null);
  const [historyFilter, setHistoryFilter] = useState<"all" | "issues">("all");

  const loadStatus = useCallback(async (): Promise<void> => {
    const token = getStoredAccessToken();
    if (!token) return;

    setBusy(true);
    try {
      const response = await getGateMobileSyncStatus(token);
      setStatus(response);
      setError(null);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Errore caricamento stato gateway mobile");
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => {
    void loadStatus();
  }, [loadStatus]);

  useEffect(() => {
    if (status?.last_run?.status !== "running") return;
    const intervalId = window.setInterval(() => void loadStatus(), 10000);
    return () => window.clearInterval(intervalId);
  }, [loadStatus, status?.last_run?.status]);

  async function handleTriggerRun(): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) return;

    setTriggerBusy(true);
    try {
      const response = await triggerGateMobileSyncRun(token);
      setStatus((current) => {
        const recentRuns = current?.recent_runs ?? [];
        const deduped = [response.job, ...recentRuns.filter((item) => item.id !== response.job.id)].slice(0, 10);
        return current
          ? {
              ...current,
              last_run: response.job,
              recent_runs: deduped,
            }
          : {
              sync_enabled: true,
              gateway_base_url: null,
              gateway_configured: false,
              token_configured: false,
              timeout_seconds: 0,
              outbound_scope: [],
              internal_connector_api: { path_prefix: "/api/mobile-sync", auth_header: "Authorization" },
              last_run: response.job,
              recent_runs: [response.job],
            };
      });
      setError(null);
      setRunNotice({
        tone: response.job.status === "failed" ? "danger" : "info",
        message:
          response.job.status === "failed"
            ? `Sync conclusa con errore: ${response.job.error_message ?? "nessun dettaglio"}`
            : `Sync completata: ${response.job.operators_pushed} operatori pushati.`,
      });
      await loadStatus();
    } catch (triggerError) {
      if (triggerError instanceof ApiError && triggerError.status === 409) {
        setRunNotice({
          tone: "info",
          message: "Una sync è già in esecuzione. Il monitor è stato aggiornato con il run attivo.",
        });
      } else {
        setError(triggerError instanceof Error ? triggerError.message : "Errore avvio sync gateway mobile");
      }
      await loadStatus();
    } finally {
      setTriggerBusy(false);
    }
  }

  const monitorMessage = buildMonitorMessage(status);
  const filteredRuns =
    historyFilter === "issues"
      ? (status?.recent_runs ?? []).filter((run) => run.status === "failed" || run.status === "skipped")
      : (status?.recent_runs ?? []);

  const content = (
    <>
      <ElaborazioneHero
        compact={embedded}
        badge={
          <>
            <ServerIcon className="h-3.5 w-3.5" />
            GAIA Mobile Sync
          </>
        }
        title="Monitor del canale outbound verso il gateway pubblico."
        description="Questo workspace mostra configurazione, ultimo run e storico della sincronizzazione GAIA -> gateway `gaia-mobile`, separata dalle API LAN `/api/mobile-sync`."
        actions={
          error ? (
            <ElaborazioneNoticeCard title="Errore monitor" description={error} tone="danger" compact={embedded} />
          ) : (
            <ElaborazioneNoticeCard
              title={monitorMessage.title}
              description={monitorMessage.description}
              tone={monitorMessage.tone}
              compact={embedded}
            />
          )
        }
      >
        <ModuleWorkspaceKpiRow compact={embedded}>
          <ModuleWorkspaceKpiTile
            compact={embedded}
            label="Ultimo stato"
            variant={status?.last_run?.status === "failed" ? "amber" : status?.last_run?.status === "succeeded" ? "emerald" : "default"}
            value={formatSyncStatus(status?.last_run?.status)}
            hint={status?.last_run?.started_at ? `Avvio ${formatDateTime(status.last_run.started_at)}` : "Nessun run registrato"}
          />
          <ModuleWorkspaceKpiTile
            compact={embedded}
            label="Operatori pushati"
            variant="emerald"
            value={formatMetricNumber(status?.last_run?.operators_pushed ?? null)}
            hint={`${formatMetricNumber(status?.last_run?.requested_tasks_count ?? null)} task richiesti`}
          />
          <ModuleWorkspaceKpiTile
            compact={embedded}
            label="Durata"
            value={formatDurationMs(status?.last_run?.duration_ms)}
            hint={status?.timeout_seconds ? `Timeout HTTP ${status.timeout_seconds}s` : "Timeout non disponibile"}
          />
          <ModuleWorkspaceKpiTile
            compact={embedded}
            label="Configurazione"
            variant={status?.sync_enabled && status?.gateway_configured && status?.token_configured ? "emerald" : "amber"}
            value={status?.sync_enabled ? "Attiva" : "Disattiva"}
            hint={
              status
                ? `${status.gateway_configured ? "gateway ok" : "gateway mancante"} · ${status.token_configured ? "token ok" : "token mancante"}`
                : "Caricamento configurazione"
            }
          />
        </ModuleWorkspaceKpiRow>
      </ElaborazioneHero>

      <article className="overflow-hidden rounded-[28px] border border-[#d9dfd6] bg-white shadow-panel">
        <ElaborazionePanelHeader
          badge={
            <>
              <ServerIcon className="h-3.5 w-3.5" />
              Canale tecnico
            </>
          }
          title="Configurazione e perimetro del gateway"
          description="Il pilot corrente pubblica solo snapshot operatori verso il cloud. Le API LAN `/api/mobile-sync/*` restano il contratto trusted per applicare eventi a GAIA."
          actions={
            <div className="flex flex-wrap gap-3">
              <button className="btn-primary" disabled={triggerBusy || status?.last_run?.status === "running"} onClick={() => void handleTriggerRun()} type="button">
                {triggerBusy ? "Avvio sync..." : status?.last_run?.status === "running" ? "Sync già in corso" : "Esegui sync ora"}
              </button>
              <button className="btn-secondary" disabled={busy || triggerBusy} onClick={() => void loadStatus()} type="button">
                {busy ? "Aggiorno..." : "Aggiorna stato"}
              </button>
            </div>
          }
        />
        <div className="grid gap-6 p-6 lg:grid-cols-[1.15fr,0.85fr]">
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-2xl border border-gray-100 bg-gray-50 px-4 py-3">
              <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-gray-500">Gateway pubblico</p>
              <p className="mt-2 break-all text-sm font-semibold text-gray-900">{status?.gateway_base_url ?? "Non configurato"}</p>
              <p className="mt-1 text-xs text-gray-500">Canale outbound autenticato con token tecnico dedicato.</p>
            </div>
            <div className="rounded-2xl border border-gray-100 bg-gray-50 px-4 py-3">
              <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-gray-500">API LAN interna</p>
              <p className="mt-2 text-sm font-semibold text-gray-900">{status?.internal_connector_api.path_prefix ?? "/api/mobile-sync"}</p>
              <p className="mt-1 text-xs text-gray-500">Header auth: {status?.internal_connector_api.auth_header ?? "—"}</p>
            </div>
            <div className="rounded-2xl border border-gray-100 bg-gray-50 px-4 py-3">
              <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-gray-500">Scope outbound</p>
              <p className="mt-2 text-sm font-semibold text-[#1D4E35]">
                {status?.outbound_scope.length ? status.outbound_scope.join(", ") : "Nessuno"}
              </p>
              <p className="mt-1 text-xs text-gray-500">Per ora il piano pubblica solo il dataset operatori.</p>
            </div>
            <div className="rounded-2xl border border-gray-100 bg-gray-50 px-4 py-3">
              <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-gray-500">Ultimo trigger</p>
              <p className="mt-2 text-sm font-semibold text-gray-900">{status?.last_run?.trigger_source ?? "Nessun trigger"}</p>
              <p className="mt-1 text-xs text-gray-500">
                {status?.last_run?.finished_at ? `Fine ${formatDateTime(status.last_run.finished_at)}` : "Nessun completamento registrato"}
              </p>
            </div>
          </div>
          <div className="space-y-4">
            {runNotice ? (
              <div
                className={[
                  "rounded-2xl px-4 py-3 text-sm",
                  runNotice.tone === "danger"
                    ? "border border-amber-100 bg-amber-50 text-amber-900"
                    : "border border-[#d9dfd6] bg-[#f7faf8] text-gray-700",
                ].join(" ")}
              >
                {runNotice.message}
              </div>
            ) : null}
            {status?.last_run?.error_message ? (
              <div className="rounded-2xl border border-amber-100 bg-amber-50 px-4 py-3">
                <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-amber-700">Ultimo errore</p>
                <p className="mt-2 break-words text-sm text-amber-900">{status.last_run.error_message}</p>
              </div>
            ) : (
              <div className="rounded-2xl border border-gray-100 bg-[#f7faf8] px-4 py-3 text-sm text-gray-600">
                Questo monitor è read-only: mostra lo stato reale dell’integrazione senza introdurre nuovi trigger lato frontend.
              </div>
            )}
            <div className="rounded-[24px] border border-[#d9dfd6] bg-[#f7faf8] p-5">
              <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[#1D4E35]">Task ultimo piano</p>
              {status?.last_run?.requested_tasks.length ? (
                <div className="mt-4 flex flex-wrap gap-2">
                  {status.last_run.requested_tasks.map((task, index) => (
                    <span key={`${String(task.type ?? "task")}-${index}`} className="rounded-full border border-[#cfe0d5] bg-white px-3 py-1 text-xs font-semibold text-[#1D4E35]">
                      {String(task.type ?? "task")}
                    </span>
                  ))}
                </div>
              ) : (
                <p className="mt-4 text-sm text-gray-500">Nessun task restituito dal piano o nessun run ancora eseguito.</p>
              )}
              <div className="mt-5 space-y-2 text-xs text-gray-500">
                <p>Sync enabled: {status?.sync_enabled ? "true" : "false"}</p>
                <p>Gateway configured: {status?.gateway_configured ? "true" : "false"}</p>
                <p>Token configured: {status?.token_configured ? "true" : "false"}</p>
              </div>
            </div>
          </div>
        </div>
      </article>

      <article className="overflow-hidden rounded-[28px] border border-[#d9dfd6] bg-white shadow-panel">
        <ElaborazionePanelHeader
          badge={
            <>
              <RefreshIcon className="h-3.5 w-3.5" />
              Storico run
            </>
          }
          title="Ultime esecuzioni persistite"
          description="Storico breve dei run registrati nel database, utile per verificare successo, skip da flag spento o errori di configurazione/trasporto."
          actions={
            <div className="flex flex-wrap gap-2">
              <button
                className={historyFilter === "all" ? "btn-primary" : "btn-secondary"}
                onClick={() => setHistoryFilter("all")}
                type="button"
              >
                Tutti
              </button>
              <button
                className={historyFilter === "issues" ? "btn-primary" : "btn-secondary"}
                onClick={() => setHistoryFilter("issues")}
                type="button"
              >
                Errori e skip
              </button>
            </div>
          }
        />
        <div className="overflow-x-auto">
          <table className="data-table">
            <thead>
              <tr>
                <th>Avvio</th>
                <th>Trigger</th>
                <th>Stato</th>
                <th>Task</th>
                <th>Operatori</th>
                <th>Durata</th>
                <th>Errore</th>
              </tr>
            </thead>
            <tbody>
              {filteredRuns.length ? (
                filteredRuns.map((run) => (
                  <tr key={run.id}>
                    <td>{formatDateTime(run.started_at)}</td>
                    <td>{run.trigger_source}</td>
                    <td>{formatSyncStatus(run.status)}</td>
                    <td>{formatMetricNumber(run.requested_tasks_count)}</td>
                    <td>{formatMetricNumber(run.operators_pushed)}</td>
                    <td>{formatDurationMs(run.duration_ms)}</td>
                    <td className="max-w-[320px]">
                      <span className="line-clamp-2 text-sm text-gray-600">{run.error_message ?? "—"}</span>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td className="text-sm text-gray-500" colSpan={7}>
                    {historyFilter === "issues" ? "Nessun run failed o skipped." : "Nessun run registrato."}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </article>
    </>
  );

  if (embedded) {
    return content;
  }

  return (
    <ProtectedPage
      title="GAIA Elaborazioni"
      description="Monitor amministrativo del canale outbound GAIA -> gateway pubblico gaia-mobile."
      breadcrumb="Elaborazioni"
      requiredModule="catasto"
      requiredRoles={["admin", "super_admin"]}
    >
      {content}
    </ProtectedPage>
  );
}
