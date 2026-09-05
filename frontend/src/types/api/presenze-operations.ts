import type {
  PresenzeBankHoursAdjustment,
  PresenzeCollaborator,
  PresenzeDailyRecord,
  PresenzeEventSummary,
} from "./presenze-base";

export type PresenzeBankHoursSnapshot = {
  collaborator_id: string;
  period_start: string;
  period_end: string;
  description: string;
  residuo_prec_minutes: number;
  spettante_minutes: number;
  fruito_minutes: number;
  saldo_minutes: number;
  saldo_totale_minutes: number;
  source_job_id: string | null;
};

export type PresenzeBankHoursBalanceItem = {
  collaborator_id: string;
  employee_code: string;
  collaborator_name: string;
  company_code: string | null;
  application_user_id: number | null;
  contract_kind: "operaio" | "impiegato" | "quadro" | "altro" | null;
  standard_daily_minutes: number | null;
  contract_profile_source: "explicit" | "derived" | "missing";
  imported_prev_balance_minutes: number;
  imported_accrued_minutes: number;
  imported_used_minutes: number;
  imported_balance_minutes: number;
  approved_adjustment_minutes: number;
  effective_balance_minutes: number;
  available_debit_minutes: number;
  available_debit_days: number | null;
  liquidation_minutes_total: number;
  manual_adjustment_count: number;
  pending_adjustment_count: number;
  latest_snapshot_period_start: string | null;
  latest_snapshot_period_end: string | null;
  last_adjustment_date: string | null;
  last_adjustment_status: "pending" | "approved" | "rejected" | null;
};

export type PresenzeBankHoursDashboardResponse = {
  date_from: string | null;
  date_to: string | null;
  collaborators_total: number;
  imported_balance_total_minutes: number;
  approved_adjustment_total_minutes: number;
  effective_balance_total_minutes: number;
  liquidation_total_minutes: number;
  pending_adjustments_total: number;
  negative_balance_total: number;
  items: PresenzeBankHoursBalanceItem[];
};

export type PresenzeBankHoursCompensationSummary = {
  records_total: number;
  worked_days_total: number;
  night_minutes_total: number;
  festive_minutes_total: number;
  festive_night_minutes_total: number;
  ordinary_night_minutes_total: number;
  overtime_day_minutes_total: number;
  overtime_night_minutes_total: number;
  overtime_festive_minutes_total: number;
  overtime_festive_night_minutes_total: number;
  shift_festive_day_minutes_total: number;
  shift_night_minutes_total: number;
  shift_festive_night_minutes_total: number;
  night_shift_days_total: number;
  max_monthly_night_shift_count: number;
  ordinary_night_bonus_threshold_met: boolean;
  ordinary_night_bonus_rate: number | null;
};

export type PresenzeBankHoursLiquidationGuidance = {
  allow_derived_profile: boolean;
  included_overtime_buckets: string[];
  min_suggested_minutes: number;
  available_minutes: number;
  candidate_minutes_from_overtime: number;
  suggested_minutes: number;
  suggested_days: number | null;
  liquidable_minutes: number;
  keep_in_bank_minutes: number;
  review_minutes: number;
  requires_profile_review: boolean;
  reason_code: "ok" | "missing_profile" | "no_overtime_candidate" | "no_available_balance" | "partial_review";
  notes: string[];
};

export type PresenzeBankHoursCollaboratorDetailResponse = {
  collaborator: PresenzeCollaborator;
  contract_profile_source: "explicit" | "derived" | "missing";
  date_from: string | null;
  date_to: string | null;
  imported_balance_minutes: number;
  approved_adjustment_minutes: number;
  effective_balance_minutes: number;
  available_debit_minutes: number;
  available_debit_days: number | null;
  compensation_summary: PresenzeBankHoursCompensationSummary;
  liquidation_guidance: PresenzeBankHoursLiquidationGuidance;
  snapshots: PresenzeBankHoursSnapshot[];
  adjustments: PresenzeBankHoursAdjustment[];
};

