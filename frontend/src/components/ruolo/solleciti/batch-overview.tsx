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
    {pec > 0 && <span className="rounded-full bg-emerald-50 px-2 py-1 text-xs font-semibold text-emerald-800" title="Spedizione PEC rilevata in inCASS per l'avviso">{items.length > 1 ? `Inviato via PEC (${pec})` : "Inviato via PEC"}</span>}
    {failed > 0 && <span className="rounded-full bg-rose-50 px-2 py-1 text-xs font-semibold text-rose-800">{items.length > 1 ? `PDF non generato (${failed})` : "PDF non generato"}</span>}
  </>;
}

type SelectProps = { title: string; items: BatchOverviewItem[]; selection: ReturnType<typeof usePosteSelection> };

export function SelectBatchForPoste({ title, items, selection }: SelectProps) {
  const sendable = items.filter((item) => item.sendable).map((item) => ({ id: item.item_id, label: item.label }));
  if (sendable.length === 0) return <span className="w-4 shrink-0" />;
  return <input type="checkbox" className="mt-5 shrink-0" aria-label={`Seleziona per Posta Online: ${title}`} checked={sendable.every((entry) => selection.isSelected(entry.id))} onChange={() => selection.toggleAll(sendable)} />;
}
