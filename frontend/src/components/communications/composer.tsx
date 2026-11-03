"use client";

import { useCallback, useEffect, useState, type CSSProperties } from "react";
import { communications, receiptBlob } from "@/lib/communications-api";
import type { Account, Attachment, CommEvent, Communication, Receipt } from "@/types/communications";
import { useComposer } from "./use-composer";
import { ComposerForm } from "./composer-form";
import { CommunicationPdfViewer } from "./pdf-viewer";

type Props = { token: string; message: Communication; accounts: Account[]; canEdit: boolean; onChange: (message: Communication) => void };

export function CommunicationComposer({ token, message, accounts, canEdit, onChange }: Props) {
  const [ratio, setRatio] = useState(55);
  const controller = useComposer({ token, message, canEdit, onChange });
  const style = { "--composition-columns": `${ratio}fr ${100 - ratio}fr` } as CSSProperties;
  return <section aria-label="Compositore comunicazione" className="space-y-4">
    <div className="flex flex-wrap justify-between gap-3"><h2 className="text-xl font-semibold">Avviso {message.notice_number} · {message.channel.toUpperCase()}</h2><span role="status">{message.state} · revisione {message.version}</span></div>
    <label className="hidden items-center gap-3 text-sm lg:flex">Larghezza documento
      <input aria-label="Larghezza documento" type="range" min="35" max="70" value={ratio} onChange={(event) => setRatio(Number(event.target.value))} /> {ratio}%
    </label>
    <div style={style} className="grid items-start gap-4 lg:grid-cols-[var(--composition-columns)]">
      <div className="min-w-0 space-y-4">{message.attachments.map((part) => <AttachmentPreview key={`${part.id}:${message.version}`} token={token} message={message} part={part} onRender={controller.onRender} canReview={canEdit} />)}</div>
      <ComposerForm message={message} accounts={accounts} canEdit={canEdit} controller={controller} />
    </div>
    <CommunicationHistory key={message.state} token={token} id={message.id} />
  </section>;
}

function AttachmentPreview({ token, message, part, onRender, canReview }: { token: string; message: Communication; part: Attachment; onRender: (id: string, ok: boolean) => void; canReview: boolean }) {
  const callback = useCallback((ok: boolean) => onRender(part.id, ok), [part.id, onRender]);
  return <CommunicationPdfViewer token={token} messageId={message.id} version={message.version} part={part} onRendered={callback} canReview={canReview} pixelBudget={64_000_000 / message.attachments.length} />;
}

function CommunicationHistory({ token, id }: { token: string; id: string }) {
  const [history, setHistory] = useState<{ events: CommEvent[]; receipts: Receipt[]; error: string }>({ events: [], receipts: [], error: "" });
  useEffect(() => {
    let disposed = false;
    Promise.all([communications<CommEvent[]>(token, `/messages/${id}/events`), communications<Receipt[]>(token, `/messages/${id}/receipts`)])
      .then(([events, receipts]) => { if (!disposed) setHistory({ events, receipts, error: "" }); })
      .catch((error: Error) => { if (!disposed) setHistory((current) => ({ ...current, error: error.message })); });
    return () => { disposed = true; };
  }, [token, id]);
  async function download(receipt: Receipt) {
    try {
      const url = URL.createObjectURL(await receiptBlob(token, id, receipt.id));
      const link = document.createElement("a"); link.href = url; link.download = `${receipt.id}.eml`; link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (error) { setHistory((current) => ({ ...current, error: error instanceof Error ? error.message : "Download fallito" })); }
  }
  return <section aria-label="Storico comunicazione" className="rounded-2xl border bg-white p-4">
    <h3 className="font-semibold">Eventi ed evidenze tecniche</h3>
    {history.error && <p role="alert">{history.error}</p>}
    <ol className="my-3 max-h-64 overflow-auto text-sm">{history.events.map((event) => <li key={event.id}>{event.created_at} · {event.kind} · {JSON.stringify(event.detail)}</li>)}</ol>
    {history.receipts.map((receipt) => <p key={receipt.id} className="my-2 break-all text-sm">{receipt.kind} · {receipt.classification} · SHA-256 {receipt.sha256} <button className="btn-secondary" onClick={() => void download(receipt)}>Scarica originale EML</button></p>)}
  </section>;
}
