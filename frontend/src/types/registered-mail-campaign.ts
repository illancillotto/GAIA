export type RegisteredMailReviewEvidence = {
  source_sha256: string;
  sheet: "Dati";
  row: number;
  ref_2022: string;
  ref_2023: string;
};

export type RegisteredMailCampaignNotice = {
  avviso_id: string;
  subject_id: string | null;
  tax_year: number;
  codice_cnc: string;
  codice_fiscale: string | null;
  nominativo: string | null;
};

export type RegisteredMailCampaignItem = {
  mail_id: string;
  source_shipment_id: string;
  recipient_name: string | null;
  recipient_address: string | null;
  tracking_number: string | null;
  legacy_avviso_id: string | null;
  classification: string;
  reasons: string[];
  candidate_notices: RegisteredMailCampaignNotice[];
  requires_operator_confirmation: boolean;
  register_document_id: string | null;
  register_avviso_ids: string[];
};

export type RegisteredMailCampaignPreview = {
  campaign: string;
  created_before: string;
  expected_years: number[];
  read_only: boolean;
  total: number;
  counts: Record<string, number>;
  items: RegisteredMailCampaignItem[];
};
