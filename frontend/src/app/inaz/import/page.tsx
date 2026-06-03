"use client";

import { useEffect, useMemo, useState } from "react";

import { ProtectedPage } from "@/components/app/protected-page";
import {
  ModuleWorkspaceHero,
  ModuleWorkspaceKpiRow,
  ModuleWorkspaceKpiTile,
  ModuleWorkspaceNoticeCard,
} from "@/components/layout/module-workspace-hero";
import { previewInazImport, importInazJson, listInazImportJobs } from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import type { InazImportJob, InazImportPreviewResponse } from "@/types/api";

export default function InazImportPage() {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<InazImportPreviewResponse | null>(null);
  const [jobs, setJobs] = useState<InazImportJob[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [isPreviewing, setIsPreviewing] = useState(false);
  const [isImporting, setIsImporting] = useState(false);

  useEffect(() => {
    const token = getStoredAccessToken();
    if (!token) return;
    listInazImportJobs(token)
      .then(setJobs)
      .catch((loadError) => setError(loadError instanceof Error ? loadError.message : "Errore caricamento job Inaz"));
  }, []);

  const lastJob = jobs[0] ?? null;
  const importedTotal = useMemo(() => jobs.reduce((sum, item) => sum + item.records_imported, 0), [jobs]);

  async function handlePreview() {
    const token = getStoredAccessToken();
    if (!token || !file) return;
    setIsPreviewing(true);
    setError(null);
    setSuccess(null);
    try {
      const response = await previewInazImport(token, file);
      setPreview(response);
    } catch (previewError) {
      setError(previewError instanceof Error ? previewError.message : "Errore preview import");
    } finally {
      setIsPreviewing(false);
    }
  }

  async function handleImport() {
    const token = getStoredAccessToken();
    if (!token || !file) return;
    setIsImporting(true);
    setError(null);
    setSuccess(null);
    try {
      const response = await importInazJson(token, file);
      setPreview(response.preview);
      setJobs((current) => [response.job, ...current]);
      setSuccess(`Import completato. Collaboratori: ${response.preview.total_collaborators}, righe giornaliere: ${response.job.records_imported}.`);
    } catch (importError) {
      setError(importError instanceof Error ? importError.message : "Errore import JSON");
    } finally {
      setIsImporting(false);
    }
  }

  return (
    <ProtectedPage title="Import Inaz" description="Import file JSON prodotto da inaz-collaboratori." breadcrumb="Inaz" requiredModule="inaz" requiredRoles={["admin", "super_admin"]}>
      <div className="space-y-8">
        <ModuleWorkspaceHero
          badge={<>Import JSON</>}
          title="Carica, valida e importa il file collaboratori/giornaliere prodotto dallo scraper Inaz."
          description="Il workflow legge il JSON come formato di interscambio stabile, mostra un'anteprima dei collaboratori e poi persiste giornaliere, timbrature e riepiloghi eventi."
          actions={
            <>
              <ModuleWorkspaceNoticeCard
                title={lastJob ? `Ultimo job: ${lastJob.status}` : "Nessun job registrato"}
                description={lastJob?.filename ?? "Seleziona un JSON Inaz e lancia prima la preview."}
                tone={lastJob?.status === "completed" ? "success" : lastJob?.status === "failed" ? "danger" : "warning"}
              />
              <ModuleWorkspaceNoticeCard
                title={preview ? "Preview pronta" : "Preview non eseguita"}
                description={
                  preview
                    ? `${preview.total_collaborators} collaboratori, ${preview.total_daily_rows} righe giornaliere, ${preview.total_summary_rows} voci riepilogo.`
                    : "La preview consente di validare il contenuto prima della persistenza."
                }
                tone={preview ? "info" : "neutral"}
              />
            </>
          }
        >
          <ModuleWorkspaceKpiRow>
            <ModuleWorkspaceKpiTile label="Job totali" value={jobs.length} hint="Storico import" />
            <ModuleWorkspaceKpiTile label="Righe importate" value={importedTotal} hint="Somma storico" variant="emerald" />
            <ModuleWorkspaceKpiTile label="File selezionato" value={file?.name ?? "Nessuno"} hint="Sorgente corrente" />
          </ModuleWorkspaceKpiRow>
        </ModuleWorkspaceHero>

        {error ? <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div> : null}
        {success ? <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">{success}</div> : null}

        <article className="panel-card space-y-5">
          <div>
            <p className="section-title">Carica file JSON</p>
            <p className="section-copy">Usa direttamente l&apos;output di `inaz-collaboratori --json-output ...`.</p>
          </div>
          <input type="file" accept=".json,application/json" onChange={(event) => setFile(event.target.files?.[0] ?? null)} />
          <div className="flex flex-wrap gap-3">
            <button className="btn-secondary" type="button" onClick={() => void handlePreview()} disabled={!file || isPreviewing}>
              {isPreviewing ? "Preview..." : "Esegui preview"}
            </button>
            <button className="btn-primary" type="button" onClick={() => void handleImport()} disabled={!file || isImporting}>
              {isImporting ? "Import..." : "Conferma import"}
            </button>
          </div>
        </article>

        {preview ? (
          <article className="panel-card">
            <div className="mb-4">
              <p className="section-title">Preview contenuto</p>
              <p className="section-copy">Collaboratori rilevati e volume delle righe giornaliere/riepilogo.</p>
            </div>
            <div className="grid gap-4 lg:grid-cols-3">
              <div className="rounded-2xl border border-gray-100 bg-gray-50 p-4">
                <p className="text-xs uppercase tracking-[0.16em] text-gray-400">Collaboratori</p>
                <p className="mt-2 text-2xl font-semibold text-gray-900">{preview.total_collaborators}</p>
              </div>
              <div className="rounded-2xl border border-gray-100 bg-gray-50 p-4">
                <p className="text-xs uppercase tracking-[0.16em] text-gray-400">Righe giornaliere</p>
                <p className="mt-2 text-2xl font-semibold text-gray-900">{preview.total_daily_rows}</p>
              </div>
              <div className="rounded-2xl border border-gray-100 bg-gray-50 p-4">
                <p className="text-xs uppercase tracking-[0.16em] text-gray-400">Riepiloghi eventi</p>
                <p className="mt-2 text-2xl font-semibold text-gray-900">{preview.total_summary_rows}</p>
              </div>
            </div>
            <div className="mt-5 space-y-3">
              {preview.collaborators.map((item) => (
                <div key={`${item.employee_code}-${item.period_start}`} className="rounded-2xl border border-gray-100 bg-gray-50 px-4 py-3">
                  <p className="font-medium text-gray-900">{item.name}</p>
                  <p className="text-xs text-gray-500">
                    Matricola {item.employee_code} · Azienda {item.company_code ?? "n/d"} · {item.total_daily_rows} giornaliere · {item.total_summary_rows} riepiloghi
                  </p>
                </div>
              ))}
              {preview.errors.length > 0 ? (
                <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
                  <p className="font-medium">Errori rilevati</p>
                  <ul className="mt-2 list-disc pl-5">
                    {preview.errors.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </div>
          </article>
        ) : null}

        <article className="panel-card">
          <div className="mb-4">
            <p className="section-title">Storico job</p>
            <p className="section-copy">Registro persistente delle importazioni JSON Inaz.</p>
          </div>
          <div className="space-y-3">
            {jobs.map((job) => (
              <div key={job.id} className="rounded-2xl border border-gray-100 bg-gray-50 px-4 py-3">
                <p className="font-medium text-gray-900">{job.filename ?? "File senza nome"}</p>
                <p className="text-xs text-gray-500">
                  {job.status} · importati {job.records_imported} · scartati {job.records_skipped} · errori {job.records_errors}
                </p>
              </div>
            ))}
            {jobs.length === 0 ? <p className="text-sm text-gray-500">Nessun job disponibile.</p> : null}
          </div>
        </article>
      </div>
    </ProtectedPage>
  );
}
