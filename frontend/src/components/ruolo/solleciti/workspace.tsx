"use client";

import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { RuoloModulePage } from "@/components/ruolo/module-page";
import { useSessionBootstrap } from "@/lib/use-session-bootstrap";
import { getTributiReminderBatch, listTributiReminderBatches } from "@/lib/ruolo-api";
import { confirmTributiReminderBatch } from "./client";
import { PostePanel, usePosteLots } from "@/components/ruolo/poste-dispatch/workspace";
import { NoticeExport } from "./document-access";
import { SelectionBar, usePosteSelection } from "./poste-selection";
import { RegenerationPanel } from "./regeneration-panel";
import { YearNoticesPanel } from "./year-notices-panel";
import { useBatchOverview, type Overview } from "./batch-overview";
import { BatchList, dateLabel, statusClass, statusLabel } from "./batch-list";
import { NoticeCards } from "./notice-cards";
import type { NoticeGenerationConfirmationResponse, RuoloTributiReminderBatchResponse } from "@/types/ruolo";
import type { PosteDispatchLotDetail } from "@/types/ruolo-poste-dispatch";

type Tab = "generati" | "poste";

const PAGE_SIZE = 50;

export function SollecitiAccess() {
  const session = useSessionBootstrap();
  if (session.status !== "ready" || !session.token || !session.currentUser) return <p role="status">Verifica accesso...</p>;
  if (!(session.currentUser.role === "super_admin" || session.currentUser.enabled_modules.includes("ruolo")) || !session.grantedSectionKeys.includes("ruolo.tributi.view")) return <p role="alert">Accesso non autorizzato.</p>;
  return <SollecitiWorkspace key={session.token} token={session.token} canEdit={session.grantedSectionKeys.includes("ruolo.tributi.manage_status")} />;
}

const TABS: { key: Tab; label: string }[] = [{ key: "generati", label: "Solleciti generati" }, { key: "poste", label: "Posta Online" }];

function SollecitiWorkspace({ token, canEdit }: { token: string; canEdit: boolean }) {
  // The former Posta Online address opens the same page on its tab.
  const initialTab: Tab = usePathname()?.endsWith("/poste") ? "poste" : "generati";
  const solleciti = useSolleciti(token, canEdit);
  const posteLots = usePosteLots(token);
  const selection = usePosteSelection();
  const [tab, setTab] = useState<Tab>(initialTab);
  function lotCreated(lot: PosteDispatchLotDetail) {
    setTab("poste");
    void posteLots.reload(lot.id);
  }
  return (
    <RuoloModulePage title="Invio solleciti" description="Lotti generati, anteprima degli avvisi e invio con Posta Online." breadcrumb="Invio solleciti" requiredSection="ruolo.tributi.view">
      <div className="space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div role="tablist" aria-label="Invio solleciti" className="flex gap-2">
            {TABS.map((entry) => <button key={entry.key} type="button" role="tab" aria-selected={tab === entry.key} className={tab === entry.key ? "btn-primary" : "btn-secondary"} onClick={() => setTab(entry.key)}>{entry.label}</button>)}
          </div>
          <p className="rounded-full bg-[#eef3ea] px-4 py-2 text-xs text-[#203829]"><span className="font-semibold">Raccomandata A/R online:</span> GAIA prepara le bozze, INVIA lo preme sempre l&apos;operatore su Posta Online.</p>
        </div>
        {!canEdit && <p className="text-sm text-slate-600">Accesso in sola lettura: per creare o rigenerare i PDF chiedi all&apos;amministratore il permesso di gestione Tributi.</p>}
        {tab === "generati"
          ? <GeneratedPanel token={token} canEdit={canEdit} solleciti={solleciti} selection={selection} onLotCreated={lotCreated} />
          : <PostePanel token={token} canEdit={canEdit} posteLots={posteLots} />}
      </div>
    </RuoloModulePage>
  );
}

type GeneratedProps = {
  token: string; canEdit: boolean; solleciti: ReturnType<typeof useSolleciti>;
  selection: ReturnType<typeof usePosteSelection>; onLotCreated: (lot: PosteDispatchLotDetail) => void;
};

