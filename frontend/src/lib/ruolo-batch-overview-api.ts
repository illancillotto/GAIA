import { request } from "@/lib/api";

export interface BatchOverviewItem {
  item_id: string;
  label: string;
  status: string;
  sendable: boolean;
  pec_sent: boolean;
}

export interface BatchOverview {
  batch_id: string;
  items: BatchOverviewItem[];
}

export function getBatchOverview(token: string, batchIds: string[]): Promise<BatchOverview[]> {
  const query = new URLSearchParams(batchIds.map((id) => ["batch_id", id]));
  return request<BatchOverview[]>(`/ruolo/tributi/solleciti/batch-overview?${query}`, { headers: { Authorization: `Bearer ${token}` } });
}
