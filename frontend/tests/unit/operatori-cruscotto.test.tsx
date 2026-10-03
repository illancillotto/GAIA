import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";
import Page from "@/app/gaia/users/operatori-cruscotto/page";

const mocks = vi.hoisted(() => ({
  token: vi.fn(), current: vi.fn(), users: vi.fn(), collaborators: vi.fn(), devices: vi.fn(),
  summary: vi.fn(), records: vi.fn(), operators: vi.fn(), detail: vi.fn(), assets: vi.fn(),
}));
vi.mock("@/components/app/protected-page", () => ({ ProtectedPage: ({ children }: { children: React.ReactNode }) => <main>{children}</main> }));
vi.mock("@/lib/auth", () => ({ getStoredAccessToken: mocks.token }));
vi.mock("@/lib/api", () => ({
  getCurrentUser: mocks.current, listAllApplicationUsers: mocks.users,
  listAllPresenzeCollaborators: mocks.collaborators, getNetworkDevices: mocks.devices,
  getPresenzeCollaboratorSummary: mocks.summary, listPresenzeDailyRecords: mocks.records,
}));
vi.mock("@/features/operazioni/api/client", () => ({ getOperators: mocks.operators, getOperatorDetail: mocks.detail }));
vi.mock("@/features/dotazioni/api", () => ({ dotazioniApi: { operatorAssets: mocks.assets } }));

function operator(values: Record<string, unknown> = {}) {
  return { id: "wc-1", wc_id: 100, gaia_user_id: 7, first_name: "Mario", last_name: "Rossi",
    username: "mrossi", email: "mario@example.local", role: "operator", tax: "SYNTHETIC",
    enabled: true, current_fuel_cards: [{ id: "card", codice: "CARD", pan: "123" }], ...values };
}
function detail(selected = operator(), values: Record<string, unknown> = {}) {
  return { operator: selected, stats: { usage_sessions_count: 1, fuel_logs_count: 1,
    fuel_cards_count: 1, total_km_travelled: "12.5", total_liters: 10 },
    current_fuel_cards: [{ id: "card", codice: "CARD", pan: "123" }],
    recent_usage_sessions: [{ id: "session", vehicle_label: "Mezzo sintetico", started_at: "2026-10-01T07:00:00Z", km_travelled: "12.5", status: "closed" }],
    recent_fuel_logs: [{ id: "fuel", vehicle_label: "Mezzo sintetico", fueled_at: "2026-10-01T09:00:00Z", liters: "10", station_name: "Stazione" }], ...values };
}
function device(values: Record<string, unknown> = {}) {
  return { id: 1, assigned_user_id: 7, resolved_label: "Telefono tecnico", ip_address: "10.0.0.1",
    operating_system: "Android", device_type: "phone", traffic_summary: {
      total_events: 3, blocked_events: 1, allowed_events: 2, bytes_in: 1024, bytes_out: 1024,
      top_peers: [{ label: "Peer", ip_address: "10.0.0.2", events_count: 2, bytes_in: 512, bytes_out: 512 }],
      recent_events: [{ observed_at: "2026-10-01T11:00:00Z", peer_label: "Peer" }, { observed_at: "2026-10-01T10:00:00Z", peer_label: "Altro" }],
    }, ...values };
}

beforeEach(() => {
  vi.resetAllMocks();
  mocks.token.mockReturnValue("token");
  mocks.current.mockResolvedValue({ role: "admin", enabled_modules: [] });
  mocks.operators.mockResolvedValue({ items: [operator()], total: 1 });
  mocks.detail.mockImplementation(async () => detail());
  mocks.users.mockResolvedValue([{ id: 7, username: "mrossi", full_name: "Mario Rossi", email: "mario@example.local", is_active: true,
    enabled_modules: ["accessi"], last_login_at: "2026-10-01T08:00:00Z", last_login_ip: "127.0.0.1", login_count: 2 }]);
  mocks.collaborators.mockResolvedValue([{ id: "inaz-1", application_user_id: 7, name: "Mario Rossi", employee_code: "INAZ-99", last_seen_at: "2026-10-01T09:00:00Z" }]);
  mocks.devices.mockResolvedValue({ items: [device()], total: 1 });
  mocks.summary.mockResolvedValue({ items: [{ id: "saldo", description: "Ferie", valid_from: "2026-01-01", valid_to: "2026-12-31", saldo_minutes: 60, fruito_minutes: -30 }] });
  mocks.records.mockResolvedValue({ items: [{ id: "day", detail_anomalies: ["Anomalia"], detail_error: null, detail_status: null, stato: null }], total: 1 });
  mocks.assets.mockResolvedValue({ items: [], total: 0 });
});

