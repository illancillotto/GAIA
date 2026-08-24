"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { ParticellaDetailDialog } from "@/components/catasto/anagrafica/ParticellaDetailDialog";
import { ProtectedPage } from "@/components/app/protected-page";
import { CatastoHero, CatastoMiniStat, CatastoNoticeCard, CatastoPanelHeader } from "@/components/catasto/module-chrome";
import { DocumentIcon, FolderIcon } from "@/components/ui/icons";
import { downloadCatastoDocumentBlob, getCatastoDocument } from "@/lib/api";
import { catastoListParticelle } from "@/lib/api/catasto";
import { getStoredAccessToken } from "@/lib/auth";
import { formatDateTime } from "@/lib/presentation";
import type { CatastoDocument } from "@/types/api";
import type { CatAnagraficaMatch, CatParticella } from "@/types/catasto";

function triggerDownload(url: string, filename: string): void {
  const anchor = window.document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
}

function documentReferenceLabel(documentItem: Pick<CatastoDocument, "foglio" | "particella" | "subalterno">): string {
  const foglio = documentItem.foglio ?? "—";
  const particella = documentItem.particella ?? "—";
  return `Fg.${foglio} Part.${particella}${documentItem.subalterno ? ` Sub.${documentItem.subalterno}` : ""}`;
}

function canResolveParticella(documentItem: CatastoDocument): boolean {
  return Boolean(documentItem.comune && documentItem.foglio && documentItem.particella);
}

function normalizeCatastoValue(value: string | null | undefined): string {
  return (value ?? "").trim().toLocaleLowerCase("it-IT");
}

function matchesDocumentReference(documentItem: CatastoDocument, particella: CatParticella): boolean {
  const sameFoglio = normalizeCatastoValue(particella.foglio) === normalizeCatastoValue(documentItem.foglio);
  const sameParticella = normalizeCatastoValue(particella.particella) === normalizeCatastoValue(documentItem.particella);
  const documentSubalterno = normalizeCatastoValue(documentItem.subalterno);
  const sameSubalterno = !documentSubalterno || normalizeCatastoValue(particella.subalterno) === documentSubalterno;
  return sameFoglio && sameParticella && sameSubalterno;
}

function particellaToMatch(particella: CatParticella): CatAnagraficaMatch {
  return {
    particella_id: particella.id,
    unit_id: null,
    comune_id: particella.comune_id,
    comune: particella.nome_comune,
    cod_comune_capacitas: particella.cod_comune_capacitas,
    codice_catastale: particella.codice_catastale,
    foglio: particella.foglio,
    particella: particella.particella,
    subalterno: particella.subalterno,
    num_distretto: particella.num_distretto,
    nome_distretto: particella.nome_distretto,
    superficie_mq: particella.superficie_mq,
    superficie_grafica_mq: particella.superficie_grafica_mq,
    presente_in_catasto_consorzio: false,
    utenza_latest: null,
    cert_com: null,
    cert_pvc: null,
    cert_fra: null,
    cert_ccs: null,
    stato_ruolo: null,
    stato_cnc: null,
    intestatari: [],
    anomalie_count: 0,
    anomalie_top: [],
    note: null,
  };
}

function CatastoDocumentHeroSection({
  compact,
  documentItem,
  error,
}: {
  compact: boolean;
  documentItem: CatastoDocument | null;
  error: string | null;
}) {
  return (
    <CatastoHero
      compact={compact}
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
          <CatastoNoticeCard compact={compact} title="Errore documento" description={error} tone="danger" />
        ) : (
          <CatastoNoticeCard
            compact={compact}
            title="PDF inline"
            description="Il file viene scaricato dal backend, convertito in blob locale e mostrato direttamente nel viewer integrato."
          />
        )
      }
    >
      <div className="grid gap-3 sm:grid-cols-3">
        <CatastoMiniStat compact={compact} eyebrow="Comune" value={documentItem?.comune ?? "—"} description="Localizzazione della visura archiviata." />
        <CatastoMiniStat compact={compact} eyebrow="Tipo visura" value={documentItem?.tipo_visura ?? "—"} description="Modalità di estrazione del documento." />
        <CatastoMiniStat compact={compact} eyebrow="Batch sorgente" value={documentItem?.batch_id ? "Presente" : "Assente"} description="Collegamento al lotto di origine quando disponibile." tone={documentItem?.batch_id ? "success" : "default"} />
      </div>
    </CatastoHero>
  );
}

