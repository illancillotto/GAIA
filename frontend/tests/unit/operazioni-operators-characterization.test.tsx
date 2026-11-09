import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import Page from "@/app/operazioni/operatori/page";

const mocks = vi.hoisted(() => ({
  role: "admin", query: "", operators: vi.fn(), areas: vi.fn(), detail: vi.fn(), unlinked: vi.fn(), save: vi.fn(),
  autoLink: vi.fn(), bulk: vi.fn(), invite: vi.fn(), clipboard: vi.fn(),
}));
vi.mock("next/navigation", () => ({ useSearchParams: () => new URLSearchParams(mocks.query) }));
vi.mock("@/components/operazioni/operazioni-module-page", () => ({
  OperazioniModulePage: ({ children }: { children: (value: unknown) => React.ReactNode }) => <main>{children({ currentUser: { role: mocks.role } })}</main>,
}));
vi.mock("@/features/operazioni/api/client", () => ({
  getOperators: mocks.operators, getAreas: mocks.areas, getOperatorDetail: mocks.detail, getUnlinkedOperators: mocks.unlinked,
  updateGateMobileConsolePermissions: mocks.save, autoLinkGaiaOperators: mocks.autoLink,
  bulkImportOperatorsAsGaiaUsers: mocks.bulk, inviteOperator: mocks.invite,
}));

function operator(values: Record<string, unknown> = {}) {
  return { id: "o1", wc_id: 100, first_name: "Ada", last_name: "Synthetic", username: "ada", email: "ada@example.test",
    tax: "SYNTHETIC", role: "operator", enabled: true, gaia_user_id: 77, gate_mobile_console_enabled: false,
    gate_mobile_console_role: null, current_fuel_cards: [], wc_synced_at: null, created_at: "2026-10-01", updated_at: "2026-10-01", ...values };
}
function detail(subject = operator(), values: Record<string, unknown> = {}) {
  return { operator: subject, stats: { fuel_cards_count: 0, total_liters: "12.5", total_fuel_cost: "20.50", total_km_travelled: "120",
    usage_sessions_count: 2, most_used_vehicle: { vehicle_label: "Synthetic Truck", usage_count: 2, km_travelled: "5.5" }, last_used_vehicle_label: "Synthetic Truck" },
    current_fuel_cards: [{ id: "f1", codice: "SYN", pan: "111" }, { id: "f2", codice: null, pan: "222" }],
    recent_fuel_logs: [
      { id: "l1", vehicle_label: "Synthetic Fuel", fueled_at: "2026-10-01T08:00:00Z", liters: "3", total_cost: "10.2", odometer_km: "12.5", station_name: "Synthetic Station" },
      { id: "l2", vehicle_label: "Synthetic Fuel Invalid", fueled_at: "invalid", liters: "invalid", total_cost: null, odometer_km: "", station_name: null },
    ],
    recent_usage_sessions: [
      { id: "s1", vehicle_label: "Synthetic Open", started_at: "2026-10-01T08:00:00Z", ended_at: null, km_travelled: "7", status: "open" },
      { id: "s2", vehicle_label: "Synthetic Closed", started_at: "invalid", ended_at: "2026-10-01T09:00:00Z", km_travelled: null, status: "closed" },
    ], ...values };
}
function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>(done => { resolve = done; });
  return { promise, resolve };
}
async function ready() { await waitFor(() => expect(screen.queryByText("Caricamento operatori in corso.")).toBeNull()); }
async function open(index = 0) {
  fireEvent.click(screen.getAllByRole("button", { name: /Ada Synthetic/ })[index]);
  await screen.findByText("KPI operativi");
}
const originalClipboard = Object.getOwnPropertyDescriptor(navigator, "clipboard");

beforeEach(() => {
  vi.resetAllMocks(); mocks.role = "admin"; mocks.query = "";
  mocks.operators.mockResolvedValue({ items: [operator()], total: 1 });
  mocks.areas.mockResolvedValue({ items: [], total: 0 });
  mocks.unlinked.mockResolvedValue({ items: [], total: 0 });
  mocks.detail.mockResolvedValue(detail());
  mocks.save.mockImplementation(async (_id, data) => ({ ...operator(), gate_mobile_console_enabled: data.enabled, gate_mobile_console_role: data.role }));
  mocks.clipboard.mockResolvedValue(undefined);
  Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText: mocks.clipboard } });
});
afterEach(() => {
  vi.restoreAllMocks(); vi.useRealTimers();
  if (originalClipboard) Object.defineProperty(navigator, "clipboard", originalClipboard);
  else Reflect.deleteProperty(navigator, "clipboard");
});

