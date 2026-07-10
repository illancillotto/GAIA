import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { RuoloReconciliationCard } from "@/components/catasto/indici/ruolo-reconciliation-card";
import type { CatIndiceRuoloReconciliation } from "@/types/catasto";

const getStoredAccessTokenMock = vi.fn<() => string | null>(() => "token-test");
const catastoGetIndiciRuoloEsclusiMock = vi.fn();
let clickedDownloadFilename = "";
const xlsxMocks = vi.hoisted(() => ({
  bookNew: vi.fn(() => ({})),
  jsonToSheet: vi.fn((rows: unknown[]) => ({ rows })),
  bookAppendSheet: vi.fn(),
  write: vi.fn(() => new ArrayBuffer(8)),
}));

vi.mock("@/lib/auth", () => ({
  getStoredAccessToken: () => getStoredAccessTokenMock(),
}));

vi.mock("@/lib/api/catasto", () => ({
  catastoGetIndiciRuoloEsclusi: (...args: unknown[]) => catastoGetIndiciRuoloEsclusiMock(...args),
}));

vi.mock("xlsx", () => ({
  utils: {
    book_new: xlsxMocks.bookNew,
    json_to_sheet: xlsxMocks.jsonToSheet,
    book_append_sheet: xlsxMocks.bookAppendSheet,
  },
  write: xlsxMocks.write,
}));

function makeReconciliation(overrides: Partial<CatIndiceRuoloReconciliation> = {}): CatIndiceRuoloReconciliation {
  return {
    righe_ruolo_totali_count: 99848,
    particelle_ruolo_totali_count: 89967,
    righe_ruolo_incluse_count: 91349,
    particelle_ruolo_incluse_count: 82124,
    righe_ruolo_escluse_count: 8499,
    particelle_ruolo_escluse_count: 7843,
    importo_ruolo_totale: "2400529.15",
    importo_ruolo_incluso: "2231321.46",
    importo_ruolo_escluso: "169207.69",
    importo_ruolo_escluso_manutenzione: "67022.22",
    importo_ruolo_escluso_irrigazione: "55627.81",
    importo_ruolo_escluso_istituzionale: "46557.66",
    superficie_irrigata_esclusa_ha: "1006.8259",
    coverage_percent: "92.951231",
    reasons: [
      {
        key: "senza_distretto",
        label: "Particella corrente senza distretto",
        description: "La particella esiste nel catasto AE corrente, ma non ha num_distretto.",
        righe_ruolo_count: 5577,
        particelle_ruolo_distinte_count: 5028,
        cat_particelle_count: 4615,
        superficie_irrigata_ha: "529.9372",
        importo_ruolo: "103317.11",
        importo_ruolo_manutenzione: "45897.64",
        importo_ruolo_irrigazione: "26251.86",
        importo_ruolo_istituzionale: "31167.61",
      },
      {
        key: "non_collegata",
        label: "Ruolo non collegato al catasto corrente",
        description: "Righe ruolo senza un aggancio sicuro a cat_particelle.",
        righe_ruolo_count: 2922,
        particelle_ruolo_distinte_count: 2815,
        cat_particelle_count: 0,
        superficie_irrigata_ha: "476.8887",
        importo_ruolo: "65890.58",
        importo_ruolo_manutenzione: "21124.58",
        importo_ruolo_irrigazione: "29375.95",
        importo_ruolo_istituzionale: "15390.05",
      },
    ],
    ...overrides,
  };
}

