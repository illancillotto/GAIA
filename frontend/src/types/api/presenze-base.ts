export type PresenzeCollaborator = {
  id: string;
  owner_user_id: number | null;
  application_user_id: number | null;
  kint: string | null;
  kkint: string | null;
  employee_code: string;
  company_code: string | null;
  company_label: string | null;
  name: string;
  birth_date: string | null;
  contract_kind: "operaio" | "impiegato" | "quadro" | "altro" | null;
  operai_group: "agrario" | "catasto_magazzino" | null;
  standard_daily_minutes: number | null;
  is_active: boolean;
  last_seen_at: string | null;
  created_at: string;
  updated_at: string;
};

export type PresenzeCollaboratorContractProfileUpdateInput = {
  contract_kind?: "operaio" | "impiegato" | "quadro" | "altro" | null;
  operai_group?: "agrario" | "catasto_magazzino" | null;
  standard_daily_minutes?: number | null;
};

export type PresenzeAccessContext = {
  can_view_all_data: boolean;
  can_view_all_credentials: boolean;
  can_manage_supervisors: boolean;
  is_supervisor: boolean;
  assigned_collaborators_count: number;
};

export type GatePresenzeRuleItem = {
  code: string;
  title: string;
  description: string;
  severity: "info" | "warning" | "blocking";
  applies_to: string[];
  operator_action: string;
};

export type GatePresenzeRuleSection = {
  code: string;
  title: string;
  description: string;
  rules: GatePresenzeRuleItem[];
};

export type GatePresenzeRulesResponse = {
  rules_version: string;
  export_rules_version: string;
  updated_at: string;
  summary: string;
  sections: GatePresenzeRuleSection[];
};

export type GatePresenzeTeamMembership = {
  id: string;
  team_id: string;
  collaborator_id: string;
  valid_from: string | null;
  valid_to: string | null;
  role: "member" | "lead" | "substitute";
  source_channel: "gaia_web" | "gate_mobile";
  created_by_user_id: number | null;
  created_at: string;
  updated_at: string;
  collaborator_name: string | null;
  employee_code: string | null;
};

export type GatePresenzeTeamSupervisor = {
  id: string;
  team_id: string;
  application_user_id: number;
  permission_scope: "view" | "validate" | "export" | "manage_team";
  valid_from: string | null;
  valid_to: string | null;
  source_channel: "gaia_web" | "gate_mobile";
  assigned_by_user_id: number | null;
  created_at: string;
  updated_at: string;
  user_label: string | null;
  username: string | null;
};

export type GatePresenzeTeam = {
  id: string;
  name: string;
  code: string | null;
  personnel_area: "AGRARIO" | "IMPIANTI";
  active: boolean;
  created_from_channel: "gaia_web" | "gate_mobile";
  created_by_user_id: number | null;
  created_at: string;
  updated_at: string;
  memberships: GatePresenzeTeamMembership[];
  supervisors: GatePresenzeTeamSupervisor[];
};

export type GatePresenzeTeamCreateInput = {
  name: string;
  code?: string | null;
  personnel_area: "AGRARIO" | "IMPIANTI";
  active?: boolean;
};

export type GatePresenzeTeamUpdateInput = Partial<GatePresenzeTeamCreateInput>;

export type GatePresenzeTeamMembershipCreateInput = {
  collaborator_id: string;
  valid_from?: string | null;
  valid_to?: string | null;
  role?: "member" | "lead" | "substitute";
};

export type GatePresenzeTeamSupervisorCreateInput = {
  application_user_id: number;
  permission_scope?: "view" | "validate" | "export" | "manage_team";
  valid_from?: string | null;
  valid_to?: string | null;
};

export type PresenzeSupervisorSummary = {
  id: number;
  username: string;
  full_name: string | null;
  email: string;
  role: string;
  is_active: boolean;
};

export type PresenzeSupervisorAssignment = {
  id: number;
  supervisor_user_id: number;
  collaborator_id: string;
  assigned_by_user_id: number | null;
  created_at: string;
  updated_at: string;
  supervisor: PresenzeSupervisorSummary | null;
  collaborator: PresenzeCollaborator | null;
};

export type PresenzeCollaboratorListResponse = {
  items: PresenzeCollaborator[];
  total: number;
  page: number;
  page_size: number;
};

export type PresenzeDailyPunch = {
  id: string;
  daily_record_id: string;
  sequence: number;
  entry_time: string | null;
  exit_time: string | null;
  terminal_label: string | null;
};

export type PresenzeDetailPunchRow = {
  time: string | null;
  direction: string | null;
  terminal_label: string | null;
  raw: Record<string, string>;
};

