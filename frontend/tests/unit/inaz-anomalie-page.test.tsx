import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import InazAnomaliePage from "@/app/inaz/anomalie/page";
import { currentMonthValue, monthLabel, previousMonthValue } from "@/lib/inaz-anomaly-months";

const mocks = vi.hoisted(() => ({
  getStoredAccessToken: vi.fn(),
  getCurrentUser: vi.fn(),
  getInazDailyRecord: vi.fn(),
  listInazCollaborators: vi.fn(),
  listInazDailyRecords: vi.fn(),
  updateInazDailyRecord: vi.fn(),
}));

vi.mock("@/lib/auth", () => ({
  getStoredAccessToken: mocks.getStoredAccessToken,
}));

vi.mock("@/lib/api", () => ({
  getCurrentUser: mocks.getCurrentUser,
  getInazDailyRecord: mocks.getInazDailyRecord,
  listInazCollaborators: mocks.listInazCollaborators,
  listInazDailyRecords: mocks.listInazDailyRecords,
  updateInazDailyRecord: mocks.updateInazDailyRecord,
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
  DataTable: ({ data }: { data: Array<{ collaborator: string; workDate: string }> }) => (
    <div data-testid="anomalie-table">
      {data.map((row) => (
        <p key={`${row.workDate}-${row.collaborator}`}>
          {row.collaborator} {row.workDate}
        </p>
      ))}
    </div>
  ),
}));

function emptyMonthResponse() {
  return { items: [], total: 0, page: 1, page_size: 200 };
}

function anomalyMonthResponse(workDate: string) {
  return {
    items: [
      {
        id: `record-${workDate}`,
        collaborator_id: "collab-1",
        owner_user_id: 1,
        application_user_id: null,
        work_date: workDate,
        schedule_code: "OPESAB",
        teo_minutes: 390,
        ordinary_minutes: 330,
        absence_minutes: 60,
        justified_minutes: 0,
        maggiorazione_minutes: 0,
        mpe_minutes: 0,
        straordinario_minutes: 0,
        km_value: null,
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
        stato: "Giornata anomala",
        evidenze: "Ore mancanti",
        raw_weekday: "L",
        detail_title: null,
        detail_status: "Giornata anomala",
        detail_programmed_schedule: "OPESAB",
        detail_effective_schedule: null,
        detail_time_slots: "07:00 - 13:30",
        detail_schedule_type: null,
        detail_theoretical_hours: null,
        detail_absence_hours: null,
        detail_day_summary: {},
        detail_day_totals: {},
        detail_requests: [],
        detail_anomalies: [{ "Anomalia giornata": "Ore mancanti" }],
        detail_text: null,
        detail_error: null,
        special_day: false,
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
  };
}

describe("Inaz anomalie page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
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
      module_inaz: true,
      enabled_modules: ["inaz"],
    });
    mocks.getInazDailyRecord.mockImplementation(async (_token: string, recordId: string) => {
      const date = recordId.replace("record-", "");
      return anomalyMonthResponse(date).items[0];
    });
    mocks.listInazCollaborators.mockResolvedValue({
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
          birth_date: null,
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
  });

  test("falls back to previous month when current month has no anomalies", async () => {
    const currentMonth = currentMonthValue();
    const previousMonth = previousMonthValue(currentMonth);

    mocks.listInazDailyRecords.mockImplementation(async (_token, params: { dateFrom: string }) => {
      if (params.dateFrom.startsWith(`${currentMonth}-`)) {
        return emptyMonthResponse();
      }
      if (params.dateFrom.startsWith(`${previousMonth}-`)) {
        return anomalyMonthResponse(`${previousMonth}-12`);
      }
      return emptyMonthResponse();
    });

    render(<InazAnomaliePage />);

    await waitFor(() => {
      expect(screen.getByText(/Nessuna anomalia in/i)).toBeInTheDocument();
    });
    await waitFor(() => {
      expect(screen.getByTestId("anomalie-table")).toHaveTextContent("AMADU SALVATORE");
    });
    expect(mocks.listInazDailyRecords).toHaveBeenCalledWith(
      "token",
      expect.objectContaining({ dateFrom: `${previousMonth}-01` }),
    );
  });

  test("shows quick links for months with anomalies", async () => {
    const currentMonth = currentMonthValue();
    const previousMonth = previousMonthValue(currentMonth);
    const twoMonthsAgo = previousMonthValue(previousMonth);

    mocks.listInazDailyRecords.mockImplementation(async (_token, params: { dateFrom: string }) => {
      if (params.dateFrom.startsWith(`${currentMonth}-`)) {
        return emptyMonthResponse();
      }
      if (params.dateFrom.startsWith(`${previousMonth}-`)) {
        return anomalyMonthResponse(`${previousMonth}-10`);
      }
      if (params.dateFrom.startsWith(`${twoMonthsAgo}-`)) {
        return anomalyMonthResponse(`${twoMonthsAgo}-05`);
      }
      return emptyMonthResponse();
    });

    render(<InazAnomaliePage />);

    const olderMonthLabel = monthLabel(twoMonthsAgo);
    await waitFor(() => {
      expect(screen.getByRole("button", { name: new RegExp(`${olderMonthLabel} \\(1\\)`, "i") })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: new RegExp(`${olderMonthLabel} \\(1\\)`, "i") }));

    await waitFor(() => {
      expect(mocks.listInazDailyRecords).toHaveBeenCalledWith(
        "token",
        expect.objectContaining({ dateFrom: `${twoMonthsAgo}-01` }),
      );
    });
  });
});
