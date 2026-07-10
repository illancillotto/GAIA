import { fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import type { CatIndiceGroupSummary, CatIndiceOverview } from "@/types/catasto";
import {
  DistrettiIndiciTable,
  buildDistrettiExcelRows,
  buildDistrettoTableRows,
  compareDistrettoRows,
  compareNullableNumber,
  distrettoSortValue,
  filterAndSortDistrettoRows,
  normalizeDistrettoCode,
  summarizeDistrettoRows,
  type DistrettoSortKey,
  type DistrettoTableRow,
} from "@/components/catasto/indici/distretti-table";

const xlsxMocks = vi.hoisted(() => ({
  bookNew: vi.fn(() => ({ Sheets: {}, SheetNames: [] })),
  bookAppendSheet: vi.fn(),
  jsonToSheet: vi.fn((rows: unknown[]) => ({ rows })),
  write: vi.fn(() => new Uint8Array([1, 2, 3]).buffer),
}));

vi.mock("xlsx", () => ({
  utils: {
    book_new: xlsxMocks.bookNew,
    book_append_sheet: xlsxMocks.bookAppendSheet,
    json_to_sheet: xlsxMocks.jsonToSheet,
  },
  write: xlsxMocks.write,
}));

function makeGroup(overrides: Partial<CatIndiceGroupSummary>): CatIndiceGroupSummary {
  return {
    indice_key: "alta_pressione",
    indice_label: "Alta pressione",
    sort_order: 10,
    distretti_count: 0,
    particelle_count: 0,
    ruolo_particelle_count: 0,
    particelle_con_anagrafica_count: 0,
    particelle_senza_ruolo_count: 0,
    particelle_senza_anagrafica_count: 0,
    superficie_catastale_mq: "0",
    superficie_irrigata_ha: "0",
    importo_stimato: "0",
    importo_ruolo: "0",
    importo_ruolo_manutenzione: "0",
    importo_ruolo_irrigazione: "0",
    importo_ruolo_istituzionale: "0",
    ruolo_metrics_reliable: true,
    ruolo_metrics_valid_count: 0,
    ruolo_metrics_invalid_count: 0,
    ruolo_metrics_warning: null,
    hectares_reference_total: "0",
    distretti: [],
    colture: [],
    comuni: [],
    distretti_analytics: [],
    ...overrides,
  };
}

function makeOverview(overrides: Partial<CatIndiceOverview> = {}): CatIndiceOverview {
  return {
    anno_riferimento: 2025,
    total_distretti: 4,
    total_particelle: 7,
    available_colture: [],
    ruolo_reconciliation: {
      righe_ruolo_totali_count: 0,
      particelle_ruolo_totali_count: 0,
      righe_ruolo_incluse_count: 0,
      particelle_ruolo_incluse_count: 0,
      righe_ruolo_escluse_count: 0,
      particelle_ruolo_escluse_count: 0,
      importo_ruolo_totale: "0",
      importo_ruolo_incluso: "0",
      importo_ruolo_escluso: "0",
      importo_ruolo_escluso_manutenzione: "0",
      importo_ruolo_escluso_irrigazione: "0",
      importo_ruolo_escluso_istituzionale: "0",
      superficie_irrigata_esclusa_ha: "0",
      coverage_percent: null,
      reasons: [],
    },
    items: [
      makeGroup({
        indice_key: "canaletta",
        indice_label: "Canaletta",
        sort_order: 30,
        distretti: [
          {
            distretto_id: "d-08",
            num_distretto: "8",
            nome_distretto: "Pauli Bingias",
            indice_key: "canaletta",
            indice_label: "Canaletta",
            hectares_reference: "1200",
          },
        ],
        distretti_analytics: [
          {
            key: "08",
            label: "08 · Pauli Bingias",
            particelle_count: 2,
            ruolo_particelle_count: 2,
            particelle_con_anagrafica_count: 1,
            superficie_irrigata_ha: "0.8",
            importo_stimato: "220",
            importo_ruolo: "540",
            importo_ruolo_manutenzione: "300",
            importo_ruolo_irrigazione: "140",
            importo_ruolo_istituzionale: "100",
          },
        ],
      }),
      makeGroup({
        indice_key: "alta_pressione",
        indice_label: "Alta pressione",
        sort_order: 10,
        distretti: [
          {
            distretto_id: "d-01",
            num_distretto: "01",
            nome_distretto: "Sinis Nord Est",
            indice_key: "alta_pressione",
            indice_label: "Alta pressione",
            hectares_reference: "1800",
          },
          {
            distretto_id: "d-29a",
            num_distretto: "291",
            nome_distretto: "Distretto alias",
            indice_key: "alta_pressione",
            indice_label: "Alta pressione",
            hectares_reference: null,
          },
        ],
        distretti_analytics: [
          {
            key: "01",
            label: "01 · Sinis Nord Est",
            particelle_count: 3,
            ruolo_particelle_count: 3,
            particelle_con_anagrafica_count: 1,
            superficie_irrigata_ha: "1.2",
            importo_stimato: "450",
            importo_ruolo: "1230",
            importo_ruolo_manutenzione: "600",
            importo_ruolo_irrigazione: "430",
            importo_ruolo_istituzionale: "200",
          },
          {
            key: "29a",
            label: "29a · Distretto alias",
            particelle_count: 4,
            ruolo_particelle_count: 3,
            particelle_con_anagrafica_count: 2,
            superficie_irrigata_ha: "2.34567",
            importo_stimato: "650",
            importo_ruolo: "755.236",
            importo_ruolo_manutenzione: "220.123",
            importo_ruolo_irrigazione: "310.456",
            importo_ruolo_istituzionale: "224.657",
          },
        ],
      }),
      makeGroup({
        indice_key: "non_classificato",
        indice_label: "Non classificato",
        sort_order: 99,
        distretti: [
          {
            distretto_id: "fd-1",
            num_distretto: "fd1",
            nome_distretto: "Fuori distretto",
            indice_key: "non_classificato",
            indice_label: "Non classificato",
            hectares_reference: "0",
          },
        ],
        distretti_analytics: [
          {
            key: "fd1",
            label: "FD1 · Fuori distretto",
            particelle_count: 1,
            ruolo_particelle_count: 0,
            particelle_con_anagrafica_count: 0,
            superficie_irrigata_ha: "0",
            importo_stimato: "0",
            importo_ruolo: "0",
            importo_ruolo_manutenzione: "0",
            importo_ruolo_irrigazione: "0",
            importo_ruolo_istituzionale: "0",
          },
        ],
      }),
      makeGroup({
        indice_key: "legacy",
        indice_label: "Legacy",
        sort_order: 100,
        distretti: [
          {
            distretto_id: "legacy-1",
            num_distretto: "x1",
            nome_distretto: null,
            indice_key: "legacy",
            indice_label: "Legacy",
            hectares_reference: null,
          },
        ],
        distretti_analytics: [],
      }),
    ],
    ...overrides,
  };
}

const leftRow: DistrettoTableRow = {
  indiceKey: "alta_pressione",
  indiceLabel: "Alta pressione",
  num: "01",
  nome: "Alpha",
  haRiferimento: 10,
  particelle: 1,
  aRuolo: 2,
  conAnagrafica: 3,
  supIrrigata: 4,
  importoRuolo: 5,
  importoRuoloManutenzione: 6,
  importoRuoloIrrigazione: 7,
  importoRuoloIstituzionale: 8,
};

const rightRow: DistrettoTableRow = {
  indiceKey: "canaletta",
  indiceLabel: "Canaletta",
  num: "02",
  nome: "Beta",
  haRiferimento: 20,
  particelle: 11,
  aRuolo: 12,
  conAnagrafica: 13,
  supIrrigata: 14,
  importoRuolo: 15,
  importoRuoloManutenzione: 16,
  importoRuoloIrrigazione: 17,
  importoRuoloIstituzionale: 18,
};

describe("DistrettiIndiciTable model", () => {
  test("normalizes and sorts district codes with numeric, alias, fd and generic groups", () => {
    expect(normalizeDistrettoCode(" 8 ")).toBe("08");
    expect(normalizeDistrettoCode("291")).toBe("29a");
    expect(distrettoSortValue("29a")).toEqual([0, 29, "a"]);
    expect(distrettoSortValue("fd12")).toEqual([1, 0, "fd12"]);
    expect(distrettoSortValue("x1")).toEqual([2, 0, "x1"]);
  });

  test("compares nullable numbers in all nullability combinations", () => {
    expect(compareNullableNumber(null, null)).toBe(0);
    expect(compareNullableNumber(null, 1)).toBe(1);
    expect(compareNullableNumber(1, null)).toBe(-1);
    expect(compareNullableNumber(1, 2)).toBe(-1);
  });

  test("compares every sortable district column and falls back to district number", () => {
    const sortKeys: DistrettoSortKey[] = [
      "indice",
      "num",
      "nome",
      "haRiferimento",
      "particelle",
      "aRuolo",
      "conAnagrafica",
      "supIrrigata",
      "importoRuolo",
      "importoRuoloManutenzione",
      "importoRuoloIrrigazione",
      "importoRuoloIstituzionale",
    ];
    for (const key of sortKeys) {
      expect(compareDistrettoRows(leftRow, rightRow, { key, direction: "asc" })).toBeLessThan(0);
    }
    expect(compareDistrettoRows(leftRow, rightRow, { key: "importoRuolo", direction: "desc" })).toBeGreaterThan(0);
    expect(compareDistrettoRows({ ...leftRow, num: "29b" }, { ...rightRow, num: "29a" }, { key: "num", direction: "asc" })).toBeGreaterThan(0);
    expect(compareDistrettoRows({ ...leftRow, indiceLabel: "Stesso", num: "03" }, { ...rightRow, indiceLabel: "Stesso", num: "02" }, { key: "indice", direction: "asc" })).toBeGreaterThan(0);
    expect(compareDistrettoRows({ ...leftRow, indiceLabel: "Stesso", num: "29b" }, { ...rightRow, indiceLabel: "Stesso", num: "29a" }, { key: "indice", direction: "asc" })).toBeGreaterThan(0);
  });

  test("builds rows from overview groups, filters, sorts, summarizes and exports sheet rows", () => {
    const rows = buildDistrettoTableRows(makeOverview().items);
    const suffixRows = buildDistrettoTableRows([
      makeGroup({
        distretti: [
          {
            distretto_id: "d-29b",
            num_distretto: "292",
            nome_distretto: "Distretto 29b",
            indice_key: "alta_pressione",
            indice_label: "Alta pressione",
            hectares_reference: null,
          },
          {
            distretto_id: "d-29a",
            num_distretto: "291",
            nome_distretto: "Distretto 29a",
            indice_key: "alta_pressione",
            indice_label: "Alta pressione",
            hectares_reference: null,
          },
        ],
      }),
    ]);

    expect(rows.map((row) => row.num)).toEqual(["01", "8", "291", "FD1", "x1"]);
    expect(suffixRows.map((row) => row.num)).toEqual(["291", "292"]);
    expect(rows.find((row) => row.num === "291")).toMatchObject({
      particelle: 4,
      importoRuoloManutenzione: 220.123,
      importoRuoloIrrigazione: 310.456,
      importoRuoloIstituzionale: 224.657,
    });
    expect(rows.find((row) => row.num === "x1")).toMatchObject({
      nome: "—",
      haRiferimento: null,
      particelle: 0,
    });

    const filteredRows = filterAndSortDistrettoRows(rows, "canaletta", { key: "importoRuolo", direction: "desc" });
    expect(filteredRows).toHaveLength(1);
    expect(filteredRows[0]?.nome).toBe("Pauli Bingias");

    const allSortedRows = filterAndSortDistrettoRows(rows, "__all__", { key: "importoRuolo", direction: "desc" });
    expect(allSortedRows[0]?.nome).toBe("Sinis Nord Est");

    const totals = summarizeDistrettoRows(rows);
    expect(totals).toMatchObject({
      haRiferimento: 3000,
      particelle: 10,
      aRuolo: 8,
      conAnagrafica: 4,
      importoRuoloManutenzione: 1120.123,
      importoRuoloIrrigazione: 880.456,
      importoRuoloIstituzionale: 524.657,
    });

    const excelRows = buildDistrettiExcelRows(rows, totals);
    expect(excelRows[2]).toMatchObject({
      "N°": "291",
      "Sup. irrigata (ha)": 2.3457,
      "Importo ruolo (EUR)": 755.24,
      "0648 Manut. (EUR)": 220.12,
      "0668 Irrig. (EUR)": 310.46,
      "0985 Ist. (EUR)": 224.66,
    });
    expect(excelRows.at(-1)).toMatchObject({
      Indice: "TOTALE",
      "Importo ruolo (EUR)": 2525.24,
      "0648 Manut. (EUR)": 1120.12,
      "0668 Irrig. (EUR)": 880.46,
      "0985 Ist. (EUR)": 524.66,
    });
  });
});

describe("DistrettiIndiciTable UI", () => {
  let createObjectUrl: ReturnType<typeof vi.fn>;
  let revokeObjectUrl: ReturnType<typeof vi.fn>;
  let clickAnchor: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    xlsxMocks.bookNew.mockClear();
    xlsxMocks.bookAppendSheet.mockClear();
    xlsxMocks.jsonToSheet.mockClear();
    xlsxMocks.write.mockClear();
    createObjectUrl = vi.fn(() => "blob:distretti");
    revokeObjectUrl = vi.fn();
    Object.defineProperty(URL, "createObjectURL", { configurable: true, value: createObjectUrl });
    Object.defineProperty(URL, "revokeObjectURL", { configurable: true, value: revokeObjectUrl });
    clickAnchor = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
  });

  afterEach(() => {
    clickAnchor.mockRestore();
  });

  test("renders loading and empty states", () => {
    const { rerender } = render(<DistrettiIndiciTable overview={null} isLoading />);

    expect(screen.getByText("Caricamento quadro distretti...")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Scarica Excel" })).toBeDisabled();
    expect(screen.getByText(/arricchito con i dati ruolo — per distretto/)).toBeInTheDocument();

    rerender(<DistrettiIndiciTable overview={makeOverview({ items: [], total_distretti: 0, total_particelle: 0 })} isLoading={false} />);

    expect(screen.getByText("Nessun distretto disponibile.")).toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });

  test("filters, sorts and exports the visible district rows", () => {
    render(<DistrettiIndiciTable overview={makeOverview()} isLoading={false} />);

    const table = screen.getByRole("table");
    expect(within(table).getByRole("columnheader", { name: /N°/ })).toHaveAttribute("aria-sort", "ascending");
    expect(within(table).getByRole("columnheader", { name: /0648 Manut./ })).toBeInTheDocument();
    expect(within(table).getByRole("columnheader", { name: /0668 Irrig./ })).toBeInTheDocument();
    expect(within(table).getByRole("columnheader", { name: /0985 Ist./ })).toBeInTheDocument();
    expect(within(table).getByText(/Totale \(5 distretti\)/)).toBeInTheDocument();
    expect(screen.getByText("5 distretti visibili")).toBeInTheDocument();

    fireEvent.click(within(table).getByRole("button", { name: /Ordina Importo ruolo/ }));
    expect(within(table).getByRole("columnheader", { name: /Importo ruolo/ })).toHaveAttribute("aria-sort", "ascending");
    expect(screen.getByText(/Ordine:/)).toHaveTextContent("crescente");

    fireEvent.click(within(table).getByRole("button", { name: /Ordina Importo ruolo/ }));
    expect(within(table).getByRole("columnheader", { name: /Importo ruolo/ })).toHaveAttribute("aria-sort", "descending");
    expect(screen.getByText(/Ordine:/)).toHaveTextContent("decrescente");

    expect(screen.getByRole("radio", { name: "Tutti" })).toHaveAttribute("aria-checked", "true");
    fireEvent.click(screen.getByRole("radio", { name: "Canaletta" }));
    expect(screen.getByRole("radio", { name: "Canaletta" })).toHaveAttribute("aria-checked", "true");
    expect(within(table).getByRole("cell", { name: "Pauli Bingias" })).toBeInTheDocument();
    expect(within(table).queryByRole("cell", { name: "Sinis Nord Est" })).not.toBeInTheDocument();
    expect(screen.getByText("1 distretti visibili")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("radio", { name: "Tutti" }));
    expect(screen.getByRole("radio", { name: "Tutti" })).toHaveAttribute("aria-checked", "true");

    fireEvent.click(screen.getByRole("button", { name: "Scarica Excel" }));
    expect(xlsxMocks.jsonToSheet).toHaveBeenCalledWith(
      expect.arrayContaining([
        expect.objectContaining({
          Indice: "Alta pressione",
          "0648 Manut. (EUR)": 600,
          "0668 Irrig. (EUR)": 430,
          "0985 Ist. (EUR)": 200,
        }),
      ]),
    );
    expect(xlsxMocks.bookAppendSheet).toHaveBeenCalledWith(expect.anything(), expect.anything(), "Distretti 2025");
    expect(xlsxMocks.write).toHaveBeenCalledWith(expect.anything(), { type: "array", bookType: "xlsx" });
    expect(createObjectUrl).toHaveBeenCalledWith(expect.any(Blob));
    expect(clickAnchor).toHaveBeenCalledTimes(1);
    expect(revokeObjectUrl).toHaveBeenCalledWith("blob:distretti");
  });

  test("exports with nd suffix when the overview year is missing", () => {
    render(<DistrettiIndiciTable overview={makeOverview({ anno_riferimento: null })} isLoading={false} />);

    fireEvent.click(screen.getByRole("button", { name: "Scarica Excel" }));

    expect(xlsxMocks.bookAppendSheet).toHaveBeenCalledWith(expect.anything(), expect.anything(), "Distretti nd");
  });
});
