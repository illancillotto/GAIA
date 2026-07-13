import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import PresenzeCapisettorePage from "@/app/presenze/capisettore/page";
import PresenzeCollaboratoriPage from "@/app/presenze/collaboratori/page";
import PresenzeImportPage from "@/app/presenze/import/page";
import PresenzePage from "@/app/presenze/page";
import PresenzeRegolePage from "@/app/presenze/regole/page";
import PresenzeSettingsPage from "@/app/presenze/settings/page";
import PresenzeSquadrePage from "@/app/presenze/squadre/page";
import PresenzeSyncPage from "@/app/presenze/sync/page";
import { PRESENZE_COLLABORATOR_DETAIL_UPDATED_MESSAGE } from "@/lib/presenze-collaborator-mapping";

const mocks = vi.hoisted(() => ({
  getStoredAccessToken: vi.fn(),
  getPresenzeDashboardSummary: vi.fn(),
  getCurrentUser: vi.fn(),
  listAllApplicationUsers: vi.fn(),
  listAllPresenzeCollaborators: vi.fn(),
  listPresenzeApplicationUsers: vi.fn(),
  listPresenzeCollaborators: vi.fn(),
  listPresenzeDailyRecords: vi.fn(),
  listPresenzeDailyMatrixRecords: vi.fn(),
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
  getGatePresenzeRules: vi.fn(),
  listGatePresenzeTeams: vi.fn(),
  createGatePresenzeTeam: vi.fn(),
  updateGatePresenzeTeam: vi.fn(),
  createGatePresenzeTeamMembership: vi.fn(),
  createGatePresenzeTeamSupervisor: vi.fn(),
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
  listPresenzeDailyMatrixRecords: mocks.listPresenzeDailyMatrixRecords,
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
  getGatePresenzeRules: mocks.getGatePresenzeRules,
  listGatePresenzeTeams: mocks.listGatePresenzeTeams,
  createGatePresenzeTeam: mocks.createGatePresenzeTeam,
  updateGatePresenzeTeam: mocks.updateGatePresenzeTeam,
  createGatePresenzeTeamMembership: mocks.createGatePresenzeTeamMembership,
  createGatePresenzeTeamSupervisor: mocks.createGatePresenzeTeamSupervisor,
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
    vi.resetAllMocks();
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
    mocks.listPresenzeDailyMatrixRecords.mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 5000,
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
      items: [],
      total: 0,
      page: 1,
      page_size: 200,
    });
    mocks.listPresenzeDailyMatrixRecords.mockResolvedValue({
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
    mocks.getGatePresenzeRules.mockResolvedValue({
      rules_version: "presenze-2026-07-extra-3h",
      export_rules_version: "presenze-xlsm-2026-07",
      updated_at: "2026-07-08T00:00:00Z",
      summary: "GAIA calcola giornaliere e anomalie come source of truth.",
      sections: [
        {
          code: "anomalie",
          title: "Anomalie operative",
          description: "Regole che determinano se una giornata entra nella coda.",
          rules: [
            {
              code: "extra_over_3h",
              title: "Straordinario oltre 3 ore",
              description: "Oltre 180 minuti entra nella coda Da verificare.",
              severity: "warning",
              applies_to: ["giornaliere", "anomalie"],
              operator_action: "Verificare autorizzazione e validare.",
            },
          ],
        },
      ],
    });
    mocks.listGatePresenzeTeams.mockResolvedValue([
      {
        id: "team-1",
        name: "Squadra Nord",
        code: "NORD",
        scope: "presenze",
        active: true,
        created_from_channel: "gate_mobile",
        created_by_user_id: 1,
        created_at: "2026-07-08T00:00:00Z",
        updated_at: "2026-07-08T00:00:00Z",
        memberships: [
          {
            id: "membership-1",
            team_id: "team-1",
            collaborator_id: "collab-1",
            valid_from: null,
            valid_to: null,
            role: "member",
            source_channel: "gate_mobile",
            created_by_user_id: 1,
            created_at: "2026-07-08T00:00:00Z",
            updated_at: "2026-07-08T00:00:00Z",
            collaborator_name: "AMADU SALVATORE",
            employee_code: "1854",
          },
        ],
        supervisors: [
          {
            id: "supervisor-1",
            team_id: "team-1",
            application_user_id: 7,
            permission_scope: "validate",
            valid_from: null,
            valid_to: null,
            source_channel: "gate_mobile",
            assigned_by_user_id: 1,
            created_at: "2026-07-08T00:00:00Z",
            updated_at: "2026-07-08T00:00:00Z",
            user_label: "Mario Rossi",
            username: "mrossi",
          },
        ],
      },
    ]);
    mocks.createGatePresenzeTeam.mockResolvedValue({
      id: "team-2",
      name: "Squadra Sud",
      code: "SUD",
      scope: "presenze",
      active: true,
      created_from_channel: "gate_mobile",
      created_by_user_id: 1,
      created_at: "2026-07-08T00:00:00Z",
      updated_at: "2026-07-08T00:00:00Z",
      memberships: [],
      supervisors: [],
    });
    mocks.updateGatePresenzeTeam.mockResolvedValue({
      id: "team-1",
      name: "Squadra Nord",
      code: "NORD",
      scope: "presenze",
      active: false,
      created_from_channel: "gate_mobile",
      created_by_user_id: 1,
      created_at: "2026-07-08T00:00:00Z",
      updated_at: "2026-07-08T00:00:00Z",
      memberships: [],
      supervisors: [],
    });
    mocks.createGatePresenzeTeamMembership.mockResolvedValue({
      id: "membership-2",
      team_id: "team-1",
      collaborator_id: "collab-2",
      valid_from: null,
      valid_to: null,
      role: "member",
      source_channel: "gate_mobile",
      created_by_user_id: 1,
      created_at: "2026-07-08T00:00:00Z",
      updated_at: "2026-07-08T00:00:00Z",
      collaborator_name: "ARDU ANTONELLO",
      employee_code: "2101",
    });
    mocks.createGatePresenzeTeamSupervisor.mockResolvedValue({
      id: "supervisor-2",
      team_id: "team-1",
      application_user_id: 7,
      permission_scope: "validate",
      valid_from: null,
      valid_to: null,
      source_channel: "gate_mobile",
      assigned_by_user_id: 1,
      created_at: "2026-07-08T00:00:00Z",
      updated_at: "2026-07-08T00:00:00Z",
      user_label: "Mario Rossi",
      username: "mrossi",
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

  test("renders shared GAIA and GATE presenze rules", async () => {
    render(<PresenzeRegolePage />);

    expect(screen.getByText("Regole Presenze")).toBeInTheDocument();
    await screen.findByText("Straordinario oltre 3 ore");
    expect(screen.getByText("GAIA calcola giornaliere e anomalie come source of truth.")).toBeInTheDocument();
    expect(screen.getByText("Rules: presenze-2026-07-extra-3h")).toBeInTheDocument();
    expect(screen.getByText("Da verificare")).toBeInTheDocument();
    expect(mocks.getGatePresenzeRules).toHaveBeenCalledWith("token");
  });

  test("manages Gate Presenze teams from GAIA", async () => {
    mocks.listAllPresenzeCollaborators.mockResolvedValueOnce([
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
        application_user_id: 7,
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
    render(<PresenzeSquadrePage />);

    await screen.findAllByText("Squadra Nord");
    expect(screen.getAllByText("AMADU SALVATORE").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Mario Rossi").length).toBeGreaterThan(0);

    fireEvent.change(screen.getByLabelText("Nome squadra"), { target: { value: "Squadra Sud" } });
    fireEvent.change(screen.getByLabelText("Codice"), { target: { value: "SUD" } });
    fireEvent.click(screen.getByText("Crea squadra"));

    await waitFor(() => {
      expect(mocks.createGatePresenzeTeam).toHaveBeenCalledWith("token", {
        name: "Squadra Sud",
        code: "SUD",
        scope: "presenze",
        active: true,
      });
    });
    expect(await screen.findByText("Squadra creata.")).toBeInTheDocument();

    fireEvent.click(screen.getByText("Squadra Nord"));
    fireEvent.change(screen.getByPlaceholderText("Cerca collaboratore o matricola"), { target: { value: "2101" } });
    fireEvent.click(screen.getByRole("button", { name: /ARDU ANTONELLO.*Aggiungi/i }));

    await waitFor(() => {
      expect(mocks.createGatePresenzeTeamMembership).toHaveBeenCalledWith("token", "team-1", {
        collaborator_id: "collab-2",
        role: "member",
      });
    });

    fireEvent.change(screen.getByPlaceholderText("Cerca responsabile, matricola o utente"), { target: { value: "mario" } });
    fireEvent.click(screen.getByRole("button", { name: /ARDU ANTONELLO.*Assegna/i }));

    await waitFor(() => {
      expect(mocks.createGatePresenzeTeamSupervisor).toHaveBeenCalledWith("token", "team-1", {
        application_user_id: 7,
        permission_scope: "validate",
      });
    });

    fireEvent.click(screen.getByText("Disattiva"));
    await waitFor(() => {
      expect(mocks.updateGatePresenzeTeam).toHaveBeenCalledWith("token", "team-1", { active: false });
    });
  });

  test("shows Gate Presenze team validation errors and empty state", async () => {
    mocks.listGatePresenzeTeams.mockResolvedValueOnce([]);

    render(<PresenzeSquadrePage />);

    expect(await screen.findByText("Crea una squadra per iniziare ad assegnare collaboratori e responsabili.")).toBeInTheDocument();
    fireEvent.click(screen.getByText("Crea squadra"));
    expect(screen.getByText("Inserisci un nome squadra.")).toBeInTheDocument();
  });

  test("renders Gate Presenze team fallback labels and reactivates inactive teams", async () => {
    mocks.listGatePresenzeTeams.mockResolvedValueOnce([
      {
        id: "team-fallback",
        name: "Squadra fallback",
        code: null,
        scope: "presenze",
        active: false,
        created_from_channel: "gate_mobile",
        created_by_user_id: 1,
        created_at: "2026-07-08T00:00:00Z",
        updated_at: "2026-07-08T00:00:00Z",
        memberships: [
          {
            id: "membership-fallback",
            team_id: "team-fallback",
            collaborator_id: "collab-x",
            valid_from: null,
            valid_to: null,
            role: "substitute",
            source_channel: "gate_mobile",
            created_by_user_id: 1,
            created_at: "2026-07-08T00:00:00Z",
            updated_at: "2026-07-08T00:00:00Z",
            collaborator_name: null,
            employee_code: null,
          },
        ],
        supervisors: [
          {
            id: "supervisor-fallback",
            team_id: "team-fallback",
            application_user_id: 99,
            permission_scope: "view",
            valid_from: null,
            valid_to: null,
            source_channel: "gate_mobile",
            assigned_by_user_id: 1,
            created_at: "2026-07-08T00:00:00Z",
            updated_at: "2026-07-08T00:00:00Z",
            user_label: null,
            username: null,
          },
        ],
      },
    ]);
    mocks.updateGatePresenzeTeam.mockResolvedValueOnce({
      id: "team-fallback",
      name: "Squadra fallback",
      code: null,
      scope: "presenze",
      active: true,
      created_from_channel: "gate_mobile",
      created_by_user_id: 1,
      created_at: "2026-07-08T00:00:00Z",
      updated_at: "2026-07-08T00:00:00Z",
      memberships: [],
      supervisors: [],
    });

    render(<PresenzeSquadrePage />);

    await screen.findByText("Senza codice · Disattiva");
    fireEvent.change(screen.getByLabelText("Cerca squadra"), { target: { value: "non-presente" } });
    expect(screen.getByText("Nessuna squadra trovata.")).toBeInTheDocument();
    fireEvent.click(screen.getByText("X"));
    expect(screen.getByText("Codice n/d · Scope presenze")).toBeInTheDocument();
    expect(screen.getByText("collab-x")).toBeInTheDocument();
    expect(screen.getByText("Matricola n/d · ruolo substitute")).toBeInTheDocument();
    expect(screen.getByText("99")).toBeInTheDocument();

    fireEvent.click(screen.getByText("Riattiva"));
    await waitFor(() => {
      expect(mocks.updateGatePresenzeTeam).toHaveBeenCalledWith("token", "team-fallback", { active: true });
    });
    expect(await screen.findByText("Squadra riattivata.")).toBeInTheDocument();
  });

  test("handles Gate Presenze team loading errors and missing tokens", async () => {
    mocks.listGatePresenzeTeams.mockRejectedValueOnce(new Error("Squadre non disponibili"));

    render(<PresenzeSquadrePage />);

    expect(await screen.findByText("Squadre non disponibili")).toBeInTheDocument();

    mocks.getStoredAccessToken.mockReturnValue(null);
    render(<PresenzeSquadrePage />);

    expect(screen.getAllByText("Crea squadra").length).toBeGreaterThan(0);
  });

  test("covers Gate Presenze defensive team actions", async () => {
    mocks.listPresenzeApplicationUsers.mockResolvedValueOnce([
      {
        id: 8,
        username: "solo_username",
        email: "solo@example.local",
        full_name: null,
        role: "reviewer",
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
        module_organigramma: false,
        gate_mobile_console: false,
        enabled_modules: ["presenze"],
        created_at: "2026-07-08T00:00:00Z",
        updated_at: "2026-07-08T00:00:00Z",
      },
    ]);
    mocks.listAllPresenzeCollaborators.mockResolvedValueOnce([
      {
        id: "collab-user",
        application_user_id: 8,
        kint: "20101",
        kkint: "{demo-user}",
        employee_code: "3101",
        company_code: "53",
        company_label: "53 - CBO",
        name: "UTENTE SENZA NOME",
        birth_date: null,
        contract_kind: "impiegato",
        operai_group: null,
        standard_daily_minutes: 420,
        is_active: true,
        last_seen_at: "2026-07-08T09:00:00Z",
        created_at: "2026-07-08T09:00:00Z",
        updated_at: "2026-07-08T09:00:00Z",
      },
      {
        id: "collab-missing-user",
        application_user_id: 99,
        kint: "20102",
        kkint: "{demo-missing-user}",
        employee_code: "3102",
        company_code: "53",
        company_label: "53 - CBO",
        name: "UTENTE NON SINCRONIZZATO",
        birth_date: null,
        contract_kind: "impiegato",
        operai_group: null,
        standard_daily_minutes: 420,
        is_active: true,
        last_seen_at: "2026-07-08T09:00:00Z",
        created_at: "2026-07-08T09:00:00Z",
        updated_at: "2026-07-08T09:00:00Z",
      },
    ]);
    mocks.createGatePresenzeTeam.mockResolvedValueOnce({
      id: "team-no-code",
      name: "Squadra senza codice",
      code: null,
      scope: "presenze",
      active: true,
      created_from_channel: "gate_mobile",
      created_by_user_id: 1,
      created_at: "2026-07-08T00:00:00Z",
      updated_at: "2026-07-08T00:00:00Z",
      memberships: [],
      supervisors: [],
    });

    render(<PresenzeSquadrePage />);
    await screen.findAllByText("Squadra Nord");

    expect(screen.getByText(/solo_username/)).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Nome squadra"), { target: { value: "Squadra senza codice" } });
    fireEvent.click(screen.getByText("Crea squadra"));
    await waitFor(() => {
      expect(mocks.createGatePresenzeTeam).toHaveBeenCalledWith("token", {
        name: "Squadra senza codice",
        code: null,
        scope: "presenze",
        active: true,
      });
    });

    mocks.getStoredAccessToken.mockReturnValue(null);
    fireEvent.click(screen.getByText("Crea squadra"));
    fireEvent.click(screen.getByText("Disattiva"));
    fireEvent.click(screen.getByRole("button", { name: /UTENTE SENZA NOME.*Aggiungi/i }));
    fireEvent.click(screen.getByRole("button", { name: /UTENTE SENZA NOME.*Assegna/i }));

    expect(mocks.updateGatePresenzeTeam).not.toHaveBeenCalledWith("token", "team-1", { active: false });
  });

  test("filters Gate Presenze teams, collaborators and supervisor personnel quickly", async () => {
    mocks.listAllPresenzeCollaborators.mockResolvedValueOnce([
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
        application_user_id: 7,
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
    render(<PresenzeSquadrePage />);

    await screen.findAllByText("Squadra Nord");

    fireEvent.change(screen.getByLabelText("Cerca squadra"), { target: { value: "zz" } });
    expect(screen.getByText("Nessuna squadra trovata.")).toBeInTheDocument();
    fireEvent.click(screen.getByText("X"));
    expect(screen.getAllByText("Squadra Nord").length).toBeGreaterThan(0);

    fireEvent.change(screen.getByPlaceholderText("Cerca collaboratore o matricola"), { target: { value: "2101" } });
    expect(screen.getByRole("button", { name: /ARDU ANTONELLO.*Aggiungi/i })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /AMADU SALVATORE.*Aggiungi/i })).not.toBeInTheDocument();

    fireEvent.change(screen.getByPlaceholderText("Cerca responsabile, matricola o utente"), { target: { value: "mario" } });
    expect(screen.getAllByText(/ARDU ANTONELLO/).length).toBeGreaterThan(0);
  });

  test("shows Gate Presenze search empty states and limits long result lists", async () => {
    mocks.listAllPresenzeCollaborators.mockResolvedValueOnce(
      Array.from({ length: 7 }, (_, index) => ({
        id: `collab-many-${index}`,
        application_user_id: index === 0 ? 7 : null,
        kint: `many-${index}`,
        kkint: `{many-${index}}`,
        employee_code: `30${index}`,
        company_code: "53",
        company_label: "53 - CBO",
        name: `COLLABORATORE ${index}`,
        birth_date: null,
        contract_kind: index === 6 ? null : "operaio",
        operai_group: null,
        standard_daily_minutes: 420,
        is_active: true,
        last_seen_at: "2026-05-29T09:00:00Z",
        created_at: "2026-05-29T09:00:00Z",
        updated_at: "2026-05-29T09:00:00Z",
      })),
    );

    render(<PresenzeSquadrePage />);
    await screen.findAllByText("Squadra Nord");

    expect(screen.getAllByText("Mostrati i primi 6. Raffina la ricerca per altri risultati.")).toHaveLength(2);
    expect(screen.getByRole("button", { name: /COLLABORATORE 0.*Assegna/i })).toBeInTheDocument();

    fireEvent.change(screen.getByPlaceholderText("Cerca collaboratore o matricola"), { target: { value: "nessuno" } });
    expect(screen.getByText("Nessun collaboratore trovato.")).toBeInTheDocument();

    fireEvent.change(screen.getByPlaceholderText("Cerca collaboratore o matricola"), { target: { value: "COLLABORATORE 6" } });
    expect(screen.getByText("Matricola 306 · contratto n/d")).toBeInTheDocument();

    fireEvent.change(screen.getByPlaceholderText("Cerca responsabile, matricola o utente"), { target: { value: "nessuno" } });
    expect(screen.getByText("Nessun responsabile trovato.")).toBeInTheDocument();
  });

  test("explains when selected Gate Presenze supervisor personnel has no GAIA or GATE user profile", async () => {
    render(<PresenzeSquadrePage />);

    await screen.findAllByText("Squadra Nord");
    fireEvent.change(screen.getByPlaceholderText("Cerca responsabile, matricola o utente"), { target: { value: "1854" } });
    fireEvent.click(screen.getByRole("button", { name: /AMADU SALVATORE.*Da collegare/i }));

    expect(await screen.findByText("Il collaboratore selezionato non e collegato a un utente GAIA/GATE. Collega prima il profilo utente.")).toBeInTheDocument();
    expect(mocks.createGatePresenzeTeamSupervisor).not.toHaveBeenCalledWith("token", "team-1", {
      application_user_id: expect.any(Number),
      permission_scope: "validate",
    });
  });

  test("shows Gate Presenze supervisor assignment API errors without crashing", async () => {
    mocks.listAllPresenzeCollaborators.mockResolvedValueOnce([
      {
        id: "collab-stale-user",
        application_user_id: 999,
        kint: "stale",
        kkint: "{stale}",
        employee_code: "9999",
        company_code: "53",
        company_label: "53 - CBO",
        name: "RESPONSABILE NON VALIDO",
        birth_date: null,
        contract_kind: "impiegato",
        operai_group: null,
        standard_daily_minutes: 420,
        is_active: true,
        last_seen_at: "2026-07-09T09:00:00Z",
        created_at: "2026-07-09T09:00:00Z",
        updated_at: "2026-07-09T09:00:00Z",
      },
    ]);
    mocks.createGatePresenzeTeamSupervisor.mockRejectedValueOnce(new Error("Application user not found"));

    render(<PresenzeSquadrePage />);

    await screen.findAllByText("Squadra Nord");
    fireEvent.click(screen.getByRole("button", { name: /RESPONSABILE NON VALIDO.*Assegna/i }));

    expect(await screen.findByText("Application user not found")).toBeInTheDocument();
  });

  test("shows Gate Presenze membership and team update API errors without crashing", async () => {
    mocks.createGatePresenzeTeamMembership.mockRejectedValueOnce(new Error("Membership failed"));
    mocks.updateGatePresenzeTeam.mockRejectedValueOnce(new Error("Update failed"));

    render(<PresenzeSquadrePage />);

    await screen.findAllByText("Squadra Nord");
    fireEvent.click(screen.getByRole("button", { name: /AMADU SALVATORE.*Aggiungi/i }));
    expect(await screen.findByText("Membership failed")).toBeInTheDocument();

    fireEvent.click(screen.getByText("Disattiva"));
    expect(await screen.findByText("Update failed")).toBeInTheDocument();
  });

  test("shows Gate Presenze generic action API errors without crashing", async () => {
    mocks.listAllPresenzeCollaborators.mockResolvedValueOnce([
      {
        id: "collab-generic-user",
        application_user_id: 7,
        kint: "generic",
        kkint: "{generic}",
        employee_code: "7007",
        company_code: "53",
        company_label: "53 - CBO",
        name: "RESPONSABILE GENERICO",
        birth_date: null,
        contract_kind: "impiegato",
        operai_group: null,
        standard_daily_minutes: 420,
        is_active: true,
        last_seen_at: "2026-07-09T09:00:00Z",
        created_at: "2026-07-09T09:00:00Z",
        updated_at: "2026-07-09T09:00:00Z",
      },
    ]);
    mocks.createGatePresenzeTeamMembership.mockRejectedValueOnce("boom");
    mocks.createGatePresenzeTeamSupervisor.mockRejectedValueOnce("boom");
    mocks.updateGatePresenzeTeam.mockRejectedValueOnce("boom");

    render(<PresenzeSquadrePage />);

    await screen.findAllByText("Squadra Nord");
    fireEvent.click(screen.getByRole("button", { name: /RESPONSABILE GENERICO.*Aggiungi/i }));
    expect(await screen.findByText("Errore aggiunta collaboratore.")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /RESPONSABILE GENERICO.*Assegna/i }));
    expect(await screen.findByText("Errore assegnazione responsabile.")).toBeInTheDocument();

    fireEvent.click(screen.getByText("Disattiva"));
    expect(await screen.findByText("Errore aggiornamento squadra.")).toBeInTheDocument();
  });

  test("renders Gate Presenze generic loading error", async () => {
    mocks.listGatePresenzeTeams.mockRejectedValueOnce("boom");

    render(<PresenzeSquadrePage />);

    expect(await screen.findByText("Errore caricamento squadre Presenze")).toBeInTheDocument();
  });

  test("updates one Gate Presenze team while preserving the others", async () => {
    mocks.listGatePresenzeTeams.mockResolvedValueOnce([
      {
        id: "team-a",
        name: "Squadra A",
        code: "A",
        scope: "presenze",
        active: true,
        created_from_channel: "gate_mobile",
        created_by_user_id: 1,
        created_at: "2026-07-08T00:00:00Z",
        updated_at: "2026-07-08T00:00:00Z",
        memberships: [],
        supervisors: [],
      },
      {
        id: "team-b",
        name: "Squadra B",
        code: "B",
        scope: "presenze",
        active: true,
        created_from_channel: "gate_mobile",
        created_by_user_id: 1,
        created_at: "2026-07-08T00:00:00Z",
        updated_at: "2026-07-08T00:00:00Z",
        memberships: [],
        supervisors: [],
      },
    ]);
    mocks.updateGatePresenzeTeam.mockResolvedValueOnce({
      id: "team-a",
      name: "Squadra A",
      code: "A",
      scope: "presenze",
      active: false,
      created_from_channel: "gate_mobile",
      created_by_user_id: 1,
      created_at: "2026-07-08T00:00:00Z",
      updated_at: "2026-07-08T00:00:00Z",
      memberships: [],
      supervisors: [],
    });

    render(<PresenzeSquadrePage />);

    await screen.findByText("Squadra B");
    fireEvent.click(screen.getByText("Disattiva"));

    expect(await screen.findByText("Squadra disattivata.")).toBeInTheDocument();
    expect(screen.getByText("Squadra B")).toBeInTheDocument();
  });

  test("shows Gate Presenze team creation API errors without crashing", async () => {
    mocks.createGatePresenzeTeam.mockRejectedValueOnce(new Error("Internal Server Error"));

    render(<PresenzeSquadrePage />);

    await screen.findAllByText("Squadra Nord");
    fireEvent.change(screen.getByLabelText("Nome squadra"), { target: { value: "Marrubiu" } });
    fireEvent.change(screen.getByLabelText("Codice"), { target: { value: "MARR" } });
    fireEvent.click(screen.getByText("Crea squadra"));

    expect(await screen.findByText("Internal Server Error")).toBeInTheDocument();
  });

  test("shows Gate Presenze generic team creation API errors without crashing", async () => {
    mocks.createGatePresenzeTeam.mockRejectedValueOnce("boom");

    render(<PresenzeSquadrePage />);

    await screen.findAllByText("Squadra Nord");
    fireEvent.change(screen.getByLabelText("Nome squadra"), { target: { value: "Marrubiu" } });
    fireEvent.click(screen.getByText("Crea squadra"));

    expect(await screen.findByText("Errore creazione squadra.")).toBeInTheDocument();
  });

  test("renders presenze rules loading state without token", () => {
    mocks.getStoredAccessToken.mockReturnValue(null);

    render(<PresenzeRegolePage />);

    expect(screen.getByText("Caricamento regole operative condivise tra GAIA e GATE.")).toBeInTheDocument();
    expect(screen.getByText("Rules: ...")).toBeInTheDocument();
    expect(mocks.getGatePresenzeRules).not.toHaveBeenCalled();
  });

  test("renders presenze rules loading error", async () => {
    mocks.getGatePresenzeRules.mockRejectedValueOnce(new Error("Regole non disponibili"));

    render(<PresenzeRegolePage />);

    expect(await screen.findByText("Regole non disponibili")).toBeInTheDocument();
  });

  test("renders presenze rules generic loading error", async () => {
    mocks.getGatePresenzeRules.mockRejectedValueOnce("boom");

    render(<PresenzeRegolePage />);

    expect(await screen.findByText("Errore caricamento regole Presenze")).toBeInTheDocument();
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

  test("filters collaborators by mapping and search text", async () => {
    mocks.listAllPresenzeCollaborators.mockResolvedValueOnce([
      {
        id: "collab-mapped",
        application_user_id: 7,
        kint: null,
        kkint: null,
        employee_code: "9999",
        company_code: null,
        company_label: null,
        name: "MARIO ROSSI",
        birth_date: null,
        contract_kind: "impiegato",
        operai_group: null,
        standard_daily_minutes: 385,
        is_active: false,
        last_seen_at: null,
        created_at: "2026-05-29T09:00:00Z",
        updated_at: "2026-05-29T09:00:00Z",
      },
      {
        id: "collab-unmapped",
        application_user_id: null,
        kint: null,
        kkint: "K-77",
        employee_code: "7777",
        company_code: null,
        company_label: null,
        name: "LUCA BIANCHI",
        birth_date: null,
        contract_kind: "quadro",
        operai_group: null,
        standard_daily_minutes: null,
        is_active: true,
        last_seen_at: null,
        created_at: "2026-05-29T09:00:00Z",
        updated_at: "2026-05-29T09:00:00Z",
      },
    ]);

    render(<PresenzeCollaboratoriPage />);

    expect((await screen.findAllByText("MARIO ROSSI")).length).toBeGreaterThan(0);
    expect(screen.getByText("Impiegato")).toBeInTheDocument();
    expect(screen.getByText("Inattivo")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Stato mapping"), { target: { value: "unmapped" } });

    await waitFor(() => {
      expect(screen.queryByText("MARIO ROSSI")).not.toBeInTheDocument();
    });
    expect(screen.getAllByText("LUCA BIANCHI").length).toBeGreaterThan(0);

    fireEvent.change(screen.getByLabelText("Cerca"), { target: { value: "quadro" } });
    expect(screen.getByText("Quadro")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Stato mapping"), { target: { value: "mapped" } });
    await waitFor(() => {
      expect(screen.queryByText("LUCA BIANCHI")).not.toBeInTheDocument();
    });
  });

  test("renders collaborator variants, suggestion confidence levels and readonly viewer state", async () => {
    mocks.getCurrentUser.mockResolvedValue({
      id: 2,
      username: "viewer",
      email: "viewer@example.local",
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
    mocks.listAllApplicationUsers.mockResolvedValueOnce([]);
    mocks.listAllPresenzeCollaborators.mockResolvedValueOnce([
      {
        id: "high",
        application_user_id: null,
        kint: null,
        kkint: null,
        employee_code: "1001",
        company_code: null,
        company_label: null,
        name: "MARIO ROSSI",
        birth_date: null,
        contract_kind: "impiegato",
        operai_group: null,
        standard_daily_minutes: 385,
        is_active: true,
        last_seen_at: null,
        created_at: "2026-05-29T09:00:00Z",
        updated_at: "2026-05-29T09:00:00Z",
      },
      {
        id: "mapped-fallback",
        application_user_id: 99,
        kint: null,
        kkint: null,
        employee_code: "1002",
        company_code: null,
        company_label: null,
        name: "UTENTE ESTERNO",
        birth_date: null,
        contract_kind: "altro",
        operai_group: null,
        standard_daily_minutes: null,
        is_active: false,
        last_seen_at: null,
        created_at: "2026-05-29T09:00:00Z",
        updated_at: "2026-05-29T09:00:00Z",
      },
    ]);
    mocks.listPresenzeDailyRecords.mockResolvedValueOnce({
      items: [
        {
          id: "variant-record",
          collaborator_id: "high",
          owner_user_id: 1,
          application_user_id: null,
          work_date: "2026-05-01",
          schedule_code: null,
          teo_minutes: null,
          ordinary_minutes: null,
          absence_minutes: null,
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
          stato: null,
          evidenze: null,
          raw_weekday: null,
          detail_title: null,
          detail_status: null,
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

    render(<PresenzeCollaboratoriPage />);

    expect(await screen.findByText("MARIO ROSSI")).toBeInTheDocument();
    expect(screen.getByText("Impiegato")).toBeInTheDocument();
    expect(screen.getByText("Altro")).toBeInTheDocument();
    expect(screen.getByText("#99")).toBeInTheDocument();
    expect(screen.getByText("Inattivo")).toBeInTheDocument();
    expect(screen.queryByText("Aggiorna mapping GAIA")).not.toBeInTheDocument();

    fireEvent.click(screen.getByText("MARIO ROSSI"));
    window.dispatchEvent(
      new MessageEvent("message", {
        origin: window.location.origin,
        data: { type: PRESENZE_COLLABORATOR_DETAIL_UPDATED_MESSAGE },
      }),
    );
    await waitFor(() => {
      expect(mocks.listAllPresenzeCollaborators.mock.calls.length).toBeGreaterThanOrEqual(2);
    });
  });

  test("renders high, medium and low collaborator suggestions for admins", async () => {
    mocks.listAllApplicationUsers.mockResolvedValueOnce([
      {
        id: 7,
        username: "mario.rossi",
        email: "mario.rossi@example.local",
        full_name: "MARIO ROSSI",
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
      {
        id: 8,
        username: "lucabianchi",
        email: "medium@example.local",
        full_name: null,
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
      {
        id: 9,
        username: "serusi.luca",
        email: "noreply@example.local",
        full_name: null,
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
    mocks.listAllPresenzeCollaborators.mockResolvedValueOnce([
      {
        id: "high",
        application_user_id: null,
        kint: null,
        kkint: null,
        employee_code: "1001",
        company_code: null,
        company_label: null,
        name: "MARIO ROSSI",
        birth_date: null,
        contract_kind: "impiegato",
        operai_group: null,
        standard_daily_minutes: 385,
        is_active: true,
        last_seen_at: null,
        created_at: "2026-05-29T09:00:00Z",
        updated_at: "2026-05-29T09:00:00Z",
      },
      {
        id: "medium",
        application_user_id: null,
        kint: null,
        kkint: null,
        employee_code: "1002",
        company_code: null,
        company_label: null,
        name: "LUCA BIANCHI",
        birth_date: null,
        contract_kind: "quadro",
        operai_group: null,
        standard_daily_minutes: null,
        is_active: true,
        last_seen_at: null,
        created_at: "2026-05-29T09:00:00Z",
        updated_at: "2026-05-29T09:00:00Z",
      },
      {
        id: "low",
        application_user_id: null,
        kint: null,
        kkint: null,
        employee_code: "1003",
        company_code: null,
        company_label: null,
        name: "SERUSI LUCA ANTONIO",
        birth_date: null,
        contract_kind: null,
        operai_group: null,
        standard_daily_minutes: null,
        is_active: true,
        last_seen_at: null,
        created_at: "2026-05-29T09:00:00Z",
        updated_at: "2026-05-29T09:00:00Z",
      },
    ]);

    render(<PresenzeCollaboratoriPage />);

    expect((await screen.findAllByText("Alta")).length).toBeGreaterThan(0);
    expect(screen.getAllByText("Media").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Bassa").length).toBeGreaterThan(0);
    expect(screen.getAllByText(/confidenza alta/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/confidenza media/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/confidenza bassa/).length).toBeGreaterThan(0);
  });

  test("handles missing token and initial collaborator load failures", async () => {
    mocks.getStoredAccessToken.mockReturnValueOnce(null);
    const { unmount } = render(<PresenzeCollaboratoriPage />);

    expect(screen.getByText("Collaboratori")).toBeInTheDocument();
    expect(mocks.getCurrentUser).not.toHaveBeenCalled();
    unmount();

    mocks.getStoredAccessToken.mockReturnValue("token");
    mocks.getCurrentUser.mockRejectedValueOnce(new Error("Errore sessione"));
    render(<PresenzeCollaboratoriPage />);

    expect(await screen.findByText("Errore sessione")).toBeInTheDocument();
  });

  test("handles non-error collaborator load failures", async () => {
    mocks.getCurrentUser.mockRejectedValueOnce("boom");
    render(<PresenzeCollaboratoriPage />);

    expect(await screen.findByText("Errore caricamento collaboratori")).toBeInTheDocument();
  });

  test("handles collaborator mapping validation, unchanged values and api errors", async () => {
    mocks.mapPresenzeCollaboratorApplicationUser.mockRejectedValueOnce(new Error("Errore mapping"));
    render(<PresenzeCollaboratoriPage />);

    await screen.findAllByText("AMADU SALVATORE");
    const selects = screen.getAllByRole("combobox");
    const mappingSelect = selects[selects.length - 2];
    mappingSelect.append(new Option("Valore non valido", "bad"));
    fireEvent.change(mappingSelect, { target: { value: "bad" } });
    fireEvent.click(screen.getAllByText("Salva")[0]);
    expect(await screen.findByText("Seleziona un utente GAIA valido.")).toBeInTheDocument();

    fireEvent.change(mappingSelect, { target: { value: "7" } });
    fireEvent.click(screen.getAllByText("Salva")[0]);
    expect(await screen.findByText("Errore mapping")).toBeInTheDocument();

    mocks.mapPresenzeCollaboratorApplicationUser.mockResolvedValueOnce({
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
    fireEvent.click(screen.getAllByText("Salva")[0]);
    await waitFor(() => {
      expect(mocks.mapPresenzeCollaboratorApplicationUser).toHaveBeenCalledWith("token", "collab-1", 7);
    });

    fireEvent.click(screen.getAllByText("Salva")[0]);
    await waitFor(() => {
      expect(screen.queryByText("Errore mapping")).not.toBeInTheDocument();
    });

    mocks.getStoredAccessToken.mockReturnValueOnce(null);
    fireEvent.change(mappingSelect, { target: { value: "" } });
    fireEvent.click(screen.getAllByText("Salva")[0]);
    expect(await screen.findByText("Sessione scaduta. Effettua di nuovo l'accesso.")).toBeInTheDocument();
  });

  test("applies suggested mappings", async () => {
    mocks.listAllApplicationUsers.mockResolvedValueOnce([
      {
        id: 7,
        username: "amadu.salvatore",
        email: "amadu.salvatore@example.local",
        full_name: "AMADU SALVATORE",
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
    mocks.mapPresenzeCollaboratorApplicationUser.mockResolvedValueOnce({
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
    render(<PresenzeCollaboratoriPage />);

    await screen.findAllByText("AMADU SALVATORE");
    fireEvent.click(screen.getByText("Applica suggeriti"));
    await waitFor(() => {
      expect(mocks.mapPresenzeCollaboratorApplicationUser).toHaveBeenCalledWith("token", "collab-1", 7);
    });

    mocks.getStoredAccessToken.mockReturnValueOnce(null);
    fireEvent.click(screen.getByText("Applica suggeriti"));
  });

  test("reports suggested mapping batch failures", async () => {
    mocks.listAllApplicationUsers.mockResolvedValueOnce([
      {
        id: 7,
        username: "amadu.salvatore",
        email: "amadu.salvatore@example.local",
        full_name: "AMADU SALVATORE",
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
    mocks.mapPresenzeCollaboratorApplicationUser.mockRejectedValueOnce("plain batch failure");
    render(<PresenzeCollaboratoriPage />);

    await screen.findAllByText("AMADU SALVATORE");
    fireEvent.click(screen.getByText("Applica suggeriti"));

    expect(await screen.findByText("Errore applicazione mapping suggeriti")).toBeInTheDocument();

    mocks.mapPresenzeCollaboratorApplicationUser.mockRejectedValueOnce(new Error("Errore batch"));
    fireEvent.click(screen.getByText("Applica suggeriti"));
    expect(await screen.findByText("Errore batch")).toBeInTheDocument();
  });

  test("refreshes collaborators list when embedded detail reports an update", async () => {
    mocks.listAllPresenzeCollaborators
      .mockResolvedValueOnce([
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
      ])
      .mockResolvedValueOnce([
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
          operai_group: "catasto_magazzino",
          standard_daily_minutes: 420,
          is_active: true,
          last_seen_at: "2026-05-29T09:00:00Z",
          created_at: "2026-05-29T09:00:00Z",
          updated_at: "2026-05-29T09:00:00Z",
        },
      ]);
    render(<PresenzeCollaboratoriPage />);

    const collaboratorCells = await screen.findAllByText("AMADU SALVATORE");
    fireEvent.click(collaboratorCells[0]);
    window.dispatchEvent(
      new MessageEvent("message", {
        origin: window.location.origin,
        data: { type: PRESENZE_COLLABORATOR_DETAIL_UPDATED_MESSAGE },
      }),
    );

    await waitFor(() => {
      expect(mocks.listAllPresenzeCollaborators.mock.calls.length).toBeGreaterThanOrEqual(2);
    });
    expect(await screen.findByText("Operaio catasto / magazzino")).toBeInTheDocument();
  });

  test("handles embedded detail ignored messages, refresh failures and close refresh", async () => {
    render(<PresenzeCollaboratoriPage />);

    const collaboratorCells = await screen.findAllByText("AMADU SALVATORE");
    fireEvent.click(collaboratorCells[0]);
    window.dispatchEvent(
      new MessageEvent("message", {
        origin: "https://example.invalid",
        data: { type: PRESENZE_COLLABORATOR_DETAIL_UPDATED_MESSAGE },
      }),
    );
    window.dispatchEvent(
      new MessageEvent("message", {
        origin: window.location.origin,
        data: { type: "ignored" },
      }),
    );

    mocks.listAllPresenzeCollaborators.mockRejectedValueOnce(new Error("Refresh failed"));
    window.dispatchEvent(
      new MessageEvent("message", {
        origin: window.location.origin,
        data: { type: PRESENZE_COLLABORATOR_DETAIL_UPDATED_MESSAGE },
      }),
    );
    expect(await screen.findByText("Refresh failed")).toBeInTheDocument();

    mocks.listAllPresenzeCollaborators.mockRejectedValueOnce("plain failure");
    fireEvent.click(screen.getByText("Chiudi"));
    expect(await screen.findByText("Errore aggiornamento elenco collaboratori")).toBeInTheDocument();
  });

  test("closes embedded detail from overlay after a successful dirty refresh", async () => {
    render(<PresenzeCollaboratoriPage />);

    const collaboratorCells = await screen.findAllByText("AMADU SALVATORE");
    fireEvent.click(collaboratorCells[0]);
    mocks.listAllPresenzeCollaborators.mockRejectedValueOnce(new Error("Temporary refresh failure"));
    window.dispatchEvent(
      new MessageEvent("message", {
        origin: window.location.origin,
        data: { type: PRESENZE_COLLABORATOR_DETAIL_UPDATED_MESSAGE },
      }),
    );
    expect(await screen.findByText("Temporary refresh failure")).toBeInTheDocument();

    const overlay = screen.getByTitle("Dettaglio collaboratore AMADU SALVATORE").closest(".fixed") as HTMLElement;
    fireEvent.click(overlay.firstElementChild as HTMLElement);
    expect(screen.getByText("Dettaglio collaboratore")).toBeInTheDocument();
    fireEvent.click(overlay);

    await waitFor(() => {
      expect(screen.queryByText("Dettaglio collaboratore")).not.toBeInTheDocument();
    });
  });

  test("covers collaborator modal and mapping fallback branches", async () => {
    mocks.getCurrentUser.mockResolvedValue({
      id: 1,
      username: "admin",
      email: "admin@example.local",
      role: "super_admin",
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
    render(<PresenzeCollaboratoriPage />);

    const collaboratorCells = await screen.findAllByText("AMADU SALVATORE");
    fireEvent.click(collaboratorCells[0]);
    fireEvent.click(screen.getByText("Chiudi"));
    await waitFor(() => {
      expect(screen.queryByText("Dettaglio collaboratore")).not.toBeInTheDocument();
    });

    fireEvent.click((await screen.findAllByText("AMADU SALVATORE"))[0]);
    mocks.getStoredAccessToken.mockReturnValueOnce(null);
    window.dispatchEvent(
      new MessageEvent("message", {
        origin: window.location.origin,
        data: { type: PRESENZE_COLLABORATOR_DETAIL_UPDATED_MESSAGE },
      }),
    );
    await waitFor(() => {
      expect(screen.getByText("Dettaglio collaboratore")).toBeInTheDocument();
    });

    mocks.listAllPresenzeCollaborators.mockRejectedValueOnce("plain refresh failure");
    window.dispatchEvent(
      new MessageEvent("message", {
        origin: window.location.origin,
        data: { type: PRESENZE_COLLABORATOR_DETAIL_UPDATED_MESSAGE },
      }),
    );
    expect(await screen.findByText("Errore aggiornamento elenco collaboratori")).toBeInTheDocument();

    mocks.listAllPresenzeCollaborators.mockRejectedValueOnce(new Error("Close refresh failed"));
    fireEvent.click(screen.getByText("Chiudi"));
    expect(await screen.findByText("Close refresh failed")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Gruppo operai"), { target: { value: "unset" } });
    expect(screen.getAllByText("ARDU ANTONELLO").length).toBeGreaterThan(0);

    const selects = screen.getAllByRole("combobox");
    const ardaMappingSelect = selects[selects.length - 1];
    fireEvent.click(screen.getAllByText("Salva").at(-1) as HTMLElement);

    mocks.mapPresenzeCollaboratorApplicationUser.mockRejectedValueOnce("plain mapping failure");
    fireEvent.change(ardaMappingSelect, { target: { value: "7" } });
    fireEvent.click(screen.getAllByText("Salva").at(-1) as HTMLElement);
    expect(await screen.findByText("Errore mapping collaboratore")).toBeInTheDocument();

    mocks.mapPresenzeCollaboratorApplicationUser.mockResolvedValueOnce({
      id: "collab-2",
      application_user_id: 7,
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
    });
    fireEvent.click(screen.getAllByText("Salva").at(-1) as HTMLElement);
    await waitFor(() => {
      expect(mocks.mapPresenzeCollaboratorApplicationUser).toHaveBeenCalledWith("token", "collab-2", 7);
    });

    fireEvent.change(ardaMappingSelect, { target: { value: "" } });
    fireEvent.click(screen.getAllByText("Salva").at(-1) as HTMLElement);
    await waitFor(() => {
      expect(mocks.mapPresenzeCollaboratorApplicationUser).toHaveBeenCalledWith("token", "collab-2", null);
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

  test("covers contract wizard empty, close and overlay interactions", async () => {
    mocks.listAllPresenzeCollaborators.mockResolvedValueOnce([
      {
        id: "complete",
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
    ]);
    render(<PresenzeCollaboratoriPage />);

    await screen.findAllByText("AMADU SALVATORE");
    fireEvent.click(screen.getByText("Wizard contratti"));
    expect(screen.getByText("Tutti i collaboratori hanno gia un profilo contrattuale coerente.")).toBeInTheDocument();
    fireEvent.click(screen.getByText("Wizard profili contrattuali").closest("div") as HTMLElement);
    fireEvent.click(screen.getByText("Chiudi"));
    await waitFor(() => {
      expect(screen.queryByText("Wizard profili contrattuali")).not.toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("Wizard contratti"));
    const overlay = screen.getByText("Wizard profili contrattuali").closest(".fixed") as HTMLElement;
    fireEvent.click(overlay);
    await waitFor(() => {
      expect(screen.queryByText("Wizard profili contrattuali")).not.toBeInTheDocument();
    });
  });

  test("handles contract wizard no-token, unchanged and api error branches", async () => {
    mocks.listAllPresenzeCollaborators.mockResolvedValueOnce([
      {
        id: "unset",
        application_user_id: null,
        kint: null,
        kkint: null,
        employee_code: "3001",
        company_code: null,
        company_label: null,
        name: "PROFILO DA LASCIARE",
        birth_date: null,
        contract_kind: null,
        operai_group: null,
        standard_daily_minutes: null,
        is_active: true,
        last_seen_at: null,
        created_at: "2026-05-29T09:00:00Z",
        updated_at: "2026-05-29T09:00:00Z",
      },
    ]);
    render(<PresenzeCollaboratoriPage />);

    expect((await screen.findAllByText("PROFILO DA LASCIARE")).length).toBeGreaterThan(0);
    fireEvent.click(screen.getByText("Wizard contratti (1)"));

    mocks.getStoredAccessToken.mockReturnValueOnce(null);
    fireEvent.click(screen.getByText("Salva profili"));
    expect(await screen.findByText("Sessione scaduta. Effettua di nuovo l'accesso.")).toBeInTheDocument();

    fireEvent.click(screen.getByText("Salva profili"));
    await waitFor(() => {
      expect(mocks.updatePresenzeCollaboratorContractProfile).not.toHaveBeenCalled();
    });

    await waitFor(() => {
      expect(screen.queryByText("Wizard profili contrattuali")).not.toBeInTheDocument();
    });
    fireEvent.click(screen.getByText("Wizard contratti (1)"));

    fireEvent.change(screen.getByLabelText("Contratto PROFILO DA LASCIARE"), { target: { value: "impiegato" } });
    mocks.updatePresenzeCollaboratorContractProfile.mockRejectedValueOnce(new Error("Errore profilo"));
    fireEvent.click(screen.getByText("Salva profili"));
    expect(await screen.findByText("Errore profilo")).toBeInTheDocument();

    mocks.updatePresenzeCollaboratorContractProfile.mockRejectedValueOnce("plain profile failure");
    fireEvent.click(screen.getByText("Salva profili"));
    expect(await screen.findByText("Errore salvataggio profili contrattuali")).toBeInTheDocument();
  });

  test("previews contract wizard alternative selections", async () => {
    render(<PresenzeCollaboratoriPage />);

    await screen.findAllByText("AMADU SALVATORE");
    fireEvent.click(screen.getByText("Wizard contratti (1)"));
    const select = screen.getByLabelText("Contratto ARDU ANTONELLO");

    fireEvent.change(select, { target: { value: "operaio_agrario" } });
    expect(screen.getAllByText("Operaio agrario").length).toBeGreaterThan(0);
    fireEvent.change(select, { target: { value: "impiegato" } });
    expect(screen.getAllByText("Impiegato").length).toBeGreaterThan(0);
    fireEvent.change(select, { target: { value: "quadro" } });
    expect(screen.getAllByText("Quadro").length).toBeGreaterThan(0);
    fireEvent.change(select, { target: { value: "altro" } });
    expect(screen.getAllByText("Altro").length).toBeGreaterThan(0);
    fireEvent.change(select, { target: { value: "unset" } });
    expect(screen.getAllByText("Non impostato").length).toBeGreaterThan(0);
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
    mocks.listPresenzeDailyMatrixRecords.mockResolvedValue({
      items: [
        {
          id: "record-1",
          collaborator_id: "collab-1",
          owner_user_id: 1,
          application_user_id: 7,
          work_date: "2026-07-16",
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
          operational_status: "blocking",
          operational_formula_code: "OPESAB",
          operational_expected_minutes: 420,
          operational_worked_minutes: 540,
          operational_missing_minutes: 90,
          operational_mpe_minutes: 120,
          operational_notes: ["Mancano minuti rispetto alla formula GAIA"],
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
      page_size: 5000,
    });
    mocks.listPresenzeSyncJobs.mockResolvedValue([
      {
        id: "sync-1",
        status: "running",
        requested_by_user_id: 1,
        credential_id: 4,
        import_job_id: null,
        period_start: "2026-07-01",
        period_end: "2026-07-31",
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
    expect(screen.getByText("Casi da verificare")).toBeInTheDocument();
    expect(screen.getByText("Apri pagina anomalie")).toHaveAttribute("href", "/presenze/anomalie");
    expect(screen.getAllByText("Vai alle anomalie").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Ore mancanti").length).toBeGreaterThan(0);
  });

  test("renders fallback states when there is no access token", async () => {
    mocks.getStoredAccessToken.mockReturnValue(null);

    render(<PresenzePage />);

    expect(await screen.findByText("Nessuna sync registrata")).toBeInTheDocument();
    expect(screen.getByText("Nessun caso prioritario nel mese corrente. Per verifiche estese puoi comunque consultare la pagina anomalie.")).toBeInTheDocument();
    expect(screen.getByText("Nessuna causale assenza rilevata nel mese.")).toBeInTheDocument();
    expect(screen.getByText("Nessun codice orario disponibile.")).toBeInTheDocument();
    expect(screen.getByText("Nessun collaboratore disponibile.")).toBeInTheDocument();
    expect(mocks.getPresenzeDashboardSummary).not.toHaveBeenCalled();
    expect(mocks.listAllPresenzeCollaborators).not.toHaveBeenCalled();
  });

  test("renders analysis and anomaly review cards with fallback reasons", async () => {
    mocks.listAllPresenzeCollaborators.mockResolvedValue([]);
    mocks.getPresenzeDashboardSummary.mockResolvedValue({
      collaborators_total: 0,
      mapped_collaborators_total: 0,
      active_collaborators_total: 0,
      daily_records_total: 2,
      ordinary_minutes_total: 0,
      absence_minutes_total: 0,
      extra_minutes_total: 0,
      straordinario_minutes_total: 0,
      maggior_presenza_minutes_total: 0,
      km_total: 0,
      trasferta_minutes_total: 0,
      trasferta_days_total: 0,
      trasferta_montano_days_total: 0,
      anomaly_total: 2,
      special_day_total: 0,
      recovery_days_matured_total: 0,
      recovery_days_used_total: 0,
      recovery_days_balance_total: 0,
      worked_days_total: 0,
      absence_days_total: 0,
      justified_days_total: 0,
      cause_stats: {},
      schedule_stats: [],
    });
    mocks.listPresenzeSyncJobs.mockResolvedValue([
      {
        id: "sync-failed-1",
        status: "failed",
        requested_by_user_id: 1,
        credential_id: 4,
        import_job_id: null,
        period_start: "2026-07-01",
        period_end: "2026-07-31",
        collaborator_limit: null,
        records_imported: 0,
        records_skipped: 0,
        records_errors: 2,
        json_artifact_path: null,
        worker_log_path: null,
        worker_pid: null,
        attempt_count: 1,
        max_attempts: 3,
        error_detail: "boom",
        params_json: {},
        created_at: "2026-07-08T09:00:00Z",
        started_at: "2026-07-08T09:00:00Z",
        finished_at: "2026-07-08T09:05:00Z",
      },
    ]);
    mocks.listPresenzeDailyMatrixRecords.mockResolvedValue({
      items: [
        {
          id: "record-analysis",
          collaborator_id: "missing-collab",
          owner_user_id: 1,
          application_user_id: null,
          work_date: "2026-07-02",
          schedule_code: null,
          teo_minutes: 0,
          ordinary_minutes: 0,
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
          operational_status: "in_analysis",
          operational_formula_code: null,
          operational_expected_minutes: 0,
          operational_worked_minutes: 0,
          operational_missing_minutes: 0,
          operational_mpe_minutes: 0,
          operational_notes: ["", "Verificare giornata ricostruita"],
          stato: null,
          evidenze: null,
          raw_weekday: "G",
          detail_title: null,
          detail_status: null,
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
          detail_text: null,
          detail_error: null,
          special_day: false,
          raw_payload_json: {},
          source_job_id: null,
          created_at: "2026-07-08T09:00:00Z",
          updated_at: "2026-07-08T09:00:00Z",
          punches: [],
        },
        {
          id: "record-unknown",
          collaborator_id: "missing-collab-2",
          owner_user_id: 1,
          application_user_id: null,
          work_date: "2026-07-03",
          schedule_code: null,
          teo_minutes: 0,
          ordinary_minutes: 0,
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
          operational_status: "unknown",
          operational_formula_code: null,
          operational_expected_minutes: 0,
          operational_worked_minutes: 0,
          operational_missing_minutes: 0,
          operational_mpe_minutes: 0,
          operational_notes: [],
          stato: null,
          evidenze: null,
          raw_weekday: "V",
          detail_title: null,
          detail_status: null,
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
          detail_text: null,
          detail_error: "Errore import dettaglio",
          special_day: false,
          raw_payload_json: {},
          source_job_id: null,
          created_at: "2026-07-08T09:00:00Z",
          updated_at: "2026-07-08T09:00:00Z",
          punches: [],
        },
      ],
      total: 2,
      page: 1,
      page_size: 5000,
    });

    render(<PresenzePage />);

    expect(await screen.findByText("Ultima sync: failed")).toBeInTheDocument();
    expect(screen.getByText("Periodo 2026-07-01 / 2026-07-31 · importati 0 · errori 2")).toBeInTheDocument();
    expect(screen.getByText("Da verificare")).toBeInTheDocument();
    expect(screen.getByText("Verificare giornata ricostruita")).toBeInTheDocument();
    expect(screen.getByText("Errore import dettaglio")).toBeInTheDocument();
    expect(screen.getByText("missing-collab")).toBeInTheDocument();
    expect(
      screen.getAllByText((_, element) => element?.textContent?.includes("Orario non disponibile") ?? false).length,
    ).toBeGreaterThan(0);
  });

  test("covers dashboard fallback branches for sync, transfers and anomaly reasons", async () => {
    mocks.listAllPresenzeCollaborators.mockResolvedValue([
      {
        id: "collab-fallback",
        application_user_id: null,
        kint: "301",
        kkint: "{fallback}",
        employee_code: null,
        company_code: null,
        company_label: null,
        name: "SENZA AZIENDA",
        birth_date: Symbol("unknown"),
        contract_kind: "operaio",
        operai_group: null,
        standard_daily_minutes: 420,
        is_active: true,
        last_seen_at: "2026-07-08T09:00:00Z",
        created_at: "2026-07-08T09:00:00Z",
        updated_at: "2026-07-08T09:00:00Z",
      },
    ]);
    mocks.getPresenzeDashboardSummary.mockResolvedValue({
      collaborators_total: 1,
      mapped_collaborators_total: 0,
      active_collaborators_total: 1,
      daily_records_total: 6,
      ordinary_minutes_total: 60,
      absence_minutes_total: 0,
      extra_minutes_total: 0,
      straordinario_minutes_total: 0,
      maggior_presenza_minutes_total: 0,
      km_total: 0,
      trasferta_minutes_total: 120,
      trasferta_days_total: 1,
      trasferta_montano_days_total: 2,
      anomaly_total: 6,
      special_day_total: 0,
      recovery_days_matured_total: 0,
      recovery_days_used_total: 0,
      recovery_days_balance_total: 0,
      worked_days_total: 1,
      absence_days_total: 0,
      justified_days_total: 0,
      cause_stats: {},
      schedule_stats: [],
    });
    mocks.listPresenzeSyncJobs.mockResolvedValue([
      {
        id: "sync-completed-1",
        status: "completed",
        requested_by_user_id: 1,
        credential_id: 4,
        import_job_id: null,
        period_start: "2026-07-01",
        period_end: "2026-07-31",
        collaborator_limit: null,
        records_imported: 3,
        records_skipped: 0,
        records_errors: 5,
        json_artifact_path: null,
        worker_log_path: null,
        worker_pid: null,
        attempt_count: 1,
        max_attempts: 3,
        error_detail: null,
        params_json: {
          progress: {
            index: 3,
            total: 7,
          },
        },
        created_at: "2026-07-08T09:00:00Z",
        started_at: "2026-07-08T09:00:00Z",
        finished_at: "2026-07-08T09:05:00Z",
      },
    ]);
    mocks.listPresenzeDailyMatrixRecords.mockResolvedValue({
      items: [
        {
          id: "fallback-1",
          collaborator_id: "collab-fallback",
          owner_user_id: 1,
          application_user_id: null,
          work_date: "2026-07-01",
          schedule_code: null,
          teo_minutes: 0,
          ordinary_minutes: 0,
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
          operational_status: "blocking",
          operational_formula_code: null,
          operational_expected_minutes: 0,
          operational_worked_minutes: 0,
          operational_missing_minutes: null,
          operational_mpe_minutes: 0,
          operational_notes: [],
          stato: null,
          evidenze: null,
          raw_weekday: "M",
          detail_title: null,
          detail_status: "Dettaglio fallback",
          detail_programmed_schedule: null,
          detail_effective_schedule: null,
          detail_time_slots: null,
          detail_schedule_type: null,
          detail_theoretical_hours: null,
          detail_absence_hours: null,
          detail_day_summary: {},
          detail_day_totals: {},
          detail_requests: [],
          detail_anomalies: [{}],
          detail_text: null,
          detail_error: null,
          special_day: false,
          raw_payload_json: {},
          source_job_id: null,
          created_at: "2026-07-08T09:00:00Z",
          updated_at: "2026-07-08T09:00:00Z",
          punches: [],
        },
        {
          id: "fallback-2",
          collaborator_id: "collab-fallback",
          owner_user_id: 1,
          application_user_id: null,
          work_date: "2026-07-02",
          schedule_code: null,
          teo_minutes: 0,
          ordinary_minutes: 0,
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
          operational_status: "unknown",
          operational_formula_code: null,
          operational_expected_minutes: 0,
          operational_worked_minutes: 0,
          operational_missing_minutes: 0,
          operational_mpe_minutes: 0,
          operational_notes: [],
          stato: null,
          evidenze: null,
          raw_weekday: "M",
          detail_title: null,
          detail_status: null,
          detail_programmed_schedule: null,
          detail_effective_schedule: null,
          detail_time_slots: null,
          detail_schedule_type: null,
          detail_theoretical_hours: null,
          detail_absence_hours: null,
          detail_day_summary: {},
          detail_day_totals: {},
          detail_requests: [],
          detail_anomalies: [{}],
          detail_text: null,
          detail_error: null,
          special_day: false,
          raw_payload_json: {},
          source_job_id: null,
          created_at: "2026-07-08T09:00:00Z",
          updated_at: "2026-07-08T09:00:00Z",
          punches: [],
        },
        {
          id: "fallback-3",
          collaborator_id: "collab-fallback",
          owner_user_id: 1,
          application_user_id: null,
          work_date: "2026-07-03",
          schedule_code: null,
          teo_minutes: 0,
          ordinary_minutes: 0,
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
          operational_status: "in_analysis",
          operational_formula_code: null,
          operational_expected_minutes: 0,
          operational_worked_minutes: 0,
          operational_missing_minutes: 0,
          operational_mpe_minutes: 0,
          operational_notes: [],
          stato: "Solo stato",
          evidenze: null,
          raw_weekday: "M",
          detail_title: null,
          detail_status: null,
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
          detail_text: null,
          detail_error: null,
          special_day: false,
          raw_payload_json: {},
          source_job_id: null,
          created_at: "2026-07-08T09:00:00Z",
          updated_at: "2026-07-08T09:00:00Z",
          punches: [],
        },
        {
          id: "fallback-4",
          collaborator_id: "collab-fallback",
          owner_user_id: 1,
          application_user_id: null,
          work_date: "2026-07-04",
          schedule_code: null,
          teo_minutes: 0,
          ordinary_minutes: 0,
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
          operational_status: "in_analysis",
          operational_formula_code: null,
          operational_expected_minutes: 0,
          operational_worked_minutes: 0,
          operational_missing_minutes: 0,
          operational_mpe_minutes: 0,
          operational_notes: [],
          stato: null,
          evidenze: null,
          raw_weekday: "M",
          detail_title: null,
          detail_status: null,
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
          detail_text: null,
          detail_error: null,
          special_day: false,
          raw_payload_json: {},
          source_job_id: null,
          created_at: "2026-07-08T09:00:00Z",
          updated_at: "2026-07-08T09:00:00Z",
          punches: [],
        },
      ],
      total: 4,
      page: 1,
      page_size: 5000,
    });

    render(<PresenzePage />);

    expect(await screen.findByText("Ultima sync completata")).toBeInTheDocument();
    expect(screen.getByText("Avanzamento 3/7 · completati 0 · falliti 5")).toBeInTheDocument();
    expect(screen.getAllByText(/montano 2/).length).toBeGreaterThan(0);
    expect(screen.getByText("Dettaglio fallback")).toBeInTheDocument();
    expect(screen.getByText("Anomalia da verificare")).toBeInTheDocument();
    expect(screen.getByText("Solo stato")).toBeInTheDocument();
    expect(screen.getByText("Caso da verificare")).toBeInTheDocument();
    const fallbackCollaboratorNames = await screen.findAllByText("SENZA AZIENDA");
    const fallbackCollaboratorButton = fallbackCollaboratorNames
      .map((element) => element.closest("button"))
      .find(Boolean);
    expect(fallbackCollaboratorButton).toBeDefined();
    expect(fallbackCollaboratorButton?.textContent).toContain("Matricola n/d");
    expect(fallbackCollaboratorButton?.textContent).toContain("Data nascita n/d");

    fireEvent.change(screen.getByPlaceholderText("Cerca per nome, matricola o azienda"), {
      target: { value: "nessun-match" },
    });
    expect(await screen.findByText("Nessun collaboratore trovato per questa ricerca.")).toBeInTheDocument();
  });

  test("opens collaborator modal and closes it from button and backdrop", async () => {
    render(<PresenzePage />);

    const collaboratorButton = await screen.findByRole("button", { name: /AMADU SALVATORE/i });
    fireEvent.click(collaboratorButton);

    expect(await screen.findByText("Dettaglio collaboratore")).toBeInTheDocument();
    expect(screen.getByTitle("Dettaglio collaboratore AMADU SALVATORE")).toHaveAttribute("src", "/presenze/collaboratori/collab-1?embedded=1");
    expect(screen.getByRole("link", { name: "Apri pagina completa" })).toHaveAttribute("href", "/presenze/collaboratori/collab-1");

    fireEvent.click(screen.getByRole("button", { name: "Chiudi" }));
    await waitFor(() => {
      expect(screen.queryByText("Dettaglio collaboratore")).not.toBeInTheDocument();
    });

    fireEvent.click(await screen.findByRole("button", { name: /AMADU SALVATORE/i }));
    expect(await screen.findByText("Dettaglio collaboratore")).toBeInTheDocument();
    fireEvent.click(screen.getByText("Dettaglio collaboratore").closest("div[class*='fixed']") ?? document.body);
    await waitFor(() => {
      expect(screen.queryByText("Dettaglio collaboratore")).not.toBeInTheDocument();
    });
  });

  test("filters collaborators and uses object/fallback display values", async () => {
    mocks.listAllPresenzeCollaborators.mockResolvedValue([
      {
        id: "collab-weird-1",
        application_user_id: null,
        kint: "201",
        kkint: "{obj-1}",
        employee_code: "ZX-01",
        company_code: "77",
        company_label: "77 - Demo",
        name: { employee_code: "OBJ-NAME-01" },
        birth_date: {},
        contract_kind: "operaio",
        operai_group: null,
        standard_daily_minutes: 420,
        is_active: true,
        last_seen_at: "2026-07-08T09:00:00Z",
        created_at: "2026-07-08T09:00:00Z",
        updated_at: "2026-07-08T09:00:00Z",
      },
      {
        id: "collab-weird-2",
        application_user_id: 7,
        kint: "202",
        kkint: "{obj-2}",
        employee_code: "ZX-02",
        company_code: "88",
        company_label: "88 - Searchable",
        name: { name: "NOME OGGETTO" },
        birth_date: "1980-01-01",
        contract_kind: "impiegato",
        operai_group: null,
        standard_daily_minutes: 480,
        is_active: true,
        last_seen_at: "2026-07-08T09:00:00Z",
        created_at: "2026-07-08T09:00:00Z",
        updated_at: "2026-07-08T09:00:00Z",
      },
    ]);

    render(<PresenzePage />);

    expect(await screen.findByText("OBJ-NAME-01")).toBeInTheDocument();
    expect(screen.getByText("NOME OGGETTO")).toBeInTheDocument();
    expect(screen.getByText(/Matricola ZX-01/)).toBeInTheDocument();
    expect(screen.getByText(/Data nascita n\/d/)).toBeInTheDocument();

    fireEvent.change(screen.getByPlaceholderText("Cerca per nome, matricola o azienda"), {
      target: { value: "searchable" },
    });

    expect(await screen.findByText("Risultati rapidi: 1")).toBeInTheDocument();
    expect(screen.getByText("NOME OGGETTO")).toBeInTheDocument();
    expect(screen.queryByText("OBJ-NAME-01")).not.toBeInTheDocument();
  });

  test("shows module load error when dashboard fetch fails", async () => {
    mocks.getPresenzeDashboardSummary.mockRejectedValue("boom");

    render(<PresenzePage />);

    expect(await screen.findByText("Errore caricamento modulo Giornaliere")).toBeInTheDocument();
  });

  test("shows Error instance message when dashboard fetch fails", async () => {
    mocks.getPresenzeDashboardSummary.mockRejectedValue(new Error("errore dashboard"));

    render(<PresenzePage />);

    expect(await screen.findByText("errore dashboard")).toBeInTheDocument();
  });

  test("shows collaborator load error and cleans up idle callback on unmount", async () => {
    const requestIdleCallback = vi.fn((callback: IdleRequestCallback) => {
      callback({ didTimeout: false, timeRemaining: () => 1 } as IdleDeadline);
      return 7;
    });
    const cancelIdleCallback = vi.fn();
    Object.defineProperty(window, "requestIdleCallback", {
      configurable: true,
      value: requestIdleCallback,
    });
    Object.defineProperty(window, "cancelIdleCallback", {
      configurable: true,
      value: cancelIdleCallback,
    });

    mocks.getPresenzeDashboardSummary.mockResolvedValue({
      collaborators_total: 0,
      mapped_collaborators_total: 0,
      active_collaborators_total: 0,
      daily_records_total: 0,
      ordinary_minutes_total: 0,
      absence_minutes_total: 0,
      extra_minutes_total: 0,
      straordinario_minutes_total: 0,
      maggior_presenza_minutes_total: 0,
      km_total: 0,
      trasferta_minutes_total: 0,
      trasferta_days_total: 0,
      trasferta_montano_days_total: 0,
      anomaly_total: 0,
      special_day_total: 0,
      recovery_days_matured_total: 0,
      recovery_days_used_total: 0,
      recovery_days_balance_total: 0,
      worked_days_total: 0,
      absence_days_total: 0,
      justified_days_total: 0,
      cause_stats: {},
      schedule_stats: [],
    });
    mocks.listPresenzeSyncJobs.mockResolvedValue([]);
    mocks.listPresenzeDailyMatrixRecords.mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 5000,
    });
    mocks.listAllPresenzeCollaborators.mockRejectedValue("boom");

    const { unmount } = render(<PresenzePage />);

    expect(await screen.findByText("Errore caricamento collaboratori giornaliere")).toBeInTheDocument();

    unmount();
    expect(requestIdleCallback).toHaveBeenCalled();
    expect(cancelIdleCallback).toHaveBeenCalledWith(7);

    Reflect.deleteProperty(window, "requestIdleCallback");
    Reflect.deleteProperty(window, "cancelIdleCallback");
  });

  test("shows Error instance message when collaborator load fails", async () => {
    const requestIdleCallback = vi.fn((callback: IdleRequestCallback) => {
      callback({ didTimeout: false, timeRemaining: () => 1 } as IdleDeadline);
      return 9;
    });
    Object.defineProperty(window, "requestIdleCallback", {
      configurable: true,
      value: requestIdleCallback,
    });
    Object.defineProperty(window, "cancelIdleCallback", {
      configurable: true,
      value: vi.fn(),
    });
    mocks.getPresenzeDashboardSummary.mockResolvedValue({
      collaborators_total: 0,
      mapped_collaborators_total: 0,
      active_collaborators_total: 0,
      daily_records_total: 0,
      ordinary_minutes_total: 0,
      absence_minutes_total: 0,
      extra_minutes_total: 0,
      straordinario_minutes_total: 0,
      maggior_presenza_minutes_total: 0,
      km_total: 0,
      trasferta_minutes_total: 0,
      trasferta_days_total: 0,
      trasferta_montano_days_total: 0,
      anomaly_total: 0,
      special_day_total: 0,
      recovery_days_matured_total: 0,
      recovery_days_used_total: 0,
      recovery_days_balance_total: 0,
      worked_days_total: 0,
      absence_days_total: 0,
      justified_days_total: 0,
      cause_stats: {},
      schedule_stats: [],
    });
    mocks.listPresenzeSyncJobs.mockResolvedValue([]);
    mocks.listPresenzeDailyMatrixRecords.mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 5000,
    });
    mocks.listAllPresenzeCollaborators.mockRejectedValue(new Error("errore collaboratori"));

    render(<PresenzePage />);

    expect(await screen.findByText("errore collaboratori")).toBeInTheDocument();

    Reflect.deleteProperty(window, "requestIdleCallback");
    Reflect.deleteProperty(window, "cancelIdleCallback");
  });

  test("does not update collaborator state after unmount on resolve", async () => {
    let resolveCollaborators: (value: unknown[]) => void = () => {
      throw new Error("resolveCollaborators not captured");
    };
    const collaboratorsPromise = new Promise<unknown[]>((resolve) => {
      resolveCollaborators = resolve;
    });
    const requestIdleCallback = vi.fn((callback: IdleRequestCallback) => {
      callback({ didTimeout: false, timeRemaining: () => 1 } as IdleDeadline);
      return 11;
    });
    Object.defineProperty(window, "requestIdleCallback", {
      configurable: true,
      value: requestIdleCallback,
    });
    Object.defineProperty(window, "cancelIdleCallback", {
      configurable: true,
      value: vi.fn(),
    });
    mocks.listAllPresenzeCollaborators.mockReturnValue(collaboratorsPromise);

    const { unmount } = render(<PresenzePage />);
    unmount();

    resolveCollaborators([]);
    await Promise.resolve();

    expect(mocks.listAllPresenzeCollaborators).toHaveBeenCalled();

    Reflect.deleteProperty(window, "requestIdleCallback");
    Reflect.deleteProperty(window, "cancelIdleCallback");
  });

  test("does not update collaborator error state after unmount on reject", async () => {
    let rejectCollaborators: (reason?: unknown) => void = () => {
      throw new Error("rejectCollaborators not captured");
    };
    const collaboratorsPromise = new Promise((_, reject) => {
      rejectCollaborators = reject;
    });
    const requestIdleCallback = vi.fn((callback: IdleRequestCallback) => {
      callback({ didTimeout: false, timeRemaining: () => 1 } as IdleDeadline);
      return 12;
    });
    Object.defineProperty(window, "requestIdleCallback", {
      configurable: true,
      value: requestIdleCallback,
    });
    Object.defineProperty(window, "cancelIdleCallback", {
      configurable: true,
      value: vi.fn(),
    });
    mocks.listAllPresenzeCollaborators.mockReturnValue(collaboratorsPromise);

    const { unmount } = render(<PresenzePage />);
    unmount();

    rejectCollaborators("late error");
    await Promise.resolve();

    expect(mocks.listAllPresenzeCollaborators).toHaveBeenCalled();

    Reflect.deleteProperty(window, "requestIdleCallback");
    Reflect.deleteProperty(window, "cancelIdleCallback");
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

  test("deletes a terminal sync job from history", async () => {
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
    mocks.deletePresenzeSyncJob.mockResolvedValue(undefined);

    render(<PresenzeSyncPage />);
    fireEvent.click(await screen.findByText("Elimina"));

    await waitFor(() => {
      expect(mocks.deletePresenzeSyncJob).toHaveBeenCalledWith("token", "sync-1");
      expect(screen.getByText(/eliminato/)).toBeInTheDocument();
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

  test("shows inactive presenze credentials as recoverable from settings", async () => {
    mocks.listPresenzeCredentials.mockResolvedValueOnce([
      {
        id: 4,
        application_user_id: 1,
        label: "Fabrizio",
        username: "Fabrizio.Podda",
        active: false,
        last_used_at: "2026-07-06T15:44:35Z",
        last_authenticated_url: "https://serviziweb.inaz.it/portalecbo/default.aspx",
        last_error: null,
        consecutive_failures: 0,
        created_at: "2026-05-29T09:00:00Z",
        updated_at: "2026-05-29T09:00:00Z",
      },
    ]);

    render(<PresenzeSettingsPage />);

    expect(await screen.findByText("Disattiva")).toBeInTheDocument();
    expect(screen.getByText(/Non verra usata dalle sync/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Test e riattiva" })).toBeInTheDocument();
  });
});
