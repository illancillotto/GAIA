import { request } from "@/lib/api";
import type { RuoloPayerAssignmentRequest, RuoloPayerAssignments } from "@/types/ruolo-payer";

function payerPath(avvisoId: string): string {
  return `/ruolo/tributi/avvisi/${avvisoId}/payer`;
}

export async function getAvvisoPayer(token: string, avvisoId: string): Promise<RuoloPayerAssignments> {
  return request<RuoloPayerAssignments>(payerPath(avvisoId), { headers: { Authorization: `Bearer ${token}` } });
}

export async function setAvvisoPayer(
  token: string,
  avvisoId: string,
  payload: RuoloPayerAssignmentRequest,
): Promise<RuoloPayerAssignments> {
  return request<RuoloPayerAssignments>(payerPath(avvisoId), {
    method: "PUT",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify(payload),
  });
}

export async function removeAvvisoPayer(token: string, avvisoId: string): Promise<RuoloPayerAssignments> {
  return request<RuoloPayerAssignments>(payerPath(avvisoId), {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
}
