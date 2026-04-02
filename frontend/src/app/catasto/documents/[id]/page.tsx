"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";

import { ProtectedPage } from "@/components/app/protected-page";
import { CatastoHero, CatastoMiniStat, CatastoNoticeCard, CatastoPanelHeader } from "@/components/catasto/module-chrome";
import { DocumentIcon, FolderIcon } from "@/components/ui/icons";
import { downloadCatastoDocumentBlob, getCatastoDocument } from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import { formatDateTime } from "@/lib/presentation";
import type { CatastoDocument } from "@/types/api";

function triggerDownload(url: string, filename: string): void {
  const anchor = window.document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
}

export default function CatastoDocumentDetailPage() {
  const params = useParams<{ id: string }>();
  const documentId = params.id;
  const [documentItem, setDocumentItem] = useState<CatastoDocument | null>(null);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [downloadBusy, setDownloadBusy] = useState(false);

  useEffect(() => {
    if (!documentId) return;

    let cancelled = false;

    async function loadDocument(): Promise<void> {
      const token = getStoredAccessToken();
      if (!token) return;

      try {
        const [metadata, blob] = await Promise.all([
          getCatastoDocument(token, documentId),
          downloadCatastoDocumentBlob(token, documentId),
        ]);
        const nextPdfUrl = URL.createObjectURL(blob);

        if (cancelled) {
          URL.revokeObjectURL(nextPdfUrl);
          return;
        }

        setDocumentItem(metadata);
        setPdfUrl((current) => {
          if (current) {
            URL.revokeObjectURL(current);
          }
          return nextPdfUrl;
        });
        setError(null);
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : "Errore caricamento documento");
        }
      }
    }

    void loadDocument();

    return () => {
      cancelled = true;
    };
  }, [documentId]);

  useEffect(() => {
    return () => {
      if (pdfUrl) {
        URL.revokeObjectURL(pdfUrl);
      }
    };
  }, [pdfUrl]);

  async function handleDownload(): Promise<void> {
    const token = getStoredAccessToken();
    if (!token || !documentItem) return;

    setDownloadBusy(true);
    try {
      const blob = await downloadCatastoDocumentBlob(token, documentItem.id);
      const url = URL.createObjectURL(blob);
      triggerDownload(url, documentItem.filename);
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
      setError(null);
    } catch (downloadError) {
      setError(downloadError instanceof Error ? downloadError.message : "Errore download documento");
    } finally {
      setDownloadBusy(false);
    }
  }

  return (
    <ProtectedPage
      title="Dettaglio documento"
      description="Metadati della visura scaricata e visualizzazione PDF inline."
      breadcrumb="Catasto / Documento"
    >
      <CatastoHero
        badge={
          <>
            <DocumentIcon className="h-3.5 w-3.5" />
            Viewer documento
          </>
        }
        title={documentItem?.filename ?? "Visualizzazione PDF della visura archiviata"}
        description="Questa pagina accorpa metadati catastali e preview inline del PDF, così il controllo documentale resta nello stesso contesto operativo."
        actions={
          error ? (
            <CatastoNoticeCard title="Errore documento" description={error} tone="danger" />
          ) : (
            <CatastoNoticeCard
              title="PDF inline"
              description="Il file viene scaricato dal backend, convertito in blob locale e mostrato direttamente nel viewer integrato."
            />
          )
        }
      >
        <div className="grid gap-3 sm:grid-cols-3">
          <CatastoMiniStat eyebrow="Comune" value={documentItem?.comune ?? "—"} description="Localizzazione della visura archiviata." />
          <CatastoMiniStat eyebrow="Tipo visura" value={documentItem?.tipo_visura ?? "—"} description="Modalità di estrazione del documento." />
          <CatastoMiniStat eyebrow="Batch sorgente" value={documentItem?.batch_id ? "Presente" : "Assente"} description="Collegamento al lotto di origine quando disponibile." tone={documentItem?.batch_id ? "success" : "default"} />
        </div>
      </CatastoHero>

      {documentItem ? (
        <>
          <article className="overflow-hidden rounded-[28px] border border-[#d9dfd6] bg-white shadow-panel">
            <CatastoPanelHeader
              badge={
                <>
                  <FolderIcon className="h-3.5 w-3.5" />
                  Metadati documento
                </>
              }
              title="Riferimenti catastali e azioni documento"
              description="Scarica il PDF oppure torna al batch che ha prodotto questa visura."
            />
            <div className="p-6">
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
              <div className="rounded-lg border border-gray-100 bg-gray-50 p-4">
                <p className="label-caption">Comune</p>
                <p className="mt-2 text-sm font-medium text-gray-900">{documentItem.comune}</p>
              </div>
              <div className="rounded-lg border border-gray-100 bg-gray-50 p-4">
                <p className="label-caption">Riferimento</p>
                <p className="mt-2 text-sm font-medium text-gray-900">
                  Fg.{documentItem.foglio} Part.{documentItem.particella}
                  {documentItem.subalterno ? ` Sub.${documentItem.subalterno}` : ""}
                </p>
              </div>
              <div className="rounded-lg border border-gray-100 bg-gray-50 p-4">
                <p className="label-caption">Tipo visura</p>
                <p className="mt-2 text-sm font-medium text-gray-900">{documentItem.tipo_visura}</p>
              </div>
              <div className="rounded-lg border border-gray-100 bg-gray-50 p-4">
                <p className="label-caption">Creato</p>
                <p className="mt-2 text-sm font-medium text-gray-900">{formatDateTime(documentItem.created_at)}</p>
              </div>
            </div>

            <div className="mt-5 flex flex-wrap items-center gap-3">
              <button className="btn-primary" disabled={downloadBusy} onClick={() => void handleDownload()} type="button">
                {downloadBusy ? "Download..." : "Scarica PDF"}
              </button>
              {documentItem.batch_id ? (
                <Link className="btn-secondary" href={`/catasto/batches/${documentItem.batch_id}`}>
                  Apri batch
                </Link>
              ) : null}
              <Link className="text-sm font-medium text-[#1D4E35]" href="/catasto/archive?view=documents">
                Torna all&apos;archivio
              </Link>
            </div>
            </div>
          </article>

          <article className="overflow-hidden rounded-[28px] border border-[#d9dfd6] bg-white p-0 shadow-panel">
            <CatastoPanelHeader
              badge={
                <>
                  <DocumentIcon className="h-3.5 w-3.5" />
                  PDF viewer
                </>
              }
              title={documentItem.filename}
              description="Viewer inline del blob PDF restituito dal backend."
            />
            {pdfUrl ? (
              <iframe className="h-[820px] w-full bg-gray-50" src={pdfUrl} title={`Viewer PDF ${documentItem.filename}`} />
            ) : (
              <div className="p-5 text-sm text-gray-500">Caricamento PDF in corso.</div>
            )}
          </article>
        </>
      ) : (
        <article className="panel-card">
          <p className="section-copy">Caricamento metadati documento in corso.</p>
        </article>
      )}
    </ProtectedPage>
  );
}
