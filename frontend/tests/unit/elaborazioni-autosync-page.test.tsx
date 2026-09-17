import { describe, expect, test, vi } from "vitest";

import ElaborazioniAutoSyncPage from "@/app/elaborazioni/autosync/page";

const { redirectMock } = vi.hoisted(() => ({ redirectMock: vi.fn() }));

vi.mock("next/navigation", () => ({ redirect: redirectMock }));

describe("ElaborazioniAutoSyncPage", () => {
  test("redirects to the unified SISTER workspace", () => {
    ElaborazioniAutoSyncPage();
    expect(redirectMock).toHaveBeenCalledWith("/elaborazioni/sister");
  });
});
