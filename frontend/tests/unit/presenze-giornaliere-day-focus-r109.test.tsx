import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import type { ReactNode } from "react";

import PresenzeGiornalierePage from "@/app/presenze/giornaliere/page";
import type {
  CurrentUser,
  PresenzeAccessContext,
  PresenzeCollaborator,
  PresenzeDailyRecord,
  PresenzeDailyRecordListResponse,
} from "@/types/api";

const api = vi.hoisted(() => ({
  getStoredAccessToken: vi.fn<() => string>(),
  getCurrentUser: vi.fn<typeof import("@/lib/api").getCurrentUser>(),
  getPresenzeAccessContext: vi.fn<typeof import("@/lib/api").getPresenzeAccessContext>(),
  listAllPresenzeCollaborators: vi.fn<typeof import("@/lib/api").listAllPresenzeCollaborators>(),
  listPresenzeDailyMatrixRecords: vi.fn<typeof import("@/lib/api").listPresenzeDailyMatrixRecords>(),
  getPresenzeDailyRecord: vi.fn<typeof import("@/lib/api").getPresenzeDailyRecord>(),
  updatePresenzeDailyRecord: vi.fn<typeof import("@/lib/api").updatePresenzeDailyRecord>(),
  getPresenzeSyncJob: vi.fn<typeof import("@/lib/api").getPresenzeSyncJob>(),
  refreshPresenzeDailyRecordFromInaz: vi.fn<typeof import("@/lib/api").refreshPresenzeDailyRecordFromInaz>(),
  updatePresenzeCollaboratorContractProfile: vi.fn<typeof import("@/lib/api").updatePresenzeCollaboratorContractProfile>(),
}));

vi.mock("@/lib/auth", () => ({ getStoredAccessToken: api.getStoredAccessToken }));
vi.mock("@/lib/api", () => ({ ...api, ApiError: class ApiError extends Error {} }));
vi.mock("@/components/app/protected-page", () => ({
  ProtectedPage: ({ children }: { children: ReactNode }) => <div>{children}</div>,
}));
vi.mock("@/components/presenze/inaz-sync-control", () => ({ InazSyncControl: () => null }));
vi.mock("@/components/presenze/whatsapp-reminder-alert", () => ({ WhatsAppReminderAlert: () => null }));
vi.mock("@/components/presenze/daily-operational-controls", () => ({ DailyOperationalControls: () => null }));

const SESSION = {
  id: 12,
  username: "r109-supervisor",
  email: "r109@example.local",
  role: "viewer",
  is_active: true,
  module_accessi: false,
  module_rete: false,
  module_inventario: false,
  module_catasto: false,
  module_utenze: false,
  module_operazioni: false,
  module_riordino: false,
  module_ruolo: false,
  module_presenze: true,
  enabled_modules: ["presenze"],
} satisfies CurrentUser;

const ACCESS = {
  can_view_all_data: false,
  can_view_all_credentials: false,
  can_manage_supervisors: false,
  is_supervisor: true,
  assigned_collaborators_count: 2,
} satisfies PresenzeAccessContext;

const COLLABORATORS: PresenzeCollaborator[] = [
  {
    id: "r109-amadu",
    owner_user_id: 77,
    application_user_id: null,
    kint: "r109-1",
    kkint: null,
    employee_code: "r109-1854",
    company_code: "53",
    company_label: "CBO",
    name: "AMADU SALVATORE",
    birth_date: null,
    contract_kind: "operaio",
    operai_group: "agrario",
    standard_daily_minutes: 420,
    is_active: true,
    last_seen_at: null,
    created_at: "2026-05-01T00:00:00Z",
    updated_at: "2026-05-01T00:00:00Z",
  },
  {
    id: "r109-podda",
    owner_user_id: 77,
    application_user_id: null,
    kint: "r109-2",
    kkint: null,
    employee_code: "r109-1855",
    company_code: "53",
    company_label: "CBO",
    name: "PODDA RAIMONDO",
    birth_date: null,
    contract_kind: "operaio",
    operai_group: "agrario",
    standard_daily_minutes: 420,
    is_active: true,
    last_seen_at: null,
    created_at: "2026-05-01T00:00:00Z",
    updated_at: "2026-05-01T00:00:00Z",
  },
];

