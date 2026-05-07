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
import { detectRuoloImportYear, getImportJob, listImportJobs, uploadRuoloFile } from "@/lib/ruolo-api";
import type { RuoloImportJobParams, RuoloImportJobResponse } from "@/types/ruolo";

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
  const [isEmbedded, setIsEmbedded] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [anno, setAnno] = useState<string>("");
  const [isDetectingYear, setIsDetectingYear] = useState(false);
  const [yearDetectionError, setYearDetectionError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [warningMsg, setWarningMsg] = useState<string | null>(null);
  const [jobs, setJobs] = useState<RuoloImportJobResponse[]>([]);
  const [pollingJobId, setPollingJobId] = useState<string | null>(null);
  const [reportJob, setReportJob] = useState<RuoloImportJobResponse | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    setToken(getStoredAccessToken());
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      setIsEmbedded(params.get("embedded") === "1");
    }
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
      const normalizedAnno = anno.trim() === "" ? undefined : Number(anno);
      const result = await uploadRuoloFile(token, file, normalizedAnno);
      if (result.warning_existing) {
        setWarningMsg(
          `Attenzione: esistono già ${result.existing_count} avvisi per l'anno ${result.anno_tributario}. I dati verranno aggiornati.`,
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
      setAnno(String(result.anno_tributario));
      setYearDetectionError(null);
    } catch (err: unknown) {
      setUploadError(err instanceof Error ? err.message : "Errore durante l'upload");
    } finally {
      setUploading(false);
    }
  }

  async function handleFileSelection(nextFile: File | null) {
    setFile(nextFile);
    setUploadError(null);
    setWarningMsg(null);
    setYearDetectionError(null);

    if (!nextFile || !token) {
      return;
    }

    setIsDetectingYear(true);
    try {
      const result = await detectRuoloImportYear(token, nextFile);
      if (result.detected_year != null) {
        setAnno(String(result.detected_year));
      } else if (anno.trim() === "") {
        setYearDetectionError("Anno non rilevato automaticamente dal file. Inseriscilo manualmente prima dell'import.");
      }
    } catch (err) {
      setYearDetectionError(err instanceof Error ? err.message : "Errore rilevamento anno");
    } finally {
      setIsDetectingYear(false);
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
          compact={isEmbedded}
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
          <ModuleWorkspaceKpiRow compact={isEmbedded}>
            <ModuleWorkspaceKpiTile
              compact={isEmbedded}
              label="Job registrati"
              value={jobs.length}
              hint="Cronologia import"
            />
            <ModuleWorkspaceKpiTile
              compact={isEmbedded}
              label="In esecuzione"
              value={runningJobs.length}
              hint="Pending + running"
              variant={runningJobs.length > 0 ? "amber" : "default"}
            />
            <ModuleWorkspaceKpiTile
              compact={isEmbedded}
              label="Completati"
              value={completedJobs.length}
              hint="Conclusi con successo"
              variant="emerald"
            />
            <ModuleWorkspaceKpiTile
              compact={isEmbedded}
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
                Seleziona il file sorgente: il sistema proverà a rilevare automaticamente l&apos;anno tributario dal contenuto e avvierà il job aggiungendolo subito alla cronologia locale con polling automatico dello stato.
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
                      onChange={(e) => setAnno(e.target.value)}
                      className="w-full rounded-xl border border-gray-200 px-3 py-2.5 text-sm text-gray-800 focus:border-[#1D4E35] focus:outline-none focus:ring-1 focus:ring-[#1D4E35]"
                      placeholder={isDetectingYear ? "Rilevamento..." : "Auto dal file o inserimento manuale"}
                    />
                    <p className="mt-1 text-xs text-gray-500">
                      {isDetectingYear ? "Rilevamento anno in corso dal file selezionato." : "Campo modificabile: se il rilevamento automatico fallisce puoi inserirlo manualmente."}
                    </p>
                  </div>
                  <div>
                    <label className="mb-1.5 block text-sm font-medium text-gray-700" htmlFor="file">
                      File `.dmp`, `.pdf` o `.txt`
                    </label>
                    <input
                      id="file"
                      type="file"
                      accept=".dmp,.pdf,.txt"
                      onChange={(e) => void handleFileSelection(e.target.files?.[0] ?? null)}
                      className="w-full rounded-xl border border-gray-200 px-3 py-2.5 text-sm text-gray-600 file:mr-3 file:rounded file:border-0 file:bg-[#EAF3E8] file:px-3 file:py-1 file:text-xs file:font-medium file:text-[#1D4E35]"
                      required
                    />
                  </div>
                </div>

                {yearDetectionError ? (
                  <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
                    {yearDetectionError}
                  </div>
                ) : null}

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
                      <div className="mt-4 rounded-xl border border-red-100 bg-red-50 px-3 py-2 text-sm text-red-700 line-clamp-4">
                        {job.error_detail}
                      </div>
                    ) : null}
                    <div className="mt-4 flex justify-end">
                      <button
                        type="button"
                        onClick={() => setReportJob(job)}
                        className="rounded-xl border border-[#d4ddd3] bg-white px-3 py-2 text-sm font-medium text-[#1D4E35] transition hover:border-[#1D4E35] hover:bg-[#f4faf5]"
                      >
                        Apri report
                      </button>
                    </div>
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
      <RuoloImportReportModal job={reportJob} onClose={() => setReportJob(null)} />
    </RuoloModulePage>
  );
}

