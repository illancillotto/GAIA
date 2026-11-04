"use client";
import type { ReactNode } from "react";
import type { Account, Communication } from "@/types/communications";
import type { useComposer } from "./use-composer";

type Controller = ReturnType<typeof useComposer>;
const CHECKS = {
  identity: "Identità del destinatario", address: "Correttezza del recapito", complete_pdf: "Contenuto integrale di tutte le pagine PDF",
  notice_year: "Numero avviso e annualità 2021", amounts: "Importi e riferimenti", text: "Oggetto e testo",
  attachments: "Elenco completo degli allegati", account: "Canale e account mittente",
};

export function ComposerForm({ message, accounts, canEdit, controller, children }: { message: Communication; accounts: Account[]; canEdit: boolean; controller: Controller; children?: ReactNode }) {
  const { form, editable, status, change, upload } = controller;
  return <div className="min-w-0 space-y-4 rounded-2xl border border-[#d8dfd3] bg-white p-5">
    <fieldset disabled={!editable || status.busy} className="space-y-4">
      <label className="block text-sm">Account mittente<select className="mt-1 w-full rounded-lg border p-2" value={form.account_id} onChange={(event) => change("account_id", event.target.value)}>
        <option value={message.account_id}>{message.sender}</option>
        {accounts.filter((account) => account.channel === message.channel).map((account) => <option key={account.id} value={account.id}>{account.name} · {account.provider} · {account.sender}{account.paused ? " (in pausa)" : ""}</option>)}
      </select></label>
      <label className="block text-sm">Destinatario<input className="mt-1 w-full rounded-lg border p-2" type="email" value={form.recipient} onChange={(event) => change("recipient", event.target.value)} /></label>
      <label className="block text-sm">Oggetto<input className="mt-1 w-full rounded-lg border p-2" maxLength={250} value={form.subject} onChange={(event) => change("subject", event.target.value)} /></label>
      <label className="block text-sm">Testo<textarea className="mt-1 min-h-28 w-full rounded-lg border p-2" maxLength={20000} value={form.body} onChange={(event) => change("body", event.target.value)} /></label>
      <label className="block text-sm">Aggiungi allegato PDF<input className="block" type="file" accept="application/pdf" onChange={(event) => { const file = event.target.files?.[0]; if (file) void upload(file); event.target.value = ""; }} /></label>
    </fieldset>
    <p className="text-sm">Allegati: {message.attachments.length} · {message.attachments.reduce((total, part) => total + part.size, 0)} byte prima della codifica MIME.</p>
    {message.channel === "email" && <p className="rounded-lg bg-sky-50 p-3 text-sm">Comunicazione di cortesia. L&apos;accettazione SMTP non attesta consegna o notifica legale.</p>}
    {children}
    <p className="text-xs text-slate-600">L&apos;approvazione registra la dichiarazione di controllo dell&apos;operatore; la correttezza sostanziale richiede la verifica dell&apos;ufficio. Invia accoda il lavoro persistente al worker. Una modifica richiede una nuova approvazione.</p>
    {canEdit && <ReviewChecklist message={message} controller={controller} />}
    {status.error && <p role="alert" className="text-rose-800">{status.error}</p>}
    {canEdit && <ComposerActions message={message} controller={controller} />}
  </div>;
}

function ReviewChecklist({ message, controller }: { message: Communication; controller: Controller }) {
  const { status, ready, checks, setChecks } = controller;
  return <fieldset disabled={status.busy || !ready || message.state !== "ready"} className="space-y-2 border-t pt-3"><legend className="font-semibold">Verifica individuale obbligatoria</legend>
    {Object.entries(CHECKS).map(([key, label]) => <label key={key} className="flex gap-2 text-sm"><input type="checkbox" checked={checks.includes(key)} onChange={(event) => setChecks((values) => event.target.checked ? [...values, key] : values.filter((value) => value !== key))} />{label}</label>)}
  </fieldset>;
}

function ComposerActions({ message, controller }: { message: Communication; controller: Controller }) {
  const { status, dirty, editable, ready, checks, action } = controller;
  const allowed = {
    save: editable && dirty, validate: !dirty && ["draft", "ready"].includes(message.state),
    approve: ready && checks.length === 8 && message.state === "ready",
    dispatch: ready && message.state === "approved",
    cancel: ["draft", "ready", "approved", "queued", "failed"].includes(message.state),
  };
  const labels = { save: "Salva bozza", validate: "Verifica dati attuali", approve: "Conferma e approva", dispatch: message.channel === "pec" ? "Invia PEC" : "Invia Email", cancel: "Annulla comunicazione" };
  return <div className="flex flex-wrap gap-2">{Object.entries(labels).map(([name, label]) => <button key={name} className="btn-secondary" disabled={status.busy || !allowed[name as keyof typeof allowed]} onClick={() => void action(name)}>{label}</button>)}</div>;
}