function dailyRecord(overrides: Partial<PresenzeDailyRecord> = {}): PresenzeDailyRecord {
  return {
    id: "r109-record",
    collaborator_id: "r109-amadu",
    owner_user_id: 77,
    application_user_id: null,
    work_date: "2026-05-18",
    schedule_code: "STD",
    teo_minutes: 420,
    ordinary_minutes: 420,
    absence_minutes: 0,
    justified_minutes: 0,
    maggiorazione_minutes: 0,
    mpe_minutes: 0,
    straordinario_minutes: 0,
    km_value: null,
    trasferta_minutes: null,
    trasferta_montano: false,
    reperibilita_unit: "none",
    reperibilita_quantity: null,
    override_straordinario_minutes: null,
    override_mpe_minutes: null,
    manual_note: null,
    request_type: null,
    request_description: null,
    request_status: null,
    request_authorized_by: null,
    resolved_absence_cause: null,
    validation_status: "pending",
    validated_by_user_id: null,
    validated_at: null,
    validation_note: null,
    effective_straordinario_minutes: 0,
    effective_mpe_minutes: 0,
    effective_extra_minutes: 0,
    operational_status: "ok",
    operational_formula_code: null,
    operational_expected_minutes: 420,
    operational_worked_minutes: 420,
    operational_missing_minutes: 0,
    operational_mpe_minutes: 0,
    operational_notes: [],
    night_minutes: 0,
    festive_minutes: 0,
    festive_night_minutes: 0,
    ordinary_night_minutes: 0,
    overtime_day_minutes: 0,
    overtime_night_minutes: 0,
    overtime_festive_minutes: 0,
    overtime_festive_night_minutes: 0,
    shift_festive_day_minutes: 0,
    shift_night_minutes: 0,
    shift_festive_night_minutes: 0,
    monthly_night_shift_count: 0,
    ordinary_night_bonus_threshold_met: false,
    ordinary_night_bonus_rate: null,
    stato: "Giornata regolare",
    evidenze: null,
    raw_weekday: "L",
    detail_title: null,
    detail_status: "Giornata regolare",
    detail_programmed_schedule: "STD - Ordinario",
    detail_effective_schedule: null,
    detail_time_slots: null,
    detail_schedule_type: null,
    detail_theoretical_hours: "07:00",
    detail_absence_hours: null,
    detail_day_summary: {},
    detail_day_totals: {},
    detail_requests: [],
    detail_anomalies: [],
    detail_punch_rows: [],
    detail_text: null,
    detail_error: null,
    special_day: false,
    holiday_kind: null,
    grants_recovery_day: false,
    recovery_day_credit: 0,
    uses_recovery_day: false,
    recovery_day_debit: 0,
    recovery_day_balance_delta: 0,
    raw_payload_json: {},
    source_job_id: null,
    created_at: "2026-05-18T00:00:00Z",
    updated_at: "2026-05-18T00:00:00Z",
    punches: [],
    ...overrides,
  } satisfies PresenzeDailyRecord;
}

type FocusKind = "anomalies" | "requests";

const BUTTON_BASE = "w-[68px] rounded-lg px-2 py-1 text-[10px] font-bold leading-none ring-1 ring-inset transition ";
const BUTTON_TONES = {
  anomalies: {
    idle: "bg-red-50 text-red-700 ring-red-200 hover:bg-red-100",
    selected: "bg-red-700 text-white ring-red-700",
    suffix: " anom.",
    title: "anomalie",
  },
  requests: {
    idle: "bg-sky-50 text-sky-700 ring-sky-200 hover:bg-sky-100",
    selected: "bg-sky-700 text-white ring-sky-700",
    suffix: " ric.",
    title: "richieste",
  },
};

