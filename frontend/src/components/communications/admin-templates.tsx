"use client";

import { useCallback, useEffect, useState } from "react";
import { communications } from "@/lib/communications-api";
import type { Template } from "@/types/communications";
import { TemplateAuthoring } from "./template-authoring";
import type { TemplateDraft } from "./use-template-catalog";
import { TemplatePreview } from "./template-preview";

const EMPTY: TemplateDraft = { code: "", name: "", channel: "pec", module: "ruolo", subject: "", body: "" };

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
  async function remove(template: Template) {
    if (!window.confirm(`Eliminare il template «${template.name}» (${template.channel.toUpperCase()}, codice ${template.code}, versione ${template.version})?\nNon sarà più disponibile per nuove comunicazioni. I messaggi già creati e lo storico resteranno conservati.`)) return;
    setStatus({ busy: true, error: "" });
    try {
      await communications(token, `/templates/${template.id}`, { confirmed: true }, "DELETE");
      await reload();
      setStatus({ busy: false, error: "" });
    } catch (error) { setStatus({ busy: false, error: error instanceof Error ? error.message : "Eliminazione fallita" }); }
  }
  return <section className="space-y-4 rounded-2xl border bg-white p-5"><h2 className="text-lg font-semibold">Template versionati</h2>
    <p className="text-sm">Le proposte iniziali sono bozze. Approvare solo dopo la verifica dell&apos;ufficio competente. Ogni modifica crea una nuova versione; i testi già usati restano conservati.</p>
    {status.error && <p role="alert" className="text-rose-800">{status.error}</p>}
    <ul className="space-y-3">{templates.map((template) => <li className="rounded-lg border p-3" key={template.id}><p>{template.name} · {template.channel} · v{template.version} · {template.status}</p><p className="text-sm">{template.subject}</p><details className="mt-2"><summary>Visualizza template</summary><TemplatePreview body={template.body} subject={template.subject} /></details><button className="btn-secondary mt-2" disabled={status.busy} onClick={() => setForm({ code: template.code, name: template.name, channel: template.channel, module: "ruolo", subject: template.subject, body: template.body })}>Crea nuova versione</button>{template.status === "draft" && <button className="btn-primary ml-2" disabled={status.busy} onClick={() => void command(template)}>Approva questa versione</button>}<button className="btn-secondary ml-2 mt-2 text-rose-800" type="button" aria-label={`Elimina ${template.name}, ${template.channel}, versione ${template.version}`} disabled={status.busy} onClick={() => void remove(template)}>Elimina</button></li>)}</ul>
    <TemplateAuthoring token={token} disabled={status.busy} form={form} onChange={setForm} />
    <button className="btn-primary" disabled={status.busy} onClick={() => void command()}>Salva nuova versione bozza</button>
  </section>;
}
