import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import MePageContent from "@/app/me/me-page-content";
import type { PresenzeDailyRecord } from "@/types/api";

const mocks = vi.hoisted(() => ({
  getStoredAccessToken: vi.fn(),
  getMePresenzeDailyRecord: vi.fn(),
  getMePresenzeStatus: vi.fn(),
  getMePresenzeSummary: vi.fn(),
  getMeOperazioniSummary: vi.fn(),
  getMeStatus: vi.fn(),
  getMeSummary: vi.fn(),
  isAuthError: vi.fn(),
  listMeAssignedDevices: vi.fn(),
  listMePresenzeDailyRecords: vi.fn(),
  listMeOperazioniActivities: vi.fn(),
  listMeOperazioniCases: vi.fn(),
  listMeOperazioniReports: vi.fn(),
  listMeVehicleAssignments: vi.fn(),
  listMeVehicleSessions: vi.fn(),
  push: vi.fn(),
  replace: vi.fn(),
  searchParams: new URLSearchParams("period=current"),
}));

vi.mock("@/lib/auth", () => ({
  getStoredAccessToken: mocks.getStoredAccessToken,
}));

vi.mock("@/lib/api", () => ({
  getMePresenzeDailyRecord: mocks.getMePresenzeDailyRecord,
  getMePresenzeStatus: mocks.getMePresenzeStatus,
  getMePresenzeSummary: mocks.getMePresenzeSummary,
  getMeOperazioniSummary: mocks.getMeOperazioniSummary,
  getMeStatus: mocks.getMeStatus,
  getMeSummary: mocks.getMeSummary,
  isAuthError: mocks.isAuthError,
  listMeAssignedDevices: mocks.listMeAssignedDevices,
  listMePresenzeDailyRecords: mocks.listMePresenzeDailyRecords,
  listMeOperazioniActivities: mocks.listMeOperazioniActivities,
  listMeOperazioniCases: mocks.listMeOperazioniCases,
  listMeOperazioniReports: mocks.listMeOperazioniReports,
  listMeVehicleAssignments: mocks.listMeVehicleAssignments,
  listMeVehicleSessions: mocks.listMeVehicleSessions,
}));

vi.mock("@/components/app/protected-page", () => ({
  ProtectedPage: ({ children, title }: { children: React.ReactNode; title: string }) => (
    <main>
      <h1>{title}</h1>
      {children}
    </main>
  ),
}));

vi.mock("next/navigation", () => ({
  usePathname: () => "/me",
  useRouter: () => ({ push: mocks.push, replace: mocks.replace }),
  useSearchParams: () => mocks.searchParams,
}));

function dailyRecord(overrides: Partial<PresenzeDailyRecord>): PresenzeDailyRecord {
  return {
    id: overrides.id ?? "record-1",
    collaborator_id: "collab-1",
    owner_user_id: null,
    application_user_id: 1,
    work_date: overrides.work_date ?? "2026-08-05",
    schedule_code: null,
    teo_minutes: null,
    ordinary_minutes: overrides.ordinary_minutes ?? null,
    absence_minutes: overrides.absence_minutes ?? null,
    justified_minutes: null,
    maggiorazione_minutes: null,
    mpe_minutes: null,
    straordinario_minutes: null,
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
    effective_straordinario_minutes: null,
    effective_mpe_minutes: null,
    effective_extra_minutes: null,
    operational_status: "unknown",
    operational_formula_code: null,
    operational_expected_minutes: null,
    operational_worked_minutes: null,
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
    stato: overrides.stato ?? "Giornata regolare",
    evidenze: null,
    raw_weekday: null,
    detail_title: null,
    detail_status: overrides.detail_status ?? null,
    detail_programmed_schedule: null,
    detail_effective_schedule: null,
    detail_time_slots: null,
    detail_schedule_type: null,
    detail_theoretical_hours: null,
    detail_absence_hours: null,
    detail_day_summary: {},
    detail_day_totals: {},
    detail_requests: [],
    detail_anomalies: [],
    detail_punch_rows: [],
    detail_text: null,
    detail_error: null,
    special_day: null,
    holiday_kind: null,
    grants_recovery_day: false,
    recovery_day_credit: 0,
    uses_recovery_day: false,
    recovery_day_debit: 0,
    recovery_day_balance_delta: 0,
    raw_payload_json: {},
    source_job_id: null,
    created_at: "2026-08-06T08:00:00Z",
    updated_at: "2026-08-06T08:00:00Z",
    punches: [],
    ...overrides,
  };
}

