import type { Dispatch, SetStateAction } from "react";

import type { applyCanvasPositionsToForest, computeHorizontalTreeLayout, computeVerticalTreeLayout, resolveSubtreeCollisionShift, safeCanvasCoord, updateTreeNodeInForest } from "@/features/organigramma/organigramma-workspace";
import type { OrgStructureKind, OrgUnitTreeNode } from "@/types/api";

export type OrganigrammaLayoutContext = {
  token: string | null;
  canModifyStructure: boolean;
  structureKind: OrgStructureKind;
  schemaOrientation: "horizontal" | "vertical";
  schemaCanvasMode: "free" | "guided";
  view: string;
  flatTree: OrgUnitTreeNode[];
  scopedTree: OrgUnitTreeNode[];
  schemaRoots: OrgUnitTreeNode[];
  selectedNode: OrgUnitTreeNode | null;
  selectedSector: OrgUnitTreeNode | null;
  selectedId: string | null;
  setTree: Dispatch<SetStateAction<OrgUnitTreeNode[]>>;
  setSchemaOrientation: (orientation: "horizontal" | "vertical") => void;
  setNotice: (message: string) => void;
  fitSchemaToViewport: () => unknown;
  refreshStructure: () => Promise<void>;
  snapCoordinate: (value: number) => number;
  safeCanvasCoord: typeof safeCanvasCoord;
  computeHorizontalTreeLayout: typeof computeHorizontalTreeLayout;
  computeVerticalTreeLayout: typeof computeVerticalTreeLayout;
  resolveSubtreeCollisionShift: typeof resolveSubtreeCollisionShift;
  applyCanvasPositionsToForest: typeof applyCanvasPositionsToForest;
  updateTreeNodeInForest: typeof updateTreeNodeInForest;
};
