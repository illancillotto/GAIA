import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import AnalysisPanel from "@/components/catasto/gis/AnalysisPanel";

describe("AnalysisPanel", () => {
  test("renders loading skeleton while the analysis is running", () => {
    const { container } = render(<AnalysisPanel isLoading onExport={vi.fn()} result={null} />);

    expect(container.querySelectorAll(".animate-pulse")).toHaveLength(4);
    expect(screen.queryByText(/Disegna un'area/i)).not.toBeInTheDocument();
  });

  test("renders the empty state when there is no result yet", () => {
    render(<AnalysisPanel isLoading={false} onExport={vi.fn()} result={null} />);

    expect(screen.getByText("Disegna un'area nel GIS per avviare l'analisi spaziale.")).toBeInTheDocument();
  });

  test("offers CSV, Excel and GeoJSON export actions", () => {
    const onExport = vi.fn();

    render(
      <AnalysisPanel
        isLoading={false}
        onExport={onExport}
        result={{
          n_particelle: 12,
          superficie_ha: 3.25,
          per_foglio: [],
          per_distretto: [],
          particelle: [],
          truncated: false,
        }}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "CSV" }));
    fireEvent.click(screen.getByRole("button", { name: "Excel" }));
    fireEvent.click(screen.getByRole("button", { name: "GeoJSON" }));

    expect(onExport).toHaveBeenNthCalledWith(1, "csv");
    expect(onExport).toHaveBeenNthCalledWith(2, "xlsx");
    expect(onExport).toHaveBeenNthCalledWith(3, "geojson");
    expect(screen.getByText(/reimport GIS/i)).toHaveTextContent(
      "`CSV` e `Excel` includono i campi utili al reimport GIS. `GeoJSON` e pensato per uso cartografico diretto.",
    );
  });

  test("renders aggregates, truncation notice and hidden fogli summary", () => {
    render(
      <AnalysisPanel
        isLoading={false}
        onExport={vi.fn()}
        result={{
          n_particelle: 234,
          superficie_ha: 12.345,
          per_foglio: [
            { foglio: "1", n_particelle: 10, superficie_ha: 1.1 },
            { foglio: "2", n_particelle: 20, superficie_ha: 2.2 },
            { foglio: "3", n_particelle: 30, superficie_ha: 3.3 },
            { foglio: "4", n_particelle: 40, superficie_ha: 4.4 },
            { foglio: "5", n_particelle: 50, superficie_ha: 5.5 },
            { foglio: "6", n_particelle: 60, superficie_ha: 6.6 },
            { foglio: "7", n_particelle: 70, superficie_ha: 7.7 },
            { foglio: "8", n_particelle: 80, superficie_ha: 8.8 },
            { foglio: "9", n_particelle: 90, superficie_ha: 9.9 },
          ],
          per_distretto: [
            { num_distretto: "01", nome_distretto: "Sinis Nord Est", n_particelle: 150, superficie_ha: 8.9 },
            { num_distretto: "02", nome_distretto: null, n_particelle: 84, superficie_ha: 3.445 },
          ],
          particelle: [],
          truncated: true,
        }}
      />,
    );

    expect(screen.getByText("234")).toBeInTheDocument();
    expect(screen.getByText("12,3")).toBeInTheDocument();
    expect(screen.getByText(/Preview limitata a 200 particelle/i)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Per foglio" })).toBeInTheDocument();
    expect(screen.getByText("Altri 1 fogli non mostrati.")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Per distretto" })).toBeInTheDocument();
    expect(screen.getByText(/01/)).toBeInTheDocument();
    expect(screen.getByText(/Sinis Nord Est/)).toBeInTheDocument();
    expect(screen.getByText(/84 part. - 3,4 ha/)).toBeInTheDocument();
  });

  test("does not render the hidden fogli summary when eight or fewer groups are present", () => {
    render(
      <AnalysisPanel
        isLoading={false}
        onExport={vi.fn()}
        result={{
          n_particelle: 8,
          superficie_ha: 1.2,
          per_foglio: [{ foglio: "1", n_particelle: 8, superficie_ha: 1.2 }],
          per_distretto: [],
          particelle: [],
          truncated: false,
        }}
      />,
    );

    expect(screen.queryByText(/Altri .* fogli non mostrati/)).not.toBeInTheDocument();
  });
});
