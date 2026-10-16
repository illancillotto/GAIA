import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import PresenzeExportPage from "@/app/presenze/export/page";

const mocks = vi.hoisted(() => ({
  getStoredAccessToken: vi.fn(),
  getCurrentUser: vi.fn(),
  listAllPresenzeCollaborators: vi.fn(),
  listPresenzeDailyRecords: vi.fn(),
  listPresenzeXlsmExportJobs: vi.fn(),
  createPresenzeXlsmExportJob: vi.fn(),
  getPresenzeXlsmExportJob: vi.fn(),
  deletePresenzeXlsmExportJob: vi.fn(),
  downloadPresenzeXlsmExportArtifact: vi.fn(),
  listPresenzeStraordinariExportJobs: vi.fn(),
  previewPresenzeStraordinariExport: vi.fn(),
  createPresenzeStraordinariExportJob: vi.fn(),
  getPresenzeStraordinariExportJob: vi.fn(),
  deletePresenzeStraordinariExportJob: vi.fn(),
  downloadPresenzeStraordinariExportArtifact: vi.fn(),
}));

vi.mock("@/lib/auth", () => ({
  getStoredAccessToken: mocks.getStoredAccessToken,
}));

vi.mock("@/lib/api", () => ({
  getCurrentUser: mocks.getCurrentUser,
  listAllPresenzeCollaborators: mocks.listAllPresenzeCollaborators,
  listPresenzeDailyRecords: mocks.listPresenzeDailyRecords,
  listPresenzeXlsmExportJobs: mocks.listPresenzeXlsmExportJobs,
  createPresenzeXlsmExportJob: mocks.createPresenzeXlsmExportJob,
  getPresenzeXlsmExportJob: mocks.getPresenzeXlsmExportJob,
  deletePresenzeXlsmExportJob: mocks.deletePresenzeXlsmExportJob,
  downloadPresenzeXlsmExportArtifact: mocks.downloadPresenzeXlsmExportArtifact,
  listPresenzeStraordinariExportJobs: mocks.listPresenzeStraordinariExportJobs,
  previewPresenzeStraordinariExport: mocks.previewPresenzeStraordinariExport,
  createPresenzeStraordinariExportJob: mocks.createPresenzeStraordinariExportJob,
  getPresenzeStraordinariExportJob: mocks.getPresenzeStraordinariExportJob,
  deletePresenzeStraordinariExportJob: mocks.deletePresenzeStraordinariExportJob,
  downloadPresenzeStraordinariExportArtifact: mocks.downloadPresenzeStraordinariExportArtifact,
}));

vi.mock("@/components/app/protected-page", () => ({
  ProtectedPage: ({ children, title }: { children: React.ReactNode; title: string }) => (
    <div>
      <h1>{title}</h1>
      {children}
    </div>
  ),
}));

