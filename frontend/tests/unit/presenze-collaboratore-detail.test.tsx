import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import PresenzeCollaboratoreDetailPage from "@/app/presenze/collaboratori/[id]/page";

const mocks = vi.hoisted(() => ({
  getStoredAccessToken: vi.fn(),
  getCurrentUser: vi.fn(),
  listAllApplicationUsers: vi.fn(),
  listAllPresenzeCollaborators: vi.fn(),
  getPresenzeCollaboratorCalendar: vi.fn(),
  getPresenzeCollaboratorSummary: vi.fn(),
  listPresenzeScheduleTemplates: vi.fn(),
  listPresenzeCollaboratorScheduleAssignments: vi.fn(),
  mapPresenzeCollaboratorApplicationUser: vi.fn(),
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
  getPresenzeCollaboratorSummary: mocks.getPresenzeCollaboratorSummary,
  listPresenzeScheduleTemplates: mocks.listPresenzeScheduleTemplates,
  listPresenzeCollaboratorScheduleAssignments: mocks.listPresenzeCollaboratorScheduleAssignments,
  mapPresenzeCollaboratorApplicationUser: mocks.mapPresenzeCollaboratorApplicationUser,
  updatePresenzeDailyRecord: mocks.updatePresenzeDailyRecord,
  createPresenzeCollaboratorScheduleAssignment: mocks.createPresenzeCollaboratorScheduleAssignment,
  deletePresenzeScheduleAssignment: mocks.deletePresenzeScheduleAssignment,
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
        standard_daily_minutes: 420,
        is_active: true,
        last_seen_at: "2026-06-04T09:00:00Z",
        created_at: "2026-06-04T09:00:00Z",
        updated_at: "2026-06-04T09:00:00Z",
      },
      items: [],
    });
    mocks.getPresenzeCollaboratorSummary.mockResolvedValue({ collaborator: { id: "collab-1" }, items: [] });
    mocks.listPresenzeScheduleTemplates.mockResolvedValue([]);
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
      standard_daily_minutes: 420,
      is_active: true,
      last_seen_at: "2026-06-04T09:00:00Z",
      created_at: "2026-06-04T09:00:00Z",
      updated_at: "2026-06-04T09:00:00Z",
    });
  });

  test("preselects suggested GAIA mapping and saves it", async () => {
    render(<PresenzeCollaboratoreDetailPage />);

    expect(await screen.findByText(/Suggerito: amadu.salvatore \(alta\)/i)).toBeInTheDocument();
    expect(screen.getByText("Profilo contrattuale")).toBeInTheDocument();
    expect(screen.getByText("Operaio")).toBeInTheDocument();
    expect(screen.getByText("Standard giornaliero")).toBeInTheDocument();
    expect(screen.getByText("7:00")).toBeInTheDocument();
    const select = screen.getAllByRole("combobox")[1];

    await waitFor(() => {
      expect(select).toHaveValue("6");
    });

    fireEvent.click(screen.getByText("Salva collegamento"));

    await waitFor(() => {
      expect(mocks.mapPresenzeCollaboratorApplicationUser).toHaveBeenCalledWith("token", "collab-1", 6);
    });

    expect(await screen.findByRole("status")).toHaveTextContent(/Mapping GAIA salvato correttamente/i);
  });
});
