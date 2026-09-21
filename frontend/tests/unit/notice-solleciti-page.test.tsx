import { act, cleanup, fireEvent, render, renderHook, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import SollecitiPage from "@/app/ruolo/tributi/solleciti/page";
import { useSolleciti } from "@/components/ruolo/solleciti/workspace";

const mocks = vi.hoisted(() => ({ session: vi.fn(), token: vi.fn(), list: vi.fn(), get: vi.fn(), confirm: vi.fn() }));
vi.mock("@/lib/use-session-bootstrap", () => ({ useSessionBootstrap: mocks.session }));
vi.mock("@/lib/auth", () => ({ getStoredAccessToken: mocks.token }));
vi.mock("@/lib/ruolo-api", () => ({
  listTributiReminderBatches: mocks.list,
  getTributiReminderBatch: mocks.get,
  confirmTributiReminderBatch: mocks.confirm,
}));
vi.mock("@/components/ruolo/solleciti/client", () => ({ confirmTributiReminderBatch: mocks.confirm }));
vi.mock("@/components/ruolo/module-page", () => ({ RuoloModulePage: ({ children }: { children: React.ReactNode }) => <main>{children}</main> }));

const batch = (status = "review_required") => ({
  id: "batch-1", title: "Import 2022/2023", status, template_path: null, filters_json: { years: [2022, 2023] },
  items_total: 1, items_generated: 0, items_failed: 0, generated_by: 1, generated_at: "2026-09-21T10:00:00Z", notes: null,
  created_at: "2026-09-21T10:00:00Z", updated_at: "2026-09-21T10:00:00Z", items: [{
    id: "item-1", batch_id: "batch-1", subject_id: null, codice_fiscale: "RSSMRA80A01H501Z", display_name: "Mario Rossi", comune_key: "URAS",
    years_json: [2022, 2023], avviso_ids_json: ["avviso-1"], due_amount: 100, paid_amount: 0, saldo_amount: 100, surcharge_amount: 0, interest_amount: 0,
    nas_folder_path: null, generated_document_path: null, status: "draft", error_detail: null,
    payload_json: { notice_identity_key: "a".repeat(64) }, created_at: "2026-09-21T10:00:00Z", updated_at: "2026-09-21T10:00:00Z", download_url: null,
  }],
});

beforeEach(() => {
  vi.resetAllMocks();
  mocks.session.mockReturnValue({ status: "ready", token: "token", currentUser: { role: "admin", enabled_modules: ["ruolo"] }, grantedSectionKeys: ["ruolo.tributi.view", "ruolo.tributi.manage_status"] });
  mocks.token.mockReturnValue("token");
  mocks.list.mockResolvedValue({ items: [batch()], total: 1, page: 1, page_size: 50 });
  mocks.get.mockResolvedValue(batch());
  mocks.confirm.mockResolvedValue({ id: "confirmation-1", generation_id: "batch-1", generation_kind: "batch", review_digest: "b".repeat(64), input_basis: {}, identity_keys: ["a".repeat(64)], notice_numbers: [], confirmed_by: 1, confirmed_at: "2026-09-21T10:01:00Z" });
});
afterEach(() => { cleanup(); vi.clearAllMocks(); });

it("loads a draft, displays identity and confirms the batch", async () => {
  render(<SollecitiPage />);
  expect(await screen.findByText("Bozza da verificare")).toBeVisible();
  fireEvent.click(screen.getByRole("button", { name: /Import 2022/ }));
  expect(await screen.findByText(/Identità: a/)).toBeVisible();
  fireEvent.click(screen.getByRole("button", { name: "Conferma lotto" }));
  await screen.findByText(/Lotto confermato/);
  expect(mocks.confirm).toHaveBeenCalledWith("token", "batch-1");
});

it("shows a conflict returned by the confirmation gate", async () => {
  mocks.confirm.mockRejectedValue(new Error("Revisione cambiata: rigenerare"));
  render(<SollecitiPage />);
  fireEvent.click(await screen.findByRole("button", { name: /Import 2022/ }));
  fireEvent.click(await screen.findByRole("button", { name: "Conferma lotto" }));
  await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("Revisione cambiata"));
});

it("does not expose confirmation for an already confirmed batch", async () => {
  mocks.list.mockResolvedValue({ items: [batch("confirmed")], total: 1, page: 1, page_size: 50 });
  mocks.get.mockResolvedValue(batch("confirmed"));
  render(<SollecitiPage />);
  await screen.findByText("Confermato");
  expect(screen.queryByRole("button", { name: "Conferma lotto" })).toBeNull();
});

it("does not expose confirmation to a read-only operator", async () => {
  mocks.session.mockReturnValue({ status: "ready", token: "token", currentUser: { role: "admin", enabled_modules: ["ruolo"] }, grantedSectionKeys: ["ruolo.tributi.view"] });
  render(<SollecitiPage />);
  fireEvent.click(await screen.findByRole("button", { name: /Import 2022/ }));
  await screen.findByText(/Identità: a/);
  expect(screen.getByText("Accesso in sola lettura.")).toBeVisible();
  expect(screen.queryByRole("button", { name: "Conferma lotto" })).toBeNull();
});

it("waits for authentication without requesting data", () => {
  mocks.session.mockReturnValue({ status: "checking" });
  render(<SollecitiPage />);
  expect(screen.getByRole("status")).toHaveTextContent("Verifica accesso");
  expect(mocks.list).not.toHaveBeenCalled();
});