export type PresenzeHoliday = {
  id: number;
  holiday_date: string;
  label: string;
  company_code: string | null;
  holiday_kind: "ordinary" | "suppressed" | "working_override";
  is_workday_override: boolean;
  created_at: string;
  updated_at: string;
};

export type PresenzeHolidayCreateInput = {
  holiday_date: string;
  label: string;
  company_code?: string | null;
  holiday_kind?: "ordinary" | "suppressed" | "working_override";
  is_workday_override?: boolean;
};

export type PresenzeHolidayUpdateInput = Partial<PresenzeHolidayCreateInput>;

export type PresenzeScheduleRule = {
  id: number;
  template_id: number;
  label: string | null;
  weekday: number | null;
  recurrence_kind: string;
  week_of_month: number | null;
  interval_weeks: number | null;
  anchor_date: string | null;
  start_time: string;
  end_time: string;
  season_start_month: number | null;
  season_start_day: number | null;
  season_end_month: number | null;
  season_end_day: number | null;
  applies_on_holiday: boolean;
  ordinary_label: string | null;
  sort_order: number;
  created_at: string;
  updated_at: string;
};

export type PresenzeScheduleTemplate = {
  id: number;
  code: string;
  label: string;
  company_code: string | null;
  is_active: boolean;
  valid_from: string | null;
  valid_to: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
  rules: PresenzeScheduleRule[];
};

export type PresenzeScheduleTemplateCreateInput = {
  code: string;
  label: string;
  company_code?: string | null;
  is_active?: boolean;
  valid_from?: string | null;
  valid_to?: string | null;
  notes?: string | null;
};

export type PresenzeScheduleTemplateUpdateInput = Partial<PresenzeScheduleTemplateCreateInput>;

export type PresenzeScheduleRuleCreateInput = {
  label?: string | null;
  weekday?: number | null;
  recurrence_kind?: string;
  week_of_month?: number | null;
  interval_weeks?: number | null;
  anchor_date?: string | null;
  start_time: string;
  end_time: string;
  season_start_month?: number | null;
  season_start_day?: number | null;
  season_end_month?: number | null;
  season_end_day?: number | null;
  applies_on_holiday?: boolean;
  ordinary_label?: string | null;
  sort_order?: number;
};

export type PresenzeScheduleRuleUpdateInput = Partial<PresenzeScheduleRuleCreateInput>;

export type PresenzeCollaboratorScheduleAssignment = {
  id: number;
  collaborator_id: string;
  template_id: number;
  valid_from: string | null;
  valid_to: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
  template: PresenzeScheduleTemplate | null;
};

export type PresenzeCollaboratorScheduleAssignmentCreateInput = {
  template_id: number;
  valid_from?: string | null;
  valid_to?: string | null;
  notes?: string | null;
};

export type PresenzeScheduleBootstrapRulePreview = {
  label: string | null;
  weekday: number | null;
  recurrence_kind: string;
  week_of_month: number | null;
  interval_weeks: number | null;
  anchor_date: string | null;
  start_time: string;
  end_time: string;
  season_start_month: number | null;
  season_start_day: number | null;
  season_end_month: number | null;
  season_end_day: number | null;
  applies_on_holiday: boolean;
  ordinary_label: string | null;
  sort_order: number;
};

export type PresenzeScheduleBootstrapPresetPreview = {
  preset_key: string;
  template_code: string;
  template_label: string;
  template_notes: string | null;
  source_schedule_codes: string[];
  detected_records_count: number;
  detected_collaborators_count: number;
  already_exists: boolean;
  rules: PresenzeScheduleBootstrapRulePreview[];
};

export type PresenzeScheduleProfilePreview = {
  profile_code: string;
  profile_label: string;
  description: string;
  default_template_code: string | null;
  template_codes: string[];
  assignable_template_codes: string[];
  inherited_template_codes: string[];
  rule_summaries: string[];
  active: boolean;
};

