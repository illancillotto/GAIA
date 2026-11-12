"use client";
import { SourcePreviewActions } from "./source-preview-actions";
import { useTemplateComposition } from "./use-template-composition";
import { useSourceRepair } from "./use-source-repair";
import type { Candidate, Channel } from "@/types/communications";
import type { useCommunicationsWorkspace } from "./use-workspace";
type Workspace = ReturnType<typeof useCommunicationsWorkspace>;

export function CandidateFilters({ workspace }: { workspace: Workspace }) {
  const { filters, setFilters, setPage, data, status, refresh } = workspace;
  return <div className="min-w-0 space-y-3 rounded-2xl border bg-white p-3 xl:col-span-2"><div className="flex flex-wrap items-end gap-3">
      <label>Cerca nominativo, CF o avviso<input className="block rounded-lg border p-2" value={filters.q} onChange={(event) => { setPage(1); setFilters({ ...filters, q: event.target.value }); }} /></label>
      {(["has_pec", "has_email"] as const).map((key) => <label key={key}>{key === "has_pec" ? "Presenza PEC" : "Presenza email"}<select className="block rounded-lg border p-2" value={filters[key]} onChange={(event) => { setPage(1); setFilters({ ...filters, [key]: event.target.value }); }}><option value="">Tutti</option><option value="true">Presente</option><option value="false">Assente</option></select></label>)}
      <button className="btn-secondary" disabled={status.busy} onClick={() => void refresh()}>Aggiorna stati</button>
      </div><details><summary className="cursor-pointer text-sm font-medium">Altri filtri · stato, account, date e lotto</summary><div className="mt-3 flex flex-wrap items-end gap-3">
      <label>Recapito<select className="block rounded-lg border p-2" value={filters.has_contact} onChange={(event) => { setPage(1); setFilters({ ...filters, has_contact: event.target.value }); }}><option value="">Tutti</option><option value="true">Presente</option><option value="false">Assente</option></select></label>
      <label>Stato<select className="block rounded-lg border p-2" value={filters.state} onChange={(event) => { setPage(1); setFilters({ ...filters, state: event.target.value }); }}><option value="">Tutti</option>{["draft", "ready", "approved", "queued", "sending", "submitted", "accepted", "delivered", "not_delivered", "uncertain", "failed", "cancelled"].map((value) => <option key={value}>{value}</option>)}</select></label>
      <label>Account<select className="block rounded-lg border p-2" value={filters.account_id} onChange={(event) => { setPage(1); setFilters({ ...filters, account_id: event.target.value }); }}><option value="">Tutti</option>{data.accounts.map((account) => <option key={account.id} value={account.id}>{account.name}</option>)}</select></label>
      <label>Dal<input className="block rounded-lg border p-2" type="date" value={filters.date_from} onChange={(event) => { setPage(1); setFilters({ ...filters, date_from: event.target.value }); }} /></label>
      <label>Al<input className="block rounded-lg border p-2" type="date" value={filters.date_to} onChange={(event) => { setPage(1); setFilters({ ...filters, date_to: event.target.value }); }} /></label>
      <label>Lotto (UUID)<input className="block rounded border p-2" value={filters.batch_id} onChange={(event) => { setPage(1); setFilters({ ...filters, batch_id: event.target.value }); }} /></label>
      <label>Pagamento<select className="block rounded border p-2" value={filters.payment_state} onChange={(event) => { setPage(1); setFilters({ ...filters, payment_state: event.target.value }); }}><option value="">Tutti</option>{["unpaid", "partial", "paid"].map((value) => <option key={value}>{value}</option>)}</select></label>
      <label>Notifica<select className="block rounded border p-2" value={filters.notification_state} onChange={(event) => { setPage(1); setFilters({ ...filters, notification_state: event.target.value }); }}><option value="">Tutte</option>{["nessuna_evidenza", "invio_in_corso", "tentativo_senza_notifica", "perfezionata", "da_verificare"].map((value) => <option key={value}>{value}</option>)}</select></label>
      </div></details>
    </div>;
}

