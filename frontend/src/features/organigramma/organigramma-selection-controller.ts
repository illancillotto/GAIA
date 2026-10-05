import type { OrganigrammaSelectionContext } from "@/features/organigramma/organigramma-selection-context";
import type { OrgUnitTreeNode } from "@/types/api";

type HandleBeginSchemaLinkContext = Pick<OrganigrammaSelectionContext, "canModifyStructure" | "schemaEditEnabled" | "setSchemaLinkDraft">;

export function handleBeginSchemaLink({ canModifyStructure, schemaEditEnabled, setSchemaLinkDraft }: HandleBeginSchemaLinkContext, nodeId: string, mode: "above" | "below") {
  if (!canModifyStructure || !schemaEditEnabled) return;
  setSchemaLinkDraft((current) => {
    if (current?.sourceId === nodeId && current.mode === mode) {
      return null;
    }
    return { sourceId: nodeId, mode };
  });
}

type HandleConnectSchemaNodeContext = Pick<OrganigrammaSelectionContext, "schemaLinkDraft" | "performSchemaLink" | "setSchemaLinkDraft">;

export async function handleConnectSchemaNode({ schemaLinkDraft, performSchemaLink, setSchemaLinkDraft }: HandleConnectSchemaNodeContext, targetId: string) {
  if (!schemaLinkDraft) return;
  const { sourceId, mode } = schemaLinkDraft;
  const ok = await performSchemaLink(sourceId, targetId, mode);
  // "above" collects children: keep the draft alive so more blocks can be
  // linked under the same source. "below" picks the single parent, so close it.
  if (!ok || mode === "below") {
    setSchemaLinkDraft(null);
  }
}

type HandleConnectSelectedNodeToTargetContext = Pick<OrganigrammaSelectionContext, "selectedId" | "setSchemaLinkDraft" | "performSchemaLink">;

export async function handleConnectSelectedNodeToTarget({ selectedId, setSchemaLinkDraft, performSchemaLink }: HandleConnectSelectedNodeToTargetContext, targetId: string, mode: "above" | "below") {
  if (!selectedId) return;
  setSchemaLinkDraft(null);
  await performSchemaLink(selectedId, targetId, mode);
}

type HandleSchemaCardSelectContext = Pick<OrganigrammaSelectionContext, "multiSelectedIds" | "setMultiSelectedIds" | "selectedId" | "setSelectedId">;

export function handleSchemaCardSelect({ multiSelectedIds, setMultiSelectedIds, selectedId, setSelectedId }: HandleSchemaCardSelectContext, nodeId: string, event?: React.MouseEvent) {
  if (!event || !(event.ctrlKey || event.metaKey || event.shiftKey)) {
    setMultiSelectedIds(new Set());
    setSelectedId(nodeId);
    return;
  }
  const isToggleOff = (event.ctrlKey || event.metaKey) && multiSelectedIds.has(nodeId);
  setMultiSelectedIds((prev) => {
    const next = new Set(prev);
    // Seed the multi-selection with the currently selected card on the first modifier click.
    if (!next.size && selectedId && selectedId !== nodeId) next.add(selectedId);
    if (isToggleOff) {
      next.delete(nodeId);
    } else {
      next.add(nodeId);
    }
    return next;
  });
  if (!isToggleOff) setSelectedId(nodeId);
}

type HandleSchemaCardPointerDownContext = Pick<OrganigrammaSelectionContext, "schemaEditEnabled" | "flatTree" | "multiSelectedIds" | "setSelectedId" | "setMultiSelectedIds" | "safeCanvasCoord" | "setSchemaDragging">;

export function handleSchemaCardPointerDown({ schemaEditEnabled, flatTree, multiSelectedIds, setSelectedId, setMultiSelectedIds, safeCanvasCoord, setSchemaDragging }: HandleSchemaCardPointerDownContext, nodeId: string, event: React.PointerEvent<HTMLDivElement>) {
  if (!schemaEditEnabled || event.button !== 0) return;
  // Modifier clicks are selection gestures (handled on click), not drag starts.
  if (event.ctrlKey || event.metaKey || event.shiftKey) return;
  const target = event.target as HTMLElement | null;
  if (target?.closest("button, input, select, textarea, label, a")) return;
  const node = flatTree.find((entry) => entry.id === nodeId);
  if (!node) return;
  if (typeof event.currentTarget.setPointerCapture === "function") {
    event.currentTarget.setPointerCapture(event.pointerId);
  }
  event.preventDefault();
  event.stopPropagation();
  setSelectedId(nodeId);
  const groupIds = multiSelectedIds.has(nodeId)
    ? Array.from(new Set([nodeId, ...multiSelectedIds]))
    : [nodeId];
  if (!multiSelectedIds.has(nodeId) && multiSelectedIds.size) {
    setMultiSelectedIds(new Set());
  }
  const dragNodes = groupIds
    .map((id) => flatTree.find((entry) => entry.id === id))
    .filter((entry): entry is OrgUnitTreeNode => Boolean(entry))
    .map((entry) => ({
      nodeId: entry.id,
      originX: safeCanvasCoord(entry.canvas_x),
      originY: safeCanvasCoord(entry.canvas_y),
    }));
  setSchemaDragging({
    nodeId,
    pointerId: event.pointerId,
    startX: event.clientX,
    startY: event.clientY,
    nodes: dragNodes,
  });
}

type HandleSchemaCardContextMenuContext = Pick<OrganigrammaSelectionContext, "schemaEditEnabled" | "setSelectedId" | "setSchemaContextMenu">;

export function handleSchemaCardContextMenu({ schemaEditEnabled, setSelectedId, setSchemaContextMenu }: HandleSchemaCardContextMenuContext, nodeId: string, event: React.MouseEvent<HTMLDivElement>) {
  if (!schemaEditEnabled) return;
  event.preventDefault();
  event.stopPropagation();
  setSelectedId(nodeId);
  setSchemaContextMenu({
    nodeId,
    x: event.clientX,
    y: event.clientY,
  });
}