async function renderMatrix(records: PresenzeDailyRecord[]) {
  api.listPresenzeDailyMatrixRecords.mockResolvedValue({
    items: records,
    total: records.length,
    page: 1,
    page_size: 5000,
  } satisfies PresenzeDailyRecordListResponse);
  api.getPresenzeDailyRecord.mockImplementation(async (_token, recordId) => {
    const record = records.find((item) => item.id === recordId);
    if (!record) throw new Error(`Unexpected R109 detail ${recordId}`);
    return record;
  });
  render(<PresenzeGiornalierePage />);
  fireEvent.change(await screen.findByLabelText("Mese operativo"), { target: { value: "2026-05" } });
  await screen.findByRole("button", { name: "AMADU SALVATORE" });
}

function dayHeading(day: number): HTMLElement {
  const headings = within(screen.getByRole("table")).getAllByRole("columnheader");
  const heading = headings[day];
  if (!(heading instanceof HTMLElement)) throw new Error(`Missing R109 heading ${day}`);
  expect(heading.children).toHaveLength(3);
  expect(heading.children[1].textContent).toBe(String(day));
  return heading;
}

function badgeHost(day: number): HTMLElement {
  const host = dayHeading(day).children[2];
  if (!(host instanceof HTMLElement)) throw new Error(`Missing R109 badge host ${day}`);
  expect(host.className).toBe("mt-2 flex min-h-[32px] flex-col items-center justify-start gap-1");
  return host;
}

function focusButton(kind: FocusKind, day = 18, count = 1): HTMLButtonElement {
  const title = `2026-05-${day} · ${count} ${BUTTON_TONES[kind].title}`;
  const button = within(dayHeading(day)).getByTitle(title);
  if (!(button instanceof HTMLButtonElement)) throw new Error(`Missing R109 button ${title}`);
  return button;
}

function expectPresentation(button: HTMLButtonElement, kind: FocusKind, selected: boolean, day = 18, count = 1) {
  const presentation = BUTTON_TONES[kind];
  expect(button.type).toBe("button");
  expect(button.textContent).toBe(`${count}${presentation.suffix}`);
  expect(button.title).toBe(`2026-05-${day} · ${count} ${presentation.title}`);
  expect(button.className).toBe(BUTTON_BASE + (selected ? presentation.selected : presentation.idle));
}

async function expectVisibleCollaborators(names: string[]) {
  await waitFor(() => {
    const table = within(screen.getByRole("table"));
    for (const collaborator of COLLABORATORS) {
      if (names.includes(collaborator.name)) {
        expect(table.getByRole("button", { name: collaborator.name })).toBeInTheDocument();
      } else {
        expect(table.queryByRole("button", { name: collaborator.name })).not.toBeInTheDocument();
      }
    }
  });
}

const VISIBILITY_CASES = [
  { name: "neither", anomaly: false, request: false },
  { name: "anomaly only", anomaly: true, request: false },
  { name: "request only", anomaly: false, request: true },
  { name: "both", anomaly: true, request: true },
];

