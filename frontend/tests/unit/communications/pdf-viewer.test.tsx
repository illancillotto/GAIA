import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { CommunicationPdfViewer } from "@/components/communications/pdf-viewer";
import { part } from "./fixtures";
const api = vi.hoisted(() => ({ communications: vi.fn(), loadSnapshot: vi.fn(), render: vi.fn() }));
vi.mock("@/lib/communications-api", () => api);
vi.mock("@/components/communications/pdf-renderer", () => ({ renderSnapshot: api.render }));
const props = () => ({ token: "token", messageId: "message", version: 1, part, onRendered: vi.fn(), canReview: true, pixelBudget: 64e6 });
beforeEach(() => {
  vi.resetAllMocks();
  api.loadSnapshot.mockResolvedValue({ content: new ArrayBuffer(4), reviewId: "proof" });
  api.communications.mockResolvedValue({});
  api.render.mockImplementation(async (_data, _part, host, _options, session) => {
    session.task = { cancel: vi.fn() }; session.document = { destroy: vi.fn() };
    host.replaceChildren(...[1, 2, 3].map((page) => { const canvas = document.createElement("canvas"); canvas.dataset.page = String(page); canvas.scrollIntoView = vi.fn(); return canvas; }));
  });
  URL.createObjectURL = vi.fn(() => "blob:synthetic"); URL.revokeObjectURL = vi.fn();
});
afterEach(cleanup);
it("renders all pages before acknowledging review and provides navigation, zoom, authenticated blob and fullscreen", async () => {
  const settings = props();
  const { container, unmount } = render(<CommunicationPdfViewer {...settings} />);
  expect(await screen.findByRole("link", { name: "Apri PDF in nuova scheda" })).toHaveAttribute("href", "blob:synthetic");
  expect(settings.onRendered).toHaveBeenLastCalledWith(true);
  expect(api.communications.mock.lastCall?.[2]).toMatchObject({ pages: 3, sha256: part.sha256, expected_version: 1 });
  fireEvent.click(screen.getByText("Pagina successiva"));
  expect(container.querySelector('[data-page="2"]')?.scrollIntoView).toHaveBeenCalled();
  fireEvent.click(screen.getByText("Pagina precedente"));
  fireEvent.click(screen.getByLabelText("Aumenta zoom"));
  await waitFor(() => expect(api.render.mock.lastCall?.[3].zoom).toBe(1.25));
  fireEvent.click(screen.getByLabelText("Riduci zoom"));
  await waitFor(() => expect(api.render.mock.lastCall?.[3].zoom).toBe(1));
  fireEvent.click(screen.getByText("Adatta alla larghezza"));
  const canvases = container.querySelectorAll("canvas");
  vi.spyOn(canvases[0], "getBoundingClientRect").mockReturnValue({ bottom: -1 } as DOMRect);
  vi.spyOn(canvases[1], "getBoundingClientRect").mockReturnValue({ bottom: 40 } as DOMRect);
  fireEvent.scroll(canvases[0].parentElement!);
  expect(screen.getByText("2 / 3")).toBeInTheDocument();
  fireEvent.click(screen.getByText("Schermo intero"));
  expect(await screen.findByRole("alert")).toHaveTextContent("non disponibile");
  const fullscreen = vi.fn().mockResolvedValue(undefined);
  container.querySelector("section")!.requestFullscreen = fullscreen;
  fireEvent.click(screen.getByText("Schermo intero"));
  await waitFor(() => expect(fullscreen).toHaveBeenCalled());
  unmount(); expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:synthetic");
});
it("read-only preview never attests an operator review", async () => {
  render(<CommunicationPdfViewer {...props()} canReview={false} />);
  await screen.findByRole("link");
  expect(api.communications).not.toHaveBeenCalled();
});
it.each([new Error("PDF non valido"), "failure"])("fails closed on renderer failure %s", async (error) => {
  api.render.mockRejectedValue(error);
  const settings = props();
  render(<CommunicationPdfViewer {...settings} />);
  expect(await screen.findByRole("alert")).toHaveTextContent(error instanceof Error ? error.message : "Rendering PDF fallito");
  expect(settings.onRendered).toHaveBeenLastCalledWith(false);
  expect(screen.queryByRole("link")).not.toBeInTheDocument();
});
it("rejects unsupported MIME and cleans up while download or rendering is pending", async () => {
  const { unmount } = render(<CommunicationPdfViewer {...props()} part={{ ...part, mime_type: "image/png" }} />);
  expect(await screen.findByRole("alert")).toHaveTextContent("non visualizzabile");
  unmount();
  let resolve!: (value: unknown) => void;
  api.loadSnapshot.mockReturnValue(new Promise((done) => { resolve = done; }));
  const pending = render(<CommunicationPdfViewer {...props()} />);
  pending.unmount();
  await act(async () => { resolve({ content: new ArrayBuffer(4), reviewId: "proof" }); });
  expect(api.render).not.toHaveBeenCalled();
  api.loadSnapshot.mockResolvedValue({ content: new ArrayBuffer(4), reviewId: "proof" });
  api.render.mockImplementation(() => new Promise((done) => { resolve = done; }));
  const painting = render(<CommunicationPdfViewer {...props()} />);
  await waitFor(() => expect(api.render).toHaveBeenCalled());
  painting.unmount();
  await act(async () => resolve(undefined));
  expect(api.communications).not.toHaveBeenCalled();
});
it("ignores a download failure after unmount and scroll with no visible page", async () => {
  let reject!: (reason: unknown) => void;
  api.loadSnapshot.mockReturnValue(new Promise((_done, fail) => { reject = fail; }));
  const pending = render(<CommunicationPdfViewer {...props()} />);
  fireEvent.scroll(pending.container.querySelector('.overflow-auto')!);
  pending.unmount();
  await act(async () => reject(new Error("aborted")));
});
it("does not enable send if rendering acknowledgement completes after unmount", async () => {
  let done!: (value: unknown) => void;
  api.communications.mockReturnValue(new Promise((resolve) => { done = resolve; }));
  const settings = props();
  const view = render(<CommunicationPdfViewer {...settings} />);
  await waitFor(() => expect(api.communications).toHaveBeenCalled());
  view.unmount();
  await act(async () => done({}));
  expect(settings.onRendered).not.toHaveBeenCalledWith(true);
});

it("renders supplied preview bytes without downloading or acknowledging a draft", async () => {
  const data = new ArrayBuffer(4);
  const loadContent = vi.fn(async () => ({ content: data.slice(0), reviewId: "" }));
  render(<CommunicationPdfViewer {...props()} canReview={false} loadContent={loadContent} />);
  await screen.findByRole("link");
  expect(api.loadSnapshot).not.toHaveBeenCalled(); expect(api.communications).not.toHaveBeenCalled();
  fireEvent.click(screen.getByLabelText("Aumenta zoom"));
  await waitFor(() => expect(loadContent).toHaveBeenCalledTimes(2));
  expect(api.render.mock.calls[0][0]).not.toBe(api.render.mock.calls[1][0]);
});
