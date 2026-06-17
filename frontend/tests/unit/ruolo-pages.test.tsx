import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import RuoloAvvisiPage from "@/app/ruolo/avvisi/page";
import RuoloGaiaCalculationPage from "@/app/ruolo/calcolo-gaia/page";
import RuoloCapacitasChecksPage from "@/app/ruolo/controlli-capacitas/page";
import RuoloParticellePage from "@/app/ruolo/particelle/page";
import RuoloDashboardPage from "@/app/ruolo/page";
import RuoloImportPage from "@/app/ruolo/import/page";
import RuoloStatsPage from "@/app/ruolo/stats/page";

const mocks = vi.hoisted(() => ({
  getStoredAccessToken: vi.fn(),
  searchUtenzeSubjects: vi.fn(),
  getUtenzeSubjectPaymentNotices: vi.fn(),
  getRuoloStats: vi.fn(),
  getRuoloCapacitasCheck: vi.fn(),
  getRuoloCapacitasCheckComuni: vi.fn(),
  getRuoloCapacitasCalculationDetail: vi.fn(),
  getRuoloGaiaCalculation: vi.fn(),
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
  getUtenzeSubjectPaymentNotices: mocks.getUtenzeSubjectPaymentNotices,
}));

vi.mock("@/lib/ruolo-api", () => ({
  getRuoloStats: mocks.getRuoloStats,
  getRuoloCapacitasCheck: mocks.getRuoloCapacitasCheck,
  getRuoloCapacitasCheckComuni: mocks.getRuoloCapacitasCheckComuni,
  getRuoloCapacitasCalculationDetail: mocks.getRuoloCapacitasCalculationDetail,
  getRuoloGaiaCalculation: mocks.getRuoloGaiaCalculation,
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
  buildRuoloGaiaCalculationExportUrl: vi.fn(() => "/api/ruolo/stats/calcolo-gaia/export?anno=2025"),
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
    mocks.getUtenzeSubjectPaymentNotices.mockReset();
    mocks.getRuoloCapacitasCheck.mockReset();
    mocks.getRuoloCapacitasCheckComuni.mockReset();
    mocks.getRuoloCapacitasCalculationDetail.mockReset();
    mocks.getRuoloGaiaCalculation.mockReset();
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
        capacitas_active_batch_id: "batch-2025",
        matched_positions: 1,
        only_in_ruolo: 1,
        only_in_capacitas: 1,
        ruolo_positions_missing_tax_code: 0,
        capacitas_positions_missing_tax_code: 0,
        ruolo_totale_0648: 1000,
        gaia_totale_0648: 950,
        excel_totale_0648: 955,
        delta_totale_0648: 50,
        delta_gaia_excel_totale_0648: -5,
        ruolo_totale_0985: 300,
        gaia_totale_0985: 280,
        excel_totale_0985: 282,
        delta_totale_0985: 20,
        delta_gaia_excel_totale_0985: -2,
        ruolo_totale_0668: 200,
        ruolo_totale_confrontabile: 1300,
        gaia_totale_confrontabile: 1230,
        excel_totale_confrontabile: 1237,
        delta_totale_confrontabile: 70,
        delta_gaia_excel_totale_confrontabile: -7,
        mismatch_positions: 2,
        diagnosis_ruolo_count: 1,
        diagnosis_gaia_count: 1,
        diagnosis_excel_count: 0,
      },
      items: [
        {
          tax_code: "RSSMRA80A01H501Z",
          ruolo_display_name: "ROSSI MARIO",
          capacitas_display_name: "ROSSI MARIO",
          status: "amount_mismatch",
          diagnosis: "problema_ruolo",
          ruolo_0648: 100,
          gaia_0648: 90,
          excel_0648: 92,
          delta_0648: 10,
          delta_gaia_excel_0648: -2,
          ruolo_0985: 50,
          gaia_0985: 50,
          excel_0985: 49,
          delta_0985: 0,
          delta_gaia_excel_0985: 1,
          ruolo_totale_confrontabile: 150,
          gaia_totale_confrontabile: 140,
          excel_totale_confrontabile: 141,
          delta_totale_confrontabile: 10,
          delta_gaia_excel_totale_confrontabile: -1,
          anomalous_rows_count: 1,
          clean_rows_count: 0,
          anomaly_gap_share: 100,
          anomaly_driven_case: true,
        },
      ],
    });
    mocks.getRuoloCapacitasCheckComuni.mockResolvedValue({
      anno_tributario: 2025,
      items: [
        {
          comune_nome: "Oristano",
          capacitas_active_batch_id: "batch-2025",
          ruolo_0648: 500,
          gaia_0648: 450,
          excel_0648: 455,
          delta_0648: 50,
          delta_gaia_excel_0648: -5,
          ruolo_0985: 100,
          gaia_0985: 80,
          excel_0985: 82,
          delta_0985: 20,
          delta_gaia_excel_0985: -2,
          ruolo_totale_confrontabile: 600,
          gaia_totale_confrontabile: 530,
          excel_totale_confrontabile: 537,
          delta_totale_confrontabile: 70,
          delta_gaia_excel_totale_confrontabile: -7,
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

    render(<RuoloDashboardPage />);

    await waitFor(() => expect(screen.getByText("Trend ruolo")).toBeInTheDocument());
    await waitFor(() => expect(screen.getByText("ROSSI MARIO")).toBeInTheDocument());
    expect(screen.getByText("Importi non allineati")).toBeInTheDocument();
    expect(screen.getByText("Ingresso rapido alla console di calcolo ruolo 2025")).toBeInTheDocument();
    expect(screen.getByText("Principali scostamenti da verificare")).toBeInTheDocument();
    expect(screen.getByText("Confronto per comune")).toBeInTheDocument();
    expect(screen.getByText("Oristano")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Esporta CSV scostamenti" })).toHaveAttribute("href", "/api/ruolo/stats/capacitas-check/export?anno=2025");
    expect(screen.getByText("Materializzazione ruolo da InCass 2023")).toBeInTheDocument();
    expect(screen.getByText("Materializzazione del read-model ruolo a partire da avvisi e partitario InCass.")).toBeInTheDocument();
    expect(screen.getByText("Completato")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Apri calcolo ruolo" })).toHaveAttribute("href", "/ruolo/calcolo-gaia");
    expect(screen.getByText("Avvisi orfani per annualità")).toBeInTheDocument();

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
        capacitas_active_batch_id: "batch-2025",
        matched_positions: 1,
        only_in_ruolo: 1,
        only_in_capacitas: 1,
        ruolo_positions_missing_tax_code: 0,
        capacitas_positions_missing_tax_code: 0,
        ruolo_totale_0648: 1000,
        gaia_totale_0648: 950,
        excel_totale_0648: 955,
        delta_totale_0648: 50,
        delta_gaia_excel_totale_0648: -5,
        ruolo_totale_0985: 300,
        gaia_totale_0985: 280,
        excel_totale_0985: 282,
        delta_totale_0985: 20,
        delta_gaia_excel_totale_0985: -2,
        ruolo_totale_0668: 200,
        ruolo_totale_confrontabile: 1300,
        gaia_totale_confrontabile: 1230,
        excel_totale_confrontabile: 1237,
        delta_totale_confrontabile: 70,
        delta_gaia_excel_totale_confrontabile: -7,
        mismatch_positions: 2,
        diagnosis_ruolo_count: 1,
        diagnosis_gaia_count: 1,
        diagnosis_excel_count: 0,
      },
      items: [
        {
          tax_code: "RSSMRA80A01H501Z",
          ruolo_display_name: "ROSSI MARIO",
          capacitas_display_name: "ROSSI MARIO",
          status: "amount_mismatch",
          diagnosis: "problema_ruolo",
          ruolo_0648: 100,
          gaia_0648: 90,
          excel_0648: 92,
          delta_0648: 10,
          delta_gaia_excel_0648: -2,
          ruolo_0985: 50,
          gaia_0985: 50,
          excel_0985: 49,
          delta_0985: 0,
          delta_gaia_excel_0985: 1,
          ruolo_totale_confrontabile: 150,
          gaia_totale_confrontabile: 140,
          excel_totale_confrontabile: 141,
          delta_totale_confrontabile: 10,
          delta_gaia_excel_totale_confrontabile: -1,
          anomalous_rows_count: 1,
          clean_rows_count: 0,
          anomaly_gap_share: 100,
          anomaly_driven_case: true,
        },
      ],
    });
    mocks.getRuoloCapacitasCheckComuni.mockResolvedValue({
      anno_tributario: 2025,
      items: [
        {
          comune_nome: "Oristano",
          capacitas_active_batch_id: "batch-2025",
          ruolo_0648: 500,
          gaia_0648: 450,
          excel_0648: 455,
          delta_0648: 50,
          delta_gaia_excel_0648: -5,
          ruolo_0985: 100,
          gaia_0985: 80,
          excel_0985: 82,
          delta_0985: 20,
          delta_gaia_excel_0985: -2,
          ruolo_totale_confrontabile: 600,
          gaia_totale_confrontabile: 530,
          excel_totale_confrontabile: 537,
          delta_totale_confrontabile: 70,
          delta_gaia_excel_totale_confrontabile: -7,
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
        capacitas_active_batch_id: "batch-2025",
        matched_positions: 2,
        only_in_ruolo: 0,
        only_in_capacitas: 0,
        ruolo_positions_missing_tax_code: 0,
        capacitas_positions_missing_tax_code: 0,
        ruolo_totale_0648: 1000,
        gaia_totale_0648: 1000,
        excel_totale_0648: 1000,
        delta_totale_0648: 0,
        delta_gaia_excel_totale_0648: 0,
        ruolo_totale_0985: 300,
        gaia_totale_0985: 300,
        excel_totale_0985: 300,
        delta_totale_0985: 0,
        delta_gaia_excel_totale_0985: 0,
        ruolo_totale_0668: 200,
        ruolo_totale_confrontabile: 1300,
        gaia_totale_confrontabile: 1300,
        excel_totale_confrontabile: 1300,
        delta_totale_confrontabile: 0,
        delta_gaia_excel_totale_confrontabile: 0,
        mismatch_positions: 0,
        diagnosis_ruolo_count: 0,
        diagnosis_gaia_count: 0,
        diagnosis_excel_count: 0,
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

  test("ruolo capacitas checks page explains missing ruolo when the subject exists only in Capacitas", async () => {
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
        ruolo_positions: 1,
        capacitas_positions: 1,
        capacitas_active_batch_id: "batch-2025",
        matched_positions: 0,
        only_in_ruolo: 0,
        only_in_capacitas: 1,
        ruolo_positions_missing_tax_code: 0,
        capacitas_positions_missing_tax_code: 0,
        ruolo_totale_0648: 0,
        gaia_totale_0648: 100,
        excel_totale_0648: 100,
        delta_totale_0648: -100,
        delta_gaia_excel_totale_0648: 0,
        ruolo_totale_0985: 0,
        gaia_totale_0985: 50,
        excel_totale_0985: 50,
        delta_totale_0985: -50,
        delta_gaia_excel_totale_0985: 0,
        ruolo_totale_0668: 0,
        ruolo_totale_confrontabile: 0,
        gaia_totale_confrontabile: 150,
        excel_totale_confrontabile: 150,
        delta_totale_confrontabile: -150,
        delta_gaia_excel_totale_confrontabile: 0,
        mismatch_positions: 1,
        diagnosis_ruolo_count: 1,
        diagnosis_gaia_count: 0,
        diagnosis_excel_count: 0,
      },
      items: [
        {
          tax_code: "MRGMRZ60P18A357G",
          ruolo_display_name: null,
          capacitas_display_name: "MOREGGIO MAURIZIO",
          status: "only_in_capacitas",
          diagnosis: "problema_ruolo",
          ruolo_0648: 0,
          gaia_0648: 100,
          excel_0648: 100,
          delta_0648: -100,
          delta_gaia_excel_0648: 0,
          ruolo_0985: 0,
          gaia_0985: 50,
          excel_0985: 50,
          delta_0985: -50,
          delta_gaia_excel_0985: 0,
          ruolo_totale_confrontabile: 0,
          gaia_totale_confrontabile: 150,
          excel_totale_confrontabile: 150,
          delta_totale_confrontabile: -150,
          delta_gaia_excel_totale_confrontabile: 0,
          anomalous_rows_count: 1,
          clean_rows_count: 0,
          anomaly_gap_share: 100,
          anomaly_driven_case: true,
        },
      ],
    });
    mocks.getRuoloCapacitasCheckComuni.mockResolvedValue({
      anno_tributario: 2025,
      items: [],
    });

    render(<RuoloCapacitasChecksPage />);

    await waitFor(() => expect(screen.getByText("MOREGGIO MAURIZIO")).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: "Apri avviso" }));
    await waitFor(() => expect(screen.getByText("Nessun avviso ruolo in GAIA")).toBeInTheDocument());
    expect(screen.getAllByRole("button", { name: "Apri ruolo Capacitas" }).length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: "Apri anagrafica Capacitas" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Apri soggetto GAIA" })).toBeInTheDocument();
  });

  test("ruolo gaia calculation page renders autonomous role calculation console", async () => {
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
    mocks.getRuoloGaiaCalculation.mockResolvedValue({
      summary: {
        anno_tributario: 2025,
        active_batch_id: "batch-2025",
        positions: 2,
        ruolo_positions: 2,
        positions_missing_tax_code: 0,
        ruolo_positions_missing_tax_code: 0,
        anomalous_positions: 1,
        anomaly_driven_positions: 1,
        total_rows: 3,
        anomalous_rows: 1,
        clean_rows: 2,
        total_sup_irrigabile_mq: 1900,
        total_imponibile_sf: 1628,
        ruolo_totale_0648: 55.24,
        gaia_totale_0648: 48.84,
        ruolo_totale_0985: 28.12,
        gaia_totale_0985: 24.42,
        ruolo_totale_0668: 0,
        ruolo_totale_confrontabile: 83.36,
        gaia_totale_confrontabile: 73.26,
        excel_totale_0648: 55.24,
        excel_totale_0985: 28.12,
        excel_totale_confrontabile: 83.36,
        delta_ruolo_gaia_totale: 10.1,
        gap_excel_gaia_totale: 10.1,
        mismatch_positions: 1,
        diagnosis_ruolo_count: 0,
        diagnosis_gaia_count: 1,
        diagnosis_excel_count: 0,
      },
      items: [
        {
          tax_code: "RSSMRA80A01H501Z",
          display_name: "ROSSI MARIO",
          ruolo_display_name: "ROSSI MARIO",
          status: "amount_mismatch",
          diagnosis: "problema_ricalcolo_gaia",
          comuni_count: 2,
          rows_count: 2,
          anomalous_rows_count: 1,
          clean_rows_count: 1,
          total_sup_irrigabile_mq: 1500,
          total_imponibile_sf: 1340,
          ruolo_0648: 46.6,
          gaia_0648: 40.2,
          ruolo_0985: 23.8,
          gaia_0985: 20.1,
          ruolo_totale_confrontabile: 70.4,
          gaia_total: 60.3,
          excel_0648: 46.6,
          excel_0985: 23.8,
          excel_total: 70.4,
          delta_ruolo_gaia_totale: 10.1,
          gap_excel_gaia_total: 10.1,
          anomaly_gap_share: 100,
          anomaly_driven_case: true,
        },
        {
          tax_code: "BNCLCU80A01H501Y",
          display_name: "BIANCHI LUCA",
          ruolo_display_name: "BIANCHI LUCA",
          status: "matched",
          diagnosis: "allineato",
          comuni_count: 1,
          rows_count: 1,
          anomalous_rows_count: 0,
          clean_rows_count: 1,
          total_sup_irrigabile_mq: 400,
          total_imponibile_sf: 288,
          ruolo_0648: 8.64,
          gaia_0648: 8.64,
          ruolo_0985: 4.32,
          gaia_0985: 4.32,
          ruolo_totale_confrontabile: 12.96,
          gaia_total: 12.96,
          excel_0648: 8.64,
          excel_0985: 4.32,
          excel_total: 12.96,
          delta_ruolo_gaia_totale: 0,
          gap_excel_gaia_total: 0,
          anomaly_gap_share: 0,
          anomaly_driven_case: false,
        },
      ],
    });
    mocks.getRuoloCapacitasCalculationDetail.mockResolvedValue({
      summary: {
        anno_tributario: 2025,
        tax_code: "RSSMRA80A01H501Z",
        display_name: "ROSSI MARIO",
        active_batch_id: "batch-2025",
        rows_count: 2,
        anomalous_rows_count: 1,
        clean_rows_count: 1,
        total_sup_irrigabile_mq: 1500,
        total_imponibile_sf: 1340,
        gaia_total: 60.3,
        excel_total: 70.4,
        gap_excel_gaia_total: 10.1,
        gaia_total_anomalous_rows: 27.9,
        excel_total_anomalous_rows: 38,
        gaia_total_clean_rows: 32.4,
        excel_total_clean_rows: 32.4,
        distinct_ind_spese_fisse: [0.72, 1.24],
        distinct_imponibile_per_mq: [0.72, 1.24],
      },
      comuni: [
        {
          comune_nome: "Arborea",
          rows_count: 1,
          anomalous_rows_count: 1,
          total_sup_irrigabile_mq: 500,
          total_imponibile_sf: 620,
          gaia_total: 27.9,
          excel_total: 38,
          gap_excel_gaia_total: 10.1,
        },
      ],
      rows: [
        {
          comune_nome: "Arborea",
          foglio: "1",
          particella: "200",
          subalterno: "1",
          sup_irrigabile_mq: 500,
          ind_spese_fisse: 1.24,
          imponibile_sf: 620,
          imponibile_per_mq: 1.24,
          aliquota_0648: 0.03,
          aliquota_0985: 0.015,
          excel_0648: 25,
          excel_0985: 13,
          excel_total: 38,
          gaia_0648: 18.6,
          gaia_0985: 9.3,
          gaia_total: 27.9,
          gap_excel_gaia_total: 10.1,
          anomalia_imponibile: true,
          anomalia_importi: true,
        },
      ],
    });

    render(<RuoloGaiaCalculationPage />);

    await waitFor(() => expect(screen.getByText("Calcolo atteso GAIA su base Capacitas attiva.")).toBeInTheDocument());
    await waitFor(() => expect(screen.getByText("ROSSI MARIO")).toBeInTheDocument());
    expect(screen.getByText("Priorita GAIA")).toBeInTheDocument();
    expect(screen.getByText("BIANCHI LUCA")).toBeInTheDocument();
    expect(screen.getByText("Allineato")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Esporta CSV" })).toHaveAttribute("href", "/api/ruolo/stats/calcolo-gaia/export?anno=2025&token=token");

    fireEvent.click(screen.getAllByRole("button", { name: "Apri calcolo" })[0]);
    await waitFor(() => expect(mocks.getRuoloCapacitasCalculationDetail).toHaveBeenCalledWith("token", 2025, "RSSMRA80A01H501Z"));
    await waitFor(() => expect(screen.getByText("Dettaglio calcolo GAIA")).toBeInTheDocument());
    expect(screen.getByText("Breakdown per comune")).toBeInTheDocument();
    expect(screen.getByText("Righe del calcolo")).toBeInTheDocument();
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

    await waitFor(() => expect(screen.getByText("Materializzazione ruolo da InCass 2023")).toBeInTheDocument());
    expect(screen.getAllByText("Completato").length).toBeGreaterThan(0);
    expect(screen.getByText("Materializzazione del read-model ruolo a partire da avvisi e partitario InCass.")).toBeInTheDocument();
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
