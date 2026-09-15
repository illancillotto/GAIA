import { formatDateTime } from "@/lib/presentation";
import { syncSummary, type SyncService, type SyncServiceState } from "@/lib/sync-dashboard-model";

export function SyncServiceCard({ service, state, onDetails, onOpen }: {
  service: SyncService;
  state?: SyncServiceState;
  onDetails: () => void;
  onOpen: () => void;
}) {
  const summary = syncSummary(state);
  return (
    <article aria-label={service.title} id={service.id} className="flex h-full min-w-0 flex-col rounded-[24px] border border-[#d9dfd6] bg-white p-5 shadow-sm transition-shadow hover:shadow-md sm:p-6">
      <div className="mb-4 flex items-center justify-between gap-2">
        <span className={`rounded-full px-3 py-1 text-xs font-semibold ${summary.tone}`}>{summary.label}</span>
        {state && !state.error ? <span className="text-xs text-stone-500">Flussi: {state.snapshots.length}</span> : null}
      </div>
      <h3 className="text-lg font-semibold text-[#163524]">{service.title}</h3>
      <p className="mt-2 text-sm leading-6 text-stone-600">{service.description}</p>
      <div className="mb-5 mt-auto pt-5">
        <p className="text-xs text-stone-500">Ultimo avvio</p>
        <p className="mt-1 text-sm font-medium text-stone-800">{summary.lastStarted ? formatDateTime(summary.lastStarted) : "Non disponibile"}</p>
        {state?.error ? <p className="mt-2 text-sm text-amber-800">Dati non disponibili. Apri i dettagli.</p> : null}
      </div>
      <div className="grid grid-cols-2 gap-2 border-t border-stone-100 pt-4">
        <button type="button" className="btn-secondary justify-center text-sm" aria-haspopup="dialog" onClick={onDetails}>Vedi dettagli</button>
        <button type="button" className="btn-primary justify-center text-sm" aria-haspopup="dialog" onClick={onOpen}>Apri monitor</button>
      </div>
    </article>
  );
}
