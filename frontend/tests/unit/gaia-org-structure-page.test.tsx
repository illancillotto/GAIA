import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import GaiaOrgStructurePage from "@/app/gaia/organigramma/page";

const mocks = vi.hoisted(() => ({
  getStoredAccessToken: vi.fn(),
  getCurrentUser: vi.fn(),
  listAllApplicationUsers: vi.fn(),
  getOrgStructureWorkspace: vi.fn(),
  bootstrapOrgStructureFromWhiteCompany: vi.fn(),
  upsertOrgStructureAssignment: vi.fn(),
  deleteOrgStructureAssignment: vi.fn(),
}));

vi.mock("@/lib/auth", () => ({
  getStoredAccessToken: mocks.getStoredAccessToken,
}));

vi.mock("@/lib/api", () => ({
  getCurrentUser: mocks.getCurrentUser,
  listAllApplicationUsers: mocks.listAllApplicationUsers,
  getOrgStructureWorkspace: mocks.getOrgStructureWorkspace,
  bootstrapOrgStructureFromWhiteCompany: mocks.bootstrapOrgStructureFromWhiteCompany,
  upsertOrgStructureAssignment: mocks.upsertOrgStructureAssignment,
  deleteOrgStructureAssignment: mocks.deleteOrgStructureAssignment,
}));

vi.mock("@/components/app/protected-page", () => ({
  ProtectedPage: ({ children, title }: { children: React.ReactNode; title: string }) => (
    <div>
      <h1>{title}</h1>
      {children}
    </div>
  ),
}));

describe("Gaia org structure page", () => {
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
      module_inaz: false,
      enabled_modules: ["accessi"],
    });
    mocks.listAllApplicationUsers.mockResolvedValue([
      {
        id: 1,
        username: "admin",
        email: "admin@example.local",
        full_name: "Admin GAIA",
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
        module_inaz: false,
        enabled_modules: ["accessi"],
        created_at: "2026-06-08T10:00:00Z",
        last_login_at: null,
        last_login_ip: null,
        login_count: 0,
        updated_at: "2026-06-08T10:00:00Z",
      },
      {
        id: 2,
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
        module_operazioni: true,
        module_riordino: false,
        module_ruolo: false,
        module_inaz: true,
        enabled_modules: ["accessi", "operazioni", "inaz"],
        created_at: "2026-06-08T10:00:00Z",
        last_login_at: null,
        last_login_ip: null,
        login_count: 0,
        updated_at: "2026-06-08T10:00:00Z",
      },
      {
        id: 3,
        username: "lbianchi",
        email: "lbianchi@example.local",
        full_name: "Laura Bianchi",
        office_location: null,
        phone_extension: null,
        role: "viewer",
        is_active: true,
        module_accessi: true,
        module_rete: false,
        module_inventario: false,
        module_catasto: false,
        module_utenze: false,
        module_operazioni: true,
        module_riordino: false,
        module_ruolo: false,
        module_inaz: true,
        enabled_modules: ["accessi", "operazioni", "inaz"],
        created_at: "2026-06-08T10:00:00Z",
        last_login_at: null,
        last_login_ip: null,
        login_count: 0,
        updated_at: "2026-06-08T10:00:00Z",
      },
    ]);
    mocks.getOrgStructureWorkspace.mockResolvedValue({
      items: [
        {
          id: "node-1",
          application_user_id: 2,
          manager_user_id: null,
          source_mode: "hybrid",
          title: "Caposettore",
          area_label: "Distretto Nord",
          notes: null,
          is_active: true,
          source_wc_role: "Caposettore",
          source_chart_summary: "Settore manutenzione",
          last_synced_from_source_at: "2026-06-08T10:00:00Z",
          created_at: "2026-06-08T10:00:00Z",
          updated_at: "2026-06-08T10:00:00Z",
          user: {
            id: 2,
            username: "mrossi",
            email: "mrossi@example.local",
            full_name: "Mario Rossi",
            role: "viewer",
            is_active: true,
          },
          manager: null,
          direct_reports_count: 0,
          descendants_count: 0,
          depth: 0,
        },
      ],
      suggestions: [
        {
          application_user_id: 3,
          wc_operator_id: "wc-3",
          username: "lbianchi",
          full_name: "Laura Bianchi",
          email: "lbianchi@example.local",
          role: "viewer",
          wc_role: "Operatore",
          chart_summary: "Settore manutenzione",
          already_published: false,
        },
      ],
      metrics: {
        total_users: 3,
        published_nodes: 1,
        root_nodes: 1,
        unassigned_users: 2,
        linked_whitecompany_users: 1,
      },
    });
    mocks.bootstrapOrgStructureFromWhiteCompany.mockResolvedValue({ created: 1, updated: 0, skipped: 0 });
    mocks.upsertOrgStructureAssignment.mockResolvedValue({
      id: "node-2",
      application_user_id: 3,
      manager_user_id: 2,
      source_mode: "manual",
      title: "Operatore settore",
      area_label: "Distretto Nord",
      notes: "Validazione giornaliere",
      is_active: true,
      source_wc_role: "Operatore",
      source_chart_summary: "Settore manutenzione",
      last_synced_from_source_at: "2026-06-08T10:00:00Z",
      created_at: "2026-06-08T10:00:00Z",
      updated_at: "2026-06-08T10:05:00Z",
      user: {
        id: 3,
        username: "lbianchi",
        email: "lbianchi@example.local",
        full_name: "Laura Bianchi",
        role: "viewer",
        is_active: true,
      },
      manager: {
        id: 2,
        username: "mrossi",
        email: "mrossi@example.local",
        full_name: "Mario Rossi",
        role: "viewer",
        is_active: true,
      },
      direct_reports_count: 0,
      descendants_count: 0,
      depth: 1,
    });
  });

  test("renders the org workspace and publishes a suggestion", async () => {
    render(<GaiaOrgStructurePage />);

    expect(await screen.findByText("Organigramma Inaz")).toBeInTheDocument();
    expect(screen.getByText("Mario Rossi")).toBeInTheDocument();
    expect(screen.getByText("Laura Bianchi")).toBeInTheDocument();

    fireEvent.click(screen.getByText("Laura Bianchi"));
    fireEvent.change(await screen.findByLabelText("Responsabile diretto"), { target: { value: "2" } });
    fireEvent.change(screen.getByLabelText("Titolo / ruolo operativo"), { target: { value: "Operatore settore" } });
    fireEvent.change(screen.getByLabelText("Area / perimetro"), { target: { value: "Distretto Nord" } });
    fireEvent.change(screen.getByLabelText("Note interne"), { target: { value: "Validazione giornaliere" } });
    fireEvent.click(screen.getByText("Pubblica nodo"));

    await waitFor(() => {
      expect(mocks.upsertOrgStructureAssignment).toHaveBeenCalledWith("token", 3, {
        manager_user_id: 2,
        title: "Operatore settore",
        area_label: "Distretto Nord",
        notes: "Validazione giornaliere",
        is_active: true,
      });
    });
  });
});
