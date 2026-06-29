import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import CatastoColturePage from "@/app/catasto/colture/page";

const mocks = vi.hoisted(() => ({
  getStoredAccessToken: vi.fn(),
  catastoGetColtureOverview: vi.fn(),
  catastoListParticelle: vi.fn(),
}));

vi.mock("@/lib/auth", () => ({
  getStoredAccessToken: mocks.getStoredAccessToken,
}));

vi.mock("@/lib/api/catasto", () => ({
  catastoGetColtureOverview: mocks.catastoGetColtureOverview,
  catastoListParticelle: mocks.catastoListParticelle,
}));

vi.mock("@/components/catasto/catasto-page", () => ({
  CatastoPage: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

vi.mock("@/components/catasto/anagrafica/ParticellaDetailDialog", () => ({
  ParticellaDetailDialog: () => null,
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

describe("Catasto colture page", () => {
  beforeEach(() => {
    mocks.getStoredAccessToken.mockReturnValue("token");
    mocks.catastoGetColtureOverview.mockReset();
    mocks.catastoListParticelle.mockReset();
  });

  test("renders crop analytics and reloads particelle when crop changes", async () => {
    mocks.catastoGetColtureOverview.mockResolvedValue({
      anno_riferimento: 2026,
      available_years: [2026, 2025],
      available_groups: ["Erbai, Medica, Mais, Sorgo"],
      available_distretti: ["01 · Sinis Nord Est"],
      available_indici: ["Alta pressione"],
      available_comuni: ["Arborea"],
      total_colture: 2,
      total_role_particelle: 5,
      total_meter_readings: 3,
      total_superficie_irrigata_ha: "4.1",
      total_importo_totale: "1200",
      total_consumo_reale_mc: "950",
      items: [
        {
          coltura: "Mais",
          gruppo_coltura: "Erbai, Medica, Mais, Sorgo",
          quality_badge: "misto",
          role_particelle_count: 3,
          meter_readings_count: 2,
          meter_points_count: 1,
          distretti_count: 1,
          indici_count: 1,
          comuni_count: 1,
          superficie_irrigata_ha: "1.2",
          importo_totale: "450",
          consumo_reale_mc: "320",
          euro_per_ha: "375",
          euro_per_mc: "1.4",
          mc_per_ha: "266.7",
          distretti: [],
          indici: [],
          comuni: [],
          years: [{ anno: 2026, key: "2026", label: "2026", role_particelle_count: 3, meter_readings_count: 2, meter_points_count: 1, superficie_irrigata_ha: "1.2", importo_totale: "450", consumo_reale_mc: "320", euro_per_ha: "375", euro_per_mc: "1.4", mc_per_ha: "266.7" }],
        },
        {
          coltura: "Erba medica",
          gruppo_coltura: "Erbai, Medica, Mais, Sorgo",
          quality_badge: "stimato",
          role_particelle_count: 2,
          meter_readings_count: 0,
          meter_points_count: 0,
          distretti_count: 1,
          indici_count: 1,
          comuni_count: 1,
          superficie_irrigata_ha: "0.8",
          importo_totale: "220",
          consumo_reale_mc: "0",
          euro_per_ha: "275",
          euro_per_mc: null,
          mc_per_ha: null,
          distretti: [],
          indici: [],
          comuni: [],
          years: [{ anno: 2026, key: "2026", label: "2026", role_particelle_count: 2, meter_readings_count: 0, meter_points_count: 0, superficie_irrigata_ha: "0.8", importo_totale: "220", consumo_reale_mc: "0", euro_per_ha: "275", euro_per_mc: null, mc_per_ha: null }],
        },
      ],
    });
    mocks.catastoListParticelle
      .mockResolvedValueOnce([
        {
          id: "particella-1",
          comune_id: null,
          national_code: null,
          cod_comune_capacitas: 165,
          codice_catastale: "A357",
          nome_comune: "Arborea",
          sezione_catastale: null,
          foglio: "5",
          particella: "120",
          subalterno: null,
          cfm: null,
          superficie_mq: "12000",
          superficie_grafica_mq: null,
          num_distretto: "01",
          nome_distretto: "Sinis Nord Est",
          source_type: "shapefile",
          capacitas_last_sync_at: null,
          capacitas_last_sync_status: null,
          capacitas_last_sync_error: null,
          capacitas_last_sync_job_id: null,
          valid_from: "2026-01-01",
          valid_to: null,
          is_current: true,
          suppressed: false,
          created_at: "2026-06-29T08:00:00Z",
          updated_at: "2026-06-29T08:00:00Z",
          ha_anagrafica: true,
          utenza_cf: "RSSMRA80A01H501U",
          utenza_denominazione: "Mario Rossi",
          indice_key: "alta_pressione",
          indice_label: "Alta pressione",
          indice_hectares_reference: "1800",
          indice_irriguo_coltura: "Mais",
          indice_irriguo_gruppo_coltura: "Seminativi",
          indice_irriguo_anno_riferimento: 2026,
          swapped_capacitas: null,
        },
      ])
      .mockResolvedValueOnce([]);

    render(<CatastoColturePage />);

    expect(await screen.findByText("Ruolo, consumi e rapporto costo/consumo")).toBeInTheDocument();
    await waitFor(() => {
      expect(mocks.catastoListParticelle).toHaveBeenCalledWith("token", {
        coltura: "Mais",
        anno: 2026,
        soloARuolo: true,
        limit: 200,
      });
    });

    fireEvent.click(screen.getByRole("button", { name: /Erba medica/i }));

    await waitFor(() => {
      expect(mocks.catastoListParticelle).toHaveBeenLastCalledWith("token", {
        coltura: "Erba medica",
        anno: 2026,
        soloARuolo: true,
        limit: 200,
      });
    });
    expect(screen.getByText("Drill-down catastale per coltura selezionata")).toBeInTheDocument();
  });
});
