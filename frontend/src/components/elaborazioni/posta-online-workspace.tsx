"use client";

import { FormEvent, useEffect, useState } from "react";

import { ProtectedPage } from "@/components/app/protected-page";
import {
  ElaborazioneHero,
  ElaborazioneMiniStat,
  ElaborazioneNoticeCard,
  ElaborazionePanelHeader,
} from "@/components/elaborazioni/module-chrome";
import { EmptyState } from "@/components/ui/empty-state";
import { CheckIcon, DocumentIcon, LockIcon, RefreshIcon } from "@/components/ui/icons";
import {
  createPostaOnlineCredential,
  createPostaOnlineRegisteredMailJob,
  deletePostaOnlineCredential,
  listPostaOnlineCredentials,
  listPostaOnlineRegisteredMailJobs,
  rerunPostaOnlineRegisteredMailJob,
  testPostaOnlineCredential,
  updatePostaOnlineCredential,
} from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import { formatDateTime } from "@/lib/presentation";
import type { PostaOnlineCredential, PostaOnlineRegisteredMailSyncJob, PostaOnlineRegisteredMailSyncJobResult } from "@/types/api";

type PostaOnlineWorkspaceProps = {
  embedded?: boolean;
};

type CredentialForm = {
  label: string;
  username: string;
  password: string;
  minDelayMs: string;
  maxDelayMs: string;
};

function formatJobStatus(status: string): string {
  if (status === "pending") return "In coda";
  if (status === "queued_resume") return "Ripresa in coda";
  if (status === "processing") return "In esecuzione";
  if (status === "succeeded") return "Completato";
  if (status === "completed_with_errors") return "Completato con anomalie";
  if (status === "failed") return "Fallito";
  return status;
}

function jobStatusClassName(status: string): string {
  if (status === "succeeded") return "border-emerald-200 bg-emerald-50 text-emerald-700";
  if (status === "completed_with_errors" || status === "queued_resume" || status === "processing" || status === "pending") {
    return "border-amber-200 bg-amber-50 text-amber-700";
  }
  if (status === "failed") return "border-red-200 bg-red-50 text-red-700";
  return "border-gray-200 bg-gray-50 text-gray-600";
}

function getJobResult(job: PostaOnlineRegisteredMailSyncJob): PostaOnlineRegisteredMailSyncJobResult | null {
  if (!job.result_json || Array.isArray(job.result_json) || typeof job.result_json !== "object") {
    return null;
  }
  return job.result_json as PostaOnlineRegisteredMailSyncJobResult;
}

function latestDate(values: Array<string | null | undefined>): string | null {
  return values.filter((value): value is string => Boolean(value)).sort().at(-1) ?? null;
}

function createDefaultForm(): CredentialForm {
  return {
    label: "Poste Online",
    username: "",
    password: "",
    minDelayMs: "3500",
    maxDelayMs: "9000",
  };
}

