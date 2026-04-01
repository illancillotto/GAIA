"use client";

import { useCallback, useEffect, useState } from "react";

import { UtenzeModulePage } from "@/components/utenze/utenze-module-page";
import { EmptyState } from "@/components/ui/empty-state";
import { FolderIcon } from "@/components/ui/icons";
import {
  getUtenzeImportJob,
  getUtenzeImportJobs,
  previewUtenzeImport,
  resetUtenzeData,
  runUtenzeImport,
  runUtenzeImportFromSubjects,
} from "@/lib/api";
import { formatDateTime } from "@/lib/presentation";
import type { UtenzeImportJob, UtenzeImportPreview, UtenzeImportRunResult, UtenzeResetResult } from "@/types/api";

function ImportContent({ token }: { token: string }) {
  const [preview, setPreview] = useState<UtenzeImportPreview | null>(null);
  const [jobs, setJobs] = useState<UtenzeImportJob[]>([]);
  const [runResult, setRunResult] = useState<UtenzeImportRunResult | null>(null);
  const [selectedJob, setSelectedJob] = useState<UtenzeImportJob | null>(null);
  const [bulkRunResult, setBulkRunResult] = useState<UtenzeImportRunResult | null>(null);
  const [resetResult, setResetResult] = useState<UtenzeResetResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isPreviewing, setIsPreviewing] = useState(false);
  const [isSavingSnapshot, setIsSavingSnapshot] = useState(false);
  const [isRunningBulkImport, setIsRunningBulkImport] = useState(false);
  const [isResetting, setIsResetting] = useState(false);
  const [isBulkImportModalOpen, setIsBulkImportModalOpen] = useState(false);
  const [activeBulkJob, setActiveBulkJob] = useState<UtenzeImportJob | null>(null);

  const loadJobs = useCallback(async () => {
    try {
      const response = await getUtenzeImportJobs(token);
      setJobs(response);
      setActiveBulkJob((current) => {
        if (current) {
          return response.find((job) => job.job_id === current.job_id) ?? current;
        }
        return null;
      });
      setSelectedJob((current) => {
        if (!current) {
          return response[0] ?? null;
        }
        return response.find((job) => job.job_id === current.job_id) ?? response[0] ?? null;
      });
    } catch {
      setJobs([]);
    }
  }, [token]);

  useEffect(() => {
    void loadJobs();
  }, [loadJobs]);

  useEffect(() => {
    if (!isRunningBulkImport && activeBulkJob?.status !== "running") {
      return;
    }

    const intervalId = window.setInterval(() => {
      void loadJobs();
    }, 1500);

    return () => window.clearInterval(intervalId);
  }, [activeBulkJob?.status, isRunningBulkImport, loadJobs]);

  async function handlePreview() {
    setIsPreviewing(true);
    setError(null);
    try {
      const response = await previewUtenzeImport(token);
      setPreview(response);
      setRunResult(null);
      setBulkRunResult(null);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Errore preview import");
    } finally {
      setIsPreviewing(false);
    }
  }

  async function handleSaveSnapshot() {
    setIsSavingSnapshot(true);
    setError(null);
    try {
      const response = await runUtenzeImport(token);
      setRunResult(response);
      setBulkRunResult(null);
      const job = await getUtenzeImportJob(token, response.job_id);
      setSelectedJob(job);
      await loadJobs();
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Errore salvataggio snapshot");
    } finally {
      setIsSavingSnapshot(false);
    }
  }

  async function handleRunBulkImport() {
    setIsBulkImportModalOpen(false);
    setIsRunningBulkImport(true);
    const startedAt = Date.now();
    setActiveBulkJob(null);
    setError(null);
    setResetResult(null);
    let pollTimer: number | null = null;
    try {
      pollTimer = window.setInterval(async () => {
        try {
          const response = await getUtenzeImportJobs(token);
          setJobs(response);
          const candidate = response.find((job) => {
            if (job.letter !== "REGISTRY") {
              return false;
            }
            return new Date(job.created_at).getTime() >= startedAt - 5000;
          });
          if (candidate) {
            setActiveBulkJob(candidate);
            setSelectedJob(candidate);
          }
        } catch {
          // Keep the main import request running even if polling fails intermittently.
        }
      }, 1200);

      const response = await runUtenzeImportFromSubjects(token);
      setBulkRunResult(response);
      setRunResult(null);
      const job = await getUtenzeImportJob(token, response.job_id);
      setActiveBulkJob(job);
      setSelectedJob(job);
      await loadJobs();
    } catch (runError) {
      setError(runError instanceof Error ? runError.message : "Errore import massivo da utenze");
    } finally {
      if (pollTimer !== null) {
        window.clearInterval(pollTimer);
      }
      setIsRunningBulkImport(false);
    }
  }

  const bulkJobProgress = activeBulkJob
    ? Math.round((((activeBulkJob.completed_items + activeBulkJob.failed_items) / Math.max(activeBulkJob.total_folders, 1)) * 100))
    : 0;

  async function handleReset() {
    if (typeof window !== "undefined" && !window.confirm("Confermi la pulizia dei dati importati dal NAS? Le anagrafiche resteranno intatte.")) {
      return;
    }

    setIsResetting(true);
    setError(null);
    try {
      const response = await resetUtenzeData(token);
      setResetResult(response);
      setPreview(null);
      setRunResult(null);
      setBulkRunResult(null);
      setSelectedJob(null);
      await loadJobs();
    } catch (resetError) {
      setError(resetError instanceof Error ? resetError.message : "Errore reset utenze");
    } finally {
      setIsResetting(false);
    }
  }

  return (
    <div className="page-stack">
      <article className="panel-card">
        <div className="mb-4">
          <p className="section-title">Import archivio NAS</p>
          <p className="section-copy">Preview/staging archivio completo, import massivo dalle anagrafiche esistenti e reset del modulo.</p>
        </div>
        {error ? <p className="mb-3 text-sm text-red-600">{error}</p> : null}
        <div className="mb-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          Il flusso operativo ora parte dalle anagrafiche già presenti: il sistema cerca sul NAS la cartella corretta per lettera, importa i file e li collega al soggetto. Lo snapshot resta disponibile come staging diagnostico dell’archivio completo.
        </div>
        <div className="flex flex-wrap items-end gap-3">
          <button className="btn-secondary" type="button" onClick={() => void handlePreview()} disabled={isPreviewing}>
            {isPreviewing ? "Anteprima..." : "Genera preview archivio"}
          </button>
          <button className="btn-primary" type="button" onClick={() => void handleSaveSnapshot()} disabled={isSavingSnapshot}>
            {isSavingSnapshot ? "Salvataggio..." : "Salva snapshot"}
          </button>
          <button className="btn-primary" type="button" onClick={() => setIsBulkImportModalOpen(true)} disabled={isRunningBulkImport}>
          {isRunningBulkImport ? "Import massivo..." : "Importa da utenze"}
          </button>
          <button className="btn-secondary" type="button" onClick={() => void handleReset()} disabled={isResetting}>
            {isResetting ? "Reset..." : "Pulisci dati importati NAS"}
          </button>
        </div>
      </article>

      {isBulkImportModalOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
          <div className="w-full max-w-xl rounded-2xl bg-white p-6 shadow-2xl">
            <div className="mb-4">
              <p className="section-title">Import massivo da utenze</p>
              <p className="section-copy mt-2">
                Il sistema proverà a trovare per ogni soggetto la cartella NAS più probabile in base a lettera archivio, nominativo e identificativi, poi importerà i documenti collegandoli alla scheda.
              </p>
            </div>

            <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
              Usa questo flusso solo quando vuoi lanciare un’importazione su tutto il database Utenze. Per casi ambigui o sporchi è meglio partire dalla scheda singola e scegliere manualmente la cartella NAS.
            </div>

            <div className="mt-6 flex justify-end gap-3">
              <button className="btn-secondary" type="button" onClick={() => setIsBulkImportModalOpen(false)} disabled={isRunningBulkImport}>
                Annulla
              </button>
              <button className="btn-primary" type="button" onClick={() => void handleRunBulkImport()} disabled={isRunningBulkImport}>
                {isRunningBulkImport ? "Import in corso..." : "Conferma import massivo"}
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {isRunningBulkImport || activeBulkJob?.status === "running" ? (
        <article className="panel-card border border-sky-100 bg-sky-50/70">
          <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="section-title">Import massivo in corso</p>
              <p className="section-copy">
                {activeBulkJob
                  ? `Job ${activeBulkJob.job_id} in esecuzione su ${activeBulkJob.total_folders} soggetti.`
                  : "Preparazione del job REGISTRY e avvio della sincronizzazione dalle anagrafiche."}
              </p>
            </div>
            <span className="rounded-full bg-sky-100 px-3 py-1 text-xs font-medium text-sky-800">
              {activeBulkJob?.status === "running" ? "running" : "starting"}
            </span>
          </div>
          <div className="overflow-hidden rounded-full bg-white">
            <div className="h-3 bg-sky-600 transition-all" style={{ width: `${bulkJobProgress}%` }} />
          </div>
          <div className="mt-3 grid gap-3 md:grid-cols-5">
            <div className="rounded-xl border border-sky-100 bg-white p-4">
              <p className="text-xs uppercase tracking-widest text-gray-400">Avanzamento</p>
              <p className="mt-2 text-2xl font-semibold text-gray-900">{bulkJobProgress}%</p>
            </div>
            <div className="rounded-xl border border-sky-100 bg-white p-4">
              <p className="text-xs uppercase tracking-widest text-gray-400">Totale</p>
              <p className="mt-2 text-2xl font-semibold text-gray-900">{activeBulkJob?.total_folders ?? "..."}</p>
            </div>
            <div className="rounded-xl border border-sky-100 bg-white p-4">
              <p className="text-xs uppercase tracking-widest text-gray-400">Completati</p>
              <p className="mt-2 text-2xl font-semibold text-emerald-700">{activeBulkJob?.completed_items ?? 0}</p>
            </div>
            <div className="rounded-xl border border-sky-100 bg-white p-4">
              <p className="text-xs uppercase tracking-widest text-gray-400">In lavorazione</p>
              <p className="mt-2 text-2xl font-semibold text-sky-700">{activeBulkJob?.running_items ?? 0}</p>
            </div>
            <div className="rounded-xl border border-sky-100 bg-white p-4">
              <p className="text-xs uppercase tracking-widest text-gray-400">Errori</p>
              <p className="mt-2 text-2xl font-semibold text-rose-700">{activeBulkJob?.failed_items ?? 0}</p>
            </div>
          </div>
          <p className="mt-4 text-sm text-gray-600">
            L&apos;import massivo rielabora i soggetti esistenti e aggiorna i documenti trovati sullo stesso `nas_path`; non duplica i soggetti. Se un file cambia path sul NAS, viene trattato come nuovo documento.
          </p>
        </article>
      ) : null}

      {preview ? (
        <article className="panel-card">
          <div className="mb-4">
            <p className="section-title">{preview.letter === "ALL" ? "Preview archivio completo" : `Preview lettera ${preview.letter}`}</p>
            <p className="section-copy">
              {preview.total_folders} cartelle · {preview.parsed_subjects} soggetti · {preview.total_documents} documenti
            </p>
          </div>
          {preview.total_folders === 0 ? (
            <p className="mb-4 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
              Nessuna cartella trovata nell’archivio NAS configurato. Verifica il path archivio o il contenuto disponibile sul NAS.
            </p>
          ) : null}
          <div className="grid gap-3 md:grid-cols-4">
            <div className="rounded-xl border border-gray-100 bg-gray-50 p-4">
              <p className="text-xs uppercase tracking-widest text-gray-400">Review</p>
              <p className="mt-2 text-2xl font-semibold text-gray-900">{preview.subjects_requiring_review}</p>
            </div>
            <div className="rounded-xl border border-gray-100 bg-gray-50 p-4">
              <p className="text-xs uppercase tracking-widest text-gray-400">Non PDF</p>
              <p className="mt-2 text-2xl font-semibold text-gray-900">{preview.non_pdf_documents}</p>
            </div>
            <div className="rounded-xl border border-gray-100 bg-gray-50 p-4">
              <p className="text-xs uppercase tracking-widest text-gray-400">Warning</p>
              <p className="mt-2 text-2xl font-semibold text-gray-900">{preview.warnings.length}</p>
            </div>
            <div className="rounded-xl border border-gray-100 bg-gray-50 p-4">
              <p className="text-xs uppercase tracking-widest text-gray-400">Errori</p>
              <p className="mt-2 text-2xl font-semibold text-gray-900">{preview.errors.length}</p>
            </div>
          </div>
          <div className="mt-5 space-y-3">
            {preview.subjects.slice(0, 12).map((subject) => (
              <div key={subject.nas_folder_path} className="rounded-lg border border-gray-100 px-4 py-3">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <p className="text-sm font-medium text-gray-900">
                      {subject.subject_type === "person"
                        ? `${subject.cognome || ""} ${subject.nome || ""}`.trim() || subject.source_name_raw
                        : subject.ragione_sociale || subject.source_name_raw}
                    </p>
                    <p className="mt-1 text-xs text-gray-500">
                      {subject.codice_fiscale || subject.partita_iva || "Identificativo non disponibile"} · {subject.documents.length} documenti
                    </p>
                  </div>
                  <span className={`rounded-full px-2 py-1 text-[11px] font-medium ${subject.requires_review ? "bg-amber-50 text-amber-700" : "bg-emerald-50 text-emerald-700"}`}>
                    {subject.requires_review ? "Review" : "OK"}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </article>
      ) : (
        <article className="panel-card">
          <EmptyState icon={FolderIcon} title="Nessuna preview disponibile" description="Genera una preview dell’archivio completo per ispezionare cartelle, warning e documenti prima del commit import." />
        </article>
      )}

      {runResult ? (
        <article className="panel-card">
          <div className="mb-3">
            <p className="section-title">Ultimo snapshot salvato</p>
            <p className="section-copy">Snapshot {runResult.job_id} con stato {runResult.status}.</p>
          </div>
          <div className="grid gap-3 md:grid-cols-4">
            <div className="rounded-xl border border-gray-100 bg-gray-50 p-4">
              <p className="text-xs uppercase tracking-widest text-gray-400">Cartelle</p>
              <p className="mt-2 text-2xl font-semibold text-gray-900">{runResult.total_folders}</p>
            </div>
            <div className="rounded-xl border border-gray-100 bg-gray-50 p-4">
              <p className="text-xs uppercase tracking-widest text-gray-400">Soggetti parsati</p>
              <p className="mt-2 text-2xl font-semibold text-gray-900">{runResult.imported_ok}</p>
            </div>
            <div className="rounded-xl border border-gray-100 bg-gray-50 p-4">
              <p className="text-xs uppercase tracking-widest text-gray-400">Warning</p>
              <p className="mt-2 text-2xl font-semibold text-gray-900">{runResult.warning_count}</p>
            </div>
            <div className="rounded-xl border border-gray-100 bg-gray-50 p-4">
              <p className="text-xs uppercase tracking-widest text-gray-400">Errori</p>
              <p className="mt-2 text-2xl font-semibold text-gray-900">{runResult.imported_errors}</p>
            </div>
          </div>
        </article>
      ) : null}

      {bulkRunResult ? (
        <article className="panel-card">
          <div className="mb-3">
            <p className="section-title">Ultimo import massivo da anagrafiche</p>
            <p className="section-copy">Job {bulkRunResult.job_id} con stato {bulkRunResult.status}.</p>
          </div>
          <div className="grid gap-3 md:grid-cols-4">
            <div className="rounded-xl border border-gray-100 bg-gray-50 p-4">
              <p className="text-xs uppercase tracking-widest text-gray-400">Soggetti processati</p>
              <p className="mt-2 text-2xl font-semibold text-gray-900">{bulkRunResult.imported_ok}</p>
            </div>
            <div className="rounded-xl border border-gray-100 bg-gray-50 p-4">
              <p className="text-xs uppercase tracking-widest text-gray-400">Errori</p>
              <p className="mt-2 text-2xl font-semibold text-gray-900">{bulkRunResult.imported_errors}</p>
            </div>
            <div className="rounded-xl border border-gray-100 bg-gray-50 p-4">
              <p className="text-xs uppercase tracking-widest text-gray-400">Doc creati</p>
              <p className="mt-2 text-2xl font-semibold text-gray-900">{bulkRunResult.created_documents}</p>
            </div>
            <div className="rounded-xl border border-gray-100 bg-gray-50 p-4">
              <p className="text-xs uppercase tracking-widest text-gray-400">Doc aggiornati</p>
              <p className="mt-2 text-2xl font-semibold text-gray-900">{bulkRunResult.updated_documents}</p>
            </div>
          </div>
        </article>
      ) : null}

      {resetResult ? (
        <article className="panel-card">
          <div className="mb-3">
            <p className="section-title">Reset completato</p>
            <p className="section-copy">Pulizia dei soli dati importati dal NAS. Le anagrafiche sono state mantenute.</p>
          </div>
          <div className="grid gap-3 md:grid-cols-3 xl:grid-cols-6">
            <div className="rounded-xl border border-gray-100 bg-gray-50 p-4">
              <p className="text-xs uppercase tracking-widest text-gray-400">Link NAS puliti</p>
              <p className="mt-2 text-2xl font-semibold text-gray-900">{resetResult.cleared_subject_links}</p>
            </div>
            <div className="rounded-xl border border-gray-100 bg-gray-50 p-4">
              <p className="text-xs uppercase tracking-widest text-gray-400">Documenti</p>
              <p className="mt-2 text-2xl font-semibold text-gray-900">{resetResult.deleted_documents}</p>
            </div>
            <div className="rounded-xl border border-gray-100 bg-gray-50 p-4">
              <p className="text-xs uppercase tracking-widest text-gray-400">Audit</p>
              <p className="mt-2 text-2xl font-semibold text-gray-900">{resetResult.deleted_audit_logs}</p>
            </div>
            <div className="rounded-xl border border-gray-100 bg-gray-50 p-4">
              <p className="text-xs uppercase tracking-widest text-gray-400">Job</p>
              <p className="mt-2 text-2xl font-semibold text-gray-900">{resetResult.deleted_import_jobs}</p>
            </div>
            <div className="rounded-xl border border-gray-100 bg-gray-50 p-4">
              <p className="text-xs uppercase tracking-widest text-gray-400">Item job</p>
              <p className="mt-2 text-2xl font-semibold text-gray-900">{resetResult.deleted_import_job_items}</p>
            </div>
            <div className="rounded-xl border border-gray-100 bg-gray-50 p-4">
              <p className="text-xs uppercase tracking-widest text-gray-400">File locali</p>
              <p className="mt-2 text-2xl font-semibold text-gray-900">{resetResult.deleted_storage_files}</p>
            </div>
          </div>
        </article>
      ) : null}

      {selectedJob ? (
        <article className="panel-card">
          <div className="mb-4 flex items-center justify-between gap-3">
            <div>
              <p className="section-title">Dettaglio snapshot</p>
              <p className="section-copy">Snapshot {selectedJob.job_id} con {selectedJob.completed_items} soggetti salvati e {selectedJob.failed_items} errori.</p>
            </div>
            <span className="rounded-full bg-sky-50 px-3 py-1 text-xs font-medium text-sky-800">Staging</span>
          </div>
          <div className="space-y-2">
            {selectedJob.items.length === 0 ? (
              <p className="text-sm text-gray-500">Nessun item disponibile per questo job.</p>
            ) : (
              selectedJob.items.slice(0, 50).map((item) => (
                <div key={item.id} className="rounded-lg border border-gray-100 px-4 py-3">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="text-sm font-medium text-gray-900">{item.folder_name}</p>
                      <p className="mt-1 text-xs text-gray-500">{item.nas_folder_path}</p>
                    </div>
                    <span className="rounded-full bg-gray-100 px-2 py-1 text-[11px] font-medium text-gray-700">{item.status}</span>
                  </div>
                  <p className="mt-2 text-xs text-gray-500">
                    tentativi {item.attempt_count} · doc creati {item.documents_created} · doc aggiornati {item.documents_updated} · warning {item.warning_count}
                  </p>
                  {item.payload_json && !Array.isArray(item.payload_json) ? (
                    <p className="mt-2 text-xs text-gray-500">
                      tipo {(item.payload_json.subject_type as string) || "unknown"} · review {item.payload_json.requires_review ? "si" : "no"}
                    </p>
                  ) : null}
                  {item.last_error ? <p className="mt-2 text-xs text-red-600">{item.last_error}</p> : null}
                </div>
              ))
            )}
          </div>
        </article>
      ) : null}

      <article className="panel-card">
        <div className="mb-4">
          <p className="section-title">Storico snapshot</p>
          <p className="section-copy">Ultime acquisizioni di staging registrate nel backend.</p>
        </div>
        {jobs.length === 0 ? (
          <p className="text-sm text-gray-500">Nessuno snapshot disponibile.</p>
        ) : (
          <div className="space-y-3">
            {jobs.map((job) => (
              <div key={job.job_id} className="rounded-lg border border-gray-100 px-4 py-3">
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-sm font-medium text-gray-900">
                      {job.letter === "ALL" ? "Archivio completo" : job.letter === "REGISTRY" ? "Import da anagrafiche" : `Lettera ${job.letter || "?"}`}
                    </p>
                    <div className="flex items-center gap-2">
                      <button className="text-xs font-medium text-[#1D4E35]" type="button" onClick={() => setSelectedJob(job)}>
                        Dettaglio
                    </button>
                    <span className="rounded-full bg-gray-100 px-2 py-1 text-[11px] font-medium text-gray-700">{job.status}</span>
                  </div>
                </div>
                <p className="mt-2 text-xs text-gray-500">
                  {job.completed_items} soggetti salvati · {job.warning_count} warning · {job.failed_items} errori
                </p>
                <p className="mt-1 text-xs text-gray-400">{formatDateTime(job.completed_at || job.created_at)}</p>
              </div>
            ))}
          </div>
        )}
      </article>
    </div>
  );
}

export default function UtenzeImportPage() {
  return (
    <UtenzeModulePage
      title="Import archivio"
      description="Import singolo o massivo dei documenti NAS a partire dalle utenze esistenti, con snapshot e reset operativo."
      breadcrumb="Import"
    >
      {({ token }) => <ImportContent token={token} />}
    </UtenzeModulePage>
  );
}
