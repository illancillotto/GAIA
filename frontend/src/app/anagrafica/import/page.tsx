"use client";

import { useCallback, useEffect, useState } from "react";

import { AnagraficaModulePage } from "@/components/anagrafica/anagrafica-module-page";
import { EmptyState } from "@/components/ui/empty-state";
import { FolderIcon } from "@/components/ui/icons";
import { getAnagraficaImportJob, getAnagraficaImportJobs, previewAnagraficaImport, runAnagraficaImport } from "@/lib/api";
import { formatDateTime } from "@/lib/presentation";
import type { AnagraficaImportJob, AnagraficaImportPreview, AnagraficaImportRunResult } from "@/types/api";

function ImportContent({ token }: { token: string }) {
  const [preview, setPreview] = useState<AnagraficaImportPreview | null>(null);
  const [jobs, setJobs] = useState<AnagraficaImportJob[]>([]);
  const [runResult, setRunResult] = useState<AnagraficaImportRunResult | null>(null);
  const [selectedJob, setSelectedJob] = useState<AnagraficaImportJob | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isPreviewing, setIsPreviewing] = useState(false);
  const [isSavingSnapshot, setIsSavingSnapshot] = useState(false);

  const loadJobs = useCallback(async () => {
    try {
      const response = await getAnagraficaImportJobs(token);
      setJobs(response);
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

  async function handlePreview() {
    setIsPreviewing(true);
    setError(null);
    try {
      const response = await previewAnagraficaImport(token);
      setPreview(response);
      setRunResult(null);
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
      const response = await runAnagraficaImport(token);
      setRunResult(response);
      const job = await getAnagraficaImportJob(token, response.job_id);
      setSelectedJob(job);
      await loadJobs();
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Errore salvataggio snapshot");
    } finally {
      setIsSavingSnapshot(false);
    }
  }

  return (
    <div className="page-stack">
      <article className="panel-card">
        <div className="mb-4">
          <p className="section-title">Wizard snapshot archivio</p>
          <p className="section-copy">Preview read-only e salvataggio in staging dell’intero archivio NAS Anagrafica.</p>
        </div>
        {error ? <p className="mb-3 text-sm text-red-600">{error}</p> : null}
        <div className="mb-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          Questa schermata non scrive più direttamente in Anagrafica. Salva uno snapshot persistente del parser NAS da usare come base per una revisione successiva.
        </div>
        <div className="flex flex-wrap items-end gap-3">
          <div className="rounded-xl border border-gray-200 bg-gray-50 px-4 py-3">
            <p className="text-xs uppercase tracking-widest text-gray-400">Ambito import</p>
            <p className="mt-1 text-sm font-medium text-gray-900">Archivio completo</p>
          </div>
          <button className="btn-secondary" type="button" onClick={() => void handlePreview()} disabled={isPreviewing}>
            {isPreviewing ? "Anteprima..." : "Genera preview"}
          </button>
          <button className="btn-primary" type="button" onClick={() => void handleSaveSnapshot()} disabled={isSavingSnapshot}>
            {isSavingSnapshot ? "Salvataggio..." : "Salva snapshot"}
          </button>
        </div>
      </article>

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
                  <p className="text-sm font-medium text-gray-900">{job.letter === "ALL" ? "Archivio completo" : `Lettera ${job.letter || "?"}`}</p>
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

export default function AnagraficaImportPage() {
  return (
    <AnagraficaModulePage
      title="Snapshot archivio"
      description="Preview read-only e salvataggio in staging dell’archivio NAS Anagrafica completo."
      breadcrumb="Import"
    >
      {({ token }) => <ImportContent token={token} />}
    </AnagraficaModulePage>
  );
}