describe("operator catalog and details used to assign HR permissions", () => {
  it("keeps filters, area structure, role grouping and sparse operator identities usable", async () => {
    mocks.role = "hr_manager";
    const variants = [operator(), operator({ id: "admin", role: "admin" }), operator({ id: "o2", first_name: null, last_name: null, username: "single", role: "admin", enabled: false }),
      operator({ id: "o3", first_name: null, last_name: null, username: null, email: "fallback@example.test", role: "capo_reparto", current_fuel_cards: [{ codice: " CARD " }] }),
      operator({ id: "o4", wc_id: 400, first_name: null, last_name: null, username: null, email: null, tax: null, gaia_user_id: null, role: null })];
    mocks.operators.mockResolvedValue({ items: variants });
    mocks.areas.mockResolvedValue({ items: [
      { id: "a1", wc_id: 1, name: "District Color", is_district: true, color: "#006600", description: "Synthetic district" },
      { id: "a2", wc_id: 2, name: "District Plain", is_district: true, color: null, description: null },
      { id: "a3", wc_id: 3, name: "Area One", is_district: false, description: "Area description" },
      { id: "a4", wc_id: 4, name: "Area Two", is_district: false, description: null },
    ] });
    render(<Page />); await ready();
    expect(screen.getByText("District Color")).toBeVisible(); expect(screen.getByText("Area One")).toBeVisible();
    expect(screen.getAllByText("Operatore 400").length).toBeGreaterThan(0);
    for (const card of screen.getAllByRole("button", { name: /Ada Synthetic/ })) fireEvent.click(card);
    expect(mocks.detail).not.toHaveBeenCalled();
    fireEvent.change(screen.getByRole("textbox", { name: "Ricerca rapida" }), { target: { value: "  Synthetic  " } });
    fireEvent.change(screen.getByRole("combobox", { name: "Filtro stato" }), { target: { value: "capo_reparto" } });
    fireEvent.change(screen.getByRole("combobox", { name: "Abilitazione" }), { target: { value: "false" } });
    await waitFor(() => expect(mocks.operators).toHaveBeenLastCalledWith({ page_size: "50", search: "Synthetic", role: "capo_reparto", enabled: "false" }));
    expect(screen.getByText("Ricerca: Synthetic")).toBeVisible();
  });

  it("shows populated detail histories, restores scrolling on close, and opens both desktop and mobile cards", async () => {
    mocks.role = "super_admin";
    render(<Page />); await ready(); await open();
    expect(screen.getByText("Synthetic Fuel")).toBeVisible(); expect(screen.getByText("Synthetic Open")).toBeVisible();
    expect(screen.getByText("222")).toBeVisible(); expect(document.body.style.overflow).toBe("hidden");
    fireEvent.keyDown(window, { key: "Tab" }); expect(screen.getByText("KPI operativi")).toBeVisible();
    fireEvent.keyDown(window, { key: "Escape" }); expect(screen.queryByText("KPI operativi")).toBeNull();
    expect(document.body.style.overflow).toBe("");
    await open(1);
    fireEvent.click(screen.getByRole("button", { name: "Chiudi", exact: true }));
    expect(screen.queryByText("KPI operativi")).toBeNull();
  });

  it("does not show a mismatched detail response as another operator's profile", async () => {
    mocks.detail.mockResolvedValue(detail(operator({ id: "different" })));
    render(<Page />); await ready();
    fireEvent.click(screen.getAllByRole("button", { name: /Ada Synthetic/ })[0]);
    expect(await screen.findByText("Nessun dettaglio disponibile.")).toBeVisible();
    expect(screen.queryByRole("combobox", { name: "Ruolo console" })).toBeNull();
  });

  it.each([new Error("Detail unavailable"), "unknown"])("shows detail fetch failures without editable permissions (%s)", async reason => {
    mocks.detail.mockRejectedValue(reason);
    render(<Page />); await ready();
    fireEvent.click(screen.getAllByRole("button", { name: /Ada Synthetic/ })[0]);
    expect(await screen.findByText(reason instanceof Error ? reason.message : "Errore nel caricamento dettaglio operatore")).toBeVisible();
    expect(screen.queryByRole("combobox", { name: "Ruolo console" })).toBeNull();
  });

  it.each([new Error("Catalog unavailable"), "unknown"])("reports catalog failure while keeping an empty safe view (%s)", async reason => {
    mocks.operators.mockRejectedValue(reason); mocks.unlinked.mockRejectedValue(new Error("Unavailable"));
    render(<Page />); await ready();
    expect(await screen.findByText(reason instanceof Error ? reason.message : "Errore nel caricamento operatori")).toBeVisible();
    expect(screen.getByText("Nessun operatore trovato")).toBeVisible();
  });

  it("accepts missing optional catalog arrays and totals", async () => {
    mocks.operators.mockResolvedValue({}); mocks.areas.mockResolvedValue({}); mocks.unlinked.mockResolvedValue({});
    render(<Page />); await ready();
    expect(screen.getByText("Nessun operatore trovato")).toBeVisible();
    expect(screen.getByText("Nessuna area trovata")).toBeVisible();
  });

  it("limits role previews and handles an area catalog with no districts", async () => {
    mocks.operators.mockResolvedValue({ items: Array.from({ length: 13 }, (_, i) => operator({ id: "o" + i, first_name: "Synthetic " + i })) });
    mocks.areas.mockResolvedValue({ items: [{ id: "a1", wc_id: 1, name: "Only Area", is_district: false }] });
    render(<Page />); await ready();
    expect(screen.getByText(/Mostrati i primi 12 utenti/)).toBeVisible();
    expect(screen.getByText(/Nessun distretto marcato/)).toBeVisible();
  });

  it("opens a deep-linked operator only once and tolerates a save finishing after its dialog is closed", async () => {
    const saving = deferred<ReturnType<typeof operator>>();
    mocks.query = "operatorId=o1"; mocks.save.mockReturnValue(saving.promise);
    mocks.operators.mockResolvedValue({ items: [operator({ id: "other", first_name: "Other" }), operator()] });
    render(<Page />);
    await screen.findByText("KPI operativi");
    fireEvent.click(screen.getByRole("checkbox"));
    fireEvent.change(screen.getByRole("combobox", { name: "Ruolo console" }), { target: { value: "hr_manager" } });
    fireEvent.click(screen.getByRole("button", { name: "Salva permessi console" }));
    expect(await screen.findByText("Salvataggio...")).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "Chiudi", exact: true }));
    await act(async () => saving.resolve(operator({ gate_mobile_console_enabled: true, gate_mobile_console_role: "hr_manager" })));
    expect(screen.queryByText("KPI operativi")).toBeNull();
    expect(mocks.detail).toHaveBeenCalledTimes(1);
    expect(screen.getByText("Console Risorse umane · tutte le aree")).toBeVisible();
  });

  it("keeps sparse detail values and unknown save errors readable", async () => {
    const sparse = operator({ username: null, email: null, tax: null, enabled: false, gaia_user_id: null, gate_mobile_console_enabled: true });
    mocks.detail.mockResolvedValue(detail(sparse, { current_fuel_cards: [], recent_fuel_logs: [], recent_usage_sessions: [],
      stats: { fuel_cards_count: 0, total_liters: "", total_fuel_cost: "invalid", total_km_travelled: null, usage_sessions_count: 0, most_used_vehicle: null, last_used_vehicle_label: null } }));
    mocks.save.mockRejectedValue("unknown");
    render(<Page />); await ready(); await open();
    expect(screen.getByText("Nessuna carta assegnata.")).toBeVisible();
    expect(screen.getByRole("combobox", { name: "Ruolo console" })).toHaveValue("viewer");
    fireEvent.click(screen.getByRole("button", { name: "Salva permessi console" }));
    expect(await screen.findByText("Errore aggiornamento permessi Console GaTe Mobile")).toBeVisible();
  });

  it("hides console permission controls when the session role changes while a detail is open", async () => {
    mocks.detail.mockResolvedValue(detail(operator({ current_fuel_cards: undefined }), { current_fuel_cards: undefined }));
    const view = render(<Page />); await ready(); await open();
    expect(screen.getByText("Nessuna carta assegnata.")).toBeVisible();
    mocks.role = "hr_manager"; view.rerender(<Page />);
    expect(screen.getByText("KPI operativi")).toBeVisible();
    expect(screen.queryByRole("combobox", { name: "Ruolo console" })).toBeNull();
    expect(mocks.save).not.toHaveBeenCalled();
  });
});

