import type { Dispatch, MutableRefObject, RefObject, SetStateAction } from "react";

import type { computeSchemaCanvasBounds, computeSchemaDisplayPositions } from "@/features/organigramma/organigramma-workspace";
import type { OrgUnitTreeNode } from "@/types/api";
import type { OrgStructureKind } from "@/types/api";
import type { SchemaDrag } from "@/features/organigramma/organigramma-selection-context";
import type { computeGuidedSchemaLayout, updateTreeNodeInForest } from "@/features/organigramma/organigramma-workspace";

type PanState = { active: boolean; startX: number; startY: number; scrollLeft: number; scrollTop: number };

export type OrganigrammaDragContext = {
  schemaDragging: SchemaDrag | null;
  token: string | null;
  schemaEditEnabled: boolean;
  schemaScale: number;
  schemaSnapToGrid: boolean;
  setTree: Dispatch<SetStateAction<OrgUnitTreeNode[]>>;
  treeRef: MutableRefObject<OrgUnitTreeNode[]>;
  setSchemaDragging: (drag: null) => void;
  structureKind: OrgStructureKind;
  setNotice: (message: string) => void;
  snapCoordinate: (value: number) => number;
  updateTreeNodeInForest: typeof updateTreeNodeInForest;
};

export type OrganigrammaFocusContext = {
  view: string;
  schemaFocusNodeId: string | null;
  schemaViewportRef: RefObject<HTMLDivElement | null>;
  roots: OrgUnitTreeNode[];
  setSchemaFocusNodeId: (id: null) => void;
  schemaCanvasMode: "free" | "guided";
  computeGuidedSchemaLayout: typeof computeGuidedSchemaLayout;
  schemaOrientation: "horizontal" | "vertical";
  guidedSchemaDensity: "compact" | "standard" | "presentation";
  computeSchemaDisplayPositions: typeof computeSchemaDisplayPositions;
  computeSchemaCanvasBounds: typeof computeSchemaCanvasBounds;
  setSchemaScale: (scale: number) => void;
  SCHEMA_NODE_WIDTH: number;
  SCHEMA_NODE_HEIGHT: number;
};

export type OrganigrammaViewportContext = {
  treeViewportRef: RefObject<HTMLDivElement | null>;
  schemaViewportRef: RefObject<HTMLDivElement | null>;
  treePanStateRef: MutableRefObject<PanState>;
  schemaPanStateRef: MutableRefObject<PanState>;
  schemaRoots: OrgUnitTreeNode[];
  schemaScale: number;
  setSchemaScale: Dispatch<SetStateAction<number>>;
  setTreeScale: Dispatch<SetStateAction<number>>;
  setSchemaMarquee: (value: { x: number; y: number; width: number; height: number } | null) => void;
  setMultiSelectedIds: (value: Set<string>) => void;
  setSchemaLinkDraft: (value: null) => void;
  computeSchemaCanvasBounds: typeof computeSchemaCanvasBounds;
  computeSchemaDisplayPositions: typeof computeSchemaDisplayPositions;
  safeCanvasCoord: (value: number | null | undefined) => number;
  SCHEMA_NODE_WIDTH: number;
  SCHEMA_NODE_HEIGHT: number;
};
