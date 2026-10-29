"use client";

import { BatchBadges, SelectBatchForPoste, type Overview } from "./batch-overview";
import type { usePosteSelection } from "./poste-selection";
import type { RuoloTributiReminderBatchResponse } from "@/types/ruolo";

export function statusLabel(status: string): string {
  if (status === "review_required") return "Bozza da verificare";
  if (status === "confirmed") return "Confermato";
  return status;
}

export function statusClass(status: string): string {
  if (status === "confirmed") return "bg-emerald-50 text-emerald-800";
  if (status === "review_required") return "bg-amber-50 text-amber-900";
  return "bg-slate-100 text-slate-700";
}

export function dateLabel(value: string | null): string {
  return value ? new Intl.DateTimeFormat("it-IT", { dateStyle: "short", timeStyle: "short" }).format(new Date(value)) : "-";
}

type Batch = RuoloTributiReminderBatchResponse;
type Selection = ReturnType<typeof usePosteSelection>;

type RowProps = { batch: Batch; active: boolean; busy: boolean; selectBatch: (id: string) => Promise<void>; overview: Overview; selection: Selection | null };

// Editors pick a whole batch for Posta Online from here, without opening it.
function BatchRow({ batch, active, busy, selectBatch, overview, selection }: RowProps) {
  const title = batch.title || `Lotto ${batch.id.slice(0, 8)}`;
  const items = overview[batch.id] ?? [];
  return <div className="flex items-start gap-3">
    {selection && <SelectBatchForPoste title={title} items={items} selection={selection} />}
    <button disabled={busy} type="button" onClick={() => void selectBatch(batch.id)} className={`min-w-0 flex-1 rounded-2xl border p-4 text-left ${active ? "border-[#1d4e35] bg-[#eef7ef]" : "border-slate-200 hover:border-[#9ab69c]"}`}>
      <div className="flex items-start justify-between gap-3"><span className="font-semibold text-slate-900">{title}</span><span className={`shrink-0 rounded-full px-2 py-1 text-xs font-semibold ${statusClass(batch.status)}`}>{statusLabel(batch.status)}</span></div>
      <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-slate-500"><span>{batch.items_total} avvisi · creato {dateLabel(batch.created_at)}</span><BatchBadges items={items} /></div>
    </button>
  </div>;
}

type ListProps = Omit<RowProps, "batch" | "active"> & { loading: boolean; batches: Batch[]; selected: Batch | null };

export function BatchList({ loading, batches, selected, ...row }: ListProps) {
  if (loading) return <p role="status" className="text-sm text-slate-500">Caricamento lotti...</p>;
  if (batches.length === 0) return <p className="text-sm text-slate-500">Nessun lotto generato.</p>;
  return <div className="space-y-2">{batches.map((batch) => <BatchRow key={batch.id} batch={batch} active={selected?.id === batch.id} {...row} />)}</div>;
}
