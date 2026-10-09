import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";
import PresenzeGiornalierePage from "@/app/presenze/giornaliere/page";
import { dailyCellIndicators, kmInputPresentation } from "@/app/presenze/giornaliere/daily-cell-model";
import type { PresenzeDailyRecord } from "@/types/api";

const api = vi.hoisted(() => ({
  getCurrentUser: vi.fn(),
  getPresenzeAccessContext: vi.fn(),
  listAllPresenzeCollaborators: vi.fn(),
  listPresenzeDailyMatrixRecords: vi.fn(),
  getPresenzeDailyRecord: vi.fn(),
  updatePresenzeDailyRecord: vi.fn(),
  getStoredAccessToken: vi.fn(),
}));

vi.mock("@/lib/auth", () => ({ getStoredAccessToken: api.getStoredAccessToken }));
vi.mock("@/lib/api", () => ({
  ...api,
  ApiError: class ApiError extends Error {},
  getPresenzeSyncJob: vi.fn(),
  refreshPresenzeDailyRecordFromInaz: vi.fn(),
  updatePresenzeCollaboratorContractProfile: vi.fn(),
}));
vi.mock("@/components/app/protected-page", () => ({ ProtectedPage: ({ children }: { children: React.ReactNode }) => <div>{children}</div> }));
vi.mock("@/components/presenze/inaz-sync-control", () => ({ InazSyncControl: () => null }));
vi.mock("@/components/presenze/whatsapp-reminder-alert", () => ({ WhatsAppReminderAlert: () => null }));
vi.mock("@/components/presenze/whatsapp-manual-message", () => ({ WhatsAppManualMessage: () => null }));
vi.mock("@/components/presenze/shift-worker-badge", () => ({ ShiftWorkerBadge: () => null }));

function record(overrides: Partial<PresenzeDailyRecord> = {}): PresenzeDailyRecord {
  return {
    id: "r6-day", collaborator_id: "r6-person", owner_user_id: 77,
    work_date: "2026-05-18", operational_status: "ok", operational_formula_code: null,
    operational_expected_minutes: 420, operational_worked_minutes: 420, operational_missing_minutes: 0,
    operational_mpe_minutes: 0, operational_notes: [], ordinary_minutes: 420, teo_minutes: 420,
    absence_minutes: 0, justified_minutes: 0, straordinario_minutes: 0, mpe_minutes: 0,
    effective_straordinario_minutes: 0, effective_mpe_minutes: 0, effective_extra_minutes: 0,
    km_value: null, trasferta_minutes: null, trasferta_montano: false,
    reperibilita_unit: "none", reperibilita_quantity: null, resolved_absence_cause: null,
    request_status: null, request_description: null, request_authorized_by: null,
    detail_requests: [], detail_anomalies: [], detail_punch_rows: [], punches: [],
    detail_day_summary: {}, detail_day_totals: {},
    detail_status: "Giornata regolare", stato: "Giornata regolare", special_day: false,
    validation_status: "pending", raw_payload_json: {},
    ...overrides,
  } as PresenzeDailyRecord;
}

let token = 0;
beforeEach(() => {
  vi.clearAllMocks();
  api.getStoredAccessToken.mockReturnValue(`r6-token-${++token}`);
  api.getCurrentUser.mockResolvedValue({ id: 12, role: "viewer" });
  api.getPresenzeAccessContext.mockResolvedValue({ can_view_all_data: true, is_supervisor: false });
  api.listAllPresenzeCollaborators.mockResolvedValue([{
    id: "r6-person", name: "R6 COLLABORATORE", employee_code: "R6", owner_user_id: 77,
    contract_kind: "operaio", operai_group: "agrario", is_active: true,
  }]);
});

describe("R6 operational display projections", () => {
  test("keeps frozen source data intact, priority and fresh arrays without leaking absent icons", () => {
    const item = Object.freeze(record({ km_value: 0, detail_requests: [{ Descrizione: "Richiesta" }], trasferta_montano: true }));
    Object.freeze(item.detail_requests);
    const first = dailyCellIndicators(item, NaN, " ");
    expect(first.map(({ label }) => label)).toEqual(["🚗", "T", "✅"]);
    const second = dailyCellIndicators(item, -1, null);
    expect(second.map(({ label }) => label)).toEqual(["🚗", "T", "✉"]);
    expect(second).not.toBe(first);
    first.pop();
    expect(second.map(({ label }) => label)).toEqual(["🚗", "T", "✉"]);
    expect(item.km_value).toBe(0);
    expect(item.detail_requests).toEqual([{ Descrizione: "Richiesta" }]);
  });

  test.each([
    { value: null, draft: undefined, expected: "" },
    { value: 0, draft: undefined, expected: "0" },
    { value: -2, draft: undefined, expected: "-2" },
    { value: NaN, draft: undefined, expected: "NaN" },
    { value: 12, draft: "", expected: "" },
    { value: null, draft: "0", expected: "0" },
  ])("keeps draft and nullish formatter $value/$draft", ({ value, draft, expected }) => {
    expect(kmInputPresentation(value, draft, true, false)).toEqual({ defaultValue: expected, disabled: false });
  });

  test.each([[true, true], [false, true], [false, false]] as const)("preserves canEdit=%s/saving=%s disabled OR", (canEdit, saving) => {
    expect(kmInputPresentation(0, undefined, canEdit, saving)).toEqual({ defaultValue: "0", disabled: true });
  });
});

