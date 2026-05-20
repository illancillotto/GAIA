"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { EmptyState } from "@/components/ui/empty-state";
import { FolderIcon, SearchIcon } from "@/components/ui/icons";
import { ElaborazioneOperationMessage } from "@/components/elaborazioni/operation-message";
import { ElaborazionePanelHeader } from "@/components/elaborazioni/module-chrome";
import { ElaborazioneStatusBadge } from "@/components/elaborazioni/status-badge";
import { getElaborazioneBatch, getElaborazioneBatches, retryFailedElaborazioneBatch } from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import { formatDateTime } from "@/lib/presentation";
import type { ElaborazioneBatch, ElaborazioneBatchDetail } from "@/types/api";

const RECENT_BATCHES_REFRESH_INTERVAL_MS = 10000;

type RecentBatchesPanelProps = {
  limit?: number;
};

export function RecentBatchesPanel({ limit = 6 }: RecentBatchesPanelProps) {
  const router = useRouter();
  const [batches, setBatches] = useState<ElaborazioneBatch[]>([]);
  const [batchDetails, setBatchDetails] = useState<Record<string, ElaborazioneBatchDetail>>({});
  const [error, setError] = useState<string | null>(null);
  const [retryBusyId, setRetryBusyId] = useState<string | null>(null);

  const recentBatches = useMemo(() => {
    const isRunning = (status: ElaborazioneBatch["status"]): boolean => status === "pending" || status === "processing";

    return [...batches]
      .sort((left, right) => {
        const runningDelta = Number(isRunning(right.status)) - Number(isRunning(left.status));
        if (runningDelta !== 0) {
          return runningDelta;
        }

        return Date.parse(right.created_at) - Date.parse(left.created_at);
      })
      .slice(0, limit);
  }, [batches, limit]);

  useEffect(() => {
    let cancelled = false;

    async function loadBatches(): Promise<void> {
      const token = getStoredAccessToken();
      if (!token) {
        if (!cancelled) {
          setBatches([]);
          setBatchDetails({});
        }
        return;
      }

      try {
        const result = await getElaborazioneBatches(token);
        if (cancelled) {
          return;
        }
        setBatches(result);
        setBatchDetails((current) => {
          const next: Record<string, ElaborazioneBatchDetail> = {};
          result.forEach((batch) => {
            if (current[batch.id]) {
              next[batch.id] = current[batch.id];
            }
          });
          return next;
        });
        setError(null);
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : "Errore caricamento batch recenti");
        }
      }
    }

    void loadBatches();
    const intervalId = window.setInterval(() => {
      void loadBatches();
    }, RECENT_BATCHES_REFRESH_INTERVAL_MS);

    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, []);

  useEffect(() => {
    const token = getStoredAccessToken();
    if (!token || recentBatches.length === 0) {
      return;
    }

    recentBatches.forEach((batch) => {
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
  }, [batchDetails, recentBatches]);

  async function handleRetryBatch(batch: ElaborazioneBatch): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) {
      return;
    }

    setRetryBusyId(batch.id);
    try {
      const updatedBatch = await retryFailedElaborazioneBatch(token, batch.id);
      setBatches((current) => current.map((item) => (item.id === updatedBatch.id ? updatedBatch : item)));
    } catch (retryError) {
      setError(retryError instanceof Error ? retryError.message : "Errore retry batch");
    } finally {
      setRetryBusyId(null);
    }
  }

  return (
    <article className="overflow-hidden rounded-[28px] border border-[#d9dfd6] bg-white p-0 shadow-panel">
      <ElaborazionePanelHeader
        badge={
          <>
            <FolderIcon className="h-3.5 w-3.5" />
            Batch recenti
          </>
        }
        title="Ultimi lotti creati dall'utente corrente delle visure"
        description="Apri il dettaglio del batch per consultare stato, richieste riga per riga e CAPTCHA manuali."
      />
      {error ? (
        <div className="p-5">
          <EmptyState icon={SearchIcon} title="Errore caricamento batch" description={error} />
        </div>
      ) : recentBatches.length === 0 ? (
        <div className="p-5">
          <EmptyState icon={SearchIcon} title="Nessun batch presente" description="Crea una visura o importa un lotto per vedere qui lo storico recente." />
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
              {recentBatches.map((batch) => (
                <tr key={batch.id}>
                  <td>
                    <button
                      className="font-medium text-[#1D4E35] transition hover:text-[#143726]"
                      onClick={() => router.push(`/elaborazioni/batches/${batch.id}`)}
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
                      <button
                        className="text-sm text-[#1D4E35] transition hover:text-[#143726]"
                        onClick={() => router.push(`/elaborazioni/batches/${batch.id}`)}
                        type="button"
                      >
                        Apri batch
                      </button>
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
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </article>
  );
}
