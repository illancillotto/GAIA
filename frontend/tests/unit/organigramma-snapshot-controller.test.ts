import { beforeEach, describe, expect, test, vi } from "vitest";

import { closeReplaceImportConfirm, handleConfirmReplaceImport, handleCreateOverride, handleExportSnapshot, handleImportFile, handleOpenImportDialog, handleSync } from "@/features/organigramma/organigramma-snapshot-controller";
import type { OrganigrammaSnapshotContext } from "@/features/organigramma/organigramma-snapshot-context";
import type { OrganigrammaSnapshot, OrgVisibilityOverrideCreateInput } from "@/types/api";

const api = vi.hoisted(() => ({ createOrgOverride: vi.fn(), exportOrganigrammaSnapshot: vi.fn(), getOrgOverrides: vi.fn(), importOrganigrammaSnapshot: vi.fn(), syncOrgWhiteCompany: vi.fn() }));
vi.mock("@/lib/api", () => api);

const snapshot = { schema_version: 1, units: [], assignments: [], overrides: [] } as unknown as OrganigrammaSnapshot;
const analysis = { units: 0, assignments: 0, overrides: 0, schemaVersion: 1, errors: [], warnings: [] };
const override: OrgVisibilityOverrideCreateInput = { viewer_user_id: 1, target_type: "org_unit", target_org_unit_id: "unit", target_user_id: null, scope: "read", motivo: null, valid_from: null, valid_to: null };
const result = { mode: "merge", units_created: 1, units_updated: 2, assignments_created: 3, assignments_updated: 4, overrides_created: 5, overrides_updated: 6 };

function file(contents = JSON.stringify(snapshot)) {
  const selected = new File([contents], "snapshot.json", { type: "application/json" });
  Object.defineProperty(selected, "text", { value: vi.fn().mockResolvedValue(contents) });
  return selected;
}

function context() {
  return {
    token: "token", canModifyStructure: true, structureKind: "organigramma" as const,
    exportFilenamePrefix: "organigramma-snapshot", importMode: "merge" as const,
    pendingImportFile: file(), importFileInputRef: { current: document.createElement("input") as HTMLInputElement | null },
    loadCore: vi.fn().mockResolvedValue(undefined), analyzeOrganigrammaSnapshot: vi.fn().mockReturnValue(analysis),
    closeReplaceImportConfirm: vi.fn(), setSyncing: vi.fn(), setNotice: vi.fn(), setExportingSnapshot: vi.fn(),
    setImportingSnapshot: vi.fn(), setPendingImportSummary: vi.fn(), setPendingImportFile: vi.fn(),
    setReplaceImportConfirmText: vi.fn(), setShowReplaceImportConfirm: vi.fn(), setOverrides: vi.fn(), setShowAddOverride: vi.fn(),
  } satisfies OrganigrammaSnapshotContext;
}

beforeEach(() => {
  vi.resetAllMocks();
  api.exportOrganigrammaSnapshot.mockResolvedValue(snapshot);
  api.importOrganigrammaSnapshot.mockResolvedValue(result);
  api.syncOrgWhiteCompany.mockResolvedValue({ message: "Sync completato" });
  api.createOrgOverride.mockResolvedValue(undefined);
  api.getOrgOverrides.mockResolvedValue([]);
  vi.stubGlobal("URL", { createObjectURL: vi.fn(() => "blob:snapshot"), revokeObjectURL: vi.fn() });
});

