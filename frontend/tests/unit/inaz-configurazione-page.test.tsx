import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import InazConfigurazionePage from "@/app/inaz/configurazione/page";

const mocks = vi.hoisted(() => ({
  getStoredAccessToken: vi.fn(),
  listInazScheduleTemplates: vi.fn(),
  getInazScheduleBootstrapPreview: vi.fn(),
  getInazBankHoursGuidanceConfig: vi.fn(),
  listInazBankHoursGuidanceConfigHistory: vi.fn(),
  updateInazBankHoursGuidanceConfig: vi.fn(),
  applyInazScheduleBootstrap: vi.fn(),
  createInazCollaboratorScheduleAssignment: vi.fn(),
  createInazScheduleRule: vi.fn(),
  createInazScheduleTemplate: vi.fn(),
  deleteInazScheduleRule: vi.fn(),
  deleteInazScheduleTemplate: vi.fn(),
}));

vi.mock("@/lib/auth", () => ({
  getStoredAccessToken: mocks.getStoredAccessToken,
}));

vi.mock("@/lib/api", () => ({
  applyInazScheduleBootstrap: mocks.applyInazScheduleBootstrap,
  createInazCollaboratorScheduleAssignment: mocks.createInazCollaboratorScheduleAssignment,
  createInazScheduleRule: mocks.createInazScheduleRule,
  createInazScheduleTemplate: mocks.createInazScheduleTemplate,
  deleteInazScheduleRule: mocks.deleteInazScheduleRule,
  deleteInazScheduleTemplate: mocks.deleteInazScheduleTemplate,
  getInazScheduleBootstrapPreview: mocks.getInazScheduleBootstrapPreview,
  getInazBankHoursGuidanceConfig: mocks.getInazBankHoursGuidanceConfig,
  listInazBankHoursGuidanceConfigHistory: mocks.listInazBankHoursGuidanceConfigHistory,
  listInazScheduleTemplates: mocks.listInazScheduleTemplates,
  updateInazBankHoursGuidanceConfig: mocks.updateInazBankHoursGuidanceConfig,
}));

vi.mock("@/components/app/protected-page", () => ({
  ProtectedPage: ({ children, title }: { children: React.ReactNode; title: string }) => (
    <div>
      <h1>{title}</h1>
      {children}
    </div>
  ),
}));

describe("Inaz configurazione page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.getStoredAccessToken.mockReturnValue("token");
    mocks.listInazScheduleTemplates.mockResolvedValue([]);
    mocks.getInazScheduleBootstrapPreview.mockResolvedValue({
      presets: [],
      collaborator_suggestions: [],
      detected_collaborators_total: 0,
      collaborators_with_suggestion_total: 0,
      collaborators_without_assignment_total: 0,
    });
    mocks.getInazBankHoursGuidanceConfig.mockResolvedValue({
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
    mocks.updateInazBankHoursGuidanceConfig.mockResolvedValue({
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
    mocks.listInazBankHoursGuidanceConfigHistory.mockResolvedValue([
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
    render(<InazConfigurazionePage />);

    expect(await screen.findByText("Policy banca ore")).toBeInTheDocument();
    expect(await screen.findByText("Storico modifiche")).toBeInTheDocument();
    fireEvent.click(screen.getByLabelText(/Consenti profilo derivato/i));
    fireEvent.click(screen.getByLabelText(/Straordinario notturno/i));
    fireEvent.change(screen.getByLabelText(/Soglia minima proposta/i), { target: { value: "90" } });
    fireEvent.click(screen.getByRole("button", { name: /Salva policy banca ore/i }));

    await waitFor(() => {
      expect(mocks.updateInazBankHoursGuidanceConfig).toHaveBeenCalledWith(
        "token",
        expect.objectContaining({
          allow_derived_profile: true,
          include_overtime_night: false,
          min_suggested_minutes: 90,
        }),
      );
    });
    expect(mocks.listInazBankHoursGuidanceConfigHistory).toHaveBeenCalled();
  });
});