export function ElaborazioniPostaOnlineWorkspace({ embedded = false }: PostaOnlineWorkspaceProps) {
  const [credentials, setCredentials] = useState<PostaOnlineCredential[]>([]);
  const [jobs, setJobs] = useState<PostaOnlineRegisteredMailSyncJob[]>([]);
  const [form, setForm] = useState<CredentialForm>(() => createDefaultForm());
  const [selectedCredentialId, setSelectedCredentialId] = useState<string>("");
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function loadData(): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) return;
    try {
      const [credentialRows, jobRows] = await Promise.all([
        listPostaOnlineCredentials(token),
        listPostaOnlineRegisteredMailJobs(token),
      ]);
      setCredentials(credentialRows);
      setJobs(jobRows.slice(0, 30));
      setSelectedCredentialId((current) => current || String(credentialRows.find((credential) => credential.active)?.id ?? credentialRows[0]?.id ?? ""));
      setError(null);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Errore caricamento Poste Online");
    }
  }

  useEffect(() => {
    void loadData();
  }, []);

  const hasActiveJobs = jobs.some((job) => job.status === "pending" || job.status === "queued_resume" || job.status === "processing");

  useEffect(() => {
    if (!hasActiveJobs) return undefined;
    const interval = window.setInterval(() => {
      void loadData();
    }, 10000);
    return () => window.clearInterval(interval);
  }, [hasActiveJobs]);

  const activeCredentials = credentials.filter((credential) => credential.active);
  const warningCredentials = credentials.filter((credential) => Boolean(credential.last_error));
  const latestUsage = latestDate(credentials.map((credential) => credential.last_used_at));
  const latestRegisteredMailJob = jobs.find((job) => job.mode === "registered_mails") ?? null;
  const latestCredentialTest = jobs.find((job) => job.mode === "credential_test") ?? null;
  const canCreateCredential = form.label.trim() && form.username.trim() && form.password.trim();
  const selectedCredential = credentials.find((credential) => String(credential.id) === selectedCredentialId) ?? null;

  async function handleCreateCredential(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    const token = getStoredAccessToken();
    if (!token || !canCreateCredential) return;
    setBusy("create-credential");
    setNotice(null);
    try {
      await createPostaOnlineCredential(token, {
        label: form.label.trim(),
        username: form.username.trim(),
        password: form.password,
        min_delay_ms: Number(form.minDelayMs),
        max_delay_ms: Number(form.maxDelayMs),
      });
      setForm(createDefaultForm());
      setNotice("Credenziale Poste Online salvata.");
      await loadData();
    } catch (createError) {
      setError(createError instanceof Error ? createError.message : "Errore salvataggio credenziale Poste Online");
    } finally {
      setBusy(null);
    }
  }

  async function handleToggleCredential(credential: PostaOnlineCredential): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) return;
    setBusy(`toggle-${credential.id}`);
    try {
      await updatePostaOnlineCredential(token, credential.id, { active: !credential.active });
      await loadData();
    } catch (toggleError) {
      setError(toggleError instanceof Error ? toggleError.message : "Errore aggiornamento credenziale Poste Online");
    } finally {
      setBusy(null);
    }
  }

  async function handleDeleteCredential(credentialId: number): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) return;
    setBusy(`delete-${credentialId}`);
    try {
      await deletePostaOnlineCredential(token, credentialId);
      await loadData();
    } catch (deleteError) {
      setError(deleteError instanceof Error ? deleteError.message : "Errore eliminazione credenziale Poste Online");
    } finally {
      setBusy(null);
    }
  }

  async function handleTestCredential(credential: PostaOnlineCredential): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) return;
    setBusy(`test-${credential.id}`);
    setNotice(null);
    try {
      await testPostaOnlineCredential(token, credential.id, {
        min_delay_ms: credential.min_delay_ms,
        max_delay_ms: credential.max_delay_ms,
      });
      setNotice("Test login Poste Online accodato sul worker.");
      await loadData();
    } catch (testError) {
      setError(testError instanceof Error ? testError.message : "Errore accodamento test Poste Online");
    } finally {
      setBusy(null);
    }
  }

  async function handleCreateRegisteredMailJob(): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) return;
    setBusy("create-job");
    setNotice(null);
    try {
      await createPostaOnlineRegisteredMailJob(token, {
        credential_id: selectedCredentialId ? Number(selectedCredentialId) : null,
        annualita: [2022, 2023],
        include_contacts: true,
        include_details: true,
        max_pages: null,
        max_details: null,
        continue_on_error: true,
      });
      setNotice("Import raccomandate 2022-2023 accodato sul worker.");
      await loadData();
    } catch (jobError) {
      setError(jobError instanceof Error ? jobError.message : "Errore accodamento import Poste Online");
    } finally {
      setBusy(null);
    }
  }

  async function handleRerunJob(jobId: number): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) return;
    setBusy(`rerun-${jobId}`);
    try {
      await rerunPostaOnlineRegisteredMailJob(token, jobId);
      await loadData();
    } catch (rerunError) {
      setError(rerunError instanceof Error ? rerunError.message : "Errore rilancio job Poste Online");
    } finally {
      setBusy(null);
    }
  }

  const content = (
    <div className={embedded ? "space-y-6" : "space-y-7"}>
      <ElaborazioneHero
        badge={
          <>
            <LockIcon className="h-3.5 w-3.5" />
            Poste Online
          </>
        }
        title="Raccomandate online e recupero tributi 2022-2023."
        description="Le credenziali Poste sono cifrate in GAIA e lo scraping parte solo dal worker elaborazioni con delay randomizzati e backoff, non dal backend applicativo."
        actions={
          error ? (
            <ElaborazioneNoticeCard title="Errore Poste Online" description={error} tone="danger" />
          ) : (
            <ElaborazioneNoticeCard
              title={hasActiveJobs ? "Worker in attività" : "Worker pronto"}
              description={hasActiveJobs ? "La lista job si aggiorna automaticamente." : "Avvia test login o import raccomandate quando serve."}
            />
          )
        }
      >
        <div className="grid gap-4 md:grid-cols-4">
          <ElaborazioneMiniStat eyebrow="Credenziali attive" value={`${activeCredentials.length}/${credentials.length}`} description="Account disponibili per il worker." />
          <ElaborazioneMiniStat eyebrow="Warning account" value={warningCredentials.length} description="Credenziali con ultimo errore registrato." />
          <ElaborazioneMiniStat eyebrow="Ultimo uso" value={latestUsage ? formatDateTime(latestUsage) : "Mai"} description="Login o import concluso con successo." />
          <ElaborazioneMiniStat eyebrow="Ultimo import" value={latestRegisteredMailJob ? formatJobStatus(latestRegisteredMailJob.status) : "Nessuno"} description="Stato dell'ultimo recupero raccomandate." />
        </div>
      </ElaborazioneHero>

      {notice ? <ElaborazioneNoticeCard title="Operazione accodata" description={notice} /> : null}

      <div className="grid gap-6 xl:grid-cols-[0.95fr,1.05fr]">
        <section className="overflow-hidden rounded-[24px] border border-[#d9dfd6] bg-white shadow-sm">
          <ElaborazionePanelHeader
            badge="Credenziali"
            title="Accesso Poste Online"
            description="Poste richiede solo username e password. Il test login viene eseguito dal worker e non scarica dati."
          />
          <div className="space-y-5 p-6">
            <form className="grid gap-3" onSubmit={handleCreateCredential}>
              <input
                className="input"
                onChange={(event) => setForm((current) => ({ ...current, label: event.target.value }))}
                placeholder="Etichetta"
                value={form.label}
              />
              <input
                className="input"
                onChange={(event) => setForm((current) => ({ ...current, username: event.target.value }))}
                placeholder="Username Poste"
                value={form.username}
              />
              <input
                className="input"
                onChange={(event) => setForm((current) => ({ ...current, password: event.target.value }))}
                placeholder="Password"
                type="password"
                value={form.password}
              />
              <div className="grid gap-3 sm:grid-cols-2">
                <label className="text-sm font-medium text-gray-700">
                  Delay minimo ms
                  <input
                    className="input mt-1"
                    min={1000}
                    onChange={(event) => setForm((current) => ({ ...current, minDelayMs: event.target.value }))}
                    type="number"
                    value={form.minDelayMs}
                  />
                </label>
                <label className="text-sm font-medium text-gray-700">
                  Delay massimo ms
                  <input
                    className="input mt-1"
                    min={1000}
                    onChange={(event) => setForm((current) => ({ ...current, maxDelayMs: event.target.value }))}
                    type="number"
                    value={form.maxDelayMs}
                  />
                </label>
              </div>
              <button className="btn-primary" disabled={!canCreateCredential || busy === "create-credential"} type="submit">
                {busy === "create-credential" ? "Salvataggio..." : "Salva credenziale"}
              </button>
            </form>

            {credentials.length === 0 ? (
              <EmptyState icon={LockIcon} title="Nessuna credenziale Poste" description="Aggiungi username e password per accodare test login e import raccomandate dal worker." />
            ) : (
              <div className="space-y-3">
                {credentials.map((credential) => (
                  <div key={credential.id} className="rounded-2xl border border-gray-200 bg-[#fbfcfb] p-4">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <p className="font-semibold text-gray-900">{credential.label}</p>
                        <p className="text-sm text-gray-600">{credential.username}</p>
                        <p className="mt-1 text-xs text-gray-500">
                          Delay {credential.min_delay_ms}-{credential.max_delay_ms} ms · ultimo uso {credential.last_used_at ? formatDateTime(credential.last_used_at) : "mai"}
                        </p>
                        {credential.last_error ? <p className="mt-2 text-sm text-red-600">{credential.last_error}</p> : null}
                      </div>
                      <span className={`rounded-full border px-2.5 py-1 text-xs font-semibold ${credential.active ? "border-emerald-200 bg-emerald-50 text-emerald-700" : "border-gray-200 bg-gray-100 text-gray-600"}`}>
                        {credential.active ? "Attiva" : "Disattiva"}
                      </span>
                    </div>
                    <div className="mt-4 flex flex-wrap gap-2">
                      <button className="btn-secondary" disabled={busy === `test-${credential.id}`} onClick={() => void handleTestCredential(credential)} type="button">
                        {busy === `test-${credential.id}` ? "Accodo..." : "Test login"}
                      </button>
                      <button className="btn-secondary" disabled={busy === `toggle-${credential.id}`} onClick={() => void handleToggleCredential(credential)} type="button">
                        {credential.active ? "Disattiva" : "Attiva"}
                      </button>
                      <button className="rounded-2xl border border-red-200 px-3 py-2 text-sm font-semibold text-red-700 transition hover:bg-red-50" disabled={busy === `delete-${credential.id}`} onClick={() => void handleDeleteCredential(credential.id)} type="button">
                        Elimina
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </section>

        <section className="overflow-hidden rounded-[24px] border border-[#d9dfd6] bg-white shadow-sm">
          <ElaborazionePanelHeader
            badge="Raccomandate"
            title="Import batch 2022-2023"
            description="Il worker recupera contatti, archivio e dettagli, poi passa il payload al modulo tributi per match su indirizzo e gestione anomalie."
            actions={<button className="btn-secondary" onClick={() => void loadData()} type="button"><RefreshIcon className="mr-2 h-4 w-4" />Aggiorna</button>}
          />
          <div className="space-y-5 p-6">
            <div className="rounded-[22px] border border-[#dce8df] bg-[#f6faf7] p-5 shadow-[inset_0_1px_0_rgba(255,255,255,0.75)]">
              <div className="grid gap-4 lg:grid-cols-[minmax(260px,1.45fr),minmax(220px,1fr)]">
                <label className="block rounded-2xl border border-[#d9e6dc] bg-white/85 p-4 shadow-sm">
                  <span className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#1D4E35]">Credenziale</span>
                  <span className="mt-1 block text-xs leading-5 text-gray-500">Account Poste da usare; lascia automatico per il primo account disponibile.</span>
                  <select
                    className="mt-3 h-11 w-full rounded-xl border border-gray-200 bg-white px-3 text-sm font-medium text-gray-900 shadow-inner outline-none transition focus:border-[#1D4E35] focus:ring-2 focus:ring-[#1D4E35]/15"
                    onChange={(event) => setSelectedCredentialId(event.target.value)}
                    value={selectedCredentialId}
                  >
                    <option value="">Pool automatico</option>
                    {credentials.map((credential) => (
                      <option key={credential.id} value={credential.id}>
                        {credential.label} · {credential.username}
                      </option>
                    ))}
                  </select>
                </label>
                <div className="block rounded-2xl border border-[#d9e6dc] bg-white/85 p-4 shadow-sm">
                  <span className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#1D4E35]">Copertura sync</span>
                  <span className="mt-1 block text-xs leading-5 text-gray-500">Sincronizzazione completa: tutte le pagine archivio e tutti i dettagli invio disponibili.</span>
                  <p className="mt-3 rounded-xl bg-[#eef7f1] px-3 py-3 text-sm font-semibold text-[#1D4E35]">Nessun limite manuale</p>
                </div>
              </div>
              <div className="mt-5 flex flex-wrap items-center justify-between gap-3 rounded-2xl bg-white/70 px-4 py-3">
                <div className="space-y-1 text-sm text-gray-600">
                  <p>
                    Annualità: <span className="rounded-full bg-[#e4f1e8] px-2.5 py-1 text-xs font-semibold text-[#1D4E35]">2022</span>{" "}
                    <span className="rounded-full bg-[#e4f1e8] px-2.5 py-1 text-xs font-semibold text-[#1D4E35]">2023</span>
                  </p>
                  <p className="text-xs text-gray-500">
                    {selectedCredential ? `Ritmo richieste: ${selectedCredential.min_delay_ms}-${selectedCredential.max_delay_ms} ms.` : "Il worker selezionerà automaticamente una credenziale attiva."}
                  </p>
                </div>
                <button className="btn-primary min-w-[150px]" disabled={busy === "create-job" || credentials.length === 0} onClick={() => void handleCreateRegisteredMailJob()} type="button">
                  {busy === "create-job" ? "Accodamento..." : "Avvia import"}
                </button>
              </div>
            </div>

            {jobs.length === 0 ? (
              <EmptyState icon={DocumentIcon} title="Nessun job Poste" description="Accoda un test login o un import raccomandate per iniziare il monitoraggio." />
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200 text-sm">
                  <thead className="bg-gray-50 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                    <tr>
                      <th className="px-4 py-3">Job</th>
                      <th className="px-4 py-3">Stato</th>
                      <th className="px-4 py-3">Risultato</th>
                      <th className="px-4 py-3">Aggiornato</th>
                      <th className="px-4 py-3"></th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {jobs.map((job) => {
                      const result = getJobResult(job);
                      return (
                        <tr key={job.id}>
                          <td className="px-4 py-3 font-medium text-gray-900">
                            #{job.id} · {job.mode === "credential_test" ? "Test login" : "Import raccomandate"}
                          </td>
                          <td className="px-4 py-3">
                            <span className={`rounded-full border px-2.5 py-1 text-xs font-semibold ${jobStatusClassName(job.status)}`}>
                              {formatJobStatus(job.status)}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-gray-600">
                            {job.error_detail ??
                              (result?.records_matched != null
                                ? `${result.records_matched} match · ${result.records_unmatched ?? 0} non associati · ${result.records_ambiguous ?? 0} ambigui`
                                : result?.ok === true
                                  ? "Login verificato"
                                  : "—")}
                          </td>
                          <td className="px-4 py-3 text-gray-500">{formatDateTime(job.updated_at)}</td>
                          <td className="px-4 py-3 text-right">
                            {job.mode === "registered_mails" && ["failed", "completed_with_errors", "succeeded"].includes(job.status) ? (
                              <button className="btn-secondary" disabled={busy === `rerun-${job.id}`} onClick={() => void handleRerunJob(job.id)} type="button">
                                Rilancia
                              </button>
                            ) : job.status === "succeeded" && job.mode === "credential_test" ? (
                              <CheckIcon className="inline h-5 w-5 text-emerald-600" />
                            ) : null}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
            {latestCredentialTest ? (
              <p className="text-xs text-gray-500">
                Ultimo test login: {formatJobStatus(latestCredentialTest.status)} · {formatDateTime(latestCredentialTest.updated_at)}
              </p>
            ) : null}
          </div>
        </section>
      </div>
    </div>
  );

  if (embedded) {
    return content;
  }

  return (
    <ProtectedPage
      title="Poste Online"
      description="Credenziali e worker per recupero raccomandate online."
      breadcrumb="Elaborazioni / Poste Online"
      requiredModule="catasto"
    >
      {content}
    </ProtectedPage>
  );
}
