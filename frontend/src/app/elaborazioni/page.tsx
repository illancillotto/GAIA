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
import { FolderIcon, GridIcon, LockIcon, RefreshIcon, SearchIcon, UsersIcon } from "@/components/ui/icons";
import {
  downloadCatastoDocumentBlob,
  downloadElaborazioneRequestArtifactsBlob,
  fetchElaborazioneRequestArtifactPreviewBlob,
  getElaborazioneBatches,
  getElaborazioneBatch,
  getElaborazioneAnprSummary,
  getElaborazioneCaptchaSummary,
  getElaborazioneCredentials,
  getBonificaSyncStatus,
  listBonificaOristaneseCredentials,
  listCapacitasParticelleSyncJobs,
  listCapacitasCredentials,
  retryFailedElaborazioneBatch,
  startElaborazioneBatch,
} from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import { formatDateTime } from "@/lib/presentation";
import type {
  BonificaOristaneseCredential,
  BonificaSyncStatusResponse,
  CapacitasCredential,
  CapacitasParticelleSyncJob,
  CapacitasParticelleSyncJobResult,
  CatastoDocument,
  ElaborazioneAnprSummary,
  ElaborazioneBatch,
  ElaborazioneBatchDetail,
  ElaborazioneCaptchaSummary,
  ElaborazioneCredentialStatus,
} from "@/types/api";

const DASHBOARD_REFRESH_INTERVAL_MS = 5000;

