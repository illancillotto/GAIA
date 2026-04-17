"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import {
  ModuleWorkspaceHero,
  ModuleWorkspaceKpiRow,
  ModuleWorkspaceKpiTile,
  ModuleWorkspaceMiniStat,
  ModuleWorkspaceNoticeCard,
} from "@/components/layout/module-workspace-hero";
import { RuoloModulePage } from "@/components/ruolo/module-page";
import { EmptyState } from "@/components/ui/empty-state";
import { AlertTriangleIcon, CalendarIcon, DocumentIcon, FolderIcon, LockIcon, RefreshIcon } from "@/components/ui/icons";
import { getStoredAccessToken } from "@/lib/auth";
import { getImportJob, listImportJobs, uploadRuoloFile } from "@/lib/ruolo-api";
import type { RuoloImportJobResponse } from "@/types/ruolo";

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    pending: "bg-yellow-100 text-yellow-700",
    running: "bg-blue-100 text-blue-700",
    completed: "bg-green-100 text-green-700",
    failed: "bg-red-100 text-red-700",
  };
  return (
    <span className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${colors[status] ?? "bg-gray-100 text-gray-600"}`}>
      {status}
    </span>
  );
}

export default function RuoloImportPage() {
  const [token, setToken] = useState<string | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [anno, setAnno] = useState<number>(new Date().getFullYear());
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [warningMsg, setWarningMsg] = useState<string | null>(null);
  const [jobs, setJobs] = useState<RuoloImportJobResponse[]>([]);
  const [pollingJobId, setPollingJobId] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    setToken(getStoredAccessToken());
  }, []);

  useEffect(() => {
    if (!token) return;
    listImportJobs(token, undefined, 1, 20)
      .then((r) => setJobs(r.items))
      .catch(console.error);
  }, [token]);

  useEffect(() => {
    if (!pollingJobId || !token) return;
    pollRef.current = setInterval(() => {
      getImportJob(token, pollingJobId)
        .then((job) => {
          setJobs((prev) => prev.map((j) => (j.id === job.id ? job : j)));
          if (job.status === "completed" || job.status === "failed") {
            clearInterval(pollRef.current!);
            setPollingJobId(null);
          }
        })
        .catch(console.error);
    }, 2000);
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [pollingJobId, token]);

  async function handleUpload(e: React.FormEvent) {
    e.preventDefault();
    if (!file || !token) return;
    setUploading(true);
    setUploadError(null);
    setWarningMsg(null);
    try {
      const result = await uploadRuoloFile(token, file, anno);
      if (result.warning_existing) {
        setWarningMsg(
          `Attenzione: esistono già ${result.existing_count} avvisi per l'anno ${anno}. I dati verranno aggiornati.`,
        );
      }
      const newJob: RuoloImportJobResponse = {
        id: result.job_id,
        anno_tributario: result.anno_tributario,
        filename: file.name,
        status: result.status,
        started_at: new Date().toISOString(),
        finished_at: null,
        total_partite: null,
        records_imported: null,
        records_skipped: null,
        records_errors: null,
        error_detail: null,
        triggered_by: null,
        params_json: null,
        created_at: new Date().toISOString(),
      };
      setJobs((prev) => [newJob, ...prev]);
      setPollingJobId(result.job_id);
      setFile(null);
    } catch (err: unknown) {
      setUploadError(err instanceof Error ? err.message : "Errore durante l'upload");
    } finally {
      setUploading(false);
    }
  }

  const runningJobs = jobs.filter((job) => job.status === "running" || job.status === "pending");
  const completedJobs = jobs.filter((job) => job.status === "completed");
  const failedJobs = jobs.filter((job) => job.status === "failed");
  const latestJob = jobs[0] ?? null;

  const importedRecords = useMemo(
    () => jobs.reduce((sum, job) => sum + (job.records_imported ?? 0), 0),
    [jobs],
  );

  return (
    <RuoloModulePage
      title="Import Ruolo"
      description="Carica un file Ruolo consortile per avviare l'import."
      breadcrumb="Import"
      requiredSection="ruolo.import"
      requiredRoles={["admin", "super_admin"]}
    >
      <div className="space-y-8">
        <ModuleWorkspaceHero
          badge={
            <>
              <LockIcon className="h-3.5 w-3.5" />
              Runtime Import Ruolo
            </>
          }
          title="Caricamento e monitoraggio dei file Ruolo."
          description="Carica `.dmp`, PDF testuali o file compatibili, avvia il job di import e monitora esito, warning e storico senza cambiare contesto operativo."
          actions={
            <>
              <ModuleWorkspaceNoticeCard
                title={latestJob ? `Ultimo job: ${latestJob.anno_tributario}` : "Nessun job eseguito"}
                description={
                  latestJob
                    ? `${latestJob.filename ?? "File senza nome"} · stato ${latestJob.status}.`
                    : "Il workspace è pronto per il primo caricamento."
                }
                tone={latestJob ? (latestJob.status === "failed" ? "danger" : latestJob.status === "completed" ? "success" : "warning") : "warning"}
              />
              <ModuleWorkspaceNoticeCard
                title={runningJobs.length > 0 ? "Import in esecuzione" : warningMsg ? "Aggiornamento dati esistenti" : "Flusso disponibile"}
                description={
                  runningJobs.length > 0
                    ? `${runningJobs.length} job in corso o in attesa di finalizzazione.`
                    : warningMsg
                      ? warningMsg
                      : "Puoi caricare un nuovo file Ruolo e il polling aggiornerà automaticamente la cronologia."
                }
                tone={runningJobs.length > 0 ? "warning" : warningMsg ? "info" : "neutral"}
              />
            </>
          }
        >
          <ModuleWorkspaceKpiRow>
            <ModuleWorkspaceKpiTile
              label="Job registrati"
              value={jobs.length}
              hint="Cronologia import"
            />
            <ModuleWorkspaceKpiTile
              label="In esecuzione"
              value={runningJobs.length}
              hint="Pending + running"
              variant={runningJobs.length > 0 ? "amber" : "default"}
            />
            <ModuleWorkspaceKpiTile
              label="Completati"
              value={completedJobs.length}
              hint="Conclusi con successo"
              variant="emerald"
            />
            <ModuleWorkspaceKpiTile
              label="Record importati"
              value={importedRecords}
              hint="Somma storico disponibile"
            />
          </ModuleWorkspaceKpiRow>
        </ModuleWorkspaceHero>

        <section className="grid gap-4 xl:grid-cols-[1.05fr,0.95fr]">
          <article className="rounded-[28px] border border-[#d8dfd3] bg-white shadow-panel">
            <div className="border-b border-[#edf1eb] bg-[linear-gradient(135deg,_rgba(29,78,53,0.06),_rgba(255,255,255,0.92))] px-6 py-5">
              <p className="inline-flex items-center gap-2 rounded-full bg-[#e8f2ec] px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-[#1D4E35]">
                <DocumentIcon className="h-3.5 w-3.5" />
                Upload file
              </p>
              <p className="mt-3 text-lg font-semibold text-gray-900">Prepara un nuovo job di import.</p>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-gray-600">
                Inserisci anno tributario e file sorgente. Il sistema avvierà il job e lo aggiungerà subito alla cronologia locale con polling automatico dello stato.
              </p>
            </div>
            <div className="p-6">
              <form onSubmit={handleUpload} className="space-y-5">
                <div className="grid gap-5 sm:grid-cols-2">
                  <div>
                    <label className="mb-1.5 block text-sm font-medium text-gray-700" htmlFor="anno">
                      Anno tributario
                    </label>
                    <input
                      id="anno"
                      type="number"
                      min={1990}
                      max={2100}
                      value={anno}
                      onChange={(e) => setAnno(Number(e.target.value))}
                      className="w-full rounded-xl border border-gray-200 px-3 py-2.5 text-sm text-gray-800 focus:border-[#1D4E35] focus:outline-none focus:ring-1 focus:ring-[#1D4E35]"
                      required
                    />
                  </div>
                  <div>
                    <label className="mb-1.5 block text-sm font-medium text-gray-700" htmlFor="file">
                      File `.dmp`, `.pdf` o `.txt`
                    </label>
                    <input
                      id="file"
                      type="file"
                      accept=".dmp,.pdf,.txt"
                      onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                      className="w-full rounded-xl border border-gray-200 px-3 py-2.5 text-sm text-gray-600 file:mr-3 file:rounded file:border-0 file:bg-[#EAF3E8] file:px-3 file:py-1 file:text-xs file:font-medium file:text-[#1D4E35]"
                      required
                    />
                  </div>
                </div>

                {warningMsg ? (
                  <div className="rounded-2xl border border-sky-200 bg-sky-50 px-4 py-3 text-sm text-sky-800">
                    {warningMsg}
                  </div>
                ) : null}

                {uploadError ? (
                  <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                    {uploadError}
                  </div>
                ) : null}

                <div className="flex justify-end">
                  <button
                    type="submit"
                    disabled={uploading || !file}
                    className="rounded-xl bg-[#1D4E35] px-5 py-2.5 text-sm font-medium text-white transition hover:bg-[#163d29] disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {uploading ? "Invio in corso..." : "Avvia import"}
                  </button>
                </div>
              </form>
            </div>
          </article>

          <article className="rounded-[28px] border border-[#d8dfd3] bg-white p-6 shadow-panel">
            <div>
              <p className="inline-flex items-center gap-2 rounded-full bg-[#eef3ec] px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-[#1D4E35]">
                <FolderIcon className="h-3.5 w-3.5" />
                Stato runtime
              </p>
              <p className="mt-3 text-lg font-semibold text-gray-900">Indicatori rapidi del workspace import.</p>
              <p className="mt-2 text-sm leading-6 text-gray-600">
                Controlla subito salute del flusso, ultimi esiti e volume storico dei caricamenti eseguiti nel dominio Ruolo.
              </p>
            </div>
            <div className="mt-6 grid gap-3">
              <ModuleWorkspaceMiniStat
                eyebrow="Ultimo anno"
                value={latestJob?.anno_tributario ?? "—"}
                description={latestJob ? `${latestJob.filename ?? "File senza nome"} è l'ultimo job registrato.` : "Nessun import disponibile."}
                compact
              />
              <ModuleWorkspaceMiniStat
                eyebrow="Job con errori"
                value={failedJobs.length}
                description={failedJobs.length > 0 ? "Controlla lo storico per verificare il dettaglio degli errori." : "Nessun fallimento nei job presenti in memoria."}
                tone={failedJobs.length > 0 ? "warning" : "success"}
                compact
              />
              <ModuleWorkspaceMiniStat
                eyebrow="File selezionato"
                value={file?.name ?? "Nessun file"}
                description="Il pulsante di avvio resta disabilitato finché non scegli un file valido."
                compact
              />
              <ModuleWorkspaceMiniStat
                eyebrow="Anno proposto"
                value={anno}
                description="Default all'anno corrente, modificabile prima di avviare il caricamento."
                compact
              />
            </div>
          </article>
        </section>

        <section className="rounded-[28px] border border-[#d8dfd3] bg-white shadow-panel">
          <div className="border-b border-[#edf1eb] bg-[linear-gradient(135deg,_rgba(29,78,53,0.06),_rgba(255,255,255,0.92))] px-6 py-5">
            <p className="inline-flex items-center gap-2 rounded-full bg-[#e8f2ec] px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-[#1D4E35]">
              <RefreshIcon className="h-3.5 w-3.5" />
              Cronologia import
            </p>
            <p className="mt-3 text-lg font-semibold text-gray-900">Storico operativo dei job Ruolo.</p>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-gray-600">
              Ogni card riporta anno, file, esito e contatori essenziali del job. Il polling aggiorna automaticamente gli import in corso.
            </p>
          </div>
          <div className="p-6">
            {jobs.length === 0 ? (
              <EmptyState
                icon={CalendarIcon}
                title="Nessun job disponibile"
                description="La cronologia import apparirà qui dopo il primo caricamento del file Ruolo."
              />
            ) : (
              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                {jobs.map((job) => (
                  <div key={job.id} className="rounded-2xl border border-[#e3e9e0] bg-[#fbfcfb] p-5">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-gray-500">Anno tributario</p>
                        <p className="mt-2 text-xl font-semibold text-gray-900">{job.anno_tributario}</p>
                      </div>
                      <StatusBadge status={job.status} />
                    </div>
                    <p className="mt-4 line-clamp-2 text-sm font-medium text-gray-900">{job.filename ?? "Import senza filename"}</p>
                    <p className="mt-1 text-sm text-gray-500">
                      Avviato il {new Date(job.started_at).toLocaleDateString("it-IT")}
                    </p>
                    <div className="mt-5 grid grid-cols-3 gap-3 text-sm">
                      <div className="rounded-xl border border-white bg-white px-3 py-2">
                        <p className="text-xs uppercase tracking-[0.16em] text-gray-400">Importati</p>
                        <p className="mt-1 font-semibold text-gray-900">{job.records_imported ?? "—"}</p>
                      </div>
                      <div className="rounded-xl border border-white bg-white px-3 py-2">
                        <p className="text-xs uppercase tracking-[0.16em] text-gray-400">Saltati</p>
                        <p className="mt-1 font-semibold text-gray-900">{job.records_skipped ?? "—"}</p>
                      </div>
                      <div className="rounded-xl border border-white bg-white px-3 py-2">
                        <p className="text-xs uppercase tracking-[0.16em] text-gray-400">Errori</p>
                        <p className={`mt-1 font-semibold ${(job.records_errors ?? 0) > 0 ? "text-red-700" : "text-gray-900"}`}>
                          {job.records_errors ?? "—"}
                        </p>
                      </div>
                    </div>
                    {job.error_detail ? (
                      <div className="mt-4 rounded-xl border border-red-100 bg-red-50 px-3 py-2 text-sm text-red-700">
                        {job.error_detail}
                      </div>
                    ) : null}
                  </div>
                ))}
              </div>
            )}
          </div>
        </section>

        {jobs.length === 0 ? (
          <div className="rounded-[28px] border border-dashed border-[#cfd9d0] bg-[#f8fbf8] p-6">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div className="max-w-2xl">
                <p className="inline-flex items-center gap-2 rounded-full bg-white px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-[#1D4E35]">
                  <AlertTriangleIcon className="h-3.5 w-3.5" />
                  Stato iniziale
                </p>
                <p className="mt-3 text-lg font-semibold text-gray-900">Il runtime Ruolo non ha ancora uno storico disponibile.</p>
                <p className="mt-2 text-sm leading-6 text-gray-600">
                  Seleziona file e anno tributario, quindi avvia il primo import per inizializzare il dataset e popolare automaticamente la cronologia del modulo.
                </p>
              </div>
            </div>
          </div>
        ) : null}
      </div>
    </RuoloModulePage>
  );
}
