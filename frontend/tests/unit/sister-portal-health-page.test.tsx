import { describe, expect, test, vi } from "vitest";

import SisterPortalHealthPage from "@/app/elaborazioni/portal-health/page";

const { redirectMock } = vi.hoisted(() => ({ redirectMock: vi.fn() }));

vi.mock("next/navigation", () => ({ redirect: redirectMock }));

describe("SisterPortalHealthPage", () => {
  test("redirects to the health view of the unified SISTER workspace", () => {
    SisterPortalHealthPage();
    expect(redirectMock).toHaveBeenCalledWith("/elaborazioni/sister?view=health");
  });
});