describe("snapshot and override authorization", () => {
  const operations = [
    ["export", (state: OrganigrammaSnapshotContext) => handleExportSnapshot(state)],
    ["import", (state: OrganigrammaSnapshotContext) => handleImportFile(state, file())],
    ["replace", (state: OrganigrammaSnapshotContext) => handleConfirmReplaceImport(state)],
    ["override", (state: OrganigrammaSnapshotContext) => handleCreateOverride(state, override)],
  ] as const;

  test.each(operations)("%s has no effects without token or permission", async (_name, run) => {
    for (const patch of [{ token: null }, { canModifyStructure: false }]) {
      const state = { ...context(), ...patch };
      await run(state);
      for (const mock of Object.values(api)) expect(mock).not.toHaveBeenCalled();
      expect(state.setNotice).not.toHaveBeenCalled();
      expect(state.loadCore).not.toHaveBeenCalled();
    }
  });

  test("cancelled file selection and absent pending replacement have no effects", async () => {
    const state = context();
    await handleImportFile(state, null);
    await handleConfirmReplaceImport({ ...state, pendingImportFile: null });
    expect(api.importOrganigrammaSnapshot).not.toHaveBeenCalled();
    expect(state.setImportingSnapshot).not.toHaveBeenCalled();
  });

  test("open dialog requires permission and tolerates an unmounted input", () => {
    const state = context();
    const click = vi.spyOn(state.importFileInputRef.current!, "click");
    handleOpenImportDialog({ ...state, canModifyStructure: false });
    expect(click).not.toHaveBeenCalled();
    handleOpenImportDialog(state);
    expect(click).toHaveBeenCalledOnce();
    handleOpenImportDialog({ ...state, importFileInputRef: { current: null } });
    expect(click).toHaveBeenCalledOnce();
  });
});

describe("snapshot persistence", () => {
  test.each(["organigramma", "territoriale"] as const)("imports %s and refreshes before showing actual result counts", async (structureKind) => {
    const state = { ...context(), structureKind };
    await handleImportFile(state, file());
    expect(api.importOrganigrammaSnapshot).toHaveBeenCalledWith("token", snapshot, "merge", structureKind);
    expect(state.loadCore).toHaveBeenCalledOnce();
    expect(state.setNotice.mock.invocationCallOrder.at(-1)).toBeGreaterThan(state.loadCore.mock.invocationCallOrder[0]!);
    expect(state.setNotice).toHaveBeenLastCalledWith("Import merge completato. Unità create 1, aggiornate 2. Assegnazioni create 3, aggiornate 4. Override create 5, aggiornate 6.");
    expect(state.setImportingSnapshot.mock.calls).toEqual([[true], [false]]);
  });

  test("replace stages a file and domain analysis without persisting any data", async () => {
    const state = { ...context(), importMode: "replace" as const };
    const selected = file();
    await handleImportFile(state, selected);
    expect(state.analyzeOrganigrammaSnapshot).toHaveBeenCalledWith(snapshot);
    expect(state.setPendingImportSummary).toHaveBeenCalledWith(analysis);
    expect(state.setPendingImportFile).toHaveBeenCalledWith(selected);
    expect(state.setReplaceImportConfirmText).toHaveBeenCalledWith("");
    expect(state.setShowReplaceImportConfirm).toHaveBeenCalledWith(true);
    expect(api.importOrganigrammaSnapshot).not.toHaveBeenCalled();
    expect(state.setImportingSnapshot).not.toHaveBeenCalled();
  });

  test("replace confirmation persists the pending file, refreshes and only then closes", async () => {
    const state = { ...context(), structureKind: "territoriale" as const };
    api.importOrganigrammaSnapshot.mockResolvedValueOnce({ ...result, mode: "replace" });
    await handleConfirmReplaceImport(state);
    expect(api.importOrganigrammaSnapshot).toHaveBeenCalledWith("token", snapshot, "replace", "territoriale");
    expect(state.setNotice).toHaveBeenLastCalledWith(expect.stringContaining("Import replace completato."));
    expect(state.closeReplaceImportConfirm.mock.invocationCallOrder[0]).toBeGreaterThan(state.loadCore.mock.invocationCallOrder[0]!);
    expect(state.setImportingSnapshot.mock.calls).toEqual([[true], [false]]);
  });

  test.each([true, false])("clears pending state on dismissal with mounted input %s", (mounted) => {
    const state = context();
    if (!mounted) state.importFileInputRef.current = null;
    const clear = mounted ? vi.spyOn(state.importFileInputRef.current!, "value", "set") : null;
    closeReplaceImportConfirm(state);
    expect(state.setShowReplaceImportConfirm).toHaveBeenCalledWith(false);
    expect(state.setPendingImportFile).toHaveBeenCalledWith(null);
    expect(state.setPendingImportSummary).toHaveBeenCalledWith(null);
    expect(state.setReplaceImportConfirmText).toHaveBeenCalledWith("");
    if (clear) expect(clear).toHaveBeenCalledWith("");
  });

  test.each(["merge", "replace"] as const)("success tolerates the input unmounting during %s", async (mode) => {
    const state = { ...context(), importFileInputRef: { current: null } };
    if (mode === "merge") await handleImportFile(state, file());
    else await handleConfirmReplaceImport(state);
    expect(api.importOrganigrammaSnapshot).toHaveBeenCalledOnce();
    expect(state.setImportingSnapshot).toHaveBeenLastCalledWith(false);
  });
});