function getJobReportParams(job: RuoloImportJobResponse): RuoloImportJobParams | null {
  return job.params_json ?? null;
}

function RuoloImportReportModal({
  job,
  onClose,
}: {
  job: RuoloImportJobResponse | null;
  onClose: () => void;
}) {
  useEffect(() => {
    if (!job) return;

    function handleKeyDown(event: KeyboardEvent): void {
      if (event.key === "Escape") {
        onClose();
      }
    }

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", handleKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [job, onClose]);

  if (!job) return null;

  const params = getJobReportParams(job);
  const summary = params?.report_summary;
  const preview = params?.report_preview;
  const skippedItems = preview?.skipped_items ?? [];
  const errorItems = preview?.error_items ?? [];
  const skippedReason =
    (job.records_skipped ?? 0) > 0
      ? "Nel flusso attuale `saltati` indica avvisi importati ma non collegati a un soggetto in Anagrafica."
      : "Nessun record non collegato rilevato nel job.";

  return (
    <div className="fixed inset-0 z-[80] flex items-center justify-center bg-black/45 px-4 py-6 backdrop-blur-sm">
      <div className="flex max-h-[92vh] w-full max-w-5xl flex-col overflow-hidden rounded-[28px] border border-gray-200 bg-white shadow-[0_30px_90px_rgba(15,23,42,0.24)]">
        <div className="flex items-start justify-between gap-4 border-b border-gray-100 px-6 py-5">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#1D4E35]">Report import</p>
            <h2 className="mt-2 text-2xl font-semibold text-gray-900">{job.filename ?? "Job Ruolo"}</h2>
            <p className="mt-1 text-sm text-gray-500">
              Anno {job.anno_tributario} · stato {job.status} · avviato il {new Date(job.started_at).toLocaleString("it-IT")}
            </p>
          </div>
          <button className="btn-secondary" type="button" onClick={onClose}>
            Chiudi
          </button>
        </div>

        <div className="flex-1 overflow-y-auto bg-[#f7faf7] px-6 py-6">
          <div className="grid gap-4 md:grid-cols-4">
            <MetricCard label="Totale partite" value={summary?.total_partite ?? job.total_partite ?? "—"} />
            <MetricCard label="Importati" value={summary?.records_imported ?? job.records_imported ?? "—"} />
            <MetricCard label="Saltati" value={summary?.records_skipped ?? job.records_skipped ?? "—"} />
            <MetricCard label="Errori" value={summary?.records_errors ?? job.records_errors ?? "—"} />
          </div>

          <div className="mt-6 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-4 text-sm text-amber-900">
            <p className="font-semibold">Significato dei record saltati</p>
            <p className="mt-1 leading-6">{skippedReason}</p>
          </div>

          <section className="mt-6 rounded-2xl border border-[#dfe7dc] bg-white p-5">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-sm font-semibold text-gray-900">Avvisi non collegati ad Anagrafica</p>
                <p className="mt-1 text-sm text-gray-500">
                  {preview
                    ? `Anteprima ${preview.skipped_preview_count} di ${preview.skipped_total_count} casi.`
                    : "Il job non contiene ancora un report strutturato; per i job futuri vedrai qui il dettaglio."}
                </p>
              </div>
            </div>

            {skippedItems.length === 0 ? (
              <p className="mt-4 text-sm text-gray-500">Nessun record saltato nel job selezionato.</p>
            ) : (
              <div className="mt-4 overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200 text-sm">
                  <thead>
                    <tr className="text-left text-xs uppercase tracking-[0.18em] text-gray-500">
                      <th className="py-2 pr-4">CNC</th>
                      <th className="py-2 pr-4">CF/P.IVA</th>
                      <th className="py-2 pr-4">Nominativo</th>
                      <th className="py-2">Motivo</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100 text-gray-700">
                    {skippedItems.map((item, index) => (
                      <tr key={`${item.codice_cnc ?? "skip"}-${index}`}>
                        <td className="py-3 pr-4 font-medium">{item.codice_cnc ?? "—"}</td>
                        <td className="py-3 pr-4">{item.codice_fiscale_raw ?? "—"}</td>
                        <td className="py-3 pr-4">{item.nominativo_raw ?? "—"}</td>
                        <td className="py-3">{item.reason_label}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          <section className="mt-6 rounded-2xl border border-[#dfe7dc] bg-white p-5">
            <div>
              <p className="text-sm font-semibold text-gray-900">Errori di import</p>
              <p className="mt-1 text-sm text-gray-500">
                {preview
                  ? `Anteprima ${preview.error_preview_count} di ${preview.error_total_count} casi.`
                  : "Per i job storici senza report strutturato viene mostrato solo il testo grezzo dell'errore."}
              </p>
            </div>

            {errorItems.length > 0 ? (
              <div className="mt-4 overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200 text-sm">
                  <thead>
                    <tr className="text-left text-xs uppercase tracking-[0.18em] text-gray-500">
                      <th className="py-2 pr-4">CNC</th>
                      <th className="py-2 pr-4">CF/P.IVA</th>
                      <th className="py-2 pr-4">Nominativo</th>
                      <th className="py-2">Motivo</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100 text-gray-700">
                    {errorItems.map((item, index) => (
                      <tr key={`${item.codice_cnc ?? "error"}-${index}`}>
                        <td className="py-3 pr-4 font-medium">{item.codice_cnc ?? "—"}</td>
                        <td className="py-3 pr-4">{item.codice_fiscale_raw ?? "—"}</td>
                        <td className="py-3 pr-4">{item.nominativo_raw ?? "—"}</td>
                        <td className="py-3">{item.reason_label}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : job.error_detail ? (
              <div className="mt-4 rounded-2xl border border-red-100 bg-red-50 px-4 py-3 text-sm text-red-700 whitespace-pre-wrap">
                {job.error_detail}
              </div>
            ) : (
              <p className="mt-4 text-sm text-gray-500">Nessun errore registrato nel job selezionato.</p>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}

function MetricCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-2xl border border-[#dfe7dc] bg-white px-4 py-4">
      <p className="text-xs uppercase tracking-[0.18em] text-gray-500">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-gray-900">{value}</p>
    </div>
  );
}
