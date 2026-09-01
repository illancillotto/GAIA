import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  id: "parcel-1" as unknown,
  actions: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useParams: () => ({ id: mocks.id }),
  useRouter: () => ({ replace: vi.fn() }),
}));

vi.mock("@/lib/use-session-bootstrap", () => ({
  useSessionBootstrap: () => ({
    token: "token",
    currentUser: { enabled_modules: ["gis"], role: "viewer" },
  }),
}));

vi.mock("@/components/catasto/gis/SchedaTerritorialeActions", () => ({
  default: (props: object) => {
    mocks.actions(props);
    return <div data-testid="sheet-actions" />;
  },
}));

import ParticellaDetailLayout from "@/app/catasto/particelle/[id]/layout";

describe("ParticellaDetailLayout", () => {
  beforeEach(() => {
    mocks.id = "parcel-1";
    mocks.actions.mockClear();
  });

  test("renders page content and binds the route parcel", () => {
    render(<ParticellaDetailLayout><p>Dettaglio</p></ParticellaDetailLayout>);
    expect(screen.getByText("Dettaglio")).toBeInTheDocument();
    expect(mocks.actions).toHaveBeenLastCalledWith(expect.objectContaining({
      token: "token",
      particellaId: "parcel-1",
      currentUser: { enabled_modules: ["gis"], role: "viewer" },
    }));
  });

  test.each(["", 7])("rejects an invalid route parcel id", (id) => {
    mocks.id = id;
    render(<ParticellaDetailLayout><p>Dettaglio</p></ParticellaDetailLayout>);
    expect(mocks.actions).toHaveBeenLastCalledWith(expect.objectContaining({ particellaId: null }));
  });
});
