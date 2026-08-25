import { defaultLeadPositionCode, defaultLeadTitle } from "@/features/organigramma/organigramma-config";
import type { OrgAssignment, OrgAssignmentCreateInput, OrgUnit, OrgUnitTreeNode, OrgUnitType } from "@/types/api";

export type UserAssignmentMode = "member" | "lead";

type BuildAssignmentParams = {
  userId: number;
  unit: Pick<OrgUnit, "id" | "tipo"> | Pick<OrgUnitTreeNode, "id" | "tipo">;
  mode: UserAssignmentMode;
  unitLeadUserId: number | null;
  parentLeadUserId: number | null;
};

type UnitLeadMap = Map<string, { lead: { user_id: number } | null }>;

export function resolveManagerUserIds(
  unit: Pick<OrgUnitTreeNode, "id" | "parent_id">,
  unitLeadMap: UnitLeadMap,
): Pick<BuildAssignmentParams, "unitLeadUserId" | "parentLeadUserId"> {
  return {
    unitLeadUserId: unitLeadMap.get(unit.id)?.lead?.user_id ?? null,
    parentLeadUserId: unit.parent_id ? unitLeadMap.get(unit.parent_id)?.lead?.user_id ?? null : null,
  };
}

export function buildAssignmentPayload(params: BuildAssignmentParams): OrgAssignmentCreateInput {
  const isLead = params.mode === "lead";
  return {
    user_id: params.userId,
    org_unit_id: params.unit.id,
    manager_user_id: isLead ? params.parentLeadUserId : params.unitLeadUserId,
    title: isLead ? defaultLeadTitle(params.unit.tipo) : null,
    position_code: isLead ? defaultLeadPositionCode(params.unit.tipo) : "collaboratore",
    is_primary: isLead,
    active: true,
    source: "manuale",
  };
}

export async function syncDirectReportManagers(
  mode: UserAssignmentMode,
  assignments: OrgAssignment[],
  unitId: string,
  managerUserId: number,
  updateManager: (assignmentId: string) => Promise<unknown>,
): Promise<void> {
  if (mode !== "lead") return;
  const directReports = assignments.filter(
    (assignment) => assignment.org_unit_id === unitId && assignment.user_id !== managerUserId,
  );
  await Promise.all(directReports.map((assignment) => updateManager(assignment.id)));
}

export function nextChildUnitType(selectedType: OrgUnitType | undefined): OrgUnitType {
  return {
    direzione: "distretto",
    distretto: "settore",
    settore: "reparto",
    reparto: "squadra",
    squadra: "settore",
  }[selectedType ?? "squadra"] as OrgUnitType;
}

export function isInvalidSectorParent(tipo: OrgUnitType, parentType: OrgUnitType | undefined): boolean {
  return tipo === "settore" && (parentType === "reparto" || parentType === "squadra");
}
