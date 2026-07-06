import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import PresenzeCollaboratoreDetailPage, {
  currentMonthBounds,
  firstDetailPreview,
  formatAbsenceCause,
  formatContractKind,
  formatDetailEntries,
  formatHours,
  formatMonthRangeLabel,
  formatOperaiGroup,
  formatRequestDescription,
  formatStandardDailyMinutes,
  inferGaiaProfileCode,
  isAssignableGaiaTemplate,
  monthBoundsFromDate,
  operaiGroupBadgeVariant,
  recoveryBadgeLabel,
  requestBadgeLabel,
  sectionSummaryLabel,
  shiftMonthBounds,
  templateDisplayTitle,
  uniqueTemplateInazCodes,
} from "@/app/presenze/collaboratori/[id]/page";

const navigationState = vi.hoisted(() => ({
  searchParams: "",
}));

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
  notifyPresenzeCollaboratorDetailUpdated: vi.fn(),
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

function getTemplateSelect(): HTMLSelectElement {
  const section = screen
    .getByText("Profilo GAIA e template orari")
    .closest("article");
  const field = section
    ? within(section).getAllByRole("combobox").at(-1)
    : null;
  if (!(field instanceof HTMLSelectElement)) {
    throw new Error("Template select non trovato");
  }
  return field;
}

vi.mock("@/lib/presenze-collaborator-mapping", async () => {
  const actual = await vi.importActual<
    typeof import("@/lib/presenze-collaborator-mapping")
  >("@/lib/presenze-collaborator-mapping");
  return {
    ...actual,
    notifyPresenzeCollaboratorDetailUpdated:
      mocks.notifyPresenzeCollaboratorDetailUpdated,
  };
});

vi.mock("next/navigation", () => ({
  useParams: () => ({ id: "collab-1" }),
  useSearchParams: () => new URLSearchParams(navigationState.searchParams),
}));

function createCollaborator(overrides: Record<string, unknown> = {}) {
  return {
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
    ...overrides,
  };
}

function createDailyRecord(overrides: Record<string, unknown> = {}) {
  return {
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
    raw_payload_json: null,
    source_job_id: null,
    created_at: "2026-06-04T09:00:00Z",
    updated_at: "2026-06-04T09:00:00Z",
    punches: [],
    ...overrides,
  };
}

