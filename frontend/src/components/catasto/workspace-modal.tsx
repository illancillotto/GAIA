"use client";

import { useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";

import { CatastoDistrettoPreviewContent } from "@/components/catasto/distretti/distretto-preview-content";

type CatastoWorkspaceModalProps = {
  open: boolean;
  href: string | null;
  title: string;
  description?: string | null;
  children?: ReactNode;
  onClose: () => void;
};

function toEmbeddedPath(path: string): string {
  /* v8 ignore next 3 -- Next.js renders this client component in browser contexts. */
  if (typeof window === "undefined") {
    return path.includes("?") ? `${path}&embedded=1` : `${path}?embedded=1`;
  }
  const url = new URL(path, window.location.origin);
  url.searchParams.set("embedded", "1");
  return `${url.pathname}${url.search}${url.hash}`;
}

function resolveDistrettoPreviewPayload(
  href: string | null,
  title: string,
): { distrettoId: string; numDistretto: string | null; anno: number | null } | null {
  if (!href) {
    return null;
  }

  const [pathPart, queryString = ""] = href.split("?");
  const match = pathPart.match(/^\/catasto\/distretti\/([^/?#]+)$/);
  if (!match) {
    return null;
  }

  const titleMatch = title.match(/Distretto\s+(.+)$/i);
  const params = new URLSearchParams(queryString);
  const annoValue = params.get("anno");
  const parsedAnno = annoValue ? Number(annoValue) : null;

  return {
    distrettoId: match[1],
    numDistretto: titleMatch?.[1]?.trim() ?? null,
    anno: Number.isFinite(parsedAnno) ? parsedAnno : null,
  };
}

export function CatastoWorkspaceModal({
  open,
  href,
  title,
  description,
  children,
  onClose,
}: CatastoWorkspaceModalProps) {
  const [isFrameLoading, setIsFrameLoading] = useState(true);
  const iframeRef = useRef<HTMLIFrameElement | null>(null);

  const frameSrc = open && href ? toEmbeddedPath(href) : null;
  const distrettoPreview = !children ? resolveDistrettoPreviewPayload(href, title) : null;

  function handleBack(): void {
    iframeRef.current?.contentWindow?.history.back();
  }

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
            <button className="btn-secondary" type="button" onClick={handleBack}>
              Indietro
            </button>
            <button className="btn-secondary" type="button" onClick={onClose}>
              Chiudi
            </button>
          </div>
        </div>

        <div className="relative min-h-[70vh] flex-1 overflow-y-auto bg-[#f4f7f5] px-6 py-6">
          {children ? <div className="mb-5">{children}</div> : null}
          {!children && distrettoPreview ? (
            <div className="mb-5">
              <CatastoDistrettoPreviewContent
                open={open}
                distrettoId={distrettoPreview.distrettoId}
                numDistretto={distrettoPreview.numDistretto}
                anno={distrettoPreview.anno}
              />
            </div>
          ) : null}
          <div className="relative">
            <iframe
              key={frameSrc}
              ref={iframeRef}
              className="h-full min-h-[calc(70vh-3rem)] w-full rounded-2xl border border-gray-200/80 bg-white shadow-sm"
              onLoad={() => setIsFrameLoading(false)}
              src={frameSrc}
              title={title}
            />
            {isFrameLoading ? (
              <div className="absolute inset-0 flex items-center justify-center rounded-2xl bg-[#f4f7f5]/90 px-6 py-6">
                <div className="rounded-2xl border border-gray-200 bg-white px-5 py-4 text-sm text-gray-500 shadow-sm">
                  Caricamento workspace.
                </div>
              </div>
            ) : null}
          </div>
        </div>
      </div>
    </div>
  );
}