const QUICK_ACTIONS = [
  {
    href: "/elaborazioni/bonifica",
    title: "WhiteCompany Sync",
    description: "Avvio e monitor sync WhiteCompany.",
    icon: RefreshIcon,
  },
  {
    href: "/elaborazioni/new-single",
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
};

function isParticelleSyncJobResult(value: CapacitasParticelleSyncJob["result_json"]): value is CapacitasParticelleSyncJobResult {
  return value != null && !Array.isArray(value) && typeof value === "object" && "progress_percent" in value;
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

export default function ElaborazioniPage() {
  const [batches, setBatches] = useState<ElaborazioneBatch[]>([]);
  const [batchDetails, setBatchDetails] = useState<Record<string, ElaborazioneBatchDetail>>({});
  const [credentialStatus, setCredentialStatus] = useState<ElaborazioneCredentialStatus | null>(null);
  const [captchaSummary, setCaptchaSummary] = useState<ElaborazioneCaptchaSummary | null>(null);
  const [anprSummary, setAnprSummary] = useState<ElaborazioneAnprSummary | null>(null);
  const [capacitasCredentials, setCapacitasCredentials] = useState<CapacitasCredential[]>([]);
  const [particelleSyncJobs, setParticelleSyncJobs] = useState<CapacitasParticelleSyncJob[]>([]);
  const [bonificaCredentials, setBonificaCredentials] = useState<BonificaOristaneseCredential[]>([]);
  const [bonificaSyncStatus, setBonificaSyncStatus] = useState<BonificaSyncStatusResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [retryBusyId, setRetryBusyId] = useState<string | null>(null);
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
        capacitasResult,
        particelleSyncResult,
        bonificaResult,
        bonificaSyncResult,
      ] = await Promise.all([
        getElaborazioneCredentials(token),
        getElaborazioneBatches(token),
        getElaborazioneCaptchaSummary(token),
        getElaborazioneAnprSummary(token),
        listCapacitasCredentials(token),
        listCapacitasParticelleSyncJobs(token),
        listBonificaOristaneseCredentials(token),
        getBonificaSyncStatus(token),
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
      setCapacitasCredentials(capacitasResult);
      setParticelleSyncJobs(particelleSyncResult);
      setBonificaCredentials(bonificaResult);
      setBonificaSyncStatus(bonificaSyncResult);
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

  useEffect(() => {
    function handleVisibilityChange(): void {
      if (document.visibilityState === "visible") {
        void loadDashboard();
      }
    }

    const intervalId = window.setInterval(() => {
      if (document.visibilityState === "visible") {
        void loadDashboard();
      }
    }, DASHBOARD_REFRESH_INTERVAL_MS);

    document.addEventListener("visibilitychange", handleVisibilityChange);

    return () => {
      window.clearInterval(intervalId);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [loadDashboard]);

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
        return action;
      }),
    [
      activeCapacitasCredentials.length,
      activeSisterCredentials.length,
      bonificaSyncStatus,
      anprSummary,
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

    return items.sort((left, right) => {
      const leftTime = left.startedAt ? Date.parse(left.startedAt) : 0;
      const rightTime = right.startedAt ? Date.parse(right.startedAt) : 0;
      return rightTime - leftTime;
    });
  }, [batches, bonificaSyncStatus, particelleSyncJobs]);

  function openWorkspaceModal(href: string, title: string, description?: string): void {
    setModalState({ href, title, description });
  }

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
              title="Refresh automatico attivo"
              description="Quando la pagina è in primo piano, i dati vengono ricaricati periodicamente per tenere allineati batch, pool e richieste CAPTCHA."
            />
          )
        }
      >
        <ModuleWorkspaceKpiRow>
          <ModuleWorkspaceKpiTile
            label="SISTER"
            variant="emerald"
            value={credentialStatus?.configured ? "Attivo" : "Setup"}
            hint={
              credentialStatus?.configured
                ? `${activeSisterCredentials.length}/${credentialStatus?.credentials.length ?? 0} attive · ${credentialStatus?.default_credential?.label ?? "default"}`
                : "non configurato"
            }
          />
          <ModuleWorkspaceKpiTile
            label="Capacitas"
            variant="amber"
            value={`${activeCapacitasCredentials.length}/${capacitasCredentials.length}`}
            hint={`${capacitasWarningCount} warning`}
          />
          <ModuleWorkspaceKpiTile
            label="WhiteCompany"
            variant="emerald"
            value={`${activeBonificaCredentials.length}/${bonificaCredentials.length}`}
            hint={`${bonificaWarningCount} warning`}
          />
          <ModuleWorkspaceKpiTile
            label="CAPTCHA"
            value={captchaSummary?.processed ?? 0}
            hint={`${captchaSummary?.correct ?? 0} ok · ${captchaSummary?.wrong ?? 0} ko`}
          />
          <ModuleWorkspaceKpiTile
            label="Ultimo uso"
            value={latestCapacitasUsage ? "Registrato" : "Assente"}
            hint={latestCapacitasUsage ? formatDateTime(latestCapacitasUsage) : "mai"}
          />
        </ModuleWorkspaceKpiRow>
        <div className="mt-4 grid gap-3 lg:grid-cols-[1.1fr,1fr,1fr]">
          <ElaborazioneNoticeCard
            title="ANPR batch a ruolo"
            description={
              anprSummary
                ? `${anprSummary.calls_today}/${anprSummary.effective_daily_limit} chiamate oggi · batch ${anprSummary.batch_size} · ruolo ${anprSummary.ruolo_year ?? "auto"}`
                : "Monitor chiamate e run ANPR sui soggetti a ruolo."
            }
            tone={
              anprSummary && anprSummary.calls_today >= anprSummary.effective_daily_limit
                ? "warning"
                : "neutral"
            }
            compact
          />
          <div className="rounded-2xl border border-gray-100 bg-white/80 px-4 py-3">
            <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-gray-500">Ultimo run ANPR</p>
            <p className="mt-2 text-sm font-semibold text-gray-900">
              {anprSummary?.recent_runs[0] ? formatDateTime(anprSummary.recent_runs[0].started_at) : "Nessun run"}
            </p>
            <p className="mt-1 text-xs text-gray-500">
              {anprSummary?.recent_runs[0]
                ? `${anprSummary.recent_runs[0].status} · ${anprSummary.recent_runs[0].calls_used} chiamate · ${anprSummary.recent_runs[0].subjects_processed} soggetti`
                : "Nessuna esecuzione registrata"}
            </p>
          </div>
          <div className="rounded-2xl border border-gray-100 bg-white/80 px-4 py-3">
            <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-gray-500">Storico run</p>
            {anprSummary?.recent_runs.length ? (
              <div className="mt-2 space-y-2">
                {anprSummary.recent_runs.slice(0, 3).map((run) => (
                  <div key={run.id} className="flex items-center justify-between gap-3 text-xs text-gray-600">
                    <span className="truncate">{formatDateTime(run.started_at)}</span>
                    <span className="shrink-0">{run.calls_used} call</span>
                    <span className="shrink-0">{run.status}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="mt-2 text-xs text-gray-500">Nessun run registrato.</p>
            )}
          </div>
        </div>
      </ElaborazioneHero>

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
                    <td>
                      <button
                        className="font-medium text-[#1D4E35] transition hover:text-[#143726]"
                        onClick={() =>
                          openWorkspaceModal(
                            `/elaborazioni/batches/${batch.id}`,
                            batch.name ?? "Dettaglio batch",
                            "Dettaglio batch aperto in modale per consultare stato, richieste e CAPTCHA senza lasciare la dashboard.",
                          )
                        }
                        type="button"
                      >
                        {batch.name ?? batch.id}
                      </button>
                    </td>
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
                        {batch.current_operation === "Retry queued" || (batch.status === "failed" && batch.failed_items > 0) ? (
                          <button
                            className="text-sm text-[#1D4E35] transition hover:text-[#143726] disabled:cursor-not-allowed disabled:text-gray-300"
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
