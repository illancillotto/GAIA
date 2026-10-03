import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { renderToString } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";
import { NativeWorkspaceRenderer as ElaborazioneWorkspaceContent, ElaborazioneWorkspaceModal } from "@/components/elaborazioni/workspace-modal";

vi.mock("@/components/catasto/archive-workspace", () => ({ CatastoArchiveWorkspaceContent: ({ embedded, initialView, isolatedView }: { embedded: boolean; initialView: string; isolatedView: boolean }) => <p data-embedded={embedded} data-view={initialView} data-isolated={isolatedView}>Archivio documenti</p> }));
vi.mock("@/components/catasto/document-detail-workspace", () => ({ CatastoDocumentDetailWorkspace: ({ documentId, embedded }: { documentId: string; embedded: boolean }) => <p data-embedded={embedded}>Documento {documentId}</p> }));
vi.mock("@/components/elaborazioni/archive-workspace", () => ({ ElaborazioneArchiveWorkspaceContent: ({ embedded, initialView, isolatedView }: { embedded: boolean; initialView: string; isolatedView: boolean }) => <p data-embedded={embedded} data-view={initialView} data-isolated={isolatedView}>Archivio lavorazioni</p> }));
vi.mock("@/components/elaborazioni/autodoc-workspace", () => ({ ElaborazioniAutodocWorkspace: ({ embedded }: { embedded: boolean }) => <p data-embedded={embedded}>Autodoc</p> }));
vi.mock("@/components/elaborazioni/batch-detail-workspace", () => ({ ElaborazioneBatchDetailWorkspace: ({ batchId, embedded }: { batchId: string; embedded: boolean }) => <p data-embedded={embedded}>Lavorazione {batchId}</p> }));
vi.mock("@/components/elaborazioni/capacitas-workspace", () => ({ ElaborazioniCapacitasWorkspace: ({ initialSection }: { initialSection: string }) => <p>Capacitas {initialSection}</p> }));
vi.mock("@/components/elaborazioni/ade-alignment-workspace", () => ({ ElaborazioniAdeAlignmentWorkspace: ({ embedded }: { embedded: boolean }) => <p data-embedded={embedded}>AdE</p> }));
vi.mock("@/components/elaborazioni/anpr-workspace", () => ({ ElaborazioniAnprWorkspace: ({ embedded }: { embedded: boolean }) => <p data-embedded={embedded}>ANPR</p> }));
vi.mock("@/components/elaborazioni/bonifica-sync-workspace", () => ({ ElaborazioniBonificaSyncWorkspace: ({ embedded }: { embedded: boolean }) => <p data-embedded={embedded}>WhiteCompany</p> }));
vi.mock("@/components/elaborazioni/gaia-mobile-sync-workspace", () => ({ ElaborazioniGaiaMobileSyncWorkspace: ({ embedded }: { embedded: boolean }) => <p data-embedded={embedded}>Mobile</p> }));
vi.mock("@/components/elaborazioni/posta-online-workspace", () => ({ ElaborazioniPostaOnlineWorkspace: ({ embedded }: { embedded: boolean }) => <p data-embedded={embedded}>Posta</p> }));
vi.mock("@/components/elaborazioni/settings-workspace", () => ({ ElaborazioniSettingsWorkspace: ({ embedded }: { embedded: boolean }) => <p data-embedded={embedded}>Impostazioni</p> }));
vi.mock("@/components/presenze/presenze-sync-workspace", () => ({ PresenzeSyncWorkspace: ({ embedded }: { embedded: boolean }) => <p data-embedded={embedded}>Presenze</p> }));
vi.mock("@/components/elaborazioni/request-workspace", () => ({ ElaborazioneRequestWorkspace: ({ initialMode, onOpenBatch }: { initialMode: string; onOpenBatch: (id: string) => void }) =>
  <button onClick={() => onOpenBatch("42")}>Richiesta {initialMode}</button> }));

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

