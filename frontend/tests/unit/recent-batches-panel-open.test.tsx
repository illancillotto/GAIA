import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { RecentBatchesOpenProvider } from "@/components/elaborazioni/recent-batches-open-context";
import { RecentBatchesPanel } from "@/components/elaborazioni/recent-batches-panel";
import type { ElaborazioneBatch } from "@/types/api";

const mocks = vi.hoisted(() => ({
  getStoredAccessToken: vi.fn(),
  getElaborazioneBatch: vi.fn(),
  getElaborazioneBatches: vi.fn(),
  retryFailedElaborazioneBatch: vi.fn(),
  startElaborazioneBatch: vi.fn(),
  push: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: mocks.push,
  }),
}));

vi.mock("@/lib/auth", () => ({
  getStoredAccessToken: mocks.getStoredAccessToken,
}));

vi.mock("@/lib/api", () => ({
  getElaborazioneBatch: mocks.getElaborazioneBatch,
  getElaborazioneBatches: mocks.getElaborazioneBatches,
  retryFailedElaborazioneBatch: mocks.retryFailedElaborazioneBatch,
  startElaborazioneBatch: mocks.startElaborazioneBatch,
}));

function buildBatch(id: string, overrides: Partial<ElaborazioneBatch> = {}): ElaborazioneBatch {
  return {
    id,
    name: `Batch ${id}`,
    status: "completed",
    total_items: 1,
    completed_items: 1,
    failed_items: 0,
    not_found_items: 0,
    skipped_items: 0,
    current_operation: "Completed",
    created_at: "2026-07-27T09:00:00Z",
    ...overrides,
  } as ElaborazioneBatch;
}

