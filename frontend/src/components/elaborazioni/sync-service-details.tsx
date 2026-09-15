import { formatDateTime } from "@/lib/presentation";
import { syncStatus, type SyncServiceState, type SyncSnapshot } from "@/lib/sync-dashboard-model";

function Snapshot({ snapshot }: { snapshot: SyncSnapshot }) {
  const status = syncStatus(snapshot.status);
  return (
    <article className="rounded-2xl border border-stone-200 bg-white p-4 sm:p-5">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <h3 className="min-w-0 break-words font-semibold text-[#163524]">{snapshot.detail ?? "Ultima sincronizzazione"}</h3>
        <span className={`rounded-full px-3 py-1 text-xs font-semibold ${status.tone}`}>{status.label}</span>
      </div>
      <dl className="grid grid-cols-2 gap-3 text-sm">
        <div><dt className="text-xs text-stone-500">Avvio</dt><dd>{snapshot.startedAt ? formatDateTime(snapshot.startedAt) : "Non disponibile"}</dd></div>
        <div><dt className="text-xs text-stone-500">Fine</dt><dd>{snapshot.finishedAt ? formatDateTime(snapshot.finishedAt) : "Non disponibile"}</dd></div>
        {snapshot.metrics.map((metric) => (
          <div key={metric.label} className="min-w-0 rounded-xl bg-stone-50 px-3 py-2">
            <dt className="text-xs text-stone-500">{metric.label}</dt>
            <dd className="mt-1 break-words font-semibold text-[#163524]">{typeof metric.value === "number" ? metric.value.toLocaleString("it-IT") : metric.value}</dd>
          </div>
        ))}
      </dl>
      {snapshot.error ? <p className="mt-4 break-words rounded-xl bg-amber-50 p-3 text-sm text-amber-900">{snapshot.error}</p> : null}
    </article>
  );
}

export function SyncServiceDetails({ state }: { state?: SyncServiceState }) {
  return (
    <div className="space-y-4">
      <p className="text-sm text-stone-500">{state?.updatedAt ? `Dati letti ${formatDateTime(state.updatedAt)}` : "In attesa di dati"}</p>
      {!state ? <p role="status">Caricamento stato...</p> : null}
      {state?.error ? <p role="alert" className="break-words rounded-xl bg-amber-50 p-4 text-amber-900">Dati non disponibili: {state.error}</p> : null}
      {state && !state.error && state.snapshots.length === 0 ? <p>Nessuna sincronizzazione registrata.</p> : null}
      {state?.snapshots.map((snapshot, index) => <Snapshot key={index} snapshot={snapshot} />)}
    </div>
  );
}
