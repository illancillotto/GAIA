import { act, cleanup, fireEvent, render, renderHook, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { NoticeExport, NoticePreview, useDocumentBlob } from "@/components/ruolo/solleciti/document-access";

const mocks = vi.hoisted(() => ({ blob: vi.fn(), create: vi.fn(), revoke: vi.fn() }));
vi.mock("@/lib/api", () => ({ requestBlob: mocks.blob }));
beforeEach(() => {
  vi.resetAllMocks();
  mocks.blob.mockResolvedValue(new Blob(["pdf"], { type: "application/pdf" }));
  mocks.create.mockReturnValue("blob:private");
  URL.createObjectURL = mocks.create;
  URL.revokeObjectURL = mocks.revoke;
});
afterEach(cleanup);

it.each(["failed", "generated"])("does not offer a private preview for %s items", (status) => {
  render(<NoticePreview token="token" batchId="batch" itemId="item" status={status} />);
  expect(screen.queryByRole("button")).toBeNull();
  expect(mocks.blob).not.toHaveBeenCalled();
});

it("loads a marked preview on demand and revokes its URL on close", async () => {
  render(<NoticePreview token="token" batchId="batch" itemId="item" status="draft" />);
  expect(mocks.blob).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Esamina documento" }));
  fireEvent.click(screen.getByRole("button", { name: "Carica anteprima PDF" }));
  expect(screen.getByRole("button", { name: /Preparazione anteprima/ })).toBeDisabled();
  expect(await screen.findByTitle("Anteprima documento - BOZZA")).toHaveAttribute("src", "blob:private");
  expect(mocks.blob).toHaveBeenCalledWith("/ruolo/tributi/solleciti/batches/batch/items/item/preview", expect.objectContaining({ method: "GET", cache: "no-store", headers: { Authorization: "Bearer token" } }));
  expect(screen.getByRole("link", { name: /nuova scheda/ })).toHaveAttribute("href", "blob:private");
  fireEvent.click(screen.getByRole("button", { name: "Chiudi anteprima" }));
  expect(mocks.revoke).toHaveBeenCalledWith("blob:private");
});

it.each([new Error("Convertitore indisponibile"), "failure"])("shows preview failures and permits retry: %s", async (error) => {
  mocks.blob.mockRejectedValueOnce(error);
  render(<NoticePreview token="token" batchId="batch" itemId="item" status="draft" />);
  fireEvent.click(screen.getByRole("button", { name: "Esamina documento" }));
  fireEvent.click(screen.getByRole("button", { name: "Carica anteprima PDF" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(error instanceof Error ? error.message : "Documento non disponibile");
  fireEvent.click(screen.getByRole("button", { name: "Carica anteprima PDF" }));
  await screen.findByTitle("Anteprima documento - BOZZA");
});

it("requires an explicit audited preparation before exposing the ZIP download", async () => {
  render(<NoticeExport token="token" batchId="batch" canEdit />);
  expect(screen.queryByRole("link")).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Prepara export definitivo" }));
  expect(screen.getByRole("button", { name: "Verifica e preparazione..." })).toBeDisabled();
  expect(await screen.findByRole("link", { name: "Scarica ZIP definitivo" })).toHaveAttribute("download", "solleciti-batch-v1.zip");
  expect(mocks.blob).toHaveBeenCalledWith("/ruolo/tributi/solleciti/batches/batch/export", expect.objectContaining({ method: "POST" }));
  fireEvent.click(screen.getByRole("button", { name: "Prepara export definitivo" }));
  await waitFor(() => expect(mocks.create).toHaveBeenCalledTimes(2));
  expect(mocks.revoke).toHaveBeenCalledWith("blob:private");
});

it("shows stale confirmation errors without offering a download", async () => {
  mocks.blob.mockRejectedValue(new Error("Dati modificati: rigenerare la bozza"));
  render(<NoticeExport token="token" batchId="batch" canEdit />);
  fireEvent.click(screen.getByRole("button", { name: "Prepara export definitivo" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("rigenerare");
  expect(screen.queryByRole("link")).toBeNull();
});

it("does not expose export commands to read-only users", () => {
  render(<NoticeExport token="token" batchId="batch" canEdit={false} />);
  expect(screen.queryByRole("button")).toBeNull();
  expect(mocks.blob).not.toHaveBeenCalled();
});

it.each([false, true])("ignores document completion after unmount, failure=%s", async (failure) => {
  let finish!: (value: Blob) => void;
  let fail!: (value: Error) => void;
  mocks.blob.mockReturnValue(new Promise<Blob>((resolve, reject) => { finish = resolve; fail = reject; }));
  const { result, unmount } = renderHook(() => useDocumentBlob("token", "/preview", "GET"));
  act(() => result.current.request());
  unmount();
  await act(async () => { if (failure) fail(new Error("obsolete")); else finish(new Blob()); });
  expect(mocks.create).not.toHaveBeenCalled();
});
