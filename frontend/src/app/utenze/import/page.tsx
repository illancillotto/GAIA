"use client";

import { useCallback, useEffect, useState } from "react";

import { ElaborazionePanelHeader } from "@/components/elaborazioni/module-chrome";
import { ModuleWorkspaceHero, ModuleWorkspaceMiniStat } from "@/components/layout/module-workspace-hero";
import { UtenzeModulePage } from "@/components/utenze/utenze-module-page";
import { EmptyState } from "@/components/ui/empty-state";
import { DocumentIcon, FolderIcon, RefreshIcon, ServerIcon } from "@/components/ui/icons";
import {
  abortUtenzeRegistryImportJob,
  deleteUtenzeRegistryImportJob,
  getUtenzeImportJob,
  getUtenzeImportJobs,
  getUtenzeXlsxImportBatch,
  getUtenzeXlsxImportBatches,
  importUtenzeSubjectsXlsx,
  previewUtenzeImport,
  resetUtenzeData,
  resumeUtenzeRegistryImportJob,
  runUtenzeImport,
  runUtenzeImportFromSubjects,
} from "@/lib/api";
import { formatDateTime } from "@/lib/presentation";
import type { UtenzeImportJob, UtenzeImportPreview, UtenzeImportRunResult, UtenzeResetResult, XlsxImportBatch } from "@/types/api";

function registryBulkDocTotals(job: UtenzeImportJob): { created: number; updated: number } {
  const log = job.log_json;
  if (log && typeof log === "object" && !Array.isArray(log)) {
    const c = log["created_documents"];
    const u = log["updated_documents"];
    if (typeof c === "number" && typeof u === "number") {
      return { created: c, updated: u };
    }
  }
  return {
    created: job.items.reduce((sum, item) => sum + item.documents_created, 0),
    updated: job.items.reduce((sum, item) => sum + item.documents_updated, 0),
  };
}

function jobToBulkRunResult(job: UtenzeImportJob): UtenzeImportRunResult {
  const docs = registryBulkDocTotals(job);
  return {
    job_id: job.job_id,
    letter: job.letter ?? "REGISTRY",
    status: job.status,
    total_folders: job.total_folders,
    imported_ok: job.imported_ok,
    imported_errors: job.imported_errors,
    warning_count: job.warning_count,
    pending_items: job.pending_items,
    running_items: job.running_items,
    completed_items: job.completed_items,
    failed_items: job.failed_items,
    created_subjects: 0,
    updated_subjects: job.completed_items,
    created_documents: docs.created,
    updated_documents: docs.updated,
    generated_at: job.started_at ?? job.created_at,
    completed_at: job.completed_at,
    log_json: job.log_json,
  };
}

function isRegistryJobActive(job: Pick<UtenzeImportJob, "status"> | null | undefined): boolean {
  return job?.status === "pending" || job?.status === "running";
}

type UtenzeImportSection = "excel" | "nas";

const UTENZE_IMPORT_SECTIONS: Array<{ id: UtenzeImportSection; label: string; description: string }> = [
  { id: "excel", label: "Anagrafica Excel", description: "Upload .xlsx, avanzamento e storico batch" },
  {
    id: "nas",
    label: "Archivio NAS",
    description: "Preview, snapshot, aggiornamento utenze, reset e cronologia job NAS",
  },
];

const NAS_PANEL_DESCRIPTION_TOOLTIP =
  "Preview: legge il NAS e mostra solo un'anteprima in memoria, senza scrivere nel database. Snapshot: salva un job con tutti gli item rilevati (staging diagnostico), senza creare documenti né aggiornare le schede. Aggiorna utenze: per ogni soggetto già in anagrafica trova la cartella NAS più probabile e aggiorna i documenti collegati. Reset: elimina documenti importati, job, audit collegati e file locali; azzera i campi NAS sulle schede ma non cancella i soggetti.";

const NAS_PREVIEW_BUTTON_TOOLTIP =
  "Scansione read-only dell'archivio NAS: cartelle, soggetti parsati, documenti e warning. Non persiste nulla a database.";
const NAS_SNAPSHOT_BUTTON_TOOLTIP =
  "Come la preview ma salva un job completato con tutti gli item (utile per audit e diagnosi). Non importa PDF né modifica le anagrafiche.";
const NAS_BULK_BUTTON_TOOLTIP =
  "Per ogni soggetto in anagrafica abbina la cartella NAS e crea o aggiorna i documenti in GAIA (job REGISTRY). Operazione massiva di allineamento.";
const NAS_RESET_BUTTON_TOOLTIP =
  "Rimuove documenti, job di import, traccia audit import e copie locali; azzera nas_folder e link sui soggetti. Le anagrafiche restano.";

