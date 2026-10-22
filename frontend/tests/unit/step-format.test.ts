import { describe, expect, it } from "vitest";

import {
  formatDate,
  formatEuro,
  formatJobMode,
  formatJobStatus,
  jobStatusClassName,
  summarizeJob,
} from "@/components/elaborazioni/step/step-format";
import type { StepSyncJob } from "@/types/step";

function job(overrides: Partial<StepSyncJob>): StepSyncJob {
  return {
    id: 1,
    credential_id: null,
    requested_by_user_id: null,
    status: "succeeded",
    mode: "sync",
    payload_json: null,
    result_json: null,
    error_detail: null,
    started_at: null,
    completed_at: null,
    created_at: "2026-10-21T10:00:00Z",
    updated_at: "2026-10-21T10:00:00Z",
    ...overrides,
  };
}

describe("step-format", () => {
  it("traduce stati e modalita, conservando i valori sconosciuti", () => {
    expect(formatJobStatus("processing")).toBe("In esecuzione");
    expect(formatJobStatus("weird")).toBe("weird");
    expect(formatJobMode("archive_import")).toBe("Import archivio");
    expect(formatJobMode("other")).toBe("other");
  });

  it("colora gli stati", () => {
    expect(jobStatusClassName("succeeded")).toContain("emerald");
    expect(jobStatusClassName("failed")).toContain("red");
    expect(jobStatusClassName("cancelled")).toContain("gray");
    expect(jobStatusClassName("pending")).toContain("amber");
  });

  it("formatta importi e date senza inventare valori", () => {
    expect(formatEuro(null)).toBe("—");
    expect(formatEuro(undefined)).toBe("—");
    expect(formatEuro("")).toBe("—");
    expect(formatEuro("abc")).toBe("abc");
    expect(formatEuro("1405.12")).toContain("1405,12");
    expect(formatDate(null)).toBe("—");
    expect(formatDate("2024-11-16")).toBe("16/11/2024");
    expect(formatDate("2024")).toBe("2024");
  });

  it("riassume i job", () => {
    expect(summarizeJob(job({ error_detail: "boom" }))).toBe("boom");
    expect(summarizeJob(job({}))).toBe("—");
    expect(summarizeJob(job({ result_json: { ok: true } }))).toBe("Login verificato");
    expect(summarizeJob(job({ result_json: { imported: 10, list_rows: 20, details: 3, errors: [{}] } }))).toBe(
      "10 schede importate · 20 righe elenco · 3 schede lette · 1 errori",
    );
    expect(summarizeJob(job({ result_json: { progress: { imported: 4, list_rows: 5, details: 6 }, errors: [] } }))).toBe(
      "4 schede importate · 5 righe elenco · 6 schede lette",
    );
    expect(summarizeJob(job({ result_json: { imported: "x", errors: "none" } }))).toBe("—");
  });
});
