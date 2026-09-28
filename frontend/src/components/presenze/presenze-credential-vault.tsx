"use client";

import { useEffect, useState } from "react";

import { EmptyState } from "@/components/ui/empty-state";
import { LockIcon } from "@/components/ui/icons";
import {
  createPresenzeCredential,
  deletePresenzeCredential,
  listPresenzeCredentials,
  testPresenzeCredential,
  updatePresenzeCredential,
} from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import { formatDateTime } from "@/lib/presentation";
import type { PresenzeCredential } from "@/types/api";

type CredentialForm = {
  id: number | null;
  label: string;
  username: string;
  password: string;
  active: boolean;
};

type VaultFeedback = {
  error: string | null;
  success: string | null;
};

const DEFAULT_FORM: CredentialForm = {
  id: null,
  label: "",
  username: "",
  password: "",
  active: true,
};

function credentialStatusTone(credential: PresenzeCredential): string {
  if (!credential.active) return "border-slate-200 bg-slate-100 text-slate-600";
  if (credential.last_error) return "border-amber-200 bg-amber-50 text-amber-700";
  return "border-emerald-200 bg-emerald-50 text-emerald-700";
}

function credentialStatusLabel(credential: PresenzeCredential): string {
  if (!credential.active) return "Disattiva";
  if (credential.last_error) return "Attiva con warning";
  return "Attiva";
}

function errorMessage(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback;
}

async function loadCredentialList(
  setCredentials: (credentials: PresenzeCredential[]) => void,
  setFeedback: (feedback: VaultFeedback) => void,
  setLoading: (loading: boolean) => void,
) {
  const token = getStoredAccessToken();
  if (!token) return;
  try {
    setCredentials(await listPresenzeCredentials(token));
  } catch (loadError) {
    setFeedback({ error: errorMessage(loadError, "Errore caricamento credenziali portale"), success: null });
  } finally {
    setLoading(false);
  }
}

async function submitCredentialForm(
  form: CredentialForm,
  setForm: (form: CredentialForm) => void,
  setFeedback: (feedback: VaultFeedback) => void,
  reload: () => Promise<void>,
) {
  const token = getStoredAccessToken();
  if (!token) return;
  if (form.id == null) {
    await createPresenzeCredential(token, {
      label: form.label,
      username: form.username,
      password: form.password,
      active: form.active,
    });
    setFeedback({ error: null, success: "Credenziale portale creata." });
  } else {
    await updatePresenzeCredential(token, form.id, {
      label: form.label,
      username: form.username,
      password: form.password || undefined,
      active: form.active,
    });
    setFeedback({ error: null, success: "Credenziale portale aggiornata." });
  }
  setForm(DEFAULT_FORM);
  await reload();
}

async function removeCredential(
  credentialId: number,
  form: CredentialForm,
  setForm: (form: CredentialForm) => void,
  setFeedback: (feedback: VaultFeedback) => void,
  reload: () => Promise<void>,
) {
  const token = getStoredAccessToken();
  if (!token) return;
  await deletePresenzeCredential(token, credentialId);
  setFeedback({ error: null, success: "Credenziale portale eliminata." });
  if (form.id === credentialId) setForm(DEFAULT_FORM);
  await reload();
}

async function verifyCredential(
  credentialId: number,
  setFeedback: (feedback: VaultFeedback) => void,
  reload: () => Promise<void>,
) {
  const token = getStoredAccessToken();
  if (!token) return;
  const result = await testPresenzeCredential(token, credentialId);
  const url = result.authenticated_url ? `: ${result.authenticated_url}` : "";
  setFeedback({ error: null, success: `Login portale verificato${url}.` });
  await reload();
}

