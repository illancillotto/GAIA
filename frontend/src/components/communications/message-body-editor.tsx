"use client";

import { readBlocks } from "./template-blocks";
import { TemplateEditor } from "./template-editor";
import { TemplatePreview } from "./template-preview";

type Props = { value: string; subject: string; onChange: (body: string) => void; disabled?: boolean; rows?: number };

export function MessageBodyEditor({ value, subject, onChange, disabled, rows = 3 }: Props) {
  if (!readBlocks(value)) return <label className="block min-w-0 text-sm">Testo<textarea rows={rows} disabled={disabled} className="mt-1 w-full rounded-lg border p-2" maxLength={20000} value={value} onChange={(event) => onChange(event.target.value)} /></label>;
  return <div className="min-w-0 space-y-2" aria-label="Messaggio da inviare">
    <details className="rounded-lg border p-3"><summary>Anteprima messaggio</summary><div className="max-h-80 overflow-y-auto" tabIndex={0}><TemplatePreview body={value} subject={subject} /></div></details>
    <details className="rounded-lg border p-3"><summary>Modifica testo e layout</summary><TemplateEditor label="Testo" value={value} subject={subject} disabled={disabled} onChange={onChange} /></details>
  </div>;
}
