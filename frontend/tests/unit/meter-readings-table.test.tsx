import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { MeterReadingsTable } from "@/components/catasto/meter-readings-table";

const mocks = vi.hoisted(() => ({
  getStoredAccessToken: vi.fn(),
  catastoGetMeterReading: vi.fn(),
  catastoListDistretti: vi.fn(),
  catastoListMeterReadingImports: vi.fn(),
  catastoListMeterReadings: vi.fn(),
}));

vi.mock("@/lib/auth", () => ({
  getStoredAccessToken: mocks.getStoredAccessToken,
}));

vi.mock("@/lib/api/catasto", () => ({
  catastoGetMeterReading: mocks.catastoGetMeterReading,
  catastoListDistretti: mocks.catastoListDistretti,
  catastoListMeterReadingImports: mocks.catastoListMeterReadingImports,
  catastoListMeterReadings: mocks.catastoListMeterReadings,
}));

vi.mock("@/components/catasto/meter-reading-detail-drawer", () => ({
  MeterReadingDetailDrawer: () => null,
}));

function buildReading(overrides: Record<string, unknown> = {}) {
  return {
    id: "reading-1",
    import_id: null,
    distretto_id: "dist-1",
    anno: 2026,
    row_number: null,
    excel_id: null,
    punto_consegna: "CNT-001",
    matricola: "A1234",
    sigillo: null,
    record_type: "CONT_NO_TES",
    record_kind: "meter_reading",
    operational_state: "active",
    tipologia_idrante: null,
    firmware_version: null,
    battery_level: null,
    lettura_iniziale: "200",
    lettura_finale: "258",
    consumo_mc: "58",
    consumo_effettivo_mc: "58",
    data_lettura: "2026-06-22",
    operatore_lettura: "Mario Rossi",
    intervento_da_eseguire: null,
    intervento_eseguito: null,
    operatore_intervento: null,
    data_intervento: null,
    dui: null,
    codice_fiscale: null,
    codice_fiscale_normalizzato: null,
    subject_id: null,
    subject_display_name: null,
    coltura: null,
    tariffa: null,
    fondo_chiuso: null,
    telefono: null,
    note: null,
    validation_status: "valid",
    validation_messages: [],
    source: "excel",
    mobile_session_id: null,
    gps_lat: null,
    gps_lng: null,
    photo_url: null,
    offline_created_at: null,
    synced_at: null,
    sync_status: null,
    device_id: null,
    mobile_operator_id: null,
    manual_corrections: null,
    manual_override_updated_at: null,
    manual_override_updated_by: null,
    manual_audits: [],
    created_at: "2026-06-22T13:08:42.132Z",
    updated_at: "2026-06-22T13:08:42.132Z",
    ...overrides,
  };
}

function buildListResponse(source: "excel" | "mobile") {
  return {
    record_tab_counts: { meter: 1, other: 0 },
    operational_counts: { all: 1, unlinked: 1, activities: 0, dismissed: 0, lowBattery: 0 },
    validation_counts: { all: 1, valid: 1, warning: 0, error: 0 },
    items: [
      buildReading({
        source,
        mobile_session_id: source === "mobile" ? "activity-1" : null,
        device_id: source === "mobile" ? "device-1" : null,
        mobile_operator_id: source === "mobile" ? "operator-1" : null,
      }),
    ],
    total: 1,
    page: 1,
    page_size: 100,
  };
}

describe("MeterReadingsTable", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.getStoredAccessToken.mockReturnValue("token");
    mocks.catastoListMeterReadingImports.mockResolvedValue([{ id: "import-1", anno: 2026 }]);
    mocks.catastoListDistretti.mockResolvedValue([]);
    mocks.catastoGetMeterReading.mockResolvedValue(buildReading());
    mocks.catastoListMeterReadings.mockImplementation(async (_token, params) => {
      if (params?.pageSize === 1) {
        return buildListResponse("excel");
      }
      return buildListResponse(params?.source === "mobile" ? "mobile" : "excel");
    });
  });

  test("applies mobile source filter and shows mobile badge", async () => {
    render(<MeterReadingsTable />);

    expect(await screen.findByText("CNT-001")).toBeInTheDocument();
    expect(screen.queryByText("GaTe Mobile")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Solo mobile/i }));

    await waitFor(() => {
      expect(mocks.catastoListMeterReadings).toHaveBeenLastCalledWith(
        "token",
        expect.objectContaining({ source: "mobile" }),
      );
    });

    expect(await screen.findByText("GaTe Mobile")).toBeInTheDocument();
    expect(screen.getByText("Origine: GaTe Mobile")).toBeInTheDocument();
  });
});