it("refuses access without the view permission", () => {
  mocks.session.mockReturnValue({ status: "ready", token: "token", currentUser: { role: "admin", enabled_modules: ["ruolo"] }, grantedSectionKeys: [] });
  render(<SollecitiPage />);
  expect(screen.getByRole("alert")).toHaveTextContent("non autorizzato");
  expect(mocks.list).not.toHaveBeenCalled();
});

it.each([null, "broken"])("shows list errors %s", async (error) => {
  mocks.list.mockRejectedValue(error === null ? new Error("Lista non disponibile") : error);
  render(<SollecitiPage />);
  expect(await screen.findByRole("alert")).toHaveTextContent(error === null ? "Lista non disponibile" : "Errore caricamento lotti");
});

it.each([null, "broken"])("shows detail errors %s", async (error) => {
  mocks.get.mockRejectedValue(error === null ? new Error("Dettaglio non disponibile") : error);
  render(<SollecitiPage />);
  fireEvent.click(await screen.findByRole("button", { name: /Import 2022/ }));
  expect(await screen.findByRole("alert")).toHaveTextContent(error === null ? "Dettaglio non disponibile" : "Errore caricamento lotto");
});

it("handles confirmation failures without an Error object", async () => {
  mocks.confirm.mockRejectedValue("failure");
  render(<SollecitiPage />);
  fireEvent.click(await screen.findByRole("button", { name: /Import 2022/ }));
  fireEvent.click(await screen.findByRole("button", { name: "Conferma lotto" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Conferma non riuscita");
});

it("paginates and displays empty history", async () => {
  mocks.list.mockResolvedValueOnce({ items: [batch()], total: 51 }).mockResolvedValue({ items: [], total: 51 });
  render(<SollecitiPage />);
  await screen.findByRole("button", { name: /Import 2022/ });
  fireEvent.click(screen.getByRole("button", { name: "Successiva" }));
  await screen.findByText("Nessun lotto generato.");
  fireEvent.click(screen.getByRole("button", { name: "Precedente" }));
  await waitFor(() => expect(mocks.list).toHaveBeenLastCalledWith("token", 1, 50));
});

it("displays legacy status and missing optional data", async () => {
  const legacy = { ...batch("failed"), title: null, created_at: null, generated_at: null };
  legacy.items = [{ ...legacy.items[0], display_name: null, years_json: null, payload_json: null } as unknown as typeof legacy.items[number]];
  mocks.list.mockResolvedValue({ items: [legacy], total: 1 });
  mocks.get.mockResolvedValue(legacy);
  render(<SollecitiPage />);
  fireEvent.click(await screen.findByRole("button", { name: /Lotto batch-1/ }));
  await screen.findByRole("heading", { name: "batch-1" });
  expect(screen.queryByRole("button", { name: "Conferma lotto" })).toBeNull();
});

it("loads the confirmed detail", async () => {
  mocks.get.mockResolvedValue(batch("confirmed"));
  render(<SollecitiPage />);
  fireEvent.click(await screen.findByRole("button", { name: /Import 2022/ }));
  await screen.findByText(/export definitivo/);
});

it.each([{ token: null }, { currentUser: null }])("waits for incomplete session %j", (values) => {
  mocks.session.mockReturnValue({ status: "ready", token: "token", currentUser: {}, ...values });
  render(<SollecitiPage />);
  expect(screen.getByRole("status")).toHaveTextContent("Verifica accesso");
});

it.each(["admin", "super_admin"])("checks module access for %s", async (role) => {
  mocks.session.mockReturnValue({ status: "ready", token: "token", currentUser: { role, enabled_modules: [] }, grantedSectionKeys: ["ruolo.tributi.view"] });
  render(<SollecitiPage />);
  if (role === "admin") expect(screen.getByRole("alert")).toBeVisible();
  else await screen.findByRole("button", { name: /Import 2022/ });
});

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}

it.each([false, true])("ignores obsolete detail responses (failure=%s)", async (failure) => {
  const pending = deferred<ReturnType<typeof batch>>();
  mocks.get.mockReturnValueOnce(pending.promise).mockResolvedValue(batch("confirmed"));
  const { result } = renderHook(() => useSolleciti("token", true));
  let first!: Promise<void>;
  act(() => { first = result.current.selectBatch("old"); });
  await act(() => result.current.selectBatch("new"));
  await act(async () => { if (failure) pending.reject(new Error("obsolete")); else pending.resolve(batch()); await first; });
  expect(result.current.selected?.status).toBe("confirmed");
  expect(result.current.error).toBeNull();
});

it.each([false, true])("ignores list completion after unmount (failure=%s)", async (failure) => {
  const pending = deferred<unknown>();
  mocks.list.mockReturnValue(pending.promise);
  const { unmount } = renderHook(() => useSolleciti("token", true));
  unmount();
  await act(async () => { if (failure) pending.reject("cancelled"); else pending.resolve({ items: [], total: 0 }); });
});

it("guards missing selection, read-only and duplicate confirmation", async () => {
  const pending = deferred<unknown>();
  mocks.confirm.mockReturnValue(pending.promise);
  const { result, rerender } = renderHook(({ edit }) => useSolleciti("token", edit), { initialProps: { edit: true } });
  await act(() => result.current.confirmSelected());
  await act(() => result.current.selectBatch("batch-1"));
  rerender({ edit: false });
  await act(() => result.current.confirmSelected());
  expect(mocks.confirm).not.toHaveBeenCalled();
  rerender({ edit: true });
  let first!: Promise<void>;
  act(() => { first = result.current.confirmSelected(); });
  await act(() => result.current.confirmSelected());
  expect(mocks.confirm).toHaveBeenCalledTimes(1);
  await act(async () => { pending.resolve({ review_digest: "digest" }); await first; });
});
