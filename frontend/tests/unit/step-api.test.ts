import { beforeEach, describe, expect, it, vi } from "vitest";

const coreMocks = vi.hoisted(() => ({
  request: vi.fn(),
  requestBlob: vi.fn(),
}));

vi.mock("@/lib/api/core", () => coreMocks);

import * as step from "@/lib/api/step";

const auth = { Authorization: "Bearer token" };

describe("STEP api client", () => {
  beforeEach(() => {
    coreMocks.request.mockReset().mockResolvedValue("ok");
    coreMocks.requestBlob.mockReset().mockResolvedValue("blob");
  });

  it("gestisce credenziali e job", async () => {
    await step.listStepCredentials("token");
    await step.createStepCredential("token", { label: "STEP", username: "u", password: "p" });
    await step.updateStepCredential("token", 3, { active: false });
    await step.deleteStepCredential("token", 3);
    await step.testStepCredential("token", 3);
    await step.listStepJobs("token");
    await step.createStepJob("token", { mode: "sync", max_details: 5 });
    await step.cancelStepJob("token", 9);
    await step.deleteStepJob("token", 9);

    expect(coreMocks.request.mock.calls).toEqual([
      ["/elaborazioni/step/credentials", { headers: auth }],
      ["/elaborazioni/step/credentials", { method: "POST", headers: auth, body: JSON.stringify({ label: "STEP", username: "u", password: "p" }) }],
      ["/elaborazioni/step/credentials/3", { method: "PATCH", headers: auth, body: JSON.stringify({ active: false }) }],
      ["/elaborazioni/step/credentials/3", { method: "DELETE", headers: auth }],
      ["/elaborazioni/step/credentials/3/test", { method: "POST", headers: auth }],
      ["/elaborazioni/step/jobs", { headers: auth }],
      ["/elaborazioni/step/jobs", { method: "POST", headers: auth, body: JSON.stringify({ mode: "sync", max_details: 5 }) }],
      ["/elaborazioni/step/jobs/9/cancel", { method: "POST", headers: auth }],
      ["/elaborazioni/step/jobs/9", { method: "DELETE", headers: auth }],
    ]);
  });

  it("legge archivio, schede, PDF e anomalie con i filtri valorizzati", async () => {
    await step.getStepOverview("token");
    await step.listStepContribuenti("token");
    await step.listStepContribuenti("token", { q: "ROSSI", onlyResiduo: true, page: 2, pageSize: 25 });
    await step.listStepContribuenti("token", { q: "", onlyResiduo: false });
    await step.getStepContribuente("token", "abc");
    await step.listStepLinkAnomalies("token");
    await step.listStepLinkAnomalies("token", { status: "ambiguous", page: 3, pageSize: 50 });
    await step.listStepLinksForAvviso("token", "avviso-1");
    await expect(step.downloadStepDocumentoPdf("token", "doc")).resolves.toBe("blob");

    expect(coreMocks.request.mock.calls.map((call) => call[0])).toEqual([
      "/elaborazioni/step/overview",
      "/elaborazioni/step/contribuenti",
      "/elaborazioni/step/contribuenti?q=ROSSI&only_residuo=true&page=2&page_size=25",
      "/elaborazioni/step/contribuenti",
      "/elaborazioni/step/contribuenti/abc",
      "/elaborazioni/step/ruolo-links",
      "/elaborazioni/step/ruolo-links?status=ambiguous&page=3&page_size=50",
      "/elaborazioni/step/ruolo-avvisi/avviso-1",
    ]);
    expect(coreMocks.requestBlob).toHaveBeenCalledWith("/elaborazioni/step/documenti/doc/pdf", { headers: auth });
  });
});
