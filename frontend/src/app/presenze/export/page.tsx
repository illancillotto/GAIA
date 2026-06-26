"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import { ProtectedPage } from "@/components/app/protected-page";
import {
  ModuleWorkspaceHero,
  ModuleWorkspaceKpiRow,
  ModuleWorkspaceKpiTile,
  ModuleWorkspaceNoticeCard,
} from "@/components/layout/module-workspace-hero";
import { EmptyState } from "@/components/ui/empty-state";
import { DocumentIcon } from "@/components/ui/icons";
import {
  createPresenzeXlsmExportJob,
  downloadPresenzeXlsmExportArtifact,
  getPresenzeXlsmExportJob,
  listAllPresenzeCollaborators,
  listPresenzeXlsmExportJobs,
  listPresenzeDailyRecords,
} from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import type { PresenzeCollaborator, PresenzeDailyRecord, PresenzeSyncJob } from "@/types/api";

type ContractFilter = "all" | "operaio" | "impiegato" | "quadro" | "altro" | "unassigned";

const CONTRACT_FILTER_OPTIONS: Array<{ value: ContractFilter; label: string }> = [
  { value: "all", label: "Tutti i contratti" },
  { value: "operaio", label: "Operai" },
  { value: "impiegato", label: "Impiegati" },
  { value: "quadro", label: "Quadri" },
  { value: "altro", label: "Altro" },
  { value: "unassigned", label: "Profilo non definito" },
];

function currentMonthValue(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
}

function shiftMonth(monthValue: string, delta: number): string {
  const [year, month] = monthValue.split("-").map(Number);
  const shifted = new Date(year, month - 1 + delta, 1);
  return `${shifted.getFullYear()}-${String(shifted.getMonth() + 1).padStart(2, "0")}`;
}

function formatMonthLabel(monthValue: string): string {
  return new Intl.DateTimeFormat("it-IT", { month: "long", year: "numeric" }).format(new Date(`${monthValue}-01T00:00:00`));
}

function monthBoundsFromValue(value: string): { start: string; end: string } {
  const [year, month] = value.split("-").map(Number);
  const end = new Date(year, month, 0).getDate();
  return {
    start: `${year}-${String(month).padStart(2, "0")}-01`,
    end: `${year}-${String(month).padStart(2, "0")}-${String(end).padStart(2, "0")}`,
  };
}

function formatMinutesAsHours(value: number): string {
  const hours = value / 60;
  return Number.isInteger(hours) ? `${hours}` : hours.toFixed(2).replace(/\.00$/, "");
}

function ExportSpinner({ label = "Esportazione in corso..." }: { label?: string }) {
  return (
    <div className="flex items-center gap-3">
      <span className="inline-flex h-5 w-5 animate-spin rounded-full border-2 border-white/35 border-t-white" aria-hidden="true" />
      <span>{label}</span>
    </div>
  );
}

function sortExportJobs(items: PresenzeSyncJob[]): PresenzeSyncJob[] {
  return [...items].sort((left, right) => Date.parse(right.created_at) - Date.parse(left.created_at));
}

