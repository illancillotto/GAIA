import { createOrgAssignment, createOrgUnit, deleteOrgAssignment, deleteOrgUnit, updateOrgAssignment, updateOrgUnit } from "@/lib/api";
import { buildAssignmentPayload, resolveManagerUserIds, syncDirectReportManagers, type UserAssignmentMode } from "@/features/organigramma/organigramma-assignment";
import type { OrganigrammaMutationContext } from "@/features/organigramma/organigramma-mutation-context";
import type { OrgUnitCreateInput } from "@/types/api";

type HandleMoveNodeContext = Pick<OrganigrammaMutationContext, "token" | "canModifyStructure" | "schemaEditEnabled" | "schemaMeta" | "setNotice" | "structureKind" | "setSelectedId" | "refreshStructure" | "setDraggingNodeId" | "setDraggingUserId">;

export async function handleMoveNode(
  { token, canModifyStructure, schemaEditEnabled, schemaMeta, setNotice, structureKind, setSelectedId, refreshStructure, setDraggingNodeId, setDraggingUserId }: HandleMoveNodeContext,
  nodeId: string,
  parentId: string | null,
) {
  if (!token || !canModifyStructure || !schemaEditEnabled || nodeId === parentId) return;
  const nodeMeta = schemaMeta.get(nodeId);
  if (parentId && nodeMeta?.descendantIds.has(parentId)) {
    setNotice("Operazione non valida: non puoi spostare un nodo dentro un suo discendente.");
    return;
  }
  setNotice(null);
  try {
    await updateOrgUnit(token, nodeId, { parent_id: parentId }, structureKind);
    setSelectedId(nodeId);
    await refreshStructure();
    setNotice(parentId ? "Gerarchia aggiornata." : "Nodo spostato in radice.");
  } catch (err) {
    setNotice(err instanceof Error ? err.message : "Aggiornamento gerarchia non riuscito");
  } finally {
    setDraggingNodeId(null);
    setDraggingUserId(null);
  }
}

type PerformSchemaLinkContext = Pick<OrganigrammaMutationContext, "token" | "canModifyStructure" | "schemaEditEnabled" | "schemaMeta" | "setNotice" | "structureKind" | "setSelectedId" | "refreshStructure">;

export async function performSchemaLink(
  { token, canModifyStructure, schemaEditEnabled, schemaMeta, setNotice, structureKind, setSelectedId, refreshStructure }: PerformSchemaLinkContext,
  sourceId: string,
  targetId: string,
  mode: "above" | "below",
): Promise<boolean> {
  if (!token || !canModifyStructure || !schemaEditEnabled) return false;
  if (sourceId === targetId) return false;

  const sourceMeta = schemaMeta.get(sourceId);
  const targetMeta = schemaMeta.get(targetId);
  if (mode === "below" && sourceMeta?.descendantIds.has(targetId)) {
    setNotice("Collegamento non valido: il blocco sorgente non può finire sotto un suo discendente.");
    return false;
  }
  if (mode === "above" && targetMeta?.descendantIds.has(sourceId)) {
    setNotice("Collegamento non valido: il blocco destinazione non può finire sotto un suo discendente.");
    return false;
  }

  try {
    if (mode === "below") {
      await updateOrgUnit(token, sourceId, { parent_id: targetId }, structureKind);
    } else {
      await updateOrgUnit(token, targetId, { parent_id: sourceId }, structureKind);
    }
    setSelectedId(sourceId);
    setNotice("Collegamento aggiornato.");
    await refreshStructure();
    return true;
  } catch (err) {
    setNotice(err instanceof Error ? err.message : "Aggiornamento collegamento non riuscito");
    return false;
  }
}

type HandleAssignUserToUnitContext = Pick<OrganigrammaMutationContext, "token" | "canModifyStructure" | "schemaEditEnabled" | "schemaMeta" | "flatTree" | "users" | "assignedUserIds" | "setNotice" | "setDraggingUserId" | "allAssignments" | "structureKind" | "refreshStructure">;

export async function handleAssignUserToUnit(
  { token, canModifyStructure, schemaEditEnabled, schemaMeta, flatTree, users, assignedUserIds, setNotice, setDraggingUserId, allAssignments, structureKind, refreshStructure }: HandleAssignUserToUnitContext,
  userId: number,
  unitId: string,
  mode: UserAssignmentMode,
) {
  if (!token || !canModifyStructure || !schemaEditEnabled) return;
  const unitMeta = schemaMeta.get(unitId);
  const unit = flatTree.find((entry) => entry.id === unitId);
  const user = users.find((entry) => entry.id === userId);
  if (!unit || !user) return;
  if (assignedUserIds.has(userId)) {
    setNotice("Questo utente risulta già assegnato a una unità.");
    setDraggingUserId(null);
    return;
  }
  if (mode === "lead" && unitMeta?.lead) {
    setNotice("L'unità ha già un responsabile diretto. Spostalo o sostituiscilo prima di assegnarne un altro.");
    setDraggingUserId(null);
    return;
  }

  const payload = buildAssignmentPayload({ userId, unit, mode, ...resolveManagerUserIds(unit, schemaMeta) });

  try {
    await createOrgAssignment(token, payload, structureKind);
    await syncDirectReportManagers(mode, allAssignments, unitId, userId, (assignmentId) =>
      updateOrgAssignment(token, assignmentId, { manager_user_id: userId }, structureKind),
    );
    setNotice(
      mode === "lead"
        ? `${user.full_name ?? user.username} impostato come responsabile di ${unit.nome}.`
        : `${user.full_name ?? user.username} assegnato a ${unit.nome}.`,
    );
    await refreshStructure();
  } catch (err) {
    setNotice(err instanceof Error ? err.message : "Assegnazione non riuscita");
  } finally {
    setDraggingUserId(null);
  }
}

