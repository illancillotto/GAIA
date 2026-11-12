"use client";

import { useState } from "react";
import { TemplateCatalog } from "./template-catalog";
import { TemplateEditor } from "./template-editor";
import type { TemplateDraft } from "./use-template-catalog";

type Props = { token: string; disabled: boolean; form: TemplateDraft; onChange: (draft: TemplateDraft) => void };

export function TemplateAuthoring({ token, disabled, form, onChange }: Props) {
  const [variables, setVariables] = useState<Record<string, string>>({});
  return <>
    <fieldset disabled={disabled} className="grid gap-3 md:grid-cols-2">
      {(["code", "name", "subject"] as const).map((key) => <label key={key}>{key === "code" ? "Codice template" : key === "name" ? "Nome template" : "Oggetto template"}<input className="block w-full rounded border p-2" value={form[key]} onChange={(event) => onChange({ ...form, [key]: event.target.value })} /></label>)}
      <label>Canale template<select className="block rounded border p-2" value={form.channel} onChange={(event) => onChange({ ...form, channel: event.target.value as TemplateDraft["channel"] })}><option value="pec">PEC</option><option value="email">Email</option></select></label>
      <div className="min-w-0 md:col-span-2"><TemplateEditor value={form.body} subject={form.subject} variables={variables} onChange={(body) => onChange({ ...form, body })} /></div>
    </fieldset>
    <TemplateCatalog token={token} disabled={disabled} onSelect={onChange} onVariables={setVariables} />
  </>;
}
