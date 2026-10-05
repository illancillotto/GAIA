import { request, requestBlob } from "@/lib/api/core";

export type RegisteredMailCard = {
  id: string;
  document_id: string;
  subject_id: string;
  filename: string;
  tracking_number: string;
  sha256: string;
  scanned_on: string;
  source_reference: string | null;
  created_at: string;
};

export function listRegisteredMailCards(token: string, mailId: string): Promise<RegisteredMailCard[]> {
  return request(`/ruolo/tributi/raccomandate/${mailId}/cartoline`, {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export function uploadRegisteredMailCard(
  token: string, mailId: string, file: File, tracking: string, scannedOn: string,
): Promise<RegisteredMailCard> {
  const body = new FormData();
  body.append("file", file);
  body.append("tracking_number", tracking);
  body.append("scanned_on", scannedOn);
  body.append("source_reference", file.name);
  return request(`/ruolo/tributi/raccomandate/${mailId}/cartoline`, {
    method: "POST", headers: { Authorization: `Bearer ${token}` }, body,
  });
}

export function downloadRegisteredMailCard(token: string, mailId: string, cardId: string): Promise<Blob> {
  return requestBlob(`/ruolo/tributi/raccomandate/${mailId}/cartoline/${cardId}/download`, {
    headers: { Authorization: `Bearer ${token}` },
  });
}