type HandleCreateUnitContext = Pick<OrganigrammaMutationContext, "token" | "canModifyStructure" | "flatTree" | "structureKind" | "setCreateUnitPreset" | "setSelectedId" | "setNotice" | "refreshStructure">;

export async function handleCreateUnit(
  { token, canModifyStructure, flatTree, structureKind, setCreateUnitPreset, setSelectedId, setNotice, refreshStructure }: HandleCreateUnitContext,
  payload: OrgUnitCreateInput,
  responsibleUserId: number | null,
) {
  if (!token || !canModifyStructure) return;
  try {
    const parentUnit = payload.parent_id ? flatTree.find((entry) => entry.id === payload.parent_id) : null;
    const seededPayload: OrgUnitCreateInput = {
      ...payload,
      canvas_x: payload.canvas_x ?? (parentUnit ? parentUnit.canvas_x + 320 : 120),
      canvas_y: payload.canvas_y ?? (parentUnit ? parentUnit.canvas_y + 220 : 120 + flatTree.length * 40),
    };
    const created = await createOrgUnit(token, seededPayload, structureKind);
    if (responsibleUserId != null) {
      await createOrgAssignment(token, buildAssignmentPayload({
        userId: responsibleUserId, unit: created, mode: "lead", unitLeadUserId: null, parentLeadUserId: null,
      }), structureKind);
    }
    setCreateUnitPreset(null);
    setSelectedId(created.id);
    setNotice(`Unità ${created.nome} creata correttamente.`);
    await refreshStructure();
  } catch (err) {
    setNotice(err instanceof Error ? err.message : "Creazione unità non riuscita");
  }
}

type HandleDetachAssignmentContext = Pick<OrganigrammaMutationContext, "token" | "canModifyStructure" | "schemaEditEnabled" | "structureKind" | "setNotice" | "entityLabel" | "refreshStructure">;

export async function handleDetachAssignment(
  { token, canModifyStructure, schemaEditEnabled, structureKind, setNotice, entityLabel, refreshStructure }: HandleDetachAssignmentContext,
  assignmentId: string,
) {
  if (!token || !canModifyStructure || !schemaEditEnabled) return;
  try {
    await deleteOrgAssignment(token, assignmentId, structureKind);
    setNotice(`Assegnazione rimossa da ${entityLabel}.`);
    await refreshStructure();
  } catch (err) {
    setNotice(err instanceof Error ? err.message : "Rimozione assegnazione non riuscita");
  }
}

type HandleDeleteUnitContext = Pick<OrganigrammaMutationContext, "token" | "canModifyStructure" | "schemaEditEnabled" | "flatTree" | "schemaMeta" | "setNotice" | "structureKind" | "setSchemaContextMenu" | "setDetail" | "setSelectedId" | "setMultiSelectedIds" | "entityLabel" | "refreshStructure">;

export async function handleDeleteUnit(
  { token, canModifyStructure, schemaEditEnabled, flatTree, schemaMeta, setNotice, structureKind, setSchemaContextMenu, setDetail, setSelectedId, setMultiSelectedIds, entityLabel, refreshStructure }: HandleDeleteUnitContext,
  nodeId: string,
) {
  if (!token || !canModifyStructure || !schemaEditEnabled) return;
  const node = flatTree.find((entry) => entry.id === nodeId);
  const nodeSummary = schemaMeta.get(nodeId);
  if (!node || !nodeSummary) return;
  if (nodeSummary.descendantIds.size > 1) {
    setNotice("Non puoi eliminare un blocco che contiene sotto-unità. Scollega o rimuovi prima i blocchi figli.");
    return;
  }
  if (nodeSummary.directPeople > 0) {
    setNotice("Non puoi eliminare un blocco con assegnazioni dirette. Rimuovi prima le persone assegnate.");
    return;
  }
  const confirmed = window.confirm(`Eliminare definitivamente il blocco “${node.nome}”?`);
  if (!confirmed) return;
  try {
    await deleteOrgUnit(token, nodeId, structureKind);
    setSchemaContextMenu(null);
    setDetail(null);
    setSelectedId((current) => (current === nodeId ? null : current));
    setMultiSelectedIds((prev) => {
      if (!prev.has(nodeId)) return prev;
      const next = new Set(prev);
      next.delete(nodeId);
      return next;
    });
    setNotice(`Blocco “${node.nome}” eliminato da ${entityLabel}.`);
    await refreshStructure();
  } catch (err) {
    setNotice(err instanceof Error ? err.message : "Eliminazione blocco non riuscita");
  }
}