describe("monitor incorporati", () => {
  it.each([
    "/elaborazioni/batches", "/elaborazioni/settings", "/elaborazioni/bonifica",
    "/elaborazioni/anpr", "/elaborazioni/presenze-sync", "/elaborazioni/ade-alignment",
    "/elaborazioni/autodoc", "/elaborazioni/gaia-mobile-sync", "/elaborazioni/posta-online",
    "/catasto/archive?view=documents",
  ])("mantiene il matching esatto della route statica %s", (href) => {
    const extendedHref = `${href}${href.includes("?") ? "&" : "?"}extra=1`;
    const onRendered = vi.fn();
    render(<ElaborazioneWorkspaceContent href={extendedHref} onNavigate={vi.fn()} onRendered={onRendered} />);
    const frame = screen.getByTitle(extendedHref);
    expect(frame).toHaveAttribute("src", extendedHref);
    expect(screen.queryByText("Archivio lavorazioni")).not.toBeInTheDocument();
    expect(onRendered).toHaveBeenCalledOnce();
    fireEvent.load(frame);
    expect(onRendered).toHaveBeenCalledTimes(2);
  });
  it.each([
    ["/elaborazioni/batches", "Archivio lavorazioni", "batches"],
    ["/catasto/archive?view=documents", "Archivio documenti", "documents"],
  ])("preserva le props dell'archivio %s", (href, content, view) => {
    render(<ElaborazioneWorkspaceContent href={href} onNavigate={vi.fn()} />);
    expect(screen.getByText(content)).toHaveAttribute("data-view", view);
    expect(screen.getByText(content)).toHaveAttribute("data-isolated", "true");
    expect(screen.getAllByText(/Archivio/)).toHaveLength(1);
  });
  it.each(["particelle", "storico", "terreni", "certificati", "anomalie", "incass"])("mantiene la sezione hash %s", (section) => {
    render(<ElaborazioneWorkspaceContent href={`/elaborazioni/capacitas#${section}`} onNavigate={vi.fn()} />);
    expect(screen.getByText(`Capacitas ${section}`)).toBeInTheDocument();
  });
  it.each([
    ["?section=storico#incass", "storico"],
    ["?section=#incass", "particelle"],
    ["?section=unknown#incass", "particelle"],
    ["?section=storico&section=incass", "storico"],
    ["?section=%74erreni", "terreni"],
    ["#%74erreni", "particelle"],
    ["?section=STORICO", "particelle"],
    ["?section=+storico+", "particelle"],
    ["?section=toString", "particelle"],
    ["?section=__proto__", "particelle"],
    ["", "particelle"],
  ])("preserva precedenza e fallback per %s", (suffix, section) => {
    render(<ElaborazioneWorkspaceContent href={`/elaborazioni/capacitas${suffix}`} onNavigate={vi.fn()} />);
    expect(screen.getByText(`Capacitas ${section}`)).toBeInTheDocument();
  });
  it.each(["particelle", "storico", "terreni", "certificati", "anomalie", "incass"])("usa il fallback SSR anche con la sezione %s", (section) => {
    vi.stubGlobal("window", undefined);
    const markup = renderToString(<ElaborazioneWorkspaceContent href={`/elaborazioni/capacitas?section=${section}`} onNavigate={vi.fn()} />);
    expect(markup.replace(/<!--.*?-->/g, "")).toContain("Capacitas particelle");
  });

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
    expect(screen.getByText(content)).toHaveAttribute("data-embedded", "true");
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
  it.each(["/elaborazioni/autosync", "/elaborazioni/sister"])("incorpora AutoSync senza shell da %s", (href) => {
    render(<ElaborazioneWorkspaceContent href={href} onNavigate={vi.fn()} />);
    expect(screen.getByRole("button", { name: "Richiesta autosync" })).toBeInTheDocument();
    expect(screen.queryByTitle(href)).not.toBeInTheDocument();
  });
  it("mantiene il fallback iframe per URL non interpretabili", () => {
    render(<ElaborazioneWorkspaceContent href="http://[" onNavigate={vi.fn()} />);
    expect(screen.getByTitle("http://[")).toBeInTheDocument();
  });
  it("puo renderizzare il workspace senza window lato server", () => {
    vi.stubGlobal("window", undefined);
    expect(renderToString(<ElaborazioneWorkspaceContent href="/elaborazioni/capacitas" onNavigate={vi.fn()} />)).toContain("particelle");
  });
});

describe("modale legacy", () => {
  it("gestisce apertura, cambio destinazione, chiusura e ripristino dello scroll", async () => {
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
    await waitFor(() => expect(screen.queryByText("Caricamento workspace.")).not.toBeInTheDocument());
    unmount();
    expect(document.body.style.overflow).toBe("");
    fireEvent.keyDown(window, { key: "Escape" });
    expect(onClose).toHaveBeenCalledTimes(2);
  });
});
