import type { Dispatch, SetStateAction } from "react";

import type { ApplicationUser, CurrentUser, OrgAssignment, OrgStructureKind, OrgUnitDetail, OrgUnitTreeNode, OrgVisibilityOverride } from "@/types/api";

export type OrganigrammaLoadingContext = {
  token: string | null;
  structureKind: OrgStructureKind;
  selectedId: string | null;
  setError: (message: string | null) => void;
  setLoading: (loading: boolean) => void;
  setCurrentUser: (user: CurrentUser) => void;
  setTree: (tree: OrgUnitTreeNode[]) => void;
  setUsers: (users: ApplicationUser[]) => void;
  setAllAssignments: (assignments: OrgAssignment[]) => void;
  setExpanded: (ids: Set<string>) => void;
  setSelectedId: Dispatch<SetStateAction<string | null>>;
  setOverrides: (overrides: OrgVisibilityOverride[]) => void;
  setCanManage: (allowed: boolean) => void;
  setDetail: (detail: OrgUnitDetail) => void;
  setNotice: (message: string) => void;
};
