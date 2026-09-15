export type PresenzeWhatsAppDay = {
  work_date: string;
  problem: string;
  detail: string;
};

export type PresenzeWhatsAppMessage = {
  id: string;
  collaborator_id: string;
  collaborator_name: string;
  application_user_id: number | null;
  user_label: string;
  username: string | null;
  phone_e164: string;
  text_body: string;
  days: PresenzeWhatsAppDay[];
  status: string;
  provider: string;
  provider_message_id: string | null;
  error_code: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
  delivered_at: string | null;
  read_at: string | null;
};

export type PresenzeWhatsAppMessageList = {
  items: PresenzeWhatsAppMessage[];
  total: number;
  page: number;
  page_size: number;
};

export type PresenzeWhatsAppDashboardSummary = {
  provider_enabled: boolean;
  provider: string | null;
  session_status: string;
  session_detail: string | null;
  cron: string;
  next_run_at: string | null;
  send_window: string;
  max_per_run: number;
  sent_total: number;
  delivered_total: number;
  read_total: number;
  failed_total: number;
  uncertain_total: number;
  opted_out_total: number;
};

export type PresenzeWhatsAppPreviewItem = {
  collaborator_id: string;
  collaborator_name: string;
  application_user_id: number | null;
  phone_e164: string | null;
  days: PresenzeWhatsAppDay[];
  message_text: string | null;
  ready: boolean;
  reason: string | null;
};

export type PresenzeWhatsAppPreview = {
  ready: PresenzeWhatsAppPreviewItem[];
  skipped: PresenzeWhatsAppPreviewItem[];
  generated_at: string;
};

export type PresenzeWhatsAppOptOut = {
  application_user_id: number;
  user_label: string;
  username: string | null;
  collaborator_name: string | null;
  phone_e164: string | null;
  source: string;
  created_at: string;
};
