import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import RuoloAvvisiPage from "@/app/ruolo/avvisi/page";
import RuoloParticellePage from "@/app/ruolo/particelle/page";
import RuoloStatsPage from "@/app/ruolo/stats/page";

const mocks = vi.hoisted(() => ({
  getStoredAccessToken: vi.fn(),
  getRuoloStats: vi.fn(),
  getRuoloStatsAnalytics: vi.fn(),
  listAvvisi: vi.fn(),
  listRuoloParticelle: vi.fn(),
  push: vi.fn(),
  replace: vi.fn(),
  searchParams: new URLSearchParams(),
}));

vi.mock("@/lib/auth", () => ({
  getStoredAccessToken: mocks.getStoredAccessToken,
}));

vi.mock("@/lib/ruolo-api", () => ({
  getRuoloStats: mocks.getRuoloStats,
  getRuoloStatsAnalytics: mocks.getRuoloStatsAnalytics,
  listAvvisi: mocks.listAvvisi,
  listRuoloParticelle: mocks.listRuoloParticelle,
  buildExportCsvUrl: vi.fn(() => "/api/ruolo/avvisi/export"),
}));

vi.mock("@/components/app/protected-page", () => ({
  ProtectedPage: ({ children, title }: { children: React.ReactNode; title: string }) => (
    <div>
      <h1>{title}</h1>
      {children}
    </div>
  ),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mocks.push, replace: mocks.replace }),
  useSearchParams: () => mocks.searchParams,
}));

vi.mock("recharts", () => {
  function Wrapper({ children }: { children?: React.ReactNode }) {
    return <div>{children}</div>;
  }

  return {
    ResponsiveContainer: Wrapper,
    ComposedChart: Wrapper,
    BarChart: Wrapper,
    PieChart: Wrapper,
    CartesianGrid: () => <div />,
    XAxis: () => <div />,
    YAxis: () => <div />,
    Tooltip: () => <div />,
    Legend: () => <div />,
    Bar: () => <div />,
    Line: () => <div />,
    Pie: Wrapper,
    Cell: () => <div />,
  };
});