export type PresenzeScheduleBootstrapCollaboratorSuggestion = {
  collaborator_id: string;
  employee_code: string;
  collaborator_name: string;
  company_code: string | null;
  dominant_schedule_code: string | null;
  schedule_codes: string[];
  assigned_template_code: string | null;
  suggested_template_code: string | null;
  suggested_template_label: string | null;
  suggestion_confidence: "high" | "medium" | "low" | "none";
  suggestion_reason: string | null;
  already_assigned: boolean;
  configuration_status: "unassigned" | "current" | "legacy_review";
  configuration_notes: string[];
};

export type PresenzeScheduleBootstrapPreviewResponse = {
  detected_collaborators_total: number;
  collaborators_with_suggestion_total: number;
  collaborators_without_assignment_total: number;
  profiles: PresenzeScheduleProfilePreview[];
  presets: PresenzeScheduleBootstrapPresetPreview[];
  collaborator_suggestions: PresenzeScheduleBootstrapCollaboratorSuggestion[];
};

export type PresenzeScheduleBootstrapApplyRequest = {
  create_missing_templates?: boolean;
  assign_unassigned_collaborators?: boolean;
};

export type PresenzeScheduleBootstrapApplyResponse = {
  created_templates: number;
  created_assignments: number;
  skipped_existing_templates: number;
  skipped_existing_assignments: number;
  template_codes: string[];
  assigned_employee_codes: string[];
};

export type PresenzeCollaboratorCalendarResponse = {
  collaborator: PresenzeCollaborator;
  date_from: string;
  date_to: string;
  items: PresenzeDailyRecord[];
};

export type PresenzeCollaboratorSummaryResponse = {
  collaborator: PresenzeCollaborator;
  period_start: string;
  period_end: string;
  items: PresenzeEventSummary[];
};

export type PresenzeImportPreviewCollaborator = {
  employee_code: string;
  company_code: string | null;
  name: string;
  application_user_id: number | null;
  total_daily_rows: number;
  total_summary_rows: number;
  period_start: string;
  period_end: string;
};

export type PresenzeImportPreviewResponse = {
  total_collaborators: number;
  total_daily_rows: number;
  total_summary_rows: number;
  collaborators: PresenzeImportPreviewCollaborator[];
  errors: string[];
};

export type PresenzeImportJob = {
  id: string;
  status: string;
  filename: string | null;
  requested_by_user_id: number;
  target_user_id: number | null;
  date_from: string | null;
  date_to: string | null;
  total_records: number;
  records_imported: number;
  records_skipped: number;
  records_errors: number;
  error_detail: string | null;
  params_json: Record<string, unknown> | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
};

export type PresenzeImportJobListResponse = {
  items: PresenzeImportJob[];
  total: number;
};

export type PresenzeCredential = {
  id: number;
  application_user_id: number;
  label: string;
  username: string;
  active: boolean;
  last_used_at: string | null;
  last_authenticated_url: string | null;
  last_error: string | null;
  consecutive_failures: number;
  created_at: string;
  updated_at: string;
};

export type PresenzeCredentialCreateInput = {
  label: string;
  username: string;
  password: string;
  active: boolean;
};

export type PresenzeCredentialUpdateInput = {
  label?: string;
  username?: string;
  password?: string;
  active?: boolean;
};

export type PresenzeCredentialTestResult = {
  ok: boolean;
  authenticated_url: string | null;
  cookies: string | null;
  error: string | null;
};

export type PresenzeSyncJobCreateInput = {
  year: number;
  month: number;
  credential_id: number;
  collaborator_limit?: number | null;
  employee_codes?: string[] | null;
};

export type PresenzeSyncJobRetrySelectedInput = {
  employee_codes: string[];
};

export type PresenzeXlsmExportJobCreateInput = {
  period_start: string;
  collaborator_ids?: string[] | null;
  employee_kind?: string | null;
  template_path?: string | null;
};

export type PresenzeStraordinariPreviewItem = {
  record_id: string;
  work_date: string;
  motivation: string;
  start_time: string | null;
  end_time: string | null;
  duration_minutes: number;
  duration_label: string;
};

