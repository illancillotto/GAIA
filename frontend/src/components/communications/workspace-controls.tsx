"use client";
import { SourcePreviewActions } from "./source-preview-actions";
import type { Candidate, Channel } from "@/types/communications";
import type { useCommunicationsWorkspace } from "./use-workspace";
type Workspace = ReturnType<typeof useCommunicationsWorkspace>;

export function CandidateFilters({ workspace }: { workspace: Workspace }) {
  const { filters, setFilters, setPage, data, status, refresh } = workspace;
  return <div className="flex flex-wrap items-end gap-3 rounded-2xl border bg-white p-4 xl:col-span-2">
      <label>Cerca nominativo, CF o avviso<input className="block rounded-lg border p-2" value={filters.q} onChange={(event) => { setPage(1); setFilters({ ...filters, q: event.target.value }); }} /></label>
      <label>Recapito<select className="block rounded-lg border p-2" value={filters.has_contact} onChange={(event) => { setPage(1); setFilters({ ...filters, has_contact: event.target.value }); }}><option value="">Tutti</option><option value="true">Presente</option><option value="false">Assente</option></select></label>
      {(["has_pec", "has_email"] as const).map((key) => <label key={key}>{key === "has_pec" ? "Presenza PEC" : "Presenza email"}<select className="block rounded-lg border p-2" value={filters[key]} onChange={(event) => { setPage(1); setFilters({ ...filters, [key]: event.target.value }); }}><option value="">Tutti</option><option value="true">Presente</option><option value="false">Assente</option></select></label>)}
      <label>Stato<select className="block rounded-lg border p-2" value={filters.state} onChange={(event) => { setPage(1); setFilters({ ...filters, state: event.target.value }); }}><option value="">Tutti</option>{["draft", "ready", "approved", "queued", "sending", "submitted", "accepted", "delivered", "not_delivered", "uncertain", "failed", "cancelled"].map((value) => <option key={value}>{value}</option>)}</select></label>
      <label>Account<select className="block rounded-lg border p-2" value={filters.account_id} onChange={(event) => { setPage(1); setFilters({ ...filters, account_id: event.target.value }); }}><option value="">Tutti</option>{data.accounts.map((account) => <option key={account.id} value={account.id}>{account.name}</option>)}</select></label>
      <label>Dal<input className="block rounded-lg border p-2" type="date" value={filters.date_from} onChange={(event) => { setPage(1); setFilters({ ...filters, date_from: event.target.value }); }} /></label>
      <label>Al<input className="block rounded-lg border p-2" type="date" value={filters.date_to} onChange={(event) => { setPage(1); setFilters({ ...filters, date_to: event.target.value }); }} /></label>
      <label>Lotto (UUID)<input className="block rounded border p-2" value={filters.batch_id} onChange={(event) => { setPage(1); setFilters({ ...filters, batch_id: event.target.value }); }} /></label>
      <label>Pagamento<select className="block rounded border p-2" value={filters.payment_state} onChange={(event) => { setPage(1); setFilters({ ...filters, payment_state: event.target.value }); }}><option value="">Tutti</option>{["unpaid", "partial", "paid"].map((value) => <option key={value}>{value}</option>)}</select></label>
      <label>Notifica<select className="block rounded border p-2" value={filters.notification_state} onChange={(event) => { setPage(1); setFilters({ ...filters, notification_state: event.target.value }); }}><option value="">Tutte</option>{["nessuna_evidenza", "invio_in_corso", "tentativo_senza_notifica", "perfezionata", "da_verificare"].map((value) => <option key={value}>{value}</option>)}</select></label>
      <button className="btn-secondary" disabled={status.busy} onClick={() => void refresh()}>Aggiorna stati</button>
    </div>;
}

