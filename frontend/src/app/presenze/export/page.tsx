"use client";

import { useEffect, useMemo, useState } from "react";

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

function ExportSpinner() {
  return (
    <div className="flex items-center gap-3">
      <span className="inline-flex h-5 w-5 animate-spin rounded-full border-2 border-white/35 border-t-white" aria-hidden="true" />
      <span>Esportazione in corso...</span>
    </div>
  );
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
  const [exportJob, setExportJob] = useState<PresenzeSyncJob | null>(null);
  const [downloadedJobId, setDownloadedJobId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

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
  const isExporting =
    isSubmittingExportJob ||
    exportJob?.status === "pending" ||
    exportJob?.status === "running" ||
    (exportJob?.status === "completed" && downloadedJobId !== exportJob.id);
  const exportProgress = exportJob?.params_json?.progress;

  useEffect(() => {
    if (!exportJob || !["pending", "running"].includes(exportJob.status)) {
      return;
    }
    const token = getStoredAccessToken();
    if (!token) return;
    const intervalId = window.setInterval(() => {
      void getPresenzeXlsmExportJob(token, exportJob.id)
        .then((job) => setExportJob(job))
        .catch((loadError) => setError(loadError instanceof Error ? loadError.message : "Errore polling export XLSM"));
    }, 2000);
    return () => {
      window.clearInterval(intervalId);
    };
  }, [exportJob]);

  useEffect(() => {
    if (!exportJob || exportJob.status !== "completed" || downloadedJobId === exportJob.id) {
      return;
    }
    const token = getStoredAccessToken();
    if (!token) return;
    void downloadPresenzeXlsmExportArtifact(token, exportJob.id, "xlsm")
      .then((blob) => {
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = `presenze_giornaliere_${selectedMonth}.xlsm`;
        document.body.appendChild(link);
        link.click();
        link.remove();
        URL.revokeObjectURL(url);
        setDownloadedJobId(exportJob.id);
        setSuccess("Export XLSM generato e download avviato.");
      })
      .catch((downloadError) => setError(downloadError instanceof Error ? downloadError.message : "Errore download export XLSM"));
  }, [downloadedJobId, exportJob, selectedMonth]);

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
      setExportJob(job);
      setDownloadedJobId(null);
      setSuccess(`Job export XLSM creato: ${job.id}. Attendo il completamento del worker.`);
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
        {isExporting ? (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#183325]/25 px-4 backdrop-blur-[2px]">
            <div className="w-full max-w-md rounded-3xl border border-[#d8dfd3] bg-white px-6 py-5 shadow-2xl">
              <div className="flex items-center gap-4">
                <span className="inline-flex h-11 w-11 animate-spin rounded-full border-[3px] border-[#d8dfd3] border-t-[#1D4E35]" aria-hidden="true" />
                <div>
                  <p className="text-sm font-semibold text-[#183325]">Preparazione file XLSM</p>
                  <p className="mt-1 text-sm text-gray-600">
                    {exportProgress?.state === "running"
                      ? "Il worker server sta preparando il file e preservando le macro del template."
                      : "Il job export è in coda e sta per essere preso in carico dal worker."}
                  </p>
                  {exportJob ? <p className="mt-2 text-xs text-gray-500">Job {exportJob.id} · stato {exportJob.status}</p> : null}
                  {exportProgress?.last_event ? <p className="mt-1 text-xs text-gray-500">Ultimo evento: {String(exportProgress.last_event)}</p> : null}
                </div>
              </div>
            </div>
          </div>
        ) : null}
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
          <div>
            <p className="section-title">Parametri export</p>
            <p className="section-copy">Configura il file da generare e avvia il download direttamente dal backend.</p>
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
              {isExporting ? <ExportSpinner /> : "Scarica XLSM"}
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
      </div>
    </ProtectedPage>
  );
}
