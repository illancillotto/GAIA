import { flattenTree } from "@/lib/organigramma";
import { updateOrgUnit } from "@/lib/api";
import type { OrganigrammaDragContext, OrganigrammaFocusContext } from "@/features/organigramma/organigramma-viewport-context";
import type { OrganigrammaViewportContext } from "@/features/organigramma/organigramma-viewport-context";

type HandleTreePanStartContext = Pick<OrganigrammaViewportContext, "treeViewportRef" | "treePanStateRef">;

export function handleTreePanStart({ treeViewportRef, treePanStateRef }: HandleTreePanStartContext, event: React.MouseEvent<HTMLDivElement>) {
  if (event.button !== 0) return;
  const target = event.target as HTMLElement | null;
  if (target?.closest("[role='treeitem'], button, input, select, textarea, label, a")) return;
  const viewport = treeViewportRef.current;
  if (!viewport) return;

  treePanStateRef.current = {
    active: true,
    startX: event.clientX,
    startY: event.clientY,
    scrollLeft: viewport.scrollLeft,
    scrollTop: viewport.scrollTop,
  };
  viewport.style.cursor = "grabbing";
  event.preventDefault();

  const handleMouseMove = (moveEvent: MouseEvent) => {
    const current = treePanStateRef.current;
    if (!current.active) return;
    viewport.scrollLeft = current.scrollLeft - (moveEvent.clientX - current.startX);
    viewport.scrollTop = current.scrollTop - (moveEvent.clientY - current.startY);
  };

  const handleMouseUp = () => {
    treePanStateRef.current.active = false;
    viewport.style.cursor = "grab";
    window.removeEventListener("mousemove", handleMouseMove);
    window.removeEventListener("mouseup", handleMouseUp);
  };

  window.addEventListener("mousemove", handleMouseMove);
  window.addEventListener("mouseup", handleMouseUp);
}

type HandleSchemaPanStartContext = Pick<OrganigrammaViewportContext, "schemaViewportRef" | "schemaPanStateRef" | "schemaRoots" | "schemaScale" | "computeSchemaCanvasBounds" | "computeSchemaDisplayPositions" | "safeCanvasCoord" | "SCHEMA_NODE_WIDTH" | "SCHEMA_NODE_HEIGHT" | "setSchemaMarquee" | "setMultiSelectedIds" | "setSchemaLinkDraft">;

export function handleSchemaPanStart({ schemaViewportRef, schemaPanStateRef, schemaRoots, schemaScale, computeSchemaCanvasBounds, computeSchemaDisplayPositions, safeCanvasCoord, SCHEMA_NODE_WIDTH, SCHEMA_NODE_HEIGHT, setSchemaMarquee, setMultiSelectedIds, setSchemaLinkDraft }: HandleSchemaPanStartContext, event: React.MouseEvent<HTMLDivElement>) {
  if (event.button !== 0) return;
  const target = event.target as HTMLElement | null;
  if (target?.closest("[data-schema-node-card], button, input, select, textarea, label, a")) return;
  const viewport = schemaViewportRef.current;
  if (!viewport) return;

  if (event.shiftKey) {
    // Shift+drag on the background: marquee selection instead of panning.
    event.preventDefault();
    const visibleNodes = flattenTree(schemaRoots);
    const bounds = computeSchemaCanvasBounds(visibleNodes, computeSchemaDisplayPositions(visibleNodes));
    const scale = Math.max(schemaScale, 0.01);
    const viewportRect = viewport.getBoundingClientRect();
    const toCanvas = (clientX: number, clientY: number) => ({
      x: (clientX - viewportRect.left + viewport.scrollLeft) / scale,
      y: (clientY - viewportRect.top + viewport.scrollTop) / scale,
    });
    const start = toCanvas(event.clientX, event.clientY);

    const updateSelection = (clientX: number, clientY: number) => {
      const current = toCanvas(clientX, clientY);
      const minX = Math.min(start.x, current.x);
      const maxX = Math.max(start.x, current.x);
      const minY = Math.min(start.y, current.y);
      const maxY = Math.max(start.y, current.y);
      setSchemaMarquee({ x: minX, y: minY, width: maxX - minX, height: maxY - minY });
      const ids = new Set<string>();
      for (const node of visibleNodes) {
        const left = safeCanvasCoord(node.canvas_x) + bounds.offsetX;
        const top = safeCanvasCoord(node.canvas_y) + bounds.offsetY;
        if (left < maxX && left + SCHEMA_NODE_WIDTH > minX && top < maxY && top + SCHEMA_NODE_HEIGHT > minY) {
          ids.add(node.id);
        }
      }
      setMultiSelectedIds(ids);
    };

    const handleMarqueeMove = (moveEvent: MouseEvent) => {
      updateSelection(moveEvent.clientX, moveEvent.clientY);
    };
    const handleMarqueeUp = (upEvent: MouseEvent) => {
      updateSelection(upEvent.clientX, upEvent.clientY);
      setSchemaMarquee(null);
      window.removeEventListener("mousemove", handleMarqueeMove);
      window.removeEventListener("mouseup", handleMarqueeUp);
    };
    window.addEventListener("mousemove", handleMarqueeMove);
    window.addEventListener("mouseup", handleMarqueeUp);
    return;
  }

  // Clicking the empty canvas exits link mode and clears the multi-selection.
  setSchemaLinkDraft(null);
  setMultiSelectedIds(new Set());

  schemaPanStateRef.current = {
    active: true,
    startX: event.clientX,
    startY: event.clientY,
    scrollLeft: viewport.scrollLeft,
    scrollTop: viewport.scrollTop,
  };
  viewport.style.cursor = "grabbing";
  event.preventDefault();

  const handleMouseMove = (moveEvent: MouseEvent) => {
    const current = schemaPanStateRef.current;
    if (!current.active) return;
    viewport.scrollLeft = current.scrollLeft - (moveEvent.clientX - current.startX);
    viewport.scrollTop = current.scrollTop - (moveEvent.clientY - current.startY);
  };

  const handleMouseUp = () => {
    schemaPanStateRef.current.active = false;
    viewport.style.cursor = "grab";
    window.removeEventListener("mousemove", handleMouseMove);
    window.removeEventListener("mouseup", handleMouseUp);
  };

  window.addEventListener("mousemove", handleMouseMove);
  window.addEventListener("mouseup", handleMouseUp);
}

