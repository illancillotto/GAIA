"use client";

import { useCallback, useEffect, useState } from "react";

import { getPosteLot, listPosteLots } from "@/lib/ruolo-poste-dispatch-api";
import type { PosteDispatchLotDetail, PosteDispatchLotSummary } from "@/types/ruolo-poste-dispatch";
import { CandidatePicker } from "./candidate-picker";
import { countsSummary, dateTime, errorMessage } from "./labels";
import { LotDetail } from "./lot-detail";

export function usePosteLots(token: string) {
  const [lots, setLots] = useState<PosteDispatchLotSummary[]>([]);
  const [selected, setSelected] = useState<PosteDispatchLotDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async (lotId?: string) => {
    setError(null);
    try {
      setLots((await listPosteLots(token)).items);
      if (lotId) setSelected(await getPosteLot(token, lotId));
    } catch (err) {
      setError(errorMessage(err, "Lotti Poste non caricati"));
    }
  }, [token]);

  useEffect(() => { void reload(); }, [reload]);
  return { lots, selected, error, reload };
}

type Props = { token: string; canEdit: boolean; posteLots: ReturnType<typeof usePosteLots> };

export function PostePanel({ token, canEdit, posteLots }: Props) {
  const { lots, selected, error, reload } = posteLots;
  return <div className="space-y-6">
    <p className="rounded-2xl border border-sky-200 bg-sky-50 p-4 text-sm text-sky-950">GAIA verifica gli indirizzi e crea le bozze in Verifica e invia. Non preme mai INVIA: la spedizione la conferma l&apos;operatore su Poste, poi GAIA registra le raccomandate dall&apos;archivio.</p>
    {error && <div role="alert" className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">{error}</div>}
    <div className="grid gap-6 lg:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)]">
      <div className="space-y-6">
        <section aria-label="Lotti Poste" className="rounded-[28px] border border-[#d8dfd3] bg-white p-5 shadow-panel">
          <h2 className="mb-3 text-lg font-semibold text-slate-900">Lotti Posta Online</h2>
          {lots.length === 0 ? <p className="text-sm text-slate-500">Nessun lotto Poste.</p> : <div className="space-y-2">{lots.map((lot) => <button key={lot.id} type="button" onClick={() => void reload(lot.id)} className={`w-full rounded-2xl border p-3 text-left ${selected?.id === lot.id ? "border-[#1d4e35] bg-[#eef7ef]" : "border-slate-200"}`}>
            <span className="font-semibold text-slate-900">{lot.title}</span>
            <span className="block text-xs text-slate-500">{countsSummary(lot.counts)} · {dateTime(lot.created_at)}</span>
          </button>)}</div>}
        </section>
        {canEdit && <section className="rounded-[28px] border border-[#d8dfd3] bg-white p-5 shadow-panel"><CandidatePicker token={token} onCreated={(lot) => void reload(lot.id)} /></section>}
      </div>
      <section className="rounded-[28px] border border-[#d8dfd3] bg-white p-5 shadow-panel">
        {selected ? <LotDetail token={token} lot={selected} canEdit={canEdit} onChanged={() => void reload(selected.id)} /> : <p className="text-sm text-slate-500">Seleziona un lotto.</p>}
      </section>
    </div>
  </div>;
}
