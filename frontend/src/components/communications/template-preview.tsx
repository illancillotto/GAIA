"use client";

import { readBlocks, safeLink, type TemplateBlock } from "./template-blocks";

export function TemplatePreview({ body, subject }: { body: string; subject?: string }) {
  const blocks = readBlocks(body);
  return <section aria-label="Anteprima messaggio" className="min-w-0 space-y-3 rounded-xl border bg-slate-50 p-4">
    <h3 className="font-semibold">Anteprima messaggio</h3>
    {subject && <p className="break-words border-b pb-3 text-sm"><strong>Oggetto: </strong>{subject}</p>}
    <div className="space-y-4 break-words rounded-lg bg-white p-5 text-slate-800">
      {blocks ? blocks.map((block, index) => <PreviewBlock key={index} block={block} />) : <p className="whitespace-pre-wrap">{body}</p>}
    </div>
    <p className="text-xs text-slate-600">I campi tra doppie parentesi verranno compilati con i dati dell’avviso. Il messaggio include anche una versione testuale.</p>
  </section>;
}

function PreviewBlock({ block }: { block: TemplateBlock }) {
  if (block.kind === "logo") return <p><img src="/communications/official-logo.png" width={180} height={90} style={{ objectFit: "contain", height: "auto" }} alt="Logo Consorzio di Bonifica dell’Oristanese" /></p>; // eslint-disable-line @next/next/no-img-element -- Same official PNG embedded inline in email, with no Next image dependency.
  if (block.kind === "title") return <h2 className="whitespace-pre-wrap text-xl font-semibold">{block.text}</h2>;
  if (block.kind === "list") return <ul className="list-disc space-y-1 pl-5">{(block.text ?? "").split("\n").map((line, index) => <li key={index}>{line}</li>)}</ul>;
  if (block.kind === "link" || block.kind === "button") {
    if (!safeLink(block.url ?? "")) return <p className="text-rose-800">{block.text} · URL HTTPS da completare</p>;
    return <p><a href={block.url} target="_blank" rel="noopener noreferrer" className={block.kind === "button" ? "inline-block rounded-lg bg-[#245537] px-5 py-3 text-white" : "text-[#245537] underline"}>{block.text}</a></p>;
  }
  return <p className="whitespace-pre-wrap">{block.text}</p>;
}