export function CandidateTable({ workspace, channel, canEdit }: { workspace: Workspace; channel: Channel; canEdit: boolean }) {
  const { data, page, setPage } = workspace;
  return <section aria-label="Elenco avvisi" className="min-w-0 space-y-3 xl:sticky xl:top-4"><div className="max-h-[70vh] overflow-auto rounded-2xl border bg-white"><table className="w-full table-fixed text-left text-xs"><caption className="p-3 text-left"><strong className="block text-sm">Solleciti 2021 · {data.total} risultati</strong>Clicca un avviso per aprire composizione e PDF. L&apos;eleggibilità viene ricontrollata alla composizione e all&apos;invio.</caption><thead className="sticky top-0 z-20 bg-white"><tr><th className="w-9 p-2"><span className="sr-only">Selezione</span></th><th className="w-[40%] p-2">Avviso / lotto</th><th className="p-2">Contribuente / recapito</th></tr></thead><tbody>{data.items.map((item) => <CandidateRow key={item.id} workspace={workspace} item={item} channel={channel} canEdit={canEdit} />)}</tbody></table></div>
    <nav aria-label="Paginazione candidati" className="flex gap-3"><button className="btn-secondary" disabled={page === 1} onClick={() => setPage(page - 1)}>Precedente</button><span>{page} / {Math.max(1, Math.ceil(data.total / 25))}</span><button className="btn-secondary" disabled={page * 25 >= data.total} onClick={() => setPage(page + 1)}>Successiva</button></nav></section>;
}

function CandidateRow({ workspace, item, channel, canEdit }: { workspace: Workspace; item: Candidate; channel: Channel; canEdit: boolean }) {
  const { selected, setSelected, setMessage, status, setCompose, open } = workspace;
  const blocked = status.busy || (!canEdit && !item.message_id);
  const isSelected = selected?.id === item.id;
  return <tr aria-label={`Apri avviso ${item.notice_number}`} aria-disabled={blocked} tabIndex={blocked ? -1 : 0} data-selected={isSelected}
    className="cursor-pointer border-t bg-white hover:bg-[#f7f9f5] focus-visible:outline focus-visible:outline-2 focus-visible:outline-emerald-700 aria-disabled:cursor-default data-[selected=true]:bg-[#eef3ea]"
    onClick={() => {
      if (blocked) return;
      void open(item);
    }}
    onKeyDown={(event) => {
      if (event.target !== event.currentTarget || !["Enter", " "].includes(event.key)) return;
      event.preventDefault(); event.currentTarget.click();
    }}>
    <td className="p-2 align-top"><input type="checkbox" aria-label={`Seleziona ${item.notice_number}`} checked={isSelected} disabled={!canEdit || status.busy} onClick={(event) => event.stopPropagation()} onChange={(event) => { setMessage(null); setSelected(event.target.checked ? item : null); setCompose({ recipient: item[channel] || "", account_id: "", template_id: "", subject: "", body: "", expected_source_sha256: "" }); }} /></td>
    <td className="break-words p-2 align-top"><strong className="block">{item.notice_number}</strong><span className="block text-slate-600">{item.batch_title}</span><span className="mt-1 block">{item.year} · {item.amount} €</span><span className="mt-1 block">{item.document_state} · {item.payment_state}</span></td>
    <td className="break-words p-2 align-top"><strong className="block">{item.display_name}</strong><span className="block">{item.tax_code}</span><span className="my-1 block break-all">{item[channel] || "Da verificare"}</span><span className="block">{item.notification_state}</span><span className="block">{item.communication_state || "Nessuna"}</span>{item.last_event_at}{item.communication_state === "cancelled" && canEdit && <button type="button" className="btn-secondary" disabled={status.busy} onClick={(event) => { event.stopPropagation(); void open(item, true); }}>Nuova revisione</button>}</td>
  </tr>;
}

