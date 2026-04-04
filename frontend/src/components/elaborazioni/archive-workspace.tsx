"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";

import { ProtectedPage } from "@/components/app/protected-page";
import { ElaborazioneHero, ElaborazioneMiniStat, ElaborazioneNoticeCard, ElaborazionePanelHeader } from "@/components/elaborazioni/module-chrome";
import { ElaborazioneStatusBadge } from "@/components/elaborazioni/status-badge";
import { ElaborazioneWorkspaceModal } from "@/components/elaborazioni/workspace-modal";
import { DataTable } from "@/components/table/data-table";
import { TableFilters } from "@/components/table/table-filters";
import { EmptyState } from "@/components/ui/empty-state";
import { DocumentIcon, FolderIcon, RefreshIcon, SearchIcon } from "@/components/ui/icons";
import {
  cancelElaborazioneBatch,
  downloadCatastoDocumentBlob,
  downloadSelectedCatastoDocumentsZipBlob,
  getElaborazioneBatches,
  getCatastoComuni,
  retryFailedElaborazioneBatch,
  searchCatastoDocuments,
} from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import { formatDateTime } from "@/lib/presentation";
import type { CatastoComune, CatastoDocument, ElaborazioneBatch } from "@/types/api";

type ArchiveView = "batches" | "documents";

type FilterState = {
  q: string;
  comune: string;
  foglio: string;
  particella: string;
  createdFrom: string;
  createdTo: string;
};

const EMPTY_FILTERS: FilterState = {
  q: "",
  comune: "",
  foglio: "",
  particella: "",
  createdFrom: "",
  createdTo: "",
};

function toStartOfDay(value: string): string | undefined {
  return value ? `${value}T00:00:00` : undefined;
}

function toEndOfDay(value: string): string | undefined {
  return value ? `${value}T23:59:59` : undefined;
}

