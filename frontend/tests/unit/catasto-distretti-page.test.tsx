import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import CatastoDistrettiPage from "@/app/catasto/distretti/page";

const mocks = vi.hoisted(() => ({
  getStoredAccessToken: vi.fn(),
  catastoListDistretti: vi.fn(),
  catastoGetImportHistory: vi.fn(),
  catastoGetDistrettoKpi: vi.fn(),
}));

vi.mock("@/lib/auth", () => ({
  getStoredAccessToken: mocks.getStoredAccessToken,
}));

vi.mock("@/lib/api/catasto", () => ({
  catastoListDistretti: mocks.catastoListDistretti,
  catastoGetImportHistory: mocks.catastoGetImportHistory,
  catastoGetDistrettoKpi: mocks.catastoGetDistrettoKpi,
}));

vi.mock("@/components/catasto/catasto-page", () => ({
  CatastoPage: ({ children, title }: { children: React.ReactNode; title: string }) => (
    <main>
      <h1>{title}</h1>
      {children}
    </main>
  ),
}));

vi.mock("@/components/catasto/distretti/distretto-gis-preview", () => ({
  DistrettoGisPreview: ({
    distretto,
  }: {
    distretto: { num_distretto: string; nome_distretto: string | null };
  }) => (
    <div data-testid="distretto-gis-preview">
      GIS {distretto.num_distretto} {distretto.nome_distretto}
    </div>
  ),
}));

vi.mock("@/components/table/data-table", () => ({
  DataTable: ({
    data,
    onRowClick,
  }: {
    data: Array<{ id: string; num_distretto: string; nome_distretto: string | null }>;
    onRowClick?: (row: { id: string; num_distretto: string; nome_distretto: string | null }) => void;
  }) => (
    <div>
      {data.map((row) => (
        <button key={row.id} type="button" onClick={() => onRowClick?.(row)}>
          Riga distretto {row.num_distretto} {row.nome_distretto}
        </button>
      ))}
    </div>
  ),
}));

vi.mock("recharts", () => {
  function Wrapper({ children }: { children?: React.ReactNode }) {
    return <div>{children}</div>;
  }
  return {
    ResponsiveContainer: Wrapper,
    BarChart: Wrapper,
    CartesianGrid: () => <div />,
    XAxis: () => <div />,
    YAxis: () => <div />,
    Tooltip: () => <div />,
    Bar: Wrapper,
    Cell: () => <div />,
  };
});

describe("CatastoDistrettiPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.getStoredAccessToken.mockReturnValue("token");
    mocks.catastoGetImportHistory.mockResolvedValue([
      {
        id: 1,
        filename: "ruolo.xlsx",
        status: "completed",
        anno_campagna: 2026,
      },
    ]);
    mocks.catastoListDistretti.mockResolvedValue([
      {
        id: "distretto-1",
        num_distretto: "01",
        nome_distretto: "Sinis Nord Est",
        decreto_istitutivo: null,
        data_decreto: null,
        attivo: true,
        note: null,
        created_at: "2026-01-01T00:00:00Z",
        updated_at: "2026-01-01T00:00:00Z",
      },
      {
        id: "distretto-fd",
        num_distretto: "FD",
        nome_distretto: "Fuori distretto",
        decreto_istitutivo: null,
        data_decreto: null,
        attivo: true,
        note: null,
        created_at: "2026-01-01T00:00:00Z",
        updated_at: "2026-01-01T00:00:00Z",
      },
    ]);
    mocks.catastoGetDistrettoKpi.mockResolvedValue({
      distretto_id: "distretto-1",
      anno: 2026,
      num_distretto: "01",
      totale_particelle: 12,
      totale_utenze: 4,
      totale_anomalie: 1,
      anomalie_error: 0,
      importo_totale_0648: "100",
      importo_totale_0985: "50",
      superficie_irrigabile_mq: "125000",
    });
  });

  test("opens the district modal with a read-only GIS preview", async () => {
    render(<CatastoDistrettiPage />);

    const rowButton = await screen.findByRole("button", {
      name: /Riga distretto 01 Sinis Nord Est/i,
    });
    fireEvent.click(rowButton);

    expect(await screen.findByTestId("distretto-gis-preview")).toHaveTextContent(
      "GIS 01 Sinis Nord Est",
    );
    expect(screen.getByTitle("Distretto 01")).toHaveAttribute(
      "src",
      "/catasto/distretti/distretto-1?embedded=1",
    );
    await waitFor(() => {
      expect(mocks.catastoGetDistrettoKpi).toHaveBeenCalledWith(
        "token",
        "distretto-1",
        2026,
      );
    });
    expect(screen.queryByText(/Fuori distretto/i)).not.toBeInTheDocument();
  });
});
