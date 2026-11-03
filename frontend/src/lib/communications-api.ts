import { getApiBaseUrl, request } from "@/lib/api";
import type { Attachment } from "@/types/communications";

const BASE = "/communications";

export function communications<T>(token: string, path: string, data?: unknown, method?: string): Promise<T> {
  return request<T>(`${BASE}${path}`, {
    method: method ?? (data === undefined ? "GET" : "POST"),
    headers: { Authorization: `Bearer ${token}`, ...(data === undefined ? {} : { "Content-Type": "application/json" }) },
    ...(data === undefined ? {} : { body: JSON.stringify(data) }), cache: "no-store",
  });
}

export async function loadSnapshot(token: string, messageId: string, part: Attachment, signal: AbortSignal) {
  const response = await fetch(`${getApiBaseUrl()}${BASE}/messages/${messageId}/attachments/${part.id}/preview`, {
    headers: { Authorization: `Bearer ${token}` }, cache: "no-store", signal,
  });
  if (!response.ok) throw new Error("PDF non disponibile o accesso negato");
  const content = await response.arrayBuffer();
  const hash = Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256", content)), (value) => value.toString(16).padStart(2, "0")).join("");
  const reviewId = response.headers.get("X-Communication-Review");
  if (!reviewId || hash !== part.sha256 || content.byteLength !== part.size || content.byteLength > 32 * 1024 * 1024) throw new Error("Integrità dello snapshot non verificata");
  return { content, reviewId };
}

export async function receiptBlob(token: string, messageId: string, receiptId: string) {
  const response = await fetch(`${getApiBaseUrl()}${BASE}/messages/${messageId}/receipts/${receiptId}/original`, {
    headers: { Authorization: `Bearer ${token}` }, cache: "no-store",
  });
  if (!response.ok) throw new Error("Ricevuta non disponibile");
  return response.blob();
}

export async function uploadAttachment(token: string, messageId: string, version: number, file: File) {
  const data = new FormData(); data.set("upload", file); data.set("expected_version", String(version));
  const response = await fetch(`${getApiBaseUrl()}${BASE}/messages/${messageId}/attachments`, {
    method: "POST", headers: { Authorization: `Bearer ${token}` }, body: data, cache: "no-store",
  });
  if (!response.ok) throw new Error("Allegato rifiutato: controllare PDF, dimensioni e versione della bozza");
  return response.json() as Promise<import("@/types/communications").Communication>;
}
