import { act, cleanup, fireEvent, render, renderHook, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import SollecitiPage from "@/app/ruolo/tributi/solleciti/page";
import PostePage from "@/app/ruolo/tributi/solleciti/poste/page";
import { useDocumentBlob } from "@/components/ruolo/solleciti/document-access";
import { usePosteSelection } from "@/components/ruolo/solleciti/poste-selection";
import { useSolleciti } from "@/components/ruolo/solleciti/workspace";

const mocks = vi.hoisted(() => ({ session: vi.fn(), token: vi.fn(), list: vi.fn(), get: vi.fn(), confirm: vi.fn(), blob: vi.fn() }));
const poste = vi.hoisted(() => ({
  listPosteLots: vi.fn(), getPosteLot: vi.fn(), createPosteLot: vi.fn(), listPosteCandidates: vi.fn(), requestPosteJob: vi.fn(),
  updatePosteRecipient: vi.fn(), acceptPosteManualAddress: vi.fn(), cancelPosteItem: vi.fn(), getPosteItemDocument: vi.fn(),
}));
vi.mock("@/lib/ruolo-poste-dispatch-api", () => poste);
const regeneration = vi.hoisted(() => ({ listRegenerationTargets: vi.fn(), regenerateReminderItem: vi.fn() }));
vi.mock("@/lib/ruolo-regeneration-api", () => regeneration);
vi.mock("@/lib/api", async (original) => ({ ...(await original<typeof import("@/lib/api")>()), requestBlob: mocks.blob }));
const pathname = vi.hoisted(() => vi.fn());
vi.mock("next/navigation", () => ({ usePathname: pathname }));
vi.mock("@/lib/use-session-bootstrap", () => ({ useSessionBootstrap: mocks.session }));
vi.mock("@/lib/auth", () => ({ getStoredAccessToken: mocks.token }));
vi.mock("@/lib/ruolo-api", () => ({
  listTributiReminderBatches: mocks.list,
  getTributiReminderBatch: mocks.get,
  confirmTributiReminderBatch: mocks.confirm,
}));
vi.mock("@/components/ruolo/solleciti/client", () => ({ confirmTributiReminderBatch: mocks.confirm }));
vi.mock("@/components/ruolo/module-page", () => ({ RuoloModulePage: ({ children, topbarActions }: { children: React.ReactNode; topbarActions?: React.ReactNode }) => <main>{topbarActions}{children}</main> }));

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
  poste.listPosteLots.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 50 });
  poste.listPosteCandidates.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 50 });
  mocks.confirm.mockResolvedValue({ id: "confirmation-1", generation_id: "batch-1", generation_kind: "batch", review_digest: "b".repeat(64), input_basis: {}, identity_keys: ["a".repeat(64)], notice_numbers: [], confirmed_by: 1, confirmed_at: "2026-09-21T10:01:00Z" });
});
afterEach(() => { cleanup(); vi.clearAllMocks(); });

