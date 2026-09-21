"use client";

import { useRef, useState, type FormEvent, type ReactNode } from "react";
import type { RegisterMutationResult } from "@/types/notice-register";
import { registerError, registerWrite } from "./client";
import { FORM_HELP, FormFields, formPayload, type FormKind } from "./form-fields";
import { Field, inputClass } from "./presentation";

export type MutationContext = { token: string; version: number; onSaved: (result: RegisterMutationResult) => void };
type MutationFormProps = MutationContext & {
  path: string; method: "POST" | "PUT"; title: string; children: ReactNode;
  buildData: (form: FormData) => Record<string, unknown>;
};

export function MutationForm({ token, version, onSaved, path, method, title, children, buildData }: MutationFormProps) {
  const pending = useRef(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (pending.current) return;
    const form = new FormData(event.currentTarget);
    pending.current = true;
    setBusy(true);
    setError(null);
    try {
      const result = await registerWrite(token, { path, method, version, reason: String(form.get("reason")).trim(), data: buildData(form) });
      onSaved(result);
    } catch (err) {
      setError(registerError(err));
    } finally {
      pending.current = false;
      setBusy(false);
    }
  }
  return <form aria-label={title} onSubmit={submit} className="space-y-4">
    <h3 className="text-lg font-semibold">{title}</h3>
    <fieldset disabled={busy} className="grid min-w-0 gap-4 sm:grid-cols-2">{children}
      <Field label="Motivo della registrazione o correzione"><textarea className={inputClass} name="reason" required /></Field>
    </fieldset>
    {error && <p role="alert" className="break-words text-sm text-rose-800">{error}</p>}
    <button className="btn-primary" type="submit" disabled={busy}>{busy ? "Salvataggio..." : "Salva registrazione"}</button>
    <p className="text-xs text-gray-500">Versione attesa: {version}. Ogni operazione viene registrata nello storico.</p>
  </form>;
}

export function RecordForm({ kind, initial, ...props }: Omit<MutationFormProps, "children" | "buildData"> & { kind: FormKind; initial: Record<string, unknown> }) {
  return <MutationForm {...props} buildData={(form) => formPayload(kind, form)}>
    <p className="text-sm text-gray-600 sm:col-span-2">{FORM_HELP[kind]}</p>
    <FormFields kind={kind} initial={initial} token={props.token} path={props.path} />
  </MutationForm>;
}
