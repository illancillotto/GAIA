"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { ProtectedPage } from "@/components/app/protected-page";
import { CatastoStatusBadge } from "@/components/catasto/status-badge";
import { EmptyState } from "@/components/ui/empty-state";
import { SearchIcon } from "@/components/ui/icons";
import { cancelCatastoBatch, getCatastoBatches, retryFailedCatastoBatch } from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import { formatDateTime } from "@/lib/presentation";
import type { CatastoBatch } from "@/types/api";

export default function CatastoBatchesPage() {
  const [batches, setBatches] = useState<CatastoBatch[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [cancelBusyId, setCancelBusyId] = useState<string | null>(null);
  const [retryBusyId, setRetryBusyId] = useState<string | null>(null);

  useEffect(() => {
    async function loadBatches() {
      await refreshBatches();
    }
    void loadBatches();
  }, []);

  async function refreshBatches(): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) return;

    try {
      const result = await getCatastoBatches(token);
      setBatches(result);
      setError(null);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Errore caricamento batch");
    }
  }

  async function handleCancelBatch(batchId: string): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) return;

    setCancelBusyId(batchId);
    try {
      await cancelCatastoBatch(token, batchId);
      await refreshBatches();
      setError(null);
    } catch (cancelError) {
      setError(cancelError instanceof Error ? cancelError.message : "Errore annullamento batch");
    } finally {
      setCancelBusyId(null);
    }
  }

  async function handleRetryFailedBatch(batchId: string): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) return;

    setRetryBusyId(batchId);
    try {
      await retryFailedCatastoBatch(token, batchId);
      await refreshBatches();
      setError(null);
    } catch (retryError) {
      setError(retryError instanceof Error ? retryError.message : "Errore retry batch");
    } finally {
      setRetryBusyId(null);
    }
  }

  return (
    <ProtectedPage
      title="Storico batch Catasto"
      description="Lista dei lotti visure con stato corrente, progresso e ultimo messaggio operativo."
      breadcrumb="Catasto / Batch"
    >
      {error ? <p className="text-sm text-red-600">{error}</p> : null}

      <article className="panel-card overflow-hidden p-0">
        <div className="border-b border-gray-100 px-5 py-4">
          <p className="section-title">Batch utente</p>
          <p className="section-copy">Monitoraggio dei lotti creati nel modulo Catasto.</p>
        </div>
        {batches.length === 0 ? (
          <div className="p-5">
            <EmptyState icon={SearchIcon} title="Nessun batch presente" description="Crea il primo lotto da /catasto/new-batch." />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Nome</th>
                  <th>Stato</th>
                  <th>Totale</th>
                  <th>Operazione</th>
                  <th>Creato</th>
                  <th>Azioni</th>
                  <th>Dettaglio</th>
                </tr>
              </thead>
              <tbody>
                {batches.map((batch) => (
                  <tr key={batch.id}>
                    <td>{batch.name ?? batch.id}</td>
                    <td><CatastoStatusBadge status={batch.status} /></td>
                    <td>{batch.total_items}</td>
                    <td>{batch.current_operation ?? "—"}</td>
                    <td>{formatDateTime(batch.created_at)}</td>
                    <td>
                      <div className="flex flex-wrap items-center gap-3">
                        <button
                          className="text-sm text-gray-500 transition hover:text-gray-800 disabled:cursor-not-allowed disabled:text-gray-300"
                          disabled={retryBusyId === batch.id || batch.failed_items === 0 || batch.status === "processing"}
                          onClick={() => void handleRetryFailedBatch(batch.id)}
                          type="button"
                        >
                          {retryBusyId === batch.id ? "Retry..." : "Riprova fallite"}
                        </button>
                        <button
                          className="text-sm text-gray-500 transition hover:text-gray-800 disabled:cursor-not-allowed disabled:text-gray-300"
                          disabled={cancelBusyId === batch.id || ["completed", "cancelled"].includes(batch.status)}
                          onClick={() => void handleCancelBatch(batch.id)}
                          type="button"
                        >
                          {cancelBusyId === batch.id ? "Annullamento..." : "Annulla"}
                        </button>
                      </div>
                    </td>
                    <td>
                      <Link className="font-medium text-[#1D4E35]" href={`/catasto/batches/${batch.id}`}>
                        Apri
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </article>
    </ProtectedPage>
  );
}
