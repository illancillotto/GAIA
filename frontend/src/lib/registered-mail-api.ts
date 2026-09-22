import { request } from "@/lib/api";
import type {
  RuoloTributiRegisteredMailAssociationRequest,
  RuoloTributiRegisteredMailResponse,
} from "@/types/ruolo";

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
