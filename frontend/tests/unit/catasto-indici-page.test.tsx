import { fireEvent, render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import CatastoIndiciPage from "@/app/catasto/indici/page";

const mocks = vi.hoisted(() => ({
  getStoredAccessToken: vi.fn(),
  catastoGetIndiciOverview: vi.fn(),
}));

vi.mock("@/lib/auth", () => ({
  getStoredAccessToken: mocks.getStoredAccessToken,
}));

vi.mock("@/lib/api/catasto", () => ({
  catastoGetIndiciOverview: mocks.catastoGetIndiciOverview,
}));

vi.mock("@/components/catasto/catasto-page", () => ({
  CatastoPage: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

vi.mock("recharts", () => {
  function Wrapper({ children }: { children?: React.ReactNode }) {
    return <div>{children}</div>;
  }
  function Tooltip({ formatter }: { formatter?: (value: number) => unknown }) {
    return <div>{formatter ? String(formatter(7)) : null}</div>;
  }
  return {
    ResponsiveContainer: Wrapper,
    BarChart: Wrapper,
    CartesianGrid: () => <div />,
    XAxis: () => <div />,
    YAxis: () => <div />,
    Tooltip,
    Bar: Wrapper,
    Cell: () => <div />,
  };
});

describe("Catasto indici page", () => {
  beforeEach(() => {
    mocks.getStoredAccessToken.mockReturnValue("token");
    mocks.catastoGetIndiciOverview.mockReset();
  });

  test("renders overview with distretti table and excel export", async () => {
    mocks.catastoGetIndiciOverview.mockResolvedValue({
      anno_riferimento: 2025,
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
          importo_ruolo: "1230",
          importo_ruolo_manutenzione: "600",
          importo_ruolo_irrigazione: "430",
          importo_ruolo_istituzionale: "200",
          ruolo_metrics_reliable: true,
          ruolo_metrics_valid_count: 3,
          ruolo_metrics_invalid_count: 0,
          ruolo_metrics_warning: null,
          hectares_reference_total: "1800",
          distretti: [
            {
              distretto_id: "d-01",
              num_distretto: "01",
              nome_distretto: "Sinis Nord Est",
              indice_key: "alta_pressione",
              indice_label: "Alta pressione",
              hectares_reference: "1800",
            },
          ],
          comuni: [
            {
              key: "095012",
              label: "Oristano",
              particelle_count: 3,
              ruolo_particelle_count: 3,
              particelle_con_anagrafica_count: 1,
              superficie_irrigata_ha: "1.2",
              importo_stimato: "450",
              importo_ruolo: "1230",
              importo_ruolo_manutenzione: "600",
              importo_ruolo_irrigazione: "430",
              importo_ruolo_istituzionale: "200",
            },
          ],
          distretti_analytics: [
            {
              key: "01",
              label: "01 · Sinis Nord Est",
              particelle_count: 3,
              ruolo_particelle_count: 3,
              particelle_con_anagrafica_count: 1,
              superficie_irrigata_ha: "1.2",
              importo_stimato: "450",
              importo_ruolo: "1230",
              importo_ruolo_manutenzione: "600",
              importo_ruolo_irrigazione: "430",
              importo_ruolo_istituzionale: "200",
            },
          ],
          colture: [
            {
              coltura: "Mais",
              gruppo_coltura: "Seminativi",
              particelle_count: 2,
              superficie_irrigata_ha: "1.2",
              importo_stimato: "450",
              importo_ruolo: "1230",
            },
            {
              coltura: "Erba medica",
              gruppo_coltura: "Foraggere",
              particelle_count: 1,
              superficie_irrigata_ha: "0.4",
              importo_stimato: "100",
              importo_ruolo: "120",
            },
          ],
        },
        {
          indice_key: "canaletta",
          indice_label: "Canaletta",
          sort_order: 30,
          distretti_count: 1,
          particelle_count: 2,
          ruolo_particelle_count: 2,
          particelle_con_anagrafica_count: 1,
          particelle_senza_ruolo_count: 0,
          particelle_senza_anagrafica_count: 1,
          superficie_catastale_mq: "8000",
          superficie_irrigata_ha: "0.8",
          importo_stimato: "220",
          importo_ruolo: "540",
          importo_ruolo_manutenzione: "300",
          importo_ruolo_irrigazione: "140",
          importo_ruolo_istituzionale: "100",
          ruolo_metrics_reliable: true,
          ruolo_metrics_valid_count: 2,
          ruolo_metrics_invalid_count: 0,
          ruolo_metrics_warning: null,
          hectares_reference_total: "1200",
          distretti: [
            {
              distretto_id: "d-08",
              num_distretto: "8",
              nome_distretto: "Pauli Bingias",
              indice_key: "canaletta",
              indice_label: "Canaletta",
              hectares_reference: "1200",
            },
          ],
          comuni: [],
          distretti_analytics: [
            {
              key: "08",
              label: "08 · Pauli Bingias",
              particelle_count: 2,
              ruolo_particelle_count: 2,
              particelle_con_anagrafica_count: 1,
              superficie_irrigata_ha: "0.8",
              importo_stimato: "220",
              importo_ruolo: "540",
              importo_ruolo_manutenzione: "300",
              importo_ruolo_irrigazione: "140",
              importo_ruolo_istituzionale: "100",
            },
          ],
          colture: [],
        },
        {
          indice_key: "legacy",
          indice_label: "Legacy",
          sort_order: 100,
          distretti_count: 0,
          particelle_count: 0,
          ruolo_particelle_count: 0,
          particelle_con_anagrafica_count: 0,
          particelle_senza_ruolo_count: 0,
          particelle_senza_anagrafica_count: 0,
          superficie_catastale_mq: "0",
          superficie_irrigata_ha: "0",
          importo_stimato: "0",
          importo_ruolo: "0",
          importo_ruolo_manutenzione: "0",
          importo_ruolo_irrigazione: "0",
          importo_ruolo_istituzionale: "0",
          ruolo_metrics_reliable: true,
          ruolo_metrics_valid_count: 0,
          ruolo_metrics_invalid_count: 0,
          ruolo_metrics_warning: null,
          hectares_reference_total: null,
          distretti: [],
          comuni: [],
          distretti_analytics: [],
          colture: [],
        },
      ],
    });

    render(<CatastoIndiciPage />);

    expect(await screen.findByText("Distribuzione particelle per indice operativo")).toBeInTheDocument();
    const distrettiTable = screen.getByRole("table");

    expect(screen.getByText("Tutti i distretti con indice, superfici e importi ruolo")).toBeInTheDocument();
    expect(within(distrettiTable).getByText("Sinis Nord Est")).toBeInTheDocument();
    expect(within(distrettiTable).getByText("Pauli Bingias")).toBeInTheDocument();
    expect(within(distrettiTable).getByRole("columnheader", { name: "Ha riferimento" })).toBeInTheDocument();
    expect(within(distrettiTable).getByRole("columnheader", { name: "0648 Manut." })).toBeInTheDocument();
    expect(within(distrettiTable).getByRole("columnheader", { name: "0668 Irrig." })).toBeInTheDocument();
    expect(within(distrettiTable).getByRole("columnheader", { name: "0985 Ist." })).toBeInTheDocument();
    expect(within(distrettiTable).getByRole("cell", { name: "1800,0" })).toBeInTheDocument();
    expect(within(distrettiTable).getByRole("cell", { name: "1200,0" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Scarica Excel" })).toBeEnabled();

    expect(screen.getByText("Colture prevalenti")).toBeInTheDocument();
    expect(screen.getByText("Approfondimenti operativi")).toBeInTheDocument();

    expect(screen.getAllByText("Importo ruolo").length).toBeGreaterThan(0);
    expect(within(distrettiTable).getByText(/Totale \(2 distretti\)/)).toBeInTheDocument();
    // Totale importo ruolo in tabella: 1230 + 540 = 1770
    expect(within(distrettiTable).getAllByText(/1770\s*€/).length).toBeGreaterThan(0);
    expect(within(distrettiTable).getAllByText(/900\s*€/).length).toBeGreaterThan(0);
    expect(within(distrettiTable).getAllByText(/570\s*€/).length).toBeGreaterThan(0);
    expect(within(distrettiTable).getAllByText(/300\s*€/).length).toBeGreaterThan(0);

    expect(screen.getByRole("radiogroup", { name: "Filtra per indice" })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: "Tutti" })).toHaveAttribute("aria-checked", "true");

    fireEvent.click(within(distrettiTable).getByRole("button", { name: /Ordina Importo ruolo/ }));
    expect(within(distrettiTable).getByRole("columnheader", { name: /Importo ruolo/ })).toHaveAttribute("aria-sort", "ascending");

    fireEvent.click(screen.getByRole("button", { name: /Legacy\s+0\s+0 distretti/ }));
    expect(screen.getByRole("heading", { name: "Legacy" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Canaletta\s+2\s+1 distretti/ }));
    expect(screen.getByRole("heading", { name: "Canaletta" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("radio", { name: "Canaletta" }));

    expect(within(distrettiTable).queryByRole("cell", { name: "Sinis Nord Est" })).not.toBeInTheDocument();
    expect(within(distrettiTable).queryByRole("cell", { name: "1800,0" })).not.toBeInTheDocument();
    expect(within(distrettiTable).getByRole("cell", { name: "Pauli Bingias" })).toBeInTheDocument();
    expect(within(distrettiTable).getAllByRole("cell", { name: "1200,0" }).length).toBeGreaterThan(0);
    expect(within(distrettiTable).getByText(/Totale \(1 distretti\)/)).toBeInTheDocument();
    expect(within(distrettiTable).getAllByText(/540\s*€/).length).toBeGreaterThan(0);
    expect(within(distrettiTable).queryAllByText(/1230\s*€/)).toHaveLength(0);
    expect(within(distrettiTable).getAllByText(/300\s*€/).length).toBeGreaterThan(0);
    expect(within(distrettiTable).getAllByText(/140\s*€/).length).toBeGreaterThan(0);
    expect(within(distrettiTable).getAllByText(/100\s*€/).length).toBeGreaterThan(0);
    expect(screen.getByRole("radio", { name: "Canaletta" })).toHaveAttribute("aria-checked", "true");
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
          importo_ruolo: "999999",
          importo_ruolo_manutenzione: "0",
          importo_ruolo_irrigazione: "0",
          importo_ruolo_istituzionale: "0",
          ruolo_metrics_reliable: false,
          ruolo_metrics_valid_count: 1,
          ruolo_metrics_invalid_count: 12,
          ruolo_metrics_warning: "Le superfici irrigate e gli importi ruolo risultano non affidabili per questo indice.",
          hectares_reference_total: "1800",
          distretti: [],
          comuni: [
            {
              key: "095012",
              label: "Oristano",
              particelle_count: 3,
              ruolo_particelle_count: 3,
              particelle_con_anagrafica_count: 1,
              superficie_irrigata_ha: "59158105",
              importo_stimato: "999999",
              importo_ruolo: "999999",
              importo_ruolo_manutenzione: "0",
              importo_ruolo_irrigazione: "0",
              importo_ruolo_istituzionale: "0",
            },
          ],
          distretti_analytics: [
            {
              key: "01",
              label: "01 · Sinis Nord Est",
              particelle_count: 3,
              ruolo_particelle_count: 3,
              particelle_con_anagrafica_count: 1,
              superficie_irrigata_ha: "59158105",
              importo_stimato: "999999",
              importo_ruolo: "999999",
              importo_ruolo_manutenzione: "0",
              importo_ruolo_irrigazione: "0",
              importo_ruolo_istituzionale: "0",
            },
          ],
          colture: [
            {
              coltura: "Mais",
              gruppo_coltura: "Seminativi",
              particelle_count: 3,
              superficie_irrigata_ha: "59158105",
              importo_stimato: "999999",
              importo_ruolo: "999999",
            },
            {
              coltura: "Erba medica",
              gruppo_coltura: "Foraggere",
              particelle_count: 1,
              superficie_irrigata_ha: "2",
              importo_stimato: "10",
              importo_ruolo: "10",
            },
          ],
        },
      ],
    });

    render(<CatastoIndiciPage />);

    expect(await screen.findByText("Dati ruolo non affidabili")).toBeInTheDocument();
    expect(screen.getAllByText("Dato non affidabile").length).toBeGreaterThan(1);
  });

  test("uses the default warning text when unreliable ruolo metrics have no custom warning", async () => {
    mocks.catastoGetIndiciOverview.mockResolvedValue({
      anno_riferimento: 2025,
      total_distretti: 1,
      total_particelle: 1,
      available_colture: [],
      items: [
        {
          indice_key: "alta_pressione",
          indice_label: "Alta pressione",
          sort_order: 10,
          distretti_count: 1,
          particelle_count: 1,
          ruolo_particelle_count: 0,
          particelle_con_anagrafica_count: 0,
          particelle_senza_ruolo_count: 1,
          particelle_senza_anagrafica_count: 1,
          superficie_catastale_mq: "0",
          superficie_irrigata_ha: "0",
          importo_stimato: "0",
          importo_ruolo: "0",
          importo_ruolo_manutenzione: "0",
          importo_ruolo_irrigazione: "0",
          importo_ruolo_istituzionale: "0",
          ruolo_metrics_reliable: false,
          ruolo_metrics_valid_count: 0,
          ruolo_metrics_invalid_count: 1,
          ruolo_metrics_warning: null,
          hectares_reference_total: "0",
          distretti: [],
          comuni: [],
          distretti_analytics: [],
          colture: [],
        },
      ],
    });

    render(<CatastoIndiciPage />);

    expect(await screen.findByText(/temporaneamente sospesi/)).toBeInTheDocument();
  });

  test("does not call the API when the access token is missing", () => {
    mocks.getStoredAccessToken.mockReturnValue(null);

    render(<CatastoIndiciPage />);

    expect(mocks.catastoGetIndiciOverview).not.toHaveBeenCalled();
    expect(screen.getByText("Caricamento quadro distretti...")).toBeInTheDocument();
    expect(screen.getAllByText("Nessun dato disponibile.").length).toBeGreaterThan(0);
  });

  test("shows API errors with explicit and fallback messages", async () => {
    mocks.catastoGetIndiciOverview.mockRejectedValueOnce(new Error("Errore controllato"));
    const { unmount } = render(<CatastoIndiciPage />);

    expect(await screen.findByText("Errore controllato")).toBeInTheDocument();

    unmount();
    mocks.catastoGetIndiciOverview.mockRejectedValueOnce("errore non standard");
    render(<CatastoIndiciPage />);

    expect(await screen.findByText("Errore caricamento indici")).toBeInTheDocument();
  });

  test("falls back to an empty overview when no indice items are returned", async () => {
    mocks.catastoGetIndiciOverview.mockResolvedValue({
      anno_riferimento: null,
      total_distretti: 0,
      total_particelle: 0,
      available_colture: [],
      items: [],
    });

    render(<CatastoIndiciPage />);

    expect(await screen.findByText("Nessun distretto disponibile.")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Indice" })).toBeInTheDocument();
    expect(screen.getAllByText("Nessun dato disponibile.").length).toBeGreaterThan(0);
  });

  test("selects the first returned indice when alta pressione is not present", async () => {
    mocks.catastoGetIndiciOverview.mockResolvedValue({
      anno_riferimento: 2025,
      total_distretti: 1,
      total_particelle: 0,
      available_colture: [],
      items: [
        {
          indice_key: "non_classificato",
          indice_label: "Non classificato",
          sort_order: 99,
          distretti_count: 1,
          particelle_count: 0,
          ruolo_particelle_count: 0,
          particelle_con_anagrafica_count: 0,
          particelle_senza_ruolo_count: 0,
          particelle_senza_anagrafica_count: 0,
          superficie_catastale_mq: "0",
          superficie_irrigata_ha: "0",
          importo_stimato: "0",
          importo_ruolo: "0",
          importo_ruolo_manutenzione: "0",
          importo_ruolo_irrigazione: "0",
          importo_ruolo_istituzionale: "0",
          ruolo_metrics_reliable: true,
          ruolo_metrics_valid_count: 0,
          ruolo_metrics_invalid_count: 0,
          ruolo_metrics_warning: null,
          hectares_reference_total: null,
          distretti: [],
          comuni: [],
          distretti_analytics: [],
          colture: [],
        },
      ],
    });

    render(<CatastoIndiciPage />);

    expect(await screen.findByText("Cosa contiene questo blocco")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Non classificato" })).toBeInTheDocument();
    expect(screen.getByText(/raggruppamenti fuori quadro/)).toBeInTheDocument();
    expect(screen.getAllByText("—").length).toBeGreaterThan(0);
  });
});
