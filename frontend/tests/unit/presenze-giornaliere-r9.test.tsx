import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";
import PresenzeGiornalierePage from "@/app/presenze/giornaliere/page";
import type { PresenzeDailyRecord } from "@/types/api";

const api = vi.hoisted(() => ({
  getCurrentUser: vi.fn(), getPresenzeAccessContext: vi.fn(),
  listAllPresenzeCollaborators: vi.fn(), listPresenzeDailyMatrixRecords: vi.fn(),
  getPresenzeDailyRecord: vi.fn(), getStoredAccessToken: vi.fn(), updatePresenzeDailyRecord: vi.fn(),
}));
vi.mock("@/lib/auth", () => ({ getStoredAccessToken: api.getStoredAccessToken }));
vi.mock("@/lib/api", () => ({
  ...api, ApiError: class ApiError extends Error {}, getPresenzeSyncJob: vi.fn(),
  refreshPresenzeDailyRecordFromInaz: vi.fn(), updatePresenzeCollaboratorContractProfile: vi.fn(),
}));
vi.mock("@/components/app/protected-page", () => ({ ProtectedPage: ({ children }: { children: React.ReactNode }) => <div>{children}</div> }));
vi.mock("@/components/presenze/inaz-sync-control", () => ({ InazSyncControl: () => null }));
vi.mock("@/components/presenze/whatsapp-reminder-alert", () => ({ WhatsAppReminderAlert: () => null }));
vi.mock("@/components/presenze/shift-worker-badge", () => ({ ShiftWorkerBadge: () => null }));
vi.mock("@/components/presenze/daily-operational-controls", () => ({ DailyOperationalControls: () => null }));

function record(overrides: Partial<PresenzeDailyRecord> = {}): PresenzeDailyRecord {
  return {
    id: "r9-first", collaborator_id: "r9-person", work_date: "2026-05-18", owner_user_id: 12,
    operational_status: "ok", operational_missing_minutes: 0,
    operational_expected_minutes: 420, operational_worked_minutes: 420,
    operational_mpe_minutes: 0, operational_formula_code: null, operational_notes: [],
    ordinary_minutes: 420, teo_minutes: 390, absence_minutes: 0, justified_minutes: 0,
    effective_extra_minutes: 0, effective_straordinario_minutes: 0, effective_mpe_minutes: 0,
    straordinario_minutes: 0, mpe_minutes: 0, km_value: 2, trasferta_minutes: null,
    trasferta_montano: false, reperibilita_unit: "none", reperibilita_quantity: null,
    override_straordinario_minutes: null, override_mpe_minutes: null, manual_note: null,
    detail_requests: [], detail_anomalies: [], detail_punch_rows: [], punches: [],
    detail_day_summary: {}, detail_day_totals: {}, raw_payload_json: {},
    request_description: null, request_status: null, request_authorized_by: null,
    resolved_absence_cause: null, validation_status: "pending", validation_note: null,
    detail_status: "Regolare", stato: "Regolare", special_day: false,
    ...overrides,
  } as PresenzeDailyRecord;
}

function deferred<Value>() {
  let resolve!: (value: Value) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<Value>((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });
  return { promise, resolve, reject };
}

let tokenSeed = 0;
beforeEach(() => {
  vi.resetAllMocks();
  api.getStoredAccessToken.mockReturnValue(`r9-token-${++tokenSeed}`);
  api.getCurrentUser.mockResolvedValue({ id: 12, role: "viewer" });
  api.getPresenzeAccessContext.mockResolvedValue({ can_view_all_data: true, is_supervisor: false });
  api.listAllPresenzeCollaborators.mockResolvedValue([{
    id: "r9-person", name: "R9 COLLABORATORE", employee_code: "R9", is_active: true,
  }]);
});

async function workspace(items: PresenzeDailyRecord[]) {
  api.listPresenzeDailyMatrixRecords.mockResolvedValue({ items, total: items.length, page: 1, page_size: 5000 });
  api.getPresenzeDailyRecord.mockImplementation((_token: string, id: string) => Promise.resolve(items.find((item) => item.id === id)));
  const view = render(<PresenzeGiornalierePage />);
  fireEvent.change(await screen.findByLabelText("Mese operativo"), { target: { value: "2026-05" } });
  await screen.findByRole("button", { name: "R9 COLLABORATORE", exact: true });
  return view;
}

async function collaborator() {
  fireEvent.click(screen.getByRole("button", { name: "R9 COLLABORATORE", exact: true }));
  await screen.findByLabelText("KM 2026-05-18");
}

