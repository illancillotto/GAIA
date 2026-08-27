import type { CatastoBatchStatistics, ElaborazioneBatch, ElaborazioneBatchDetail } from "@/types/api";


export function formatBatchDuration(seconds: number | null | undefined): string {
  if (seconds == null) return "—";
  const safeSeconds = Math.max(Math.round(seconds), 0);
  const hours = Math.floor(safeSeconds / 3600);
  const minutes = Math.floor((safeSeconds % 3600) / 60);
  const remainder = safeSeconds % 60;
  if (hours > 0) return `${hours}h ${minutes.toString().padStart(2, "0")}m`;
  if (minutes > 0) return `${minutes}m ${remainder.toString().padStart(2, "0")}s`;
  return `${remainder}s`;
}

function formatRate(value: number | null): string {
  return value == null ? "—" : value.toLocaleString("it-IT", { maximumFractionDigits: 2 });
}

export function shouldRetainBatchDetail(
  detail: ElaborazioneBatchDetail | undefined,
  status: ElaborazioneBatch["status"],
): detail is ElaborazioneBatchDetail {
  return detail !== undefined && !["pending", "processing"].includes(status);
}

export function BatchStatisticsInline({ statistics }: { statistics?: CatastoBatchStatistics | null }) {
  if (!statistics) return <span className="text-xs text-gray-400">Calcolo statistiche...</span>;
  return (
    <div className="space-y-1 text-xs text-gray-600">
      <div><span className="font-semibold text-gray-800">{formatBatchDuration(statistics.duration_seconds)}</span> · {formatRate(statistics.completed_per_hour)} visure/ora</div>
      <div className="max-w-[20rem] truncate" title={statistics.credentials_used.map((item) => item.label).join(", ")}>
        {statistics.credentials_used.length > 0
          ? statistics.credentials_used.map((item) => item.label).join(", ")
          : "Nessuna credenziale usata"}
      </div>
    </div>
  );
}

export function BatchStatisticsPanel({ statistics }: { statistics?: CatastoBatchStatistics | null }) {
  if (!statistics) return null;
  const metrics = [
    ["Durata totale", formatBatchDuration(statistics.duration_seconds)],
    ["Visure/ora", formatRate(statistics.completed_per_hour)],
    ["Avanzamento", `${statistics.progress_percent.toLocaleString("it-IT")}%`],
    ["Successo", statistics.success_rate_percent == null ? "—" : `${statistics.success_rate_percent.toLocaleString("it-IT")}%`],
    ["Tentativi medi", statistics.average_attempts.toLocaleString("it-IT", { maximumFractionDigits: 2 })],
    ["Tempo residuo stimato", formatBatchDuration(statistics.estimated_remaining_seconds)],
  ];

  return (
    <section aria-label="Statistiche batch" className="border-b border-[#edf1eb] bg-[#f7faf6] px-5 py-5">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-6">
        {metrics.map(([label, value]) => (
          <div className="rounded-2xl border border-[#dce7de] bg-white px-4 py-3" key={label}>
            <div className="text-[11px] font-semibold uppercase tracking-[0.14em] text-gray-500">{label}</div>
            <div className="mt-1 text-lg font-semibold text-[#173f2c]">{value}</div>
          </div>
        ))}
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        {statistics.credentials_used.length > 0 ? statistics.credentials_used.map((credential) => (
          <div className="rounded-full border border-[#cfe0d5] bg-white px-3 py-1.5 text-xs text-gray-600" key={credential.credential_id}>
            <span className="font-semibold text-[#1D4E35]">{credential.label}</span>
            {credential.sister_username ? ` · ${credential.sister_username}` : ""}
            {` · ${credential.request_count} richieste · ${credential.execution_count} esecuzioni`}
          </div>
        )) : <span className="text-sm text-gray-500">Nessuna credenziale ancora utilizzata.</span>}
      </div>
    </section>
  );
}
