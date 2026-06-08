import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import InazCollaboratoriPage from "@/app/inaz/collaboratori/page";
import InazCapisettorePage from "@/app/inaz/capisettore/page";
import InazImportPage from "@/app/inaz/import/page";
import InazPage from "@/app/inaz/page";
import InazSettingsPage from "@/app/inaz/settings/page";
import InazSyncPage from "@/app/inaz/sync/page";

const mocks = vi.hoisted(() => ({
  getStoredAccessToken: vi.fn(),
  getCurrentUser: vi.fn(),
  listAllApplicationUsers: vi.fn(),
  listAllInazCollaborators: vi.fn(),
  listInazApplicationUsers: vi.fn(),
  listInazCollaborators: vi.fn(),
  listInazDailyRecords: vi.fn(),
  listInazSupervisorAssignments: vi.fn(),
  mapInazCollaboratorApplicationUser: vi.fn(),
  listInazImportJobs: vi.fn(),
  previewInazImport: vi.fn(),
  importInazJson: vi.fn(),
  listInazSyncJobs: vi.fn(),
  createInazSyncJob: vi.fn(),
  retryInazSyncJob: vi.fn(),
  cancelInazSyncJob: vi.fn(),
  downloadInazSyncArtifact: vi.fn(),
  listInazCredentials: vi.fn(),
  createInazCredential: vi.fn(),
  updateInazCredential: vi.fn(),
  deleteInazCredential: vi.fn(),
  testInazCredential: vi.fn(),
  updateInazSupervisorAssignment: vi.fn(),
  push: vi.fn(),
}));

vi.mock("@/lib/auth", () => ({
  getStoredAccessToken: mocks.getStoredAccessToken,
}));

