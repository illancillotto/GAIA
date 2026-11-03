"use client";
import { useEffect, useState, type RefObject } from "react";
import { communications, loadSnapshot } from "@/lib/communications-api";
import type { Attachment } from "@/types/communications";
import { renderSnapshot, type RenderSession } from "./pdf-renderer";

export type PdfViewerProps = {
  token: string; messageId: string; version: number; part: Attachment; onRendered: (ok: boolean) => void;
  canReview: boolean; pixelBudget: number;
};

export function usePdfSnapshot(props: PdfViewerProps, host: RefObject<HTMLDivElement>, zoom: number) {
  const { token, messageId, version, part, onRendered, canReview, pixelBudget } = props;
  const [resource, setResource] = useState({ url: "", error: "", loading: true });
  useEffect(() => {
    const abort = new AbortController();
    const session: RenderSession = { disposed: false };
    let blobUrl = "";
    onRendered(false); setResource({ url: "", error: "", loading: true });
    async function render() {
      try {
        if (part.mime_type !== "application/pdf") throw new Error("Allegato non visualizzabile come PDF");
        const { content, reviewId } = await loadSnapshot(token, messageId, part, abort.signal);
        if (session.disposed || !host.current) return;
        blobUrl = URL.createObjectURL(new Blob([content], { type: "application/pdf" }));
        await renderSnapshot(content, part, host.current, { zoom, pixelBudget, total: part.pages }, session);
        if (session.disposed) return;
        if (canReview) await communications(token, `/messages/${messageId}/attachments/${part.id}/rendered`, {
          expected_version: version, review_id: reviewId, pages: part.pages, sha256: part.sha256,
        });
        if (!session.disposed) { onRendered(true); setResource({ url: blobUrl, error: "", loading: false }); }
      } catch (error) {
        if (!session.disposed) { onRendered(false); setResource({ url: "", error: error instanceof Error ? error.message : "Rendering PDF fallito", loading: false }); }
      }
    }
    void render();
    return () => { session.disposed = true; abort.abort(); session.task?.cancel(); void session.document?.destroy(); if (blobUrl) URL.revokeObjectURL(blobUrl); };
  }, [token, messageId, version, part, zoom, onRendered, canReview, pixelBudget, host]);
  return { resource, setResource };
}
