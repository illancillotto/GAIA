import { createOrgOverride, exportOrganigrammaSnapshot, getOrgOverrides, importOrganigrammaSnapshot, syncOrgWhiteCompany } from "@/lib/api";
import type { OrganigrammaSnapshotContext } from "@/features/organigramma/organigramma-snapshot-context";
import type { OrganigrammaSnapshot, OrgVisibilityOverrideCreateInput } from "@/types/api";

type HandleSyncContext = Pick<OrganigrammaSnapshotContext, "token" | "setSyncing" | "setNotice" | "loadCore">;

export async function handleSync({ token, setSyncing, setNotice, loadCore }: HandleSyncContext) {
  if (!token) return;
  setSyncing(true);
  setNotice(null);
  try {
    const result = await syncOrgWhiteCompany(token);
    setNotice(result.message);
    await loadCore();
  } catch (err) {
    setNotice(err instanceof Error ? err.message : "Sync non riuscito");
  } finally {
    setSyncing(false);
  }
}

type HandleExportSnapshotContext = Pick<OrganigrammaSnapshotContext, "token" | "canModifyStructure" | "setExportingSnapshot" | "setNotice" | "structureKind" | "exportFilenamePrefix">;

export async function handleExportSnapshot({ token, canModifyStructure, setExportingSnapshot, setNotice, structureKind, exportFilenamePrefix }: HandleExportSnapshotContext) {
  if (!token || !canModifyStructure) return;
  setExportingSnapshot(true);
  setNotice(null);
  try {
    const snapshot = await exportOrganigrammaSnapshot(token, structureKind);
    const blob = new Blob([JSON.stringify(snapshot, null, 2)], { type: "application/json;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    const timestamp = new Date().toISOString().replaceAll(":", "-");
    link.href = url;
    link.download = `${exportFilenamePrefix}-${timestamp}.json`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
    setNotice("Snapshot JSON esportato.");
  } catch (err) {
    setNotice(err instanceof Error ? err.message : "Export JSON non riuscito");
  } finally {
    setExportingSnapshot(false);
  }
}

type HandleOpenImportDialogContext = Pick<OrganigrammaSnapshotContext, "canModifyStructure" | "importFileInputRef">;

export function handleOpenImportDialog({ canModifyStructure, importFileInputRef }: HandleOpenImportDialogContext) {
  if (!canModifyStructure) return;
  importFileInputRef.current?.click();
}

type CloseReplaceImportConfirmContext = Pick<OrganigrammaSnapshotContext, "setShowReplaceImportConfirm" | "setPendingImportFile" | "setPendingImportSummary" | "setReplaceImportConfirmText" | "importFileInputRef">;

export function closeReplaceImportConfirm({ setShowReplaceImportConfirm, setPendingImportFile, setPendingImportSummary, setReplaceImportConfirmText, importFileInputRef }: CloseReplaceImportConfirmContext) {
  setShowReplaceImportConfirm(false);
  setPendingImportFile(null);
  setPendingImportSummary(null);
  setReplaceImportConfirmText("");
  if (importFileInputRef.current) importFileInputRef.current.value = "";
}

type HandleImportFileContext = Pick<OrganigrammaSnapshotContext, "token" | "canModifyStructure" | "importMode" | "setPendingImportSummary" | "analyzeOrganigrammaSnapshot" | "setNotice" | "importFileInputRef" | "setPendingImportFile" | "setReplaceImportConfirmText" | "setShowReplaceImportConfirm" | "setImportingSnapshot" | "structureKind" | "loadCore">;

export async function handleImportFile({ token, canModifyStructure, importMode, setPendingImportSummary, analyzeOrganigrammaSnapshot, setNotice, importFileInputRef, setPendingImportFile, setReplaceImportConfirmText, setShowReplaceImportConfirm, setImportingSnapshot, structureKind, loadCore }: HandleImportFileContext, file: File | null) {
  if (!file || !token || !canModifyStructure) return;
  if (importMode === "replace") {
    try {
      const parsed = JSON.parse(await file.text()) as OrganigrammaSnapshot;
      setPendingImportSummary(analyzeOrganigrammaSnapshot(parsed));
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "JSON non valido");
      if (importFileInputRef.current) importFileInputRef.current.value = "";
      return;
    }
    setPendingImportFile(file);
    setReplaceImportConfirmText("");
    setShowReplaceImportConfirm(true);
    return;
  }
  setImportingSnapshot(true);
  setNotice(null);
  try {
    const parsed = JSON.parse(await file.text()) as OrganigrammaSnapshot;
    const result = await importOrganigrammaSnapshot(token, parsed, importMode, structureKind);
    await loadCore();
    setNotice(
      [
        `Import ${result.mode} completato.`,
        `Unità create ${result.units_created}, aggiornate ${result.units_updated}.`,
        `Assegnazioni create ${result.assignments_created}, aggiornate ${result.assignments_updated}.`,
        `Override create ${result.overrides_created}, aggiornate ${result.overrides_updated}.`,
      ].join(" "),
    );
  } catch (err) {
    setNotice(err instanceof Error ? err.message : "Import JSON non riuscito");
  } finally {
    if (importFileInputRef.current) importFileInputRef.current.value = "";
    setImportingSnapshot(false);
  }
}

type HandleConfirmReplaceImportContext = Pick<OrganigrammaSnapshotContext, "pendingImportFile" | "token" | "canModifyStructure" | "setImportingSnapshot" | "setNotice" | "structureKind" | "loadCore" | "closeReplaceImportConfirm" | "importFileInputRef">;

export async function handleConfirmReplaceImport({ pendingImportFile, token, canModifyStructure, setImportingSnapshot, setNotice, structureKind, loadCore, closeReplaceImportConfirm, importFileInputRef }: HandleConfirmReplaceImportContext) {
  if (!pendingImportFile || !token || !canModifyStructure) return;
  setImportingSnapshot(true);
  setNotice(null);
  try {
    const parsed = JSON.parse(await pendingImportFile.text()) as OrganigrammaSnapshot;
    const result = await importOrganigrammaSnapshot(token, parsed, "replace", structureKind);
    await loadCore();
    setNotice(
      [
        `Import ${result.mode} completato.`,
        `Unità create ${result.units_created}, aggiornate ${result.units_updated}.`,
        `Assegnazioni create ${result.assignments_created}, aggiornate ${result.assignments_updated}.`,
        `Override create ${result.overrides_created}, aggiornate ${result.overrides_updated}.`,
      ].join(" "),
    );
    closeReplaceImportConfirm();
  } catch (err) {
    setNotice(err instanceof Error ? err.message : "Import JSON non riuscito");
  } finally {
    if (importFileInputRef.current) importFileInputRef.current.value = "";
    setImportingSnapshot(false);
  }
}

type HandleCreateOverrideContext = Pick<OrganigrammaSnapshotContext, "token" | "canModifyStructure" | "structureKind" | "setOverrides" | "setShowAddOverride">;

export async function handleCreateOverride({ token, canModifyStructure, structureKind, setOverrides, setShowAddOverride }: HandleCreateOverrideContext, payload: OrgVisibilityOverrideCreateInput) {
  if (!token || !canModifyStructure) return;
  await createOrgOverride(token, payload, structureKind);
  setOverrides(await getOrgOverrides(token, structureKind));
  setShowAddOverride(false);
}
