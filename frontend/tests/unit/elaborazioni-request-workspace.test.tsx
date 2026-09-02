import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { ElaborazioneRequestWorkspace, visureImmobileComune, visureSearchMode } from "@/components/elaborazioni/request-workspace";
import { ApiError } from "@/lib/api";
import type { CatastoBatch, CatastoVisuraRequest, ElaborazioneBatchDetail } from "@/types/api";

const api = vi.hoisted(() => ({
  token: "token" as string | null,
  push: vi.fn(),
  getComuni: vi.fn(),
  getBatches: vi.fn(),
  createRichiesta: vi.fn(),
  createBatch: vi.fn(),
  startBatch: vi.fn(),
}));

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: api.push }) }));
vi.mock("@/lib/auth", () => ({ getStoredAccessToken: () => api.token }));
vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  getCatastoComuni: (...args: unknown[]) => api.getComuni(...args),
  getElaborazioneBatches: (...args: unknown[]) => api.getBatches(...args),
  createElaborazioneRichiesta: (...args: unknown[]) => api.createRichiesta(...args),
  createElaborazioneBatch: (...args: unknown[]) => api.createBatch(...args),
  startElaborazioneBatch: (...args: unknown[]) => api.startBatch(...args),
}));
vi.mock("@/components/app/protected-page", () => ({
  ProtectedPage: ({ children, title }: { children: ReactNode; title: string }) => (
    <main data-testid="protected-page" data-title={title}>
      {children}
    </main>
  ),
}));
vi.mock("@/components/elaborazioni/batch-credential-selector", () => ({
  BatchCredentialSelector: () => <div>Credential selector</div>,
}));
vi.mock("@/components/elaborazioni/continuous-catasto-sync-panel", () => ({
  ContinuousCatastoSyncPanel: () => <div>AutoSync panel</div>,
}));
vi.mock("@/components/elaborazioni/recent-batches-panel", () => ({
  RecentBatchesPanel: () => <div>Recent batches panel</div>,
}));

function visuraRequest(overrides: Partial<CatastoVisuraRequest> = {}): CatastoVisuraRequest {
  return {
    id: "req-1",
    batch_id: "batch-1",
    user_id: 1,
    row_index: 1,
    search_mode: "immobile",
    comune: "Oristano",
    comune_codice: "F205",
    catasto: "Terreni",
    sezione: null,
    foglio: "12",
    particella: "3",
    subalterno: null,
    tipo_visura: "Sintetica",
    subject_kind: null,
    subject_id: null,
    request_type: null,
    intestazione: null,
    status: "pending",
    current_operation: null,
    error_message: null,
    attempts: 0,
    sister_credential_id: null,
    sister_remote_request_id: null,
    sister_remote_state: null,
    retry_not_before: null,
    last_error_code: null,
    captcha_image_path: null,
    captcha_requested_at: null,
    captcha_expires_at: null,
    captcha_skip_requested: false,
    artifact_dir: null,
    document_id: null,
    created_at: "2026-09-01T10:00:00Z",
    processed_at: null,
    ...overrides,
  };
}

function batch(overrides: Partial<CatastoBatch> = {}): CatastoBatch {
  return {
    id: "batch-1",
    user_id: 1,
    name: "Lotto A",
    status: "processing",
    total_items: 2,
    completed_items: 1,
    failed_items: 0,
    skipped_items: 0,
    not_found_items: 0,
    source_filename: "file.csv",
    current_operation: "Download",
    report_json_path: null,
    report_md_path: null,
    created_at: "2026-09-01T10:00:00Z",
    started_at: "2026-09-01T10:01:00Z",
    completed_at: null,
    ...overrides,
  };
}

function draftBatch(overrides: Partial<ElaborazioneBatchDetail> = {}): ElaborazioneBatchDetail {
  return {
    ...batch({ id: "draft-1", name: "Bozza", status: "pending", started_at: null }),
    requests: [visuraRequest({ batch_id: "draft-1" })],
    ...overrides,
  };
}

async function openBatchMode(): Promise<void> {
  fireEvent.click(screen.getByRole("button", { name: /Import batch/ }));
  expect(await screen.findByText("Caricamento file e validazione preliminare")).toBeInTheDocument();
}

function chooseFile(file: File | null): void {
  const input = document.querySelector('input[type="file"]') as HTMLInputElement;
  fireEvent.change(input, { target: { files: file ? [file] : [] } });
}

