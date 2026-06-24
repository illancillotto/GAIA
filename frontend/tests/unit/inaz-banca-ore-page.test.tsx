import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import InazBankHoursPage from "@/app/inaz/banca-ore/page";

const mocks = vi.hoisted(() => ({
  getStoredAccessToken: vi.fn(),
  getInazBankHoursDashboard: vi.fn(),
  getInazBankHoursCollaboratorDetail: vi.fn(),
  createInazBankHoursAdjustment: vi.fn(),
  updateInazBankHoursAdjustment: vi.fn(),
  reviewInazBankHoursAdjustment: vi.fn(),
  deleteInazBankHoursAdjustment: vi.fn(),
}));

vi.mock("@/lib/auth", () => ({
  getStoredAccessToken: mocks.getStoredAccessToken,
}));

vi.mock("@/lib/api", () => ({
  getInazBankHoursDashboard: mocks.getInazBankHoursDashboard,
  getInazBankHoursCollaboratorDetail: mocks.getInazBankHoursCollaboratorDetail,
  createInazBankHoursAdjustment: mocks.createInazBankHoursAdjustment,
  updateInazBankHoursAdjustment: mocks.updateInazBankHoursAdjustment,
  reviewInazBankHoursAdjustment: mocks.reviewInazBankHoursAdjustment,
  deleteInazBankHoursAdjustment: mocks.deleteInazBankHoursAdjustment,
}));

vi.mock("@/components/app/protected-page", () => ({
  ProtectedPage: ({ children, title }: { children: React.ReactNode; title: string }) => (
    <div>
      <h1>{title}</h1>
      {children}
    </div>
  ),
}));