export type PresenzeDailyRecord = {
  id: string;
  collaborator_id: string;
  owner_user_id: number | null;
  application_user_id: number | null;
  work_date: string;
  schedule_code: string | null;
  teo_minutes: number | null;
  ordinary_minutes: number | null;
  absence_minutes: number | null;
  justified_minutes: number | null;
  maggiorazione_minutes: number | null;
  mpe_minutes: number | null;
  straordinario_minutes: number | null;
  km_value: number | null;
  trasferta_minutes: number | null;
  trasferta_montano: boolean;
  reperibilita_unit: "none" | "hours" | "days" | "shifts";
  reperibilita_quantity: number | null;
  override_straordinario_minutes: number | null;
  override_mpe_minutes: number | null;
  manual_note: string | null;
  request_type: string | null;
  request_description: string | null;
  request_status: string | null;
  request_authorized_by: string | null;
  resolved_absence_cause: string | null;
  validation_status: string;
  validated_by_user_id: number | null;
  validated_at: string | null;
  validation_note: string | null;
  effective_straordinario_minutes: number | null;
  effective_mpe_minutes: number | null;
  effective_extra_minutes: number | null;
  operational_status: "ok" | "in_analysis" | "blocking" | "unknown";
  operational_formula_code: string | null;
  operational_expected_minutes: number | null;
  operational_worked_minutes: number | null;
  operational_missing_minutes: number;
  operational_mpe_minutes: number;
  operational_notes: string[];
  night_minutes: number;
  festive_minutes: number;
  festive_night_minutes: number;
  ordinary_night_minutes: number;
  overtime_day_minutes: number;
  overtime_night_minutes: number;
  overtime_festive_minutes: number;
  overtime_festive_night_minutes: number;
  shift_festive_day_minutes: number;
  shift_night_minutes: number;
  shift_festive_night_minutes: number;
  monthly_night_shift_count: number;
  ordinary_night_bonus_threshold_met: boolean;
  ordinary_night_bonus_rate: number | null;
  stato: string | null;
  evidenze: string | null;
  raw_weekday: string | null;
  detail_title: string | null;
  detail_status: string | null;
  detail_programmed_schedule: string | null;
  detail_effective_schedule: string | null;
  detail_time_slots: string | null;
  detail_schedule_type: string | null;
  detail_theoretical_hours: string | null;
  detail_absence_hours: string | null;
  detail_day_summary: Record<string, string>;
  detail_day_totals: Record<string, string>;
  detail_requests: Array<Record<string, string>>;
  detail_anomalies: Array<Record<string, string>>;
  detail_punch_rows: PresenzeDetailPunchRow[];
  detail_text: string | null;
  detail_error: string | null;
  special_day: boolean | null;
  holiday_kind: "ordinary" | "suppressed" | "working_override" | null;
  grants_recovery_day: boolean;
  recovery_day_credit: number;
  uses_recovery_day: boolean;
  recovery_day_debit: number;
  recovery_day_balance_delta: number;
  raw_payload_json: Record<string, unknown> | unknown[] | null;
  source_job_id: string | null;
  created_at: string;
  updated_at: string;
  punches: PresenzeDailyPunch[];
};

export type PresenzeDailyRecordManualUpdateInput = {
  km_value?: number | null;
  trasferta_minutes?: number | null;
  trasferta_montano?: boolean | null;
  reperibilita_unit?: "none" | "hours" | "days" | "shifts" | null;
  reperibilita_quantity?: number | null;
  override_straordinario_minutes?: number | null;
  override_mpe_minutes?: number | null;
  manual_note?: string | null;
  validation_status?: "pending" | "validated" | null;
  validation_note?: string | null;
};

export type PresenzeDailyRecordListResponse = {
  items: PresenzeDailyRecord[];
  total: number;
  page: number;
  page_size: number;
};

export type PresenzeAnomalyListItem = {
  id: string;
  collaborator_id: string;
  work_date: string;
  collaborator_name: string;
  collaborator_code: string;
  company: string;
  schedule_code: string | null;
  programmed_schedule: string | null;
  status: string | null;
  time_slots: string | null;
  ordinary_minutes: number | null;
  absence_minutes: number | null;
  effective_extra_minutes: number;
  km_value: number | null;
  special_day: boolean;
  has_anomalies: boolean;
  has_requests: boolean;
  evidenze: string | null;
  summary: string;
};

export type PresenzeAnomalyListResponse = {
  items: PresenzeAnomalyListItem[];
  total: number;
  page: number;
  page_size: number;
};

export type PresenzeAnomalyMonthSummaryItem = {
  month: string;
  count: number;
};

export type PresenzeAnomalyMonthSummaryResponse = {
  items: PresenzeAnomalyMonthSummaryItem[];
};

