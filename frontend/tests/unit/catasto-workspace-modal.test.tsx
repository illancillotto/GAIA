import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import { CatastoWorkspaceModal } from "@/components/catasto/workspace-modal";

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

  test("does not render when closed", () => {
    render(
      <CatastoWorkspaceModal
        open={false}
        href="/catasto/distretti/distretto-1"
        title="Distretto 01"
        onClose={vi.fn()}
      />,
    );

    expect(screen.queryByTitle("Distretto 01")).not.toBeInTheDocument();
  });
});
