import { render, screen } from "@testing-library/react";

import { MeterReadingImportReport } from "@/components/catasto/meter-reading-import-report";

describe("MeterReadingImportReport", () => {
  test("renders empty state when there are no previews", () => {
    render(<MeterReadingImportReport previews={[]} />);

    expect(screen.getByText("Nessuna anteprima disponibile.")).toBeInTheDocument();
  });

  test("renders one card per imported file preview", () => {
    render(
      <MeterReadingImportReport
        previews={[
          {
            filename: "D01-Sinis 2025.xlsx",
            preview: {
              anno: 2025,
              distretto_id: "00000000-0000-0000-0000-000000000001",
              distretto_numero: "1",
              distretto_nome: "Sinis",
              filename: "D01-Sinis 2025.xlsx",
              totale_righe: 10,
              righe_valide: 8,
              righe_con_warning: 1,
              righe_con_errori: 1,
              items: [],
            },
          },
          {
            filename: "D02-Terralba 2025.xlsx",
            preview: {
              anno: 2025,
              distretto_id: "00000000-0000-0000-0000-000000000002",
              distretto_numero: "2",
              distretto_nome: "Terralba",
              filename: "D02-Terralba 2025.xlsx",
              totale_righe: 12,
              righe_valide: 11,
              righe_con_warning: 1,
              righe_con_errori: 0,
              items: [],
            },
          },
        ]}
      />,
    );

    expect(screen.getByText((content) => content.includes("D01-Sinis 2025.xlsx"))).toBeInTheDocument();
    expect(screen.getByText((content) => content.includes("D02-Terralba 2025.xlsx"))).toBeInTheDocument();
    expect(screen.getAllByText("Report validazione")).toHaveLength(2);
  });
});