describe("Presenze collaborator detail helpers", () => {
  test("formats date bounds and labels", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-07-06T10:00:00Z"));

    expect(currentMonthBounds()).toEqual({
      start: "2026-07-01",
      end: "2026-07-31",
    });
    expect(monthBoundsFromDate("2026-02-10")).toEqual({
      start: "2026-02-01",
      end: "2026-02-28",
    });
    expect(shiftMonthBounds("2026-01-15", -1)).toEqual({
      start: "2025-12-01",
      end: "2025-12-31",
    });
    expect(formatMonthRangeLabel("2026-07-01")).toMatch(/luglio 2026/i);
  });

  test("formats collaborator values and contract metadata", () => {
    expect(formatHours(null)).toBe("—");
    expect(formatHours(90)).toBe("1.50 h");
    expect(formatStandardDailyMinutes(null)).toBe("—");
    expect(formatStandardDailyMinutes(420)).toBe("7:00");
    expect(formatContractKind(undefined)).toBe("—");
    expect(formatContractKind("quadro")).toBe("Quadro");
    expect(formatContractKind("dirigente" as never)).toBe("dirigente");
    expect(formatOperaiGroup("agrario")).toBe("Agrario");
    expect(formatOperaiGroup("catasto_magazzino")).toBe("Catasto / magazzino");
    expect(formatOperaiGroup(null)).toBe("Non impostato");
    expect(operaiGroupBadgeVariant("agrario")).toBe("success");
    expect(operaiGroupBadgeVariant("catasto_magazzino")).toBe("info");
    expect(operaiGroupBadgeVariant(null)).toBe("neutral");
    expect(
      inferGaiaProfileCode(createCollaborator({ operai_group: "agrario" })),
    ).toBe("GAIA_OPERAI");
    expect(
      inferGaiaProfileCode(createCollaborator({ contract_kind: "impiegato" })),
    ).toBe("GAIA_IMPIEGATI");
    expect(
      inferGaiaProfileCode(createCollaborator({ contract_kind: null })),
    ).toBe("");
    expect(
      inferGaiaProfileCode(
        createCollaborator({ contract_kind: "dirigente" as never }),
      ),
    ).toBe("");
  });

  test("formats request and anomaly helper values", () => {
    expect(formatAbsenceCause(undefined)).toBe("—");
    expect(formatAbsenceCause("assenza_da_giustificare")).toBe(
      "Assenza da giustificare",
    );
    expect(formatAbsenceCause("permesso_speciale")).toBe("permesso speciale");
    expect(formatRequestDescription(undefined)).toBe("—");
    expect(formatRequestDescription("Richiesta - Permesso breve")).toBe(
      "Permesso breve",
    );
    expect(formatRequestDescription("Richiesta -   ")).toBe("Richiesta -   ");
    expect(formatRequestDescription("Permesso breve")).toBe("Permesso breve");
    expect(formatDetailEntries({ Uno: "1", Due: "2" })).toEqual([
      ["Uno", "1"],
      ["Due", "2"],
    ]);
    expect(firstDetailPreview([{ A: " " }, { B: "prima preview" }])).toBe(
      "prima preview",
    );
    expect(firstDetailPreview([{ A: " " }])).toBeNull();
    expect(sectionSummaryLabel("Richieste")).toBe("Richieste");
    expect(
      sectionSummaryLabel("Richieste", {
        count: 1,
        preview: "Permesso",
        status: "errore",
      }),
    ).toBe("Richieste (errore · Permesso · 1 voce)");
  });

  test("handles schedule templates and badges", () => {
    const assignmentTemplate = {
      id: 10,
      code: "OPE0714_1E3SAB",
      label: " Operai 07:00-14:00 ",
      company_code: "53",
      is_active: true,
      valid_from: null,
      valid_to: null,
      notes: null,
      created_at: "2026-06-04T09:00:00Z",
      updated_at: "2026-06-04T09:00:00Z",
      rules: [
        { ordinary_label: "OPE0714" },
        { ordinary_label: " OPE0714 " },
        { ordinary_label: "OSAB5.3_12.3" },
      ],
    };

    expect(uniqueTemplateInazCodes(assignmentTemplate as never)).toEqual([
      "OPE0714",
      "OSAB5.3_12.3",
    ]);
    expect(
      uniqueTemplateInazCodes({ ...assignmentTemplate, rules: undefined } as never),
    ).toEqual([]);
    expect(uniqueTemplateInazCodes(null)).toEqual([]);
    expect(templateDisplayTitle(assignmentTemplate as never)).toBe(
      "Operai 07:00-14:00",
    );
    expect(
      templateDisplayTitle({
        id: 15,
        code: "",
        label: " ",
      } as never),
    ).toBe("Template #15");
    expect(templateDisplayTitle(null)).toBe("Template non disponibile");
    expect(
      isAssignableGaiaTemplate({
        id: 1,
        code: " OP_5.3_12.3 ",
        label: "",
        company_code: "53",
        is_active: true,
        valid_from: null,
        valid_to: null,
        notes: null,
        created_at: "",
        updated_at: "",
        rules: [],
      }),
    ).toBe(false);
  });

  test("builds request and recovery badges from a daily record", () => {
    expect(
      requestBadgeLabel(
        createDailyRecord({ resolved_absence_cause: "ferie" }) as never,
      ),
    ).toBe("Ferie");
    expect(
      requestBadgeLabel(
        createDailyRecord({
          resolved_absence_cause: null,
          request_description: "Richiesta - Permesso ordinario",
        }) as never,
      ),
    ).toBe("Permesso ordinario");
    expect(requestBadgeLabel(createDailyRecord() as never)).toBeNull();
    expect(
      recoveryBadgeLabel(
        createDailyRecord({
          grants_recovery_day: true,
          recovery_day_credit: 1,
        }) as never,
      ),
    ).toBe("Recupero +1");
    expect(
      recoveryBadgeLabel(
        createDailyRecord({
          uses_recovery_day: true,
          recovery_day_debit: 1,
        }) as never,
      ),
    ).toBe("Recupero -1");
    expect(
      recoveryBadgeLabel(
        createDailyRecord({ holiday_kind: "ordinary" }) as never,
      ),
    ).toBe("Festivita ordinaria");
    expect(
      recoveryBadgeLabel(
        createDailyRecord({ holiday_kind: "working_override" }) as never,
      ),
    ).toBe("Override lavorativo");
    expect(recoveryBadgeLabel(createDailyRecord() as never)).toBeNull();
  });
});

