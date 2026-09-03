import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { AutoSyncErrorArtifactList } from "@/components/elaborazioni/autosync-error-artifacts";
import { getAutoSyncErrorRequest } from "@/lib/autosync-error-artifacts-api";

const api = vi.hoisted(() => ({
  token: "token" as string | null,
  request: vi.fn(),
  download: vi.fn(),
  preview: vi.fn(),
  apiRequest: vi.fn(),
}));
vi.mock("@/lib/auth", () => ({ getStoredAccessToken: () => api.token }));
vi.mock("@/lib/api", () => ({
  request: (...args: unknown[]) => api.apiRequest(...args),
  downloadElaborazioneRequestArtifactsBlob: (...args: unknown[]) =>
    api.download(...args),
  fetchElaborazioneRequestArtifactPreviewBlob: (...args: unknown[]) =>
    api.preview(...args),
}));

const item = {
  id: "item",
  search_mode: "soggetto",
  subject_kind: "PF",
  subject_identifier: "RSS",
  intestazione: "Mario Rossi",
  attempt_count: 2,
  next_due_at: "2026-08-30T10:00:00Z",
  last_error_message: "Timeout",
  status: "failed",
  linked_request_id: "request",
};
const request = {
  id: "request",
  status: "failed",
  attempts: 2,
  current_operation: "SISTER",
  processed_at: null,
  error_message: "Timeout",
  artifact_dir: "/tmp/artifacts",
};

