vi.mock("@/components/presenze/whatsapp-manual-message", () => ({ WhatsAppManualMessage: () => null }));
vi.mock("@/components/presenze/inaz-sync-control", () => ({ InazSyncControl: ({ onCompleted }: { onCompleted: () => void }) => <button onClick={onCompleted}>Simula completamento INAZ</button> }));
import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { StrictMode } from "react";

import PresenzeGiornalierePage from "@/app/presenze/giornaliere/page";
import type { PresenzeDailyRecord } from "@/lib/api";
import { ApiError } from "@/lib/api";

const baseDailyRecord = {
  id: "record-1",
  collaborator_id: "collab-1",
  owner_user_id: 77,
  application_user_id: null,
  work_date: "2026-05-16",
  schedule_code: "OPESAB",
  teo_minutes: 390,
  ordinary_minutes: 330,
  absence_minutes: 60,
  justified_minutes: 0,
  maggiorazione_minutes: 15,
  mpe_minutes: 45,
  straordinario_minutes: 75,
  km_value: 24,
  trasferta_minutes: null,
  trasferta_montano: false,
  reperibilita_unit: "none",
  reperibilita_quantity: null,
  override_straordinario_minutes: null,
  override_mpe_minutes: null,
  manual_note: null,
  request_type: "Eventi",
  request_description: "Permesso ordinario",
  request_status: "RIC",
  request_authorized_by: "PODDA FABRIZIO",
  resolved_absence_cause: "permesso",
  validation_status: "pending",
  validated_by_user_id: null,
  validated_at: null,
  validation_note: null,
  effective_straordinario_minutes: 75,
  effective_mpe_minutes: 45,
  effective_extra_minutes: 120,
  operational_status: "in_analysis",
  operational_formula_code: "OPESAB",
  operational_expected_minutes: 420,
  operational_worked_minutes: 435,
  operational_missing_minutes: 0,
  operational_mpe_minutes: 15,
  operational_notes: ["INAZ segnala anomalia, ma la formula GAIA quadra le ore"],
  stato: "Giornata anomala",
  evidenze: "Ore mancanti",
  raw_weekday: "S",
  detail_title: null,
  detail_status: "Giornata anomala",
  detail_programmed_schedule: "OPESAB - Rientro Operai",
  detail_effective_schedule: null,
  detail_time_slots: "07:00 - 13:30",
  detail_schedule_type: null,
  detail_theoretical_hours: "06:30",
  detail_absence_hours: "01:00",
  detail_day_summary: { "Ore Ordinarie": "05:30" },
  detail_day_totals: { "CARTELLINO Gruppo Ore Straordinario": "01:15" },
  detail_requests: [{ Descrizione: "Permesso ordinario" }],
  detail_anomalies: [{ "Anomalia giornata": "Ore mancanti" }],
  detail_punch_rows: [
    { time: "06:55", direction: "E", terminal_label: "FENO-Fenoso", raw: { Ora: "06:55", EU: "E", Term: "FENO-Fenoso" } },
    { time: "10:30", direction: "U", terminal_label: "FENO-Fenoso", raw: { Ora: "10:30", EU: "U", Term: "FENO-Fenoso" } },
    { time: "10:45", direction: "E", terminal_label: "FENO-Fenoso", raw: { Ora: "10:45", EU: "E", Term: "FENO-Fenoso" } },
    { time: "12:30", direction: "U", terminal_label: "FENO-Fenoso", raw: { Ora: "12:30", EU: "U", Term: "FENO-Fenoso" } },
  ],
  detail_text: null,
  detail_error: null,
  special_day: true,
  raw_payload_json: {},
  source_job_id: null,
  created_at: "2026-06-04T09:00:00Z",
  updated_at: "2026-06-04T09:00:00Z",
  punches: [
    {
      id: "p1",
      daily_record_id: "record-1",
      sequence: 1,
      entry_time: "06:55",
      exit_time: "12:30",
      terminal_label: "FENO-Fenoso",
      created_at: "2026-06-04T09:00:00Z",
    },
  ],
};

const mocks = vi.hoisted(() => ({
  getStoredAccessToken: vi.fn(),
  getCurrentUser: vi.fn(),
  getPresenzeAccessContext: vi.fn(),
  getPresenzeDailyRecord: vi.fn(),
  getPresenzeSyncJob: vi.fn(),
  listAllPresenzeCollaborators: vi.fn(),
  listPresenzeDailyMatrixRecords: vi.fn(),
  refreshPresenzeDailyRecordFromInaz: vi.fn(),
  updatePresenzeCollaboratorContractProfile: vi.fn(),
  updatePresenzeDailyRecord: vi.fn(),
}));

vi.mock("@/lib/auth", () => ({
  getStoredAccessToken: mocks.getStoredAccessToken,
}));

vi.mock("@/lib/api", () => ({
  ApiError: class ApiError extends Error {
    status?: number;
    detailData: unknown;

    constructor(message: string, detailData?: unknown, status?: number) {
      super(message);
      this.name = "ApiError";
      this.detailData = detailData;
      this.status = status;
    }
  },
  getCurrentUser: mocks.getCurrentUser,
  getPresenzeAccessContext: mocks.getPresenzeAccessContext,
  getPresenzeDailyRecord: mocks.getPresenzeDailyRecord,
  getPresenzeSyncJob: mocks.getPresenzeSyncJob,
  listAllPresenzeCollaborators: mocks.listAllPresenzeCollaborators,
  listPresenzeDailyMatrixRecords: mocks.listPresenzeDailyMatrixRecords,
  refreshPresenzeDailyRecordFromInaz: mocks.refreshPresenzeDailyRecordFromInaz,
  updatePresenzeCollaboratorContractProfile: mocks.updatePresenzeCollaboratorContractProfile,
  updatePresenzeDailyRecord: mocks.updatePresenzeDailyRecord,
}));

vi.mock("@/components/app/protected-page", () => ({
  ProtectedPage: ({ children, title }: { children: React.ReactNode; title: string }) => (
    <div>
      <h1>{title}</h1>
      {children}
    </div>
  ),
}));

vi.mock("@/components/ui/badge", () => ({
  Badge: ({ children, variant }: { children: React.ReactNode; variant?: string }) => <span data-variant={variant}>{children}</span>,
}));

vi.mock("@/components/presenze/whatsapp-reminder-alert", () => ({
  WhatsAppReminderAlert: () => null,
}));

vi.mock("@/components/table/data-table", () => ({
  DataTable: ({ data, onRowClick }: { data: Array<{ id: string; collaborator: string; workDate: string }>; onRowClick?: (row: { id: string }) => void }) => (
    <div>
      {data.map((row) => (
        <button key={row.id} type="button" onClick={() => onRowClick?.(row)}>
          {row.collaborator} {row.workDate}
        </button>
      ))}
    </div>
  ),
}));

