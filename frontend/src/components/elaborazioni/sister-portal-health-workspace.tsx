"use client";

import { useCallback, useEffect, useState } from "react";

import {
  ElaborazioneHero,
  ElaborazioneNoticeCard,
  ElaborazionePanelHeader,
} from "@/components/elaborazioni/module-chrome";
import { ModuleWorkspaceKpiRow, ModuleWorkspaceKpiTile } from "@/components/layout/module-workspace-hero";
import { EmptyState } from "@/components/ui/empty-state";
import { AlertTriangleIcon, RefreshIcon, ServerIcon } from "@/components/ui/icons";
import { getStoredAccessToken } from "@/lib/auth";
import { getSisterPortalHealth } from "@/lib/portal-health-api";
import { formatDateTime } from "@/lib/presentation";
import type {
  SisterPortalAlert,
  SisterPortalCredentialMetric,
  SisterPortalDownloadTotals,
  SisterPortalErrorMetric,
  SisterPortalHealth,
  SisterPortalRecentEvent,
  SisterPortalStepMetric,
  SisterPortalTimelinePoint,
} from "@/types/api";


const REFRESH_INTERVAL_MS = 30_000;
const WINDOWS = [
  { hours: 24, label: "24 ore" },
  { hours: 168, label: "7 giorni" },
  { hours: 720, label: "30 giorni" },
];


export function formatPortalDuration(value: number | null): string {
  if (value === null) return "n/d";
  if (value < 1000) return `${value} ms`;
  if (value < 60_000) return `${(value / 1000).toFixed(1)} s`;
  return `${(value / 60_000).toFixed(1)} min`;
}


export function portalStatusLabel(status: SisterPortalHealth["status"]): string {
  if (status === "healthy") return "Operativo";
  if (status === "degraded") return "Degradato";
  if (status === "critical") return "Critico";
  return "In attesa di dati";
}


function statusTone(status: SisterPortalHealth["status"]): string {
  if (status === "healthy") return "border-emerald-200 bg-emerald-50 text-emerald-800";
  if (status === "degraded") return "border-amber-200 bg-amber-50 text-amber-800";
  if (status === "critical") return "border-rose-200 bg-rose-50 text-rose-800";
  return "border-slate-200 bg-slate-50 text-slate-600";
}


function StatusPill({ status }: { status: SisterPortalHealth["status"] }) {
  return (
    <span className={`inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-bold ${statusTone(status)}`}>
      <span className="h-2 w-2 rounded-full bg-current" />
      {portalStatusLabel(status)}
    </span>
  );
}


function WindowSelector({
  hours,
  onChange,
}: {
  hours: number;
  onChange: (hours: number) => void;
}) {
  return (
    <div className="inline-flex rounded-full border border-[#cfd9d1] bg-white/90 p-1 shadow-sm" aria-label="Finestra telemetria">
      {WINDOWS.map((window) => (
        <button
          key={window.hours}
          type="button"
          className={[
            "rounded-full px-3 py-1.5 text-xs font-semibold transition",
            hours === window.hours ? "bg-[#163f2c] text-white" : "text-[#42614f] hover:bg-[#eaf3ed]",
          ].join(" ")}
          onClick={() => onChange(window.hours)}
        >
          {window.label}
        </button>
      ))}
    </div>
  );
}