export function CandidateTable({ workspace, channel, canEdit }: { workspace: Workspace; channel: Channel; canEdit: boolean }) {
  const { data, page, setPage } = workspace;
  return <section aria-label="Elenco avvisi" className="min-w-0 space-y-3"><div className="max-h-[65vh] overflow-auto rounded-2xl border bg-white"><table className="w-full min-w-[64rem] text-left text-sm"><caption className="p-3 text-left">Solleciti 2021 · {data.total} risultati. Clicca un avviso per aprire composizione e PDF. L&apos;eleggibilità viene ricontrollata alla composizione e all&apos;invio.</caption><thead className="sticky top-0 z-20 bg-white"><tr>{["Selezione", "Avviso / lotto", "Contribuente / CF", "Anno / importo", "Recapito", "Documento", "Pagamento", "Notifica", "Comunicazione / ultimo evento"].map((label) => <th className="p-3" key={label}>{label}</th>)}</tr></thead><tbody>{data.items.map((item) => <CandidateRow key={item.id} workspace={workspace} item={item} channel={channel} canEdit={canEdit} />)}</tbody></table></div>
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
    <td className="p-3"><input type="checkbox" aria-label={`Seleziona ${item.notice_number}`} checked={isSelected} disabled={!canEdit || status.busy} onClick={(event) => event.stopPropagation()} onChange={(event) => { setMessage(null); setSelected(event.target.checked ? item : null); setCompose({ recipient: item[channel] || "", account_id: "", template_id: "", subject: "", body: "", expected_source_sha256: "" }); }} /></td>
    <td className="p-3">{item.notice_number}<br />{item.batch_title}</td><td className="p-3">{item.display_name}<br />{item.tax_code}</td><td className="p-3">{item.year}<br />{item.amount} €</td><td className="p-3">{item[channel] || "Da verificare"}</td><td className="p-3">{item.document_state}</td><td className="p-3">{item.payment_state}</td><td className="p-3">{item.notification_state}</td><td className="p-3">{item.communication_state || "Nessuna"}<br />{item.last_event_at}{item.communication_state === "cancelled" && canEdit && <button type="button" className="btn-secondary" disabled={status.busy} onClick={(event) => { event.stopPropagation(); void open(item, true); }}>Nuova revisione</button>}</td>
  </tr>;
}

export function NewCommunication({ workspace, channel, canEdit, token }: { workspace: Workspace; channel: Channel; canEdit: boolean; token: string }) {
  const { selected, compose, setCompose, data } = workspace;
  if (!selected || !canEdit) return <div className="space-y-2 p-4"><h2 className="text-lg font-semibold">Composizione e documento</h2><p className="text-sm text-slate-600">Clicca un avviso nell&apos;elenco: qui troverai i campi dell&apos;avviso selezionato e l&apos;anteprima del PDF.</p></div>;
  return <section aria-label="Nuova comunicazione" className="space-y-3 rounded-2xl border bg-white p-4"><h2 className="font-semibold">Componi avviso {selected.notice_number}</h2>
      <label className="block">Account<select className="mt-1 block w-full rounded border p-2" value={compose.account_id} onChange={(event) => setCompose({ ...compose, account_id: event.target.value })}><option value="">Predefinito autorizzato</option>{data.accounts.filter((account) => account.channel === channel).map((account) => <option value={account.id} key={account.id}>{account.name} · {account.sender}</option>)}</select></label>
      <label className="block">Recapito verificato<input type="email" className="mt-1 block w-full rounded border p-2" value={compose.recipient} onChange={(event) => setCompose({ ...compose, recipient: event.target.value })} /></label>
      <label className="block">Template approvato<select className="mt-1 block w-full rounded border p-2" value={compose.template_id} onChange={(event) => setCompose({ ...compose, template_id: event.target.value })}><option value="">Testo personalizzato</option>{data.templates.filter((template) => template.channel === channel).map((template) => <option key={template.id} value={template.id}>{template.name} v{template.version}</option>)}</select></label>
      <label className="block">Oggetto<input className="mt-1 block w-full rounded border p-2" value={compose.subject} onChange={(event) => setCompose({ ...compose, subject: event.target.value })} /></label>
      <label className="block">Testo<textarea className="block min-h-28 w-full rounded border p-2" value={compose.body} onChange={(event) => setCompose({ ...compose, body: event.target.value })} /></label>
      <SourcePreviewActions key={selected.id} token={token} sourceId={selected.id} workspace={workspace} />
    </section>;
}
