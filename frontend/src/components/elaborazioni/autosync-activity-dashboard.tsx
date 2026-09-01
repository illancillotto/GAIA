"use client";

import Link from "next/link";

import { ElaborazioneStatusBadge } from "@/components/elaborazioni/status-badge";
import { formatDateTime } from "@/lib/presentation";
import type { ElaborazioneCredential, ElaborazioneRuoloAutoSyncStatus } from "@/types/api";
import type {
  CatastoAutoSyncDashboardSummary,
  CatastoAutoSyncEvent,
} from "@/types/elaborazioni-continuous-sync";

const NUMBER = new Intl.NumberFormat("it-IT", { maximumFractionDigits: 1 });

function formatDuration(seconds: number | null): string {
  if (seconds === null) return "—";
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.round(seconds / 60);
  return minutes < 60 ? `${minutes} min` : `${NUMBER.format(minutes / 60)} h`;
}

function MetricCard({ label, value, detail }: { label: string; value: string | number; detail: string }) {
  return (
    <div className="min-w-0 rounded-[20px] border border-gray-100 bg-white p-3 sm:p-4">
      <p className="text-[11px] font-medium text-gray-500 sm:text-xs">{label}</p>
      <p className="mt-1 truncate text-xl font-semibold text-gray-950 sm:mt-2 sm:text-2xl">{value}</p>
      <p className="mt-1 text-xs text-gray-500">{detail}</p>
    </div>
  );
}

function SummaryMetrics({ summary }: { summary: CatastoAutoSyncDashboardSummary }) {
  return (
    <div data-testid="autosync-summary-metrics" className="grid grid-cols-2 gap-2 sm:gap-3 xl:grid-cols-6">
      <MetricCard detail="documenti prodotti" label="Visure scaricate da SISTER" value={NUMBER.format(summary.documents_downloaded)} />
      <MetricCard detail="visure completate/ora" label="Velocità oraria" value={NUMBER.format(summary.completed_per_hour)} />
      <MetricCard detail="richieste complessive" label="Visure elaborate" value={`${NUMBER.format(summary.requests_completed)} / ${NUMBER.format(summary.requests_total)}`} />
      <MetricCard detail="batch in lavorazione" label="Attività in corso" value={summary.batches_active} />
      <MetricCard detail="richieste con blocco" label="Blocchi" value={summary.requests_blocked} />
      <MetricCard detail="media batch completati" label="Durata media" value={formatDuration(summary.average_batch_duration_seconds)} />
    </div>
  );
}

function OperationalPipeline({ status, credentials }: { status: ElaborazioneRuoloAutoSyncStatus; credentials: ElaborazioneCredential[] }) {
  const selected = status.config.credential_ids ?? (status.config.credential_id ? [status.config.credential_id] : []);
  const available = selected.filter((id) => status.available_credential_ids.includes(id)).length;
  const stages = [
    ["1. Aggiornamento sorgenti", status.config.last_source_refresh_at ? `Ultimo: ${formatDateTime(status.config.last_source_refresh_at)}` : "Non ancora eseguito"],
    ["2. Pianificazione e coda", `${status.counts.pending + status.counts.queued} in attesa · ${status.counts.processing} in corso`],
    ["3. Elaborazione progressiva", status.running_batch?.current_operation ?? "Nessuna elaborazione attiva"],
    ["4. Archiviazione documenti", `${status.dashboard.summary.documents_downloaded} visure disponibili`],
  ];
  return (
    <div className="grid gap-3 lg:grid-cols-[2fr,1fr]">
      <section aria-labelledby="autosync-pipeline-title" className="rounded-[24px] border border-gray-100 bg-gray-50 p-4">
        <h3 className="text-sm font-semibold text-gray-900" id="autosync-pipeline-title">Attività svolte dall’AutoSync</h3>
        <div className="mt-3 grid grid-cols-2 gap-2 sm:gap-3">
          {stages.map(([title, detail]) => <div className="min-w-0 rounded-[18px] border border-gray-100 bg-white p-3" key={title}><p className="text-sm font-semibold text-gray-900">{title}</p><p className="mt-1 text-xs text-gray-500">{detail}</p></div>)}
        </div>
      </section>
      <section aria-labelledby="autosync-runtime-title" className="rounded-[24px] border border-gray-100 bg-gray-50 p-4">
        <h3 className="text-sm font-semibold text-gray-900" id="autosync-runtime-title">Stato credenziali e worker</h3>
        <dl className="mt-3 space-y-3 text-sm">
          <div className="flex justify-between gap-3"><dt className="text-gray-500">Worker visure</dt><dd className="font-medium text-gray-900">{status.running_batch ? "In elaborazione" : "In attesa"}</dd></div>
          <div className="flex justify-between gap-3"><dt className="text-gray-500">Credenziali libere</dt><dd className="font-medium text-gray-900">{available} / {selected.length}</dd></div>
          <div className="flex justify-between gap-3"><dt className="text-gray-500">Profili attivi</dt><dd className="font-medium text-gray-900">{credentials.filter((credential) => credential.active).length}</dd></div>
          <div className="flex justify-between gap-3"><dt className="text-gray-500">Lock / concorrenza</dt><dd className="font-medium text-gray-900">{status.dashboard.summary.batches_active ? "Batch attivo" : "Libero"}</dd></div>
        </dl>
      </section>
    </div>
  );
}