function TelemetryTimeline({ items }: { items: SisterPortalTimelinePoint[] }) {
  if (items.length === 0) {
    return (
      <EmptyState
        icon={ServerIcon}
        title="Nessun evento nella finestra"
        description="La serie temporale comparira quando il worker visure iniziera a registrare eventi."
      />
    );
  }
  const maxEvents = Math.max(...items.map((item) => item.events), 1);
  return (
    <div className="grid gap-3">
      {items.map((item) => {
        const successWidth = Math.round(item.successes / maxEvents * 100);
        const errorWidth = Math.round(item.errors / maxEvents * 100);
        return (
          <div key={item.bucket} className="grid gap-2 sm:grid-cols-[140px_1fr_110px] sm:items-center">
            <p className="text-xs font-semibold text-slate-600">{formatDateTime(item.bucket)}</p>
            <div className="relative h-3 overflow-hidden rounded-full bg-[#edf1eb]">
              <div className="absolute inset-y-0 left-0 bg-[#2d7a54]" style={{ width: `${successWidth}%` }} />
              <div
                className="absolute inset-y-0 bg-[#d85b50]"
                style={{ left: `${successWidth}%`, width: `${errorWidth}%` }}
              />
            </div>
            <p className="text-right text-xs text-slate-500">
              {item.events} eventi / {formatPortalDuration(item.average_duration_ms)}
            </p>
          </div>
        );
      })}
      <div className="flex items-center justify-end gap-4 text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-500">
        <span className="inline-flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-[#2d7a54]" />Successi</span>
        <span className="inline-flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-[#d85b50]" />Errori</span>
      </div>
    </div>
  );
}


function AlertsPanel({ alerts }: { alerts: SisterPortalAlert[] }) {
  if (alerts.length === 0) {
    return (
      <div className="rounded-[24px] border border-emerald-200 bg-emerald-50 px-5 py-4 text-sm text-emerald-900">
        Nessun alert attivo nella finestra selezionata.
      </div>
    );
  }
  return (
    <div className="grid gap-3">
      {alerts.map((alert) => (
        <article
          key={alert.id}
          className={`rounded-[24px] border px-5 py-4 ${
            alert.severity === "critical"
              ? "border-rose-200 bg-rose-50 text-rose-950"
              : "border-amber-200 bg-amber-50 text-amber-950"
          }`}
        >
          <div className="flex items-start gap-3">
            <AlertTriangleIcon className="mt-0.5 h-5 w-5 shrink-0" />
            <div>
              <p className="font-bold">{alert.title}</p>
              <p className="mt-1 text-sm leading-6 opacity-80">{alert.detail}</p>
              <p className="mt-2 text-xs font-semibold opacity-60">Attivo da {formatDateTime(alert.active_since)}</p>
            </div>
          </div>
        </article>
      ))}
    </div>
  );
}


