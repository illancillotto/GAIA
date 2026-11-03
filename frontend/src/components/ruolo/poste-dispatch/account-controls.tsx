"use client";

import { useEffect, useState } from "react";

import { bindPosteAccount, listPosteAccounts } from "@/lib/ruolo-poste-dispatch-api";
import type { PosteDispatchAccount, PosteDispatchItem } from "@/types/ruolo-poste-dispatch";
import { errorMessage } from "./labels";

type AccountProps = {
  token: string; label: string; value: number | null;
  onChange: (value: number | null) => void; filter?: boolean;
};

export function AccountSelector({ token, label, value, onChange, filter = false }: AccountProps) {
  const [accounts, setAccounts] = useState<PosteDispatchAccount[]>([]);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    let current = true;
    setError(null);
    listPosteAccounts(token)
      .then((rows) => { if (current) setAccounts(rows); })
      .catch((err) => { if (current) setError(errorMessage(err, "Account Poste non caricati")); });
    return () => { current = false; };
  }, [token]);
  return <div>
    <label className="text-sm text-slate-700">{label}
      <select className="form-control w-full" value={value ?? ""} onChange={(event) => onChange(Number(event.target.value) || null)}>
        <option value="">{filter ? "Tutti gli account" : "Scegli l’account Poste"}</option>
        {accounts.filter((account) => filter || account.active).map((account) =>
          <option key={account.id} value={account.id}>{account.label} · {account.username}</option>)}
      </select>
    </label>
    {error && <p role="alert" className="text-sm text-rose-800">{error}</p>}
  </div>;
}

export function LegacyAccountBinding({ token, lotId, onChanged }: { token: string; lotId: string; onChanged: () => void }) {
  const [credentialId, setCredentialId] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  async function bind() {
    setBusy(true);
    setError(null);
    try {
      await bindPosteAccount(token, lotId, credentialId!);
      onChanged();
    } catch (err) {
      setError(errorMessage(err, "Account non associato"));
    } finally {
      setBusy(false);
    }
  }
  return <div className="space-y-2 rounded-xl border border-amber-300 p-3">
    <p>Lotto storico: indica l’account con cui sono state caricate le bozze. L’associazione resterà fissa.</p>
    <AccountSelector token={token} label="Account del lotto storico" value={credentialId} onChange={setCredentialId} />
    <button type="button" className="btn-secondary" disabled={busy || credentialId === null} onClick={() => void bind()}>Associa account</button>
    {error && <p role="alert">{error}</p>}
  </div>;
}

export function UploadAudit({ item }: { item: PosteDispatchItem }) {
  if (!item.upload_requested_by_username) return <p className="text-xs text-slate-500">Operatore del caricamento non ancora attribuito.</p>;
  return <p className="text-xs text-slate-500">Caricamento avviato da {item.upload_requested_by_username} · operazione {item.upload_job_id}</p>;
}
