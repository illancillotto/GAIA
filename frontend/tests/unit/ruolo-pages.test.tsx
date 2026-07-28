import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import AvvisoDetailPage from "@/app/ruolo/avvisi/[id]/page";
import RuoloAvvisiPage from "@/app/ruolo/avvisi/page";
import RuoloGaiaCalculationPage from "@/app/ruolo/calcolo-gaia/page";
import RuoloCapacitasChecksPage from "@/app/ruolo/controlli-capacitas/page";
import RuoloParticellePage from "@/app/ruolo/particelle/page";
import RuoloDashboardPage from "@/app/ruolo/page";
import RuoloImportPage from "@/app/ruolo/import/page";
import RuoloStatsPage from "@/app/ruolo/stats/page";
import { getRuoloCapacitasEvaluationSummary } from "@/components/ruolo/capacitas-check-details";

const mocks = vi.hoisted(() => ({
  getStoredAccessToken: vi.fn(),
  createCapacitasInCassSyncJob: vi.fn(),
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
  getAvviso: vi.fn(),
  listAvvisi: vi.fn(),
  listRuoloParticelle: vi.fn(),
  push: vi.fn(),
  replace: vi.fn(),
  searchParams: new URLSearchParams(),
  routeParams: { id: "avviso-1" },
}));

vi.mock("@/lib/auth", () => ({
  getStoredAccessToken: mocks.getStoredAccessToken,
}));

