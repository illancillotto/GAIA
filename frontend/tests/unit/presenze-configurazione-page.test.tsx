import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import PresenzeConfigurazionePage from "@/app/presenze/configurazione/page";

const mocks = vi.hoisted(() => ({
  getStoredAccessToken: vi.fn(),
  listAllPresenzeCollaborators: vi.fn(),
  listPresenzeScheduleTemplates: vi.fn(),
  getPresenzeScheduleBootstrapPreview: vi.fn(),
  getPresenzeBankHoursGuidanceConfig: vi.fn(),
  listPresenzeBankHoursGuidanceConfigHistory: vi.fn(),
  updatePresenzeBankHoursGuidanceConfig: vi.fn(),
  applyPresenzeScheduleBootstrap: vi.fn(),
  createPresenzeCollaboratorScheduleAssignment: vi.fn(),
  createPresenzeScheduleRule: vi.fn(),
  createPresenzeScheduleTemplate: vi.fn(),
  deletePresenzeScheduleRule: vi.fn(),
  deletePresenzeScheduleTemplate: vi.fn(),
}));

vi.mock("@/lib/auth", () => ({
  getStoredAccessToken: mocks.getStoredAccessToken,
}));

vi.mock("@/lib/api", () => ({
  applyPresenzeScheduleBootstrap: mocks.applyPresenzeScheduleBootstrap,
  createPresenzeCollaboratorScheduleAssignment: mocks.createPresenzeCollaboratorScheduleAssignment,
  createPresenzeScheduleRule: mocks.createPresenzeScheduleRule,
  createPresenzeScheduleTemplate: mocks.createPresenzeScheduleTemplate,
  deletePresenzeScheduleRule: mocks.deletePresenzeScheduleRule,
  deletePresenzeScheduleTemplate: mocks.deletePresenzeScheduleTemplate,
  getPresenzeScheduleBootstrapPreview: mocks.getPresenzeScheduleBootstrapPreview,
  getPresenzeBankHoursGuidanceConfig: mocks.getPresenzeBankHoursGuidanceConfig,
  listAllPresenzeCollaborators: mocks.listAllPresenzeCollaborators,
  listPresenzeBankHoursGuidanceConfigHistory: mocks.listPresenzeBankHoursGuidanceConfigHistory,
  listPresenzeScheduleTemplates: mocks.listPresenzeScheduleTemplates,
  updatePresenzeBankHoursGuidanceConfig: mocks.updatePresenzeBankHoursGuidanceConfig,
}));

vi.mock("@/components/app/protected-page", () => ({
  ProtectedPage: ({ children, title }: { children: React.ReactNode; title: string }) => (
    <div>
      <h1>{title}</h1>
      {children}
    </div>
  ),
}));

