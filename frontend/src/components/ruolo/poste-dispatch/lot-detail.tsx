"use client";

import { useState } from "react";

import { requestPosteJob } from "@/lib/ruolo-poste-dispatch-api";
import type { PosteDispatchJobKind, PosteDispatchLotDetail } from "@/types/ruolo-poste-dispatch";
import { ItemRow } from "./item-row";
import { JOB_ACTIONS, JOB_LABELS, countsSummary, dateTime, errorMessage, euro } from "./labels";

const POSTE_DRAFTS_URL = "https://corrispondenza.poste.it/col/incorso.do";

function PortalWarnings({ lot }: { lot: PosteDispatchLotDetail }) {
  const foreign = lot.portal_snapshot?.foreign_drafts ?? [];
  const duplicates = lot.portal_snapshot?.duplicate_names ?? [];
  if (!foreign.length && !duplicates.length) return null;
  return <div role="alert" className="rounded-2xl border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900">
    {foreign.length > 0 && <p>In Verifica e invia ci sono {foreign.length} bozze che non sono di questo lotto: INVIA potrebbe spedire anche quelle. {foreign.map((draft) => draft.name).join(", ")}</p>}
    {duplicates.length > 0 && <p>Bozze doppie su Poste: {duplicates.join(", ")}. Eliminare le copie prima di INVIA.</p>}
  </div>;
}

function OperatorSteps({ lot }: { lot: PosteDispatchLotDetail }) {
  return <div className="rounded-2xl border border-sky-200 bg-sky-50 p-4 text-sm text-sky-950">
    <p className="font-semibold">INVIA lo preme l&apos;operatore, su Poste.</p>
    <ol className="mt-2 list-decimal space-y-1 pl-5">
      <li>Attendere che tutte le bozze siano prezzate (totale {euro(lot.priced_total)}).</li>
      <li>Aprire <a className="underline" href={POSTE_DRAFTS_URL} target="_blank" rel="noreferrer">Verifica e invia su Posta Online</a>, controllare anteprime, destinatari e prezzi.</li>
      <li>Premere INVIA su Poste, poi tornare qui e usare &quot;Controlla Poste&quot; per registrare le raccomandate.</li>
    </ol>
    {lot.draft_expires_at && <p className="mt-2">Le bozze scadono su Poste dal {dateTime(lot.draft_expires_at)}.</p>}
  </div>;
}

type Props = { token: string; lot: PosteDispatchLotDetail; canEdit: boolean; onChanged: () => void };

export function LotDetail({ token, lot, canEdit, onChanged }: Props) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function queue(kind: PosteDispatchJobKind) {
    setBusy(true);
    setError(null);
    try {
      await requestPosteJob(token, lot.id, kind);
      onChanged();
    } catch (err) {
      setError(errorMessage(err, "Operazione non avviata"));
    } finally {
      setBusy(false);
    }
  }

  return <section aria-label="Dettaglio lotto Poste" className="space-y-4">
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div>
        <h2 className="text-2xl font-semibold text-slate-900">{lot.title}</h2>
        <p className="text-sm text-slate-600">{countsSummary(lot.counts)}</p>
      </div>
      <button type="button" className="btn-secondary" onClick={onChanged}>Aggiorna</button>
    </div>
    {lot.active_job && <p role="status" className="text-sm text-slate-700">In corso: {JOB_LABELS[lot.active_job.mode] ?? lot.active_job.mode} ({lot.active_job.status}){lot.active_job.error_detail ? ` - ${lot.active_job.error_detail}` : ""}</p>}
    {error && <p role="alert" className="text-sm text-rose-800">{error}</p>}
    {canEdit && <div className="flex flex-wrap gap-2">
      {JOB_ACTIONS.map((action) => <button key={action.kind} type="button" className="btn-secondary" title={action.hint} disabled={busy || lot.active_job !== null} onClick={() => void queue(action.kind)}>{action.label}</button>)}
    </div>}
    <PortalWarnings lot={lot} />
    <OperatorSteps lot={lot} />
    <ul className="space-y-2">
      {lot.items.map((item) => <ItemRow key={`${item.id}:${item.updated_at}`} token={token} lotId={lot.id} item={item} canEdit={canEdit} onChanged={onChanged} />)}
    </ul>
  </section>;
}
