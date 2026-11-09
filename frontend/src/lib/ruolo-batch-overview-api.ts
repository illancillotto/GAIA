import { request } from "@/lib/api";
import type { PosteDispatchItem } from "@/types/ruolo-poste-dispatch";

export type BatchPosteDispatch = Pick<PosteDispatchItem,
  "id" | "notice_number" | "status" | "poste_draft_id" | "poste_status" | "draft_created_at" |
  "sent_at" | "tracking_number" | "upload_requested_by_username" | "updated_at"
> & { poste_username: string | null };

export interface BatchOverviewItem {
  item_id: string;
  label: string;
  status: string;
  sendable: boolean;
  pec_sent: boolean;
  notice_number: string | null;
  years: number[];
  amount: number;
  poste_dispatches?: BatchPosteDispatch[];
}

export interface BatchOverview {
  batch_id: string;
  items: BatchOverviewItem[];
}

export function getBatchOverview(token: string, batchIds: string[]): Promise<BatchOverview[]> {
  const query = new URLSearchParams(batchIds.map((id) => ["batch_id", id]));
  return request<BatchOverview[]>(`/ruolo/tributi/solleciti/batch-overview?${query}`, { headers: { Authorization: `Bearer ${token}` } });
}