function formatJobDateTime(value: string): string {
  return new Intl.DateTimeFormat("it-IT", {
    day: "2-digit",
    month: "2-digit",
    year: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function formatJobStatus(status: string): string {
  if (status === "pending") return "In coda";
  if (status === "running") return "In lavorazione";
  if (status === "completed") return "Pronto";
  if (status === "failed") return "Fallito";
  return status;
}

function statusToneClasses(status: string): string {
  if (status === "completed") return "border-emerald-200 bg-emerald-50 text-emerald-700";
  if (status === "failed") return "border-red-200 bg-red-50 text-red-700";
  if (status === "running") return "border-amber-200 bg-amber-50 text-amber-700";
  return "border-slate-200 bg-slate-50 text-slate-700";
}

function buildExportFilename(job: PresenzeSyncJob): string {
  const monthKey = job.period_start.slice(0, 7);
  return `presenze_giornaliere_${monthKey}.xlsm`;
}

function matchesContractFilter(collaborator: PresenzeCollaborator, filter: ContractFilter): boolean {
  if (filter === "all") return true;
  if (filter === "unassigned") return collaborator.contract_kind == null;
  return collaborator.contract_kind === filter;
}

function resolveEmployeeKindLabel(filter: ContractFilter): string | undefined {
  const labels: Record<Exclude<ContractFilter, "all" | "unassigned">, string> = {
    operaio: "OPERAI",
    impiegato: "IMPIEGATI",
    quadro: "QUADRI",
    altro: "ALTRO",
  };
  if (filter === "all" || filter === "unassigned") {
    return undefined;
  }
  return labels[filter];
}

async function listAllMonthlyRecords(token: string, dateFrom: string, dateTo: string): Promise<PresenzeDailyRecord[]> {
  const pageSize = 500;
  let page = 1;
  const items: PresenzeDailyRecord[] = [];

  while (true) {
    const response = await listPresenzeDailyRecords(token, { dateFrom, dateTo, page, pageSize });
    items.push(...response.items);
    if (items.length >= response.total || response.items.length === 0) {
      return items;
    }
    page += 1;
  }
}

export default function PresenzeExportPage() {
  const [collaborators, setCollaborators] = useState<PresenzeCollaborator[]>([]);
  const [records, setRecords] = useState<PresenzeDailyRecord[]>([]);
  const [selectedMonth, setSelectedMonth] = useState(currentMonthValue());
  const [contractFilter, setContractFilter] = useState<ContractFilter>("all");
  const [templatePath, setTemplatePath] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingPreview, setIsLoadingPreview] = useState(false);
  const [isSubmittingExportJob, setIsSubmittingExportJob] = useState(false);
  const [isLoadingExportJobs, setIsLoadingExportJobs] = useState(true);
  const [exportJobs, setExportJobs] = useState<PresenzeSyncJob[]>([]);
  const [downloadingJobId, setDownloadingJobId] = useState<string | null>(null);
  const [isHistoryModalOpen, setIsHistoryModalOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const knownJobStatusesRef = useRef<Map<string, string>>(new Map());

  useEffect(() => {
    const token = getStoredAccessToken();
    if (!token) return;
    listAllPresenzeCollaborators(token)
      .then((response) => setCollaborators(response))
      .catch((loadError) => setError(loadError instanceof Error ? loadError.message : "Errore caricamento collaboratori"))
      .finally(() => setIsLoading(false));
  }, []);

  useEffect(() => {
    const token = getStoredAccessToken();
    if (!token || !selectedMonth) return;
    const bounds = monthBoundsFromValue(selectedMonth);
    setIsLoadingPreview(true);
    listAllMonthlyRecords(token, bounds.start, bounds.end)
      .then((response) => setRecords(response))
      .catch((loadError) => setError(loadError instanceof Error ? loadError.message : "Errore caricamento preview export"))
      .finally(() => setIsLoadingPreview(false));
  }, [selectedMonth]);

  useEffect(() => {
    const token = getStoredAccessToken();
    if (!token) return;
    const authToken = token;

    let cancelled = false;
    async function refreshExportJobs(options?: { silent?: boolean; suppressCompletionNotice?: boolean }) {
      if (!options?.silent) {
        setIsLoadingExportJobs(true);
      }
      try {
        const items = sortExportJobs(await listPresenzeXlsmExportJobs(authToken, { limit: 25 }));
        if (cancelled) return;

        if (!options?.suppressCompletionNotice) {
          for (const item of items) {
            const previousStatus = knownJobStatusesRef.current.get(item.id);
            if ((previousStatus === "pending" || previousStatus === "running") && item.status === "completed") {
              setSuccess(`Export ${formatMonthLabel(item.period_start.slice(0, 7))} pronto. Trovi il file nella sezione Ultimi export XLSM.`);
            }
          }
        }

        knownJobStatusesRef.current = new Map(items.map((item) => [item.id, item.status]));
        setExportJobs(items);
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : "Errore caricamento storico export XLSM");
        }
      } finally {
        if (!cancelled && !options?.silent) {
          setIsLoadingExportJobs(false);
        }
      }
    }

    void refreshExportJobs({ suppressCompletionNotice: true });
    const intervalId = window.setInterval(() => {
      if (knownJobStatusesRef.current.size === 0) {
        return;
      }
      const hasActiveJob = Array.from(knownJobStatusesRef.current.values()).some((status) => status === "pending" || status === "running");
      if (!hasActiveJob) {
        return;
      }
      void refreshExportJobs({ silent: true });
    }, 2500);

    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, []);

  useEffect(() => {
    if (!isHistoryModalOpen) {
      return;
    }
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, [isHistoryModalOpen]);

  const mappedCount = useMemo(() => collaborators.filter((item) => item.application_user_id != null).length, [collaborators]);
  const filteredCollaborators = useMemo(
    () => collaborators.filter((item) => matchesContractFilter(item, contractFilter)),
    [collaborators, contractFilter],
  );
  const filteredCollaboratorIds = useMemo(() => new Set(filteredCollaborators.map((item) => item.id)), [filteredCollaborators]);
  const scopedRecords = useMemo(
    () => records.filter((record) => filteredCollaboratorIds.has(record.collaborator_id)),
    [records, filteredCollaboratorIds],
  );
  const specialDayCount = useMemo(() => scopedRecords.filter((record) => record.special_day).length, [scopedRecords]);
  const detailDrivenCount = useMemo(
    () => scopedRecords.filter((record) => Object.keys(record.detail_day_totals).length > 0 || Object.keys(record.detail_day_summary).length > 0).length,
    [scopedRecords],
  );
  const trasfertaDaysCount = useMemo(() => scopedRecords.filter((record) => (record.trasferta_minutes ?? 0) > 0).length, [scopedRecords]);
  const trasfertaMinutesTotal = useMemo(() => scopedRecords.reduce((sum, record) => sum + (record.trasferta_minutes ?? 0), 0), [scopedRecords]);
  const trasfertaMontanoCount = useMemo(() => scopedRecords.filter((record) => record.trasferta_montano).length, [scopedRecords]);
  const reperibilitaBreakdown = useMemo(() => {
    return scopedRecords.reduce(
      (accumulator, record) => {
        if (record.reperibilita_unit !== "none" && (record.reperibilita_quantity ?? 0) > 0) {
          accumulator.total += 1;
          accumulator[record.reperibilita_unit] += 1;
        }
        return accumulator;
      },
      { total: 0, hours: 0, days: 0, shifts: 0 },
    );
  }, [scopedRecords]);
  const activeExportJob = useMemo(
    () => exportJobs.find((job) => job.status === "pending" || job.status === "running") ?? null,
    [exportJobs],
  );
  const isExporting = isSubmittingExportJob || activeExportJob != null;
  const recentExportJobs = useMemo(() => exportJobs.slice(0, 5), [exportJobs]);

  async function handleDownloadJob(job: PresenzeSyncJob) {
    const token = getStoredAccessToken();
    if (!token) return;
    setDownloadingJobId(job.id);
    setError(null);
    try {
      const blob = await downloadPresenzeXlsmExportArtifact(token, job.id, "xlsm");
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = buildExportFilename(job);
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      setSuccess(`Download avviato per l'export ${formatMonthLabel(job.period_start.slice(0, 7))}.`);
    } catch (downloadError) {
      setError(downloadError instanceof Error ? downloadError.message : "Errore download export XLSM");
    } finally {
      setDownloadingJobId(null);
    }
  }

  async function handleExport() {
    const token = getStoredAccessToken();
    if (!token) return;
    setIsSubmittingExportJob(true);
    setError(null);
    setSuccess(null);
    try {
      const { start } = monthBoundsFromValue(selectedMonth);
      const job = await createPresenzeXlsmExportJob(token, {
        period_start: start,
        collaborator_ids: contractFilter === "all" ? undefined : filteredCollaborators.map((item) => item.id),
        employee_kind: resolveEmployeeKindLabel(contractFilter) ?? null,
        template_path: templatePath.trim() || null,
      });
      const refreshedJob = await getPresenzeXlsmExportJob(token, job.id);
      setExportJobs((current) => sortExportJobs([refreshedJob, ...current.filter((item) => item.id !== refreshedJob.id)]));
      knownJobStatusesRef.current.set(refreshedJob.id, refreshedJob.status);
      setSuccess(`Export avviato. Il file sara disponibile nella sezione Ultimi export XLSM al termine dell'elaborazione.`);
    } catch (exportError) {
      setError(exportError instanceof Error ? exportError.message : "Errore export XLSM");
    } finally {
      setIsSubmittingExportJob(false);
    }
  }

  return (
    <ProtectedPage
      title="Export Giornaliere"
      description="Generazione file giornaliere XLSM."
      breadcrumb="Giornaliere"
      requiredModule="presenze"
      requiredRoles={["admin", "super_admin"]}
    >
      <div className="space-y-8">
        <ModuleWorkspaceHero
          badge={<>Export giornaliere</>}
          title="Genera il file XLSM dalle giornaliere persistite in GAIA."
          description="Seleziona il mese, filtra se serve per tipologia contrattuale e indica opzionalmente un template `.xlsm` alternativo. Il backend preserva le macro del file sorgente."
          actions={
            <>
              <ModuleWorkspaceNoticeCard
                title={templatePath.trim() ? "Template personalizzato" : "Template di default"}
                description={templatePath.trim() || "Verrà usato il template standard configurato lato backend."}
                tone="info"
              />
              <ModuleWorkspaceNoticeCard
                title={contractFilter === "all" ? "Export completo" : "Export filtrato"}
                description={
                  contractFilter === "all"
                    ? "Nessun filtro contratto: il backend includera tutti i collaboratori con giornaliere nel mese scelto."
                    : `${filteredCollaborators.length} collaboratori inclusi dal filtro contrattuale.`
                }
                tone={contractFilter === "all" ? "success" : "warning"}
              />
            </>
          }
        >
          <ModuleWorkspaceKpiRow>
            <ModuleWorkspaceKpiTile label="Collaboratori" value={collaborators.length} hint="Dataset disponibile" />
            <ModuleWorkspaceKpiTile label="Mappati GAIA" value={mappedCount} hint="Collegati a application_users" variant="emerald" />
            <ModuleWorkspaceKpiTile label="Inclusi" value={contractFilter === "all" ? "Tutti" : filteredCollaborators.length} hint="Ambito export" />
            <ModuleWorkspaceKpiTile label="Righe mese" value={scopedRecords.length} hint="Giornaliere incluse" />
          </ModuleWorkspaceKpiRow>
        </ModuleWorkspaceHero>

        {error ? <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div> : null}
        {success ? <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">{success}</div> : null}

        <section className="panel-card space-y-5">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <p className="section-title">Ultimi export XLSM</p>
              <p className="section-copy">
                L&apos;export parte come job asincrono. Puoi continuare a navigare: il file restera disponibile qui a fine elaborazione.
              </p>
            </div>
            <button className="btn-secondary" type="button" onClick={() => setIsHistoryModalOpen(true)} disabled={isLoadingExportJobs || exportJobs.length === 0}>
              Vedi storico completo{exportJobs.length > 5 ? ` (${exportJobs.length})` : ""}
            </button>
          </div>

          {activeExportJob ? (
            <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-4 text-sm text-amber-900">
              <p className="font-semibold text-amber-950">Elaborazione in corso</p>
              <p className="mt-1">
                L&apos;export di {formatMonthLabel(activeExportJob.period_start.slice(0, 7))} e in {activeExportJob.status === "running" ? "lavorazione" : "coda"}.
                Il file comparira in questa lista appena pronto.
              </p>
              {activeExportJob.params_json?.progress?.last_event ? (
                <p className="mt-2 text-xs text-amber-800">Ultimo evento: {String(activeExportJob.params_json.progress.last_event)}</p>
              ) : null}
            </div>
          ) : (
            <div className="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-4 text-sm text-emerald-800">
              Nessuna esportazione in corso. I file completati restano scaricabili da questa sezione.
            </div>
          )}

          {isLoadingExportJobs ? (
            <p className="text-sm text-gray-500">Caricamento storico export...</p>
          ) : recentExportJobs.length === 0 ? (
            <EmptyState icon={DocumentIcon} title="Nessun export eseguito" description="Avvia il primo export XLSM per popolare lo storico file." />
          ) : (
            <div className="space-y-3">
              {recentExportJobs.map((job) => (
                <article key={job.id} className="rounded-2xl border border-gray-100 bg-gray-50 px-4 py-4">
                  <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="text-base font-semibold text-gray-900">{formatMonthLabel(job.period_start.slice(0, 7))}</p>
                        <span className={`rounded-full border px-2.5 py-1 text-xs font-medium ${statusToneClasses(job.status)}`}>
                          {formatJobStatus(job.status)}
                        </span>
                      </div>
                      <p className="mt-1 text-sm text-gray-500">Creato il {formatJobDateTime(job.created_at)} · job {job.id}</p>
                      {job.status === "failed" && job.error_detail ? <p className="mt-2 text-sm text-red-700">{job.error_detail}</p> : null}
                      {job.status !== "failed" && job.params_json?.progress?.last_event ? (
                        <p className="mt-2 text-sm text-gray-600">Ultimo evento: {String(job.params_json.progress.last_event)}</p>
                      ) : null}
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      {job.status === "completed" ? (
                        <button
                          className="btn-primary"
                          type="button"
                          disabled={downloadingJobId === job.id}
                          onClick={() => void handleDownloadJob(job)}
                        >
                          {downloadingJobId === job.id ? <ExportSpinner label="Download..." /> : "Scarica file"}
                        </button>
                      ) : null}
                      {job.status === "pending" || job.status === "running" ? (
                        <span className="inline-flex items-center gap-2 rounded-full border border-amber-200 bg-white px-3 py-2 text-sm text-amber-700">
                          <span className="inline-flex h-3 w-3 animate-spin rounded-full border-2 border-amber-300 border-t-amber-700" aria-hidden="true" />
                          Elaborazione attiva
                        </span>
                      ) : null}
                    </div>
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>

        <section className="panel-card space-y-5">
          <div>
            <p className="section-title">Parametri export</p>
            <p className="section-copy">Configura il file da generare e avvia il job. Il download finale restera disponibile nella sezione Ultimi export XLSM.</p>
          </div>

          <div className="grid gap-4 lg:grid-cols-3">
            <label className="block text-sm font-medium text-gray-700">
              <span>Mese di riferimento</span>
              <div className="mt-1 flex items-center gap-2">
                <button
                  type="button"
                  className="btn-secondary px-3"
                  aria-label="Mese precedente"
                  disabled={isExporting}
                  onClick={() => setSelectedMonth((current) => shiftMonth(current, -1))}
                >
                  ‹
                </button>
                <input
                  className="form-control flex-1"
                  type="month"
                  value={selectedMonth}
                  disabled={isExporting}
                  onChange={(event) => setSelectedMonth(event.target.value)}
                />
                <button
                  type="button"
                  className="btn-secondary px-3"
                  aria-label="Mese successivo"
                  disabled={isExporting}
                  onClick={() => setSelectedMonth((current) => shiftMonth(current, 1))}
                >
                  ›
                </button>
              </div>
              <p className="mt-1 text-xs capitalize text-gray-400">{formatMonthLabel(selectedMonth)}</p>
            </label>
            <label className="block text-sm font-medium text-gray-700" htmlFor="contract-filter">
              Tipologia contratto
              <select
                id="contract-filter"
                aria-label="Tipologia contratto"
                className="form-control mt-1"
                value={contractFilter}
                disabled={isExporting}
                onChange={(event) => setContractFilter(event.target.value as ContractFilter)}
              >
                {CONTRACT_FILTER_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
              <p className="mt-1 text-xs text-gray-400">Usato per limitare l&apos;export; se lasci tutti, il file include l&apos;intero mese.</p>
            </label>
            <label className="block text-sm font-medium text-gray-700">
              Template XLSM opzionale
              <input
                className="form-control mt-1"
                value={templatePath}
                disabled={isExporting}
                onChange={(event) => setTemplatePath(event.target.value)}
                placeholder="/percorso/template.xlsm"
              />
            </label>
          </div>

          <div className="flex justify-end">
            <button className="btn-primary" type="button" onClick={() => void handleExport()} disabled={isExporting || !selectedMonth}>
              {isExporting ? <ExportSpinner /> : "Avvia export XLSM"}
            </button>
          </div>

          <div className="rounded-2xl border border-gray-100 bg-gray-50 p-4">
            <p className="section-title">Preview dataset mese</p>
            <p className="section-copy">
              {isLoadingPreview
                ? "Caricamento giornaliere del mese selezionato..."
                : `Periodo ${monthBoundsFromValue(selectedMonth).start} / ${monthBoundsFromValue(selectedMonth).end}. La preview usa le giornaliere gia persistite in GAIA.`}
            </p>
            <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-5">
              <div className="rounded-xl border border-white bg-white px-3 py-3">
                <p className="text-xs uppercase tracking-[0.16em] text-gray-400">Righe incluse</p>
                <p className="mt-2 text-2xl font-semibold text-gray-900">{scopedRecords.length}</p>
              </div>
              <div className="rounded-xl border border-white bg-white px-3 py-3">
                <p className="text-xs uppercase tracking-[0.16em] text-gray-400">Giorni speciali</p>
                <p className="mt-2 text-2xl font-semibold text-gray-900">{specialDayCount}</p>
              </div>
              <div className="rounded-xl border border-white bg-white px-3 py-3">
                <p className="text-xs uppercase tracking-[0.16em] text-gray-400">Dettaglio giornaliero ricco</p>
                <p className="mt-2 text-2xl font-semibold text-gray-900">{detailDrivenCount}</p>
              </div>
              <div className="rounded-xl border border-white bg-white px-3 py-3">
                <p className="text-xs uppercase tracking-[0.16em] text-gray-400">Giorni con trasferta</p>
                <p className="mt-2 text-2xl font-semibold text-gray-900">{trasfertaDaysCount}</p>
                <p className="mt-1 text-xs text-gray-500">
                  {formatMinutesAsHours(trasfertaMinutesTotal)} ore totali esportabili{trasfertaMontanoCount > 0 ? ` · montano ${trasfertaMontanoCount}` : ""}
                </p>
              </div>
              <div className="rounded-xl border border-white bg-white px-3 py-3">
                <p className="text-xs uppercase tracking-[0.16em] text-gray-400">Reperibilita strutturata</p>
                <p className="mt-2 text-2xl font-semibold text-gray-900">{reperibilitaBreakdown.total}</p>
                <p className="mt-1 text-xs text-gray-500">
                  ore {reperibilitaBreakdown.hours} · giorni {reperibilitaBreakdown.days} · turni {reperibilitaBreakdown.shifts}
                </p>
              </div>
            </div>
            <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50 px-3 py-3 text-sm text-amber-900">
              Il template XLSM legacy salva la reperibilita come flag `X`; la quantita strutturata resta comunque disponibile in GAIA e nella preview export.
            </div>
          </div>

          {isLoading ? (
            <p className="text-sm text-gray-500">Caricamento collaboratori...</p>
          ) : collaborators.length === 0 ? (
            <EmptyState icon={DocumentIcon} title="Nessun collaboratore importato" description="Importa prima un file JSON giornaliere per poter esportare il mese." />
          ) : (
            <div className="rounded-2xl border border-gray-100 bg-gray-50 p-4">
              <p className="section-title">Collaboratori inclusi</p>
              <p className="section-copy">
                {contractFilter === "all"
                  ? `Export aperto su ${collaborators.length} collaboratori disponibili.`
                  : `Il filtro contratto include ${filteredCollaborators.length} collaboratori su ${collaborators.length}.`}
              </p>
              <div className="mt-4 grid gap-3 md:grid-cols-3">
                <div className="rounded-xl border border-white bg-white px-3 py-3">
                  <p className="text-xs uppercase tracking-[0.16em] text-gray-400">Operai</p>
                  <p className="mt-2 text-2xl font-semibold text-gray-900">{collaborators.filter((item) => item.contract_kind === "operaio").length}</p>
                </div>
                <div className="rounded-xl border border-white bg-white px-3 py-3">
                  <p className="text-xs uppercase tracking-[0.16em] text-gray-400">Impiegati e quadri</p>
                  <p className="mt-2 text-2xl font-semibold text-gray-900">
                    {collaborators.filter((item) => item.contract_kind === "impiegato" || item.contract_kind === "quadro").length}
                  </p>
                </div>
                <div className="rounded-xl border border-white bg-white px-3 py-3">
                  <p className="text-xs uppercase tracking-[0.16em] text-gray-400">Profilo non definito</p>
                  <p className="mt-2 text-2xl font-semibold text-gray-900">{collaborators.filter((item) => item.contract_kind == null).length}</p>
                </div>
              </div>
            </div>
          )}
        </section>

        {isHistoryModalOpen ? (
          <div className="fixed inset-0 z-[70] flex items-center justify-center bg-black/45 px-4 py-6 backdrop-blur-sm">
            <div className="flex max-h-[92vh] w-full max-w-5xl flex-col overflow-hidden rounded-[28px] border border-gray-200 bg-white shadow-[0_30px_90px_rgba(15,23,42,0.24)]">
              <div className="flex items-start justify-between gap-4 border-b border-gray-100 px-6 py-5">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#1D4E35]">Storico export</p>
                  <h2 className="mt-2 text-2xl font-semibold text-gray-900">Tutti gli ultimi export XLSM</h2>
                  <p className="mt-1 text-sm text-gray-500">Consulta lo stato completo dei job e scarica i file gia pronti senza rilanciare l&apos;elaborazione.</p>
                </div>
                <button className="btn-secondary" type="button" onClick={() => setIsHistoryModalOpen(false)}>
                  Chiudi
                </button>
              </div>
              <div className="overflow-y-auto px-6 py-6">
                <div className="space-y-3">
                  {exportJobs.map((job) => (
                    <article key={job.id} className="rounded-2xl border border-gray-100 bg-gray-50 px-4 py-4">
                      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                        <div>
                          <div className="flex flex-wrap items-center gap-2">
                            <p className="text-base font-semibold text-gray-900">{formatMonthLabel(job.period_start.slice(0, 7))}</p>
                            <span className={`rounded-full border px-2.5 py-1 text-xs font-medium ${statusToneClasses(job.status)}`}>
                              {formatJobStatus(job.status)}
                            </span>
                          </div>
                          <p className="mt-1 text-sm text-gray-500">Creato il {formatJobDateTime(job.created_at)} · job {job.id}</p>
                          {job.error_detail ? <p className="mt-2 text-sm text-red-700">{job.error_detail}</p> : null}
                        </div>
                        {job.status === "completed" ? (
                          <button
                            className="btn-primary"
                            type="button"
                            disabled={downloadingJobId === job.id}
                            onClick={() => void handleDownloadJob(job)}
                          >
                            {downloadingJobId === job.id ? <ExportSpinner label="Download..." /> : "Scarica file"}
                          </button>
                        ) : null}
                      </div>
                    </article>
                  ))}
                </div>
              </div>
            </div>
          </div>
        ) : null}
      </div>
    </ProtectedPage>
  );
}
