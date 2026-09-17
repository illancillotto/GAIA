import { describe, expect, test, vi } from "vitest";

import ElaborazioniVisurePage from "@/app/elaborazioni/visure/page";

const { redirectMock } = vi.hoisted(() => ({ redirectMock: vi.fn() }));

vi.mock("next/navigation", () => ({ redirect: redirectMock }));

describe("ElaborazioniVisurePage", () => {
  test("redirects to the unified SISTER workspace", () => {
    ElaborazioniVisurePage();
    expect(redirectMock).toHaveBeenCalledWith("/elaborazioni/sister");
  });
});
