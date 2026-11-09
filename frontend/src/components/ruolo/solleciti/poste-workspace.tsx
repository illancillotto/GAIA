"use client";

import { useState, type ReactNode } from "react";
import { AccountSelector } from "@/components/ruolo/poste-dispatch/account-controls";
import { dateTime, euro } from "@/components/ruolo/poste-dispatch/labels";
import { GeneratedNoticePreview } from "./document-access";
import { PosteHistory } from "./poste-history";
import { usePosteWorkspace } from "./use-poste-workspace";
import { WorkspaceGeneration } from "./workspace-generation";
import { STAGES, STAGE_TONES } from "./workspace-status";
import type { WorkspaceNotice, WorkspaceStage } from "@/lib/ruolo-solleciti-workspace-api";

type Props = { token: string; canEdit: boolean; legacy: ReactNode };
type State = ReturnType<typeof usePosteWorkspace>;

export function PosteWorkspace({ token, canEdit, legacy }: Props) {
  const state = usePosteWorkspace(token);
  const [historical, setHistorical] = useState(false);
  return <div className="space-y-4">
    <header className="flex flex-wrap items-center justify-between gap-3">
      <h2 className="text-xl font-semibold">{historical ? "Storico avvisi" : "Avvisi"}</h2>
      {historical ? <button type="button" className="btn-secondary" onClick={() => setHistorical(false)}>Torna agli avvisi</button> : canEdit && <WorkspaceGeneration />}
    </header>
    {historical ? legacy : <>
      <WorkspaceFilters key={state.filters.q} state={state} canEdit={canEdit} />
      {state.data && <WorkspacePosteStates state={state} />}
      {state.error && <p role="alert" className="text-sm text-rose-800">{state.error}</p>}
      {state.notice && <p role="status" className="text-sm text-emerald-900">{state.notice}</p>}
      {!state.data ? !state.error && <p role="status">Caricamento avvisi...</p> : <div className="grid items-start gap-4 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
        <NoticeList state={state} canEdit={canEdit} />
        <NoticeDetail state={state} token={token} canEdit={canEdit} />
      </div>}
      {canEdit && state.selected.length > 0 && <PrepareSelection state={state} token={token} />}
      <details className="rounded-xl border border-slate-200 px-4 py-3 text-sm">
        <summary className="cursor-pointer text-slate-600">Strumenti avanzati</summary>
        <button type="button" className="btn-secondary mt-3" onClick={() => setHistorical(true)}>Storico lotti di generazione</button>
      </details>
    </>}
  </div>;
}

function WorkspaceFilters({ state, canEdit }: { state: State; canEdit: boolean }) {
  const [q, setQ] = useState(state.filters.q);
  const years = [...new Set([2021, ...(state.filters.year ? [Number(state.filters.year)] : []), ...state.data?.groups.flatMap((group) => group.years) ?? []])].sort();
  return <div className="space-y-3">
    <form aria-label="Filtri avvisi" className="flex flex-wrap items-end gap-3" onSubmit={(event) => { event.preventDefault(); state.filter({ q }); }}>
      <label className="text-sm">Anno di riferimento<select className="form-control block" value={state.filters.year} onChange={(event) => state.filter({ year: event.target.value, account: "all" })}><option value="">Tutti gli anni</option>{years.map((year) => <option key={year} value={year}>{year}</option>)}</select></label>
      <label className="min-w-0 basis-64 grow text-sm">Cerca contribuente o avviso<input className="form-control block w-full" placeholder="Nome, cognome o CF/P.IVA" maxLength={120} value={q} onChange={(event) => setQ(event.target.value)} /></label>
      <button className="btn-primary" type="submit">Cerca</button>
      <button type="button" className="btn-secondary" onClick={state.reload}>Aggiorna elenco</button>
    </form>
    <AdditionalFilters state={state} canEdit={canEdit} />
  </div>;
}

