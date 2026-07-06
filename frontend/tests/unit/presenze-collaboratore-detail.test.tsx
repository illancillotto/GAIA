import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import PresenzeCollaboratoreDetailPage from "@/app/presenze/collaboratori/[id]/page";

const mocks = vi.hoisted(() => ({
  getStoredAccessToken: vi.fn(),
  getCurrentUser: vi.fn(),
  listAllApplicationUsers: vi.fn(),
  listAllPresenzeCollaborators: vi.fn(),
  getPresenzeCollaboratorCalendar: vi.fn(),
  getPresenzeScheduleBootstrapPreview: vi.fn(),
  getPresenzeCollaboratorSummary: vi.fn(),
  listPresenzeScheduleTemplates: vi.fn(),
  listPresenzeCollaboratorScheduleAssignments: vi.fn(),
  mapPresenzeCollaboratorApplicationUser: vi.fn(),
  updatePresenzeCollaboratorContractProfile: vi.fn(),
  updatePresenzeDailyRecord: vi.fn(),
  createPresenzeCollaboratorScheduleAssignment: vi.fn(),
  deletePresenzeScheduleAssignment: vi.fn(),
}));

vi.mock("@/lib/auth", () => ({
  getStoredAccessToken: mocks.getStoredAccessToken,
}));

vi.mock("@/lib/api", () => ({
  getCurrentUser: mocks.getCurrentUser,
  listAllApplicationUsers: mocks.listAllApplicationUsers,
  listAllPresenzeCollaborators: mocks.listAllPresenzeCollaborators,
  getPresenzeCollaboratorCalendar: mocks.getPresenzeCollaboratorCalendar,
  getPresenzeScheduleBootstrapPreview:
    mocks.getPresenzeScheduleBootstrapPreview,
  getPresenzeCollaboratorSummary: mocks.getPresenzeCollaboratorSummary,
  listPresenzeScheduleTemplates: mocks.listPresenzeScheduleTemplates,
  listPresenzeCollaboratorScheduleAssignments:
    mocks.listPresenzeCollaboratorScheduleAssignments,
  mapPresenzeCollaboratorApplicationUser:
    mocks.mapPresenzeCollaboratorApplicationUser,
  updatePresenzeCollaboratorContractProfile:
    mocks.updatePresenzeCollaboratorContractProfile,
  updatePresenzeDailyRecord: mocks.updatePresenzeDailyRecord,
  createPresenzeCollaboratorScheduleAssignment:
    mocks.createPresenzeCollaboratorScheduleAssignment,
  deletePresenzeScheduleAssignment: mocks.deletePresenzeScheduleAssignment,
}));

vi.mock("@/components/app/protected-page", () => ({
  ProtectedPage: ({
    children,
    title,
  }: {
    children: React.ReactNode;
    title: string;
  }) => (
    <div>
      <h1>{title}</h1>
      {children}
    </div>
  ),
}));

vi.mock("next/navigation", () => ({
  useParams: () => ({ id: "collab-1" }),
  useSearchParams: () => new URLSearchParams(),
}));

