import { request } from "@/lib/api";
import type {
  RuoloTributiRegisteredMailAssociationRequest,
  RuoloTributiRegisteredMailResponse,
  RuoloTributiRegisteredMailSummaryResponse,
} from "@/types/ruolo";

export async function getTributiRegisteredMailSummary(token: string): Promise<RuoloTributiRegisteredMailSummaryResponse> {
  return request<RuoloTributiRegisteredMailSummaryResponse>("/ruolo/tributi/raccomandate/summary", {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function updateTributiRegisteredMailAssociation(
  token: string,
  mailId: string,
  payload: RuoloTributiRegisteredMailAssociationRequest,
): Promise<RuoloTributiRegisteredMailResponse> {
  return request<RuoloTributiRegisteredMailResponse>(`/ruolo/tributi/raccomandate/${mailId}/association`, {
    method: "PATCH",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify(payload),
  });
}