function GeneratedPanel({ token, canEdit, solleciti, selection, onLotCreated }: GeneratedProps) {
  const { page, setPage, total, batches, selected, confirmation, loading, busy, error, selectBatch, confirmSelected, reload } = solleciti;
  const overview = useBatchOverview(token, batches.map((batch) => batch.id));
  function regenerated() {
    overview.reload();
    if (selected) void selectBatch(selected.id);
  }
  return <div className="space-y-6">
    {canEdit && <YearNoticesPanel token={token} onFinished={() => { reload(); overview.reload(); }} />}
    {canEdit && <RegenerationPanel token={token} batchId={selected?.id ?? null} onFinished={regenerated} />}
    {error && <div role="alert" className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">{error}</div>}
    {confirmation && <div role="status" className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-900">Lotto confermato. Digest: <code className="break-all">{confirmation.review_digest}</code></div>}
    <div className="grid gap-6 lg:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)]">
      <section className="self-start rounded-[28px] border border-[#d8dfd3] bg-white p-5 shadow-panel lg:sticky lg:top-4 lg:flex lg:max-h-[calc(100vh-2rem)] lg:flex-col">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-lg font-semibold text-slate-900">Lotti generati <span className="text-sm font-normal text-slate-500">{total}</span></h2>
          <Pager page={page} total={total} busy={busy} setPage={setPage} />
        </div>
        <div className="lg:min-h-0 lg:overflow-y-auto"><BatchList loading={loading} batches={batches} selected={selected} busy={busy} selectBatch={selectBatch} overview={overview.overview} selection={canEdit ? selection : null} /></div>
      </section>
      <section className="rounded-[28px] border border-[#d8dfd3] bg-white p-5 shadow-panel">
        <BatchDetail token={token} selected={selected} canEdit={canEdit} busy={busy} confirmSelected={confirmSelected} selection={selection} overview={overview.overview} onRegenerated={overview.reload} />
      </section>
    </div>
    {canEdit && <SelectionBar token={token} selection={selection} onCreated={onLotCreated} />}
  </div>;
}


function Pager({ page, total, busy, setPage }: { page: number; total: number; busy: boolean; setPage: (page: number) => void }) {
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  if (pages === 1) return null;
  return <nav aria-label="Pagine lotti" className="flex items-center gap-2 text-sm text-slate-600">
    <button type="button" className="btn-secondary px-3" aria-label="Precedente" disabled={busy || page === 1} onClick={() => setPage(page - 1)}>‹</button>
    <span>{page} / {pages}</span>
    <button type="button" className="btn-secondary px-3" aria-label="Successiva" disabled={busy || page >= pages} onClick={() => setPage(page + 1)}>›</button>
  </nav>;
}

export function useSolleciti(token: string, canEdit: boolean) {
  const selectionRequest = useRef(0);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [batches, setBatches] = useState<RuoloTributiReminderBatchResponse[]>([]);
  const [selected, setSelected] = useState<RuoloTributiReminderBatchResponse | null>(null);
  const [confirmation, setConfirmation] = useState<NoticeGenerationConfirmationResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [version, setVersion] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    listTributiReminderBatches(token, page, PAGE_SIZE)
      .then((response) => { if (!cancelled) { setBatches(response.items); setTotal(response.total); } })
      .catch((err) => { if (!cancelled) setError(err instanceof Error ? err.message : "Errore caricamento lotti"); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [token, page, version]);

  async function selectBatch(batchId: string) {
    setError(null);
    setConfirmation(null);
    setSelected(null);
    const request = ++selectionRequest.current;
    try {
      const detail = await getTributiReminderBatch(token, batchId);
      if (request === selectionRequest.current) setSelected(detail);
    } catch (err) {
      if (request === selectionRequest.current) setError(err instanceof Error ? err.message : "Errore caricamento lotto");
    }
  }

  async function confirmSelected() {
    if (!selected || !canEdit || busy) return;
    setBusy(true);
    setError(null);
    setConfirmation(null);
    try {
      const result = await confirmTributiReminderBatch(token, selected.id);
      setConfirmation(result);
      setVersion((value) => value + 1);
      setSelected(await getTributiReminderBatch(token, selected.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Conferma non riuscita");
    } finally {
      setBusy(false);
    }
  }

  return { page, setPage, total, batches, selected, confirmation, loading, busy, error, selectBatch, confirmSelected, reload: () => setVersion((value) => value + 1) };
}

type Selection = ReturnType<typeof usePosteSelection>;

function BatchDetail({ selected, canEdit, busy, confirmSelected, token, selection, overview, onRegenerated }: {
  selected: RuoloTributiReminderBatchResponse | null; canEdit: boolean; busy: boolean; confirmSelected: () => Promise<void>; token: string; selection: Selection; overview: Overview; onRegenerated: () => void;
}) {
  return <>{!selected ? <p className="text-sm text-slate-500">Seleziona un lotto per visualizzare i dettagli.</p> : <><div className="flex flex-wrap items-start justify-between gap-4"><div><p className="text-xs uppercase tracking-[0.18em] text-slate-500">Dettaglio lotto</p><h2 className="mt-1 text-2xl font-semibold text-slate-900">{selected.title || selected.id}</h2></div><span className={`rounded-full px-3 py-1 text-sm font-semibold ${statusClass(selected.status)}`}>{statusLabel(selected.status)}</span></div><div className="mt-5 grid grid-cols-2 gap-4 text-sm sm:grid-cols-4"><div><p className="text-slate-500">Avvisi</p><p className="font-semibold">{selected.items_total}</p></div><div><p className="text-slate-500">Generati</p><p className="font-semibold">{selected.items_generated}</p></div><div><p className="text-slate-500">Errori</p><p className="font-semibold">{selected.items_failed}</p></div><div><p className="text-slate-500">Creato</p><p className="font-semibold">{dateLabel(selected.generated_at)}</p></div></div><div className="mt-6 space-y-2"><NoticeCards items={selected.items} token={token} batchId={selected.id} canEdit={canEdit} selection={selection} overview={overview[selected.id]} onRegenerated={onRegenerated} /></div>{canEdit && selected.status === "review_required" && <div className="mt-6 border-t border-slate-200 pt-5"><p className="text-sm text-slate-600">Confermando dichiari di aver verificato destinatari, annualità, artefatti e anomalie del lotto.</p><button type="button" className="btn-primary mt-4" disabled={busy} onClick={() => void confirmSelected()}>{busy ? "Verifica e conferma..." : "Conferma lotto"}</button></div>}{selected.status === "confirmed" && <NoticeExport key={`${selected.id}:${token}`} token={token} batchId={selected.id} canEdit={canEdit} />}</>}</>;
}
