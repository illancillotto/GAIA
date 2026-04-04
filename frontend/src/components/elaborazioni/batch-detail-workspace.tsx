"use client";

import { useCallback, useEffect, useState } from "react";

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
  downloadElaborazioneBatchZipBlob,
  downloadElaborazioneBatchReportJsonBlob,
  downloadElaborazioneBatchReportMarkdownBlob,
  downloadElaborazioneRequestArtifactsBlob,
  fetchElaborazioneCaptchaImageBlob,
  getElaborazioneBatch,
  retryFailedElaborazioneBatch,
  solveElaborazioneCaptcha,
  skipElaborazioneCaptcha,
  startElaborazioneBatch,
} from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import { formatDateTime } from "@/lib/presentation";
import type { ElaborazioneBatchDetail } from "@/types/api";

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
      void loadBatch();
    };

    return () => {
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

  const canCancelBatch = batch != null && !["completed", "cancelled"].includes(batch.status);
  const canRetryFailedBatch = batch != null && batch.failed_items > 0 && batch.status !== "processing";
  const canStartBatch = batch != null && ["pending", "failed", "cancelled"].includes(batch.status);

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
                    {startBusy ? "Avvio..." : "Avvia batch"}
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
            <div className="overflow-x-auto">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Riga</th>
                    <th>Comune</th>
                    <th>Riferimento</th>
                    <th>Stato</th>
                    <th>Operazione</th>
                    <th>Errore</th>
                  </tr>
                </thead>
                <tbody>
                  {batch.requests.map((request) => (
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
                      <td><ElaborazioneOperationMessage value={request.current_operation} /></td>
                      <td className="text-xs text-gray-500">
                        <ElaborazioneOperationMessage value={request.error_message} />
                        {request.artifact_dir ? (
                          <div className="mt-2">
                            <button
                              className="text-xs font-medium text-[#1D4E35] underline underline-offset-2"
                              disabled={artifactBusyRequestId === request.id}
                              onClick={() => void handleDownloadRequestArtifacts(request.id)}
                              type="button"
                            >
                              {artifactBusyRequestId === request.id ? "Download artifact..." : "Scarica artifact"}
                            </button>
                          </div>
                        ) : null}
                      </td>
                    </tr>
                  ))}
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
