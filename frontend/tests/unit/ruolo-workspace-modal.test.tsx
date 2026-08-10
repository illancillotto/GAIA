import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import { RuoloWorkspaceModal } from "@/components/ruolo/workspace-modal";

describe("RuoloWorkspaceModal", () => {
  test("renders responsive embedded workspace and closes with escape or button", () => {
    const onClose = vi.fn();
    const { unmount } = render(
      <RuoloWorkspaceModal
        open
        href="/ruolo/avvisi/avviso-1?anno=2025"
        title="Dettaglio avviso"
        description="Avviso 01 per RSSMRA."
        onClose={onClose}
      />,
    );

    expect(screen.getByRole("dialog")).toHaveAttribute("aria-modal", "true");
    expect(screen.getByText("Workspace rapido")).toBeInTheDocument();
    expect(screen.getByText("Avviso 01 per RSSMRA.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Apri pagina" })).toHaveAttribute(
      "href",
      "/ruolo/avvisi/avviso-1?anno=2025",
    );
    expect(screen.getByTitle("Dettaglio avviso")).toHaveAttribute(
      "src",
      "/ruolo/avvisi/avviso-1?anno=2025&embedded=1",
    );
    expect(screen.getByText("Caricamento workspace.")).toBeInTheDocument();

    fireEvent.load(screen.getByTitle("Dettaglio avviso"));
    expect(screen.queryByText("Caricamento workspace.")).not.toBeInTheDocument();

    fireEvent.keyDown(window, { key: "Enter" });
    expect(onClose).not.toHaveBeenCalled();
    fireEvent.keyDown(window, { key: "Escape" });
    expect(onClose).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByRole("button", { name: "Chiudi" }));
    expect(onClose).toHaveBeenCalledTimes(2);

    unmount();
    expect(document.body.style.overflow).toBe("");
  });

  test("renders the default description and appends embedded query to clean paths", () => {
    render(
      <RuoloWorkspaceModal
        open
        href="/ruolo/avvisi/avviso-1"
        title="Dettaglio avviso"
        onClose={vi.fn()}
      />,
    );

    expect(
      screen.getByText("Flusso aperto in modale per non perdere il contesto della dashboard."),
    ).toBeInTheDocument();
    expect(screen.getByTitle("Dettaglio avviso")).toHaveAttribute(
      "src",
      "/ruolo/avvisi/avviso-1?embedded=1",
    );
  });

  test("does not render when closed or missing href", () => {
    const { rerender } = render(
      <RuoloWorkspaceModal
        open={false}
        href="/ruolo/avvisi/avviso-1"
        title="Dettaglio avviso"
        onClose={vi.fn()}
      />,
    );

    expect(screen.queryByText("Workspace rapido")).not.toBeInTheDocument();

    rerender(
      <RuoloWorkspaceModal
        open
        href={null}
        title="Dettaglio avviso"
        onClose={vi.fn()}
      />,
    );

    expect(screen.queryByText("Workspace rapido")).not.toBeInTheDocument();
  });
});
