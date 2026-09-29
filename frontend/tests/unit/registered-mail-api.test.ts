import { beforeEach, describe, expect, test, vi } from "vitest";

import {
  checkRegisteredMailReferences,
  getRegisteredMailCampaignPreview,
  getTributiRegisteredMailSummary,
  updateTributiRegisteredMailAssociation,
} from "@/lib/registered-mail-api";

const request = vi.hoisted(() => vi.fn());
vi.mock("@/lib/api", () => ({ request }));

describe("registered mail API", () => {
  beforeEach(() => request.mockReset().mockResolvedValue({}));

  test("sends the campaign cutoff and annual reference verification", async () => {
    await getRegisteredMailCampaignPreview("token", "2026-09-29T00:00:00+02:00");
    expect(request).toHaveBeenCalledWith(
      "/ruolo/tributi/raccomandate/campaign-preview?created_before=2026-09-29T00%3A00%3A00%2B02%3A00",
      { headers: { Authorization: "Bearer token" } },
    );
    await checkRegisteredMailReferences("token", "mail", "02022", "02023");
    expect(request).toHaveBeenLastCalledWith("/ruolo/tributi/raccomandate/mail/reference-check", {
      method: "POST", headers: { Authorization: "Bearer token" },
      body: JSON.stringify({ ref_2022: "02022", ref_2023: "02023" }),
    });
  });

  test("retains summary and manual-association contracts", async () => {
    await getTributiRegisteredMailSummary("token");
    expect(request).toHaveBeenCalledWith("/ruolo/tributi/raccomandate/summary", { headers: { Authorization: "Bearer token" } });
    await updateTributiRegisteredMailAssociation("token", "mail", { avviso_ids: ["a22", "a23"] });
    expect(request).toHaveBeenLastCalledWith("/ruolo/tributi/raccomandate/mail/association", {
      method: "PATCH", headers: { Authorization: "Bearer token" }, body: JSON.stringify({ avviso_ids: ["a22", "a23"] }),
    });
  });
});
