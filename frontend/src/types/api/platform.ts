export type LoginResponse = {
  access_token: string;
  token_type: string;
};

export type AuthProvidersResponse = {
  password: boolean;
  google: boolean;
};

export type PasswordResetRequestResult = {
  message: string;
};

export type PasswordResetInfo = {
  username: string;
  email: string;
  full_name: string | null;
  expires_at: string;
};

export type PasswordResetConfirmResult = {
  username: string;
  message: string;
};

export type CurrentUser = {
  id: number;
  username: string;
  email: string;
  role: string;
  is_active: boolean;
  module_accessi: boolean;
  module_rete: boolean;
  module_inventario: boolean;
  module_gis?: boolean;
  module_catasto: boolean;
  module_utenze: boolean;
  module_operazioni: boolean;
  module_riordino: boolean;
  module_ruolo: boolean;
  module_presenze: boolean;
  enabled_modules: string[];
};

export type OperationalSearchModule = "utenze" | "ruolo" | "catasto";

export type OperationalSearchResult = {
  id: string;
  module: OperationalSearchModule;
  type: string;
  title: string;
  subtitle: string;
  description: string | null;
  href: string;
  score: number;
  metadata: Record<string, unknown>;
};

export type OperationalSearchResponse = {
  query: string;
  items: OperationalSearchResult[];
  total: number;
  modules: OperationalSearchModule[];
};

export type UserPresenceHeartbeatInput = {
  path: string;
  route_label?: string | null;
  module_key?: string | null;
  action_label?: string | null;
  visible: boolean;
};

export type UserPresenceHeartbeatResponse = {
  ok: boolean;
  last_seen_at: string;
};

export type UserPresenceRecentRoute = {
  path: string;
  route_label: string | null;
  module_key: string | null;
  seen_at: string;
};

export type UserPresenceRecentAction = {
  action_label: string;
  occurred_at: string;
};

export type UserPresenceSummaryItem = {
  user_id: number;
  username: string;
  full_name: string | null;
  role: string;
  module_key: string | null;
  route_label: string | null;
  action_label: string | null;
  path: string;
  visible: boolean;
  last_seen_at: string;
  minutes_since_last_seen: number;
  last_login_at: string | null;
  recent_routes: UserPresenceRecentRoute[];
  recent_actions: UserPresenceRecentAction[];
};

export type UserPresenceModuleBucket = {
  module_key: string;
  count: number;
};

export type UserPresenceSummary = {
  window_minutes: number;
  active_users: number;
  visible_users: number;
  items: UserPresenceSummaryItem[];
  by_module: UserPresenceModuleBucket[];
};

export type MeCapabilities = {
  presenze: boolean;
  operazioni: boolean;
  network: boolean;
};

export type MeModuleStatusResponse = {
  module: string;
  enabled: boolean;
  username: string;
  capabilities: MeCapabilities;
  message: string;
};

export type MePresenzeStatusResponse = {
  module: string;
  enabled: boolean;
  mapped: boolean;
  collaborator_id: string | null;
  collaborator_name: string | null;
  employee_code: string | null;
  message: string;
};

export type MeStraordinariPreviewItem = {
  record_id: string;
  work_date: string;
  motivation: string;
  start_time: string | null;
  end_time: string | null;
  duration_minutes: number;
  duration_label: string;
  original_duration_minutes: number;
  pause_deduction_minutes: number;
  lunch_break_minutes: number | null;
  duration_adjustment_reason: string | null;
};

export type MeStraordinariPreviewResponse = {
  collaborator: {
    id: string;
    name: string;
    employee_code: string;
  };
  period_start: string;
  period_end: string;
  items: MeStraordinariPreviewItem[];
};

export type MeStraordinariExportRequest = {
  items: Array<{
    record_id: string;
    motivation: string;
  }>;
};

export type MeSummaryResponse = {
  period_start: string;
  period_end: string;
  ordinary_minutes: number;
  extra_minutes: number;
  absence_minutes: number;
  worked_days: number;
  anomaly_days: number;
  km_from_presenze: number;
  activities_count: number;
  activity_minutes: number;
  reports_count: number;
  assigned_cases_count: number;
  open_cases_count: number;
  closed_cases_count: number;
  vehicle_sessions_count: number;
  vehicle_km: number;
  assigned_devices_count: number;
  active_vehicle_assignments_count: number;
};