vi.mock("@/lib/api", () => ({
  createCapacitasInCassSyncJob: mocks.createCapacitasInCassSyncJob,
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
  getAvviso: mocks.getAvviso,
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
  useParams: () => mocks.routeParams,
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

function buildAvvisoDetail(overrides: Record<string, unknown> = {}) {
  return {
    id: "avviso-1",
    import_job_id: "import-1",
    codice_cnc: "01.02025000141860",
    anno_tributario: 2025,
    subject_id: "subject-1",
    codice_fiscale_raw: "RMNMRC66E30G113G",
    nominativo_raw: "ROMANET MARCO",
    domicilio_raw: "Via Roma",
    residenza_raw: "Oristano",
    n2_extra_raw: null,
    codice_utenza: "UT-1",
    importo_totale_0648: 100,
    importo_totale_0985: 50,
    importo_totale_0668: 0,
    importo_totale_euro: 150,
    importo_totale_lire: null,
    n4_campo_sconosciuto: null,
    partite: [],
    display_name: "ROMANET MARCO",
    created_at: "2026-07-10T19:00:00Z",
    updated_at: "2026-07-10T19:00:00Z",
    ...overrides,
  };
}

describe("Ruolo pages", () => {
  beforeEach(() => {
    mocks.getStoredAccessToken.mockReturnValue("token");
    mocks.searchParams = new URLSearchParams();
    mocks.routeParams = { id: "avviso-1" };
    mocks.push.mockReset();
    mocks.replace.mockReset();
    mocks.createCapacitasInCassSyncJob.mockReset();
    mocks.getAvviso.mockReset();
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

  test("ruolo capacitas helper explains gaia recalculation priority", () => {
    expect(
      getRuoloCapacitasEvaluationSummary({
        tax_code: "RSSMRA80A01H501Z",
        ruolo_display_name: "ROSSI MARIO",
        capacitas_display_name: "ROSSI MARIO",
        status: "amount_mismatch",
        diagnosis: "problema_ricalcolo_gaia",
        ruolo_0648: 46.6,
        gaia_0648: 40.2,
        excel_0648: 46.6,
        delta_0648: 6.4,
        delta_gaia_excel_0648: -6.4,
        ruolo_0985: 23.8,
        gaia_0985: 20.1,
        excel_0985: 23.8,
        delta_0985: 3.7,
        delta_gaia_excel_0985: -3.7,
        ruolo_totale_confrontabile: 70.4,
        gaia_totale_confrontabile: 60.3,
        excel_totale_confrontabile: 70.4,
        delta_totale_confrontabile: 10.1,
        delta_gaia_excel_totale_confrontabile: -10.1,
        anomalous_rows_count: 0,
        clean_rows_count: 2,
        anomaly_gap_share: 0,
        anomaly_driven_case: false,
      }),
    ).toContain("ruolo inCASS");
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
          anomaly_gap_share: 80,
          anomaly_driven_case: false,
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
        source_filename: "capacitas-2025.xlsx",
        ruolo_avviso_id: "avviso-2025",
        codice_cnc: "CNC-CALC-001",
        capacitas_url: "https://incass3.servizicapacitas.com/pages/dettaglioAvviso.aspx?avviso=020250001234560",
        capacitas_avviso_code: "020250001234560",
        capacitas_link_source: "incass_live",
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
          ruolo_0648: 12.5,
          ruolo_0985: 6.5,
          ruolo_total: 19,
          ruolo_matched_rows_count: 1,
          gaia_0648: 18.6,
          gaia_0985: 9.3,
          gaia_total: 27.9,
          excel_0648: 25,
          excel_0985: 13,
          excel_total: 38,
          gap_excel_gaia_total: 10.1,
          delta_ruolo_gaia_total: -8.9,
          delta_ruolo_excel_total: -19,
        },
      ],
      rows: [
        {
          source_filename: "capacitas-2025.xlsx",
          source_row_number: 42,
          cco: null,
          cod_provincia: 95,
          cod_comune_capacitas: 42,
          cod_frazione: null,
          num_distretto: 3,
          nome_distretto_loc: "Distretto Nord",
          comune_nome: "Arborea",
          sezione_catastale: null,
          foglio: "1",
          particella: "200",
          subalterno: "1",
          sup_catastale_mq: null,
          sup_irrigabile_mq: 500,
          ind_spese_fisse: 1.24,
          imponibile_sf: 620,
          imponibile_per_mq: 1.24,
          esente_0648: false,
          aliquota_0648: 0.03,
          aliquota_0985: 0.015,
          excel_0648: 25,
          excel_0985: 13,
          excel_total: 38,
          gaia_0648: 18.6,
          gaia_0985: 9.3,
          gaia_total: 27.9,
          gap_excel_gaia_total: 10.1,
          ruolo_match_found: true,
          ruolo_match_level: "exact",
          ruolo_partite_count: 1,
          ruolo_comuni: ["Arborea"],
          ruolo_0648: 12.5,
          ruolo_0985: 6.5,
          ruolo_total: 19,
          delta_ruolo_gaia_total: -8.9,
          delta_ruolo_excel_total: -19,
          codice_fiscale_raw: " rssmra80a01h501z ",
          anomalia_superficie: true,
          anomalia_cf_invalido: true,
          anomalia_cf_mancante: true,
          anomalia_comune_invalido: true,
          anomalia_particella_assente: true,
          anomalia_imponibile: true,
          anomalia_importi: true,
        },
      ],
    });

    render(<RuoloGaiaCalculationPage />);

    await waitFor(() => expect(screen.getByText("Confronto tra ruolo inCASS, Excel Capacitas e calcolo GAIA.")).toBeInTheDocument());
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
    expect(screen.getAllByText("Ruolo Capacitas live").length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Ruolo\/GAIA/).length).toBeGreaterThan(0);
    expect(screen.getByRole("link", { name: "Apri avviso CapaciTas" })).toHaveAttribute(
      "href",
      "https://incass3.servizicapacitas.com/pages/dettaglioAvviso.aspx?avviso=020250001234560",
    );
    expect(screen.getByText(/Gap max:/)).toBeInTheDocument();
    expect(screen.getByText(/Moltiplicatore Excel\/Ruolo:/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Visualizza righe Excel" }));
    await waitFor(() => expect(screen.getByText("Anteprima Excel Capacitas")).toBeInTheDocument());
    expect(screen.getByText("capacitas-2025.xlsx")).toBeInTheDocument();
    expect(screen.getAllByText("Superficie").length).toBeGreaterThan(0);
    expect(screen.getByText("CF invalido")).toBeInTheDocument();
    expect(screen.getByText("CF mancante")).toBeInTheDocument();
    expect(screen.getAllByText("Comune").length).toBeGreaterThan(0);
    expect(screen.getByText("Particella assente")).toBeInTheDocument();
    expect(screen.getByText("Imponibile")).toBeInTheDocument();
    expect(screen.getByText("Importi")).toBeInTheDocument();
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

  test("ruolo avvisi renders notification badges without codice utenza in rows", async () => {
    mocks.listAvvisi.mockResolvedValue({
      items: [
        {
          id: "avviso-pec-raccomandata",
          codice_cnc: "CNC-PEC",
          anno_tributario: 2025,
          subject_id: "subject-1",
          codice_fiscale_raw: "RSSMRA80A01H501Z",
          nominativo_raw: "ROSSI MARIO",
          codice_utenza: "UT-ROW-HIDDEN",
          importo_totale_0648: 100,
          importo_totale_0985: 50,
          importo_totale_0668: 0,
          importo_totale_euro: 150,
          display_name: "ROSSI MARIO",
          is_linked: true,
          digital_delivery: {
            source_notice_id: "INCASS-CNC-PEC",
            pec_recipient: "rossi.mario@pec.example.it",
            delivery_status: "Consegnata",
            delivered_at: "17/12/2025 20:01:58",
            accepted_at: "17/12/2025 20:01:57",
            receipt_documents_count: 2,
          },
          registered_mail: {
            source_shipment_id: "POSTA-001",
            service: "Raccomandata A/R",
            status_label: "Accettata da Poste",
            sent_at: "2025-12-18T09:30:00",
            tracking_number: "619608197350",
          },
          created_at: "2026-06-16T09:00:00Z",
          updated_at: "2026-06-16T09:00:00Z",
        },
        {
          id: "avviso-senza-notifiche",
          codice_cnc: "CNC-NO-NOTIFY",
          anno_tributario: 2024,
          subject_id: null,
          codice_fiscale_raw: null,
          nominativo_raw: "SENZA NOTIFICHE",
          codice_utenza: "UT-NO-NOTIFY",
          importo_totale_0648: 10,
          importo_totale_0985: 0,
          importo_totale_0668: 0,
          importo_totale_euro: 10,
          display_name: null,
          is_linked: false,
          digital_delivery: null,
          registered_mail: null,
          created_at: "2026-06-16T09:00:00Z",
          updated_at: "2026-06-16T09:00:00Z",
        },
      ],
      total: 2,
      page: 1,
      page_size: 25,
    });

    render(<RuoloAvvisiPage />);

    await waitFor(() => expect(screen.getByText("ROSSI MARIO")).toBeInTheDocument());
    expect(screen.getByText((text) => text.includes("Digitale/PEC") && text.includes("Consegnata"))).toBeInTheDocument();
    expect(screen.getByText((text) => text.includes("rossi.mario@pec.example.it"))).toBeInTheDocument();
    expect(screen.getByText((text) => text.includes("Raccomandata") && text.includes("619608197350"))).toBeInTheDocument();
    expect(screen.getByText("Nessuna notifica digitale o raccomandata agganciata")).toBeInTheDocument();
    expect(screen.queryByText(/UT-ROW-HIDDEN|UT-NO-NOTIFY/)).not.toBeInTheDocument();
  });

  test("ruolo avvisi covers modal, pagination, autosubmit filters, focused view and fallback", async () => {
    mocks.searchParams = new URLSearchParams("q=Rossi&anno=2025&comune=Oristano&codice_fiscale=RSSMRA80A01H501Z&page=2");
    mocks.listAvvisi.mockResolvedValue({
      items: [
        {
          id: "avviso-pec",
          codice_cnc: "CNC-PEC",
          anno_tributario: 2025,
          subject_id: "subject-1",
          codice_fiscale_raw: "RSSMRA80A01H501Z",
          nominativo_raw: "ROSSI MARIO RAW",
          codice_utenza: "UT-1",
          importo_totale_0648: 80,
          importo_totale_0985: 20,
          importo_totale_0668: 0,
          importo_totale_euro: 100,
          display_name: "ROSSI MARIO",
          is_linked: true,
          digital_delivery: {
            source_notice_id: "020250PEC",
            pec_recipient: "rossi@example.pec.it",
            delivery_status: "Consegna",
            accepted_at: "2026-07-20T09:00:00Z",
            delivered_at: "data manuale",
            receipt_documents_count: 2,
          },
          registered_mail: null,
          created_at: "2026-07-20T09:00:00Z",
          updated_at: "2026-07-20T09:00:00Z",
        },
        {
          id: "avviso-raccomandata",
          codice_cnc: "CNC-RACC",
          anno_tributario: 2025,
          subject_id: null,
          codice_fiscale_raw: null,
          nominativo_raw: "BIANCHI LUCA",
          codice_utenza: "UT-2",
          importo_totale_0648: 0,
          importo_totale_0985: 0,
          importo_totale_0668: 0,
          importo_totale_euro: null,
          display_name: null,
          is_linked: false,
          digital_delivery: null,
          registered_mail: {
            source_shipment_id: "ship-1",
            service: "Raccomandata AR",
            status_label: "Consegnata",
            sent_at: "2026-07-21T10:00:00Z",
            tracking_number: "619608197350",
          },
          created_at: "2026-07-21T10:00:00Z",
          updated_at: "2026-07-21T10:00:00Z",
        },
        {
          id: "avviso-empty",
          codice_cnc: "CNC-EMPTY",
          anno_tributario: 2025,
          subject_id: null,
          codice_fiscale_raw: null,
          nominativo_raw: null,
          codice_utenza: null,
          importo_totale_0648: null,
          importo_totale_0985: null,
          importo_totale_0668: null,
          importo_totale_euro: null,
          display_name: null,
          is_linked: false,
          digital_delivery: null,
          registered_mail: null,
          created_at: "2026-07-22T10:00:00Z",
          updated_at: "2026-07-22T10:00:00Z",
        },
        {
          id: "avviso-bare-delivery",
          codice_cnc: "CNC-BARE",
          anno_tributario: 2025,
          subject_id: null,
          codice_fiscale_raw: "NLLNLL00A00A000A",
          nominativo_raw: null,
          codice_utenza: null,
          importo_totale_0648: 0,
          importo_totale_0985: 0,
          importo_totale_0668: 0,
          importo_totale_euro: 0,
          display_name: null,
          is_linked: false,
          digital_delivery: {
            source_notice_id: null,
            pec_recipient: null,
            delivery_status: null,
            accepted_at: null,
            delivered_at: null,
            receipt_documents_count: 0,
          },
          registered_mail: {
            source_shipment_id: null,
            service: null,
            status_label: null,
            sent_at: null,
            tracking_number: null,
          },
          created_at: "2026-07-23T10:00:00Z",
          updated_at: "2026-07-23T10:00:00Z",
        },
      ],
      total: 60,
      page: 2,
      page_size: 25,
    });

    const listRender = render(<RuoloAvvisiPage />);

    expect(await screen.findByText("ROSSI MARIO")).toBeInTheDocument();
    expect(screen.getByText(/Ricerca attiva su "Rossi"/)).toBeInTheDocument();
    expect(screen.getByText(/Digitale\/PEC · Consegna · accettata/)).toBeInTheDocument();
    expect(screen.getByText(/consegnata data manuale/)).toBeInTheDocument();
    expect(screen.getByText(/rossi@example.pec.it/)).toBeInTheDocument();
    expect(screen.getByText(/Raccomandata · inviata/)).toBeInTheDocument();
    expect(screen.getByText(/tracking 619608197350/)).toBeInTheDocument();
    expect(screen.getByText("Digitale/PEC")).toBeInTheDocument();
    expect(screen.getByText("Raccomandata")).toBeInTheDocument();
    expect(screen.getAllByText("Avviso senza nominativo").length).toBeGreaterThan(0);
    expect(screen.getAllByText("—").length).toBeGreaterThan(0);

    fireEvent.click(screen.getByText("ROSSI MARIO"));
    expect(await screen.findByText("Dettaglio avviso")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Apri pagina" })).toHaveAttribute("href", "/ruolo/avvisi/avviso-pec");
    expect(screen.getByTitle("Dettaglio avviso CNC-PEC")).toHaveAttribute("src", "/ruolo/avvisi/avviso-pec?embedded=1");
    fireEvent.click(screen.getByRole("button", { name: "Chiudi" }));
    await waitFor(() => expect(screen.queryByTitle("Dettaglio avviso CNC-PEC")).not.toBeInTheDocument());

    fireEvent.click(screen.getByText("BIANCHI LUCA"));
    expect(await screen.findByTitle("Dettaglio avviso CNC-RACC")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Chiudi" }));
    await waitFor(() => expect(screen.queryByTitle("Dettaglio avviso CNC-RACC")).not.toBeInTheDocument());

    fireEvent.click(screen.getAllByText("Avviso senza nominativo")[0]);
    expect(await screen.findByText("CNC-EMPTY")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Chiudi" }));
    await waitFor(() => expect(screen.queryByText("CNC-EMPTY")).not.toBeInTheDocument());

    fireEvent.click(screen.getByRole("button", { name: "← Precedente" }));
    expect(mocks.push).toHaveBeenCalledWith("/ruolo/avvisi?q=Rossi&anno=2025&comune=Oristano&codice_fiscale=RSSMRA80A01H501Z&page=1");
    fireEvent.click(screen.getByRole("button", { name: "Successiva →" }));
    expect(mocks.push).toHaveBeenCalledWith("/ruolo/avvisi?q=Rossi&anno=2025&comune=Oristano&codice_fiscale=RSSMRA80A01H501Z&page=3");

    fireEvent.change(screen.getByPlaceholderText(/Es. Rossi/), { target: { value: "Ro" } });
    await new Promise((resolve) => window.setTimeout(resolve, 420));
    expect(mocks.replace).not.toHaveBeenCalled();
    expect(screen.getByText("Inserisci almeno 3 caratteri per avviare la ricerca.")).toBeInTheDocument();

    fireEvent.change(screen.getByPlaceholderText(/Es. Rossi/), { target: { value: "Verdi" } });
    fireEvent.change(screen.getByPlaceholderText("Anno"), { target: { value: "2024" } });
    fireEvent.change(screen.getByPlaceholderText("Comune"), { target: { value: "Marrubiu" } });
    fireEvent.click(screen.getByLabelText("Solo avvisi non collegati"));
    await waitFor(() => {
      expect(mocks.replace).toHaveBeenCalledWith("/ruolo/avvisi?q=Verdi&anno=2024&comune=Marrubiu&codice_fiscale=RSSMRA80A01H501Z&unlinked=true&page=1");
    });

    fireEvent.click(screen.getByRole("button", { name: "Reset" }));
    expect(mocks.push).toHaveBeenCalledWith("/ruolo/avvisi?page=1");
    await waitFor(() => {
      expect(mocks.replace).toHaveBeenCalledWith("/ruolo/avvisi?page=1");
    });
    listRender.unmount();

    mocks.searchParams = new URLSearchParams("embedded=1&focus=mismatch");
    mocks.listAvvisi.mockResolvedValueOnce({ items: [], total: 0, page: 1, page_size: 25 });
    const focusRender = render(<RuoloAvvisiPage />);
    expect(await screen.findByText("Avvisi collegati allo scostamento")).toBeInTheDocument();
    expect(screen.queryByText("Ricerca avvisi")).not.toBeInTheDocument();
    expect(screen.getAllByText("—").length).toBeGreaterThanOrEqual(3);
    focusRender.unmount();

    mocks.listAvvisi.mockRejectedValueOnce(new Error("Errore avvisi"));
    const errorRender = render(<RuoloAvvisiPage />);
    expect(await screen.findByText("Errore avvisi")).toBeInTheDocument();
    errorRender.unmount();

    mocks.listAvvisi.mockRejectedValueOnce("boom");
    const fallbackErrorRender = render(<RuoloAvvisiPage />);
    expect(await screen.findByText("Errore")).toBeInTheDocument();
    fallbackErrorRender.unmount();

    mocks.getStoredAccessToken.mockReturnValueOnce(null);
    const loadingRender = render(<RuoloAvvisiPage />);
    expect(screen.getAllByText("Caricamento...").length).toBeGreaterThan(0);
    loadingRender.unmount();

    mocks.searchParams = new URLSearchParams();
    mocks.replace.mockClear();
    mocks.listAvvisi.mockResolvedValueOnce({ items: [], total: 0, page: 1, page_size: 25 });
    const queryOnlyRender = render(<RuoloAvvisiPage />);
    await screen.findByText("Nessun avviso trovato");
    fireEvent.change(screen.getByPlaceholderText(/Es. Rossi/), { target: { value: "Luca" } });
    await waitFor(() => {
      expect(mocks.replace).toHaveBeenCalledWith("/ruolo/avvisi?q=Luca&page=1");
    });
    queryOnlyRender.unmount();

    mocks.searchParams = new URLSearchParams();
    mocks.replace.mockClear();
    mocks.listAvvisi.mockResolvedValueOnce({ items: [], total: 0, page: 1, page_size: 25 });
    const annoOnlyRender = render(<RuoloAvvisiPage />);
    await screen.findByText("Nessun avviso trovato");
    fireEvent.change(screen.getByPlaceholderText("Anno"), { target: { value: "2026" } });
    await waitFor(() => {
      expect(mocks.replace).toHaveBeenCalledWith("/ruolo/avvisi?anno=2026&page=1");
    });
    annoOnlyRender.unmount();
  });

  test("ruolo avviso detail queues a Capacitas inCASS sync for the linked subject", async () => {
    mocks.getAvviso.mockResolvedValue(buildAvvisoDetail());
    mocks.createCapacitasInCassSyncJob.mockResolvedValue({ id: 123 });

    render(<AvvisoDetailPage />);

    const syncButton = await screen.findByRole("button", { name: "Sincronizza da CapaciTas" });
    fireEvent.click(syncButton);

    await waitFor(() => {
      expect(mocks.createCapacitasInCassSyncJob).toHaveBeenCalledWith("token", {
        subject_ids: ["subject-1"],
        include_details: true,
        include_partitario: true,
        include_mailing_list: false,
        download_mailing_receipts: false,
        continue_on_error: true,
        throttle_ms: 250,
      });
    });
    expect(await screen.findByText(/Job inCASS #123 accodato/)).toBeInTheDocument();
  });

  test("ruolo avviso detail reports non-error Capacitas sync failures", async () => {
    mocks.getAvviso.mockResolvedValue(buildAvvisoDetail());
    mocks.createCapacitasInCassSyncJob.mockRejectedValue("Errore sync stringa");

    render(<AvvisoDetailPage />);

    const syncButton = await screen.findByRole("button", { name: "Sincronizza da CapaciTas" });
    fireEvent.click(syncButton);

    expect(await screen.findByText("Errore sincronizzazione Capacitas")).toBeInTheDocument();
  });

  test("ruolo avviso detail reports Error Capacitas sync failures", async () => {
    mocks.getAvviso.mockResolvedValue(buildAvvisoDetail());
    mocks.createCapacitasInCassSyncJob.mockRejectedValue(new Error("Credenziale non disponibile"));

    render(<AvvisoDetailPage />);

    const syncButton = await screen.findByRole("button", { name: "Sincronizza da CapaciTas" });
    fireEvent.click(syncButton);

    expect(await screen.findByText("Credenziale non disponibile")).toBeInTheDocument();
  });

  test("ruolo avviso detail shows loading and api errors", async () => {
    mocks.getAvviso.mockRejectedValue(new Error("Avviso non leggibile"));

    render(<AvvisoDetailPage />);

    expect(screen.getByText("Caricamento...")).toBeInTheDocument();
    expect(await screen.findByText("Avviso non leggibile")).toBeInTheDocument();
  });

  test("ruolo avviso detail handles non-error api failures", async () => {
    mocks.getAvviso.mockRejectedValue("Errore API stringa");

    render(<AvvisoDetailPage />);

    expect(await screen.findByText("Errore")).toBeInTheDocument();
  });

  test("ruolo avviso detail renders orphan embedded notices without Capacitas sync", async () => {
    mocks.searchParams = new URLSearchParams("embedded=1");
    mocks.getAvviso.mockResolvedValue(buildAvvisoDetail({
      subject_id: null,
      display_name: null,
      nominativo_raw: null,
      codice_fiscale_raw: null,
      codice_utenza: null,
      domicilio_raw: null,
      residenza_raw: null,
      importo_totale_0648: null,
      importo_totale_0985: null,
      importo_totale_0668: null,
      importo_totale_euro: null,
    }));

    render(<AvvisoDetailPage />);

    expect(await screen.findByText("Avviso non collegato")).toBeInTheDocument();
    expect(screen.getByText("Orfano")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /Torna agli avvisi/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Sincronizza da CapaciTas" })).not.toBeInTheDocument();
    expect(screen.getAllByText("—").length).toBeGreaterThan(0);
  });

  test("ruolo avviso detail renders non-embedded orphan notices without subject link", async () => {
    mocks.getAvviso.mockResolvedValue(buildAvvisoDetail({
      subject_id: null,
      display_name: null,
    }));

    render(<AvvisoDetailPage />);

    expect(await screen.findByRole("link", { name: /Torna agli avvisi/ })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Apri soggetto GAIA" })).not.toBeInTheDocument();
  });

  test("ruolo avviso detail falls back to subject id when display name is missing", async () => {
    mocks.getAvviso.mockResolvedValue(buildAvvisoDetail({
      display_name: null,
      nominativo_raw: null,
    }));

    render(<AvvisoDetailPage />);

    expect(await screen.findByText(/display name subject-1/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "subject-1" })).toHaveAttribute("href", "/utenze/subject-1");
  });

  test("ruolo avviso detail renders and expands partite with particelle", async () => {
    mocks.getAvviso.mockResolvedValue(buildAvvisoDetail({
      partite: [
        {
          id: "partita-1",
          avviso_id: "avviso-1",
          codice_partita: "P-1",
          comune_nome: "Arborea",
          comune_codice: "A357",
          contribuente_cf: "RMNMRC66E30G113G",
          co_intestati_raw: "Romanet Alessandro",
          importo_0648: 100,
          importo_0985: 25,
          importo_0668: 5,
          created_at: "2026-07-10T19:00:00Z",
          particelle: [
            {
              id: "particella-1",
              partita_id: "partita-1",
              anno_tributario: 2025,
              comune_nome: "Arborea",
              comune_codice: "A357",
              domanda_irrigua: "SI",
              distretto: "10",
              foglio: "12",
              particella: "34",
              subalterno: "1",
              sup_catastale_are: 120,
              sup_catastale_ha: 1.2345,
              sup_irrigata_ha: 0.5,
              coltura: "Seminativo",
              importo_manut: 10,
              importo_irrig: 20,
              importo_ist: 5,
              catasto_parcel_id: null,
              cat_particella_id: null,
              cat_particella_match_status: null,
              cat_particella_match_confidence: null,
              cat_particella_match_reason: null,
              ade_scan_status: null,
              ade_scan_classification: null,
              created_at: "2026-07-10T19:00:00Z",
            },
            {
              id: "particella-2",
              partita_id: "partita-1",
              anno_tributario: 2025,
              comune_nome: "Arborea",
              comune_codice: "A357",
              domanda_irrigua: null,
              distretto: null,
              foglio: "13",
              particella: "35",
              subalterno: null,
              sup_catastale_are: null,
              sup_catastale_ha: null,
              sup_irrigata_ha: null,
              coltura: null,
              importo_manut: null,
              importo_irrig: null,
              importo_ist: null,
              catasto_parcel_id: null,
              cat_particella_id: null,
              cat_particella_match_status: null,
              cat_particella_match_confidence: null,
              cat_particella_match_reason: null,
              ade_scan_status: null,
              ade_scan_classification: null,
              created_at: "2026-07-10T19:00:00Z",
            },
          ],
        },
        {
          id: "partita-2",
          avviso_id: "avviso-1",
          codice_partita: null,
          comune_nome: null,
          comune_codice: null,
          contribuente_cf: null,
          co_intestati_raw: null,
          importo_0648: null,
          importo_0985: null,
          importo_0668: null,
          created_at: "2026-07-10T19:00:00Z",
          particelle: [],
        },
      ],
    }));

    render(<AvvisoDetailPage />);

    expect(await screen.findByText("Arborea")).toBeInTheDocument();
    fireEvent.click(screen.getAllByRole("button", { name: /Apri/ })[0]);
    expect(screen.getByText(/Co-intestatari:/)).toBeInTheDocument();
    expect(screen.getByText(/Foglio 12 · Particella 34 · Sub 1/)).toBeInTheDocument();
    expect(screen.getByText(/Coltura Seminativo/)).toBeInTheDocument();
    expect(screen.getByText(/Foglio 13 · Particella 35/)).toBeInTheDocument();
    expect(screen.getByText(/Coltura —/)).toBeInTheDocument();

    fireEvent.click(screen.getAllByRole("button", { name: /Apri/ })[0]);
    expect(screen.getByText("Nessuna particella")).toBeInTheDocument();
  });

  test("ruolo avviso detail handles missing API payload with not-found copy", async () => {
    mocks.getAvviso.mockResolvedValue(null);

    render(<AvvisoDetailPage />);

    expect(await screen.findByText("Avviso non trovato.")).toBeInTheDocument();
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
