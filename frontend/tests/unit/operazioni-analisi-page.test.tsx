import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import AnalisiPage from "@/app/operazioni/analisi/page";

const mocks = vi.hoisted(() => ({
  getAnalyticsSummary: vi.fn(),
  getAnalyticsFuel: vi.fn(),
  getAnalyticsKm: vi.fn(),
  getAnalyticsWorkHours: vi.fn(),
  getAnalyticsAnomalies: vi.fn(),
  getAnalyticsAvailablePeriods: vi.fn(),
  getUnresolvedTransactions: vi.fn(),
  getOperatorDetail: vi.fn(),
}));

vi.mock("next/link", () => ({
  default: ({
    href,
    children,
    className,
    target,
    rel,
    onClick,
  }: {
    href: string;
    children: ReactNode;
    className?: string;
    target?: string;
    rel?: string;
    onClick?: () => void;
  }) => (
    <a href={href} className={className} target={target} rel={rel} onClick={onClick}>
      {children}
    </a>
  ),
}));

vi.mock("recharts", () => {
  function Wrapper({ children }: { children?: ReactNode }) {
    return <div>{children}</div>;
  }
  return {
    ResponsiveContainer: Wrapper,
    BarChart: Wrapper,
    Bar: Wrapper,
    LineChart: Wrapper,
    Line: Wrapper,
    PieChart: Wrapper,
    Pie: Wrapper,
    XAxis: () => <div />,
    YAxis: () => <div />,
    CartesianGrid: () => <div />,
    Tooltip: () => <div />,
    Legend: () => <div />,
  };
});

vi.mock("@/components/operazioni/operazioni-module-page", () => ({
  OperazioniModulePage: ({ children }: { children: () => ReactNode }) => <div>{children()}</div>,
}));

vi.mock("@/features/operazioni/api/client", () => ({
  getAnalyticsSummary: mocks.getAnalyticsSummary,
  getAnalyticsFuel: mocks.getAnalyticsFuel,
  getAnalyticsKm: mocks.getAnalyticsKm,
  getAnalyticsWorkHours: mocks.getAnalyticsWorkHours,
  getAnalyticsAnomalies: mocks.getAnalyticsAnomalies,
  getAnalyticsAvailablePeriods: mocks.getAnalyticsAvailablePeriods,
  getUnresolvedTransactions: mocks.getUnresolvedTransactions,
  getOperatorDetail: mocks.getOperatorDetail,
}));

describe("Operazioni analisi page", () => {
  beforeEach(() => {
    mocks.getAnalyticsSummary.mockReset();
    mocks.getAnalyticsFuel.mockReset();
    mocks.getAnalyticsKm.mockReset();
    mocks.getAnalyticsWorkHours.mockReset();
    mocks.getAnalyticsAnomalies.mockReset();
    mocks.getAnalyticsAvailablePeriods.mockReset();
    mocks.getUnresolvedTransactions.mockReset();
    mocks.getOperatorDetail.mockReset();

    mocks.getAnalyticsAvailablePeriods.mockResolvedValue({
      years: [],
      quarters: [],
      months: [],
    });
    mocks.getAnalyticsSummary.mockResolvedValue({
      period_label: "Ultimi 90 giorni",
      total_km: 0,
      total_liters: 45.5,
      total_fuel_cost: 88,
      total_work_hours: 0,
      work_hours_source: "session",
      active_sessions: 1,
      anomaly_count: 1,
      avg_consumption_l_per_100km: null,
    });
    mocks.getAnalyticsFuel.mockResolvedValue({
      time_series: [],
      cost_series: [],
      top_vehicles: [],
      top_operators: [],
      total_liters: 0,
      total_cost: 0,
      avg_liters_per_refuel: 0,
    });
    mocks.getAnalyticsKm.mockResolvedValue({
      time_series: [],
      top_vehicles: [],
      top_operators: [],
      total_km: 0,
      avg_km_per_session: 0,
      longest_session: null,
      shortest_session: null,
    });
    mocks.getAnalyticsWorkHours.mockResolvedValue({
      time_series: [],
      top_operators: [],
      by_team: [],
      by_category: [],
      total_hours: 0,
      avg_hours_per_operator: 0,
    });
    mocks.getUnresolvedTransactions.mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 10,
    });
  });

  test("operator quick modal shows fuel fallback km and opens operator page in new tab", async () => {
    mocks.getAnalyticsAnomalies.mockResolvedValue({
      items: [
        {
          id: "anomaly-1",
          type: "orphan_session",
          severity: "medium",
          description: "Sessione mezzo ancora aperta",
          entity_id: "session-1",
          entity_label: "FIAT Panda",
          detected_at: "2026-07-01T08:30:00Z",
          details: {
            operator_id: "operator-1",
            operator_name: "Simone Scanu",
            hours_open: 4,
          },
        },
      ],
      total: 1,
      by_type: { orphan_session: 1 },
      by_severity: { medium: 1 },
    });
    mocks.getOperatorDetail.mockResolvedValue({
      operator: {
        id: "operator-1",
        wc_id: 11,
        username: "simone.scanu",
        email: "scanus@bonificaoristanese.it",
        first_name: "Simone",
        last_name: "Scanu",
        tax: null,
        role: "11",
        enabled: true,
        gate_mobile_console_enabled: false,
        gate_mobile_console_role: null,
        gaia_user_id: null,
        wc_synced_at: null,
        created_at: "2026-01-01T00:00:00Z",
        updated_at: "2026-07-01T00:00:00Z",
        current_fuel_cards: [],
      },
      stats: {
        fuel_cards_count: 0,
        fuel_logs_count: 1,
        usage_sessions_count: 1,
        total_liters: "1625.7",
        total_fuel_cost: "2666.67",
        total_km_travelled: "0",
        most_used_vehicle: null,
        last_used_vehicle_label: "FIAT Panda",
      },
      current_fuel_cards: [],
      recent_fuel_logs: [
        {
          id: "fuel-1",
          vehicle_id: "vehicle-1",
          vehicle_label: "FIAT Panda",
          fueled_at: "2026-07-01T07:15:00Z",
          liters: "35.4",
          total_cost: "61.20",
          odometer_km: null,
          station_name: "Q8 Oristano",
        },
      ],
      recent_usage_sessions: [],
    });

    render(<AnalisiPage />);

    fireEvent.click(await screen.findByRole("button", { name: /Anomalie/i }));
    fireEvent.click(await screen.findByRole("button", { name: "Visualizza operatore" }));

    expect(await screen.findByText("Ultimo rifornimento")).toBeInTheDocument();
    const fuelKmCard = screen.getByText("Km carburante").closest("div");
    const fuelContextCard = screen.getByText("Contesto").closest("div");
    expect(fuelKmCard).not.toBeNull();
    expect(fuelContextCard).not.toBeNull();
    expect(within(fuelKmCard as HTMLElement).getByText("0 km")).toBeInTheDocument();
    expect(within(fuelContextCard as HTMLElement).getByText(/Q8 Oristano/)).toBeInTheDocument();

    const operatorLink = screen.getByRole("link", { name: "Apri pagina operatore" });
    expect(operatorLink).toHaveAttribute("href", "/operazioni/operatori?operatorId=operator-1&from=analisi");
    expect(operatorLink).toHaveAttribute("target", "_blank");
    expect(operatorLink).toHaveAttribute("rel", "noopener noreferrer");

    fireEvent.click(operatorLink);

    await waitFor(() => {
      expect(screen.queryByText("Ultimo rifornimento")).not.toBeInTheDocument();
    });
  });
});