function HourlyTrend({ status }: { status: ElaborazioneRuoloAutoSyncStatus }) {
  const rows = status.dashboard.hourly;
  const maximum = Math.max(1, ...rows.map((row) => row.completed + row.failed));
  return (
    <section aria-labelledby="autosync-hourly-title" className="rounded-[24px] border border-gray-100 p-4">
      <div className="flex flex-wrap items-end justify-between gap-2"><div><h3 className="text-sm font-semibold text-gray-900" id="autosync-hourly-title">Andamento ultime 24 ore</h3><p className="mt-1 text-xs text-gray-500">Completate, fallite e documenti scaricati per ora.</p></div><p className="text-xs text-gray-500">Ultima attività: {status.dashboard.summary.last_activity_at ? formatDateTime(status.dashboard.summary.last_activity_at) : "—"}</p></div>
      {rows.length ? <div className="mt-4 flex min-h-36 items-end gap-2 overflow-x-auto pb-2" role="img" aria-label="Andamento orario delle visure AutoSync">{rows.map((row) => {
        const height = Math.max(8, ((row.completed + row.failed) / maximum) * 100);
        return <div className="flex min-w-14 flex-1 flex-col items-center gap-2" key={row.hour}><div aria-label={`${row.completed} completate, ${row.failed} fallite, ${row.documents_downloaded} scaricate`} className="relative flex h-24 w-full items-end overflow-hidden rounded-lg bg-gray-100"><span className="block w-full bg-[#477a55]" style={{ height: `${height}%` }} /><span className="absolute bottom-0 right-0 block w-2 bg-red-400" style={{ height: `${Math.max(0, (row.failed / maximum) * 100)}%` }} /></div><span className="text-[11px] text-gray-500">{new Date(row.hour).toLocaleTimeString("it-IT", { hour: "2-digit", minute: "2-digit" })}</span></div>;
      })}</div> : <p className="mt-4 text-sm text-gray-500">Nessuna attività nelle ultime 24 ore.</p>}
    </section>
  );
}

function RecentBatches({ status }: { status: ElaborazioneRuoloAutoSyncStatus }) {
  return (
    <section aria-labelledby="autosync-batches-title" className="rounded-[24px] border border-gray-100 p-4">
      <h3 className="text-sm font-semibold text-gray-900" id="autosync-batches-title">Ultime esecuzioni AutoSync</h3>
      <div className="mt-3 space-y-3">{status.dashboard.recent_batches.length ? status.dashboard.recent_batches.map((batch) => {
        const processed = batch.completed_items + batch.failed_items + batch.not_found_items + batch.skipped_items;
        const progress = Math.min(100, Math.round((processed / Math.max(1, batch.total_items)) * 100));
        return <div className="rounded-[18px] border border-gray-100 bg-gray-50 p-3" key={batch.id}><div className="flex flex-wrap items-start justify-between gap-2"><div className="min-w-0 flex-1"><p className="truncate text-sm font-semibold text-gray-900">{batch.name ?? "Esecuzione AutoSync"}</p><p className="mt-1 text-xs text-gray-500">{processed} / {batch.total_items} · {batch.current_operation ?? "In attesa"}</p></div><ElaborazioneStatusBadge status={batch.status} /></div><div className="mt-3 h-2 overflow-hidden rounded-full bg-gray-200"><div className="h-full rounded-full bg-[#477a55]" style={{ width: `${progress}%` }} /></div><div className="mt-3 flex justify-between gap-3 text-xs"><span className="text-gray-500">{formatDateTime(batch.created_at)}</span><Link className="font-semibold text-[#1D4E35] underline-offset-4 hover:underline" href={`/elaborazioni/batches/${batch.id}`}>Apri dettaglio</Link></div></div>;
      }) : <p className="text-sm text-gray-500">Nessuna esecuzione AutoSync presente.</p>}</div>
    </section>
  );
}

