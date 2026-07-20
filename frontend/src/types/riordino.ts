export type RiordinoEvent = {
  id: string;
  practice_id: string | null;
  block_id: string | null;
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
  block_id: string | null;
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

export type RiordinoParcelLink = {
  id: string;
  practice_id: string;
  foglio: string;
  particella: string;
  subalterno: string | null;
  quality_class: string | null;
  title_holder_name: string | null;
  title_holder_subject_id: string | null;
  source: string | null;
  notes: string | null;
  cat_particella_id: string | null;
  cat_particella_match_status: string | null;
  cat_particella_match_reason: string | null;
  cat_particella_nome_comune: string | null;
  cat_particella_num_distretto: string | null;
  cat_particella_has_geometry: boolean | null;
  created_at: string;
  updated_at: string;
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
  blocks_by_status?: Record<string, number>;
  practices_by_status: Record<string, number>;
  practices_by_phase: Record<string, number>;
  blocking_issues_open: number;
  recent_events: RiordinoEvent[];
};

export type RiordinoBlockAssignment = {
  id: string;
  block_id: string;
  user_id: number;
  assignment_role: string;
  is_active: boolean;
  assigned_by: number;
  assigned_at: string;
};

export type RiordinoBlockParcelSnapshot = {
  id: string;
  block_id: string;
  ade_particella_id: string | null;
  national_cadastral_reference: string;
  administrative_unit: string | null;
  codice_catastale: string | null;
  sezione_catastale: string | null;
  foglio: string | null;
  particella: string | null;
  label: string | null;
  cat_particella_id: string | null;
  cat_particella_match_status: string;
  cat_particella_match_reason: string | null;
  capacitas_payload_json: Record<string, unknown> | null;
  operator_review_status: string;
  operator_review_notes: string | null;
  reviewed_by: number | null;
  reviewed_at: string | null;
  sister_visura_status: string;
  sister_visura_request_id: string | null;
  sister_visura_document_ref: string | null;
  sister_visura_error: string | null;
  sister_visura_requested_by: number | null;
  sister_visura_requested_at: string | null;
  sister_visura_completed_by: number | null;
  sister_visura_completed_at: string | null;
  created_at: string;
};

export type RiordinoBlock = {
  id: string;
  code: string;
  title: string;
  description: string | null;
  municipality: string | null;
  selection_type: string;
  selection_json: Record<string, unknown>;
  status: string;
  coordinator_user_id: number;
  created_by: number;
  parcel_count: number;
  mismatch_count: number;
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
};

export type RiordinoBlockDetail = RiordinoBlock & {
  assignments: RiordinoBlockAssignment[];
  parcel_snapshots: RiordinoBlockParcelSnapshot[];
  events: RiordinoEvent[];
};

export type RiordinoBlockListResponse = {
  items: RiordinoBlock[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
};

export type RiordinoBlockParcelRefInput = {
  codice_catastale?: string | null;
  administrative_unit?: string | null;
  foglio: string;
  particella: string;
};

export type RiordinoBlockCreateInput = {
  title: string;
  coordinator_user_id: number;
  selection_type: "municipality" | "lot" | "parcel_list" | "gis_selection";
  description?: string | null;
  municipality?: string | null;
  codice_catastale?: string | null;
  administrative_unit?: string | null;
  foglio?: string | null;
  grid_code?: string | null;
  lot_code?: string | null;
  ade_particella_ids?: string[];
  parcel_refs?: RiordinoBlockParcelRefInput[];
  operator_user_ids?: number[];
};

export type RiordinoBlockSelectionPreviewInput = Pick<
  RiordinoBlockCreateInput,
  "selection_type" | "codice_catastale" | "administrative_unit" | "foglio" | "ade_particella_ids" | "parcel_refs"
>;

export type RiordinoBlockSelectionPreviewItem = {
  ade_particella_id: string;
  national_cadastral_reference: string;
  codice_catastale: string | null;
  foglio: string | null;
  particella: string | null;
  cat_particella_match_status: string;
  capacitas_match_status: string;
};

export type RiordinoBlockSelectionPreview = {
  parcel_count: number;
  matched_count: number;
  mismatch_count: number;
  ambiguous_count: number;
  unmatched_count: number;
  sister_missing_keys_count: number;
  sample: RiordinoBlockSelectionPreviewItem[];
};

export type RiordinoBlockWizardTask = {
  code: string;
  title: string;
  status: string;
  snapshot_id: string | null;
  phase: string;
  assignee_hint: string;
  blocking_reason: string | null;
};

export type RiordinoBlockWizard = {
  block_id: string;
  block_code: string;
  tasks: RiordinoBlockWizardTask[];
};

export type RiordinoBlockCoordinatorOperatorSummary = {
  user_id: number;
  assignment_role: string;
  is_active: boolean;
  reviewed_count: number;
  sister_requested_count: number;
  sister_completed_count: number;
  last_activity_at: string | null;
};

export type RiordinoBlockCoordinatorSummary = {
  block_id: string;
  block_code: string;
  coordinator_user_id: number;
  parcel_count: number;
  mismatch_count: number;
  review_status_counts: Record<string, number>;
  sister_status_counts: Record<string, number>;
  task_status_counts: Record<string, number>;
  operators: RiordinoBlockCoordinatorOperatorSummary[];
  recent_events: RiordinoEvent[];
};

export type RiordinoBlockParcelReviewInput = {
  status: "pending" | "aligned" | "mismatch" | "resolved";
  notes?: string | null;
};

export type RiordinoBlockSisterVisuraRequestInput = {
  enqueue?: boolean;
  request_id?: string | null;
  notes?: string | null;
};

export type RiordinoBlockSisterVisuraCompleteInput = {
  status: "downloaded" | "failed";
  document_ref?: string | null;
  error_message?: string | null;
};

export type RiordinoBlockSisterVisuraSyncInput = {
  force?: boolean;
};

export type RiordinoBlockSisterVisuraBulkSync = {
  block_id: string;
  synced_count: number;
  downloaded_count: number;
  failed_count: number;
  requested_count: number;
  skipped_count: number;
};

export type RiordinoBlockPhase2PracticeInput = {
  title?: string | null;
  description?: string | null;
  municipality?: string | null;
  grid_code?: string | null;
  lot_code?: string | null;
  owner_user_id?: number | null;
  include_only_reviewed?: boolean;
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
