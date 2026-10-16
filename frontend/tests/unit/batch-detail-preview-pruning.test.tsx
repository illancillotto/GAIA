import { act, fireEvent, render, screen, within } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ElaborazioneBatchDetailWorkspace } from "@/components/elaborazioni/batch-detail-workspace";
import * as api from "@/lib/api";
import { getStoredAccessToken } from "@/lib/auth";
import type { ElaborazioneBatchDetail } from "@/types/api";

vi.mock("@/components/app/protected-page", () => ({
  ProtectedPage: ({ children }: { children: ReactNode }) => <main>{children}</main>,
}));
vi.mock("@/lib/auth", () => ({ getStoredAccessToken: vi.fn() }));
vi.mock("@/lib/api", () => ({
  createElaborazioneBatchWebSocket: vi.fn(),
  getElaborazioneBatch: vi.fn(),
  cancelElaborazioneBatch: vi.fn(),
  retryFailedElaborazioneBatch: vi.fn(),
  startElaborazioneBatch: vi.fn(),
  downloadCatastoDocumentBlob: vi.fn(),
  downloadElaborazioneBatchZipBlob: vi.fn(),
  downloadElaborazioneBatchReportJsonBlob: vi.fn(),
  downloadElaborazioneBatchReportMarkdownBlob: vi.fn(),
  downloadElaborazioneRequestArtifactsBlob: vi.fn(),
  fetchElaborazioneCaptchaImageBlob: vi.fn(),
  fetchElaborazioneRequestArtifactPreviewBlob: vi.fn(),
  solveElaborazioneCaptcha: vi.fn(),
  skipElaborazioneCaptcha: vi.fn(),
}));

type Request = ElaborazioneBatchDetail["requests"][number];

function request(row: number, overrides: Partial<Request> = {}): Request {
  return {
    id: `r${row}`,
    batch_id: "batch",
    user_id: 1,
    row_index: row,
    search_mode: "immobile",
    comune: `Comune ${row}`,
    comune_codice: "G113",
    catasto: "Terreni",
    sezione: null,
    foglio: "1",
    particella: "2",
    subalterno: null,
    tipo_visura: "Completa",
    subject_kind: null,
    subject_id: null,
    request_type: null,
    intestazione: null,
    status: "completed",
    current_operation: null,
    error_message: null,
    attempts: 1,
    sister_credential_id: "c1",
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
    created_at: "2026-09-07T10:00:00Z",
    processed_at: `2026-09-09T10:0${row}:00Z`,
    ...overrides,
  };
}

