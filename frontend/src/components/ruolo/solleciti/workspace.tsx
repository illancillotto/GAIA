"use client";

import { useEffect, useRef, useState } from "react";

import { RuoloModulePage } from "@/components/ruolo/module-page";
import { useSessionBootstrap } from "@/lib/use-session-bootstrap";
import { getTributiReminderBatch, listTributiReminderBatches } from "@/lib/ruolo-api";
import { confirmTributiReminderBatch } from "./client";
import type { NoticeGenerationConfirmationResponse, RuoloTributiReminderBatchResponse } from "@/types/ruolo";

function statusLabel(status: string): string {
  if (status === "review_required") return "Bozza da verificare";
  if (status === "confirmed") return "Confermato";
  return status;
}

function statusClass(status: string): string {
  if (status === "confirmed") return "bg-emerald-50 text-emerald-800";
  if (status === "review_required") return "bg-amber-50 text-amber-900";
  return "bg-slate-100 text-slate-700";
}

function dateLabel(value: string | null): string {
  return value ? new Intl.DateTimeFormat("it-IT", { dateStyle: "short", timeStyle: "short" }).format(new Date(value)) : "-";
}

export function SollecitiAccess() {
  const session = useSessionBootstrap();
  if (session.status !== "ready" || !session.token || !session.currentUser) return <p role="status">Verifica accesso...</p>;
  if (!(session.currentUser.role === "super_admin" || session.currentUser.enabled_modules.includes("ruolo")) || !session.grantedSectionKeys.includes("ruolo.tributi.view")) return <p role="alert">Accesso non autorizzato.</p>;
  return <SollecitiWorkspace key={session.token} token={session.token} canEdit={session.grantedSectionKeys.includes("ruolo.tributi.manage_status")} />;
}

