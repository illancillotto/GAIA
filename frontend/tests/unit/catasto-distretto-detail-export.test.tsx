import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import CatastoDistrettoDetailPage from "@/app/catasto/distretti/[id]/page";

const mocks = vi.hoisted(() => ({
  getStoredAccessToken: vi.fn(),
  catastoDownloadDistrettoParticelleExport: vi.fn(),
  catastoGetDistretto: vi.fn(),
  catastoGetDistrettoKpi: vi.fn(),
  catastoGetImportHistory: vi.fn(),
  catastoListAnomalie: vi.fn(),
  catastoListParticelle: vi.fn(),
  routerPush: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useParams: () => ({ id: "distretto-1" }),
  useRouter: () => ({ push: mocks.routerPush }),
  useSearchParams: () => ({ get: () => null }),
}));

vi.mock("@/lib/auth", () => ({
  getStoredAccessToken: mocks.getStoredAccessToken,
}));

vi.mock("@/lib/api/catasto-distretti-export", () => ({
  catastoDownloadDistrettoParticelleExport: mocks.catastoDownloadDistrettoParticelleExport,
}));

vi.mock("@/lib/api/catasto", () => ({
  catastoGetDistretto: mocks.catastoGetDistretto,
  catastoGetDistrettoKpi: mocks.catastoGetDistrettoKpi,
  catastoGetImportHistory: mocks.catastoGetImportHistory,
  catastoListAnomalie: mocks.catastoListAnomalie,
  catastoListParticelle: mocks.catastoListParticelle,
}));

vi.mock("@/components/catasto/catasto-page", () => ({
  CatastoPage: ({ children, title }: { children: React.ReactNode; title: string }) => (
    <main>
      <h1>{title}</h1>
      {children}
    </main>
  ),
}));

vi.mock("@/components/table/data-table", () => ({
  DataTable: ({ data }: { data: Array<{ id: string; particella?: string }> }) => (
    <div>
      {data.map((row) => (
        <span key={row.id}>Particella {row.particella ?? row.id}</span>
      ))}
    </div>
  ),
}));

vi.mock("@/components/ui/metric-card", () => ({
  MetricCard: ({ label, value }: { label: string; value: React.ReactNode }) => (
    <div>
      {label}: {value}
    </div>
  ),
}));

vi.mock("@/components/catasto/AnomaliaStatusBadge", () => ({
  AnomaliaStatusBadge: ({ severita }: { severita: string }) => <span>{severita}</span>,
}));

vi.mock("@/components/catasto/AnomaliaStatusPill", () => ({
  AnomaliaStatusPill: ({ status }: { status: string }) => <span>{status}</span>,
}));

describe("CatastoDistrettoDetailPage exports", () => {
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
    mocks.catastoGetDistretto.mockResolvedValue({
      id: "distretto-1",
      num_distretto: "01",
      nome_distretto: "Sinis Nord Est",
      decreto_istitutivo: null,
      data_decreto: null,
      attivo: true,
      note: null,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    });
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
    mocks.catastoListParticelle.mockResolvedValue([
      {
        id: "part-1",
        nome_comune: "ARBOREA",
        cod_comune_capacitas: 95,
        foglio: "5",
        particella: "120",
        subalterno: null,
        superficie_mq: "1000",
        superficie_grafica_mq: "990",
        num_distretto: "01",
      },
    ]);
    mocks.catastoListAnomalie.mockResolvedValue({ items: [] });
    mocks.catastoDownloadDistrettoParticelleExport.mockResolvedValue(
      new Blob(["export"], { type: "text/plain" }),
    );
    vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:export");
    vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => undefined);
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
  });

  test("downloads district parcel CSV and XLSX from backend", async () => {
    render(<CatastoDistrettoDetailPage />);

    await screen.findByText("Particella 120");

    fireEvent.click(screen.getByRole("button", { name: "Esporta CSV" }));
    await waitFor(() => {
      expect(mocks.catastoDownloadDistrettoParticelleExport).toHaveBeenCalledWith(
        "token",
        "distretto-1",
        "csv",
      );
    });

    fireEvent.click(screen.getByRole("button", { name: "Esporta XLSX" }));
    await waitFor(() => {
      expect(mocks.catastoDownloadDistrettoParticelleExport).toHaveBeenCalledWith(
        "token",
        "distretto-1",
        "xlsx",
      );
    });
  });
});