function batch(requests: Request[]): ElaborazioneBatchDetail {
  return {
    id: "batch",
    user_id: 1,
    name: "Batch preview",
    status: "failed",
    total_items: requests.length,
    completed_items: 0,
    failed_items: requests.length,
    skipped_items: 0,
    not_found_items: 0,
    source_filename: null,
    current_operation: null,
    report_json_path: null,
    report_md_path: null,
    created_at: "2026-09-07T10:00:00Z",
    started_at: null,
    completed_at: null,
    requests,
    statistics: {
      duration_seconds: 10,
      processed_items: requests.length,
      remaining_items: 0,
      progress_percent: 100,
      success_rate_percent: 0,
      completed_per_hour: 0,
      processed_per_hour: 1,
      estimated_remaining_seconds: 0,
      total_attempts: 1,
      average_attempts: 1,
      credentials_used: [],
    },
  };
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (error: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

const failedArtifact = (row: number) => request(row, { status: "failed", artifact_dir: `/artifact/${row}` });
const fetchPreview = () => vi.mocked(api.fetchElaborazioneRequestArtifactPreviewBlob);

const MAX_TOKEN_READS = 500;

let current: ElaborazioneBatchDetail;
let socket: { onmessage: null | (() => void); close: ReturnType<typeof vi.fn> };

async function flush() {
  await act(async () => {
    await Promise.resolve();
  });
}

async function open(requests: Request[]) {
  current = batch(requests);
  const view = render(<ElaborazioneBatchDetailWorkspace batchId="batch" embedded />);
  await flush();
  return view;
}

async function refresh(requests: Request[]) {
  current = batch(requests);
  act(() => socket.onmessage?.());
  await act(async () => {
    await vi.advanceTimersByTimeAsync(400);
  });
}

function row(index: number) {
  const match = within(screen.getByRole("table"))
    .getAllByRole("row")
    .find((candidate) => within(candidate).queryByText(`Comune ${index}`));
  if (!match) throw new Error(`Missing row ${index}`);
  return match;
}

beforeEach(() => {
  vi.resetAllMocks();
  vi.useFakeTimers();
  // Every preview-effect run reads the token: a bounded counter turns a render loop into a fast failure.
  let tokenReads = 0;
  vi.mocked(getStoredAccessToken).mockImplementation(() => {
    tokenReads += 1;
    if (tokenReads > MAX_TOKEN_READS) {
      throw new Error(`render loop: preview effect ran more than ${MAX_TOKEN_READS} times`);
    }
    return "token";
  });
  socket = { onmessage: null, close: vi.fn() };
  vi.mocked(api.createElaborazioneBatchWebSocket).mockReturnValue(socket as unknown as WebSocket);
  vi.mocked(api.getElaborazioneBatch).mockImplementation(async () => current);
  fetchPreview().mockResolvedValue(new Blob(["png"], { type: "image/png" }));
  vi.mocked(api.downloadCatastoDocumentBlob).mockResolvedValue(new Blob(["pdf"], { type: "application/pdf" }));
  let url = 0;
  URL.createObjectURL = vi.fn(() => `blob:preview-${++url}`);
  URL.revokeObjectURL = vi.fn();
});

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe("batch detail preview pruning", () => {
  it("(a) keeps preview state stable when refreshes do not change the eligible requests", async () => {
    fetchPreview()
      .mockResolvedValueOnce(new Blob(["png"], { type: "image/png" }))
      .mockRejectedValueOnce("offline");
    const view = await open([failedArtifact(1), failedArtifact(2)]);
    await flush();
    expect(fetchPreview()).toHaveBeenCalledTimes(2);

    for (let index = 0; index < 3; index += 1) {
      await refresh([failedArtifact(1), failedArtifact(2)]);
    }
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1000);
    });

    expect(fetchPreview()).toHaveBeenCalledTimes(2);
    expect(URL.createObjectURL).toHaveBeenCalledTimes(1);
    expect(URL.revokeObjectURL).not.toHaveBeenCalled();
    expect(within(row(1)).getByRole("button", { name: "Preview screenshot" })).toBeInTheDocument();
    expect(within(row(2)).queryByRole("button", { name: "Preview screenshot" })).not.toBeInTheDocument();
    view.unmount();
    expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:preview-1");
  });

  it("(b) revokes and forgets a loaded preview when its request leaves the batch", async () => {
    await open([failedArtifact(1)]);
    await flush();
    expect(screen.getByRole("button", { name: "Preview screenshot" })).toBeInTheDocument();

    await refresh([]);
    expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:preview-1");

    await refresh([failedArtifact(1)]);
    await flush();
    expect(fetchPreview()).toHaveBeenCalledTimes(2);
    fireEvent.click(screen.getByRole("button", { name: "Preview screenshot" }));
    expect(screen.getByAltText("Preview artifact richiesta 1")).toHaveAttribute("src", "blob:preview-2");
  });

  it("(c) drops the failed marker of a request that becomes ineligible so it is retried later", async () => {
    fetchPreview().mockRejectedValueOnce("offline");
    await open([failedArtifact(1)]);
    await flush();
    await refresh([failedArtifact(1)]);
    expect(fetchPreview()).toHaveBeenCalledTimes(1);

    await refresh([request(1, { status: "completed", artifact_dir: "/artifact/1" })]);
    expect(fetchPreview()).toHaveBeenCalledTimes(1);

    await refresh([failedArtifact(1)]);
    await flush();
    expect(fetchPreview()).toHaveBeenCalledTimes(2);
    expect(screen.getByRole("button", { name: "Preview screenshot" })).toBeInTheDocument();
  });

  it("(d) drops the loading marker of a pending request that leaves the batch", async () => {
    const first = deferred<Blob>();
    fetchPreview().mockReturnValueOnce(first.promise);
    await open([failedArtifact(1)]);
    expect(screen.getByText("Caricamento preview...")).toBeInTheDocument();

    await refresh([]);
    expect(screen.queryByText("Caricamento preview...")).not.toBeInTheDocument();

    const second = deferred<Blob>();
    fetchPreview().mockReturnValueOnce(second.promise);
    await refresh([failedArtifact(1)]);
    expect(fetchPreview()).toHaveBeenCalledTimes(2);
    expect(screen.getByText("Caricamento preview...")).toBeInTheDocument();

    await act(async () => second.resolve(new Blob(["png"], { type: "image/png" })));
    await act(async () => first.resolve(new Blob(["late"], { type: "image/png" })));
    expect(screen.queryByText("Caricamento preview...")).not.toBeInTheDocument();
    expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:preview-2");
    fireEvent.click(screen.getByRole("button", { name: "Preview screenshot" }));
    expect(screen.getByAltText("Preview artifact richiesta 1")).toHaveAttribute("src", "blob:preview-1");
  });

  it("(e) prunes only the requests that left and keeps urls, mime types and failures of the others", async () => {
    fetchPreview()
      .mockResolvedValueOnce(new Blob(["png"], { type: "image/png" }))
      .mockResolvedValueOnce(new Blob(["png"], { type: "image/png" }))
      .mockRejectedValueOnce("offline");
    const pdf = request(4, { document_id: "doc" });
    await open([failedArtifact(1), failedArtifact(2), failedArtifact(3), pdf]);
    await flush();
    fireEvent.click(within(row(4)).getByRole("button", { name: "Preview PDF" }));
    await flush();
    expect(screen.getByTitle("PDF visura richiesta 4")).toHaveAttribute("src", "blob:preview-3");
    fireEvent.click(screen.getByRole("button", { name: "Chiudi" }));
    expect(fetchPreview()).toHaveBeenCalledTimes(3);

    await refresh([failedArtifact(1), failedArtifact(3), pdf]);
    expect(URL.revokeObjectURL).toHaveBeenCalledTimes(1);
    expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:preview-2");
    expect(fetchPreview()).toHaveBeenCalledTimes(3);

    fireEvent.click(within(row(1)).getByRole("button", { name: "Preview screenshot" }));
    expect(screen.getByText("Preview screen")).toBeInTheDocument();
    expect(screen.getByAltText("Preview artifact richiesta 1")).toHaveAttribute("src", "blob:preview-1");
    fireEvent.click(screen.getByRole("button", { name: "Chiudi" }));
    fireEvent.click(within(row(4)).getByRole("button", { name: "Preview PDF" }));
    expect(api.downloadCatastoDocumentBlob).toHaveBeenCalledTimes(1);
    expect(screen.getByTitle("PDF visura richiesta 4")).toHaveAttribute("src", "blob:preview-3");
  });
});
