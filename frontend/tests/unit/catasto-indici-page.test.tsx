import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import CatastoIndiciPage from "@/app/catasto/indici/page";

const mocks = vi.hoisted(() => ({
  getStoredAccessToken: vi.fn(),
  catastoGetIndiciOverview: vi.fn(),
  catastoListParticelle: vi.fn(),
}));

vi.mock("@/lib/auth", () => ({
  getStoredAccessToken: mocks.getStoredAccessToken,
}));

vi.mock("@/lib/api/catasto", () => ({
  catastoGetIndiciOverview: mocks.catastoGetIndiciOverview,
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

describe("Catasto indici page", () => {
  beforeEach(() => {
    mocks.getStoredAccessToken.mockReturnValue("token");
    mocks.catastoGetIndiciOverview.mockReset();
    mocks.catastoListParticelle.mockReset();
  });

  test("renders overview and filters particelle by selected indice and coltura", async () => {
    mocks.catastoGetIndiciOverview.mockResolvedValue({
      anno_riferimento: 2026,
      total_distretti: 2,
      total_particelle: 5,
      available_colture: ["Mais", "Erba medica"],
      items: [
        {
          indice_key: "alta_pressione",
          indice_label: "Alta pressione",
          sort_order: 10,
          distretti_count: 1,
          particelle_count: 3,
          ruolo_particelle_count: 3,
          particelle_con_anagrafica_count: 1,
          particelle_senza_ruolo_count: 0,
          particelle_senza_anagrafica_count: 2,
          superficie_catastale_mq: "12000",
          superficie_irrigata_ha: "1.2",
          importo_stimato: "450",
          ruolo_metrics_reliable: true,
          ruolo_metrics_valid_count: 3,
          ruolo_metrics_invalid_count: 0,
          ruolo_metrics_warning: null,
          hectares_reference_total: "1800",
          distretti: [],
          comuni: [],
          distretti_analytics: [],
          colture: [
            {
              coltura: "Mais",
              gruppo_coltura: "Seminativi",
              particelle_count: 2,
              superficie_irrigata_ha: "1.2",
              importo_stimato: "450",
            },
          ],
        },
        {
          indice_key: "bassa_pressione",
          indice_label: "Bassa pressione",
          sort_order: 20,
          distretti_count: 1,
          particelle_count: 2,
          ruolo_particelle_count: 2,
          particelle_con_anagrafica_count: 1,
          particelle_senza_ruolo_count: 0,
          particelle_senza_anagrafica_count: 1,
          superficie_catastale_mq: "8000",
          superficie_irrigata_ha: "0.8",
          importo_stimato: "220",
          ruolo_metrics_reliable: true,
          ruolo_metrics_valid_count: 2,
          ruolo_metrics_invalid_count: 0,
          ruolo_metrics_warning: null,
          hectares_reference_total: "110",
          distretti: [],
          comuni: [],
          distretti_analytics: [],
          colture: [],
        },
      ],
    });
    mocks.catastoListParticelle.mockResolvedValue([
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
    ]);

    render(<CatastoIndiciPage />);

    expect(await screen.findByText("Distribuzione particelle per indice operativo")).toBeInTheDocument();
    await waitFor(() => {
      expect(mocks.catastoListParticelle).toHaveBeenCalledWith("token", {
        indice: "alta_pressione",
        coltura: undefined,
        anno: 2026,
        search: undefined,
        nomeComune: undefined,
        distretto: undefined,
        foglio: undefined,
        particella: undefined,
        soloARuolo: true,
        soloConAnagrafica: false,
        limit: 200,
      });
    });

    fireEvent.change(screen.getAllByRole("combobox")[0], { target: { value: "Mais" } });

    await waitFor(() => {
      expect(mocks.catastoListParticelle).toHaveBeenLastCalledWith("token", {
        indice: "alta_pressione",
        coltura: "Mais",
        anno: 2026,
        search: undefined,
        nomeComune: undefined,
        distretto: undefined,
        foglio: undefined,
        particella: undefined,
        soloARuolo: true,
        soloConAnagrafica: false,
        limit: 200,
      });
    });

    expect(screen.getByText("Mario Rossi")).toBeInTheDocument();
    expect(screen.getAllByText("Alta pressione").length).toBeGreaterThan(0);
  });

  test("shows warning instead of irrigated metrics when ruolo data is unreliable", async () => {
    mocks.catastoGetIndiciOverview.mockResolvedValue({
      anno_riferimento: 2025,
      total_distretti: 1,
      total_particelle: 3,
      available_colture: ["Mais"],
      items: [
        {
          indice_key: "alta_pressione",
          indice_label: "Alta pressione",
          sort_order: 10,
          distretti_count: 1,
          particelle_count: 3,
          ruolo_particelle_count: 3,
          particelle_con_anagrafica_count: 1,
          particelle_senza_ruolo_count: 0,
          particelle_senza_anagrafica_count: 2,
          superficie_catastale_mq: "12000",
          superficie_irrigata_ha: "59158105",
          importo_stimato: "999999",
          ruolo_metrics_reliable: false,
          ruolo_metrics_valid_count: 1,
          ruolo_metrics_invalid_count: 12,
          ruolo_metrics_warning: "Le superfici irrigate e gli importi ruolo risultano non affidabili per questo indice.",
          hectares_reference_total: "1800",
          distretti: [],
          comuni: [],
          distretti_analytics: [],
          colture: [
            {
              coltura: "Mais",
              gruppo_coltura: "Seminativi",
              particelle_count: 3,
              superficie_irrigata_ha: "59158105",
              importo_stimato: "999999",
            },
          ],
        },
      ],
    });
    mocks.catastoListParticelle.mockResolvedValue([]);

    render(<CatastoIndiciPage />);

    expect(await screen.findByText("Dati ruolo non affidabili")).toBeInTheDocument();
    expect(screen.getAllByText("Dato non affidabile").length).toBeGreaterThan(1);
  });
});
