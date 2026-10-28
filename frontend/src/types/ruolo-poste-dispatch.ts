export type PosteDispatchJobKind = "addresses" | "drafts" | "reconcile" | "delete";

export interface PosteDispatchCandidate {
  batch_item_id: string;
  batch_title: string | null;
  display_name: string | null;
  codice_fiscale: string;
  notice_number: string | null;
  years: unknown[];
  created_at: string;
}

export interface PosteDispatchCandidateList {
  items: PosteDispatchCandidate[];
  total: number;
  page: number;
  page_size: number;
}

export interface PosteDispatchRecipient {
  name: string;
  name_extra: string;
  address: string;
  cap: string;
  city: string;
  province: string;
}

export interface PosteDispatchItem {
  id: string;
  batch_item_id: string;
  notice_number: string;
  shipment_name: string;
  status: string;
  recipient: PosteDispatchRecipient;
  poste_address: Record<string, unknown> | null;
  address_review: { reason?: string; problems?: string[]; suggestions?: string[] } | null;
  artifact_sha256: string;
  artifact_size: number;
  poste_draft_id: string | null;
  poste_status: string | null;
  price_amount: number | null;
  draft_created_at: string | null;
  sent_at: string | null;
  tracking_number: string | null;
  registered_mail_id: string | null;
  error_detail: string | null;
  updated_at: string;
}

export interface PosteDispatchJob {
  id: number;
  mode: string;
  status: string;
  error_detail: string | null;
  created_at: string;
}

export interface PosteDispatchPortalSnapshot {
  checked_at?: string;
  drafts_total?: number;
  foreign_drafts?: { draft_id: string; name: string; status: string }[];
  duplicate_names?: string[];
}

export interface PosteDispatchLotSummary {
  id: string;
  title: string;
  status: string;
  created_by: number;
  created_at: string;
  counts: Record<string, number>;
  priced_total: number;
}

export interface PosteDispatchLotDetail extends PosteDispatchLotSummary {
  postal_options: Record<string, unknown>;
  portal_snapshot: PosteDispatchPortalSnapshot | null;
  draft_expires_at: string | null;
  active_job: PosteDispatchJob | null;
  items: PosteDispatchItem[];
  events: { kind: string; item_id: string | null; created_at: string }[];
}

export interface PosteDispatchLotList {
  items: PosteDispatchLotSummary[];
  total: number;
  page: number;
  page_size: number;
}
