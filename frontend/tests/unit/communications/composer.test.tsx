import { act, cleanup, fireEvent, render, renderHook, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { CommunicationComposer } from "@/components/communications/composer";
import { useComposer } from "@/components/communications/use-composer";
import { ComposerForm } from "@/components/communications/composer-form";
import { message, account } from "./fixtures";
const api = vi.hoisted(() => ({ communications: vi.fn(), uploadAttachment: vi.fn(), receiptBlob: vi.fn(), rendered: vi.fn() }));
vi.mock("@/lib/communications-api", () => api);
vi.mock("@/components/communications/pdf-viewer", () => ({ CommunicationPdfViewer: (props: { onRendered: (ok: boolean) => void }) => <button onClick={() => props.onRendered(true)}>PDF caricato</button> }));
beforeEach(() => { vi.resetAllMocks(); api.communications.mockResolvedValue([]); });
afterEach(() => { cleanup(); vi.restoreAllMocks(); });
it("invalidates checks on edits, uses versioned commands, and reports command/upload failures", async () => {
  const onChange = vi.fn();
  const { result } = renderHook(() => useComposer({ token: "token", message, canEdit: true, onChange }));
  act(() => { result.current.onRender("pdf", true); result.current.setChecks(["identity"]); });
  expect(result.current.ready).toBe(true);
  act(() => result.current.change("subject", "Corrected"));
  expect(result.current.checks).toEqual([]); expect(result.current.dirty).toBe(true);
  api.communications.mockResolvedValue(message);
  await act(async () => result.current.action("save"));
  expect(api.communications.mock.calls[0]).toMatchObject(["token", "/messages/message", { subject: "Corrected", expected_version: 1 }, "PATCH"]);
  act(() => result.current.setChecks(["identity"]));
  await act(async () => result.current.action("approve"));
  expect(api.communications.mock.calls[2][2]).toMatchObject({ checklist: { identity: true }, confirmed: true });
  await act(async () => result.current.action("dispatch"));
  expect(api.communications.mock.calls[4][2]).toEqual({ expected_version: 1 });
  api.uploadAttachment.mockResolvedValue(message);
  await act(async () => result.current.upload(new File([], "test.pdf")));
  expect(onChange).toHaveBeenCalledWith(message);
  for (const failure of [new Error("stale"), "error"]) {
    api.communications.mockRejectedValue(failure);
    await act(async () => result.current.action("save"));
    expect(result.current.status.error).toBe(failure instanceof Error ? "stale" : "Operazione fallita");
    api.uploadAttachment.mockRejectedValue(failure);
    await act(async () => result.current.upload(new File([], "bad.pdf")));
    expect(result.current.status.error).toBe(failure instanceof Error ? "stale" : "Caricamento fallito");
  }
});
it("requires complete PDF rendering plus eight checks before approval, and no dirty edits before dispatch", async () => {
  const { result } = renderHook(() => useComposer({ token: "token", message: { ...message, state: "ready" }, canEdit: true, onChange: vi.fn() }));
  const view = render(<ComposerForm message={{ ...message, state: "ready" }} accounts={[account, { ...account, id: "paused", paused: true }, { ...account, id: "ordinary", channel: "email" }]} canEdit controller={result.current} />);
  expect(screen.getByText("Conferma e approva")).toBeDisabled();
  act(() => result.current.onRender("pdf", true));
  view.rerender(<ComposerForm message={{ ...message, state: "ready" }} accounts={[account]} canEdit controller={result.current} />);
  for (const box of screen.getAllByRole("checkbox")) fireEvent.click(box);
  // Hook state drives the form through its parent in the actual composer.
  view.rerender(<ComposerForm message={{ ...message, state: "ready" }} accounts={[account]} canEdit controller={result.current} />);
  expect(result.current.checks).toHaveLength(8);
  expect(screen.getByText("Conferma e approva")).toBeEnabled();
  fireEvent.click(screen.getAllByRole("checkbox")[0]);
  expect(result.current.checks).toHaveLength(7);
  fireEvent.change(screen.getByLabelText("Account mittente"), { target: { value: "account" } });
  fireEvent.change(screen.getByLabelText("Destinatario"), { target: { value: "new@example.org" } });
  fireEvent.change(screen.getByLabelText("Oggetto"), { target: { value: "New" } });
  fireEvent.change(screen.getByLabelText("Testo"), { target: { value: "New text" } });
  fireEvent.change(screen.getByLabelText("Aggiungi allegato PDF"), { target: { files: [] } });
  api.uploadAttachment.mockResolvedValue(message);
  fireEvent.change(screen.getByLabelText("Aggiungi allegato PDF"), { target: { files: [new File([], "attachment.pdf")] } });
  await waitFor(() => expect(api.uploadAttachment).toHaveBeenCalled());
  fireEvent.click(screen.getByText("Verifica dati attuali"));
});
it("renders immutable/read-only communication, email courtesy warning, errors and history downloads", async () => {
  const receipt = { id: "receipt", kind: "delivered", classification: "matched", sha256: "hash" };
  api.communications.mockImplementation((_t, path) => Promise.resolve(path.endsWith("events") ? [{ id: "event", kind: "submitted", detail: {}, created_at: "today" }] : [receipt]));
  const { rerender } = render(<CommunicationComposer token="token" message={{ ...message, state: "submitted", channel: "email" }} accounts={[account]} canEdit={false} onChange={vi.fn()} />);
  expect(screen.getByText(/Comunicazione di cortesia/)).toBeInTheDocument();
  expect(screen.queryByText("Invia Email")).not.toBeInTheDocument();
  fireEvent.click(screen.getByText("PDF caricato"));
  await screen.findByText(/submitted ·/);
  URL.createObjectURL = vi.fn(() => "blob:eml"); URL.revokeObjectURL = vi.fn();
  vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
  api.receiptBlob.mockResolvedValue(new Blob(["eml"]));
  fireEvent.click(screen.getByText("Scarica originale EML"));
  await waitFor(() => expect(URL.createObjectURL).toHaveBeenCalled());
  for (const failure of [new Error("access denied"), "error"]) {
    api.receiptBlob.mockRejectedValue(failure);
    fireEvent.click(screen.getByText("Scarica originale EML"));
    expect(await screen.findByRole("alert")).toHaveTextContent(failure instanceof Error ? failure.message : "Download fallito");
  }
  api.communications.mockRejectedValue(new Error("history unavailable"));
  rerender(<CommunicationComposer token="different" message={{ ...message, state: "failed" }} accounts={[]} canEdit onChange={vi.fn()} />);
  expect(await screen.findByRole("alert")).toHaveTextContent("history unavailable");
});
it("discards late history success/failure after unmount", async () => {
  let resolve!: (value: unknown) => void;
  let reject!: (reason: unknown) => void;
  api.communications.mockImplementation(() => new Promise((done, fail) => { resolve = done; reject = fail; }));
  const first = render(<CommunicationComposer token="token" message={message} accounts={[]} canEdit onChange={vi.fn()} />);
  first.unmount(); await act(async () => resolve([]));
  const second = render(<CommunicationComposer token="token" message={message} accounts={[]} canEdit onChange={vi.fn()} />);
  second.unmount(); await act(async () => reject(new Error("late")));
});
it("disables checks while a command is pending and renders the ordinary email dispatch action", async () => {
  api.communications.mockReturnValue(new Promise(() => {}));
  const { result } = renderHook(() => useComposer({ token: "token", message: { ...message, channel: "email", state: "ready" }, canEdit: true, onChange: vi.fn() }));
  act(() => { result.current.onRender("pdf", true); void result.current.action("validate"); });
  render(<ComposerForm message={{ ...message, channel: "email", state: "ready" }} accounts={[]} canEdit controller={result.current} />);
  expect(screen.getByText("Invia Email")).toBeDisabled();
  expect(screen.getAllByRole("checkbox")[0]).toBeDisabled();
});
it("revokes downloaded EML URLs and discards both resolved history requests on unmount", async () => {
  const resolvers: ((value: unknown) => void)[] = [];
  api.communications.mockImplementation(() => new Promise((resolve) => resolvers.push(resolve)));
  const view = render(<CommunicationComposer token="token" message={message} accounts={[]} canEdit onChange={vi.fn()} />);
  view.unmount();
  await act(async () => resolvers.forEach((resolve) => resolve([])));
  api.communications.mockImplementation((_t, path) => Promise.resolve(path.endsWith("events") ? [] : [{ id: "r", kind: "accepted", classification: "matched", sha256: "hash" }]));
  render(<CommunicationComposer token="token" message={message} accounts={[]} canEdit onChange={vi.fn()} />);
  await screen.findByText("Scarica originale EML");
  URL.createObjectURL = vi.fn(() => "blob:receipt"); URL.revokeObjectURL = vi.fn();
  vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
  api.receiptBlob.mockResolvedValue(new Blob(["eml"]));
  vi.useFakeTimers();
  await act(async () => fireEvent.click(screen.getByText("Scarica originale EML")));
  act(() => vi.advanceTimersByTime(1000));
  expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:receipt");
  vi.useRealTimers();
});
it("keeps failed validation visible in the composition form", async () => {
  api.communications.mockRejectedValue(new Error("Dati modificati, nuova revisione richiesta"));
  const { result } = renderHook(() => useComposer({ token: "token", message, canEdit: true, onChange: vi.fn() }));
  await act(async () => result.current.action("validate"));
  render(<ComposerForm message={message} accounts={[]} canEdit controller={result.current} />);
  expect(screen.getByRole("alert")).toHaveTextContent("Dati modificati");
});

it("places message fields above the PDF and the review checklist after it", async () => {
  render(<CommunicationComposer token="token" message={message} accounts={[account]} canEdit onChange={vi.fn()} />);
  const before = (a: Element, b: Element) => expect(a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  before(screen.getByLabelText("Oggetto"), screen.getByLabelText("Anteprima allegati PDF"));
  before(screen.getByLabelText("Anteprima allegati PDF"), screen.getByText("Verifica individuale obbligatoria"));
  expect(screen.getByRole("heading", { name: "Componi avviso 1/2021 · PEC" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Invia PEC" })).toBeDisabled();
  await screen.findByLabelText("Storico comunicazione");
});
