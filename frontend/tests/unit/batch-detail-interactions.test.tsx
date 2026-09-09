import { act, fireEvent, render, screen, within } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ElaborazioneBatchDetailWorkspace, isReleasedBatchDetail } from "@/components/elaborazioni/batch-detail-workspace";
import * as api from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import type { ElaborazioneBatchDetail } from "@/types/api";

vi.mock("@/components/app/protected-page", () => ({
  ProtectedPage: ({ children }: { children: ReactNode }) => <main>{children}</main>,
}));
vi.mock("@/lib/auth", () => ({ getStoredAccessToken: vi.fn() }));
vi.mock("@/lib/api", () => ({
  createElaborazioneBatchWebSocket: vi.fn(), getElaborazioneBatch: vi.fn(),
  cancelElaborazioneBatch: vi.fn(), retryFailedElaborazioneBatch: vi.fn(), startElaborazioneBatch: vi.fn(),
  downloadCatastoDocumentBlob: vi.fn(), downloadElaborazioneBatchZipBlob: vi.fn(),
  downloadElaborazioneBatchReportJsonBlob: vi.fn(), downloadElaborazioneBatchReportMarkdownBlob: vi.fn(),
  downloadElaborazioneRequestArtifactsBlob: vi.fn(), fetchElaborazioneCaptchaImageBlob: vi.fn(),
  fetchElaborazioneRequestArtifactPreviewBlob: vi.fn(), solveElaborazioneCaptcha: vi.fn(), skipElaborazioneCaptcha: vi.fn(),
}));

type Request = ElaborazioneBatchDetail["requests"][number];
function request(row: number, overrides: Partial<Request> = {}): Request {
  return {
    id: `r${row}`, batch_id: "batch", user_id: 1, row_index: row, search_mode: "immobile",
    comune: `Comune ${row}`, comune_codice: "G113", catasto: "Terreni", sezione: null,
    foglio: "1", particella: "2", subalterno: null, tipo_visura: "Completa",
    subject_kind: null, subject_id: null, request_type: null, intestazione: null,
    status: "completed", current_operation: null, error_message: null, attempts: 1,
    sister_credential_id: "c1", sister_remote_request_id: null, sister_remote_state: null,
    retry_not_before: null, last_error_code: null, captcha_image_path: null,
    captcha_requested_at: null, captcha_expires_at: null, captcha_skip_requested: false,
    artifact_dir: null, document_id: null, created_at: "2026-09-07T10:00:00Z",
    processed_at: `2026-09-09T10:0${row}:00Z`, ...overrides,
  };
}
function batch(overrides: Partial<ElaborazioneBatchDetail> = {}): ElaborazioneBatchDetail {
  return {
    id: "batch", user_id: 1, name: "Batch/test", status: "failed", total_items: 1,
    completed_items: 1, failed_items: 1, skipped_items: 0, not_found_items: 0,
    source_filename: null, current_operation: null, report_json_path: "report.json", report_md_path: "report.md",
    created_at: "2026-09-07T10:00:00Z", started_at: null, completed_at: null,
    requests: [request(1)], statistics: {
      duration_seconds: 100, processed_items: 1, remaining_items: 0, progress_percent: 100,
      success_rate_percent: 100, completed_per_hour: 36, processed_per_hour: 36,
      estimated_remaining_seconds: 0, total_attempts: 1, average_attempts: 1,
      credentials_used: [{ credential_id: "c1", label: "Alessandro", sister_username: "USER", request_count: 1, execution_count: 2, completed_count: 1 }],
    }, ...overrides,
  };
}
function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (error: unknown) => void;
  const promise = new Promise<T>((res, rej) => { resolve = res; reject = rej; });
  return { promise, resolve, reject };
}
async function flush() { await act(async () => { await Promise.resolve(); }); }
let current: ElaborazioneBatchDetail;
let socket: { onmessage: null | (() => void); close: ReturnType<typeof vi.fn> };
async function open(overrides: Partial<ElaborazioneBatchDetail> = {}, embedded = true) {
  current = batch(overrides);
  const view = render(<ElaborazioneBatchDetailWorkspace batchId="batch" embedded={embedded} />);
  await flush();
  return view;
}
async function refresh(next: ElaborazioneBatchDetail) {
  current = next;
  act(() => socket.onmessage?.());
  await act(async () => { await vi.advanceTimersByTimeAsync(400); });
}
function rowNames() {
  return within(screen.getByRole("table")).getAllByRole("row").slice(1)
    .map((row) => within(row).getAllByRole("cell")[1].textContent);
}

