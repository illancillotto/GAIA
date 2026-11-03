"use client";

import { useCallback, useEffect, useState, type Dispatch, type SetStateAction } from "react";
import { communications } from "@/lib/communications-api";

type Configuration = {
  name: string; channel: "pec" | "email"; provider: string; sender: string; display_name: string;
  smtp_host: string; smtp_port: number; smtp_encryption: string; imap_host: string; imap_port: number;
  imap_encryption: string; auth_method: string; username: string; secret_ref: string; active: boolean;
  paused: boolean; allowed_modules: string[]; allowed_user_ids: number[]; default_modules: string[];
  is_default: boolean; priority: number; max_bytes: number; hourly_limit: number;
};
type Stored = Configuration & { id: string; version: number; health: string; last_test_at: string | null; last_sync_at: string | null };
const EMPTY: Configuration = {
  name: "", channel: "pec", provider: "", sender: "", display_name: "", smtp_host: "", smtp_port: 465,
  smtp_encryption: "tls", imap_host: "", imap_port: 993, imap_encryption: "tls", auth_method: "password",
  username: "", secret_ref: "", active: false, paused: true, allowed_modules: ["ruolo"], allowed_user_ids: [],
  default_modules: [], is_default: false, priority: 100, max_bytes: 16777216, hourly_limit: 30,
};
const TEXT_FIELDS = { name: "Nome account", provider: "Provider", sender: "Indirizzo mittente", display_name: "Nome visualizzato", smtp_host: "Host SMTP verificato", imap_host: "Host IMAP verificato", username: "Username", secret_ref: "Riferimento secret esterno" } as const;
const NUMBERS = { smtp_port: "Porta SMTP", imap_port: "Porta IMAP", priority: "Priorità", max_bytes: "Limite MIME in byte", hourly_limit: "Invii massimi per ora" } as const;

export function AccountAdministration({ token }: { token: string }) {
  const [accounts, setAccounts] = useState<Stored[]>([]);
  const [selected, setSelected] = useState<Stored | null>(null);
  const [form, setForm] = useState<Configuration>(EMPTY);
  const [status, setStatus] = useState({ busy: false, error: "", notice: "" });
  const reload = useCallback(async () => setAccounts(await communications<Stored[]>(token, "/admin/accounts")), [token]);
  useEffect(() => { void reload().catch((error: Error) => setStatus({ busy: false, error: error.message, notice: "" })); }, [reload]);
  function edit(account: Stored) {
    setSelected(account);
    setForm(Object.fromEntries(Object.keys(EMPTY).map((key) => [key, account[key as keyof Configuration]])) as Configuration);
  }
  async function save() {
    setStatus({ busy: true, error: "", notice: "" });
    try {
      await communications(token, selected ? `/accounts/${selected.id}` : "/accounts", selected ? { ...form, expected_version: selected.version } : form, selected ? "PATCH" : "POST");
      await reload(); setSelected(null); setForm(EMPTY); setStatus({ busy: false, error: "", notice: "Configurazione salvata. Le approvazioni legate alla versione precedente richiedono revisione." });
    } catch (error) { setStatus({ busy: false, error: error instanceof Error ? error.message : "Salvataggio fallito", notice: "" }); }
  }
  async function command(account: Stored, action: string) {
    setStatus({ busy: true, error: "", notice: "" });
    try {
      await communications(token, `/accounts/${account.id}/${action}`, action === "pause" ? { paused: !account.paused } : {});
      await reload(); setStatus({ busy: false, error: "", notice: action === "pause" ? "Pausa aggiornata" : "Operazione accodata al worker; non invia messaggi di prova." });
    } catch (error) { setStatus({ busy: false, error: error instanceof Error ? error.message : "Operazione fallita", notice: "" }); }
  }
  return <section className="space-y-4 rounded-2xl border bg-white p-5"><h2 className="text-lg font-semibold">Account e provider</h2>
    {status.error && <p role="alert" className="text-rose-800">{status.error}</p>}{status.notice && <p role="status">{status.notice}</p>}
    <AccountTable accounts={accounts} busy={status.busy} edit={edit} command={command} />
    <h3 className="font-semibold">{selected ? "Modifica account" : "Nuovo account"}</h3>
    <p className="text-sm text-slate-600">Indicare gli endpoint pubblicati dal provider per lo specifico contratto. Il secret è un file montato esclusivamente al worker: qui si salva il riferimento, mai la password. Configurare un account non autorizza connessioni reali.</p>
    <AccountFields form={form} setForm={setForm} busy={status.busy} />
    <button className="btn-primary" disabled={status.busy} onClick={() => void save()}>Salva configurazione</button><button className="btn-secondary ml-2" onClick={() => { setSelected(null); setForm(EMPTY); }}>Nuovo account</button>
  </section>;
}

