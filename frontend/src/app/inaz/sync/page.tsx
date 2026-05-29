"use client";

import { useEffect, useMemo, useState } from "react";

import { ProtectedPage } from "@/components/app/protected-page";
import {
  ModuleWorkspaceHero,
  ModuleWorkspaceKpiRow,
  ModuleWorkspaceKpiTile,
  ModuleWorkspaceNoticeCard,
} from "@/components/layout/module-workspace-hero";
import { EmptyState } from "@/components/ui/empty-state";
import { RefreshIcon } from "@/components/ui/icons";
import { cancelInazSyncJob, createInazSyncJob, downloadInazSyncArtifact, listInazCredentials, listInazSyncJobs, retryInazSyncJob } from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import type { InazCredential, InazSyncJob } from "@/types/api";

function formatMonthLabel(value: string): string {
  return new Intl.DateTimeFormat("it-IT", { month: "long", year: "numeric" }).format(new Date(`${value}T00:00:00`));
}

export default function InazSyncPage() {
  const today = new Date();
  const [year, setYear] = useState(String(today.getFullYear()));
  const [month, setMonth] = useState(String(today.getMonth() + 1).padStart(2, "0"));
  const [collaboratorLimit, setCollaboratorLimit] = useState("");
  const [credentialId, setCredentialId] = useState("");
  const [cdpEndpoint, setCdpEndpoint] = useState("http://127.0.0.1:9224");
  const [credentials, setCredentials] = useState<InazCredential[]>([]);
  const [jobs, setJobs] = useState<InazSyncJob[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [retryingJobId, setRetryingJobId] = useState<string | null>(null);
  const [downloadingArtifact, setDownloadingArtifact] = useState<string | null>(null);
  const [cancellingJobId, setCancellingJobId] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadJobs() {
      const token = getStoredAccessToken();
      if (!token) return;
      try {
        const [items, credentialsResult] = await Promise.all([listInazSyncJobs(token), listInazCredentials(token)]);
        if (!cancelled) {
          setJobs(items);
          setCredentials(credentialsResult);
        }
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : "Errore caricamento job sync Inaz");
        }
      }
    }

    void loadJobs();
    const intervalId = window.setInterval(() => {
      const hasActiveJobs = jobs.some((job) => job.status === "pending" || job.status === "running");
      if (hasActiveJobs) {
        void loadJobs();
      }
    }, 5000);

    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, [jobs]);

  const activeJob = jobs.find((job) => job.status === "running" || job.status === "pending") ?? null;
  const completedJobs = useMemo(() => jobs.filter((job) => job.status === "completed").length, [jobs]);
  const failedJobs = useMemo(() => jobs.filter((job) => job.status === "failed").length, [jobs]);
  const activeCredentials = useMemo(() => credentials.filter((credential) => credential.active), [credentials]);

  async function handleCreateJob() {
    const token = getStoredAccessToken();
    if (!token) return;
    setIsSubmitting(true);
    setError(null);
    setSuccess(null);
    try {
      const created = await createInazSyncJob(token, {
        year: Number(year),
        month: Number(month),
        credential_id: credentialId ? Number(credentialId) : null,
        collaborator_limit: collaboratorLimit ? Number(collaboratorLimit) : null,
        cdp_endpoint: credentialId ? null : cdpEndpoint || null,
      });
      setJobs((current) => [created, ...current]);
      setSuccess(`Job live sync creato per ${String(created.period_start).slice(0, 7)}.`);
    } catch (createError) {
      setError(createError instanceof Error ? createError.message : "Errore avvio sync Inaz");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleRetry(jobId: string) {
    const token = getStoredAccessToken();
    if (!token) return;
    setRetryingJobId(jobId);
    setError(null);
    setSuccess(null);
    try {
      const retried = await retryInazSyncJob(token, jobId);
      setJobs((current) => current.map((job) => (job.id === jobId ? retried : job)));
      setSuccess(`Retry avviato per job ${jobId}.`);
    } catch (retryError) {
      setError(retryError instanceof Error ? retryError.message : "Errore retry sync Inaz");
    } finally {
      setRetryingJobId(null);
    }
  }

  async function handleCancel(jobId: string) {
    const token = getStoredAccessToken();
    if (!token) return;
    setCancellingJobId(jobId);
    setError(null);
    setSuccess(null);
    try {
      const cancelled = await cancelInazSyncJob(token, jobId);
      setJobs((current) => current.map((job) => (job.id === jobId ? cancelled : job)));
      setSuccess(`Job ${jobId} annullato.`);
    } catch (cancelError) {
      setError(cancelError instanceof Error ? cancelError.message : "Errore annullamento sync Inaz");
    } finally {
      setCancellingJobId(null);
    }
  }

  async function handleDownloadArtifact(jobId: string, artifactName: "json" | "log" | "summary") {
    const token = getStoredAccessToken();
    if (!token) return;
    const key = `${jobId}:${artifactName}`;
    setDownloadingArtifact(key);
    setError(null);
    try {
      const blob = await downloadInazSyncArtifact(token, jobId, artifactName);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      const extension = artifactName === "log" ? "log" : "json";
      link.href = url;
      link.download = `inaz-sync-${jobId}-${artifactName}.${extension}`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (downloadError) {
      setError(downloadError instanceof Error ? downloadError.message : "Errore download artefatto sync Inaz");
    } finally {
      setDownloadingArtifact(null);
    }
  }

  return (
    <ProtectedPage
      title="Sync Inaz"
      description="Avvio e monitor del worker live Inaz via browser CDP."
      breadcrumb="Inaz"
      requiredModule="inaz"
    >
      <div className="space-y-8">
        <ModuleWorkspaceHero
          badge={<>Worker live</>}
          title="Avvia una sync collaboratori Inaz su processo separato e monitora import automatico e diagnostica."
          description="Il backend accoda un job persistente, avvia un worker Python separato, richiama lo scraper esterno via CDP e poi importa il JSON nel database GAIA."
          actions={
            <>
              <ModuleWorkspaceNoticeCard
                title={activeJob ? `Job attivo: ${activeJob.status}` : "Nessun job attivo"}
                description={activeJob ? `${activeJob.id} · periodo ${activeJob.period_start} / ${activeJob.period_end}` : "Puoi avviare una nuova sync live dal pannello sotto."}
                tone={activeJob ? "warning" : "neutral"}
              />
              <ModuleWorkspaceNoticeCard
                title={credentialId ? "Autenticazione via credenziali" : "Endpoint CDP"}
                description={credentialId ? "Il worker fara login Playwright con la credenziale selezionata." : cdpEndpoint || "Non configurato"}
                tone="info"
              />
            </>
          }
        >
          <ModuleWorkspaceKpiRow>
            <ModuleWorkspaceKpiTile label="Job totali" value={jobs.length} hint="Storico sync" />
            <ModuleWorkspaceKpiTile label="Completati" value={completedJobs} hint="Run con import riuscito" variant="emerald" />
            <ModuleWorkspaceKpiTile label="Falliti" value={failedJobs} hint="Richiedono verifica o retry" variant="amber" />
            <ModuleWorkspaceKpiTile label="Credenziali attive" value={activeCredentials.length} hint="Vault Inaz" />
          </ModuleWorkspaceKpiRow>
        </ModuleWorkspaceHero>

        {error ? <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div> : null}
        {success ? <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">{success}</div> : null}

        <article className="panel-card space-y-5">
          <div>
            <p className="section-title">Nuova sync live</p>
            <p className="section-copy">La run puo fare login con credenziali cifrate oppure collegarsi a una sessione Chrome gia autenticata via CDP, poi usa il formato JSON standard per l'import GAIA.</p>
          </div>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <label className="block text-sm font-medium text-gray-700">
              Anno
              <input className="form-control mt-1" value={year} onChange={(event) => setYear(event.target.value)} />
            </label>
            <label className="block text-sm font-medium text-gray-700">
              Mese
              <input className="form-control mt-1" value={month} onChange={(event) => setMonth(event.target.value)} />
            </label>
            <label className="block text-sm font-medium text-gray-700">
              Credenziale Inaz
              <select className="form-control mt-1" value={credentialId} onChange={(event) => setCredentialId(event.target.value)}>
                <option value="">Usa sessione CDP</option>
                {credentials.map((credential) => (
                  <option key={credential.id} value={credential.id}>
                    {credential.label} · {credential.username} {credential.active ? "" : "(disattiva)"}
                  </option>
                ))}
              </select>
            </label>
            <label className="block text-sm font-medium text-gray-700">
              Limite collaboratori
              <input className="form-control mt-1" value={collaboratorLimit} onChange={(event) => setCollaboratorLimit(event.target.value)} placeholder="Vuoto = tutti" />
            </label>
            <label className="block text-sm font-medium text-gray-700">
              Endpoint CDP
              <input className="form-control mt-1" value={cdpEndpoint} onChange={(event) => setCdpEndpoint(event.target.value)} disabled={Boolean(credentialId)} />
            </label>
          </div>
          <div className="flex flex-wrap gap-3">
            <button className="btn-primary" type="button" onClick={() => void handleCreateJob()} disabled={isSubmitting}>
              {isSubmitting ? "Avvio..." : "Avvia sync live"}
            </button>
          </div>
        </article>

        <article className="panel-card">
          <div className="mb-4">
            <p className="section-title">Storico job sync</p>
            <p className="section-copy">Monitor periodi, artefatti JSON, esito import e tentativi worker.</p>
          </div>
          {jobs.length === 0 ? (
            <EmptyState icon={RefreshIcon} title="Nessun job disponibile" description="Avvia la prima sync live per popolare il monitor." />
          ) : (
            <div className="space-y-3">
              {jobs.map((job) => (
                <div key={job.id} className="rounded-2xl border border-gray-100 bg-gray-50 px-4 py-4">
                  <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                    <div className="space-y-1">
                      <p className="font-medium text-gray-900">{formatMonthLabel(job.period_start)}</p>
                      <p className="text-xs text-gray-500">
                        {job.status} · {job.credential_id ? `credenziale #${job.credential_id}` : "modalita CDP"} · tentativo {job.attempt_count}/{job.max_attempts} · importati {job.records_imported} · scartati {job.records_skipped} · errori {job.records_errors}
                      </p>
                      <p className="text-xs text-gray-500">
                        JSON: {job.json_artifact_path ?? "n/d"} · Log: {job.worker_log_path ?? "n/d"}
                      </p>
                      {job.error_detail ? <p className="text-xs text-red-600">{job.error_detail}</p> : null}
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <button
                        className="btn-secondary"
                        type="button"
                        onClick={() => void handleDownloadArtifact(job.id, "json")}
                        disabled={downloadingArtifact === `${job.id}:json`}
                      >
                        {downloadingArtifact === `${job.id}:json` ? "JSON..." : "Scarica JSON"}
                      </button>
                      <button
                        className="btn-secondary"
                        type="button"
                        onClick={() => void handleDownloadArtifact(job.id, "log")}
                        disabled={downloadingArtifact === `${job.id}:log`}
                      >
                        {downloadingArtifact === `${job.id}:log` ? "Log..." : "Scarica log"}
                      </button>
                      <button
                        className="btn-secondary"
                        type="button"
                        onClick={() => void handleDownloadArtifact(job.id, "summary")}
                        disabled={downloadingArtifact === `${job.id}:summary`}
                      >
                        {downloadingArtifact === `${job.id}:summary` ? "Summary..." : "Scarica summary"}
                      </button>
                      {job.status === "pending" || job.status === "running" ? (
                        <button className="btn-secondary" type="button" onClick={() => void handleCancel(job.id)} disabled={cancellingJobId === job.id}>
                          {cancellingJobId === job.id ? "Stop..." : "Annulla job"}
                        </button>
                      ) : null}
                      {job.status === "failed" && job.attempt_count < job.max_attempts ? (
                        <button className="btn-secondary" type="button" onClick={() => void handleRetry(job.id)} disabled={retryingJobId === job.id}>
                          {retryingJobId === job.id ? "Retry..." : "Riprova"}
                        </button>
                      ) : null}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </article>
      </div>
    </ProtectedPage>
  );
}
