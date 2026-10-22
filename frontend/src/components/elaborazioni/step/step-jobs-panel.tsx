"use client";

import { useState } from "react";

import { ElaborazionePanelHeader } from "@/components/elaborazioni/module-chrome";
import { EmptyState } from "@/components/ui/empty-state";
import { DocumentIcon, RefreshIcon } from "@/components/ui/icons";
import { cancelStepJob, createStepJob, deleteStepJob } from "@/lib/api";
import { formatDateTime } from "@/lib/presentation";
import type { StepJobMode, StepSyncJob, StepSyncJobCreateInput } from "@/types/step";

import { ACTIVE_JOB_STATUSES, formatJobMode, formatJobStatus, jobStatusClassName, summarizeJob } from "./step-format";

type StepJobsPanelProps = {
  token: string;
  jobs: StepSyncJob[];
  archives: string[];
  onChanged: (notice: string | null) => Promise<void>;
  onError: (message: string) => void;
};

type LaunchForm = { mode: StepJobMode; maxDetails: string; forceDetails: boolean; archiveName: string };

const MODE_HINTS: Record<StepJobMode, string> = {
  sync: "Legge tutto l'elenco e apre le schede nuove o cambiate (documenti, tributi, PDF, pagamenti).",
  list_only: "Aggiorna solo le righe dell'elenco contribuenti, senza aprire le schede.",
  archive_import: "Importa un archivio verificato dello scraper dalla cartella import del server.",
  relink: "Ricalcola i collegamenti agli avvisi del ruolo, ad esempio dopo un nuovo import ruolo.",
};

function buildPayload(form: LaunchForm): StepSyncJobCreateInput {
  if (form.mode === "archive_import") return { mode: form.mode, archive_name: form.archiveName };
  if (form.mode !== "sync") return { mode: form.mode };
  return {
    mode: form.mode,
    max_details: form.maxDetails ? Number(form.maxDetails) : null,
    force_details: form.forceDetails,
  };
}

function SyncOptions({ form, onChange }: { form: LaunchForm; onChange: (form: LaunchForm) => void }) {
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      <label className="text-sm font-medium text-gray-700">
        Massimo schede (vuoto = tutte)
        <input
          aria-label="Massimo schede"
          className="input mt-1"
          min={1}
          onChange={(event) => onChange({ ...form, maxDetails: event.target.value })}
          type="number"
          value={form.maxDetails}
        />
      </label>
      <label className="flex items-center gap-2 text-sm font-medium text-gray-700">
        <input
          checked={form.forceDetails}
          onChange={(event) => onChange({ ...form, forceDetails: event.target.checked })}
          type="checkbox"
        />
        Rileggi tutte le schede
      </label>
    </div>
  );
}

function ArchiveOptions({ form, archives, onChange }: { form: LaunchForm; archives: string[]; onChange: (form: LaunchForm) => void }) {
  if (archives.length === 0) {
    return <p className="text-sm text-amber-700">Nessun archivio .zip nella cartella import STEP del server.</p>;
  }
  return (
    <label className="text-sm font-medium text-gray-700">
      Archivio
      <select aria-label="Archivio" className="input mt-1" onChange={(event) => onChange({ ...form, archiveName: event.target.value })} value={form.archiveName}>
        <option value="">Seleziona archivio</option>
        {archives.map((name) => (
          <option key={name} value={name}>
            {name}
          </option>
        ))}
      </select>
    </label>
  );
}

function JobRow({ job, busy, onAction }: { job: StepSyncJob; busy: boolean; onAction: (action: "cancel" | "delete", job: StepSyncJob) => void }) {
  const active = ACTIVE_JOB_STATUSES.has(job.status);
  return (
    <tr>
      <td className="px-4 py-3 font-medium text-gray-900">
        #{job.id} · {formatJobMode(job.mode)}
      </td>
      <td className="px-4 py-3">
        <span className={`rounded-full border px-2.5 py-1 text-xs font-semibold ${jobStatusClassName(job.status)}`}>{formatJobStatus(job.status)}</span>
      </td>
      <td className="px-4 py-3 text-gray-600">{summarizeJob(job)}</td>
      <td className="px-4 py-3 text-gray-500">{formatDateTime(job.updated_at)}</td>
      <td className="px-4 py-3 text-right">
        {job.status === "pending" ? (
          <button className="btn-secondary" disabled={busy} onClick={() => onAction("cancel", job)} type="button">
            Annulla
          </button>
        ) : null}
        {!active ? (
          <button className="btn-secondary" disabled={busy} onClick={() => onAction("delete", job)} type="button">
            Elimina
          </button>
        ) : null}
      </td>
    </tr>
  );
}

export function StepJobsPanel({ token, jobs, archives, onChanged, onError }: StepJobsPanelProps) {
  const [form, setForm] = useState<LaunchForm>({ mode: "sync", maxDetails: "", forceDetails: false, archiveName: "" });
  const [busy, setBusy] = useState(false);
  const canLaunch = form.mode !== "archive_import" || Boolean(form.archiveName);

  async function run(operation: () => Promise<unknown>, notice: string | null): Promise<void> {
    setBusy(true);
    try {
      await operation();
      await onChanged(notice);
    } catch (error) {
      onError(error instanceof Error ? error.message : "Operazione job STEP non riuscita");
    } finally {
      setBusy(false);
    }
  }

  function handleAction(action: "cancel" | "delete", job: StepSyncJob): void {
    void run(() => (action === "cancel" ? cancelStepJob(token, job.id) : deleteStepJob(token, job.id)), null);
  }

  return (
    <section className="overflow-hidden rounded-[24px] border border-[#d9dfd6] bg-white shadow-sm">
      <ElaborazionePanelHeader
        badge="Job"
        title="Sincronizzazione dal worker"
        description="Un solo job STEP alla volta. Il worker legge il portale in sola lettura e non modifica dati su STEP."
        actions={
          <button className="btn-secondary" onClick={() => void onChanged(null)} type="button">
            <RefreshIcon className="mr-2 h-4 w-4" />
            Aggiorna
          </button>
        }
      />
      <div className="space-y-5 p-6">
        <div className="space-y-3 rounded-[22px] border border-[#dce8df] bg-[#f6faf7] p-5">
          <label className="block text-sm font-medium text-gray-700">
            Operazione
            <select aria-label="Operazione" className="input mt-1" onChange={(event) => setForm({ ...form, mode: event.target.value as StepJobMode })} value={form.mode}>
              <option value="sync">Sincronizzazione</option>
              <option value="list_only">Solo elenco</option>
              <option value="archive_import">Import archivio</option>
              <option value="relink">Ricollega al ruolo</option>
            </select>
          </label>
          <p className="text-xs text-gray-500">{MODE_HINTS[form.mode]}</p>
          {form.mode === "sync" ? <SyncOptions form={form} onChange={setForm} /> : null}
          {form.mode === "archive_import" ? <ArchiveOptions archives={archives} form={form} onChange={setForm} /> : null}
          <button className="btn-primary" disabled={busy || !canLaunch} onClick={() => void run(() => createStepJob(token, buildPayload(form)), "Job STEP accodato sul worker.")} type="button">
            {busy ? "Accodamento..." : "Avvia"}
          </button>
        </div>
        {jobs.length === 0 ? (
          <EmptyState icon={DocumentIcon} title="Nessun job STEP" description="Avvia un import o una sincronizzazione per iniziare." />
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
                {jobs.map((job) => (
                  <JobRow key={job.id} busy={busy} job={job} onAction={handleAction} />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </section>
  );
}
