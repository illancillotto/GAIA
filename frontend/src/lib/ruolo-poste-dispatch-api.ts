import { request, requestBlob } from "@/lib/api";
import type {
  PosteDispatchCandidateList,
  PosteDispatchItem,
  PosteDispatchJob,
  PosteDispatchJobKind,
  PosteDispatchLotDetail,
  PosteDispatchLotList,
  PosteDispatchRecipient,
} from "@/types/ruolo-poste-dispatch";

const BASE = "/ruolo/tributi/poste-dispatch";

function auth(token: string) {
  return { Authorization: `Bearer ${token}` };
}

function itemPath(lotId: string, itemId: string): string {
  return `${BASE}/lots/${lotId}/items/${itemId}`;
}

export function listPosteCandidates(token: string, q: string): Promise<PosteDispatchCandidateList> {
  const query = new URLSearchParams({ page: "1", page_size: "50" });
  if (q.trim()) query.set("q", q.trim());
  return request<PosteDispatchCandidateList>(`${BASE}/candidates?${query}`, { headers: auth(token) });
}

export function listPosteLots(token: string): Promise<PosteDispatchLotList> {
  return request<PosteDispatchLotList>(`${BASE}/lots?page=1&page_size=50`, { headers: auth(token) });
}

export function getPosteLot(token: string, lotId: string): Promise<PosteDispatchLotDetail> {
  return request<PosteDispatchLotDetail>(`${BASE}/lots/${lotId}`, { headers: auth(token) });
}

export function createPosteLot(token: string, title: string, batchItemIds: string[]): Promise<PosteDispatchLotDetail> {
  return request<PosteDispatchLotDetail>(`${BASE}/lots`, {
    method: "POST",
    headers: auth(token),
    body: JSON.stringify({ title, batch_item_ids: batchItemIds }),
  });
}

export function requestPosteJob(token: string, lotId: string, kind: PosteDispatchJobKind): Promise<PosteDispatchJob> {
  return request<PosteDispatchJob>(`${BASE}/lots/${lotId}/jobs`, {
    method: "POST",
    headers: auth(token),
    body: JSON.stringify({ kind }),
  });
}

export function updatePosteRecipient(token: string, lotId: string, itemId: string, recipient: PosteDispatchRecipient): Promise<PosteDispatchItem> {
  return request<PosteDispatchItem>(`${itemPath(lotId, itemId)}/recipient`, {
    method: "PUT",
    headers: auth(token),
    body: JSON.stringify(recipient),
  });
}

export function acceptPosteManualAddress(token: string, lotId: string, itemId: string): Promise<PosteDispatchItem> {
  return request<PosteDispatchItem>(`${itemPath(lotId, itemId)}/manual-address`, { method: "POST", headers: auth(token) });
}

export function cancelPosteItem(token: string, lotId: string, itemId: string): Promise<PosteDispatchItem> {
  return request<PosteDispatchItem>(`${itemPath(lotId, itemId)}/cancel`, { method: "POST", headers: auth(token) });
}

export function getPosteItemDocument(token: string, lotId: string, itemId: string): Promise<Blob> {
  return requestBlob(`${itemPath(lotId, itemId)}/document`, { headers: auth(token), cache: "no-store" });
}
