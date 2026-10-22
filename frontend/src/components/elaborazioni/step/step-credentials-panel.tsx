"use client";

import { FormEvent, useState } from "react";

import { ElaborazionePanelHeader } from "@/components/elaborazioni/module-chrome";
import { EmptyState } from "@/components/ui/empty-state";
import { LockIcon } from "@/components/ui/icons";
import { createStepCredential, deleteStepCredential, testStepCredential, updateStepCredential } from "@/lib/api";
import { formatDateTime } from "@/lib/presentation";
import type { StepCredential } from "@/types/step";

type StepCredentialsPanelProps = {
  token: string;
  credentials: StepCredential[];
  onChanged: (notice: string | null) => Promise<void>;
  onError: (message: string) => void;
};

type CredentialForm = { label: string; username: string; password: string };

const EMPTY_FORM: CredentialForm = { label: "STEP", username: "", password: "" };

function errorMessage(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback;
}

function CredentialCard({
  credential,
  busy,
  onAction,
}: {
  credential: StepCredential;
  busy: string | null;
  onAction: (action: "test" | "toggle" | "delete", credential: StepCredential) => void;
}) {
  return (
    <div className="rounded-2xl border border-gray-200 bg-[#fbfcfb] p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="font-semibold text-gray-900">{credential.label}</p>
          <p className="text-sm text-gray-600">{credential.username}</p>
          <p className="mt-1 text-xs text-gray-500">
            Ultimo uso {credential.last_used_at ? formatDateTime(credential.last_used_at) : "mai"} · errori consecutivi{" "}
            {credential.consecutive_failures}
          </p>
          {credential.last_error ? <p className="mt-2 text-sm text-red-600">{credential.last_error}</p> : null}
        </div>
        <span
          className={`rounded-full border px-2.5 py-1 text-xs font-semibold ${credential.active ? "border-emerald-200 bg-emerald-50 text-emerald-700" : "border-gray-200 bg-gray-100 text-gray-600"}`}
        >
          {credential.active ? "Attiva" : "Disattiva"}
        </span>
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        <button className="btn-secondary" disabled={busy !== null} onClick={() => onAction("test", credential)} type="button">
          Test login
        </button>
        <button className="btn-secondary" disabled={busy !== null} onClick={() => onAction("toggle", credential)} type="button">
          {credential.active ? "Disattiva" : "Attiva"}
        </button>
        <button
          className="rounded-2xl border border-red-200 px-3 py-2 text-sm font-semibold text-red-700 transition hover:bg-red-50"
          disabled={busy !== null}
          onClick={() => onAction("delete", credential)}
          type="button"
        >
          Elimina
        </button>
      </div>
    </div>
  );
}

const ACTION_NOTICES = {
  test: "Test login STEP accodato sul worker.",
  toggle: null,
  delete: null,
} as const;

export function StepCredentialsPanel({ token, credentials, onChanged, onError }: StepCredentialsPanelProps) {
  const [form, setForm] = useState<CredentialForm>(EMPTY_FORM);
  const [busy, setBusy] = useState<string | null>(null);
  const canSave = Boolean(form.label.trim() && form.username.trim() && form.password);

  async function run(key: string, operation: () => Promise<unknown>, notice: string | null): Promise<void> {
    setBusy(key);
    try {
      await operation();
      await onChanged(notice);
    } catch (error) {
      onError(errorMessage(error, "Operazione credenziale STEP non riuscita"));
    } finally {
      setBusy(null);
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!canSave) return;
    await run(
      "create",
      async () => {
        await createStepCredential(token, { label: form.label.trim(), username: form.username.trim(), password: form.password });
        setForm(EMPTY_FORM);
      },
      "Credenziale STEP salvata.",
    );
  }

  function handleAction(action: "test" | "toggle" | "delete", credential: StepCredential): void {
    const operations = {
      test: () => testStepCredential(token, credential.id),
      toggle: () => updateStepCredential(token, credential.id, { active: !credential.active }),
      delete: () => deleteStepCredential(token, credential.id),
    };
    void run(`${action}-${credential.id}`, operations[action], ACTION_NOTICES[action]);
  }

  return (
    <section className="overflow-hidden rounded-[24px] border border-[#d9dfd6] bg-white shadow-sm">
      <ElaborazionePanelHeader
        badge="Credenziali"
        title="Accesso portale STEP"
        description="Password cifrata in GAIA e mai mostrata. Dopo 3 login rifiutati la credenziale viene disattivata per evitare il blocco dell'account."
      />
      <div className="space-y-5 p-6">
        <form className="grid gap-3" onSubmit={(event) => void handleSubmit(event)}>
          <input aria-label="Etichetta" className="input" onChange={(event) => setForm({ ...form, label: event.target.value })} placeholder="Etichetta" value={form.label} />
          <input aria-label="Utente STEP" className="input" onChange={(event) => setForm({ ...form, username: event.target.value })} placeholder="Utente STEP" value={form.username} />
          <input aria-label="Password STEP" className="input" onChange={(event) => setForm({ ...form, password: event.target.value })} placeholder="Password" type="password" value={form.password} />
          <button className="btn-primary" disabled={!canSave || busy !== null} type="submit">
            {busy === "create" ? "Salvataggio..." : "Salva credenziale"}
          </button>
        </form>
        {credentials.length === 0 ? (
          <EmptyState icon={LockIcon} title="Nessuna credenziale STEP" description="Aggiungi utente e password del portale per abilitare la sincronizzazione dal worker." />
        ) : (
          <div className="space-y-3">
            {credentials.map((credential) => (
              <CredentialCard key={credential.id} busy={busy} credential={credential} onAction={handleAction} />
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
