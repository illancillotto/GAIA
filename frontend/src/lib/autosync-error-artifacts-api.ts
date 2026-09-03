import { request } from "@/lib/api";
import type { ElaborazioneRichiesta } from "@/types/api";

export function getAutoSyncErrorRequest(
  token: string,
  requestId: string,
): Promise<ElaborazioneRichiesta> {
  return request<ElaborazioneRichiesta>(`/elaborazioni/requests/${requestId}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
}