type HandleTreeZoomWheelContext = Pick<OrganigrammaViewportContext, "treeViewportRef" | "setTreeScale">;

export function handleTreeZoomWheel({ treeViewportRef, setTreeScale }: HandleTreeZoomWheelContext, event: WheelEvent) {
  if (!event.ctrlKey) return;
  event.preventDefault();
  const viewport = treeViewportRef.current;
  if (!viewport) return;

  const rect = viewport.getBoundingClientRect();
  const pointerX = event.clientX - rect.left + viewport.scrollLeft;
  const pointerY = event.clientY - rect.top + viewport.scrollTop;

  setTreeScale((current) => {
    const delta = event.deltaY > 0 ? -0.08 : 0.08;
    const next = Math.max(0.65, Math.min(1.6, Number((current + delta).toFixed(2))));
    window.requestAnimationFrame(() => {
      const ratio = next / current;
      viewport.scrollLeft = Math.max(pointerX * ratio - (event.clientX - rect.left), 0);
      viewport.scrollTop = Math.max(pointerY * ratio - (event.clientY - rect.top), 0);
    });
    return next;
  });
}

export function bindSchemaDrag({ schemaDragging, token, schemaEditEnabled, schemaScale, schemaSnapToGrid, setTree, snapCoordinate, updateTreeNodeInForest, treeRef, setSchemaDragging, structureKind, setNotice }: OrganigrammaDragContext) {
  if (!schemaDragging || !token || !schemaEditEnabled) return;

  const handlePointerMove = (event: PointerEvent) => {
    if (event.pointerId !== schemaDragging.pointerId) return;
    const deltaX = Math.round((event.clientX - schemaDragging.startX) / Math.max(schemaScale, 0.01));
    const deltaY = Math.round((event.clientY - schemaDragging.startY) / Math.max(schemaScale, 0.01));
    setTree((current) => {
      let nextTree = current;
      for (const dragNode of schemaDragging.nodes) {
        const rawX = Math.max(0, dragNode.originX + deltaX);
        const rawY = Math.max(0, dragNode.originY + deltaY);
        const nextX = schemaSnapToGrid ? snapCoordinate(rawX) : rawX;
        const nextY = schemaSnapToGrid ? snapCoordinate(rawY) : rawY;
        nextTree = updateTreeNodeInForest(nextTree, dragNode.nodeId, { canvas_x: nextX, canvas_y: nextY });
      }
      return nextTree;
    });
  };

  const handlePointerUp = (event: PointerEvent) => {
    if (event.pointerId !== schemaDragging.pointerId) return;
    const flat = flattenTree(treeRef.current);
    setSchemaDragging(null);
    for (const dragNode of schemaDragging.nodes) {
      const movedNode = flat.find((entry) => entry.id === dragNode.nodeId);
      if (!movedNode) continue;
      void updateOrgUnit(token, dragNode.nodeId, {
        canvas_x: movedNode.canvas_x,
        canvas_y: movedNode.canvas_y,
      }, structureKind).catch((err) => {
        setNotice(err instanceof Error ? err.message : "Salvataggio posizione non riuscito");
      });
    }
  };

  window.addEventListener("pointermove", handlePointerMove);
  window.addEventListener("pointerup", handlePointerUp);
  window.addEventListener("pointercancel", handlePointerUp);
  return () => {
    window.removeEventListener("pointermove", handlePointerMove);
    window.removeEventListener("pointerup", handlePointerUp);
    window.removeEventListener("pointercancel", handlePointerUp);
  };
}

