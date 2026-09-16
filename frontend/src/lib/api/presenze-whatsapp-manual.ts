import { request } from "./core";

export type ManualWhatsAppPreview = {
  record_id: string;
  collaborator_name: string;
  phone_e164: string;
  work_date: string;
  reason: string;
  text: string;
  provider: "waha" | "dry_run";
  fingerprint: string;
};

export function previewManualWhatsApp(token: string, recordId: string): Promise<ManualWhatsAppPreview> {
  return request(`/presenze/whatsapp/daily/${recordId}/preview`, {
    headers: { Authorization: `Bearer ${token}` }, cache: "no-store",
  });
}

export function sendManualWhatsApp(token: string, preview: ManualWhatsAppPreview, reason: string): Promise<{ message_id: string; status: string }> {
  return request(`/presenze/whatsapp/daily/${preview.record_id}/send`, {
    method: "POST", headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify({ fingerprint: preview.fingerprint, reason }),
  });
}