describe("RecentBatchesPanel open action", () => {
  beforeEach(() => {
    vi.useRealTimers();
    mocks.getStoredAccessToken.mockReturnValue("token");
    mocks.getElaborazioneBatches.mockReset();
    mocks.getElaborazioneBatches.mockResolvedValue([buildBatch("batch-1")]);
    mocks.getElaborazioneBatch.mockReset();
    mocks.getElaborazioneBatch.mockResolvedValue({ id: "batch-1" });
    mocks.retryFailedElaborazioneBatch.mockReset();
    mocks.startElaborazioneBatch.mockReset();
    mocks.push.mockReset();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  test("uses the explicit callback when present", async () => {
    const onOpenBatch = vi.fn();
    mocks.getElaborazioneBatches.mockResolvedValue([buildBatch("batch-without-name", { name: null })]);

    render(<RecentBatchesPanel onOpenBatch={onOpenBatch} />);

    fireEvent.click(await screen.findByRole("button", { name: "Apri" }));

    expect(screen.getByText("batch-without-name")).toBeInTheDocument();
    expect(onOpenBatch).toHaveBeenCalledWith("batch-without-name");
    expect(mocks.push).not.toHaveBeenCalled();
  });

  test("uses the provider callback when no explicit callback is present", async () => {
    const onOpenBatch = vi.fn();

    render(
      <RecentBatchesOpenProvider value={{ onOpenBatch }}>
        <RecentBatchesPanel />
      </RecentBatchesOpenProvider>,
    );

    fireEvent.click(await screen.findByRole("button", { name: "Apri" }));

    expect(onOpenBatch).toHaveBeenCalledWith("batch-1");
    expect(mocks.push).not.toHaveBeenCalled();
  });

  test("falls back to route navigation outside modal-aware workspaces", async () => {
    render(<RecentBatchesPanel />);

    fireEvent.click(await screen.findByRole("button", { name: "Apri" }));

    expect(mocks.push).toHaveBeenCalledWith("/elaborazioni/batches/batch-1");
  });

  test("renders the empty state without a token", async () => {
    mocks.getStoredAccessToken.mockReturnValue(null);

    render(<RecentBatchesPanel />);

    await waitFor(() => {
      expect(screen.getByText("Nessun batch presente")).toBeInTheDocument();
    });
    expect(mocks.getElaborazioneBatches).not.toHaveBeenCalled();
  });

  test("renders the load error message", async () => {
    mocks.getElaborazioneBatches.mockRejectedValue(new Error("API non disponibile"));

    render(<RecentBatchesPanel />);

    expect(await screen.findByText("Errore caricamento batch")).toBeInTheDocument();
    expect(screen.getByText("API non disponibile")).toBeInTheDocument();
  });

  test("renders the generic load error for non-Error failures", async () => {
    mocks.getElaborazioneBatches.mockRejectedValue("KO load");

    render(<RecentBatchesPanel />);

    expect(await screen.findByText("Errore caricamento batch recenti")).toBeInTheDocument();
  });

  test("does not set load errors after unmounting during a failed load", async () => {
    let rejectBatches: (reason?: unknown) => void = () => {};
    mocks.getElaborazioneBatches.mockReturnValue(
      new Promise<ElaborazioneBatch[]>((_, reject) => {
        rejectBatches = reject;
      }),
    );

    const { unmount } = render(<RecentBatchesPanel />);
    unmount();

    await act(async () => {
      rejectBatches(new Error("Errore tardivo"));
    });

    expect(screen.queryByText("Errore tardivo")).not.toBeInTheDocument();
  });

  test("does not update rows after unmounting during a load", async () => {
    let resolveBatches: (value: ElaborazioneBatch[]) => void = () => {};
    mocks.getElaborazioneBatches.mockReturnValue(
      new Promise<ElaborazioneBatch[]>((resolve) => {
        resolveBatches = resolve;
      }),
    );

    const { unmount } = render(<RecentBatchesPanel />);
    unmount();

    await act(async () => {
      resolveBatches([buildBatch("late-batch")]);
    });

    expect(screen.queryByText("Batch late-batch")).not.toBeInTheDocument();
  });

  test("sorts running batches first and limits the visible rows", async () => {
    mocks.getElaborazioneBatches.mockResolvedValue([
      buildBatch("old-completed", { created_at: "2026-07-25T09:00:00Z" }),
      buildBatch("running", { status: "processing", created_at: "2026-07-24T09:00:00Z", not_found_items: 2, skipped_items: 1 }),
      buildBatch("new-completed", { created_at: "2026-07-26T09:00:00Z" }),
    ]);

    render(<RecentBatchesPanel limit={2} />);

    expect(await screen.findByText("Batch running")).toBeInTheDocument();
    expect(screen.getByText("Batch new-completed")).toBeInTheDocument();
    expect(screen.queryByText("Batch old-completed")).not.toBeInTheDocument();
    expect(screen.getByText("n.d. 2")).toBeInTheDocument();
    expect(screen.getByText("skip 1")).toBeInTheDocument();
  });

  test("shows batch statistics returned by the detail endpoint", async () => {
    mocks.getElaborazioneBatch.mockResolvedValue({
      id: "batch-1",
      statistics: {
        duration_seconds: 3723,
        completed_per_hour: 4.5,
        credentials_used: [{ label: "Marco" }],
      },
    });

    render(<RecentBatchesPanel />);

    expect(await screen.findByText(/4,5 visure\/ora/)).toBeInTheDocument();
    expect(screen.getByText("Marco")).toBeInTheDocument();
  });

  test("ignores detail lookup failures for recent batches", async () => {
    mocks.getElaborazioneBatch.mockRejectedValue(new Error("Dettaglio non disponibile"));

    render(<RecentBatchesPanel />);

    expect(await screen.findByText("Batch batch-1")).toBeInTheDocument();
    await waitFor(() => {
      expect(mocks.getElaborazioneBatch).toHaveBeenCalledWith("token", "batch-1");
    });
    expect(screen.queryByText("Errore caricamento batch")).not.toBeInTheDocument();
  });

  test("retries failed batches and updates the row", async () => {
    mocks.getElaborazioneBatches.mockResolvedValue([
      buildBatch("failed-batch", { status: "failed", failed_items: 2, current_operation: "Errore runtime" }),
      buildBatch("unchanged-batch"),
    ]);
    mocks.retryFailedElaborazioneBatch.mockResolvedValue(
      buildBatch("failed-batch", { status: "pending", failed_items: 2, current_operation: "Retry queued" }),
    );

    render(<RecentBatchesPanel />);

    fireEvent.click(await screen.findByRole("button", { name: "Riprova" }));

    await waitFor(() => {
      expect(mocks.retryFailedElaborazioneBatch).toHaveBeenCalledWith("token", "failed-batch");
    });
    expect(screen.queryByText("Errore retry batch")).not.toBeInTheDocument();
  });

  test("shows retry errors in the panel", async () => {
    mocks.getElaborazioneBatches.mockResolvedValue([
      buildBatch("failed-batch", { status: "failed", failed_items: 2, current_operation: "Errore runtime" }),
    ]);
    mocks.retryFailedElaborazioneBatch.mockRejectedValue(new Error("KO retry"));

    render(<RecentBatchesPanel />);

    fireEvent.click(await screen.findByRole("button", { name: "Riprova" }));

    expect(await screen.findByText("KO retry")).toBeInTheDocument();
  });

  test("shows the generic retry error for non-Error failures", async () => {
    mocks.getElaborazioneBatches.mockResolvedValue([
      buildBatch("failed-batch", { status: "failed", failed_items: 2, current_operation: "Errore runtime" }),
    ]);
    mocks.retryFailedElaborazioneBatch.mockRejectedValue("KO retry");

    render(<RecentBatchesPanel />);

    fireEvent.click(await screen.findByRole("button", { name: "Riprova" }));

    expect(await screen.findByText("Errore retry batch")).toBeInTheDocument();
  });

  test("does not retry when the action token is missing", async () => {
    mocks.getElaborazioneBatches.mockResolvedValue([
      buildBatch("failed-batch", { status: "failed", failed_items: 2, current_operation: "Retry queued" }),
    ]);

    render(<RecentBatchesPanel />);

    const retryButton = await screen.findByRole("button", { name: "Riprova" });
    mocks.getStoredAccessToken.mockReturnValue(null);
    fireEvent.click(retryButton);

    expect(mocks.retryFailedElaborazioneBatch).not.toHaveBeenCalled();
  });

  test("starts a released batch and clears previous errors", async () => {
    mocks.getElaborazioneBatches.mockResolvedValue([
      buildBatch("released-batch", {
        status: "cancelled",
        current_operation: "Release requested by user",
        skipped_items: 3,
      }),
      buildBatch("unchanged-batch"),
    ]);
    mocks.startElaborazioneBatch.mockResolvedValue(
      buildBatch("released-batch", { status: "pending", current_operation: "Queued", skipped_items: 0 }),
    );

    render(<RecentBatchesPanel />);

    fireEvent.click(await screen.findByRole("button", { name: "Riprendi" }));

    await waitFor(() => {
      expect(mocks.startElaborazioneBatch).toHaveBeenCalledWith("token", "released-batch");
    });
    expect(screen.queryByText("Errore ripresa batch")).not.toBeInTheDocument();
  });

  test("shows start errors in the panel", async () => {
    mocks.getElaborazioneBatches.mockResolvedValue([
      buildBatch("released-batch", {
        status: "cancelled",
        current_operation: "Release requested by user",
        skipped_items: 3,
      }),
    ]);
    mocks.startElaborazioneBatch.mockRejectedValue(new Error("KO start"));

    render(<RecentBatchesPanel />);

    fireEvent.click(await screen.findByRole("button", { name: "Riprendi" }));

    expect(await screen.findByText("KO start")).toBeInTheDocument();
  });

  test("shows the generic start error for non-Error failures", async () => {
    mocks.getElaborazioneBatches.mockResolvedValue([
      buildBatch("released-batch", {
        status: "cancelled",
        current_operation: "Release requested by user",
        skipped_items: 3,
      }),
    ]);
    mocks.startElaborazioneBatch.mockRejectedValue("KO start");

    render(<RecentBatchesPanel />);

    fireEvent.click(await screen.findByRole("button", { name: "Riprendi" }));

    expect(await screen.findByText("Errore ripresa batch")).toBeInTheDocument();
  });

  test("does not start a released batch when the action token is missing", async () => {
    mocks.getElaborazioneBatches.mockResolvedValue([
      buildBatch("released-batch", {
        status: "cancelled",
        current_operation: "Release requested by user",
        skipped_items: 3,
      }),
    ]);

    render(<RecentBatchesPanel />);

    const startButton = await screen.findByRole("button", { name: "Riprendi" });
    mocks.getStoredAccessToken.mockReturnValue(null);
    fireEvent.click(startButton);

    expect(mocks.startElaborazioneBatch).not.toHaveBeenCalled();
  });

  test("refreshes active batches on the polling interval and visibility events", async () => {
    vi.useFakeTimers();
    mocks.getElaborazioneBatches
      .mockResolvedValueOnce([buildBatch("running", { status: "processing" })])
      .mockResolvedValue([buildBatch("running", { status: "processing" })]);

    render(<RecentBatchesPanel />);

    await act(async () => {});

    expect(screen.getByText("Batch running")).toBeInTheDocument();
    const initialCalls = mocks.getElaborazioneBatches.mock.calls.length;

    await act(async () => {
      vi.advanceTimersByTime(30000);
    });

    expect(mocks.getElaborazioneBatches).toHaveBeenCalledTimes(initialCalls + 1);

    fireEvent(document, new Event("visibilitychange"));

    await act(async () => {});

    expect(mocks.getElaborazioneBatches).toHaveBeenCalledTimes(initialCalls + 2);
  });

  test("skips interval and visibility refreshes while the document is hidden", async () => {
    vi.useFakeTimers();
    const visibilityDescriptor = Object.getOwnPropertyDescriptor(Document.prototype, "visibilityState");
    Object.defineProperty(document, "visibilityState", {
      configurable: true,
      get: () => "hidden",
    });
    mocks.getElaborazioneBatches.mockResolvedValue([buildBatch("running", { status: "processing" })]);

    try {
      render(<RecentBatchesPanel />);

      await act(async () => {});

      const initialCalls = mocks.getElaborazioneBatches.mock.calls.length;

      await act(async () => {
        vi.advanceTimersByTime(30000);
      });
      fireEvent(document, new Event("visibilitychange"));
      await act(async () => {});

      expect(mocks.getElaborazioneBatches).toHaveBeenCalledTimes(initialCalls);
    } finally {
      if (visibilityDescriptor) {
        Object.defineProperty(document, "visibilityState", visibilityDescriptor);
      }
    }
  });
});