function StepsTable({ items }: { items: SisterPortalStepMetric[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-slate-100 text-sm">
        <thead>
          <tr className="text-left text-[11px] uppercase tracking-[0.16em] text-slate-400">
            <th className="px-3 py-3 font-semibold">Fase</th>
            <th className="px-3 py-3 text-right font-semibold">Eventi</th>
            <th className="px-3 py-3 text-right font-semibold">Errori</th>
            <th className="px-3 py-3 text-right font-semibold">Media</th>
            <th className="px-3 py-3 text-right font-semibold">P95</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {items.slice(0, 12).map((item) => (
            <tr key={item.step} className="text-slate-700">
              <td className="px-3 py-3 font-semibold">{item.step.replaceAll("_", " ")}</td>
              <td className="px-3 py-3 text-right">{item.events}</td>
              <td className={`px-3 py-3 text-right font-bold ${item.errors ? "text-rose-700" : "text-emerald-700"}`}>
                {item.errors}
              </td>
              <td className="px-3 py-3 text-right">{formatPortalDuration(item.average_duration_ms)}</td>
              <td className="px-3 py-3 text-right">{formatPortalDuration(item.p95_duration_ms)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}


function CredentialCards({ items }: { items: SisterPortalCredentialMetric[] }) {
  if (items.length === 0) {
    return <p className="text-sm text-slate-500">Nessuna sessione associata a credenziali nella finestra.</p>;
  }
  return (
    <div className="grid gap-3 md:grid-cols-2">
      {items.map((item) => (
        <article key={item.credential_id ?? item.label} className="rounded-[22px] border border-[#dce5de] bg-[#f8faf8] p-4">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="font-bold text-slate-900">{item.label}</p>
              <p className="mt-1 text-xs text-slate-500">Ultimo evento {formatDateTime(item.last_seen_at)}</p>
            </div>
            <span className="rounded-full bg-white px-2.5 py-1 text-xs font-bold text-[#1D4E35] shadow-sm">
              {item.success_rate}%
            </span>
          </div>
          <div className="mt-4 grid grid-cols-2 gap-2 text-center text-xs sm:grid-cols-4">
            <div className="rounded-xl bg-white p-2"><b className="block text-base text-slate-900">{item.events}</b>eventi</div>
            <div className="rounded-xl bg-white p-2"><b className="block text-base text-emerald-700">{item.successes}</b>successi</div>
            <div className="rounded-xl bg-white p-2"><b className="block text-base text-rose-700">{item.errors}</b>errori</div>
            <div className="rounded-xl bg-white p-2"><b className="block text-base text-sky-700">{item.downloads}</b>visure</div>
          </div>
        </article>
      ))}
    </div>
  );
}


function ErrorList({ items }: { items: SisterPortalErrorMetric[] }) {
  if (items.length === 0) {
    return <p className="text-sm text-slate-500">Nessun errore classificato.</p>;
  }
  return (
    <div className="grid gap-2">
      {items.slice(0, 10).map((item) => (
        <div key={`${item.event_type}-${item.step}-${item.http_status}`} className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-rose-100 bg-rose-50/60 px-4 py-3">
          <div>
            <p className="text-sm font-bold text-rose-950">{item.event_type.replaceAll("_", " ")}</p>
            <p className="mt-0.5 text-xs text-rose-800/70">{item.step.replaceAll("_", " ")} / {formatDateTime(item.last_seen_at)}</p>
          </div>
          <div className="flex items-center gap-2 text-xs font-bold text-rose-800">
            {item.http_status ? <span>HTTP {item.http_status}</span> : null}
            <span className="rounded-full bg-white px-2.5 py-1">{item.count}x</span>
          </div>
        </div>
      ))}
    </div>
  );
}


function RecentEvents({ items }: { items: SisterPortalRecentEvent[] }) {
  if (items.length === 0) return <p className="text-sm text-slate-500">Nessun evento recente.</p>;
  return (
    <div className="max-h-[420px] overflow-auto">
      <table className="min-w-full divide-y divide-slate-100 text-sm">
        <thead className="sticky top-0 bg-white">
          <tr className="text-left text-[11px] uppercase tracking-[0.16em] text-slate-400">
            <th className="px-3 py-3 font-semibold">Ora</th>
            <th className="px-3 py-3 font-semibold">Evento</th>
            <th className="px-3 py-3 font-semibold">Fase</th>
            <th className="px-3 py-3 font-semibold">Credenziale</th>
            <th className="px-3 py-3 font-semibold">Esito</th>
            <th className="px-3 py-3 text-right font-semibold">Durata</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {items.map((item) => (
            <tr key={item.id}>
              <td className="whitespace-nowrap px-3 py-3 text-xs text-slate-500">{formatDateTime(item.occurred_at)}</td>
              <td className="px-3 py-3 font-semibold text-slate-800">{item.event_type.replaceAll("_", " ")}</td>
              <td className="px-3 py-3 text-slate-600">{item.step.replaceAll("_", " ")}</td>
              <td className="px-3 py-3 font-semibold text-slate-700">
                {item.credential_label ?? "Non associata"}
              </td>
              <td className="px-3 py-3">
                <span className={`rounded-full px-2 py-1 text-xs font-bold ${
                  item.outcome === "error" || item.outcome === "failed"
                    ? "bg-rose-50 text-rose-700"
                    : "bg-emerald-50 text-emerald-700"
                }`}>
                  {item.outcome}
                </span>
              </td>
              <td className="whitespace-nowrap px-3 py-3 text-right text-slate-600">{formatPortalDuration(item.duration_ms)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}


function downloadBreakdown(downloads: SisterPortalDownloadTotals | undefined): string {
  if (!downloads || downloads.total === 0) return "nessuna visura nella finestra";
  const visuraTypes = Object.entries(downloads.by_visura_type)
    .filter(([, count]) => count > 0)
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([type, count]) => `${type} ${count}`);
  const requestTypes = Object.entries(downloads.by_request_type)
    .filter(([, count]) => count > 0)
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([type, count]) => `${type === "ATTUALITA" ? "Attualità" : type === "STORICA" ? "Storiche" : type} ${count}`);
  return [...visuraTypes, ...requestTypes].join(" · ");
}


function DownloadKpi({ health }: { health: SisterPortalHealth | null }) {
  return (
    <ModuleWorkspaceKpiTile
      label="Visure scaricate"
      value={health?.downloads.total ?? 0}
      hint={downloadBreakdown(health?.downloads)}
    />
  );
}


function CredentialExecutionKpis({ health }: { health: SisterPortalHealth | null }) {
  return (
    <>
      <ModuleWorkspaceKpiTile
        label="Credenziali attive"
        value={health?.totals.operating_credentials ?? 0}
        hint="con esecuzioni nella finestra"
      />
      <ModuleWorkspaceKpiTile
        label="Media operazioni"
        value={health?.totals.average_executions_per_credential ?? 0}
        hint="per credenziale attiva"
      />
    </>
  );
}


function HealthHero({
  health,
  hours,
  onWindowChange,
}: {
  health: SisterPortalHealth | null;
  hours: number;
  onWindowChange: (hours: number) => void;
}) {
  const totals = health?.totals;
  return (
    <ElaborazioneHero
      badge={<><ServerIcon className="h-3.5 w-3.5" />Portal health</>}
      title="Il comportamento di SISTER, misurato esecuzione per esecuzione."
      description="Tempi per fase, risposte server, retry e cooldown mostrano quando il portale rallenta e come il worker reagisce."
      actions={
        <div className="flex flex-col items-end gap-3">
          <StatusPill status={health?.status ?? "unknown"} />
          <WindowSelector hours={hours} onChange={onWindowChange} />
        </div>
      }
    >
      <ModuleWorkspaceKpiRow>
        <ModuleWorkspaceKpiTile label="Esecuzioni" value={totals?.executions ?? 0} hint={`${totals?.events ?? 0} eventi`} />
        <CredentialExecutionKpis health={health} />
        <DownloadKpi health={health} />
        <ModuleWorkspaceKpiTile label="Successo" value={`${totals?.success_rate ?? 0}%`} hint={`${totals?.successes ?? 0} completate`} />
        <ModuleWorkspaceKpiTile label="Errori" value={totals?.errors ?? 0} hint="esiti terminali" variant={(totals?.errors ?? 0) > 0 ? "amber" : "default"} />
        <ModuleWorkspaceKpiTile label="P95" value={formatPortalDuration(totals?.p95_duration_ms ?? null)} hint="latenza osservata" />
        <ModuleWorkspaceKpiTile label="Retry" value={totals?.retries ?? 0} hint={`${totals?.cooldowns ?? 0} cooldown`} variant={(totals?.cooldowns ?? 0) > 0 ? "amber" : "default"} />
      </ModuleWorkspaceKpiRow>
    </ElaborazioneHero>
  );
}


function TrendAndAlerts({
  health,
  loading,
  onRefresh,
}: {
  health: SisterPortalHealth | null;
  loading: boolean;
  onRefresh: () => void;
}) {
  return (
    <div className="grid gap-6 xl:grid-cols-[1.45fr_0.75fr]">
      <article className="overflow-hidden rounded-[28px] border border-[#d9dfd6] bg-white shadow-panel">
        <ElaborazionePanelHeader
          badge={<><RefreshIcon className="h-3.5 w-3.5" />Trend</>}
          title="Andamento del portale"
          description="Verde per esiti positivi, rosso per errori. La durata media aiuta a distinguere indisponibilita e semplice lentezza."
          actions={
            <button type="button" className="btn-secondary" onClick={onRefresh} disabled={loading}>
              <RefreshIcon className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
              Aggiorna
            </button>
          }
        />
        <div className="p-6"><TelemetryTimeline items={health?.timeline ?? []} /></div>
      </article>
      <article className="overflow-hidden rounded-[28px] border border-[#d9dfd6] bg-white shadow-panel">
        <ElaborazionePanelHeader
          badge={<><AlertTriangleIcon className="h-3.5 w-3.5" />Alert</>}
          title="Segnali attivi"
          description="Alert deduplicati calcolati sui dati della finestra selezionata."
        />
        <div className="p-6"><AlertsPanel alerts={health?.alerts ?? []} /></div>
      </article>
    </div>
  );
}


function DetailPanels({ health }: { health: SisterPortalHealth | null }) {
  return (
    <>
      <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
        <article className="overflow-hidden rounded-[28px] border border-[#d9dfd6] bg-white shadow-panel">
          <ElaborazionePanelHeader title="Tempi per fase" description="Media e P95 isolano il punto del flusso che sta rallentando." />
          <div className="p-4 sm:p-6"><StepsTable items={health?.steps ?? []} /></div>
        </article>
        <article className="overflow-hidden rounded-[28px] border border-[#d9dfd6] bg-white shadow-panel">
          <ElaborazionePanelHeader title="Pool credenziali" description="Affidabilita osservata per ogni sessione operativa SISTER." />
          <div className="p-6"><CredentialCards items={health?.credentials ?? []} /></div>
        </article>
      </div>
      <div className="grid gap-6 xl:grid-cols-[0.75fr_1.25fr]">
        <article className="overflow-hidden rounded-[28px] border border-[#d9dfd6] bg-white shadow-panel">
          <ElaborazionePanelHeader title="Errori classificati" description="Frequenza, ultimo riscontro e codice HTTP quando disponibile." />
          <div className="p-6"><ErrorList items={health?.errors ?? []} /></div>
        </article>
        <article className="overflow-hidden rounded-[28px] border border-[#d9dfd6] bg-white shadow-panel">
          <ElaborazionePanelHeader title="Eventi recenti" description="Timeline tecnica sanitizzata: nessuna password, CAPTCHA o dato catastale viene registrato." />
          <div className="p-3 sm:p-5"><RecentEvents items={health?.recent_events ?? []} /></div>
        </article>
      </div>
    </>
  );
}


export function SisterPortalHealthWorkspace() {
  const [hours, setHours] = useState(24);
  const [health, setHealth] = useState<SisterPortalHealth | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const loadHealth = useCallback(async () => {
    const token = getStoredAccessToken();
    if (!token) {
      setError("Sessione non disponibile.");
      setLoading(false);
      return;
    }
    try {
      const response = await getSisterPortalHealth(token, hours);
      setHealth(response);
      setError(null);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Errore nel caricamento della telemetria SISTER.");
    } finally {
      setLoading(false);
    }
  }, [hours]);

  useEffect(() => {
    setLoading(true);
    void loadHealth();
    const interval = window.setInterval(() => void loadHealth(), REFRESH_INTERVAL_MS);
    return () => window.clearInterval(interval);
  }, [loadHealth]);

  return (
    <div className="space-y-6">
      <HealthHero health={health} hours={hours} onWindowChange={setHours} />
      {error ? (
        <ElaborazioneNoticeCard title="Telemetria non disponibile" description={error} tone="danger" />
      ) : null}
      <TrendAndAlerts health={health} loading={loading} onRefresh={() => void loadHealth()} />
      <DetailPanels health={health} />
    </div>
  );
}