describe("snapshot failures", () => {
  test.each([true, false])("invalid replace JSON does not change pending state (input mounted %s)", async (mounted) => {
    const state = { ...context(), importMode: "replace" as const };
    if (!mounted) state.importFileInputRef.current = null;
    await handleImportFile(state, file("not JSON"));
    expect(state.setNotice).toHaveBeenCalledWith(expect.any(String));
    expect(state.setPendingImportFile).not.toHaveBeenCalled();
    expect(state.setShowReplaceImportConfirm).not.toHaveBeenCalled();
    expect(api.importOrganigrammaSnapshot).not.toHaveBeenCalled();
  });

  test("uses the invalid JSON fallback for non-Error file reading failures", async () => {
    const selected = file();
    vi.mocked(selected.text).mockRejectedValueOnce("unreadable");
    const state = { ...context(), importMode: "replace" as const };
    await handleImportFile(state, selected);
    expect(state.setNotice).toHaveBeenCalledWith("JSON non valido");
    expect(state.setPendingImportFile).not.toHaveBeenCalled();
  });

  test.each(["merge", "replace"] as const)("%s preserves API errors and releases busy state", async (mode) => {
    for (const failure of [new Error("Import rifiutato"), "failure"]) {
      const state = context();
      api.importOrganigrammaSnapshot.mockRejectedValueOnce(failure);
      if (mode === "merge") await handleImportFile(state, file());
      else await handleConfirmReplaceImport(state);
      expect(state.setNotice).toHaveBeenLastCalledWith(failure instanceof Error ? failure.message : "Import JSON non riuscito");
      expect(state.loadCore).not.toHaveBeenCalled();
      expect(state.closeReplaceImportConfirm).not.toHaveBeenCalled();
      expect(state.setImportingSnapshot).toHaveBeenLastCalledWith(false);
    }
  });

  test.each(["merge", "replace"] as const)("%s does not persist malformed JSON", async (mode) => {
    const selected = file("{");
    const state = { ...context(), pendingImportFile: selected };
    if (mode === "merge") await handleImportFile(state, selected);
    else await handleConfirmReplaceImport(state);
    expect(api.importOrganigrammaSnapshot).not.toHaveBeenCalled();
    expect(state.setNotice).toHaveBeenLastCalledWith(expect.any(String));
    expect(state.setImportingSnapshot).toHaveBeenLastCalledWith(false);
  });

  test.each(["merge", "replace"] as const)("%s preserves committed data if refresh fails and does not claim success", async (mode) => {
    const state = context();
    state.loadCore.mockRejectedValueOnce(new Error("Refresh rifiutato"));
    if (mode === "merge") await handleImportFile(state, file());
    else await handleConfirmReplaceImport(state);
    expect(api.importOrganigrammaSnapshot).toHaveBeenCalledOnce();
    expect(state.setNotice).toHaveBeenLastCalledWith("Refresh rifiutato");
    expect(state.closeReplaceImportConfirm).not.toHaveBeenCalled();
    expect(state.setImportingSnapshot).toHaveBeenLastCalledWith(false);
  });
});