export function focusSchemaNode({ view, schemaFocusNodeId, schemaViewportRef, roots, setSchemaFocusNodeId, schemaCanvasMode, computeGuidedSchemaLayout, schemaOrientation, guidedSchemaDensity, computeSchemaDisplayPositions, computeSchemaCanvasBounds, setSchemaScale, SCHEMA_NODE_WIDTH, SCHEMA_NODE_HEIGHT }: OrganigrammaFocusContext) {
  if (view !== "schema" || !schemaFocusNodeId) return;
  const viewport = schemaViewportRef.current;
  if (!viewport) return;
  const visibleNodes = flattenTree(roots);
  const targetNode = visibleNodes.find((node) => node.id === schemaFocusNodeId);
  if (!targetNode) {
    setSchemaFocusNodeId(null);
    return;
  }
  const positions = schemaCanvasMode === "guided"
    ? computeGuidedSchemaLayout(roots, schemaOrientation, guidedSchemaDensity)
    : computeSchemaDisplayPositions(visibleNodes);
  const bounds = computeSchemaCanvasBounds(visibleNodes, positions);
  const widthRatio = (viewport.clientWidth - 32) / Math.max(bounds.width, 1);
  const heightRatio = (viewport.clientHeight - 32) / Math.max(bounds.height, 1);
  const nextScale = Math.max(0.45, Math.min(1.2, Math.min(widthRatio, heightRatio)));
  setSchemaScale(nextScale);

  const id = window.requestAnimationFrame(() => {
    const targetPosition = positions.get(targetNode.id)!;
    const targetX = (targetPosition.x + bounds.offsetX) * nextScale;
    const targetY = (targetPosition.y + bounds.offsetY) * nextScale;
    viewport.scrollLeft = Math.max(targetX - (viewport.clientWidth - SCHEMA_NODE_WIDTH * nextScale) / 2, 0);
    viewport.scrollTop = Math.max(targetY - (viewport.clientHeight - SCHEMA_NODE_HEIGHT * nextScale) / 2, 0);
    setSchemaFocusNodeId(null);
  });

  return () => window.cancelAnimationFrame(id);
}


type HandleSchemaZoomWheelContext = Pick<OrganigrammaViewportContext, "schemaViewportRef" | "setSchemaScale">;

export function handleSchemaZoomWheel({ schemaViewportRef, setSchemaScale }: HandleSchemaZoomWheelContext, event: WheelEvent) {
  if (!event.ctrlKey) return;
  event.preventDefault();
  const viewport = schemaViewportRef.current;
  if (!viewport) return;

  const rect = viewport.getBoundingClientRect();
  const pointerX = event.clientX - rect.left + viewport.scrollLeft;
  const pointerY = event.clientY - rect.top + viewport.scrollTop;

  setSchemaScale((current) => {
    const delta = event.deltaY > 0 ? -0.08 : 0.08;
    const next = Math.max(0.5, Math.min(1.6, Number((current + delta).toFixed(2))));
    window.requestAnimationFrame(() => {
      const ratio = next / current;
      viewport.scrollLeft = Math.max(pointerX * ratio - (event.clientX - rect.left), 0);
      viewport.scrollTop = Math.max(pointerY * ratio - (event.clientY - rect.top), 0);
    });
    return next;
  });
}
