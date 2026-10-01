"use client";
import { relevantInazJobs, lastSuccessfulInazJob } from "@/lib/presenze-inaz-sync-state";
import type { PresenzeSyncJob } from "@/types/api";
import { useInazSync } from "./use-inaz-sync";

type Props = { month: string; employeeCode?: string; onCompleted: () => void };
function InazSyncOutcome({ latest }: { latest?: PresenzeSyncJob }) {
  return <>
    {latest?.status === "failed" && <p role="alert">{latest.error_detail || "Sincronizzazione fallita"}. Puoi avviare una nuova sincronizzazione o usare Retry in Sync Presenze.</p>}
    {latest?.status === "completed" && latest.records_errors > 0 && <p role="alert">Completamento parziale: {latest.records_errors} errori. Verifica lo storico Sync Presenze.</p>}
  </>;
}
function availability(sync: ReturnType<typeof useInazSync>, latest?: PresenzeSyncJob): string {
  if (sync.activeJob) return `Job ${sync.activeJob.status}: ${sync.activeJob.period_start} / ${sync.activeJob.period_end}`;
  if (!sync.ready) return "Verifica disponibilità…";
  if (!sync.credentialId) return "Configura una credenziale INAZ attiva nella pagina Sync Presenze.";
  return latest?.status === "completed" ? "Sincronizzazione completata" : "Sincronizzazione disponibile";
}
export function InazSyncControl({ month, employeeCode, onCompleted }: Props) {
  const sync = useInazSync(month, employeeCode, onCompleted);
  const relevant = relevantInazJobs(sync.jobs, month, employeeCode);
  const lastSuccess = lastSuccessfulInazJob(relevant);
  const running = Boolean(sync.activeJob) || sync.submitting;
  return <div className="space-y-1 rounded border p-3 text-sm print:hidden">
    <button type="button" className="rounded border px-3 py-2 disabled:opacity-50" disabled={!sync.ready || !sync.credentialId || running} onClick={() => void sync.startInazSync()}>{running ? "Sincronizzazione in corso" : "Sincronizza da INAZ"}</button>
    <p role="status">{availability(sync, relevant[0])}</p>
    <p>Ultima sincronizzazione riuscita: {lastSuccess?.finished_at ? new Date(lastSuccess.finished_at).toLocaleString("it-IT") : "nessuna per il periodo selezionato"}</p>
    <InazSyncOutcome latest={relevant[0]} />
    {sync.error && <p role="alert">{sync.error}</p>}
  </div>;
}