function PresenzeCredentialAlerts({ error, success }: VaultFeedback) {
  return (
    <>
      {error ? <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div> : null}
      {success ? <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">{success}</div> : null}
    </>
  );
}

function PresenzeCredentialForm({
  form,
  submitting,
  onChange,
  onSubmit,
  onCancel,
}: {
  form: CredentialForm;
  submitting: boolean;
  onChange: (form: CredentialForm) => void;
  onSubmit: () => void;
  onCancel: () => void;
}) {
  const editing = form.id != null;
  return (
    <article className="panel-card space-y-5">
      <div>
        <p className="section-title">{editing ? `Modifica credenziale #${form.id}` : "Nuova credenziale portale"}</p>
        <p className="section-copy">Le password sono cifrate con `CREDENTIAL_MASTER_KEY` e non vengono piu restituite dal backend dopo il salvataggio.</p>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <label className="block text-sm font-medium text-gray-700">
          Label
          <input className="form-control mt-1" value={form.label} onChange={(event) => onChange({ ...form, label: event.target.value })} />
        </label>
        <label className="block text-sm font-medium text-gray-700">
          Username portale
          <input className="form-control mt-1" value={form.username} onChange={(event) => onChange({ ...form, username: event.target.value })} />
        </label>
        <label className="block text-sm font-medium text-gray-700 md:col-span-2">
          Password
          <input
            className="form-control mt-1"
            type="password"
            value={form.password}
            onChange={(event) => onChange({ ...form, password: event.target.value })}
            placeholder={editing ? "Lascia vuoto per mantenere la password attuale" : ""}
          />
        </label>
      </div>
      <label className="inline-flex items-center gap-2 text-sm text-gray-700">
        <input checked={form.active} onChange={(event) => onChange({ ...form, active: event.target.checked })} type="checkbox" />
        Credenziale attiva
      </label>
      <div className="flex flex-wrap gap-3">
        <button className="btn-primary" type="button" onClick={onSubmit} disabled={submitting}>
          {submitLabel(submitting, editing)}
        </button>
        {editing ? (
          <button className="btn-secondary" type="button" onClick={onCancel}>
            Annulla modifica
          </button>
        ) : null}
      </div>
    </article>
  );
}

function submitLabel(submitting: boolean, editing: boolean): string {
  if (submitting) return "Salvataggio...";
  if (editing) return "Aggiorna credenziale";
  return "Crea credenziale";
}

function testActionLabel(testing: boolean, active: boolean): string {
  if (testing) return "Test...";
  if (active) return "Test";
  return "Test e riattiva";
}

function PresenzeCredentialRow({
  credential,
  testing,
  onEdit,
  onTest,
  onDelete,
}: {
  credential: PresenzeCredential;
  testing: boolean;
  onEdit: (credential: PresenzeCredential) => void;
  onTest: (credentialId: number) => void;
  onDelete: (credentialId: number) => void;
}) {
  return (
    <tr>
      <td className="py-3 pr-4 font-medium text-gray-900">{credential.label}</td>
      <td className="py-3 pr-4">{credential.username}</td>
      <td className="py-3 pr-4">
        <div className="space-y-1">
          <span className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-semibold ${credentialStatusTone(credential)}`}>
            {credentialStatusLabel(credential)}
          </span>
          {credential.active ? null : (
            <p className="max-w-[36ch] text-xs text-slate-500">
              Non verra usata dalle sync. Modifica e spunta “Credenziale attiva”, oppure esegui un test riuscito per riattivarla.
            </p>
          )}
          {credential.last_error ? <p className="max-w-[36ch] truncate text-xs text-red-600" title={credential.last_error}>{credential.last_error}</p> : null}
        </div>
      </td>
      <td className="py-3 pr-4">{formatDateTime(credential.last_used_at)}</td>
      <td className="py-3 pr-4">{credential.last_authenticated_url ?? "—"}</td>
      <td className="py-3">
        <div className="flex flex-wrap gap-2">
          <button className="btn-secondary" type="button" onClick={() => onEdit(credential)}>
            Modifica
          </button>
          <button
            className={credential.active ? "btn-secondary" : "rounded-2xl border border-amber-200 bg-amber-50 px-3 py-2 text-sm font-semibold text-amber-700 transition hover:bg-amber-100 disabled:opacity-60"}
            type="button"
            disabled={testing}
            onClick={() => onTest(credential.id)}
          >
            {testActionLabel(testing, credential.active)}
          </button>
          <button className="rounded-2xl border border-red-200 px-3 py-2 text-sm font-semibold text-red-700 transition hover:bg-red-50" type="button" onClick={() => onDelete(credential.id)}>
            Elimina
          </button>
        </div>
      </td>
    </tr>
  );
}

function PresenzeCredentialList({
  credentials,
  loading,
  testingId,
  onEdit,
  onTest,
  onDelete,
}: {
  credentials: PresenzeCredential[];
  loading: boolean;
  testingId: number | null;
  onEdit: (credential: PresenzeCredential) => void;
  onTest: (credentialId: number) => void;
  onDelete: (credentialId: number) => void;
}) {
  if (loading) return <p className="text-sm text-gray-500">Caricamento credenziali...</p>;
  if (credentials.length === 0) {
    return <EmptyState icon={LockIcon} title="Nessuna credenziale portale" description="Aggiungi il primo account da usare nei job di sync live." />;
  }
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200 text-sm">
        <thead>
          <tr className="text-left text-xs uppercase tracking-[0.14em] text-gray-500">
            <th className="py-3 pr-4">Label</th>
            <th className="py-3 pr-4">Username</th>
            <th className="py-3 pr-4">Stato</th>
            <th className="py-3 pr-4">Ultimo uso</th>
            <th className="py-3 pr-4">Ultimo URL auth</th>
            <th className="py-3">Azioni</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {credentials.map((credential) => (
            <PresenzeCredentialRow
              key={credential.id}
              credential={credential}
              testing={testingId === credential.id}
              onEdit={onEdit}
              onTest={onTest}
              onDelete={onDelete}
            />
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function PresenzeCredentialVault() {
  const [credentials, setCredentials] = useState<PresenzeCredential[]>([]);
  const [form, setForm] = useState(DEFAULT_FORM);
  const [feedback, setFeedback] = useState<VaultFeedback>({ error: null, success: null });
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [testingId, setTestingId] = useState<number | null>(null);

  async function reload() {
    await loadCredentialList(setCredentials, setFeedback, setLoading);
  }

  useEffect(() => {
    void reload();
  }, []);

  async function handleSubmit() {
    setSubmitting(true);
    setFeedback({ error: null, success: null });
    try {
      await submitCredentialForm(form, setForm, setFeedback, reload);
    } catch (submitError) {
      setFeedback({ error: errorMessage(submitError, "Errore salvataggio credenziale portale"), success: null });
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete(credentialId: number) {
    setFeedback({ error: null, success: null });
    try {
      await removeCredential(credentialId, form, setForm, setFeedback, reload);
    } catch (deleteError) {
      setFeedback({ error: errorMessage(deleteError, "Errore eliminazione credenziale portale"), success: null });
    }
  }

  async function handleTest(credentialId: number) {
    setTestingId(credentialId);
    setFeedback({ error: null, success: null });
    try {
      await verifyCredential(credentialId, setFeedback, reload);
    } catch (testError) {
      setFeedback({ error: errorMessage(testError, "Errore test credenziale portale"), success: null });
      await reload();
    } finally {
      setTestingId(null);
    }
  }

  return (
    <div className="space-y-6">
      <PresenzeCredentialAlerts error={feedback.error} success={feedback.success} />
      <PresenzeCredentialForm
        form={form}
        submitting={submitting}
        onChange={setForm}
        onSubmit={() => void handleSubmit()}
        onCancel={() => setForm(DEFAULT_FORM)}
      />
      <article className="panel-card">
        <div className="mb-4">
          <p className="section-title">Vault credenziali</p>
          <p className="section-copy">Usa il test per verificare l&apos;accesso automatico al portale. Le sync live useranno solo le credenziali associate al tuo utente.</p>
        </div>
        <PresenzeCredentialList
          credentials={credentials}
          loading={loading}
          testingId={testingId}
          onEdit={(credential) =>
            setForm({
              id: credential.id,
              label: credential.label,
              username: credential.username,
              password: "",
              active: credential.active,
            })
          }
          onTest={(credentialId) => void handleTest(credentialId)}
          onDelete={(credentialId) => void handleDelete(credentialId)}
        />
      </article>
    </div>
  );
}