describe("MePageContent", () => {
  beforeEach(() => {
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(new Date("2026-08-06T10:00:00Z"));
    vi.clearAllMocks();
    mocks.searchParams = new URLSearchParams("period=current");
    mocks.getStoredAccessToken.mockReturnValue("token");
    mocks.getMeStatus.mockResolvedValue({
      module: "me",
      enabled: true,
      username: "amadu.salvatore",
      capabilities: { presenze: true, operazioni: false, network: false },
      message: "",
    });
    mocks.getMeSummary.mockResolvedValue({
      period_start: "2026-08-01",
      period_end: "2026-08-31",
      presenze: { ordinary_hours: 7, extra_hours: 0, absence_hours: 0, worked_days: 1, anomaly_days: 0, km: 0 },
      ordinary_minutes: 420,
      extra_minutes: 0,
      absence_minutes: 0,
      worked_days: 1,
      anomaly_days: 0,
      km_from_presenze: 0,
      activities_count: 0,
      activity_minutes: 0,
      reports_count: 0,
      assigned_cases_count: 0,
      open_cases_count: 0,
      closed_cases_count: 0,
      vehicle_sessions_count: 0,
      vehicle_km: 0,
      assigned_devices_count: 0,
      active_vehicle_assignments_count: 0,
    });
    mocks.getMePresenzeStatus.mockResolvedValue({
      module: "presenze",
      enabled: true,
      mapped: true,
      collaborator_id: "collab-1",
      collaborator_name: "AMADU SALVATORE",
      employee_code: "1854",
      message: "",
    });
    mocks.getMePresenzeSummary.mockResolvedValue({ period_start: "2026-08-01", period_end: "2026-08-31", items: [] });
    mocks.getMePresenzeDailyRecord.mockResolvedValue(
      dailyRecord({
        id: "compiled",
        work_date: "2026-08-05",
        stato: "Giornata regolare",
        ordinary_minutes: 420,
        detail_day_totals: { Ordinarie: "7:00" },
      }),
    );
    mocks.listMePresenzeDailyRecords.mockResolvedValue({
      total: 4,
      page: 1,
      page_size: 200,
      items: [
        dailyRecord({ id: "future", work_date: "2026-08-31", stato: "Giornata da calcolare", absence_minutes: 420 }),
        dailyRecord({ id: "today-open", work_date: "2026-08-06", stato: "Giornata da calcolare" }),
        dailyRecord({ id: "compiled", work_date: "2026-08-05", stato: "Giornata regolare", ordinary_minutes: 420 }),
        dailyRecord({ id: "sunday-rest", work_date: "2026-08-02", stato: "Giornata regolare", special_day: true }),
      ],
    });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  test("shows only compiled latest daily records in the overview card", async () => {
    render(<MePageContent />);

    await waitFor(() => expect(screen.getByText("mer 05/08/2026")).toBeInTheDocument());

    expect(screen.queryByText("lun 31/08/2026")).not.toBeInTheDocument();
    expect(screen.queryByText("gio 06/08/2026")).not.toBeInTheDocument();
  });

  test("uses an info badge for unworked weekend records", async () => {
    render(<MePageContent />);

    const sundayCard = await screen.findByText("dom 02/08/2026");
    const card = sundayCard.closest(".rounded-2xl");

    expect(card).not.toBeNull();
    expect(within(card as HTMLElement).getByText("Giornata regolare")).toHaveClass("text-blue-700");
  });

  test("renders current presenze as a monthly calendar with clickable daily details", async () => {
    render(<MePageContent initialTab="presenze" />);

    expect(await screen.findByRole("heading", { name: "Calendario mensile giornaliere" })).toBeInTheDocument();
    expect(screen.getByText("Lun")).toBeInTheDocument();
    expect(screen.getByText("Dom")).toBeInTheDocument();
    expect(screen.getByText("Ord 7.0 h")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Apri dettaglio presenze mer 05/08/2026" }));

    await waitFor(() => expect(mocks.getMePresenzeDailyRecord).toHaveBeenCalledWith("token", "compiled"));
    expect(await screen.findByRole("heading", { name: "mer 05/08/2026" })).toBeInTheDocument();
  });
});
