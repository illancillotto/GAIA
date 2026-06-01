"use client";

import { cn } from "@/lib/cn";
import type { WikiChatMessage, WikiEvidence, WikiToolCallSummary } from "./types";

function formatValue(value: number | string): string {
  if (typeof value === "number") {
    return Number.isInteger(value) ? value.toLocaleString("it-IT") : value.toLocaleString("it-IT", { maximumFractionDigits: 2 });
  }
  return value;
}

function asRecordArray(value: unknown): Array<Record<string, unknown>> {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.filter((item): item is Record<string, unknown> => typeof item === "object" && item !== null);
}

function renderPill(label: string, value: unknown, suffix = "") {
  if (value === null || value === undefined || value === "") {
    return null;
  }
  return (
    <span key={label} className="rounded-full border border-black/10 px-2 py-0.5 font-medium">
      {label}: {typeof value === "number" ? formatValue(value) : String(value)}
      {suffix}
    </span>
  );
}

function renderAnalyticsPreview(payload: Record<string, unknown>) {
  const metricEntries = [
    ["Km", payload.total_km],
    ["Litri", payload.total_liters],
    ["Ore", payload.total_work_hours],
    ["Sessioni", payload.active_sessions],
    ["Anomalie", payload.anomaly_count],
  ].filter((entry): entry is [string, number] => typeof entry[1] === "number");

  const topVehicles = asRecordArray(payload.top_vehicles).slice(0, 3);
  const topOperators = asRecordArray(payload.top_operators).slice(0, 3);
  const byTeam = asRecordArray(payload.by_team).slice(0, 3);

  if (metricEntries.length === 0 && topVehicles.length === 0 && topOperators.length === 0 && byTeam.length === 0) {
    return null;
  }

  return (
    <div className="mt-2 space-y-2 rounded-lg bg-white/60 p-2 text-[11px]">
      {metricEntries.length > 0 ? (
        <div className="flex flex-wrap gap-1">
          {metricEntries.map(([label, value]) => (
            <span key={label} className="rounded-full border border-black/10 px-2 py-0.5 font-medium">
              {label}: {formatValue(value)}
            </span>
          ))}
        </div>
      ) : null}
      {topVehicles.length > 0 ? (
        <div className="space-y-1">
          {topVehicles.map((item, index) => (
            <p key={`vehicle-${index}`} className="truncate">
              {(item.label as string) ?? "Mezzo"}: {formatValue((item.total_liters as number) ?? 0)} L
            </p>
          ))}
        </div>
      ) : null}
      {topOperators.length > 0 ? (
        <div className="space-y-1">
          {topOperators.map((item, index) => (
            <p key={`operator-${index}`} className="truncate">
              {(item.label as string) ?? "Operatore"}: {formatValue((item.total_km as number) ?? 0)} km
            </p>
          ))}
        </div>
      ) : null}
      {byTeam.length > 0 ? (
        <div className="space-y-1">
          {byTeam.map((item, index) => (
            <p key={`team-${index}`} className="truncate">
              {(item.team_name as string) ?? "Team"}: {formatValue((item.total_hours as number) ?? 0)} h
            </p>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function renderOperationalPreview(payload: Record<string, unknown>) {
  const alerts = asRecordArray(payload.alerts).slice(0, 3);
  const activeAlertCount = typeof payload.active_alert_count === "number" ? payload.active_alert_count : null;
  const highestLevel = typeof payload.highest_level === "string" ? payload.highest_level : null;
  const percentageUsed =
    payload.metric && typeof payload.metric === "object" && payload.metric !== null
      ? (payload.metric as Record<string, unknown>).percentage_used
      : payload.percentage_used;
  const operatorsCount = typeof payload.operators_count === "number" ? payload.operators_count : null;
  const catalogsCount = typeof payload.catalogs_count === "number" ? payload.catalogs_count : null;
  const worksetsCount = typeof payload.worksets_count === "number" ? payload.worksets_count : null;
  const recordsSynced = typeof payload.records_synced === "number" ? payload.records_synced : null;
  const recordsErrors = typeof payload.records_errors === "number" ? payload.records_errors : null;
  const jobStatus = typeof payload.status === "string" ? payload.status : null;
  const vehicles =
    payload.vehicles && typeof payload.vehicles === "object" && payload.vehicles !== null
      ? (payload.vehicles as Record<string, unknown>)
      : null;
  const activities =
    payload.activities && typeof payload.activities === "object" && payload.activities !== null
      ? (payload.activities as Record<string, unknown>)
      : null;
  const cases =
    payload.cases && typeof payload.cases === "object" && payload.cases !== null
      ? (payload.cases as Record<string, unknown>)
      : null;
  const pendingCount = typeof payload.count === "number" ? payload.count : null;
  const worksetTypeCounts =
    payload.workset_type_counts && typeof payload.workset_type_counts === "object" && payload.workset_type_counts !== null
      ? Object.entries(payload.workset_type_counts as Record<string, unknown>).slice(0, 3)
      : [];

  if (
    activeAlertCount === null &&
    highestLevel === null &&
    typeof percentageUsed !== "number" &&
    operatorsCount === null &&
    catalogsCount === null &&
    worksetsCount === null &&
    recordsSynced === null &&
    recordsErrors === null &&
    jobStatus === null &&
    vehicles === null &&
    activities === null &&
    cases === null &&
    pendingCount === null
  ) {
    return null;
  }

  return (
    <div className="mt-2 space-y-2 rounded-lg bg-white/60 p-2 text-[11px]">
      <div className="flex flex-wrap gap-1">
        {typeof percentageUsed === "number" ? (
          <span className="rounded-full border border-black/10 px-2 py-0.5 font-medium">Quota: {formatValue(percentageUsed)}%</span>
        ) : null}
        {activeAlertCount !== null ? (
          <span className="rounded-full border border-black/10 px-2 py-0.5 font-medium">Alert: {activeAlertCount}</span>
        ) : null}
        {highestLevel ? (
          <span className="rounded-full border border-black/10 px-2 py-0.5 font-medium">Livello: {highestLevel}</span>
        ) : null}
        {operatorsCount !== null ? (
          <span className="rounded-full border border-black/10 px-2 py-0.5 font-medium">Operatori: {operatorsCount}</span>
        ) : null}
        {catalogsCount !== null ? (
          <span className="rounded-full border border-black/10 px-2 py-0.5 font-medium">Cataloghi: {catalogsCount}</span>
        ) : null}
        {worksetsCount !== null ? (
          <span className="rounded-full border border-black/10 px-2 py-0.5 font-medium">Workset: {worksetsCount}</span>
        ) : null}
        {jobStatus ? (
          <span className="rounded-full border border-black/10 px-2 py-0.5 font-medium">Job: {jobStatus}</span>
        ) : null}
        {recordsSynced !== null ? (
          <span className="rounded-full border border-black/10 px-2 py-0.5 font-medium">Synced: {recordsSynced}</span>
        ) : null}
        {recordsErrors !== null ? (
          <span className="rounded-full border border-black/10 px-2 py-0.5 font-medium">Errori: {recordsErrors}</span>
        ) : null}
        {pendingCount !== null ? (
          <span className="rounded-full border border-black/10 px-2 py-0.5 font-medium">Pending: {pendingCount}</span>
        ) : null}
        {vehicles && typeof vehicles.total === "number" ? (
          <span className="rounded-full border border-black/10 px-2 py-0.5 font-medium">Mezzi: {formatValue(vehicles.total)}</span>
        ) : null}
        {activities && typeof activities.in_progress === "number" ? (
          <span className="rounded-full border border-black/10 px-2 py-0.5 font-medium">Attività in corso: {formatValue(activities.in_progress)}</span>
        ) : null}
        {cases && typeof cases.open === "number" ? (
          <span className="rounded-full border border-black/10 px-2 py-0.5 font-medium">Case aperti: {formatValue(cases.open)}</span>
        ) : null}
      </div>
      {alerts.length > 0 ? (
        <div className="space-y-1">
          {alerts.map((alert, index) => (
            <p key={`alert-${index}`} className="truncate">
              {String(alert.level ?? "alert")}: soglia {formatValue((alert.threshold as number) ?? 0)}%
            </p>
          ))}
        </div>
      ) : null}
      {worksetTypeCounts.length > 0 ? (
        <div className="space-y-1">
          {worksetTypeCounts.map(([key, value]) => (
            <p key={key} className="truncate">
              {key}: {formatValue(typeof value === "number" ? value : String(value))}
            </p>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function renderWorkflowPreview(payload: Record<string, unknown>) {
  const pills = [
    renderPill("Stato", payload.status),
    renderPill("Mezzo", payload.vehicle_code),
    renderPill("Catalogo", payload.activity_catalog_code),
    renderPill("Decisione", payload.decision),
    renderPill("Classe", payload.classification),
    renderPill("Motivo", payload.reason_type),
    renderPill("Driver", payload.actual_driver_username ?? payload.operator_username),
    renderPill("Reviewer", payload.reviewer_username),
  ].filter(Boolean);

  const lines = [
    payload.vehicle_name ? `Mezzo: ${String(payload.vehicle_name)}` : null,
    payload.team_name ? `Team: ${String(payload.team_name)}` : null,
    payload.station_name ? `Stazione: ${String(payload.station_name)}` : null,
    payload.card_code ? `Carta: ${String(payload.card_code)}` : null,
    payload.start_at ? `Inizio: ${String(payload.start_at)}` : null,
    payload.end_at ? `Fine: ${String(payload.end_at)}` : null,
    payload.started_at ? `Avvio: ${String(payload.started_at)}` : null,
    payload.ended_at ? `Chiusura: ${String(payload.ended_at)}` : null,
    payload.note ? `Nota: ${String(payload.note)}` : null,
    payload.reason_detail ? `Dettaglio: ${String(payload.reason_detail)}` : null,
  ].filter((value): value is string => Boolean(value)).slice(0, 3);

  if (pills.length === 0 && lines.length === 0) {
    return null;
  }

  return (
    <div className="mt-2 space-y-2 rounded-lg bg-white/60 p-2 text-[11px]">
      {pills.length > 0 ? <div className="flex flex-wrap gap-1">{pills}</div> : null}
      {lines.length > 0 ? (
        <div className="space-y-1">
          {lines.map((line) => (
            <p key={line} className="truncate">
              {line}
            </p>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function renderBusinessPreview(payload: Record<string, unknown>) {
  const pills = [
    renderPill("Comune", payload.nome_comune ?? payload.codice_catastale),
    renderPill("Foglio", payload.foglio),
    renderPill("Particella", payload.particella),
    renderPill("Stato", payload.status),
    renderPill("Tipo", payload.subject_type),
    renderPill("Review", typeof payload.requires_review === "boolean" ? (payload.requires_review ? "sì" : "no") : undefined),
    renderPill("Avvisi", payload.avvisi_count),
    renderPill("Documenti", payload.documents_count),
    renderPill("Utenti NAS", payload.nas_users),
    renderPill("Share", payload.shares),
    renderPill("Read", payload.read_count),
    renderPill("Write", payload.write_count),
    renderPill("Review", payload.pending_reviews),
  ].filter(Boolean);

  const lines = [
    payload.display_name ? `Nome: ${String(payload.display_name)}` : null,
    payload.full_name ? `Nome completo: ${String(payload.full_name)}` : null,
    payload.path ? `Path: ${String(payload.path)}` : null,
    payload.email_domain ? `Dominio email: ${String(payload.email_domain)}` : null,
    typeof payload.total_importo === "number" ? `Totale: ${formatValue(payload.total_importo)} euro` : null,
    typeof payload.total_subjects === "number" ? `Soggetti: ${formatValue(payload.total_subjects)}` : null,
  ].filter((value): value is string => Boolean(value)).slice(0, 3);

  if (pills.length === 0 && lines.length === 0) {
    return null;
  }

  return (
    <div className="mt-2 space-y-2 rounded-lg bg-white/60 p-2 text-[11px]">
      {pills.length > 0 ? <div className="flex flex-wrap gap-1">{pills}</div> : null}
      {lines.length > 0 ? (
        <div className="space-y-1">
          {lines.map((line) => (
            <p key={line} className="truncate">
              {line}
            </p>
          ))}
        </div>
      ) : null}
    </div>
  );
}

export function EvidencePayloadPreview({ evidence }: { evidence: WikiEvidence }) {
  if (!evidence.payload) {
    return null;
  }
  const payload = evidence.payload;
  if (typeof payload !== "object" || payload === null) {
    return null;
  }
  if (
    evidence.payload_kind === "operazioni_analytics_summary" ||
    evidence.payload_kind === "operazioni_analytics_top_fuel_vehicles" ||
    evidence.payload_kind === "operazioni_analytics_top_km_operators" ||
    evidence.payload_kind === "operazioni_analytics_work_hours_by_team"
  ) {
    return renderAnalyticsPreview(payload);
  }
  if (
    evidence.payload_kind === "operazioni_storage_status" ||
    evidence.payload_kind === "operazioni_mobile_sync_status" ||
    evidence.payload_kind === "operazioni_autodoc_sync_status" ||
    evidence.payload_kind === "operazioni_dashboard_summary" ||
    evidence.payload_kind === "operazioni_pending_approvals"
  ) {
    return renderOperationalPreview(payload);
  }
  if (
    evidence.payload_kind === "accessi_dashboard_summary" ||
    evidence.payload_kind === "accessi_nas_user_detail" ||
    evidence.payload_kind === "accessi_share_detail" ||
    evidence.payload_kind === "catasto_dashboard_summary" ||
    evidence.payload_kind === "catasto_particella_detail" ||
    evidence.payload_kind === "ruolo_dashboard_summary" ||
    evidence.payload_kind === "ruolo_subject_detail" ||
    evidence.payload_kind === "utenze_stats" ||
    evidence.payload_kind === "utenze_subject_detail" ||
    evidence.payload_kind === "riordino_practice_detail"
  ) {
    return renderBusinessPreview(payload);
  }
  if (
    evidence.payload_kind === "operazioni_case_detail" ||
    evidence.payload_kind === "operazioni_assignment_detail" ||
    evidence.payload_kind === "operazioni_maintenance_detail" ||
    evidence.payload_kind === "operazioni_usage_session_detail" ||
    evidence.payload_kind === "operazioni_activity_detail" ||
    evidence.payload_kind === "operazioni_activity_approval_detail" ||
    evidence.payload_kind === "operazioni_fuel_log_detail" ||
    evidence.payload_kind === "operazioni_unresolved_transaction_detail"
  ) {
    return renderWorkflowPreview(payload);
  }
  return null;
}

export function ModeBadge({ mode }: { mode: WikiChatMessage["mode"] }) {
  if (!mode || mode === "docs_only") {
    return <span className="rounded-full border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-[11px] font-semibold text-emerald-700">Docs</span>;
  }
  if (mode === "live_data") {
    return <span className="rounded-full border border-sky-200 bg-sky-50 px-2 py-0.5 text-[11px] font-semibold text-sky-700">Live</span>;
  }
  if (mode === "logic") {
    return <span className="rounded-full border border-amber-200 bg-amber-50 px-2 py-0.5 text-[11px] font-semibold text-amber-700">Logic</span>;
  }
  return <span className="rounded-full border border-violet-200 bg-violet-50 px-2 py-0.5 text-[11px] font-semibold text-violet-700">Hybrid</span>;
}

export function EvidenceBadge({ evidence }: { evidence: WikiEvidence }) {
  const tone =
    evidence.type === "live_data"
      ? "border-sky-200 bg-sky-50 text-sky-700"
      : evidence.type === "logic"
        ? "border-amber-200 bg-amber-50 text-amber-700"
        : evidence.type === "inference"
          ? "border-violet-200 bg-violet-50 text-violet-700"
          : "border-emerald-200 bg-emerald-50 text-emerald-700";

  return (
    <div className={cn("rounded-xl border px-2.5 py-2 text-xs", tone)}>
      <p className="font-semibold">{evidence.label}</p>
      <p className="mt-0.5 truncate opacity-80">{evidence.source_key}</p>
      {evidence.excerpt ? <p className="mt-1 line-clamp-2 text-[11px] opacity-80">{evidence.excerpt}</p> : null}
      <EvidencePayloadPreview evidence={evidence} />
    </div>
  );
}

export function ToolCallBadge({ toolCall }: { toolCall: WikiToolCallSummary }) {
  return (
    <span
      className={cn(
        "rounded-full border px-2 py-0.5 text-[11px] font-medium",
        toolCall.success
          ? "border-sky-200 bg-sky-50 text-sky-700"
          : "border-rose-200 bg-rose-50 text-rose-700"
      )}
    >
      {toolCall.tool_name}
    </span>
  );
}