function CatastoDocumentMetadataPanel({
  documentItem,
  downloadBusy,
  onDownload,
  onOpenParticella,
  particellaLookupBusy,
  particellaLookupMessage,
}: {
  documentItem: CatastoDocument;
  downloadBusy: boolean;
  onDownload: () => void;
  onOpenParticella: () => void;
  particellaLookupBusy: boolean;
  particellaLookupMessage: string | null;
}) {
  return (
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
            <button
              type="button"
              className="mt-2 text-left text-sm font-semibold text-[#1D4E35] underline decoration-[#9dbd9f] underline-offset-4 transition hover:text-[#153926] disabled:cursor-not-allowed disabled:text-gray-500 disabled:no-underline"
              disabled={particellaLookupBusy || !canResolveParticella(documentItem)}
              onClick={onOpenParticella}
              title="Apri dettaglio particella"
            >
              {particellaLookupBusy ? "Apertura particella..." : documentReferenceLabel(documentItem)}
            </button>
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
          <button className="btn-primary" disabled={downloadBusy} onClick={onDownload} type="button">
            {downloadBusy ? "Download..." : "Scarica PDF"}
          </button>
          {documentItem.batch_id ? (
            <Link className="btn-secondary" href={`/elaborazioni/batches/${documentItem.batch_id}`}>
              Apri batch
            </Link>
          ) : null}
          <Link className="text-sm font-medium text-[#1D4E35]" href="/catasto/archive?view=documents">
            Torna all&apos;archivio
          </Link>
        </div>
        {particellaLookupMessage ? (
          <p className="mt-3 text-sm font-medium text-amber-700">{particellaLookupMessage}</p>
        ) : null}
      </div>
    </article>
  );
}

function CatastoDocumentPdfPanel({
  documentItem,
  pdfUrl,
}: {
  documentItem: CatastoDocument;
  pdfUrl: string | null;
}) {
  return (
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
  );
}

function CatastoDocumentLoadingPanel() {
  return (
    <article className="panel-card">
      <p className="section-copy">Caricamento metadati documento in corso.</p>
    </article>
  );
}

function useCatastoDocumentPreview(documentId: string) {
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

  async function downloadDocument(): Promise<void> {
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

  return { documentItem, downloadBusy, downloadDocument, error, pdfUrl };
}

function useParticellaLookup(documentItem: CatastoDocument | null) {
  const [particellaLookupBusy, setParticellaLookupBusy] = useState(false);
  const [particellaLookupMessage, setParticellaLookupMessage] = useState<string | null>(null);
  const [selectedParticella, setSelectedParticella] = useState<CatParticella | null>(null);

  async function openParticella(): Promise<void> {
    const token = getStoredAccessToken();
    const comune = documentItem?.comune;
    const foglio = documentItem?.foglio;
    const particella = documentItem?.particella;
    if (!token || !documentItem || !comune || !foglio || !particella) {
      setParticellaLookupMessage("Riferimento catastale incompleto: impossibile aprire il dettaglio particella.");
      return;
    }

    setParticellaLookupBusy(true);
    setParticellaLookupMessage(null);
    try {
      const candidates = await catastoListParticelle(token, {
        nomeComune: comune,
        foglio,
        particella,
        limit: 10,
      });
      const exactMatches = candidates.filter((candidate) => matchesDocumentReference(documentItem, candidate));
      if (exactMatches.length === 1) {
        setSelectedParticella(exactMatches[0]);
        return;
      }
      setParticellaLookupMessage(
        exactMatches.length === 0
          ? "Nessuna particella corrente trovata per questo riferimento."
          : "Riferimento ambiguo: apri l'elenco particelle per scegliere il dettaglio corretto.",
      );
    } catch (lookupError) {
      setParticellaLookupMessage(lookupError instanceof Error ? lookupError.message : "Errore apertura dettaglio particella.");
    } finally {
      setParticellaLookupBusy(false);
    }
  }

  return {
    openParticella,
    particellaLookupBusy,
    particellaLookupMessage,
    selectedParticella,
    setSelectedParticella,
  };
}

export function CatastoDocumentDetailWorkspace({
  documentId,
  embedded = false,
}: {
  documentId: string;
  embedded?: boolean;
}) {
  const { documentItem, downloadBusy, downloadDocument, error, pdfUrl } = useCatastoDocumentPreview(documentId);
  const {
    openParticella,
    particellaLookupBusy,
    particellaLookupMessage,
    selectedParticella,
    setSelectedParticella,
  } = useParticellaLookup(documentItem);

  const content = (
    <>
      <CatastoDocumentHeroSection compact={embedded} documentItem={documentItem} error={error} />

      {documentItem ? (
        <>
          <CatastoDocumentMetadataPanel
            documentItem={documentItem}
            downloadBusy={downloadBusy}
            onDownload={() => void downloadDocument()}
            onOpenParticella={() => void openParticella()}
            particellaLookupBusy={particellaLookupBusy}
            particellaLookupMessage={particellaLookupMessage}
          />
          <CatastoDocumentPdfPanel documentItem={documentItem} pdfUrl={pdfUrl} />
        </>
      ) : (
        <CatastoDocumentLoadingPanel />
      )}
      <ParticellaDetailDialog
        open={selectedParticella !== null}
        match={selectedParticella ? particellaToMatch(selectedParticella) : null}
        onClose={() => setSelectedParticella(null)}
      />
    </>
  );

  if (embedded) {
    return <div className="space-y-6">{content}</div>;
  }

  return (
    <ProtectedPage
      title="Dettaglio documento"
      description="Metadati della visura scaricata e visualizzazione PDF inline."
      breadcrumb="Catasto / Documento"
    >
      {content}
    </ProtectedPage>
  );
}
