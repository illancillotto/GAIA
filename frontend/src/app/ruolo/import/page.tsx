"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import {
  ModuleWorkspaceHero,
  ModuleWorkspaceKpiRow,
  ModuleWorkspaceKpiTile,
  ModuleWorkspaceMiniStat,
  ModuleWorkspaceNoticeCard,
} from "@/components/layout/module-workspace-hero";
import { RuoloModulePage } from "@/components/ruolo/module-page";
import { EmptyState } from "@/components/ui/empty-state";
import { AlertTriangleIcon, CalendarIcon, FolderIcon, LockIcon, RefreshIcon } from "@/components/ui/icons";
import { getStoredAccessToken } from "@/lib/auth";
import { listImportJobs } from "@/lib/ruolo-api";
import type { RuoloImportJobParams, RuoloImportJobResponse } from "@/types/ruolo";

function formatRuoloJobLabel(job: RuoloImportJobResponse): string {
  const raw = (job.filename ?? "").trim();
  if (!raw) {
    return `Workflow ruolo ${job.anno_tributario}`;
  }

  const normalized = raw.toLowerCase();
  const yearFromName = normalized.match(/(20\d{2})/)?.[1] ?? String(job.anno_tributario);

  if (normalized.includes("incass_backfill")) {
    return `Recupero storico InCass ${yearFromName}`;
  }
  if (normalized.includes("ruolo_harvest") || normalized.includes("ruolo-harvest")) {
    return `Raccolta partitario InCass ${yearFromName}`;
  }
  if (normalized.includes("backfill") && normalized.includes("ruolo")) {
    return `Completamento dati ruolo ${yearFromName}`;
  }
  if (normalized.includes("repair") && normalized.includes("ruolo")) {
    return `Bonifica collegamenti ruolo ${yearFromName}`;
  }
  if (normalized.endsWith(".dmp")) {
    return `Legacy import ruolo ${yearFromName}`;
  }
  if (normalized.endsWith(".pdf")) {
    return `Legacy PDF ruolo ${yearFromName}`;
  }
  return raw.replace(/[_-]+/g, " ");
}

function formatRuoloJobStatus(status: string): string {
  const labels: Record<string, string> = {
    pending: "In attesa",
    running: "In corso",
    completed: "Completato",
    failed: "Con errori",
  };
  return labels[status] ?? status;
}

