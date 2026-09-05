import type { OrganigrammaImportResponse, OrganigrammaSnapshot, OrgAssignment, OrgAssignmentCreateInput, OrgAssignmentUpdateInput, OrgStructureKind, OrgImportMode, OrgUnit, OrgUnitCreateInput, OrgUnitDetail, OrgUnitTreeNode, OrgUnitUpdateInput, OrgVisibilityOverride, OrgVisibilityOverrideCreateInput, OrgVisibilityOverrideUpdateInput, OrgVisibilityResult, OrgWhiteCompanySyncResult } from "@/types/api";
import { request } from "./core";

function authHeaders(token: string): HeadersInit {
  return { Authorization: `Bearer ${token}` };
}

export async function getOrgUnits(
  token: string,
  params: { parentId?: string; structureKind?: OrgStructureKind } = {},
): Promise<OrgUnit[]> {
  const query = new URLSearchParams();
  if (params.parentId) query.set("parent_id", params.parentId);
  if (params.structureKind) query.set("structure_kind", params.structureKind);
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return request<OrgUnit[]>(`/organigramma/units${suffix}`, { headers: authHeaders(token) });
}

export async function getOrgTree(token: string, structureKind: OrgStructureKind = "organigramma"): Promise<OrgUnitTreeNode[]> {
  return request<OrgUnitTreeNode[]>(`/organigramma/units/tree?structure_kind=${structureKind}`, { headers: authHeaders(token) });
}

export async function getOrgUnit(
  token: string,
  unitId: string,
  structureKind: OrgStructureKind = "organigramma",
): Promise<OrgUnitDetail> {
  return request<OrgUnitDetail>(`/organigramma/units/${unitId}?structure_kind=${structureKind}`, { headers: authHeaders(token) });
}

export async function createOrgUnit(
  token: string,
  payload: OrgUnitCreateInput,
  structureKind: OrgStructureKind = "organigramma",
): Promise<OrgUnit> {
  return request<OrgUnit>(`/organigramma/units?structure_kind=${structureKind}`, {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify(payload),
  });
}

export async function updateOrgUnit(
  token: string,
  unitId: string,
  payload: OrgUnitUpdateInput,
  structureKind: OrgStructureKind = "organigramma",
): Promise<OrgUnit> {
  return request<OrgUnit>(`/organigramma/units/${unitId}?structure_kind=${structureKind}`, {
    method: "PUT",
    headers: authHeaders(token),
    body: JSON.stringify(payload),
  });
}

export async function deleteOrgUnit(
  token: string,
  unitId: string,
  structureKind: OrgStructureKind = "organigramma",
): Promise<void> {
  await request<void>(`/organigramma/units/${unitId}?structure_kind=${structureKind}`, { method: "DELETE", headers: authHeaders(token) });
}

export async function getOrgAssignments(
  token: string,
  params: { unitId?: string; userId?: number; structureKind?: OrgStructureKind } = {},
): Promise<OrgAssignment[]> {
  const query = new URLSearchParams();
  if (params.unitId) query.set("unit_id", params.unitId);
  if (params.userId != null) query.set("user_id", String(params.userId));
  if (params.structureKind) query.set("structure_kind", params.structureKind);
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return request<OrgAssignment[]>(`/organigramma/assignments${suffix}`, { headers: authHeaders(token) });
}

export async function createOrgAssignment(
  token: string,
  payload: OrgAssignmentCreateInput,
  structureKind: OrgStructureKind = "organigramma",
): Promise<OrgAssignment> {
  return request<OrgAssignment>(`/organigramma/assignments?structure_kind=${structureKind}`, {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify(payload),
  });
}

export async function updateOrgAssignment(
  token: string,
  assignmentId: string,
  payload: OrgAssignmentUpdateInput,
  structureKind: OrgStructureKind = "organigramma",
): Promise<OrgAssignment> {
  return request<OrgAssignment>(`/organigramma/assignments/${assignmentId}?structure_kind=${structureKind}`, {
    method: "PUT",
    headers: authHeaders(token),
    body: JSON.stringify(payload),
  });
}

export async function deleteOrgAssignment(
  token: string,
  assignmentId: string,
  structureKind: OrgStructureKind = "organigramma",
): Promise<void> {
  await request<void>(`/organigramma/assignments/${assignmentId}?structure_kind=${structureKind}`, {
    method: "DELETE",
    headers: authHeaders(token),
  });
}

export async function getOrgOverrides(
  token: string,
  structureKind: OrgStructureKind = "organigramma",
): Promise<OrgVisibilityOverride[]> {
  return request<OrgVisibilityOverride[]>(`/organigramma/overrides?structure_kind=${structureKind}`, { headers: authHeaders(token) });
}

export async function createOrgOverride(
  token: string,
  payload: OrgVisibilityOverrideCreateInput,
  structureKind: OrgStructureKind = "organigramma",
): Promise<OrgVisibilityOverride> {
  return request<OrgVisibilityOverride>(`/organigramma/overrides?structure_kind=${structureKind}`, {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify(payload),
  });
}

export async function updateOrgOverride(
  token: string,
  overrideId: string,
  payload: OrgVisibilityOverrideUpdateInput,
  structureKind: OrgStructureKind = "organigramma",
): Promise<OrgVisibilityOverride> {
  return request<OrgVisibilityOverride>(`/organigramma/overrides/${overrideId}?structure_kind=${structureKind}`, {
    method: "PUT",
    headers: authHeaders(token),
    body: JSON.stringify(payload),
  });
}

export async function deleteOrgOverride(
  token: string,
  overrideId: string,
  structureKind: OrgStructureKind = "organigramma",
): Promise<void> {
  await request<void>(`/organigramma/overrides/${overrideId}?structure_kind=${structureKind}`, { method: "DELETE", headers: authHeaders(token) });
}

export async function getOrgVisibility(
  token: string,
  userId: number,
  structureKind: OrgStructureKind = "organigramma",
): Promise<OrgVisibilityResult> {
  return request<OrgVisibilityResult>(`/organigramma/visibility/${userId}?structure_kind=${structureKind}`, { headers: authHeaders(token) });
}

export async function syncOrgWhiteCompany(token: string): Promise<OrgWhiteCompanySyncResult> {
  return request<OrgWhiteCompanySyncResult>("/organigramma/sync/whitecompany", {
    method: "POST",
    headers: authHeaders(token),
  });
}

export async function exportOrganigrammaSnapshot(
  token: string,
  structureKind: OrgStructureKind = "organigramma",
): Promise<OrganigrammaSnapshot> {
  return request<OrganigrammaSnapshot>(`/organigramma/io/export?structure_kind=${structureKind}`, {
    headers: authHeaders(token),
  });
}

export async function importOrganigrammaSnapshot(
  token: string,
  snapshot: OrganigrammaSnapshot,
  mode: OrgImportMode = "merge",
  structureKind: OrgStructureKind = "organigramma",
): Promise<OrganigrammaImportResponse> {
  return request<OrganigrammaImportResponse>(`/organigramma/io/import?mode=${mode}&structure_kind=${structureKind}`, {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify(snapshot),
  });
}
