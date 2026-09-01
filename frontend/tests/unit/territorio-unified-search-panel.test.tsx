import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  runSearch: vi.fn(),
  selectResult: vi.fn(),
  clear: vi.fn(),
  setQuery: vi.fn(),
  state: {} as Record<string, unknown>,
}));
vi.mock("@/components/catasto/gis/use-territorio-unified-search", () => ({
  useTerritorioUnifiedSearch: () => ({
    query: "Arborea",
    results: [],
    busy: false,
    message: null,
    runSearch: mocks.runSearch,
    selectResult: mocks.selectResult,
    clear: mocks.clear,
    setQuery: mocks.setQuery,
    ...mocks.state,
  }),
}));

import TerritorioUnifiedSearch from "@/components/catasto/gis/TerritorioUnifiedSearch";

const layer = { id: "municipal", name: "ras_limiti_comunali", queryable: "wfs_queryable" };

describe("TerritorioUnifiedSearch", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.state = {};
  });

  test("explains municipality gating and submits the unified query", () => {
    render(<TerritorioUnifiedSearch token="token" map={null} groups={[]} enabled={{}} />);
    expect(screen.getByText(/Non cerca indirizzi o numeri civici/)).toBeVisible();
    expect(screen.getByText(/attiva “Limiti amministrativi/)).toBeVisible();
    fireEvent.change(screen.getByLabelText("Cerca nel GIS"), { target: { value: "Terralba" } });
    expect(mocks.setQuery).toHaveBeenCalledWith("Terralba");
    fireEvent.submit(screen.getByRole("button", { name: "Cerca" }).closest("form")!);
    expect(mocks.runSearch).toHaveBeenCalled();
  });

  test("renders source badges, status, busy state and actions", () => {
    const result = { id: "comune:1", kind: "comune", label: "Arborea", detail: "Limite comunale", source: "RAS SITR" };
    mocks.state = { results: [result], busy: true, message: "Messaggio governato" };
    render(<TerritorioUnifiedSearch token="token" map={null} groups={[{ theme: "amministrativo", label: "", layers: [layer] } as never]} enabled={{ municipal: true }} />);
    expect(screen.queryByText(/attiva “Limiti/)).not.toBeInTheDocument();
    expect(screen.getByText("RAS SITR")).toBeVisible();
    expect(screen.getByRole("status")).toHaveTextContent("Messaggio governato");
    expect(screen.getByRole("button", { name: "Ricerca..." })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Pulisci" }));
    fireEvent.click(screen.getByRole("button", { name: /Arborea/ }));
    expect(mocks.clear).toHaveBeenCalled();
    expect(mocks.selectResult).toHaveBeenCalledWith(result);
  });
});
