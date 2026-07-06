import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import PresenzeCapisettorePage from "@/app/presenze/capisettore/page";
import PresenzeCollaboratoriPage from "@/app/presenze/collaboratori/page";
import PresenzeImportPage from "@/app/presenze/import/page";
import PresenzePage from "@/app/presenze/page";
import PresenzeSettingsPage from "@/app/presenze/settings/page";
import PresenzeSyncPage from "@/app/presenze/sync/page";

const mocks = vi.hoisted(() => ({
  getStoredAccessToken: vi.fn(),
  getPresenzeDashboardSummary: vi.fn(),
  getCurrentUser: vi.fn(),
  listAllApplicationUsers: vi.fn(),
  listAllPresenzeCollaborators: vi.fn(),
  listPresenzeApplicationUsers: vi.fn(),
  listPresenzeCollaborators: vi.fn(),
  listPresenzeDailyRecords: vi.fn(),
  listPresenzeSupervisorAssignments: vi.fn(),
  mapPresenzeCollaboratorApplicationUser: vi.fn(),
  updatePresenzeCollaboratorContractProfile: vi.fn(),
  listPresenzeImportJobs: vi.fn(),
  previewPresenzeImport: vi.fn(),
  importPresenzeJson: vi.fn(),
  listPresenzeSyncJobs: vi.fn(),
  createPresenzeSyncJob: vi.fn(),
  retryPresenzeSyncJob: vi.fn(),
  retrySelectedPresenzeSyncJob: vi.fn(),
  cancelPresenzeSyncJob: vi.fn(),
  deletePresenzeSyncJob: vi.fn(),
  downloadPresenzeSyncArtifact: vi.fn(),
  getPresenzeAutoSyncConfig: vi.fn(),
  updatePresenzeAutoSyncConfig: vi.fn(),
  listPresenzeCredentials: vi.fn(),
  createPresenzeCredential: vi.fn(),
  updatePresenzeCredential: vi.fn(),
  deletePresenzeCredential: vi.fn(),
  testPresenzeCredential: vi.fn(),
  updatePresenzeSupervisorAssignment: vi.fn(),
  push: vi.fn(),
}));

vi.mock("@/lib/auth", () => ({
  getStoredAccessToken: mocks.getStoredAccessToken,
}));

vi.mock("@/lib/api", () => ({
  getPresenzeDashboardSummary: mocks.getPresenzeDashboardSummary,
  getCurrentUser: mocks.getCurrentUser,
  listAllApplicationUsers: mocks.listAllApplicationUsers,
  listAllPresenzeCollaborators: mocks.listAllPresenzeCollaborators,
  listPresenzeApplicationUsers: mocks.listPresenzeApplicationUsers,
  listPresenzeCollaborators: mocks.listPresenzeCollaborators,
  listPresenzeDailyRecords: mocks.listPresenzeDailyRecords,
  listPresenzeSupervisorAssignments: mocks.listPresenzeSupervisorAssignments,
  mapPresenzeCollaboratorApplicationUser: mocks.mapPresenzeCollaboratorApplicationUser,
  updatePresenzeCollaboratorContractProfile: mocks.updatePresenzeCollaboratorContractProfile,
  listPresenzeImportJobs: mocks.listPresenzeImportJobs,
  previewPresenzeImport: mocks.previewPresenzeImport,
  importPresenzeJson: mocks.importPresenzeJson,
  listPresenzeSyncJobs: mocks.listPresenzeSyncJobs,
  createPresenzeSyncJob: mocks.createPresenzeSyncJob,
  retryPresenzeSyncJob: mocks.retryPresenzeSyncJob,
  retrySelectedPresenzeSyncJob: mocks.retrySelectedPresenzeSyncJob,
  cancelPresenzeSyncJob: mocks.cancelPresenzeSyncJob,
  deletePresenzeSyncJob: mocks.deletePresenzeSyncJob,
  downloadPresenzeSyncArtifact: mocks.downloadPresenzeSyncArtifact,
  getPresenzeAutoSyncConfig: mocks.getPresenzeAutoSyncConfig,
  updatePresenzeAutoSyncConfig: mocks.updatePresenzeAutoSyncConfig,
  listPresenzeCredentials: mocks.listPresenzeCredentials,
  createPresenzeCredential: mocks.createPresenzeCredential,
  updatePresenzeCredential: mocks.updatePresenzeCredential,
  deletePresenzeCredential: mocks.deletePresenzeCredential,
  testPresenzeCredential: mocks.testPresenzeCredential,
  updatePresenzeSupervisorAssignment: mocks.updatePresenzeSupervisorAssignment,
}));

