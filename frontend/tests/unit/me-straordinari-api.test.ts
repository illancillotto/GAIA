import { describe, expect, test, vi } from "vitest";

import { downloadMeStraordinariPeriodRequest, previewMeStraordinariPeriodRequest } from "@/lib/me-straordinari-api";

const mocks = vi.hoisted(() => ({
  request: vi.fn(),
  requestBlob: vi.fn(),
}));

vi.mock("@/lib/api", () => ({
  request: mocks.request,
  requestBlob: mocks.requestBlob,
}));

describe("me straordinari api", () => {
  test("loads a period preview", async () => {
    const payload = { period_start: "2026-08-01", items: [] };
    mocks.request.mockResolvedValueOnce(payload);

    await expect(previewMeStraordinariPeriodRequest("token", "2026-08-01")).resolves.toEqual(payload);
    expect(mocks.request).toHaveBeenCalledWith("/me/presenze/straordinari/preview/2026-08-01", {
      headers: {
        Authorization: "Bearer token",
      },
    });
  });

  test("downloads a period export", async () => {
    const payload = { items: [{ record_id: "record-1", motivation: "Servizio urgente" }] };
    const blob = new Blob(["xlsx"]);
    mocks.requestBlob.mockResolvedValueOnce(blob);

    await expect(downloadMeStraordinariPeriodRequest("token", "xlsx", payload, "2026-08-01")).resolves.toBe(blob);
    expect(mocks.requestBlob).toHaveBeenCalledWith("/me/presenze/straordinari/export/xlsx/2026-08-01", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: "Bearer token",
      },
      body: JSON.stringify(payload),
    });
  });
});