function AdditionalFilters({ state, canEdit }: { state: State; canEdit: boolean }) {
  const accounts = new Map(state.data?.groups.map((group) => [group.account_key, group.account_label]));
  const active = state.filters.account !== "all" || state.filters.stage !== "all";
  return <details className="rounded-xl border border-slate-200 px-4 py-3">
    <summary className="cursor-pointer text-sm text-slate-600">Altri filtri{active && <span className="ml-2 font-semibold text-emerald-900">Attivi</span>}</summary>
    <div className="mt-3 flex flex-wrap items-end gap-3">
      <label className="text-sm">Stato avviso<select className="form-control block" value={state.filters.stage} onChange={(event) => state.filter({ stage: event.target.value })}><option value="all">Tutti gli stati</option>{Object.entries(STAGES).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label>
      <label className="text-sm">Account Poste<select className="form-control block max-w-full" value={state.filters.account} onChange={(event) => state.filter({ account: event.target.value })}><option value="all">Tutti gli account</option>{[...accounts].map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label>
      <button type="button" className="btn-secondary" onClick={() => state.filter({ account: "all", stage: "all" })}>Reimposta filtri</button>
      {canEdit && /^[1-9][0-9]*$/.test(state.filters.account) && <button type="button" className="btn-secondary" disabled={state.busy} onClick={() => void state.reconcileAccount()}>Controlla account su Poste</button>}
    </div>
  </details>;
}

function WorkspacePosteStates({ state }: { state: State }) {
  const counts: Record<string, number> = {};
  for (const group of state.data!.groups) {
    if (state.filters.year && !group.years.includes(Number(state.filters.year))) continue;
    if (state.filters.account !== "all" && state.filters.account !== group.account_key) continue;
    for (const [stage, count] of Object.entries(group.stages)) counts[stage] = (counts[stage] ?? 0) + count;
  }
  const total = Object.values(counts).reduce((sum, count) => sum + count, 0);
  return <nav aria-label="Stati avvisi su Poste" className="flex flex-wrap gap-2">
    <button type="button" className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm aria-pressed:ring-2 aria-pressed:ring-emerald-700" aria-pressed={state.filters.stage === "all"} onClick={() => state.filter({ stage: "all" })}>Tutti · {total}</button>
    {Object.entries(STAGES).map(([stage, label]) => <button key={stage} type="button" className={`rounded-lg border px-3 py-2 text-sm aria-pressed:ring-2 aria-pressed:ring-emerald-700 ${STAGE_TONES[stage as WorkspaceStage]}`} aria-pressed={state.filters.stage === stage} onClick={() => state.filter({ stage })}>{label} · {counts[stage] ?? 0}</button>)}
  </nav>;
}

function NoticePosteEvidence({ row }: { row: WorkspaceNotice }) {
  if (!["sent", "draft"].includes(row.stage)) return null;
  const statuses = row.stage === "sent" ? ["sent"] : ["draft_created", "draft_priced"];
  const dispatch = row.poste_dispatches.find((attempt) => statuses.includes(attempt.status));
  if (!dispatch) return <span className="mt-1 block text-xs text-amber-900">Storico Poste da verificare</span>;
  const timestamp = row.stage === "sent" ? dispatch.sent_at : dispatch.draft_created_at;
  return <span className="mt-1 block break-words text-xs text-slate-600">ID Poste: {dispatch.poste_draft_id ?? "Non registrato"} · {row.stage === "sent" ? "Spedito il" : "Caricato il"} {dateTime(timestamp)}{dispatch.tracking_number && <span className="block">Raccomandata: {dispatch.tracking_number}</span>}</span>;
}

function NoticeList({ state, canEdit }: { state: State; canEdit: boolean }) {
  const data = state.data!;
  return <section aria-label="Elenco avvisi" className="min-w-0 rounded-2xl border border-slate-200 bg-white p-4">
    <h3 className="mb-3 font-semibold">{data.total} avvisi · pagina {data.page}</h3>
    {data.items.length === 0 && <p>Nessun avviso corrisponde ai filtri.</p>}
    <div className="divide-y divide-slate-200">{data.items.map((row) => <div key={row.item_id} className={`flex items-start gap-3 rounded-lg p-3 ${state.detailId === row.item_id ? "bg-emerald-50" : ""}`}>
      {canEdit && <input type="checkbox" className="mt-1" aria-label={`Prepara avviso ${row.notice_number}`} checked={state.selected.includes(row.item_id)} disabled={!row.can_prepare || state.busy} onChange={() => state.toggle(row.item_id)} />}
      <button type="button" aria-label={`Apri avviso ${row.notice_number}`} aria-pressed={state.detailId === row.item_id} onClick={() => state.setDetailId(row.item_id)} className="min-w-0 flex-1 text-left">
        <span className="block break-words font-semibold">{row.label}</span>
        <span className="block break-words text-xs text-slate-600">{row.codice_fiscale} · {row.years.join(", ")} · {row.notice_number}</span>
        <span className="mt-1 flex flex-wrap items-center gap-2 text-sm"><span>{euro(row.amount)}</span><span className={`rounded-full border px-2 py-0.5 text-xs font-semibold ${STAGE_TONES[row.stage]}`}>{STAGES[row.stage]}</span></span>
        <NoticePosteEvidence row={row} />
      </button>
    </div>)}</div>
    <nav aria-label="Pagine avvisi" className="mt-3 flex flex-wrap gap-3"><button type="button" className="btn-secondary" disabled={data.page === 1} onClick={() => state.filter({ page: data.page - 1 })}>Precedenti avvisi</button><button type="button" className="btn-secondary" disabled={data.page * data.page_size >= data.total} onClick={() => state.filter({ page: data.page + 1 })}>Altri avvisi</button></nav>
  </section>;
}

function NoticeDetail({ state, token, canEdit }: { state: State; token: string; canEdit: boolean }) {
  const row = state.detail;
  if (!row) return <section className="rounded-2xl border border-slate-200 bg-white p-5 text-sm text-slate-600"><p>Apri un avviso per controllare il PDF e lo stato su Poste.</p></section>;
  return <section aria-label="Dettaglio avviso" className="min-w-0 space-y-4 rounded-2xl border border-slate-200 bg-white p-4 lg:sticky lg:top-4">
    <div><h3 className="text-lg font-semibold">Avviso {row.notice_number}</h3><p className="break-words">{row.label}</p><p className="text-sm text-slate-600">{row.codice_fiscale} · {row.years.join(", ")} · {euro(row.amount)}</p></div>
    <div className="flex flex-wrap items-center gap-3"><span className={`rounded-full border px-3 py-1 text-sm font-semibold ${STAGE_TONES[row.stage]}`}>{STAGES[row.stage]}</span>{row.lot_id && canEdit && <button type="button" className="btn-secondary" disabled={state.busy} onClick={() => void state.reconcile(row.lot_id!)}>Controlla stato su Poste</button>}</div>
    {row.download_url ? <GeneratedNoticePreview key={row.item_id} token={token} url={row.download_url} defaultOpen /> : <p role="alert">PDF non disponibile: chiedi all’ufficio Tributi di verificare il documento.</p>}
    {row.poste_dispatches.length > 0 && <details className="rounded-xl border border-slate-200 px-4 py-3"><summary className="cursor-pointer text-sm font-medium">ID Poste, date e storico</summary><PosteHistory dispatches={row.poste_dispatches} /></details>}
  </section>;
}

function PrepareSelection({ state, token }: { state: State; token: string }) {
  const [credentialId, setCredentialId] = useState<number | null>(null);
  return <section aria-label="Prepara su Poste" className="sticky bottom-3 z-10 space-y-3 rounded-2xl border border-emerald-200 bg-white p-4 shadow-lg">
    <p className="font-semibold">Selezionati: {state.selected.length} · massimo 50</p>
    <div className="flex flex-wrap items-end gap-3"><div className="min-w-0 flex-1"><AccountSelector token={token} label="Account per la preparazione" value={credentialId} onChange={setCredentialId} /></div>
      <button type="button" className="btn-primary" disabled={state.busy || credentialId === null} onClick={() => void state.prepare(credentialId!)}>Prepara su Poste</button></div>
    <p className="text-xs text-slate-600">GAIA controlla gli indirizzi e prepara le bozze. Verifica finale e INVIA sul portale Poste.</p>
  </section>;
}