function triggerDownload(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const anchor = window.document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export function ElaborazioneArchiveWorkspace({ initialView }: { initialView: ArchiveView }) {
  return <ElaborazioneArchiveWorkspaceContent initialView={initialView} embedded={false} />;
}

export function ElaborazioneArchiveWorkspaceContent({
  initialView,
  embedded = false,
  isolatedView = false,
}: {
  initialView: ArchiveView;
  embedded?: boolean;
  isolatedView?: boolean;
}) {
  const activeView = initialView;
  const [modalState, setModalState] = useState<{ href: string; title: string; description?: string | null } | null>(null);
  const [batches, setBatches] = useState<ElaborazioneBatch[]>([]);
  const [batchError, setBatchError] = useState<string | null>(null);
  const [cancelBusyId, setCancelBusyId] = useState<string | null>(null);
  const [retryBusyId, setRetryBusyId] = useState<string | null>(null);

  const [documents, setDocuments] = useState<CatastoDocument[]>([]);
  const [comuni, setComuni] = useState<CatastoComune[]>([]);
  const [filters, setFilters] = useState<FilterState>(EMPTY_FILTERS);
  const [documentsError, setDocumentsError] = useState<string | null>(null);
  const [documentsBusy, setDocumentsBusy] = useState(false);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);
  const [selectedDocumentIds, setSelectedDocumentIds] = useState<string[]>([]);
  const [zipBusy, setZipBusy] = useState(false);

  function openWorkspaceModal(href: string, title: string, description?: string): void {
    setModalState({ href, title, description });
  }

  useEffect(() => {
    void refreshBatches();
    void loadDocuments(EMPTY_FILTERS);
  }, []);

  useEffect(() => {
    async function loadComuni(): Promise<void> {
      const token = getStoredAccessToken();
      if (!token) return;

      try {
        const result = await getCatastoComuni(token);
        setComuni(result);
      } catch {
        setComuni([]);
      }
    }

    void loadComuni();
  }, []);

  async function refreshBatches(): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) return;

    try {
      const result = await getElaborazioneBatches(token);
      setBatches(result);
      setBatchError(null);
    } catch (loadError) {
      setBatchError(loadError instanceof Error ? loadError.message : "Errore caricamento batch");
    }
  }

  async function handleCancelBatch(batchId: string): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) return;

    setCancelBusyId(batchId);
    try {
      await cancelElaborazioneBatch(token, batchId);
      await refreshBatches();
      setBatchError(null);
    } catch (cancelError) {
      setBatchError(cancelError instanceof Error ? cancelError.message : "Errore annullamento batch");
    } finally {
      setCancelBusyId(null);
    }
  }

  async function handleRetryFailedBatch(batchId: string): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) return;

    setRetryBusyId(batchId);
    try {
      await retryFailedElaborazioneBatch(token, batchId);
      await refreshBatches();
      setBatchError(null);
    } catch (retryError) {
      setBatchError(retryError instanceof Error ? retryError.message : "Errore retry batch");
    } finally {
      setRetryBusyId(null);
    }
  }

  async function loadDocuments(nextFilters: FilterState): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) return;

    setDocumentsBusy(true);
    try {
      const result = await searchCatastoDocuments(token, {
        q: nextFilters.q,
        comune: nextFilters.comune,
        foglio: nextFilters.foglio,
        particella: nextFilters.particella,
        created_from: toStartOfDay(nextFilters.createdFrom),
        created_to: toEndOfDay(nextFilters.createdTo),
      });
      setDocuments(result);
      setSelectedDocumentIds([]);
      setDocumentsError(null);
    } catch (loadError) {
      setDocumentsError(loadError instanceof Error ? loadError.message : "Errore caricamento archivio documenti");
    } finally {
      setDocumentsBusy(false);
    }
  }

  async function handleDownload(documentItem: CatastoDocument): Promise<void> {
    const token = getStoredAccessToken();
    if (!token) return;

    setDownloadingId(documentItem.id);
    try {
      const blob = await downloadCatastoDocumentBlob(token, documentItem.id);
      triggerDownload(blob, documentItem.filename);
      setDocumentsError(null);
    } catch (downloadError) {
      setDocumentsError(downloadError instanceof Error ? downloadError.message : "Errore download PDF");
    } finally {
      setDownloadingId(null);
    }
  }

  async function handleDownloadSelected(): Promise<void> {
    const token = getStoredAccessToken();
    if (!token || selectedDocumentIds.length === 0) return;

    setZipBusy(true);
    try {
      const blob = await downloadSelectedCatastoDocumentsZipBlob(token, selectedDocumentIds);
      triggerDownload(blob, "catasto-documents-selection.zip");
      setDocumentsError(null);
    } catch (downloadError) {
      setDocumentsError(downloadError instanceof Error ? downloadError.message : "Errore download ZIP selezione");
    } finally {
      setZipBusy(false);
    }
  }

  const toggleDocumentSelection = useCallback((documentId: string): void => {
    setSelectedDocumentIds((current) =>
      current.includes(documentId) ? current.filter((item) => item !== documentId) : [...current, documentId],
    );
  }, []);

  const toggleAllDocumentsSelection = useCallback((): void => {
    setSelectedDocumentIds((current) =>
      current.length === documents.length ? [] : documents.map((documentItem) => documentItem.id),
    );
  }, [documents]);

  const documentColumns = useMemo<ColumnDef<CatastoDocument>[]>(
    () => [
      {
        id: "select",
        header: () => (
          <input
            aria-label="Seleziona tutti i documenti"
            checked={documents.length > 0 && selectedDocumentIds.length === documents.length}
            onChange={() => toggleAllDocumentsSelection()}
            type="checkbox"
          />
        ),
        cell: ({ row }) => (
          <input
            aria-label={`Seleziona documento ${row.original.filename}`}
            checked={selectedDocumentIds.includes(row.original.id)}
            onChange={() => toggleDocumentSelection(row.original.id)}
            type="checkbox"
          />
        ),
      },
      {
        header: "Comune",
        accessorKey: "comune",
        cell: ({ row }) => (
          <div>
            <p className="text-sm font-medium text-[#1D4E35]">{row.original.comune}</p>
            <p className="text-xs text-gray-400">{row.original.catasto}</p>
          </div>
        ),
      },
      {
        header: "Riferimento",
        accessorKey: "particella",
        cell: ({ row }) => (
          <div className="text-sm text-gray-700">
            Fg.{row.original.foglio} Part.{row.original.particella}
            {row.original.subalterno ? ` Sub.${row.original.subalterno}` : ""}
          </div>
        ),
      },
      {
        header: "Tipo visura",
        accessorKey: "tipo_visura",
        cell: ({ row }) => <span className="text-sm text-gray-700">{row.original.tipo_visura}</span>,
      },
      {
        header: "Creato",
        accessorKey: "created_at",
        cell: ({ row }) => <span className="text-sm text-gray-700">{formatDateTime(row.original.created_at)}</span>,
      },
      {
        header: "Documento",
        accessorKey: "filename",
        cell: ({ row }) => (
          <div className="flex items-center gap-3">
            <button
              className="text-sm font-medium text-[#1D4E35] transition hover:text-[#143726]"
              onClick={() =>
                openWorkspaceModal(
                  `/catasto/documents/${row.original.id}`,
                  row.original.filename,
                  "Viewer documento aperto in modale per non interrompere la consultazione dell'archivio.",
                )
              }
              type="button"
            >
              Apri viewer
            </button>
            <button
              className="text-sm text-gray-500 transition hover:text-gray-800"
              disabled={downloadingId === row.original.id}
              onClick={() => void handleDownload(row.original)}
              type="button"
            >
              {downloadingId === row.original.id ? "Download..." : "Scarica"}
            </button>
          </div>
        ),
      },
    ],
    [documents, downloadingId, selectedDocumentIds, toggleAllDocumentsSelection, toggleDocumentSelection],
  );

  const completedCount = batches.filter((batch) => batch.status === "completed").length;
  const processingCount = batches.filter((batch) => batch.status === "processing").length;
  const failedCount = batches.filter((batch) => batch.failed_items > 0 || batch.status === "failed").length;
  const sharedError = activeView === "batches" ? batchError : documentsError;
  const batchOnlyMode = isolatedView && activeView === "batches";

  const content = (
    <>
      <ElaborazioneHero
        compact={embedded}
        badge={
          <>
            <FolderIcon className="h-3.5 w-3.5" />
            Archivio
          </>
        }
        title="Monitor operativo delle elaborazioni e accesso ai documenti prodotti."
        description={
          batchOnlyMode
            ? "Archivio operativo dedicato ai lotti del runtime elaborazioni: monitoraggio, retry, annullamento e accesso al dettaglio."
            : "La vista batch è il punto d'accesso canonico al runtime. I documenti restano consultabili nel dominio catasto."
        }
        actions={
          sharedError ? (
            <ElaborazioneNoticeCard compact={embedded} title="Errore archivio" description={sharedError} tone="danger" />
          ) : (
            <ElaborazioneNoticeCard
              compact={embedded}
              title={batchOnlyMode ? "Archivio batch" : "Vista unificata"}
              description={
                batchOnlyMode
                  ? "Questa vista e concentrata solo sui batch del runtime, senza elementi documentali."
                  : "Usa Batch per monitorare lotti e retry; usa Documenti per ricerca, ZIP e apertura viewer."
              }
            />
          )
        }
      >
        {batchOnlyMode ? (
          <div className="grid gap-3 sm:grid-cols-3">
            <ElaborazioneMiniStat compact={embedded} eyebrow="Batch" value={batches.length} description={`${processingCount} in lavorazione · ${failedCount} con errori`} />
            <ElaborazioneMiniStat compact={embedded} eyebrow="Completati" value={completedCount} description="Lotti conclusi disponibili nello storico." tone={completedCount > 0 ? "success" : "default"} />
            <ElaborazioneMiniStat compact={embedded} eyebrow="Falliti" value={failedCount} description="Batch con richieste fallite o errori in corso." tone={failedCount > 0 ? "warning" : "default"} />
          </div>
        ) : (
          <div className="grid gap-3 sm:grid-cols-4">
            <ElaborazioneMiniStat compact={embedded} eyebrow="Documenti" value={documents.length} description="Risultati correnti della ricerca documentale." />
            <ElaborazioneMiniStat compact={embedded} eyebrow="Selezione ZIP" value={selectedDocumentIds.length} description="Documenti pronti per export massivo." tone={selectedDocumentIds.length > 0 ? "success" : "default"} />
            <ElaborazioneMiniStat compact={embedded} eyebrow="Batch" value={batches.length} description={`${processingCount} in lavorazione · ${failedCount} con errori`} />
            <ElaborazioneMiniStat compact={embedded} eyebrow="Completati" value={completedCount} description="Lotti conclusi disponibili nello storico." tone={completedCount > 0 ? "success" : "default"} />
          </div>
        )}
      </ElaborazioneHero>

      {!isolatedView ? (
        <article className="overflow-hidden rounded-[28px] border border-[#d9dfd6] bg-white shadow-panel">
          <ElaborazionePanelHeader
            badge={
              <>
                <RefreshIcon className="h-3.5 w-3.5" />
                Vista archivio
              </>
            }
            title="Scegli la vista di consultazione"
            description="Batch per la parte operativa. Documenti per l'output PDF e la ricerca archivistica."
          />
          <div className="grid gap-4 p-6 md:grid-cols-2">
            <button
              className={`rounded-[24px] border p-5 text-left transition ${activeView === "documents" ? "border-[#1D4E35] bg-[#eef6f0] shadow-sm" : "border-gray-200 bg-white hover:border-gray-300"}`}
              onClick={() =>
                activeView === "documents"
                  ? undefined
                  : openWorkspaceModal(
                      "/catasto/archive?view=documents",
                      "Archivio documenti",
                      "Vista documentale aperta in modale per mantenere il contesto dell'archivio elaborazioni.",
                    )
              }
              type="button"
            >
              <div className="flex items-center gap-3">
                <div className={`rounded-2xl p-3 ${activeView === "documents" ? "bg-[#1D4E35] text-white" : "bg-gray-100 text-gray-700"}`}>
                  <DocumentIcon className="h-5 w-5" />
                </div>
                <div>
                  <p className="text-base font-semibold text-gray-900">Documenti</p>
                  <p className="mt-1 text-sm leading-6 text-gray-600">Ricerca PDF, selezione multipla, ZIP e viewer inline.</p>
                </div>
              </div>
            </button>
            <button
              className={`rounded-[24px] border p-5 text-left transition ${activeView === "batches" ? "border-[#1D4E35] bg-[#eef6f0] shadow-sm" : "border-gray-200 bg-white hover:border-gray-300"}`}
              onClick={() =>
                activeView === "batches"
                  ? undefined
                  : openWorkspaceModal(
                      "/elaborazioni/batches",
                      "Archivio batch",
                      "Vista batch aperta in modale per evitare navigazioni fuori dal workspace corrente.",
                    )
              }
              type="button"
            >
              <div className="flex items-center gap-3">
                <div className={`rounded-2xl p-3 ${activeView === "batches" ? "bg-[#1D4E35] text-white" : "bg-gray-100 text-gray-700"}`}>
                  <RefreshIcon className="h-5 w-5" />
                </div>
                <div>
                  <p className="text-base font-semibold text-gray-900">Batch</p>
                  <p className="mt-1 text-sm leading-6 text-gray-600">Monitoraggio lotti, retry, annullamento e accesso al dettaglio.</p>
                </div>
              </div>
            </button>
          </div>
        </article>
      ) : null}

      {activeView === "batches" ? (
        <article className="overflow-hidden rounded-[28px] border border-[#d9dfd6] bg-white p-0 shadow-panel">
          <ElaborazionePanelHeader
            badge={
              <>
                <RefreshIcon className="h-3.5 w-3.5" />
                Storico batch
              </>
            }
            title="Monitoraggio dei lotti creati nel modulo elaborazioni"
            description="Apri il dettaglio per vedere progress realtime, richieste riga per riga e CAPTCHA manuali."
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
                      <td><ElaborazioneStatusBadge status={batch.status} /></td>
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
                        <button
                          className="font-medium text-[#1D4E35] transition hover:text-[#143726]"
                          onClick={() =>
                            openWorkspaceModal(
                              `/elaborazioni/batches/${batch.id}`,
                              batch.name ?? batch.id,
                              "Dettaglio batch aperto in modale per restare nell'archivio.",
                            )
                          }
                          type="button"
                        >
                          Apri
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </article>
      ) : (
        <>
          <article className="overflow-hidden rounded-[28px] border border-[#d9dfd6] bg-white shadow-panel">
            <ElaborazionePanelHeader
              badge={
                <>
                  <SearchIcon className="h-3.5 w-3.5" />
                  Filtri documenti
                </>
              }
              title="Ricerca per comune, riferimento e periodo"
              description="Combina filtri testuali e temporali per restringere il dataset prima del download o dell'apertura del viewer."
            />
            <div className="p-6">
              <TableFilters>
                <label className="text-sm font-medium text-gray-700">
                  Ricerca libera
                  <input
                    className="form-control mt-1"
                    onChange={(event) => setFilters((current) => ({ ...current, q: event.target.value }))}
                    placeholder="Comune, file, foglio o particella"
                    value={filters.q}
                  />
                </label>
                <label className="text-sm font-medium text-gray-700">
                  Comune
                  <select
                    className="form-control mt-1"
                    onChange={(event) => setFilters((current) => ({ ...current, comune: event.target.value }))}
                    value={filters.comune}
                  >
                    <option value="">Tutti i comuni</option>
                    {comuni.map((comune) => (
                      <option key={comune.id} value={comune.nome}>
                        {comune.nome}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="text-sm font-medium text-gray-700">
                  Foglio
                  <input
                    className="form-control mt-1"
                    inputMode="numeric"
                    onChange={(event) => setFilters((current) => ({ ...current, foglio: event.target.value }))}
                    placeholder="Es. 5"
                    value={filters.foglio}
                  />
                </label>
                <label className="text-sm font-medium text-gray-700">
                  Particella
                  <input
                    className="form-control mt-1"
                    inputMode="numeric"
                    onChange={(event) => setFilters((current) => ({ ...current, particella: event.target.value }))}
                    placeholder="Es. 120"
                    value={filters.particella}
                  />
                </label>
                <label className="text-sm font-medium text-gray-700">
                  Data da
                  <input
                    className="form-control mt-1"
                    onChange={(event) => setFilters((current) => ({ ...current, createdFrom: event.target.value }))}
                    type="date"
                    value={filters.createdFrom}
                  />
                </label>
                <label className="text-sm font-medium text-gray-700">
                  Data a
                  <input
                    className="form-control mt-1"
                    onChange={(event) => setFilters((current) => ({ ...current, createdTo: event.target.value }))}
                    type="date"
                    value={filters.createdTo}
                  />
                </label>
              </TableFilters>
              <div className="mt-4 flex flex-wrap items-center gap-3">
                <button className="btn-primary" disabled={documentsBusy} onClick={() => void loadDocuments(filters)} type="button">
                  {documentsBusy ? "Ricerca..." : "Applica filtri"}
                </button>
                <button
                  className="btn-secondary"
                  disabled={documentsBusy}
                  onClick={() => {
                    setFilters(EMPTY_FILTERS);
                    void loadDocuments(EMPTY_FILTERS);
                  }}
                  type="button"
                >
                  Reset
                </button>
                <button
                  className="btn-secondary"
                  disabled={zipBusy || selectedDocumentIds.length === 0}
                  onClick={() => void handleDownloadSelected()}
                  type="button"
                >
                  {zipBusy ? "Preparazione ZIP..." : `Scarica selezione (${selectedDocumentIds.length})`}
                </button>
              </div>
            </div>
          </article>

          <article className="overflow-hidden rounded-[28px] border border-[#d9dfd6] bg-white p-0 shadow-panel">
            <ElaborazionePanelHeader
              badge={
                <>
                  <DocumentIcon className="h-3.5 w-3.5" />
                  Archivio documenti
                </>
              }
              title="Tabella documentale con apertura viewer e download inline"
              description="Le selezioni vengono azzerate a ogni nuova ricerca per evitare ZIP incoerenti."
            />
            <div className="p-5">
              <DataTable
                columns={documentColumns}
                data={documents}
                emptyTitle="Nessun documento trovato"
                emptyDescription="Non ci sono visure che corrispondono ai filtri correnti."
                initialPageSize={12}
              />
            </div>
          </article>
        </>
      )}
      <ElaborazioneWorkspaceModal
        description={modalState?.description}
        href={modalState?.href ?? null}
        onClose={() => setModalState(null)}
        open={modalState != null}
        title={modalState?.title ?? "Workspace"}
      />
    </>
  );

  if (embedded) {
    return <div className="space-y-6">{content}</div>;
  }

  return (
    <ProtectedPage
      title="Elaborazioni"
      description="Monitoraggio dei batch e accesso ai documenti prodotti dal runtime."
      breadcrumb="Elaborazioni / Batch"
    >
      {content}
    </ProtectedPage>
  );
}
