import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { CatastoDistrettoPreviewContent } from "@/components/catasto/distretti/distretto-preview-content";

const mocks = vi.hoisted(() => ({
  getStoredAccessToken: vi.fn(),
  catastoGetDistretto: vi.fn(),
  catastoGetDistrettoKpi: vi.fn(),
}));

vi.mock("@/lib/auth", () => ({
  getStoredAccessToken: mocks.getStoredAccessToken,
}));

vi.mock("@/lib/api/catasto", () => ({
  catastoGetDistretto: mocks.catastoGetDistretto,
  catastoGetDistrettoKpi: mocks.catastoGetDistrettoKpi,
}));

vi.mock("@/components/catasto/distretti/distretto-gis-preview", () => ({
  DistrettoGisPreview: ({
    distretto,
    kpi,
  }: {
    distretto: { num_distretto: string };
    kpi: { totale_particelle: number } | null;
  }) => (
    <div data-testid="distretto-gis-preview">
      preview {distretto.num_distretto} {kpi?.totale_particelle ?? 0}
    </div>
  ),
}));

describe("CatastoDistrettoPreviewContent", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.getStoredAccessToken.mockReturnValue("token");
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
  });

  test("loads the district preview", async () => {
    render(
      <CatastoDistrettoPreviewContent
        open
        distrettoId="distretto-1"
        numDistretto="01"
        anno={2026}
      />,
    );

    expect(screen.getByText(/Caricamento distretto/i)).toBeInTheDocument();
    expect(await screen.findByTestId("distretto-gis-preview")).toHaveTextContent("preview 01 12");
    expect(mocks.catastoGetDistretto).toHaveBeenCalledWith("token", "distretto-1");
    expect(mocks.catastoGetDistrettoKpi).toHaveBeenCalledWith("token", "distretto-1", 2026);
  });

  test("shows a session error without calling the API when auth is missing", async () => {
    mocks.getStoredAccessToken.mockReturnValueOnce(null);

    render(
      <CatastoDistrettoPreviewContent
        open
        distrettoId="distretto-1"
        numDistretto="01"
      />,
    );

    expect(await screen.findByText(/Sessione non disponibile/i)).toBeInTheDocument();
    expect(mocks.catastoGetDistretto).not.toHaveBeenCalled();
    expect(mocks.catastoGetDistrettoKpi).not.toHaveBeenCalled();
  });

  test("surfaces the district load error and tolerates KPI failures", async () => {
    mocks.catastoGetDistretto.mockRejectedValueOnce(new Error("Distretto non trovato"));
    mocks.catastoGetDistrettoKpi.mockRejectedValueOnce(new Error("KPI non disponibile"));

    render(
      <CatastoDistrettoPreviewContent
        open
        distrettoId="distretto-1"
        numDistretto="01"
      />,
    );

    await waitFor(() => {
      expect(screen.getByText("Distretto non trovato")).toBeInTheDocument();
    });
    expect(screen.queryByTestId("distretto-gis-preview")).not.toBeInTheDocument();
  });

  test("falls back to the generic district message for non-Error rejections", async () => {
    mocks.catastoGetDistretto.mockRejectedValueOnce("errore primitivo");
    mocks.catastoGetDistrettoKpi.mockRejectedValueOnce("errore primitivo");

    render(
      <CatastoDistrettoPreviewContent
        open
        distrettoId="distretto-1"
        numDistretto="01"
      />,
    );

    expect(
      await screen.findByText("Impossibile caricare il dettaglio del distretto 01."),
    ).toBeInTheDocument();
  });

  test("returns the generic fallback without a district number and skips loading when closed", async () => {
    render(
      <CatastoDistrettoPreviewContent
        open={false}
        distrettoId="distretto-1"
        numDistretto={null}
      />,
    );

    expect(
      await screen.findByText("Impossibile caricare il dettaglio del distretto."),
    ).toBeInTheDocument();
    expect(mocks.catastoGetDistretto).not.toHaveBeenCalled();
    expect(mocks.catastoGetDistrettoKpi).not.toHaveBeenCalled();
  });

  test("ignores late responses after unmount", async () => {
    let resolveDistretto!: (value: unknown) => void;
    let resolveKpi!: (value: unknown) => void;
    const distrettoPromise = new Promise((resolve) => {
      resolveDistretto = resolve;
    });
    const kpiPromise = new Promise((resolve) => {
      resolveKpi = resolve;
    });

    mocks.catastoGetDistretto.mockReturnValueOnce(distrettoPromise);
    mocks.catastoGetDistrettoKpi.mockReturnValueOnce(kpiPromise);

    const { unmount } = render(
      <CatastoDistrettoPreviewContent
        open
        distrettoId="distretto-1"
        numDistretto="01"
      />,
    );

    unmount();
    resolveDistretto({
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
    resolveKpi({
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

    await expect(distrettoPromise).resolves.toEqual(expect.any(Object));
    await expect(kpiPromise).resolves.toEqual(expect.any(Object));
  });
});