it("loads a draft, displays identity and confirms the batch", async () => {
  render(<SollecitiPage />);
  expect(await screen.findByText("Bozza da verificare")).toBeVisible();
  expect(screen.getByRole("tab", { name: "Solleciti generati" })).toHaveAttribute("aria-selected", "true");
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
  await screen.findByRole("region", { name: "Export definitivo" });
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


function generatedBatch(path: string | null = "/nas/solleciti/rossi.pdf", id = "batch-2", itemId = "item-2", name = "Anna Bianchi") {
  const base = batch();
  return { ...base, id, title: `Generati ${id}`, status: "generated", items: [{
    ...base.items[0], id: itemId, batch_id: id, display_name: name, status: "generated", generated_document_path: path,
    download_url: path ? `/ruolo/tributi/solleciti/items/${itemId}/download` : null,
  }] };
}

const posteLot = { id: "lot-1", title: "Solleciti 2021", status: "open", created_by: 1, created_at: "2026-10-29T10:00:00Z", counts: { address_pending: 1 }, priced_total: 0, postal_options: {}, portal_snapshot: null, draft_expires_at: null, active_job: null, items: [], events: [] };

async function openGenerated(detail = generatedBatch()) {
  mocks.list.mockResolvedValue({ items: [detail], total: 1 });
  mocks.get.mockResolvedValue(detail);
  render(<SollecitiPage />);
  fireEvent.click(await screen.findByRole("button", { name: new RegExp(detail.title) }));
  await screen.findByText(detail.items[0].display_name);
}

it("previews the generated PDF that Poste would upload", async () => {
  vi.stubGlobal("URL", Object.assign(URL, { createObjectURL: vi.fn(() => "blob:avviso"), revokeObjectURL: vi.fn() }));
  mocks.blob.mockResolvedValue(new Blob(["%PDF"]));
  await openGenerated();
  fireEvent.click(screen.getByRole("button", { name: "Anteprima avviso" }));
  expect(await screen.findByTitle("Anteprima avviso generato")).toHaveAttribute("src", "blob:avviso");
  expect(mocks.blob).toHaveBeenCalledWith("/ruolo/tributi/solleciti/items/item-2/download", expect.objectContaining({ method: "GET" }));
  fireEvent.click(screen.getByRole("button", { name: "Chiudi anteprima" }));
  fireEvent.click(screen.getByRole("button", { name: "Anteprima avviso" }));
  expect(await screen.findByRole("link", { name: "Apri avviso in una nuova scheda" })).toHaveAttribute("href", "blob:avviso");
  expect(mocks.blob).toHaveBeenCalledTimes(1);
});

it("reports a generated PDF that cannot be loaded", async () => {
  mocks.blob.mockRejectedValue(new Error("Documento sollecito non trovato"));
  await openGenerated();
  fireEvent.click(screen.getByRole("button", { name: "Anteprima avviso" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Documento sollecito non trovato");
});

it("collects reminders from several batches and loads them on Poste", async () => {
  const first = generatedBatch();
  const second = generatedBatch("/nas/solleciti/verdi.PDF", "batch-3", "item-3", "Luca Verdi");
  mocks.list.mockResolvedValue({ items: [first, second], total: 2 });
  mocks.get.mockImplementation(async (_token: string, id: string) => id === "batch-2" ? first : second);
  poste.createPosteLot.mockResolvedValue(posteLot);
  poste.getPosteLot.mockResolvedValue(posteLot);
  render(<SollecitiPage />);
  fireEvent.click(await screen.findByRole("button", { name: /Generati batch-2/ }));
  fireEvent.click(await screen.findByRole("checkbox", { name: "Seleziona per Posta Online" }));
  fireEvent.click(screen.getByRole("button", { name: /Generati batch-3/ }));
  fireEvent.click(await screen.findByRole("checkbox", { name: "Seleziona per Posta Online" }));
  const bar = screen.getByRole("region", { name: "Selezione per Posta Online" });
  expect(bar).toHaveTextContent("2 di massimo 50 solleciti selezionati");
  expect(bar).toHaveTextContent("Anna Bianchi, Luca Verdi");
  expect(screen.getByRole("button", { name: "Carica su Poste (2)" })).toBeDisabled();
  fireEvent.change(screen.getByRole("textbox", { name: "Titolo lotto Poste" }), { target: { value: "Solleciti 2021" } });
  fireEvent.click(screen.getByRole("button", { name: "Carica su Poste (2)" }));
  expect(await screen.findByRole("region", { name: "Dettaglio lotto Poste" })).toBeVisible();
  expect(poste.createPosteLot).toHaveBeenCalledWith("token", "Solleciti 2021", ["item-2", "item-3"]);
  expect(poste.getPosteLot).toHaveBeenCalledWith("token", "lot-1");
  expect(screen.getByRole("tab", { name: "Posta Online" })).toHaveAttribute("aria-selected", "true");
  fireEvent.click(screen.getByRole("tab", { name: "Solleciti generati" }));
  expect(await screen.findByText("0 di massimo 50 solleciti selezionati")).toBeVisible();
});

it.each([[new Error("Sollecito già in un lotto Poste attivo"), "già in un lotto"], ["broken", "Lotto Poste non creato"]])("keeps the selection when Poste refuses the lot (%s)", async (failure, message) => {
  poste.createPosteLot.mockRejectedValue(failure);
  await openGenerated();
  fireEvent.click(screen.getByRole("checkbox", { name: "Seleziona per Posta Online" }));
  fireEvent.change(screen.getByRole("textbox", { name: "Titolo lotto Poste" }), { target: { value: "Prova" } });
  fireEvent.click(screen.getByRole("button", { name: "Carica su Poste (1)" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(message);
  expect(screen.getByRole("tab", { name: "Solleciti generati" })).toHaveAttribute("aria-selected", "true");
  expect(screen.getByRole("checkbox", { name: "Seleziona per Posta Online" })).toBeChecked();
  fireEvent.click(screen.getByRole("button", { name: "Svuota" }));
  expect(screen.getByRole("checkbox", { name: "Seleziona per Posta Online" })).not.toBeChecked();
});

it("unselects a reminder and caps the selection at one Poste lot", () => {
  const { result } = renderHook(() => usePosteSelection());
  const items = Array.from({ length: 51 }, (_, index) => ({ ...generatedBatch().items[0], id: `item-${index}`, display_name: null }));
  act(() => { items.forEach((entry) => result.current.toggle(entry)); });
  expect(result.current.selected).toHaveLength(50);
  expect(result.current.selected[0].label).toBe("RSSMRA80A01H501Z");
  act(() => result.current.toggle(items[0]));
  expect(result.current.isSelected("item-0")).toBe(false);
  expect(result.current.selected).toHaveLength(49);
});

it("offers Poste only for generated PDFs and only to editors", async () => {
  await openGenerated(generatedBatch("/nas/solleciti/rossi.docx"));
  expect(screen.queryByRole("checkbox", { name: "Seleziona per Posta Online" })).toBeNull();
  expect(screen.queryByRole("button", { name: "Anteprima avviso" })).toBeNull();
  cleanup();
  mocks.session.mockReturnValue({ status: "ready", token: "token", currentUser: { role: "admin", enabled_modules: ["ruolo"] }, grantedSectionKeys: ["ruolo.tributi.view"] });
  await openGenerated();
  expect(screen.queryByRole("checkbox", { name: "Seleziona per Posta Online" })).toBeNull();
  expect(screen.queryByRole("region", { name: "Selezione per Posta Online" })).toBeNull();
  expect(screen.getByRole("button", { name: "Anteprima avviso" })).toBeVisible();
});

it("opens the former Posta Online address on its tab", async () => {
  pathname.mockReturnValue("/ruolo/tributi/solleciti/poste");
  render(<PostePage />);
  expect(screen.getByRole("tab", { name: "Posta Online" })).toHaveAttribute("aria-selected", "true");
  expect(await screen.findByText("Nessun lotto Poste.")).toBeVisible();
  fireEvent.click(screen.getByRole("tab", { name: "Solleciti generati" }));
  expect(await screen.findByRole("button", { name: /Import 2022/ })).toBeVisible();
});

it("loads the marked draft copy and the generated PDF, showing progress while they arrive", async () => {
  vi.stubGlobal("URL", Object.assign(URL, { createObjectURL: vi.fn(() => "blob:bozza"), revokeObjectURL: vi.fn() }));
  const pending = deferred<Blob>();
  mocks.blob.mockReturnValueOnce(pending.promise);
  render(<SollecitiPage />);
  fireEvent.click(await screen.findByRole("button", { name: /Import 2022/ }));
  fireEvent.click(await screen.findByRole("button", { name: "Esamina documento" }));
  fireEvent.click(screen.getByRole("button", { name: "Carica anteprima PDF" }));
  expect(screen.getByRole("button", { name: "Preparazione anteprima..." })).toBeDisabled();
  await act(async () => pending.resolve(new Blob(["%PDF"])));
  expect(screen.getByTitle("Anteprima documento - BOZZA")).toHaveAttribute("src", "blob:bozza");
  expect(mocks.blob).toHaveBeenCalledWith("/ruolo/tributi/solleciti/batches/batch-1/items/item-1/preview", expect.objectContaining({ method: "GET" }));
  cleanup();
  mocks.blob.mockReturnValueOnce(new Promise(() => undefined));
  await openGenerated();
  fireEvent.click(screen.getByRole("button", { name: "Anteprima avviso" }));
  expect(screen.getByRole("status")).toHaveTextContent("Caricamento avviso...");
});

it("does not offer Poste for a generated reminder without a document", async () => {
  await openGenerated(generatedBatch(null));
  expect(screen.queryByRole("checkbox", { name: "Seleziona per Posta Online" })).toBeNull();
});


it("reports a draft copy that cannot be prepared", async () => {
  mocks.blob.mockRejectedValue("offline");
  render(<SollecitiPage />);
  fireEvent.click(await screen.findByRole("button", { name: /Import 2022/ }));
  fireEvent.click(await screen.findByRole("button", { name: "Esamina documento" }));
  fireEvent.click(screen.getByRole("button", { name: "Carica anteprima PDF" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Documento non disponibile");
});

it.each([false, true])("drops a document answer that arrives after closing (failure=%s)", async (failure) => {
  const created = vi.fn(() => "blob:late");
  vi.stubGlobal("URL", Object.assign(URL, { createObjectURL: created, revokeObjectURL: vi.fn() }));
  const pending = deferred<Blob>();
  mocks.blob.mockReturnValue(pending.promise);
  const { result, unmount } = renderHook(() => useDocumentBlob("token", "/documento", "GET"));
  act(() => result.current.request());
  unmount();
  await act(async () => { if (failure) pending.reject(new Error("late")); else pending.resolve(new Blob(["%PDF"])); });
  expect(created).not.toHaveBeenCalled();
});

it("releases the loaded document when the viewer closes", async () => {
  const revoked = vi.fn();
  vi.stubGlobal("URL", Object.assign(URL, { createObjectURL: vi.fn(() => "blob:chiuso"), revokeObjectURL: revoked }));
  mocks.blob.mockResolvedValue(new Blob(["%PDF"]));
  const { result, unmount } = renderHook(() => useDocumentBlob("token", "/documento", "GET"));
  act(() => result.current.request());
  await waitFor(() => expect(result.current.url).toBe("blob:chiuso"));
  unmount();
  expect(revoked).toHaveBeenCalledWith("blob:chiuso");
});

it("prepares the final export once confirmed and reports a stale batch", async () => {
  vi.stubGlobal("URL", Object.assign(URL, { createObjectURL: vi.fn(() => "blob:zip"), revokeObjectURL: vi.fn() }));
  const pending = deferred<Blob>();
  mocks.blob.mockRejectedValueOnce(new Error("Dati modificati: rigenerare la bozza")).mockReturnValueOnce(pending.promise);
  mocks.get.mockResolvedValue(batch("confirmed"));
  render(<SollecitiPage />);
  fireEvent.click(await screen.findByRole("button", { name: /Import 2022/ }));
  fireEvent.click(await screen.findByRole("button", { name: "Prepara export definitivo" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("rigenerare la bozza");
  fireEvent.click(screen.getByRole("button", { name: "Prepara export definitivo" }));
  expect(screen.getByRole("button", { name: "Verifica e preparazione..." })).toBeDisabled();
  await act(async () => pending.resolve(new Blob(["ZIP"])));
  expect(screen.getByRole("link", { name: "Scarica ZIP definitivo" })).toHaveAttribute("download", "solleciti-batch-1-v1.zip");
  expect(mocks.blob).toHaveBeenLastCalledWith("/ruolo/tributi/solleciti/batches/batch-1/export", expect.objectContaining({ method: "POST" }));
});

it("shows the confirmed export without the prepare action to viewers", async () => {
  mocks.session.mockReturnValue({ status: "ready", token: "token", currentUser: { role: "admin", enabled_modules: ["ruolo"] }, grantedSectionKeys: ["ruolo.tributi.view"] });
  mocks.get.mockResolvedValue(batch("confirmed"));
  render(<SollecitiPage />);
  fireEvent.click(await screen.findByRole("button", { name: /Import 2022/ }));
  await screen.findByRole("region", { name: "Export definitivo" });
  expect(screen.queryByRole("button", { name: "Prepara export definitivo" })).toBeNull();
});


it("lets editors regenerate the selected batch, then reloads it", async () => {
  regeneration.listRegenerationTargets.mockResolvedValue({ items: [{ item_id: "item-2", batch_id: "batch-2", display_name: "Anna Bianchi", codice_fiscale: "RSSMRA80A01H501Z" }], excluded_drafts: 0 });
  regeneration.regenerateReminderItem.mockResolvedValue({ item_id: "item-2", outcome: "regenerated", detail: null });
  await openGenerated();
  const panel = screen.getByRole("region", { name: "Rigenera PDF" });
  fireEvent.click(within(panel).getByRole("radio", { name: "Solo il lotto selezionato" }));
  fireEvent.click(within(panel).getByRole("button", { name: "Rigenera PDF" }));
  expect(await within(panel).findByText(/Completata: 1 di 1/)).toBeVisible();
  expect(regeneration.listRegenerationTargets).toHaveBeenCalledWith("token", "batch-2");
  await waitFor(() => expect(mocks.get).toHaveBeenCalledTimes(2));
});

it("reloads nothing when no batch is open, and hides regeneration from viewers", async () => {
  regeneration.listRegenerationTargets.mockResolvedValue({ items: [], excluded_drafts: 0 });
  render(<SollecitiPage />);
  await screen.findByRole("button", { name: /Import 2022/ });
  fireEvent.click(screen.getByRole("button", { name: "Rigenera PDF" }));
  expect(await screen.findByText(/Completata: 0 di 0/)).toBeVisible();
  expect(mocks.get).not.toHaveBeenCalled();
  cleanup();
  mocks.session.mockReturnValue({ status: "ready", token: "token", currentUser: { role: "admin", enabled_modules: ["ruolo"] }, grantedSectionKeys: ["ruolo.tributi.view"] });
  render(<SollecitiPage />);
  await screen.findByRole("button", { name: /Import 2022/ });
  expect(screen.queryByRole("region", { name: "Rigenera PDF" })).toBeNull();
});
