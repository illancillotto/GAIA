export type Channel = "pec" | "email";
export type Attachment = { id: string; filename: string; mime_type: string; size: number; pages: number; sha256: string; version: number };
export type Communication = {
  id: string; channel: Channel; account_id: string; sender: string; recipient: string; subject: string;
  body: string; state: string; version: number; notice_number: string; source_entity_id: string;
  attachments: Attachment[];
};
export type Account = { id: string; name: string; channel: Channel; provider: string; sender: string; paused: boolean; max_bytes: number };
export type Candidate = {
  id: string; batch_title: string; batch_id: string; notice_number: string; display_name: string; tax_code: string;
  amount: string; year: number; email: string | null; pec: string | null; document_state: string;
  payment_state: string; notification_state: string; communication_state: string | null; message_id: string | null;
  last_event_at: string | null;
};
export type Template = { id: string; code: string; name: string; channel: Channel; subject: string; body: string; version: number; status: string };
export type CommEvent = { id: string; kind: string; created_at: string; detail: Record<string, unknown> };
export type Receipt = { id: string; kind: string; classification: string; created_at: string; sha256: string };