function formatRuoloJobDescription(job: RuoloImportJobResponse): string {
  const raw = (job.filename ?? "").trim().toLowerCase();
  if (!raw) {
    return "Workflow tecnico del modulo ruolo.";
  }
  if (raw.includes("incass_backfill")) {
    return "Recupero storico degli avvisi e del partitario da InCass.";
  }
  if (raw.includes("ruolo_harvest") || raw.includes("ruolo-harvest")) {
    return "Raccolta massiva del partitario dagli avvisi a ruolo.";
  }
  if (raw.includes("backfill") && raw.includes("ruolo")) {
    return "Completamento del dataset ruolo a partire da dati gia raccolti.";
  }
  if (raw.includes("repair") && raw.includes("ruolo")) {
    return "Bonifica dei collegamenti catastali del ruolo.";
  }
  if (raw.endsWith(".dmp")) {
    return "Import legacy del dump ruolo originale.";
  }
  if (raw.endsWith(".pdf")) {
    return "Import legacy del PDF testuale del ruolo.";
  }
  return "Elaborazione tecnica del modulo ruolo.";
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    pending: "bg-yellow-100 text-yellow-700",
    running: "bg-blue-100 text-blue-700",
    completed: "bg-green-100 text-green-700",
    failed: "bg-red-100 text-red-700",
  };
  return (
    <span className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${colors[status] ?? "bg-gray-100 text-gray-600"}`}>
      {formatRuoloJobStatus(status)}
    </span>
  );
}

export default function RuoloImportPage() {
  const [token, setToken] = useState<string | null>(null);
  const [isEmbedded, setIsEmbedded] = useState(false);
  const [jobs, setJobs] = useState<RuoloImportJobResponse[]>([]);
  const [reportJob, setReportJob] = useState<RuoloImportJobResponse | null>(null);

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
      title="Storico Workflow Ruolo"
      description="Storico tecnico dei job ruolo e accesso al flusso corretto inCASS."
      breadcrumb="Storico"
      requiredSection="ruolo.import"
      requiredRoles={["admin", "super_admin"]}
    >
      <div className="space-y-8">
        <ModuleWorkspaceHero
          compact={isEmbedded}
          badge={
            <>
              <LockIcon className="h-3.5 w-3.5" />
              Runtime Ruolo
            </>
          }
          title="L'import da file è stato dismesso."
          description="Il dump DMP/PDF del ruolo non è affidabile. La fonte canonica è lo scraping `inCASS`, mentre questo workspace resta disponibile per consultare storico job e report legacy."
          actions={
            <>
              <ModuleWorkspaceNoticeCard
                title={latestJob ? `Ultimo job: ${latestJob.anno_tributario}` : "Nessun job eseguito"}
                description={
                  latestJob
                    ? `${formatRuoloJobLabel(latestJob)} · stato ${formatRuoloJobStatus(latestJob.status)}.`
                    : "Il workflow ruolo va avviato dal workspace Capacitas inCASS."
                }
                tone={latestJob ? (latestJob.status === "failed" ? "danger" : latestJob.status === "completed" ? "success" : "warning") : "warning"}
              />
              <ModuleWorkspaceNoticeCard
                title={runningJobs.length > 0 ? "Job in esecuzione" : "Flusso file dismesso"}
                description={
                  runningJobs.length > 0
                    ? `${runningJobs.length} job in corso o in attesa di finalizzazione.`
                    : "L'upload manuale DMP/PDF non è più disponibile in GAIA."
                }
                tone={runningJobs.length > 0 ? "warning" : "info"}
              />
            </>
          }
        >
          <ModuleWorkspaceKpiRow compact={isEmbedded}>
            <ModuleWorkspaceKpiTile compact={isEmbedded} label="Job registrati" value={jobs.length} hint="Cronologia tecnica" />
            <ModuleWorkspaceKpiTile
              compact={isEmbedded}
              label="In esecuzione"
              value={runningJobs.length}
              hint="Pending + running"
              variant={runningJobs.length > 0 ? "amber" : "default"}
            />
            <ModuleWorkspaceKpiTile compact={isEmbedded} label="Completati" value={completedJobs.length} hint="Conclusi con successo" variant="emerald" />
            <ModuleWorkspaceKpiTile compact={isEmbedded} label="Record importati" value={importedRecords} hint="Somma storico disponibile" />
          </ModuleWorkspaceKpiRow>
        </ModuleWorkspaceHero>

        <section className="grid gap-4 xl:grid-cols-[1.05fr,0.95fr]">
          <article className="rounded-[28px] border border-[#d8dfd3] bg-white shadow-panel">
            <div className="border-b border-[#edf1eb] bg-[linear-gradient(135deg,_rgba(29,78,53,0.06),_rgba(255,255,255,0.92))] px-6 py-5">
              <p className="inline-flex items-center gap-2 rounded-full bg-[#fff4e5] px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-[#9a5b00]">
                <AlertTriangleIcon className="h-3.5 w-3.5" />
                Flusso operativo
              </p>
              <p className="mt-3 text-lg font-semibold text-gray-900">Usa il workflow inCASS.</p>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-gray-600">
                La raccolta del ruolo passa dal partitario `inCASS` già persistito in GAIA. Qui manteniamo solo lo storico tecnico dei job, i report e i riferimenti alle elaborazioni legacy.
              </p>
            </div>
            <div className="space-y-4 p-6">
              <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-4 text-sm text-amber-900">
                <p className="font-semibold">Motivo della dismissione</p>
                <p className="mt-1 leading-6">
                  Il dump ruolo tronca o perde informazioni. Per questo la quadratura e le raccolte correnti sono state spostate sullo scrape `inCASS`.
                </p>
              </div>
              <div className="flex flex-wrap gap-3">
                <Link
                  href="/elaborazioni/capacitas?section=incass"
                  className="rounded-xl bg-[#1D4E35] px-5 py-2.5 text-sm font-medium text-white transition hover:bg-[#163d29]"
                >
                  Apri workspace inCASS
                </Link>
                <Link
                  href="/ruolo/controlli-capacitas"
                  className="rounded-xl border border-[#d6e5db] bg-white px-5 py-2.5 text-sm font-medium text-[#1D4E35] transition hover:bg-[#f3f8f5]"
                >
                  Apri controlli Capacitas
                </Link>
              </div>
            </div>
          </article>

          <article className="rounded-[28px] border border-[#d8dfd3] bg-white p-6 shadow-panel">
            <div>
              <p className="inline-flex items-center gap-2 rounded-full bg-[#eef3ec] px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-[#1D4E35]">
                <FolderIcon className="h-3.5 w-3.5" />
                Stato runtime
              </p>
              <p className="mt-3 text-lg font-semibold text-gray-900">Indicatori rapidi del workflow ruolo.</p>
              <p className="mt-2 text-sm leading-6 text-gray-600">
                Controlla rapidamente ultimi esiti, volume storico e stato dei job già registrati sul dominio ruolo.
              </p>
            </div>
            <div className="mt-6 grid gap-3">
              <ModuleWorkspaceMiniStat
                eyebrow="Ultimo anno"
                value={latestJob?.anno_tributario ?? "—"}
                description={latestJob ? `${formatRuoloJobLabel(latestJob)} è l'ultimo job registrato.` : "Nessun job disponibile."}
                compact
              />
              <ModuleWorkspaceMiniStat
                eyebrow="Job con errori"
                value={failedJobs.length}
                description={failedJobs.length > 0 ? "Controlla lo storico per verificare il dettaglio degli errori." : "Nessun fallimento nei job presenti in memoria."}
                tone={failedJobs.length > 0 ? "warning" : "success"}
                compact
              />
              <ModuleWorkspaceMiniStat eyebrow="Canale attivo" value="inCASS" description="Il caricamento manuale da file è disattivato." compact />
              <ModuleWorkspaceMiniStat
                eyebrow="Percorso consigliato"
                value="Elaborazioni"
                description="Usa il workspace Capacitas per lanciare i job di raccolta ruolo."
                compact
              />
            </div>
          </article>
        </section>

        <section className="rounded-[28px] border border-[#d8dfd3] bg-white shadow-panel">
          <div className="border-b border-[#edf1eb] bg-[linear-gradient(135deg,_rgba(29,78,53,0.06),_rgba(255,255,255,0.92))] px-6 py-5">
            <p className="inline-flex items-center gap-2 rounded-full bg-[#e8f2ec] px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-[#1D4E35]">
              <RefreshIcon className="h-3.5 w-3.5" />
              Cronologia job
            </p>
            <p className="mt-3 text-lg font-semibold text-gray-900">Storico operativo del dominio Ruolo.</p>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-gray-600">
              Ogni card riporta anno, file, esito e contatori essenziali dei job storici, dei backfill e delle elaborazioni tecniche eseguite sul ruolo.
            </p>
          </div>
          <div className="p-6">
            {jobs.length === 0 ? (
              <EmptyState
                icon={CalendarIcon}
                title="Nessun job disponibile"
                description="La cronologia apparirà qui dopo il primo harvest o backfill tecnico del ruolo."
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
                    <p className="mt-4 line-clamp-2 text-sm font-medium text-gray-900">{formatRuoloJobLabel(job)}</p>
                    <p className="mt-1 text-sm text-gray-500">Avviato il {new Date(job.started_at).toLocaleDateString("it-IT")}</p>
                    <p className="mt-1 text-sm text-gray-600">{formatRuoloJobDescription(job)}</p>
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
                      <div className="mt-4 line-clamp-4 rounded-xl border border-red-100 bg-red-50 px-3 py-2 text-sm text-red-700">
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
                  Avvia il primo job dal workspace inCASS per inizializzare il dataset e popolare automaticamente la cronologia del modulo.
                </p>
              </div>
              <div className="flex flex-wrap gap-3">
                <Link
                  href="/elaborazioni/capacitas?section=incass"
                  className="rounded-xl bg-[#1D4E35] px-4 py-2 text-sm font-medium text-white transition hover:bg-[#163d29]"
                >
                  Apri workspace inCASS
                </Link>
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
            <h2 className="mt-2 text-2xl font-semibold text-gray-900">{formatRuoloJobLabel(job)}</h2>
            <p className="mt-1 text-sm text-gray-500">
              Anno {job.anno_tributario} · stato {formatRuoloJobStatus(job.status)} · avviato il {new Date(job.started_at).toLocaleString("it-IT")}
            </p>
            <p className="mt-2 text-sm text-gray-600">{formatRuoloJobDescription(job)}</p>
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
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-sm font-semibold text-gray-900">Errori tecnici rilevati</p>
                <p className="mt-1 text-sm text-gray-500">
                  {preview
                    ? `Anteprima ${preview.error_preview_count} di ${preview.error_total_count} casi.`
                    : "Il job non contiene ancora un report strutturato; per i job futuri vedrai qui il dettaglio."}
                </p>
              </div>
            </div>

            {errorItems.length === 0 ? (
              <p className="mt-4 text-sm text-gray-500">Nessun errore strutturato nel job selezionato.</p>
            ) : (
              <div className="mt-4 overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200 text-sm">
                  <thead>
                    <tr className="text-left text-xs uppercase tracking-[0.18em] text-gray-500">
                      <th className="py-2 pr-4">CNC</th>
                      <th className="py-2 pr-4">CF/P.IVA</th>
                      <th className="py-2 pr-4">Nominativo</th>
                      <th className="py-2">Errore</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100 text-gray-700">
                    {errorItems.map((item, index) => (
                      <tr key={`${item.codice_cnc ?? "err"}-${index}`}>
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
        </div>
      </div>
    </div>
  );
}

function MetricCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-2xl border border-[#dfe7dc] bg-white px-4 py-4">
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-500">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-gray-900">{value}</p>
    </div>
  );
}
