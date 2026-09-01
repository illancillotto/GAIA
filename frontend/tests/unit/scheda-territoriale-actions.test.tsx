import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

const state = vi.hoisted(() => ({
  value: {
    parcelId: "parcel-1",
    sheet: null as { status: "queued" | "processing" | "completed" } | null,
    error: null as string | null,
    downloadUrl: null as string | null,
    generate: vi.fn(),
  },
}));

vi.mock("@/components/layout/app-shell-context", () => ({
  useAppShellContext: () => ({
    currentUser: { enabled_modules: ["gis"], role: "viewer" },
  }),
}));

vi.mock("@/components/catasto/gis/use-scheda-territoriale", () => ({
  useSchedaTerritoriale: () => state.value,
}));

import SchedaTerritorialeActions from "@/components/catasto/gis/SchedaTerritorialeActions";
import ParticellaSchedaTerritorialeAction from "@/components/catasto/gis/ParticellaSchedaTerritorialeAction";

const user = { enabled_modules: ["gis"], role: "viewer" };

describe("SchedaTerritorialeActions", () => {
  beforeEach(() => {
    state.value = {
      parcelId: "parcel-1",
      sheet: null,
      error: null,
      downloadUrl: null,
      generate: vi.fn(),
    };
  });

  test.each([
    ["queued", "Scheda in coda..."],
    ["processing", "Generazione scheda..."],
  ] as const)("renders the %s state", (status, label) => {
    state.value.sheet = { status };
    render(
      <SchedaTerritorialeActions token="token" particellaId="parcel-1" currentUser={user} />,
    );
    expect(screen.getByRole("button", { name: label })).toBeDisabled();
  });

  test("renders errors and the completed download", () => {
    state.value.sheet = { status: "completed" };
    state.value.error = "generation failed";
    state.value.downloadUrl = "blob:sheet";
    render(
      <SchedaTerritorialeActions
        token="token"
        particellaId="parcel-1"
        currentUser={user}
        className="surface"
      />,
    );
    expect(screen.getByRole("alert")).toHaveTextContent("generation failed");
    expect(screen.getByRole("link", { name: /Scarica scheda/ })).toHaveAttribute("href", "blob:sheet");
    expect(screen.getByTestId("scheda-territoriale-actions")).toHaveClass("surface");
  });

  test("starts generation when ready", () => {
    render(
      <SchedaTerritorialeActions token="token" particellaId="parcel-1" currentUser={user} />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Genera scheda territoriale" }));
    expect(state.value.generate).toHaveBeenCalledOnce();
  });

  test("binds the authenticated parcel adapter", () => {
    window.localStorage.setItem("gaia.access_token", "token");
    render(<ParticellaSchedaTerritorialeAction particellaId="parcel-1" />);
    expect(screen.getByTestId("scheda-territoriale-actions")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Genera scheda territoriale" }));
    expect(state.value.generate).toHaveBeenCalledOnce();
  });
});
