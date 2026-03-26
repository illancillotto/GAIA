"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";

import { ProtectedPage } from "@/components/app/protected-page";
import { CatastoOperationMessage } from "@/components/catasto/operation-message";
import { BatchProgress } from "@/components/catasto/batch-progress";
import { CaptchaDialog } from "@/components/catasto/captcha-dialog";
import { CatastoStatusBadge } from "@/components/catasto/status-badge";
import {
  cancelCatastoBatch,
  createCatastoBatchWebSocket,
  downloadCatastoBatchZipBlob,
  fetchCatastoCaptchaImageBlob,
  getCatastoBatch,
  retryFailedCatastoBatch,
  solveCatastoCaptcha,
  skipCatastoCaptcha,
  startCatastoBatch,
} from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import { formatDateTime } from "@/lib/presentation";
import type { CatastoBatchDetail } from "@/types/api";

export default function CatastoBatchDetailPage() {
  const params = useParams<{ id: string }>();
  const batchId = params.id;
  const [batch, setBatch] = useState<CatastoBatchDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [captchaBusy, setCaptchaBusy] = useState(false);
  const [captchaImageUrl, setCaptchaImageUrl] = useState<string | null>(null);
  const [downloadBusy, setDownloadBusy] = useState(false);
  const [cancelBusy, setCancelBusy] = useState(false);
  const [retryBusy, setRetryBusy] = useState(false);
  const [startBusy, setStartBusy] = useState(false);

  const loadBatch = useCallback(async (): Promise<void> => {
    const token = getStoredAccessToken();
    if (!token || !batchId) return;

    try {
      const result = await getCatastoBatch(token, batchId);
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

    const socket = createCatastoBatchWebSocket(batchId, token);
    if (!socket) return;

    socket.onmessage = () => {
      void loadBatch();
    };

    return () => {
      socket.close();
    };
  }, [batchId, loadBatch]);

  const activeCaptchaRequest =
    batch?.requests.find((request) => request.status === "awaiting_captcha") ?? null;

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

    const safeToken: string = token;
    const safeRequestId: string = requestId;
    let cancelled = false;

    async function loadCaptchaImage(): Promise<void> {
      try {
        const blob = await fetchCatastoCaptchaImageBlob(safeToken, safeRequestId);
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
      await solveCatastoCaptcha(token, activeCaptchaRequest.id, value);
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
      await skipCatastoCaptcha(token, activeCaptchaRequest.id);
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
      const blob = await downloadCatastoBatchZipBlob(token, batch.id);
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
      await cancelCatastoBatch(token, batch.id);
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
      await retryFailedCatastoBatch(token, batch.id);
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
      await startCatastoBatch(token, batch.id);
      await loadBatch();
      setError(null);
    } catch (startError) {
      setError(startError instanceof Error ? startError.message : "Errore avvio batch");
    } finally {
      setStartBusy(false);
    }
  }

  const canCancelBatch = batch != null && !["completed", "cancelled"].includes(batch.status);
  const canRetryFailedBatch = batch != null && batch.failed_items > 0 && batch.status !== "processing";
  const canStartBatch = batch != null && ["pending", "failed", "cancelled"].includes(batch.status);

  return (
    <ProtectedPage
      title="Dettaglio batch Catasto"
      description="Progress realtime, stato per riga e gestione manuale dei CAPTCHA richiesti dal worker."
      breadcrumb="Catasto / Batch detail"
    >
      {error ? <p className="text-sm text-red-600">{error}</p> : null}

      {batch ? (
        <>
          <BatchProgress batch={batch} />

          <article className="panel-card overflow-hidden p-0">
            <div className="border-b border-gray-100 px-5 py-4">
              <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                <div>
                  <p className="section-title">{batch.name ?? batch.id}</p>
                  <p className="section-copy">
                    Creato {formatDateTime(batch.created_at)} · Avvio {formatDateTime(batch.started_at)} · Chiusura {formatDateTime(batch.completed_at)}
                  </p>
                </div>
                <button
                  className="btn-secondary"
                  disabled={startBusy || !canStartBatch}
                  onClick={() => void handleStartBatch()}
                  type="button"
                >
                  {startBusy ? "Avvio..." : "Avvia batch"}
                </button>
                <button
                  className="btn-secondary"
                  disabled={downloadBusy || batch.completed_items === 0}
                  onClick={() => void handleDownloadBatch()}
                  type="button"
                >
                  {downloadBusy ? "Preparazione ZIP..." : "Scarica tutti i PDF (ZIP)"}
                </button>
                <button
                  className="btn-secondary"
                  disabled={retryBusy || !canRetryFailedBatch}
                  onClick={() => void handleRetryFailedBatch()}
                  type="button"
                >
                  {retryBusy ? "Retry..." : "Riprova richieste fallite"}
                </button>
                <button
                  className="btn-secondary"
                  disabled={cancelBusy || !canCancelBatch}
                  onClick={() => void handleCancelBatch()}
                  type="button"
                >
                  {cancelBusy ? "Annullamento..." : "Annulla batch"}
                </button>
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
                    <th>Errore</th>
                  </tr>
                </thead>
                <tbody>
                  {batch.requests.map((request) => (
                    <tr key={request.id}>
                      <td>{request.row_index}</td>
                      <td>{request.comune}</td>
                      <td>
                        Fg.{request.foglio} Part.{request.particella}
                        {request.subalterno ? ` Sub.${request.subalterno}` : ""}
                        <br />
                        <span className="text-xs text-gray-400">{request.tipo_visura}</span>
                      </td>
                      <td><CatastoStatusBadge status={request.status} /></td>
                      <td><CatastoOperationMessage value={request.current_operation} /></td>
                      <td className="text-xs text-gray-500"><CatastoOperationMessage value={request.error_message} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </article>
        </>
      ) : (
        <article className="panel-card">
          <p className="section-copy">Caricamento batch in corso.</p>
        </article>
      )}

      <CaptchaDialog
        busy={captchaBusy}
        imageUrl={captchaImageUrl}
        open={Boolean(activeCaptchaRequest)}
        onSkip={handleSkipCaptcha}
        onSolve={handleSolveCaptcha}
        requestLabel={
          activeCaptchaRequest
            ? `${activeCaptchaRequest.comune} · Fg.${activeCaptchaRequest.foglio} Part.${activeCaptchaRequest.particella}`
            : null
        }
      />
    </ProtectedPage>
  );
}