describe("Inaz banca ore page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.getStoredAccessToken.mockReturnValue("token");
    mocks.getInazBankHoursDashboard.mockResolvedValue({
      date_from: "2026-01-01",
      date_to: "2026-12-31",
      collaborators_total: 1,
      imported_balance_total_minutes: 720,
      approved_adjustment_total_minutes: -120,
      effective_balance_total_minutes: 600,
      liquidation_total_minutes: 120,
      pending_adjustments_total: 1,
      negative_balance_total: 0,
      items: [
        {
          collaborator_id: "collab-1",
          employee_code: "1854",
          collaborator_name: "AMADU SALVATORE",
          company_code: "53",
          application_user_id: null,
          contract_kind: "operaio",
          standard_daily_minutes: 420,
          contract_profile_source: "explicit",
          imported_prev_balance_minutes: 600,
          imported_accrued_minutes: 180,
          imported_used_minutes: 60,
          imported_balance_minutes: 720,
          approved_adjustment_minutes: -120,
          effective_balance_minutes: 600,
          available_debit_minutes: 600,
          available_debit_days: 1.43,
          liquidation_minutes_total: 120,
          manual_adjustment_count: 1,
          pending_adjustment_count: 1,
          latest_snapshot_period_start: "2026-05-01",
          latest_snapshot_period_end: "2026-05-31",
          last_adjustment_date: "2026-05-20",
          last_adjustment_status: "pending",
        },
      ],
    });
    mocks.getInazBankHoursCollaboratorDetail.mockResolvedValue({
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
        last_seen_at: "2026-06-24T10:00:00Z",
        created_at: "2026-06-24T10:00:00Z",
        updated_at: "2026-06-24T10:00:00Z",
      },
      contract_profile_source: "explicit",
      date_from: "2026-01-01",
      date_to: "2026-12-31",
      imported_balance_minutes: 720,
      approved_adjustment_minutes: -120,
      effective_balance_minutes: 600,
      available_debit_minutes: 600,
      available_debit_days: 1.43,
      compensation_summary: {
        records_total: 1,
        worked_days_total: 1,
        night_minutes_total: 240,
        festive_minutes_total: 0,
        festive_night_minutes_total: 0,
        ordinary_night_minutes_total: 240,
        overtime_day_minutes_total: 120,
        overtime_night_minutes_total: 0,
        overtime_festive_minutes_total: 0,
        overtime_festive_night_minutes_total: 0,
        shift_festive_day_minutes_total: 0,
        shift_night_minutes_total: 0,
        shift_festive_night_minutes_total: 0,
        night_shift_days_total: 1,
        max_monthly_night_shift_count: 1,
        ordinary_night_bonus_threshold_met: false,
        ordinary_night_bonus_rate: 10,
      },
      liquidation_guidance: {
        allow_derived_profile: false,
        included_overtime_buckets: ["overtime_day", "overtime_night", "overtime_festive", "overtime_festive_night"],
        min_suggested_minutes: 60,
        available_minutes: 600,
        candidate_minutes_from_overtime: 120,
        suggested_minutes: 120,
        suggested_days: 0.29,
        liquidable_minutes: 120,
        keep_in_bank_minutes: 480,
        review_minutes: 0,
        requires_profile_review: false,
        reason_code: "ok",
        notes: ["La proposta usa il minore tra saldo banca ore disponibile e straordinario del periodo classificato dal motore CCNL."],
      },
      snapshots: [
        {
          collaborator_id: "collab-1",
          period_start: "2026-05-01",
          period_end: "2026-05-31",
          description: "Banca ore CBO",
          residuo_prec_minutes: 600,
          spettante_minutes: 180,
          fruito_minutes: 60,
          saldo_minutes: 720,
          saldo_totale_minutes: 720,
          source_job_id: null,
        },
      ],
      adjustments: [],
    });
    mocks.createInazBankHoursAdjustment.mockResolvedValue({
      id: "adj-1",
      collaborator_id: "collab-1",
      adjustment_date: "2026-05-20",
      delta_minutes: -120,
      kind: "liquidation",
      approval_status: "pending",
      reason: "Liquidazione straordinario",
      note: null,
      approval_note: null,
      created_by_user_id: 1,
      updated_by_user_id: 1,
      reviewed_by_user_id: null,
      created_by_label: "Admin",
      updated_by_label: "Admin",
      reviewed_by_label: null,
      created_at: "2026-06-24T10:00:00Z",
      updated_at: "2026-06-24T10:00:00Z",
      reviewed_at: null,
    });
  });

  test("renders dashboard and creates a pending liquidation from guidance", async () => {
    render(<InazBankHoursPage />);

    expect(await screen.findByText("Controllo banca ore")).toBeInTheDocument();
    expect(await screen.findByText("AMADU SALVATORE")).toBeInTheDocument();
    expect(await screen.findByText("Disponibile a scarico")).toBeInTheDocument();
    expect(await screen.findAllByText("Operaio")).toHaveLength(2);
    expect(await screen.findByText("1.43 gg")).toBeInTheDocument();
    expect(await screen.findByText("Quadro CCNL periodo")).toBeInTheDocument();
    expect(await screen.findByText("Bonus Art. 82")).toBeInTheDocument();
    expect(await screen.findByText("10%")).toBeInTheDocument();
    expect(await screen.findByText("Proponi liquidazione")).toBeInTheDocument();
    expect(await screen.findByText("Resta in banca ore")).toBeInTheDocument();
    expect(await screen.findByText("Da revisione HR")).toBeInTheDocument();
    expect(await screen.findByText(/Profilo derivato liquidabile:/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Proponi liquidazione/i }));
    fireEvent.click(screen.getByRole("button", { name: /Crea movimento/i }));

    await waitFor(() => {
      expect(mocks.createInazBankHoursAdjustment).toHaveBeenCalledWith(
        "token",
        expect.objectContaining({
          collaborator_id: "collab-1",
          delta_minutes: -120,
          kind: "liquidation",
          reason: "Liquidazione guidata 2026-01-01 / 2026-12-31",
        }),
      );
    });
  });
});
