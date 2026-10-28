"use client";

import { useCallback, useEffect, useState } from "react";

import { RuoloModulePage } from "@/components/ruolo/module-page";
import { getPosteLot, listPosteLots } from "@/lib/ruolo-poste-dispatch-api";
import { useSessionBootstrap } from "@/lib/use-session-bootstrap";
import type { PosteDispatchLotDetail, PosteDispatchLotSummary } from "@/types/ruolo-poste-dispatch";
import { CandidatePicker } from "./candidate-picker";
import { countsSummary, dateTime, errorMessage } from "./labels";
import { LotDetail } from "./lot-detail";

export function PosteDispatchAccess() {
  const session = useSessionBootstrap();
  if (session.status !== "ready" || !session.token || !session.currentUser) return <p role="status">Verifica accesso...</p>;
  const allowed = session.currentUser.role === "super_admin" || session.currentUser.enabled_modules.includes("ruolo");
  if (!allowed || !session.grantedSectionKeys.includes("ruolo.tributi.view")) return <p role="alert">Accesso non autorizzato.</p>;
  return <PosteDispatchWorkspace key={session.token} token={session.token} canEdit={session.grantedSectionKeys.includes("ruolo.tributi.manage_status")} />;
}

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

function PosteDispatchWorkspace({ token, canEdit }: { token: string; canEdit: boolean }) {
  const { lots, selected, error, reload } = usePosteLots(token);
  return <RuoloModulePage title="Invio solleciti con Posta Online" description="Bozze di Raccomandata A/R preparate da GAIA, inviate dall'operatore su Poste." breadcrumb="Invio Poste" requiredSection="ruolo.tributi.view">
    <div className="space-y-6">
      <section className="rounded-[28px] border border-[#d8dfd3] bg-[#203829] p-7 text-white shadow-panel">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[#cfe2b8]">Raccomandata A/R online</p>
        <h1 className="mt-2 text-3xl font-semibold">GAIA prepara, l&apos;operatore invia</h1>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-white/75">GAIA verifica gli indirizzi e crea le bozze in Verifica e invia. Non preme mai INVIA: la spedizione la conferma l&apos;operatore su Poste, poi GAIA registra le raccomandate dall&apos;archivio.</p>
      </section>
      {!canEdit && <p>Accesso in sola lettura.</p>}
      {error && <div role="alert" className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">{error}</div>}
      <div className="grid gap-6 lg:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)]">
        <div className="space-y-6">
          <section aria-label="Lotti Poste" className="rounded-[28px] border border-[#d8dfd3] bg-white p-5 shadow-panel">
            <h2 className="mb-3 text-lg font-semibold text-slate-900">Lotti</h2>
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
    </div>
  </RuoloModulePage>;
}
