import { beforeEach, describe, expect, test, vi } from "vitest";

import { getSisterPortalEvents, getSisterPortalHealth } from "@/lib/portal-health-api";
import { request } from "@/lib/api";


vi.mock("@/lib/api", () => ({ request: vi.fn() }));


describe("portal health API", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(request).mockResolvedValue({});
  });

  test("loads summary with defaults and explicit window", async () => {
    await getSisterPortalHealth("token");
    await getSisterPortalHealth("token", 168);
    expect(request).toHaveBeenNthCalledWith(1, "/elaborazioni/portal-health?hours=24", {
      headers: { Authorization: "Bearer token" },
    });
    expect(request).toHaveBeenNthCalledWith(2, "/elaborazioni/portal-health?hours=168", {
      headers: { Authorization: "Bearer token" },
    });
  });

  test("loads recent events with defaults and explicit limits", async () => {
    await getSisterPortalEvents("token");
    await getSisterPortalEvents("token", 720, 25);
    expect(request).toHaveBeenNthCalledWith(
      1,
      "/elaborazioni/portal-health/events?hours=24&limit=100",
      { headers: { Authorization: "Bearer token" } },
    );
    expect(request).toHaveBeenNthCalledWith(
      2,
      "/elaborazioni/portal-health/events?hours=720&limit=25",
      { headers: { Authorization: "Bearer token" } },
    );
  });
});