describe("RuoloReconciliationCard", () => {
  beforeEach(() => {
    getStoredAccessTokenMock.mockReturnValue("token-test");
    xlsxMocks.bookNew.mockClear();
    xlsxMocks.jsonToSheet.mockClear();
    xlsxMocks.bookAppendSheet.mockClear();
    xlsxMocks.write.mockClear();
    clickedDownloadFilename = "";
    vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:excel");
    vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => undefined);
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (this: HTMLAnchorElement) {
      clickedDownloadFilename = this.download;
    });
    catastoGetIndiciRuoloEsclusiMock.mockReset();
    catastoGetIndiciRuoloEsclusiMock.mockResolvedValue({
      anno_riferimento: 2025,
      total: 3,
      items: [
        {
          key: "senza_distretto|ARBOREA|70|200|",
          reason_key: "senza_distretto",
          reason_label: "Particella corrente senza distretto",
          comune_nome: "Arborea",
          foglio: "70",
          particella: "200",
          subalterno: null,
          righe_ruolo_count: 2,
          cat_particella_id: "00000000-0000-0000-0000-000000000001",
          catasto_is_current: true,
          catasto_num_distretto: null,
          superficie_irrigata_ha: "0.4",
          importo_ruolo: "30",
          importo_ruolo_manutenzione: "8",
          importo_ruolo_irrigazione: "10",
          importo_ruolo_istituzionale: "12",
          avvisi: ["CNC-1"],
          nominativi: ["Azienda agricola"],
          partite: ["P-1"],
        },
        {
          key: "non_collegata|ORISTANO|10|30|1",
          reason_key: "non_collegata",
          reason_label: "Ruolo non collegato al catasto corrente",
          comune_nome: "Oristano",
          foglio: "10",
          particella: "30",
          subalterno: "1",
          righe_ruolo_count: 1,
          cat_particella_id: null,
          catasto_is_current: null,
          catasto_num_distretto: null,
          superficie_irrigata_ha: "0",
          importo_ruolo: "0",
          importo_ruolo_manutenzione: "0",
          importo_ruolo_irrigazione: "0",
          importo_ruolo_istituzionale: "0",
          avvisi: [],
          nominativi: [],
          partite: [],
        },
        {
          key: "catasto_non_corrente_o_assente|CABRAS|11|31|",
          reason_key: "catasto_non_corrente_o_assente",
          reason_label: "Aggancio non corrente o non disponibile",
          comune_nome: null,
          foglio: "11",
          particella: "31",
          subalterno: null,
          righe_ruolo_count: 1,
          cat_particella_id: "00000000-0000-0000-0000-000000000002",
          catasto_is_current: false,
          catasto_num_distretto: "03",
          superficie_irrigata_ha: "0.25",
          importo_ruolo: "12.3456",
          importo_ruolo_manutenzione: "1.234",
          importo_ruolo_irrigazione: "2.345",
          importo_ruolo_istituzionale: "8.7666",
          avvisi: ["CNC-2"],
          nominativi: ["Soggetto non corrente"],
          partite: ["P-2"],
        },
      ],
    });
  });

  test("renders nothing while reconciliation is unavailable", () => {
    const { container } = render(<RuoloReconciliationCard reconciliation={null} anno={2025} />);

    expect(container).toBeEmptyDOMElement();
  });

  test("explains included and excluded role amounts with reason breakdown", () => {
    render(<RuoloReconciliationCard reconciliation={makeReconciliation()} anno={2025} />);

    expect(screen.getByText("Riconciliazione ruolo")).toBeInTheDocument();
    expect(screen.getByText("Perché il totale ruolo non coincide sempre con gli indici")).toBeInTheDocument();
    expect(screen.getByText("Anno ruolo 2025")).toBeInTheDocument();
    expect(screen.getAllByText(/ruolo_particelle/).length).toBeGreaterThan(0);
    expect(screen.getByText(/catasto corrente Agenzia Entrate/)).toBeInTheDocument();
    expect(screen.getByText(/2\.231\.321\s*€/)).toBeInTheDocument();
    expect(screen.getByText(/169\.208\s*€/)).toBeInTheDocument();
    expect(screen.getByText(/2\.400\.529\s*€/)).toBeInTheDocument();
    expect(screen.getByText(/1\.?006,8 ha/)).toBeInTheDocument();
    expect(screen.getByText(/82.124 particelle ruolo · 93,0% del totale/)).toBeInTheDocument();
    expect(screen.getByText(/7\.?843 particelle ruolo · 7,0% del totale/)).toBeInTheDocument();
    expect(screen.getByText(/99.848 righe ruolo da ruolo_particelle/)).toBeInTheDocument();
    expect(screen.getByText("Particella corrente senza distretto")).toBeInTheDocument();
    expect(screen.getByText("Ruolo non collegato al catasto corrente")).toBeInTheDocument();
    expect(screen.getByText(/103\.317\s*€/)).toBeInTheDocument();
    expect(screen.getByText(/65\.891\s*€/)).toBeInTheDocument();
    expect(screen.getByText(/manutenzione\s*67\.022\s*€/)).toBeInTheDocument();
  });

  test("renders the no-exclusions state and defensive percent fallbacks", () => {
    render(
      <RuoloReconciliationCard
        anno={null}
        reconciliation={makeReconciliation({
          righe_ruolo_totali_count: 0,
          particelle_ruolo_totali_count: 0,
          righe_ruolo_incluse_count: 0,
          particelle_ruolo_incluse_count: 0,
          righe_ruolo_escluse_count: 0,
          particelle_ruolo_escluse_count: 0,
          importo_ruolo_totale: "0",
          importo_ruolo_incluso: "0",
          importo_ruolo_escluso: "0",
          superficie_irrigata_esclusa_ha: "0",
          coverage_percent: null,
          reasons: [],
        })}
      />,
    );

    expect(screen.getByText("Anno ruolo —")).toBeInTheDocument();
    expect(screen.getByText("Nessuna riga ruolo esclusa dagli indici.")).toBeInTheDocument();
    expect(screen.getAllByText(/0 particelle ruolo · — del totale/)).toHaveLength(2);
    expect(screen.getByText("0,0 ha")).toBeInTheDocument();
  });

  test("opens the excluded role particles modal and loads rows lazily", async () => {
    render(<RuoloReconciliationCard reconciliation={makeReconciliation()} anno={2025} />);

    fireEvent.click(screen.getByRole("button", { name: "Visualizza ed esporta" }));

    expect(screen.getByRole("dialog", { name: "Elenco particelle ruolo fuori dal quadro indici" })).toBeInTheDocument();
    expect(screen.getByText("Caricamento particelle escluse...")).toBeInTheDocument();
    await waitFor(() => expect(catastoGetIndiciRuoloEsclusiMock).toHaveBeenCalledWith("token-test", 2025));
    expect(await screen.findByText("Arborea")).toBeInTheDocument();
    expect(screen.getByText("CNC-1")).toBeInTheDocument();
    expect(screen.getAllByText("—").length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: "Esporta Excel" })).toBeEnabled();
  });

  test("exports excluded role particles to Excel and reuses already loaded rows", async () => {
    render(<RuoloReconciliationCard reconciliation={makeReconciliation()} anno={2025} />);

    fireEvent.click(screen.getByRole("button", { name: "Visualizza ed esporta" }));
    expect(await screen.findByText("Oristano")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Esporta Excel" }));

    expect(xlsxMocks.bookNew).toHaveBeenCalledOnce();
    expect(xlsxMocks.jsonToSheet).toHaveBeenCalledWith(
      expect.arrayContaining([
        expect.objectContaining({
          Comune: "Oristano",
          Subalterno: "1",
          "Catasto corrente": "",
          Avvisi: "",
        }),
        expect.objectContaining({
          Comune: "",
          "Catasto corrente": "no",
          "Importo ruolo (EUR)": 12.35,
        }),
        expect.objectContaining({
          "Catasto corrente": "si",
        }),
      ]),
    );
    expect(URL.createObjectURL).toHaveBeenCalled();
    expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:excel");

    fireEvent.click(screen.getByRole("button", { name: "Chiudi" }));
    fireEvent.click(screen.getByRole("button", { name: "Visualizza ed esporta" }));
    expect(catastoGetIndiciRuoloEsclusiMock).toHaveBeenCalledTimes(1);
  });

  test("loads and exports with fallback filename when year is unavailable", async () => {
    render(<RuoloReconciliationCard reconciliation={makeReconciliation()} anno={null} />);

    fireEvent.click(screen.getByRole("button", { name: "Visualizza ed esporta" }));
    expect(await screen.findByText("Arborea")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Esporta Excel" }));

    expect(catastoGetIndiciRuoloEsclusiMock).toHaveBeenCalledWith("token-test", undefined);
    expect(xlsxMocks.bookAppendSheet).toHaveBeenCalledWith(expect.anything(), expect.anything(), "Esclusi nd");
    expect(clickedDownloadFilename).toBe("particelle-ruolo-escluse-indici-nd.xlsx");
  });

  test("shows a session error when opening without token", async () => {
    getStoredAccessTokenMock.mockReturnValue(null);
    render(<RuoloReconciliationCard reconciliation={makeReconciliation()} anno={null} />);

    fireEvent.click(screen.getByRole("button", { name: "Visualizza ed esporta" }));

    expect(screen.getByText("Sessione non disponibile: effettua nuovamente l'accesso.")).toBeInTheDocument();
    expect(catastoGetIndiciRuoloEsclusiMock).not.toHaveBeenCalled();
  });

  test("shows API errors and empty excluded list states", async () => {
    catastoGetIndiciRuoloEsclusiMock.mockRejectedValueOnce(new Error("errore API"));
    const { rerender } = render(<RuoloReconciliationCard reconciliation={makeReconciliation()} anno={2025} />);

    fireEvent.click(screen.getByRole("button", { name: "Visualizza ed esporta" }));

    expect(await screen.findByText("errore API")).toBeInTheDocument();

    catastoGetIndiciRuoloEsclusiMock.mockRejectedValueOnce("boom");
    rerender(<RuoloReconciliationCard reconciliation={makeReconciliation({ importo_ruolo_escluso: "10.00" })} anno={2025} />);
    fireEvent.click(screen.getByRole("button", { name: "Chiudi" }));
    fireEvent.click(screen.getByRole("button", { name: "Visualizza ed esporta" }));

    expect(await screen.findByText("Errore caricamento particelle escluse.")).toBeInTheDocument();
  });

  test("keeps modal actions disabled for empty excluded payloads", async () => {
    catastoGetIndiciRuoloEsclusiMock.mockResolvedValueOnce({ anno_riferimento: 2025, total: 0, items: [] });
    render(<RuoloReconciliationCard reconciliation={makeReconciliation()} anno={2025} />);

    fireEvent.click(screen.getByRole("button", { name: "Visualizza ed esporta" }));

    expect(await screen.findByText("Nessuna particella esclusa disponibile.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Esporta Excel" })).toBeDisabled();
  });

  test("does not open excluded modal when there are no exclusions", () => {
    render(<RuoloReconciliationCard reconciliation={makeReconciliation({ particelle_ruolo_escluse_count: 0 })} anno={2025} />);

    expect(screen.getByRole("button", { name: "Visualizza ed esporta" })).toBeDisabled();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});