describe("Presenze collaborator detail", () => {
  beforeEach(() => {
    mocks.getStoredAccessToken.mockReturnValue("token");
    mocks.getCurrentUser.mockResolvedValue({
      id: 1,
      username: "admin",
      email: "admin@example.local",
      full_name: "Admin User",
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
    mocks.listAllApplicationUsers.mockResolvedValue([
      {
        id: 6,
        username: "amadu.salvatore",
        email: "salvatoremda26@gmail.com",
        full_name: null,
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
        module_presenze: false,
        enabled_modules: ["accessi"],
        created_at: "2026-06-04T00:00:00Z",
        updated_at: "2026-06-04T00:00:00Z",
      },
      {
        id: 7,
        username: "mrossi",
        email: "mrossi@example.local",
        full_name: "Mario Rossi",
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
        module_presenze: false,
        enabled_modules: ["accessi"],
        created_at: "2026-06-04T00:00:00Z",
        updated_at: "2026-06-04T00:00:00Z",
      },
    ]);
    mocks.listAllPresenzeCollaborators.mockResolvedValue([
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
        operai_group: null,
        standard_daily_minutes: 420,
        is_active: true,
        last_seen_at: "2026-06-04T09:00:00Z",
        created_at: "2026-06-04T09:00:00Z",
        updated_at: "2026-06-04T09:00:00Z",
      },
    ]);
    mocks.getPresenzeCollaboratorCalendar.mockResolvedValue({
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
        contract_kind: "operaio",
        operai_group: null,
        standard_daily_minutes: 420,
        is_active: true,
        last_seen_at: "2026-06-04T09:00:00Z",
        created_at: "2026-06-04T09:00:00Z",
        updated_at: "2026-06-04T09:00:00Z",
      },
      items: [],
    });
    mocks.getPresenzeCollaboratorSummary.mockResolvedValue({
      collaborator: { id: "collab-1" },
      items: [],
    });
    mocks.getPresenzeScheduleBootstrapPreview.mockResolvedValue({
      detected_collaborators_total: 1,
      collaborators_with_suggestion_total: 1,
      collaborators_without_assignment_total: 1,
      profiles: [
        {
          profile_code: "GAIA_OPERAI",
          profile_label: "Profilo Operai",
          description: "Profilo operai",
          template_codes: [
            "OPE0714_1E3SAB",
            "OPE0736_STD",
            "OP_5.3_12.3",
            "OSAB5.3_12.3",
          ],
          rule_summaries: ["Feriale 7h"],
          active: true,
        },
        {
          profile_code: "GAIA_IMPIEGATI",
          profile_label: "Profilo Impiegati",
          description: "Profilo impiegati",
          template_codes: ["IMP1_STD", "IMP1_RIENTRO"],
          rule_summaries: ["Flessibile IMP1"],
          active: true,
        },
      ],
      presets: [],
      collaborator_suggestions: [
        {
          collaborator_id: "collab-1",
          employee_code: "1854",
          collaborator_name: "AMADU SALVATORE",
          company_code: "53",
          dominant_schedule_code: "OPE0714",
          schedule_codes: ["OPE0714", "OPESAB"],
          assigned_template_code: null,
          suggested_template_code: "OPE0714_1E3SAB",
          suggested_template_label: "Operai 07:00-14:00 con 1° e 3° sabato",
          suggestion_confidence: "high",
          suggestion_reason:
            "Template operaio compatibile con i codici rilevati.",
          already_assigned: false,
          configuration_status: "unassigned",
          configuration_notes: [],
        },
      ],
    });
    mocks.listPresenzeScheduleTemplates.mockResolvedValue([
      {
        id: 10,
        code: "OPE0714_1E3SAB",
        label: "Operai 07:00-14:00 con 1° e 3° sabato",
        company_code: "53",
        is_active: true,
        valid_from: null,
        valid_to: null,
        notes: null,
        created_at: "2026-06-04T09:00:00Z",
        updated_at: "2026-06-04T09:00:00Z",
        rules: [],
      },
      {
        id: 12,
        code: "IMP1_STD",
        label: "Impiegati flessibile 07:35-14:00",
        company_code: "53",
        is_active: true,
        valid_from: null,
        valid_to: null,
        notes: null,
        created_at: "2026-06-04T09:00:00Z",
        updated_at: "2026-06-04T09:00:00Z",
        rules: [],
      },
      {
        id: 11,
        code: "OP_5.3_12.3",
        label: "Operai 05:30-12:30",
        company_code: "53",
        is_active: true,
        valid_from: null,
        valid_to: null,
        notes: null,
        created_at: "2026-06-04T09:00:00Z",
        updated_at: "2026-06-04T09:00:00Z",
        rules: [],
      },
    ]);
    mocks.listPresenzeCollaboratorScheduleAssignments.mockResolvedValue([]);
    mocks.mapPresenzeCollaboratorApplicationUser.mockResolvedValue({
      id: "collab-1",
      owner_user_id: 1,
      application_user_id: 6,
      kint: "10159",
      kkint: "{demo}",
      employee_code: "1854",
      company_code: "53",
      company_label: "53 - CBO",
      name: "AMADU SALVATORE",
      birth_date: "1967-02-26",
      contract_kind: "operaio",
      operai_group: null,
      standard_daily_minutes: 420,
      is_active: true,
      last_seen_at: "2026-06-04T09:00:00Z",
      created_at: "2026-06-04T09:00:00Z",
      updated_at: "2026-06-04T09:00:00Z",
    });
    mocks.updatePresenzeCollaboratorContractProfile.mockResolvedValue({
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
      last_seen_at: "2026-06-04T09:00:00Z",
      created_at: "2026-06-04T09:00:00Z",
      updated_at: "2026-06-04T09:00:00Z",
    });
  });

  test("preselects suggested GAIA mapping and saves it", async () => {
    render(<PresenzeCollaboratoreDetailPage />);

    expect(
      await screen.findByText(/Suggerito: amadu.salvatore \(alta\)/i),
    ).toBeInTheDocument();
    expect(screen.getAllByText("Profilo contrattuale").length).toBeGreaterThan(
      0,
    );
    expect(screen.getAllByText("Operaio").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Standard giornaliero").length).toBeGreaterThan(
      0,
    );
    expect(screen.getAllByText("7:00").length).toBeGreaterThan(0);
    const mappingSection = screen
      .getByText("Mapping GAIA -> Presenze")
      .closest("article");
    expect(mappingSection).not.toBeNull();
    const select = within(mappingSection as HTMLElement).getByRole("combobox");

    await waitFor(() => {
      expect(select).toHaveValue("6");
    });

    fireEvent.click(screen.getByText("Salva collegamento"));

    await waitFor(() => {
      expect(mocks.mapPresenzeCollaboratorApplicationUser).toHaveBeenCalledWith(
        "token",
        "collab-1",
        6,
      );
    });

    expect(await screen.findByRole("status")).toHaveTextContent(
      /Mapping GAIA salvato correttamente/i,
    );
  });

  test("allows admins to update operai group from the GAIA profile panel", async () => {
    render(<PresenzeCollaboratoreDetailPage />);

    expect(
      await screen.findByText("Profilo GAIA e template orari"),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Profilo GAIA")).toHaveValue("GAIA_OPERAI");
    fireEvent.change(screen.getByLabelText("Gruppo operai"), {
      target: { value: "agrario" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Salva profilo GAIA" }));

    await waitFor(() => {
      expect(
        mocks.updatePresenzeCollaboratorContractProfile,
      ).toHaveBeenCalledWith("token", "collab-1", {
        contract_kind: "operaio",
        operai_group: "agrario",
        standard_daily_minutes: 420,
      });
    });
  });

  test("auto-loads the selected GAIA template when saving the GAIA profile", async () => {
    mocks.createPresenzeCollaboratorScheduleAssignment.mockResolvedValue({
      id: 99,
      collaborator_id: "collab-1",
      template_id: 10,
      valid_from: null,
      valid_to: null,
      notes: "Auto-caricato dal profilo GAIA_OPERAI",
      created_at: "2026-06-04T09:00:00Z",
      updated_at: "2026-06-04T09:00:00Z",
      template: {
        id: 10,
        code: "OPE0714_1E3SAB",
        label: "Operai 07:00-14:00 con 1° e 3° sabato",
        company_code: "53",
        is_active: true,
        valid_from: null,
        valid_to: null,
        notes: null,
        created_at: "2026-06-04T09:00:00Z",
        updated_at: "2026-06-04T09:00:00Z",
        rules: [],
      },
    });

    render(<PresenzeCollaboratoreDetailPage />);

    expect(
      await screen.findByText("Profilo GAIA e template orari"),
    ).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Gruppo operai"), {
      target: { value: "agrario" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Salva profilo GAIA" }));

    await waitFor(() => {
      expect(
        mocks.createPresenzeCollaboratorScheduleAssignment,
      ).toHaveBeenCalledWith("token", "collab-1", {
        template_id: 10,
        valid_from: null,
        valid_to: null,
        notes: "Auto-caricato dal profilo GAIA_OPERAI",
      });
    });
  });

  test("shows the operai group badge in the contract summary", async () => {
    mocks.listAllPresenzeCollaborators.mockResolvedValue([
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
        last_seen_at: "2026-06-04T09:00:00Z",
        created_at: "2026-06-04T09:00:00Z",
        updated_at: "2026-06-04T09:00:00Z",
      },
    ]);
    mocks.getPresenzeCollaboratorCalendar.mockResolvedValue({
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
        contract_kind: "operaio",
        operai_group: "agrario",
        standard_daily_minutes: 420,
        is_active: true,
        last_seen_at: "2026-06-04T09:00:00Z",
        created_at: "2026-06-04T09:00:00Z",
        updated_at: "2026-06-04T09:00:00Z",
      },
      items: [],
    });

    render(<PresenzeCollaboratoreDetailPage />);

    expect(await screen.findAllByText("Agrario")).not.toHaveLength(0);
  });

  test("shows GAIA template first and exposes included INAZ codes on demand", async () => {
    mocks.listPresenzeCollaboratorScheduleAssignments.mockResolvedValue([
      {
        id: 1,
        collaborator_id: "collab-1",
        template_id: 10,
        valid_from: null,
        valid_to: null,
        notes: "Bootstrap automatico",
        created_at: "2026-06-04T09:00:00Z",
        updated_at: "2026-06-04T09:00:00Z",
        template: {
          id: 10,
          code: "OPE0714_1E3SAB",
          label: "Operai 07:00-14:00 con 1° e 3° sabato",
          company_code: "53",
          is_active: true,
          valid_from: null,
          valid_to: null,
          notes: null,
          created_at: "2026-06-04T09:00:00Z",
          updated_at: "2026-06-04T09:00:00Z",
          rules: [
            {
              id: 1,
              template_id: 10,
              label: "Lun-Ven 07:00-14:00",
              weekday: 0,
              recurrence_kind: "weekly",
              week_of_month: null,
              interval_weeks: null,
              anchor_date: null,
              start_time: "07:00:00",
              end_time: "14:00:00",
              season_start_month: null,
              season_start_day: null,
              season_end_month: null,
              season_end_day: null,
              applies_on_holiday: false,
              ordinary_label: "OPE0714",
              sort_order: 0,
              created_at: "2026-06-04T09:00:00Z",
              updated_at: "2026-06-04T09:00:00Z",
            },
            {
              id: 2,
              template_id: 10,
              label: "Sabato",
              weekday: 5,
              recurrence_kind: "first_weekday_of_month",
              week_of_month: null,
              interval_weeks: null,
              anchor_date: null,
              start_time: "05:30:00",
              end_time: "12:30:00",
              season_start_month: 6,
              season_start_day: 1,
              season_end_month: 9,
              season_end_day: 30,
              applies_on_holiday: false,
              ordinary_label: "OSAB5.3_12.3",
              sort_order: 10,
              created_at: "2026-06-04T09:00:00Z",
              updated_at: "2026-06-04T09:00:00Z",
            },
          ],
        },
      },
    ]);

    render(<PresenzeCollaboratoreDetailPage />);

    expect(
      await screen.findByText("Operai 07:00-14:00 con 1° e 3° sabato"),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Template GAIA OPE0714_1E3SAB/i),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByText("Codici INAZ inclusi nel template GAIA"));
    expect(await screen.findByText("OPE0714")).toBeInTheDocument();
    expect(screen.getByText("OSAB5.3_12.3")).toBeInTheDocument();
  });

  test("deletes a schedule assignment from the detail panel", async () => {
    mocks.listPresenzeCollaboratorScheduleAssignments.mockResolvedValue([
      {
        id: 1,
        collaborator_id: "collab-1",
        template_id: 10,
        valid_from: null,
        valid_to: null,
        notes: "Bootstrap automatico",
        created_at: "2026-06-04T09:00:00Z",
        updated_at: "2026-06-04T09:00:00Z",
        template: {
          id: 10,
          code: "OPE0714_1E3SAB",
          label: "Operai 07:00-14:00 con 1° e 3° sabato",
          company_code: "53",
          is_active: true,
          valid_from: null,
          valid_to: null,
          notes: null,
          created_at: "2026-06-04T09:00:00Z",
          updated_at: "2026-06-04T09:00:00Z",
          rules: [],
        },
      },
    ]);

    render(<PresenzeCollaboratoreDetailPage />);

    expect(
      await screen.findByText("Operai 07:00-14:00 con 1° e 3° sabato"),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Elimina" }));

    await waitFor(() => {
      expect(mocks.deletePresenzeScheduleAssignment).toHaveBeenCalledWith(
        "token",
        1,
      );
    });
    await waitFor(() => {
      expect(
        screen.queryByText("Operai 07:00-14:00 con 1° e 3° sabato"),
      ).not.toBeInTheDocument();
    });
  });

  test("hides technical INAZ templates from the assignment dropdown", async () => {
    render(<PresenzeCollaboratoreDetailPage />);

    expect(
      await screen.findByText("Profilo GAIA e template orari"),
    ).toBeInTheDocument();
    const templateSelect = screen.getByLabelText("Template");
    expect(
      within(templateSelect).getByRole("option", { name: /OPE0714_1E3SAB/i }),
    ).toBeInTheDocument();
    expect(
      within(templateSelect).queryByRole("option", { name: /OP_5.3_12.3/i }),
    ).not.toBeInTheDocument();
  });

  test("preselects the suggested GAIA template for the collaborator", async () => {
    render(<PresenzeCollaboratoreDetailPage />);

    expect(
      await screen.findByText("Profilo GAIA e template orari"),
    ).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByLabelText("Template")).toHaveValue("10");
    });
  });

  test("renders compact expandable cartellino sections with relevant indicators", async () => {
    mocks.getPresenzeCollaboratorCalendar.mockResolvedValue({
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
        contract_kind: "operaio",
        operai_group: null,
        standard_daily_minutes: 420,
        is_active: true,
        last_seen_at: "2026-06-04T09:00:00Z",
        created_at: "2026-06-04T09:00:00Z",
        updated_at: "2026-06-04T09:00:00Z",
      },
      items: [
        {
          id: "rec-1",
          collaborator_id: "collab-1",
          owner_user_id: 1,
          application_user_id: null,
          work_date: "2026-06-08",
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
          request_description: "Richiesta - Permesso ordinario",
          request_status: "Approvata",
          request_authorized_by: null,
          resolved_absence_cause: "permesso",
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
          stato: "Validata",
          evidenze: null,
          raw_weekday: "Domenica",
          detail_title: null,
          detail_status: "Validata",
          detail_programmed_schedule: "OPE0714",
          detail_effective_schedule: null,
          detail_time_slots: "05:30-12:30",
          detail_schedule_type: "Operaio",
          detail_theoretical_hours: "7:00",
          detail_absence_hours: "0:00",
          detail_day_summary: {
            Attese: "7:00",
            Lavorate: "7:00",
          },
          detail_day_totals: {
            Ordinarie: "7:00",
          },
          detail_requests: [
            {
              Tipo: "Permesso ordinario",
              Stato: "Approvata",
            },
          ],
          detail_anomalies: [],
          detail_punch_rows: [],
          detail_text: null,
          detail_error:
            "Nessun collaboratore giornaliere associato al tuo utente GAIA.",
          special_day: false,
          holiday_kind: null,
          grants_recovery_day: false,
          recovery_day_credit: 0,
          uses_recovery_day: false,
          recovery_day_debit: 0,
          recovery_day_balance_delta: 0,
          raw_payload_json: null,
          source_job_id: null,
          created_at: "2026-06-04T09:00:00Z",
          updated_at: "2026-06-04T09:00:00Z",
          punches: [],
        },
      ],
    });

    render(<PresenzeCollaboratoreDetailPage />);

    expect(await screen.findByText("2026-06-08")).toBeInTheDocument();
    expect(screen.getByText("Riepilogo giornata (2 voci)")).toBeInTheDocument();
    expect(screen.getByText("Totali giornata (1 voce)")).toBeInTheDocument();
    expect(
      screen.getByText("Richieste (Permesso ordinario · 1 voce)"),
    ).toBeInTheDocument();
    const anomaliesSummary = screen.getByText("Anomalie (errore)");
    expect(anomaliesSummary).toBeInTheDocument();
    expect(anomaliesSummary.closest("details")).toHaveAttribute("open");
    expect(
      screen.getByText(
        "Nessun collaboratore giornaliere associato al tuo utente GAIA.",
      ),
    ).toBeInTheDocument();
  });

  test("infers GAIA_OPERAI when operai group is present even without a complete contract profile", async () => {
    mocks.listAllPresenzeCollaborators.mockResolvedValue([
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
        contract_kind: null,
        operai_group: "catasto_magazzino",
        standard_daily_minutes: 420,
        is_active: true,
        last_seen_at: "2026-06-04T09:00:00Z",
        created_at: "2026-06-04T09:00:00Z",
        updated_at: "2026-06-04T09:00:00Z",
      },
    ]);
    mocks.getPresenzeCollaboratorCalendar.mockResolvedValue({
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
        contract_kind: null,
        operai_group: "catasto_magazzino",
        standard_daily_minutes: 420,
        is_active: true,
        last_seen_at: "2026-06-04T09:00:00Z",
        created_at: "2026-06-04T09:00:00Z",
        updated_at: "2026-06-04T09:00:00Z",
      },
      items: [],
    });

    render(<PresenzeCollaboratoreDetailPage />);

    expect(
      await screen.findByText("Profilo GAIA e template orari"),
    ).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByLabelText("Profilo GAIA")).toHaveValue("GAIA_OPERAI");
    });
  });
});
