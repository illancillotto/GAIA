"use client";

import Image from "next/image";

type OperazioniAttachmentPreviewDialogProps = {
  open: boolean;
  title: string;
  url: string | null;
  mimeType: string | null;
  textContent?: string | null;
  onClose: () => void;
};

export function OperazioniAttachmentPreviewDialog({
  open,
  title,
  url,
  mimeType,
  textContent,
  onClose,
}: OperazioniAttachmentPreviewDialogProps) {
  if (!open || (!url && !textContent)) {
    return null;
  }

  const isImage = Boolean(mimeType?.startsWith("image/"));
  const isPdf = mimeType === "application/pdf";
  const isAudio = Boolean(mimeType?.startsWith("audio/"));
  const isVideo = Boolean(mimeType?.startsWith("video/"));
  const isText =
    textContent != null &&
    (Boolean(mimeType?.startsWith("text/")) ||
      mimeType === "application/json" ||
      mimeType === "application/ld+json" ||
      mimeType === "application/xml");
  const mediaUrl = url ?? undefined;

  return (
    <div className="fixed inset-0 z-[120] flex items-center justify-center bg-black/55 p-4" role="dialog" aria-modal="true">
      <div className="flex h-[85vh] w-full max-w-5xl flex-col overflow-hidden rounded-[28px] border border-[#d9dfd6] bg-white shadow-2xl">
        <div className="flex items-center justify-between gap-4 border-b border-[#edf1eb] px-6 py-4">
          <div className="min-w-0">
            <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[#667267]">Anteprima allegato</p>
            <p className="mt-1 truncate text-sm font-semibold text-gray-900">{title}</p>
          </div>
          <button type="button" className="btn-secondary" onClick={onClose}>
            Chiudi
          </button>
        </div>
        <div className="min-h-0 flex-1 overflow-auto bg-[#f6f8f5] p-4">
          {isPdf && mediaUrl ? <iframe className="h-full min-h-[70vh] w-full rounded-2xl border border-[#d9dfd6] bg-white" src={mediaUrl} title={title} /> : null}
          {isImage && mediaUrl ? (
            <div className="flex h-full min-h-[70vh] items-center justify-center rounded-2xl border border-[#d9dfd6] bg-white p-4">
              <div className="relative h-full min-h-[60vh] w-full">
                <Image src={mediaUrl} alt={title} fill unoptimized className="object-contain" sizes="100vw" />
              </div>
            </div>
          ) : null}
          {isAudio && mediaUrl ? (
            <div className="flex h-full min-h-[24rem] items-center justify-center rounded-2xl border border-[#d9dfd6] bg-white p-6">
              <audio controls className="w-full max-w-2xl" src={mediaUrl}>
                Il browser non supporta la riproduzione audio.
              </audio>
            </div>
          ) : null}
          {isVideo && mediaUrl ? (
            <div className="flex h-full min-h-[24rem] items-center justify-center rounded-2xl border border-[#d9dfd6] bg-white p-4">
              <video controls className="max-h-full max-w-full rounded-xl" src={mediaUrl}>
                Il browser non supporta la riproduzione video.
              </video>
            </div>
          ) : null}
          {isText ? (
            <div className="rounded-2xl border border-[#d9dfd6] bg-[#fcfdfb] p-4">
              <pre className="overflow-auto whitespace-pre-wrap break-words rounded-xl bg-white p-4 font-mono text-[13px] leading-6 text-[#243127]">
                {textContent}
              </pre>
            </div>
          ) : null}
          {!isPdf && !isImage && !isAudio && !isVideo && !isText ? (
            <div className="flex h-full min-h-[24rem] items-center justify-center rounded-2xl border border-dashed border-[#d9dfd6] bg-white p-6 text-center">
              <div>
                <p className="text-sm font-semibold text-gray-900">Anteprima non disponibile</p>
                <p className="mt-2 text-sm text-gray-500">
                  Questo formato non è visualizzabile inline. Usa il download dalla scheda dettaglio.
                </p>
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
