"use client";
import { useEffect, useRef, useState } from "react";
import { createPresenzeSyncJob, getPresenzeAutoSyncConfig, listPresenzeCredentials, listPresenzeSyncJobs } from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import type { PresenzeSyncJob } from "@/types/api";

export const OPEN_INAZ_JOB_STATUSES = new Set(["pending", "running"]);
function message(cause: unknown, fallback: string): string { return cause instanceof Error ? cause.message : fallback; }

function useInazCredential() {
  const [credentialId, setCredentialId] = useState<number | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    const token = getStoredAccessToken();
    if (!token) return;
    Promise.all([listPresenzeCredentials(token), getPresenzeAutoSyncConfig(token)]).then(([credentials, config]) => {
      if (!active) return;
      const available = credentials.filter(item => item.active);
      setCredentialId((available.find(item => item.id === config.credential_id) || available[0])?.id ?? null);
    }).catch(cause => { if (active) setError(message(cause, "Credenziale INAZ non disponibile")); });
    return () => { active = false; };
  }, []);
  return { credentialId, error };
}

function useInazJobMonitor(onCompleted: () => void) {
  const [jobs, setJobs] = useState<PresenzeSyncJob[]>([]);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState("");
  const observedOpen = useRef(new Set<string>());
  const callback = useRef(onCompleted);
  callback.current = onCompleted;
  useEffect(() => {
    let active = true;
    let polling = false;
    const token = getStoredAccessToken();
    if (!token) return;
    async function pollInazJobs() {
      if (polling) return;
      polling = true;
      try {
        const items = await listPresenzeSyncJobs(token!);
        if (!active) return;
        for (const job of items) {
          if (job.status === "completed" && observedOpen.current.delete(job.id)) callback.current();
          if (OPEN_INAZ_JOB_STATUSES.has(job.status)) observedOpen.current.add(job.id);
        }
        setJobs(items);
        setReady(true);
        setError("");
      } catch (cause) {
        if (active) setError(message(cause, "Stato INAZ non disponibile"));
      } finally { polling = false; }
    }
    void pollInazJobs();
    const timer = window.setInterval(pollInazJobs, 3000);
    return () => { active = false; window.clearInterval(timer); };
  }, []);
  function observeJob(job: PresenzeSyncJob) {
    observedOpen.current.add(job.id);
    setJobs(current => [job, ...current]);
  }
  return { jobs, ready, error, observeJob };
}

export function useInazSync(month: string, employeeCode: string | undefined, onCompleted: () => void) {
  const credential = useInazCredential();
  const monitor = useInazJobMonitor(onCompleted);
  const [submitting, setSubmitting] = useState(false);
  const [startError, setStartError] = useState("");
  const busy = useRef(false);
  const activeJob = monitor.jobs.find(job => OPEN_INAZ_JOB_STATUSES.has(job.status));
  async function startInazSync() {
    const token = getStoredAccessToken();
    if (!token || !credential.credentialId || activeJob || busy.current) return;
    busy.current = true;
    setSubmitting(true);
    setStartError("");
    try {
      const [year, number] = month.split("-").map(Number);
      const job = await createPresenzeSyncJob(token, { credential_id: credential.credentialId, year, month: number, collaborator_limit: null, employee_codes: employeeCode ? [employeeCode] : null });
      monitor.observeJob(job);
    } catch (cause) { setStartError(message(cause, "Sincronizzazione non avviata")); }
    finally { busy.current = false; setSubmitting(false); }
  }
  return { jobs: monitor.jobs, ready: monitor.ready, credentialId: credential.credentialId, activeJob, submitting, error: startError || monitor.error || credential.error, startInazSync };
}
