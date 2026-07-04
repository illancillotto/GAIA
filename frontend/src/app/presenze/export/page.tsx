/* v8 ignore start -- Next page shell: covered by rendering tests; operational logic is tested in backend/helpers. */
"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import { ProtectedPage } from "@/components/app/protected-page";
import { Badge } from "@/components/ui/badge";
import {
  ModuleWorkspaceHero,
  ModuleWorkspaceKpiRow,
  ModuleWorkspaceKpiTile,
  ModuleWorkspaceNoticeCard,
} from "@/components/layout/module-workspace-hero";
import { EmptyState } from "@/components/ui/empty-state";
import { DocumentIcon } from "@/components/ui/icons";
import {
  createPresenzeStraordinariExportJob,
  createPresenzeXlsmExportJob,
  deletePresenzeStraordinariExportJob,
  deletePresenzeXlsmExportJob,
  downloadPresenzeStraordinariExportArtifact,
  downloadPresenzeXlsmExportArtifact,
  getCurrentUser,
  getPresenzeStraordinariExportJob,
  getPresenzeXlsmExportJob,
  listAllPresenzeCollaborators,
  listPresenzeStraordinariExportJobs,
  listPresenzeXlsmExportJobs,
  listPresenzeDailyRecords,
  previewPresenzeStraordinariExport,
} from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import { getPresenzeCompanyLabel } from "@/lib/presenze-display";
import type { CurrentUser, PresenzeCollaborator, PresenzeDailyRecord, PresenzeStraordinariPreviewResponse, PresenzeSyncJob } from "@/types/api";

type ContractFilter = "all" | "operaio" | "impiegato" | "quadro" | "altro" | "unassigned";
type ExportWorkspaceTab = "parameters" | "preview";
type DayColumn = {
  iso: string;
  day: number;
  weekday: string;
  isWeekend: boolean;
  isToday: boolean;
};
type CellKind = "anomaly" | "analysis" | "special" | "ferie" | "permesso" | "malattia" | "absence" | "worked" | "rest";
type StraordinariDraftItem = {
  recordId: string;
  workDate: string;
  startTime: string | null;
  endTime: string | null;
  durationLabel: string;
  motivation: string;
};

const CONTRACT_FILTER_OPTIONS: Array<{ value: ContractFilter; label: string }> = [
  { value: "all", label: "Tutti i contratti" },
  { value: "operaio", label: "Operai" },
  { value: "impiegato", label: "Impiegati" },
  { value: "quadro", label: "Quadri" },
  { value: "altro", label: "Altro" },
  { value: "unassigned", label: "Profilo non definito" },
];
const EXPORT_WORKSPACE_TABS: Array<{ id: ExportWorkspaceTab; label: string; description: string }> = [
  { id: "parameters", label: "Parametri export", description: "Configura job, template e filtri." },
  { id: "preview", label: "Anteprima export", description: "Controlla il mese con vista stile archivio." },
];
const WEEKDAY_LABELS = ["dom", "lun", "mar", "mer", "gio", "ven", "sab"];
const CELL_TONE: Record<CellKind, string> = {
  anomaly: "bg-red-50 text-red-700 ring-1 ring-inset ring-red-200 hover:bg-red-100",
  analysis: "bg-amber-50 text-amber-800 ring-1 ring-inset ring-amber-200 hover:bg-amber-100",
  special: "bg-violet-50 text-violet-700 ring-1 ring-inset ring-violet-200 hover:bg-violet-100",
  ferie: "bg-amber-50 text-amber-800 ring-1 ring-inset ring-amber-200 hover:bg-amber-100",
  permesso: "bg-sky-50 text-sky-800 ring-1 ring-inset ring-sky-200 hover:bg-sky-100",
  malattia: "bg-fuchsia-50 text-fuchsia-800 ring-1 ring-inset ring-fuchsia-200 hover:bg-fuchsia-100",
  absence: "bg-slate-100 text-slate-700 ring-1 ring-inset ring-slate-200 hover:bg-slate-200",
  worked: "bg-emerald-50 text-emerald-700 ring-1 ring-inset ring-emerald-100 hover:bg-emerald-100",
  rest: "bg-gray-50 text-gray-300 hover:bg-gray-100",
};

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

