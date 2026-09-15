import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { renderToString } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";
import { NativeWorkspaceRenderer as ElaborazioneWorkspaceContent, ElaborazioneWorkspaceModal } from "@/components/elaborazioni/workspace-modal";

vi.mock("@/components/catasto/archive-workspace", () => ({ CatastoArchiveWorkspaceContent: () => <p>Archivio documenti</p> }));
vi.mock("@/components/catasto/document-detail-workspace", () => ({ CatastoDocumentDetailWorkspace: ({ documentId }: { documentId: string }) => <p>Documento {documentId}</p> }));
vi.mock("@/components/elaborazioni/archive-workspace", () => ({ ElaborazioneArchiveWorkspaceContent: () => <p>Archivio lavorazioni</p> }));
vi.mock("@/components/elaborazioni/autodoc-workspace", () => ({ ElaborazioniAutodocWorkspace: () => <p>Autodoc</p> }));
vi.mock("@/components/elaborazioni/batch-detail-workspace", () => ({ ElaborazioneBatchDetailWorkspace: ({ batchId }: { batchId: string }) => <p>Lavorazione {batchId}</p> }));
vi.mock("@/components/elaborazioni/capacitas-workspace", () => ({ ElaborazioniCapacitasWorkspace: ({ initialSection }: { initialSection: string }) => <p>Capacitas {initialSection}</p> }));
vi.mock("@/components/elaborazioni/ade-alignment-workspace", () => ({ ElaborazioniAdeAlignmentWorkspace: () => <p>AdE</p> }));
vi.mock("@/components/elaborazioni/anpr-workspace", () => ({ ElaborazioniAnprWorkspace: () => <p>ANPR</p> }));
vi.mock("@/components/elaborazioni/bonifica-sync-workspace", () => ({ ElaborazioniBonificaSyncWorkspace: () => <p>WhiteCompany</p> }));
vi.mock("@/components/elaborazioni/gaia-mobile-sync-workspace", () => ({ ElaborazioniGaiaMobileSyncWorkspace: () => <p>Mobile</p> }));
vi.mock("@/components/elaborazioni/posta-online-workspace", () => ({ ElaborazioniPostaOnlineWorkspace: () => <p>Posta</p> }));
vi.mock("@/components/elaborazioni/settings-workspace", () => ({ ElaborazioniSettingsWorkspace: () => <p>Impostazioni</p> }));
vi.mock("@/components/presenze/presenze-sync-workspace", () => ({ PresenzeSyncWorkspace: () => <p>Presenze</p> }));
vi.mock("@/components/elaborazioni/request-workspace", () => ({ ElaborazioneRequestWorkspace: ({ initialMode, onOpenBatch }: { initialMode: string; onOpenBatch: (id: string) => void }) =>
  <button onClick={() => onOpenBatch("42")}>Richiesta {initialMode}</button> }));

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

