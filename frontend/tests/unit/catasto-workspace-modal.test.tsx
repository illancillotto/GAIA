import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import { CatastoWorkspaceModal } from "@/components/catasto/workspace-modal";

vi.mock("@/components/catasto/distretti/distretto-preview-content", () => ({
  CatastoDistrettoPreviewContent: ({
    distrettoId,
    numDistretto,
    anno,
  }: {
    distrettoId: string;
    numDistretto: string | null;
    anno?: number | null;
  }) => (
    <div data-testid="auto-distretto-preview">
      auto {distrettoId} {numDistretto} {anno ?? "null"}
    </div>
  ),
}));

describe("CatastoWorkspaceModal", () => {
  test("renders optional preview content above the embedded workspace", () => {
    const onClose = vi.fn();

    render(
      <CatastoWorkspaceModal
        open
        href="/catasto/distretti/distretto-1?anno=2026"
        title="Distretto 01"
        description="Sinis Nord Est"
        onClose={onClose}
      >
        <div>Preview GIS distretto</div>
      </CatastoWorkspaceModal>,
    );

    expect(screen.getByText("Preview GIS distretto")).toBeInTheDocument();
    expect(screen.getByTitle("Distretto 01")).toHaveAttribute(
      "src",
      "/catasto/distretti/distretto-1?anno=2026&embedded=1",
    );
    expect(screen.getByText("Caricamento workspace.")).toBeInTheDocument();

    fireEvent.load(screen.getByTitle("Distretto 01"));
    expect(screen.queryByText("Caricamento workspace.")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Indietro" }));
    fireEvent.keyDown(window, { key: "Enter" });
    expect(onClose).not.toHaveBeenCalled();
    fireEvent.keyDown(window, { key: "Escape" });
    expect(onClose).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByRole("button", { name: "Chiudi" }));
    expect(onClose).toHaveBeenCalledTimes(2);
  });

  test("renders the default description and no preview slot", () => {
    render(
      <CatastoWorkspaceModal
        open
        href="/catasto/distretti/distretto-1"
        title="Distretto 01"
        onClose={vi.fn()}
      />,
    );

    expect(
      screen.getByText("Flusso aperto in modale per non perdere il contesto della dashboard."),
    ).toBeInTheDocument();
    expect(screen.queryByText("Preview GIS distretto")).not.toBeInTheDocument();
    expect(screen.getByTitle("Distretto 01")).toHaveAttribute(
      "src",
      "/catasto/distretti/distretto-1?embedded=1",
    );
  });

  test("auto-injects the district preview for catasto district workspaces without explicit children", () => {
    render(
      <CatastoWorkspaceModal
        open
        href="/catasto/distretti/distretto-1?anno=2026"
        title="Distretto 01"
        onClose={vi.fn()}
      />,
    );

    expect(screen.getByTestId("auto-distretto-preview")).toHaveTextContent(
      "auto distretto-1 01 2026",
    );
  });

  test("passes a null district number when the title does not match the standard pattern", () => {
    render(
      <CatastoWorkspaceModal
        open
        href="/catasto/distretti/distretto-1"
        title="Dettaglio rapido"
        onClose={vi.fn()}
      />,
    );

    expect(screen.getByTestId("auto-distretto-preview")).toHaveTextContent(
      "auto distretto-1 null",
    );
  });

  test("does not auto-inject the district preview for non-district workspaces", () => {
    render(
      <CatastoWorkspaceModal
        open
        href="/catasto/particelle/particella-1"
        title="Particella 1"
        onClose={vi.fn()}
      />,
    );

    expect(screen.queryByTestId("auto-distretto-preview")).not.toBeInTheDocument();
  });

  test("does not render when closed", () => {
    render(
      <CatastoWorkspaceModal
        open={false}
        href={null}
        title="Distretto 01"
        onClose={vi.fn()}
      />,
    );

    expect(screen.queryByTitle("Distretto 01")).not.toBeInTheDocument();
  });
});
