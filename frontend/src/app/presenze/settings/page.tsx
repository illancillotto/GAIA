"use client";

import { useEffect, useState } from "react";

import { ProtectedPage } from "@/components/app/protected-page";
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

const DEFAULT_FORM = {
  id: null as number | null,
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

export default function PresenzeSettingsPage() {
  const [credentials, setCredentials] = useState<PresenzeCredential[]>([]);
  const [form, setForm] = useState(DEFAULT_FORM);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [testingId, setTestingId] = useState<number | null>(null);

  async function loadCredentials() {
    const token = getStoredAccessToken();
    if (!token) return;
    try {
      const result = await listPresenzeCredentials(token);
      setCredentials(result);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Errore caricamento credenziali portale");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadCredentials();
  }, []);

  async function handleSubmit() {
    const token = getStoredAccessToken();
    if (!token) return;
    setSubmitting(true);
    setError(null);
    setSuccess(null);
    try {
      if (form.id == null) {
        await createPresenzeCredential(token, {
          label: form.label,
          username: form.username,
          password: form.password,
          active: form.active,
        });
        setSuccess("Credenziale portale creata.");
      } else {
        await updatePresenzeCredential(token, form.id, {
          label: form.label,
          username: form.username,
          password: form.password || undefined,
          active: form.active,
        });
        setSuccess("Credenziale portale aggiornata.");
      }
      setForm(DEFAULT_FORM);
      await loadCredentials();
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Errore salvataggio credenziale portale");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete(credentialId: number) {
    const token = getStoredAccessToken();
    if (!token) return;
    setError(null);
    setSuccess(null);
    try {
      await deletePresenzeCredential(token, credentialId);
      setSuccess("Credenziale portale eliminata.");
      if (form.id === credentialId) {
        setForm(DEFAULT_FORM);
      }
      await loadCredentials();
    } catch (deleteError) {
      setError(deleteError instanceof Error ? deleteError.message : "Errore eliminazione credenziale portale");
    }
  }

  async function handleTest(credentialId: number) {
    const token = getStoredAccessToken();
    if (!token) return;
    setTestingId(credentialId);
    setError(null);
    setSuccess(null);
    try {
      const result = await testPresenzeCredential(token, credentialId);
      setSuccess(`Login portale verificato${result.authenticated_url ? `: ${result.authenticated_url}` : ""}.`);
      await loadCredentials();
    } catch (testError) {
      setError(testError instanceof Error ? testError.message : "Errore test credenziale portale");
      await loadCredentials();
    } finally {
      setTestingId(null);
    }
  }

  return (
    <ProtectedPage
      title="Settings giornaliere"
      description="Gestione delle tue credenziali cifrate per login automatico e worker live."
      breadcrumb="Giornaliere"
      requiredModule="presenze"
    >
      <div className="space-y-6">
        {error ? <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div> : null}
        {success ? <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">{success}</div> : null}

        <article className="panel-card space-y-5">
          <div>
            <p className="section-title">{form.id == null ? "Nuova credenziale portale" : `Modifica credenziale #${form.id}`}</p>
            <p className="section-copy">Le password sono cifrate con `CREDENTIAL_MASTER_KEY` e non vengono piu restituite dal backend dopo il salvataggio.</p>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <label className="block text-sm font-medium text-gray-700">
              Label
              <input className="form-control mt-1" value={form.label} onChange={(event) => setForm((current) => ({ ...current, label: event.target.value }))} />
            </label>
            <label className="block text-sm font-medium text-gray-700">
              Username portale
              <input className="form-control mt-1" value={form.username} onChange={(event) => setForm((current) => ({ ...current, username: event.target.value }))} />
            </label>
            <label className="block text-sm font-medium text-gray-700 md:col-span-2">
              Password
              <input className="form-control mt-1" type="password" value={form.password} onChange={(event) => setForm((current) => ({ ...current, password: event.target.value }))} placeholder={form.id == null ? "" : "Lascia vuoto per mantenere la password attuale"} />
            </label>
          </div>
          <label className="inline-flex items-center gap-2 text-sm text-gray-700">
            <input checked={form.active} onChange={(event) => setForm((current) => ({ ...current, active: event.target.checked }))} type="checkbox" />
            Credenziale attiva
          </label>
          <div className="flex flex-wrap gap-3">
            <button className="btn-primary" type="button" onClick={() => void handleSubmit()} disabled={submitting}>
              {submitting ? "Salvataggio..." : form.id == null ? "Crea credenziale" : "Aggiorna credenziale"}
            </button>
            {form.id != null ? (
              <button className="btn-secondary" type="button" onClick={() => setForm(DEFAULT_FORM)}>
                Annulla modifica
              </button>
            ) : null}
          </div>
        </article>

        <article className="panel-card">
          <div className="mb-4">
            <p className="section-title">Vault credenziali</p>
            <p className="section-copy">Usa il test per verificare l&apos;accesso automatico al portale. Le sync live useranno solo le credenziali associate al tuo utente.</p>
          </div>
          {loading ? (
            <p className="text-sm text-gray-500">Caricamento credenziali...</p>
          ) : credentials.length === 0 ? (
            <EmptyState icon={LockIcon} title="Nessuna credenziale portale" description="Aggiungi il primo account da usare nei job di sync live." />
          ) : (
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
                    <tr key={credential.id}>
                      <td className="py-3 pr-4 font-medium text-gray-900">{credential.label}</td>
                      <td className="py-3 pr-4">{credential.username}</td>
                      <td className="py-3 pr-4">
                        <div className="space-y-1">
                          <span className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-semibold ${credentialStatusTone(credential)}`}>
                            {credentialStatusLabel(credential)}
                          </span>
                          {!credential.active ? (
                            <p className="max-w-[36ch] text-xs text-slate-500">
                              Non verra usata dalle sync. Modifica e spunta “Credenziale attiva”, oppure esegui un test riuscito per riattivarla.
                            </p>
                          ) : null}
                          {credential.last_error ? <p className="max-w-[36ch] truncate text-xs text-red-600" title={credential.last_error}>{credential.last_error}</p> : null}
                        </div>
                      </td>
                      <td className="py-3 pr-4">{formatDateTime(credential.last_used_at)}</td>
                      <td className="py-3 pr-4">{credential.last_authenticated_url ?? "—"}</td>
                      <td className="py-3">
                        <div className="flex flex-wrap gap-2">
                          <button
                            className="btn-secondary"
                            type="button"
                            onClick={() =>
                              setForm({
                                id: credential.id,
                                label: credential.label,
                                username: credential.username,
                                password: "",
                                active: credential.active,
                              })
                            }
                          >
                            Modifica
                          </button>
                          <button
                            className={credential.active ? "btn-secondary" : "rounded-2xl border border-amber-200 bg-amber-50 px-3 py-2 text-sm font-semibold text-amber-700 transition hover:bg-amber-100 disabled:opacity-60"}
                            type="button"
                            disabled={testingId === credential.id}
                            onClick={() => void handleTest(credential.id)}
                          >
                            {testingId === credential.id ? "Test..." : credential.active ? "Test" : "Test e riattiva"}
                          </button>
                          <button className="rounded-2xl border border-red-200 px-3 py-2 text-sm font-semibold text-red-700 transition hover:bg-red-50" type="button" onClick={() => void handleDelete(credential.id)}>
                            Elimina
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </article>
      </div>
    </ProtectedPage>
  );
}
