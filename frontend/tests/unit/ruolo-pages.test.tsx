import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import RuoloAvvisiPage from "@/app/ruolo/avvisi/page";
import RuoloCapacitasChecksPage from "@/app/ruolo/controlli-capacitas/page";
import RuoloParticellePage from "@/app/ruolo/particelle/page";
import RuoloDashboardPage from "@/app/ruolo/page";
import RuoloImportPage from "@/app/ruolo/import/page";
import RuoloStatsPage from "@/app/ruolo/stats/page";

const mocks = vi.hoisted(() => ({
  getStoredAccessToken: vi.fn(),
  searchUtenzeSubjects: vi.fn(),
  getRuoloStats: vi.fn(),
  getRuoloCapacitasCheck: vi.fn(),
  getRuoloCapacitasCheckComuni: vi.fn(),
  getRuoloStatsAnalytics: vi.fn(),
  getRuoloParticelleSummary: vi.fn(),
  listImportJobs: vi.fn(),
  listAvvisi: vi.fn(),
  listRuoloParticelle: vi.fn(),
  push: vi.fn(),
  replace: vi.fn(),
  searchParams: new URLSearchParams(),
}));

vi.mock("@/lib/auth", () => ({
  getStoredAccessToken: mocks.getStoredAccessToken,
}));

vi.mock("@/lib/api", () => ({
  searchUtenzeSubjects: mocks.searchUtenzeSubjects,
}));

vi.mock("@/lib/ruolo-api", () => ({
  getRuoloStats: mocks.getRuoloStats,
  getRuoloCapacitasCheck: mocks.getRuoloCapacitasCheck,
  getRuoloCapacitasCheckComuni: mocks.getRuoloCapacitasCheckComuni,
  getRuoloStatsAnalytics: mocks.getRuoloStatsAnalytics,
  getRuoloParticelleSummary: mocks.getRuoloParticelleSummary,
  listImportJobs: mocks.listImportJobs,
  listAvvisi: mocks.listAvvisi,
  listRuoloParticelle: mocks.listRuoloParticelle,
  formatRuoloCapacitasCheckStatus: (status: string) => ({
    amount_mismatch: "Importi non allineati",
    only_in_ruolo: "Presente solo nel ruolo",
    only_in_capacitas: "Presente solo in Capacitas",
    matched: "Allineato",
  }[status] ?? status),
  getRuoloCapacitasCheckStatusBadgeClassName: (status: string) => ({
    amount_mismatch: "bg-amber-50 text-amber-800 border border-amber-200",
    only_in_ruolo: "bg-sky-50 text-sky-800 border border-sky-200",
    only_in_capacitas: "bg-fuchsia-50 text-fuchsia-800 border border-fuchsia-200",
    matched: "bg-emerald-50 text-emerald-800 border border-emerald-200",
  }[status] ?? "bg-gray-100 text-gray-700 border border-gray-200"),
  buildExportCsvUrl: vi.fn(() => "/api/ruolo/avvisi/export"),
  buildRuoloCapacitasCheckExportUrl: vi.fn(() => "/api/ruolo/stats/capacitas-check/export?anno=2025"),
  detectRuoloImportYear: vi.fn(),
  getImportJob: vi.fn(),
  uploadRuoloFile: vi.fn(),
}));

