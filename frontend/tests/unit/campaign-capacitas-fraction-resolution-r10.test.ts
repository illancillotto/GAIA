import { describe, expect, test } from "vitest";

import { transitionFractionResolution } from "@/components/elaborazioni/capacitas-fraction-resolution";
import type { FractionResolutionState } from "@/components/elaborazioni/capacitas-fraction-resolution";
import type { CapacitasFrazioneCandidate, CapacitasResolveFragioneResult } from "@/types/api";

const candidate: CapacitasFrazioneCandidate = { frazione_id: "FRA-B", n_rows: 2, ccos: ["100"], stati: ["attivo"] };

function state(overrides: Partial<FractionResolutionState> = {}): FractionResolutionState {
  return Object.freeze({
    particella: Object.freeze({
      id: "00000000-0000-4000-8000-000000000001",
      comune_id: "00000000-0000-4000-8000-000000000010",
      nome_comune: "Uras",
      foglio: "01",
      particella: "680",
      subalterno: null,
      anomaly_type: "multiple_fractions",
      candidates: [candidate],
      capacitas_last_sync_at: null,
      capacitas_last_sync_error: null,
    }),
    selectedFrazioneId: "FRA-A",
    busy: true,
    error: "Previous error",
    success: true,
    ...overrides,
  });
}

function expectPatch(previous: FractionResolutionState, next: FractionResolutionState | null, patch: Partial<FractionResolutionState>) {
  expect(next).toEqual({ ...previous, ...patch });
  expect(next).not.toBe(previous);
  expect(next?.particella).toBe(previous.particella);
  expect(Object.isFrozen(previous)).toBe(true);
  expect(previous.error).toBe("Previous error");
  expect(previous.selectedFrazioneId).toBe("FRA-A");
}

function response(error: string | null): CapacitasResolveFragioneResult {
  return { ok: false, total_rows: 0, imported_certificati: 0, error };
}

describe("R10 fraction-resolution domain transitions", () => {
  test("selection retains busy, error, success and row identity without mutating state or candidate", () => {
    const previous = state();
    const selected = Object.freeze({ ...candidate });
    expect(transitionFractionResolution(null, "selected", selected)).toBeNull();
    expectPatch(previous, transitionFractionResolution(previous, "selected", selected), { selectedFrazioneId: "FRA-B" });
    expect(selected).toEqual(candidate);
  });

  test("start sets busy and clears only error while retaining prior success and selection", () => {
    const previous = state({ busy: false });
    expect(transitionFractionResolution(null, "started", undefined)).toBeNull();
    expectPatch(previous, transitionFractionResolution(previous, "started", undefined), { busy: true, error: null });
  });

  test("synchronization releases busy and sets success while retaining an earlier failure", () => {
    const previous = state({ success: false });
    expect(transitionFractionResolution(null, "synchronized", undefined)).toBeNull();
    expectPatch(previous, transitionFractionResolution(previous, "synchronized", undefined), { busy: false, success: true });
  });

  test.each([
    { error: "Portale indisponibile", expected: "Portale indisponibile" },
    { error: null, expected: "Errore sync" },
    { error: "", expected: "" },
  ])("unsuccessful response retains success with error=$error", ({ error, expected }) => {
    const previous = state();
    const result = Object.freeze(response(error));
    expect(transitionFractionResolution(null, "unsuccessful", result)).toBeNull();
    expectPatch(previous, transitionFractionResolution(previous, "unsuccessful", result), { busy: false, error: expected });
    expect(result.error).toBe(error);
  });

  test.each([
    { rejected: new Error("Timeout Capacitas"), expected: "Timeout Capacitas" },
    { rejected: new Error(""), expected: "" },
    { rejected: "unknown failure", expected: "Errore" },
    { rejected: null, expected: "Errore" },
    { rejected: { message: "Not an Error" }, expected: "Errore" },
  ])("rejection preserves selection and success using the original Error contract: $expected", ({ rejected, expected }) => {
    const previous = state();
    expect(transitionFractionResolution(null, "rejected", rejected)).toBeNull();
    expectPatch(previous, transitionFractionResolution(previous, "rejected", rejected), { busy: false, error: expected });
  });

  test("candidate ID remains lazy behind the null guard and is reevaluated for each nonnull transition", () => {
    let reads = 0;
    const lazyCandidate: CapacitasFrazioneCandidate = {
      ...candidate,
      get frazione_id() {
        reads += 1;
        return "FRA-B";
      },
    };
    expect(transitionFractionResolution(null, "selected", lazyCandidate)).toBeNull();
    expect(reads).toBe(0);
    const previous = state();
    expectPatch(previous, transitionFractionResolution(previous, "selected", lazyCandidate), { selectedFrazioneId: "FRA-B" });
    expect(reads).toBe(1);
    transitionFractionResolution(previous, "selected", lazyCandidate);
    expect(reads).toBe(2);
  });

  test("unsuccessful error remains lazy behind the null guard", () => {
    let reads = 0;
    const result: CapacitasResolveFragioneResult = {
      ok: false,
      total_rows: 0,
      imported_certificati: 0,
      get error() {
        reads += 1;
        return "Late error";
      },
    };
    expect(transitionFractionResolution(null, "unsuccessful", result)).toBeNull();
    expect(reads).toBe(0);
    const previous = state();
    expectPatch(previous, transitionFractionResolution(previous, "unsuccessful", result), { busy: false, error: "Late error" });
    expect(reads).toBe(1);
  });

  test("rejected Error message remains lazy behind the null guard", () => {
    let reads = 0;
    const rejection = new Error("Initial");
    Object.defineProperty(rejection, "message", {
      get() {
        reads += 1;
        return "Late rejection";
      },
    });
    expect(transitionFractionResolution(null, "rejected", rejection)).toBeNull();
    expect(reads).toBe(0);
    const previous = state();
    expectPatch(previous, transitionFractionResolution(previous, "rejected", rejection), { busy: false, error: "Late rejection" });
    expect(reads).toBe(1);
  });
});
