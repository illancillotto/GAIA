import type { Dispatch, SetStateAction } from "react";

import type { OrgUnitTreeNode } from "@/types/api";

export type SchemaLinkDraft = { sourceId: string; mode: "above" | "below" };
export type SchemaDrag = {
  nodeId: string;
  pointerId: number;
  startX: number;
  startY: number;
  nodes: { nodeId: string; originX: number; originY: number }[];
};

export type OrganigrammaSelectionContext = {
  canModifyStructure: boolean;
  schemaEditEnabled: boolean;
  selectedId: string | null;
  multiSelectedIds: Set<string>;
  flatTree: OrgUnitTreeNode[];
  schemaLinkDraft: SchemaLinkDraft | null;
  setSchemaLinkDraft: Dispatch<SetStateAction<SchemaLinkDraft | null>>;
  setMultiSelectedIds: Dispatch<SetStateAction<Set<string>>>;
  setSelectedId: (value: string) => void;
  setSchemaDragging: (value: SchemaDrag) => void;
  setSchemaContextMenu: (value: { nodeId: string; x: number; y: number }) => void;
  safeCanvasCoord: (value: number | null | undefined) => number;
  performSchemaLink: (sourceId: string, targetId: string, mode: "above" | "below") => Promise<boolean>;
};
