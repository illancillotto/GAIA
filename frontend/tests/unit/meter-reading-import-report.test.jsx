import { fireEvent, render, screen } from "@testing-library/react";

import { MeterReadingImportReport } from "@/components/catasto/meter-reading-import-report";

describe("MeterReadingImportReport", () => {
  const basePreview = {
    anno: 2025,
    distretto_id: "00000000-0000-0000-0000-000000000001",
    distretto_numero: "1",
    distretto_nome: "Sinis",
    filename: "D01-Sinis 2025.xlsx",
    totale_righe: 3,
    righe_valide: 1,
    righe_con_warning: 1,
    righe_con_errori: 1,
    items: [],
  };

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

  test("omits issue action when a file has no validation issues", () => {
    render(
      <MeterReadingImportReport
        previews={[
          {
            filename: "D01-Sinis 2025.xlsx",
            preview: {
              ...basePreview,
              righe_valide: 3,
              righe_con_warning: 0,
              righe_con_errori: 0,
            },
          },
        ]}
      />,
    );

    expect(screen.queryByRole("button", { name: "Vedi errori" })).not.toBeInTheDocument();
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

  test("filters modal rows and renders shared subject diagnostics", () => {
    render(
      <MeterReadingImportReport
        previews={[
          {
            filename: "D01-Sinis 2025.xlsx",
            preview: {
              ...basePreview,
              items: [
                {
                  row_number: 1,
                  punto_consegna: "PC-001",
                  codice_fiscale: "RSSMRA80A01H501U",
                  codice_fiscale_normalizzato: "RSSMRA80A01H501U",
                  subject_id: null,
                  subject_display_name: "Mario Rossi",
                  validation_status: "valid",
                  validation_messages: [
                    {
                      level: "info",
                      code: "MATCH_OK",
                      message: "Riga associata.",
                      field: null,
                    },
                  ],
                  data: {
                    shared_meter_subject_labels: ["Mario Rossi", "", 42, "Anna Verdi"],
                    tax_code_candidates: ["RSSMRA80A01H501U", null, "VRDNNA80A01H501U"],
                  },
                },
                {
                  row_number: 2,
                  punto_consegna: "PC-002",
                  codice_fiscale: "BNCLGU80A01H501U",
                  codice_fiscale_normalizzato: "BNCLGU80A01H501U",
                  subject_id: null,
                  subject_display_name: null,
                  validation_status: "warning",
                  validation_messages: [
                    {
                      level: "warning",
                      code: "SOGGETTO_AMBIGUO",
                      message: "Piu soggetti candidati.",
                      field: "codice_fiscale",
                    },
                  ],
                  data: {
                    shared_meter_subject_labels: "not-an-array",
                    tax_code_candidates: "not-an-array",
                  },
                },
                {
                  row_number: 3,
                  punto_consegna: null,
                  codice_fiscale: null,
                  codice_fiscale_normalizzato: null,
                  subject_id: null,
                  subject_display_name: null,
                  validation_status: "error",
                  validation_messages: [
                    {
                      level: "error",
                      code: "CF_MANCANTE",
                      message: "Codice fiscale mancante.",
                      field: "codice_fiscale",
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

    expect(screen.getByText("Soggetti candidati")).toBeInTheDocument();
    expect(screen.getByText("Mario Rossi, Anna Verdi")).toBeInTheDocument();
    expect(screen.getByText("CF/P.IVA rilevati: RSSMRA80A01H501U · VRDNNA80A01H501U")).toBeInTheDocument();
    expect(screen.getByText(/MATCH_OK/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Valide (1)" }));
    expect(screen.getByText("Riga 1 · PC-001")).toBeInTheDocument();
    expect(screen.queryByText("Riga 2 · PC-002")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Warning (1)" }));
    expect(screen.getByText("Riga 2 · PC-002")).toBeInTheDocument();
    expect(screen.getByText(/SOGGETTO_AMBIGUO/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Errori (1)" }));
    expect(screen.getByText("Riga 3")).toBeInTheDocument();
    expect(screen.getByText("Soggetto non risolto")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Chiudi" }));
    expect(screen.queryByText("Dettaglio validazione")).not.toBeInTheDocument();
  });

  test("shows empty modal states for issue filters without rows", () => {
    render(
      <MeterReadingImportReport
        previews={[
          {
            filename: "Sinis 2025.xlsx",
            preview: {
              ...basePreview,
              distretto_id: null,
              distretto_numero: null,
              distretto_nome: null,
              righe_valide: 0,
              righe_con_warning: 0,
              righe_con_errori: 0,
              items: [],
            },
          },
        ]}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Vedi errori" }));

    expect(screen.getAllByText((content) => content.includes("Distretto non dedotto")).length).toBeGreaterThan(0);
    expect(screen.getByText("Nessun warning o errore su questo file.")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Errori (0)" }));
    expect(screen.getByText("Nessuna riga trovata per il filtro selezionato.")).toBeInTheDocument();
  });

  test("renders missing year and omits tax candidates when none are available", () => {
    render(
      <MeterReadingImportReport
        previews={[
          {
            filename: "D01-Sinis.xlsx",
            preview: {
              ...basePreview,
              anno: null,
              righe_valide: 0,
              righe_con_warning: 1,
              righe_con_errori: 0,
              items: [
                {
                  row_number: 1,
                  punto_consegna: "PC-001",
                  codice_fiscale: "RSSMRA80A01H501U",
                  codice_fiscale_normalizzato: "RSSMRA80A01H501U",
                  subject_id: null,
                  subject_display_name: null,
                  validation_status: "warning",
                  validation_messages: [
                    {
                      level: "warning",
                      code: "SOGGETTO_CONDIVISO",
                      message: "Contatore condiviso.",
                      field: null,
                    },
                  ],
                  data: {
                    shared_meter_subject_labels: ["Mario Rossi"],
                    tax_code_candidates: [],
                  },
                },
              ],
            },
          },
        ]}
      />,
    );

    expect(screen.getByText("Anno —")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Vedi errori" }));

    expect(screen.getByText("Soggetti candidati")).toBeInTheDocument();
    expect(screen.getByText("Mario Rossi")).toBeInTheDocument();
    expect(screen.queryByText(/CF\/P\.IVA rilevati/)).not.toBeInTheDocument();
  });
});