describe("visure flow helpers", () => {
  test("normalizes search mode and immobile comune fallbacks", () => {
    expect(visureSearchMode("soggetto")).toBe("soggetto");
    expect(visureSearchMode("immobile")).toBe("immobile");
    expect(visureSearchMode(undefined)).toBe("immobile");
    expect(visureImmobileComune("Oristano", "")).toBe("Oristano");
    expect(visureImmobileComune(undefined, "Cabras")).toBe("Cabras");
    expect(visureImmobileComune(undefined, "")).toBe("");
  });
});

describe("ElaborazioneRequestWorkspace", () => {
  beforeEach(() => {
    api.token = "token";
    api.push.mockReset();
    api.getComuni.mockReset().mockResolvedValue([{ id: 1, nome: "Oristano", codice_sister: "F205", ufficio: "OR" }]);
    api.getBatches.mockReset().mockImplementation((_token: string, status: string) => {
      if (status === "processing") {
        return Promise.resolve([batch({ id: "proc-old", name: "Vecchio", created_at: "2026-08-01T10:00:00Z", started_at: "2026-08-01T10:00:00Z" })]);
      }
      return Promise.resolve([
        batch({
          id: "pend-new",
          name: null,
          status: "pending",
          current_operation: null,
          started_at: null,
          created_at: "2026-09-02T10:00:00Z",
        }),
      ]);
    });
    api.createRichiesta.mockReset().mockResolvedValue(batch({ id: "single-1" }));
    api.createBatch.mockReset().mockResolvedValue(draftBatch());
    api.startBatch.mockReset().mockResolvedValue(batch({ id: "draft-1" }));
  });

  test("orders the visure flow cards and switches every workspace mode", async () => {
    const { rerender } = render(<ElaborazioneRequestWorkspace embedded />);

    const titles = within(screen.getByTestId("visure-flow-choice"))
      .getAllByRole("button")
      .map((button) => button.querySelector("p")?.textContent);
    expect(titles).toEqual(["AutoSync a ruolo", "Batch recenti", "Import batch", "Visura singola"]);
    expect(screen.getByText("Flusso rapido")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /AutoSync a ruolo/ }));
    expect(await screen.findByText("AutoSync panel")).toBeInTheDocument();
    expect(screen.getByText("Sincronizzazione continua")).toBeInTheDocument();
    expect(screen.getByText("4 scope")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Batch recenti/ }));
    expect(await screen.findByText("Recent batches panel")).toBeInTheDocument();
    expect(screen.getByText("Import guidato")).toBeInTheDocument();
    expect(screen.getByText("Recenti")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Import batch/ }));
    expect(await screen.findByText("Caricamento file e validazione preliminare")).toBeInTheDocument();
    expect(screen.getByText("Batch")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Visura singola/ }));
    expect(await screen.findByText("Parametri catastali della visura singola")).toBeInTheDocument();

    rerender(<ElaborazioneRequestWorkspace embedded initialMode="batch" />);
    expect(await screen.findByText("Caricamento file e validazione preliminare")).toBeInTheDocument();
  });

  test("wraps the standalone workspace in the protected page shell", () => {
    render(<ElaborazioneRequestWorkspace />);
    expect(screen.getByTestId("protected-page")).toHaveAttribute("data-title", "Elaborazioni massive Catasto");
    expect(screen.getByText(/Un solo ingresso per il runtime elaborazioni/)).toBeInTheDocument();
  });

  test("loads comuni, skips work without a token and reports both error shapes", async () => {
    api.getComuni.mockRejectedValueOnce(new Error("comuni down"));
    const { unmount } = render(<ElaborazioneRequestWorkspace embedded />);
    expect(await screen.findByText("comuni down")).toBeInTheDocument();
    unmount();

    api.getComuni.mockRejectedValueOnce("comuni raw");
    const second = render(<ElaborazioneRequestWorkspace embedded />);
    expect(await screen.findByText("Errore caricamento comuni")).toBeInTheDocument();
    second.unmount();

    api.token = null;
    render(<ElaborazioneRequestWorkspace embedded />);
    fireEvent.click(screen.getByRole("button", { name: /Ricerca per soggetto/ }));
    fireEvent.change(screen.getByPlaceholderText("RSSMRA80A01H501U oppure 01234567890"), { target: { value: "RSSMRA80A01H501U" } });
    fireEvent.click(screen.getByRole("button", { name: "Avvia ricerca soggetto" }));
    expect(api.createRichiesta).not.toHaveBeenCalled();
  });

  test("prefills the first comune and submits a trimmed immobile visura through the overlay", async () => {
    const onOpenBatch = vi.fn();
    render(<ElaborazioneRequestWorkspace embedded onOpenBatch={onOpenBatch} />);

    expect(await screen.findByRole("option", { name: "Oristano" })).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Comune"), { target: { value: "Oristano" } });
    fireEvent.change(screen.getByPlaceholderText("Es. 5"), { target: { value: "12" } });
    fireEvent.change(screen.getByPlaceholderText("Es. 120"), { target: { value: "3" } });
    fireEvent.change(screen.getByLabelText("Subalterno"), { target: { value: "7" } });
    fireEvent.change(screen.getByLabelText("Sezione"), { target: { value: "  " } });
    fireEvent.change(screen.getByLabelText("Catasto"), { target: { value: "Terreni" } });
    fireEvent.click(screen.getByRole("button", { name: "Avvia visura singola" }));

    await waitFor(() => expect(api.createRichiesta).toHaveBeenCalled());
    expect(api.createRichiesta.mock.calls[0][1]).toMatchObject({
      search_mode: "immobile",
      comune: "Oristano",
      catasto: "Terreni",
      foglio: "12",
      particella: "3",
      subalterno: "7",
      sezione: undefined,
    });
    expect(onOpenBatch).toHaveBeenCalledWith("single-1");
  });

  test("navigates after a single visura when no overlay handler is provided", async () => {
    render(<ElaborazioneRequestWorkspace embedded />);
    await screen.findByRole("option", { name: "Oristano" });
    fireEvent.change(screen.getByLabelText("Comune"), { target: { value: "Oristano" } });
    fireEvent.change(screen.getByPlaceholderText("Es. 5"), { target: { value: "1" } });
    fireEvent.change(screen.getByPlaceholderText("Es. 120"), { target: { value: "2" } });
    fireEvent.click(screen.getByRole("button", { name: "Avvia visura singola" }));
    await waitFor(() => expect(api.push).toHaveBeenCalledWith("/elaborazioni/batches/single-1"));
  });

  test("submits a subject search and reports both single-visura failure shapes", async () => {
    const { unmount } = render(<ElaborazioneRequestWorkspace embedded />);
    await screen.findByRole("option", { name: "Oristano" });
    fireEvent.click(screen.getByRole("button", { name: /Ricerca per soggetto/ }));
    fireEvent.change(screen.getByPlaceholderText("RSSMRA80A01H501U oppure 01234567890"), { target: { value: "  RSSMRA80A01H501U  " } });
    fireEvent.change(screen.getByLabelText("Tipo soggetto"), { target: { value: "PNF" } });
    fireEvent.change(screen.getByLabelText("Tipo richiesta"), { target: { value: "STORICA" } });
    fireEvent.change(screen.getByPlaceholderText("Opzionale, utile per identificazione e naming documento"), { target: { value: "  Rossi  " } });
    fireEvent.click(screen.getByRole("button", { name: "Avvia ricerca soggetto" }));

    await waitFor(() => expect(api.createRichiesta).toHaveBeenCalledWith(
      "token",
      expect.objectContaining({
        search_mode: "soggetto",
        subject_kind: "PNF",
        subject_id: "RSSMRA80A01H501U",
        request_type: "STORICA",
        intestazione: "Rossi",
      }),
    ));
    fireEvent.click(screen.getByRole("button", { name: /Ricerca per immobile/ }));
    expect(screen.getByText("Comune, foglio, particella e subalterno opzionale.")).toBeInTheDocument();
    unmount();

    render(<ElaborazioneRequestWorkspace embedded />);
    await screen.findByRole("option", { name: "Oristano" });
    fireEvent.click(screen.getByRole("button", { name: /Ricerca per soggetto/ }));
    fireEvent.change(screen.getByPlaceholderText("RSSMRA80A01H501U oppure 01234567890"), { target: { value: "RSSMRA80A01H501U" } });
    api.createRichiesta.mockRejectedValueOnce(new Error("sister down"));
    fireEvent.click(screen.getByRole("button", { name: "Avvia ricerca soggetto" }));
    expect(await screen.findByText("sister down")).toBeInTheDocument();

    api.createRichiesta.mockRejectedValueOnce("raw fail");
    fireEvent.click(screen.getByRole("button", { name: "Avvia ricerca soggetto" }));
    expect(await screen.findByText("Errore avvio visura singola")).toBeInTheDocument();
  });

  test("shows validation messages for invalid immobile fields", async () => {
    render(<ElaborazioneRequestWorkspace embedded />);
    await screen.findByRole("option", { name: "Oristano" });
    fireEvent.change(screen.getByLabelText("Comune"), { target: { value: "" } });
    fireEvent.change(screen.getByPlaceholderText("Es. 5"), { target: { value: "ab" } });
    fireEvent.change(screen.getByPlaceholderText("Es. 120"), { target: { value: "xy" } });
    fireEvent.change(screen.getByLabelText("Subalterno"), { target: { value: "sub" } });
    fireEvent.click(screen.getByRole("button", { name: "Avvia visura singola" }));
    expect(await screen.findByText("Seleziona un comune")).toBeInTheDocument();
    expect(screen.getAllByText("Inserisci un valore numerico")).toHaveLength(2);
    expect(screen.getByText("Solo valori numerici")).toBeInTheDocument();
  });

  test("lists, sorts and opens active batches including the unnamed fallback", async () => {
    render(<ElaborazioneRequestWorkspace embedded />);
    expect(await screen.findByText("Vecchio")).toBeInTheDocument();
    expect(screen.getByText("Batch pend-new")).toBeInTheDocument();
    expect(screen.getByText("In attesa del worker elaborazioni")).toBeInTheDocument();
    expect(screen.getByText(/1 in lavorazione · 1 in attesa/)).toBeInTheDocument();
    fireEvent.click(screen.getAllByRole("button", { name: "Apri batch" })[0]);
    expect(api.push).toHaveBeenCalledWith("/elaborazioni/batches/pend-new");
  });

  test("keeps at most six active batches and shows the loading placeholder", async () => {
    const many = Array.from({ length: 7 }, (_, index) => batch({
      id: `b-${index}`,
      name: `Lotto ${index}`,
      created_at: `2026-09-01T0${index}:00:00Z`,
      started_at: null,
    }));
    api.getBatches.mockImplementation((_token: string, status: string) => Promise.resolve(status === "processing" ? many : []));
    const unmountMany = render(<ElaborazioneRequestWorkspace embedded />);
    expect(await screen.findByText("Lotto 6")).toBeInTheDocument();
    expect(screen.queryByText("Lotto 0")).not.toBeInTheDocument();
    unmountMany.unmount();

    let resolveBusy: ((value: CatastoBatch[]) => void) | undefined;
    api.getBatches.mockImplementation(() => new Promise((resolve) => {
      resolveBusy = resolve;
    }));
    const { unmount } = render(<ElaborazioneRequestWorkspace embedded />);
    expect(await screen.findByText("Caricamento elaborazioni in corso.")).toBeInTheDocument();
    resolveBusy?.([]);
    unmount();
  });

  test("reports active-batch load failures and ignores late completions after unmount", async () => {
    api.getBatches.mockRejectedValueOnce(new Error("batches down")).mockRejectedValueOnce(new Error("batches down"));
    const { unmount } = render(<ElaborazioneRequestWorkspace embedded />);
    expect(await screen.findByText("batches down")).toBeInTheDocument();
    unmount();

    api.getBatches.mockRejectedValueOnce("raw batches").mockRejectedValueOnce("raw batches");
    const second = render(<ElaborazioneRequestWorkspace embedded />);
    expect(await screen.findByText("Errore caricamento elaborazioni in corso")).toBeInTheDocument();
    second.unmount();

    let resolveLate: ((value: CatastoBatch[]) => void) | undefined;
    const hangingSuccess = new Promise<CatastoBatch[]>((resolve) => {
      resolveLate = resolve;
    });
    api.getBatches.mockReturnValue(hangingSuccess);
    const lateSuccess = render(<ElaborazioneRequestWorkspace embedded />);
    lateSuccess.unmount();
    resolveLate?.([]);
    await Promise.resolve();

    let rejectLate: ((reason: unknown) => void) | undefined;
    const hangingFailure = new Promise<CatastoBatch[]>((_, reject) => {
      rejectLate = reject;
    });
    api.getBatches.mockReturnValue(hangingFailure);
    const lateFailure = render(<ElaborazioneRequestWorkspace embedded />);
    lateFailure.unmount();
    rejectLate?.(new Error("late"));
    await Promise.resolve();
  });

  test("refreshes active batches on the polling interval", async () => {
    vi.useFakeTimers();
    render(<ElaborazioneRequestWorkspace embedded />);
    await vi.runOnlyPendingTimersAsync();
    const callsAfterMount = api.getBatches.mock.calls.length;
    await vi.advanceTimersByTimeAsync(10_000);
    expect(api.getBatches.mock.calls.length).toBeGreaterThan(callsAfterMount);
    vi.useRealTimers();
  });

  test("uploads a batch, previews mixed rows and starts it through the overlay", async () => {
    const onOpenBatch = vi.fn();
    api.createBatch.mockResolvedValueOnce(draftBatch({
      skipped_items: 1,
      total_items: 2,
      name: null,
      requests: [
        visuraRequest({ id: "imm", subalterno: "4", current_operation: "Check" }),
        visuraRequest({
          id: "sog",
          row_index: 2,
          search_mode: "soggetto",
          subject_kind: "PF",
          subject_id: "CF1",
          request_type: "STORICA",
          intestazione: "Rossi",
          error_message: "captcha",
        }),
        visuraRequest({
          id: "sog-empty",
          row_index: 3,
          search_mode: "soggetto",
          subject_kind: null,
          subject_id: null,
          request_type: null,
          intestazione: null,
          error_message: null,
          current_operation: null,
        }),
      ],
    }));
    render(<ElaborazioneRequestWorkspace embedded onOpenBatch={onOpenBatch} />);
    await openBatchMode();
    chooseFile(null);
    expect(screen.getByRole("button", { name: "Carica e valida" })).toBeDisabled();
    chooseFile(new File(["a"], "lotto.csv", { type: "text/csv" }));
    fireEvent.change(screen.getByPlaceholderText("Lotto marzo 2026"), { target: { value: "Lotto QA" } });
    fireEvent.click(screen.getByRole("button", { name: "Carica e valida" }));

    expect(await screen.findByText("Bozza batch pronta")).toBeInTheDocument();
    expect(screen.getByText("draft-1")).toBeInTheDocument();
    expect(screen.getByText("Sono state importate 2 righe. Rivedi l'anteprima e poi avvia.")).toBeInTheDocument();
    expect(screen.getByText(/1 record saltati/)).toBeInTheDocument();
    expect(screen.getByText("Fg.12 Part.3 Sub.4")).toBeInTheDocument();
    expect(screen.getByText("STORICA · Rossi")).toBeInTheDocument();
    expect(screen.getByText("ATTUALITA")).toBeInTheDocument();
    expect(screen.getByText("SOGGETTO")).toBeInTheDocument();
    expect(screen.getByText("captcha")).toBeInTheDocument();
    expect(screen.getByText("Check")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Avvia batch" }));
    await waitFor(() => expect(api.startBatch).toHaveBeenCalledWith("token", "draft-1"));
    expect(onOpenBatch).toHaveBeenCalledWith("draft-1");
  });

  test("navigates after starting a batch without an overlay handler", async () => {
    render(<ElaborazioneRequestWorkspace embedded />);
    await openBatchMode();
    chooseFile(new File(["a"], "lotto.csv", { type: "text/csv" }));
    fireEvent.click(screen.getByRole("button", { name: "Carica e valida" }));
    fireEvent.click(await screen.findByRole("button", { name: "Avvia batch" }));
    await waitFor(() => expect(api.push).toHaveBeenCalledWith("/elaborazioni/batches/draft-1"));
  });

  test("reports upload and start failures including ApiError validation rows", async () => {
    render(<ElaborazioneRequestWorkspace embedded />);
    await openBatchMode();
    chooseFile(new File(["a"], "lotto.csv", { type: "text/csv" }));

    api.createBatch.mockRejectedValueOnce(new ApiError("invalid", { errors: [{ row_index: 4, errors: ["comune mancante"] }] }));
    fireEvent.click(screen.getByRole("button", { name: "Carica e valida" }));
    expect(await screen.findByText("Righe da correggere prima dell'avvio")).toBeInTheDocument();
    expect(screen.getByText("Riga 4")).toBeInTheDocument();
    expect(screen.getByText("comune mancante")).toBeInTheDocument();
    expect(screen.getByText("invalid")).toBeInTheDocument();

    api.createBatch.mockRejectedValueOnce(new ApiError("invalid-empty", { errors: undefined }));
    fireEvent.click(screen.getByRole("button", { name: "Carica e valida" }));
    expect(await screen.findByText("invalid-empty")).toBeInTheDocument();
    expect(screen.queryByText("Riga 4")).not.toBeInTheDocument();

    api.createBatch.mockRejectedValueOnce(new ApiError("no-errors", { other: true }));
    fireEvent.click(screen.getByRole("button", { name: "Carica e valida" }));
    expect(await screen.findByText("no-errors")).toBeInTheDocument();

    api.createBatch.mockRejectedValueOnce("upload raw");
    fireEvent.click(screen.getByRole("button", { name: "Carica e valida" }));
    expect(await screen.findByText("Errore upload batch")).toBeInTheDocument();

    api.createBatch.mockResolvedValueOnce(draftBatch());
    fireEvent.click(screen.getByRole("button", { name: "Carica e valida" }));
    await screen.findByRole("button", { name: "Avvia batch" });

    api.startBatch.mockRejectedValueOnce(new Error("start down"));
    fireEvent.click(screen.getByRole("button", { name: "Avvia batch" }));
    expect(await screen.findByText("start down")).toBeInTheDocument();

    api.startBatch.mockRejectedValueOnce("start raw");
    fireEvent.click(screen.getByRole("button", { name: "Avvia batch" }));
    expect(await screen.findByText("Errore avvio batch")).toBeInTheDocument();
  });

  test("skips upload and start when the token disappears after a file is chosen", async () => {
    render(<ElaborazioneRequestWorkspace embedded />);
    await openBatchMode();
    chooseFile(new File(["a"], "lotto.csv", { type: "text/csv" }));
    api.token = null;
    fireEvent.click(screen.getByRole("button", { name: "Carica e valida" }));
    expect(api.createBatch).not.toHaveBeenCalled();

    api.token = "token";
    fireEvent.click(screen.getByRole("button", { name: "Carica e valida" }));
    await screen.findByRole("button", { name: "Avvia batch" });
    api.token = null;
    fireEvent.click(screen.getByRole("button", { name: "Avvia batch" }));
    expect(api.startBatch).not.toHaveBeenCalled();
  });

  test("shows the empty active-batch state after a successful idle load", async () => {
    api.getComuni.mockResolvedValue([]);
    api.getBatches.mockResolvedValue([]);
    render(<ElaborazioneRequestWorkspace embedded />);
    expect(await screen.findByText("Nessuna elaborazione in corso")).toBeInTheDocument();
    expect(screen.getByText("Nessuna elaborazione aperta per l'utente corrente.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Ricerca per soggetto/ }));
    fireEvent.click(screen.getByRole("button", { name: /Ricerca per immobile/ }));
    fireEvent.click(screen.getByRole("button", { name: /Ricerca per soggetto/ }));
    fireEvent.click(screen.getByRole("button", { name: "Avvia ricerca soggetto" }));
    expect(await screen.findByText("Identificativo soggetto obbligatorio")).toBeInTheDocument();
    fireEvent.change(screen.getByPlaceholderText("RSSMRA80A01H501U oppure 01234567890"), { target: { value: "CF1" } });
    fireEvent.change(screen.getByLabelText("Tipo visura"), { target: { value: "Analitica" } });
    fireEvent.click(screen.getByRole("button", { name: "Avvia ricerca soggetto" }));
    await waitFor(() => expect(api.createRichiesta).toHaveBeenCalledWith(
      "token",
      expect.objectContaining({
        search_mode: "soggetto",
        comune: undefined,
        catasto: "Terreni e Fabbricati",
        subject_id: "CF1",
        tipo_visura: "Analitica",
      }),
    ));
  });

  test("omits a blank catasto from the single visura payload", async () => {
    render(<ElaborazioneRequestWorkspace embedded />);
    await screen.findByRole("option", { name: "Oristano" });
    fireEvent.change(screen.getByLabelText("Comune"), { target: { value: "Oristano" } });
    fireEvent.change(screen.getByPlaceholderText("Es. 5"), { target: { value: "1" } });
    fireEvent.change(screen.getByPlaceholderText("Es. 120"), { target: { value: "2" } });
    fireEvent.change(screen.getByLabelText("Catasto"), { target: { value: "" } });
    fireEvent.click(screen.getByRole("button", { name: "Avvia visura singola" }));
    await waitFor(() => expect(api.createRichiesta).toHaveBeenCalledWith(
      "token",
      expect.objectContaining({
        search_mode: "immobile",
        catasto: undefined,
      }),
    ));
  });
});
