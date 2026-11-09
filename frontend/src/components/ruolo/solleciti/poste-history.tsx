import { dateTime, statusLabel } from "@/components/ruolo/poste-dispatch/labels";
import type { BatchPosteDispatch } from "@/lib/ruolo-batch-overview-api";

export function PosteHistory({ dispatches = [] }: { dispatches?: BatchPosteDispatch[] }) {
  if (dispatches.length === 0) return null;
  return <section aria-label="Storico Posta Online" className="mt-3 space-y-2">
    <h3 className="text-sm font-semibold text-slate-900">Posta Online</h3>
    {dispatches.map((dispatch) => <article key={dispatch.id} className="rounded-xl border border-slate-200 bg-slate-50 p-3">
      <p className="text-sm font-semibold text-slate-900">{statusLabel(dispatch.status)}</p>
      <dl className="mt-2 grid gap-x-4 gap-y-2 text-xs sm:grid-cols-2">
        {[
          ["ID Poste", dispatch.poste_draft_id ?? "Non disponibile"],
          ["Bozza creata", dateTime(dispatch.draft_created_at)],
          ["Spedito il", dateTime(dispatch.sent_at)],
          ["Codice raccomandata", dispatch.tracking_number ?? "Non disponibile"],
          ["Account Poste", dispatch.poste_username ?? "Non registrato"],
          ["Caricato da", dispatch.upload_requested_by_username ?? "Non registrato"],
          ["Stato rilevato su Poste", dispatch.poste_status ?? "Non disponibile"],
          ["Ultimo aggiornamento GAIA", dateTime(dispatch.updated_at)],
        ].map(([label, value]) => <div key={label} className="min-w-0"><dt className="text-slate-500">{label}</dt><dd className="break-all font-medium text-slate-900">{value}</dd></div>)}
      </dl>
    </article>)}
  </section>;
}