function previousMonthValue(): string {
  return shiftMonth(currentMonthValue(), -1);
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

function formatHoursCompact(minutes: number | null | undefined): string {
  if (!minutes) return "0";
  const value = minutes / 60;
  return Number.isInteger(value) ? String(value) : value.toFixed(1);
}

function buildMonthDays(monthValue: string): DayColumn[] {
  const [yearString, monthString] = monthValue.split("-");
  const year = Number(yearString);
  const month = Number(monthString);
  const total = new Date(year, month, 0).getDate();
  const today = new Date();
  const todayIso = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}-${String(today.getDate()).padStart(2, "0")}`;
  const days: DayColumn[] = [];
  for (let day = 1; day <= total; day += 1) {
    const iso = `${yearString}-${monthString}-${String(day).padStart(2, "0")}`;
    const weekdayIndex = new Date(`${iso}T00:00:00`).getDay();
    days.push({
      iso,
      day,
      weekday: WEEKDAY_LABELS[weekdayIndex],
      isWeekend: weekdayIndex === 0 || weekdayIndex === 6,
      isToday: iso === todayIso,
    });
  }
  return days;
}

function effectiveExtraMinutes(record: PresenzeDailyRecord): number {
  return (
    record.effective_extra_minutes ??
    (record.effective_straordinario_minutes ?? record.straordinario_minutes ?? 0) +
      (record.effective_mpe_minutes ?? record.mpe_minutes ?? 0)
  );
}

function classifyCell(record: PresenzeDailyRecord): CellKind {
  if (record.operational_status === "blocking") return "anomaly";
  if (record.operational_status === "in_analysis") return "analysis";
  if (record.operational_status === "unknown" && (record.detail_anomalies.length > 0 || record.detail_error)) return "anomaly";
  if (record.special_day) return "special";
  if (record.resolved_absence_cause === "ferie") return "ferie";
  if (record.resolved_absence_cause === "permesso") return "permesso";
  if (record.resolved_absence_cause === "malattia") return "malattia";
  if ((record.ordinary_minutes ?? 0) > 0) return "worked";
  if ((record.absence_minutes ?? 0) > 0) return "absence";
  return "rest";
}

function cellPrimaryLabel(record: PresenzeDailyRecord, kind: CellKind): string {
  if (kind === "worked" || kind === "special") {
    return formatHoursCompact(record.ordinary_minutes ?? record.teo_minutes);
  }
  if (kind === "ferie") return "Fer";
  if (kind === "permesso") return "Perm";
  if (kind === "malattia") return "Mal";
  if (kind === "analysis") return "Anal";
  if (kind === "absence" || kind === "anomaly") {
    const status = (record.detail_status ?? record.stato ?? "").trim();
    if (status) {
      return status.length > 4 ? status.slice(0, 4) : status;
    }
    return formatHoursCompact(record.absence_minutes);
  }
  return "·";
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

function buildStraordinariFilename(job: PresenzeSyncJob): string {
  const explicitFilename = typeof job.params_json?.output_filename === "string" ? job.params_json.output_filename : null;
  if (explicitFilename) {
    return explicitFilename;
  }
  const monthKey = job.period_start.slice(0, 7);
  return `straordinari_${monthKey}.xlsx`;
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
  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null);
  const [collaborators, setCollaborators] = useState<PresenzeCollaborator[]>([]);
  const [records, setRecords] = useState<PresenzeDailyRecord[]>([]);
  const [selectedMonth, setSelectedMonth] = useState(currentMonthValue());
  const [straordinariMonth] = useState(previousMonthValue());
  const [contractFilter, setContractFilter] = useState<ContractFilter>("all");
  const [activeTab, setActiveTab] = useState<ExportWorkspaceTab>("parameters");
  const [templatePath, setTemplatePath] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingPreview, setIsLoadingPreview] = useState(false);
  const [isSubmittingExportJob, setIsSubmittingExportJob] = useState(false);
  const [isLoadingExportJobs, setIsLoadingExportJobs] = useState(true);
  const [exportJobs, setExportJobs] = useState<PresenzeSyncJob[]>([]);
  const [isLoadingStraordinariJobs, setIsLoadingStraordinariJobs] = useState(true);
  const [straordinariJobs, setStraordinariJobs] = useState<PresenzeSyncJob[]>([]);
  const [downloadingJobId, setDownloadingJobId] = useState<string | null>(null);
  const [deletingJobId, setDeletingJobId] = useState<string | null>(null);
  const [isHistoryModalOpen, setIsHistoryModalOpen] = useState(false);
  const [isStraordinariModalOpen, setIsStraordinariModalOpen] = useState(false);
  const [isLoadingStraordinariPreview, setIsLoadingStraordinariPreview] = useState(false);
  const [isSubmittingStraordinariJob, setIsSubmittingStraordinariJob] = useState(false);
  const [selectedStraordinariCollaboratorId, setSelectedStraordinariCollaboratorId] = useState<string>("");
  const [straordinariPreview, setStraordinariPreview] = useState<PresenzeStraordinariPreviewResponse | null>(null);
  const [straordinariDraftItems, setStraordinariDraftItems] = useState<StraordinariDraftItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const knownJobStatusesRef = useRef<Map<string, string>>(new Map());
  const knownStraordinariJobStatusesRef = useRef<Map<string, string>>(new Map());
  const canManageXlsm = currentUser?.role === "admin" || currentUser?.role === "super_admin";

  useEffect(() => {
    const token = getStoredAccessToken();
    if (!token) return;
    Promise.all([getCurrentUser(token), listAllPresenzeCollaborators(token)])
      .then(([sessionUser, response]) => {
        setCurrentUser(sessionUser);
        setCollaborators(response);
      })
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
    if (!canManageXlsm) {
      setIsLoadingExportJobs(false);
      setExportJobs([]);
      knownJobStatusesRef.current = new Map();
      return;
    }
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
  }, [canManageXlsm]);

  useEffect(() => {
    const token = getStoredAccessToken();
    if (!token) return;
    const authToken = token;

    let cancelled = false;
    async function refreshStraordinariJobs(options?: { silent?: boolean; suppressCompletionNotice?: boolean }) {
      if (!options?.silent) {
        setIsLoadingStraordinariJobs(true);
      }
      try {
        const items = sortExportJobs(await listPresenzeStraordinariExportJobs(authToken, { limit: 25 }));
        if (cancelled) return;

        if (!options?.suppressCompletionNotice) {
          for (const item of items) {
            const previousStatus = knownStraordinariJobStatusesRef.current.get(item.id);
            if ((previousStatus === "pending" || previousStatus === "running") && item.status === "completed") {
              setSuccess(`Richiesta straordinari ${formatMonthLabel(item.period_start.slice(0, 7))} pronta. Trovi il file nella sezione dedicata.`);
            }
          }
        }

        knownStraordinariJobStatusesRef.current = new Map(items.map((item) => [item.id, item.status]));
        setStraordinariJobs(items);
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : "Errore caricamento storico export straordinari");
        }
      } finally {
        if (!cancelled && !options?.silent) {
          setIsLoadingStraordinariJobs(false);
        }
      }
    }

    void refreshStraordinariJobs({ suppressCompletionNotice: true });
    const intervalId = window.setInterval(() => {
      if (knownStraordinariJobStatusesRef.current.size === 0) {
        return;
      }
      const hasActiveJob = Array.from(knownStraordinariJobStatusesRef.current.values()).some((status) => status === "pending" || status === "running");
      if (!hasActiveJob) {
        return;
      }
      void refreshStraordinariJobs({ silent: true });
    }, 2500);

    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, []);

  useEffect(() => {
    if (!isHistoryModalOpen && !isStraordinariModalOpen) {
      return;
    }
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, [isHistoryModalOpen, isStraordinariModalOpen]);

  const mappedCount = useMemo(() => collaborators.filter((item) => item.application_user_id != null).length, [collaborators]);
  const straordinariSelectableCollaborators = useMemo(() => {
    if (!currentUser) return [];
    if (canManageXlsm) return collaborators;
    return collaborators.filter((item) => item.application_user_id === currentUser.id);
  }, [canManageXlsm, collaborators, currentUser]);
  const filteredCollaborators = useMemo(
    () => collaborators.filter((item) => matchesContractFilter(item, contractFilter)),
    [collaborators, contractFilter],
  );
  const filteredCollaboratorIds = useMemo(() => new Set(filteredCollaborators.map((item) => item.id)), [filteredCollaborators]);
  const scopedRecords = useMemo(
    () => records.filter((record) => filteredCollaboratorIds.has(record.collaborator_id)),
    [records, filteredCollaboratorIds],
  );
  const monthDays = useMemo(() => buildMonthDays(selectedMonth), [selectedMonth]);
  const previewRecordIndex = useMemo(() => {
    const index = new Map<string, PresenzeDailyRecord>();
    for (const record of scopedRecords) {
      index.set(`${record.collaborator_id}|${record.work_date}`, record);
    }
    return index;
  }, [scopedRecords]);
  const previewRows = useMemo(() => {
    return filteredCollaborators
      .filter((collaborator) => scopedRecords.some((record) => record.collaborator_id === collaborator.id))
      .map((collaborator) => {
        const collaboratorRecords = scopedRecords.filter((record) => record.collaborator_id === collaborator.id);
        const ordinaryMinutes = collaboratorRecords.reduce((sum, record) => sum + (record.ordinary_minutes ?? 0), 0);
        const extraMinutes = collaboratorRecords.reduce((sum, record) => sum + effectiveExtraMinutes(record), 0);
        const anomalyCount = collaboratorRecords.filter((record) => classifyCell(record) === "anomaly").length;
        return {
          collaborator,
          company: getPresenzeCompanyLabel(collaborator.company_label, collaborator.company_code, ""),
          ordinaryMinutes,
          extraMinutes,
          anomalyCount,
          dayCount: collaboratorRecords.length,
        };
      })
      .sort((left, right) => left.collaborator.name.localeCompare(right.collaborator.name));
  }, [filteredCollaborators, scopedRecords]);
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
  const activeStraordinariJob = useMemo(
    () => straordinariJobs.find((job) => job.status === "pending" || job.status === "running") ?? null,
    [straordinariJobs],
  );
  const isExporting = isSubmittingExportJob || activeExportJob != null;
  const recentExportJobs = useMemo(() => exportJobs.slice(0, 5), [exportJobs]);
  const recentStraordinariJobs = useMemo(() => straordinariJobs.slice(0, 5), [straordinariJobs]);

  useEffect(() => {
    if (selectedStraordinariCollaboratorId || straordinariSelectableCollaborators.length === 0) {
      return;
    }
    if (straordinariSelectableCollaborators.length === 1) {
      setSelectedStraordinariCollaboratorId(straordinariSelectableCollaborators[0].id);
    }
  }, [selectedStraordinariCollaboratorId, straordinariSelectableCollaborators]);

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

  async function handleDeleteJob(job: PresenzeSyncJob) {
    const token = getStoredAccessToken();
    if (!token) return;
    setDeletingJobId(job.id);
    setError(null);
    setSuccess(null);
    try {
      await deletePresenzeXlsmExportJob(token, job.id);
      setExportJobs((current) => current.filter((item) => item.id !== job.id));
      knownJobStatusesRef.current.delete(job.id);
      setSuccess(`Export ${formatMonthLabel(job.period_start.slice(0, 7))} rimosso dallo storico.`);
    } catch (deleteError) {
      setError(deleteError instanceof Error ? deleteError.message : "Errore eliminazione export XLSM");
    } finally {
      setDeletingJobId(null);
    }
  }

  async function handleOpenStraordinariModal() {
    const token = getStoredAccessToken();
    if (!token) return;
    setIsStraordinariModalOpen(true);
    setIsLoadingStraordinariPreview(true);
    setError(null);
    setSuccess(null);
    try {
      const preview = await previewPresenzeStraordinariExport(token, {
        collaboratorId: selectedStraordinariCollaboratorId || null,
      });
      setStraordinariPreview(preview);
      setStraordinariDraftItems(
        preview.items.map((item) => ({
          recordId: item.record_id,
          workDate: item.work_date,
          startTime: item.start_time,
          endTime: item.end_time,
          durationLabel: item.duration_label,
          motivation: item.motivation,
        })),
      );
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Errore caricamento anteprima straordinari");
      setIsStraordinariModalOpen(false);
    } finally {
      setIsLoadingStraordinariPreview(false);
    }
  }

  async function handleCreateStraordinariJob() {
    const token = getStoredAccessToken();
    if (!token) return;
    setIsSubmittingStraordinariJob(true);
    setError(null);
    setSuccess(null);
    try {
      const collaboratorId = straordinariPreview?.collaborator.id ?? selectedStraordinariCollaboratorId ?? null;
      const job = await createPresenzeStraordinariExportJob(token, {
        collaborator_id: collaboratorId,
        items: straordinariDraftItems.map((item) => ({
          record_id: item.recordId,
          motivation: item.motivation,
        })),
      });
      const refreshedJob = await getPresenzeStraordinariExportJob(token, job.id);
      setStraordinariJobs((current) => sortExportJobs([refreshedJob, ...current.filter((item) => item.id !== refreshedJob.id)]));
      knownStraordinariJobStatusesRef.current.set(refreshedJob.id, refreshedJob.status);
      setIsStraordinariModalOpen(false);
      setSuccess("Richiesta straordinari avviata. Il file restera disponibile nella sezione dedicata al termine dell'elaborazione.");
    } catch (jobError) {
      setError(jobError instanceof Error ? jobError.message : "Errore export straordinari");
    } finally {
      setIsSubmittingStraordinariJob(false);
    }
  }

  async function handleDownloadStraordinariJob(job: PresenzeSyncJob) {
    const token = getStoredAccessToken();
    if (!token) return;
    setDownloadingJobId(job.id);
    setError(null);
    try {
      const blob = await downloadPresenzeStraordinariExportArtifact(token, job.id, "xlsx");
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = buildStraordinariFilename(job);
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      setSuccess(`Download avviato per la richiesta straordinari ${formatMonthLabel(job.period_start.slice(0, 7))}.`);
    } catch (downloadError) {
      setError(downloadError instanceof Error ? downloadError.message : "Errore download straordinari");
    } finally {
      setDownloadingJobId(null);
    }
  }

  async function handleDeleteStraordinariJob(job: PresenzeSyncJob) {
    const token = getStoredAccessToken();
    if (!token) return;
    setDeletingJobId(job.id);
    setError(null);
    setSuccess(null);
    try {
      await deletePresenzeStraordinariExportJob(token, job.id);
      setStraordinariJobs((current) => current.filter((item) => item.id !== job.id));
      knownStraordinariJobStatusesRef.current.delete(job.id);
      setSuccess(`Richiesta straordinari ${formatMonthLabel(job.period_start.slice(0, 7))} rimossa dallo storico.`);
    } catch (deleteError) {
      setError(deleteError instanceof Error ? deleteError.message : "Errore eliminazione export straordinari");
    } finally {
      setDeletingJobId(null);
    }
  }

  return (
    <ProtectedPage
      title="Export Giornaliere"
      description="Export giornaliere e richiesta straordinari dai dati persistiti in GAIA."
      breadcrumb="Giornaliere"
      requiredModule="presenze"
    >
      <div className="space-y-8">
        <ModuleWorkspaceHero
          badge={<>Export presenze</>}
          title="Genera export giornaliere e richieste straordinari dai dati persistiti in GAIA."
          description="La richiesta straordinari usa sempre il mese precedente e permette all'operatore di compilare le motivazioni in una modal prima della generazione del file Excel."
          actions={
            <>
              <ModuleWorkspaceNoticeCard
                title="Straordinari mese precedente"
                description={`Periodo fisso: ${formatMonthLabel(straordinariMonth)}.`}
                tone="info"
              />
              <ModuleWorkspaceNoticeCard
                title={canManageXlsm ? "Export XLSM amministrativo" : "Accesso operatore"}
                description={
                  canManageXlsm
                    ? "Il workspace mantiene anche l'export giornaliere XLSM per il personale amministrativo."
                    : "Puoi generare solo la richiesta straordinari associata al tuo collaboratore GAIA."
                }
                tone={canManageXlsm ? "success" : "warning"}
              />
            </>
          }
        >
          <ModuleWorkspaceKpiRow>
            <ModuleWorkspaceKpiTile label="Collaboratori" value={collaborators.length} hint="Dataset disponibile" />
            <ModuleWorkspaceKpiTile label="Mappati GAIA" value={mappedCount} hint="Collegati a application_users" variant="emerald" />
            <ModuleWorkspaceKpiTile label="Straordinari mese" value={formatMonthLabel(straordinariMonth)} hint="Periodo richiesta" />
            <ModuleWorkspaceKpiTile label="Operatore" value={currentUser?.username ?? "-"} hint="Utente corrente" />
          </ModuleWorkspaceKpiRow>
        </ModuleWorkspaceHero>

        {error ? <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div> : null}
        {success ? <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">{success}</div> : null}

        <section className="panel-card space-y-5">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <p className="section-title">Richiesta straordinari</p>
              <p className="section-copy">
                Il file viene generato dal template Excel usando le giornaliere persistite del mese precedente. Prima del job puoi compilare o correggere la motivazione per ogni giornata proposta.
              </p>
            </div>
            <div className="rounded-2xl border border-emerald-100 bg-emerald-50 px-4 py-4 text-sm text-emerald-900">
              <p className="font-semibold text-emerald-950">{formatMonthLabel(straordinariMonth)}</p>
              <p className="mt-1">La finestra viene caricata solo sulle giornate con extra effettivo maggiore di zero.</p>
            </div>
          </div>

          <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_auto]">
            <label className="block text-sm font-medium text-gray-700">
              Collaboratore per la richiesta
              <select
                className="form-control mt-1"
                value={selectedStraordinariCollaboratorId}
                onChange={(event) => setSelectedStraordinariCollaboratorId(event.target.value)}
                disabled={straordinariSelectableCollaborators.length <= 1 || isSubmittingStraordinariJob || isLoadingStraordinariPreview}
              >
                {straordinariSelectableCollaborators.length > 1 ? <option value="">Seleziona collaboratore</option> : null}
                {straordinariSelectableCollaborators.map((collaborator) => (
                  <option key={collaborator.id} value={collaborator.id}>
                    {collaborator.name} · {collaborator.employee_code}
                  </option>
                ))}
              </select>
              <p className="mt-1 text-xs text-gray-400">
                {straordinariSelectableCollaborators.length === 0
                  ? "Nessun collaboratore associato al tuo utente GAIA."
                  : "Se apri la modal vedrai solo le giornate candidate del mese precedente."}
              </p>
            </label>
            <div className="flex items-end">
              <button
                className="btn-primary"
                type="button"
                onClick={() => void handleOpenStraordinariModal()}
                disabled={straordinariSelectableCollaborators.length === 0 || (!selectedStraordinariCollaboratorId && straordinariSelectableCollaborators.length > 1)}
              >
                Compila motivazioni
              </button>
            </div>
          </div>

          {activeStraordinariJob ? (
            <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-4 text-sm text-amber-900">
              <p className="font-semibold text-amber-950">Generazione in corso</p>
              <p className="mt-1">
                La richiesta straordinari di {formatMonthLabel(activeStraordinariJob.period_start.slice(0, 7))} e in {activeStraordinariJob.status === "running" ? "lavorazione" : "coda"}.
              </p>
            </div>
          ) : (
            <div className="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-4 text-sm text-emerald-800">
              Nessuna richiesta straordinari in corso. I file completati restano scaricabili da questa sezione.
            </div>
          )}

          {isLoadingStraordinariJobs ? (
            <p className="text-sm text-gray-500">Caricamento storico straordinari...</p>
          ) : recentStraordinariJobs.length === 0 ? (
            <EmptyState icon={DocumentIcon} title="Nessuna richiesta straordinari" description="Apri la modal, compila le motivazioni giornaliere e genera il primo file Excel." />
          ) : (
            <div className="space-y-3">
              {recentStraordinariJobs.map((job) => (
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
                      {job.error_detail ? <p className="mt-2 text-sm text-red-700">{job.error_detail}</p> : null}
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      {job.status === "completed" ? (
                        <button
                          className="btn-primary"
                          type="button"
                          disabled={downloadingJobId === job.id}
                          onClick={() => void handleDownloadStraordinariJob(job)}
                        >
                          {downloadingJobId === job.id ? <ExportSpinner label="Download..." /> : "Scarica file"}
                        </button>
                      ) : null}
                      {job.status === "completed" || job.status === "failed" || job.status === "cancelled" ? (
                        <button
                          className="btn-secondary"
                          type="button"
                          disabled={deletingJobId === job.id}
                          onClick={() => void handleDeleteStraordinariJob(job)}
                        >
                          {deletingJobId === job.id ? "Rimozione..." : "Rimuovi"}
                        </button>
                      ) : null}
                    </div>
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>

        {canManageXlsm ? (
          <>
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
                      {job.status === "completed" || job.status === "failed" || job.status === "cancelled" ? (
                        <button
                          className="btn-secondary"
                          type="button"
                          disabled={deletingJobId === job.id}
                          onClick={() => void handleDeleteJob(job)}
                        >
                          {deletingJobId === job.id ? "Rimozione..." : "Rimuovi"}
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
          <div className="space-y-4">
            <div>
              <p className="section-title">Workspace export</p>
              <p className="section-copy">
                Configura il job oppure controlla l&apos;anteprima del mese con la stessa logica dati usata dall&apos;archivio giornaliere.
              </p>
            </div>
            <div className="flex flex-wrap gap-3">
              {EXPORT_WORKSPACE_TABS.map((tab) => {
                const active = activeTab === tab.id;
                return (
                  <button
                    key={tab.id}
                    type="button"
                    onClick={() => setActiveTab(tab.id)}
                    className={
                      active
                        ? "rounded-2xl border border-[#1D4E35] bg-[#1D4E35] px-4 py-3 text-left text-sm text-white shadow-sm"
                        : "rounded-2xl border border-gray-200 bg-white px-4 py-3 text-left text-sm text-gray-700 hover:border-gray-300 hover:bg-gray-50"
                    }
                  >
                    <span className="block font-semibold">{tab.label}</span>
                    <span className={`mt-1 block text-xs ${active ? "text-white/80" : "text-gray-500"}`}>{tab.description}</span>
                  </button>
                );
              })}
            </div>
          </div>

          <div className="rounded-[28px] border border-gray-100 bg-gray-50/80 p-4 sm:p-6">
            <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(280px,360px)] lg:items-start">
              <div className="grid gap-4 lg:grid-cols-2">
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
              </div>
              <div className="rounded-2xl border border-emerald-100 bg-white px-4 py-4">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#1D4E35]">Dataset selezionato</p>
                <p className="mt-2 text-lg font-semibold text-gray-900">{formatMonthLabel(selectedMonth)}</p>
                <p className="mt-1 text-sm text-gray-500">
                  {isLoadingPreview
                    ? "Caricamento giornaliere del mese in corso..."
                    : `${previewRows.length} collaboratori con ${scopedRecords.length} righe utili alla preview export.`}
                </p>
              </div>
            </div>
          </div>

          {activeTab === "parameters" ? (
            <>
              <div className="grid gap-4 lg:grid-cols-3">
                <label className="block text-sm font-medium text-gray-700 lg:col-span-2">
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
            </>
          ) : (
            <>
              <div className="rounded-2xl border border-gray-100 bg-gray-50 p-4">
                <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
                  <div>
                    <p className="section-title">Anteprima export</p>
                    <p className="section-copy">
                      Vista matrice del mese selezionato, pensata per controllare i dati prima dell&apos;export. Riprende l&apos;impostazione dell&apos;archivio giornaliere.
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2 text-xs text-gray-500">
                    <span className="rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1">verde = lavorato</span>
                    <span className="rounded-full border border-violet-200 bg-violet-50 px-3 py-1">viola = giorno speciale</span>
                    <span className="rounded-full border border-red-200 bg-red-50 px-3 py-1">rosso = anomalia</span>
                  </div>
                </div>
                <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-5">
                  <div className="rounded-xl border border-white bg-white px-3 py-3">
                    <p className="text-xs uppercase tracking-[0.16em] text-gray-400">Collaboratori in matrice</p>
                    <p className="mt-2 text-2xl font-semibold text-gray-900">{previewRows.length}</p>
                  </div>
                  <div className="rounded-xl border border-white bg-white px-3 py-3">
                    <p className="text-xs uppercase tracking-[0.16em] text-gray-400">Righe incluse</p>
                    <p className="mt-2 text-2xl font-semibold text-gray-900">{scopedRecords.length}</p>
                  </div>
                  <div className="rounded-xl border border-white bg-white px-3 py-3">
                    <p className="text-xs uppercase tracking-[0.16em] text-gray-400">Anomalie rilevate</p>
                    <p className="mt-2 text-2xl font-semibold text-gray-900">
                      {previewRows.reduce((sum, row) => sum + row.anomalyCount, 0)}
                    </p>
                  </div>
                  <div className="rounded-xl border border-white bg-white px-3 py-3">
                    <p className="text-xs uppercase tracking-[0.16em] text-gray-400">Straordinario effettivo</p>
                    <p className="mt-2 text-2xl font-semibold text-gray-900">
                      {formatMinutesAsHours(previewRows.reduce((sum, row) => sum + row.extraMinutes, 0))}h
                    </p>
                  </div>
                  <div className="rounded-xl border border-white bg-white px-3 py-3">
                    <p className="text-xs uppercase tracking-[0.16em] text-gray-400">Ore ordinarie</p>
                    <p className="mt-2 text-2xl font-semibold text-gray-900">
                      {formatMinutesAsHours(previewRows.reduce((sum, row) => sum + row.ordinaryMinutes, 0))}h
                    </p>
                  </div>
                </div>
              </div>

              {isLoadingPreview ? (
                <p className="text-sm text-gray-500">Caricamento anteprima export...</p>
              ) : previewRows.length === 0 ? (
                <EmptyState
                  icon={DocumentIcon}
                  title="Nessuna riga nel mese selezionato"
                  description="Non risultano giornaliere compatibili con il filtro attuale, quindi l'anteprima export è vuota."
                />
              ) : (
                <div className="overflow-hidden rounded-[28px] border border-gray-200 bg-white shadow-sm">
                  <div className="overflow-x-auto">
                    <table className="min-w-full border-separate border-spacing-0">
                      <thead>
                        <tr className="bg-[#F6F8F7]">
                          <th className="sticky left-0 z-20 min-w-[280px] border-b border-r border-gray-200 bg-[#F6F8F7] px-4 py-3 text-left text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">
                            Collaboratore
                          </th>
                          {monthDays.map((day) => (
                            <th
                              key={day.iso}
                              className={`min-w-[52px] border-b border-r border-gray-200 px-2 py-3 text-center text-[11px] font-semibold uppercase tracking-[0.08em] ${
                                day.isWeekend ? "bg-amber-50 text-amber-800" : "text-gray-500"
                              } ${day.isToday ? "bg-emerald-50 text-emerald-800" : ""}`}
                            >
                              <div>{day.day}</div>
                              <div className="mt-1 text-[10px]">{day.weekday}</div>
                            </th>
                          ))}
                          <th className="min-w-[110px] border-b border-r border-gray-200 bg-[#F6F8F7] px-3 py-3 text-left text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">
                            Ordinarie
                          </th>
                          <th className="min-w-[110px] border-b border-r border-gray-200 bg-[#F6F8F7] px-3 py-3 text-left text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">
                            Extra
                          </th>
                          <th className="min-w-[110px] border-b border-gray-200 bg-[#F6F8F7] px-3 py-3 text-left text-xs font-semibold uppercase tracking-[0.16em] text-gray-500">
                            Anomalie
                          </th>
                        </tr>
                      </thead>
                      <tbody>
                        {previewRows.map((row) => (
                          <tr key={row.collaborator.id} className="align-top">
                            <td className="sticky left-0 z-10 border-b border-r border-gray-100 bg-white px-4 py-3">
                              <div className="space-y-1">
                                <div className="font-semibold text-gray-900">{row.collaborator.name}</div>
                                <div className="text-xs text-gray-500">
                                  {row.collaborator.employee_code} · {row.company}
                                </div>
                                <div className="flex flex-wrap gap-2">
                                  {row.collaborator.contract_kind ? <Badge variant="neutral">{row.collaborator.contract_kind}</Badge> : null}
                                  <Badge variant={row.anomalyCount > 0 ? "warning" : "success"}>
                                    {row.dayCount} giorni
                                  </Badge>
                                </div>
                              </div>
                            </td>
                            {monthDays.map((day) => {
                              const record = previewRecordIndex.get(`${row.collaborator.id}|${day.iso}`) ?? null;
                              const kind = record ? classifyCell(record) : "rest";
                              return (
                                <td key={day.iso} className="border-b border-r border-gray-100 px-1 py-1 text-center">
                                  <div
                                    className={`flex h-10 min-w-[44px] items-center justify-center rounded-xl text-[11px] font-semibold ${CELL_TONE[kind]}`}
                                    title={
                                      record
                                        ? `${day.iso} · ${record.detail_status ?? record.stato ?? "giornata"} · ord ${formatHoursCompact(record.ordinary_minutes)}h`
                                        : `${day.iso} · nessun record`
                                    }
                                  >
                                    {record ? cellPrimaryLabel(record, kind) : "·"}
                                  </div>
                                </td>
                              );
                            })}
                            <td className="border-b border-r border-gray-100 px-3 py-3 text-sm font-semibold text-gray-900">
                              {formatMinutesAsHours(row.ordinaryMinutes)}h
                            </td>
                            <td className="border-b border-r border-gray-100 px-3 py-3 text-sm font-semibold text-gray-900">
                              {formatMinutesAsHours(row.extraMinutes)}h
                            </td>
                            <td className="border-b border-gray-100 px-3 py-3 text-sm">
                              <span className={row.anomalyCount > 0 ? "font-semibold text-red-700" : "text-gray-500"}>{row.anomalyCount}</span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </>
          )}

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
          </>
        ) : null}

        {isStraordinariModalOpen ? (
          <div className="fixed inset-0 z-[75] flex items-center justify-center bg-black/45 px-4 py-6 backdrop-blur-sm">
            <div className="flex max-h-[92vh] w-full max-w-5xl flex-col overflow-hidden rounded-[28px] border border-gray-200 bg-white shadow-[0_30px_90px_rgba(15,23,42,0.24)]">
              <div className="flex items-start justify-between gap-4 border-b border-gray-100 px-6 py-5">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#1D4E35]">Motivazioni straordinari</p>
                  <h2 className="mt-2 text-2xl font-semibold text-gray-900">{formatMonthLabel(straordinariMonth)}</h2>
                  <p className="mt-1 text-sm text-gray-500">
                    Compila la motivazione per ogni giornata proposta prima di avviare la generazione del file Excel.
                  </p>
                </div>
                <button className="btn-secondary" type="button" onClick={() => setIsStraordinariModalOpen(false)} disabled={isSubmittingStraordinariJob}>
                  Chiudi
                </button>
              </div>
              <div className="overflow-y-auto px-6 py-6">
                {isLoadingStraordinariPreview ? (
                  <p className="text-sm text-gray-500">Caricamento giornate candidate...</p>
                ) : straordinariPreview == null || straordinariDraftItems.length === 0 ? (
                  <EmptyState
                    icon={DocumentIcon}
                    title="Nessuna giornata candidata"
                    description="Nel mese precedente non risultano giornate con extra effettivo da esportare nel modulo straordinari."
                  />
                ) : (
                  <div className="space-y-4">
                    <div className="rounded-2xl border border-gray-100 bg-gray-50 px-4 py-4">
                      <p className="text-sm font-semibold text-gray-900">{straordinariPreview.collaborator.name}</p>
                      <p className="mt-1 text-sm text-gray-500">
                        {straordinariPreview.collaborator.employee_code} · {straordinariDraftItems.length} giornate candidate
                      </p>
                    </div>
                    <div className="space-y-3">
                      {straordinariDraftItems.map((item) => (
                        <article key={item.recordId} className="rounded-2xl border border-gray-100 bg-gray-50 px-4 py-4">
                          <div className="grid gap-4 lg:grid-cols-[220px_170px_minmax(0,1fr)]">
                            <div>
                              <p className="text-xs uppercase tracking-[0.16em] text-gray-400">Giornata</p>
                              <p className="mt-2 text-sm font-semibold text-gray-900">{item.workDate}</p>
                            </div>
                            <div>
                              <p className="text-xs uppercase tracking-[0.16em] text-gray-400">Fascia e durata</p>
                              <p className="mt-2 text-sm font-semibold text-gray-900">
                                {(item.startTime && item.endTime) ? `${item.startTime} - ${item.endTime}` : "Orario da verificare"}
                              </p>
                              <p className="mt-1 text-xs text-gray-500">{item.durationLabel}</p>
                            </div>
                            <label className="block text-sm font-medium text-gray-700">
                              Motivazione
                              <input
                                className="form-control mt-1"
                                value={item.motivation}
                                onChange={(event) =>
                                  setStraordinariDraftItems((current) =>
                                    current.map((draft) => (draft.recordId === item.recordId ? { ...draft, motivation: event.target.value } : draft)),
                                  )
                                }
                                placeholder="Compila la motivazione della giornata"
                              />
                            </label>
                          </div>
                        </article>
                      ))}
                    </div>
                  </div>
                )}
              </div>
              <div className="flex items-center justify-between gap-3 border-t border-gray-100 px-6 py-5">
                <p className="text-sm text-gray-500">Il file verra generato come job asincrono e restera scaricabile nello storico.</p>
                <button
                  className="btn-primary"
                  type="button"
                  onClick={() => void handleCreateStraordinariJob()}
                  disabled={isSubmittingStraordinariJob || straordinariDraftItems.length === 0}
                >
                  {isSubmittingStraordinariJob ? <ExportSpinner label="Generazione..." /> : "Genera file straordinari"}
                </button>
              </div>
            </div>
          </div>
        ) : null}

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
                          {job.status === "completed" || job.status === "failed" || job.status === "cancelled" ? (
                            <button
                              className="btn-secondary"
                              type="button"
                              disabled={deletingJobId === job.id}
                              onClick={() => void handleDeleteJob(job)}
                            >
                              {deletingJobId === job.id ? "Rimozione..." : "Rimuovi"}
                            </button>
                          ) : null}
                        </div>
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

/* v8 ignore stop */
// Keeps this page present in V8 coverage after excluding the shell above.
export const __presenzeExportPageCoverageMarker = true;