vi.mock("@/lib/api", () => ({
  getCurrentUser: mocks.getCurrentUser,
  listAllApplicationUsers: mocks.listAllApplicationUsers,
  listAllInazCollaborators: mocks.listAllInazCollaborators,
  listInazApplicationUsers: mocks.listInazApplicationUsers,
  listInazCollaborators: mocks.listInazCollaborators,
  listInazDailyRecords: mocks.listInazDailyRecords,
  listInazSupervisorAssignments: mocks.listInazSupervisorAssignments,
  mapInazCollaboratorApplicationUser: mocks.mapInazCollaboratorApplicationUser,
  listInazImportJobs: mocks.listInazImportJobs,
  previewInazImport: mocks.previewInazImport,
  importInazJson: mocks.importInazJson,
  listInazSyncJobs: mocks.listInazSyncJobs,
  createInazSyncJob: mocks.createInazSyncJob,
  retryInazSyncJob: mocks.retryInazSyncJob,
  cancelInazSyncJob: mocks.cancelInazSyncJob,
  downloadInazSyncArtifact: mocks.downloadInazSyncArtifact,
  listInazCredentials: mocks.listInazCredentials,
  createInazCredential: mocks.createInazCredential,
  updateInazCredential: mocks.updateInazCredential,
  deleteInazCredential: mocks.deleteInazCredential,
  testInazCredential: mocks.testInazCredential,
  updateInazSupervisorAssignment: mocks.updateInazSupervisorAssignment,
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

describe("Inaz pages", () => {
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
      module_inaz: true,
      enabled_modules: ["accessi", "inaz"],
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
        module_inaz: true,
        enabled_modules: ["accessi", "inaz"],
        created_at: "2026-05-29T00:00:00Z",
        updated_at: "2026-05-29T00:00:00Z",
      },
    ]);
    mocks.listAllInazCollaborators.mockResolvedValue([
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
        is_active: true,
        last_seen_at: "2026-05-29T09:00:00Z",
        created_at: "2026-05-29T09:00:00Z",
        updated_at: "2026-05-29T09:00:00Z",
      },
    ]);
    mocks.listInazCollaborators.mockResolvedValue({
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
    mocks.listInazApplicationUsers.mockResolvedValue([
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
        module_inaz: true,
        enabled_modules: ["accessi", "inaz"],
        created_at: "2026-05-29T00:00:00Z",
        updated_at: "2026-05-29T00:00:00Z",
      },
    ]);
    mocks.listInazSupervisorAssignments.mockResolvedValue([]);
    mocks.listInazDailyRecords.mockResolvedValue({
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
    mocks.mapInazCollaboratorApplicationUser.mockResolvedValue({
      id: "collab-1",
      application_user_id: 7,
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
      updated_at: "2026-05-29T09:00:00Z",
    });
    mocks.listInazImportJobs.mockResolvedValue([]);
    mocks.previewInazImport.mockResolvedValue({
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
    mocks.listInazSyncJobs.mockResolvedValue([]);
    mocks.listInazCredentials.mockResolvedValue([
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
    mocks.createInazSyncJob.mockResolvedValue({
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
      json_artifact_path: "/tmp/inaz/sync-1/inaz_collaboratori.json",
      worker_log_path: "/tmp/inaz/sync-1/worker.log",
      worker_pid: 4242,
      attempt_count: 0,
      max_attempts: 3,
      error_detail: null,
      params_json: { year: 2026, month: 5 },
      created_at: "2026-05-29T09:00:00Z",
      started_at: null,
      finished_at: null,
    });
    mocks.createInazCredential.mockResolvedValue({
      id: 5,
      application_user_id: 1,
      label: "Admin Inaz",
      username: "admin.inaz",
      active: true,
      last_used_at: null,
      last_authenticated_url: null,
      last_error: null,
      consecutive_failures: 0,
      created_at: "2026-05-29T09:00:00Z",
      updated_at: "2026-05-29T09:00:00Z",
    });
    mocks.updateInazSupervisorAssignment.mockResolvedValue({
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
    mocks.downloadInazSyncArtifact.mockResolvedValue(new Blob(['{"ok":true}'], { type: "application/json" }));
    mocks.cancelInazSyncJob.mockResolvedValue({
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
      json_artifact_path: "/tmp/inaz/sync-1/inaz_collaboratori.json",
      worker_log_path: "/tmp/inaz/sync-1/worker.log",
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
    render(<InazCollaboratoriPage />);

    await screen.findAllByText("AMADU SALVATORE");
    const selects = screen.getAllByRole("combobox");
    fireEvent.change(selects[selects.length - 1], { target: { value: "7" } });
    fireEvent.click(screen.getByText("Salva"));

    await waitFor(() => {
      expect(mocks.mapInazCollaboratorApplicationUser).toHaveBeenCalledWith("token", "collab-1", 7);
    });
  });

  test("redirects capisettore page to organigramma", async () => {
    render(<InazCapisettorePage />);

    await waitFor(() => {
      expect(mocks.push).toHaveBeenCalledWith("/inaz/organigramma");
    });
  });

  test("renders the inaz dashboard with monthly presence metrics", async () => {
    mocks.listInazCollaborators.mockResolvedValue({
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
    mocks.listInazDailyRecords.mockResolvedValue({
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
    mocks.listInazSyncJobs.mockResolvedValue([
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
        json_artifact_path: "/tmp/inaz/sync-1/inaz_collaboratori.json",
        worker_log_path: "/tmp/inaz/sync-1/worker.log",
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

    render(<InazPage />);

    expect(await screen.findByText("Supervisiona collaboratori, cartellini ed export giornaliere da un unico workspace.")).toBeInTheDocument();
    expect(screen.getAllByText("5.5 h").length).toBeGreaterThan(0);
    expect(screen.getAllByText("2.0 h").length).toBeGreaterThan(0);
    expect(screen.getByText("24")).toBeInTheDocument();
    expect(screen.getByText("Permessi")).toBeInTheDocument();
    expect(screen.getByText("OPESAB")).toBeInTheDocument();
  });

  test("redirects import page to sync", async () => {
    render(<InazImportPage />);

    await waitFor(() => {
      expect(mocks.push).toHaveBeenCalledWith("/inaz/sync");
    });
  });

  test("creates a live sync job", async () => {
    render(<InazSyncPage />);

    await waitFor(() => {
      expect(screen.getByLabelText("Credenziale Inaz")).toHaveValue("4");
    });
    fireEvent.change(screen.getByLabelText("Anno"), { target: { value: "2026" } });
    fireEvent.change(screen.getByLabelText("Mese"), { target: { value: "05" } });
    fireEvent.change(screen.getByLabelText("Credenziale Inaz"), { target: { value: "4" } });
    fireEvent.change(screen.getByPlaceholderText("Vuoto = tutti"), { target: { value: "2" } });
    fireEvent.click(screen.getByText("Avvia sync live"));

    await waitFor(() => {
      expect(mocks.createInazSyncJob).toHaveBeenCalledWith("token", {
        year: 2026,
        month: 5,
        credential_id: 4,
        collaborator_limit: 2,
      });
      expect(screen.getByText(/Job live sync creato/)).toBeInTheDocument();
    });
  });

  test("downloads a sync artifact", async () => {
    mocks.listInazSyncJobs.mockResolvedValue([
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
        json_artifact_path: "/tmp/inaz/sync-1/inaz_collaboratori.json",
        worker_log_path: "/tmp/inaz/sync-1/worker.log",
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

    render(<InazSyncPage />);
    fireEvent.click(await screen.findByText("Scarica JSON"));

    await waitFor(() => {
      expect(mocks.downloadInazSyncArtifact).toHaveBeenCalledWith("token", "sync-1", "json");
    });

    createObjectUrlSpy.mockRestore();
    revokeObjectUrlSpy.mockRestore();
    clickSpy.mockRestore();
  });

  test("cancels an active sync job", async () => {
    mocks.listInazSyncJobs.mockResolvedValue([
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
        json_artifact_path: "/tmp/inaz/sync-1/inaz_collaboratori.json",
        worker_log_path: "/tmp/inaz/sync-1/worker.log",
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

    render(<InazSyncPage />);
    fireEvent.click(await screen.findByText("Annulla job"));

    await waitFor(() => {
      expect(mocks.cancelInazSyncJob).toHaveBeenCalledWith("token", "sync-1");
      expect(screen.getByText(/annullato/)).toBeInTheDocument();
    });
  });

  test("renders sync history even when last_event arrives as structured object", async () => {
    mocks.listInazSyncJobs.mockResolvedValue([
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
        json_artifact_path: "/tmp/inaz/sync-1/inaz_collaboratori.json",
        worker_log_path: "/tmp/inaz/sync-1/worker.log",
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

    render(<InazSyncPage />);

    expect(await screen.findByText("Avanzamento 12/75")).toBeInTheDocument();
    expect(screen.getByText("Collaboratore corrente: 1672 · CAUGLIA GIANLUCA")).toBeInTheDocument();
    expect(screen.getByText(/Job attivo: running/)).toBeInTheDocument();
  });

  test("creates an inaz credential from settings", async () => {
    render(<InazSettingsPage />);

    fireEvent.change(screen.getByLabelText("Label"), { target: { value: "Admin Inaz" } });
    fireEvent.change(screen.getByLabelText("Username Inaz"), { target: { value: "admin.inaz" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "secret123" } });
    fireEvent.click(screen.getByText("Crea credenziale"));

    await waitFor(() => {
      expect(mocks.createInazCredential).toHaveBeenCalledWith("token", {
        label: "Admin Inaz",
        username: "admin.inaz",
        password: "secret123",
        active: true,
      });
    });
  });
});
