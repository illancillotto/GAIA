"use client";

import { useEffect, useState } from "react";

import { getBatchOverview, type BatchOverviewItem } from "@/lib/ruolo-batch-overview-api";
import type { usePosteSelection } from "./poste-selection";

export type Overview = Record<string, BatchOverviewItem[]>;

// Without the summary the list still works: it only loses checkboxes and badges.
export function useBatchOverview(token: string, batchIds: string[]) {
  const [overview, setOverview] = useState<Overview>({});
  const [version, setVersion] = useState(0);
  const key = batchIds.join(",");
  useEffect(() => {
    if (!key) return;
    let cancelled = false;
    getBatchOverview(token, key.split(","))
      .then((rows) => { if (!cancelled) setOverview(Object.fromEntries(rows.map((row) => [row.batch_id, row.items]))); })
      .catch(() => { if (!cancelled) setOverview({}); });
    return () => { cancelled = true; };
  }, [token, key, version]);
  return { overview, reload: () => setVersion((value) => value + 1) };
}

export function BatchBadges({ items }: { items: BatchOverviewItem[] }) {
  const pec = items.filter((item) => item.pec_sent).length;
  const failed = items.filter((item) => item.status === "failed").length;
  return <>
    {pec > 0 && <span className="rounded-full bg-emerald-50 px-2 py-1 text-xs font-semibold text-emerald-800" title="Spedizione PEC rilevata in inCASS per l'avviso">Inviato via PEC ({pec})</span>}
    {failed > 0 && <span className="rounded-full bg-rose-50 px-2 py-1 text-xs font-semibold text-rose-800">PDF non generato ({failed})</span>}
  </>;
}

type SelectProps = { title: string; items: BatchOverviewItem[]; selection: ReturnType<typeof usePosteSelection> };

export function SelectBatchForPoste({ title, items, selection }: SelectProps) {
  const sendable = items.filter((item) => item.sendable).map((item) => ({ id: item.item_id, label: item.label }));
  if (sendable.length === 0) return <span className="w-4 shrink-0" />;
  return <input type="checkbox" className="mt-5 shrink-0" aria-label={`Seleziona per Posta Online: ${title}`} checked={sendable.every((entry) => selection.isSelected(entry.id))} onChange={() => selection.toggleAll(sendable)} />;
}

const SHOWN_NOTICES = 3;
const euro = new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR" });

// Each notice of the batch at a glance: number, year, amount printed on it, PEC already sent.
export function BatchNotices({ items }: { items: BatchOverviewItem[] }) {
  if (items.length === 0) return null;
  const hidden = items.length - SHOWN_NOTICES;
  return <ul className="mt-2 space-y-1 text-xs text-slate-600">
    {items.slice(0, SHOWN_NOTICES).map((item) => <li key={item.item_id} className="flex flex-wrap items-center gap-x-2 gap-y-1">
      <span className="font-mono text-slate-800">{item.notice_number ?? "senza numero"}</span>
      {item.years.length > 0 && <span>{item.years.join(", ")}</span>}
      <span className="font-semibold text-slate-900">{euro.format(item.amount)}</span>
      {item.pec_sent && <span className="rounded-full bg-emerald-50 px-2 py-0.5 font-semibold text-emerald-800" title="Spedizione PEC rilevata in inCASS per l'avviso">Inviato via PEC</span>}
      {item.status === "failed" && <span className="rounded-full bg-rose-50 px-2 py-0.5 font-semibold text-rose-800">PDF non generato</span>}
    </li>)}
    {hidden > 0 && <li>e altri {hidden} avvisi</li>}
  </ul>;
}
