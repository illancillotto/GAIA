"use client";

import { GeneratedNoticePreview, NoticePreview } from "./document-access";
import { FailedNotice } from "./failed-notice";
import { SelectForPoste, canSendToPoste, type usePosteSelection } from "./poste-selection";
import type { BatchOverviewItem } from "@/lib/ruolo-batch-overview-api";
import type { RuoloTributiReminderBatchItemResponse } from "@/types/ruolo";
import { PosteHistory } from "./poste-history";

// Previews open with the batch, up to this many: a large batch would download every PDF at once.
const OPEN_PREVIEWS = 5;

type Item = RuoloTributiReminderBatchItemResponse;
type Shared = { token: string; batchId: string; canEdit: boolean; onRegenerated: () => void };
type CardProps = Shared & { item: Item; selection: ReturnType<typeof usePosteSelection>; previewOpen: boolean; overview: BatchOverviewItem | undefined };

function NoticeDocument({ item, token, batchId, canEdit, onRegenerated, previewOpen }: Omit<CardProps, "selection" | "overview">) {
  if (item.status === "failed") return <FailedNotice key={`${item.id}:${token}`} token={token} itemId={item.id} detail={item.error_detail} canEdit={canEdit} onRegenerated={onRegenerated} />;
  if (item.download_url && canSendToPoste(item)) return <GeneratedNoticePreview key={`${item.id}:${token}`} token={token} url={item.download_url} defaultOpen={previewOpen} />;
  return <NoticePreview key={`${batchId}:${item.id}:${token}`} token={token} batchId={batchId} itemId={item.id} status={item.status} />;
}

function NoticeCard({ selection, overview, item, canEdit, ...props }: CardProps) {
  const identity = item.payload_json?.notice_identity_key;
  return <div className="rounded-2xl border border-slate-200 p-4">
    <div className="flex flex-wrap items-center justify-between gap-2">
      <span className="font-semibold text-slate-900">{item.display_name || item.codice_fiscale}</span>
      <span className="flex items-center gap-2">
        {overview?.pec_sent && <span className="rounded-full bg-emerald-50 px-2 py-1 text-xs font-semibold text-emerald-800" title="Spedizione PEC rilevata in inCASS per l'avviso">Avviso già inviato via PEC</span>}
        <span className="text-xs font-semibold uppercase text-slate-500">{item.status}</span>
      </span>
    </div>
    <p className="mt-1 text-sm text-slate-600">{item.codice_fiscale} · annualità {(item.years_json ?? []).join(", ") || "-"}</p>
    {typeof identity === "string" && <p className="mt-2 break-all text-xs text-slate-500">Identità: {identity}</p>}
    <PosteHistory dispatches={overview?.poste_dispatches} />
    <SelectForPoste item={item} canEdit={canEdit} checked={selection.isSelected(item.id)} onToggle={selection.toggle} />
    <NoticeDocument {...props} item={item} canEdit={canEdit} />
  </div>;
}

type CardsProps = Shared & { items: Item[]; selection: CardProps["selection"]; overview: BatchOverviewItem[] | undefined };

export function NoticeCards({ items, overview, ...shared }: CardsProps) {
  const summaries = new Map((overview ?? []).map((entry) => [entry.item_id, entry]));
  return <>{items.map((item, index) => <NoticeCard key={item.id} item={item} previewOpen={index < OPEN_PREVIEWS} overview={summaries.get(item.id)} {...shared} />)}</>;
}
