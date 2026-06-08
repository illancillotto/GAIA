import { fireEvent, render, screen } from "@testing-library/react";

import { MeterReadingImportPanel } from "@/components/catasto/meter-reading-import-panel";

vi.mock("@/lib/auth", () => ({
  getStoredAccessToken: () => "token",
}));

vi.mock("@/lib/api/catasto", () => ({
  catastoValidateMeterReadingsImport: vi.fn(),
  catastoImportMeterReadings: vi.fn(),
}));

describe("MeterReadingImportPanel", () => {
  test("ignores temporary excel files and shows a warning banner", () => {
    render(<MeterReadingImportPanel />);

    const input = document.getElementById("catasto-meter-readings-file");
    const tempFile = new File(["temp"], "~$D31-SantAnna_letture_2024.xlsx", {
      type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    });
    const realFile = new File(["real"], "D31-SantAnna_letture_2024.xlsx", {
      type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    });

    fireEvent.change(input, { target: { files: [tempFile, realFile] } });

    expect(screen.getByText("File ignorati")).toBeInTheDocument();
    expect(screen.getByText("I file temporanei di Excel non vengono importati.")).toBeInTheDocument();
    expect(screen.getByText("~$D31-SantAnna_letture_2024.xlsx")).toBeInTheDocument();
    expect(screen.getByText("D31-SantAnna_letture_2024.xlsx")).toBeInTheDocument();
    expect(screen.queryByText("I file temporanei di Excel (~$...) non sono importabili. Seleziona i file .xlsx reali.")).not.toBeInTheDocument();
  });

  test("shows a blocking error when only temporary excel files are selected", () => {
    render(<MeterReadingImportPanel />);

    const input = document.getElementById("catasto-meter-readings-file");
    const tempFile = new File(["temp"], "~$D28-1°D Terralba letture 2024-totale.xlsx", {
      type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    });

    fireEvent.change(input, { target: { files: [tempFile] } });

    expect(screen.getByText("Errore")).toBeInTheDocument();
    expect(screen.getByText("I file temporanei di Excel (~$...) non sono importabili. Seleziona i file .xlsx reali.")).toBeInTheDocument();
    expect(screen.getByText("File ignorati")).toBeInTheDocument();
  });
});
