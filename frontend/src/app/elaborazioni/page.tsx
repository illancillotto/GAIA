"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { ProtectedPage } from "@/components/app/protected-page";
import {
  ElaborazioneHero,
  ElaborazioneNoticeCard,
  ElaborazionePanelHeader,
} from "@/components/elaborazioni/module-chrome";
import { ModuleWorkspaceKpiRow, ModuleWorkspaceKpiTile } from "@/components/layout/module-workspace-hero";
import { ElaborazioneOperationMessage } from "@/components/elaborazioni/operation-message";
import { ElaborazioneStatusBadge } from "@/components/elaborazioni/status-badge";
import { ElaborazioneWorkspaceModal } from "@/components/elaborazioni/workspace-modal";
import { EmptyState } from "@/components/ui/empty-state";
import { ChevronRightIcon, FolderIcon, GridIcon, LockIcon, RefreshIcon, SearchIcon, UsersIcon } from "@/components/ui/icons";
import {
  downloadCatastoDocumentBlob,
  downloadElaborazioneRequestArtifactsBlob,
  fetchElaborazioneRequestArtifactPreviewBlob,
  getElaborazioneBatches,
  getElaborazioneBatch,
  getElaborazioneAnprSummary,
  getElaborazioneCaptchaSummary,
  getElaborazioneCredentials,
  getElaborazioneRuntimeMetrics,
  getBonificaSyncStatus,
  listCapacitasInCassSyncJobs,
  listBonificaOristaneseCredentials,
  listCapacitasParticelleSyncJobs,
  listCapacitasCredentials,
  retryFailedElaborazioneBatch,
  startElaborazioneBatch,
} from "@/lib/api";
import {
  getVehicleAutodocSyncStatus,
  queueVehicleAutodocSync,
  type VehicleAutodocSyncJob,
} from "@/features/operazioni/api/client";
import { getStoredAccessToken } from "@/lib/auth";
import { formatDateTime } from "@/lib/presentation";
import type {
  BonificaOristaneseCredential,
  BonificaSyncStatusResponse,
  CapacitasCredential,
  CapacitasInCassSyncJob,
  CapacitasParticelleSyncJob,
  CapacitasParticelleSyncJobResult,
  CatastoDocument,
  ElaborazioneAnprSummary,
  ElaborazioneBatch,
  ElaborazioneBatchDetail,
  ElaborazioneCaptchaSummary,
  ElaborazioneCredentialStatus,
  ElaborazioneRuntimeMetrics,
} from "@/types/api";

const DASHBOARD_REFRESH_INTERVAL_MS = 15000;

const QUICK_ACTIONS = [
  {
    href: "/elaborazioni/bonifica",
    title: "WhiteCompany Sync",
    description: "Avvio e monitor sync WhiteCompany.",
    icon: RefreshIcon,
  },
  {
    href: "/elaborazioni/visure",
    title: "Visure",
    description: "Ingresso unico per visura singola e import batch.",
    icon: SearchIcon,
  },
  {
    href: "/elaborazioni/anpr",
    title: "ANPR batch",
    description: "Storico run e consumo chiamate giornaliere ANPR.",
    icon: UsersIcon,
  },
  {
    href: "/elaborazioni/capacitas",
    title: "Pool operativo dedicato",
    description: "Capacitas e monitor del pool account operativo.",
    icon: UsersIcon,
  },
  {
    href: "/elaborazioni/ade-alignment",
    title: "Allineamento AdE",
    description: "Run comprensorio, monitor e apply fuori dal GIS.",
    icon: GridIcon,
  },
  {
    href: "/elaborazioni/autodoc",
    title: "AUTODOC mezzi",
    description: "Sync massiva dettagli mezzi e accesso rapido al parco mezzi.",
    icon: RefreshIcon,
  },
] as const;

type DashboardModalState = {
  href: string;
  title: string;
  description?: string | null;
};

type DashboardRunningOperation = {
  id: string;
  area: string;
  title: string;
  detail: string;
  startedAt: string | null;
  tone: "default" | "warning" | "success";
  kind: "batch" | "bonifica" | "particelle-sync";
  bonifica?: {
    entity: string;
    records_synced: number | null;
    records_skipped: number | null;
    records_errors: number | null;
    error_detail: string | null;
    last_finished_at: string | null;
  };
  particelleSync?: {
    status: string;
    progress_percent: number | null;
    total_items: number | null;
    processed_items: number | null;
    success_items: number | null;
    skipped_items: number | null;
    failed_items: number | null;
    current_label: string | null;
    aggressive_window: boolean | null;
    throttle_ms: number | null;
  };
  autodocSync?: {
    status: string;
    records_synced: number | null;
    records_skipped: number | null;
    records_errors: number | null;
    finished_at: string | null;
    error_detail: string | null;
    only_with_autodoc_url: boolean;
    force_refresh: boolean;
  };
};

function formatRunRecordEsito(value: string): string {
  if (value === "alive") return "Vivo";
  if (value === "deceased") return "Deceduto";
  if (value === "not_found") return "Non trovato";
  if (value === "cancelled") return "Cancellato";
  if (value === "error") return "Errore";
  if (value === "anpr_id_found") return "idANPR trovato";
  return value;
}

function isParticelleSyncJobResult(value: CapacitasParticelleSyncJob["result_json"]): value is CapacitasParticelleSyncJobResult {
  return value != null && !Array.isArray(value) && typeof value === "object" && "progress_percent" in value;
}

function isInCassJobInFlight(status: string): boolean {
  return status === "pending" || status === "processing" || status === "queued_resume";
}