export type MeOperazioniSummaryStatusItem = {
  status: string;
  count: number;
};

export type MeOperazioniSummaryCategoryItem = {
  category: string;
  count: number;
};

export type MeOperazioniSummaryResponse = {
  period_start: string;
  period_end: string;
  activities_count: number;
  activity_minutes: number;
  reports_count: number;
  assigned_cases_count: number;
  open_cases_count: number;
  closed_cases_count: number;
  vehicle_sessions_count: number;
  vehicle_km: number;
  distinct_vehicles_count: number;
  activity_statuses: MeOperazioniSummaryStatusItem[];
  activity_categories: MeOperazioniSummaryCategoryItem[];
};

export type MeOperazioniActivity = {
  id: string;
  activity_catalog_id: string;
  activity_name: string | null;
  activity_category: string | null;
  vehicle_id: string | null;
  vehicle_name: string | null;
  vehicle_plate_number: string | null;
  status: string;
  started_at: string;
  ended_at: string | null;
  duration_minutes: number | null;
  text_note: string | null;
  review_outcome: string | null;
  review_note: string | null;
  submitted_at: string | null;
  created_at: string;
};

export type MeOperazioniActivityListResponse = {
  items: MeOperazioniActivity[];
  total: number;
  page: number;
  page_size: number;
};

export type MeOperazioniReport = {
  id: string;
  report_number: string;
  title: string;
  description: string | null;
  status: string;
  category_name: string | null;
  severity_name: string | null;
  vehicle_name: string | null;
  vehicle_plate_number: string | null;
  created_at: string;
  updated_at: string;
};

export type MeOperazioniReportListResponse = {
  items: MeOperazioniReport[];
  total: number;
  page: number;
  page_size: number;
};

export type MeOperazioniCase = {
  id: string;
  case_number: string;
  title: string;
  status: string;
  priority_rank: number | null;
  category_name: string | null;
  severity_name: string | null;
  source_report_number: string | null;
  created_at: string;
  updated_at: string;
  started_at: string | null;
  resolved_at: string | null;
  closed_at: string | null;
};

export type MeOperazioniCaseListResponse = {
  items: MeOperazioniCase[];
  total: number;
  page: number;
  page_size: number;
};

export type MeVehicleUsageSession = {
  id: string;
  vehicle_id: string;
  vehicle_name: string | null;
  vehicle_plate_number: string | null;
  status: string;
  started_at: string;
  ended_at: string | null;
  km: number;
  notes: string | null;
  operator_name: string | null;
  created_at: string;
};

export type MeVehicleUsageSessionListResponse = {
  items: MeVehicleUsageSession[];
  total: number;
  page: number;
  page_size: number;
};

export type MeAssignedDevice = {
  id: number;
  ip_address: string;
  hostname: string | null;
  display_name: string | null;
  resolved_label: string;
  lifecycle_state: string;
  status: string;
  device_type: string | null;
  operating_system: string | null;
  asset_label: string | null;
  location_hint: string | null;
  last_seen_at: string;
  updated_at: string;
};

export type MeAssignedDeviceListResponse = {
  items: MeAssignedDevice[];
  total: number;
};

export type MeVehicleAssignment = {
  id: string;
  vehicle_id: string;
  vehicle_name: string;
  vehicle_plate_number: string | null;
  vehicle_type: string;
  assignment_target_type: string;
  start_at: string;
  end_at: string | null;
  reason: string | null;
  notes: string | null;
  is_active: boolean;
};

export type MeVehicleAssignmentListResponse = {
  items: MeVehicleAssignment[];
  total: number;
};

export type ResolvedSectionPermission = {
  section_key: string;
  section_label: string;
  module: string;
  is_granted: boolean;
  source: string;
};

export type MyPermissionsResponse = {
  sections: ResolvedSectionPermission[];
  granted_keys: string[];
};