async function detail(item: PresenzeDailyRecord) {
  const heading = screen.getByRole("button", { name: "R9 COLLABORATORE", exact: true });
  const day = within(heading.closest("tr")!).getAllByRole("button").find((button) => button.title.startsWith(item.work_date));
  expect(day).toBeDefined();
  fireEvent.click(day!);
  await screen.findByText("Rettifiche operative");
}

function blurKm(date = "2026-05-18", value = "7") {
  const input = screen.getByLabelText(`KM ${date}`);
  fireEvent.change(input, { target: { value } });
  fireEvent.blur(input);
  return input;
}

describe("R9 original daily-record mutation lifecycle", () => {
  test("keeps owner editing separate from validation permission and omits validation_note", async () => {
    api.getPresenzeAccessContext.mockResolvedValue({ can_view_all_data: false, is_supervisor: false });
    const item = record();
    await workspace([item]);
    await detail(item);
    expect(screen.queryByRole("button", { name: "Valida giornaliera" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Salva rettifiche" })).toBeEnabled();
    const pending = deferred<PresenzeDailyRecord>();
    api.updatePresenzeDailyRecord.mockReturnValue(pending.promise);
    fireEvent.change(screen.getByLabelText("Nota operativa"), { target: { value: "  owner note  " } });
    fireEvent.click(screen.getByRole("button", { name: "Salva rettifiche" }));
    expect(api.updatePresenzeDailyRecord).toHaveBeenCalledWith(expect.any(String), item.id, {
      km_value: 2, trasferta_minutes: null, trasferta_montano: false,
      reperibilita_unit: "none", reperibilita_quantity: null,
      override_straordinario_minutes: null, override_mpe_minutes: null, manual_note: "owner note",
    });
    expect(screen.getByRole("button", { name: "Salvataggio..." })).toBeDisabled();
    await act(async () => pending.resolve({ ...item, manual_note: "owner note" }));
    expect(await screen.findByText("Giornata 2026-05-18 aggiornata.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Salva rettifiche" })).toBeEnabled();
  });

  test("keeps supervisor validation available while operational editing remains denied", async () => {
    api.getPresenzeAccessContext.mockResolvedValue({ can_view_all_data: false, is_supervisor: true });
    const item = record({ owner_user_id: 77 });
    await workspace([item]);
    await collaborator();
    expect(screen.getByLabelText("KM 2026-05-18")).toBeDisabled();
    expect(screen.getByRole("button", { name: "Rep", exact: true })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Chiudi ✕" }));
    await detail(item);
    expect(screen.getByRole("button", { name: "Salva rettifiche" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Valida giornaliera" })).toBeEnabled();
    api.updatePresenzeDailyRecord.mockResolvedValue({ ...item, validation_status: "validated" });
    fireEvent.change(screen.getByLabelText("Nota validazione"), { target: { value: "  supervisor note  " } });
    fireEvent.click(screen.getByRole("button", { name: "Valida giornaliera" }));
    expect(api.updatePresenzeDailyRecord).toHaveBeenCalledWith(expect.any(String), item.id, { validation_status: "validated", validation_note: "supervisor note" });
    expect(await screen.findByText("Giornata 2026-05-18 validata.")).toBeInTheDocument();
  });

  test("ferie disables reperibilita but keeps KM independently editable", async () => {
    const item = record({ resolved_absence_cause: "ferie", ordinary_minutes: 0, absence_minutes: 420 });
    await workspace([item]);
    await collaborator();
    expect(screen.getByRole("button", { name: "Rep", exact: true })).toBeDisabled();
    expect(screen.getByLabelText("KM 2026-05-18")).toBeEnabled();
    api.updatePresenzeDailyRecord.mockResolvedValue({ ...item, km_value: 7 });
    blurKm();
    await waitFor(() => expect(api.updatePresenzeDailyRecord).toHaveBeenCalledWith(expect.any(String), item.id, { km_value: 7 }));
    expect(api.updatePresenzeDailyRecord).toHaveBeenCalledTimes(1);
  });

  test("editor retains complete conversion payload and trims both notes", async () => {
    const item = record();
    await workspace([item]);
    await detail(item);
    api.updatePresenzeDailyRecord.mockResolvedValue({ ...item, manual_note: "manual" });
    fireEvent.change(screen.getByLabelText("Straordinario override"), { target: { value: "01:15" } });
    fireEvent.change(screen.getByLabelText("Maggior presenza override"), { target: { value: "-4" } });
    fireEvent.change(screen.getByLabelText("Nota operativa"), { target: { value: " manual " } });
    fireEvent.change(screen.getByLabelText("Nota validazione"), { target: { value: " validation " } });
    fireEvent.click(screen.getByRole("button", { name: "Salva rettifiche" }));
    expect(api.updatePresenzeDailyRecord).toHaveBeenCalledWith(expect.any(String), item.id, {
      km_value: 2, trasferta_minutes: null, trasferta_montano: false, reperibilita_unit: "none",
      reperibilita_quantity: null, override_straordinario_minutes: 75, override_mpe_minutes: 0,
      manual_note: "manual", validation_note: "validation",
    });
    expect(await screen.findByText("Giornata 2026-05-18 aggiornata.")).toBeInTheDocument();
  });

  test.each(["km", "reperibilita", "editor", "validation"] as const)("captures %s invocation token and catches a synchronous API failure", async (action) => {
    const item = record();
    await workspace([item]);
    if (action === "km" || action === "reperibilita") await collaborator();
    else await detail(item);
    api.getStoredAccessToken.mockReturnValue("r9-invocation-token");
    api.updatePresenzeDailyRecord.mockImplementation(() => { throw new Error("synchronous update failure"); });
    if (action === "km") blurKm();
    else fireEvent.click(screen.getByRole("button", { name: action === "reperibilita" ? "Rep" : action === "editor" ? "Salva rettifiche" : "Valida giornaliera", exact: true }));
    expect(api.updatePresenzeDailyRecord.mock.calls[0][0]).toBe("r9-invocation-token");
    expect(await screen.findByText("synchronous update failure")).toBeInTheDocument();
    if (action === "km" || action === "reperibilita") expect(screen.getByLabelText("KM 2026-05-18")).toBeEnabled();
    else expect(screen.getByRole("button", { name: "Salva rettifiche" })).toBeEnabled();
  });

  test.each(["km", "reperibilita", "editor", "validation"] as const)("does not reset saving state or issue %s after token expiry", async (action) => {
    const item = record();
    await workspace([item]);
    if (action === "km" || action === "reperibilita") await collaborator();
    else await detail(item);
    api.getStoredAccessToken.mockReturnValue(null);
    if (action === "km") blurKm();
    else fireEvent.click(screen.getByRole("button", { name: action === "reperibilita" ? "Rep" : action === "editor" ? "Salva rettifiche" : "Valida giornaliera", exact: true }));
    expect(api.updatePresenzeDailyRecord).not.toHaveBeenCalled();
    expect(screen.queryByText("Salvataggio...")).not.toBeInTheDocument();
  });

  test("inline persistence retains existing success while editor persistence clears it before waiting", async () => {
    const item = record();
    await workspace([item]);
    await detail(item);
    api.updatePresenzeDailyRecord.mockResolvedValue({ ...item, manual_note: "saved" });
    fireEvent.click(screen.getByRole("button", { name: "Salva rettifiche" }));
    await screen.findByText("Giornata 2026-05-18 aggiornata.");
    fireEvent.click(screen.getByRole("button", { name: "Chiudi ✕" }));
    await collaborator();
    const pending = deferred<PresenzeDailyRecord>();
    api.updatePresenzeDailyRecord.mockReturnValue(pending.promise);
    blurKm();
    expect(screen.getByText("Giornata 2026-05-18 aggiornata.")).toBeInTheDocument();
    expect(screen.getByLabelText("KM 2026-05-18")).toBeDisabled();
    await act(async () => pending.resolve({ ...item, km_value: 7 }));
    fireEvent.click(screen.getByRole("button", { name: "Chiudi ✕" }));
    await detail(item);
    const second = deferred<PresenzeDailyRecord>();
    api.updatePresenzeDailyRecord.mockReturnValue(second.promise);
    fireEvent.click(screen.getByRole("button", { name: "Salva rettifiche" }));
    expect(screen.queryByText("Giornata 2026-05-18 aggiornata.")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Salvataggio..." })).toBeDisabled();
    await act(async () => second.reject("not an Error"));
    expect(await screen.findByText("Errore salvataggio giornaliera")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Salva rettifiche" })).toBeEnabled();
  });

  test.each(["first", "second"] as const)("preserves scalar saving flag and independent records when %s inline request finishes first", async (firstToFinish) => {
    const first = record();
    const second = record({ id: "r9-second", work_date: "2026-05-19", km_value: 3 });
    await workspace([first, second]);
    await collaborator();
    const firstPending = deferred<PresenzeDailyRecord>();
    const secondPending = deferred<PresenzeDailyRecord>();
    api.updatePresenzeDailyRecord.mockReturnValueOnce(firstPending.promise).mockReturnValueOnce(secondPending.promise);
    blurKm(first.work_date, "11");
    expect(screen.getByLabelText(`KM ${first.work_date}`)).toBeDisabled();
    blurKm(second.work_date, "22");
    expect(screen.getByLabelText(`KM ${first.work_date}`)).toBeEnabled();
    expect(screen.getByLabelText(`KM ${second.work_date}`)).toBeDisabled();
    const winner = firstToFinish === "first" ? firstPending : secondPending;
    const loser = firstToFinish === "first" ? secondPending : firstPending;
    const winnerRecord = firstToFinish === "first" ? first : second;
    const loserRecord = firstToFinish === "first" ? second : first;
    await act(async () => winner.resolve({ ...winnerRecord, km_value: firstToFinish === "first" ? 11 : 22 }));
    expect(screen.getByLabelText(`KM ${first.work_date}`)).toBeEnabled();
    expect(screen.getByLabelText(`KM ${second.work_date}`)).toBeEnabled();
    await act(async () => loser.resolve({ ...loserRecord, km_value: firstToFinish === "first" ? 22 : 11 }));
    fireEvent.click(screen.getByRole("button", { name: "Chiudi ✕" }));
    await collaborator();
    expect(screen.getByLabelText(`KM ${first.work_date}`)).toHaveValue("11");
    expect(screen.getByLabelText(`KM ${second.work_date}`)).toHaveValue("22");
    expect(api.updatePresenzeDailyRecord.mock.calls.map((call) => call[1])).toEqual([first.id, second.id]);
  });

  test("late inline failure retains successful second update without clearing its result", async () => {
    const first = record();
    const second = record({ id: "r9-second", work_date: "2026-05-19" });
    await workspace([first, second]);
    await collaborator();
    const pending = deferred<PresenzeDailyRecord>();
    api.updatePresenzeDailyRecord.mockReturnValueOnce(pending.promise).mockResolvedValueOnce({ ...second, km_value: 9 });
    blurKm(first.work_date, "8");
    blurKm(second.work_date, "9");
    await waitFor(() => expect(screen.getByLabelText(`KM ${second.work_date}`)).toBeEnabled());
    await act(async () => pending.reject(new Error("first failed late")));
    expect(await screen.findByText("first failed late")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Chiudi ✕" }));
    await detail(second);
    expect(screen.getByLabelText("Chilometri auto")).toHaveValue("9");
  });

  test("editor response replaces original tuple by new ID without overwriting newly selected detail", async () => {
    const first = record();
    const second = record({ id: "r9-second", work_date: "2026-05-19", manual_note: "second original" });
    await workspace([first, second]);
    await detail(first);
    const pending = deferred<PresenzeDailyRecord>();
    api.updatePresenzeDailyRecord.mockReturnValue(pending.promise);
    fireEvent.change(screen.getByLabelText("Nota operativa"), { target: { value: "first saved" } });
    fireEvent.click(screen.getByRole("button", { name: "Salva rettifiche" }));
    fireEvent.click(screen.getByRole("button", { name: "Chiudi ✕" }));
    await detail(second);
    expect(screen.getByLabelText("Nota operativa")).toHaveValue("second original");
    await act(async () => pending.resolve({ ...first, id: "r9-replaced", manual_note: "first saved", km_value: 31 }));
    expect(await screen.findByText("Giornata 2026-05-18 aggiornata.")).toBeInTheDocument();
    expect(screen.getByLabelText("Nota operativa")).toHaveValue("second original");
    expect(screen.getByRole("button", { name: "Salva rettifiche" })).toBeEnabled();
    fireEvent.click(screen.getByRole("button", { name: "Chiudi ✕" }));
    await detail(first);
    expect(api.getPresenzeDailyRecord).not.toHaveBeenCalledWith(expect.any(String), "r9-replaced");
    expect(screen.getByLabelText("Nota operativa")).toHaveValue("first saved");
    expect(screen.getByLabelText("Chilometri auto")).toHaveValue("31");
  });

  test.each(["2026-05-18", "2026-06-18"])("evicts only captured token and response month for %s after an unmount", async (responseDate) => {
    const item = record();
    const view = await workspace([item]);
    const originalToken = api.getStoredAccessToken.mock.results[0].value;
    await collaborator();
    const pending = deferred<PresenzeDailyRecord>();
    api.updatePresenzeDailyRecord.mockReturnValue(pending.promise);
    blurKm();
    view.unmount();
    api.getStoredAccessToken.mockReturnValue("r9-new-current-token");
    await act(async () => pending.resolve({ ...item, work_date: responseDate, km_value: 7 }));
    api.getStoredAccessToken.mockReturnValue(originalToken);
    api.listPresenzeDailyMatrixRecords.mockClear();
    const remounted = await workspace([item]);
    expect(api.listPresenzeDailyMatrixRecords.mock.calls.filter((call) => call[1].dateFrom === "2026-05-01")).toHaveLength(responseDate.startsWith("2026-05") ? 1 : 0);
    remounted.unmount();
  });
});
