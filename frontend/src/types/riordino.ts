export type RiordinoEvent = {
  id: string;
  practice_id: string;
  phase_id: string | null;
  step_id: string | null;
  event_type: string;
  payload_json: Record<string, unknown> | null;
  created_by: number;
  created_at: string;
};

export type RiordinoDocument = {
  id: string;
  practice_id: string;
  phase_id: string | null;
  step_id: string | null;
  issue_id: string | null;
  appeal_id: string | null;
  document_type: string;
  version_no: number;
  storage_path: string;
  original_filename: string;
  mime_type: string;
  file_size_bytes: number;
  uploaded_by: number;
  uploaded_at: string;
  deleted_at: string | null;
  notes: string | null;
  created_at: string;
};

export type RiordinoDocumentListResponse = {
  items: RiordinoDocument[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
};

export type RiordinoChecklistItem = {
  id: string;
  step_id: string;
  label: string;
  is_checked: boolean;
  is_blocking: boolean;
  checked_by: number | null;
  checked_at: string | null;
  sequence_no: number;
  created_at: string;
};

export type RiordinoStep = {
  id: string;
  practice_id: string;
  phase_id: string;
  template_id: string | null;
  code: string;
  title: string;
  sequence_no: number;
  status: string;
  is_required: boolean;
  branch: string | null;
  is_decision: boolean;
  outcome_code: string | null;
  outcome_notes: string | null;
  skip_reason: string | null;
  requires_document: boolean;
  owner_user_id: number | null;
  due_at: string | null;
  started_at: string | null;
  completed_at: string | null;
  version: number;
  updated_at: string;
  created_at: string;
  checklist_items: RiordinoChecklistItem[];
  documents: RiordinoDocument[];
};

export type RiordinoPhase = {
  id: string;
  practice_id: string;
  phase_code: string;
  status: string;
  started_at: string | null;
  completed_at: string | null;
  approved_by: number | null;
  notes: string | null;
  updated_at: string;
  created_at: string;
  steps: RiordinoStep[];
};

export type RiordinoPractice = {
  id: string;
  code: string;
  title: string;
  description: string | null;
  municipality: string;
  grid_code: string;
  lot_code: string;
  current_phase: string;
  status: string;
  owner_user_id: number;
  opened_at: string | null;
  completed_at: string | null;
  archived_at: string | null;
  deleted_at: string | null;
  version: number;
  created_by: number;
  created_at: string;
  updated_at: string;
};

export type RiordinoPracticeDetail = RiordinoPractice & {
  phases: RiordinoPhase[];
  issues_count: number;
  appeals_count: number;
  documents_count: number;
};

export type RiordinoPracticeListResponse = {
  items: RiordinoPractice[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
};

export type RiordinoAppeal = {
  id: string;
  practice_id: string;
  phase_id: string;
  step_id: string | null;
  appellant_subject_id: string | null;
  appellant_name: string;
  filed_at: string;
  deadline_at: string | null;
  commission_name: string | null;
  commission_date: string | null;
  status: string;
  resolution_notes: string | null;
  resolved_at: string | null;
  created_by: number;
  created_at: string;
};

export type RiordinoIssue = {
  id: string;
  practice_id: string;
  phase_id: string | null;
  step_id: string | null;
  type: string;
  category: string;
  severity: string;
  status: string;
  title: string;
  description: string | null;
  opened_by: number;
  assigned_to: number | null;
  opened_at: string;
  closed_at: string | null;
  resolution_notes: string | null;
  version: number;
  created_at: string;
};

export type RiordinoGisLink = {
  id: string;
  practice_id: string;
  layer_name: string;
  feature_id: string | null;
  geometry_ref: string | null;
  sync_status: string;
  last_synced_at: string | null;
  notes: string | null;
  updated_at: string;
  created_at: string;
};

export type RiordinoNotification = {
  id: string;
  user_id: number;
  practice_id: string | null;
  type: string;
  message: string;
  is_read: boolean;
  created_at: string;
};

export type RiordinoDocumentTypeConfig = {
  id: string;
  code: string;
  label: string;
  description: string | null;
  is_active: boolean;
  sort_order: number;
  created_at: string;
  updated_at: string;
};

export type RiordinoIssueTypeConfig = {
  id: string;
  code: string;
  label: string;
  category: string;
  default_severity: string;
  description: string | null;
  is_active: boolean;
  sort_order: number;
  created_at: string;
  updated_at: string;
};

export type RiordinoDashboardResponse = {
  practices_by_status: Record<string, number>;
  practices_by_phase: Record<string, number>;
  blocking_issues_open: number;
  recent_events: RiordinoEvent[];
};

export type RiordinoStepAdvanceInput = {
  outcome_code?: string | null;
  outcome_notes?: string | null;
};

export type RiordinoStepSkipInput = {
  skip_reason: string;
};

export type RiordinoPhaseCompleteInput = {
  notes?: string | null;
};

export type RiordinoAppealCreateInput = {
  appellant_name: string;
  filed_at: string;
  deadline_at?: string | null;
  commission_name?: string | null;
  commission_date?: string | null;
};

export type RiordinoAppealResolveInput = {
  status: string;
  resolution_notes?: string | null;
};

export type RiordinoIssueCreateInput = {
  phase_id?: string | null;
  step_id?: string | null;
  type: string;
  category: string;
  severity: string;
  title: string;
  description?: string | null;
  assigned_to?: number | null;
};

export type RiordinoIssueCloseInput = {
  resolution_notes: string;
};

export type RiordinoGisCreateInput = {
  layer_name: string;
  feature_id?: string | null;
  geometry_ref?: string | null;
  notes?: string | null;
};

export type RiordinoGisUpdateInput = {
  layer_name?: string | null;
  feature_id?: string | null;
  geometry_ref?: string | null;
  sync_status?: string | null;
  notes?: string | null;
};

export type RiordinoDocumentUploadInput = {
  file: File;
  document_type: string;
  phase_id?: string | null;
  step_id?: string | null;
  appeal_id?: string | null;
  issue_id?: string | null;
  notes?: string | null;
};

export type RiordinoDocumentTypeConfigInput = {
  code: string;
  label: string;
  description?: string | null;
  is_active?: boolean;
  sort_order?: number;
};

export type RiordinoIssueTypeConfigInput = {
  code: string;
  label: string;
  category: string;
  default_severity: string;
  description?: string | null;
  is_active?: boolean;
  sort_order?: number;
};
