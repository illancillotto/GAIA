import { describe, expect, it } from "vitest";
import { patchPresenzeEditor } from "@/lib/presenze-editor-state";

describe("Presenze editor updates", () => {
  it("merges an input change without mutating the other pending edits", () => {
    const current = { kmValue: "12", validationNote: "Confermata", manualNote: "" };
    expect(patchPresenzeEditor(current, { manualNote: "Turno temporaneo" })).toEqual({ ...current, manualNote: "Turno temporaneo" });
    expect(current.manualNote).toBe("");
  });
  it("keeps a dismissed editor closed when a previous input event arrives", () => {
    expect(patchPresenzeEditor<{ kmValue: string }>(null, { kmValue: "24" })).toBeNull();
  });
});