export function NewCommunication({ workspace, channel, canEdit, token }: { workspace: Workspace; channel: Channel; canEdit: boolean; token: string }) {
  const { selected, compose, setCompose, data } = workspace;
  const template = useTemplateComposition({ token, sourceId: selected?.id || "", channel, templates: data.templates, compose, setCompose });
  const repair = useSourceRepair(token, selected?.id || "", compose.expected_source_sha256, template.retry);
  if (!selected || !canEdit) return <div className="space-y-2 p-4"><h2 className="text-lg font-semibold">Composizione e documento</h2><p className="text-sm text-slate-600">Clicca un avviso nell&apos;elenco: qui troverai i campi dell&apos;avviso selezionato e l&apos;anteprima del PDF.</p></div>;
  return <section aria-label="Nuova comunicazione" className="min-w-0 space-y-3 rounded-2xl border bg-white p-3"><header><h2 className="font-semibold">Componi avviso {selected.notice_number}</h2><p className="break-words text-sm"><strong>{selected.display_name}</strong> · CF {selected.tax_code} · {selected.year} · {selected.amount} €</p></header>
      <div className="grid min-w-0 gap-3 sm:grid-cols-2 xl:grid-cols-3">
      <label className="block min-w-0">Account<select className="mt-1 block w-full rounded border p-2" value={compose.account_id} onChange={(event) => setCompose({ ...compose, account_id: event.target.value })}><option value="">Predefinito autorizzato</option>{data.accounts.filter((account) => account.channel === channel).map((account) => <option value={account.id} key={account.id}>{account.name} · {account.sender}</option>)}</select></label>
      <label className="block min-w-0">Recapito verificato<input type="email" className="mt-1 block w-full rounded border p-2" value={compose.recipient} onChange={(event) => setCompose({ ...compose, recipient: event.target.value })} /></label>
      <label className="block min-w-0">Template approvato<select aria-describedby="template-help" className="mt-1 block w-full rounded border p-2" value={template.templateId} onChange={(event) => template.selectTemplate(event.target.value)}><option value="">Testo personalizzato</option>{template.available.map((value) => <option key={value.id} value={value.id}>{value.name} v{value.version}</option>)}</select></label>
      <label className="block min-w-0">Oggetto<input disabled={template.loading} className="mt-1 block w-full rounded border p-2" value={compose.subject} onChange={(event) => setCompose({ ...compose, subject: event.target.value })} /></label>
      <label className="block min-w-0 sm:col-span-2">Testo<textarea disabled={template.loading} rows={2} className="mt-1 block w-full rounded border p-2" value={compose.body} onChange={(event) => setCompose({ ...compose, body: event.target.value })} /></label>
      </div>
      <p id="template-help" className="text-xs text-slate-600">{template.available.length ? "Oggetto e testo vengono caricati con i dati dell’avviso dal template selezionato. Puoi modificarli prima di creare la bozza." : `Nessun template ${channel.toUpperCase()} approvato disponibile. Un amministratore deve creare e approvare una versione in Amministrazione comunicazioni → Template versionati. Poi usa Aggiorna stati.`}</p>
      {template.loading && <p role="status" className="text-sm">Caricamento oggetto e testo del template...</p>}
      {template.error && <div role="alert" className="text-sm text-rose-800">{template.error} <button className="btn-secondary" onClick={template.retry}>Riprova testo</button></div>}
      {template.incomplete && <p role="alert" className="text-sm text-amber-900">Testo incompleto: dati mancanti nel documento ({template.incomplete}). Verifica i dati e il PDF prima di creare la bozza.</p>}
      {template.incomplete.includes("utenza") && <button className="btn-secondary" disabled={repair.busy || !compose.expected_source_sha256} onClick={() => void repair.complete()}>Crea nuova revisione PDF con credenziali</button>}
      {repair.error && <p role="alert" className="text-sm text-rose-800">{repair.error}</p>}
      {template.blocked && <p role="alert" className="text-sm text-rose-800">Invio bloccato: {template.blocked}. Verifica la posizione nel Registro avvisi e aggiorna gli stati.</p>}
      <SourcePreviewActions key={`${selected.id}:${repair.revision}`} token={token} sourceId={selected.id} workspace={workspace} templateReady={template.ready && !repair.busy} />
    </section>;
}
