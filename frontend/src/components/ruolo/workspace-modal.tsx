"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

type RuoloWorkspaceModalProps = {
  open: boolean;
  href: string | null;
  title: string;
  description?: string | null;
  onClose: () => void;
};

function toEmbeddedPath(path: string): string {
  if (typeof window === "undefined") {
    return path.includes("?") ? `${path}&embedded=1` : `${path}?embedded=1`;
  }
  const url = new URL(path, window.location.origin);
  url.searchParams.set("embedded", "1");
  return `${url.pathname}${url.search}${url.hash}`;
}

export function RuoloWorkspaceModal({
  open,
  href,
  title,
  description,
  onClose,
}: RuoloWorkspaceModalProps) {
  const [isFrameLoading, setIsFrameLoading] = useState(true);

  const frameSrc = open && href ? toEmbeddedPath(href) : null;

  useEffect(() => {
    if (frameSrc) {
      setIsFrameLoading(true);
    }
  }, [frameSrc]);

  useEffect(() => {
    if (!open || !href) {
      return;
    }

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

  if (!open || !href || !frameSrc) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-[70] flex items-center justify-center bg-black/45 px-4 py-6 backdrop-blur-sm">
      <div className="flex max-h-[94vh] w-full max-w-[1400px] flex-col overflow-hidden rounded-[28px] border border-gray-200 bg-white shadow-[0_30px_90px_rgba(15,23,42,0.24)]">
        <div className="flex items-start justify-between gap-4 border-b border-gray-100 bg-white px-6 py-5">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#1D4E35]">Workspace rapido</p>
            <h2 className="mt-2 text-2xl font-semibold text-gray-900">{title}</h2>
            <p className="mt-1 text-sm text-gray-500">
              {description ?? "Flusso aperto in modale per non perdere il contesto della dashboard."}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <Link className="btn-secondary" href={href} target="_blank" rel="noreferrer">
              Apri pagina
            </Link>
            <button className="btn-secondary" type="button" onClick={onClose}>
              Chiudi
            </button>
          </div>
        </div>

        <div className="relative min-h-[70vh] flex-1 overflow-hidden bg-[#f4f7f5] px-6 py-6">
          <iframe
            key={frameSrc}
            className="h-full min-h-[calc(70vh-3rem)] w-full rounded-2xl border border-gray-200/80 bg-white shadow-sm"
            onLoad={() => setIsFrameLoading(false)}
            src={frameSrc}
            title={title}
          />
          {isFrameLoading ? (
            <div className="absolute inset-0 flex items-center justify-center bg-[#f4f7f5]/90 px-6 py-6">
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