export type ApplicationUser = {
  id: number;
  username: string;
  email: string;
  full_name: string | null;
  office_location: string | null;
  phone_extension: string | null;
  role: string;
  is_active: boolean;
  module_accessi: boolean;
  module_rete: boolean;
  module_inventario: boolean;
  module_gis: boolean;
  module_catasto: boolean;
  module_utenze: boolean;
  module_operazioni: boolean;
  module_riordino: boolean;
  module_ruolo: boolean;
  module_presenze: boolean;
  enabled_modules: string[];
  created_at: string;
  last_login_at: string | null;
  last_login_ip: string | null;
  login_count: number;
  gate_mobile_console: {
    operator_id: string;
    enabled: boolean;
    role: string | null;
  } | null;
  updated_at: string;
};

export type ApplicationUserListResponse = {
  items: ApplicationUser[];
  total: number;
};

export type UserSectionPermissionResponse = {
  id: number;
  user_id: number;
  section_id: number;
  is_granted: boolean;
  granted_by_id: number | null;
  created_at: string;
  updated_at: string;
};

export type UserPermissionsAdminView = {
  user_id: number;
  username: string;
  role: string;
  resolved: ResolvedSectionPermission[];
  overrides: UserSectionPermissionResponse[];
};

export type SectionResponse = {
  id: number;
  module: string;
  key: string;
  label: string;
  description: string | null;
  min_role: string;
  is_active: boolean;
  sort_order: number;
  created_at: string;
  updated_at: string;
};

export type ApplicationUserCreateInput = {
  username: string;
  email: string;
  full_name?: string | null;
  office_location?: string | null;
  phone_extension?: string | null;
  password?: string | null;
  role: string;
  is_active: boolean;
  module_accessi: boolean;
  module_rete: boolean;
  module_inventario: boolean;
  module_gis: boolean;
  module_catasto: boolean;
  module_utenze: boolean;
  module_operazioni: boolean;
  module_riordino: boolean;
  module_ruolo?: boolean;
  module_presenze?: boolean;
};

export type ApplicationUserInviteResponse = {
  user_id: number;
  email: string;
  expires_at: string;
  activation_url: string;
  activation_url_path: string;
  email_sent: boolean;
};

export type ApplicationUserUpdateInput = {
  email?: string;
  full_name?: string | null;
  office_location?: string | null;
  phone_extension?: string | null;
  password?: string;
  role?: string;
  is_active?: boolean;
  module_accessi?: boolean;
  module_rete?: boolean;
  module_inventario?: boolean;
  module_gis?: boolean;
  module_catasto?: boolean;
  module_utenze?: boolean;
  module_operazioni?: boolean;
  module_riordino?: boolean;
  module_ruolo?: boolean;
  module_presenze?: boolean;
};

export type OrgStructureUserSummary = {
  id: number;
  username: string;
  email: string;
  full_name: string | null;
  role: string;
  is_active: boolean;
};

export type OrgStructureAssignment = {
  id: string;
  application_user_id: number;
  manager_user_id: number | null;
  source_mode: string;
  title: string | null;
  area_label: string | null;
  notes: string | null;
  is_active: boolean;
  source_wc_role: string | null;
  source_chart_summary: string | null;
  last_synced_from_source_at: string | null;
  created_at: string;
  updated_at: string;
  user: OrgStructureUserSummary;
  manager: OrgStructureUserSummary | null;
  direct_reports_count: number;
  descendants_count: number;
  depth: number;
};

export type OrgStructureSuggestion = {
  application_user_id: number;
  wc_operator_id: string | null;
  username: string;
  full_name: string | null;
  email: string;
  role: string;
  wc_role: string | null;
  chart_summary: string | null;
  already_published: boolean;
};

export type OrgStructureMetrics = {
  total_users: number;
  published_nodes: number;
  root_nodes: number;
  unassigned_users: number;
  linked_whitecompany_users: number;
};

export type OrgStructureWorkspace = {
  items: OrgStructureAssignment[];
  suggestions: OrgStructureSuggestion[];
  metrics: OrgStructureMetrics;
};

export type OrgStructureAssignmentUpdateInput = {
  manager_user_id?: number | null;
  title?: string | null;
  area_label?: string | null;
  notes?: string | null;
  is_active: boolean;
};

export type OrgStructureBootstrapResult = {
  created: number;
  updated: number;
  skipped: number;
};