describe("Presenze configurazione page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.getStoredAccessToken.mockReturnValue("token");
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
        last_seen_at: "2026-07-04T10:00:00Z",
        created_at: "2026-07-04T10:00:00Z",
        updated_at: "2026-07-04T10:00:00Z",
      },
      {
        id: "collab-2",
        owner_user_id: 1,
        application_user_id: null,
        kint: "10160",
        kkint: "{demo}",
        employee_code: "1855",
        company_code: "53",
        company_label: "53 - CBO",
        name: "OPERAIO LEGACY",
        birth_date: null,
        contract_kind: null,
        operai_group: null,
        standard_daily_minutes: null,
        is_active: true,
        last_seen_at: "2026-07-04T10:00:00Z",
        created_at: "2026-07-04T10:00:00Z",
        updated_at: "2026-07-04T10:00:00Z",
      },
      {
        id: "collab-3",
        owner_user_id: 1,
        application_user_id: null,
        kint: "10161",
        kkint: "{demo}",
        employee_code: "1016",
        company_code: "53",
        company_label: "53 - CBO",
        name: "TRONU GIAN FRANCO",
        birth_date: null,
        contract_kind: "impiegato",
        operai_group: null,
        standard_daily_minutes: null,
        is_active: true,
        last_seen_at: "2026-07-04T10:00:00Z",
        created_at: "2026-07-04T10:00:00Z",
        updated_at: "2026-07-04T10:00:00Z",
      },
    ]);
    mocks.listPresenzeScheduleTemplates.mockResolvedValue([
      {
        id: 1,
        code: "OP_5.3_12.3",
        label: "Operai 05:30-12:30",
        company_code: "53",
        is_active: true,
        valid_from: null,
        valid_to: null,
        notes: "Template feriale",
        created_at: "2026-07-04T10:00:00Z",
        updated_at: "2026-07-04T10:00:00Z",
        rules: [
          {
            id: 11,
            template_id: 1,
            label: "Lun 05:30-12:30",
            weekday: 0,
            recurrence_kind: "weekly",
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
            ordinary_label: "OP_5.3_12.3",
            sort_order: 0,
            created_at: "2026-07-04T10:00:00Z",
            updated_at: "2026-07-04T10:00:00Z",
          },
        ],
      },
      {
        id: 2,
        code: "OSAB5.3_12.3",
        label: "Operai sabato 05:30-12:30",
        company_code: "53",
        is_active: true,
        valid_from: null,
        valid_to: null,
        notes: "Template senza regole rigide del sabato",
        created_at: "2026-07-04T10:00:00Z",
        updated_at: "2026-07-04T10:00:00Z",
        rules: [],
      },
    ]);
    mocks.getPresenzeScheduleBootstrapPreview.mockResolvedValue({
      profiles: [
        {
          profile_code: "operai_gaia",
          profile_label: "Profilo Operai",
          description: "Controllo rigido delle ore effettive con assegnazione flessibile del turno INAZ.",
          template_codes: ["OPE0714_1E3SAB", "OP_5.3_12.3", "OSAB5.3_12.3"],
          rule_summaries: ["Feriale 7h", "Agrario sabato 6h30", "Catasto/magazzino sabato 6h"],
          active: true,
        },
        {
          profile_code: "impiegati_gaia",
          profile_label: "Profilo Impiegati",
          description: "Profilo gestionale per impiegati con orari INAZ flessibili.",
          template_codes: ["IMP1_STD", "IMP1_RIENTRO"],
          rule_summaries: ["Flessibile IMP1", "Rientro lunedi pomeriggio"],
          active: false,
        },
      ],
      presets: [],
      collaborator_suggestions: [
        {
          collaborator_id: "collab-1",
          employee_code: "1854",
          collaborator_name: "AMADU SALVATORE",
          company_code: "53",
          dominant_schedule_code: "OP_5.3_12.3",
          schedule_codes: ["OP_5.3_12.3"],
          assigned_template_code: null,
          suggested_template_code: "OP_5.3_12.3",
          suggested_template_label: "Operai 05:30-12:30",
          suggestion_confidence: "high",
          suggestion_reason: "Compatibilita alta sui codici osservati",
          already_assigned: false,
          configuration_status: "unassigned",
          configuration_notes: ["Nessun template orario assegnato."],
        },
        {
          collaborator_id: "collab-2",
          employee_code: "1855",
          collaborator_name: "OPERAIO LEGACY",
          company_code: "53",
          dominant_schedule_code: "OP_5.3_12.3",
          schedule_codes: ["OP_5.3_12.3"],
          assigned_template_code: "OP_5.3_12.3",
          suggested_template_code: "OP_5.3_12.3",
          suggested_template_label: "Operai 05:30-12:30",
          suggestion_confidence: "high",
          suggestion_reason: "Compatibilita alta sui codici osservati",
          already_assigned: true,
          configuration_status: "legacy_review",
          configuration_notes: [
            "Profilo contratto non impostato come operaio.",
            "Gruppo operaio mancante: serve distinguere agrario da catasto/magazzino.",
          ],
        },
        {
          collaborator_id: "collab-3",
          employee_code: "1016",
          collaborator_name: "TRONU GIAN FRANCO",
          company_code: "53",
          dominant_schedule_code: "IMP1",
          schedule_codes: ["IMP1", "RIENTRO IMP"],
          assigned_template_code: null,
          suggested_template_code: "IMP1_RIENTRO",
          suggested_template_label: "Impiegati con rientro",
          suggestion_confidence: "high",
          suggestion_reason: "Compatibilita alta sui codici osservati",
          already_assigned: true,
          configuration_status: "unassigned",
          configuration_notes: [],
        },
      ],
      detected_collaborators_total: 3,
      collaborators_with_suggestion_total: 3,
      collaborators_without_assignment_total: 1,
    });
    mocks.getPresenzeBankHoursGuidanceConfig.mockResolvedValue({
      allow_derived_profile: false,
      include_overtime_day: true,
      include_overtime_night: true,
      include_overtime_festive: true,
      include_overtime_festive_night: true,
      min_suggested_minutes: 60,
      updated_at: null,
      updated_by_user_id: null,
      updated_by_label: null,
    });
    mocks.updatePresenzeBankHoursGuidanceConfig.mockResolvedValue({
      allow_derived_profile: true,
      include_overtime_day: true,
      include_overtime_night: false,
      include_overtime_festive: true,
      include_overtime_festive_night: true,
      min_suggested_minutes: 90,
      updated_at: "2026-06-24T19:10:00Z",
      updated_by_user_id: 1,
      updated_by_label: "bank_hours_guidance_config_admin",
    });
    mocks.createPresenzeCollaboratorScheduleAssignment.mockResolvedValue({
      id: 1,
      collaborator_id: "collab-1",
      template_id: 1,
      valid_from: null,
      valid_to: null,
      notes: "Assegnazione guidata",
      created_at: "2026-07-04T10:00:00Z",
      updated_at: "2026-07-04T10:00:00Z",
      template: null,
    });
    mocks.applyPresenzeScheduleBootstrap.mockResolvedValue({
      created_templates: 1,
      created_assignments: 1,
      skipped_existing_templates: 2,
      skipped_existing_assignments: 3,
      template_codes: ["OPE0714_1E3SAB"],
      assigned_employee_codes: ["1854"],
    });
    mocks.listPresenzeBankHoursGuidanceConfigHistory.mockResolvedValue([
      {
        id: 1,
        allow_derived_profile: true,
        include_overtime_day: true,
        include_overtime_night: false,
        include_overtime_festive: true,
        include_overtime_festive_night: true,
        min_suggested_minutes: 90,
        changed_at: "2026-06-24T19:10:00Z",
        changed_by_user_id: 1,
        changed_by_label: "bank_hours_guidance_config_admin",
      },
    ]);
  });

  test("loads and updates bank hours guidance policy", async () => {
    render(<PresenzeConfigurazionePage />);

    expect(await screen.findByText("Policy banca ore")).toBeInTheDocument();
    expect(await screen.findByText("Template presenti nel sistema")).toBeInTheDocument();
    expect(screen.getByText("Template GAIA")).toBeInTheDocument();
    expect(screen.getByText("operai_gaia · Profilo Operai")).toBeInTheDocument();
    expect(screen.getByText("impiegati_gaia · Profilo Impiegati")).toBeInTheDocument();
    expect(screen.getAllByText((_, element) => element?.textContent?.includes("Template INAZ collegati: OPE0714_1E3SAB") ?? false).length).toBeGreaterThan(0);
    expect(screen.getAllByText((_, element) => element?.textContent?.includes("Template INAZ collegati: IMP1_STD") ?? false).length).toBeGreaterThan(0);
    expect(screen.getByText("Template ereditati da INAZ")).toBeInTheDocument();
    expect(screen.getAllByText("Apri").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Dettagli").length).toBeGreaterThan(0);
    expect(await screen.findAllByText("Agrario")).not.toHaveLength(0);
    expect(screen.getAllByText("OP_5.3_12.3 · Operai 05:30-12:30").length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Periodo 01\/06-30\/09/).length).toBeGreaterThan(0);
    expect(screen.getAllByText("OSAB5.3_12.3 · Operai sabato 05:30-12:30").length).toBeGreaterThan(0);
    expect(screen.getByText("Collaboratori")).toBeInTheDocument();
    expect(screen.queryByText("Collaboratori da completare")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Operai GAIA/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Impiegati GAIA/i })).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText(/Cerca collaboratore o codice orario/i), { target: { value: "Tronu" } });
    expect(screen.getByText(/TRONU GIAN FRANCO/)).toBeInTheDocument();
    expect(screen.queryByText(/OPERAIO LEGACY/)).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText(/Cerca collaboratore o codice orario/i), { target: { value: "" } });
    expect(screen.getAllByText("Da impostare").length).toBeGreaterThan(0);
    expect(screen.getByText(/OPERAIO LEGACY/)).toBeInTheDocument();
    expect(screen.getByText(/Gruppo operaio mancante/)).toBeInTheDocument();
    expect(screen.getByText(/TRONU GIAN FRANCO/)).toBeInTheDocument();
    expect(screen.getByText((_, element) => element?.textContent === "Template assegnato: IMP1_RIENTRO · risolto da proposta corrente")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Rivedi configurazione automatica/i }));
    expect(screen.getByText("Conferma configurazione automatica")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Conferma e configura/i }));
    await waitFor(() => {
      expect(mocks.applyPresenzeScheduleBootstrap).toHaveBeenCalledWith(
        "token",
        expect.objectContaining({
          create_missing_templates: true,
          assign_unassigned_collaborators: true,
        }),
      );
    });
    expect(await screen.findByText("Risultato configurazione automatica")).toBeInTheDocument();
    expect(screen.getByText("OPE0714_1E3SAB")).toBeInTheDocument();
    expect(screen.getByText("1854")).toBeInTheDocument();
    expect(screen.getByText("Template senza regole orarie fisse: il comportamento operativo viene completato da configurazioni applicative dedicate.")).toBeInTheDocument();
    expect(await screen.findByText("Storico modifiche")).toBeInTheDocument();
    fireEvent.click(screen.getByLabelText(/Consenti profilo derivato/i));
    fireEvent.click(screen.getByLabelText(/Straordinario notturno/i));
    fireEvent.change(screen.getByLabelText(/Soglia minima proposta/i), { target: { value: "90" } });
    fireEvent.click(screen.getByRole("button", { name: /Salva policy banca ore/i }));

    await waitFor(() => {
      expect(mocks.updatePresenzeBankHoursGuidanceConfig).toHaveBeenCalledWith(
        "token",
        expect.objectContaining({
          allow_derived_profile: true,
          include_overtime_night: false,
          min_suggested_minutes: 90,
        }),
      );
    });
    expect(mocks.listPresenzeBankHoursGuidanceConfigHistory).toHaveBeenCalled();
  });
});
