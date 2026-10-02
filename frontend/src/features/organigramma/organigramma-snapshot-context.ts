import type { RefObject } from "react";

import type { OrganigrammaSnapshot, OrgImportMode, OrgStructureKind, OrgVisibilityOverride } from "@/types/api";

export type ImportSnapshotAnalysis = {
  units: number;
  assignments: number;
  overrides: number;
  schemaVersion: number | null;
  errors: string[];
  warnings: string[];
};

export type OrganigrammaSnapshotContext = {
  token: string | null;
  canModifyStructure: boolean;
  structureKind: OrgStructureKind;
  exportFilenamePrefix: string;
  importMode: OrgImportMode;
  pendingImportFile: File | null;
  importFileInputRef: RefObject<HTMLInputElement | null>;
  loadCore: () => Promise<void>;
  analyzeOrganigrammaSnapshot: (snapshot: OrganigrammaSnapshot) => ImportSnapshotAnalysis;
  closeReplaceImportConfirm: () => void;
  setSyncing: (value: boolean) => void;
  setNotice: (value: string | null) => void;
  setExportingSnapshot: (value: boolean) => void;
  setImportingSnapshot: (value: boolean) => void;
  setPendingImportSummary: (value: ImportSnapshotAnalysis | null) => void;
  setPendingImportFile: (value: File | null) => void;
  setReplaceImportConfirmText: (value: string) => void;
  setShowReplaceImportConfirm: (value: boolean) => void;
  setOverrides: (value: OrgVisibilityOverride[]) => void;
  setShowAddOverride: (value: boolean) => void;
};
