import { request } from "@/lib/api";
import type { NoticeGenerationConfirmationResponse } from "@/types/ruolo";

export function confirmTributiReminderBatch(token: string, batchId: string) {
  return request<NoticeGenerationConfirmationResponse>(`/ruolo/tributi/solleciti/batches/${batchId}/confirm`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify({ batch: true }),
  });
}