function AccountFields({ form, setForm, busy }: { form: Configuration; setForm: Dispatch<SetStateAction<Configuration>>; busy: boolean }) {
  return <fieldset disabled={busy} className="grid gap-3 md:grid-cols-2">
      {Object.entries(TEXT_FIELDS).map(([key, label]) => <label key={key}>{label}<input className="block w-full rounded border p-2" value={String(form[key as keyof Configuration])} onChange={(event) => setForm({ ...form, [key]: event.target.value })} /></label>)}
      {Object.entries(NUMBERS).map(([key, label]) => <label key={key}>{label}<input className="block w-full rounded border p-2" type="number" value={Number(form[key as keyof Configuration])} onChange={(event) => setForm({ ...form, [key]: Number(event.target.value) })} /></label>)}
      <label>Canale<select className="block rounded border p-2" value={form.channel} onChange={(event) => setForm({ ...form, channel: event.target.value as "pec" | "email" })}><option value="pec">PEC</option><option value="email">Email</option></select></label>
      {(["smtp_encryption", "imap_encryption"] as const).map((key) => <label key={key}>{key}<select className="block rounded border p-2" value={form[key]} onChange={(event) => setForm({ ...form, [key]: event.target.value })}><option value="tls">TLS implicito</option><option value="starttls">STARTTLS obbligatorio</option></select></label>)}
      <label>Autenticazione<select className="block rounded border p-2" value={form.auth_method} onChange={(event) => setForm({ ...form, auth_method: event.target.value })}><option value="password">Password / password applicativa</option><option value="oauth2">OAuth2 — token dal secret store</option></select></label>
      <label>ID utenti autorizzati (vuoto: tutti i gestori Tributi)<input className="block w-full rounded border p-2" value={form.allowed_user_ids.join(",")} onChange={(event) => setForm({ ...form, allowed_user_ids: event.target.value ? event.target.value.split(",").map(Number) : [] })} /></label>
      {(["active", "paused", "is_default"] as const).map((key) => <label key={key} className="flex items-center gap-2"><input type="checkbox" checked={form[key]} onChange={(event) => setForm({ ...form, [key]: event.target.checked })} />{key === "active" ? "Account abilitato" : key === "paused" ? "Invii in pausa" : "Predefinito generale del canale"}</label>)}
      <label className="flex items-center gap-2"><input type="checkbox" checked={form.default_modules.includes("ruolo")} onChange={(event) => setForm({ ...form, default_modules: event.target.checked ? ["ruolo"] : [] })} />Predefinito Ruolo per questo canale</label>
    </fieldset>;
}

function AccountTable({ accounts, busy, edit, command }: { accounts: Stored[]; busy: boolean; edit: (account: Stored) => void; command: (account: Stored, action: string) => Promise<void> }) {
  return <div className="overflow-auto"><table className="w-full text-left text-sm"><thead><tr><th>Account</th><th>Stato</th><th>Salute provider</th><th>Ultima verifica / sincronizzazione</th><th>Azioni</th></tr></thead><tbody>{accounts.map((account) => <tr key={account.id} className="border-t"><td className="p-2">{account.name}<br />{account.sender} · {account.provider} · {account.channel}</td><td>{account.active ? "Attivo" : "Disabilitato"} · {account.paused ? "Pausa" : "Coda attiva"}</td><td>{account.health}</td><td>{account.last_test_at || "Mai"}<br />{account.last_sync_at || "Mai"}</td><td className="space-x-2"><button className="btn-secondary" disabled={busy} onClick={() => edit(account)}>Modifica</button><button className="btn-secondary" disabled={busy} onClick={() => void command(account, "test")}>Test SMTP e IMAP</button><button className="btn-secondary" disabled={busy} onClick={() => void command(account, "reconcile")}>Acquisisci ricevute</button><button className="btn-secondary" disabled={busy} onClick={() => void command(account, "pause")}>{account.paused ? "Riprendi account" : "Pausa account"}</button></td></tr>)}</tbody></table></div>;
}
