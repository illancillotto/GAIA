import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { CatastoDocumentDetailWorkspace } from "@/components/catasto/document-detail-workspace";
import type { CatastoDocument } from "@/types/api";
import type { CatParticella } from "@/types/catasto";

const mocks = vi.hoisted(() => ({
  downloadCatastoDocumentBlob: vi.fn(),
  getCatastoDocument: vi.fn(),
  catastoListParticelle: vi.fn(),
  getStoredAccessToken: vi.fn(),
}));

vi.mock("@/lib/api", () => ({
  downloadCatastoDocumentBlob: mocks.downloadCatastoDocumentBlob,
  getCatastoDocument: mocks.getCatastoDocument,
}));

vi.mock("@/lib/api/catasto", () => ({
  catastoListParticelle: mocks.catastoListParticelle,
}));

vi.mock("@/lib/auth", () => ({
  getStoredAccessToken: mocks.getStoredAccessToken,
}));

vi.mock("@/components/app/protected-page", () => ({
  ProtectedPage: ({
    children,
    title,
  }: {
    children: React.ReactNode;
    title: string;
  }) => (
    <div>
      <h1>{title}</h1>
      {children}
    </div>
  ),
}));

vi.mock("@/components/catasto/anagrafica/ParticellaDetailDialog", () => ({
  ParticellaDetailDialog: ({
    open,
    match,
    onClose,
  }: {
    open: boolean;
    match: { particella_id: string; foglio: string; particella: string } | null;
    onClose: () => void;
  }) =>
    open && match ? (
      <div role="dialog">
        Particella {match.particella_id}
        <button type="button" onClick={onClose}>
          Chiudi particella
        </button>
      </div>
    ) : null,
}));

const documentItem: CatastoDocument = {
  id: "doc-1",
  user_id: 1,
  request_id: null,
  batch_id: "batch-1",
  search_mode: "immobile",
  comune: "Marrubiu",
  foglio: "16",
  particella: "292",
  subalterno: null,
  catasto: "T",
  tipo_visura: "Sintetica",
  subject_kind: null,
  subject_id: null,
  request_type: "STORICA",
  intestazione: null,
  filename: "visura.pdf",
  file_size: 1024,
  codice_fiscale: null,
  created_at: "2026-08-22T18:20:00Z",
};

const particella: CatParticella = {
  id: "particella-1",
  comune_id: null,
  national_code: null,
  cod_comune_capacitas: 123,
  codice_catastale: "E972",
  nome_comune: "Marrubiu",
  sezione_catastale: null,
  foglio: "16",
  particella: "292",
  subalterno: null,
  cfm: null,
  superficie_mq: "10000",
  superficie_grafica_mq: null,
  num_distretto: "01",
  nome_distretto: "Distretto",
  source_type: "catasto",
  capacitas_last_sync_at: null,
  capacitas_last_sync_status: null,
  capacitas_last_sync_error: null,
  capacitas_last_sync_job_id: null,
  valid_from: "2026-01-01",
  valid_to: null,
  is_current: true,
  suppressed: false,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
  ha_anagrafica: false,
  utenza_cf: null,
  utenza_denominazione: null,
  indice_key: null,
  indice_label: null,
  indice_hectares_reference: null,
  indice_irriguo_coltura: null,
  indice_irriguo_gruppo_coltura: null,
  indice_irriguo_anno_riferimento: null,
  swapped_capacitas: null,
};

function deferred<T>(): {
  promise: Promise<T>;
  reject: (reason?: unknown) => void;
  resolve: (value: T) => void;
} {
  let reject!: (reason?: unknown) => void;
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((promiseResolve, promiseReject) => {
    resolve = promiseResolve;
    reject = promiseReject;
  });
  return { promise, reject, resolve };
}

