"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { ProtectedPage } from "@/components/app/protected-page";
import { ElaborazioneBatchProgress } from "@/components/elaborazioni/batch-progress";
import { ElaborazioneCaptchaDialog } from "@/components/elaborazioni/captcha-dialog";
import {
  ElaborazioneHero,
  ElaborazioneMiniStat,
  ElaborazioneNoticeCard,
  ElaborazionePanelHeader,
} from "@/components/elaborazioni/module-chrome";
import { ElaborazioneOperationMessage } from "@/components/elaborazioni/operation-message";
import { ElaborazioneStatusBadge } from "@/components/elaborazioni/status-badge";
import { AlertTriangleIcon, FolderIcon, RefreshIcon } from "@/components/ui/icons";
import {
  createElaborazioneBatchWebSocket,
  cancelElaborazioneBatch,
  downloadCatastoDocumentBlob,
  downloadElaborazioneBatchZipBlob,
  downloadElaborazioneBatchReportJsonBlob,
  downloadElaborazioneBatchReportMarkdownBlob,
  downloadElaborazioneRequestArtifactsBlob,
  fetchElaborazioneCaptchaImageBlob,
  fetchElaborazioneRequestArtifactPreviewBlob,
  getElaborazioneBatch,
  retryFailedElaborazioneBatch,
  solveElaborazioneCaptcha,
  skipElaborazioneCaptcha,
  startElaborazioneBatch,
} from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import { formatDateTime } from "@/lib/presentation";
import type { ElaborazioneBatchDetail } from "@/types/api";

type RequestQuickFilter = "all" | "active" | "completed" | "failed" | "not_found" | "awaiting_captcha";

export function isReleasedBatchDetail(batch: ElaborazioneBatchDetail | null): boolean {
  return Boolean(
    batch?.status === "cancelled" &&
      batch.current_operation === "Release requested by user" &&
      batch.requests.some(
        (request) =>
          request.status === "skipped" &&
          request.current_operation === "Release requested by user" &&
          request.error_message === "Credenziale SISTER liberata su richiesta utente",
      ),
  );
}