describe("Presenze export page", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  beforeEach(() => {
    mocks.getStoredAccessToken.mockReturnValue("token");
    mocks.getCurrentUser.mockResolvedValue({
      id: 1,
      username: "admin",
      email: "admin@example.local",
      role: "admin",
      enabled_modules: ["presenze"],
      is_active: true,
      created_at: "2026-06-04T09:00:00Z",
      updated_at: "2026-06-04T09:00:00Z",
    });
    mocks.listAllPresenzeCollaborators.mockResolvedValue([
      {
        id: "collab-1",
        owner_user_id: 1,
        application_user_id: 7,
        kint: "10159",
        kkint: "{demo}",
        employee_code: "1854",
        company_code: "53",
        company_label: "53 - CBO",
        name: "AMADU SALVATORE",
        birth_date: "1967-02-26",
        contract_kind: "operaio",
        standard_daily_minutes: 420,
        is_active: true,
        last_seen_at: "2026-06-04T09:00:00Z",
        created_at: "2026-06-04T09:00:00Z",
        updated_at: "2026-06-04T09:00:00Z",
      },
    ]);
    mocks.listPresenzeDailyRecords.mockResolvedValue({
      items: [
        {
          id: "record-1",
          collaborator_id: "collab-1",
          owner_user_id: 1,
          application_user_id: 7,
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
          trasferta_minutes: 180,
          trasferta_montano: false,
          reperibilita_unit: "hours",
          reperibilita_quantity: 4,
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
          detail_text: null,
          detail_error: null,
          special_day: true,
          holiday_kind: "ordinary",
          grants_recovery_day: false,
          recovery_day_credit: 0,
          uses_recovery_day: false,
          recovery_day_debit: 0,
          recovery_day_balance_delta: 0,
          raw_payload_json: {},
          source_job_id: null,
          created_at: "2026-06-04T09:00:00Z",
          updated_at: "2026-06-04T09:00:00Z",
          punches: [],
        },
      ],
      total: 1,
      page: 1,
      page_size: 200,
    });
    mocks.listPresenzeXlsmExportJobs.mockResolvedValue([
      {
        id: "job-archived-1",
        status: "completed",
        requested_by_user_id: 1,
        credential_id: null,
        import_job_id: null,
        period_start: "2026-05-01",
        period_end: "2026-05-31",
        collaborator_limit: 1,
        records_imported: 0,
        records_skipped: 0,
        records_errors: 0,
        json_artifact_path: "/tmp/giornaliere_export.xlsm",
        worker_log_path: "/tmp/worker.log",
        worker_pid: 1234,
        attempt_count: 1,
        max_attempts: 1,
        error_detail: null,
        params_json: { mode: "export_xlsm", progress: { state: "completed" } },
        created_at: "2026-06-04T09:00:00Z",
        started_at: "2026-06-04T09:00:01Z",
        finished_at: "2026-06-04T09:00:02Z",
      },
    ]);
    mocks.listPresenzeStraordinariExportJobs.mockResolvedValue([]);
    mocks.previewPresenzeStraordinariExport.mockResolvedValue({
      collaborator: {
        id: "collab-1",
        owner_user_id: 1,
        application_user_id: 1,
        kint: "10159",
        kkint: "{demo}",
        employee_code: "1854",
        company_code: "53",
        company_label: "53 - CBO",
        name: "AMADU SALVATORE",
        birth_date: "1967-02-26",
        contract_kind: "operaio",
        standard_daily_minutes: 420,
        is_active: true,
        last_seen_at: "2026-06-04T09:00:00Z",
        created_at: "2026-06-04T09:00:00Z",
        updated_at: "2026-06-04T09:00:00Z",
      },
      period_start: "2026-05-01",
      period_end: "2026-05-31",
      items: [
        {
          record_id: "record-1",
          work_date: "2026-05-16",
          motivation: "Intervento impianto",
          start_time: "14:30",
          end_time: "16:30",
          duration_minutes: 120,
          duration_label: "02:00",
        },
      ],
    });
    mocks.createPresenzeStraordinariExportJob.mockResolvedValue({
      id: "str-job-1",
      status: "pending",
      requested_by_user_id: 1,
      credential_id: null,
      import_job_id: null,
      period_start: "2026-05-01",
      period_end: "2026-05-31",
      collaborator_limit: 1,
      records_imported: 0,
      records_skipped: 0,
      records_errors: 0,
      json_artifact_path: "/tmp/straordinari.xlsx",
      worker_log_path: "/tmp/worker.log",
      worker_pid: 2233,
      attempt_count: 1,
      max_attempts: 1,
      error_detail: null,
      params_json: { mode: "export_straordinari_xlsx", progress: { state: "pending", last_event: "queued" } },
      created_at: "2026-06-04T09:00:00Z",
      started_at: null,
      finished_at: null,
    });
    mocks.getPresenzeStraordinariExportJob.mockResolvedValue({
      id: "str-job-1",
      status: "pending",
      requested_by_user_id: 1,
      credential_id: null,
      import_job_id: null,
      period_start: "2026-05-01",
      period_end: "2026-05-31",
      collaborator_limit: 1,
      records_imported: 0,
      records_skipped: 0,
      records_errors: 0,
      json_artifact_path: "/tmp/straordinari.xlsx",
      worker_log_path: "/tmp/worker.log",
      worker_pid: 2233,
      attempt_count: 1,
      max_attempts: 1,
      error_detail: null,
      params_json: { mode: "export_straordinari_xlsx", progress: { state: "pending", last_event: "queued" } },
      created_at: "2026-06-04T09:00:00Z",
      started_at: null,
      finished_at: null,
    });
    mocks.downloadPresenzeStraordinariExportArtifact.mockResolvedValue(new Blob(["test"], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" }));
    mocks.deletePresenzeStraordinariExportJob.mockResolvedValue(undefined);
    mocks.createPresenzeXlsmExportJob.mockResolvedValue({
      id: "job-1",
      status: "pending",
      requested_by_user_id: 1,
      credential_id: null,
      import_job_id: null,
      period_start: "2026-06-01",
      period_end: "2026-06-30",
      collaborator_limit: 1,
      records_imported: 0,
      records_skipped: 0,
      records_errors: 0,
      json_artifact_path: "/tmp/giornaliere_export.xlsm",
      worker_log_path: "/tmp/worker.log",
      worker_pid: 1234,
      attempt_count: 1,
      max_attempts: 1,
      error_detail: null,
      params_json: { mode: "export_xlsm", progress: { state: "pending", last_event: "queued" } },
      created_at: "2026-06-04T09:00:00Z",
      started_at: null,
      finished_at: null,
    });
    mocks.getPresenzeXlsmExportJob.mockResolvedValue({
      id: "job-1",
      status: "pending",
      requested_by_user_id: 1,
      credential_id: null,
      import_job_id: null,
      period_start: "2026-06-01",
      period_end: "2026-06-30",
      collaborator_limit: 1,
      records_imported: 0,
      records_skipped: 0,
      records_errors: 0,
      json_artifact_path: "/tmp/giornaliere_export.xlsm",
      worker_log_path: "/tmp/worker.log",
      worker_pid: 1234,
      attempt_count: 1,
      max_attempts: 1,
      error_detail: null,
      params_json: { mode: "export_xlsm", progress: { state: "pending", last_event: "queued" } },
      created_at: "2026-06-04T09:00:00Z",
      started_at: null,
      finished_at: null,
    });
    mocks.downloadPresenzeXlsmExportArtifact.mockResolvedValue(new Blob(["test"], { type: "application/vnd.ms-excel.sheet.macroEnabled.12" }));
    mocks.deletePresenzeXlsmExportJob.mockResolvedValue(undefined);
    vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:test");
    vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => {});
  });

  test("shows export history, starts async export and downloads completed files manually", async () => {
    render(<PresenzeExportPage />);

    await waitFor(() => expect(mocks.listAllPresenzeCollaborators).toHaveBeenCalled());
    await waitFor(() => expect(mocks.listPresenzeDailyRecords).toHaveBeenCalled());
    await waitFor(() => expect(mocks.listPresenzeXlsmExportJobs).toHaveBeenCalled());

    expect(screen.getByText("Giorni con trasferta")).toBeInTheDocument();
    expect(screen.getByText("3 ore totali esportabili")).toBeInTheDocument();
    expect(screen.getByText("Reperibilita strutturata")).toBeInTheDocument();
    expect(screen.getByText(/Il template XLSM legacy salva la reperibilita come flag/)).toBeInTheDocument();
    expect(screen.getByText("Ultimi export XLSM")).toBeInTheDocument();
    expect(screen.getByText(/il file restera disponibile qui a fine elaborazione/i)).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Tipologia contratto"), { target: { value: "operaio" } });
    fireEvent.click(screen.getByRole("button", { name: "Avvia export XLSM" }));

    await waitFor(() =>
      expect(mocks.createPresenzeXlsmExportJob).toHaveBeenCalledWith(
        "token",
        expect.objectContaining({
          collaborator_ids: ["collab-1"],
          employee_kind: "OPERAI",
        }),
      ),
    );

    expect(mocks.downloadPresenzeXlsmExportArtifact).not.toHaveBeenCalled();
    expect(screen.getByText(/Il file sara disponibile nella sezione Ultimi export XLSM/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Scarica file" }));

    await waitFor(() => expect(mocks.downloadPresenzeXlsmExportArtifact).toHaveBeenCalledWith("token", "job-archived-1", "xlsm"));
    expect(URL.createObjectURL).toHaveBeenCalled();
  });

  test("shows archive-style monthly preview in Anteprima export tab", async () => {
    render(<PresenzeExportPage />);

    await waitFor(() => expect(mocks.listAllPresenzeCollaborators).toHaveBeenCalled());
    await waitFor(() => expect(mocks.listPresenzeDailyRecords).toHaveBeenCalled());

    fireEvent.click(screen.getByRole("button", { name: /Anteprima export/i }));

    expect(screen.getByText("Collaboratori in matrice")).toBeInTheDocument();
    expect(screen.getByText(/Vista matrice del mese selezionato/i)).toBeInTheDocument();
    expect(screen.getByText("AMADU SALVATORE")).toBeInTheDocument();
    expect(screen.getByText("Ordinarie")).toBeInTheDocument();
    expect(screen.getByText("Anomalie")).toBeInTheDocument();
  });

  test("opens straordinari modal and creates async job with edited motivations", async () => {
    render(<PresenzeExportPage />);

    await waitFor(() => expect(mocks.getCurrentUser).toHaveBeenCalled());
    await waitFor(() => expect(mocks.listAllPresenzeCollaborators).toHaveBeenCalled());

    fireEvent.click(screen.getByRole("button", { name: "Compila motivazioni" }));

    await waitFor(() => expect(mocks.previewPresenzeStraordinariExport).toHaveBeenCalledWith("token", { collaboratorId: "collab-1" }));
    expect(screen.getByText("Motivazioni straordinari")).toBeInTheDocument();
    fireEvent.change(screen.getByDisplayValue("Intervento impianto"), { target: { value: "Chiusura segnalazione urgente" } });
    fireEvent.click(screen.getByRole("button", { name: "Genera file straordinari" }));

    await waitFor(() =>
      expect(mocks.createPresenzeStraordinariExportJob).toHaveBeenCalledWith("token", {
        collaborator_id: "collab-1",
        items: [{ record_id: "record-1", motivation: "Chiusura segnalazione urgente" }],
      }),
    );
  });

  test("removes a completed export job from history", async () => {
    render(<PresenzeExportPage />);

    await waitFor(() => expect(mocks.listPresenzeXlsmExportJobs).toHaveBeenCalled());
    expect(screen.getByText("maggio 2026")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Rimuovi" }));

    await waitFor(() => expect(mocks.deletePresenzeXlsmExportJob).toHaveBeenCalledWith("token", "job-archived-1"));
    await waitFor(() => expect(screen.queryByText("maggio 2026")).not.toBeInTheDocument());
  });
});

describe("Presenze export page job history polling (characterization)", () => {
  function buildJob(overrides: Record<string, unknown>) {
    return {
      id: "job-poll-1",
      status: "pending",
      requested_by_user_id: 1,
      credential_id: null,
      import_job_id: null,
      period_start: "2026-05-01",
      period_end: "2026-05-31",
      collaborator_limit: 1,
      records_imported: 0,
      records_skipped: 0,
      records_errors: 0,
      json_artifact_path: null,
      worker_log_path: null,
      worker_pid: null,
      attempt_count: 1,
      max_attempts: 1,
      error_detail: null,
      params_json: { mode: "export_xlsm" },
      created_at: "2026-06-04T09:00:00Z",
      started_at: null,
      finished_at: null,
      ...overrides,
    };
  }

  function mockSessionUser(role: string) {
    mocks.getCurrentUser.mockResolvedValue({
      id: 1,
      username: "user",
      email: "user@example.local",
      role,
      enabled_modules: ["presenze"],
      is_active: true,
      created_at: "2026-06-04T09:00:00Z",
      updated_at: "2026-06-04T09:00:00Z",
    });
  }

  async function advancePollingInterval() {
    await act(async () => {
      vi.advanceTimersByTime(2500);
    });
  }

  beforeEach(() => {
    vi.useFakeTimers({ toFake: ["setInterval", "clearInterval"] });
    Object.values(mocks).forEach((mock) => mock.mockReset());
    mocks.getStoredAccessToken.mockReturnValue("token");
    mockSessionUser("admin");
    mocks.listAllPresenzeCollaborators.mockResolvedValue([]);
    mocks.listPresenzeDailyRecords.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 500 });
    mocks.listPresenzeXlsmExportJobs.mockResolvedValue([]);
    mocks.listPresenzeStraordinariExportJobs.mockResolvedValue([]);
    mocks.createPresenzeXlsmExportJob.mockResolvedValue(buildJob({ id: "job-1", period_start: "2026-06-01", period_end: "2026-06-30" }));
    mocks.getPresenzeXlsmExportJob.mockResolvedValue(buildJob({ id: "job-1", period_start: "2026-06-01", period_end: "2026-06-30" }));
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  test("polls the XLSM history silently while a job is active and announces its completion once", async () => {
    mocks.listPresenzeXlsmExportJobs
      .mockResolvedValueOnce([buildJob({ status: "running" })])
      .mockResolvedValue([buildJob({ status: "completed" })]);

    render(<PresenzeExportPage />);

    await waitFor(() => expect(mocks.listPresenzeXlsmExportJobs).toHaveBeenCalledTimes(1));
    expect(mocks.listPresenzeXlsmExportJobs).toHaveBeenCalledWith("token", { limit: 25 });
    await screen.findByText("In lavorazione");
    expect(screen.queryByText(/pronto\. Trovi il file/)).not.toBeInTheDocument();

    await advancePollingInterval();

    await waitFor(() => expect(mocks.listPresenzeXlsmExportJobs).toHaveBeenCalledTimes(2));
    expect(await screen.findByText("Export maggio 2026 pronto. Trovi il file nella sezione Ultimi export XLSM.")).toBeInTheDocument();
    expect(screen.getByText("Pronto")).toBeInTheDocument();

    await advancePollingInterval();
    await advancePollingInterval();
    expect(mocks.listPresenzeXlsmExportJobs).toHaveBeenCalledTimes(2);
  });

  test("polls the straordinari history while a job is pending and announces its completion", async () => {
    mocks.listPresenzeStraordinariExportJobs
      .mockResolvedValueOnce([buildJob({ id: "str-poll-1", status: "pending" })])
      .mockResolvedValueOnce([buildJob({ id: "str-poll-1", status: "pending" })])
      .mockResolvedValue([buildJob({ id: "str-poll-1", status: "completed" })]);

    render(<PresenzeExportPage />);

    await waitFor(() => expect(mocks.listPresenzeStraordinariExportJobs).toHaveBeenCalledTimes(1));
    expect(mocks.listPresenzeStraordinariExportJobs).toHaveBeenCalledWith("token", { limit: 25 });

    await advancePollingInterval();
    await waitFor(() => expect(mocks.listPresenzeStraordinariExportJobs).toHaveBeenCalledTimes(2));
    expect(screen.queryByText(/Richiesta straordinari .* pronta/)).not.toBeInTheDocument();

    await advancePollingInterval();
    await waitFor(() => expect(mocks.listPresenzeStraordinariExportJobs).toHaveBeenCalledTimes(3));
    expect(await screen.findByText("Richiesta straordinari maggio 2026 pronta. Trovi il file nella sezione dedicata.")).toBeInTheDocument();

    await advancePollingInterval();
    expect(mocks.listPresenzeStraordinariExportJobs).toHaveBeenCalledTimes(3);
  });

  test("suppresses the completion notice on the initial load and does not poll without active jobs", async () => {
    mocks.listPresenzeXlsmExportJobs.mockResolvedValue([buildJob({ status: "completed" })]);
    mocks.listPresenzeStraordinariExportJobs.mockResolvedValue([buildJob({ id: "str-done", status: "completed" })]);

    render(<PresenzeExportPage />);

    await waitFor(() => expect(mocks.listPresenzeXlsmExportJobs).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(mocks.listPresenzeStraordinariExportJobs).toHaveBeenCalledTimes(1));
    await advancePollingInterval();
    await advancePollingInterval();

    expect(mocks.listPresenzeXlsmExportJobs).toHaveBeenCalledTimes(1);
    expect(mocks.listPresenzeStraordinariExportJobs).toHaveBeenCalledTimes(1);
    expect(screen.queryByText(/pronto\. Trovi il file/)).not.toBeInTheDocument();
    expect(screen.queryByText(/pronta\. Trovi il file/)).not.toBeInTheDocument();
  });

  test("starts polling for a job registered by the export action and announces its completion", async () => {
    mocks.listPresenzeXlsmExportJobs.mockResolvedValueOnce([]).mockResolvedValue([
      buildJob({ id: "job-1", status: "completed", period_start: "2026-06-01", period_end: "2026-06-30" }),
    ]);

    render(<PresenzeExportPage />);

    await waitFor(() => expect(mocks.listPresenzeXlsmExportJobs).toHaveBeenCalledTimes(1));
    await advancePollingInterval();
    expect(mocks.listPresenzeXlsmExportJobs).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByRole("button", { name: "Avvia export XLSM" }));
    await waitFor(() => expect(mocks.getPresenzeXlsmExportJob).toHaveBeenCalledWith("token", "job-1"));
    await screen.findByText(/Export avviato\./);

    await advancePollingInterval();

    await waitFor(() => expect(mocks.listPresenzeXlsmExportJobs).toHaveBeenCalledTimes(2));
    expect(await screen.findByText("Export giugno 2026 pronto. Trovi il file nella sezione Ultimi export XLSM.")).toBeInTheDocument();
  });

  test("never loads the XLSM history for a non-admin user but still loads straordinari", async () => {
    mockSessionUser("viewer");
    mocks.listPresenzeStraordinariExportJobs.mockResolvedValue([buildJob({ id: "str-own", status: "running" })]);

    render(<PresenzeExportPage />);

    await waitFor(() => expect(mocks.listPresenzeStraordinariExportJobs).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(mocks.getCurrentUser).toHaveBeenCalled());
    await advancePollingInterval();

    await waitFor(() => expect(mocks.listPresenzeStraordinariExportJobs).toHaveBeenCalledTimes(2));
    expect(mocks.listPresenzeXlsmExportJobs).not.toHaveBeenCalled();
  });

  test("shows the XLSM history fallback error for non-Error rejections", async () => {
    mocks.listPresenzeXlsmExportJobs.mockRejectedValue("network down");

    render(<PresenzeExportPage />);

    expect(await screen.findByText("Errore caricamento storico export XLSM")).toBeInTheDocument();
  });

  test("shows the XLSM history error message for Error rejections", async () => {
    mocks.listPresenzeXlsmExportJobs.mockRejectedValue(new Error("Storico XLSM non disponibile"));

    render(<PresenzeExportPage />);

    expect(await screen.findByText("Storico XLSM non disponibile")).toBeInTheDocument();
  });

  test("shows the straordinari history fallback error for non-Error rejections", async () => {
    mocks.listPresenzeStraordinariExportJobs.mockRejectedValue("network down");

    render(<PresenzeExportPage />);

    expect(await screen.findByText("Errore caricamento storico export straordinari")).toBeInTheDocument();
  });

  test("does not load any history without an access token", async () => {
    mocks.getStoredAccessToken.mockReturnValue(null);

    render(<PresenzeExportPage />);

    await advancePollingInterval();
    expect(mocks.listPresenzeXlsmExportJobs).not.toHaveBeenCalled();
    expect(mocks.listPresenzeStraordinariExportJobs).not.toHaveBeenCalled();
  });

  test("stops polling after unmount", async () => {
    mocks.listPresenzeXlsmExportJobs.mockResolvedValue([buildJob({ status: "running" })]);
    mocks.listPresenzeStraordinariExportJobs.mockResolvedValue([buildJob({ id: "str-run", status: "running" })]);

    const { unmount } = render(<PresenzeExportPage />);

    await waitFor(() => expect(mocks.listPresenzeXlsmExportJobs).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(mocks.listPresenzeStraordinariExportJobs).toHaveBeenCalledTimes(1));
    await advancePollingInterval();
    await waitFor(() => expect(mocks.listPresenzeXlsmExportJobs).toHaveBeenCalledTimes(2));
    await waitFor(() => expect(mocks.listPresenzeStraordinariExportJobs).toHaveBeenCalledTimes(2));

    unmount();
    expect(vi.getTimerCount()).toBe(0);
    await advancePollingInterval();

    expect(mocks.listPresenzeXlsmExportJobs).toHaveBeenCalledTimes(2);
    expect(mocks.listPresenzeStraordinariExportJobs).toHaveBeenCalledTimes(2);
  });

  test("starts polling for a straordinari job registered by the create action and announces its completion", async () => {
    mocks.listAllPresenzeCollaborators.mockResolvedValue([
      {
        id: "collab-1",
        owner_user_id: 1,
        application_user_id: 7,
        kint: "10159",
        kkint: "{demo}",
        employee_code: "1854",
        company_code: "53",
        company_label: "53 - CBO",
        name: "AMADU SALVATORE",
        birth_date: "1967-02-26",
        contract_kind: "operaio",
        standard_daily_minutes: 420,
        is_active: true,
        last_seen_at: "2026-06-04T09:00:00Z",
        created_at: "2026-06-04T09:00:00Z",
        updated_at: "2026-06-04T09:00:00Z",
      },
    ]);
    mocks.previewPresenzeStraordinariExport.mockResolvedValue({
      collaborator: { id: "collab-1", name: "AMADU SALVATORE" },
      period_start: "2026-05-01",
      period_end: "2026-05-31",
      items: [
        {
          record_id: "record-1",
          work_date: "2026-05-16",
          motivation: "Intervento impianto",
          start_time: "14:30",
          end_time: "16:30",
          duration_minutes: 120,
          duration_label: "02:00",
        },
      ],
    });
    mocks.createPresenzeStraordinariExportJob.mockResolvedValue(buildJob({ id: "str-new", status: "pending" }));
    mocks.getPresenzeStraordinariExportJob.mockResolvedValue(buildJob({ id: "str-new", status: "pending" }));
    mocks.listPresenzeStraordinariExportJobs.mockResolvedValueOnce([]).mockResolvedValue([buildJob({ id: "str-new", status: "completed" })]);

    render(<PresenzeExportPage />);

    await waitFor(() => expect(mocks.listPresenzeStraordinariExportJobs).toHaveBeenCalledTimes(1));
    await advancePollingInterval();
    expect(mocks.listPresenzeStraordinariExportJobs).toHaveBeenCalledTimes(1);

    await waitFor(() => expect(screen.getByRole("button", { name: "Compila motivazioni" })).toBeEnabled());
    fireEvent.click(screen.getByRole("button", { name: "Compila motivazioni" }));
    await waitFor(() => expect(mocks.previewPresenzeStraordinariExport).toHaveBeenCalledWith("token", { collaboratorId: "collab-1" }));
    fireEvent.click(await screen.findByRole("button", { name: "Genera file straordinari" }));
    await waitFor(() => expect(mocks.getPresenzeStraordinariExportJob).toHaveBeenCalledWith("token", "str-new"));
    await screen.findByText(/Richiesta straordinari avviata\./);

    await advancePollingInterval();

    await waitFor(() => expect(mocks.listPresenzeStraordinariExportJobs).toHaveBeenCalledTimes(2));
    expect(await screen.findByText("Richiesta straordinari maggio 2026 pronta. Trovi il file nella sezione dedicata.")).toBeInTheDocument();
  });
});