describe("CatastoDocumentDetailWorkspace", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    vi.useRealTimers();
  });

  beforeEach(() => {
    mocks.downloadCatastoDocumentBlob.mockReset();
    mocks.getCatastoDocument.mockReset();
    mocks.catastoListParticelle.mockReset();
    mocks.getStoredAccessToken.mockReturnValue("token");
    mocks.getCatastoDocument.mockResolvedValue(documentItem);
    mocks.downloadCatastoDocumentBlob.mockResolvedValue(new Blob(["pdf"], { type: "application/pdf" }));
    vi.stubGlobal("URL", {
      createObjectURL: vi.fn(() => "blob:visura"),
      revokeObjectURL: vi.fn(),
    });
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
  });

  test("opens the particella dialog when the document reference resolves unambiguously", async () => {
    mocks.catastoListParticelle.mockResolvedValue([particella]);

    render(<CatastoDocumentDetailWorkspace documentId="doc-1" embedded />);

    fireEvent.click(await screen.findByRole("button", { name: "Fg.16 Part.292" }));

    await waitFor(() => {
      expect(mocks.catastoListParticelle).toHaveBeenCalledWith("token", {
        nomeComune: "Marrubiu",
        foglio: "16",
        particella: "292",
        limit: 10,
      });
    });
    expect(await screen.findByRole("dialog")).toHaveTextContent("Particella particella-1");

    fireEvent.click(screen.getByRole("button", { name: "Chiudi particella" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  test("resolves references with a matching subalterno", async () => {
    mocks.getCatastoDocument.mockResolvedValue({ ...documentItem, subalterno: "7" });
    mocks.catastoListParticelle.mockResolvedValue([
      { ...particella, id: "wrong-sub", subalterno: "8" },
      { ...particella, id: "right-sub", subalterno: "7" },
    ]);

    render(<CatastoDocumentDetailWorkspace documentId="doc-1" embedded />);

    fireEvent.click(await screen.findByRole("button", { name: "Fg.16 Part.292 Sub.7" }));

    expect(await screen.findByRole("dialog")).toHaveTextContent("Particella right-sub");
  });

  test("renders the protected page wrapper when it is not embedded", async () => {
    render(<CatastoDocumentDetailWorkspace documentId="doc-1" />);

    expect(await screen.findByRole("heading", { name: "Dettaglio documento" })).toBeInTheDocument();
    expect(screen.getByTitle("Viewer PDF visura.pdf")).toHaveAttribute("src", "blob:visura");
  });

  test("keeps the document open and reports an unresolved particella reference", async () => {
    mocks.catastoListParticelle.mockResolvedValue([]);

    render(<CatastoDocumentDetailWorkspace documentId="doc-1" embedded />);

    fireEvent.click(await screen.findByRole("button", { name: "Fg.16 Part.292" }));

    expect(await screen.findByText("Nessuna particella corrente trovata per questo riferimento.")).toBeInTheDocument();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  test("reports an ambiguous particella reference without opening the dialog", async () => {
    mocks.catastoListParticelle.mockResolvedValue([
      particella,
      { ...particella, id: "particella-2" },
    ]);

    render(<CatastoDocumentDetailWorkspace documentId="doc-1" embedded />);

    fireEvent.click(await screen.findByRole("button", { name: "Fg.16 Part.292" }));

    expect(await screen.findByText("Riferimento ambiguo: apri l'elenco particelle per scegliere il dettaglio corretto.")).toBeInTheDocument();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  test("reports lookup failures without leaving the document page", async () => {
    mocks.catastoListParticelle.mockRejectedValue(new Error("Lookup non disponibile"));

    render(<CatastoDocumentDetailWorkspace documentId="doc-1" embedded />);

    fireEvent.click(await screen.findByRole("button", { name: "Fg.16 Part.292" }));

    expect(await screen.findByText("Lookup non disponibile")).toBeInTheDocument();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  test("uses a generic message for unknown lookup failures", async () => {
    mocks.catastoListParticelle.mockRejectedValue("lookup failed");

    render(<CatastoDocumentDetailWorkspace documentId="doc-1" embedded />);

    fireEvent.click(await screen.findByRole("button", { name: "Fg.16 Part.292" }));

    expect(await screen.findByText("Errore apertura dettaglio particella.")).toBeInTheDocument();
  });

  test("does not query particelle when the token is missing at click time", async () => {
    render(<CatastoDocumentDetailWorkspace documentId="doc-1" embedded />);

    const referenceButton = await screen.findByRole("button", { name: "Fg.16 Part.292" });
    mocks.getStoredAccessToken.mockReturnValue(null);
    fireEvent.click(referenceButton);

    expect(await screen.findByText("Riferimento catastale incompleto: impossibile aprire il dettaglio particella.")).toBeInTheDocument();
    expect(mocks.catastoListParticelle).not.toHaveBeenCalled();
  });

  test("disables the particella action when the document reference is incomplete", async () => {
    mocks.getCatastoDocument.mockResolvedValue({ ...documentItem, foglio: null });

    render(<CatastoDocumentDetailWorkspace documentId="doc-1" embedded />);

    expect(await screen.findByRole("button", { name: "Fg.— Part.292" })).toBeDisabled();
    expect(mocks.catastoListParticelle).not.toHaveBeenCalled();
  });

  test("formats incomplete references with a missing particella", async () => {
    mocks.getCatastoDocument.mockResolvedValue({ ...documentItem, particella: null });

    render(<CatastoDocumentDetailWorkspace documentId="doc-1" embedded />);

    expect(await screen.findByRole("button", { name: "Fg.16 Part.—" })).toBeDisabled();
  });

  test("reports load and download errors", async () => {
    mocks.getCatastoDocument.mockRejectedValueOnce(new Error("Documento non disponibile"));

    const { rerender } = render(<CatastoDocumentDetailWorkspace documentId="doc-1" embedded />);

    expect(await screen.findByText("Documento non disponibile")).toBeInTheDocument();

    mocks.getCatastoDocument.mockResolvedValue(documentItem);
    rerender(<CatastoDocumentDetailWorkspace documentId="doc-2" embedded />);
    const downloadButton = await screen.findByRole("button", { name: "Scarica PDF" });
    mocks.downloadCatastoDocumentBlob.mockRejectedValueOnce(new Error("Download fallito"));

    fireEvent.click(downloadButton);

    expect(await screen.findByText("Download fallito")).toBeInTheDocument();
  });

  test("uses generic messages for unknown load and download errors", async () => {
    mocks.getCatastoDocument.mockRejectedValueOnce("load failed");

    const { rerender } = render(<CatastoDocumentDetailWorkspace documentId="doc-1" embedded />);

    expect(await screen.findByText("Errore caricamento documento")).toBeInTheDocument();

    mocks.getCatastoDocument.mockResolvedValue(documentItem);
    rerender(<CatastoDocumentDetailWorkspace documentId="doc-2" embedded />);
    const downloadButton = await screen.findByRole("button", { name: "Scarica PDF" });
    mocks.downloadCatastoDocumentBlob.mockRejectedValueOnce("download failed");

    fireEvent.click(downloadButton);

    expect(await screen.findByText("Errore download documento")).toBeInTheDocument();
  });

  test("ignores download clicks when the token is missing", async () => {
    render(<CatastoDocumentDetailWorkspace documentId="doc-1" embedded />);

    const downloadButton = await screen.findByRole("button", { name: "Scarica PDF" });
    mocks.downloadCatastoDocumentBlob.mockClear();
    mocks.getStoredAccessToken.mockReturnValue(null);
    fireEvent.click(downloadButton);

    expect(mocks.downloadCatastoDocumentBlob).not.toHaveBeenCalled();
  });

  test("downloads the PDF from the document actions", async () => {
    render(<CatastoDocumentDetailWorkspace documentId="doc-1" embedded />);

    const downloadButton = await screen.findByRole("button", { name: "Scarica PDF" });
    mocks.downloadCatastoDocumentBlob.mockResolvedValueOnce(new Blob(["download"], { type: "application/pdf" }));
    const timeoutSpy = vi.spyOn(window, "setTimeout").mockImplementation((handler: TimerHandler) => {
      if (typeof handler === "function") {
        handler();
      }
      return 0;
    });
    fireEvent.click(downloadButton);
    await Promise.resolve();
    await Promise.resolve();
    timeoutSpy.mockRestore();

    expect(mocks.downloadCatastoDocumentBlob).toHaveBeenLastCalledWith("token", "doc-1");
    expect(URL.createObjectURL).toHaveBeenCalledTimes(2);
    expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:visura");
  });

  test("revokes the previous PDF blob when a different document is loaded", async () => {
    const { rerender } = render(<CatastoDocumentDetailWorkspace documentId="doc-1" embedded />);

    expect(await screen.findByTitle("Viewer PDF visura.pdf")).toHaveAttribute("src", "blob:visura");
    mocks.getCatastoDocument.mockResolvedValueOnce({ ...documentItem, id: "doc-2", filename: "visura-2.pdf" });
    rerender(<CatastoDocumentDetailWorkspace documentId="doc-2" embedded />);

    await waitFor(() => {
      expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:visura");
    });
    expect(await screen.findByTitle("Viewer PDF visura-2.pdf")).toBeInTheDocument();
  });

  test("renders fallback states for documents without batch or usable pdf url", async () => {
    mocks.getCatastoDocument.mockResolvedValue({ ...documentItem, batch_id: null });
    vi.stubGlobal("URL", {
      createObjectURL: vi.fn(() => ""),
      revokeObjectURL: vi.fn(),
    });

    render(<CatastoDocumentDetailWorkspace documentId="doc-1" embedded />);

    expect(await screen.findByText("Caricamento PDF in corso.")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Apri batch" })).not.toBeInTheDocument();
  });

  test("does not load data without a document id or token", async () => {
    mocks.getStoredAccessToken.mockReturnValue(null);

    render(<CatastoDocumentDetailWorkspace documentId="doc-1" embedded />);

    await waitFor(() => {
      expect(mocks.getCatastoDocument).not.toHaveBeenCalled();
    });
    expect(screen.getByText("Caricamento metadati documento in corso.")).toBeInTheDocument();
  });

  test("does not load data without a document id", async () => {
    render(<CatastoDocumentDetailWorkspace documentId="" embedded />);

    await waitFor(() => {
      expect(mocks.getCatastoDocument).not.toHaveBeenCalled();
    });
    expect(screen.getByText("Caricamento metadati documento in corso.")).toBeInTheDocument();
  });

  test("revokes blob urls on cleanup paths", async () => {
    const pendingMetadata = deferred<CatastoDocument>();
    const pendingBlob = deferred<Blob>();
    mocks.getCatastoDocument.mockReturnValueOnce(pendingMetadata.promise);
    mocks.downloadCatastoDocumentBlob.mockReturnValueOnce(pendingBlob.promise);

    const { unmount } = render(<CatastoDocumentDetailWorkspace documentId="doc-1" embedded />);
    unmount();
    pendingMetadata.resolve(documentItem);
    pendingBlob.resolve(new Blob(["pdf"], { type: "application/pdf" }));

    await waitFor(() => {
      expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:visura");
    });
  });

  test("ignores load errors after unmount", async () => {
    const pendingMetadata = deferred<CatastoDocument>();
    mocks.getCatastoDocument.mockReturnValueOnce(pendingMetadata.promise);

    const { unmount } = render(<CatastoDocumentDetailWorkspace documentId="doc-1" embedded />);
    unmount();
    pendingMetadata.reject(new Error("late failure"));

    await Promise.resolve();
    expect(screen.queryByText("late failure")).not.toBeInTheDocument();
  });
});
