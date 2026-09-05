// --- Organigramma (canonical layer) ---------------------------------------
export type OrgUnitType = "direzione" | "distretto" | "settore" | "reparto" | "squadra";

export type OrgPositionCode = "dirigente" | "capo_settore" | "capo_operai" | "capo_reparto" | "collaboratore";

export type OrgSource = "manuale" | "whitecompany" | "bridge_team";

export type OrgOverrideTargetType = "user" | "org_unit";

export type OrgOverrideScope = "read" | "approve" | "full";

export type OrgOverrideStatus = "attivo" | "programmato" | "scaduto" | "disattivato";

export type OrgVisibilityVia = "gerarchia" | "override";

export type OrgPersonRef = {
  user_id: number;
  full_name: string | null;
  username: string;
  email: string;
  rbac_role: string;
  is_active: boolean;
};

export type OrgUnit = {
  id: string;
  nome: string;
  tipo: OrgUnitType;
  parent_id: string | null;
  is_active: boolean;
  sort_order: number;
  canvas_x: number;
  canvas_y: number;
  source: OrgSource;
  wc_area_id: string | null;
  legacy_team_id: string | null;
  created_at: string;
  updated_at: string;
};

export type OrgUnitTreeNode = {
  id: string;
  nome: string;
  tipo: OrgUnitType;
  parent_id: string | null;
  canvas_x: number;
  canvas_y: number;
  source: OrgSource;
  wc_area_id: string | null;
  legacy_team_id: string | null;
  is_active: boolean;
  sort_order: number;
  person_count: number;
  child_count: number;
  children: OrgUnitTreeNode[];
};

export type OrgAssignment = {
  id: string;
  user_id: number;
  org_unit_id: string;
  manager_user_id: number | null;
  title: string | null;
  position_code: OrgPositionCode | null;
  is_primary: boolean;
  active: boolean;
  valid_from: string | null;
  valid_to: string | null;
  source: OrgSource;
  wc_operator_id: string | null;
  created_at: string;
  updated_at: string;
  person: OrgPersonRef | null;
  manager: OrgPersonRef | null;
};

export type OrgUnitDetail = {
  unit: OrgUnit;
  path: OrgUnit[];
  responsabile: OrgPersonRef | null;
  responsabile_title: string | null;
  assignments: OrgAssignment[];
};

export type OrgVisibilityOverride = {
  id: string;
  viewer_user_id: number;
  target_type: OrgOverrideTargetType;
  target_user_id: number | null;
  target_org_unit_id: string | null;
  scope: OrgOverrideScope;
  motivo: string | null;
  valid_from: string | null;
  valid_to: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  status: OrgOverrideStatus | null;
  viewer: OrgPersonRef | null;
  target_label: string | null;
};

export type OrgVisibleUnit = {
  org_unit_id: string;
  nome: string;
  tipo: OrgUnitType;
  parent_id: string | null;
  via: OrgVisibilityVia;
  scope: OrgOverrideScope | null;
};

export type OrgVisiblePerson = {
  user_id: number;
  full_name: string | null;
  title: string | null;
  org_unit_id: string | null;
  via: OrgVisibilityVia;
  scope: OrgOverrideScope;
};

export type OrgVisibilityResult = {
  viewer: OrgPersonRef;
  full: boolean;
  units: OrgVisibleUnit[];
  people: OrgVisiblePerson[];
};

export type OrgStructureKind = "organigramma" | "territoriale";

export type OrgUnitCreateInput = {
  nome: string;
  tipo: OrgUnitType;
  parent_id?: string | null;
  is_active?: boolean;
  source?: OrgSource;
  sort_order?: number;
  canvas_x?: number;
  canvas_y?: number;
  wc_area_id?: string | null;
  legacy_team_id?: string | null;
};

export type OrgUnitUpdateInput = {
  nome?: string;
  tipo?: OrgUnitType;
  parent_id?: string | null;
  is_active?: boolean;
  source?: OrgSource;
  sort_order?: number;
  canvas_x?: number;
  canvas_y?: number;
  wc_area_id?: string | null;
  legacy_team_id?: string | null;
};

export type OrgAssignmentCreateInput = {
  user_id: number;
  org_unit_id: string;
  manager_user_id?: number | null;
  title?: string | null;
  position_code?: OrgPositionCode | null;
  is_primary?: boolean;
  active?: boolean;
  valid_from?: string | null;
  valid_to?: string | null;
  source?: OrgSource;
  wc_operator_id?: string | null;
};

export type OrgAssignmentUpdateInput = {
  org_unit_id?: string;
  manager_user_id?: number | null;
  title?: string | null;
  position_code?: OrgPositionCode | null;
  is_primary?: boolean;
  active?: boolean;
  valid_from?: string | null;
  valid_to?: string | null;
  source?: OrgSource;
  wc_operator_id?: string | null;
};

export type OrgVisibilityOverrideCreateInput = {
  viewer_user_id: number;
  target_type: OrgOverrideTargetType;
  target_user_id?: number | null;
  target_org_unit_id?: string | null;
  scope: OrgOverrideScope;
  motivo?: string | null;
  valid_from?: string | null;
  valid_to?: string | null;
};

export type OrgVisibilityOverrideUpdateInput = {
  scope?: OrgOverrideScope;
  motivo?: string | null;
  valid_from?: string | null;
  valid_to?: string | null;
  is_active?: boolean;
};

export type OrgWhiteCompanySyncResult = {
  units_created: number;
  units_updated: number;
  units_skipped_locked: number;
  assignments_created: number;
  assignments_updated: number;
  assignments_skipped_locked: number;
  message: string;
};

export type OrgImportMode = "merge" | "replace";

export type OrganigrammaSnapshot = {
  schema_version: number;
  exported_at: string | null;
  exported_by_user_id: number | null;
  exported_by_username: string | null;
  units: (OrgUnitCreateInput & { id: string })[];
  assignments: (OrgAssignmentCreateInput & { id: string })[];
  overrides: (OrgVisibilityOverrideCreateInput & { id: string; is_active: boolean })[];
};

export type OrganigrammaImportResponse = {
  mode: OrgImportMode;
  units_created: number;
  units_updated: number;
  assignments_created: number;
  assignments_updated: number;
  overrides_created: number;
  overrides_updated: number;
};
