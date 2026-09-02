import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import { useRecentBatchesOpenHandler } from "@/components/elaborazioni/recent-batches-open-context";
import { ElaborazioniVisureWorkspaceClient } from "@/app/elaborazioni/visure/visure-workspace-client";

function RecentBatchesOpenProbe() {
  const handler = useRecentBatchesOpenHandler();

  return <div data-testid="context-probe">{handler ? "present" : "missing"}</div>;
}

vi.mock("@/components/elaborazioni/request-workspace", () => ({
  ElaborazioneRequestWorkspace: ({
    embedded,
    initialMode,
    onOpenBatch,
  }: {
    embedded: boolean;
    initialMode: string;
    onOpenBatch?: (batchId: string) => void;
  }) => {
    const contextOpenBatch = useRecentBatchesOpenHandler();

    return (
      <div data-testid="request-workspace" data-embedded={String(embedded)} data-mode={initialMode}>
        <button type="button" onClick={() => onOpenBatch?.("prop-batch")}>
          Apri via prop
        </button>
        <button type="button" onClick={() => contextOpenBatch?.("context-batch")}>
          Apri via context
        </button>
      </div>
    );
  },
}));

vi.mock("@/components/elaborazioni/workspace-modal", () => ({
  ElaborazioneWorkspaceModal: ({
    description,
    href,
    onClose,
    open,
    title,
  }: {
    description?: string | null;
    href: string | null;
    onClose: () => void;
    open: boolean;
    title: string;
  }) => (
    <div data-testid="workspace-modal" data-description={description ?? ""} data-href={href ?? ""} data-open={String(open)} data-title={title}>
      {open ? <button type="button" onClick={onClose}>Chiudi</button> : null}
    </div>
  ),
}));

describe("ElaborazioniVisureWorkspaceClient", () => {
  test("opens batch details in the elaborazioni modal through the explicit prop", () => {
    render(<ElaborazioniVisureWorkspaceClient />);

    expect(screen.getByTestId("request-workspace")).toHaveAttribute("data-embedded", "true");
    expect(screen.getByTestId("request-workspace")).toHaveAttribute("data-mode", "autosync");
    expect(screen.getByTestId("workspace-modal")).toHaveAttribute("data-open", "false");

    fireEvent.click(screen.getByRole("button", { name: "Apri via prop" }));

    expect(screen.getByTestId("workspace-modal")).toHaveAttribute("data-open", "true");
    expect(screen.getByTestId("workspace-modal")).toHaveAttribute("data-href", "/elaborazioni/batches/prop-batch");
    expect(screen.getByTestId("workspace-modal")).toHaveAttribute("data-title", "Dettaglio batch visure");
    expect(screen.getByTestId("workspace-modal")).toHaveAttribute(
      "data-description",
      "Dettaglio aperto in modale per mantenere il contesto del workspace visure.",
    );

    fireEvent.click(screen.getByRole("button", { name: "Chiudi" }));
    expect(screen.getByTestId("workspace-modal")).toHaveAttribute("data-open", "false");
  });

  test("opens batch details in the elaborazioni modal through the provider context", () => {
    render(<ElaborazioniVisureWorkspaceClient />);

    fireEvent.click(screen.getByRole("button", { name: "Apri via context" }));

    expect(screen.getByTestId("workspace-modal")).toHaveAttribute("data-open", "true");
    expect(screen.getByTestId("workspace-modal")).toHaveAttribute("data-href", "/elaborazioni/batches/context-batch");
  });

  test("returns no handler outside the recent batches provider", () => {
    render(<RecentBatchesOpenProbe />);

    expect(screen.getByTestId("context-probe")).toHaveTextContent("missing");
  });
});