describe("Ruolo pages", () => {
  beforeEach(() => {
    mocks.getStoredAccessToken.mockReturnValue("token");
    mocks.searchParams = new URLSearchParams();
    mocks.push.mockReset();
    mocks.replace.mockReset();
    mocks.getRuoloStats.mockReset();
    mocks.getRuoloStatsAnalytics.mockReset();
    mocks.listAvvisi.mockReset();
    mocks.listRuoloParticelle.mockReset();
  });

  test("ruolo stats renders analytics links for selected anno and top comune", async () => {
    mocks.getRuoloStats.mockResolvedValue({
      items: [
        {
          anno_tributario: 2025,
          total_avvisi: 12,
          avvisi_collegati: 10,
          avvisi_non_collegati: 2,
          totale_0648: 1000,
          totale_0985: 300,
          totale_0668: 200,
          totale_euro: 1500,
        },
      ],
    });
    mocks.getRuoloStatsAnalytics.mockResolvedValue({
      anno_tributario: 2025,
      particelle_summary: {
        anno_tributario: 2025,
        total_particelle: 80,
        collegate_catasto: 65,
        non_collegate_catasto: 15,
        soppresse_ade: 3,
      },
      tributi_breakdown: [
        { key: "0648", label: "0648 Manutenzione", amount: 1000 },
        { key: "0985", label: "0985 Irrigazione", amount: 300 },
        { key: "0668", label: "0668 Istituzionale", amount: 200 },
      ],
      match_status_breakdown: [
        { key: "matched", label: "matched", count: 65 },
        { key: "unmatched", label: "unmatched", count: 15 },
      ],
      match_reason_breakdown: [
        { key: "no_cat_particella_match", label: "no cat particella match", count: 10 },
      ],
      distretto_breakdown: [
        { key: "10", label: "10", count: 50 },
      ],
      coltura_breakdown: [
        { key: "MAIS", label: "MAIS", count: 30 },
      ],
      comuni: [
        {
          comune_nome: "Marrubiu",
          anno_tributario: 2025,
          totale_0648: 700,
          totale_0985: 200,
          totale_0668: 100,
          totale_euro: 1000,
          num_avvisi: 5,
          num_partite: 6,
          num_particelle: 40,
          non_collegate_catasto: 8,
        },
      ],
    });

    render(<RuoloStatsPage />);

    await waitFor(() => expect(mocks.getRuoloStats).toHaveBeenCalledWith("token"));
    await waitFor(() => expect(mocks.getRuoloStatsAnalytics).toHaveBeenCalledWith("token", 2025));
    await waitFor(() => expect(screen.getByText("Comune leader: Marrubiu")).toBeInTheDocument());

    expect(screen.getByText("Trend storico annualità")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Apri avvisi dell'anno" })).toHaveAttribute("href", "/ruolo/avvisi?anno=2025");
    expect(screen.getByRole("link", { name: "Apri avvisi orfani" })).toHaveAttribute("href", "/ruolo/avvisi?anno=2025&unlinked=true");
    expect(screen.getByRole("link", { name: "Avvisi" })).toHaveAttribute("href", "/ruolo/avvisi?anno=2025&comune=Marrubiu");
  });

  test("ruolo avvisi applies anno and comune filters from search params", async () => {
    mocks.searchParams = new URLSearchParams("anno=2025&comune=Oristano&unlinked=true");
    mocks.listAvvisi.mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 25,
    });

    render(<RuoloAvvisiPage />);

    await waitFor(() => {
      expect(mocks.listAvvisi).toHaveBeenCalledWith("token", {
        anno: 2025,
        comune: "Oristano",
        q: undefined,
        unlinked: true,
        page: 1,
        page_size: 25,
      });
    });

    expect(screen.getByText(/Anno 2025\./)).toBeInTheDocument();
    expect(screen.getByText(/Comune Oristano\./)).toBeInTheDocument();
  });

  test("ruolo particelle applies match filters from search params", async () => {
    mocks.searchParams = new URLSearchParams(
      "anno=2025&comune=Oristano&match_status=unmatched&match_reason=no_cat_particella_match",
    );
    mocks.listRuoloParticelle.mockResolvedValue([
      {
        id: "11111111-1111-1111-1111-111111111111",
        partita_id: "22222222-2222-2222-2222-222222222222",
        anno_tributario: 2025,
        comune_nome: "Oristano",
        comune_codice: "G113",
        domanda_irrigua: null,
        distretto: "10",
        foglio: "1",
        particella: "100",
        subalterno: null,
        sup_catastale_are: null,
        sup_catastale_ha: null,
        sup_irrigata_ha: null,
        coltura: null,
        importo_manut: 10,
        importo_irrig: 0,
        importo_ist: 0,
        catasto_parcel_id: null,
        cat_particella_id: null,
        cat_particella_match_status: "unmatched",
        cat_particella_match_confidence: null,
        cat_particella_match_reason: "no_cat_particella_match",
        ade_scan_status: null,
        ade_scan_classification: null,
        created_at: "2026-06-04T12:00:00Z",
      },
    ]);

    render(<RuoloParticellePage />);

    await waitFor(() => {
      expect(mocks.listRuoloParticelle).toHaveBeenCalledWith("token", {
        comune: "Oristano",
        foglio: undefined,
        particella: undefined,
        anno: 2025,
        match_status: "unmatched",
        match_reason: "no_cat_particella_match",
        unmatched_only: true,
        page: 1,
        page_size: 50,
      });
    });

    expect(screen.getByDisplayValue("unmatched")).toBeInTheDocument();
    expect(screen.getByDisplayValue("no_cat_particella_match")).toBeInTheDocument();
    expect(screen.getByText("Reason: no_cat_particella_match")).toBeInTheDocument();
  });
});