async function ready() {
  await screen.findByText("Timeline unificata");
  await waitFor(() => expect(screen.queryByText("Caricamento scheda operatore.")).not.toBeInTheDocument());
}

describe("operator dashboard characterization", () => {
  test("preserves canonical mappings, presence, network and vehicle summaries", async () => {
    render(<Page />);
    await ready();
    expect(mocks.summary).toHaveBeenCalledWith("token", "inaz-1", expect.any(String), expect.any(String));
    expect(screen.getByText("Ferie")).toBeInTheDocument();
    expect(screen.getByText("Saldo 1h 00m")).toBeInTheDocument();
    expect(screen.getByText("Fruito -0h 30m")).toBeInTheDocument();
    expect(screen.getAllByText("Mezzo sintetico").length).toBeGreaterThan(0);
    expect(screen.getByText("Telefono tecnico")).toBeInTheDocument();
    expect(await screen.findByText("0 dotazioni")).toBeInTheDocument();
    expect(mocks.assets).toHaveBeenCalledWith(7);
    expect(screen.getByRole("link", { name: "Apri dettaglio giornaliere" })).toHaveAttribute("href", "/presenze/collaboratori/inaz-1");
    fireEvent.change(screen.getByPlaceholderText("Cerca nome, username, matricola, CF"), { target: { value: "nessuno" } });
    expect(await screen.findByText("Nessun operatore trovato")).toBeInTheDocument();
    fireEvent.change(screen.getByPlaceholderText("Cerca nome, username, matricola, CF"), { target: { value: "INAZ-99" } });
    await ready();
    for (const label of ["Con rete", "Con giornaliere", "Con anomalie", "Tutti"]) fireEvent.click(screen.getByRole("button", { name: label, exact: true }));
    await ready();
  });

  test("uses only canonical GAIA identity and isolates Dotazioni permission failures", async () => {
    mocks.assets.mockRejectedValue(new Error("Permesso Dotazioni insufficiente"));
    render(<Page />);
    await ready();
    expect(await screen.findByRole("alert")).toHaveTextContent("Permesso Dotazioni insufficiente");
    expect(mocks.assets).toHaveBeenCalledWith(7);
    expect(mocks.assets).not.toHaveBeenCalledWith(100);
    expect(screen.getByText("Telefono tecnico")).toBeInTheDocument();
  });

  test("switches custody by the detail canonical identity and discards stale responses", async () => {
    const another = operator({ id: "wc-2", wc_id: 200, gaia_user_id: 8, first_name: "Antonio", last_name: "Piras" });
    mocks.operators.mockResolvedValue({ items: [operator(), another], total: 2 });
    mocks.detail.mockImplementation(async (identifier) => detail(identifier === "wc-2" ? another : operator()));
    let resolveOldAssets!: (value: unknown) => void;
    const heldAsset = { id: "asset-2", asset_code: "RAD-02", name: "Radio Antonio", asset_type: "radio",
      assigned_org_unit_name: "Nord", is_active: true, effective_status: "in_use",
      current_custody: { holder_name: "Antonio Piras", taken_at: "2026-10-01T07:15:00Z" } };
    mocks.assets.mockImplementation((identifier) => identifier === 7
      ? new Promise((resolve) => { resolveOldAssets = resolve; })
      : Promise.resolve({ items: [heldAsset], total: 1 }));
    render(<Page />);
    await waitFor(() => expect(mocks.assets).toHaveBeenCalledWith(7));
    fireEvent.click(screen.getByRole("button", { name: /Antonio Piras/ }));
    await screen.findByRole("link", { name: "RAD-02 · Radio Antonio" });
    expect(mocks.assets).toHaveBeenCalledWith(8);
    expect(mocks.assets.mock.calls.filter(([identifier]) => identifier === 7)).toHaveLength(1);
    await act(async () => resolveOldAssets({ items: [{ ...heldAsset, asset_code: "OLD", name: "Vecchio bene" }], total: 1 }));
    expect(screen.queryByText("OLD · Vecchio bene")).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "RAD-02 · Radio Antonio" })).toHaveAttribute("href", "/dotazioni/assets/asset-2");
  });

  test("shows empty domains and healthy operators with search and anomaly filters", async () => {
    const valid = operator({ first_name: null, last_name: null, username: "solo", email: null, role: null });
    const aliases = [valid, operator({ id: "alias", gaia_user_id: null, first_name: null, last_name: null, username: null, email: "alias@example.local", current_fuel_cards: undefined }),
      operator({ id: "fallback", gaia_user_id: null, first_name: null, last_name: null, username: null, email: null }),
      operator({ id: "spaces", gaia_user_id: null, first_name: null, last_name: null, username: " " })];
    mocks.operators.mockResolvedValue({ items: aliases, total: aliases.length });
    mocks.devices.mockResolvedValue({ items: [device({ traffic_summary: { total_events: 0, blocked_events: 0, allowed_events: 0, bytes_in: 0, bytes_out: 0, top_peers: [], recent_events: [] } })], total: 1 });
    mocks.users.mockResolvedValue([{ id: 7, username: "solo", email: null, full_name: null, enabled_modules: [], is_active: true }]);
    mocks.detail.mockImplementation(async (identifier) => detail(aliases.find((item) => item.id === identifier), { current_fuel_cards: [], recent_usage_sessions: [], recent_fuel_logs: [] }));
    mocks.summary.mockResolvedValue({ items: [] });
    render(<Page />);
    await ready();
    expect(screen.getByText("Nessun riepilogo giornaliere disponibile per il mese corrente.")).toBeInTheDocument();
    expect(screen.getByText("Nessun peer rilevante disponibile.")).toBeInTheDocument();
    expect(screen.getByText("0 B")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Con anomalie", exact: true }));
    await waitFor(() => expect(screen.queryByRole("button", { name: /solo/ })).not.toBeInTheDocument());
  });

  test("paginates daily records and aggregates duplicate peers", async () => {
    mocks.records.mockResolvedValueOnce({ items: [{ detail_anomalies: [], detail_error: null, detail_status: null, stato: null }], total: 2 })
      .mockResolvedValue({ items: [], total: 2 });
    const traffic = { total_events: 1, blocked_events: 0, allowed_events: 1, bytes_in: 100, bytes_out: 0,
      top_peers: [{ label: "", ip_address: "10.0.0.9", events_count: 1, bytes_in: 100, bytes_out: 0 },
        { label: "Autodoc", ip_address: "10.0.0.8", events_count: 2, bytes_in: 0, bytes_out: 0 }], recent_events: [] };
    mocks.devices.mockResolvedValue({ items: [device({ traffic_summary: traffic }), device({ id: 2, operating_system: null, device_type: "tablet", traffic_summary: traffic })], total: 2 });
    render(<Page />);
    await ready();
    expect(mocks.records).toHaveBeenCalledWith("token", expect.objectContaining({ page: 2 }));
    expect(screen.getByText("10.0.0.9")).toBeInTheDocument();
    expect(screen.getAllByText("200 B")).toHaveLength(2);
  });

  test("ignores base requests resolved after unmount and their failures", async () => {
    let resolveUser!: (value: unknown) => void;
    mocks.current.mockImplementation(() => new Promise((resolve) => { resolveUser = resolve; }));
    const view = render(<Page />);
    await waitFor(() => expect(mocks.current).toHaveBeenCalled());
    view.unmount();
    await act(async () => resolveUser({ role: "admin", enabled_modules: [] }));
    expect(mocks.operators).not.toHaveBeenCalled();
  });

  test("ignores base catalogs resolved after unmount", async () => {
    let resolveOperators!: (value: unknown) => void;
    mocks.operators.mockImplementation(() => new Promise((resolve) => { resolveOperators = resolve; }));
    const view = render(<Page />);
    await waitFor(() => expect(mocks.operators).toHaveBeenCalled());
    view.unmount();
    await act(async () => resolveOperators({ items: [], total: 0 }));
  });

  test("accepts an operator catalog without an optional total", async () => {
    mocks.operators.mockResolvedValue({ items: [operator()] });
    render(<Page />);
    await ready();
    expect(mocks.operators).toHaveBeenCalledTimes(1);
  });

  test.each(["base", "detail"])("ignores cancelled %s failures", async (phase) => {
    let rejectRequest!: (reason: Error) => void;
    const request = new Promise((_, reject) => { rejectRequest = reject; });
    const selectedMock = phase === "base" ? mocks.current : mocks.detail;
    selectedMock.mockReturnValue(request);
    const view = render(<Page />);
    await waitFor(() => expect(selectedMock).toHaveBeenCalled());
    view.unmount();
    await act(async () => rejectRequest(new Error("Cancelled failure")));
  });

  test("ignores presence responses after selecting another operator", async () => {
    let resolveSummary!: (value: unknown) => void;
    mocks.summary.mockImplementation(() => new Promise((resolve) => { resolveSummary = resolve; }));
    const view = render(<Page />);
    await waitFor(() => expect(mocks.summary).toHaveBeenCalled());
    view.unmount();
    await act(async () => resolveSummary({ items: [] }));
  });

  test("does not infer identity from names, email or equal namespace identifiers", async () => {
    const unlinked = operator({ gaia_user_id: null, enabled: false });
    mocks.operators.mockResolvedValue({ items: [unlinked], total: 1 });
    mocks.detail.mockResolvedValue(detail(unlinked, { current_fuel_cards: [], recent_usage_sessions: [], recent_fuel_logs: [] }));
    render(<Page />);
    await ready();
    expect(screen.getByText("Nessun collaboratore giornaliere collegato a questo operatore.")).toBeInTheDocument();
    expect(screen.getByText("Nessun dispositivo rete assegnato a questo operatore.")).toBeInTheDocument();
    expect(screen.getByText("Nessuna timeline disponibile per questo operatore.")).toBeInTheDocument();
    expect(mocks.summary).not.toHaveBeenCalled();
    expect(mocks.assets).not.toHaveBeenCalled();
    for (const label of ["Con rete", "Con giornaliere"]) {
      fireEvent.click(screen.getByRole("button", { name: label }));
      await screen.findByText("Nessun operatore trovato");
    }
  });

  test.each([{ modules: [] }, { modules: ["accessi"] }, { modules: ["presenze"] }, { modules: ["rete"] }])("does not fetch inaccessible domains: $modules", async ({ modules }) => {
    mocks.current.mockResolvedValue({ role: "viewer", enabled_modules: modules });
    render(<Page />);
    await ready();
    expect(mocks.users.mock.calls.length > 0).toBe(modules.includes("accessi"));
    expect(mocks.collaborators.mock.calls.length > 0).toBe(modules.includes("presenze"));
    expect(mocks.devices.mock.calls.length > 0).toBe(modules.includes("rete"));
  });

  test("handles missing session and empty operator lists", async () => {
    mocks.token.mockReturnValue(null);
    const view = render(<Page />);
    expect(screen.getByText("Sessione non disponibile.")).toBeInTheDocument();
    expect(mocks.current).not.toHaveBeenCalled();
    view.unmount();
    mocks.token.mockReturnValue("token");
    mocks.operators.mockResolvedValue({});
    render(<Page />);
    await screen.findByText("Nessun operatore trovato");
  });

  test.each([new Error("Sessione fallita"), "failed"])("reports base errors without crashing", async (failure) => {
    mocks.current.mockRejectedValue(failure);
    render(<Page />);
    await screen.findByText(failure instanceof Error ? failure.message : "Errore caricamento cruscotto operatori");
  });

  test.each([new Error("Dettaglio fallito"), "failed"])("reports detail errors separately", async (failure) => {
    mocks.detail.mockRejectedValue(failure);
    render(<Page />);
    await screen.findByText(failure instanceof Error ? failure.message : "Errore caricamento dettaglio operatore");
    expect(screen.queryByText("Timeline unificata")).not.toBeInTheDocument();
  });

  test("paginates catalogs and presence records without skipping operators", async () => {
    mocks.operators.mockResolvedValueOnce({ items: [operator()], total: 2 }).mockResolvedValue({ items: [], total: 2 });
    mocks.devices.mockResolvedValueOnce({ items: [device()], total: 2 }).mockResolvedValue({ items: [], total: 2 });
    mocks.records.mockResolvedValueOnce({ items: [], total: 1 });
    render(<Page />);
    await ready();
    expect(mocks.operators).toHaveBeenCalledWith({ page: "2", page_size: "100" });
    expect(mocks.devices).toHaveBeenCalledWith("token", { page: 2, pageSize: 100 });
  });

  test("does not apply a late detail response to another selected operator", async () => {
    const another = operator({ id: "wc-2", gaia_user_id: 8, first_name: "Antonio", last_name: "Piras" });
    mocks.operators.mockResolvedValue({ items: [operator(), another], total: 2 });
    let resolveDetail!: (value: unknown) => void;
    mocks.detail.mockImplementation((identifier) => identifier === "wc-2"
      ? new Promise((resolve) => { resolveDetail = resolve; }) : Promise.resolve(detail()));
    render(<Page />);
    await ready();
    fireEvent.click(screen.getByRole("button", { name: /Antonio Piras/ }));
    await waitFor(() => expect(mocks.detail).toHaveBeenCalledWith("wc-2"));
    fireEvent.click(screen.getByRole("button", { name: /Mario Rossi/ }));
    await ready();
    await act(async () => resolveDetail(detail(another)));
    expect(screen.getByRole("heading", { name: "Mario Rossi" })).toBeInTheDocument();
  });

  test("aggregates peers, tolerates sparse summaries and invalid dates/numbers", async () => {
    mocks.users.mockResolvedValue([{ id: 7, username: "mrossi", is_active: false, enabled_modules: [], last_login_at: "invalid", last_login_ip: null }]);
    mocks.collaborators.mockResolvedValue([{ id: "inaz-1", application_user_id: 7, name: "Mario", employee_code: "", last_seen_at: null }, { id: "unmapped", application_user_id: null }]);
    mocks.devices.mockResolvedValue({ items: [device(), device({ id: 2, operating_system: null, device_type: null, traffic_summary: null }), device({ id: 3, assigned_user_id: null })], total: 3 });
    mocks.summary.mockResolvedValue({ items: [{ id: "saldo", description: "Saldo incompleto", valid_from: "invalid", valid_to: null, saldo_minutes: null, fruito_minutes: undefined }, { id: "period", description: "Periodo", valid_from: null, saldo_minutes: 0, fruito_minutes: 0 }] });
    mocks.records.mockResolvedValue({ items: [
      { detail_anomalies: [], detail_error: "error" }, { detail_anomalies: [], detail_status: "anomalia" },
      { detail_anomalies: [], detail_status: "ok", stato: "anomalo" }, { detail_anomalies: [], detail_status: null, stato: null },
    ], total: 4 });
    mocks.detail.mockResolvedValue(detail(operator(), { stats: { total_km_travelled: "invalid", total_liters: "" },
      current_fuel_cards: [{ id: "card", codice: null, pan: "PAN" }],
      recent_usage_sessions: [{ id: "s", vehicle_label: null, started_at: null, km_travelled: undefined, status: "open" }],
      recent_fuel_logs: [{ id: "f", fueled_at: "invalid", vehicle_label: null, liters: null, station_name: null }] }));
    render(<Page />);
    await ready();
    expect(screen.getByText("PAN")).toBeInTheDocument();
    expect(screen.getByText("Saldo incompleto")).toBeInTheDocument();
    expect(screen.getByText("10.0.0.1 · Tipo non rilevato")).toBeInTheDocument();
  });
});
