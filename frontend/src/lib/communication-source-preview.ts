import { sha256 as digest } from "@noble/hashes/sha2.js";
import { bytesToHex } from "@noble/hashes/utils.js";
import { getApiBaseUrl } from "@/lib/api";
import type { Attachment } from "@/types/communications";

export type SourceSnapshot = { content: ArrayBuffer; part: Attachment };

export async function loadSourcePreview(token: string, sourceId: string, signal: AbortSignal): Promise<SourceSnapshot> {
  const response = await fetch(`${getApiBaseUrl()}/communications/ruolo/candidates/${sourceId}/preview`, {
    headers: { Authorization: `Bearer ${token}` }, cache: "no-store", signal,
  });
  if (!response.ok) throw new Error("PDF dell'avviso non disponibile o accesso negato");
  const content = await response.arrayBuffer();
  const sha256 = response.headers.get("X-Content-SHA256");
  const pages = Number(response.headers.get("X-PDF-Pages"));
  if (!sha256 || !Number.isInteger(pages) || pages < 1 || pages > 200 || content.byteLength === 0 || content.byteLength > 32 * 1024 * 1024) {
    throw new Error("Integrità o limiti del PDF non verificati");
  }
  if (bytesToHex(digest(new Uint8Array(content))) !== sha256) throw new Error("Integrità o limiti del PDF non verificati");
  return { content, part: { id: sourceId, filename: "Avviso.pdf", mime_type: "application/pdf", size: content.byteLength, sha256, pages, version: 1 } };
}