export type PresenzeDashboardSummaryResponse = {
  period_start: string;
  period_end: string;
  collaborators_total: number;
  mapped_collaborators_total: number;
  active_collaborators_total: number;
  daily_records_total: number;
  ordinary_minutes_total: number;
  absence_minutes_total: number;
  extra_minutes_total: number;
  straordinario_minutes_total: number;
  maggior_presenza_minutes_total: number;
  km_total: number;
  trasferta_minutes_total: number;
  trasferta_days_total: number;
  trasferta_montano_days_total: number;
  anomaly_total: number;
  special_day_total: number;
  recovery_days_matured_total: number;
  recovery_days_used_total: number;
  recovery_days_balance_total: number;
  worked_days_total: number;
  absence_days_total: number;
  justified_days_total: number;
  cause_stats: Record<string, number>;
  schedule_stats: Array<{ code: string; count: number }>;
};

export type MePresenzeSummaryResponse = {
  period_start: string;
  period_end: string;
  items: PresenzeEventSummary[];
};

export type PresenzeEventSummary = {
  id: string;
  collaborator_id: string;
  owner_user_id: number | null;
  application_user_id: number | null;
  period_start: string;
  period_end: string;
  event_code: string | null;
  description: string;
  valid_from: string | null;
  valid_to: string | null;
  spettante_minutes: number | null;
  fruito_minutes: number | null;
  residuo_prec_minutes: number | null;
  saldo_minutes: number | null;
  autorizzato_minutes: number | null;
  pianificato_minutes: number | null;
  richiesto_minutes: number | null;
  saldo_totale_minutes: number | null;
  unitamisura: string | null;
  raw_payload_json: Record<string, unknown> | unknown[] | null;
  source_job_id: string | null;
  created_at: string;
  updated_at: string;
};

export type PresenzeRecoveryAdjustment = {
  id: string;
  collaborator_id: string;
  adjustment_date: string;
  delta_days: number;
  kind: "credit" | "debit" | "correction";
  approval_status: "pending" | "approved" | "rejected";
  reason: string;
  note: string | null;
  approval_note: string | null;
  created_by_user_id: number | null;
  updated_by_user_id: number | null;
  reviewed_by_user_id: number | null;
  created_by_label: string | null;
  updated_by_label: string | null;
  reviewed_by_label: string | null;
  created_at: string;
  updated_at: string;
  reviewed_at: string | null;
};

export type PresenzeRecoveryAdjustmentCreateInput = {
  collaborator_id: string;
  adjustment_date: string;
  delta_days: number;
  kind?: "credit" | "debit" | "correction";
  reason: string;
  note?: string | null;
};

export type PresenzeRecoveryAdjustmentUpdateInput = Partial<Omit<PresenzeRecoveryAdjustmentCreateInput, "collaborator_id">>;

export type PresenzeRecoveryAdjustmentReviewInput = {
  approval_status: "approved" | "rejected";
  approval_note?: string | null;
};

export type PresenzeRecoveryBalanceItem = {
  collaborator_id: string;
  employee_code: string;
  collaborator_name: string;
  company_code: string | null;
  application_user_id: number | null;
  matured_days: number;
  used_days: number;
  manual_delta_days: number;
  balance_days: number;
  pending_validation_count: number;
  manual_adjustment_count: number;
  pending_adjustment_count: number;
  last_matured_date: string | null;
  last_used_date: string | null;
  last_adjustment_date: string | null;
  last_adjustment_status: "pending" | "approved" | "rejected" | null;
};

export type PresenzeRecoveryDashboardResponse = {
  date_from: string | null;
  date_to: string | null;
  collaborators_total: number;
  matured_days_total: number;
  used_days_total: number;
  manual_delta_days_total: number;
  balance_days_total: number;
  pending_validation_total: number;
  pending_adjustments_total: number;
  negative_balance_total: number;
  items: PresenzeRecoveryBalanceItem[];
};

export type PresenzeBankHoursAdjustment = {
  id: string;
  collaborator_id: string;
  adjustment_date: string;
  delta_minutes: number;
  kind: "credit" | "debit" | "liquidation" | "correction";
  approval_status: "pending" | "approved" | "rejected";
  reason: string;
  note: string | null;
  approval_note: string | null;
  created_by_user_id: number | null;
  updated_by_user_id: number | null;
  reviewed_by_user_id: number | null;
  created_by_label: string | null;
  updated_by_label: string | null;
  reviewed_by_label: string | null;
  created_at: string;
  updated_at: string;
  reviewed_at: string | null;
};

export type PresenzeBankHoursAdjustmentCreateInput = {
  collaborator_id: string;
  adjustment_date: string;
  delta_minutes: number;
  kind?: "credit" | "debit" | "liquidation" | "correction";
  reason: string;
  note?: string | null;
};

export type PresenzeBankHoursAdjustmentUpdateInput = Partial<Omit<PresenzeBankHoursAdjustmentCreateInput, "collaborator_id">>;

export type PresenzeBankHoursAdjustmentReviewInput = {
  approval_status: "approved" | "rejected";
  approval_note?: string | null;
};