function SollecitiWorkspace({ token, canEdit }: { token: string; canEdit: boolean }) {
  const { page, setPage, total, batches, selected, confirmation, loading, busy, error, selectBatch, confirmSelected } = useSolleciti(token, canEdit);
  return (
    <RuoloModulePage title="Solleciti Tributi" description="Bozze, conferma e storico dei lotti generati." breadcrumb="Solleciti" requiredSection="ruolo.tributi.view">
      <div className="space-y-6">
        {!canEdit && <p>Accesso in sola lettura.</p>}
        <nav aria-label="Pagine lotti" className="flex gap-3">
          <button className="btn-secondary" disabled={busy || page === 1} onClick={() => setPage(page - 1)}>Precedente</button>
          <span>Pagina {page} | {total} lotti</span>
          <button className="btn-secondary" disabled={busy || page * 50 >= total} onClick={() => setPage(page + 1)}>Successiva</button>
        </nav>
        <section className="rounded-[28px] border border-[#d8dfd3] bg-[#203829] p-7 text-white shadow-panel">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[#cfe2b8]">Registro generazione</p>
          <h1 className="mt-2 text-3xl font-semibold">Lotti 2022/2023</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-white/75">Le bozze restano private. La conferma ricontrolla revisione, artefatti e identità prima del successivo export.</p>
        </section>
        {error && <div role="alert" className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">{error}</div>}
        {confirmation && <div role="status" className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-900">Lotto confermato. Digest: <code className="break-all">{confirmation.review_digest}</code></div>}
        <div className="grid gap-6 lg:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)]">
          <section className="rounded-[28px] border border-[#d8dfd3] bg-white p-5 shadow-panel">
            <div className="mb-4 flex items-center justify-between"><h2 className="text-lg font-semibold text-slate-900">Lotti generati</h2><span className="text-sm text-slate-500">{batches.length}</span></div>
            <BatchList loading={loading} batches={batches} selected={selected} busy={busy} selectBatch={selectBatch} />
          </section>
          <section className="rounded-[28px] border border-[#d8dfd3] bg-white p-5 shadow-panel">
            <BatchDetail selected={selected} canEdit={canEdit} busy={busy} confirmSelected={confirmSelected} />
          </section>
        </div>
      </div>
    </RuoloModulePage>
  );
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

  async function loadBatches(accessToken: string) {
    const response = await listTributiReminderBatches(accessToken, page, 50);
    setBatches(response.items);
    setTotal(response.total);
  }

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    listTributiReminderBatches(token, page, 50)
      .then((response) => { if (!cancelled) { setBatches(response.items); setTotal(response.total); } })
      .catch((err) => { if (!cancelled) setError(err instanceof Error ? err.message : "Errore caricamento lotti"); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [token, page]);

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
      await loadBatches(token);
      setSelected(await getTributiReminderBatch(token, selected.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Conferma non riuscita");
    } finally {
      setBusy(false);
    }
  }

  return { page, setPage, total, batches, selected, confirmation, loading, busy, error, selectBatch, confirmSelected };
}

function NoticeItem({ item }: { item: RuoloTributiReminderBatchResponse["items"][number] }) {
  return (<div className="rounded-2xl border border-slate-200 p-4"><div className="flex flex-wrap items-center justify-between gap-2"><span className="font-semibold text-slate-900">{item.display_name || item.codice_fiscale}</span><span className="text-xs font-semibold uppercase text-slate-500">{item.status}</span></div><p className="mt-1 text-sm text-slate-600">{item.codice_fiscale} · annualità {(item.years_json ?? []).join(", ") || "-"}</p>{typeof item.payload_json?.notice_identity_key === "string" && <p className="mt-2 break-all text-xs text-slate-500">Identità: {item.payload_json.notice_identity_key}</p>}</div>);
}

function BatchDetail({ selected, canEdit, busy, confirmSelected }: {
  selected: RuoloTributiReminderBatchResponse | null; canEdit: boolean; busy: boolean; confirmSelected: () => Promise<void>;
}) {
  return <>{!selected ? <p className="text-sm text-slate-500">Seleziona un lotto per visualizzare i dettagli.</p> : <><div className="flex flex-wrap items-start justify-between gap-4"><div><p className="text-xs uppercase tracking-[0.18em] text-slate-500">Dettaglio lotto</p><h2 className="mt-1 text-2xl font-semibold text-slate-900">{selected.title || selected.id}</h2></div><span className={`rounded-full px-3 py-1 text-sm font-semibold ${statusClass(selected.status)}`}>{statusLabel(selected.status)}</span></div><div className="mt-5 grid grid-cols-2 gap-4 text-sm sm:grid-cols-4"><div><p className="text-slate-500">Avvisi</p><p className="font-semibold">{selected.items_total}</p></div><div><p className="text-slate-500">Generati</p><p className="font-semibold">{selected.items_generated}</p></div><div><p className="text-slate-500">Errori</p><p className="font-semibold">{selected.items_failed}</p></div><div><p className="text-slate-500">Creato</p><p className="font-semibold">{dateLabel(selected.generated_at)}</p></div></div><div className="mt-6 space-y-2">{selected.items.map((item) => <NoticeItem key={item.id} item={item} />)}</div>{canEdit && selected.status === "review_required" && <div className="mt-6 border-t border-slate-200 pt-5"><p className="text-sm text-slate-600">Confermando dichiari di aver verificato destinatari, annualità, artefatti e anomalie del lotto.</p><button type="button" className="btn-primary mt-4" disabled={busy} onClick={() => void confirmSelected()}>{busy ? "Verifica e conferma..." : "Conferma lotto"}</button></div>}{selected.status === "confirmed" && <p className="mt-6 border-t border-emerald-100 pt-5 text-sm text-emerald-800">Lotto confermato. L&apos;export definitivo sarà disponibile in una fase successiva.</p>}</>}</>;
}

function BatchList({ loading, batches, selected, busy, selectBatch }: {
  loading: boolean; batches: RuoloTributiReminderBatchResponse[]; selected: RuoloTributiReminderBatchResponse | null;
  busy: boolean; selectBatch: (id: string) => Promise<void>;
}) {
  return <>{loading ? <p role="status" className="text-sm text-slate-500">Caricamento lotti...</p> : batches.length === 0 ? <p className="text-sm text-slate-500">Nessun lotto generato.</p> : <div className="space-y-2">{batches.map((batch) => <button key={batch.id} disabled={busy} type="button" onClick={() => void selectBatch(batch.id)} className={`w-full rounded-2xl border p-4 text-left ${selected?.id === batch.id ? "border-[#1d4e35] bg-[#eef7ef]" : "border-slate-200 hover:border-[#9ab69c]"}`}><div className="flex items-start justify-between gap-3"><span className="font-semibold text-slate-900">{batch.title || `Lotto ${batch.id.slice(0, 8)}`}</span><span className={`rounded-full px-2 py-1 text-xs font-semibold ${statusClass(batch.status)}`}>{statusLabel(batch.status)}</span></div><p className="mt-2 text-xs text-slate-500">{batch.items_total} avvisi · creato {dateLabel(batch.created_at)}</p></button>)}</div>}</>;
}