describe("R109 public daily-heading focus contract", () => {
  let tokenSequence = 0;

  beforeEach(() => {
    vi.resetAllMocks();
    tokenSequence += 1;
    api.getStoredAccessToken.mockReturnValue(`r109-day-focus-${tokenSequence}`);
    api.getCurrentUser.mockResolvedValue(SESSION);
    api.getPresenzeAccessContext.mockResolvedValue(ACCESS);
    api.listAllPresenzeCollaborators.mockResolvedValue(COLLABORATORS);
  });

  afterEach(() => {
    cleanup();
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  test.each(VISIBILITY_CASES)("keeps exact heading presentation for $name", async ({ anomaly, request }) => {
    await renderMatrix([dailyRecord({
      operational_status: anomaly ? "in_analysis" : "ok",
      request_description: request ? "Permesso R109" : null,
      detail_requests: request ? [{ Descrizione: "Permesso R109" }] : [],
    })]);
    const host = badgeHost(18);
    const buttons = within(host).queryAllByRole("button");
    expect(buttons).toHaveLength(Number(anomaly) + Number(request));
    const expectedButtons: HTMLButtonElement[] = [];
    if (anomaly) {
      const button = focusButton("anomalies");
      expectPresentation(button, "anomalies", false);
      expectedButtons.push(button);
    }
    if (request) {
      const button = focusButton("requests");
      expectPresentation(button, "requests", false);
      expectedButtons.push(button);
    }
    if (anomaly || request) {
      expect(Array.from(host.children)).toEqual(expectedButtons);
      expect(host.textContent).not.toContain("-");
    } else {
      expect(host.children).toHaveLength(1);
      expect(host.firstElementChild?.tagName).toBe("SPAN");
      expect(host.firstElementChild?.className).toBe("text-[10px] leading-none text-slate-300");
      expect(host.textContent).toBe("-");
    }
    const emptyHost = badgeHost(20);
    expect(emptyHost.children).toHaveLength(1);
    expect(emptyHost.firstElementChild?.tagName).toBe("SPAN");
    expect(emptyHost.firstElementChild?.className).toBe("text-[10px] leading-none text-slate-300");
    expect(emptyHost.textContent).toBe("-");
  });

  test.each(["anomalies", "requests"] as const)("retains focused %s node through selection, same-kind toggle and removal", async (kind) => {
    await renderMatrix([
      dailyRecord({ operational_status: "in_analysis", request_description: "Permesso R109" }),
      dailyRecord({ id: "r109-other", collaborator_id: "r109-podda", work_date: "2026-05-19" }),
    ]);
    const button = focusButton(kind);
    button.focus();
    expect(document.activeElement).toBe(button);
    fireEvent.click(button);
    await expectVisibleCollaborators(["AMADU SALVATORE"]);
    expect(focusButton(kind)).toBe(button);
    expectPresentation(button, kind, true);
    expect(document.activeElement).toBe(button);
    fireEvent.click(button);
    await expectVisibleCollaborators(["AMADU SALVATORE", "PODDA RAIMONDO"]);
    expect(focusButton(kind)).toBe(button);
    expectPresentation(button, kind, false);
    expect(document.activeElement).toBe(button);
    expect(screen.queryByText(/Filtro giorno:/)).not.toBeInTheDocument();
    fireEvent.click(button);
    await expectVisibleCollaborators(["AMADU SALVATORE"]);
    fireEvent.click(screen.getByRole("button", { name: "Rimuovi" }));
    await expectVisibleCollaborators(["AMADU SALVATORE", "PODDA RAIMONDO"]);
    expect(focusButton(kind)).toBe(button);
    expectPresentation(button, kind, false);
    expect(screen.queryByText(/Filtro giorno:/)).not.toBeInTheDocument();
  });

  test("selects another kind and then another day without replacing header nodes", async () => {
    await renderMatrix([
      dailyRecord({ operational_status: "in_analysis", request_description: "Permesso R109" }),
      dailyRecord({ id: "r109-podda-anomaly", collaborator_id: "r109-podda", operational_status: "in_analysis" }),
      dailyRecord({ id: "r109-podda-request", collaborator_id: "r109-podda", work_date: "2026-05-19", request_description: "Ferie R109" }),
    ]);
    const anomaly = focusButton("anomalies", 18, 2);
    const request = focusButton("requests");
    const otherDayRequest = focusButton("requests", 19);
    fireEvent.click(anomaly);
    await expectVisibleCollaborators(["AMADU SALVATORE", "PODDA RAIMONDO"]);
    expectPresentation(anomaly, "anomalies", true, 18, 2);
    expectPresentation(request, "requests", false);
    expectPresentation(otherDayRequest, "requests", false, 19);
    fireEvent.click(request);
    await expectVisibleCollaborators(["AMADU SALVATORE"]);
    expectPresentation(anomaly, "anomalies", false, 18, 2);
    expectPresentation(request, "requests", true);
    fireEvent.click(otherDayRequest);
    await expectVisibleCollaborators(["PODDA RAIMONDO"]);
    expectPresentation(request, "requests", false);
    expectPresentation(otherDayRequest, "requests", true, 19);
    expect(focusButton("anomalies", 18, 2)).toBe(anomaly);
    expect(focusButton("requests")).toBe(request);
    expect(focusButton("requests", 19)).toBe(otherDayRequest);
    fireEvent.click(otherDayRequest);
    await expectVisibleCollaborators(["AMADU SALVATORE", "PODDA RAIMONDO"]);
    expectPresentation(otherDayRequest, "requests", false, 19);
  });

  test("retains selected request DOM identity and focus when deferred validation removes its anomaly sibling", async () => {
    const record = dailyRecord({
      operational_status: "in_analysis",
      request_description: "Permesso R109",
      detail_requests: [{ Descrizione: "Permesso R109" }],
    });
    await renderMatrix([record]);
    const request = focusButton("requests");
    const anomaly = focusButton("anomalies");
    expect(Array.from(badgeHost(18).children)).toEqual([anomaly, request]);
    request.focus();
    expect(document.activeElement).toBe(request);
    fireEvent.click(request);
    await expectVisibleCollaborators(["AMADU SALVATORE"]);
    expect(focusButton("requests")).toBe(request);
    expectPresentation(request, "requests", true);
    expect(document.activeElement).toBe(request);
    const row = screen.getByRole("button", { name: "AMADU SALVATORE" }).closest("tr");
    if (!row) throw new Error("Missing R109 collaborator row");
    const cell = within(row).getAllByRole("button")[1];
    fireEvent.click(cell);
    await screen.findByText("Rettifiche operative");
    let resolveValidation: (value: PresenzeDailyRecord) => void = () => {
      throw new Error("R109 validation deferred promise was not initialized");
    };
    const pendingValidation = new Promise<PresenzeDailyRecord>((resolve) => { resolveValidation = resolve; });
    api.updatePresenzeDailyRecord.mockReturnValueOnce(pendingValidation);
    const validate = screen.getByRole("button", { name: "Valida giornaliera" });
    fireEvent.click(validate);
    expect(api.updatePresenzeDailyRecord).toHaveBeenCalledExactlyOnceWith(
      api.getStoredAccessToken(), record.id, { validation_status: "validated", validation_note: null },
    );
    expect(validate).toBeDisabled();
    expect(focusButton("anomalies")).toBe(anomaly);
    request.focus();
    expect(request.isConnected).toBe(true);
    expect(document.activeElement).toBe(request);
    await act(async () => {
      resolveValidation({ ...record, operational_status: "ok", validation_status: "validated" });
      await pendingValidation;
    });
    await waitFor(() => {
      expect(within(dayHeading(18)).queryByTitle("2026-05-18 · 1 anomalie")).not.toBeInTheDocument();
      expect(focusButton("requests")).toBe(request);
      expect(request.isConnected).toBe(true);
      expect(document.activeElement).toBe(request);
      expectPresentation(request, "requests", true);
      expect(Array.from(badgeHost(18).children)).toEqual([request]);
      expect(badgeHost(18).textContent).toBe("1 ric.");
      expect(screen.getByText("Filtro giorno: lunedì 18 · richieste")).toBeInTheDocument();
      expect(screen.getByText("Giornata 2026-05-18 validata.")).toBeInTheDocument();
    });
  });
});