beforeEach(() => {
  vi.resetAllMocks();
  vi.useFakeTimers();
  vi.mocked(getStoredAccessToken).mockReturnValue("token");
  current = batch();
  socket = { onmessage: null, close: vi.fn() };
  vi.mocked(api.createElaborazioneBatchWebSocket).mockReturnValue(socket as unknown as WebSocket);
  vi.mocked(api.getElaborazioneBatch).mockImplementation(async () => current);
  for (const fn of [api.downloadCatastoDocumentBlob, api.downloadElaborazioneBatchZipBlob,
    api.downloadElaborazioneBatchReportJsonBlob, api.downloadElaborazioneBatchReportMarkdownBlob,
    api.downloadElaborazioneRequestArtifactsBlob, api.fetchElaborazioneCaptchaImageBlob,
    api.fetchElaborazioneRequestArtifactPreviewBlob]) vi.mocked(fn).mockResolvedValue(new Blob(["data"]));
  let url = 0;
  URL.createObjectURL = vi.fn(() => `blob:preview-${++url}`);
  URL.revokeObjectURL = vi.fn();
  vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
});
afterEach(() => { vi.useRealTimers(); vi.restoreAllMocks(); });

describe("batch detail interactions", () => {
  it.each(["pdf", "artifact", "artifact-retry"])("handles overlapping %s previews across realtime removal and reappearance", async (kind) => {
    const first = deferred<Blob>();
    const second = deferred<Blob>();
    const method = kind === "pdf" ? api.downloadCatastoDocumentBlob : api.fetchElaborazioneRequestArtifactPreviewBlob;
    vi.mocked(method).mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise);
    const item = request(1, { status: kind === "pdf" ? "completed" : "failed", artifact_dir: "/artifact", document_id: kind === "pdf" ? "doc" : null });
    await open({ requests: [item] });
    if (kind === "pdf") fireEvent.click(screen.getByRole("button", { name: "Preview PDF" }));
    await refresh(batch({ requests: [] }));
    await refresh(batch({ requests: [{ ...item }] }));
    if (kind === "pdf") fireEvent.click(screen.getByRole("button", { name: "Preview PDF" }));
    expect(method).toHaveBeenCalledTimes(2);
    await act(async () => {
      if (kind === "artifact-retry") second.reject("offline");
      else second.resolve(new Blob(["latest"], { type: kind === "pdf" ? "application/pdf" : "image/png" }));
    });
    await act(async () => first.resolve(new Blob(["earlier"])));
    if (kind === "artifact-retry") expect(screen.getByRole("button", { name: "Preview screenshot" })).toBeInTheDocument();
    else expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:preview-2");
  });

  it.each(["solve", "skip"])("handles CAPTCHA %s, errors and expired sessions", async (action) => {
    await open({ requests: [request(1, { status: "awaiting_captcha" })] });
    fireEvent.click(screen.getByRole("button", { name: "CAPTCHA 1" }));
    expect(rowNames()).toEqual(["Comune 1"]);
    const method = action === "solve" ? api.solveElaborazioneCaptcha : api.skipElaborazioneCaptcha;
    const label = action === "solve" ? "Invia" : "Salta";
    fireEvent.change(screen.getByPlaceholderText("Inserisci il CAPTCHA"), { target: { value: "abc" } });
    const pending = deferred<never>();
    vi.mocked(method).mockReturnValueOnce(pending.promise);
    fireEvent.click(screen.getByRole("button", { name: label }));
    expect(screen.getByRole("button", { name: label })).toBeDisabled();
    await act(async () => pending.resolve(undefined as never));
    expect(method).toHaveBeenCalledWith(...(action === "solve" ? ["token", "r1", "ABC"] : ["token", "r1"]));
    for (const error of [new Error("captcha failed"), "offline"]) {
      vi.mocked(method).mockRejectedValueOnce(error);
      fireEvent.click(screen.getByRole("button", { name: label }));
      await flush();
      expect(screen.getByText(error instanceof Error ? error.message : `Errore ${action === "solve" ? "invio" : "skip"} CAPTCHA`)).toBeInTheDocument();
    }
    vi.mocked(getStoredAccessToken).mockReturnValue(null);
    fireEvent.click(screen.getByRole("button", { name: label }));
    expect(method).toHaveBeenCalledTimes(3);
    vi.mocked(getStoredAccessToken).mockReturnValue("token");
    await refresh(batch());
    expect(screen.queryByPlaceholderText("Inserisci il CAPTCHA")).not.toBeInTheDocument();
    expect(URL.revokeObjectURL).toHaveBeenCalled();
  });

  it("replaces CAPTCHA images and clears them on failure", async () => {
    await open({ requests: [request(1, { status: "awaiting_captcha" })] });
    await refresh(batch({ requests: [request(2, { status: "awaiting_captcha", search_mode: "soggetto" })] }));
    expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:preview-1");
    for (const error of [new Error("image failed"), "offline"]) {
      vi.mocked(api.fetchElaborazioneCaptchaImageBlob).mockRejectedValueOnce(error);
      await refresh(batch({ requests: [request(3, { status: "awaiting_captcha" })] }));
      expect(screen.getByText(error instanceof Error ? error.message : "Errore caricamento immagine CAPTCHA")).toBeInTheDocument();
      expect(screen.queryByPlaceholderText("Inserisci il CAPTCHA")).not.toBeInTheDocument();
    }
  });

  it.each([true, false])("ignores CAPTCHA responses after unmount (success=%s)", async (success) => {
    const pending = deferred<Blob>();
    vi.mocked(api.fetchElaborazioneCaptchaImageBlob).mockReturnValueOnce(pending.promise);
    const view = await open({ requests: [request(1, { status: "awaiting_captcha" })] });
    view.unmount();
    await act(async () => { if (success) pending.resolve(new Blob(["image"])); else pending.reject("offline"); });
    if (success) expect(URL.revokeObjectURL).toHaveBeenCalled();
  });

  it("opens lazy PDF previews, reuses cached documents and clears them when no longer eligible", async () => {
    const view = await open({ requests: [request(1, { document_id: "doc", artifact_dir: "/artifact" })] });
    const pending = deferred<Blob>();
    vi.mocked(api.downloadCatastoDocumentBlob).mockReturnValueOnce(pending.promise);
    fireEvent.click(screen.getByRole("button", { name: "Preview PDF" }));
    expect(screen.getByRole("button", { name: "Caricamento PDF..." })).toBeDisabled();
    expect(screen.getByText("Caricamento preview...")).toBeInTheDocument();
    await act(async () => pending.resolve(new Blob(["pdf"])));
    expect(screen.getByTitle("PDF visura richiesta 1")).toHaveAttribute("src", "blob:preview-1");
    fireEvent.click(screen.getByRole("button", { name: "Chiudi" }));
    fireEvent.click(screen.getByRole("button", { name: "Preview PDF" }));
    expect(api.downloadCatastoDocumentBlob).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByRole("button", { name: "Chiudi" }));
    await refresh(batch({ requests: [request(1)] }));
    expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:preview-1");
    expect(screen.queryByRole("button", { name: "Preview PDF" })).not.toBeInTheDocument();
    view.unmount();
  });

  it("retries failed PDF downloads, supports documents without artifacts and revoked auth", async () => {
    const view = await open({ requests: [request(1, { document_id: "doc" })] });
    for (const error of [new Error("pdf failed"), "offline"]) {
      vi.mocked(api.downloadCatastoDocumentBlob).mockRejectedValueOnce(error);
      fireEvent.click(screen.getByRole("button", { name: "Preview PDF" }));
      await flush();
      expect(screen.getByText(error instanceof Error ? error.message : "Errore caricamento preview PDF")).toBeInTheDocument();
    }
    const pending = deferred<Blob>();
    vi.mocked(api.downloadCatastoDocumentBlob).mockReturnValueOnce(pending.promise);
    fireEvent.click(screen.getByRole("button", { name: "Preview PDF" }));
    expect(screen.getByRole("button", { name: "Caricamento PDF..." })).toBeDisabled();
    await act(async () => pending.resolve(new Blob(["pdf"], { type: "application/pdf" })));
    expect(screen.getByTitle("PDF visura richiesta 1")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Chiudi" }));
    vi.mocked(getStoredAccessToken).mockReturnValue(null);
    fireEvent.click(screen.getByRole("button", { name: "Preview PDF" }));
    expect(screen.queryByTitle("PDF visura richiesta 1")).not.toBeInTheDocument();
    view.unmount();
    expect(URL.revokeObjectURL).toHaveBeenCalled();
  });

  it("shows artifact screenshots and does not repeatedly retry failed automatic previews", async () => {
    const pending = deferred<Blob>();
    vi.mocked(api.fetchElaborazioneRequestArtifactPreviewBlob).mockReturnValueOnce(pending.promise);
    const view = await open({ requests: [request(1, { status: "failed", artifact_dir: "/artifact" })] });
    expect(screen.getByText("Caricamento preview...")).toBeInTheDocument();
    await act(async () => pending.resolve(new Blob(["png"])));
    fireEvent.click(screen.getByRole("button", { name: "Preview screenshot" }));
    expect(screen.getByAltText("Preview artifact richiesta 1")).toHaveAttribute("src", "blob:preview-1");
    fireEvent.click(screen.getByRole("button", { name: "Chiudi" }));
    vi.mocked(api.fetchElaborazioneRequestArtifactPreviewBlob).mockRejectedValueOnce("offline");
    await refresh(batch({ requests: [request(2, { status: "not_found", artifact_dir: "/artifact" })] }));
    expect(api.fetchElaborazioneRequestArtifactPreviewBlob).toHaveBeenCalledTimes(2);
    await refresh(batch({ requests: [request(2, { status: "not_found", artifact_dir: "/artifact" })] }));
    expect(api.fetchElaborazioneRequestArtifactPreviewBlob).toHaveBeenCalledTimes(2);
    await refresh(batch({ requests: [] }));
    vi.mocked(api.fetchElaborazioneRequestArtifactPreviewBlob).mockResolvedValueOnce(new Blob(["png"], { type: "image/png" }));
    await refresh(batch({ requests: [request(2, { status: "not_found", artifact_dir: "/artifact" })] }));
    expect(screen.getByRole("button", { name: "Preview screenshot" })).toBeInTheDocument();
    view.unmount();
  });

  it.each(["pdf", "artifact"])("cleans loading state when a pending %s request leaves the batch", async (kind) => {
    const pending = deferred<Blob>();
    const method = kind === "pdf" ? api.downloadCatastoDocumentBlob : api.fetchElaborazioneRequestArtifactPreviewBlob;
    vi.mocked(method).mockReturnValueOnce(pending.promise);
    await open({ requests: [request(1, { status: kind === "pdf" ? "completed" : "failed", artifact_dir: "/artifact", document_id: kind === "pdf" ? "doc" : null })] });
    if (kind === "pdf") fireEvent.click(screen.getByRole("button", { name: "Preview PDF" }));
    await refresh(batch({ requests: [] }));
    await act(async () => pending.resolve(new Blob(["data"])));
    expect(screen.queryByRole("button", { name: /Preview/ })).not.toBeInTheDocument();
    expect(URL.revokeObjectURL).toHaveBeenCalled();
  });

  it("renders loading and unavailable sessions and closes sockets", async () => {
    vi.mocked(getStoredAccessToken).mockReturnValue(null);
    const view = render(<ElaborazioneBatchDetailWorkspace batchId="" />);
    await flush();
    expect(screen.getByText("Caricamento batch in corso.")).toBeInTheDocument();
    expect(api.getElaborazioneBatch).not.toHaveBeenCalled();
    vi.mocked(getStoredAccessToken).mockReturnValue("token");
    view.rerender(<ElaborazioneBatchDetailWorkspace batchId="" />);
    await flush();
    view.rerender(<ElaborazioneBatchDetailWorkspace batchId="batch" />);
    await flush();
    act(() => { socket.onmessage?.(); socket.onmessage?.(); });
    await act(async () => { await vi.advanceTimersByTimeAsync(400); });
    expect(api.getElaborazioneBatch).toHaveBeenCalledTimes(2);
    act(() => socket.onmessage?.());
    view.unmount();
    expect(socket.close).toHaveBeenCalled();
  });

  it.each([new Error("load failed"), "offline"])("shows loading errors: %s", async (error) => {
    vi.mocked(api.getElaborazioneBatch).mockRejectedValue(error);
    vi.mocked(api.createElaborazioneBatchWebSocket).mockReturnValue(null);
    await open();
    expect(screen.getByText(error instanceof Error ? error.message : "Errore caricamento batch")).toBeInTheDocument();
  });

  it("shows credential names and keeps descending order across filters and refreshes", async () => {
    const requests = [request(1), request(3, { status: "failed" }), request(2, { status: "pending", processed_at: null }),
      request(4, { status: "processing", processed_at: null }), request(5, { status: "not_found", processed_at: null }),
      request(6, { status: "skipped", processed_at: null })];
    await open({ requests });
    expect(rowNames()).toEqual(["Comune 3", "Comune 1", "Comune 6", "Comune 5", "Comune 4", "Comune 2"]);
    expect(within(screen.getByRole("table")).getAllByText("Alessandro")).toHaveLength(6);
    for (const [filter, names] of [
      ["In corso 2", ["Comune 4", "Comune 2"]], ["Completate 1", ["Comune 1"]],
      ["Fallite 2", ["Comune 3", "Comune 6"]], ["Non trovate 1", ["Comune 5"]],
    ] as const) {
      fireEvent.click(screen.getByRole("button", { name: filter }));
      expect(rowNames()).toEqual(names);
    }
    fireEvent.click(screen.getByRole("button", { name: "CAPTCHA 0" }));
    expect(screen.getByText("Nessuna richiesta nel filtro selezionato.").closest("td")).toHaveAttribute("colspan", "8");
    fireEvent.click(screen.getByRole("button", { name: "Tutte 6" }));
    await refresh(batch({ requests: [request(1), request(2, { processed_at: "2026-09-09T12:00:00Z", sister_credential_id: null })] }));
    expect(rowNames()).toEqual(["Comune 2", "Comune 1"]);
    expect(screen.getByText("Non assegnata")).toBeInTheDocument();
  });

  it("renders subject and parcel references, terminal states and missing labels", async () => {
    await open({ name: null, status: "completed", requests: [
      request(1, { search_mode: "soggetto", subject_kind: "PF", subject_id: "ABC", request_type: "ATTUALITA", intestazione: "Nome", status: "not_found", current_operation: "Nessuna corrispondenza" }),
      request(2, { search_mode: "soggetto", status: "not_found", current_operation: "Altro" }),
      request(3, { comune: null, foglio: null, particella: null, subalterno: "3", processed_at: null }),
    ] }, false);
    expect(screen.getByText("PF ABC · ATTUALITA")).toBeInTheDocument();
    expect(screen.getByText("Ricerca soggetto")).toBeInTheDocument();
    expect(screen.getByText(/Utente non è titolare/)).toBeInTheDocument();
    expect(screen.getByText(/Fg.- Part.- Sub.3/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Annulla batch" })).toBeDisabled();
  });

  it("recognizes release states", () => {
    expect(isReleasedBatchDetail(null)).toBe(false);
    expect(isReleasedBatchDetail(batch({ status: "cancelled", current_operation: "Release requested by user", requests: [request(1)] }))).toBe(false);
    expect(isReleasedBatchDetail(batch({ status: "cancelled", current_operation: "Release requested by user", requests: [request(1, { status: "skipped" })] }))).toBe(false);
    expect(isReleasedBatchDetail(batch({ status: "cancelled", current_operation: "Release requested by user", requests: [request(1, { status: "skipped", current_operation: "Release requested by user" })] }))).toBe(false);
  });

  it.each([
    ["Avvia batch", "startElaborazioneBatch", "Avvio...", "Errore avvio batch"],
    ["Annulla batch", "cancelElaborazioneBatch", "Annullamento...", "Errore annullamento batch"],
    ["Riprova richieste fallite", "retryFailedElaborazioneBatch", "Retry...", "Errore retry batch"],
  ] as const)("handles %s success, errors and expired authentication", async (label, method, busy, fallback) => {
    await open();
    const pending = deferred<never>();
    vi.mocked(api[method]).mockReturnValueOnce(pending.promise);
    fireEvent.click(screen.getByRole("button", { name: label }));
    expect(screen.getByRole("button", { name: busy })).toBeDisabled();
    await act(async () => pending.resolve(undefined as never));
    expect(api[method]).toHaveBeenCalledWith("token", "batch");
    for (const error of [new Error("action failed"), "offline"]) {
      vi.mocked(api[method]).mockRejectedValueOnce(error);
      fireEvent.click(screen.getByRole("button", { name: label }));
      await flush();
      expect(screen.getByText(error instanceof Error ? error.message : fallback)).toBeInTheDocument();
    }
    vi.mocked(getStoredAccessToken).mockReturnValue(null);
    fireEvent.click(screen.getByRole("button", { name: label }));
    expect(api[method]).toHaveBeenCalledTimes(3);
  });

  it("resumes released batches and labels a processing batch", async () => {
    await open({ status: "cancelled", current_operation: "Release requested by user", requests: [request(1, {
      status: "skipped", current_operation: "Release requested by user", error_message: "Credenziale SISTER liberata su richiesta utente",
    })] });
    const pending = deferred<never>();
    vi.mocked(api.startElaborazioneBatch).mockReturnValueOnce(pending.promise);
    fireEvent.click(screen.getByRole("button", { name: "Riprendi batch" }));
    expect(screen.getByRole("button", { name: "Ripresa..." })).toBeDisabled();
    current = batch({ status: "processing" });
    await act(async () => pending.resolve(undefined as never));
    expect(screen.getByRole("button", { name: "Batch in esecuzione" })).toBeDisabled();
  });

  it.each([
    ["Scarica tutti i PDF (ZIP)", "downloadElaborazioneBatchZipBlob", "Preparazione ZIP...", "Errore download ZIP batch", "zip"],
    ["Report JSON", "downloadElaborazioneBatchReportJsonBlob", "Download...", "Errore download report batch", "json"],
    ["Report Markdown", "downloadElaborazioneBatchReportMarkdownBlob", "Download...", "Errore download report batch", "md"],
    ["Scarica artifact", "downloadElaborazioneRequestArtifactsBlob", "Download artifact...", "Errore download artifact richiesta", "artifacts.zip"],
  ] as const)("downloads %s and reports errors", async (label, method, busy, fallback, extension) => {
    await open({ requests: [request(1, { artifact_dir: "/artifact" })] });
    const pending = deferred<Blob>();
    vi.mocked(api[method]).mockReturnValueOnce(pending.promise);
    const names: string[] = [];
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function () { names.push(this.download); });
    fireEvent.click(screen.getByRole("button", { name: label }));
    expect(screen.getByRole("button", { name: busy })).toBeDisabled();
    await act(async () => pending.resolve(new Blob(["download"])));
    expect(names[0]).toBe(extension === "artifacts.zip" ? "request-r1-artifacts.zip" : `Batch-test.${extension}`);
    await act(async () => { await vi.advanceTimersByTimeAsync(1000); });
    expect(URL.revokeObjectURL).toHaveBeenCalled();
    for (const error of [new Error("download failed"), "offline"]) {
      vi.mocked(api[method]).mockRejectedValueOnce(error);
      fireEvent.click(screen.getByRole("button", { name: label }));
      await flush();
      expect(screen.getByText(error instanceof Error ? error.message : fallback)).toBeInTheDocument();
    }
    await refresh(batch({ name: null, requests: [request(1, { artifact_dir: "/artifact" })] }));
    fireEvent.click(screen.getByRole("button", { name: label }));
    await flush();
    vi.mocked(getStoredAccessToken).mockReturnValue(null);
    fireEvent.click(screen.getByRole("button", { name: label }));
    expect(api[method]).toHaveBeenCalledTimes(4);
  });
});
