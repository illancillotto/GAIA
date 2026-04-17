"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { CatastoArchiveWorkspaceContent } from "@/components/catasto/archive-workspace";
import { CatastoDocumentDetailWorkspace } from "@/components/catasto/document-detail-workspace";
import { ElaborazioneArchiveWorkspaceContent } from "@/components/elaborazioni/archive-workspace";
import { ElaborazioneBatchDetailWorkspace } from "@/components/elaborazioni/batch-detail-workspace";
import { ElaborazioniCapacitasWorkspace } from "@/components/elaborazioni/capacitas-workspace";
import { ElaborazioniBonificaSyncWorkspace } from "@/components/elaborazioni/bonifica-sync-workspace";
import { ElaborazioneRequestWorkspace } from "@/components/elaborazioni/request-workspace";
import { ElaborazioniSettingsWorkspace } from "@/components/elaborazioni/settings-workspace";

type ElaborazioneWorkspaceModalProps = {
  open: boolean;
  href: string | null;
  title: string;
  description?: string | null;
  onClose: () => void;
};

export function ElaborazioneWorkspaceModal({
  open,
  href,
  title,
  description,
  onClose,
}: ElaborazioneWorkspaceModalProps) {
  const [isFrameLoading, setIsFrameLoading] = useState(true);
  const [currentHref, setCurrentHref] = useState<string | null>(href);

  useEffect(() => {
    if (!open) {
      return;
    }

    setCurrentHref(href);
    setIsFrameLoading(true);

    function handleKeyDown(event: KeyboardEvent): void {
      if (event.key === "Escape") {
        onClose();
      }
    }

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", handleKeyDown);

    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [open, href, onClose]);

  if (!open || !currentHref) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-[70] flex items-center justify-center bg-black/45 px-3 py-5 backdrop-blur-sm xl:px-5">
      <div className="flex max-h-[95vh] w-full max-w-[min(1600px,98vw)] flex-col overflow-hidden rounded-[28px] border border-gray-200 bg-white shadow-[0_30px_90px_rgba(15,23,42,0.24)]">
        <div className="flex items-center justify-between gap-4 border-b border-gray-100 bg-white px-6 py-3.5">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#1D4E35]">Workspace rapido</p>
            <h2 className="mt-1.5 text-lg font-semibold text-gray-900">{title}</h2>
            {description ? <p className="mt-1 text-sm text-gray-500">{description}</p> : null}
          </div>
          <div className="flex items-center gap-3">
            <Link className="btn-secondary" href={currentHref} target="_blank" rel="noreferrer">
              Apri pagina
            </Link>
            <button className="btn-secondary" type="button" onClick={onClose}>
              Chiudi
            </button>
          </div>
        </div>

        <div className="relative min-h-[70vh] flex-1 overflow-y-auto bg-[#f4f7f5] px-4 py-5 xl:px-5">
          <NativeWorkspaceRenderer
            href={currentHref}
            onNavigate={setCurrentHref}
            onRendered={() => setIsFrameLoading(false)}
          />
          {isFrameLoading ? (
            <div className="absolute inset-0 flex items-center justify-center bg-[#f4f7f5]">
              <div className="rounded-2xl border border-gray-200 bg-white px-5 py-4 text-sm text-gray-500 shadow-sm">
                Caricamento workspace.
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}

function NativeWorkspaceRenderer({
  href,
  onRendered,
  onNavigate,
}: {
  href: string;
  onRendered: () => void;
  onNavigate: (href: string) => void;
}) {
  useEffect(() => {
    onRendered();
  }, [href, onRendered]);

  if (href === "/elaborazioni/new-single") {
    return <ElaborazioneRequestWorkspace embedded initialMode="single" onOpenBatch={(batchId) => onNavigate(`/elaborazioni/batches/${batchId}`)} />;
  }

  if (href === "/elaborazioni/new-batch") {
    return <ElaborazioneRequestWorkspace embedded initialMode="batch" onOpenBatch={(batchId) => onNavigate(`/elaborazioni/batches/${batchId}`)} />;
  }

  if (href === "/elaborazioni/batches") {
    return <ElaborazioneArchiveWorkspaceContent embedded initialView="batches" isolatedView />;
  }

  if (href === "/elaborazioni/capacitas") {
    return <ElaborazioniCapacitasWorkspace embedded />;
  }

  if (href === "/elaborazioni/settings") {
    return <ElaborazioniSettingsWorkspace embedded />;
  }

  if (href === "/elaborazioni/bonifica") {
    return <ElaborazioniBonificaSyncWorkspace embedded />;
  }

  if (href === "/catasto/archive?view=documents") {
    return <CatastoArchiveWorkspaceContent embedded initialView="documents" isolatedView />;
  }

  if (href.startsWith("/elaborazioni/batches/")) {
    const batchId = href.split("/").filter(Boolean).at(-1);
    if (batchId) {
      return <ElaborazioneBatchDetailWorkspace batchId={batchId} embedded />;
    }
  }

  if (href.startsWith("/catasto/documents/")) {
    const documentId = href.split("/").filter(Boolean).at(-1);
    if (documentId) {
      return <CatastoDocumentDetailWorkspace documentId={documentId} embedded />;
    }
  }

  return (
    <iframe
      className="h-full min-h-[70vh] w-full border-0 bg-white"
      onLoad={onRendered}
      src={href}
      title={href}
    />
  );
}