export type PresenzeStraordinariPreviewResponse = {
  collaborator: PresenzeCollaborator;
  period_start: string;
  period_end: string;
  items: PresenzeStraordinariPreviewItem[];
};

export type PresenzeStraordinariExportJobCreateInput = {
  collaborator_id?: string | null;
  items: Array<{
    record_id: string;
    motivation: string;
  }>;
  template_path?: string | null;
};

export type PresenzeSyncJobProgress = {
  state?: string;
  job_id?: string;
  attempt_count?: number;
  started_at?: string;
  finished_at?: string;
  completed_collaborators?: number;
  failed_collaborators?: number;
  total_collaborators?: number;
  last_event?: string;
  last_event_at?: string;
  error_count?: number;
  resumed?: boolean;
  pending_collaborators?: number;
  selected_employee_codes?: string[];
  index?: number;
  total?: number;
  employee_code?: string;
  name?: string;
  elapsed_seconds?: number;
  daily_rows?: number;
  summary_rows?: number;
  error?: string;
};

export type PresenzeSyncJobSummaryErrorItem = {
  employee_code: string;
  name: string;
  error: string;
};

export type PresenzeSyncJobSummary = {
  sync_job_id: string;
  import_job_id: string | null;
  status: string;
  records_imported: number;
  records_skipped: number;
  records_errors: number;
  completed_collaborators: number;
  failed_collaborators: number;
  total_collaborators: number;
  resumed_from_checkpoint: boolean;
  error_items: PresenzeSyncJobSummaryErrorItem[];
};

export type PresenzeSyncJob = {
  id: string;
  status: string;
  requested_by_user_id: number;
  credential_id: number | null;
  import_job_id: string | null;
  period_start: string;
  period_end: string;
  collaborator_limit: number | null;
  records_imported: number;
  records_skipped: number;
  records_errors: number;
  json_artifact_path: string | null;
  worker_log_path: string | null;
  worker_pid: number | null;
  attempt_count: number;
  max_attempts: number;
  error_detail: string | null;
  params_json: {
    progress?: PresenzeSyncJobProgress;
    [key: string]: unknown;
  } | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
};

export type PresenzeSyncJobListResponse = {
  items: PresenzeSyncJob[];
  total: number;
};

export type PresenzeAutoSyncConfig = {
  job_enabled: boolean;
  credential_id: number | null;
  collaborator_limit: number | null;
  updated_at: string | null;
  updated_by_user_id: number | null;
  schedule_cron: string;
  schedule_timezone: string;
  schedule_times: string[];
};

export type PresenzeAutoSyncConfigUpdateInput = {
  job_enabled?: boolean;
  credential_id?: number | null;
  collaborator_limit?: number | null;
};

export type PresenzeBankHoursGuidanceConfig = {
  allow_derived_profile: boolean;
  include_overtime_day: boolean;
  include_overtime_night: boolean;
  include_overtime_festive: boolean;
  include_overtime_festive_night: boolean;
  min_suggested_minutes: number;
  updated_at: string | null;
  updated_by_user_id: number | null;
  updated_by_label: string | null;
};

export type PresenzeBankHoursGuidanceConfigRevision = {
  id: number;
  allow_derived_profile: boolean;
  include_overtime_day: boolean;
  include_overtime_night: boolean;
  include_overtime_festive: boolean;
  include_overtime_festive_night: boolean;
  min_suggested_minutes: number;
  changed_at: string;
  changed_by_user_id: number | null;
  changed_by_label: string | null;
};

export type PresenzeBankHoursGuidanceConfigUpdateInput = {
  allow_derived_profile?: boolean;
  include_overtime_day?: boolean;
  include_overtime_night?: boolean;
  include_overtime_festive?: boolean;
  include_overtime_festive_night?: boolean;
  min_suggested_minutes?: number | null;
};

export type PresenzeImportJsonResponse = {
  job: PresenzeImportJob;
  preview: PresenzeImportPreviewResponse;
};

export type DashboardSummary = {
  nas_users: number;
  nas_groups: number;
  shares: number;
  reviews: number;
  snapshots: number;
  sync_runs: number;
};
