import { act, cleanup, fireEvent, render, renderHook, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { PosteWorkspace } from "@/components/ruolo/solleciti/poste-workspace";
import { usePosteWorkspace } from "@/components/ruolo/solleciti/use-poste-workspace";
import type { WorkspaceNotice, WorkspaceResult } from "@/lib/ruolo-solleciti-workspace-api";

const api = vi.hoisted(() => ({ getSollecitiWorkspace: vi.fn(), generateSolleciti: vi.fn(), prepareSolleciti: vi.fn(), reconcileSollecitiAccount: vi.fn() }));
const poste = vi.hoisted(() => ({ requestPosteJob: vi.fn(), getPosteLot: vi.fn(), listPosteAccounts: vi.fn() }));
vi.mock("@/lib/ruolo-solleciti-workspace-api", () => api);
vi.mock("@/lib/ruolo-poste-dispatch-api", () => poste);
// Real document fetching/render controls are already characterized by the PDF suite.
vi.mock("@/components/ruolo/solleciti/document-access", () => ({ GeneratedNoticePreview: ({ url }: { url: string }) => <div aria-label="PDF reale" data-url={url} /> }));
const available: WorkspaceNotice = {
  item_id: "i1", batch_id: "b1", notice_number: "N1", codice_fiscale: "12345678901", label: "Azienda sintetica",
  years: [2021], document_status: "generated", amount: 100, can_prepare: true, download_url: "/document/i1",
  poste_dispatches: [], account_key: "none", account_label: "Da assegnare", lot_id: null, stage: "available",
};
const sent: WorkspaceNotice = { ...available, item_id: "i2", notice_number: "N2", stage: "sent", can_prepare: false, account_key: "1", account_label: "account-1", lot_id: "lot-1", poste_dispatches: [{ id: "d1", notice_number: "N2", status: "sent", poste_draft_id: "POSTE-TEST", poste_status: "Accettato", draft_created_at: null, sent_at: "2026-11-05T10:00:00Z", tracking_number: "TRACK-TEST", upload_requested_by_username: "operator-test", updated_at: "2026-11-05T10:00:00Z", poste_username: "account-1" }] };
function data(overrides: Partial<WorkspaceResult> = {}): WorkspaceResult {
  return { items: [available, sent], groups: [
    { years: [2021], account_key: "none", account_label: "Da assegnare", total: 1, stages: { available: 1 } },
    { years: [2021], account_key: "1", account_label: "account-1", total: 1, stages: { sent: 1 } },
  ], total: 2, page: 1, page_size: 20, ...overrides };
}
function mount(canEdit = true) { return render(<PosteWorkspace token="t" canEdit={canEdit} legacy={<p>Storico tecnico mantenuto</p>} />); }

beforeEach(() => {
  vi.resetAllMocks();
  api.getSollecitiWorkspace.mockResolvedValue(data());
  api.generateSolleciti.mockResolvedValue({ created: ["i3"], reused: ["i1"], problems: [] });
  api.prepareSolleciti.mockResolvedValue({ id: "new-lot" });
  api.reconcileSollecitiAccount.mockResolvedValue({ queued_jobs: [1, 2], busy_lots: 1 });
  poste.requestPosteJob.mockResolvedValue({ id: 1 });
  poste.getPosteLot.mockResolvedValue({ id: "lot-1" });
  poste.listPosteAccounts.mockResolvedValue([{ id: 1, label: "Account test", username: "account-1", active: true }]);
});
afterEach(() => { cleanup(); vi.useRealTimers(); });

it("refreshes only an explicitly selected account and reports queueing and provider errors", async () => {
  mount(); await screen.findByText("2 avvisi · pagina 1");
  expect(screen.queryByRole("button", { name: "Controlla account su Poste" })).toBeNull();
  fireEvent.click(screen.getByText("Altri filtri"));
  fireEvent.change(screen.getByLabelText("Account Poste"), { target: { value: "1" } });
  fireEvent.click(await screen.findByRole("button", { name: "Controlla account su Poste" }));
  await screen.findByText(/Controlli accodati: 2/);
  expect(api.reconcileSollecitiAccount).toHaveBeenCalledWith("t", 1, 2021);
  api.reconcileSollecitiAccount.mockRejectedValueOnce(new Error("Account non disponibile"));
  fireEvent.click(screen.getByRole("button", { name: "Controlla account su Poste" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Account non disponibile");
  expect(screen.getByRole("button", { name: "Controlla account su Poste" })).toBeEnabled();
});

it("can queue an account refresh across all years and surfaces non-Error failures", async () => {
  const hook = renderHook(() => usePosteWorkspace("t"));
  act(() => hook.result.current.filter({ account: "1", year: "" }));
  await act(async () => { await hook.result.current.reconcileAccount(); });
  expect(api.reconcileSollecitiAccount).toHaveBeenCalledWith("t", 1, null);
  api.reconcileSollecitiAccount.mockRejectedValueOnce("offline");
  await act(async () => { await hook.result.current.reconcileAccount(); });
  expect(hook.result.current.error).toBe("Controllo account non avviato");
  expect(hook.result.current.notice).toBeNull();
  expect(hook.result.current.busy).toBe(false);
});

it("opens canonical notices and only selects available ones for worker preparation", async () => {
  mount();
  await screen.findByText("2 avvisi · pagina 1");
  expect(screen.getByRole("checkbox", { name: "Prepara avviso N2" })).toBeDisabled();
  fireEvent.click(screen.getByRole("button", { name: "Apri avviso N1" }));
  expect(screen.getByRole("region", { name: "Dettaglio avviso" })).toHaveTextContent("Avviso N1");
  expect(screen.getByLabelText("PDF reale")).toHaveAttribute("data-url", "/document/i1");
  expect(screen.getByRole("button", { name: "Apri avviso N1" })).toHaveAttribute("aria-pressed", "true");
  fireEvent.click(screen.getByRole("checkbox", { name: "Prepara avviso N1" }));
  const prepare = screen.getByRole("button", { name: "Prepara su Poste" });
  expect(prepare).toBeDisabled();
  await screen.findByRole("option", { name: "Account test · account-1" });
  fireEvent.change(screen.getByRole("combobox", { name: "Account per la preparazione" }), { target: { value: "1" } });
  fireEvent.click(prepare);
  await screen.findByText(/Preparazione avviata/);
  await screen.findByText("2 avvisi · pagina 1");
  expect(screen.queryByRole("region", { name: "Prepara su Poste" })).toBeNull();
  expect(api.prepareSolleciti).toHaveBeenCalledWith("t", ["i1"], 1);
  expect(api.generateSolleciti).not.toHaveBeenCalled();
});

it("preserves technical batch history without making it the default view", async () => {
  mount();
  expect(screen.queryByText("Storico tecnico mantenuto")).toBeNull();
  fireEvent.click(screen.getByText("Strumenti avanzati"));
  fireEvent.click(screen.getByRole("button", { name: "Storico lotti di generazione" }));
  expect(screen.getByText("Storico tecnico mantenuto")).toBeVisible();
  fireEvent.click(screen.getByRole("button", { name: "Torna agli avvisi" }));
  expect(await screen.findByText("2 avvisi · pagina 1")).toBeVisible();
});

it("keeps Poste identifiers and dates in the notice detail without exposing a lot command", async () => {
  mount(); await screen.findByText("2 avvisi · pagina 1");
  fireEvent.click(screen.getByRole("button", { name: "Apri avviso N2" }));
  const summary = screen.getByText("ID Poste, date e storico");
  expect(summary.closest("details")).not.toHaveAttribute("open");
  fireEvent.click(summary);
  expect(screen.getByText("POSTE-TEST")).toBeVisible();
  expect(screen.getByText("TRACK-TEST")).toBeVisible();
  expect(screen.queryByRole("button", { name: "Apri lavorazione Poste" })).toBeNull();
});

it("filters on the server by reference year, account, status and search", async () => {
  mount(); await screen.findByText("2 avvisi · pagina 1");
  fireEvent.click(screen.getByText("Altri filtri"));
  fireEvent.change(screen.getByLabelText("Account Poste"), { target: { value: "1" } });
  await waitFor(() => expect(api.getSollecitiWorkspace).toHaveBeenLastCalledWith("t", expect.objectContaining({ year: "2021", account: "1", page: 1 })));
  await screen.findByText("2 avvisi · pagina 1");
  fireEvent.change(screen.getByLabelText("Stato avviso"), { target: { value: "sent" } });
  await waitFor(() => expect(api.getSollecitiWorkspace).toHaveBeenLastCalledWith("t", expect.objectContaining({ stage: "sent" })));
  fireEvent.change(screen.getByLabelText("Anno di riferimento"), { target: { value: "" } });
  await waitFor(() => expect(api.getSollecitiWorkspace).toHaveBeenLastCalledWith("t", expect.objectContaining({ year: "", account: "all" })));
  fireEvent.change(screen.getByLabelText("Cerca contribuente o avviso"), { target: { value: "Rossi" } });
  fireEvent.click(screen.getByRole("button", { name: "Cerca" }));
  await waitFor(() => expect(api.getSollecitiWorkspace).toHaveBeenLastCalledWith("t", expect.objectContaining({ q: "Rossi", page: 1 })));
  fireEvent.click(screen.getByText("Altri filtri"));
  fireEvent.click(screen.getByRole("button", { name: "Reimposta filtri" }));
  const calls = api.getSollecitiWorkspace.mock.calls.length;
  fireEvent.click(screen.getByRole("button", { name: "Aggiorna elenco" }));
  await waitFor(() => expect(api.getSollecitiWorkspace.mock.calls.length).toBeGreaterThan(calls));
});

it("paginates and exposes missing documents without a false preview", async () => {
  api.getSollecitiWorkspace.mockResolvedValue(data({ page: 2, total: 60, items: [{ ...available, download_url: null, years: [] }] }));
  mount(); await screen.findByText("60 avvisi · pagina 2");
  fireEvent.click(screen.getByRole("button", { name: "Apri avviso N1" }));
  expect(screen.getByRole("alert")).toHaveTextContent("PDF non disponibile");
  fireEvent.click(screen.getByRole("button", { name: "Precedenti avvisi" }));
  await waitFor(() => expect(api.getSollecitiWorkspace).toHaveBeenLastCalledWith("t", expect.objectContaining({ page: 1 })));
  await screen.findByText("60 avvisi · pagina 2");
  fireEvent.click(screen.getByRole("button", { name: "Altri avvisi" }));
  await waitFor(() => expect(api.getSollecitiWorkspace).toHaveBeenLastCalledWith("t", expect.objectContaining({ page: 3 })));
});

it("keeps read-only users from generation, selections and reconciliation writes", async () => {
  mount(false); await screen.findByText("2 avvisi · pagina 1");
  expect(screen.queryByRole("checkbox")).toBeNull();
  expect(screen.queryByRole("button", { name: "Genera o recupera PDF" })).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Apri avviso N2" }));
  expect(screen.queryByRole("button", { name: "Controlla stato su Poste" })).toBeNull();
  expect(screen.queryByRole("button", { name: "Apri lavorazione Poste" })).toBeNull();
  fireEvent.click(screen.getByText("Altri filtri"));
  fireEvent.change(screen.getByLabelText("Account Poste"), { target: { value: "1" } });
  expect(screen.queryByRole("button", { name: "Controlla account su Poste" })).toBeNull();
});

it("reconciles via the existing worker job and reports failures instead of changing sent state locally", async () => {
  mount(); await screen.findByText("2 avvisi · pagina 1");
  fireEvent.click(screen.getByRole("button", { name: "Apri avviso N2" }));
  fireEvent.click(screen.getByRole("button", { name: "Controlla stato su Poste" }));
  await screen.findByText(/Controllo Poste accodato/);
  expect(poste.requestPosteJob).toHaveBeenCalledWith("t", "lot-1", "reconcile");
  await screen.findByText("2 avvisi · pagina 1");
  poste.requestPosteJob.mockRejectedValue(new Error("Account disabilitato"));
  fireEvent.click(screen.getByRole("button", { name: "Controlla stato su Poste" }));
  expect(await screen.findByText("Account disabilitato")).toBeVisible();
  expect(screen.queryByRole("button", { name: "Apri lavorazione Poste" })).toBeNull();
});

it("disables PDF generation without duplicate identity or year fields and keeps the unified search usable", async () => {
  mount();
  await screen.findByText("2 avvisi · pagina 1");
  const generate = screen.getByRole("button", { name: "Genera o recupera PDF" });
  expect(generate).toBeDisabled();
  expect(generate).toHaveAccessibleDescription("Generazione temporaneamente disabilitata.");
  expect(screen.queryByLabelText("CF / P.IVA")).toBeNull();
  expect(screen.queryByLabelText("Anno da generare")).toBeNull();
  expect(screen.getAllByRole("textbox")).toHaveLength(1);
  fireEvent.click(generate);
  expect(api.generateSolleciti).not.toHaveBeenCalled();
  fireEvent.change(screen.getByLabelText("Cerca contribuente o avviso"), { target: { value: "Rossi Mario" } });
  fireEvent.submit(screen.getByRole("form", { name: "Filtri avvisi" }));
  await waitFor(() => expect(api.getSollecitiWorkspace).toHaveBeenLastCalledWith("t", expect.objectContaining({ year: "2021", q: "Rossi Mario" })));
  expect(api.generateSolleciti).not.toHaveBeenCalled();
});

it("reports preparation conflicts, preserves selection and supports retry", async () => {
  mount();
  await screen.findByText("2 avvisi · pagina 1");
  fireEvent.click(screen.getByRole("checkbox", { name: "Prepara avviso N1" }));
  await screen.findByRole("option", { name: "Account test · account-1" });
  fireEvent.change(screen.getByRole("combobox", { name: "Account per la preparazione" }), { target: { value: "1" } });
  api.prepareSolleciti.mockRejectedValueOnce(new Error("Avviso già assegnato"));
  fireEvent.click(screen.getByRole("button", { name: "Prepara su Poste" }));
  expect(await screen.findByText("Avviso già assegnato")).toBeVisible();
  expect(screen.getByRole("region", { name: "Prepara su Poste" })).toBeVisible();
  expect(screen.getByRole("checkbox", { name: "Prepara avviso N1" })).toBeChecked();
  fireEvent.click(screen.getByRole("button", { name: "Prepara su Poste" }));
  await screen.findByText(/Preparazione avviata/);
  await screen.findByText("2 avvisi · pagina 1");
  expect(screen.queryByRole("region", { name: "Prepara su Poste" })).toBeNull();
});

it("reports empty/error reads and yearless historical records", async () => {
  api.getSollecitiWorkspace.mockRejectedValueOnce("offline");
  mount();
  expect(await screen.findByText("Avvisi non caricati")).toBeVisible();
  expect(screen.queryByText("Caricamento avvisi...")).toBeNull();
  api.getSollecitiWorkspace.mockResolvedValueOnce(data({ items: [], total: 0, groups: [{ years: [], account_key: "none", account_label: "Da assegnare", total: 1, stages: { review: 1 } }] }));
  fireEvent.click(screen.getByRole("button", { name: "Aggiorna elenco" }));
  expect(await screen.findByText("Nessun avviso corrisponde ai filtri.")).toBeVisible();
  expect(screen.getByLabelText("Anno di riferimento")).toHaveValue("2021");
});

it("keeps the default screen focused on notices and reveals extra filters only on request", async () => {
  mount(); await screen.findByText("2 avvisi · pagina 1");
  expect(screen.queryByRole("navigation", { name: "Avvisi per anno e account" })).toBeNull();
  expect(screen.getByLabelText("Stato avviso").closest("details")).not.toHaveAttribute("open");
  expect(screen.getByRole("button", { name: "Storico lotti di generazione" }).closest("details")).not.toHaveAttribute("open");
  expect(screen.queryByRole("region", { name: "Prepara su Poste" })).toBeNull();
  fireEvent.click(screen.getByText("Altri filtri"));
  expect(screen.getByRole("combobox", { name: "Stato avviso" })).toBeVisible();
  fireEvent.change(screen.getByLabelText("Stato avviso"), { target: { value: "sent" } });
  expect(screen.getByText("Attivi")).toBeVisible();
  fireEvent.click(screen.getByRole("button", { name: "Reimposta filtri" }));
  expect(screen.queryByText("Attivi")).toBeNull();
});

it("discards stale reads, bounds selection and clears it when filters change", async () => {
  let stale!: (value: WorkspaceResult) => void;
  api.getSollecitiWorkspace.mockReturnValueOnce(new Promise<WorkspaceResult>((resolve) => { stale = resolve; }));
  const hook = renderHook(() => usePosteWorkspace("t"));
  act(() => hook.result.current.filter({ q: "new" }));
  await waitFor(() => expect(hook.result.current.data).not.toBeNull());
  await act(async () => stale(data({ total: 999 })));
  expect(hook.result.current.data?.total).toBe(2);
  act(() => { hook.result.current.toggle("i1"); });
  act(() => { hook.result.current.toggle("i1"); });
  expect(hook.result.current.selected).toEqual([]);
  act(() => { for (let i = 0; i < 51; i++) hook.result.current.toggle(`id-${i}`); });
  expect(hook.result.current.selected).toHaveLength(50);
  act(() => hook.result.current.filter({ account: "none" }));
  expect(hook.result.current.selected).toEqual([]);
  hook.unmount();
});

it("refreshes visible pages and cleans the timer on unmount", async () => {
  vi.useFakeTimers();
  const hook = renderHook(() => usePosteWorkspace("t"));
  await act(async () => { await Promise.resolve(); });
  const visibility = vi.spyOn(document, "visibilityState", "get");
  visibility.mockReturnValue("hidden");
  await act(async () => { vi.advanceTimersByTime(30_000); });
  expect(api.getSollecitiWorkspace).toHaveBeenCalledTimes(1);
  visibility.mockReturnValue("visible");
  await act(async () => { vi.advanceTimersByTime(30_000); });
  expect(api.getSollecitiWorkspace).toHaveBeenCalledTimes(2);
  hook.unmount(); visibility.mockRestore();
  expect(vi.getTimerCount()).toBe(0);
});

it("ignores a failed obsolete request after a newer filter has loaded", async () => {
  let reject!: (reason: Error) => void;
  api.getSollecitiWorkspace.mockReturnValueOnce(new Promise<WorkspaceResult>((_resolve, fail) => { reject = fail; }));
  const hook = renderHook(() => usePosteWorkspace("t"));
  act(() => hook.result.current.filter({ q: "current" }));
  await waitFor(() => expect(hook.result.current.data?.total).toBe(2));
  await act(async () => reject(new Error("obsolete failure")));
  expect(hook.result.current.error).toBeNull();
});

it("keeps the open PDF mounted while refreshing states", async () => {
  mount(); await screen.findByText("2 avvisi · pagina 1");
  fireEvent.click(screen.getByRole("button", { name: "Apri avviso N1" }));
  const preview = screen.getByLabelText("PDF reale");
  let finish!: (value: WorkspaceResult) => void;
  api.getSollecitiWorkspace.mockReturnValueOnce(new Promise<WorkspaceResult>((resolve) => { finish = resolve; }));
  fireEvent.click(screen.getByRole("button", { name: "Aggiorna elenco" }));
  expect(preview).toBeInTheDocument();
  expect(screen.queryByText("Caricamento avvisi...")).toBeNull();
  await act(async () => finish(data()));
  expect(screen.getByLabelText("PDF reale")).toBe(preview);
});

it("clears previous identity data, selection and detail when the session token changes", async () => {
  const hook = renderHook(({ token }) => usePosteWorkspace(token), { initialProps: { token: "first" } });
  await waitFor(() => expect(hook.result.current.data?.total).toBe(2));
  act(() => { hook.result.current.toggle("i1"); hook.result.current.setDetailId("i1"); });
  let finish!: (value: WorkspaceResult) => void;
  api.getSollecitiWorkspace.mockReturnValueOnce(new Promise<WorkspaceResult>((resolve) => { finish = resolve; }));
  hook.rerender({ token: "second" });
  expect(hook.result.current.data).toBeNull();
  expect(hook.result.current.selected).toEqual([]);
  expect(hook.result.current.detailId).toBeNull();
  expect(api.getSollecitiWorkspace).toHaveBeenLastCalledWith("second", expect.any(Object));
  await act(async () => finish(data()));
});


it("shows global Poste state counts independently of the current page and filters them by year/account", async () => {
  api.getSollecitiWorkspace.mockResolvedValue(data({ groups: [
    ...data().groups,
    { years: [2021], account_key: "1", account_label: "account-1", total: 7, stages: { sent: 2, draft: 3, processing: 1, review: 1 } },
    { years: [2022], account_key: "2", account_label: "account-2", total: 4, stages: { sent: 4 } },
  ] }));
  mount();
  const counts = await screen.findByRole("navigation", { name: "Stati avvisi su Poste" });
  expect(within(counts).getByRole("button", { name: "Tutti · 9" })).toHaveAttribute("aria-pressed", "true");
  expect(within(counts).getByRole("button", { name: "Caricato su Poste · 3" })).toBeVisible();
  fireEvent.click(within(counts).getByRole("button", { name: "Spedito · 3" }));
  await waitFor(() => expect(api.getSollecitiWorkspace).toHaveBeenLastCalledWith("t", expect.objectContaining({ stage: "sent", page: 1 })));
  const states = await screen.findByRole("navigation", { name: "Stati avvisi su Poste" });
  expect(within(states).getByRole("button", { name: "Spedito · 3" })).toHaveAttribute("aria-pressed", "true");
  fireEvent.click(within(states).getByRole("button", { name: "Tutti · 9" }));
  await screen.findByText("2 avvisi · pagina 1");
  fireEvent.change(screen.getByRole("combobox", { name: "Account Poste", exact: true }), { target: { value: "1" } });
  await waitFor(() => expect(within(screen.getByRole("navigation", { name: "Stati avvisi su Poste" })).getByRole("button", { name: "Tutti · 8" })).toBeInTheDocument());
  fireEvent.change(screen.getByLabelText("Anno di riferimento"), { target: { value: "2022" } });
  await waitFor(() => expect(within(screen.getByRole("navigation", { name: "Stati avvisi su Poste" })).getByRole("button", { name: "Tutti · 4" })).toBeInTheDocument());
  fireEvent.change(screen.getByLabelText("Anno di riferimento"), { target: { value: "" } });
  await waitFor(() => expect(within(screen.getByRole("navigation", { name: "Stati avvisi su Poste" })).getByRole("button", { name: "Tutti · 13" })).toBeInTheDocument());
});

it("shows persisted sent/upload IDs and dates in the list, ignoring cancelled attempts and keeping selection blocked", async () => {
  const uploaded = { ...sent, item_id: "i3", notice_number: "N3", stage: "draft" as const, poste_dispatches: [{ ...sent.poste_dispatches[0], id: "draft", status: "draft_priced", poste_draft_id: "UPLOAD-ID", sent_at: null, draft_created_at: "2026-11-04T09:00:00Z", tracking_number: null }] };
  const cancelled = { ...sent.poste_dispatches[0], id: "cancelled", status: "cancelled", poste_draft_id: "IGNORE-CANCELLED" };
  api.getSollecitiWorkspace.mockResolvedValue(data({ items: [{ ...sent, poste_dispatches: [cancelled, ...sent.poste_dispatches] }, uploaded] }));
  mount();
  const list = await screen.findByRole("region", { name: "Elenco avvisi" });
  expect(within(list).getByText(/ID Poste: POSTE-TEST · Spedito il/)).toHaveTextContent("05/11/26");
  expect(within(list).getByText("Raccomandata: TRACK-TEST")).toBeVisible();
  expect(within(list).getByText(/ID Poste: UPLOAD-ID · Caricato il/)).toHaveTextContent("04/11/26");
  expect(within(list).queryByText(/IGNORE-CANCELLED/)).not.toBeInTheDocument();
  expect(within(list).getByRole("checkbox", { name: "Prepara avviso N2" })).toBeDisabled();
  expect(within(list).getByRole("checkbox", { name: "Prepara avviso N3" })).toBeDisabled();
});

it("keeps absent Poste metadata explicit without fabricating a shipment date or draft ID", async () => {
  api.getSollecitiWorkspace.mockResolvedValue(data({ groups: [], items: [
    { ...sent, poste_dispatches: [] },
    { ...sent, item_id: "i3", notice_number: "N3", stage: "draft", poste_dispatches: [{ ...sent.poste_dispatches[0], status: "draft_created", poste_draft_id: null, draft_created_at: null, tracking_number: null }] },
  ] }));
  mount();
  await screen.findByText("2 avvisi · pagina 1");
  expect(screen.getByText("Storico Poste da verificare")).toBeVisible();
  expect(screen.getByText("ID Poste: Non registrato · Caricato il -")).toBeVisible();
  expect(within(screen.getByRole("navigation", { name: "Stati avvisi su Poste" })).getByRole("button", { name: "Tutti · 0" })).toBeInTheDocument();
});