vi.mock("@/components/app/protected-page", () => ({
  ProtectedPage: ({ children, title }: { children: React.ReactNode; title: string }) => (
    <div>
      <h1>{title}</h1>
      {children}
    </div>
  ),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mocks.push, replace: mocks.push }),
}));

describe("Presenze pages", () => {
  beforeEach(() => {
    mocks.getStoredAccessToken.mockReturnValue("token");
    mocks.getCurrentUser.mockResolvedValue({
      id: 1,
      username: "admin",
      email: "admin@example.local",
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
    mocks.listAllApplicationUsers.mockResolvedValue([
      {
        id: 7,
        username: "mrossi",
        email: "mrossi@example.local",
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
        created_at: "2026-05-29T00:00:00Z",
        updated_at: "2026-05-29T00:00:00Z",
      },
    ]);
    mocks.listAllPresenzeCollaborators.mockResolvedValue([
      {
        id: "collab-1",
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
        last_seen_at: "2026-05-29T09:00:00Z",
        created_at: "2026-05-29T09:00:00Z",
        updated_at: "2026-05-29T09:00:00Z",
      },
      {
        id: "collab-2",
        application_user_id: null,
        kint: "10184",
        kkint: "{demo-2}",
        employee_code: "2101",
        company_code: "53",
        company_label: "53 - CBO",
        name: "ARDU ANTONELLO",
        birth_date: "1959-06-12",
        contract_kind: "operaio",
        operai_group: null,
        standard_daily_minutes: 420,
        is_active: true,
        last_seen_at: "2026-05-29T09:00:00Z",
        created_at: "2026-05-29T09:00:00Z",
        updated_at: "2026-05-29T09:00:00Z",
      },
    ]);
    mocks.listPresenzeCollaborators.mockResolvedValue({
      items: [
        {
          id: "collab-1",
          owner_user_id: 1,
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
          last_seen_at: "2026-05-29T09:00:00Z",
          created_at: "2026-05-29T09:00:00Z",
          updated_at: "2026-05-29T09:00:00Z",
        },
      ],
      total: 1,
      page: 1,
      page_size: 200,
    });
    mocks.listPresenzeApplicationUsers.mockResolvedValue([
      {
        id: 7,
        username: "mrossi",
        email: "mrossi@example.local",
        full_name: "Mario Rossi",
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
        created_at: "2026-05-29T00:00:00Z",
        updated_at: "2026-05-29T00:00:00Z",
      },
    ]);
    mocks.listPresenzeSupervisorAssignments.mockResolvedValue([]);
    mocks.listPresenzeDailyRecords.mockResolvedValue({
      items: [
        {
          id: "record-1",
          collaborator_id: "collab-1",
          owner_user_id: 1,
          application_user_id: null,
          work_date: "2026-05-01",
          schedule_code: "OPE0714",
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
          effective_straordinario_minutes: null,
          effective_mpe_minutes: null,
          effective_extra_minutes: null,
          stato: "Giornata regolare",
          evidenze: null,
          raw_weekday: "V",
          detail_title: null,
          detail_status: "Giornata regolare",
          detail_programmed_schedule: "OPE0714",
          detail_effective_schedule: null,
          detail_time_slots: "07:00 - 14:00",
          detail_schedule_type: null,
          detail_theoretical_hours: "07:00",
          detail_absence_hours: "00:00",
          detail_day_summary: {},
          detail_day_totals: {},
          detail_requests: [],
          detail_anomalies: [],
          detail_text: null,
          detail_error: null,
          special_day: false,
          raw_payload_json: {},
          source_job_id: null,
          created_at: "2026-05-29T09:00:00Z",
          updated_at: "2026-05-29T09:00:00Z",
          punches: [],
        },
      ],
      total: 1,
      page: 1,
      page_size: 200,
    });
    mocks.mapPresenzeCollaboratorApplicationUser.mockResolvedValue({
      id: "collab-1",
      application_user_id: 7,
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
      last_seen_at: "2026-05-29T09:00:00Z",
      created_at: "2026-05-29T09:00:00Z",
      updated_at: "2026-05-29T09:00:00Z",
    });
    mocks.updatePresenzeCollaboratorContractProfile.mockImplementation(async (_token, collaboratorId, payload) => ({
      id: collaboratorId,
      owner_user_id: 1,
      application_user_id: null,
      kint: collaboratorId === "collab-2" ? "10184" : "10159",
      kkint: collaboratorId === "collab-2" ? "{demo-2}" : "{demo}",
      employee_code: collaboratorId === "collab-2" ? "2101" : "1854",
      company_code: "53",
      company_label: "53 - CBO",
      name: collaboratorId === "collab-2" ? "ARDU ANTONELLO" : "AMADU SALVATORE",
      birth_date: collaboratorId === "collab-2" ? "1959-06-12" : "1967-02-26",
      contract_kind: payload.contract_kind ?? null,
      operai_group: payload.operai_group ?? null,
      standard_daily_minutes: payload.standard_daily_minutes ?? null,
      is_active: true,
      last_seen_at: "2026-05-29T09:00:00Z",
      created_at: "2026-05-29T09:00:00Z",
      updated_at: "2026-05-29T09:00:00Z",
    }));
    mocks.listPresenzeImportJobs.mockResolvedValue([]);
    mocks.previewPresenzeImport.mockResolvedValue({
      total_collaborators: 1,
      total_daily_rows: 31,
      total_summary_rows: 7,
      collaborators: [
        {
          employee_code: "1854",
          company_code: "53",
          name: "AMADU SALVATORE",
          application_user_id: null,
          total_daily_rows: 31,
          total_summary_rows: 7,
          period_start: "2026-05-01",
          period_end: "2026-05-31",
        },
      ],
      errors: [],
    });
    mocks.listPresenzeSyncJobs.mockResolvedValue([]);
    mocks.getPresenzeAutoSyncConfig.mockResolvedValue({
      job_enabled: false,
      credential_id: null,
      collaborator_limit: null,
      schedule_cron: "0 6,12,18 * * *",
      schedule_timezone: "Europe/Rome",
      schedule_times: ["06:00", "12:00", "18:00"],
      updated_by_user_id: null,
      updated_at: null,
    });
    mocks.updatePresenzeAutoSyncConfig.mockResolvedValue({
      job_enabled: true,
      credential_id: 4,
      collaborator_limit: null,
      schedule_cron: "0 6,12,18 * * *",
      schedule_timezone: "Europe/Rome",
      schedule_times: ["06:00", "12:00", "18:00"],
      updated_by_user_id: 1,
      updated_at: "2026-05-29T09:00:00Z",
    });
    mocks.listPresenzeCredentials.mockResolvedValue([
      {
        id: 4,
        application_user_id: 1,
        label: "Ufficio HR",
        username: "hr.inaz",
        active: true,
        last_used_at: null,
        last_authenticated_url: null,
        last_error: null,
        consecutive_failures: 0,
        created_at: "2026-05-29T09:00:00Z",
        updated_at: "2026-05-29T09:00:00Z",
      },
    ]);
    mocks.createPresenzeSyncJob.mockResolvedValue({
      id: "sync-1",
      status: "pending",
      requested_by_user_id: 1,
      credential_id: null,
      import_job_id: null,
      period_start: "2026-05-01",
      period_end: "2026-05-31",
      collaborator_limit: 2,
      records_imported: 0,
      records_skipped: 0,
      records_errors: 0,
      json_artifact_path: "/tmp/presenze/sync-1/presenze_collaboratori.json",
      worker_log_path: "/tmp/presenze/sync-1/worker.log",
      worker_pid: 4242,
      attempt_count: 0,
      max_attempts: 3,
      error_detail: null,
      params_json: { year: 2026, month: 5 },
      created_at: "2026-05-29T09:00:00Z",
      started_at: null,
      finished_at: null,
    });
    mocks.createPresenzeCredential.mockResolvedValue({
      id: 5,
      application_user_id: 1,
      label: "Admin Presenze",
      username: "admin.inaz",
      active: true,
      last_used_at: null,
      last_authenticated_url: null,
      last_error: null,
      consecutive_failures: 0,
      created_at: "2026-05-29T09:00:00Z",
      updated_at: "2026-05-29T09:00:00Z",
    });
    mocks.updatePresenzeSupervisorAssignment.mockResolvedValue({
      id: 1,
      collaborator_id: "collab-1",
      supervisor_user_id: 7,
      assigned_by_user_id: 1,
      created_at: "2026-05-29T09:00:00Z",
      updated_at: "2026-05-29T09:10:00Z",
      supervisor: {
        id: 7,
        username: "mrossi",
        email: "mrossi@example.local",
        full_name: "Mario Rossi",
        role: "viewer",
        is_active: true,
      },
      collaborator: {
        id: "collab-1",
        owner_user_id: 1,
        application_user_id: null,
        kint: "10159",
        kkint: "{demo}",
        employee_code: "1854",
        company_code: "53",
        company_label: "53 - CBO",
        name: "AMADU SALVATORE",
        birth_date: "1967-02-26",
        is_active: true,
        last_seen_at: "2026-05-29T09:00:00Z",
        created_at: "2026-05-29T09:00:00Z",
        updated_at: "2026-05-29T09:10:00Z",
      },
    });
    mocks.downloadPresenzeSyncArtifact.mockResolvedValue(new Blob(['{"ok":true}'], { type: "application/json" }));
    mocks.retrySelectedPresenzeSyncJob.mockResolvedValue({
      id: "sync-retry-selected-1",
      status: "pending",
      requested_by_user_id: 1,
      credential_id: 4,
      import_job_id: null,
      period_start: "2026-05-01",
      period_end: "2026-05-31",
      collaborator_limit: null,
      records_imported: 0,
      records_skipped: 0,
      records_errors: 0,
      json_artifact_path: "/tmp/presenze/sync-retry-selected-1/presenze_collaboratori.json",
      worker_log_path: "/tmp/presenze/sync-retry-selected-1/worker.log",
      worker_pid: 5252,
      attempt_count: 0,
      max_attempts: 3,
      error_detail: null,
      params_json: { trigger: "retry_selected", employee_codes: ["1396"] },
      created_at: "2026-05-29T09:00:00Z",
      started_at: null,
      finished_at: null,
    });
    mocks.cancelPresenzeSyncJob.mockResolvedValue({
      id: "sync-1",
      status: "cancelled",
      requested_by_user_id: 1,
      credential_id: null,
      import_job_id: null,
      period_start: "2026-05-01",
      period_end: "2026-05-31",
      collaborator_limit: 2,
      records_imported: 0,
      records_skipped: 0,
      records_errors: 0,
      json_artifact_path: "/tmp/presenze/sync-1/presenze_collaboratori.json",
      worker_log_path: "/tmp/presenze/sync-1/worker.log",
      worker_pid: 4242,
      attempt_count: 1,
      max_attempts: 3,
      error_detail: "Sync job cancelled by user",
      params_json: { year: 2026, month: 5 },
      created_at: "2026-05-29T09:00:00Z",
      started_at: "2026-05-29T09:01:00Z",
      finished_at: "2026-05-29T09:02:00Z",
    });
  });

  test("renders collaborators and saves mapping", async () => {
    render(<PresenzeCollaboratoriPage />);

    await screen.findAllByText("AMADU SALVATORE");
    expect(screen.getAllByText("Operaio agrario").length).toBeGreaterThan(0);
    const selects = screen.getAllByRole("combobox");
    fireEvent.change(selects[selects.length - 2], { target: { value: "7" } });
    fireEvent.click(screen.getAllByText("Salva")[0]);

    await waitFor(() => {
      expect(mocks.mapPresenzeCollaboratorApplicationUser).toHaveBeenCalledWith("token", "collab-1", 7);
    });
  });

  test("filters collaborators by operai group", async () => {
    render(<PresenzeCollaboratoriPage />);

    await screen.findAllByText("AMADU SALVATORE");
    fireEvent.change(screen.getByLabelText("Gruppo operai"), { target: { value: "agrario" } });
    expect(screen.getAllByText("AMADU SALVATORE").length).toBeGreaterThan(0);

    fireEvent.change(screen.getByLabelText("Gruppo operai"), { target: { value: "catasto_magazzino" } });
    await waitFor(() => {
      expect(screen.queryByText("AMADU SALVATORE")).not.toBeInTheDocument();
    });
  });

  test("opens contract wizard and saves missing operaio group", async () => {
    render(<PresenzeCollaboratoriPage />);

    await screen.findAllByText("AMADU SALVATORE");
    fireEvent.click(screen.getByText("Wizard contratti (1)"));
    fireEvent.change(screen.getByLabelText("Contratto ARDU ANTONELLO"), { target: { value: "operaio_catasto_magazzino" } });
    fireEvent.click(screen.getByText("Salva profili"));

    await waitFor(() => {
      expect(mocks.updatePresenzeCollaboratorContractProfile).toHaveBeenCalledWith("token", "collab-2", {
        contract_kind: "operaio",
        operai_group: "catasto_magazzino",
        standard_daily_minutes: 420,
      });
    });
  });

  test("redirects capisettore page to organigramma", async () => {
    render(<PresenzeCapisettorePage />);

    await waitFor(() => {
      expect(mocks.push).toHaveBeenCalledWith("/presenze/organigramma");
    });
  });
  test("renders the inaz dashboard with monthly presence metrics", async () => {
    mocks.listPresenzeCollaborators.mockResolvedValue({
      items: [
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
          operai_group: "agrario",
          standard_daily_minutes: 420,
          is_active: true,
          last_seen_at: "2026-05-29T09:00:00Z",
          created_at: "2026-05-29T09:00:00Z",
          updated_at: "2026-05-29T09:00:00Z",
        },
      ],
      total: 1,
      page: 1,
      page_size: 200,
    });
    mocks.getPresenzeDashboardSummary.mockResolvedValue({
      collaborators_total: 1,
      mapped_collaborators_total: 1,
      active_collaborators_total: 1,
      daily_records_total: 1,
      ordinary_minutes_total: 330,
      absence_minutes_total: 120,
      extra_minutes_total: 120,
      straordinario_minutes_total: 75,
      maggior_presenza_minutes_total: 45,
      km_total: 24,
      trasferta_minutes_total: 0,
      trasferta_days_total: 0,
      trasferta_montano_days_total: 0,
      anomaly_total: 1,
      special_day_total: 1,
      recovery_days_matured_total: 0,
      recovery_days_used_total: 0,
      recovery_days_balance_total: 0,
      worked_days_total: 1,
      absence_days_total: 1,
      justified_days_total: 0,
      cause_stats: { Permessi: 1 },
      schedule_stats: [{ code: "OPESAB", count: 1 }],
    });
    mocks.listPresenzeDailyRecords.mockResolvedValue({
      items: [
        {
          id: "record-1",
          collaborator_id: "collab-1",
          owner_user_id: 1,
          application_user_id: 7,
          work_date: "2026-06-16",
          schedule_code: "OPESAB",
          teo_minutes: 390,
          ordinary_minutes: 330,
          absence_minutes: 60,
          justified_minutes: 0,
          maggiorazione_minutes: 0,
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
          detail_day_summary: {},
          detail_day_totals: {},
          detail_requests: [],
          detail_anomalies: [{ "Anomalia giornata": "Ore mancanti" }],
          detail_text: null,
          detail_error: null,
          special_day: true,
          raw_payload_json: {},
          source_job_id: null,
          created_at: "2026-05-29T09:00:00Z",
          updated_at: "2026-05-29T09:00:00Z",
          punches: [],
        },
      ],
      total: 1,
      page: 1,
      page_size: 200,
    });
    mocks.listPresenzeSyncJobs.mockResolvedValue([
      {
        id: "sync-1",
        status: "running",
        requested_by_user_id: 1,
        credential_id: 4,
        import_job_id: null,
        period_start: "2026-06-01",
        period_end: "2026-06-30",
        collaborator_limit: null,
        records_imported: 1,
        records_skipped: 0,
        records_errors: 0,
        json_artifact_path: "/tmp/presenze/sync-1/presenze_collaboratori.json",
        worker_log_path: "/tmp/presenze/sync-1/worker.log",
        worker_pid: 4242,
        attempt_count: 1,
        max_attempts: 3,
        error_detail: null,
        params_json: {
          progress: {
            index: 1,
            total: 1,
            completed_collaborators: 1,
            failed_collaborators: 0,
            last_event: "job_completed",
          },
        },
        created_at: "2026-05-29T09:00:00Z",
        started_at: "2026-05-29T09:01:00Z",
        finished_at: null,
      },
    ]);

    render(<PresenzePage />);

    expect(await screen.findByText("Supervisiona collaboratori, cartellini ed export giornaliere da un unico workspace.")).toBeInTheDocument();
    expect(screen.getAllByText("5.5 h").length).toBeGreaterThan(0);
    expect(screen.getAllByText("2.0 h").length).toBeGreaterThan(0);
    expect(screen.getByText("Recuperi maturati")).toBeInTheDocument();
    expect(screen.getByText("Saldo recuperi")).toBeInTheDocument();
    expect(screen.getByText("Permessi")).toBeInTheDocument();
    expect(screen.getByText("OPESAB")).toBeInTheDocument();
  });

  test("redirects import page to sync", async () => {
    render(<PresenzeImportPage />);

    await waitFor(() => {
      expect(mocks.push).toHaveBeenCalledWith("/presenze/sync");
    });
  });

  test("creates a live sync job", async () => {
    render(<PresenzeSyncPage />);

    await waitFor(() => {
      expect(screen.getByLabelText("Credenziale portale")).toHaveValue("4");
    });
    fireEvent.change(screen.getByLabelText("Anno"), { target: { value: "2026" } });
    fireEvent.change(screen.getByLabelText("Mese"), { target: { value: "05" } });
    fireEvent.change(screen.getByLabelText("Credenziale portale"), { target: { value: "4" } });
    fireEvent.change(screen.getByPlaceholderText("Vuoto = tutti"), { target: { value: "2" } });
    fireEvent.click(screen.getByText("Avvia sync live"));

    await waitFor(() => {
      expect(mocks.createPresenzeSyncJob).toHaveBeenCalledWith("token", {
        year: 2026,
        month: 5,
        credential_id: 4,
        collaborator_limit: 2,
      });
      expect(screen.getByText(/Job live sync creato/)).toBeInTheDocument();
    });
  });

  test("downloads a sync artifact", async () => {
    mocks.listPresenzeSyncJobs.mockResolvedValue([
      {
        id: "sync-1",
        status: "completed",
        requested_by_user_id: 1,
        credential_id: null,
        import_job_id: "import-1",
        period_start: "2026-05-01",
        period_end: "2026-05-31",
        collaborator_limit: null,
        records_imported: 3,
        records_skipped: 0,
        records_errors: 0,
        json_artifact_path: "/tmp/presenze/sync-1/presenze_collaboratori.json",
        worker_log_path: "/tmp/presenze/sync-1/worker.log",
        worker_pid: 4242,
        attempt_count: 1,
        max_attempts: 3,
        error_detail: null,
        params_json: { auth_mode: "credential" },
        created_at: "2026-05-29T09:00:00Z",
        started_at: "2026-05-29T09:01:00Z",
        finished_at: "2026-05-29T09:02:00Z",
      },
    ]);

    const createObjectUrlSpy = vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:demo");
    const revokeObjectUrlSpy = vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => {});
    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});

    render(<PresenzeSyncPage />);
    fireEvent.click(await screen.findByText("Scarica JSON"));

    await waitFor(() => {
      expect(mocks.downloadPresenzeSyncArtifact).toHaveBeenCalledWith("token", "sync-1", "json");
    });

    createObjectUrlSpy.mockRestore();
    revokeObjectUrlSpy.mockRestore();
    clickSpy.mockRestore();
  });

  test("cancels an active sync job", async () => {
    mocks.listPresenzeSyncJobs.mockResolvedValue([
      {
        id: "sync-1",
        status: "running",
        requested_by_user_id: 1,
        credential_id: null,
        import_job_id: null,
        period_start: "2026-05-01",
        period_end: "2026-05-31",
        collaborator_limit: 2,
        records_imported: 0,
        records_skipped: 0,
        records_errors: 0,
        json_artifact_path: "/tmp/presenze/sync-1/presenze_collaboratori.json",
        worker_log_path: "/tmp/presenze/sync-1/worker.log",
        worker_pid: 4242,
        attempt_count: 1,
        max_attempts: 3,
        error_detail: null,
        params_json: { auth_mode: "credential" },
        created_at: "2026-05-29T09:00:00Z",
        started_at: "2026-05-29T09:01:00Z",
        finished_at: null,
      },
    ]);

    render(<PresenzeSyncPage />);
    fireEvent.click(await screen.findByText("Annulla job"));

    await waitFor(() => {
      expect(mocks.cancelPresenzeSyncJob).toHaveBeenCalledWith("token", "sync-1");
      expect(screen.getByText(/annullato/)).toBeInTheDocument();
    });
  });

  test("renders sync history even when last_event arrives as structured object", async () => {
    mocks.listPresenzeSyncJobs.mockResolvedValue([
      {
        id: "sync-1",
        status: "running",
        requested_by_user_id: 1,
        credential_id: 4,
        import_job_id: null,
        period_start: "2026-05-01",
        period_end: "2026-05-31",
        collaborator_limit: null,
        records_imported: 10,
        records_skipped: 0,
        records_errors: 0,
        json_artifact_path: "/tmp/presenze/sync-1/presenze_collaboratori.json",
        worker_log_path: "/tmp/presenze/sync-1/worker.log",
        worker_pid: 563,
        attempt_count: 2,
        max_attempts: 3,
        error_detail: null,
        params_json: {
          progress: {
            state: "running",
            index: 12,
            total: 75,
            completed_collaborators: 11,
            failed_collaborators: 0,
            employee_code: "1672",
            name: "CAUGLIA GIANLUCA",
            last_event: {
              type: "collaborator_phase",
              employee_code: "1672",
              name: "CAUGLIA GIANLUCA",
              phase: "timesheet_opened",
            },
            last_event_at: "2026-06-04T14:29:59.670112+00:00",
          },
        },
        created_at: "2026-05-29T09:00:00Z",
        started_at: "2026-05-29T09:01:00Z",
        finished_at: null,
      },
    ]);

    render(<PresenzeSyncPage />);

    expect(await screen.findByText("Avanzamento 12/75")).toBeInTheDocument();
    expect(screen.getByText("Collaboratore corrente: 1672 · CAUGLIA GIANLUCA")).toBeInTheDocument();
    expect(screen.getByText(/Job attivo: running/)).toBeInTheDocument();
  });

  test("loads failed summary items and retries a single collaborator", async () => {
    mocks.listPresenzeSyncJobs.mockResolvedValue([
      {
        id: "sync-1",
        status: "completed",
        requested_by_user_id: 1,
        credential_id: 4,
        import_job_id: "import-1",
        period_start: "2026-06-01",
        period_end: "2026-06-30",
        collaborator_limit: null,
        records_imported: 1980,
        records_skipped: 0,
        records_errors: 0,
        json_artifact_path: "/tmp/presenze/sync-1/presenze_collaboratori.json",
        worker_log_path: "/tmp/presenze/sync-1/worker.log",
        worker_pid: 64489,
        attempt_count: 1,
        max_attempts: 3,
        error_detail: null,
        params_json: {
          progress: {
            state: "completed",
            completed_collaborators: 66,
            failed_collaborators: 5,
            total_collaborators: 71,
            last_event: "job_completed",
            last_event_at: "2026-07-03T07:01:15Z",
          },
        },
        created_at: "2026-07-03T05:48:52Z",
        started_at: "2026-07-03T05:48:54Z",
        finished_at: "2026-07-03T07:01:15Z",
      },
    ]);
    mocks.downloadPresenzeSyncArtifact.mockResolvedValueOnce(
      new Blob(
        [
          JSON.stringify({
            sync_job_id: "sync-1",
            import_job_id: "import-1",
            status: "completed",
            records_imported: 1980,
            records_skipped: 0,
            records_errors: 0,
            completed_collaborators: 66,
            failed_collaborators: 5,
            total_collaborators: 71,
            resumed_from_checkpoint: false,
            error_items: [
              {
                employee_code: "1396",
                name: "MELE ANDREA",
                error: "TimeoutError: ",
              },
            ],
          }),
        ],
        { type: "application/json" },
      ),
    );

    render(<PresenzeSyncPage />);

    fireEvent.click(await screen.findByText("Dettagli avanzamento"));
    fireEvent.click(await screen.findByText("Carica falliti"));
    expect(await screen.findByText("1396 · MELE ANDREA")).toBeInTheDocument();

    fireEvent.click(screen.getByText("Riprova questo caso"));

    await waitFor(() => {
      expect(mocks.retrySelectedPresenzeSyncJob).toHaveBeenCalledWith("token", "sync-1", {
        employee_codes: ["1396"],
      });
      expect(screen.getByText(/Retry avviato per 1396/)).toBeInTheDocument();
    });
  });

  test("creates a presenze credential from settings", async () => {
    render(<PresenzeSettingsPage />);

    fireEvent.change(screen.getByLabelText("Label"), { target: { value: "Admin Presenze" } });
    fireEvent.change(screen.getByLabelText("Username portale"), { target: { value: "admin.inaz" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "secret123" } });
    fireEvent.click(screen.getByText("Crea credenziale"));

    await waitFor(() => {
      expect(mocks.createPresenzeCredential).toHaveBeenCalledWith("token", {
        label: "Admin Presenze",
        username: "admin.inaz",
        password: "secret123",
        active: true,
      });
    });
  });
});