describe("Presenze collaborator detail", () => {
  beforeEach(() => {
    vi.useRealTimers();
    vi.clearAllMocks();
    navigationState.searchParams = "";
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
          default_template_code: "OPE0714_1E3SAB",
          template_codes: [
            "OPE0714_1E3SAB",
            "OPE0736_STD",
            "OP_5.3_12.3",
            "OSAB5.3_12.3",
          ],
          assignable_template_codes: ["OPE0714_1E3SAB", "OPE0736_STD"],
          inherited_template_codes: ["OP_5.3_12.3", "OSAB5.3_12.3"],
          rule_summaries: ["Feriale 7h"],
          active: true,
        },
        {
          profile_code: "GAIA_IMPIEGATI",
          profile_label: "Profilo Impiegati",
          description: "Profilo impiegati",
          default_template_code: "IMP1_STD",
          template_codes: ["IMP1_STD", "IMP1_RIENTRO"],
          assignable_template_codes: ["IMP1_STD", "IMP1_RIENTRO"],
          inherited_template_codes: [],
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
    const templateSelect = getTemplateSelect();
    expect(
      within(templateSelect).getByRole("option", {
        name: /OPE0714_1E3SAB.*predefinito/i,
      }),
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
    expect(screen.getByText("Template guida del profilo")).toBeInTheDocument();
    expect(screen.getAllByText(/Predefinito/i).length).toBeGreaterThan(0);
    expect(
      screen.getAllByText(/OPE0714_1E3SAB · Operai 07:00-14:00 con 1° e 3° sabato/i)
        .length,
    ).toBeGreaterThan(0);
    expect(screen.getByText(/Varianti assegnabili/i)).toBeInTheDocument();
    expect(screen.getByText(/OPE0714_1E3SAB, OPE0736_STD/i)).toBeInTheDocument();
    expect(screen.getByText(/Ereditati da INAZ/i)).toBeInTheDocument();
    expect(screen.getByText(/OP_5.3_12.3, OSAB5.3_12.3/i)).toBeInTheDocument();
    await waitFor(() => {
      expect(getTemplateSelect()).toHaveValue("10");
    });
    expect(
      screen.getByText("Template predefinito del profilo GAIA selezionato."),
    ).toBeInTheDocument();
  });

  test("omits the suggested mapping when no GAIA user reaches the confidence threshold", async () => {
    mocks.listAllApplicationUsers.mockResolvedValue([
      {
        id: 99,
        username: "x",
        email: "x@example.local",
        full_name: "Utente scollegato",
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

    render(<PresenzeCollaboratoreDetailPage />);

    expect(await screen.findByText("Mapping GAIA -> Presenze")).toBeInTheDocument();
    expect(screen.queryByText(/Suggerito:/i)).not.toBeInTheDocument();
  });

  test("loads the summary tab, navigates months, and shows empty-state messages", async () => {
    mocks.getPresenzeCollaboratorSummary.mockResolvedValue({
      collaborator: { id: "collab-1" },
      items: [
        {
          id: "sum-1",
          collaborator_id: "collab-1",
          event_code: "FER",
          description: "Ferie residue",
          valid_from: "2026-06-01",
          valid_to: "2026-06-30",
          spettante_minutes: 480,
          fruito_minutes: 120,
          saldo_minutes: 360,
          raw_payload_json: null,
          source_job_id: null,
          created_at: "2026-06-04T09:00:00Z",
          updated_at: "2026-06-04T09:00:00Z",
        },
      ],
    });

    render(<PresenzeCollaboratoreDetailPage />);

    expect(await screen.findByText(/luglio 2026/i)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /precedente/i }));
    await waitFor(() => {
      expect(mocks.getPresenzeCollaboratorCalendar).toHaveBeenLastCalledWith(
        "token",
        "collab-1",
        "2026-06-01",
        "2026-06-30",
      );
    });
    fireEvent.click(screen.getByRole("button", { name: /successivo/i }));
    fireEvent.click(screen.getByRole("button", { name: /mese corrente/i }));
    fireEvent.click(screen.getByRole("button", { name: "Riepilogo eventi" }));

    expect(await screen.findByText("Ferie residue")).toBeInTheDocument();
    expect(screen.getByText(/Saldo 6.00 h/i)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Cartellino" }));
    expect(
      await screen.findByText("Nessuna giornaliera nel periodo selezionato."),
    ).toBeInTheDocument();
  });

  test("renders fallback states for partial day details and saves daily overrides", async () => {
    const updatedRecord = createDailyRecord({
      id: "rec-1",
      km_value: 18,
      trasferta_minutes: 30,
      trasferta_montano: true,
      reperibilita_unit: "days",
      reperibilita_quantity: 1,
      override_straordinario_minutes: 45,
      override_mpe_minutes: 15,
      manual_note: "Verificato",
      effective_extra_minutes: 60,
      grants_recovery_day: true,
      recovery_day_credit: 1,
      uses_recovery_day: true,
      recovery_day_debit: 1,
    });
    mocks.getPresenzeCollaboratorCalendar.mockResolvedValue({
      collaborator: createCollaborator(),
      items: [
        createDailyRecord({
          id: "rec-1",
          detail_day_summary: {},
          detail_day_totals: { Ordinarie: "7:00" },
          detail_requests: [],
          detail_anomalies: [{ Tipo: "Anomalia badge" }],
          special_day: true,
          holiday_kind: "working_override",
          grants_recovery_day: true,
          recovery_day_credit: 1,
          uses_recovery_day: true,
          recovery_day_debit: 1,
          punches: [
            { id: "p1", sequence: 1, entry_time: "05:30", exit_time: "12:30" },
          ],
          evidenze: "Timbratura corretta",
          effective_extra_minutes: 60,
        }),
      ],
    });
    mocks.updatePresenzeDailyRecord.mockResolvedValue(updatedRecord);

    render(<PresenzeCollaboratoreDetailPage />);

    expect(
      await screen.findByText("Totali giornata (1 voce)"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Anomalie (Anomalia badge · 1 voce)"),
    ).toBeInTheDocument();
    expect(screen.getByText("Timbratura 1: 05:30 / 12:30")).toBeInTheDocument();
    expect(
      screen.getByText("Evidenze: Timbratura corretta"),
    ).toBeInTheDocument();
    expect(screen.getByText("Giorno speciale")).toBeInTheDocument();
    expect(screen.getByText(/Recupero \+1/)).toBeInTheDocument();

    const kmInput = screen.getByLabelText("KM");
    fireEvent.change(kmInput, { target: { value: "18" } });
    fireEvent.change(screen.getByPlaceholderText("Minuti"), {
      target: { value: "30" },
    });
    fireEvent.click(screen.getByLabelText("Comune montano"));
    fireEvent.click(
      screen.getByLabelText("Segna reperibilita per l'intera giornata"),
    );
    fireEvent.change(screen.getByLabelText("Straordinario override"), {
      target: { value: "45" },
    });
    fireEvent.change(screen.getByLabelText("MPE override"), {
      target: { value: "15" },
    });
    fireEvent.change(screen.getAllByLabelText("Note").at(-1) as HTMLElement, {
      target: { value: "Verificato" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Salva rettifiche" }));

    await waitFor(() => {
      expect(mocks.updatePresenzeDailyRecord).toHaveBeenCalledWith(
        "token",
        "rec-1",
        {
          km_value: 18,
          trasferta_minutes: 30,
          trasferta_montano: true,
          reperibilita_unit: "days",
          reperibilita_quantity: 1,
          override_straordinario_minutes: 45,
          override_mpe_minutes: 15,
          manual_note: "Verificato",
        },
      );
    });
  });

  test("handles embedded notifications and mapping save edge cases", async () => {
    navigationState.searchParams = "embedded=1";
    mocks.listAllPresenzeCollaborators.mockResolvedValue([
      createCollaborator({ application_user_id: 6 }),
    ]);
    mocks.getPresenzeCollaboratorCalendar.mockResolvedValue({
      collaborator: createCollaborator({ application_user_id: 6 }),
      items: [],
    });
    mocks.mapPresenzeCollaboratorApplicationUser.mockResolvedValue(
      createCollaborator({ application_user_id: null }),
    );

    render(<PresenzeCollaboratoreDetailPage />);

    expect(
      await screen.findByText("Profilo GAIA e template orari"),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Salva collegamento" }));
    expect(await screen.findByRole("status")).toHaveTextContent(
      "Mapping già salvato.",
    );

    const mappingSection = screen
      .getByText("Mapping GAIA -> Presenze")
      .closest("article") as HTMLElement;
    fireEvent.change(within(mappingSection).getByRole("combobox"), {
      target: { value: "" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Salva collegamento" }));

    await waitFor(() => {
      expect(mocks.mapPresenzeCollaboratorApplicationUser).toHaveBeenCalledWith(
        "token",
        "collab-1",
        null,
      );
    });
    expect(await screen.findByRole("status")).toHaveTextContent(
      "Mapping GAIA rimosso correttamente.",
    );
    expect(mocks.notifyPresenzeCollaboratorDetailUpdated).toHaveBeenCalled();
  });

  test("shows mapping errors when the session expires or the API fails", async () => {
    render(<PresenzeCollaboratoreDetailPage />);

    expect(
      await screen.findByText("Mapping GAIA -> Presenze"),
    ).toBeInTheDocument();
    mocks.getStoredAccessToken.mockReturnValue(null);
    fireEvent.click(screen.getByRole("button", { name: "Salva collegamento" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Sessione scaduta. Effettua di nuovo l'accesso.",
    );

    mocks.getStoredAccessToken.mockReturnValue("token");
    mocks.mapPresenzeCollaboratorApplicationUser.mockRejectedValueOnce(
      new Error("Errore mapping"),
    );
    const mappingSelect = screen.getAllByRole("combobox").at(-1) as HTMLElement;
    fireEvent.change(mappingSelect, {
      target: { value: "7" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Salva collegamento" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Errore mapping",
    );
  });

  test("validates and handles errors in GAIA profile and assignment actions", async () => {
    render(<PresenzeCollaboratoreDetailPage />);

    expect(
      await screen.findByText("Profilo GAIA e template orari"),
    ).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Gruppo operai"), {
      target: { value: "" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Salva profilo GAIA" }));
    expect(
      await screen.findByText(/devi indicare il gruppo operaio/i),
    ).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Profilo GAIA"), {
      target: { value: "GAIA_IMPIEGATI" },
    });
    fireEvent.change(screen.getByPlaceholderText("385"), {
      target: { value: "385" },
    });
    mocks.updatePresenzeCollaboratorContractProfile.mockRejectedValueOnce(
      new Error("Errore profilo"),
    );
    fireEvent.click(screen.getByRole("button", { name: "Salva profilo GAIA" }));
    expect(await screen.findByText("Errore profilo")).toBeInTheDocument();

    mocks.createPresenzeCollaboratorScheduleAssignment.mockRejectedValueOnce(
      new Error("Errore creazione"),
    );
    fireEvent.change(getTemplateSelect(), {
      target: { value: "12" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Aggiungi" }));
    expect(await screen.findByText("Errore creazione")).toBeInTheDocument();
  });

  test("shows duplicate-assignment warning and recovers when profile templates change", async () => {
    mocks.listPresenzeCollaboratorScheduleAssignments.mockResolvedValue([
      {
        id: 1,
        collaborator_id: "collab-1",
        template_id: 10,
        valid_from: null,
        valid_to: null,
        notes: null,
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
      await screen.findByText("Profilo GAIA e template orari"),
    ).toBeInTheDocument();
    expect(getTemplateSelect()).toHaveValue("10");
    fireEvent.change(screen.getByLabelText("Profilo GAIA"), {
      target: { value: "GAIA_IMPIEGATI" },
    });
    await waitFor(() => {
      expect(getTemplateSelect()).toHaveValue("12");
    });
    fireEvent.change(screen.getByLabelText("Profilo GAIA"), {
      target: { value: "GAIA_OPERAI" },
    });
    await waitFor(() => {
      expect(getTemplateSelect()).toHaveValue("10");
    });
  });

  test("handles delete-assignment and daily-override failures", async () => {
    mocks.listPresenzeCollaboratorScheduleAssignments.mockResolvedValue([
      {
        id: 1,
        collaborator_id: "collab-1",
        template_id: 10,
        valid_from: null,
        valid_to: null,
        notes: null,
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
    mocks.getPresenzeCollaboratorCalendar.mockResolvedValue({
      collaborator: createCollaborator(),
      items: [createDailyRecord({ id: "rec-1" })],
    });
    mocks.deletePresenzeScheduleAssignment.mockRejectedValueOnce(
      new Error("Errore eliminazione"),
    );
    mocks.updatePresenzeDailyRecord.mockRejectedValueOnce(
      new Error("Errore rettifica"),
    );

    render(<PresenzeCollaboratoreDetailPage />);

    expect(
      await screen.findByText("Operai 07:00-14:00 con 1° e 3° sabato"),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Elimina" }));
    expect(await screen.findByText("Errore eliminazione")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Salva rettifiche" }));
    expect(await screen.findByText("Errore rettifica")).toBeInTheDocument();
  });

  test("covers embedded success paths for profile, assignment, daily override, and delete", async () => {
    navigationState.searchParams = "embedded=1";
    mocks.listPresenzeCollaboratorScheduleAssignments.mockResolvedValue([
      {
        id: 1,
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
      },
    ]);
    mocks.getPresenzeCollaboratorCalendar.mockResolvedValue({
      collaborator: createCollaborator(),
      items: [createDailyRecord({ id: "rec-1" })],
    });
    mocks.updatePresenzeDailyRecord.mockResolvedValue(createDailyRecord({ id: "rec-1" }));
    mocks.createPresenzeCollaboratorScheduleAssignment.mockResolvedValue({
      id: 2,
      collaborator_id: "collab-1",
      template_id: 12,
      valid_from: "2026-06-01",
      valid_to: "2026-06-30",
      notes: "Nuova assegnazione",
      created_at: "2026-06-04T09:00:00Z",
      updated_at: "2026-06-04T09:00:00Z",
      template: {
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
    });

    render(<PresenzeCollaboratoreDetailPage />);

    expect(await screen.findByText("Profilo GAIA e template orari")).toBeInTheDocument();
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
    expect(
      mocks.createPresenzeCollaboratorScheduleAssignment,
    ).not.toHaveBeenCalledWith(
      "token",
      "collab-1",
      expect.objectContaining({ template_id: 10 }),
    );

    fireEvent.change(screen.getByLabelText("Profilo GAIA"), {
      target: { value: "GAIA_IMPIEGATI" },
    });
    fireEvent.change(getTemplateSelect(), {
      target: { value: "12" },
    });
    fireEvent.change(screen.getByLabelText("Dal"), {
      target: { value: "2026-06-01" },
    });
    fireEvent.change(screen.getByLabelText("Al"), {
      target: { value: "2026-06-30" },
    });
    fireEvent.change(screen.getAllByLabelText("Note")[0], {
      target: { value: "Nuova assegnazione" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Aggiungi" }));

    await waitFor(() => {
      expect(
        mocks.createPresenzeCollaboratorScheduleAssignment,
      ).toHaveBeenCalledWith("token", "collab-1", {
        template_id: 12,
        valid_from: "2026-06-01",
        valid_to: "2026-06-30",
        notes: "Nuova assegnazione",
      });
    });
    expect(screen.getByLabelText("Dal")).toHaveValue("");
    expect(screen.getByLabelText("Al")).toHaveValue("");

    fireEvent.click(screen.getByRole("button", { name: "Salva rettifiche" }));
    await waitFor(() => {
      expect(mocks.updatePresenzeDailyRecord).toHaveBeenCalledWith(
        "token",
        "rec-1",
        expect.any(Object),
      );
    });

    fireEvent.click(screen.getAllByRole("button", { name: "Elimina" })[0]);
    await waitFor(() => {
      expect(mocks.deletePresenzeScheduleAssignment).toHaveBeenCalledWith(
        "token",
        2,
      );
    });
    expect(mocks.notifyPresenzeCollaboratorDetailUpdated).toHaveBeenCalled();
  });

  test("short-circuits assignment, delete, profile, and override actions without a token", async () => {
    mocks.getPresenzeCollaboratorCalendar.mockResolvedValue({
      collaborator: createCollaborator(),
      items: [createDailyRecord({ id: "rec-1" })],
    });
    mocks.listPresenzeCollaboratorScheduleAssignments.mockResolvedValue([
      {
        id: 1,
        collaborator_id: "collab-1",
        template_id: 10,
        valid_from: null,
        valid_to: null,
        notes: null,
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

    expect(await screen.findByText("Profilo GAIA e template orari")).toBeInTheDocument();
    mocks.getStoredAccessToken.mockReturnValue(null);
    fireEvent.click(screen.getByRole("button", { name: "Salva profilo GAIA" }));
    fireEvent.click(screen.getByRole("button", { name: "Salva rettifiche" }));
    fireEvent.click(screen.getByRole("button", { name: "Elimina" }));
    fireEvent.change(screen.getByLabelText("Profilo GAIA"), {
      target: { value: "GAIA_IMPIEGATI" },
    });
    fireEvent.change(getTemplateSelect(), {
      target: { value: "12" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Aggiungi" }));

    expect(mocks.updatePresenzeCollaboratorContractProfile).not.toHaveBeenCalled();
    expect(mocks.updatePresenzeDailyRecord).not.toHaveBeenCalled();
    expect(mocks.deletePresenzeScheduleAssignment).not.toHaveBeenCalled();
  });

  test("shows the loading placeholder when no token is available", () => {
    mocks.getStoredAccessToken.mockReturnValue(null);

    render(<PresenzeCollaboratoreDetailPage />);

    expect(
      screen.getByText("Caricamento dettaglio collaboratore..."),
    ).toBeInTheDocument();
    expect(
      screen.queryByText("Profilo GAIA e template orari"),
    ).not.toBeInTheDocument();
  });

  test("renders load failures", async () => {
    mocks.getCurrentUser.mockRejectedValueOnce(new Error("Errore caricamento"));
    render(<PresenzeCollaboratoreDetailPage />);
    expect(await screen.findByText("Errore caricamento")).toBeInTheDocument();
  });

  test("initializes from calendar fallback data and covers admin bootstrap fallbacks", async () => {
    mocks.listAllPresenzeCollaborators.mockResolvedValue([]);
    mocks.getPresenzeCollaboratorCalendar.mockResolvedValue({
      collaborator: createCollaborator({
        application_user_id: 7,
        company_label: null,
        company_code: null,
        birth_date: null,
        contract_kind: null,
        operai_group: null,
        standard_daily_minutes: null,
      }),
      items: [
        createDailyRecord({
          id: "rec-init",
          collaborator_id: "collab-1",
          ordinary_minutes: null,
          absence_minutes: null,
          straordinario_minutes: null,
          mpe_minutes: null,
          recovery_day_credit: null,
          recovery_day_debit: null,
          km_value: 12,
          trasferta_minutes: 25,
          reperibilita_unit: "days",
          reperibilita_quantity: 1,
          override_straordinario_minutes: 50,
          override_mpe_minutes: 30,
          manual_note: "nota init",
        }),
      ],
    });
    mocks.getPresenzeScheduleBootstrapPreview.mockResolvedValue({
      detected_collaborators_total: 1,
      collaborators_with_suggestion_total: 0,
      collaborators_without_assignment_total: 1,
      profiles: [],
      presets: [],
      collaborator_suggestions: [],
    });

    render(<PresenzeCollaboratoreDetailPage />);

    expect(await screen.findByText(/Matricola 1854 · Nascita n\/d/)).toBeInTheDocument();
    expect(screen.getAllByText("Non impostato").length).toBeGreaterThan(0);
    expect(screen.getAllByText("—").length).toBeGreaterThan(0);
    expect(screen.getByLabelText("Profilo GAIA")).toHaveValue("");
    expect(getTemplateSelect()).toHaveValue("10");
    expect(screen.getByLabelText("KM")).toHaveValue("12");
    expect(screen.getByPlaceholderText("Minuti")).toHaveValue("25");
    expect(screen.getByLabelText("Straordinario override")).toHaveValue("50");
    expect(screen.getByLabelText("MPE override")).toHaveValue("30");
    expect(
      (screen.getAllByLabelText("Note").at(-1) as HTMLInputElement).value,
    ).toBe("nota init");
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

  test("renders viewer fallbacks for empty anomalies and summary metadata", async () => {
    mocks.getCurrentUser.mockResolvedValue({
      id: 2,
      username: "viewer",
      email: "viewer@example.local",
      full_name: "Viewer",
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
      enabled_modules: ["presenze"],
    });
    mocks.getPresenzeCollaboratorCalendar.mockResolvedValue({
      collaborator: createCollaborator({ application_user_id: 6 }),
      items: [
        createDailyRecord({
          request_description: "Richiesta - Permesso ordinario",
          request_status: "Approvata",
          detail_requests: [{ Tipo: "Permesso ordinario" }],
        }),
      ],
    });
    mocks.getPresenzeCollaboratorSummary.mockResolvedValue({
      collaborator: { id: "collab-1" },
      items: [
        {
          id: "sum-1",
          collaborator_id: "collab-1",
          event_code: null,
          description: "Evento senza codice",
          valid_from: null,
          valid_to: null,
          spettante_minutes: 60,
          fruito_minutes: 0,
          saldo_minutes: 60,
          raw_payload_json: null,
          source_job_id: null,
          created_at: "2026-06-04T09:00:00Z",
          updated_at: "2026-06-04T09:00:00Z",
        },
      ],
    });

    render(<PresenzeCollaboratoreDetailPage />);

    expect(await screen.findByText("2026-06-08")).toBeInTheDocument();
    fireEvent.click(screen.getByText("Anomalie"));
    expect(screen.getByText("Nessuna anomalia.")).toBeInTheDocument();
    expect(
      screen.queryByText("Profilo GAIA e template orari"),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByText("Mapping GAIA -> Presenze"),
    ).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Riepilogo eventi" }));
    expect(await screen.findByText("Evento senza codice")).toBeInTheDocument();
    expect(screen.getByText(/Codice — · Validita — \/ —/)).toBeInTheDocument();
    expect(mocks.listAllApplicationUsers).not.toHaveBeenCalled();
    expect(mocks.listPresenzeScheduleTemplates).not.toHaveBeenCalled();
    expect(
      mocks.listPresenzeCollaboratorScheduleAssignments,
    ).not.toHaveBeenCalled();
    expect(mocks.getPresenzeScheduleBootstrapPreview).not.toHaveBeenCalled();
  });

  test("renders cartellino fallback values and summary empty state branches", async () => {
    mocks.getPresenzeCollaboratorCalendar.mockResolvedValue({
      collaborator: createCollaborator(),
      items: [
        createDailyRecord({
          id: "rec-fallback",
          schedule_code: null,
          stato: null,
          detail_programmed_schedule: null,
          detail_status: null,
          detail_time_slots: null,
          detail_schedule_type: null,
          detail_theoretical_hours: null,
          detail_absence_hours: null,
          teo_minutes: null,
          absence_minutes: null,
          request_description: "Richiesta - Permesso",
          request_status: null,
          resolved_absence_cause: null,
          punches: [{ id: "p-null", sequence: 1, entry_time: null, exit_time: null }],
          detail_day_summary: { Attese: "7:00" },
          detail_day_totals: {},
          detail_requests: [],
          detail_anomalies: [],
          detail_error: null,
        }),
      ],
    });
    mocks.getPresenzeCollaboratorSummary.mockResolvedValue({
      collaborator: { id: "collab-1" },
      items: [],
    });

    render(<PresenzeCollaboratoreDetailPage />);

    expect(await screen.findByText("2026-06-08")).toBeInTheDocument();
    expect(screen.getByText(/Orario — · Stato —/)).toBeInTheDocument();
    expect(screen.getByText(/Fasce:/).parentElement).toHaveTextContent("Fasce: —");
    expect(screen.getByText(/Tipo:/).parentElement).toHaveTextContent("Tipo: —");
    expect(screen.getByText(/Ore teoriche:/).parentElement).toHaveTextContent("Ore teoriche: —");
    expect(screen.getByText(/Ore assenza:/).parentElement).toHaveTextContent("Ore assenza: —");
    expect(screen.getByText("Timbratura 1: — / —")).toBeInTheDocument();
    expect(screen.getByText("Totali giornata")).toBeInTheDocument();
    fireEvent.click(screen.getByText("Riepilogo giornata (1 voce)"));
    expect(screen.getByText("Attese")).toBeInTheDocument();
    fireEvent.click(screen.getByText("Totali giornata"));
    expect(screen.getByText("Nessun totale disponibile.")).toBeInTheDocument();
    expect(screen.getByText("Richiesta:")).toBeInTheDocument();
    expect(screen.getByText("Stato:").parentElement).toHaveTextContent("Stato: —");
    fireEvent.click(screen.getByRole("button", { name: "Riepilogo eventi" }));
    expect(
      await screen.findByText("Nessun riepilogo eventi nel periodo selezionato."),
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