function ImportContent({ token }: { token: string }) {
  const [activeSection, setActiveSection] = useState<UtenzeImportSection>("excel");
  const [preview, setPreview] = useState<UtenzeImportPreview | null>(null);
  const [jobs, setJobs] = useState<UtenzeImportJob[]>([]);
  const [runResult, setRunResult] = useState<UtenzeImportRunResult | null>(null);
  const [selectedJob, setSelectedJob] = useState<UtenzeImportJob | null>(null);
  const [bulkRunResult, setBulkRunResult] = useState<UtenzeImportRunResult | null>(null);
  const [resetResult, setResetResult] = useState<UtenzeResetResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isPreviewing, setIsPreviewing] = useState(false);
  const [isSavingSnapshot, setIsSavingSnapshot] = useState(false);
  const [isBulkPostPending, setIsBulkPostPending] = useState(false);
  const [bulkTrackingJobId, setBulkTrackingJobId] = useState<string | null>(null);
  const [isResetting, setIsResetting] = useState(false);
  const [isBulkImportModalOpen, setIsBulkImportModalOpen] = useState(false);
  const [activeBulkJob, setActiveBulkJob] = useState<UtenzeImportJob | null>(null);
  const [registryMutationJobId, setRegistryMutationJobId] = useState<string | null>(null);

  const [xlsxFile, setXlsxFile] = useState<File | null>(null);
  const [xlsxBatches, setXlsxBatches] = useState<XlsxImportBatch[]>([]);
  const [xlsxActiveBatch, setXlsxActiveBatch] = useState<XlsxImportBatch | null>(null);
  const [xlsxUploading, setXlsxUploading] = useState(false);
  const [xlsxUploadProgress, setXlsxUploadProgress] = useState(0);
  const [xlsxError, setXlsxError] = useState<string | null>(null);

  const loadXlsxBatches = useCallback(async () => {
    try {
      const batches = await getUtenzeXlsxImportBatches(token);
      setXlsxBatches(batches);
      setXlsxActiveBatch((current) => {
        if (!current) return batches[0] ?? null;
        return batches.find((b) => b.id === current.id) ?? batches[0] ?? null;
      });
    } catch {
      // non bloccante
    }
  }, [token]);

  useEffect(() => {
    void loadXlsxBatches();
  }, [loadXlsxBatches]);

  const xlsxActiveBatchStatus = xlsxActiveBatch?.status;

  useEffect(() => {
    if (!xlsxActiveBatchStatus || xlsxActiveBatchStatus === "completed" || xlsxActiveBatchStatus === "failed") return;
    const id = window.setInterval(() => void loadXlsxBatches(), 1500);
    return () => window.clearInterval(id);
  }, [xlsxActiveBatchStatus, loadXlsxBatches]);

  async function handleXlsxImport() {
    if (!xlsxFile) return;
    setXlsxUploading(true);
    setXlsxError(null);
    setXlsxUploadProgress(0);
    try {
      const result = await importUtenzeSubjectsXlsx(token, xlsxFile, setXlsxUploadProgress);
      const batch = await getUtenzeXlsxImportBatch(token, result.batch_id);
      setXlsxActiveBatch(batch);
      setXlsxFile(null);
      await loadXlsxBatches();
    } catch (err) {
      setXlsxError(err instanceof Error ? err.message : "Errore import Excel");
    } finally {
      setXlsxUploading(false);
      setXlsxUploadProgress(0);
    }
  }

  const loadJobs = useCallback(async () => {
    try {
      const response = await getUtenzeImportJobs(token);
      setJobs(response);
      setActiveBulkJob((current) => {
        if (!current) return current;
        return response.find((job) => job.job_id === current.job_id) ?? current;
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
    if (!bulkTrackingJobId) {
      return;
    }

    let cancelled = false;

    async function pollOnce() {
      try {
        const job = await getUtenzeImportJob(token, bulkTrackingJobId);
        if (cancelled) return;
        setActiveBulkJob(job);
        setSelectedJob((current) => (current?.job_id === job.job_id ? job : current));
        await loadJobs();
        if (!isRegistryJobActive(job)) {
          setBulkTrackingJobId(null);
          setBulkRunResult(jobToBulkRunResult(job));
        }
      } catch {
        // Transient polling errors are ignored; the next tick will retry.
      }
    }

    void pollOnce();
    const intervalId = window.setInterval(() => void pollOnce(), 1200);
    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, [bulkTrackingJobId, token, loadJobs]);

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
    setIsBulkPostPending(true);
    setBulkTrackingJobId(null);
    setActiveBulkJob(null);
    setError(null);
    setResetResult(null);
    setBulkRunResult(null);
    setRunResult(null);
    try {
      const response = await runUtenzeImportFromSubjects(token);
      setBulkTrackingJobId(response.job_id);
      const job = await getUtenzeImportJob(token, response.job_id);
      setActiveBulkJob(job);
      setSelectedJob(job);
      await loadJobs();
    } catch (runError) {
      setError(runError instanceof Error ? runError.message : "Errore durante l'aggiornamento utenze da NAS");
    } finally {
      setIsBulkPostPending(false);
    }
  }

  const bulkJobProgress = activeBulkJob
    ? Math.round((((activeBulkJob.completed_items + activeBulkJob.failed_items) / Math.max(activeBulkJob.total_folders, 1)) * 100))
    : isBulkPostPending
      ? 3
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
      setBulkTrackingJobId(null);
      setActiveBulkJob(null);
      await loadJobs();
    } catch (resetError) {
      setError(resetError instanceof Error ? resetError.message : "Errore reset utenze");
    } finally {
      setIsResetting(false);
    }
  }

  async function handleAbortRegistryJob(jobId: string) {
    setRegistryMutationJobId(jobId);
    setError(null);
    try {
      const updated = await abortUtenzeRegistryImportJob(token, jobId);
      if (bulkTrackingJobId === jobId) {
        setBulkTrackingJobId(null);
      }
      if (activeBulkJob?.job_id === jobId) {
        setActiveBulkJob(updated);
      }
      await loadJobs();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Errore durante l'interruzione del job");
    } finally {
      setRegistryMutationJobId(null);
    }
  }

  async function handleResumeRegistryJob(jobId: string) {
    setRegistryMutationJobId(jobId);
    setError(null);
    try {
      await resumeUtenzeRegistryImportJob(token, jobId);
      setBulkRunResult(null);
      setBulkTrackingJobId(jobId);
      const job = await getUtenzeImportJob(token, jobId);
      setActiveBulkJob(job);
      setSelectedJob(job);
      await loadJobs();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Errore durante la ripresa del job");
    } finally {
      setRegistryMutationJobId(null);
    }
  }

  async function handleDeleteRegistryJob(jobId: string) {
    if (typeof window !== "undefined" && !window.confirm("Eliminare questo job dallo storico? I soggetti e i documenti già importati non vengono rimossi.")) {
      return;
    }

    setRegistryMutationJobId(jobId);
    setError(null);
    try {
      await deleteUtenzeRegistryImportJob(token, jobId);
      if (bulkTrackingJobId === jobId) {
        setBulkTrackingJobId(null);
      }
      if (activeBulkJob?.job_id === jobId) {
        setActiveBulkJob(null);
      }
      if (selectedJob?.job_id === jobId) {
        setSelectedJob(null);
      }
      await loadJobs();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Errore durante l'eliminazione del job");
    } finally {
      setRegistryMutationJobId(null);
    }
  }

  const xlsxProgress = xlsxActiveBatch
    ? Math.round((xlsxActiveBatch.processed_rows / Math.max(xlsxActiveBatch.total_rows, 1)) * 100)
    : 0;

  const bulkInFlight = isBulkPostPending || Boolean(bulkTrackingJobId) || isRegistryJobActive(activeBulkJob);
  const registryImportJobs = jobs.filter((job) => job.letter === "REGISTRY");
  const xlsxTerminalOrIdle =
    !xlsxActiveBatch || xlsxActiveBatch.status === "completed" || xlsxActiveBatch.status === "failed";
  const xlsxRunning = Boolean(xlsxActiveBatch && !xlsxTerminalOrIdle);

  return (
    <>
      <div className="space-y-6">
        <ModuleWorkspaceHero
          badge={
            <>
              <ServerIcon className="h-3.5 w-3.5" />
              Import utenze
            </>
          }
          title="Centro import archivio"
          description="Carica anagrafiche da Excel, sincronizza i documenti dal NAS con le utenze esistenti e consulta preview, snapshot e cronologia job — con stessa struttura di navigazione del workspace Capacitas."
        >
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <ModuleWorkspaceMiniStat
              eyebrow="Batch Excel"
              value={xlsxBatches.length}
              description="Import .xlsx registrati nel backend."
            />
            <ModuleWorkspaceMiniStat
              eyebrow="Ultimo batch Excel"
              value={xlsxActiveBatch?.status ?? "—"}
              description={xlsxActiveBatch?.filename ?? "Nessun batch selezionato."}
              tone={xlsxRunning ? "warning" : "default"}
            />
            <ModuleWorkspaceMiniStat
              eyebrow="Job import"
              value={jobs.length}
              description="Snapshot e job di aggiornamento da anagrafica registrati."
            />
            <ModuleWorkspaceMiniStat
              eyebrow="Aggiorna utenze"
              value={bulkInFlight ? "In corso" : "—"}
              description={bulkInFlight ? "Sincronizzazione soggetti e documenti dal NAS." : "Nessun aggiornamento massivo attivo."}
              tone={bulkInFlight ? "warning" : "default"}
            />
          </div>
        </ModuleWorkspaceHero>

        <nav className="grid gap-3 md:grid-cols-2" aria-label="Sezioni import utenze">
          {UTENZE_IMPORT_SECTIONS.map((section) => {
            const active = activeSection === section.id;
            return (
              <button
                className={
                  active
                    ? "rounded-2xl border border-[#1D4E35] bg-[#eef7ef] px-5 py-4 text-left shadow-sm"
                    : "rounded-2xl border border-[#d9dfd6] bg-white px-5 py-4 text-left shadow-sm transition hover:border-[#1D4E35]/40 hover:bg-[#f8fbf8]"
                }
                key={section.id}
                onClick={() => setActiveSection(section.id)}
                type="button"
              >
                <span className={active ? "text-sm font-semibold text-[#1D4E35]" : "text-sm font-semibold text-gray-900"}>{section.label}</span>
                <span className="mt-1 block text-xs text-gray-500">{section.description}</span>
              </button>
            );
          })}
        </nav>

        {bulkInFlight ? (
          <article className="overflow-hidden rounded-[28px] border border-sky-200 bg-sky-50/90 shadow-panel ring-1 ring-sky-100">
            <div className="space-y-6 p-6">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="section-title">Aggiornamento utenze da NAS</p>
                  <p className="section-copy">
                    {activeBulkJob
                      ? `Job ${activeBulkJob.job_id}: ${activeBulkJob.completed_items + activeBulkJob.failed_items}/${Math.max(activeBulkJob.total_folders, 1)} soggetti elaborati`
                      : "Connessione al server e avvio del job di sincronizzazione…"}
                  </p>
                  {activeBulkJob && activeBulkJob.running_items > 0 ? (
                    <p className="mt-2 text-sm font-medium text-sky-900">Lettura NAS / aggiornamento documenti in corso…</p>
                  ) : activeBulkJob?.status === "pending" ? (
                    <p className="mt-2 text-sm font-medium text-sky-900">Job in coda sul worker, in attesa di presa in carico…</p>
                  ) : null}
                </div>
                <span className="rounded-full bg-sky-100 px-3 py-1 text-xs font-medium text-sky-800">
                  {isBulkPostPending ? "starting" : activeBulkJob?.status ?? "starting"}
                </span>
              </div>
              <div className="overflow-hidden rounded-full bg-white">
                <div className="h-3 bg-sky-600 transition-all" style={{ width: `${bulkJobProgress}%` }} />
              </div>
              <div className="grid gap-3 md:grid-cols-5">
                <div className="rounded-xl border border-sky-100 bg-white p-4">
                  <p className="text-xs uppercase tracking-widest text-gray-400">Avanzamento</p>
                  <p className="mt-2 text-2xl font-semibold text-gray-900">{bulkJobProgress}%</p>
                </div>
                <div className="rounded-xl border border-sky-100 bg-white p-4">
                  <p className="text-xs uppercase tracking-widest text-gray-400">Totale soggetti</p>
                  <p className="mt-2 text-2xl font-semibold text-gray-900">{activeBulkJob?.total_folders ?? "…"}</p>
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
              <p className="text-sm text-gray-600">
                Puoi cambiare sezione (Excel o Archivio NAS): l&apos;avanzamento resta qui sopra finché il job è attivo. Al termine trovi il riepilogo nella sezione NAS (storico aggiornamenti massivi).
              </p>
            </div>
          </article>
        ) : null}

        {activeSection === "excel" ? (
          <article className="overflow-hidden rounded-[28px] border border-[#d9dfd6] bg-white shadow-panel">
            <ElaborazionePanelHeader
              badge={
                <>
                  <DocumentIcon className="h-3.5 w-3.5" />
                  Anagrafica Excel
                </>
              }
              title="Import anagrafica Excel"
              description="Carica il file .xlsx dell'anagrafica per popolare o aggiornare le utenze. Solo amministratori. Per ogni riga viene eseguito un upsert basato su Codice Fiscale / Partita IVA."
            />
            <div className="space-y-6 p-6">
              {xlsxError ? <p className="text-sm text-red-600">{xlsxError}</p> : null}
              <div className="flex flex-wrap items-end gap-3">
                <label className="flex flex-col gap-1">
                  <span className="label-caption">File Excel (.xlsx)</span>
                  <input
                    accept=".xlsx,.xls"
                    className="form-control"
                    disabled={xlsxUploading}
                    type="file"
                    onChange={(e) => setXlsxFile(e.target.files?.[0] ?? null)}
                  />
                </label>
                <button
                  className="btn-primary"
                  disabled={!xlsxFile || xlsxUploading}
                  type="button"
                  onClick={() => void handleXlsxImport()}
                >
                  {xlsxUploading ? `Upload ${xlsxUploadProgress}%...` : "Avvia import anagrafica"}
                </button>
              </div>

              {xlsxRunning ? (
                <div className="rounded-2xl border border-sky-100 bg-sky-50/70 p-5">
                  <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="section-title">Import Excel in corso</p>
                      <p className="section-copy">
                        {xlsxActiveBatch!.filename} · {xlsxActiveBatch!.processed_rows}/{xlsxActiveBatch!.total_rows} righe elaborate
                      </p>
                    </div>
                    <span className="rounded-full bg-sky-100 px-3 py-1 text-xs font-medium text-sky-800">{xlsxActiveBatch!.status}</span>
                  </div>
                  <div className="overflow-hidden rounded-full bg-white">
                    <div className="h-3 bg-sky-600 transition-all" style={{ width: `${xlsxProgress}%` }} />
                  </div>
                  <div className="mt-3 grid gap-3 sm:grid-cols-5">
                    {[
                      { label: "Avanzamento", value: `${xlsxProgress}%` },
                      { label: "Inseriti", value: xlsxActiveBatch!.inserted, tone: "emerald" },
                      { label: "Aggiornati", value: xlsxActiveBatch!.updated, tone: "sky" },
                      { label: "Invariati", value: xlsxActiveBatch!.unchanged },
                      { label: "Anomalie", value: xlsxActiveBatch!.anomalies, tone: "amber" },
                    ].map(({ label, value, tone }) => (
                      <div key={label} className="rounded-xl border border-sky-100 bg-white p-4">
                        <p className="text-xs uppercase tracking-widest text-gray-400">{label}</p>
                        <p
                          className={`mt-2 text-2xl font-semibold ${tone === "emerald" ? "text-emerald-700" : tone === "sky" ? "text-sky-700" : tone === "amber" ? "text-amber-700" : "text-gray-900"}`}
                        >
                          {value}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              ) : null}

              {xlsxActiveBatch && (xlsxActiveBatch.status === "completed" || xlsxActiveBatch.status === "failed") ? (
                <div
                  className={`rounded-2xl border p-5 ${xlsxActiveBatch.status === "failed" ? "border-red-100 bg-red-50/50" : "border-gray-100 bg-gray-50/50"}`}
                >
                  <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="section-title">{xlsxActiveBatch.status === "completed" ? "Import Excel completato" : "Import Excel fallito"}</p>
                      <p className="section-copy">
                        {xlsxActiveBatch.filename} · {formatDateTime(xlsxActiveBatch.completed_at ?? xlsxActiveBatch.created_at)}
                      </p>
                    </div>
                    <span
                      className={`rounded-full px-3 py-1 text-xs font-medium ${xlsxActiveBatch.status === "completed" ? "bg-emerald-50 text-emerald-800" : "bg-red-50 text-red-800"}`}
                    >
                      {xlsxActiveBatch.status}
                    </span>
                  </div>
                  <div className="grid gap-3 sm:grid-cols-3 lg:grid-cols-6">
                    {[
                      { label: "Totale righe", value: xlsxActiveBatch.total_rows },
                      { label: "Inseriti", value: xlsxActiveBatch.inserted, tone: "emerald" },
                      { label: "Aggiornati", value: xlsxActiveBatch.updated, tone: "sky" },
                      { label: "Invariati", value: xlsxActiveBatch.unchanged },
                      { label: "Anomalie", value: xlsxActiveBatch.anomalies, tone: "amber" },
                      { label: "Errori", value: xlsxActiveBatch.errors, tone: "red" },
                    ].map(({ label, value, tone }) => (
                      <div key={label} className="rounded-xl border border-gray-100 bg-white p-4">
                        <p className="text-xs uppercase tracking-widest text-gray-400">{label}</p>
                        <p
                          className={`mt-2 text-2xl font-semibold ${tone === "emerald" ? "text-emerald-700" : tone === "sky" ? "text-sky-700" : tone === "amber" ? "text-amber-700" : tone === "red" ? "text-red-700" : "text-gray-900"}`}
                        >
                          {value}
                        </p>
                      </div>
                    ))}
                  </div>
                  {xlsxActiveBatch.error_log && xlsxActiveBatch.error_log.length > 0 ? (
                    <div className="mt-4">
                      <p className="mb-2 text-sm font-medium text-gray-700">Dettaglio errori ({xlsxActiveBatch.error_log.length})</p>
                      <div className="max-h-64 space-y-1 overflow-y-auto">
                        {xlsxActiveBatch.error_log.slice(0, 100).map((entry, i) => (
                          <div key={i} className="rounded-lg border border-red-100 bg-red-50 px-3 py-2 text-xs">
                            <span className="font-medium text-red-700">Riga {entry.row}</span>
                            {entry.denominazione ? <span className="ml-2 text-red-600">{entry.denominazione}</span> : null}
                            <span className="ml-2 text-red-500">— {entry.message}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : null}
                </div>
              ) : null}

              {xlsxBatches.length > 0 ? (
                <div>
                  <p className="section-title mb-3">Storico import Excel</p>
                  <div className="space-y-2">
                    {xlsxBatches.map((b) => (
                      <div
                        key={b.id}
                        className={`cursor-pointer rounded-lg border px-4 py-3 transition-colors hover:bg-gray-50 ${xlsxActiveBatch?.id === b.id ? "border-sky-200 bg-sky-50/40" : "border-gray-100"}`}
                        onClick={() => setXlsxActiveBatch(b)}
                      >
                        <div className="flex items-center justify-between gap-3">
                          <p className="truncate text-sm font-medium text-gray-900">{b.filename}</p>
                          <span
                            className={`shrink-0 rounded-full px-2 py-0.5 text-[11px] font-medium ${b.status === "completed" ? "bg-emerald-50 text-emerald-700" : b.status === "failed" ? "bg-red-50 text-red-700" : b.status === "running" ? "bg-sky-50 text-sky-700" : "bg-gray-100 text-gray-600"}`}
                          >
                            {b.status}
                          </span>
                        </div>
                        <p className="mt-1 text-xs text-gray-500">
                          {b.total_rows} righe · +{b.inserted} inseriti · ↻{b.updated} aggiornati · ⚠{b.anomalies} anomalie ·{" "}
                          {formatDateTime(b.completed_at ?? b.created_at)}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              ) : null}
            </div>
          </article>
        ) : null}

        {activeSection === "nas" ? (
          <div className="space-y-6">
            <article className="overflow-hidden rounded-[28px] border border-[#d9dfd6] bg-white shadow-panel">
              <ElaborazionePanelHeader
                badge={
                  <>
                    <FolderIcon className="h-3.5 w-3.5" />
                    Archivio NAS
                  </>
                }
                title="Import archivio NAS"
                description="Preview e staging dell'archivio completo, aggiornamento documenti NAS sulle utenze esistenti, reset dei soli dati importati dal NAS, più dettaglio e storico dei job registrati."
                descriptionTooltip={NAS_PANEL_DESCRIPTION_TOOLTIP}
              />
              <div className="space-y-6 p-6">
                {error ? <p className="text-sm text-red-600">{error}</p> : null}
                <div
                  className="cursor-help rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800"
                  title={NAS_PANEL_DESCRIPTION_TOOLTIP}
                >
                  Il flusso operativo ora parte dalle anagrafiche già presenti: il sistema cerca sul NAS la cartella corretta per lettera, importa i file e li
                  collega al soggetto. Lo snapshot resta disponibile come staging diagnostico dell'archivio completo.
                </div>
                <div className="flex flex-wrap items-end gap-3">
                  <button
                    className="btn-secondary"
                    title={NAS_PREVIEW_BUTTON_TOOLTIP}
                    type="button"
                    onClick={() => void handlePreview()}
                    disabled={isPreviewing}
                  >
                    {isPreviewing ? "Anteprima..." : "Genera preview archivio"}
                  </button>
                  <button
                    className="btn-primary"
                    title={NAS_SNAPSHOT_BUTTON_TOOLTIP}
                    type="button"
                    onClick={() => void handleSaveSnapshot()}
                    disabled={isSavingSnapshot}
                  >
                    {isSavingSnapshot ? "Salvataggio..." : "Salva snapshot"}
                  </button>
                  <button
                    className="btn-primary"
                    title={NAS_BULK_BUTTON_TOOLTIP}
                    type="button"
                    onClick={() => setIsBulkImportModalOpen(true)}
                    disabled={bulkInFlight}
                  >
                    {bulkInFlight ? "Aggiornamento..." : "Aggiorna utenze"}
                  </button>
                  <button
                    className="btn-secondary"
                    title={NAS_RESET_BUTTON_TOOLTIP}
                    type="button"
                    onClick={() => void handleReset()}
                    disabled={isResetting}
                  >
                    {isResetting ? "Reset..." : "Pulisci dati importati NAS"}
                  </button>
                </div>
              </div>
            </article>

            {registryImportJobs.length > 0 ? (
              <article className="overflow-hidden rounded-[28px] border border-[#d9dfd6] bg-white shadow-panel">
                <div className="space-y-4 p-6">
                  <div>
                    <p className="section-title">Storico aggiornamenti massivi</p>
                    <p className="section-copy">
                      Job REGISTRY: ogni esecuzione di &quot;Aggiorna utenze&quot; accoda il lavoro al worker, che abbina le cartelle NAS alle anagrafiche esistenti. Se un job resta in{" "}
                      <span className="font-medium">running</span> senza avanzare, usa <span className="font-medium">Interrompi</span> per chiuderlo o{" "}
                      <span className="font-medium">Riprendi</span> per sbloccare le righe in elaborazione e continuare sui soggetti mancanti.{" "}
                      <span className="font-medium">Elimina</span> rimuove solo lo storico del job dal database.
                    </p>
                  </div>
                  <div className="space-y-2">
                    {registryImportJobs.map((job) => {
                      const rowBusy = registryMutationJobId === job.job_id;
                      const canStop = job.status === "running";
                      const canResume = job.status === "pending" || job.status === "running" || job.status === "failed";
                      return (
                        <div
                          key={job.job_id}
                          className={`rounded-lg border px-4 py-3 transition-colors ${selectedJob?.job_id === job.job_id ? "border-[#1D4E35]/40 bg-[#eef7ef]/50" : "border-gray-100"}`}
                        >
                          <div className="flex flex-wrap items-start justify-between gap-3">
                            <button
                              className="min-w-0 flex-1 text-left"
                              type="button"
                              onClick={() => setSelectedJob(job)}
                            >
                              <p className="text-sm font-medium text-gray-900">
                                Aggiornamento anagrafiche · {formatDateTime(job.completed_at ?? job.created_at)}
                              </p>
                              <p className="mt-1 text-xs text-gray-500">
                                {job.completed_items} completati · {job.failed_items} errori · {job.total_folders} soggetti previsti · {job.warning_count} warning
                                {job.running_items > 0 ? ` · ${job.running_items} in lavorazione` : null}
                              </p>
                              <p className="mt-1 font-mono text-[11px] text-gray-400">{job.job_id}</p>
                            </button>
                            <div className="flex flex-wrap items-center gap-2" onClick={(e) => e.stopPropagation()}>
                              <span className="rounded-full bg-gray-100 px-2 py-0.5 text-[11px] font-medium text-gray-700">{job.status}</span>
                              {canStop ? (
                                <button
                                  className="btn-secondary text-xs px-3 py-1.5"
                                  disabled={rowBusy}
                                  type="button"
                                  title="Imposta come falliti gli elementi ancora in processing e chiudi il job senza continuare"
                                  onClick={() => void handleAbortRegistryJob(job.job_id)}
                                >
                                  {rowBusy ? "…" : "Interrompi"}
                                </button>
                              ) : null}
                              {canResume ? (
                                <button
                                  className="btn-primary text-xs px-3 py-1.5"
                                  disabled={
                                    rowBusy ||
                                    (Boolean(bulkTrackingJobId) && bulkTrackingJobId !== job.job_id) ||
                                    (bulkTrackingJobId === job.job_id && isRegistryJobActive(job))
                                  }
                                  type="button"
                                  title="Sblocca eventuali righe bloccate e continua con i soggetti non ancora completati"
                                  onClick={() => void handleResumeRegistryJob(job.job_id)}
                                >
                                  {rowBusy ? "…" : "Riprendi"}
                                </button>
                              ) : null}
                              <button
                                className="btn-secondary text-xs px-3 py-1.5 text-rose-800 border-rose-200 hover:bg-rose-50"
                                disabled={rowBusy || bulkTrackingJobId === job.job_id}
                                type="button"
                                title="Rimuovi questo job dallo storico"
                                onClick={() => void handleDeleteRegistryJob(job.job_id)}
                              >
                                {rowBusy ? "…" : "Elimina"}
                              </button>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </article>
            ) : null}

            <article className="overflow-hidden rounded-[28px] border border-[#d9dfd6] bg-white shadow-panel" id="utenze-import-nas-job-storico">
              <ElaborazionePanelHeader
                badge={
                  <>
                    <RefreshIcon className="h-3.5 w-3.5" />
                    Job e storico NAS
                  </>
                }
                title="Snapshot e cronologia job"
                description="Dettaglio item del job selezionato e elenco degli snapshot registrati dal modulo NAS (staging archivio completo, lettere singole e aggiornamenti REGISTRY)."
              />
              <div className="space-y-8 p-6">
                {selectedJob ? (
                  <div>
                    <div className="mb-4 flex items-center justify-between gap-3">
                      <div>
                        <p className="section-title">Dettaglio job selezionato</p>
                        <p className="section-copy">
                          Job {selectedJob.job_id} · {selectedJob.completed_items} completati · {selectedJob.failed_items} errori.
                        </p>
                      </div>
                      <span className="rounded-full bg-sky-50 px-3 py-1 text-xs font-medium text-sky-800">
                        {selectedJob.letter === "REGISTRY" ? "REGISTRY" : "Staging"}
                      </span>
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
                              tentativi {item.attempt_count} · doc creati {item.documents_created} · doc aggiornati {item.documents_updated} · warning{" "}
                              {item.warning_count}
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
                  </div>
                ) : (
                  <p className="text-sm text-gray-500">Seleziona un job dall&apos;elenco qui sotto per vedere il dettaglio.</p>
                )}

                <div>
                  <p className="section-title mb-1">Storico snapshot e job NAS</p>
                  <p className="section-copy mb-4">Ultimi job registrati dal backend (snapshot lettere / archivio completo / aggiornamento massivo).</p>
                  {jobs.length === 0 ? (
                    <p className="text-sm text-gray-500">Nessun job disponibile.</p>
                  ) : (
                    <div className="space-y-3">
                      {jobs.map((job) => (
                        <div key={job.job_id} className="rounded-lg border border-gray-100 px-4 py-3">
                          <div className="flex items-center justify-between gap-3">
                            <p className="text-sm font-medium text-gray-900">
                              {job.letter === "ALL"
                                ? "Archivio completo"
                                : job.letter === "REGISTRY"
                                  ? "Aggiornamento da anagrafiche"
                                  : `Lettera ${job.letter || "?"}`}
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
                </div>
              </div>
            </article>

            {preview ? (
              <article className="overflow-hidden rounded-[28px] border border-[#d9dfd6] bg-white shadow-panel">
                <div className="space-y-6 p-6">
                  <div>
                    <p className="section-title">{preview.letter === "ALL" ? "Preview archivio completo" : `Preview lettera ${preview.letter}`}</p>
                    <p className="section-copy">
                      {preview.total_folders} cartelle · {preview.parsed_subjects} soggetti · {preview.total_documents} documenti
                    </p>
                  </div>
                  {preview.total_folders === 0 ? (
                    <p className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
                      Nessuna cartella trovata nell'archivio NAS configurato. Verifica il path archivio o il contenuto disponibile sul NAS.
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
                  <div className="space-y-3">
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
                          <span
                            className={`rounded-full px-2 py-1 text-[11px] font-medium ${subject.requires_review ? "bg-amber-50 text-amber-700" : "bg-emerald-50 text-emerald-700"}`}
                          >
                            {subject.requires_review ? "Review" : "OK"}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </article>
            ) : (
              <article className="overflow-hidden rounded-[28px] border border-[#d9dfd6] bg-white shadow-panel">
                <div className="p-6">
                  <EmptyState
                    icon={FolderIcon}
                    title="Nessuna preview disponibile"
                    description="Genera una preview dell'archivio completo per ispezionare cartelle, warning e documenti prima del commit import."
                  />
                </div>
              </article>
            )}

            {runResult ? (
              <article className="overflow-hidden rounded-[28px] border border-[#d9dfd6] bg-white shadow-panel">
                <div className="space-y-6 p-6">
                  <div>
                    <p className="section-title">Ultimo snapshot salvato</p>
                    <p className="section-copy">
                      Snapshot {runResult.job_id} con stato {runResult.status}.
                    </p>
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
                </div>
              </article>
            ) : null}

            {bulkRunResult ? (
              <article className="overflow-hidden rounded-[28px] border border-[#d9dfd6] bg-white shadow-panel">
                <div className="space-y-6 p-6">
                  <div>
                    <p className="section-title">Ultimo aggiornamento utenze da anagrafica</p>
                    <p className="section-copy">
                      Job {bulkRunResult.job_id} con stato {bulkRunResult.status}.
                    </p>
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
                </div>
              </article>
            ) : null}

            {resetResult ? (
              <article className="overflow-hidden rounded-[28px] border border-[#d9dfd6] bg-white shadow-panel">
                <div className="space-y-6 p-6">
                  <div>
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
                </div>
              </article>
            ) : null}
          </div>
        ) : null}
      </div>

      {isBulkImportModalOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-gray-950/35 px-4">
          <div className="w-full max-w-xl rounded-3xl bg-white p-6 shadow-2xl">
            <div className="mb-4">
              <p className="section-title">Aggiorna utenze da NAS</p>
              <p className="section-copy mt-2">
                Il sistema cercherà per ogni soggetto la cartella NAS più probabile in base a lettera archivio, nominativo e identificativi, poi allineerà i
                documenti collegati alla scheda.
              </p>
            </div>

            <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
              Usa questa azione solo per un aggiornamento massivo su tutto il database utenze. Per casi ambigui è preferibile la scheda singola con scelta manuale
              della cartella NAS.
            </div>

            <div className="mt-6 flex justify-end gap-3">
              <button className="btn-secondary" type="button" onClick={() => setIsBulkImportModalOpen(false)} disabled={bulkInFlight}>
                Annulla
              </button>
              <button className="btn-primary" type="button" onClick={() => void handleRunBulkImport()} disabled={bulkInFlight}>
                {bulkInFlight ? "Aggiornamento in corso..." : "Conferma aggiornamento"}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
}

export default function UtenzeImportPage() {
  return (
    <UtenzeModulePage
      title="Import archivio"
      description="Aggiornamento o caricamento documenti NAS sulle utenze esistenti, con preview, snapshot e reset operativo."
      breadcrumb="Import"
    >
      {({ token }) => <ImportContent token={token} />}
    </UtenzeModulePage>
  );
}
