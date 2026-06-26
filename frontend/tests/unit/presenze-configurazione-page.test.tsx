import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import PresenzeConfigurazionePage from "@/app/presenze/configurazione/page";

const mocks = vi.hoisted(() => ({
  getStoredAccessToken: vi.fn(),
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
    mocks.listPresenzeScheduleTemplates.mockResolvedValue([]);
    mocks.getPresenzeScheduleBootstrapPreview.mockResolvedValue({
      presets: [],
      collaborator_suggestions: [],
      detected_collaborators_total: 0,
      collaborators_with_suggestion_total: 0,
      collaborators_without_assignment_total: 0,
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
