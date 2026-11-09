"use client";

import { useCallback, useEffect, useState } from "react";
import { communications } from "@/lib/communications-api";
import type { Template } from "@/types/communications";
import { TemplateCatalog } from "./template-catalog";

const EMPTY = { code: "", name: "", channel: "pec", module: "ruolo", subject: "", body: "" };

export function TemplateAdministration({ token }: { token: string }) {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [form, setForm] = useState(EMPTY);
  const [status, setStatus] = useState({ busy: false, error: "" });
  const reload = useCallback(async () => setTemplates(await communications<Template[]>(token, "/admin/templates")), [token]);
  useEffect(() => { void reload().catch((error: Error) => setStatus({ busy: false, error: error.message })); }, [reload]);
  async function command(template?: Template) {
    setStatus({ busy: true, error: "" });
    try {
      await communications(token, template ? `/templates/${template.id}/approve` : "/templates", template ? {} : form);
      await reload(); setForm(EMPTY); setStatus({ busy: false, error: "" });
    } catch (error) { setStatus({ busy: false, error: error instanceof Error ? error.message : "Operazione fallita" }); }
  }
  return <section className="space-y-4 rounded-2xl border bg-white p-5"><h2 className="text-lg font-semibold">Template versionati</h2>
    <p className="text-sm">Le proposte iniziali sono bozze. Approvare solo dopo la verifica dell&apos;ufficio competente. Ogni modifica crea una nuova versione; i testi già usati restano conservati.</p>
    {status.error && <p role="alert" className="text-rose-800">{status.error}</p>}
    <ul className="space-y-3">{templates.map((template) => <li className="rounded-lg border p-3" key={template.id}><p>{template.name} · {template.channel} · v{template.version} · {template.status}</p><p className="text-sm">{template.subject}</p><pre className="whitespace-pre-wrap text-sm">{template.body}</pre><button className="btn-secondary mt-2" disabled={status.busy} onClick={() => setForm({ code: template.code, name: template.name, channel: template.channel, module: "ruolo", subject: template.subject, body: template.body })}>Crea nuova versione</button>{template.status === "draft" && <button className="btn-primary ml-2" disabled={status.busy} onClick={() => void command(template)}>Approva questa versione</button>}</li>)}</ul>
    <fieldset disabled={status.busy} className="grid gap-3 md:grid-cols-2">
      {(["code", "name", "subject"] as const).map((key) => <label key={key}>{key === "code" ? "Codice template" : key === "name" ? "Nome template" : "Oggetto template"}<input className="block w-full rounded border p-2" value={form[key]} onChange={(event) => setForm({ ...form, [key]: event.target.value })} /></label>)}
      <label>Canale template<select className="block rounded border p-2" value={form.channel} onChange={(event) => setForm({ ...form, channel: event.target.value })}><option value="pec">PEC</option><option value="email">Email</option></select></label>
      <label className="md:col-span-2">Corpo template<textarea className="block min-h-40 w-full rounded border p-2" value={form.body} onChange={(event) => setForm({ ...form, body: event.target.value })} /></label>
    </fieldset>
    <TemplateCatalog token={token} disabled={status.busy} onSelect={setForm} />
    <button className="btn-primary" disabled={status.busy} onClick={() => void command()}>Salva nuova versione bozza</button>
  </section>;
}
