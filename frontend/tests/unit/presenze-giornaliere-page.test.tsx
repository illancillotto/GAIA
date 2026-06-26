import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import PresenzeGiornalierePage from "@/app/presenze/giornaliere/page";

const baseDailyRecord = {
  id: "record-1",
  collaborator_id: "collab-1",
  owner_user_id: 77,
  application_user_id: null,
  work_date: "2026-05-16",
  schedule_code: "OPESAB",
  teo_minutes: 390,
  ordinary_minutes: 330,
  absence_minutes: 60,
  justified_minutes: 0,
  maggiorazione_minutes: 15,
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
  detail_day_summary: { "Ore Ordinarie": "05:30" },
  detail_day_totals: { "CARTELLINO Gruppo Ore Straordinario": "01:15" },
  detail_requests: [{ Descrizione: "Permesso ordinario" }],
  detail_anomalies: [{ "Anomalia giornata": "Ore mancanti" }],
  detail_text: null,
  detail_error: null,
  special_day: true,
  raw_payload_json: {},
  source_job_id: null,
  created_at: "2026-06-04T09:00:00Z",
  updated_at: "2026-06-04T09:00:00Z",
  punches: [
    {
      id: "p1",
      daily_record_id: "record-1",
      sequence: 1,
      entry_time: "06:55",
      exit_time: "12:30",
      terminal_label: "FENO-Fenoso",
      created_at: "2026-06-04T09:00:00Z",
    },
  ],
};

const mocks = vi.hoisted(() => ({
  getStoredAccessToken: vi.fn(),
  getCurrentUser: vi.fn(),
  getPresenzeAccessContext: vi.fn(),
  getPresenzeDailyRecord: vi.fn(),
  listAllPresenzeCollaborators: vi.fn(),
  listPresenzeDailyMatrixRecords: vi.fn(),
  updatePresenzeDailyRecord: vi.fn(),
}));

vi.mock("@/lib/auth", () => ({
  getStoredAccessToken: mocks.getStoredAccessToken,
}));

vi.mock("@/lib/api", () => ({
  getCurrentUser: mocks.getCurrentUser,
  getPresenzeAccessContext: mocks.getPresenzeAccessContext,
  getPresenzeDailyRecord: mocks.getPresenzeDailyRecord,
  listAllPresenzeCollaborators: mocks.listAllPresenzeCollaborators,
  listPresenzeDailyMatrixRecords: mocks.listPresenzeDailyMatrixRecords,
  updatePresenzeDailyRecord: mocks.updatePresenzeDailyRecord,
}));

vi.mock("@/components/app/protected-page", () => ({
  ProtectedPage: ({ children, title }: { children: React.ReactNode; title: string }) => (
    <div>
      <h1>{title}</h1>
      {children}
    </div>
  ),
}));

vi.mock("@/components/ui/badge", () => ({
  Badge: ({ children }: { children: React.ReactNode }) => <span>{children}</span>,
}));

vi.mock("@/components/table/data-table", () => ({
  DataTable: ({ data, onRowClick }: { data: Array<{ id: string; collaborator: string; workDate: string }>; onRowClick?: (row: { id: string }) => void }) => (
    <div>
      {data.map((row) => (
        <button key={row.id} type="button" onClick={() => onRowClick?.(row)}>
          {row.collaborator} {row.workDate}
        </button>
      ))}
    </div>
  ),
}));

