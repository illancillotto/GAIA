import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import InazExportPage from "@/app/inaz/export/page";

const mocks = vi.hoisted(() => ({
  getStoredAccessToken: vi.fn(),
  listInazCollaborators: vi.fn(),
  listInazDailyRecords: vi.fn(),
  exportInazXlsm: vi.fn(),
}));

vi.mock("@/lib/auth", () => ({
  getStoredAccessToken: mocks.getStoredAccessToken,
}));

vi.mock("@/lib/api", () => ({
  listInazCollaborators: mocks.listInazCollaborators,
  listInazDailyRecords: mocks.listInazDailyRecords,
  exportInazXlsm: mocks.exportInazXlsm,
}));

vi.mock("@/components/app/protected-page", () => ({
  ProtectedPage: ({ children, title }: { children: React.ReactNode; title: string }) => (
    <div>
      <h1>{title}</h1>
      {children}
    </div>
  ),
}));

describe("Inaz export page", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  beforeEach(() => {
    mocks.getStoredAccessToken.mockReturnValue("token");
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
          last_seen_at: "2026-06-04T09:00:00Z",
          created_at: "2026-06-04T09:00:00Z",
          updated_at: "2026-06-04T09:00:00Z",
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
          trasferta_minutes: 180,
          trasferta_montano: false,
          reperibilita_unit: "hours",
          reperibilita_quantity: 4,
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
          holiday_kind: "ordinary",
          grants_recovery_day: false,
          recovery_day_credit: 0,
          uses_recovery_day: false,
          recovery_day_debit: 0,
          recovery_day_balance_delta: 0,
          raw_payload_json: {},
          source_job_id: null,
          created_at: "2026-06-04T09:00:00Z",
          updated_at: "2026-06-04T09:00:00Z",
          punches: [],
        },
      ],
      total: 1,
      page: 1,
      page_size: 200,
    });
    mocks.exportInazXlsm.mockResolvedValue(new Blob(["test"], { type: "application/vnd.ms-excel.sheet.macroEnabled.12" }));
    vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:test");
    vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => {});
  });

  test("shows trasferta and reperibilita diagnostics and triggers export", async () => {
    render(<InazExportPage />);

    await waitFor(() => expect(mocks.listInazCollaborators).toHaveBeenCalled());
    await waitFor(() => expect(mocks.listInazDailyRecords).toHaveBeenCalled());

    expect(screen.getByText("Giorni con trasferta")).toBeInTheDocument();
    expect(screen.getByText("3 ore totali esportabili")).toBeInTheDocument();
    expect(screen.getByText("Reperibilita strutturata")).toBeInTheDocument();
    expect(screen.getByText(/Il template XLSM legacy salva la reperibilita come flag/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Scarica XLSM" }));

    await waitFor(() =>
      expect(mocks.exportInazXlsm).toHaveBeenCalledWith(
        "token",
        expect.objectContaining({
          collaboratorIds: [],
          employeeKind: "AVVENTIZI",
        }),
      ),
    );
    expect(URL.createObjectURL).toHaveBeenCalled();
  });
});