async function openMatrix(item: PresenzeDailyRecord): Promise<HTMLButtonElement> {
  api.listPresenzeDailyMatrixRecords.mockResolvedValue({ items: [item], total: 1, page: 1, page_size: 5000 });
  api.getPresenzeDailyRecord.mockResolvedValue(item);
  render(<PresenzeGiornalierePage />);
  fireEvent.change(await screen.findByLabelText("Mese operativo"), { target: { value: "2026-05" } });
  const collaborator = await screen.findByRole("button", { name: "R6 COLLABORATORE", exact: true });
  const row = collaborator.closest("tr")!;
  return within(row).getAllByRole("button")[1] as HTMLButtonElement;
}

describe("R6 daily operational presentation characterization", () => {
  test("keeps icon order, exact tones, authorized priority and selection flow", async () => {
    const button = await openMatrix(record({
      effective_extra_minutes: 30, km_value: 0, trasferta_minutes: null, trasferta_montano: true,
      reperibilita_unit: "hours", reperibilita_quantity: 0,
      request_status: "acc", request_description: "Timbratura E", request_authorized_by: " Revisore ",
      detail_requests: [{ Descrizione: "Altra richiesta" }],
    }));
    const icons = button.lastElementChild!;
    expect(Array.from(icons.children).map((node) => [node.textContent, node.className])).toEqual([
      ["▲", "text-emerald-600"], ["🚗", ""], ["T", "text-sky-600"],
      ["R", "text-amber-700"], ["✅", "text-emerald-700"],
    ]);
    expect(button).toHaveAttribute("title", "2026-05-18 · GAIA: giornata quadrata · Timbratura di entrata autorizzata da Revisore");
    fireEvent.click(button);
    await waitFor(() => expect(button).toHaveClass("outline-slate-950"));
    expect(api.getPresenzeDailyRecord).toHaveBeenCalledWith(expect.any(String), "r6-day");
  });

  test.each([
    { label: "null", extra: 0, km: null, travel: null, unit: "none", expected: [] },
    { label: "negative", extra: -1, km: -1, travel: -1, unit: "none", expected: ["🚗"] },
    { label: "NaN", extra: NaN, km: NaN, travel: NaN, unit: "shifts", expected: ["🚗", "R"] },
    { label: "positive", extra: 1, km: 0, travel: 1, unit: "days", expected: ["▲", "🚗", "T", "R"] },
  ] as const)("retains $label arithmetic and nullish icon semantics", async ({ extra, km, travel, unit, expected }) => {
    const button = await openMatrix(record({ effective_extra_minutes: extra, km_value: km, trasferta_minutes: travel, reperibilita_unit: unit }));
    expect(Array.from(button.lastElementChild!.children).map((node) => node.textContent)).toEqual(expected);
    expect(button.lastElementChild).toHaveClass("min-h-[12px]");
  });

  test.each([
    { status: "RIC", description: "Timbratura E", detail: [{}], expected: ["✉"] },
    { status: "ACC", description: "Permesso", detail: [{}], expected: ["✉"] },
    { status: "ACC", description: "Timbratura U", detail: [], expected: ["✅"] },
    { status: "RIC", description: "Solo descrizione", detail: [], expected: [] },
  ])("retains request precedence $status/$description", async ({ status, description, detail, expected }) => {
    const button = await openMatrix(record({ request_status: status, request_description: description, detail_requests: detail }));
    expect(Array.from(button.lastElementChild!.children).map((node) => node.textContent)).toEqual(expected);
  });

  test.each([null, 0, -4, NaN])("keeps KM null/zero/sign/NaN value %s and empty draft across both inputs", async (km) => {
    await openMatrix(record({ km_value: km }));
    fireEvent.click(screen.getByRole("button", { name: "Inserisci KM" }));
    const matrixInput = within(screen.getByRole("table")).getByRole("textbox");
    expect(matrixInput).toHaveValue(km === null ? "" : String(km));
    fireEvent.change(matrixInput, { target: { value: "" } });
    fireEvent.click(screen.getByRole("button", { name: "R6 COLLABORATORE", exact: true }));
    const modalInput = await screen.findByLabelText("KM 2026-05-18");
    expect(modalInput).toHaveValue("");
    expect(modalInput).toBeEnabled();
    expect(api.updatePresenzeDailyRecord).not.toHaveBeenCalled();
  });

  test("keeps a supervisor's non-owned modal KM disabled", async () => {
    api.getPresenzeAccessContext.mockResolvedValue({ can_view_all_data: false, is_supervisor: true });
    await openMatrix(record());
    fireEvent.click(screen.getByRole("button", { name: "R6 COLLABORATORE", exact: true }));
    expect(await screen.findByLabelText("KM 2026-05-18")).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Chiudi ✕" }));
    expect(api.updatePresenzeDailyRecord).not.toHaveBeenCalled();
  });

  test("retains the same uncontrolled KM input and disables it until saving finishes", async () => {
    let finish!: (item: PresenzeDailyRecord) => void;
    api.updatePresenzeDailyRecord.mockImplementation(() => new Promise<PresenzeDailyRecord>((resolve) => { finish = resolve; }));
    const item = record({ km_value: 0 });
    await openMatrix(item);
    fireEvent.click(screen.getByRole("button", { name: "Inserisci KM" }));
    const input = within(screen.getByRole("table")).getByRole("textbox");
    fireEvent.change(input, { target: { value: "12" } });
    expect(within(screen.getByRole("table")).getByRole("textbox")).toBe(input);
    fireEvent.blur(input);
    await waitFor(() => expect(input).toBeDisabled());
    expect(api.updatePresenzeDailyRecord).toHaveBeenCalledWith(expect.any(String), item.id, { km_value: 12 });
    finish({ ...item, km_value: 12 });
    await waitFor(() => expect(input).toBeEnabled());
    expect(input).toHaveValue("12");
    expect(within(screen.getByRole("table")).getByRole("textbox")).toBe(input);
  });
});
