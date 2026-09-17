import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { useRecentBatchesOpenHandler } from "@/components/elaborazioni/recent-batches-open-context";
import { SisterWorkspace } from "@/components/elaborazioni/sister-workspace";

const { useAppShellContextMock } = vi.hoisted(() => ({ useAppShellContextMock: vi.fn() }));

vi.mock("@/components/layout/app-shell-context", () => ({ useAppShellContext: useAppShellContextMock }));
vi.mock("@/components/elaborazioni/sister-portal-health-workspace", () => ({
  SisterPortalHealthWorkspace: () => <div>Telemetria SISTER</div>,
}));

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

function currentUser(role = "viewer", enabledModules = ["catasto"]) {
  return { role, enabled_modules: enabledModules };
}

beforeEach(() => {
  useAppShellContextMock.mockReturnValue({ currentUser: currentUser() });
});

describe("SisterWorkspace", () => {
  test("opens batch details in the elaborazioni modal through the explicit prop", () => {
    render(<SisterWorkspace />);

    expect(screen.getByRole("navigation", { name: "Sezioni SISTER" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Operatività visure" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "Stato portale" })).toHaveAttribute("href", "/elaborazioni/sister?view=health");
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
    render(<SisterWorkspace />);

    fireEvent.click(screen.getByRole("button", { name: "Apri via context" }));

    expect(screen.getByTestId("workspace-modal")).toHaveAttribute("data-open", "true");
    expect(screen.getByTestId("workspace-modal")).toHaveAttribute("data-href", "/elaborazioni/batches/context-batch");
  });

  test.each(["viewer", "admin", "super_admin"])("shows portal health to an authorized %s", (role) => {
    useAppShellContextMock.mockReturnValue({ currentUser: currentUser(role, role === "viewer" ? ["catasto"] : []) });
    render(<SisterWorkspace initialView="health" />);

    expect(screen.getByRole("link", { name: "Stato portale" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByText("Telemetria SISTER")).toBeInTheDocument();
    expect(screen.queryByTestId("request-workspace")).not.toBeInTheDocument();
  });

  test.each([null, currentUser("viewer", [])])("keeps portal health unavailable without Catasto access", (user) => {
    useAppShellContextMock.mockReturnValue({ currentUser: user });
    render(<SisterWorkspace initialView="health" />);

    expect(screen.queryByRole("link", { name: "Stato portale" })).not.toBeInTheDocument();
    expect(screen.getByText("Stato portale non disponibile")).toBeInTheDocument();
    expect(screen.getByTestId("request-workspace")).toBeInTheDocument();
    expect(screen.queryByText("Telemetria SISTER")).not.toBeInTheDocument();
  });

  test("returns no handler outside the recent batches provider", () => {
    render(<RecentBatchesOpenProbe />);

    expect(screen.getByTestId("context-probe")).toHaveTextContent("missing");
  });
});
