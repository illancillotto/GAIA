import { fireEvent, render, screen } from "@testing-library/react";

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

  test("opens issue modal for files with warnings or missing district", () => {
    render(
      <MeterReadingImportReport
        previews={[
          {
            filename: "Sinis 2025.xlsx",
            preview: {
              anno: 2025,
              distretto_id: null,
              distretto_numero: null,
              distretto_nome: null,
              filename: "Sinis 2025.xlsx",
              totale_righe: 1,
              righe_valide: 0,
              righe_con_warning: 0,
              righe_con_errori: 1,
              items: [
                {
                  row_number: 3,
                  punto_consegna: "PC-001",
                  codice_fiscale: "RSSMRA80A01H501U",
                  codice_fiscale_normalizzato: "RSSMRA80A01H501U",
                  subject_id: null,
                  subject_display_name: null,
                  validation_status: "error",
                  validation_messages: [
                    {
                      level: "error",
                      code: "DISTRETTO_MANCANTE",
                      message: "Distretto mancante o non deducibile.",
                      field: "distretto_id",
                    },
                  ],
                  data: {},
                },
              ],
            },
          },
        ]}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Vedi errori" }));

    expect(screen.getByText("Dettaglio validazione")).toBeInTheDocument();
    expect(screen.getByText("Riga 3 · PC-001")).toBeInTheDocument();
    expect(screen.getByText(/DISTRETTO_MANCANTE/)).toBeInTheDocument();
  });
});
