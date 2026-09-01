import { fireEvent, render, screen } from "@testing-library/react";
import type { Dispatch, SetStateAction } from "react";
import { describe, expect, test, vi } from "vitest";

import WhiteCompanyReportsPanel, {
  EMPTY_WHITECOMPANY_REPORT_FILTERS,
  type WhiteCompanyReportFilters,
} from "@/components/catasto/gis/WhiteCompanyReportsPanel";
import type { WhiteCompanyReportLayerResponse } from "@/types/gis";

function buildLayer(overrides: Partial<WhiteCompanyReportLayerResponse> = {}): WhiteCompanyReportLayerResponse {
  return {
    generated_at: "2026-07-15T08:00:00",
    tipologie: ["Perdita condotta", "Allaccio"],
    operatori: ["Mario Rossi", "Giulia Bianchi"],
    stats: { total: 12, mapped: 8, unmapped: 4, truncated: false },
    geojson: { type: "FeatureCollection", features: [{ type: "Feature", properties: { id: "r-1" }, geometry: { type: "Point", coordinates: [8.5, 39.9] } }] },
    ...overrides,
  };
}

function renderPanel(overrides: Partial<{
  isDark: boolean;
  token: string | null;
  layer: WhiteCompanyReportLayerResponse | null;
  visible: boolean;
  busy: boolean;
  error: string | null;
  filters: WhiteCompanyReportFilters;
  onVisibleChange: Dispatch<SetStateAction<boolean>>;
  onFiltersChange: Dispatch<SetStateAction<WhiteCompanyReportFilters>>;
  onLoadLayer: (filters?: WhiteCompanyReportFilters) => void | Promise<void>;
}> = {}) {
  const resolvedFilterUpdates: WhiteCompanyReportFilters[] = [];
  const initialFilters = overrides.filters ?? { ...EMPTY_WHITECOMPANY_REPORT_FILTERS };
  const defaultFiltersSetter = vi.fn((updater: SetStateAction<WhiteCompanyReportFilters>) => {
    resolvedFilterUpdates.push(typeof updater === "function" ? updater(initialFilters) : updater);
  });
  const props = {
    isDark: false,
    token: "token",
    layer: buildLayer(),
    visible: true,
    busy: false,
    error: null,
    filters: initialFilters,
    onVisibleChange: vi.fn(),
    onFiltersChange: defaultFiltersSetter,
    onLoadLayer: vi.fn(),
    resolvedFilterUpdates,
    ...overrides,
  };
  render(<WhiteCompanyReportsPanel {...props} />);
  return props;
}

describe("WhiteCompanyReportsPanel", () => {
  test("renders stats, filter options and visibility control", () => {
    const props = renderPanel();

    expect(screen.getByText("Segnalazioni WhiteCompany")).toBeInTheDocument();
    expect(screen.getByText("12")).toBeInTheDocument();
    expect(screen.getByText("8")).toBeInTheDocument();
    expect(screen.getByText("4")).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Perdita condotta" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Mario Rossi" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("checkbox", { name: "Visibile" }));
    expect(props.onVisibleChange).toHaveBeenCalledWith(expect.any(Function));
    expect(vi.mocked(props.onVisibleChange).mock.calls[0][0](true)).toBe(false);
  });

  test("updates filters through the same functional setters used by the page", () => {
    const props = renderPanel({ filters: { dateFrom: "", dateTo: "", tipologia: "", operatore: "" } });

    fireEvent.change(screen.getByLabelText("Da"), { target: { value: "2026-07-01" } });
    fireEvent.change(screen.getByLabelText("A"), { target: { value: "2026-07-31" } });
    fireEvent.change(screen.getByLabelText("Tipologia"), { target: { value: "Allaccio" } });
    fireEvent.change(screen.getByLabelText("Operatore"), { target: { value: "Giulia Bianchi" } });

    expect(props.onFiltersChange).toHaveBeenCalledTimes(4);
    expect(props.resolvedFilterUpdates).toEqual([
      { ...props.filters, dateFrom: "2026-07-01" },
      { ...props.filters, dateTo: "2026-07-31" },
      { ...props.filters, tipologia: "Allaccio" },
      { ...props.filters, operatore: "Giulia Bianchi" },
    ]);
  });

  test("preserves apply, reset, disabled and warning behaviours", () => {
    const props = renderPanel({
      busy: false,
      layer: buildLayer({ stats: { total: 20, mapped: 15, unmapped: 5, truncated: true } }),
      filters: { dateFrom: "2026-07-01", dateTo: "2026-07-31", tipologia: "Allaccio", operatore: "Mario Rossi" },
    });

    fireEvent.click(screen.getByRole("button", { name: "Applica filtri" }));
    expect(props.onLoadLayer).toHaveBeenCalledWith();

    fireEvent.click(screen.getByRole("button", { name: "Azzera" }));
    expect(props.onFiltersChange).toHaveBeenLastCalledWith(EMPTY_WHITECOMPANY_REPORT_FILTERS);
    expect(props.onLoadLayer).toHaveBeenLastCalledWith(EMPTY_WHITECOMPANY_REPORT_FILTERS);
    expect(screen.getByText("Mostrati 1 marker su 15: restringi i filtri per vedere tutto.")).toBeInTheDocument();
  });

  test("shows loading, error and token disabled states", () => {
    renderPanel({ token: null, busy: true, error: "Errore layer WhiteCompany" });

    expect(screen.getByRole("button", { name: "Carico..." })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Azzera" })).toBeDisabled();
    expect(screen.getByText("Errore layer WhiteCompany")).toBeInTheDocument();
  });

  test("renders the dark empty-state variant without optional layer data", () => {
    renderPanel({ isDark: true, layer: null, visible: false, busy: false, error: null });

    expect(screen.getByRole("checkbox", { name: "Visibile" })).not.toBeChecked();
    expect(screen.getAllByText("0")).toHaveLength(3);
    expect(screen.getByRole("button", { name: "Applica filtri" })).toBeEnabled();
    expect(screen.queryByText(/Mostrati .* marker/)).not.toBeInTheDocument();
  });

  test("disables actions when only the token is missing", () => {
    renderPanel({ token: null, busy: false });

    expect(screen.getByRole("button", { name: "Applica filtri" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Azzera" })).toBeDisabled();
  });

  test("renders dark error and truncated warning variants", () => {
    renderPanel({
      isDark: true,
      error: "Errore layer scuro",
      layer: buildLayer({ stats: { total: 20, mapped: 15, unmapped: 5, truncated: true } }),
    });

    expect(screen.getByText("Errore layer scuro")).toBeInTheDocument();
    expect(screen.getByText("Mostrati 1 marker su 15: restringi i filtri per vedere tutto.")).toBeInTheDocument();
  });
});