describe("Presenze giornaliere workspace", () => {
  let tokenSeed = 0;

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  beforeEach(() => {
    vi.clearAllMocks();
    tokenSeed += 1;
    mocks.getStoredAccessToken.mockReturnValue(`token-${tokenSeed}`);
    mocks.getCurrentUser.mockResolvedValue({
      id: 12,
      username: "caposettore",
      email: "capo@example.local",
      full_name: "Capo Settore",
      office_location: null,
      phone_extension: null,
      role: "viewer",
      is_active: true,
      module_accessi: true,
      module_rete: false,
      module_inventario: false,
      module_catasto: false,
      module_utenze: false,
      module_operazioni: false,
      module_riordino: false,
      module_ruolo: false,
      module_presenze: true,
      enabled_modules: ["accessi", "presenze"],
    });
    mocks.getPresenzeAccessContext.mockResolvedValue({
      can_view_all_data: false,
      can_view_all_credentials: false,
      can_manage_supervisors: false,
      is_supervisor: true,
      assigned_collaborators_count: 1,
    });
    mocks.listAllPresenzeCollaborators.mockResolvedValue([
      {
        id: "collab-1",
        owner_user_id: 77,
        application_user_id: null,
        kint: "10159",
        kkint: "{demo}",
        employee_code: "1854",
        company_code: "53",
        company_label: "53 - CBO",
        name: "AMADU SALVATORE",
        birth_date: "1967-02-26",
        contract_kind: "operaio",
        operai_group: "agrario",
        standard_daily_minutes: 420,
        is_active: true,
        last_seen_at: "2026-06-04T09:00:00Z",
        created_at: "2026-06-04T09:00:00Z",
        updated_at: "2026-06-04T09:00:00Z",
      },
      {
        id: "collab-2",
        owner_user_id: 77,
        application_user_id: null,
        kint: "10160",
        kkint: "{demo2}",
        employee_code: "1855",
        company_code: "53",
        company_label: "53 - CBO",
        name: "PODDA RAIMONDO",
        birth_date: "1968-02-26",
        contract_kind: "operaio",
        operai_group: "catasto_magazzino",
        standard_daily_minutes: 360,
        is_active: true,
        last_seen_at: "2026-06-04T09:00:00Z",
        created_at: "2026-06-04T09:00:00Z",
        updated_at: "2026-06-04T09:00:00Z",
      },
      {
        id: "collab-3",
        owner_user_id: 77,
        application_user_id: null,
        kint: "10161",
        kkint: "{demo3}",
        employee_code: "1856",
        company_code: "53",
        company_label: "53 - CBO",
        name: "ZEDDA MARIO",
        birth_date: "1970-02-26",
        contract_kind: "operaio",
        operai_group: null,
        standard_daily_minutes: 420,
        is_active: true,
        last_seen_at: "2026-06-04T09:00:00Z",
        created_at: "2026-06-04T09:00:00Z",
        updated_at: "2026-06-04T09:00:00Z",
      },
    ]);
    mocks.listPresenzeDailyMatrixRecords.mockResolvedValue({
      items: [
        baseDailyRecord,
        {
          ...baseDailyRecord,
          id: "record-2",
          collaborator_id: "collab-2",
          owner_user_id: 77,
          work_date: "2026-05-16",
          km_value: null,
          trasferta_minutes: null,
          trasferta_montano: false,
          straordinario_minutes: 0,
          effective_straordinario_minutes: 0,
          mpe_minutes: 0,
          effective_mpe_minutes: 0,
          effective_extra_minutes: 0,
          reperibilita_unit: "none",
          reperibilita_quantity: null,
          punches: [],
          detail_punch_rows: [],
          detail_anomalies: [],
          detail_requests: [],
          evidenze: null,
          stato: "Giornata regolare",
          detail_status: "Giornata regolare",
          operational_status: "ok",
          operational_notes: [],
          operational_missing_minutes: 0,
          request_description: null,
          request_type: null,
          request_status: null,
          request_authorized_by: null,
          resolved_absence_cause: null,
        },
        {
          ...baseDailyRecord,
          id: "record-3",
          collaborator_id: "collab-3",
          owner_user_id: 77,
          work_date: "2026-05-16",
          km_value: null,
          trasferta_minutes: null,
          trasferta_montano: false,
          straordinario_minutes: 0,
          effective_straordinario_minutes: 0,
          mpe_minutes: 0,
          effective_mpe_minutes: 0,
          effective_extra_minutes: 0,
          reperibilita_unit: "none",
          reperibilita_quantity: null,
          punches: [],
          detail_punch_rows: [],
          detail_anomalies: [],
          detail_requests: [],
          evidenze: null,
          stato: "Giornata regolare",
          detail_status: "Giornata regolare",
          operational_status: "ok",
          operational_notes: [],
          operational_missing_minutes: 0,
          request_description: null,
          request_type: null,
          request_status: null,
          request_authorized_by: null,
          resolved_absence_cause: null,
        },
      ],
      total: 3,
      page: 1,
      page_size: 5000,
    });
    mocks.getPresenzeDailyRecord.mockResolvedValue(baseDailyRecord);
    mocks.getPresenzeSyncJob.mockResolvedValue({
      id: "sync-job-1",
      status: "completed",
      requested_by_user_id: 12,
      credential_id: 1,
      import_job_id: null,
      period_start: "2026-05-16",
      period_end: "2026-05-16",
      collaborator_limit: 1,
      records_imported: 1,
      records_skipped: 0,
      records_errors: 0,
      json_artifact_path: null,
      worker_log_path: null,
      worker_pid: null,
      attempt_count: 1,
      max_attempts: 3,
      error_detail: null,
      params_json: { trigger: "manual_record_refresh" },
      created_at: "2026-06-04T09:00:00Z",
      started_at: "2026-06-04T09:00:01Z",
      finished_at: "2026-06-04T09:00:02Z",
    });
    mocks.refreshPresenzeDailyRecordFromInaz.mockResolvedValue({
      id: "sync-job-1",
      status: "pending",
      requested_by_user_id: 12,
      credential_id: 1,
      import_job_id: null,
      period_start: "2026-05-16",
      period_end: "2026-05-16",
      collaborator_limit: 1,
      records_imported: 0,
      records_skipped: 0,
      records_errors: 0,
      json_artifact_path: null,
      worker_log_path: null,
      worker_pid: null,
      attempt_count: 1,
      max_attempts: 3,
      error_detail: null,
      params_json: { trigger: "manual_record_refresh" },
      created_at: "2026-06-04T09:00:00Z",
      started_at: null,
      finished_at: null,
    });
    mocks.updatePresenzeDailyRecord.mockResolvedValue({
      id: "record-1",
      collaborator_id: "collab-1",
      owner_user_id: 77,
      application_user_id: null,
      work_date: "2026-05-16",
      schedule_code: "OPESAB",
      teo_minutes: 390,
      ordinary_minutes: 330,
      absence_minutes: 60,
      justified_minutes: 0,
      maggiorazione_minutes: 15,
      mpe_minutes: 45,
      straordinario_minutes: 75,
      km_value: 30,
      trasferta_minutes: null,
      trasferta_montano: false,
      reperibilita_unit: "days",
      reperibilita_quantity: 1,
      override_straordinario_minutes: 90,
      override_mpe_minutes: 30,
      manual_note: "Corretto dal capo settore",
      request_type: "Eventi",
      request_description: "Permesso ordinario",
      request_status: "RIC",
      request_authorized_by: "PODDA FABRIZIO",
      resolved_absence_cause: "permesso",
      validation_status: "validated",
      validated_by_user_id: 12,
      validated_at: "2026-06-04T09:05:00Z",
      validation_note: "Verificata dal capo settore",
      effective_straordinario_minutes: 90,
      effective_mpe_minutes: 30,
      effective_extra_minutes: 120,
      operational_status: "in_analysis",
      operational_formula_code: "OPESAB",
      operational_expected_minutes: 420,
      operational_worked_minutes: 435,
      operational_missing_minutes: 0,
      operational_mpe_minutes: 15,
      operational_notes: ["INAZ segnala anomalia, ma la formula GAIA quadra le ore"],
      stato: "Giornata anomala",
      evidenze: "Ore mancanti",
      raw_weekday: "S",
      detail_title: null,
      detail_status: "Giornata anomala",
      detail_programmed_schedule: "OPESAB - Rientro Operai",
      detail_effective_schedule: null,
      detail_time_slots: "07:00 - 13:30",
      detail_schedule_type: null,
      detail_theoretical_hours: "06:30",
      detail_absence_hours: "01:00",
      detail_day_summary: { "Ore Ordinarie": "05:30" },
      detail_day_totals: { "CARTELLINO Gruppo Ore Straordinario": "01:30" },
      detail_requests: [{ Descrizione: "Permesso ordinario" }],
      detail_anomalies: [{ "Anomalia giornata": "Ore mancanti" }],
      detail_punch_rows: [
        { time: "06:55", direction: "E", terminal_label: "FENO-Fenoso", raw: { Ora: "06:55", EU: "E", Term: "FENO-Fenoso" } },
        { time: "10:30", direction: "U", terminal_label: "FENO-Fenoso", raw: { Ora: "10:30", EU: "U", Term: "FENO-Fenoso" } },
        { time: "10:45", direction: "E", terminal_label: "FENO-Fenoso", raw: { Ora: "10:45", EU: "E", Term: "FENO-Fenoso" } },
        { time: "12:30", direction: "U", terminal_label: "FENO-Fenoso", raw: { Ora: "12:30", EU: "U", Term: "FENO-Fenoso" } },
      ],
      detail_text: null,
      detail_error: null,
      special_day: true,
      raw_payload_json: {},
      source_job_id: null,
      created_at: "2026-06-04T09:00:00Z",
      updated_at: "2026-06-04T09:05:00Z",
      punches: [
        {
          id: "p1",
          daily_record_id: "record-1",
          sequence: 1,
          entry_time: "06:55:00",
          exit_time: "12:30:00",
          terminal_label: "FENO-Fenoso",
          created_at: "2026-06-04T09:00:00Z",
        },
      ],
    });
    mocks.updatePresenzeCollaboratorContractProfile.mockResolvedValue({
      id: "collab-1",
      owner_user_id: 77,
      application_user_id: null,
      kint: "10159",
      kkint: "{demo}",
      employee_code: "1854",
      company_code: "53",
      company_label: "53 - CBO",
      name: "AMADU SALVATORE",
      birth_date: "1967-02-26",
      contract_kind: "impiegato",
      operai_group: null,
      standard_daily_minutes: 385,
      is_active: true,
      last_seen_at: "2026-06-04T09:00:00Z",
      created_at: "2026-06-04T09:00:00Z",
      updated_at: "2026-06-04T09:05:00Z",
    });
  });

  function matrixRecord(overrides: Partial<PresenzeDailyRecord> = {}): PresenzeDailyRecord {
    return {
      ...baseDailyRecord,
      work_date: "2026-05-18",
      km_value: null,
      trasferta_minutes: null,
      straordinario_minutes: 0,
      effective_straordinario_minutes: 0,
      mpe_minutes: 0,
      effective_mpe_minutes: 0,
      effective_extra_minutes: 0,
      reperibilita_unit: "none",
      reperibilita_quantity: null,
      absence_minutes: 0,
      justified_minutes: 0,
      resolved_absence_cause: null,
      request_description: null,
      request_type: null,
      request_status: null,
      request_authorized_by: null,
      detail_requests: [],
      detail_anomalies: [],
      evidenze: null,
      stato: "Giornata regolare",
      detail_status: "Giornata regolare",
      operational_status: "ok",
      operational_notes: [],
      special_day: false,
      ...overrides,
    } as PresenzeDailyRecord;
  }

  async function renderMayMatrix(items?: PresenzeDailyRecord[]) {
    if (items) {
      mocks.listPresenzeDailyMatrixRecords.mockResolvedValue({ items, total: items.length, page: 1, page_size: 5000 });
      mocks.getPresenzeDailyRecord.mockImplementation(async (_token: string, recordId: string) => items.find((record) => record.id === recordId));
    }
    render(<PresenzeGiornalierePage />);
    fireEvent.change(await screen.findByLabelText("Mese operativo"), { target: { value: "2026-05" } });
    await screen.findByRole("button", { name: "AMADU SALVATORE", exact: true });
  }

  async function expectMatrixCollaborators(names: string[]) {
    await waitFor(() => {
      const table = within(screen.getByRole("table"));
      for (const name of ["AMADU SALVATORE", "PODDA RAIMONDO", "ZEDDA MARIO"]) {
        if (names.includes(name)) {
          expect(table.getByRole("button", { name, exact: true })).toBeInTheDocument();
        } else {
          expect(table.queryByRole("button", { name, exact: true })).not.toBeInTheDocument();
        }
      }
    });
  }

  function enableOperationalEditing(role = "hr_manager") {
    mocks.getCurrentUser.mockResolvedValue({ id: 12, role });
    mocks.getPresenzeAccessContext.mockResolvedValue({ can_view_all_data: true, is_supervisor: false });
  }

  async function openFirstMatrixDay() {
    const row = screen.getByRole("button", { name: "AMADU SALVATORE", exact: true }).closest("tr")!;
    fireEvent.click(within(row).getAllByRole("button")[1]);
    await screen.findByText("Rettifiche operative");
  }

  test("changes months across year boundaries and requests their actual date bounds", async () => {
    await renderMayMatrix();
    fireEvent.change(screen.getByLabelText("Mese operativo"), { target: { value: "2026-01" } });
    fireEvent.click(screen.getByRole("button", { name: "Mese precedente" }));
    expect(screen.getByLabelText("Mese operativo")).toHaveValue("2025-12");
    fireEvent.click(screen.getByRole("button", { name: "Mese successivo" }));
    expect(screen.getByLabelText("Mese operativo")).toHaveValue("2026-01");
    await waitFor(() => expect(mocks.listPresenzeDailyMatrixRecords).toHaveBeenCalledWith(
      expect.stringMatching(/^token-/), { dateFrom: "2025-12-01", dateTo: "2025-12-31", page: 1, pageSize: 5000 },
    ));
  });

  test("preserves the operative month and the open day when the month input is cleared", async () => {
    await renderMayMatrix([matrixRecord()]);
    await openFirstMatrixDay();
    const matrixCalls = mocks.listPresenzeDailyMatrixRecords.mock.calls.length;
    fireEvent.change(screen.getByLabelText("Mese operativo"), { target: { value: "" } });
    await act(async () => {});
    expect(screen.getByLabelText("Mese operativo")).toHaveValue("2026-05");
    expect(screen.getByText("Rettifiche operative")).toBeInTheDocument();
    expect(screen.getByRole("table")).toBeInTheDocument();
    expect(mocks.listPresenzeDailyMatrixRecords).toHaveBeenCalledTimes(matrixCalls);
    expect(mocks.updatePresenzeDailyRecord).not.toHaveBeenCalled();
    fireEvent.change(screen.getByLabelText("Mese operativo"), { target: { value: "2026-06" } });
    await waitFor(() => expect(mocks.listPresenzeDailyMatrixRecords).toHaveBeenCalledWith(
      expect.stringMatching(/^token-/), { dateFrom: "2026-06-01", dateTo: "2026-06-30", page: 1, pageSize: 5000 },
    ));
    expect(screen.getByLabelText("Mese operativo")).toHaveValue("2026-06");
    await waitFor(() => expect(screen.queryByText("Rettifiche operative")).not.toBeInTheDocument());
  });

  test.each([
    [{ operational_status: "unknown", detail_anomalies: [{ col_1: "Anomalia" }] }, "Anom"],
    [{ operational_status: "unknown", detail_error: "Errore dettaglio" }, "Anom"],
    [{ resolved_absence_cause: "ferie" }, "Fer"],
    [{ resolved_absence_cause: "permesso" }, "Perm"],
    [{ resolved_absence_cause: "malattia" }, "Mal"],
    [{ ordinary_minutes: 0, absence_minutes: 60 }, "1"],
    [{ ordinary_minutes: null, absence_minutes: null }, "·"],
    [{ operational_status: "in_analysis", resolved_absence_cause: "ferie" }, "Fer"],
    [{ operational_status: "in_analysis", resolved_absence_cause: "malattia" }, "Mal"],
    [{ operational_status: "in_analysis", detail_requests: [{ Descrizione: "Richiesta" }] }, "Rich"],
    [{ operational_status: "in_analysis" }, "Anom"],
    [{ operational_status: "blocking", detail_status: "Permesso" }, "Perm"],
    [{ operational_status: "blocking", detail_status: "Ferie" }, "Fer"],
    [{ operational_status: "blocking", detail_status: "Malattia" }, "Mal"],
    [{ operational_status: "blocking", detail_status: "Richiesta" }, "Rich"],
    [{ operational_status: "blocking", detail_status: "ALTRO" }, "altr"],
    [{ operational_status: "blocking", detail_status: "ABC" }, "abc"],
    [{ operational_status: "blocking", detail_status: null, stato: null }, "Anom"],
    [{ ordinary_minutes: 0, absence_minutes: 60, detail_status: "Giornata regolare" }, "1"],
    [{ operational_formula_code: null, ordinary_minutes: 0, absence_minutes: 0, punches: [], special_day: true, operational_worked_minutes: 0 }, "Fest"],
    [{ operational_formula_code: null, ordinary_minutes: 0, punches: [], special_day: true, operational_worked_minutes: null, teo_minutes: 60 }, "Fest"],
    [{ effective_extra_minutes: 60 }, "7"],
    [{ trasferta_minutes: 60 }, "7"],
    [{ km_value: 5 }, "7"],
    [{ detail_requests: [{ Descrizione: "Richiesta" }] }, "7"],
  ] satisfies Array<[Partial<PresenzeDailyRecord>, string]>)("renders the matrix classification for %j", async (values, label) => {
    const record = matrixRecord(values);
    await renderMayMatrix([record]);
    const row = screen.getByRole("button", { name: "AMADU SALVATORE", exact: true }).closest("tr")!;
    expect(within(row).getAllByRole("button")[1]).toHaveTextContent(label);
    await openFirstMatrixDay();
    expect(screen.getByText("Rettifiche operative")).toBeInTheDocument();
  });

  test.each([new Error("Errore sessione"), "non-error"])("shows session load failures (%s)", async (failure) => {
    mocks.getCurrentUser.mockRejectedValue(failure);
    render(<PresenzeGiornalierePage />);
    expect(await screen.findByText(failure instanceof Error ? failure.message : "Errore caricamento giornaliere")).toBeInTheDocument();
  });

  test.each([new Error("Errore cartellino"), "non-error"])("shows monthly matrix failures (%s)", async (failure) => {
    mocks.listPresenzeDailyMatrixRecords.mockRejectedValue(failure);
    render(<PresenzeGiornalierePage />);
    expect(await screen.findByText(failure instanceof Error ? failure.message : "Errore caricamento giornaliere")).toBeInTheDocument();
  });

  test("does not load data without an access token", () => {
    mocks.getStoredAccessToken.mockReturnValue(null);
    render(<PresenzeGiornalierePage />);
    expect(mocks.getCurrentUser).not.toHaveBeenCalled();
    expect(mocks.listPresenzeDailyMatrixRecords).not.toHaveBeenCalled();
  });

  test.each([new Error("Errore dettaglio"), "non-error"])("shows detail load failures (%s)", async (failure) => {
    await renderMayMatrix([matrixRecord()]);
    mocks.getPresenzeDailyRecord.mockRejectedValue(failure);
    await openFirstMatrixDay();
    expect(await screen.findByText(failure instanceof Error ? failure.message : "Errore caricamento dettaglio giornaliera")).toBeInTheDocument();
  });

  test("navigates adjacent days with buttons and keyboard, preserving input editing", async () => {
    await renderMayMatrix([
      matrixRecord({ id: "first", work_date: "2026-05-18" }),
      matrixRecord({ id: "second", work_date: "2026-05-19" }),
      matrixRecord({ id: "third", work_date: "2026-05-20" }),
    ]);
    await openFirstMatrixDay();
    fireEvent.click(screen.getByRole("button", { name: "Giorno successivo" }));
    expect(await screen.findByText(/2026-05-19 · martedì · AMADU/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Giorno precedente" }));
    expect(await screen.findByText(/2026-05-18 · lunedì · AMADU/)).toBeInTheDocument();
    fireEvent.keyDown(document.body, { key: "ArrowRight" });
    expect(await screen.findByText(/2026-05-19 · martedì · AMADU/)).toBeInTheDocument();
    fireEvent.keyDown(screen.getByLabelText("Nota validazione"), { key: "ArrowRight" });
    expect(screen.getByText(/2026-05-19 · martedì · AMADU/)).toBeInTheDocument();
    fireEvent.keyDown(document.body, { key: "ArrowLeft" });
    expect(await screen.findByText(/2026-05-18 · lunedì · AMADU/)).toBeInTheDocument();
    fireEvent.keyDown(document.body, { key: "ArrowLeft" });
    fireEvent.keyDown(document.body, { key: "Tab" });
    fireEvent.keyDown(screen.getByLabelText("Nota validazione"), { key: "Escape" });
    expect(screen.queryByText("Rettifiche operative")).not.toBeInTheDocument();
  });

  test("returns to the collaborator modal after closing a selected day", async () => {
    await renderMayMatrix([matrixRecord()]);
    fireEvent.click(screen.getByRole("button", { name: "AMADU SALVATORE", exact: true }));
    fireEvent.click(await screen.findByRole("button", { name: /2026-05-18.*Giornata regolare/ }));
    await screen.findByText("Rettifiche operative");
    fireEvent.click(screen.getByRole("button", { name: "Chiudi ✕" }));
    expect(await screen.findByRole("link", { name: "Apri scheda completa" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Chiudi ✕" }));
    expect(screen.queryByRole("link", { name: "Apri scheda completa" })).not.toBeInTheDocument();
  });

  test.each([
    ["30.6", 31], ["-2", 0], ["  ", null], ["not-a-number", undefined], ["24", undefined],
  ])("saves collaborator KM with normalization and no-op guards (%s)", async (raw, expected) => {
    enableOperationalEditing();
    const record = matrixRecord({ km_value: 24 });
    await renderMayMatrix([record]);
    mocks.updatePresenzeDailyRecord.mockImplementation(async (_token, _id, payload) => ({ ...record, ...payload }));
    fireEvent.click(screen.getByRole("button", { name: "AMADU SALVATORE", exact: true }));
    const input = await screen.findByLabelText("KM 2026-05-18");
    fireEvent.change(input, { target: { value: raw } });
    fireEvent.blur(input);
    if (expected === undefined) {
      expect(mocks.updatePresenzeDailyRecord).not.toHaveBeenCalled();
    } else {
      await waitFor(() => expect(mocks.updatePresenzeDailyRecord).toHaveBeenCalledWith(expect.stringMatching(/^token-/), record.id, { km_value: expected }));
    }
  });

  test.each([new Error("KM falliti"), "non-error"])("reports failures when saving inline KM (%s)", async (failure) => {
    enableOperationalEditing();
    await renderMayMatrix([matrixRecord()]);
    mocks.updatePresenzeDailyRecord.mockRejectedValue(failure);
    fireEvent.click(screen.getByRole("button", { name: "AMADU SALVATORE", exact: true }));
    const input = await screen.findByLabelText("KM 2026-05-18");
    fireEvent.change(input, { target: { value: "12" } });
    fireEvent.blur(input);
    expect(await screen.findByText(failure instanceof Error ? failure.message : "Errore salvataggio KM")).toBeInTheDocument();
  });

  test("toggles reperibilita in the collaborator list and restores it", async () => {
    enableOperationalEditing();
    const record = matrixRecord();
    await renderMayMatrix([record]);
    mocks.updatePresenzeDailyRecord.mockImplementation(async (_token, _id, payload) => ({ ...record, ...payload }));
    fireEvent.click(screen.getByRole("button", { name: "AMADU SALVATORE", exact: true }));
    fireEvent.click(await screen.findByRole("button", { name: "Rep", exact: true }));
    await waitFor(() => expect(mocks.updatePresenzeDailyRecord).toHaveBeenLastCalledWith(expect.stringMatching(/^token-/), record.id, { reperibilita_unit: "days", reperibilita_quantity: 1 }));
    await waitFor(() => expect(screen.getByRole("button", { name: "Rep", exact: true })).toBeEnabled());
    fireEvent.click(screen.getByRole("button", { name: "Rep", exact: true }));
    await waitFor(() => expect(mocks.updatePresenzeDailyRecord).toHaveBeenLastCalledWith(expect.stringMatching(/^token-/), record.id, { reperibilita_unit: "none", reperibilita_quantity: null }));
  });

  test.each([new Error("Reperibilita fallita"), "non-error"])("reports reperibilita save failures (%s)", async (failure) => {
    enableOperationalEditing();
    await renderMayMatrix([matrixRecord()]);
    mocks.updatePresenzeDailyRecord.mockRejectedValue(failure);
    fireEvent.click(screen.getByRole("button", { name: "AMADU SALVATORE", exact: true }));
    fireEvent.click(await screen.findByRole("button", { name: "Rep", exact: true }));
    expect(await screen.findByText(failure instanceof Error ? failure.message : "Errore salvataggio reperibilita")).toBeInTheDocument();
  });

  test("edits KM directly in the matrix and exits KM mode", async () => {
    enableOperationalEditing();
    const record = matrixRecord({ km_value: 3 });
    await renderMayMatrix([record]);
    mocks.updatePresenzeDailyRecord.mockResolvedValue({ ...record, km_value: 8 });
    fireEvent.click(screen.getByRole("button", { name: "Inserisci KM" }));
    const input = within(screen.getByRole("table")).getByRole("textbox");
    fireEvent.change(input, { target: { value: "8" } });
    fireEvent.blur(input);
    await waitFor(() => expect(mocks.updatePresenzeDailyRecord).toHaveBeenCalledWith(expect.stringMatching(/^token-/), record.id, { km_value: 8 }));
    fireEvent.click(screen.getByRole("button", { name: "Esci da inserimento KM" }));
    expect(within(screen.getByRole("table")).queryByRole("textbox")).not.toBeInTheDocument();
  });

  test.each([new Error("Rettifiche fallite"), "non-error"])("reports editor save failures (%s)", async (failure) => {
    enableOperationalEditing();
    await renderMayMatrix([matrixRecord()]);
    await openFirstMatrixDay();
    mocks.updatePresenzeDailyRecord.mockRejectedValue(failure);
    fireEvent.click(screen.getByRole("button", { name: "Salva rettifiche" }));
    expect(await screen.findByText(failure instanceof Error ? failure.message : "Errore salvataggio giornaliera")).toBeInTheDocument();
  });

  test.each([new Error("Validazione fallita"), "non-error"])("reports validation failures (%s)", async (failure) => {
    await renderMayMatrix([matrixRecord()]);
    await openFirstMatrixDay();
    mocks.updatePresenzeDailyRecord.mockRejectedValue(failure);
    fireEvent.click(screen.getByRole("button", { name: "Valida giornaliera" }));
    expect(await screen.findByText(failure instanceof Error ? failure.message : "Errore validazione giornaliera")).toBeInTheDocument();
  });

  test("removes validation and records an empty validation note as null", async () => {
    const record = matrixRecord({ validation_status: "validated", validated_at: "2026-05-18T10:00:00Z" });
    await renderMayMatrix([record]);
    await openFirstMatrixDay();
    mocks.updatePresenzeDailyRecord.mockResolvedValue({ ...record, validation_status: "pending" });
    fireEvent.click(screen.getByRole("button", { name: "Riapri validazione" }));
    await waitFor(() => expect(mocks.updatePresenzeDailyRecord).toHaveBeenCalledWith(expect.stringMatching(/^token-/), record.id, { validation_status: "pending", validation_note: null }));
    expect(await screen.findByText("Validazione rimossa per 2026-05-18.")).toBeInTheDocument();
  });

  test.each([
    [new Error("Refresh fallito"), "Refresh fallito"],
    ["non-error", "Errore avvio recupero dati da INAZ"],
    [new ApiError("Server error", undefined, 500), "Server error"],
  ])("reports INAZ enqueue failures (%s)", async (failure, message) => {
    await renderMayMatrix([matrixRecord()]);
    await openFirstMatrixDay();
    mocks.refreshPresenzeDailyRecordFromInaz.mockRejectedValue(failure);
    fireEvent.click(screen.getByRole("button", { name: /Sincronizza da INAZ/ }));
    expect(await screen.findByText(message)).toBeInTheDocument();
  });

  test.each([
    ["", "Il job di recupero non ha restituito dettagli."],
    ["worker process not found", "Il worker Presenze si e interrotto"],
    ["marked stale", "Il worker Presenze si e interrotto"],
    ["login.aspx", "INAZ ha ripresentato la pagina di login"],
    ["frame atteso non trovato", "INAZ ha ripresentato la pagina di login"],
    ["timeout cercando il frame di login", "INAZ ha ripresentato la pagina di login"],
    ["Errore upstream", "Recupero INAZ non completato: Errore upstream"],
  ])("polls failed INAZ jobs and explains %s", async (detail, message) => {
    await renderMayMatrix([matrixRecord()]);
    await openFirstMatrixDay();
    mocks.getPresenzeSyncJob.mockResolvedValue({ id: "sync-job-1", status: "failed", error_detail: detail });
    vi.useFakeTimers();
    await act(async () => fireEvent.click(screen.getByRole("button", { name: /Sincronizza da INAZ/ })));
    await act(async () => vi.advanceTimersByTimeAsync(2000));
    expect(screen.getAllByText(new RegExp(message.replaceAll(".", "\\."))).length).toBeGreaterThan(0);
    expect(screen.getByText("Sync INAZ failed")).toBeInTheDocument();
  });

  test.each([new Error("Polling fallito"), "non-error"])("reports INAZ polling failures (%s)", async (failure) => {
    await renderMayMatrix([matrixRecord()]);
    await openFirstMatrixDay();
    mocks.getPresenzeSyncJob.mockRejectedValue(failure);
    vi.useFakeTimers();
    await act(async () => fireEvent.click(screen.getByRole("button", { name: /Sincronizza da INAZ/ })));
    await act(async () => vi.advanceTimersByTimeAsync(2000));
    expect(screen.getByText(failure instanceof Error ? failure.message : "Errore monitoraggio recupero dati da INAZ")).toBeInTheDocument();
  });

  test("continues polling a running INAZ job and applies its completed daily record", async () => {
    const record = matrixRecord();
    await renderMayMatrix([record]);
    await openFirstMatrixDay();
    mocks.getPresenzeSyncJob.mockResolvedValueOnce({ id: "sync-job-1", status: "running" }).mockResolvedValueOnce({ id: "sync-job-1", status: "completed" });
    mocks.getPresenzeDailyRecord.mockResolvedValue({ ...record, km_value: 99 });
    vi.useFakeTimers();
    await act(async () => fireEvent.click(screen.getByRole("button", { name: /Sincronizza da INAZ/ })));
    await act(async () => vi.advanceTimersByTimeAsync(2000));
    expect(screen.getByText("Sync INAZ running")).toBeInTheDocument();
    await act(async () => vi.advanceTimersByTimeAsync(2000));
    expect(screen.getAllByText("Dati INAZ recuperati per 2026-05-18.")).toHaveLength(2);
    expect(screen.getByLabelText("Chilometri auto")).toHaveValue("99");
  });

  test("cancels an in-flight INAZ poll when the day modal closes", async () => {
    await renderMayMatrix([matrixRecord()]);
    await openFirstMatrixDay();
    let resolveJob!: (job: { id: string; status: string }) => void;
    mocks.getPresenzeSyncJob.mockImplementation(() => new Promise((resolve) => { resolveJob = resolve; }));
    vi.useFakeTimers();
    await act(async () => fireEvent.click(screen.getByRole("button", { name: /Sincronizza da INAZ/ })));
    await act(async () => vi.advanceTimersByTimeAsync(2000));
    fireEvent.click(screen.getByRole("button", { name: "Chiudi ✕" }));
    await act(async () => resolveJob({ id: "sync-job-1", status: "completed" }));
    expect(screen.queryByText(/Dati INAZ recuperati/)).not.toBeInTheDocument();
  });

  test("drags the monthly matrix horizontally and prevents a drag from opening a day", async () => {
    await renderMayMatrix([matrixRecord()]);
    const viewport = screen.getByRole("table").parentElement!;
    viewport.scrollLeft = 30;
    fireEvent.mouseMove(viewport, { clientX: 10 });
    fireEvent.mouseUp(viewport);
    fireEvent.mouseDown(viewport, { button: 2, clientX: 10 });
    expect(viewport).not.toHaveClass("cursor-grabbing");
    fireEvent.mouseDown(viewport, { button: 0, clientX: 10 });
    expect(viewport).toHaveClass("cursor-grabbing");
    fireEvent.mouseMove(viewport, { clientX: 12 });
    fireEvent.mouseMove(viewport, { clientX: 25 });
    expect(viewport.scrollLeft).toBe(15);
    fireEvent.mouseLeave(viewport);
    const row = screen.getByRole("button", { name: "AMADU SALVATORE", exact: true }).closest("tr")!;
    fireEvent.click(within(row).getAllByRole("button")[1]);
    expect(screen.queryByText("Rettifiche operative")).not.toBeInTheDocument();
    await openFirstMatrixDay();
  });

  test("does not start dragging while an inline KM input is being edited", async () => {
    enableOperationalEditing();
    await renderMayMatrix([matrixRecord()]);
    fireEvent.click(screen.getByRole("button", { name: "Inserisci KM" }));
    const viewport = screen.getByRole("table").parentElement!;
    fireEvent.mouseDown(within(screen.getByRole("table")).getByRole("textbox"), { button: 0 });
    expect(viewport).not.toHaveClass("cursor-grabbing");
  });

  test("filters and groups blocking and analysis cases without changing the matrix", async () => {
    await renderMayMatrix([
      matrixRecord({ id: "analysis", operational_status: "in_analysis", detail_anomalies: [{ col_1: "Analisi A" }] }),
      matrixRecord({ id: "blocking", collaborator_id: "collab-2", operational_status: "blocking", operational_missing_minutes: 60, detail_anomalies: [{ anomaliagiornata: "Blocco B" }] }),
      matrixRecord({ id: "blocking-2", collaborator_id: "collab-2", work_date: "2026-05-19", operational_status: "blocking", operational_missing_minutes: 60, detail_anomalies: [{ other: "Blocco C", empty: "" }] }),
      matrixRecord({ id: "analysis-2", collaborator_id: "collab-3", operational_status: "in_analysis", detail_anomalies: [{}], detail_error: "Analisi D", operational_formula_code: null }),
    ]);
    fireEvent.click(screen.getByRole("button", { name: "Vedi anomalie mese (4)" }));
    fireEvent.click(screen.getByRole("button", { name: "Correggere subito (2)" }));
    expect(screen.getByText("Mostra solo le giornate bloccanti")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Da verificare (2)" }));
    expect(screen.getByText("Mostra solo i casi da verificare")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Collaboratore", exact: true }));
    expect(screen.getByText("Analisi A")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Tutte (4)" }));
    fireEvent.click(screen.getByRole("button", { name: "Giorno", exact: true }));
    expect(screen.getByText("Blocco B")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Solo anomalie", exact: true }));
    fireEvent.click(screen.getByRole("button", { name: "Mostra tutti i collaboratori" }));
    fireEvent.click(screen.getByRole("button", { name: "Nascondi elenco anomalie" }));
    expect(screen.queryByText("Anomalie del mese")).not.toBeInTheDocument();
  });

  test("shows an empty anomaly panel when the month has no critical days", async () => {
    await renderMayMatrix([matrixRecord()]);
    fireEvent.click(screen.getByRole("button", { name: "Vedi anomalie mese (0)" }));
    expect(screen.getByText("Nessuna anomalia o giornata in analisi nel mese selezionato.")).toBeInTheDocument();
  });

  test("loads all matrix pages and stops on an empty page even if the reported total is larger", async () => {
    mocks.listPresenzeDailyMatrixRecords.mockImplementation(async (_token, params) => ({
      items: params.page === 1 ? [matrixRecord()] : [], total: 10, page: params.page, page_size: 5000,
    }));
    await renderMayMatrix();
    await waitFor(() => expect(mocks.listPresenzeDailyMatrixRecords).toHaveBeenCalledWith(
      expect.stringMatching(/^token-/), { dateFrom: "2026-05-01", dateTo: "2026-05-31", page: 2, pageSize: 5000 },
    ));
    expect(screen.getByRole("button", { name: "AMADU SALVATORE", exact: true })).toBeInTheDocument();
  });

  test.each(["idle", "timeout"] as const)("renders large matrices progressively using %s callbacks", async (mode) => {
    const template = (await mocks.listAllPresenzeCollaborators())[0];
    const collaborators = Array.from({ length: 100 }, (_value, index) => ({
      ...template, id: `collab-${index}`, name: index === 0 ? "AMADU SALVATORE" : `PERSONA ${String(index).padStart(3, "0")}`,
    }));
    const records = collaborators.map((collaborator) => matrixRecord({ id: `record-${collaborator.id}`, collaborator_id: collaborator.id }));
    mocks.listAllPresenzeCollaborators.mockResolvedValue(collaborators);
    mocks.listPresenzeDailyMatrixRecords.mockResolvedValue({ items: records, total: records.length, page: 1, page_size: 5000 });
    const callbacks: Array<() => void> = [];
    if (mode === "idle") {
      vi.stubGlobal("requestIdleCallback", vi.fn((callback: () => void) => { callbacks.push(callback); return callbacks.length; }));
      vi.stubGlobal("cancelIdleCallback", vi.fn());
    } else {
      vi.useFakeTimers();
    }
    const view = render(<PresenzeGiornalierePage />);
    await act(async () => {});
    const table = screen.getByRole("table");
    expect(within(table).getAllByRole("row")).toHaveLength(37);
    if (mode === "idle") {
      await act(async () => callbacks.shift()!());
      await act(async () => callbacks.shift()!());
    } else {
      await act(async () => vi.advanceTimersByTimeAsync(160));
    }
    expect(within(table).getAllByRole("row")).toHaveLength(101);
    view.unmount();
  });

  test("ignores a cancelled progressive-render callback after unmount", async () => {
    const template = (await mocks.listAllPresenzeCollaborators())[0];
    const collaborators = Array.from({ length: 40 }, (_value, index) => ({ ...template, id: `collab-${index}`, name: `PERSONA ${index}` }));
    const records = collaborators.map((collaborator) => matrixRecord({ id: collaborator.id, collaborator_id: collaborator.id }));
    mocks.listAllPresenzeCollaborators.mockResolvedValue(collaborators);
    mocks.listPresenzeDailyMatrixRecords.mockResolvedValue({ items: records, total: 40, page: 1, page_size: 5000 });
    let callback!: () => void;
    const cancel = vi.fn();
    vi.stubGlobal("requestIdleCallback", vi.fn((pending: () => void) => { callback = pending; return 3; }));
    vi.stubGlobal("cancelIdleCallback", cancel);
    const view = render(<PresenzeGiornalierePage />);
    await screen.findByRole("button", { name: "PERSONA 0", exact: true });
    view.unmount();
    expect(cancel).toHaveBeenCalledWith(3);
    expect(() => callback()).not.toThrow();
  });

  test("preserves a fully expanded matrix when saving KM recalculates its rows", async () => {
    enableOperationalEditing();
    const template = (await mocks.listAllPresenzeCollaborators())[0];
    const collaborators = Array.from({ length: 40 }, (_value, index) => ({
      ...template, id: `collab-${index}`, name: index === 0 ? "AMADU SALVATORE" : `PERSONA ${String(index).padStart(2, "0")}`,
    }));
    const records = collaborators.map((collaborator) => matrixRecord({ id: `record-${collaborator.id}`, collaborator_id: collaborator.id }));
    mocks.listAllPresenzeCollaborators.mockResolvedValue(collaborators);
    const callbacks = new Map<number, () => void>();
    let callbackSequence = 0;
    vi.stubGlobal("requestIdleCallback", vi.fn((callback: () => void) => {
      callbackSequence += 1;
      callbacks.set(callbackSequence, callback);
      return callbackSequence;
    }));
    vi.stubGlobal("cancelIdleCallback", vi.fn((handle: number) => callbacks.delete(handle)));
    await renderMayMatrix(records);
    const table = within(screen.getByRole("table"));
    expect(table.getAllByRole("row")).toHaveLength(37);
    const [initialHandle, initialCallback] = callbacks.entries().next().value!;
    callbacks.delete(initialHandle);
    await act(async () => initialCallback());
    expect(table.getAllByRole("row")).toHaveLength(41);
    mocks.updatePresenzeDailyRecord.mockResolvedValue({ ...records[0], km_value: 9 });
    fireEvent.click(screen.getByRole("button", { name: "Inserisci KM" }));
    const input = within(screen.getByRole("table")).getAllByRole("textbox")[0];
    fireEvent.change(input, { target: { value: "9" } });
    fireEvent.blur(input);
    await waitFor(() => expect(mocks.updatePresenzeDailyRecord).toHaveBeenCalledWith(
      expect.stringMatching(/^token-/), records[0].id, { km_value: 9 },
    ));
    await waitFor(() => expect(callbacks.size).toBe(1));
    const [reloadHandle, reloadCallback] = callbacks.entries().next().value!;
    callbacks.delete(reloadHandle);
    await act(async () => reloadCallback());
    expect(within(screen.getByRole("table")).getAllByRole("row")).toHaveLength(41);
    expect(within(screen.getByRole("table")).getAllByRole("textbox")[0]).toHaveValue("9");
    expect(callbacks.size).toBe(0);
  });

  test.each([new Error("Profilo fallito"), "non-error"])("reports contract profile save failures (%s)", async (failure) => {
    enableOperationalEditing("admin");
    await renderMayMatrix([matrixRecord()]);
    fireEvent.click(screen.getByRole("button", { name: "AMADU SALVATORE", exact: true }));
    fireEvent.click(await screen.findByRole("button", { name: /Modifica profilo/ }));
    mocks.updatePresenzeCollaboratorContractProfile.mockRejectedValue(failure);
    fireEvent.click(screen.getByRole("button", { name: "Salva profilo" }));
    expect(await screen.findByText(failure instanceof Error ? failure.message : "Errore salvataggio profilo contrattuale")).toBeInTheDocument();
  });

  test("requires an operaio group and saves an unset contract with empty minutes", async () => {
    enableOperationalEditing("admin");
    await renderMayMatrix([matrixRecord()]);
    fireEvent.click(screen.getByRole("button", { name: "AMADU SALVATORE", exact: true }));
    fireEvent.click(await screen.findByRole("button", { name: /Modifica profilo/ }));
    fireEvent.change(screen.getByLabelText("Gruppo operai collaboratore"), { target: { value: "" } });
    fireEvent.click(screen.getByRole("button", { name: "Salva profilo" }));
    expect(await screen.findByText("Per il profilo operaio devi indicare il gruppo operaio.")).toBeInTheDocument();
    expect(mocks.updatePresenzeCollaboratorContractProfile).not.toHaveBeenCalled();
    fireEvent.change(screen.getByLabelText("Gruppo operai collaboratore"), { target: { value: "agrario" } });
    fireEvent.change(screen.getByLabelText("Tipo contratto collaboratore"), { target: { value: "altro" } });
    expect(screen.getByLabelText("Gruppo operai collaboratore")).toBeDisabled();
    fireEvent.change(screen.getByLabelText("Tipo contratto collaboratore"), { target: { value: "" } });
    fireEvent.change(screen.getByLabelText("Minuti standard collaboratore"), { target: { value: "" } });
    fireEvent.click(screen.getByRole("button", { name: /Chiudi editor/ }));
    expect(screen.queryByLabelText("Tipo contratto collaboratore")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Modifica profilo/ }));
    fireEvent.click(screen.getByRole("button", { name: "Salva profilo" }));
    await waitFor(() => expect(mocks.updatePresenzeCollaboratorContractProfile).toHaveBeenCalledWith(expect.stringMatching(/^token-/), "collab-1", { contract_kind: null, operai_group: null, standard_daily_minutes: null }));
    await waitFor(() => expect(screen.queryByLabelText("Tipo contratto collaboratore")).not.toBeInTheDocument());
  });

  test("saves minutes, travel and empty notes without supervisor permissions", async () => {
    mocks.getCurrentUser.mockResolvedValue({ id: 12, role: "viewer" });
    mocks.getPresenzeAccessContext.mockResolvedValue({ can_view_all_data: false, is_supervisor: false });
    const record = matrixRecord({ owner_user_id: 12, reperibilita_unit: "days", reperibilita_quantity: 1 });
    await renderMayMatrix([record]);
    await openFirstMatrixDay();
    fireEvent.change(screen.getByLabelText("Ore / minuti"), { target: { value: "90" } });
    fireEvent.click(screen.getByLabelText("Comune montano"));
    fireEvent.change(screen.getByLabelText("Straordinario override"), { target: { value: "invalid" } });
    fireEvent.change(screen.getByLabelText("Maggior presenza override"), { target: { value: "-5" } });
    fireEvent.click(screen.getByLabelText("Reperibilita giornaliera"));
    fireEvent.click(screen.getByRole("button", { name: "Salva rettifiche" }));
    await waitFor(() => expect(mocks.updatePresenzeDailyRecord).toHaveBeenCalledWith(expect.stringMatching(/^token-/), record.id, {
      km_value: null, trasferta_minutes: 90, trasferta_montano: true, reperibilita_unit: "none", reperibilita_quantity: null,
      override_straordinario_minutes: null, override_mpe_minutes: 0, manual_note: null,
    }));
    expect(screen.queryByLabelText("Nota validazione")).not.toBeInTheDocument();
  });

  test.each([
    [{ trasferta_minutes: 60, trasferta_montano: true }, "1.00 h · comune montano"],
    [{ trasferta_minutes: null, trasferta_montano: true }, "Comune montano (X)"],
    [{ trasferta_minutes: 0 }, "Nessuna"],
    [{ trasferta_minutes: 60 }, "1.00 h"],
    [{ reperibilita_unit: "hours", reperibilita_quantity: 2 }, "2 ore"],
    [{ reperibilita_unit: "shifts", reperibilita_quantity: null }, "— turni"],
    [{ reperibilita_unit: "days", reperibilita_quantity: 0 }, "0 giorni"],
    [{ reperibilita_unit: "days", reperibilita_quantity: null }, "— giorni"],
    [{ operational_status: "blocking", effective_extra_minutes: 240, operational_missing_minutes: 0 }, "Rientra in anomalia per extra/straordinario oltre 3 ore (4.00 h)."],
    [{ operational_status: "ok", resolved_absence_cause: "ferie", absence_minutes: 60 }, "Ferie"],
    [{ request_status: "ACC", request_description: "Timbratura E", request_authorized_by: "" }, "Timbratura di entrata autorizzata"],
    [{ request_status: "ACC", request_description: "Timbratura U", request_authorized_by: "" }, "Timbratura di uscita autorizzata"],
    [{ request_status: "ACC", request_description: "Richiesta generica" }, "Richiesta generica"],
    [{ request_description: "Permesso (Lunga descrizione)", absence_minutes: 30 }, "Permesso (Lunga descrizione)"],
    [{ operational_status: "blocking", detail_anomalies: [{ empty: "", null: null }], operational_formula_code: null, detail_status: null, stato: null }, "Anomalia da verificare"],
    [{ operational_status: "blocking", detail_anomalies: [], operational_formula_code: null, operational_notes: ["Nota operativa"] }, "Nota operativa"],
  ] satisfies Array<[Partial<PresenzeDailyRecord>, string]>)("shows operational detail boundary values %j", async (values, expected) => {
    enableOperationalEditing();
    await renderMayMatrix([matrixRecord(values)]);
    if (expected === "Anomalia da verificare") {
      fireEvent.click(screen.getByRole("button", { name: "Vedi anomalie mese (1)" }));
    }
    await openFirstMatrixDay();
    expect(screen.getAllByText(expected).length).toBeGreaterThan(0);
  });

  test.each([
    [null, [], "—"],
    ["E", [{ time: null, direction: "E", terminal_label: null }, { time: "12:30", direction: "U", terminal_label: "TERMINAL" }], "06:55 (ingresso autorizzato)"],
    ["U", [{ time: "06:55", direction: "E", terminal_label: "TERMINAL-" }, { time: null, direction: "U", terminal_label: null }], "12:30 (uscita autorizzata)"],
    [null, [{ time: "9:00", direction: "U", terminal_label: null }, { time: "9:00", direction: "E", terminal_label: null }, { time: "9:00", direction: "X", terminal_label: null }, { time: "invalid", direction: null, terminal_label: null }], "09:00"],
  ])("renders detail punch times, authorization and stable direction ordering (%s)", async (direction, punches, expected) => {
    const record = matrixRecord({
      punches: direction ? baseDailyRecord.punches : [],
      detail_punch_rows: punches,
      request_status: direction ? "ACC" : null,
      request_description: direction ? `Timbratura ${direction}` : null,
      request_authorized_by: null,
    });
    await renderMayMatrix([record]);
    await openFirstMatrixDay();
    expect(screen.getAllByText(expected).length).toBeGreaterThan(0);
  });

  test("uses detail punches when no paired punch exists and includes anomaly metadata", async () => {
    const record = matrixRecord({
      punches: [], detail_punch_rows: [
        { time: null, direction: null, terminal_label: null },
        { time: "8:05:00", direction: "E", terminal_label: "FENO-Fenoso" },
        { time: "12:00", direction: "U", terminal_label: "FENO-Fenoso" },
      ],
      detail_anomalies: [{ col_1: "Anomalia test", Descrizione: "Dettaglio utile", Vuoto: "" }, { altro: "seconda" }],
      detail_error: "Dettaglio INAZ incompleto",
    });
    await renderMayMatrix([record]);
    await openFirstMatrixDay();
    expect(screen.getByText("08:05")).toBeInTheDocument();
    expect(screen.getByText("Anomalia test")).toBeInTheDocument();
    expect(screen.getByText("Anomalia 2")).toBeInTheDocument();
    expect(screen.getByText("Dettaglio INAZ incompleto")).toBeInTheDocument();
    expect(screen.getByText(/Dettaglio utile/)).toBeInTheDocument();
  });

  test("preserves identical paired/detail punches when authorization provides extra information", async () => {
    await renderMayMatrix([matrixRecord({
      request_status: "ACC", request_description: "Timbratura E",
      detail_punch_rows: [
        { time: "06:55", direction: "E", terminal_label: "FENO-Fenoso" },
        { time: "12:30", direction: "U", terminal_label: "FENO-Fenoso" },
      ],
    })]);
    await openFirstMatrixDay();
    expect(screen.getByText("06:55 (ingresso autorizzato)")).toBeInTheDocument();
  });

  test.each([
    ["blocking", "anom"], ["ok", "valid"],
  ] as const)("summarizes an unworked Saturday with %s status", async (status, expected) => {
    await renderMayMatrix([matrixRecord({
      work_date: "2026-05-16", operational_status: status, operational_worked_minutes: 0,
      ordinary_minutes: 0, punches: [], request_status: "ACC",
    })]);
    expect(screen.getByText(`3° ${expected}`)).toBeInTheDocument();
  });

  test.each([null, "quadro"] as const)("renders unset profile defaults (%s)", async (kind) => {
    enableOperationalEditing("admin");
    const collaborators = await mocks.listAllPresenzeCollaborators();
    mocks.listAllPresenzeCollaborators.mockResolvedValue([{ ...collaborators[0], contract_kind: kind, operai_group: null, standard_daily_minutes: null }]);
    await renderMayMatrix([matrixRecord()]);
    expect(screen.getByRole("button", { name: "Profilo non impostato (1)" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "AMADU SALVATORE", exact: true }));
    fireEvent.click(await screen.findByRole("button", { name: /Modifica profilo/ }));
    expect(screen.getByLabelText("Minuti standard collaboratore")).toHaveValue("");
    fireEvent.change(screen.getByLabelText("Tipo contratto collaboratore"), { target: { value: "operaio" } });
    expect(screen.getByLabelText("Minuti standard collaboratore")).toHaveValue("420");
    fireEvent.change(screen.getByLabelText("Minuti standard collaboratore"), { target: { value: "" } });
    fireEvent.change(screen.getByLabelText("Tipo contratto collaboratore"), { target: { value: "impiegato" } });
    expect(screen.getByLabelText("Minuti standard collaboratore")).toHaveValue("385");
  });

  test.each([
    [{ operational_formula_code: null, operational_worked_minutes: 0, ordinary_minutes: 0, special_day: true }, "6.5"],
    [{ operational_formula_code: null, operational_worked_minutes: 0, ordinary_minutes: 60, special_day: true }, "1"],
    [{ operational_formula_code: null, operational_worked_minutes: 0, ordinary_minutes: 0, special_day: true, punches: [{ ...baseDailyRecord.punches[0], entry_time: null, exit_time: "12:30" }] }, "6.5"],
    [{ operational_formula_code: null, operational_worked_minutes: 0, ordinary_minutes: 0, special_day: true, punches: [{ ...baseDailyRecord.punches[0], entry_time: null, exit_time: null }] }, "Fest"],
    [{ operational_status: "blocking", detail_status: "Anomalia" }, "Anom"],
    [{ ordinary_minutes: 0, absence_minutes: null, justified_minutes: 60, detail_status: "Assenza", operational_status: "unknown" }, "·"],
  ] satisfies Array<[Partial<PresenzeDailyRecord>, string]>)("uses available worked-time evidence for %j", async (values, expected) => {
    await renderMayMatrix([matrixRecord(values)]);
    const row = screen.getByRole("button", { name: "AMADU SALVATORE", exact: true }).closest("tr")!;
    expect(within(row).getAllByRole("button")[1]).toHaveTextContent(expected);
  });

  test.each([
    [{ resolved_absence_cause: "ferie" }, "warning"],
    [{ resolved_absence_cause: "permesso" }, "warning"],
    [{ resolved_absence_cause: "malattia" }, "warning"],
    [{ special_day: true }, "warning"],
    [{ ordinary_minutes: 60 }, "success"],
    [{ ordinary_minutes: 0, absence_minutes: 60 }, "neutral"],
  ] satisfies Array<[Partial<PresenzeDailyRecord>, string]>)("selects the detail badge tone using cell kind when INAZ has no regular status %j", async (values, tone) => {
    await renderMayMatrix([matrixRecord({ detail_status: "Status INAZ", ...values })]);
    await openFirstMatrixDay();
    expect(screen.getByText("Status INAZ")).toHaveAttribute("data-variant", tone);
  });

  test("opens the first critical day and the day-group anomaly card", async () => {
    await renderMayMatrix([matrixRecord({ operational_status: "blocking", operational_missing_minutes: 60, detail_anomalies: [{ col_1: "Criticita test" }] })]);
    fireEvent.click(screen.getByRole("button", { name: "Vedi anomalie mese (1)" }));
    fireEvent.click(screen.getByRole("button", { name: "Apri la prima giornata critica" }));
    expect(await screen.findByText("Rettifiche operative")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Chiudi ✕" }));
    fireEvent.click(screen.getByRole("button", { name: /AMADU SALVATORE.*Criticita test/ }));
    expect(await screen.findByText("Rettifiche operative")).toBeInTheDocument();
  });

  test("closes the collaborator modal through its backdrop", async () => {
    await renderMayMatrix([matrixRecord()]);
    fireEvent.click(screen.getByRole("button", { name: "AMADU SALVATORE", exact: true }));
    const title = await screen.findByRole("heading", { name: "AMADU SALVATORE" });
    fireEvent.click(title.closest(".fixed")!);
    expect(screen.queryByRole("heading", { name: "AMADU SALVATORE" })).not.toBeInTheDocument();
  });

  test("renders a single detail entry punch with missing time and no paired authorization fallback", async () => {
    await renderMayMatrix([matrixRecord({
      punches: [], request_status: "ACC", request_description: "Timbratura E", request_authorized_by: null,
      detail_punch_rows: [{ time: null, direction: "E", terminal_label: null }],
    })]);
    await openFirstMatrixDay();
    expect(screen.getByText("Riga 1")).toBeInTheDocument();
    expect(screen.getAllByText("—").length).toBeGreaterThan(0);
  });

  test("sorts critical collaborators by severity, count and name and preserves unknown identifiers", async () => {
    await renderMayMatrix([
      matrixRecord({ operational_status: "in_analysis" }),
      matrixRecord({ id: "amadu-next", work_date: "2026-05-19", operational_status: "in_analysis" }),
      matrixRecord({ id: "podda", collaborator_id: "collab-2", operational_status: "in_analysis" }),
      matrixRecord({ id: "zedda", collaborator_id: "collab-3", operational_status: "in_analysis" }),
      matrixRecord({ id: "orphan-1", collaborator_id: "missing-1", operational_status: "blocking", operational_missing_minutes: 60, schedule_code: null, detail_programmed_schedule: null }),
      matrixRecord({ id: "orphan-2", collaborator_id: "missing-2", operational_status: "blocking", operational_missing_minutes: 60, schedule_code: null, detail_programmed_schedule: null }),
    ]);
    fireEvent.click(screen.getByRole("button", { name: "Vedi anomalie mese (6)" }));
    fireEvent.click(screen.getByRole("button", { name: "Collaboratore", exact: true }));
    expect(screen.getAllByText("missing-1").length).toBeGreaterThan(0);
    expect(screen.getByText("2 giornate aperte nel mese")).toBeInTheDocument();
    const group = screen.getByText("missing-1").closest("section")!;
    fireEvent.click(within(group).getByRole("button"));
    expect(await screen.findByText("Rettifiche operative")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Sincronizza da INAZ/ })).toBeDisabled();
  });

  test("cancels a finished INAZ job while the updated record is still loading", async () => {
    await renderMayMatrix([matrixRecord()]);
    await openFirstMatrixDay();
    let resolveRecord!: (record: PresenzeDailyRecord) => void;
    mocks.getPresenzeDailyRecord.mockImplementation(() => new Promise((resolve) => { resolveRecord = resolve; }));
    vi.useFakeTimers();
    await act(async () => fireEvent.click(screen.getByRole("button", { name: /Sincronizza da INAZ/ })));
    await act(async () => vi.advanceTimersByTimeAsync(2000));
    fireEvent.click(screen.getByRole("button", { name: "Chiudi ✕" }));
    await act(async () => resolveRecord(matrixRecord()));
    expect(screen.queryByText(/Dati INAZ recuperati/)).not.toBeInTheDocument();
  });

  test("ignores a failed INAZ poll after its day has been closed", async () => {
    await renderMayMatrix([matrixRecord()]);
    await openFirstMatrixDay();
    let rejectJob!: (error: Error) => void;
    mocks.getPresenzeSyncJob.mockImplementation(() => new Promise((_resolve, reject) => { rejectJob = reject; }));
    vi.useFakeTimers();
    await act(async () => fireEvent.click(screen.getByRole("button", { name: /Sincronizza da INAZ/ })));
    await act(async () => vi.advanceTimersByTimeAsync(2000));
    fireEvent.click(screen.getByRole("button", { name: "Chiudi ✕" }));
    await act(async () => rejectJob(new Error("Errore dopo chiusura")));
    expect(screen.queryByText("Errore dopo chiusura")).not.toBeInTheDocument();
  });

  test.each(["km", "reperibilita", "editor", "validation", "contract", "refresh"] as const)("does not submit %s after the access token expires", async (action) => {
    enableOperationalEditing("admin");
    await renderMayMatrix([matrixRecord()]);
    if (["km", "reperibilita", "contract"].includes(action)) {
      fireEvent.click(screen.getByRole("button", { name: "AMADU SALVATORE", exact: true }));
      await screen.findByRole("link", { name: "Apri scheda completa" });
      if (action === "contract") fireEvent.click(screen.getByRole("button", { name: /Modifica profilo/ }));
    } else {
      await openFirstMatrixDay();
    }
    mocks.getStoredAccessToken.mockReturnValue(null);
    if (action === "km") {
      const input = screen.getByLabelText("KM 2026-05-18");
      fireEvent.change(input, { target: { value: "99" } });
      fireEvent.blur(input);
    } else {
      const labels = { reperibilita: "Rep", editor: "Salva rettifiche", validation: "Valida giornaliera", contract: "Salva profilo", refresh: /Sincronizza da INAZ/ };
      fireEvent.click(screen.getByRole("button", { name: labels[action], exact: true }));
    }
    expect(mocks.updatePresenzeDailyRecord).not.toHaveBeenCalled();
    expect(mocks.updatePresenzeCollaboratorContractProfile).not.toHaveBeenCalled();
    expect(mocks.refreshPresenzeDailyRecordFromInaz).not.toHaveBeenCalled();
  });

  test("displays absent metrics, null absence causes and fallback raw overtime safely", async () => {
    await renderMayMatrix([matrixRecord({
      operational_formula_code: null, operational_worked_minutes: null, ordinary_minutes: null, teo_minutes: null,
      absence_minutes: null, justified_minutes: null, effective_extra_minutes: null,
      effective_straordinario_minutes: null, straordinario_minutes: null, effective_mpe_minutes: null, mpe_minutes: null,
      request_status: "ACC", request_description: "", detail_status: null, stato: null, detail_time_slots: null,
      punches: [{ ...baseDailyRecord.punches[0], entry_time: null, exit_time: null, terminal_label: null }],
      detail_punch_rows: [], validation_note: "Verificata in precedenza",
    })]);
    await openFirstMatrixDay();
    expect(screen.getAllByText("—").length).toBeGreaterThan(0);
    expect(screen.getByText("Extra 0.00 h")).toBeInTheDocument();
  });

  test("uses unknown absence causes in both matrix and collaborator summaries", async () => {
    await renderMayMatrix([matrixRecord({ resolved_absence_cause: "causa_nuova", absence_minutes: 60 })]);
    expect(screen.getByText("causa nuova")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "AMADU SALVATORE", exact: true }));
    expect(screen.getAllByText("causa nuova")).toHaveLength(2);
  });

  test("shows existing validation notes to collaborators who cannot validate", async () => {
    mocks.getPresenzeAccessContext.mockResolvedValue({ can_view_all_data: false, is_supervisor: false });
    await renderMayMatrix([matrixRecord({ validation_note: "Nota registrata" })]);
    await openFirstMatrixDay();
    expect(screen.getByText("Nota registrata")).toBeInTheDocument();
    expect(screen.queryByLabelText("Nota validazione")).not.toBeInTheDocument();
  });

  test("does not expose operational extras for ferie but still allows validation", async () => {
    enableOperationalEditing();
    await renderMayMatrix([matrixRecord({ resolved_absence_cause: "ferie", absence_minutes: 60 })]);
    await openFirstMatrixDay();
    expect(screen.getByLabelText("Chilometri auto")).toBeDisabled();
    expect(screen.getByLabelText("Comune montano")).toBeDisabled();
    expect(screen.getByLabelText("Reperibilita giornaliera")).toBeDisabled();
    expect(screen.getByRole("button", { name: "Valida giornaliera" })).toBeEnabled();
  });

  test("converts legacy hourly reperibilita to none from the collaborator list", async () => {
    enableOperationalEditing();
    await renderMayMatrix([matrixRecord({ reperibilita_unit: "hours", reperibilita_quantity: null })]);
    fireEvent.click(screen.getByRole("button", { name: "AMADU SALVATORE", exact: true }));
    fireEvent.click(await screen.findByRole("button", { name: "Rep", exact: true }));
    await waitFor(() => expect(mocks.updatePresenzeDailyRecord).toHaveBeenCalledWith(expect.stringMatching(/^token-/), "record-1", { reperibilita_unit: "none", reperibilita_quantity: null }));
  });

  test("shows a Saturday without work, requests or absence without a summary entry", async () => {
    await renderMayMatrix([matrixRecord({ work_date: "2026-05-16", operational_worked_minutes: null, ordinary_minutes: null, punches: [] })]);
    expect(screen.queryByText("Sabati mese")).not.toBeInTheDocument();
  });

  test("orders equal-time equal-direction punch rows stably and preserves missing directions", async () => {
    await renderMayMatrix([matrixRecord({
      punches: [], detail_punch_rows: [
        { time: "09:00", direction: "E", terminal_label: "Primo" },
        { time: "09:00", direction: "E", terminal_label: "Secondo" },
        { time: null, direction: "U", terminal_label: "Terzo" },
        { time: null, direction: null, terminal_label: "Quarto" },
      ],
    })]);
    await openFirstMatrixDay();
    expect(screen.getByText("Primo").closest("div.rounded-xl")).toHaveTextContent("Riga 1");
    expect(screen.getByText("Secondo").closest("div.rounded-xl")).toHaveTextContent("Riga 2");
    expect(screen.getByText("Terzo").closest("div.rounded-xl")).toHaveTextContent("Riga 3");
    expect(screen.getByText("Quarto").closest("div.rounded-xl")).toHaveTextContent("Riga 4");
  });

  test("handles terminal INAZ enqueue responses without starting a poll", async () => {
    await renderMayMatrix([matrixRecord()]);
    await openFirstMatrixDay();
    mocks.refreshPresenzeDailyRecordFromInaz.mockResolvedValue({ id: "already-completed", status: "completed" });
    vi.useFakeTimers();
    await act(async () => fireEvent.click(screen.getByRole("button", { name: /Sincronizza da INAZ/ })));
    await act(async () => vi.advanceTimersByTimeAsync(4000));
    expect(mocks.getPresenzeSyncJob).not.toHaveBeenCalled();
    expect(screen.getByText("Sync INAZ completed")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Sincronizza da INAZ/ })).toBeEnabled();
  });

  test("orders mixed critical days by severity within a collaborator group", async () => {
    await renderMayMatrix([
      matrixRecord({ operational_status: "in_analysis", detail_status: null, stato: null }),
      matrixRecord({ id: "blocking", work_date: "2026-05-19", operational_status: "blocking", operational_missing_minutes: 60 }),
    ]);
    fireEvent.click(screen.getByRole("button", { name: "Vedi anomalie mese (2)" }));
    fireEvent.click(screen.getByRole("button", { name: "Collaboratore", exact: true }));
    const group = screen.getAllByText("AMADU SALVATORE").find((element) => element.closest("section"))!.closest("section")!;
    expect(within(group).getAllByRole("button")[0]).toHaveTextContent("2026-05-19");
    expect(within(group).getByText("Stato INAZ non disponibile")).toBeInTheDocument();
  });

  test("retains a collaborator modal without a schedule and displays its unworked holiday", async () => {
    await renderMayMatrix([matrixRecord({
      schedule_code: null, detail_programmed_schedule: null, detail_status: null, stato: null,
      special_day: true, operational_worked_minutes: 0, operational_formula_code: null, ordinary_minutes: 0, punches: [],
    })]);
    fireEvent.click(screen.getByRole("button", { name: "AMADU SALVATORE", exact: true }));
    expect(await screen.findByRole("link", { name: "Apri scheda completa" })).toBeInTheDocument();
    expect(screen.getAllByText("Fest").length).toBeGreaterThan(0);
    expect(screen.queryByText(/^Orario /)).not.toBeInTheDocument();
  });

  test("replaces an imported record with a new id using collaborator and date identity", async () => {
    enableOperationalEditing();
    const record = matrixRecord();
    await renderMayMatrix([record, matrixRecord({ id: "next", work_date: "2026-05-19" })]);
    mocks.updatePresenzeDailyRecord.mockResolvedValue({ ...record, id: "reimported", km_value: 10 });
    fireEvent.click(screen.getByRole("button", { name: "AMADU SALVATORE", exact: true }));
    const input = await screen.findByLabelText("KM 2026-05-18");
    fireEvent.change(input, { target: { value: "10" } });
    fireEvent.blur(input);
    await waitFor(() => expect(screen.getByText("10 KM")).toBeInTheDocument());
    expect(screen.getByLabelText("KM 2026-05-19")).toBeInTheDocument();
  });

  test("finishes progressive rendering under StrictMode", async () => {
    const template = (await mocks.listAllPresenzeCollaborators())[0];
    const collaborators = Array.from({ length: 100 }, (_value, index) => ({ ...template, id: `collab-${index}`, name: `PERSONA ${index}` }));
    const records = collaborators.map((collaborator) => matrixRecord({ id: collaborator.id, collaborator_id: collaborator.id }));
    mocks.listAllPresenzeCollaborators.mockResolvedValue(collaborators);
    mocks.listPresenzeDailyMatrixRecords.mockResolvedValue({ items: records, total: 100, page: 1, page_size: 5000 });
    const callbacks = new Map<number, () => void>();
    let handle = 0;
    vi.stubGlobal("requestIdleCallback", vi.fn((callback: () => void) => { handle += 1; callbacks.set(handle, callback); return handle; }));
    vi.stubGlobal("cancelIdleCallback", vi.fn((cancelled: number) => callbacks.delete(cancelled)));
    render(<StrictMode><PresenzeGiornalierePage /></StrictMode>);
    await screen.findByRole("button", { name: "PERSONA 0", exact: true });
    for (let iteration = 0; callbacks.size > 0 && iteration < 10; iteration += 1) {
      const [pending, callback] = callbacks.entries().next().value!;
      callbacks.delete(pending);
      await act(async () => callback());
    }
    expect(callbacks.size).toBe(0);
    expect(within(screen.getByRole("table")).getAllByRole("row")).toHaveLength(101);
  });

  test("closes stale collaborator details when a concurrent session load removes that collaborator", async () => {
    const collaborators = await mocks.listAllPresenzeCollaborators();
    let resolveReload!: (updatedCollaborators: typeof collaborators) => void;
    mocks.listAllPresenzeCollaborators
      .mockResolvedValueOnce(collaborators)
      .mockImplementationOnce(() => new Promise((resolve) => { resolveReload = resolve; }));
    render(<StrictMode><PresenzeGiornalierePage /></StrictMode>);
    fireEvent.click(await screen.findByRole("button", { name: "AMADU SALVATORE", exact: true }));
    expect(await screen.findByRole("link", { name: "Apri scheda completa" })).toBeInTheDocument();
    await act(async () => resolveReload(collaborators.filter((collaborator: { id: string }) => collaborator.id !== "collab-1")));
    expect(screen.queryByRole("link", { name: "Apri scheda completa" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "AMADU SALVATORE", exact: true })).not.toBeInTheDocument();
  });

  test.each(["operaio", "impiegato"] as const)("keeps a cleared contract editor null when a concurrent reload races a change to %s", async (contractKind) => {
    enableOperationalEditing("admin");
    const initialCollaborators = await mocks.listAllPresenzeCollaborators();
    const collaborators = initialCollaborators.map((collaborator: { id: string }) => collaborator.id === "collab-1"
      ? { ...collaborator, contract_kind: contractKind === "operaio" ? "impiegato" : "operaio", operai_group: contractKind === "operaio" ? null : "agrario" }
      : collaborator);
    let resolveReload!: (updatedCollaborators: typeof collaborators) => void;
    mocks.listAllPresenzeCollaborators
      .mockResolvedValueOnce(collaborators)
      .mockImplementationOnce(() => new Promise((resolve) => { resolveReload = resolve; }));
    render(<StrictMode><PresenzeGiornalierePage /></StrictMode>);
    fireEvent.click(await screen.findByRole("button", { name: "AMADU SALVATORE", exact: true }));
    fireEvent.click(await screen.findByRole("button", { name: /Modifica profilo/ }));
    const input = screen.getByLabelText("Tipo contratto collaboratore");
    await act(async () => {
      resolveReload(collaborators.filter((collaborator: { id: string }) => collaborator.id !== "collab-1"));
      await Promise.resolve();
      await Promise.resolve();
      fireEvent.change(input, { target: { value: contractKind } });
    });
    expect(screen.queryByLabelText("Tipo contratto collaboratore")).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Apri scheda completa" })).not.toBeInTheDocument();
    expect(mocks.updatePresenzeCollaboratorContractProfile).not.toHaveBeenCalled();
  });

  test("uses raw schedules, ignores whitespace schedule codes and keeps the first tied schedule", async () => {
    await renderMayMatrix([
      matrixRecord({ schedule_code: "RAW", detail_programmed_schedule: null }),
      matrixRecord({ id: "second", work_date: "2026-05-19", schedule_code: "OTHER", detail_programmed_schedule: null }),
      matrixRecord({ id: "podda", collaborator_id: "collab-2", schedule_code: null, detail_programmed_schedule: " - " }),
    ]);
    fireEvent.click(screen.getByRole("button", { name: "RAW (1)" }));
    await expectMatrixCollaborators(["AMADU SALVATORE"]);
    expect(screen.queryByRole("button", { name: "OTHER (1)" })).not.toBeInTheDocument();
  });

  test("closes an editor whose record was replaced during an in-flight detail request", async () => {
    enableOperationalEditing();
    const record = matrixRecord();
    await renderMayMatrix([record]);
    let rejectDetail!: (error: Error) => void;
    const pendingDetail = new Promise((_resolve, reject) => { rejectDetail = reject; });
    mocks.getPresenzeDailyRecord.mockReturnValue(pendingDetail);
    await openFirstMatrixDay();
    mocks.updatePresenzeDailyRecord.mockResolvedValue({ ...record, id: "reimported" });
    fireEvent.click(screen.getByRole("button", { name: "Salva rettifiche" }));
    await waitFor(() => expect(screen.queryByText("Rettifiche operative")).not.toBeInTheDocument());
    await act(async () => rejectDetail(new Error("Giornata non piu disponibile")));
    expect(screen.getByText("Giornata non piu disponibile")).toBeInTheDocument();
    expect(screen.queryByText("Rettifiche operative")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "AMADU SALVATORE", exact: true })).toBeInTheDocument();
  });

  test("does not retain KM edits when an earlier month response closes the selected day", async () => {
    enableOperationalEditing();
    const record = matrixRecord();
    let resolveEarlierMonth!: (response: { items: PresenzeDailyRecord[]; total: number; page: number; page_size: number }) => void;
    mocks.listPresenzeDailyMatrixRecords
      .mockImplementationOnce(() => new Promise((resolve) => { resolveEarlierMonth = resolve; }))
      .mockResolvedValue({ items: [record], total: 1, page: 1, page_size: 5000 });
    mocks.getPresenzeDailyRecord.mockResolvedValue(record);
    render(<PresenzeGiornalierePage />);
    const monthInput = await screen.findByLabelText("Mese operativo");
    const earlierMonth = (monthInput as HTMLInputElement).value;
    const requestedMonth = earlierMonth === "2026-05" ? "2026-06" : "2026-05";
    record.work_date = `${requestedMonth}-18`;
    fireEvent.change(monthInput, { target: { value: requestedMonth } });
    await screen.findByRole("button", { name: "AMADU SALVATORE", exact: true });
    await openFirstMatrixDay();
    const input = screen.getByLabelText("Chilometri auto");
    await act(async () => {
      resolveEarlierMonth({ items: [{ ...record, id: "earlier-record", work_date: `${earlierMonth}-18` }], total: 1, page: 1, page_size: 5000 });
      await Promise.resolve();
      await Promise.resolve();
      expect(input.isConnected).toBe(true);
      fireEvent.change(input, { target: { value: "99" } });
    });
    expect(screen.queryByText("Rettifiche operative")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Chilometri auto")).not.toBeInTheDocument();
    expect(mocks.updatePresenzeDailyRecord).not.toHaveBeenCalled();
  });

  test("uses justified minutes in request summaries when explicit absence minutes are missing", async () => {
    await renderMayMatrix([matrixRecord({ request_description: "Permesso ordinario", absence_minutes: null, justified_minutes: 30 })]);
    await openFirstMatrixDay();
    expect(screen.getByText("Permesso ordinario · 0.50 h")).toBeInTheDocument();
  });

  test("keeps missing authorized times without inventing a paired punch", async () => {
    await renderMayMatrix([matrixRecord({
      punches: [], request_status: "ACC", request_description: "Timbratura E", request_authorized_by: null,
      detail_punch_rows: [{ time: null, direction: "E", terminal_label: "Primo" }, { time: null, direction: "E", terminal_label: "Secondo" }],
    })]);
    await openFirstMatrixDay();
    expect(screen.getByText("Primo").closest("div.rounded-xl")).toHaveTextContent("—");
    expect(screen.getByText("Secondo").closest("div.rounded-xl")).toHaveTextContent("—");
  });

  test.each(["E", "U"])("shows an authorized %s punch without inventing missing INAZ rows", async (direction) => {
    await renderMayMatrix([matrixRecord({
      punches: [], detail_punch_rows: [], request_status: "ACC", request_description: `Timbratura ${direction}`,
    })]);
    await openFirstMatrixDay();
    expect(screen.getByText("Timbrature dettaglio Inaz")).toBeInTheDocument();
    expect(screen.getAllByText(direction === "E" ? "Timbratura di entrata autorizzata" : "Timbratura di uscita autorizzata").length).toBeGreaterThan(0);
    expect(screen.queryByText(/^Riga \d+$/)).not.toBeInTheDocument();
    expect(screen.queryByText(/righe? lette$/)).not.toBeInTheDocument();
  });

  test("normalizes missing directions when paired and detail punch counts match", async () => {
    await renderMayMatrix([matrixRecord({ detail_punch_rows: [
      { time: "06:55", direction: null, terminal_label: "FENO-Fenoso" },
      { time: "12:30", direction: "U", terminal_label: "FENO-Fenoso" },
    ] })]);
    await openFirstMatrixDay();
    expect(screen.getByText("Riga 1")).toBeInTheDocument();
    expect(screen.getByText("Riga 2")).toBeInTheDocument();
  });

  test("keeps weekend shading while editing matrix KM", async () => {
    enableOperationalEditing();
    await renderMayMatrix([matrixRecord({ work_date: "2026-05-16" })]);
    fireEvent.click(screen.getByRole("button", { name: "Inserisci KM" }));
    expect(within(screen.getByRole("table")).getByRole("textbox").closest("td")).toHaveClass("bg-slate-100/50");
  });

  test("falls back to a schedule code when its programmed label is empty", async () => {
    await renderMayMatrix([matrixRecord({ schedule_code: "RAW", detail_programmed_schedule: "" })]);
    expect(screen.getByRole("button", { name: "RAW (1)" })).toHaveAttribute("title", "RAW");
  });

  test("preserves request descriptions with an empty suffix and uses operational MPE for the rule hint", async () => {
    await renderMayMatrix([matrixRecord({ request_description: "Titolo - ", effective_extra_minutes: null, operational_mpe_minutes: 15 })]);
    await openFirstMatrixDay();
    expect(screen.getAllByText("Titolo -").length).toBeGreaterThan(0);
    expect(screen.getByText("Extra/straordinario fino a 3 ore: non entra in anomalia se le timbrature quadrano.")).toBeInTheDocument();
  });

  test("keeps an active daily anomaly filter fail-closed when validation clears the last anomaly", async () => {
    const record = matrixRecord({ operational_status: "in_analysis" });
    await renderMayMatrix([record]);
    fireEvent.click(screen.getByTitle("2026-05-18 · 1 anomalie"));
    await openFirstMatrixDay();
    mocks.updatePresenzeDailyRecord.mockResolvedValue({ ...record, operational_status: "ok", validation_status: "validated" });
    fireEvent.click(screen.getByRole("button", { name: "Valida giornaliera" }));
    expect(await screen.findByText("0 coll.")).toBeInTheDocument();
    expect(screen.getByText("Filtro giorno: lunedì 18 · anomalie")).toBeInTheDocument();
  });

  test.each([
    ["Trasferte", { trasferta_minutes: 60 }],
    ["Straordinari", { effective_straordinario_minutes: 30, straordinario_minutes: 0 }],
    ["Straordinari", { effective_straordinario_minutes: null, straordinario_minutes: 30 }],
    ["Reperibilita", { reperibilita_unit: "days", reperibilita_quantity: 2 }],
    ["Reperibilita", { reperibilita_unit: "days", reperibilita_quantity: null }],
    ["KM carburanti", { km_value: 12 }],
  ] satisfies Array<[string, Partial<PresenzeDailyRecord>]>)(
    "toggles %s using monthly operational totals (%j)",
    async (filter, values) => {
      await renderMayMatrix([
        matrixRecord(),
        matrixRecord({ id: "podda", collaborator_id: "collab-2", ...values }),
        matrixRecord({ id: "zedda", collaborator_id: "collab-3" }),
      ]);
      fireEvent.click(screen.getByRole("button", { name: filter, exact: true }));
      await expectMatrixCollaborators(["PODDA RAIMONDO"]);
      fireEvent.click(screen.getByRole("button", { name: filter, exact: true }));
      await expectMatrixCollaborators(["AMADU SALVATORE", "PODDA RAIMONDO", "ZEDDA MARIO"]);
    },
  );

  test("intersects operational filters and keeps month totals when no collaborators match", async () => {
    await renderMayMatrix([
      matrixRecord({ km_value: 12 }),
      matrixRecord({ id: "podda", collaborator_id: "collab-2", trasferta_minutes: 60 }),
      matrixRecord({ id: "zedda", collaborator_id: "collab-3", reperibilita_unit: "days", reperibilita_quantity: 0 }),
    ]);
    fireEvent.click(screen.getByRole("button", { name: "KM carburanti" }));
    fireEvent.click(screen.getByRole("button", { name: "Trasferte", exact: true }));
    expect(await screen.findByText("Nessun collaboratore corrisponde ai filtri correnti.")).toBeInTheDocument();
    expect(screen.getByText("0 coll.")).toBeInTheDocument();
    expect(screen.getByText("12 KM")).toBeInTheDocument();
    expect(screen.getByText("Trasferta 1.00 h")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "KM carburanti" }));
    fireEvent.click(screen.getByRole("button", { name: "Trasferte", exact: true }));
    fireEvent.click(screen.getByRole("button", { name: "Reperibilita", exact: true }));
    expect(await screen.findByText("Nessun collaboratore corrisponde ai filtri correnti.")).toBeInTheDocument();
  });

  test.each([
    ["  aMaDu  ", ["AMADU SALVATORE"]],
    ["1855", ["PODDA RAIMONDO"]],
    ["cbo", ["AMADU SALVATORE", "PODDA RAIMONDO", "ZEDDA MARIO"]],
  ])("searches names, employee codes and company labels: %s", async (query, names) => {
    await renderMayMatrix();
    fireEvent.change(screen.getByPlaceholderText("Nome o matricola"), { target: { value: query } });
    await expectMatrixCollaborators(names);
  });

  test("toggles profile filters and restores all profiles explicitly", async () => {
    await renderMayMatrix();
    const profile = screen.getByRole("button", { name: "Operai catasto / magazzino (1)" });
    fireEvent.click(profile);
    await expectMatrixCollaborators(["PODDA RAIMONDO"]);
    fireEvent.click(profile);
    await expectMatrixCollaborators(["AMADU SALVATORE", "PODDA RAIMONDO", "ZEDDA MARIO"]);
    fireEvent.click(screen.getByRole("button", { name: "Operai da classificare (1)" }));
    await expectMatrixCollaborators(["ZEDDA MARIO"]);
    fireEvent.click(screen.getByRole("button", { name: "Tutti i profili (3)" }));
    await expectMatrixCollaborators(["AMADU SALVATORE", "PODDA RAIMONDO", "ZEDDA MARIO"]);
  });

  test("uses the dominant monthly schedule and combines schedule, profile and search", async () => {
    await renderMayMatrix([
      matrixRecord({ schedule_code: "ALT", detail_programmed_schedule: "ALT - Alternativo" }),
      matrixRecord({ id: "amadu-2", work_date: "2026-05-19", schedule_code: "STD" }),
      matrixRecord({ id: "amadu-3", work_date: "2026-05-20", schedule_code: "STD" }),
      matrixRecord({ id: "podda", collaborator_id: "collab-2", schedule_code: null, detail_programmed_schedule: "ALT - Alternativo" }),
      matrixRecord({ id: "zedda", collaborator_id: "collab-3", schedule_code: null, detail_programmed_schedule: null }),
    ]);
    fireEvent.click(screen.getByRole("button", { name: "ALT (1)" }));
    await expectMatrixCollaborators(["PODDA RAIMONDO"]);
    fireEvent.click(screen.getByRole("button", { name: "ALT (1)" }));
    await expectMatrixCollaborators(["AMADU SALVATORE", "PODDA RAIMONDO", "ZEDDA MARIO"]);
    fireEvent.click(screen.getByRole("button", { name: "STD (1)" }));
    fireEvent.click(screen.getByRole("button", { name: "Operai agrario (1)" }));
    fireEvent.change(screen.getByPlaceholderText("Nome o matricola"), { target: { value: "1854" } });
    await expectMatrixCollaborators(["AMADU SALVATORE"]);
    fireEvent.click(screen.getByRole("button", { name: "Tutti (2)" }));
    fireEvent.click(screen.getByRole("button", { name: "Tutti i profili (3)" }));
    fireEvent.click(screen.getByRole("button", { name: "Pulisci ricerca collaboratore" }));
    await expectMatrixCollaborators(["AMADU SALVATORE", "PODDA RAIMONDO", "ZEDDA MARIO"]);
  });

  test.each(["anomalies", "requests"] as const)("toggles and removes the daily %s focus", async (kind) => {
    await renderMayMatrix([
      matrixRecord({ operational_status: "in_analysis", request_description: "Permesso" }),
      matrixRecord({ id: "podda", collaborator_id: "collab-2", work_date: "2026-05-19", operational_status: "blocking", operational_missing_minutes: 60, detail_requests: [{ Descrizione: "Ferie" }] }),
      matrixRecord({ id: "zedda", collaborator_id: "collab-3" }),
    ]);
    const title = kind === "anomalies" ? "2026-05-18 · 1 anomalie" : "2026-05-18 · 1 richieste";
    fireEvent.click(screen.getByTitle(title));
    await expectMatrixCollaborators(["AMADU SALVATORE"]);
    expect(screen.getByText(/Filtro giorno: lunedì 18/)).toBeInTheDocument();
    fireEvent.click(screen.getByTitle(title));
    await expectMatrixCollaborators(["AMADU SALVATORE", "PODDA RAIMONDO", "ZEDDA MARIO"]);
    fireEvent.click(screen.getByTitle(title));
    fireEvent.click(screen.getByRole("button", { name: "Rimuovi", exact: true }));
    await expectMatrixCollaborators(["AMADU SALVATORE", "PODDA RAIMONDO", "ZEDDA MARIO"]);
    expect(screen.queryByText(/Filtro giorno:/)).not.toBeInTheDocument();
  });

  test("aggregates monthly ordinary, extra, km, travel and absences across multiple days", async () => {
    await renderMayMatrix([
      matrixRecord({ km_value: 10, trasferta_minutes: 30, effective_extra_minutes: 90, absence_minutes: 60, resolved_absence_cause: "permesso" }),
      matrixRecord({ id: "amadu-2", work_date: "2026-05-19", km_value: 5, trasferta_minutes: 60, effective_extra_minutes: null, effective_straordinario_minutes: null, straordinario_minutes: 30, effective_mpe_minutes: null, mpe_minutes: 15, operational_formula_code: null, ordinary_minutes: 120, absence_minutes: null, justified_minutes: 30, resolved_absence_cause: "permesso" }),
      matrixRecord({ id: "podda", collaborator_id: "collab-2", operational_status: "blocking", operational_missing_minutes: 120 }),
    ]);
    expect(screen.getByText("Extra 2.25 h")).toBeInTheDocument();
    expect(screen.getByText("15 KM")).toBeInTheDocument();
    expect(screen.getByText("Trasferta 1.50 h")).toBeInTheDocument();
    expect(screen.getByText("1 anomalie")).toBeInTheDocument();
    const row = screen.getByRole("button", { name: "AMADU SALVATORE", exact: true }).closest("tr")!;
    expect(within(row).getByText("Lavorate ord. 9h")).toBeInTheDocument();
    expect(within(row).getByText("15 km")).toBeInTheDocument();
    expect(within(row).getByText("Trasf 1.5h")).toBeInTheDocument();
    expect(within(row).getByText("2.3h")).toBeInTheDocument();
    expect(within(row).getByText("1.5h")).toBeInTheDocument();
    const blockingRow = screen.getByRole("button", { name: "PODDA RAIMONDO", exact: true }).closest("tr")!;
    expect(within(blockingRow).getByText("Assenza da giustificare")).toBeInTheDocument();
    expect(within(blockingRow).getByText("2h")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "AMADU SALVATORE", exact: true }));
    const summary = screen.getByText("Riepilogo operativo mese").parentElement!;
    expect(within(summary).getByText("2.3h")).toBeInTheDocument();
    expect(within(summary).getByText("1.5h")).toBeInTheDocument();
  });

  test("sorts monthly Saturdays chronologically and retains each absence cause", async () => {
    await renderMayMatrix([
      matrixRecord({ id: "third", work_date: "2026-05-16", resolved_absence_cause: "malattia", absence_minutes: 120 }),
      matrixRecord({ id: "first", work_date: "2026-05-02", resolved_absence_cause: "permesso", absence_minutes: 60 }),
      matrixRecord({ id: "second", work_date: "2026-05-09", resolved_absence_cause: "ferie", absence_minutes: 180 }),
    ]);
    const row = screen.getByRole("button", { name: "AMADU SALVATORE", exact: true }).closest("tr")!;
    expect(within(row).getByText("1° perm · 2° fer · 3° mal")).toBeInTheDocument();
    expect(within(row).getByText("Ferie")).toBeInTheDocument();
    expect(within(row).getByText("Malattia")).toBeInTheDocument();
    expect(within(row).getByText("Permesso")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "AMADU SALVATORE", exact: true }));
    const summary = screen.getByText("Riepilogo operativo mese").parentElement!;
    expect(within(summary).getByText("1° perm · 2° fer · 3° mal")).toBeInTheDocument();
    expect(within(summary).getByText("3h")).toBeInTheDocument();
    expect(within(summary).getByText("2h")).toBeInTheDocument();
    expect(within(summary).getByText("1h")).toBeInTheDocument();
  });

  test("renders an empty month with zero summaries and no profile or schedule options", async () => {
    mocks.listPresenzeDailyMatrixRecords.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 5000 });
    render(<PresenzeGiornalierePage />);
    fireEvent.change(await screen.findByLabelText("Mese operativo"), { target: { value: "2026-05" } });
    expect(await screen.findByText("0 coll.")).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByText("Caricamento cartellino…")).not.toBeInTheDocument());
    expect(within(screen.getByRole("table")).queryByRole("button", { name: "AMADU SALVATORE", exact: true })).not.toBeInTheDocument();
    expect(screen.queryByText("Nessun collaboratore corrisponde ai filtri correnti.")).not.toBeInTheDocument();
    expect(screen.getByText("Extra 0.00 h")).toBeInTheDocument();
    expect(screen.getByText("0 KM")).toBeInTheDocument();
    expect(screen.getByText("Trasferta 0.00 h")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Tutti i profili/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^OPESAB/ })).not.toBeInTheDocument();
  });

  test("renders the monthly matrix, opens the day modal and lets a supervisor validate only", async () => {
    mocks.getPresenzeDailyRecord.mockResolvedValue({
      ...baseDailyRecord,
      request_status: "ACC",
      request_description: "Permesso ordinario (U)",
    });

    render(<PresenzeGiornalierePage />);

    expect(await screen.findByText("Giornaliere")).toBeInTheDocument();

    // Sposta la vista sul mese del record mockato (maggio 2026).
    fireEvent.change(await screen.findByLabelText("Mese operativo"), { target: { value: "2026-05" } });

    // Il collaboratore compare in verticale nella matrice.
    expect(await screen.findByText("AMADU SALVATORE")).toBeInTheDocument();
    expect(screen.getAllByText("Operaio agrario")).not.toHaveLength(0);
    expect(screen.getByText("profilo, ordinario, alert")).toBeInTheDocument();

    // La cella del giorno apre la modale operativa.
    const dayCell = await screen.findByTitle("2026-05-16 · GAIA: in analisi · INAZ: Giornata anomala");
    fireEvent.click(dayCell);
    expect(await screen.findByLabelText("Giorno precedente")).toBeDisabled();
    expect(screen.getByLabelText("Giorno successivo")).toBeDisabled();
    expect(screen.getByText("Causale rilevata")).toBeInTheDocument();
    expect(screen.getByText("Permesso ordinario (U)")).toBeInTheDocument();
    expect(screen.getByText("GAIA in analisi")).toBeInTheDocument();
    expect(screen.getByText("Formula GAIA")).toBeInTheDocument();
    expect(screen.getByText("Extra/straordinario fino a 3 ore: non entra in anomalia se le timbrature quadrano.")).toBeInTheDocument();
    expect(screen.getAllByText("OPESAB").length).toBeGreaterThan(0);
    expect(screen.getByText("PODDA FABRIZIO")).toBeInTheDocument();
    expect(screen.getAllByText("Operaio agrario")).not.toHaveLength(0);
    expect(screen.getAllByText("06:55")).toHaveLength(2);
    expect(screen.getAllByText("12:30")).toHaveLength(2);
    expect(screen.getAllByText("Fenoso")).toHaveLength(4);
    expect(screen.getByText("Timbrature dettaglio Inaz")).toBeInTheDocument();
    expect(screen.getAllByText("Timbratura di uscita autorizzata da PODDA FABRIZIO")).toHaveLength(1);
    expect(screen.getByText("Riga 4")).toBeInTheDocument();
    expect(screen.getAllByText("Entrata")).toHaveLength(2);
    expect(screen.getAllByText("Uscita")).toHaveLength(2);
    expect(screen.getByText("I capisettore possono validare la giornata, ma non modificare KM e rettifiche operative.")).toBeInTheDocument();

    expect(screen.getByLabelText("Chilometri auto")).toBeDisabled();
    expect(screen.getByLabelText("Reperibilita giornaliera")).toBeDisabled();
    expect(screen.getByLabelText("Straordinario override")).toBeDisabled();
    expect(screen.getByLabelText("Maggior presenza override")).toBeDisabled();
    expect(screen.getByLabelText("Nota operativa")).toBeDisabled();
    expect(screen.getByText("Salva rettifiche")).toBeDisabled();

    fireEvent.change(screen.getByLabelText("Nota validazione"), { target: { value: "Verificata dal capo settore" } });
    fireEvent.click(screen.getByText("Valida giornaliera"));

    await waitFor(() => {
      expect(mocks.updatePresenzeDailyRecord).toHaveBeenCalledWith(expect.stringMatching(/^token-/), "record-1", {
        validation_status: "validated",
        validation_note: "Verificata dal capo settore",
      });
    });

    expect(await screen.findByText("Giornata 2026-05-16 validata.")).toBeInTheDocument();
  });

  test("shows month anomalies directly and opens the selected anomaly", async () => {
    render(<PresenzeGiornalierePage />);

    expect(await screen.findByText("Giornaliere")).toBeInTheDocument();
    fireEvent.change(await screen.findByLabelText("Mese operativo"), { target: { value: "2026-05" } });

    expect(await screen.findByRole("button", { name: "Vedi anomalie mese (1)" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Vedi anomalie mese (1)" }));

    expect(await screen.findByText("Anomalie del mese")).toBeInTheDocument();
    expect(screen.getByText("Ore mancanti")).toBeInTheDocument();
    expect(screen.getAllByText("Da verificare").length).toBeGreaterThan(0);
    expect(screen.getByText("Apri la prima giornata critica")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Tutte (1)" })).toBeInTheDocument();
    expect(screen.getAllByText(/2026-05-16 · sabato/i).length).toBeGreaterThan(0);
    expect(screen.getByText("1 giornata aperta da lavorare in sequenza")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Collaboratore" })).toBeInTheDocument();
    expect(screen.getByText("Bloccante = da correggere subito")).toBeInTheDocument();
    expect(screen.getByText("Extra corretti fino a 3h = non anomalia")).toBeInTheDocument();
    expect(screen.getByText("Regola operativa: gli extra corretti non entrano in anomalia fino a 3 ore; oltre 3 ore restano da lavorare.")).toBeInTheDocument();
    expect(screen.getByText("Extra/straordinario fino a 3 ore: non entra in anomalia se le timbrature quadrano.")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Collaboratore" }));

    expect(screen.getByText("1 giornata aperta nel mese")).toBeInTheDocument();
    expect(screen.getAllByText("AMADU SALVATORE").length).toBeGreaterThan(0);

    fireEvent.click(screen.getByRole("button", { name: "Solo anomalie" }));

    await waitFor(() => {
      expect(screen.getAllByText("AMADU SALVATORE").length).toBeGreaterThan(0);
      expect(screen.queryAllByText("PODDA RAIMONDO")).toHaveLength(0);
      expect(screen.queryAllByText("ZEDDA MARIO")).toHaveLength(0);
    });

    fireEvent.click(screen.getByRole("button", { name: /2026-05-16[\s\S]*Ore mancanti/i }));

    expect(await screen.findByText(/2026-05-16 · sabato · AMADU SALVATORE/i)).toBeInTheDocument();
  });

  test("allows users with full access to save operational overrides", async () => {
    mocks.getCurrentUser.mockResolvedValue({
      id: 1,
      username: "hr_manager",
      email: "hr@example.local",
      full_name: "HR Manager",
      office_location: null,
      phone_extension: null,
      role: "hr_manager",
      is_active: true,
      module_accessi: true,
      module_rete: false,
      module_inventario: false,
      module_catasto: false,
      module_utenze: false,
      module_operazioni: false,
      module_riordino: false,
      module_ruolo: false,
      module_presenze: true,
      enabled_modules: ["accessi", "presenze"],
    });
    mocks.getPresenzeAccessContext.mockResolvedValue({
      can_view_all_data: true,
      can_view_all_credentials: false,
      can_manage_supervisors: false,
      is_supervisor: false,
      assigned_collaborators_count: 0,
    });
    mocks.listPresenzeDailyMatrixRecords.mockResolvedValue({
      items: [{ ...baseDailyRecord, owner_user_id: 1 }],
      total: 1,
      page: 1,
      page_size: 5000,
    });

    render(<PresenzeGiornalierePage />);

    fireEvent.change(await screen.findByLabelText("Mese operativo"), { target: { value: "2026-05" } });
    fireEvent.click(await screen.findByTitle("2026-05-16 · GAIA: in analisi · INAZ: Giornata anomala"));

    fireEvent.change(await screen.findByLabelText("Chilometri auto"), { target: { value: "30" } });
    fireEvent.click(screen.getByLabelText("Reperibilita giornaliera"));
    fireEvent.change(screen.getByLabelText("Straordinario override"), { target: { value: "01:30" } });
    fireEvent.change(screen.getByLabelText("Maggior presenza override"), { target: { value: "00:30" } });
    fireEvent.change(screen.getByLabelText("Nota operativa"), { target: { value: "Corretto HR" } });
    fireEvent.click(screen.getByText("Salva rettifiche"));

    await waitFor(() => {
      expect(mocks.updatePresenzeDailyRecord).toHaveBeenCalledWith(expect.stringMatching(/^token-/), "record-1", {
        km_value: 30,
        trasferta_minutes: null,
        trasferta_montano: false,
        reperibilita_unit: "days",
        reperibilita_quantity: 1,
        override_straordinario_minutes: 90,
        override_mpe_minutes: 30,
        manual_note: "Corretto HR",
        validation_note: null,
      });
    });
  });

  test("opens the collaborator detail modal from the matrix", async () => {
    mocks.updatePresenzeDailyRecord
      .mockResolvedValueOnce({ ...baseDailyRecord, km_value: 42, reperibilita_unit: "none", reperibilita_quantity: null })
      .mockResolvedValueOnce({ ...baseDailyRecord, km_value: 42, reperibilita_unit: "days", reperibilita_quantity: 1 });

    render(<PresenzeGiornalierePage />);

    expect(await screen.findByText("Giornaliere")).toBeInTheDocument();
    fireEvent.change(await screen.findByLabelText("Mese operativo"), { target: { value: "2026-05" } });

    fireEvent.click(await screen.findByRole("button", { name: "AMADU SALVATORE" }));

    // La modal mostra la scheda sintetica del collaboratore e l'elenco giornate.
    expect(await screen.findByText("Apri scheda completa")).toBeInTheDocument();
    expect(screen.getByText("2026-05-16")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /2026-05-16.*sabato.*Giornata anomala/i })).toBeInTheDocument();
    expect(screen.getByText("Riepilogo operativo mese")).toBeInTheDocument();
    const kmInput = screen.getByLabelText("KM 2026-05-16");
    expect(kmInput).toHaveValue("24");
    fireEvent.change(kmInput, { target: { value: "42" } });
    fireEvent.blur(kmInput);
    await waitFor(() => {
      expect(mocks.updatePresenzeDailyRecord).toHaveBeenCalledWith(expect.stringMatching(/^token-/), "record-1", { km_value: 42 });
    });
    expect(screen.getAllByRole("button", { name: "Rep" }).length).toBeGreaterThan(0);

    fireEvent.click(screen.getByRole("button", { name: /2026-05-16.*sabato.*Giornata anomala/i }));
    expect(await screen.findByText(/2026-05-16 · sabato · AMADU SALVATORE/i)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Chiudi/i }));
    expect(await screen.findByText("Apri scheda completa")).toBeInTheDocument();
  });

  test("allows admins to change the collaborator contract profile from the modal", async () => {
    mocks.getCurrentUser.mockResolvedValue({
      id: 1,
      username: "admin",
      email: "admin@example.local",
      full_name: "Admin",
      office_location: null,
      phone_extension: null,
      role: "admin",
      is_active: true,
      module_accessi: true,
      module_rete: false,
      module_inventario: false,
      module_catasto: false,
      module_utenze: false,
      module_operazioni: false,
      module_riordino: false,
      module_ruolo: false,
      module_presenze: true,
      enabled_modules: ["accessi", "presenze"],
    });
    mocks.getPresenzeAccessContext.mockResolvedValue({
      can_view_all_data: true,
      can_view_all_credentials: false,
      can_manage_supervisors: false,
      is_supervisor: false,
      assigned_collaborators_count: 0,
    });
    mocks.listPresenzeDailyMatrixRecords.mockResolvedValue({
      items: [{ ...baseDailyRecord, owner_user_id: 1 }],
      total: 1,
      page: 1,
      page_size: 5000,
    });

    render(<PresenzeGiornalierePage />);

    fireEvent.change(await screen.findByLabelText("Mese operativo"), { target: { value: "2026-05" } });
    fireEvent.click(await screen.findByRole("button", { name: "AMADU SALVATORE" }));

    fireEvent.click(await screen.findByRole("button", { name: /Modifica profilo/i }));
    fireEvent.change(await screen.findByLabelText("Tipo contratto collaboratore"), { target: { value: "impiegato" } });
    fireEvent.change(screen.getByLabelText("Minuti standard collaboratore"), { target: { value: "385" } });
    fireEvent.click(screen.getByRole("button", { name: "Salva profilo" }));

    await waitFor(() => {
      expect(mocks.updatePresenzeCollaboratorContractProfile).toHaveBeenCalledWith(expect.stringMatching(/^token-/), "collab-1", {
        contract_kind: "impiegato",
        operai_group: null,
        standard_daily_minutes: 385,
      });
    });

    expect(await screen.findByText("Profilo contrattuale aggiornato per AMADU SALVATORE.")).toBeInTheDocument();
    expect(screen.getAllByText("Impiegato").length).toBeGreaterThan(0);
  });

  test("filters collaborators with km carburanti", async () => {
    render(<PresenzeGiornalierePage />);

    expect(await screen.findByText("Giornaliere")).toBeInTheDocument();
    fireEvent.change(await screen.findByLabelText("Mese operativo"), { target: { value: "2026-05" } });

    expect(await screen.findByText("AMADU SALVATORE")).toBeInTheDocument();
    expect(screen.getByText("PODDA RAIMONDO")).toBeInTheDocument();
    expect(screen.getByText("ZEDDA MARIO")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Operai agrario (1)" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Operai catasto / magazzino (1)" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Operai da classificare (1)" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Operai agrario (1)" }));

    await waitFor(() => {
      expect(screen.getByText("AMADU SALVATORE")).toBeInTheDocument();
      expect(screen.queryByText("PODDA RAIMONDO")).not.toBeInTheDocument();
      expect(screen.queryByText("ZEDDA MARIO")).not.toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "Tutti i profili (3)" }));

    fireEvent.click(screen.getByRole("button", { name: "KM carburanti" }));

    await waitFor(() => {
      expect(screen.getByText("AMADU SALVATORE")).toBeInTheDocument();
      expect(screen.queryByText("PODDA RAIMONDO")).not.toBeInTheDocument();
      expect(screen.queryByText("ZEDDA MARIO")).not.toBeInTheDocument();
    });
  });

  test("clears the collaborator search with the inline X button", async () => {
    render(<PresenzeGiornalierePage />);

    expect(await screen.findByText("Giornaliere")).toBeInTheDocument();
    fireEvent.change(await screen.findByLabelText("Mese operativo"), { target: { value: "2026-05" } });

    const searchInput = screen.getByPlaceholderText("Nome o matricola");
    fireEvent.change(searchInput, { target: { value: "ama" } });

    await waitFor(() => {
      expect(screen.getByText("AMADU SALVATORE")).toBeInTheDocument();
      expect(screen.queryByText("SERUSI LUCA ANTONIO")).not.toBeInTheDocument();
      expect(screen.queryByText("PODDA RAIMONDO")).not.toBeInTheDocument();
      expect(screen.queryByText("ZEDDA MARIO")).not.toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "Pulisci ricerca collaboratore" }));

    await waitFor(() => {
      expect(screen.getByDisplayValue("")).toBeInTheDocument();
      expect(screen.getByText("AMADU SALVATORE")).toBeInTheDocument();
      expect(screen.getByText("PODDA RAIMONDO")).toBeInTheDocument();
      expect(screen.getByText("ZEDDA MARIO")).toBeInTheDocument();
    });
  });

  test("shows Fest on holidays without worked time instead of the template theoretical hours", async () => {
    mocks.listPresenzeDailyMatrixRecords.mockResolvedValueOnce({
      items: [
        {
          ...baseDailyRecord,
          id: "holiday-record-1",
          work_date: "2026-06-02",
          schedule_code: "OPE0714",
          teo_minutes: 420,
          ordinary_minutes: null,
          absence_minutes: 420,
          justified_minutes: null,
          stato: "Giornata regolare",
          detail_status: "Giornata regolare",
          special_day: true,
          request_type: null,
          request_description: null,
          request_status: null,
          request_authorized_by: null,
          resolved_absence_cause: null,
          effective_straordinario_minutes: 0,
          effective_mpe_minutes: 0,
          effective_extra_minutes: 0,
          operational_status: "ok",
          operational_formula_code: "OPE0714",
          operational_expected_minutes: 420,
          operational_worked_minutes: 0,
          operational_missing_minutes: 0,
          operational_mpe_minutes: 0,
          operational_notes: [],
          punches: [],
          detail_punch_rows: [],
          detail_requests: [],
          detail_anomalies: [],
        },
      ],
      total: 1,
      page: 1,
      page_size: 5000,
    });

    render(<PresenzeGiornalierePage />);

    fireEvent.change(await screen.findByLabelText("Mese operativo"), { target: { value: "2026-06" } });

    const holidayCell = await screen.findByTitle("2026-06-02 · GAIA: giornata quadrata");
    expect(holidayCell).toHaveTextContent("Fest");
    expect(holidayCell).not.toHaveTextContent("7");
  });

  test("orders Inaz detail punches by entry then exit to keep the sequence readable", async () => {
    mocks.getPresenzeDailyRecord.mockResolvedValueOnce({
      ...baseDailyRecord,
      detail_punch_rows: [
        { time: "10:00", direction: "U", terminal_label: "0", raw: { Ora: "10:00", EU: "U", Term: "0" } },
        { time: null, direction: "E", terminal_label: null, raw: { Ora: null, EU: "E", Term: null } },
      ],
      punches: [
        {
          id: "p-entry",
          daily_record_id: "record-1",
          sequence: 1,
          entry_time: "05:30",
          exit_time: "10:03",
          terminal_label: "Bennaxi EST",
          created_at: "2026-06-04T09:00:00Z",
        },
      ],
      request_status: "ACC",
      request_description: "Inserimento - 05:30 E",
    });

    render(<PresenzeGiornalierePage />);

    fireEvent.change(await screen.findByLabelText("Mese operativo"), { target: { value: "2026-05" } });
    fireEvent.click(await screen.findByTitle("2026-05-16 · GAIA: in analisi · INAZ: Giornata anomala"));

    expect(await screen.findByText("Timbrature dettaglio Inaz")).toBeInTheDocument();
    const rowTitles = screen.getAllByText(/Riga \d/).map((node) => node.textContent);
    const directionLabels = screen.getAllByText(/Entrata|Uscita/).map((node) => node.textContent);
    expect(rowTitles[0]).toBe("Riga 1");
    expect(directionLabels.indexOf("Entrata")).toBeLessThan(directionLabels.lastIndexOf("Uscita"));
    expect(screen.getAllByText("05:30").length).toBeGreaterThan(0);
    expect(screen.getAllByText("10:03").length).toBeGreaterThan(0);
  });

  test("starts a targeted INAZ refresh from the modal", async () => {
    render(<PresenzeGiornalierePage />);

    fireEvent.change(await screen.findByLabelText("Mese operativo"), { target: { value: "2026-05" } });
    fireEvent.click(await screen.findByTitle("2026-05-16 · GAIA: in analisi · INAZ: Giornata anomala"));

    fireEvent.click(await screen.findByRole("button", { name: /Sincronizza da INAZ/i }));

    await waitFor(() => {
      expect(mocks.refreshPresenzeDailyRecordFromInaz).toHaveBeenCalledWith(expect.stringMatching(/^token-/), "record-1");
      expect(screen.getByText("Recupero dati INAZ accodato per AMADU SALVATORE · 2026-05-16.")).toBeInTheDocument();
    });
  });

  test("explains when targeted INAZ refresh is blocked by another sync job", async () => {
    const { ApiError } = await import("@/lib/api");
    mocks.refreshPresenzeDailyRecordFromInaz.mockRejectedValueOnce(new ApiError("Another Presenze sync job is already pending or running", undefined, 409));

    render(<PresenzeGiornalierePage />);

    fireEvent.change(await screen.findByLabelText("Mese operativo"), { target: { value: "2026-05" } });
    fireEvent.click(await screen.findByTitle("2026-05-16 · GAIA: in analisi · INAZ: Giornata anomala"));

    fireEvent.click(await screen.findByRole("button", { name: /Sincronizza da INAZ/i }));

    expect(
      await screen.findByText(
        "Recupero INAZ non avviato: c'e gia una sincronizzazione Presenze in corso o in coda. Attendi la fine oppure annulla il job dalla pagina Sync Presenze.",
      ),
    ).toBeInTheDocument();
  });

  test("shows a readable INAZ login failure when targeted refresh fails", async () => {
    mocks.getPresenzeSyncJob.mockResolvedValueOnce({
      id: "sync-job-1",
      status: "failed",
      requested_by_user_id: 12,
      credential_id: 1,
      import_job_id: null,
      period_start: "2026-05-16",
      period_end: "2026-05-16",
      collaborator_limit: 1,
      records_imported: 0,
      records_skipped: 0,
      records_errors: 1,
      json_artifact_path: null,
      worker_log_path: null,
      worker_pid: 1,
      attempt_count: 1,
      max_attempts: 3,
      error_detail: "Frame atteso non trovato entro il timeout. Frames visibili: FunPers/Login.aspx",
      params_json: { trigger: "manual_record_refresh" },
      created_at: "2026-06-04T09:00:00Z",
      started_at: "2026-06-04T09:00:01Z",
      finished_at: "2026-06-04T09:00:02Z",
    });

    render(<PresenzeGiornalierePage />);

    fireEvent.change(await screen.findByLabelText("Mese operativo"), { target: { value: "2026-05" } });
    fireEvent.click(await screen.findByTitle("2026-05-16 · GAIA: in analisi · INAZ: Giornata anomala"));
    fireEvent.click(await screen.findByRole("button", { name: /Sincronizza da INAZ/i }));

    await waitFor(() => expect(mocks.getPresenzeSyncJob).toHaveBeenCalledWith(expect.stringMatching(/^token-/), "sync-job-1"), { timeout: 3500 });

    expect(await screen.findByText("Accesso INAZ da verificare")).toBeInTheDocument();
    expect(screen.getByText("Recupero singola giornata non completato")).toBeInTheDocument();
    expect(
      screen.getAllByText("INAZ ha ripresentato la pagina di login. Non e un problema della giornata: va verificata la credenziale o la sessione INAZ usata dalla sync.").length,
    ).toBeGreaterThan(0);
    expect(screen.getByRole("link", { name: "Apri Sync Presenze" })).toHaveAttribute("href", "/elaborazioni/presenze-sync");
  }, 8000);

  test("classifies operai without subgroup separately from truly unset profiles", async () => {
    render(<PresenzeGiornalierePage />);

    expect(await screen.findByText("Giornaliere")).toBeInTheDocument();
    fireEvent.change(await screen.findByLabelText("Mese operativo"), { target: { value: "2026-05" } });

    expect(await screen.findByRole("button", { name: "Operai da classificare (1)" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Profilo non impostato/i })).not.toBeInTheDocument();
    expect(screen.getAllByText("Operaio da classificare").length).toBeGreaterThan(0);
  });

  test("keeps the Inaz detail section for authorized punches even when detail rows are redundant", async () => {
    mocks.getPresenzeDailyRecord.mockResolvedValue({
      ...baseDailyRecord,
      request_status: "ACC",
      request_description: "Permesso ordinario (U)",
      detail_punch_rows: [
        { time: "06:55", direction: "E", terminal_label: "FENO-Fenoso", raw: {} },
        { time: "12:30", direction: "U", terminal_label: "FENO-Fenoso", raw: {} },
        { time: null, direction: null, terminal_label: null, raw: {} },
      ],
      punches: [
        {
          id: "p1",
          daily_record_id: "record-1",
          sequence: 1,
          entry_time: "06:55",
          exit_time: "12:30",
          terminal_label: "FENO-Fenoso",
          created_at: "2026-06-04T09:00:00Z",
        },
      ],
    });

    render(<PresenzeGiornalierePage />);

    fireEvent.change(await screen.findByLabelText("Mese operativo"), { target: { value: "2026-05" } });
    fireEvent.click(await screen.findByTitle("2026-05-16 · GAIA: in analisi · INAZ: Giornata anomala"));

    expect(screen.getByText("Timbrature dettaglio Inaz")).toBeInTheDocument();
    expect(await screen.findByText("Timbratura di uscita autorizzata da PODDA FABRIZIO")).toBeInTheDocument();
    expect(screen.getByText("Riga 1")).toBeInTheDocument();
    expect(screen.getByText("Riga 2")).toBeInTheDocument();
    expect(screen.getByText("2 righe lette")).toBeInTheDocument();
    expect(screen.getByText("Qui vedi le timbrature lette da Inaz per la giornata.")).toBeInTheDocument();
    expect(screen.getByText("12:30 (uscita autorizzata)")).toBeInTheDocument();
  });
});


