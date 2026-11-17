"use client";

import type { ReactNode } from "react";
import { type TemplateBlock, writeBlocks } from "./template-blocks";

export const ICATASTO_TEXT = "Per consultare la propria posizione e gli avvisi di pagamento è disponibile il SERVIZIO ICATASTO:\nAnno di riferimento: {{anno_tributario}}\nCodice utenza servizi online: {{codice_utenza}}\nPIN: {{pin_utenza}}";
const PORTAL_URL = "https://incatasto.servizicapacitas.com/pages/main.aspx?cons=090";
export const CONDITION_LABEL = "Solo con codice utenza e PIN ICATASTO disponibili";

export function icatastoBlocks(text = ICATASTO_TEXT): TemplateBlock[] {
  return [
    { kind: "paragraph", text, condition: "icatasto" },
    { kind: "button", text: "Accedi al SERVIZIO ICATASTO", url: PORTAL_URL, condition: "icatasto" },
  ];
}

export function convertToBlocks(text: string): string {
  const paragraphs = text.split(/(?:\r?\n){2,}/).filter((paragraph) => paragraph.trim());
  const blocks = paragraphs.flatMap((paragraph): TemplateBlock[] => {
    const officePortal = paragraph.includes("SERVIZIO ICATASTO") && ["codice_utenza", "pin_utenza", "url_portale"].every((key) => paragraph.includes(`{{${key}}}`));
    if (officePortal) return icatastoBlocks(paragraph.replace(/\r?\n\{\{url_portale\}\}/, ""));
    return [{ kind: "paragraph", text: paragraph }];
  });
  // Preserve oversized legacy texts for manual editing within the existing block limit.
  return writeBlocks(blocks.length > 0 && blocks.length <= 60 ? blocks : [{ kind: "paragraph", text }]);
}

export function IcatastoInsert({ blocks, onChange }: { blocks: TemplateBlock[]; onChange: (body: string) => void }) {
  return <button type="button" className="btn-secondary" disabled={blocks.length > 58} onClick={() => onChange(writeBlocks([...blocks, ...icatastoBlocks()]))}>+ Servizio ICATASTO</button>;
}

export function BlockCondition({ block, update }: { block: TemplateBlock; update: (changes: Partial<TemplateBlock>) => void }) {
  return <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={block.condition === "icatasto"} onChange={(event) => update({ condition: event.target.checked ? "icatasto" : undefined })} />{CONDITION_LABEL}</label>;
}

export function ConditionalPreview({ block, children }: { block: TemplateBlock; children: ReactNode }) {
  if (!block.condition) return <>{children}</>;
  return <div className="space-y-2 rounded border border-dashed border-slate-300 p-3"><p className="text-xs text-slate-600">{CONDITION_LABEL}. Se manca uno dei due dati, questo blocco non sarà incluso.</p>{children}</div>;
}