describe("AutoSyncErrorArtifactList", () => {
  beforeEach(() => {
    api.token = "token";
    api.apiRequest.mockReset().mockResolvedValue(request);
    api.download.mockReset().mockResolvedValue(new Blob(["zip"]));
    api.preview
      .mockReset()
      .mockResolvedValue(new Blob(["image"], { type: "image/png" }));
    api.apiRequest.mockReset().mockResolvedValue(request);
  });

  test("loads a linked request through the dedicated authorized API client", async () => {
    await expect(getAutoSyncErrorRequest("token", "request")).resolves.toEqual(
      request,
    );
    expect(api.apiRequest).toHaveBeenCalledWith(
      "/elaborazioni/requests/request",
      { headers: { Authorization: "Bearer token" } },
    );
  });

  test("shows detail, artifact download and screenshot preview for a linked error", async () => {
    render(<AutoSyncErrorArtifactList items={[item]} />);
    fireEvent.click(screen.getByRole("button", { name: "Dettagli" }));
    expect(await screen.findByText("SISTER")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Scarica artifact" }));
    await waitFor(() =>
      expect(api.download).toHaveBeenCalledWith("token", "request"),
    );
    await new Promise((resolve) => window.setTimeout(resolve, 1000));
    fireEvent.click(screen.getByRole("button", { name: "Preview screenshot" }));
    expect(
      await screen.findByRole("img", { name: /Mario Rossi/ }),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Preview screenshot" }));
    await waitFor(() => expect(api.preview).toHaveBeenCalledTimes(2));
    fireEvent.click(screen.getByRole("button", { name: "Chiudi" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  test("handles missing artifacts and request errors", async () => {
    api.apiRequest.mockResolvedValueOnce({
      ...request,
      artifact_dir: null,
      current_operation: null,
      error_message: null,
    });
    render(<AutoSyncErrorArtifactList items={[item]} />);
    fireEvent.click(screen.getByRole("button", { name: "Dettagli" }));
    expect(
      await screen.findByText(
        "Nessun artifact disponibile per questa richiesta.",
      ),
    ).toBeInTheDocument();
  });

  test("does not expose details when an error is not linked to a request", () => {
    render(
      <AutoSyncErrorArtifactList
        items={[{ ...item, linked_request_id: null }]}
      />,
    );
    expect(
      screen.queryByRole("button", { name: "Dettagli" }),
    ).not.toBeInTheDocument();
  });

  test("renders the empty and parcel error-list states", () => {
    const { rerender } = render(<AutoSyncErrorArtifactList items={[]} />);
    expect(
      screen.getByText("Nessun elemento da mostrare."),
    ).toBeInTheDocument();
    rerender(
      <AutoSyncErrorArtifactList
        items={[
          {
            ...item,
            search_mode: "immobile",
            comune: null,
            foglio: null,
            particella: null,
            last_error_message: null,
          },
        ]}
      />,
    );
    expect(
      screen.getByText("Comune non risolto · Fg. - · Part. -"),
    ).toBeInTheDocument();
    rerender(
      <AutoSyncErrorArtifactList
        items={[
          {
            ...item,
            intestazione: null,
            subject_kind: null,
            subject_identifier: null,
          },
        ]}
      />,
    );
    expect(
      screen.getByText("Soggetto · identificativo mancante"),
    ).toBeInTheDocument();
  });

  test("reports unavailable, failed and cancelled request-detail loading", async () => {
    api.token = null;
    const unavailable = render(<AutoSyncErrorArtifactList items={[item]} />);
    fireEvent.click(screen.getByRole("button", { name: "Dettagli" }));
    expect(
      await screen.findByText("Dettagli richiesta non disponibili."),
    ).toBeInTheDocument();
    unavailable.unmount();

    api.token = "token";
    api.apiRequest.mockRejectedValueOnce("generic failure");
    const genericFailure = render(<AutoSyncErrorArtifactList items={[item]} />);
    fireEvent.click(screen.getByRole("button", { name: "Dettagli" }));
    expect(
      await screen.findByText("Errore caricamento dettagli richiesta"),
    ).toBeInTheDocument();
    genericFailure.unmount();

    api.apiRequest.mockRejectedValueOnce(new Error("specific failure"));
    const specificFailure = render(
      <AutoSyncErrorArtifactList items={[item]} />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Dettagli" }));
    expect(await screen.findByText("specific failure")).toBeInTheDocument();
    specificFailure.unmount();

    let resolveRequest: ((value: typeof request) => void) | null = null;
    api.apiRequest.mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          resolveRequest = resolve;
        }),
    );
    const cancelled = render(<AutoSyncErrorArtifactList items={[item]} />);
    fireEvent.click(screen.getByRole("button", { name: "Dettagli" }));
    await waitFor(() =>
      expect(api.apiRequest).toHaveBeenCalled(),
    );
    cancelled.unmount();
    resolveRequest?.(request);
    await Promise.resolve();

    let rejectRequest: ((reason?: unknown) => void) | null = null;
    api.apiRequest.mockImplementationOnce(
      () =>
        new Promise((_resolve, reject) => {
          rejectRequest = reject;
        }),
    );
    const cancelledFailure = render(
      <AutoSyncErrorArtifactList items={[item]} />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Dettagli" }));
    await waitFor(() => expect(api.apiRequest).toHaveBeenCalledTimes(4));
    cancelledFailure.unmount();
    rejectRequest?.(new Error("closed dialog"));
    await Promise.resolve();
  });

  test("reports artifact action errors and does nothing after session expiry", async () => {
    api.download
      .mockRejectedValueOnce("generic download")
      .mockRejectedValueOnce(new Error("download denied"));
    api.preview
      .mockRejectedValueOnce("generic preview")
      .mockRejectedValueOnce(new Error("preview denied"));
    render(<AutoSyncErrorArtifactList items={[item]} />);
    fireEvent.click(screen.getByRole("button", { name: "Dettagli" }));
    await screen.findByRole("button", { name: "Scarica artifact" });
    fireEvent.click(screen.getByRole("button", { name: "Scarica artifact" }));
    expect(
      await screen.findByText("Errore download artifact richiesta"),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Scarica artifact" }));
    expect(await screen.findByText("download denied")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Preview screenshot" }));
    expect(
      await screen.findByText("Errore caricamento preview screenshot"),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Preview screenshot" }));
    expect(await screen.findByText("preview denied")).toBeInTheDocument();
    api.token = null;
    fireEvent.click(screen.getByRole("button", { name: "Scarica artifact" }));
    fireEvent.click(screen.getByRole("button", { name: "Preview screenshot" }));
    expect(api.download).toHaveBeenCalledTimes(2);
    expect(api.preview).toHaveBeenCalledTimes(2);
  });
});
