import { updateOrgUnit } from "@/lib/api";
import { flattenTree } from "@/lib/organigramma";
import type { OrganigrammaLayoutContext } from "@/features/organigramma/organigramma-layout-context";

type SchemaDisplayPosition = { x: number; y: number };
type SchemaOrientation = "horizontal" | "vertical";

type ResolveSectorParentIdContext = Pick<OrganigrammaLayoutContext, "selectedNode" | "selectedSector" | "selectedId">;

export function resolveSectorParentId({ selectedNode, selectedSector, selectedId }: ResolveSectorParentIdContext) {
  if (selectedNode?.tipo === "distretto" || selectedNode?.tipo === "direzione") {
    return selectedNode.id;
  }
  if (selectedNode?.tipo === "settore") {
    return selectedNode.parent_id;
  }
  if (selectedSector?.parent_id) {
    return selectedSector.parent_id;
  }
  return selectedId;
}

type RealignExpandedSubtreeContext = Pick<OrganigrammaLayoutContext, "flatTree" | "schemaOrientation" | "safeCanvasCoord" | "computeHorizontalTreeLayout" | "computeVerticalTreeLayout" | "snapCoordinate" | "resolveSubtreeCollisionShift" | "setTree" | "applyCanvasPositionsToForest" | "token" | "canModifyStructure" | "structureKind">;

export async function realignExpandedSubtree({ flatTree, schemaOrientation, safeCanvasCoord, computeHorizontalTreeLayout, computeVerticalTreeLayout, snapCoordinate, resolveSubtreeCollisionShift, setTree, applyCanvasPositionsToForest, token, canModifyStructure, structureKind }: RealignExpandedSubtreeContext, nodeId: string) {
  const expandedNode = flatTree.find((node) => node.id === nodeId);
  if (!expandedNode || !expandedNode.children.length) return;
  const subtreeRoot = expandedNode.parent_id
    ? flatTree.find((node) => node.id === expandedNode.parent_id) ?? expandedNode
    : expandedNode;
  if (!subtreeRoot.children.length) return;

  const layout = schemaOrientation === "horizontal"
    ? computeHorizontalTreeLayout([subtreeRoot])
    : computeVerticalTreeLayout([subtreeRoot]);
  const rootLayout = layout.get(subtreeRoot.id)!;

  const rootX = safeCanvasCoord(subtreeRoot.canvas_x);
  const rootY = safeCanvasCoord(subtreeRoot.canvas_y);
  const deltaX = rootX - rootLayout.x;
  const deltaY = rootY - rootLayout.y;
  const rawPositions = new Map<string, SchemaDisplayPosition>();

  for (const [entryId, position] of layout.entries()) {
    if (entryId === subtreeRoot.id) continue;
    rawPositions.set(entryId, {
      x: snapCoordinate(position.x + deltaX),
      y: snapCoordinate(position.y + deltaY),
    });
  }

  const subtreeIds = new Set(rawPositions.keys());
  subtreeIds.add(subtreeRoot.id);
  const occupiedPositions = flatTree
    .filter((entry) => !subtreeIds.has(entry.id))
    .map((entry) => ({
      x: safeCanvasCoord(entry.canvas_x),
      y: safeCanvasCoord(entry.canvas_y),
    }));
  const collisionShift = resolveSubtreeCollisionShift(rawPositions, occupiedPositions, schemaOrientation);
  const nextPositions = new Map<string, SchemaDisplayPosition>();

  for (const [entryId, position] of rawPositions.entries()) {
    nextPositions.set(entryId, {
      x: snapCoordinate(Math.max(0, position.x + collisionShift.x)),
      y: snapCoordinate(Math.max(0, position.y + collisionShift.y)),
    });
  }

  setTree((current) => applyCanvasPositionsToForest(current, nextPositions));

  if (!token || !canModifyStructure) return;

  await Promise.all(
    [...nextPositions.entries()].map(([entryId, position]) =>
      updateOrgUnit(token, entryId, {
        canvas_x: position.x,
        canvas_y: position.y,
      }, structureKind),
    ),
  );
}

type HandleApplyTreeLayoutContext = Pick<OrganigrammaLayoutContext, "schemaCanvasMode" | "setSchemaOrientation" | "setNotice" | "view" | "fitSchemaToViewport" | "token" | "canModifyStructure" | "scopedTree" | "computeHorizontalTreeLayout" | "computeVerticalTreeLayout" | "setTree" | "updateTreeNodeInForest" | "structureKind" | "refreshStructure">;