describe("Presenze giornaliere workspace", () => {
  beforeEach(() => {
    mocks.getStoredAccessToken.mockReturnValue("token");
    mocks.getCurrentUser.mockResolvedValue({
      id: 12,
      username: "caposettore",
      email: "capo@example.local",
      full_name: "Capo Settore",
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
      enabled_modules: ["accessi", "presenze"],
    });
    mocks.getPresenzeAccessContext.mockResolvedValue({
      can_view_all_data: false,
      can_view_all_credentials: false,
      can_manage_supervisors: false,
      is_supervisor: true,
      assigned_collaborators_count: 1,
    });
    mocks.listAllPresenzeCollaborators.mockResolvedValue([
      {
        id: "collab-1",
        owner_user_id: 77,
        application_user_id: null,
        kint: "10159",
        kkint: "{demo}",
        employee_code: "1854",
        company_code: "53",
        company_label: "53 - CBO",
        name: "AMADU SALVATORE",
        birth_date: "1967-02-26",
        is_active: true,
        last_seen_at: "2026-06-04T09:00:00Z",
        created_at: "2026-06-04T09:00:00Z",
        updated_at: "2026-06-04T09:00:00Z",
      },
    ]);
    mocks.listPresenzeDailyMatrixRecords.mockResolvedValue({
      items: [baseDailyRecord],
      total: 1,
      page: 1,
      page_size: 5000,
    });
    mocks.getPresenzeDailyRecord.mockResolvedValue(baseDailyRecord);
    mocks.updatePresenzeDailyRecord.mockResolvedValue({
      id: "record-1",
      collaborator_id: "collab-1",
      owner_user_id: 77,
      application_user_id: null,
      work_date: "2026-05-16",
      schedule_code: "OPESAB",
      teo_minutes: 390,
      ordinary_minutes: 330,
      absence_minutes: 60,
      justified_minutes: 0,
      maggiorazione_minutes: 15,
      mpe_minutes: 45,
      straordinario_minutes: 75,
      km_value: 30,
      trasferta_minutes: null,
      trasferta_montano: false,
      reperibilita_unit: "days",
      reperibilita_quantity: 1,
      override_straordinario_minutes: 90,
      override_mpe_minutes: 30,
      manual_note: "Corretto dal capo settore",
      request_type: "Eventi",
      request_description: "Permesso ordinario",
      request_status: "RIC",
      request_authorized_by: "PODDA FABRIZIO",
      resolved_absence_cause: "permesso",
      validation_status: "validated",
      validated_by_user_id: 12,
      validated_at: "2026-06-04T09:05:00Z",
      validation_note: "Verificata dal capo settore",
      effective_straordinario_minutes: 90,
          effective_mpe_minutes: 30,
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
      detail_day_summary: { "Ore Ordinarie": "05:30" },
      detail_day_totals: { "CARTELLINO Gruppo Ore Straordinario": "01:30" },
      detail_requests: [{ Descrizione: "Permesso ordinario" }],
      detail_anomalies: [{ "Anomalia giornata": "Ore mancanti" }],
      detail_text: null,
      detail_error: null,
      special_day: true,
      raw_payload_json: {},
      source_job_id: null,
      created_at: "2026-06-04T09:00:00Z",
      updated_at: "2026-06-04T09:05:00Z",
      punches: [
        {
          id: "p1",
          daily_record_id: "record-1",
          sequence: 1,
          entry_time: "06:55",
          exit_time: "12:30",
          terminal_label: "FENO-Fenoso",
          created_at: "2026-06-04T09:00:00Z",
        },
      ],
    });
  });

  test("renders the monthly matrix, opens the day modal and lets a supervisor validate only", async () => {
    render(<PresenzeGiornalierePage />);

    expect(await screen.findByText("Giornaliere")).toBeInTheDocument();

    // Sposta la vista sul mese del record mockato (maggio 2026).
    fireEvent.change(await screen.findByLabelText("Mese operativo"), { target: { value: "2026-05" } });

    // Il collaboratore compare in verticale nella matrice.
    expect(await screen.findByText("AMADU SALVATORE")).toBeInTheDocument();

    // La cella del giorno apre la modale operativa.
    fireEvent.click(await screen.findByTitle("2026-05-16 · Giornata anomala"));
    expect(await screen.findByLabelText("Giorno precedente")).toBeDisabled();
    expect(screen.getByLabelText("Giorno successivo")).toBeDisabled();
    expect(screen.getByText("Causale rilevata")).toBeInTheDocument();
    expect(screen.getByText("Permesso ordinario")).toBeInTheDocument();
    expect(screen.getByText("PODDA FABRIZIO")).toBeInTheDocument();
    expect(screen.getByText("Timbrature")).toBeInTheDocument();
    expect(screen.getByText("Timbratura 1")).toBeInTheDocument();
    expect(screen.getByText("06:55")).toBeInTheDocument();
    expect(screen.getByText("12:30")).toBeInTheDocument();
    expect(screen.getByText("Terminale: Fenoso")).toBeInTheDocument();
    expect(screen.getByText("I capisettore possono validare la giornata, ma non modificare KM e rettifiche operative.")).toBeInTheDocument();

    expect(screen.getByLabelText("Chilometri auto")).toBeDisabled();
    expect(screen.getByLabelText("Reperibilita giornaliera")).toBeDisabled();
    expect(screen.getByLabelText("Straordinario override")).toBeDisabled();
    expect(screen.getByLabelText("Maggior presenza override")).toBeDisabled();
    expect(screen.getByLabelText("Nota operativa")).toBeDisabled();
    expect(screen.getByText("Salva rettifiche")).toBeDisabled();

    fireEvent.change(screen.getByLabelText("Nota validazione"), { target: { value: "Verificata dal capo settore" } });
    fireEvent.click(screen.getByText("Valida giornaliera"));

    await waitFor(() => {
      expect(mocks.updatePresenzeDailyRecord).toHaveBeenCalledWith("token", "record-1", {
        validation_status: "validated",
        validation_note: "Verificata dal capo settore",
      });
    });

    expect(await screen.findByText("Giornata 2026-05-16 validata.")).toBeInTheDocument();
  });

  test("allows users with full access to save operational overrides", async () => {
    mocks.getCurrentUser.mockResolvedValue({
      id: 1,
      username: "hr_manager",
      email: "hr@example.local",
      full_name: "HR Manager",
      office_location: null,
      phone_extension: null,
      role: "hr_manager",
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
    mocks.getPresenzeAccessContext.mockResolvedValue({
      can_view_all_data: true,
      can_view_all_credentials: false,
      can_manage_supervisors: false,
      is_supervisor: false,
      assigned_collaborators_count: 0,
    });
    mocks.listPresenzeDailyMatrixRecords.mockResolvedValue({
      items: [{ ...baseDailyRecord, owner_user_id: 1 }],
      total: 1,
      page: 1,
      page_size: 5000,
    });

    render(<PresenzeGiornalierePage />);

    fireEvent.change(await screen.findByLabelText("Mese operativo"), { target: { value: "2026-05" } });
    fireEvent.click(await screen.findByTitle("2026-05-16 · Giornata anomala"));

    fireEvent.change(await screen.findByLabelText("Chilometri auto"), { target: { value: "30" } });
    fireEvent.click(screen.getByLabelText("Reperibilita giornaliera"));
    fireEvent.change(screen.getByLabelText("Straordinario override"), { target: { value: "01:30" } });
    fireEvent.change(screen.getByLabelText("Maggior presenza override"), { target: { value: "00:30" } });
    fireEvent.change(screen.getByLabelText("Nota operativa"), { target: { value: "Corretto HR" } });
    fireEvent.click(screen.getByText("Salva rettifiche"));

    await waitFor(() => {
      expect(mocks.updatePresenzeDailyRecord).toHaveBeenCalledWith("token", "record-1", {
        km_value: 30,
        trasferta_minutes: null,
        trasferta_montano: false,
        reperibilita_unit: "days",
        reperibilita_quantity: 1,
        override_straordinario_minutes: 90,
        override_mpe_minutes: 30,
        manual_note: "Corretto HR",
        validation_note: null,
      });
    });
  });

  test("opens the collaborator detail modal from the matrix", async () => {
    render(<PresenzeGiornalierePage />);

    expect(await screen.findByText("Giornaliere")).toBeInTheDocument();
    fireEvent.change(await screen.findByLabelText("Mese operativo"), { target: { value: "2026-05" } });

    fireEvent.click(await screen.findByRole("button", { name: "AMADU SALVATORE" }));

    // La modal mostra la scheda sintetica del collaboratore e l'elenco giornate.
    expect(await screen.findByText("Apri scheda completa")).toBeInTheDocument();
    expect(screen.getByText("2026-05-16")).toBeInTheDocument();
  });
});