describe("monitor incorporati", () => {
  it.each([
    ["/elaborazioni/batches", "Archivio lavorazioni"],
    ["/elaborazioni/settings", "Impostazioni"], ["/elaborazioni/bonifica", "WhiteCompany"],
    ["/elaborazioni/anpr", "ANPR"], ["/elaborazioni/presenze-sync", "Presenze"],
    ["/elaborazioni/ade-alignment", "AdE"], ["/elaborazioni/autodoc", "Autodoc"],
    ["/elaborazioni/gaia-mobile-sync", "Mobile"], ["/elaborazioni/posta-online", "Posta"],
    ["/catasto/archive?view=documents", "Archivio documenti"],
    ["/elaborazioni/batches/42", "Lavorazione 42"], ["/catasto/documents/123", "Documento 123"],
  ])("riusa il workspace di %s", (href, content) => {
    const onRendered = vi.fn();
    render(<ElaborazioneWorkspaceContent href={href} onNavigate={vi.fn()} onRendered={onRendered} />);
    expect(screen.getByText(content)).toBeInTheDocument();
    expect(onRendered).toHaveBeenCalledOnce();
  });
  it.each(["particelle", "storico", "terreni", "certificati", "anomalie", "incass"])("mantiene la sezione Capacitas %s", (section) => {
    render(<ElaborazioneWorkspaceContent href={`/elaborazioni/capacitas?section=${section}`} onNavigate={vi.fn()} />);
    expect(screen.getByText(`Capacitas ${section}`)).toBeInTheDocument();
  });
  it("legge gli hash e usa la sezione predefinita per valori non riconosciuti", () => {
    const { rerender } = render(<ElaborazioneWorkspaceContent href="/elaborazioni/capacitas#incass" onNavigate={vi.fn()} />);
    expect(screen.getByText("Capacitas incass")).toBeInTheDocument();
    rerender(<ElaborazioneWorkspaceContent href="/elaborazioni/capacitas?section=unknown" onNavigate={vi.fn()} />);
    expect(screen.getByText("Capacitas particelle")).toBeInTheDocument();
  });
  it.each([["/elaborazioni/visure", "single"], ["/elaborazioni/new-single", "single"], ["/elaborazioni/new-batch", "batch"]])("apre la lavorazione dalla richiesta %s", (href, mode) => {
    const onNavigate = vi.fn();
    render(<ElaborazioneWorkspaceContent href={href} onNavigate={onNavigate} />);
    fireEvent.click(screen.getByRole("button", { name: `Richiesta ${mode}` }));
    expect(onNavigate).toHaveBeenCalledWith("/elaborazioni/batches/42");
  });
  it("mantiene il fallback iframe per monitor non nativi e URL non interpretabili", () => {
    const { rerender } = render(<ElaborazioneWorkspaceContent href="/elaborazioni/autosync" onNavigate={vi.fn()} />);
    expect(screen.getByTitle("/elaborazioni/autosync")).toHaveAttribute("src", "/elaborazioni/autosync");
    rerender(<ElaborazioneWorkspaceContent href="http://[" onNavigate={vi.fn()} />);
    expect(screen.getByTitle("http://[")).toBeInTheDocument();
  });
  it("puo renderizzare il workspace senza window lato server", () => {
    vi.stubGlobal("window", undefined);
    expect(renderToString(<ElaborazioneWorkspaceContent href="/elaborazioni/capacitas" onNavigate={vi.fn()} />)).toContain("particelle");
  });
});

describe("modale legacy", () => {
  it("gestisce apertura, cambio destinazione, chiusura e ripristino dello scroll", () => {
    const onClose = vi.fn();
    const { rerender, unmount } = render(<ElaborazioneWorkspaceModal open={false} href={null} title="Monitor" onClose={onClose} />);
    expect(screen.queryByText("Monitor")).not.toBeInTheDocument();
    rerender(<ElaborazioneWorkspaceModal open href={null} title="Monitor" onClose={onClose} />);
    expect(screen.queryByText("Monitor")).not.toBeInTheDocument();
    rerender(<ElaborazioneWorkspaceModal open href="/elaborazioni/visure" title="Monitor" description="Descrizione" onClose={onClose} />);
    expect(screen.getByText("Descrizione")).toBeInTheDocument();
    expect(document.body.style.overflow).toBe("hidden");
    fireEvent.click(screen.getByRole("button", { name: "Richiesta single" }));
    expect(screen.getByText("Lavorazione 42")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Apri pagina" })).toHaveAttribute("href", "/elaborazioni/batches/42");
    fireEvent.keyDown(window, { key: "Enter" });
    expect(onClose).not.toHaveBeenCalled();
    fireEvent.keyDown(window, { key: "Escape" });
    fireEvent.click(screen.getByRole("button", { name: "Chiudi" }));
    expect(onClose).toHaveBeenCalledTimes(2);
    rerender(<ElaborazioneWorkspaceModal open href="/elaborazioni/autosync" title="Monitor" onClose={onClose} />);
    fireEvent.load(screen.getByTitle("/elaborazioni/autosync"));
    expect(screen.queryByText("Caricamento workspace.")).not.toBeInTheDocument();
    unmount();
    expect(document.body.style.overflow).toBe("");
    fireEvent.keyDown(window, { key: "Escape" });
    expect(onClose).toHaveBeenCalledTimes(2);
  });
});
