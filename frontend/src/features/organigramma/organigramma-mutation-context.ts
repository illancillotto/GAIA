import type { Dispatch, SetStateAction } from "react";

import type { ApplicationUser, OrgAssignment, OrgStructureKind, OrgUnitTreeNode } from "@/types/api";

export type OrganigrammaMutationContext = {
  token: string | null;
  canModifyStructure: boolean;
  schemaEditEnabled: boolean;
  structureKind: OrgStructureKind;
  entityLabel: string;
  flatTree: OrgUnitTreeNode[];
  users: ApplicationUser[];
  allAssignments: OrgAssignment[];
  assignedUserIds: Set<number>;
  schemaMeta: Map<string, {
    lead: OrgAssignment | null;
    descendantIds: Set<string>;
    directPeople: number;
  }>;
  refreshStructure: () => Promise<void>;
  setNotice: (value: string | null) => void;
  setSelectedId: Dispatch<SetStateAction<string | null>>;
  setMultiSelectedIds: Dispatch<SetStateAction<Set<string>>>;
  setDraggingNodeId: (value: null) => void;
  setDraggingUserId: (value: null) => void;
  setCreateUnitPreset: (value: null) => void;
  setSchemaContextMenu: (value: null) => void;
  setDetail: (value: null) => void;
};