export async function handleApplyTreeLayout({ schemaCanvasMode, setSchemaOrientation, setNotice, view, fitSchemaToViewport, token, canModifyStructure, scopedTree, computeHorizontalTreeLayout, computeVerticalTreeLayout, setTree, updateTreeNodeInForest, structureKind, refreshStructure }: HandleApplyTreeLayoutContext, orientation: SchemaOrientation) {
  if (schemaCanvasMode === "guided") {
    setSchemaOrientation(orientation);
    setNotice(`Vista guidata ${orientation === "horizontal" ? "orizzontale" : "verticale"} applicata.`);
    if (view === "schema") {
      window.requestAnimationFrame(() => {
        fitSchemaToViewport();
      });
    }
    return;
  }
  if (!token || !canModifyStructure) return;
  const layoutTree = scopedTree;
  const nextPositions = orientation === "horizontal"
    ? computeHorizontalTreeLayout(layoutTree)
    : computeVerticalTreeLayout(layoutTree);
  setTree((current) => {
    let nextTree = current;
    for (const [nodeId, position] of nextPositions) {
      nextTree = updateTreeNodeInForest(nextTree, nodeId, {
        canvas_x: position.x,
        canvas_y: position.y,
      });
    }
    return nextTree;
  });
  try {
    await Promise.all(
      Array.from(nextPositions.entries()).map(([nodeId, position]) =>
        updateOrgUnit(token, nodeId, {
          canvas_x: position.x,
          canvas_y: position.y,
        }, structureKind),
      ),
    );
    setSchemaOrientation(orientation);
    setNotice(`Layout ${orientation === "horizontal" ? "orizzontale" : "verticale"} applicato.`);
    await refreshStructure();
    if (view === "schema") {
      window.requestAnimationFrame(() => {
        fitSchemaToViewport();
      });
    }
  } catch (err) {
    setNotice(err instanceof Error ? err.message : `Applicazione layout ${orientation === "horizontal" ? "orizzontale" : "verticale"} non riuscita`);
  }
}

type HandleCompactVisibleAreaContext = Pick<OrganigrammaLayoutContext, "token" | "canModifyStructure" | "schemaRoots" | "schemaOrientation" | "computeHorizontalTreeLayout" | "computeVerticalTreeLayout" | "safeCanvasCoord" | "snapCoordinate" | "setTree" | "applyCanvasPositionsToForest" | "structureKind" | "setNotice" | "view" | "fitSchemaToViewport">;

export async function handleCompactVisibleArea({ token, canModifyStructure, schemaRoots, schemaOrientation, computeHorizontalTreeLayout, computeVerticalTreeLayout, safeCanvasCoord, snapCoordinate, setTree, applyCanvasPositionsToForest, structureKind, setNotice, view, fitSchemaToViewport }: HandleCompactVisibleAreaContext) {
  if (!token || !canModifyStructure) return;
  const layoutTree = schemaRoots;
  const visibleNodes = flattenTree(layoutTree);
  if (!visibleNodes.length) return;

  const baseLayout = schemaOrientation === "horizontal"
    ? computeHorizontalTreeLayout(layoutTree)
    : computeVerticalTreeLayout(layoutTree);
  const currentMinX = Math.min(...visibleNodes.map((node) => safeCanvasCoord(node.canvas_x)));
  const currentMinY = Math.min(...visibleNodes.map((node) => safeCanvasCoord(node.canvas_y)));
  const layoutMinX = Math.min(...visibleNodes.map((node) => baseLayout.get(node.id)!.x));
  const layoutMinY = Math.min(...visibleNodes.map((node) => baseLayout.get(node.id)!.y));
  const offsetX = currentMinX - layoutMinX;
  const offsetY = currentMinY - layoutMinY;
  const nextPositions = new Map<string, SchemaDisplayPosition>();

  for (const node of visibleNodes) {
    const position = baseLayout.get(node.id)!;
    nextPositions.set(node.id, {
      x: snapCoordinate(Math.max(0, position.x + offsetX)),
      y: snapCoordinate(Math.max(0, position.y + offsetY)),
    });
  }

  setTree((current) => applyCanvasPositionsToForest(current, nextPositions));
  try {
    await Promise.all(
      [...nextPositions.entries()].map(([nodeId, position]) =>
        updateOrgUnit(token, nodeId, {
          canvas_x: position.x,
          canvas_y: position.y,
        }, structureKind),
      ),
    );
    setNotice("Area visibile compattata.");
    if (view === "schema") {
      window.requestAnimationFrame(() => {
        fitSchemaToViewport();
      });
    }
  } catch (err) {
    setNotice(err instanceof Error ? err.message : "Compattazione area visibile non riuscita");
  }
}