export function ElaborazioneBatchDetailWorkspace({
  batchId,
  embedded = false,
}: {
  batchId: string;
  embedded?: boolean;
}) {
  const [batch, setBatch] = useState<ElaborazioneBatchDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [captchaBusy, setCaptchaBusy] = useState(false);
  const [captchaImageUrl, setCaptchaImageUrl] = useState<string | null>(null);
  const [downloadBusy, setDownloadBusy] = useState(false);
  const [cancelBusy, setCancelBusy] = useState(false);
  const [retryBusy, setRetryBusy] = useState(false);
  const [startBusy, setStartBusy] = useState(false);
  const [reportBusy, setReportBusy] = useState<"json" | "md" | null>(null);
  const [artifactBusyRequestId, setArtifactBusyRequestId] = useState<string | null>(null);
  const [artifactPreviewUrls, setArtifactPreviewUrls] = useState<Record<string, string>>({});
  const [artifactPreviewMimeTypes, setArtifactPreviewMimeTypes] = useState<Record<string, string>>({});
  const [artifactPreviewLoadingIds, setArtifactPreviewLoadingIds] = useState<Record<string, boolean>>({});
  const [artifactPreviewFailedIds, setArtifactPreviewFailedIds] = useState<Record<string, boolean>>({});
  const [previewModalRequestId, setPreviewModalRequestId] = useState<string | null>(null);
  const [requestQuickFilter, setRequestQuickFilter] = useState<RequestQuickFilter>("all");
  const artifactPreviewUrlsRef = useRef<Record<string, string>>({});
  const websocketRefreshTimeoutRef = useRef<number | null>(null);

  const isArtifactPreviewEligible = useCallback((request: ElaborazioneBatchDetail["requests"][number]): boolean => {
    return (
      Boolean(request.artifact_dir && ["not_found", "failed"].includes(request.status)) ||
      Boolean(request.document_id && request.status === "completed")
    );
  }, []);

  const loadBatch = useCallback(async (): Promise<void> => {
    const token = getStoredAccessToken();
    if (!token || !batchId) return;

    try {
      const result = await getElaborazioneBatch(token, batchId);
      setBatch(result);
      setError(null);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Errore caricamento batch");
    }
  }, [batchId]);

  useEffect(() => {
    void loadBatch();
  }, [loadBatch]);

  useEffect(() => {
    const token = getStoredAccessToken();
    if (!token || !batchId) return;

    const socket = createElaborazioneBatchWebSocket(batchId, token);
    if (!socket) return;

    socket.onmessage = () => {
      if (websocketRefreshTimeoutRef.current != null) {
        window.clearTimeout(websocketRefreshTimeoutRef.current);
      }
      websocketRefreshTimeoutRef.current = window.setTimeout(() => {
        websocketRefreshTimeoutRef.current = null;
        void loadBatch();
      }, 400);
    };

    return () => {
      if (websocketRefreshTimeoutRef.current != null) {
        window.clearTimeout(websocketRefreshTimeoutRef.current);
        websocketRefreshTimeoutRef.current = null;
      }
      socket.close();
    };
  }, [batchId, loadBatch]);

  const activeCaptchaRequest = batch?.requests.find((request) => request.status === "awaiting_captcha") ?? null;

  useEffect(() => {
    const token = getStoredAccessToken();
    const requestId = activeCaptchaRequest?.id ?? null;

    if (!token || !requestId) {
      setCaptchaImageUrl((current) => {
        if (current) {
          URL.revokeObjectURL(current);
        }
        return null;
      });
      return;
    }

    const safeToken = token;
    const safeRequestId = requestId;
    let cancelled = false;

    async function loadCaptchaImage(): Promise<void> {
      try {
        const blob = await fetchElaborazioneCaptchaImageBlob(safeToken, safeRequestId);
        const nextUrl = URL.createObjectURL(blob);

        if (cancelled) {
          URL.revokeObjectURL(nextUrl);
          return;
        }

        setCaptchaImageUrl((current) => {
          if (current) {
            URL.revokeObjectURL(current);
          }
          return nextUrl;
        });
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : "Errore caricamento immagine CAPTCHA");
          setCaptchaImageUrl((current) => {
            if (current) {
              URL.revokeObjectURL(current);
            }
            return null;
          });
        }
      }
    }

    void loadCaptchaImage();

    return () => {
      cancelled = true;
    };
  }, [activeCaptchaRequest]);

  useEffect(() => {
    return () => {
      if (captchaImageUrl) {
        URL.revokeObjectURL(captchaImageUrl);
      }
    };
  }, [captchaImageUrl]);

  useEffect(() => {
    artifactPreviewUrlsRef.current = artifactPreviewUrls;
  }, [artifactPreviewUrls]);

  useEffect(() => {
    const token = getStoredAccessToken();
    const requests = batch?.requests ?? [];
    const eligibleRequestIds = new Set(
      requests
        .filter((request) => isArtifactPreviewEligible(request))
        .map((request) => request.id),
    );

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
    setArtifactPreviewMimeTypes((current) => {
      const next = Object.fromEntries(Object.entries(current).filter(([requestId]) => eligibleRequestIds.has(requestId)));
      const sameKeys =
        Object.keys(next).length === Object.keys(current).length &&
        Object.keys(next).every((requestId) => current[requestId] === next[requestId]);
      return sameKeys ? current : next;
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

    if (!token) {
      return;
    }

    requests
      .filter((request) => request.artifact_dir && ["not_found", "failed"].includes(request.status))
      .forEach((request) => {
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
            setArtifactPreviewMimeTypes((current) => ({ ...current, [request.id]: blob.type || "image/png" }));
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
  }, [artifactPreviewFailedIds, artifactPreviewLoadingIds, artifactPreviewUrls, batch?.requests, isArtifactPreviewEligible]);

  useEffect(() => {
    return () => {
      Object.values(artifactPreviewUrlsRef.current).forEach((url) => URL.revokeObjectURL(url));
    };
  }, []);

  async function handleSolveCaptcha(value: string): Promise<void> {
    const token = getStoredAccessToken();
    if (!token || !activeCaptchaRequest) return;

    setCaptchaBusy(true);
    try {
      await solveElaborazioneCaptcha(token, activeCaptchaRequest.id, value);
      await loadBatch();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Errore invio CAPTCHA");
    } finally {
      setCaptchaBusy(false);
    }
  }

  async function handleSkipCaptcha(): Promise<void> {
    const token = getStoredAccessToken();
    if (!token || !activeCaptchaRequest) return;

    setCaptchaBusy(true);
    try {
      await skipElaborazioneCaptcha(token, activeCaptchaRequest.id);
      await loadBatch();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Errore skip CAPTCHA");
    } finally {
      setCaptchaBusy(false);
    }
  }

  async function handleDownloadBatch(): Promise<void> {
    const token = getStoredAccessToken();
    if (!token || !batch) return;

    setDownloadBusy(true);
    try {
      const blob = await downloadElaborazioneBatchZipBlob(token, batch.id);
      const url = URL.createObjectURL(blob);
      const anchor = window.document.createElement("a");
      anchor.href = url;
      anchor.download = `${(batch.name ?? batch.id).replaceAll("/", "-")}.zip`;
      anchor.click();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
      setError(null);
    } catch (downloadError) {
      setError(downloadError instanceof Error ? downloadError.message : "Errore download ZIP batch");
    } finally {
      setDownloadBusy(false);
    }
  }

  async function handleCancelBatch(): Promise<void> {
    const token = getStoredAccessToken();
    if (!token || !batch) return;

    setCancelBusy(true);
    try {
      await cancelElaborazioneBatch(token, batch.id);
      await loadBatch();
      setError(null);
    } catch (cancelError) {
      setError(cancelError instanceof Error ? cancelError.message : "Errore annullamento batch");
    } finally {
      setCancelBusy(false);
    }
  }

  async function handleRetryFailedBatch(): Promise<void> {
    const token = getStoredAccessToken();
    if (!token || !batch) return;

    setRetryBusy(true);
    try {
      await retryFailedElaborazioneBatch(token, batch.id);
      await loadBatch();
      setError(null);
    } catch (retryError) {
      setError(retryError instanceof Error ? retryError.message : "Errore retry batch");
    } finally {
      setRetryBusy(false);
    }
  }

  async function handleStartBatch(): Promise<void> {
    const token = getStoredAccessToken();
    if (!token || !batch) return;

    setStartBusy(true);
    try {
      await startElaborazioneBatch(token, batch.id);
      await loadBatch();
      setError(null);
    } catch (startError) {
      setError(startError instanceof Error ? startError.message : "Errore avvio batch");
    } finally {
      setStartBusy(false);
    }
  }

  async function handleDownloadReport(format: "json" | "md"): Promise<void> {
    const token = getStoredAccessToken();
    if (!token || !batch) return;

    setReportBusy(format);
    try {
      const blob =
        format === "json"
          ? await downloadElaborazioneBatchReportJsonBlob(token, batch.id)
          : await downloadElaborazioneBatchReportMarkdownBlob(token, batch.id);
      const url = URL.createObjectURL(blob);
      const anchor = window.document.createElement("a");
      anchor.href = url;
      anchor.download = `${(batch.name ?? batch.id).replaceAll("/", "-")}.${format}`;
      anchor.click();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
      setError(null);
    } catch (downloadError) {
      setError(downloadError instanceof Error ? downloadError.message : "Errore download report batch");
    } finally {
      setReportBusy(null);
    }
  }

  async function handleDownloadRequestArtifacts(requestId: string): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) return;

    setArtifactBusyRequestId(requestId);
    try {
      const blob = await downloadElaborazioneRequestArtifactsBlob(token, requestId);
      const url = URL.createObjectURL(blob);
      const anchor = window.document.createElement("a");
      anchor.href = url;
      anchor.download = `request-${requestId}-artifacts.zip`;
      anchor.click();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
      setError(null);
    } catch (downloadError) {
      setError(downloadError instanceof Error ? downloadError.message : "Errore download artifact richiesta");
    } finally {
      setArtifactBusyRequestId(null);
    }
  }

  async function handleOpenPreviewModal(request: ElaborazioneBatchDetail["requests"][number]): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) return;

    if (artifactPreviewUrls[request.id]) {
      setPreviewModalRequestId(request.id);
      return;
    }

    if (!request.document_id || request.status !== "completed") {
      return;
    }

    setArtifactPreviewLoadingIds((current) => ({ ...current, [request.id]: true }));
    try {
      const blob = await downloadCatastoDocumentBlob(token, request.document_id);
      const url = URL.createObjectURL(blob);
      setArtifactPreviewUrls((current) => {
        if (current[request.id]) {
          URL.revokeObjectURL(url);
          return current;
        }
        return { ...current, [request.id]: url };
      });
      setArtifactPreviewMimeTypes((current) => ({ ...current, [request.id]: blob.type || "application/pdf" }));
      setArtifactPreviewFailedIds((current) => {
        if (!current[request.id]) return current;
        const next = { ...current };
        delete next[request.id];
        return next;
      });
      setPreviewModalRequestId(request.id);
    } catch (previewError) {
      setError(previewError instanceof Error ? previewError.message : "Errore caricamento preview PDF");
      setArtifactPreviewFailedIds((current) => ({ ...current, [request.id]: true }));
    } finally {
      setArtifactPreviewLoadingIds((current) => {
        if (!current[request.id]) return current;
        const next = { ...current };
        delete next[request.id];
        return next;
      });
    }
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

  function renderRequestOperation(request: ElaborazioneBatchDetail["requests"][number]): string | null {
    if (request.status === "not_found" && request.search_mode === "soggetto" && request.current_operation === "Nessuna corrispondenza") {
      return "Utente non è titolare di terreni o immobili";
    }
    return request.current_operation;
  }

  function getArtifactActionClassName(disabled = false): string {
    return [
      "inline-flex items-center rounded-full border px-3 py-1.5 text-xs font-semibold transition",
      disabled
        ? "cursor-not-allowed border-gray-200 bg-gray-100 text-gray-400"
        : "border-[#cfe0d5] bg-[#f3f8f4] text-[#1D4E35] hover:border-[#1D4E35] hover:bg-[#e8f2eb]",
    ].join(" ");
  }

  const canCancelBatch = batch != null && !["completed", "cancelled"].includes(batch.status);
  const canRetryFailedBatch = batch != null && batch.failed_items > 0 && batch.status !== "processing";
  const canStartBatch = batch != null && ["pending", "failed", "cancelled"].includes(batch.status);
  const isReleasedBatch = isReleasedBatchDetail(batch);
  const startBatchLabel = startBusy
    ? isReleasedBatch
      ? "Ripresa..."
      : "Avvio..."
    : batch?.status === "processing"
      ? "Batch in esecuzione"
      : isReleasedBatch
        ? "Riprendi batch"
        : "Avvia batch";
  const previewModalRequest = batch?.requests.find((request) => request.id === previewModalRequestId) ?? null;
  const previewModalUrl = previewModalRequestId ? artifactPreviewUrls[previewModalRequestId] ?? null : null;
  const previewModalMimeType = previewModalRequestId ? artifactPreviewMimeTypes[previewModalRequestId] ?? null : null;
  const quickFilterItems = useMemo(
    () => [
      { id: "all" as const, label: "Tutte", count: batch?.requests.length ?? 0 },
      {
        id: "active" as const,
        label: "In corso",
        count:
          batch?.requests.filter((request) =>
            ["pending", "processing"].includes(request.status),
          ).length ?? 0,
      },
      { id: "awaiting_captcha" as const, label: "CAPTCHA", count: batch?.requests.filter((request) => request.status === "awaiting_captcha").length ?? 0 },
      { id: "completed" as const, label: "Completate", count: batch?.requests.filter((request) => request.status === "completed").length ?? 0 },
      {
        id: "failed" as const,
        label: "Fallite",
        count: batch?.requests.filter((request) => ["failed", "skipped"].includes(request.status)).length ?? 0,
      },
      { id: "not_found" as const, label: "Non trovate", count: batch?.requests.filter((request) => request.status === "not_found").length ?? 0 },
    ],
    [batch?.requests],
  );
  const filteredRequests = useMemo(() => {
    const requests = batch?.requests ?? [];
    switch (requestQuickFilter) {
      case "active":
        return requests.filter((request) => ["pending", "processing"].includes(request.status));
      case "completed":
        return requests.filter((request) => request.status === "completed");
      case "failed":
        return requests.filter((request) => ["failed", "skipped"].includes(request.status));
      case "not_found":
        return requests.filter((request) => request.status === "not_found");
      case "awaiting_captcha":
        return requests.filter((request) => request.status === "awaiting_captcha");
      default:
        return requests;
    }
  }, [batch?.requests, requestQuickFilter]);

  const content = (
    <>
      <ElaborazioneHero
        compact={embedded}
        badge={
          <>
            <FolderIcon className="h-3.5 w-3.5" />
            Dettaglio batch
          </>
        }
        title={batch?.name ?? "Monitor realtime del batch"}
        description="Lo stream websocket mantiene questa vista aggiornata su stato righe, operazioni correnti e richieste CAPTCHA che richiedono intervento manuale."
        actions={
          error ? (
            <ElaborazioneNoticeCard compact={embedded} title="Errore batch" description={error} tone="danger" />
          ) : activeCaptchaRequest ? (
            <ElaborazioneNoticeCard
              compact={embedded}
              title="Intervento richiesto"
              description={`CAPTCHA aperto per ${activeCaptchaRequest.comune} · Fg.${activeCaptchaRequest.foglio} Part.${activeCaptchaRequest.particella}.`}
              tone="warning"
            />
          ) : (
            <ElaborazioneNoticeCard
              compact={embedded}
              title="Canale realtime"
              description="Ogni aggiornamento ricevuto dal websocket forza un refresh del dettaglio batch."
            />
          )
        }
      >
        <div className="grid gap-3 sm:grid-cols-4">
          <ElaborazioneMiniStat
            compact={embedded}
            description={batch?.current_operation ?? "Recupero stato batch"}
            eyebrow="Stato"
            tone={batch?.status === "completed" ? "success" : batch?.status === "failed" ? "warning" : "default"}
            value={batch?.status ?? "Caricamento"}
          />
          <ElaborazioneMiniStat compact={embedded} eyebrow="Totale" value={batch?.total_items ?? 0} description="Righe inserite nel lotto." />
          <ElaborazioneMiniStat
            compact={embedded}
            description={`${batch?.failed_items ?? 0} fallite · ${batch?.skipped_items ?? 0} saltate`}
            eyebrow="Completate"
            tone={(batch?.completed_items ?? 0) > 0 ? "success" : "default"}
            value={batch?.completed_items ?? 0}
          />
          <ElaborazioneMiniStat
            compact={embedded}
            description="Richieste manuali ancora da risolvere per il worker."
            eyebrow="CAPTCHA"
            tone={activeCaptchaRequest ? "warning" : "default"}
            value={activeCaptchaRequest ? "Aperto" : "Nessuno"}
          />
        </div>
      </ElaborazioneHero>

      {batch ? (
        <>
          <ElaborazioneBatchProgress batch={batch} />

          <article className="overflow-hidden rounded-[28px] border border-[#d9dfd6] bg-white p-0 shadow-panel">
            <ElaborazionePanelHeader
              badge={
                <>
                  <RefreshIcon className="h-3.5 w-3.5" />
                  Gestione batch
                </>
              }
              title={batch.name ?? batch.id}
              description={`Creato ${formatDateTime(batch.created_at)} · Avvio ${formatDateTime(batch.started_at)} · Chiusura ${formatDateTime(batch.completed_at)}`}
              actions={
                <div className="flex flex-wrap gap-2">
                  <button className="btn-secondary" disabled={startBusy || !canStartBatch} onClick={() => void handleStartBatch()} type="button">
                    {startBatchLabel}
                  </button>
                  <button className="btn-secondary" disabled={downloadBusy || batch.completed_items === 0} onClick={() => void handleDownloadBatch()} type="button">
                    {downloadBusy ? "Preparazione ZIP..." : "Scarica tutti i PDF (ZIP)"}
                  </button>
                  <button className="btn-secondary" disabled={reportBusy !== null || !batch.report_json_path} onClick={() => void handleDownloadReport("json")} type="button">
                    {reportBusy === "json" ? "Download..." : "Report JSON"}
                  </button>
                  <button className="btn-secondary" disabled={reportBusy !== null || !batch.report_md_path} onClick={() => void handleDownloadReport("md")} type="button">
                    {reportBusy === "md" ? "Download..." : "Report Markdown"}
                  </button>
                  <button className="btn-secondary" disabled={retryBusy || !canRetryFailedBatch} onClick={() => void handleRetryFailedBatch()} type="button">
                    {retryBusy ? "Retry..." : "Riprova richieste fallite"}
                  </button>
                  <button className="btn-secondary" disabled={cancelBusy || !canCancelBatch} onClick={() => void handleCancelBatch()} type="button">
                    {cancelBusy ? "Annullamento..." : "Annulla batch"}
                  </button>
                </div>
              }
            />
            <div className="border-b border-[#edf1eb] px-5 py-4">
              <div className="flex flex-wrap items-center gap-2">
                {quickFilterItems.map((filterItem) => (
                  <button
                    key={filterItem.id}
                    className={`rounded-full border px-3 py-1.5 text-xs font-semibold transition ${
                      requestQuickFilter === filterItem.id
                        ? "border-[#1D4E35] bg-[#eef6f0] text-[#1D4E35]"
                        : "border-gray-200 bg-white text-gray-600 hover:border-gray-300 hover:text-gray-900"
                    }`}
                    onClick={() => setRequestQuickFilter(filterItem.id)}
                    type="button"
                  >
                    {filterItem.label} {filterItem.count}
                  </button>
                ))}
              </div>
            </div>
            <div className="overflow-x-auto">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Riga</th>
                    <th>Comune</th>
                    <th>Riferimento</th>
                    <th>Stato</th>
                    <th>Operazione</th>
                    <th>Eseguita</th>
                    <th>Dettagli</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredRequests.map((request) => (
                    <tr key={request.id}>
                      <td>{request.row_index}</td>
                      <td>{renderRequestLabel(request)}</td>
                      <td>
                        {renderRequestReference(request)}
                        <br />
                        <span className="text-xs text-gray-400">
                          {request.tipo_visura}
                          {request.search_mode === "soggetto" ? " · soggetto" : " · immobile"}
                        </span>
                      </td>
                      <td><ElaborazioneStatusBadge status={request.status} /></td>
                      <td><ElaborazioneOperationMessage value={renderRequestOperation(request)} /></td>
                      <td className="text-xs text-gray-500">
                        {request.processed_at
                          ? formatDateTime(request.processed_at)
                          : request.status === "processing"
                            ? "In esecuzione"
                            : request.status === "pending"
                              ? "In coda"
                              : "—"}
                      </td>
                      <td className="text-xs text-gray-500">
                        <ElaborazioneOperationMessage value={request.error_message} />
                        {request.artifact_dir ? (
                          <div className="mt-2">
                            <div className="flex flex-wrap gap-3">
                              <button
                                className={getArtifactActionClassName(artifactBusyRequestId === request.id)}
                                disabled={artifactBusyRequestId === request.id}
                                onClick={() => void handleDownloadRequestArtifacts(request.id)}
                                type="button"
                              >
                                {artifactBusyRequestId === request.id ? "Download artifact..." : "Scarica artifact"}
                              </button>
                              {artifactPreviewLoadingIds[request.id] ? (
                                <span className="text-[11px] text-gray-400">Caricamento preview...</span>
                              ) : null}
                              {artifactPreviewUrls[request.id] ? (
                                <button
                                  className={getArtifactActionClassName()}
                                  onClick={() => void handleOpenPreviewModal(request)}
                                  type="button"
                                >
                                  {request.status === "completed" ? "Preview PDF" : "Preview screenshot"}
                                </button>
                              ) : null}
                              {request.status === "completed" && request.document_id && !artifactPreviewUrls[request.id] ? (
                                <button
                                  className={getArtifactActionClassName(artifactPreviewLoadingIds[request.id])}
                                  disabled={artifactPreviewLoadingIds[request.id]}
                                  onClick={() => void handleOpenPreviewModal(request)}
                                  type="button"
                                >
                                  {artifactPreviewLoadingIds[request.id] ? "Caricamento PDF..." : "Preview PDF"}
                                </button>
                              ) : null}
                            </div>
                          </div>
                        ) : null}
                        {request.status === "completed" && request.document_id && !request.artifact_dir ? (
                          <div className="mt-2">
                            <button
                              className={getArtifactActionClassName(artifactPreviewLoadingIds[request.id])}
                              disabled={artifactPreviewLoadingIds[request.id]}
                              onClick={() => void handleOpenPreviewModal(request)}
                              type="button"
                            >
                              {artifactPreviewLoadingIds[request.id] ? "Caricamento PDF..." : "Preview PDF"}
                            </button>
                          </div>
                        ) : null}
                      </td>
                    </tr>
                  ))}
                  {filteredRequests.length === 0 ? (
                    <tr>
                      <td className="py-6 text-center text-sm text-gray-500" colSpan={7}>
                        Nessuna richiesta nel filtro selezionato.
                      </td>
                    </tr>
                  ) : null}
                </tbody>
              </table>
            </div>
          </article>

          {activeCaptchaRequest ? (
            <article className="rounded-[28px] border border-amber-200 bg-white p-6 shadow-panel">
              <div className="flex items-start gap-3">
                <div className="rounded-2xl bg-amber-100 p-3 text-amber-700">
                  <AlertTriangleIcon className="h-5 w-5" />
                </div>
                <div>
                  <p className="text-lg font-semibold text-gray-900">CAPTCHA attualmente bloccante</p>
                  <p className="mt-2 text-sm leading-6 text-gray-600">
                    {renderRequestLabel(activeCaptchaRequest)} · {renderRequestReference(activeCaptchaRequest)}. Inserisci il
                    codice o usa skip per far proseguire il worker secondo la logica backend.
                  </p>
                </div>
              </div>
            </article>
          ) : null}
        </>
      ) : (
        <article className="panel-card">
          <p className="section-copy">Caricamento batch in corso.</p>
        </article>
      )}

      <ElaborazioneCaptchaDialog
        busy={captchaBusy}
        imageUrl={captchaImageUrl}
        open={Boolean(activeCaptchaRequest)}
        onSkip={handleSkipCaptcha}
        onSolve={handleSolveCaptcha}
        requestLabel={
          activeCaptchaRequest
            ? `${renderRequestLabel(activeCaptchaRequest)} · ${renderRequestReference(activeCaptchaRequest)}`
            : null
        }
      />

      {previewModalRequest && previewModalUrl ? (
        <div className="fixed inset-0 z-[80] flex items-center justify-center bg-black/45 px-4 py-6 backdrop-blur-sm">
          <div className="flex max-h-[96vh] w-full max-w-[96vw] flex-col overflow-hidden rounded-[28px] border border-gray-200 bg-white shadow-[0_30px_90px_rgba(15,23,42,0.24)]">
            <div className="flex items-center justify-between gap-4 border-b border-gray-100 px-6 py-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#1D4E35]">
                  {previewModalMimeType === "application/pdf" ? "Preview PDF" : "Preview screen"}
                </p>
                <h2 className="mt-1 text-lg font-semibold text-gray-900">{renderRequestLabel(previewModalRequest)}</h2>
                <p className="mt-1 text-sm text-gray-500">{renderRequestReference(previewModalRequest)}</p>
              </div>
              <button className="btn-secondary" onClick={() => setPreviewModalRequestId(null)} type="button">
                Chiudi
              </button>
            </div>
            <div className="overflow-auto bg-[#f4f7f5] p-5">
              <div className="overflow-hidden rounded-2xl border border-[#d9dfd6] bg-white p-3">
                {previewModalMimeType === "application/pdf" ? (
                  <iframe
                    className="h-[84vh] w-full rounded-xl border border-[#d9dfd6] bg-white"
                    src={previewModalUrl}
                    title={`PDF visura richiesta ${previewModalRequest.row_index}`}
                  />
                ) : (
                  <>
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      alt={`Preview artifact richiesta ${previewModalRequest.row_index}`}
                      className="h-auto w-full rounded-xl border border-[#d9dfd6] object-contain"
                      src={previewModalUrl}
                    />
                  </>
                )}
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </>
  );

  if (embedded) {
    return <div className="space-y-6">{content}</div>;
  }

  return (
    <ProtectedPage
      title="Dettaglio elaborazione"
      description="Progress realtime, stato per riga e gestione manuale dei CAPTCHA richiesti dal worker."
      breadcrumb="Elaborazioni / Dettaglio batch"
    >
      {content}
    </ProtectedPage>
  );
}