function EventList({ events, empty }: { events: CatastoAutoSyncEvent[]; empty: string }) {
  if (!events.length) return <p className="mt-3 text-sm text-gray-500">{empty}</p>;
  return <div className="mt-3 space-y-3">{events.map((event) => <div className={`rounded-[18px] border p-3 ${event.level === "error" ? "border-red-100 bg-red-50" : "border-gray-100 bg-gray-50"}`} key={`${event.request_id ?? event.batch_id}-${event.timestamp}`}><div className="flex flex-wrap items-start justify-between gap-2"><div><p className="text-sm font-semibold text-gray-900">{event.title}</p>{event.detail ? <p className="mt-1 text-sm text-gray-600">{event.detail}</p> : null}</div><time className="text-xs text-gray-500" dateTime={event.timestamp}>{formatDateTime(event.timestamp)}</time></div><Link className="mt-2 inline-flex text-xs font-semibold text-[#1D4E35]" href={`/elaborazioni/batches/${event.batch_id}`}>Apri batch</Link></div>)}</div>;
}

function EventsAndBlocks({ status }: { status: ElaborazioneRuoloAutoSyncStatus }) {
  const blocked = status.dashboard.events.filter((event) => event.level === "error" || event.level === "warning");
  const logs = status.dashboard.events.filter((event) => event.level !== "error" && event.level !== "warning");
  return <div className="grid gap-4 xl:grid-cols-2"><section aria-labelledby="autosync-blocks-title" className="rounded-[24px] border border-gray-100 p-4"><h3 className="text-sm font-semibold text-gray-900" id="autosync-blocks-title">Blocchi ed errori</h3><EventList empty="Nessun blocco o errore recente." events={blocked} /></section><section aria-labelledby="autosync-logs-title" className="rounded-[24px] border border-gray-100 p-4"><h3 className="text-sm font-semibold text-gray-900" id="autosync-logs-title">Ultimi eventi e log</h3><EventList empty="Nessun evento informativo recente." events={logs} /></section></div>;
}

export function AutoSyncActivityDashboard({ status, credentials }: { status: ElaborazioneRuoloAutoSyncStatus | null; credentials: ElaborazioneCredential[] }) {
  if (!status) return <section aria-labelledby="autosync-activity-title" className="rounded-[28px] border border-gray-100 bg-white p-6 shadow-panel"><h2 className="text-lg font-semibold" id="autosync-activity-title">Attività AutoSync</h2><p className="mt-2 text-sm text-gray-500">Caricamento attività in corso…</p></section>;
  return (
    <section aria-labelledby="autosync-activity-title" className="space-y-3 rounded-[28px] border border-[#d9dfd6] bg-white p-3 shadow-panel sm:space-y-4 md:p-6" data-testid="autosync-dashboard-shell">
      <div className="flex flex-wrap items-start justify-between gap-3"><div><p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#477a55]">Monitor operativo</p><h2 className="mt-2 text-xl font-semibold text-gray-950" id="autosync-activity-title">Attività AutoSync</h2><p className="mt-1 max-w-3xl text-sm text-gray-600">Stato, avanzamento, visure, velocità, code, blocchi e log dell’elaborazione continua.</p></div><span className={`rounded-full px-3 py-1.5 text-xs font-semibold ${status.config.enabled ? "bg-emerald-100 text-emerald-800" : "bg-gray-100 text-gray-700"}`}>AutoSync {status.config.enabled ? "ON" : "OFF"}</span></div>
      <SummaryMetrics summary={status.dashboard.summary} />
      <OperationalPipeline credentials={credentials} status={status} />
      <div className="grid gap-4 xl:grid-cols-[1.35fr,1fr]"><HourlyTrend status={status} /><RecentBatches status={status} /></div>
      <EventsAndBlocks status={status} />
    </section>
  );
}