describe("existing operator reconciliation controls remain separate from HR role assignment", () => {
  function unlinked() {
    return Array.from({ length: 7 }, (_, i) => ({ ...operator({ id: "unlinked" + i, wc_id: 200 + i, first_name: null, last_name: null,
      username: i === 0 ? "unlinked" : null, email: i ? null : "synthetic@example.test", role: i ? null : "operator", enabled: i === 0 }), suggested_gaia_user: null }));
  }
  it("creates an activation link, copies it, and recovers from an invitation failure", async () => {
    mocks.unlinked.mockResolvedValue({ items: unlinked() });
    const invitation = deferred<{ activation_url_path: string }>();
    mocks.invite.mockRejectedValueOnce(new Error("Unavailable")).mockReturnValueOnce(invitation.promise);
    render(<Page />); await ready();
    expect(await screen.findByText(/Anteprima dei primi 6 su 7/)).toBeVisible();
    fireEvent.click(screen.getAllByRole("button", { name: "Genera link di attivazione" })[0]);
    await waitFor(() => expect(mocks.invite).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(screen.queryByText("Generazione link...")).toBeNull());
    fireEvent.click(screen.getAllByRole("button", { name: "Genera link di attivazione" })[0]);
    expect(await screen.findByText("Generazione link...")).toBeVisible();
    await act(async () => invitation.resolve({ activation_url_path: "/activate/synthetic" }));
    vi.useFakeTimers();
    await act(async () => fireEvent.click(screen.getByRole("button", { name: "Copia", exact: true })));
    expect(mocks.clipboard).toHaveBeenCalledWith(window.location.origin + "/activate/synthetic");
    expect(screen.getByRole("button", { name: "Copiato!" })).toBeVisible();
    await act(async () => vi.advanceTimersByTimeAsync(2000));
    expect(screen.getByRole("button", { name: "Copia", exact: true })).toBeVisible();
  });

  it.each([new Error("Import unavailable"), "unknown"])("preserves import errors and allows a retry (%s)", async reason => {
    mocks.unlinked.mockResolvedValue({ items: unlinked() }); mocks.bulk.mockRejectedValue(reason);
    render(<Page />);
    fireEvent.click(await screen.findByRole("button", { name: "Importa tutti (7)" }));
    expect(await screen.findByText(reason instanceof Error ? reason.message : "Errore durante l'importazione")).toBeVisible();
    expect(screen.getByRole("button", { name: "Importa tutti (7)" })).toBeEnabled();
  });

  it("copies only created synthetic credentials and clears the result on close", async () => {
    mocks.unlinked.mockResolvedValue({ items: unlinked() });
    const imported = deferred<{ created: number; operators: unknown[] }>(); mocks.bulk.mockReturnValue(imported.promise);
    render(<Page />);
    fireEvent.click(await screen.findByRole("button", { name: "Importa tutti (7)" }));
    expect(await screen.findByText("Importazione in corso...")).toBeVisible();
    await act(async () => imported.resolve({ created: 1, operators: [
      { wc_operator_id: "created", full_name: "Synthetic Created", username: "synthetic", temp_password: "test-only", skipped: false },
      { wc_operator_id: "skipped", full_name: "Synthetic Skipped", username: "", temp_password: "", skipped: true },
    ] }));
    expect(await screen.findByText("Synthetic Created")).toBeVisible();
    expect(screen.queryByText("Synthetic Skipped")).toBeNull();
    vi.useFakeTimers();
    await act(async () => fireEvent.click(screen.getByRole("button", { name: "Copia tutto" })));
    expect(mocks.clipboard).toHaveBeenCalledWith("Nome\tUsername\tPassword temporanea\nSynthetic Created\tsynthetic\ttest-only");
    expect(screen.getByRole("button", { name: "Copiato!" })).toBeVisible();
    await act(async () => vi.advanceTimersByTimeAsync(2000));
    expect(screen.getByRole("button", { name: "Copia tutto" })).toBeVisible();
    vi.useRealTimers();
    fireEvent.click(screen.getByRole("button", { name: "Chiudi", exact: true }));
    expect(await screen.findByRole("button", { name: "Importa tutti (7)" })).toBeVisible();
  });

  it.each([
    { result: { linked: 0, skipped: 7 }, message: "Collegati 0, non abbinabili: 7." },
    { failure: new Error("Reconciliation unavailable"), message: "Reconciliation unavailable" },
    { failure: "unknown", message: "Errore" },
  ])("shows the existing reconciliation result without granting console access ($message)", async ({ result, failure, message }) => {
    mocks.unlinked.mockResolvedValue({ items: unlinked() });
    if (failure) mocks.autoLink.mockRejectedValue(failure); else mocks.autoLink.mockResolvedValue(result);
    render(<Page />);
    fireEvent.click(await screen.findByRole("button", { name: "Auto-collega per email / username" }));
    expect(await screen.findByText(message)).toBeVisible();
    expect(mocks.save).not.toHaveBeenCalled();
  });
});