describe("operational voucher and sync integration", () => {
  test("saves a manual voucher and refreshes the monthly matrix after INAZ", async () => {
    vi.resetAllMocks();
    mocks.getStoredAccessToken.mockReturnValue("operational-controls-token");
    mocks.getCurrentUser.mockResolvedValue({ id: 12, role: "admin", module_presenze: true });
    mocks.getPresenzeAccessContext.mockResolvedValue({ can_view_all_data: true, is_supervisor: false });
    mocks.listAllPresenzeCollaborators.mockResolvedValue([{ id: "collab-1", name: "Persona test", employee_code: "1854", contract_kind: "operaio", operai_group: "agrario" }]);
    const day = { ...baseDailyRecord, meal_voucher_manual: false, meal_voucher_count: 1, meal_voucher_automatic: true, meal_voucher_sources: ["automatic"] };
    mocks.listPresenzeDailyMatrixRecords.mockResolvedValue({ items: [day], total: 1 });
    mocks.getPresenzeDailyRecord.mockResolvedValue(day);
    mocks.updatePresenzeDailyRecord.mockResolvedValue({ ...day, meal_voucher_manual: true, meal_voucher_sources: ["automatic", "manual"] });
    const view = render(<PresenzeGiornalierePage />);
    fireEvent.change(screen.getByLabelText("Mese operativo"), { target: { value: "2026-05" } });
    await waitFor(() => expect(view.container.querySelector('button[title^="2026-05-16 · GAIA:"]')).not.toBeNull());
    fireEvent.click(view.container.querySelector('button[title^="2026-05-16 · GAIA:"]')!);
    await screen.findByLabelText("Buono pasto manuale");
    await waitFor(() => expect(mocks.getPresenzeDailyRecord).toHaveBeenCalled());
    await act(async () => {});
    fireEvent.click(screen.getByLabelText("Buono pasto manuale"));
    await waitFor(() => expect(screen.getByLabelText("Buono pasto manuale")).toBeChecked());
    expect(mocks.updatePresenzeDailyRecord).toHaveBeenCalledWith("operational-controls-token", "record-1", { meal_voucher_manual: true });
    expect(screen.getByText("Buono pasto: 1 · automatic + manual")).toBeInTheDocument();
    const previous = mocks.listPresenzeDailyMatrixRecords.mock.calls.length;
    fireEvent.click(screen.getByText("Simula completamento INAZ"));
    await waitFor(() => expect(mocks.listPresenzeDailyMatrixRecords.mock.calls.length).toBeGreaterThan(previous));
    const monthCalls = mocks.listPresenzeDailyMatrixRecords.mock.calls.length;
    fireEvent.change(screen.getByLabelText("Mese operativo"), { target: { value: "" } });
    expect(screen.getByLabelText("Mese operativo")).toHaveValue("2026-05");
    await act(async () => {});
    expect(mocks.listPresenzeDailyMatrixRecords).toHaveBeenCalledTimes(monthCalls);
  });
});


