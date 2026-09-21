"use client";

import { useRef, useState, type FormEvent, type ReactNode } from "react";
import { registerError } from "./client";
import { submitImport, type ImportBatch } from "./import-client";
import { Field, inputClass } from "./presentation";

type ImportFormProps = {
  token: string; path: string; title: string; children: ReactNode;
  body: (form: FormData) => FormData | Record<string, unknown>;
  onSaved: (batch: ImportBatch) => void;
};

function ImportForm({ token, path, title, children, body, onSaved }: ImportFormProps) {
  const pending = useRef(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (pending.current) return;
    const form = new FormData(event.currentTarget);
    pending.current = true; setBusy(true); setError(null);
    try { onSaved(await submitImport(token, path, body(form))); }
    catch (err) { setError(registerError(err)); }
    finally { pending.current = false; setBusy(false); }
  }
  return <form onSubmit={submit} aria-label={title} className="space-y-3">
    <fieldset disabled={busy} className="space-y-3">{children}<button className="btn-primary" type="submit">{busy ? "Elaborazione..." : title}</button></fieldset>
    {error && <p role="alert" className="text-sm text-rose-800">{error}</p>}
  </form>;
}

export function ImportSources({ token, onSaved }: Pick<ImportFormProps, "token" | "onSaved">) {
  return <div className="grid gap-6 lg:grid-cols-2">
    <ImportForm token={token} onSaved={onSaved} path="/excel" title="Prepara anteprima Excel" body={(form) => form}>
      <Field label="Excel avvisi 2022/2023"><input className={inputClass} type="file" accept=".xlsx" name="file" required /></Field>
      <p className="text-sm">Tracciato approvato, foglio Dati. Massimo 12 MiB. Tutte le righe 2022/2023, anche pagate o dubbie.</p>
    </ImportForm>
    <ImportForm token={token} onSaved={onSaved} path="/poste" title="Prepara snapshot Poste" body={() => ({})}>
      <p className="text-sm">Copia nel registro i dati Poste gia presenti in GAIA, dopo la conferma. Non interroga il portale e non deduce la consegna da &quot;Servizio erogato&quot;.</p>
    </ImportForm>
  </div>;
}

export function ConfirmImport({ token, batch, onSaved }: Pick<ImportFormProps, "token" | "onSaved"> & { batch: ImportBatch }) {
  return <ImportForm token={token} onSaved={onSaved} path={`/${batch.id}/conferma`} title="Conferma importazione"
    body={(form) => ({ digest: batch.digest, reason: String(form.get("reason")).trim(), confirmed: form.get("confirmed") === "on" })}>
    <p className="text-sm">La conferma importa i nuovi documenti, ignora i duplicati e conserva i conflitti senza sovrascrivere il registro. I conteggi vengono ricontrollati alla conferma. Notifica e STEP restano da verificare; nessun invio viene autorizzato.</p>
    <label className="flex items-start gap-2 text-sm"><input type="checkbox" name="confirmed" required className="mt-1" />Ho verificato anteprima, anomalie e provenienza dei dati.</label>
    <Field label="Motivo importazione"><textarea className={inputClass} name="reason" required /></Field>
  </ImportForm>;
}