vi.mock("@/components/app/protected-page", () => ({
  ProtectedPage: ({
    children,
    title,
    topbarActions,
  }: {
    children: React.ReactNode;
    title: string;
    topbarActions?: React.ReactNode;
  }) => (
    <div>
      <h1>{title}</h1>
      {topbarActions}
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
    LineChart: Wrapper,
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
    mocks.searchUtenzeSubjects.mockReset();
    mocks.getRuoloCapacitasCheck.mockReset();
    mocks.getRuoloCapacitasCheckComuni.mockReset();
    mocks.getRuoloStatsAnalytics.mockReset();
    mocks.getRuoloParticelleSummary.mockReset();
    mocks.listImportJobs.mockReset();
    mocks.listAvvisi.mockReset();
    mocks.listRuoloParticelle.mockReset();
  });

  test("ruolo dashboard renders readable backfill labels and trend section", async () => {
    mocks.getRuoloStats.mockResolvedValue({
      items: [
        {
          anno_tributario: 2024,
          total_avvisi: 10,
          avvisi_collegati: 9,
          avvisi_non_collegati: 1,
          totale_0648: 800,
          totale_0985: 100,
          totale_0668: 100,
          totale_euro: 1000,
        },
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
    mocks.getRuoloParticelleSummary.mockResolvedValue({
      anno_tributario: null,
      total_particelle: 120,
      collegate_catasto: 90,
      non_collegate_catasto: 30,
      soppresse_ade: 4,
    });
    mocks.getRuoloCapacitasCheck.mockResolvedValue({
      summary: {
        anno_tributario: 2025,
        ruolo_positions: 2,
        capacitas_positions: 2,
        matched_positions: 1,
        only_in_ruolo: 1,
        only_in_capacitas: 1,
        ruolo_positions_missing_tax_code: 0,
        capacitas_positions_missing_tax_code: 0,
        ruolo_totale_0648: 1000,
        capacitas_totale_0648: 950,
        delta_totale_0648: 50,
        ruolo_totale_0985: 300,
        capacitas_totale_0985: 280,
        delta_totale_0985: 20,
        ruolo_totale_0668: 200,
        ruolo_totale_confrontabile: 1300,
        capacitas_totale_confrontabile: 1230,
        delta_totale_confrontabile: 70,
        mismatch_positions: 2,
      },
      items: [
        {
          tax_code: "RSSMRA80A01H501Z",
          ruolo_display_name: "ROSSI MARIO",
          capacitas_display_name: "ROSSI MARIO",
          status: "amount_mismatch",
          ruolo_0648: 100,
          capacitas_0648: 90,
          delta_0648: 10,
          ruolo_0985: 50,
          capacitas_0985: 50,
          delta_0985: 0,
          ruolo_totale_confrontabile: 150,
          capacitas_totale_confrontabile: 140,
          delta_totale_confrontabile: 10,
        },
      ],
    });
    mocks.getRuoloCapacitasCheckComuni.mockResolvedValue({
      anno_tributario: 2025,
      items: [
        {
          comune_nome: "Oristano",
          ruolo_0648: 500,
          capacitas_0648: 450,
          delta_0648: 50,
          ruolo_0985: 100,
          capacitas_0985: 80,
          delta_0985: 20,
          ruolo_totale_confrontabile: 600,
          capacitas_totale_confrontabile: 530,
          delta_totale_confrontabile: 70,
        },
      ],
    });
    mocks.listImportJobs.mockResolvedValue({
      items: [
        {
          id: "job-1",
          anno_tributario: 2023,
          filename: "incass_backfill_2023",
          status: "completed",
          started_at: "2026-06-04T10:00:00Z",
          finished_at: "2026-06-04T10:30:00Z",
          total_partite: 100,
          records_imported: 95,
          records_skipped: 5,
          records_errors: 0,
          error_detail: null,
          triggered_by: 1,
          params_json: null,
          created_at: "2026-06-04T10:00:00Z",
        },
      ],
      total: 1,
      page: 1,
      page_size: 5,
    });

    render(<RuoloDashboardPage />);

    await waitFor(() => expect(screen.getByText("Trend ruolo")).toBeInTheDocument());
    await waitFor(() => expect(screen.getByText("ROSSI MARIO")).toBeInTheDocument());
    expect(screen.getByText("Importi non allineati")).toBeInTheDocument();
    expect(screen.getByText("Verifica economica ruolo vs Capacitas 2025")).toBeInTheDocument();
    expect(screen.getByText("Principali scostamenti da verificare")).toBeInTheDocument();
    expect(screen.getByText("Confronto per comune")).toBeInTheDocument();
    expect(screen.getByText("Oristano")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Esporta CSV scostamenti" })).toHaveAttribute("href", "/api/ruolo/stats/capacitas-check/export?anno=2025");
    expect(screen.getByText("Recupero storico InCass 2023")).toBeInTheDocument();
    expect(screen.getByText("Recupero storico degli avvisi e del partitario da InCass.")).toBeInTheDocument();
    expect(screen.getByText("Completato")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Apri analisi completa" })).toHaveAttribute("href", "/ruolo/stats");
    expect(screen.getByText("Avvisi orfani per annualità")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Apri avvisi" }));
    await waitFor(() => expect(screen.getByText("Avvisi collegati allo scostamento")).toBeInTheDocument());
    expect(screen.getByRole("link", { name: "Apri pagina" })).toHaveAttribute(
      "href",
      "/ruolo/avvisi?anno=2025&codice_fiscale=RSSMRA80A01H501Z&focus=mismatch",
    );
    expect(screen.getByTitle("Avvisi collegati allo scostamento")).toHaveAttribute(
      "src",
      "/ruolo/avvisi?anno=2025&codice_fiscale=RSSMRA80A01H501Z&focus=mismatch&embedded=1",
    );
  });

  test("ruolo capacitas checks page renders dedicated supervision console", async () => {
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
    mocks.getRuoloCapacitasCheck.mockResolvedValue({
      summary: {
        anno_tributario: 2025,
        ruolo_positions: 2,
        capacitas_positions: 2,
        matched_positions: 1,
        only_in_ruolo: 1,
        only_in_capacitas: 1,
        ruolo_positions_missing_tax_code: 0,
        capacitas_positions_missing_tax_code: 0,
        ruolo_totale_0648: 1000,
        capacitas_totale_0648: 950,
        delta_totale_0648: 50,
        ruolo_totale_0985: 300,
        capacitas_totale_0985: 280,
        delta_totale_0985: 20,
        ruolo_totale_0668: 200,
        ruolo_totale_confrontabile: 1300,
        capacitas_totale_confrontabile: 1230,
        delta_totale_confrontabile: 70,
        mismatch_positions: 2,
      },
      items: [
        {
          tax_code: "RSSMRA80A01H501Z",
          ruolo_display_name: "ROSSI MARIO",
          capacitas_display_name: "ROSSI MARIO",
          status: "amount_mismatch",
          ruolo_0648: 100,
          capacitas_0648: 90,
          delta_0648: 10,
          ruolo_0985: 50,
          capacitas_0985: 50,
          delta_0985: 0,
          ruolo_totale_confrontabile: 150,
          capacitas_totale_confrontabile: 140,
          delta_totale_confrontabile: 10,
        },
      ],
    });
    mocks.getRuoloCapacitasCheckComuni.mockResolvedValue({
      anno_tributario: 2025,
      items: [
        {
          comune_nome: "Oristano",
          ruolo_0648: 500,
          capacitas_0648: 450,
          delta_0648: 50,
          ruolo_0985: 100,
          capacitas_0985: 80,
          delta_0985: 20,
          ruolo_totale_confrontabile: 600,
          capacitas_totale_confrontabile: 530,
          delta_totale_confrontabile: 70,
        },
      ],
    });
    mocks.listAvvisi.mockResolvedValue({
      items: [
        {
          id: "avviso-1",
          codice_cnc: "CNC-001",
          anno_tributario: 2025,
          subject_id: "subject-1",
          codice_fiscale_raw: "RSSMRA80A01H501Z",
          nominativo_raw: "ROSSI MARIO",
          codice_utenza: "U12345",
          importo_totale_0648: 100,
          importo_totale_0985: 50,
          importo_totale_0668: 0,
          importo_totale_euro: 150,
          display_name: "ROSSI MARIO",
          is_linked: true,
          created_at: "2026-06-16T09:00:00Z",
          updated_at: "2026-06-16T09:00:00Z",
        },
      ],
      total: 1,
      page: 1,
      page_size: 10,
    });

    render(<RuoloCapacitasChecksPage />);

    await waitFor(() => expect(screen.getByText("Console di controllo ruolo vs Capacitas.")).toBeInTheDocument());
    await waitFor(() => expect(screen.getByText("ROSSI MARIO")).toBeInTheDocument());
    expect(screen.getByText("Importi non allineati")).toBeInTheDocument();
    expect(screen.getByText("Scostamenti aggregati territorio per territorio.")).toBeInTheDocument();
    expect(screen.getByText("Oristano")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Esporta CSV" })).toHaveAttribute("href", "/api/ruolo/stats/capacitas-check/export?anno=2025&token=token");
    fireEvent.click(screen.getByRole("button", { name: "Apri avviso" }));
    await waitFor(() => expect(mocks.listAvvisi).toHaveBeenCalledWith("token", expect.objectContaining({
      anno: 2025,
      codice_fiscale: "RSSMRA80A01H501Z",
      page: 1,
      page_size: 10,
    })));
    await waitFor(() => expect(screen.getByText("Dettaglio avviso")).toBeInTheDocument());
    expect(screen.getByRole("link", { name: "Apri pagina" })).toHaveAttribute(
      "href",
      "/ruolo/avvisi/avviso-1",
    );
    expect(screen.getByTitle("Dettaglio avviso")).toHaveAttribute(
      "src",
      "/ruolo/avvisi/avviso-1?embedded=1",
    );
  });

  test("ruolo capacitas checks page shows empty-state copy when no mismatches are returned", async () => {
    mocks.getRuoloStats.mockResolvedValue({
      items: [
        {
          anno_tributario: 2025,
          total_avvisi: 12,
          avvisi_collegati: 12,
          avvisi_non_collegati: 0,
          totale_0648: 1000,
          totale_0985: 300,
          totale_0668: 200,
          totale_euro: 1500,
        },
      ],
    });
    mocks.getRuoloCapacitasCheck.mockResolvedValue({
      summary: {
        anno_tributario: 2025,
        ruolo_positions: 2,
        capacitas_positions: 2,
        matched_positions: 2,
        only_in_ruolo: 0,
        only_in_capacitas: 0,
        ruolo_positions_missing_tax_code: 0,
        capacitas_positions_missing_tax_code: 0,
        ruolo_totale_0648: 1000,
        capacitas_totale_0648: 1000,
        delta_totale_0648: 0,
        ruolo_totale_0985: 300,
        capacitas_totale_0985: 300,
        delta_totale_0985: 0,
        ruolo_totale_0668: 200,
        ruolo_totale_confrontabile: 1300,
        capacitas_totale_confrontabile: 1300,
        delta_totale_confrontabile: 0,
        mismatch_positions: 0,
      },
      items: [],
    });
    mocks.getRuoloCapacitasCheckComuni.mockResolvedValue({
      anno_tributario: 2025,
      items: [],
    });

    render(<RuoloCapacitasChecksPage />);

    await waitFor(() => expect(screen.getByText("Nessun mismatch rilevato")).toBeInTheDocument());
    await waitFor(() =>
      expect(
        screen.getByText(
          "Per l'anno selezionato non risultano scostamenti oltre soglia sul confronto per chiave fiscale.",
        ),
      ).toBeInTheDocument(),
    );
  });

  test("ruolo import renders readable job labels and statuses", async () => {
    mocks.listImportJobs.mockResolvedValue({
      items: [
        {
          id: "job-2",
          anno_tributario: 2023,
          filename: "incass_backfill_2023",
          status: "completed",
          started_at: "2026-06-04T10:00:00Z",
          finished_at: "2026-06-04T10:30:00Z",
          total_partite: 100,
          records_imported: 95,
          records_skipped: 5,
          records_errors: 0,
          error_detail: null,
          triggered_by: 1,
          params_json: null,
          created_at: "2026-06-04T10:00:00Z",
        },
      ],
      total: 1,
      page: 1,
      page_size: 20,
    });

    render(<RuoloImportPage />);

    await waitFor(() => expect(screen.getByText("Recupero storico InCass 2023")).toBeInTheDocument());
    expect(screen.getAllByText("Completato").length).toBeGreaterThan(0);
    expect(screen.getByText("Recupero storico degli avvisi e del partitario da InCass.")).toBeInTheDocument();
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