test("does not reload protected data when the session expires during a voucher save", async () => {
  vi.resetAllMocks();
  mocks.getStoredAccessToken.mockReturnValue("expiry-voucher-token");
  mocks.getCurrentUser.mockResolvedValue({ id: 12, role: "admin", module_presenze: true });
  mocks.getPresenzeAccessContext.mockResolvedValue({ can_view_all_data: true });
  mocks.listAllPresenzeCollaborators.mockResolvedValue([{ id: "collab-1", name: "Persona test", employee_code: "1854", contract_kind: "operaio", operai_group: "agrario" }]);
  const day = { ...baseDailyRecord, meal_voucher_manual: false, meal_voucher_count: 0 };
  mocks.listPresenzeDailyMatrixRecords.mockResolvedValue({ items: [day], total: 1 });
  mocks.getPresenzeDailyRecord.mockResolvedValue(day);
  let finish!: (record: PresenzeDailyRecord) => void;
  mocks.updatePresenzeDailyRecord.mockReturnValue(new Promise<PresenzeDailyRecord>(resolve => { finish = resolve; }));
  const view = render(<PresenzeGiornalierePage />);
  fireEvent.change(screen.getByLabelText("Mese operativo"), { target: { value: "2026-05" } });
  await waitFor(() => expect(view.container.querySelector('button[title^="2026-05-16 · GAIA:"]')).not.toBeNull());
  fireEvent.click(view.container.querySelector('button[title^="2026-05-16 · GAIA:"]')!);
  await waitFor(() => expect(mocks.getPresenzeDailyRecord).toHaveBeenCalled());
  await act(async () => {});
  fireEvent.click(screen.getByLabelText("Buono pasto manuale"));
  expect(mocks.updatePresenzeDailyRecord).toHaveBeenCalledTimes(1);
  mocks.getStoredAccessToken.mockReturnValue(null);
  await act(async () => finish({ ...day, meal_voucher_manual: true, meal_voucher_count: 1 } as PresenzeDailyRecord));
  expect(screen.getByLabelText("Buono pasto manuale")).toBeChecked();
  const calls = mocks.listPresenzeDailyMatrixRecords.mock.calls.length;
  fireEvent.click(screen.getByText("Simula completamento INAZ"));
  await act(async () => {});
  expect(mocks.listPresenzeDailyMatrixRecords).toHaveBeenCalledTimes(calls);
});