function triggerDownload(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const anchor = window.document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function renderRequestLabel(request: ElaborazioneBatchDetail["requests"][number]): string {
  if (request.search_mode === "soggetto") {
    const primary = `${request.subject_kind ?? "SOGGETTO"} ${request.subject_id ?? ""}`.trim();
    const suffix = request.request_type ? ` · ${request.request_type}` : "";
    return `${primary}${suffix}`;
  }
  return request.comune ?? "—";
}

function renderRequestReference(request: ElaborazioneBatchDetail["requests"][number]): string {
  if (request.search_mode === "soggetto") {
    return request.intestazione ?? "Ricerca soggetto";
  }
  return `Fg.${request.foglio ?? "-"} Part.${request.particella ?? "-"}${request.subalterno ? ` Sub.${request.subalterno}` : ""}`;
}

function getArtifactActionClassName(disabled = false): string {
  return [
    "inline-flex items-center rounded-full border px-3 py-1.5 text-xs font-semibold transition",
    disabled
      ? "cursor-not-allowed border-gray-200 bg-gray-100 text-gray-400"
      : "border-[#cfe0d5] bg-[#f3f8f4] text-[#1D4E35] hover:border-[#1D4E35] hover:bg-[#e8f2eb]",
  ].join(" ");
}

function isReleasedBatchSummary(batch: ElaborazioneBatch): boolean {
  return batch.status === "cancelled" && batch.current_operation === "Release requested by user" && batch.skipped_items > 0;
}

function formatMetricNumber(value: number | null | undefined, maximumFractionDigits = 0): string {
  if (value == null) return "—";
  return new Intl.NumberFormat("it-IT", { maximumFractionDigits }).format(value);
}

function formatMetricSeconds(seconds: number | null | undefined): string {
  if (seconds == null) return "—";
  if (seconds < 60) return `${formatMetricNumber(seconds, 0)}s`;
  if (seconds < 3600) return `${formatMetricNumber(seconds / 60, 1)} min`;
  return `${formatMetricNumber(seconds / 3600, 1)} h`;
}

function formatMetricMinutes(minutes: number | null | undefined): string {
  if (minutes == null) return "—";
  if (minutes < 60) return `${formatMetricNumber(minutes, 1)} min`;
  return `${formatMetricNumber(minutes / 60, 1)} h`;
}

function formatAutodocStatus(status: string | null | undefined): string {
  switch (status) {
    case "queued":
      return "In coda";
    case "running":
      return "In esecuzione";
    case "completed":
      return "Completato";
    case "failed":
      return "Fallito";
    default:
      return status ?? "Nessun job";
  }
}

export default function ElaborazioniPage() {
  const [batches, setBatches] = useState<ElaborazioneBatch[]>([]);
  const [batchDetails, setBatchDetails] = useState<Record<string, ElaborazioneBatchDetail>>({});
  const [credentialStatus, setCredentialStatus] = useState<ElaborazioneCredentialStatus | null>(null);
  const [captchaSummary, setCaptchaSummary] = useState<ElaborazioneCaptchaSummary | null>(null);
  const [anprSummary, setAnprSummary] = useState<ElaborazioneAnprSummary | null>(null);
  const [expandedAnprRuns, setExpandedAnprRuns] = useState<Record<string, boolean>>({});
  const [runtimeMetrics, setRuntimeMetrics] = useState<ElaborazioneRuntimeMetrics | null>(null);
  const [capacitasCredentials, setCapacitasCredentials] = useState<CapacitasCredential[]>([]);
  const [incassJobs, setIncassJobs] = useState<CapacitasInCassSyncJob[]>([]);
  const [particelleSyncJobs, setParticelleSyncJobs] = useState<CapacitasParticelleSyncJob[]>([]);
  const [bonificaCredentials, setBonificaCredentials] = useState<BonificaOristaneseCredential[]>([]);
  const [bonificaSyncStatus, setBonificaSyncStatus] = useState<BonificaSyncStatusResponse | null>(null);
  const [autodocSyncJob, setAutodocSyncJob] = useState<VehicleAutodocSyncJob | null>(null);
  const [autodocSyncBusy, setAutodocSyncBusy] = useState<"full" | "cached" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [retryBusyId, setRetryBusyId] = useState<string | null>(null);
  const [startBusyId, setStartBusyId] = useState<string | null>(null);
  const [artifactBusyRequestId, setArtifactBusyRequestId] = useState<string | null>(null);
  const [downloadingDocumentId, setDownloadingDocumentId] = useState<string | null>(null);
  const [artifactPreviewUrls, setArtifactPreviewUrls] = useState<Record<string, string>>({});
  const [artifactPreviewLoadingIds, setArtifactPreviewLoadingIds] = useState<Record<string, boolean>>({});
  const [artifactPreviewFailedIds, setArtifactPreviewFailedIds] = useState<Record<string, boolean>>({});
  const [previewModalRequest, setPreviewModalRequest] = useState<{ requestId: string; label: string; reference: string } | null>(null);
  const [modalState, setModalState] = useState<DashboardModalState | null>(null);
  const artifactPreviewUrlsRef = useRef<Record<string, string>>({});

  const loadDashboard = useCallback(async (): Promise<void> => {
    const token = getStoredAccessToken();
    if (!token) return;

    try {
      const [
        credentialsResult,
        batchesResult,
        captchaSummaryResult,
        anprSummaryResult,
        runtimeMetricsResult,
        capacitasResult,
        incassJobsResult,
        particelleSyncResult,
        bonificaResult,
        bonificaSyncResult,
        autodocSyncResult,
      ] = await Promise.all([
        getElaborazioneCredentials(token),
        getElaborazioneBatches(token),
        getElaborazioneCaptchaSummary(token),
        getElaborazioneAnprSummary(token),
        getElaborazioneRuntimeMetrics(token),
        listCapacitasCredentials(token),
        listCapacitasInCassSyncJobs(token),
        listCapacitasParticelleSyncJobs(token),
        listBonificaOristaneseCredentials(token),
        getBonificaSyncStatus(token),
        getVehicleAutodocSyncStatus(),
      ]);
      setCredentialStatus(credentialsResult);
      setBatches(batchesResult.slice(0, 50));
      setBatchDetails((current) => {
        const next: Record<string, ElaborazioneBatchDetail> = {};
        batchesResult.slice(0, 50).forEach((batch) => {
          if (current[batch.id]) {
            next[batch.id] = current[batch.id];
          }
        });
        return next;
      });
      setCaptchaSummary(captchaSummaryResult);
      setAnprSummary(anprSummaryResult);
      setRuntimeMetrics(runtimeMetricsResult);
      setCapacitasCredentials(capacitasResult);
      setIncassJobs(incassJobsResult);
      setParticelleSyncJobs(particelleSyncResult);
      setBonificaCredentials(bonificaResult);
      setBonificaSyncStatus(bonificaSyncResult);
      setAutodocSyncJob(autodocSyncResult);
      setError(null);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Errore caricamento dashboard Elaborazioni");
    }
  }, []);

  useEffect(() => {
    void loadDashboard();
  }, [loadDashboard]);

  useEffect(() => {
    artifactPreviewUrlsRef.current = artifactPreviewUrls;
  }, [artifactPreviewUrls]);

  useEffect(() => {
    return () => {
      Object.values(artifactPreviewUrlsRef.current).forEach((url) => URL.revokeObjectURL(url));
    };
  }, []);

  const batchesForTable = useMemo(() => {
    const isRunning = (status: ElaborazioneBatch["status"]): boolean => status === "pending" || status === "processing";

    return [...batches]
      .sort((left, right) => {
        const runningDelta = Number(isRunning(right.status)) - Number(isRunning(left.status));
        if (runningDelta !== 0) return runningDelta;

        const leftTime = Date.parse(left.created_at);
        const rightTime = Date.parse(right.created_at);
        return rightTime - leftTime;
      })
      .slice(0, 6);
  }, [batches]);

  const hasActivePollingTargets = useMemo(() => {
    const hasActiveBatches = batches.some((batch) => ["pending", "processing"].includes(batch.status));
    const hasActiveParticelleJobs = particelleSyncJobs.some((job) => ["pending", "processing", "queued_resume"].includes(job.status));
    const hasActiveBonificaJobs = Object.values(bonificaSyncStatus?.entities ?? {}).some((item) => item.status === "running");
    const hasActiveAutodocJob = autodocSyncJob?.status === "queued" || autodocSyncJob?.status === "running";
    return hasActiveBatches || hasActiveParticelleJobs || hasActiveBonificaJobs || hasActiveAutodocJob;
  }, [autodocSyncJob?.status, batches, bonificaSyncStatus, particelleSyncJobs]);

  useEffect(() => {
    function handleVisibilityChange(): void {
      if (document.visibilityState === "visible") {
        void loadDashboard();
      }
    }

    document.addEventListener("visibilitychange", handleVisibilityChange);
    const intervalId = hasActivePollingTargets
      ? window.setInterval(() => {
          if (document.visibilityState === "visible") {
            void loadDashboard();
          }
        }, DASHBOARD_REFRESH_INTERVAL_MS)
      : null;

    return () => {
      if (intervalId !== null) {
        window.clearInterval(intervalId);
      }
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [hasActivePollingTargets, loadDashboard]);

  useEffect(() => {
    const token = getStoredAccessToken();
    if (!token || batchesForTable.length === 0) {
      return;
    }

    batchesForTable.forEach((batch) => {
      if (batchDetails[batch.id]) {
        return;
      }
      void getElaborazioneBatch(token, batch.id)
        .then((detail) => {
          setBatchDetails((current) => ({ ...current, [batch.id]: detail }));
        })
        .catch(() => {
          return;
        });
    });
  }, [batchDetails, batchesForTable]);

  useEffect(() => {
    const token = getStoredAccessToken();
    if (!token) {
      return;
    }

    const eligibleRequests = Object.values(batchDetails)
      .flatMap((batch) => batch.requests)
      .filter((request) => request.artifact_dir && request.status === "not_found");
    const eligibleRequestIds = new Set(eligibleRequests.map((request) => request.id));

    setArtifactPreviewUrls((current) => {
      let changed = false;
      const next: Record<string, string> = {};
      Object.entries(current).forEach(([requestId, url]) => {
        if (eligibleRequestIds.has(requestId)) {
          next[requestId] = url;
          return;
        }
        URL.revokeObjectURL(url);
        changed = true;
      });
      return changed ? next : current;
    });
    setArtifactPreviewLoadingIds((current) => {
      const next = Object.fromEntries(Object.entries(current).filter(([requestId]) => eligibleRequestIds.has(requestId)));
      const sameKeys =
        Object.keys(next).length === Object.keys(current).length &&
        Object.keys(next).every((requestId) => current[requestId] === next[requestId]);
      return sameKeys ? current : next;
    });
    setArtifactPreviewFailedIds((current) => {
      const next = Object.fromEntries(Object.entries(current).filter(([requestId]) => eligibleRequestIds.has(requestId)));
      const sameKeys =
        Object.keys(next).length === Object.keys(current).length &&
        Object.keys(next).every((requestId) => current[requestId] === next[requestId]);
      return sameKeys ? current : next;
    });

    eligibleRequests.forEach((request) => {
      if (artifactPreviewUrls[request.id] || artifactPreviewLoadingIds[request.id] || artifactPreviewFailedIds[request.id]) {
        return;
      }

      setArtifactPreviewLoadingIds((current) => ({ ...current, [request.id]: true }));
      void fetchElaborazioneRequestArtifactPreviewBlob(token, request.id)
        .then((blob) => {
          const url = URL.createObjectURL(blob);
          setArtifactPreviewUrls((current) => {
            if (current[request.id]) {
              URL.revokeObjectURL(url);
              return current;
            }
            return { ...current, [request.id]: url };
          });
          setArtifactPreviewFailedIds((current) => {
            if (!current[request.id]) return current;
            const next = { ...current };
            delete next[request.id];
            return next;
          });
        })
        .catch(() => {
          setArtifactPreviewFailedIds((current) => ({ ...current, [request.id]: true }));
        })
        .finally(() => {
          setArtifactPreviewLoadingIds((current) => {
            if (!current[request.id]) return current;
            const next = { ...current };
            delete next[request.id];
            return next;
          });
        });
    });
  }, [artifactPreviewFailedIds, artifactPreviewLoadingIds, artifactPreviewUrls, batchDetails]);

  async function handleRetryBatch(batch: ElaborazioneBatch): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) return;

    setRetryBusyId(batch.id);
    try {
      if (batch.status === "failed" && batch.failed_items > 0) {
        await retryFailedElaborazioneBatch(token, batch.id);
      }
      await startElaborazioneBatch(token, batch.id);
      await loadDashboard();
      setError(null);
    } catch (retryError) {
      setError(retryError instanceof Error ? retryError.message : "Errore riavvio batch");
    } finally {
      setRetryBusyId(null);
    }
  }

  async function handleStartBatch(batch: ElaborazioneBatch): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) return;

    setStartBusyId(batch.id);
    try {
      await startElaborazioneBatch(token, batch.id);
      await loadDashboard();
      setError(null);
    } catch (startError) {
      setError(startError instanceof Error ? startError.message : "Errore riavvio batch");
    } finally {
      setStartBusyId(null);
    }
  }

  async function handleDownloadRequestArtifacts(requestId: string): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) return;

    setArtifactBusyRequestId(requestId);
    try {
      const blob = await downloadElaborazioneRequestArtifactsBlob(token, requestId);
      triggerDownload(blob, `request-${requestId}-artifacts.zip`);
      setError(null);
    } catch (downloadError) {
      setError(downloadError instanceof Error ? downloadError.message : "Errore download artifact richiesta");
    } finally {
      setArtifactBusyRequestId(null);
    }
  }

  async function handleDownloadDocument(documentItem: CatastoDocument): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) return;

    setDownloadingDocumentId(documentItem.id);
    try {
      const blob = await downloadCatastoDocumentBlob(token, documentItem.id);
      triggerDownload(blob, documentItem.filename);
      setError(null);
    } catch (downloadError) {
      setError(downloadError instanceof Error ? downloadError.message : "Errore download PDF");
    } finally {
      setDownloadingDocumentId(null);
    }
  }

  async function handleQueueAutodocSync(mode: "full" | "cached"): Promise<void> {
    setAutodocSyncBusy(mode);
    try {
      const response = await queueVehicleAutodocSync({
        only_with_autodoc_url: true,
        force_refresh: mode === "full",
      });
      setAutodocSyncJob(response.job);
      setError(null);
      await loadDashboard();
    } catch (queueError) {
      setError(queueError instanceof Error ? queueError.message : "Errore avvio sync AUTODOC");
    } finally {
      setAutodocSyncBusy(null);
    }
  }

  function handleOpenPreviewModal(request: ElaborazioneBatchDetail["requests"][number]): void {
    if (!artifactPreviewUrls[request.id]) {
      return;
    }
    setPreviewModalRequest({
      requestId: request.id,
      label: renderRequestLabel(request),
      reference: renderRequestReference(request),
    });
  }

  const activeCapacitasCredentials = capacitasCredentials.filter((credential) => credential.active);
  const capacitasWarningCount = capacitasCredentials.filter((credential) => Boolean(credential.last_error)).length;
  const activeBonificaCredentials = bonificaCredentials.filter((credential) => credential.active);
  const bonificaWarningCount = bonificaCredentials.filter((credential) => Boolean(credential.last_error)).length;
  const activeSisterCredentials = credentialStatus?.credentials.filter((credential) => credential.active) ?? [];
  const latestCapacitasUsage = capacitasCredentials
    .map((credential) => credential.last_used_at)
    .filter((value): value is string => Boolean(value))
    .sort()
    .at(-1);
  const latestBonificaUsage = bonificaCredentials
    .map((credential) => credential.last_used_at)
    .filter((value): value is string => Boolean(value))
    .sort()
    .at(-1);
  const operatingWindowHint = useMemo(() => {
    if (!runtimeMetrics) {
      return "Nessuna finestra operativa configurata";
    }
    const windowConfig = runtimeMetrics.operating_window;
    if (!windowConfig.enabled) {
      return "Sempre attiva";
    }
    const base = `${String(windowConfig.start_hour).padStart(2, "0")}:00-${String(windowConfig.end_hour).padStart(2, "0")}:59 ${windowConfig.timezone}`;
    if (windowConfig.is_within_window || !windowConfig.next_resume_at) {
      return base;
    }
    return `${base} · ripresa ${formatDateTime(windowConfig.next_resume_at)}`;
  }, [runtimeMetrics]);
  const activeBatchCount = batches.filter((batch) => ["pending", "processing"].includes(batch.status)).length;
  const activeParticelleCount = particelleSyncJobs.filter((job) => ["pending", "processing", "queued_resume"].includes(job.status)).length;
  const activeInCassCount = incassJobs.filter((job) => isInCassJobInFlight(job.status)).length;
  const latestInCassJob = incassJobs[0] ?? null;
  const latestInCassResult =
    latestInCassJob?.result_json && !Array.isArray(latestInCassJob.result_json) && typeof latestInCassJob.result_json === "object"
      ? latestInCassJob.result_json
      : null;
  const inCassNoticesSynced =
    latestInCassResult && "notices_synced" in latestInCassResult && typeof latestInCassResult.notices_synced === "number"
      ? latestInCassResult.notices_synced
      : null;
  const inCassProcessedSubjects =
    latestInCassResult && "processed_subjects" in latestInCassResult && typeof latestInCassResult.processed_subjects === "number"
      ? latestInCassResult.processed_subjects
      : null;
  const activeBonificaCount = Object.values(bonificaSyncStatus?.entities ?? {}).filter((item) => item.status === "running").length;
  const activeAutodocCount = autodocSyncJob?.status === "queued" || autodocSyncJob?.status === "running" ? 1 : 0;
  const totalActiveOperations = activeBatchCount + activeParticelleCount + activeInCassCount + activeBonificaCount + activeAutodocCount;
  const latestAnprRun = anprSummary?.recent_runs[0] ?? null;
  const totalAnprRecentCalls = anprSummary?.recent_runs.reduce((total, run) => total + run.calls_used, 0) ?? 0;
  const totalAnprRecentSubjects = anprSummary?.recent_runs.reduce((total, run) => total + run.subjects_processed, 0) ?? 0;
  const totalAnprRecentDeceased = anprSummary?.recent_runs.reduce((total, run) => total + run.deceased_found, 0) ?? 0;
  const totalAnprRecentErrors = anprSummary?.recent_runs.reduce((total, run) => total + run.errors, 0) ?? 0;
  const totalWarnings =
    capacitasWarningCount +
    bonificaWarningCount +
    (credentialStatus?.configured === false ? 1 : 0) +
    ((anprSummary?.calls_today ?? 0) >= (anprSummary?.effective_daily_limit ?? Number.MAX_SAFE_INTEGER) ? 1 : 0);
  const primaryStatusLabel = error
    ? "Errore dati"
    : totalWarnings > 0
      ? "Da verificare"
      : totalActiveOperations > 0
        ? "Operativo"
        : "Stabile";
  const attentionItems = [
    credentialStatus?.configured === false ? "SISTER non configurato." : null,
    capacitasWarningCount > 0 ? `${capacitasWarningCount} account Capacitas con warning.` : null,
    bonificaWarningCount > 0 ? `${bonificaWarningCount} account WhiteCompany con warning.` : null,
    anprSummary && anprSummary.calls_today >= anprSummary.effective_daily_limit
      ? `ANPR ha raggiunto il limite giornaliero di ${anprSummary.effective_daily_limit} chiamate.`
      : null,
    activeInCassCount > 0 ? `${activeInCassCount} job inCass in esecuzione o in coda.` : null,
    totalActiveOperations > 0 ? `${totalActiveOperations} lavorazioni in corso.` : null,
  ].filter((item): item is string => Boolean(item));
  const heroRefreshDescription = hasActivePollingTargets
    ? "Aggiornamento automatico attivo finché esistono batch, sync o job in esecuzione."
    : "Nessun polling continuo: la pagina si aggiorna al ritorno in primo piano.";
  const quickActions = useMemo(
    () =>
      QUICK_ACTIONS.map((action) => {
        if (action.title === "Pool operativo dedicato") {
          return {
            ...action,
            description:
              capacitasCredentials.length > 0
                ? `${activeCapacitasCredentials.length}/${capacitasCredentials.length} account attivi · ${capacitasWarningCount} warning`
                : "Nessun account Capacitas configurato.",
          };
        }
        if (action.title === "WhiteCompany Sync") {
          const runningCount = Object.values(bonificaSyncStatus?.entities ?? {}).filter((item) => item.status === "running").length;
          return {
            ...action,
            description:
              runningCount > 0
                ? `${runningCount} entity in esecuzione · ultimo uso ${latestBonificaUsage ? formatDateTime(latestBonificaUsage) : "assente"}`
                : `Ultimo uso ${latestBonificaUsage ? formatDateTime(latestBonificaUsage) : "assente"}`,
          };
        }
        if (action.title === "Visure") {
          return {
            ...action,
            description: credentialStatus?.configured
              ? `${activeSisterCredentials.length}/${credentialStatus.credentials.length} credenziali attive · singole e batch nello stesso workspace`
              : "Workspace unico per visure singole e import batch.",
          };
        }
        if (action.title === "ANPR batch") {
          return {
            ...action,
            description: anprSummary
              ? `${anprSummary.calls_today}/${anprSummary.effective_daily_limit} chiamate oggi · ultimo stato ${anprSummary.recent_runs[0]?.status ?? "n/d"}`
              : "Storico run e consumo chiamate giornaliere ANPR.",
          };
        }
        if (action.title === "AUTODOC mezzi") {
          return {
            ...action,
            description: autodocSyncJob
              ? `${formatAutodocStatus(autodocSyncJob.status)} · synced ${autodocSyncJob.records_synced ?? 0} · errori ${autodocSyncJob.records_errors ?? 0}`
              : "Sync massiva dettagli mezzi e accesso rapido al parco mezzi.",
          };
        }
        return action;
      }),
    [
      activeCapacitasCredentials.length,
      activeSisterCredentials.length,
      bonificaSyncStatus,
      anprSummary,
      autodocSyncJob,
      capacitasCredentials.length,
      capacitasWarningCount,
      credentialStatus,
      latestBonificaUsage,
    ],
  );
  const runningOperations = useMemo<DashboardRunningOperation[]>(() => {
    const items: DashboardRunningOperation[] = [];

    for (const batch of batches) {
      if (!["pending", "processing"].includes(batch.status)) continue;
      items.push({
        id: `batch-${batch.id}`,
        area: "Batch runtime",
        title: batch.name ?? batch.id,
        detail: batch.current_operation ?? batch.status,
        startedAt: batch.started_at ?? batch.created_at,
        tone: batch.status === "processing" ? "warning" : "default",
        kind: "batch",
      });
    }

    for (const job of particelleSyncJobs) {
      if (!["pending", "processing", "queued_resume"].includes(job.status)) continue;
      const result = isParticelleSyncJobResult(job.result_json) ? job.result_json : null;
      const progress = result?.progress_percent ?? null;
      const currentLabel = result?.current_label ?? null;
      const processedItems = result?.processed_items ?? null;
      const totalItems = result?.total_items ?? null;
      items.push({
        id: `particelle-sync-${job.id}`,
        area: "Capacitas particelle",
        title: `Sync progressiva #${job.id}`,
        detail: currentLabel
          ? `In corso: ${currentLabel}`
          : job.status === "queued_resume"
            ? "Job in ripresa automatica dopo restart backend"
          : job.status === "pending"
            ? "Job in coda per la sync progressiva particelle"
            : "Monitor sync progressiva particelle in esecuzione",
        startedAt: job.started_at ?? job.created_at,
        tone: job.status === "processing" || job.status === "queued_resume" ? "warning" : "default",
        kind: "particelle-sync",
        particelleSync: {
          status: job.status,
          progress_percent: progress,
          total_items: totalItems,
          processed_items: processedItems,
          success_items: result?.success_items ?? null,
          skipped_items: result?.skipped_items ?? null,
          failed_items: result?.failed_items ?? null,
          current_label: currentLabel,
          aggressive_window: result?.aggressive_window ?? null,
          throttle_ms: result?.throttle_ms ?? null,
        },
      });
    }

    for (const [entityKey, entity] of Object.entries(bonificaSyncStatus?.entities ?? {})) {
      if (entity.status !== "running") continue;
      items.push({
        id: `bonifica-${entityKey}`,
        area: "WhiteCompany Sync",
        title: entityKey,
        detail: "Sync entity in esecuzione",
        startedAt: entity.last_started_at,
        tone: "warning",
        kind: "bonifica",
        bonifica: {
          entity: entity.entity,
          records_synced: entity.records_synced,
          records_skipped: entity.records_skipped,
          records_errors: entity.records_errors,
          error_detail: entity.error_detail,
          last_finished_at: entity.last_finished_at,
        },
      });
    }

    if (autodocSyncJob && ["queued", "running"].includes(autodocSyncJob.status)) {
      const params = autodocSyncJob.params_json ?? {};
      items.push({
        id: `autodoc-sync-${autodocSyncJob.job_id}`,
        area: "AUTODOC mezzi",
        title: `Sync massiva #${autodocSyncJob.job_id.slice(0, 8)}`,
        detail:
          autodocSyncJob.status === "queued"
            ? "Job AUTODOC in coda per i mezzi con URL salvato"
            : params.force_refresh
              ? "Refresh forzato dei mezzi con link AUTODOC già noto"
              : "Aggiornamento mezzi con link AUTODOC già noto",
        startedAt: autodocSyncJob.started_at,
        tone: "warning",
        kind: "bonifica",
        bonifica: {
          entity: autodocSyncJob.entity,
          records_synced: autodocSyncJob.records_synced,
          records_skipped: autodocSyncJob.records_skipped,
          records_errors: autodocSyncJob.records_errors,
          error_detail: autodocSyncJob.error_detail,
          last_finished_at: autodocSyncJob.finished_at,
        },
      });
    }

    return items.sort((left, right) => {
      const leftTime = left.startedAt ? Date.parse(left.startedAt) : 0;
      const rightTime = right.startedAt ? Date.parse(right.startedAt) : 0;
      return rightTime - leftTime;
    });
  }, [autodocSyncJob, batches, bonificaSyncStatus, particelleSyncJobs]);

  function openWorkspaceModal(href: string, title: string, description?: string): void {
    setModalState({ href, title, description });
  }

  useEffect(() => {
    const scrollToHashTarget = (): void => {
      if (typeof window === "undefined" || window.location.hash !== "#autodoc-mezzi") return;
      const target = window.document.getElementById("autodoc-mezzi");
      target?.scrollIntoView({ behavior: "smooth", block: "start" });
    };

    scrollToHashTarget();
    window.addEventListener("hashchange", scrollToHashTarget);
    return () => window.removeEventListener("hashchange", scrollToHashTarget);
  }, []);

  const previewModalUrl = previewModalRequest ? artifactPreviewUrls[previewModalRequest.requestId] ?? null : null;

  return (
    <ProtectedPage
      title="GAIA Elaborazioni"
      description="Workspace operativo per batch, richieste singole, CAPTCHA e monitoraggio esecuzioni del runtime catastale."
      breadcrumb="Elaborazioni"
      requiredModule="catasto"
    >
      <ElaborazioneHero
        badge={
          <>
            <LockIcon className="h-3.5 w-3.5" />
            Workspace Elaborazioni
          </>
        }
        title="Console operativa per richieste, batch, credenziali e pool Capacitas."
        description="Qui restano concentrati i flussi runtime: stato credenziali, attività recenti, CAPTCHA e accesso rapido alle azioni più usate."
        actions={
          error ? (
            <ElaborazioneNoticeCard title="Errore dashboard" description={error} tone="danger" />
          ) : (
            <ElaborazioneNoticeCard
              title={hasActivePollingTargets ? "Monitor live attivo" : "Monitor automatico pronto"}
              description={heroRefreshDescription}
            />
          )
        }
      >
        <ModuleWorkspaceKpiRow>
          <ModuleWorkspaceKpiTile
            label="Stato generale"
            variant={error || totalWarnings > 0 ? "amber" : "emerald"}
            value={primaryStatusLabel}
            hint={error ? "Controlla il caricamento della dashboard" : `${totalWarnings} segnalazioni · ${totalActiveOperations} lavorazioni attive`}
          />
          <ModuleWorkspaceKpiTile
            label="SISTER"
            variant="amber"
            value={credentialStatus?.configured ? "Pronto" : "Setup"}
            hint={
              credentialStatus?.configured
                ? `${activeSisterCredentials.length}/${credentialStatus?.credentials.length ?? 0} credenziali attive`
                : "Configura almeno una credenziale"
            }
          />
          <ModuleWorkspaceKpiTile
            label="Sync esterni"
            variant={capacitasWarningCount + bonificaWarningCount > 0 ? "amber" : "emerald"}
            value={`${activeCapacitasCredentials.length + activeBonificaCredentials.length} attivi`}
            hint={`Capacitas ${activeCapacitasCredentials.length}/${capacitasCredentials.length} · White ${activeBonificaCredentials.length}/${bonificaCredentials.length}`}
          />
          <ModuleWorkspaceKpiTile
            label="Lavorazioni attive"
            value={totalActiveOperations}
            hint={`batch ${activeBatchCount} · sync ${activeBonificaCount + activeAutodocCount} · particelle ${activeParticelleCount}`}
          />
        </ModuleWorkspaceKpiRow>
        <div className="mt-4 grid gap-4 xl:grid-cols-[1.35fr,0.65fr]">
          <div className="rounded-[24px] border border-[#d9dfd6] bg-white/85 p-5">
            <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[#1D4E35]">Situazione operativa</p>
            <div className="mt-4 grid gap-3 md:grid-cols-2">
              <div className="rounded-2xl bg-[#f6faf7] px-4 py-3">
                <p className="text-sm font-semibold text-gray-900">Visure ultime 24 ore</p>
                <p className="mt-2 text-2xl font-semibold text-[#163524]">
                  {formatMetricNumber(runtimeMetrics?.last_24_hours.processed_requests ?? null)}
                </p>
                <p className="mt-1 text-sm text-gray-600">
                  {formatMetricNumber(runtimeMetrics?.last_24_hours.requests_completed ?? null)} concluse ·{" "}
                  {formatMetricNumber(runtimeMetrics?.last_24_hours.throughput_per_hour ?? null, 2)} all&apos;ora
                </p>
              </div>
              <div className="rounded-2xl bg-[#f6faf7] px-4 py-3">
                <p className="text-sm font-semibold text-gray-900">Tempo medio di lavorazione</p>
                <p className="mt-2 text-2xl font-semibold text-[#163524]">
                  {formatMetricSeconds(runtimeMetrics?.totals.average_request_duration_seconds ?? null)}
                </p>
                <p className="mt-1 text-sm text-gray-600">
                  batch medi {formatMetricMinutes(runtimeMetrics?.totals.average_batch_duration_minutes ?? null)}
                </p>
              </div>
              <div className="rounded-2xl bg-[#f6faf7] px-4 py-3">
                <p className="text-sm font-semibold text-gray-900">Ultimo elemento processato</p>
                <p className="mt-2 text-base font-semibold text-[#163524]">
                  {runtimeMetrics?.totals.latest_processed_at ? formatDateTime(runtimeMetrics.totals.latest_processed_at) : "Nessun dato"}
                </p>
                <p className="mt-1 text-sm text-gray-600">
                  totali {formatMetricNumber(runtimeMetrics?.totals.processed_requests ?? null)} · fallite{" "}
                  {formatMetricNumber(runtimeMetrics?.totals.requests_failed ?? null)}
                </p>
              </div>
              <div className="rounded-2xl bg-[#f6faf7] px-4 py-3">
                <p className="text-sm font-semibold text-gray-900">ANPR oggi</p>
                <p className="mt-2 text-2xl font-semibold text-[#163524]">
                  {anprSummary ? `${anprSummary.calls_today}/${anprSummary.effective_daily_limit}` : "—"}
                </p>
                <p className="mt-1 text-sm text-gray-600">
                  {anprSummary
                    ? `batch ${anprSummary.batch_size} · ruolo ${anprSummary.ruolo_year ?? "auto"}`
                    : "Monitor chiamate e run giornalieri"}
                </p>
              </div>
            </div>
          </div>
          <div className="space-y-4">
            <div className="rounded-[24px] border border-[#d9dfd6] bg-white/85 p-5">
              <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[#1D4E35]">Da controllare</p>
              {attentionItems.length > 0 ? (
                <div className="mt-4 space-y-2">
                  {attentionItems.slice(0, 4).map((item) => (
                    <div key={item} className="rounded-2xl border border-amber-100 bg-amber-50 px-3 py-2 text-sm text-amber-900">
                      {item}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="mt-4 rounded-2xl border border-emerald-100 bg-emerald-50 px-3 py-3 text-sm text-emerald-900">
                  Nessuna criticità evidente. Le credenziali sono attive e non risultano blocchi operativi.
                </div>
              )}
            </div>
            <div className="rounded-[24px] border border-[#d9dfd6] bg-white/85 p-5">
              <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[#1D4E35]">Monitor rapido</p>
              <div className="mt-4 space-y-3 text-sm text-gray-600">
                <div className="flex items-start justify-between gap-3">
                  <span>Finestra operativa</span>
                  <span className="text-right font-semibold text-gray-900">{runtimeMetrics?.operating_window.state_label ?? "—"}</span>
                </div>
                <p className="text-xs leading-5 text-gray-500">{operatingWindowHint}</p>
                <div className="flex items-start justify-between gap-3">
                  <span>CAPTCHA gestiti</span>
                  <span className="text-right font-semibold text-gray-900">
                    {formatMetricNumber(captchaSummary?.processed ?? null)} totali
                  </span>
                </div>
                <p className="text-xs leading-5 text-gray-500">
                  corretti {formatMetricNumber(captchaSummary?.correct ?? null)} · errati {formatMetricNumber(captchaSummary?.wrong ?? null)}
                </p>
                <div className="flex items-start justify-between gap-3">
                  <span>Ultimo uso pool</span>
                  <span className="text-right font-semibold text-gray-900">
                    {latestCapacitasUsage ? formatDateTime(latestCapacitasUsage) : "Mai"}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div className="mt-4 grid items-start gap-3 lg:grid-cols-[0.95fr,1.05fr]">
          <div
            className={[
              "rounded-2xl border px-4 py-3",
              latestAnprRun?.status === "completed_with_errors" ? "border-amber-200 bg-amber-50 text-amber-900" : "border-gray-100 bg-white/80 text-gray-700",
            ].join(" ")}
          >
            <p className="text-sm font-semibold text-gray-900">Ultimo run ANPR</p>
            {latestAnprRun ? (
              <>
                <p className="mt-2 text-sm leading-5">
                  {formatDateTime(latestAnprRun.started_at)} · {latestAnprRun.status}
                </p>
                <div className="mt-3 grid gap-2 sm:grid-cols-2">
                  <div className="rounded-xl bg-white/60 px-3 py-2">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-gray-500">Questo run</p>
                    <p className="mt-1 text-sm font-semibold text-gray-900">{formatMetricNumber(latestAnprRun.calls_used)} chiamate</p>
                  </div>
                  <div className="rounded-xl bg-white/60 px-3 py-2">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-gray-500">Soggetti recenti</p>
                    <p className="mt-1 text-sm font-semibold text-gray-900">{formatMetricNumber(totalAnprRecentSubjects)}</p>
                  </div>
                  <div className="rounded-xl bg-white/60 px-3 py-2">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-gray-500">Call recenti</p>
                    <p className="mt-1 text-sm font-semibold text-gray-900">{formatMetricNumber(totalAnprRecentCalls)}</p>
                  </div>
                  <div className="rounded-xl bg-white/60 px-3 py-2">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-gray-500">Errori recenti</p>
                    <p className="mt-1 text-sm font-semibold text-gray-900">{formatMetricNumber(totalAnprRecentErrors)}</p>
                  </div>
                </div>
              </>
            ) : (
              <p className="mt-2 text-sm text-gray-500">Nessuna esecuzione ANPR registrata.</p>
            )}
          </div>
          <div className="rounded-2xl border border-gray-100 bg-white/80 px-4 py-3">
            <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-gray-500">Storico ANPR recente</p>
            {anprSummary?.recent_runs.length ? (
              <p className="mt-2 text-xs text-gray-500">
                Totali: {formatMetricNumber(totalAnprRecentCalls)} call · {formatMetricNumber(totalAnprRecentSubjects)} soggetti ·{" "}
                {formatMetricNumber(totalAnprRecentDeceased)} deceduti · {formatMetricNumber(totalAnprRecentErrors)} errori
              </p>
            ) : null}
            {anprSummary?.recent_runs.length ? (
              <div className="mt-3 space-y-1.5">
                {anprSummary.recent_runs.slice(0, 3).map((run) => {
                  const isExpanded = Boolean(expandedAnprRuns[run.id]);
                  const latestErrors = run.records
                    .filter((record) => record.final_esito === "error" || Boolean(record.error_detail))
                    .slice(0, 5);

                  return (
                    <div key={run.id} className="rounded-xl border border-gray-100 bg-gray-50">
                      <button
                        type="button"
                        className="flex w-full items-center justify-between gap-3 px-3 py-2 text-left text-xs text-gray-600"
                        onClick={() => setExpandedAnprRuns((current) => ({ ...current, [run.id]: !current[run.id] }))}
                        aria-expanded={isExpanded}
                        aria-controls={`anpr-run-${run.id}`}
                      >
                        <span className="inline-flex items-center gap-2 truncate">
                          <span className="inline-flex h-6 w-6 items-center justify-center rounded-full border border-[#d9dfd6] bg-white text-gray-500">
                            <ChevronRightIcon className={["h-3.5 w-3.5 transition-transform", isExpanded ? "rotate-90" : ""].join(" ")} />
                          </span>
                          <span className="truncate">{formatDateTime(run.started_at)}</span>
                        </span>
                        <span className="shrink-0">{run.calls_used} call</span>
                        <span className="shrink-0 font-medium text-gray-800">{run.status}</span>
                      </button>
                      {isExpanded ? (
                        <div id={`anpr-run-${run.id}`} className="border-t border-gray-100 bg-white px-3 py-3">
                          {latestErrors.length ? (
                            <div className="space-y-2">
                              {latestErrors.map((record) => (
                                <div key={record.id} className="rounded-lg border border-red-100 bg-red-50/60 px-3 py-2">
                                  <div className="flex items-start justify-between gap-3">
                                    <div className="min-w-0">
                                      <p className="truncate text-xs font-semibold text-gray-900">{record.display_name}</p>
                                      <p className="mt-0.5 font-mono text-[11px] text-gray-500">{record.codice_fiscale}</p>
                                    </div>
                                    <span className="shrink-0 rounded-full bg-white px-2 py-1 text-[10px] font-semibold text-red-700">
                                      {formatRunRecordEsito(record.final_esito)}
                                    </span>
                                  </div>
                                  <p className="mt-2 text-[11px] leading-5 text-gray-700">{record.error_detail || "Errore senza dettaglio disponibile."}</p>
                                  <p className="mt-1 text-[10px] uppercase tracking-[0.16em] text-gray-400">
                                    {formatDateTime(record.last_event_at)} · {record.calls_made} call
                                  </p>
                                </div>
                              ))}
                            </div>
                          ) : (
                            <p className="text-[11px] text-gray-500">Nessun errore registrato in questo run.</p>
                          )}
                        </div>
                      ) : null}
                    </div>
                  );
                })}
              </div>
            ) : (
              <p className="mt-3 text-xs text-gray-500">Nessun run registrato.</p>
            )}
          </div>
        </div>
      </ElaborazioneHero>

      <article className="overflow-hidden rounded-[28px] border border-[#d9dfd6] bg-white shadow-panel">
        <ElaborazionePanelHeader
          badge={
            <>
              <UsersIcon className="h-3.5 w-3.5" />
              inCass ruolo
            </>
          }
          title="Harvest massivo avvisi e partitario"
          description="Accesso rapido alla coda inCass costruita dai soggetti a ruolo, con focus sui job batch per completare i casi troncati nel dump."
        />
        <div className="grid gap-6 p-6 lg:grid-cols-[1.1fr,0.9fr]">
          <div className="space-y-4">
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              <div className="rounded-2xl border border-gray-100 bg-gray-50 px-4 py-3">
                <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-gray-500">Job attivi</p>
                <p className="mt-2 text-2xl font-semibold text-[#163524]">{formatMetricNumber(activeInCassCount)}</p>
                <p className="mt-1 text-xs text-gray-500">pending, processing o resume pianificato</p>
              </div>
              <div className="rounded-2xl border border-gray-100 bg-gray-50 px-4 py-3">
                <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-gray-500">Ultimo stato</p>
                <p className="mt-2 text-sm font-semibold text-gray-900">{latestInCassJob?.status ?? "Nessun job"}</p>
                <p className="mt-1 text-xs text-gray-500">
                  {latestInCassJob?.created_at ? `Creato ${formatDateTime(latestInCassJob.created_at)}` : "Nessun batch registrato"}
                </p>
              </div>
              <div className="rounded-2xl border border-gray-100 bg-gray-50 px-4 py-3">
                <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-gray-500">Soggetti processati</p>
                <p className="mt-2 text-sm font-semibold text-emerald-700">{formatMetricNumber(inCassProcessedSubjects)}</p>
                <p className="mt-1 text-xs text-gray-500">ultimo job con risultato persistito</p>
              </div>
              <div className="rounded-2xl border border-gray-100 bg-gray-50 px-4 py-3">
                <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-gray-500">Avvisi sincronizzati</p>
                <p className="mt-2 text-sm font-semibold text-[#1D4E35]">{formatMetricNumber(inCassNoticesSynced)}</p>
                <p className="mt-1 text-xs text-gray-500">ultimo job con dettaglio notice/partitario</p>
              </div>
            </div>
            {latestInCassJob?.error_detail ? (
              <div className="rounded-2xl border border-amber-100 bg-amber-50 px-4 py-3">
                <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-amber-700">Ultimo errore inCass</p>
                <p className="mt-2 break-words text-sm text-amber-900">{latestInCassJob.error_detail}</p>
              </div>
            ) : (
              <div className="rounded-2xl border border-gray-100 bg-[#f7faf8] px-4 py-3 text-sm text-gray-600">
                La sezione `Avvisi pagamenti` ora gestisce sia il sync puntuale sia l&apos;harvest massivo da soggetti `a ruolo`, con chunk configurabili e monitor unico.
              </div>
            )}
          </div>
          <div className="rounded-[24px] border border-[#d9dfd6] bg-[#f7faf8] p-5">
            <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[#1D4E35]">Azioni inCass</p>
            <h3 className="mt-2 text-lg font-semibold text-gray-900">Apri il monitor batch ruolo</h3>
            <p className="mt-2 text-sm leading-6 text-gray-600">
              Usa la workspace `Capacitas` già posizionata sulla scheda `Avvisi pagamenti` per creare job da `ruolo`, escludere i soggetti già sincronizzati e seguire l&apos;avanzamento del partitario completo.
            </p>
            <div className="mt-5 flex flex-wrap gap-3">
              <button
                className="btn-primary"
                onClick={() =>
                  openWorkspaceModal(
                    "/elaborazioni/capacitas?section=incass",
                    "Capacitas · Avvisi pagamenti",
                    "Apre direttamente la sezione inCass con monitor job e harvest massivo da ruolo.",
                  )
                }
                type="button"
              >
                Apri monitor inCass
              </button>
            </div>
            <div className="mt-5 space-y-2 text-xs text-gray-500">
              <p>Ultimo job id: {latestInCassJob?.id ?? "nessuno"}</p>
              <p>Credenziali Capacitas attive: {activeCapacitasCredentials.length}</p>
              <p>Ultimo uso pool: {latestCapacitasUsage ? formatDateTime(latestCapacitasUsage) : "Mai"}</p>
            </div>
          </div>
        </div>
      </article>

      <article id="autodoc-mezzi" className="overflow-hidden rounded-[28px] border border-[#d9dfd6] bg-white shadow-panel">
        <ElaborazionePanelHeader
          badge={
            <>
              <RefreshIcon className="h-3.5 w-3.5" />
              AUTODOC mezzi
            </>
          }
          title="Sync massiva dei dettagli AUTODOC"
          description="Da qui puoi lanciare il job backend che aggiorna il parco mezzi usando AUTODOC e monitorare l'ultimo esito senza restare nel modulo Operazioni."
        />
        <div className="grid gap-6 p-6 lg:grid-cols-[1.15fr,0.85fr]">
          <div className="space-y-4">
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              <div className="rounded-2xl border border-gray-100 bg-gray-50 px-4 py-3">
                <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-gray-500">Ultimo stato</p>
                <p className="mt-2 text-sm font-semibold text-gray-900">{formatAutodocStatus(autodocSyncJob?.status)}</p>
                <p className="mt-1 text-xs text-gray-500">
                  {autodocSyncJob?.started_at ? `Avvio ${formatDateTime(autodocSyncJob.started_at)}` : "Nessun job registrato"}
                </p>
              </div>
              <div className="rounded-2xl border border-gray-100 bg-gray-50 px-4 py-3">
                <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-gray-500">Record sincronizzati</p>
                <p className="mt-2 text-sm font-semibold text-emerald-700">{formatMetricNumber(autodocSyncJob?.records_synced ?? null)}</p>
                <p className="mt-1 text-xs text-gray-500">Skippati {formatMetricNumber(autodocSyncJob?.records_skipped ?? null)}</p>
              </div>
              <div className="rounded-2xl border border-gray-100 bg-gray-50 px-4 py-3">
                <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-gray-500">Errori</p>
                <p className="mt-2 text-sm font-semibold text-red-700">{formatMetricNumber(autodocSyncJob?.records_errors ?? null)}</p>
                <p className="mt-1 text-xs text-gray-500">
                  {autodocSyncJob?.finished_at ? `Fine ${formatDateTime(autodocSyncJob.finished_at)}` : "Job non concluso"}
                </p>
              </div>
              <div className="rounded-2xl border border-gray-100 bg-gray-50 px-4 py-3">
                <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-gray-500">Modalità</p>
                <p className="mt-2 text-sm font-semibold text-gray-900">
                  {autodocSyncJob?.params_json?.force_refresh ? "Refresh URL salvati" : "Solo non sincronizzati"}
                </p>
                <p className="mt-1 text-xs text-gray-500">
                  La sync massiva aggiorna solo i mezzi che hanno già un link AUTODOC salvato.
                </p>
              </div>
            </div>
            {autodocSyncJob?.error_detail ? (
              <div className="rounded-2xl border border-amber-100 bg-amber-50 px-4 py-3">
                <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-amber-700">Ultimo errore</p>
                <p className="mt-2 break-words text-sm text-amber-900">{autodocSyncJob.error_detail}</p>
              </div>
            ) : (
              <div className="rounded-2xl border border-gray-100 bg-[#f7faf8] px-4 py-3 text-sm text-gray-600">
                Il job AUTODOC usa il worker backend. Se una sync è già in coda o in esecuzione, il backend restituisce il job aperto invece di crearne uno nuovo.
              </div>
            )}
          </div>
          <div className="rounded-[24px] border border-[#d9dfd6] bg-[#f7faf8] p-5">
            <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[#1D4E35]">Azioni AUTODOC</p>
            <h3 className="mt-2 text-lg font-semibold text-gray-900">Avvio e monitoraggio run</h3>
            <p className="mt-2 text-sm leading-6 text-gray-600">
              La sync massiva AUTODOC aggiorna i mezzi che hanno già un link AUTODOC salvato. Il refresh forzato rilegge tutte le schede note; la modalità veloce salta quelle già sincronizzate.
            </p>
            <div className="mt-5 flex flex-wrap gap-3">
              <button
                className="btn-primary"
                disabled={autodocSyncBusy != null}
                onClick={() => void handleQueueAutodocSync("full")}
                type="button"
              >
                {autodocSyncBusy === "full" ? "Avvio refresh..." : "Refresh URL salvati"}
              </button>
              <button
                className="btn-secondary"
                disabled={autodocSyncBusy != null}
                onClick={() => void handleQueueAutodocSync("cached")}
                type="button"
              >
                {autodocSyncBusy === "cached" ? "Avvio sync..." : "Solo non sincronizzati"}
              </button>
              <button
                className="btn-secondary"
                onClick={() => openWorkspaceModal("/operazioni/mezzi", "Parco mezzi", "Apre il modulo Operazioni per consultare mezzi, schede e sync puntuali AUTODOC.")}
                type="button"
              >
                Apri parco mezzi
              </button>
            </div>
            <div className="mt-5 space-y-2 text-xs text-gray-500">
              <p>Job id: {autodocSyncJob?.job_id ?? "nessun job"}</p>
              <p>Entity worker: {autodocSyncJob?.entity ?? "autodoc_vehicle_details"}</p>
            </div>
          </div>
        </div>
      </article>

      <article className="overflow-hidden rounded-[28px] border border-[#d9dfd6] bg-white shadow-panel">
        <ElaborazionePanelHeader
          badge={
            <>
              <RefreshIcon className="h-3.5 w-3.5" />
              Azioni rapide
            </>
          }
          title="Flussi principali del runtime"
          description="Accessi diretti ai percorsi operativi più usati. La barra resta orizzontale per mantenere leggibile la mappa del modulo."
        />
        <div className="p-6">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {quickActions.map((action) => {
              const Icon = action.icon;
              return (
                <button
                  key={action.href}
                  className="group rounded-2xl border border-gray-100 bg-gray-50 px-4 py-3 text-left transition hover:border-[#c8d8ce] hover:bg-white"
                  onClick={() => openWorkspaceModal(action.href, action.title, action.description)}
                  type="button"
                >
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-white text-[#1D4E35] shadow-sm ring-1 ring-[#dfe8e2] transition group-hover:bg-[#edf5f0]">
                      <Icon className="h-4.5 w-4.5" />
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-gray-900">{action.title}</p>
                      <p className="mt-0.5 line-clamp-2 text-xs leading-5 text-gray-500">{action.description}</p>
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      </article>

      <article className="overflow-hidden rounded-[28px] border border-[#d9dfd6] bg-white shadow-panel">
        <ElaborazionePanelHeader
          badge={
            <>
              <RefreshIcon className="h-3.5 w-3.5" />
              Operazioni in corso
            </>
          }
          title="Esecuzioni attive aggregate"
          description="Vista unica delle operazioni attualmente in lavorazione: batch runtime, sync WhiteCompany e sync progressiva particelle ancora aperte."
        />
        <div className="p-6">
          {runningOperations.length === 0 ? (
            <EmptyState icon={RefreshIcon} title="Nessuna operazione attiva" description="Al momento non risultano batch, sync WhiteCompany o job particelle in esecuzione." />
          ) : (
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              {runningOperations.map((operation) => (
                <article
                  key={operation.id}
                  className="flex h-full flex-col justify-between gap-4 rounded-3xl border border-gray-100 bg-gray-50 p-4"
                >
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-gray-400">{operation.area}</p>
                        <p className="mt-1 truncate text-sm font-medium text-gray-900">{operation.title}</p>
                      </div>
                      <span
                        className={`inline-flex shrink-0 rounded-full px-2 py-1 text-[11px] font-semibold ${
                          operation.tone === "warning"
                            ? "bg-amber-50 text-amber-700"
                            : operation.tone === "success"
                              ? "bg-emerald-50 text-emerald-700"
                              : "bg-gray-100 text-gray-700"
                        }`}
                      >
                        attiva
                      </span>
                    </div>

                    <p className="mt-2 line-clamp-2 text-sm text-gray-600">{operation.detail}</p>
                    <p className="mt-2 text-xs text-gray-500">Avvio: {formatDateTime(operation.startedAt)}</p>

                    {operation.kind === "bonifica" && operation.bonifica ? (
                      <div className="mt-4 grid gap-2 text-xs text-gray-600 sm:grid-cols-2">
                        <div className="rounded-2xl bg-white px-3 py-2 ring-1 ring-gray-100">
                          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-gray-400">Synced</p>
                          <p className="mt-1 text-sm font-semibold text-emerald-700">{operation.bonifica.records_synced ?? "—"}</p>
                        </div>
                        <div className="rounded-2xl bg-white px-3 py-2 ring-1 ring-gray-100">
                          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-gray-400">Errors</p>
                          <p className="mt-1 text-sm font-semibold text-red-700">{operation.bonifica.records_errors ?? "—"}</p>
                        </div>
                        <div className="rounded-2xl bg-white px-3 py-2 ring-1 ring-gray-100">
                          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-gray-400">Skipped</p>
                          <p className="mt-1 text-sm font-semibold text-slate-700">{operation.bonifica.records_skipped ?? "—"}</p>
                        </div>
                        <div className="rounded-2xl bg-white px-3 py-2 ring-1 ring-gray-100">
                          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-gray-400">Ultimo fine</p>
                          <p className="mt-1 text-sm font-semibold text-gray-900">
                            {operation.bonifica.last_finished_at ? formatDateTime(operation.bonifica.last_finished_at) : "—"}
                          </p>
                        </div>
                        {operation.bonifica.error_detail ? (
                          <div className="sm:col-span-2">
                            <div className="rounded-2xl border border-amber-100 bg-amber-50 px-3 py-2">
                              <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-amber-700">Errore</p>
                              <p className="mt-1 break-words text-sm text-amber-900">{operation.bonifica.error_detail}</p>
                            </div>
                          </div>
                        ) : null}
                      </div>
                    ) : null}

                    {operation.kind === "particelle-sync" && operation.particelleSync ? (
                      <div className="mt-4 space-y-3">
                        <div className="flex items-center justify-between gap-3">
                          <div>
                            <p className="text-sm font-medium text-gray-900">
                              {operation.particelleSync.processed_items ?? "—"} / {operation.particelleSync.total_items ?? "—"} particelle
                            </p>
                            <p className="mt-1 text-xs text-gray-500">
                              ok {operation.particelleSync.success_items ?? "—"} · skipped {operation.particelleSync.skipped_items ?? "—"} · failed{" "}
                              {operation.particelleSync.failed_items ?? "—"}
                            </p>
                          </div>
                          <span className="rounded-full bg-white px-3 py-1 text-sm font-semibold text-[#1D4E35] shadow-sm">
                            {operation.particelleSync.progress_percent != null ? `${operation.particelleSync.progress_percent}%` : operation.particelleSync.status}
                          </span>
                        </div>
                        {operation.particelleSync.progress_percent != null ? (
                          <div className="h-3 overflow-hidden rounded-full bg-[#dfe9df]">
                            <div
                              className="h-full rounded-full bg-[#1D4E35] transition-all duration-500"
                              style={{ width: `${operation.particelleSync.progress_percent}%` }}
                            />
                          </div>
                        ) : null}
                        <div className="grid gap-2 text-xs text-gray-600 sm:grid-cols-2">
                          <div className="rounded-2xl bg-white px-3 py-2 ring-1 ring-gray-100">
                            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-gray-400">Finestra</p>
                            <p className="mt-1 text-sm font-semibold text-gray-900">
                              {operation.particelleSync.aggressive_window == null
                                ? "—"
                                : operation.particelleSync.aggressive_window
                                  ? "Serale aggressiva"
                                  : "Diurna conservativa"}
                            </p>
                          </div>
                          <div className="rounded-2xl bg-white px-3 py-2 ring-1 ring-gray-100">
                            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-gray-400">Pausa</p>
                            <p className="mt-1 text-sm font-semibold text-gray-900">
                              {operation.particelleSync.throttle_ms != null ? `${operation.particelleSync.throttle_ms} ms` : "—"}
                            </p>
                          </div>
                        </div>
                      </div>
                    ) : null}
                  </div>
                </article>
              ))}
            </div>
          )}
        </div>
      </article>

      <article className="overflow-hidden rounded-[28px] border border-[#d9dfd6] bg-white p-0 shadow-panel">
        <ElaborazionePanelHeader
          badge={
            <>
              <FolderIcon className="h-3.5 w-3.5" />
              Batch recenti
            </>
          }
          title="Ultimi lotti creati dall'utente corrente"
          description="Da qui puoi aprire il dettaglio batch oppure usare direttamente azioni rapide di preview, artifact e download risultato quando il lotto le rende disponibili."
        />
        {batches.length === 0 ? (
          <div className="p-5">
            <EmptyState icon={SearchIcon} title="Nessun batch presente" description="Apri /elaborazioni/new-batch per creare una richiesta o importare un lotto." />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Nome</th>
                  <th>Stato</th>
                  <th>Totale</th>
                  <th>Esito</th>
                  <th>Operazione</th>
                  <th>Creato</th>
                  <th>Azioni</th>
                </tr>
              </thead>
              <tbody>
                {batchesForTable.map((batch) => (
                  <tr key={batch.id}>
                    <td className="font-medium text-gray-900">{batch.name ?? batch.id}</td>
                    <td><ElaborazioneStatusBadge status={batch.status} /></td>
                    <td>{batch.total_items}</td>
                    <td>
                      <div className="flex flex-wrap gap-2 text-xs text-gray-600">
                        <span>ok {batch.completed_items}</span>
                        <span>ko {batch.failed_items}</span>
                        {batch.not_found_items > 0 ? <span>n.d. {batch.not_found_items}</span> : null}
                        {batch.skipped_items > 0 ? <span>skip {batch.skipped_items}</span> : null}
                      </div>
                    </td>
                    <td><ElaborazioneOperationMessage value={batch.current_operation} /></td>
                    <td>{formatDateTime(batch.created_at)}</td>
                    <td>
                      <div className="flex flex-wrap items-center gap-3">
                        <button
                          className={getArtifactActionClassName()}
                          onClick={() =>
                            openWorkspaceModal(
                              `/elaborazioni/batches/${batch.id}`,
                              batch.name ?? "Dettaglio batch",
                              "Dettaglio batch aperto in modale per consultare stato, richieste e CAPTCHA senza lasciare la dashboard.",
                            )
                          }
                          type="button"
                        >
                          Apri
                        </button>
                        {isReleasedBatchSummary(batch) ? (
                          <button
                            className={getArtifactActionClassName(startBusyId === batch.id)}
                            disabled={startBusyId === batch.id}
                            onClick={() => void handleStartBatch(batch)}
                            type="button"
                          >
                            {startBusyId === batch.id ? "Ripresa..." : "Riprendi"}
                          </button>
                        ) : null}
                        {batch.current_operation === "Retry queued" || (batch.status === "failed" && batch.failed_items > 0) ? (
                          <button
                            className={getArtifactActionClassName(retryBusyId === batch.id)}
                            disabled={retryBusyId === batch.id}
                            onClick={() => void handleRetryBatch(batch)}
                            type="button"
                          >
                            {retryBusyId === batch.id ? "Riprovo..." : "Riprova"}
                          </button>
                        ) : null}
                        {(() => {
                          const detail = batchDetails[batch.id];
                          if (!detail || detail.requests.length !== 1) {
                            return null;
                          }
                          const request = detail.requests[0];
                          const downloadPdfItem: CatastoDocument = {
                            id: request.document_id ?? "",
                            user_id: 0,
                            request_id: request.id,
                            batch_id: batch.id,
                            search_mode: request.search_mode,
                            comune: request.comune,
                            foglio: request.foglio,
                            particella: request.particella,
                            subalterno: request.subalterno,
                            catasto: request.catasto,
                            tipo_visura: request.tipo_visura,
                            subject_kind: request.subject_kind,
                            subject_id: request.subject_id,
                            request_type: request.request_type,
                            intestazione: request.intestazione,
                            filename: `${batch.name ?? batch.id}.pdf`,
                            file_size: null,
                            codice_fiscale: null,
                            created_at: batch.created_at,
                          };
                          return (
                            <>
                              {request.artifact_dir ? (
                                <button
                                  className={getArtifactActionClassName(artifactBusyRequestId === request.id)}
                                  disabled={artifactBusyRequestId === request.id}
                                  onClick={() => void handleDownloadRequestArtifacts(request.id)}
                                  type="button"
                                >
                                  {artifactBusyRequestId === request.id ? "Download artifact..." : "Scarica artifact"}
                                </button>
                              ) : null}
                              {artifactPreviewLoadingIds[request.id] ? <span className="text-[11px] text-gray-400">Caricamento preview...</span> : null}
                              {artifactPreviewUrls[request.id] ? (
                                <button
                                  className={getArtifactActionClassName()}
                                  onClick={() => handleOpenPreviewModal(request)}
                                  type="button"
                                >
                                  Preview screen
                                </button>
                              ) : null}
                              {request.document_id ? (
                                <button
                                  className={getArtifactActionClassName(downloadingDocumentId === request.document_id)}
                                  disabled={downloadingDocumentId === request.document_id}
                                  onClick={() => void handleDownloadDocument(downloadPdfItem)}
                                  type="button"
                                >
                                  {downloadingDocumentId === request.document_id ? "Download PDF..." : "Scarica PDF"}
                                </button>
                              ) : null}
                            </>
                          );
                        })()}
                        {!(batch.current_operation === "Retry queued" || (batch.status === "failed" && batch.failed_items > 0)) &&
                        !batchDetails[batch.id] ? (
                          "—"
                        ) : null}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </article>
      <ElaborazioneWorkspaceModal
        description={modalState?.description}
        href={modalState?.href ?? null}
        onClose={() => setModalState(null)}
        open={modalState != null}
        title={modalState?.title ?? "Workspace"}
      />
      {previewModalRequest && previewModalUrl ? (
        <div className="fixed inset-0 z-[80] flex items-center justify-center bg-black/45 px-4 py-6 backdrop-blur-sm">
          <div className="flex max-h-[92vh] w-full max-w-5xl flex-col overflow-hidden rounded-[28px] border border-gray-200 bg-white shadow-[0_30px_90px_rgba(15,23,42,0.24)]">
            <div className="flex items-center justify-between gap-4 border-b border-gray-100 px-6 py-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#1D4E35]">Preview screen</p>
                <h2 className="mt-1 text-lg font-semibold text-gray-900">{previewModalRequest.label}</h2>
                <p className="mt-1 text-sm text-gray-500">{previewModalRequest.reference}</p>
              </div>
              <button className="btn-secondary" onClick={() => setPreviewModalRequest(null)} type="button">
                Chiudi
              </button>
            </div>
            <div className="overflow-auto bg-[#f4f7f5] p-5">
              <div className="overflow-hidden rounded-2xl border border-[#d9dfd6] bg-white p-3">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  alt={`Preview artifact richiesta ${previewModalRequest.requestId}`}
                  className="h-auto w-full rounded-xl border border-[#d9dfd6] object-contain"
                  src={previewModalUrl}
                />
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </ProtectedPage>
  );
}