describe("export and sync", () => {
  test("exports the API snapshot as a downloadable JSON blob and revokes its URL", async () => {
    const state = { ...context(), structureKind: "territoriale" as const, exportFilenamePrefix: "territoriale" };
    const downloads: { filename: string; href: string }[] = [];
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function () {
      downloads.push({ filename: this.download, href: this.href });
      expect(document.body.contains(this)).toBe(true);
    });
    await handleExportSnapshot(state);
    expect(api.exportOrganigrammaSnapshot).toHaveBeenCalledWith("token", "territoriale");
    expect(downloads).toEqual([{ filename: expect.stringMatching(/^territoriale-.*\.json$/), href: "blob:snapshot" }]);
    const blob = vi.mocked(URL.createObjectURL).mock.calls[0]![0] as Blob;
    expect(blob.type).toBe("application/json;charset=utf-8");
    const contents = await blob.text();
    expect(JSON.parse(contents)).toEqual(snapshot);
    expect(document.querySelector('a[href="blob:snapshot"]')).toBeNull();
    expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:snapshot");
    expect(state.setNotice).toHaveBeenLastCalledWith("Snapshot JSON esportato.");
    expect(state.setExportingSnapshot.mock.calls).toEqual([[true], [false]]);
    click.mockRestore();
  });

  test.each([new Error("Export rifiutato"), "failure"])("export failures do not trigger download (%s)", async (failure) => {
    const state = context();
    api.exportOrganigrammaSnapshot.mockRejectedValueOnce(failure);
    await handleExportSnapshot(state);
    expect(URL.createObjectURL).not.toHaveBeenCalled();
    expect(state.setNotice).toHaveBeenLastCalledWith(failure instanceof Error ? failure.message : "Export JSON non riuscito");
    expect(state.setExportingSnapshot).toHaveBeenLastCalledWith(false);
  });

  test("sync rejects missing token and refreshes only after reporting the connector result", async () => {
    const state = context();
    await handleSync({ ...state, token: null });
    expect(api.syncOrgWhiteCompany).not.toHaveBeenCalled();
    await handleSync(state);
    expect(api.syncOrgWhiteCompany).toHaveBeenCalledWith("token");
    expect(state.setNotice).toHaveBeenLastCalledWith("Sync completato");
    expect(state.setNotice.mock.invocationCallOrder.at(-1)).toBeLessThan(state.loadCore.mock.invocationCallOrder[0]!);
    expect(state.setSyncing.mock.calls).toEqual([[true], [false]]);
  });

  test.each([new Error("Connector indisponibile"), "failure"])("sync releases busy state after connector failure (%s)", async (failure) => {
    const state = context();
    api.syncOrgWhiteCompany.mockRejectedValueOnce(failure);
    await handleSync(state);
    expect(state.setNotice).toHaveBeenLastCalledWith(failure instanceof Error ? failure.message : "Sync non riuscito");
    expect(state.loadCore).not.toHaveBeenCalled();
    expect(state.setSyncing).toHaveBeenLastCalledWith(false);
  });
});

describe("override persistence", () => {
  test("creates and reloads territorial overrides before closing the modal", async () => {
    const state = { ...context(), structureKind: "territoriale" as const };
    await handleCreateOverride(state, override);
    expect(api.createOrgOverride).toHaveBeenCalledWith("token", override, "territoriale");
    expect(api.getOrgOverrides).toHaveBeenCalledWith("token", "territoriale");
    expect(state.setOverrides).toHaveBeenCalledWith([]);
    expect(state.setShowAddOverride).toHaveBeenCalledWith(false);
    expect(api.getOrgOverrides.mock.invocationCallOrder[0]).toBeGreaterThan(api.createOrgOverride.mock.invocationCallOrder[0]!);
  });

  test.each(["createOrgOverride", "getOrgOverrides"] as const)("propagates %s errors and leaves the modal open", async (apiMethod) => {
    const state = context();
    const failure = new Error("Override rifiutato");
    api[apiMethod].mockRejectedValueOnce(failure);
    await expect(handleCreateOverride(state, override)).rejects.toBe(failure);
    expect(state.setOverrides).not.toHaveBeenCalled();
    expect(state.setShowAddOverride).not.toHaveBeenCalled();
  });
});
