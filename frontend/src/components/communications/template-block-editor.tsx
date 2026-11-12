"use client";

import { BLOCK_LABELS, safeLink, type TemplateBlock } from "./template-blocks";

type Props = {
  block: TemplateBlock; index: number; count: number;
  update: (changes: Partial<TemplateBlock>) => void;
  move: (step: number) => void; remove: () => void;
  select: (start: number, end: number) => void;
};

export function TemplateBlockEditor({ block, index, count, update, move, remove, select }: Props) {
  return <div className="space-y-2 rounded-lg border p-3">
    <div className="flex flex-wrap items-center justify-between gap-2"><strong className="text-sm">{index + 1}. {BLOCK_LABELS[block.kind]}</strong><div className="flex gap-2">
      <button type="button" className="btn-secondary" aria-label={`Sposta su blocco ${index + 1}`} disabled={index === 0} onClick={() => move(-1)}>↑</button>
      <button type="button" className="btn-secondary" aria-label={`Sposta giù blocco ${index + 1}`} disabled={index === count - 1} onClick={() => move(1)}>↓</button>
      <button type="button" className="btn-secondary" aria-label={`Rimuovi blocco ${index + 1}`} disabled={count === 1} onClick={remove}>Rimuovi</button>
    </div></div>
    {block.kind === "logo" ? <p className="text-sm">Logo ufficiale del Consorzio, incorporato nel messaggio.</p> : <label className="block text-sm">{block.kind === "list" ? "Voci, una per riga" : "Testo"}<textarea aria-label={`Testo blocco ${index + 1}`} className="mt-1 w-full rounded border p-2" value={block.text} onSelect={(event) => select(event.currentTarget.selectionStart, event.currentTarget.selectionEnd)} onChange={(event) => update({ text: event.target.value })} /></label>}
    {(block.kind === "link" || block.kind === "button") && <label className="block text-sm">Destinazione HTTPS<input aria-label={`URL blocco ${index + 1}`} className="mt-1 w-full rounded border p-2" type="url" value={block.url} onChange={(event) => update({ url: event.target.value })} />{!safeLink(block.url!) && <span className="text-rose-800">Inserisci un URL HTTPS completo, senza variabili.</span>}</label>}
  </div>;
}
