import { render } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import GaiaOrgStructurePage from "@/app/gaia/organigramma/page";

const mocks = vi.hoisted(() => ({
  redirect: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  redirect: mocks.redirect,
}));

describe("Gaia org structure page", () => {
  test("redirects to the Presenze org chart page", () => {
    render(<GaiaOrgStructurePage />);

    expect(mocks.redirect).toHaveBeenCalledWith("/presenze/organigramma");
  });
});
