import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import ArchiveList from "@/components/catasto/gis/ArchiveList";
import type { GisMapOverlayLayer, GisSavedSelectionSummary } from "@/types/gis";

const selections = [
  {
    id: "sel-1",
    name: "Layer importato",
    color: "#0F766E",
    source_filename: "import.xlsx",
    n_particelle: 1234,
    n_with_geometry: 987,
    import_summary: null,
    created_at: "2026-08-19T10:00:00Z",
    updated_at: "2026-08-19T10:00:00Z",
  },
  {
    id: "sel-2",
    name: "Layer archivio",
    color: "#DC2626",
    source_filename: null,
    n_particelle: 5,
    n_with_geometry: 2,
    import_summary: null,
    created_at: "2026-08-19T11:00:00Z",
    updated_at: "2026-08-19T11:00:00Z",
  },
] satisfies GisSavedSelectionSummary[];

const loadedLayer = {
  layer_key: "saved-sel-1",
  saved_selection_id: "sel-1",
  name: "Layer importato",
  color: "#0F766E",
  opacity: 0.4,
  showFill: false,
  visible: true,
} satisfies GisMapOverlayLayer;

const baseProps = {
  isDark: false,
  savedSelections: selections,
  loadedSavedSelectionIds: new Set<string>(["sel-1"]),
  loadedSavedSelectionLayerMap: new Map<string, GisMapOverlayLayer>([["sel-1", loadedLayer]]),
  savedSelectionFills: { "sel-2": false } as Record<string, boolean>,
  savedSelectionOpacities: { "sel-2": 0.85 } as Record<string, number>,
  savedBusy: false,
  onRefresh: vi.fn(),
  onDraftColorChange: vi.fn(),
  onCommitColor: vi.fn(),
  onDelete: vi.fn(),
  onFillChange: vi.fn(),
  onOpacityChange: vi.fn(),
  onLoad: vi.fn(),
  onRemoveLoaded: vi.fn(),
};

function renderArchiveList(overrides: Partial<typeof baseProps> = {}) {
  const props = { ...baseProps, ...overrides };
  return { ...render(<ArchiveList {...props} />), props };
}

describe("ArchiveList", () => {
  test("renders saved selections in order with counts and loaded state", () => {
    const onRefresh = vi.fn();
    const onLoad = vi.fn();
    const onRemoveLoaded = vi.fn();

    renderArchiveList({ onRefresh, onLoad, onRemoveLoaded });

    expect(screen.getByText("Archivio layer salvati")).toBeInTheDocument();
    expect(screen.getByText("Layer importato")).toBeInTheDocument();
    expect(screen.getByText(/1234\s+particelle\s+·\s+987\s+in mappa/)).toBeInTheDocument();
    expect(screen.getByText("Layer archivio")).toBeInTheDocument();
    expect(screen.getByText(/5\s+particelle\s+·\s+2\s+in mappa/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Aggiorna" }));
    expect(onRefresh).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByRole("button", { name: "Porta in primo piano" }));
    expect(onLoad).toHaveBeenCalledWith("sel-1");

    const removeButtons = screen.getAllByRole("button", { name: "Rimuovi" });
    expect(removeButtons[0]).toBeEnabled();
    fireEvent.click(removeButtons[0]);
    expect(onRemoveLoaded).toHaveBeenCalledWith("sel-1");
    expect(removeButtons[1]).toBeDisabled();
  });

  test("handles color, fill, opacity, load and delete callbacks", () => {
    const onDraftColorChange = vi.fn();
    const onCommitColor = vi.fn();
    const onDelete = vi.fn();
    const onFillChange = vi.fn();
    const onOpacityChange = vi.fn();
    const onLoad = vi.fn();

    renderArchiveList({
      onDraftColorChange,
      onCommitColor,
      onDelete,
      onFillChange,
      onOpacityChange,
      onLoad,
    });

    const colorInput = screen.getAllByTitle("Modifica colore")[0];
    fireEvent.change(colorInput, { target: { value: "#123456" } });
    const draftUpdater = onDraftColorChange.mock.calls[0][0] as (items: GisSavedSelectionSummary[]) => GisSavedSelectionSummary[];
    expect(draftUpdater(selections)[0].id).toBe("sel-1");
    fireEvent.blur(colorInput, { target: { value: "#abcdef" } });
    expect(onCommitColor).toHaveBeenCalledWith("sel-1", "#ABCDEF");

    const fillButtons = screen.getAllByRole("button", { name: "Riempimento" });
    fireEvent.click(fillButtons[0]);
    expect(onFillChange).toHaveBeenCalledWith("sel-1", true);
    fireEvent.click(fillButtons[1]);
    expect(onFillChange).toHaveBeenCalledWith("sel-2", true);

    const opacitySliders = screen.getAllByRole("slider");
    expect(opacitySliders[0]).toHaveValue("40");
    expect(opacitySliders[1]).toHaveValue("85");
    fireEvent.change(opacitySliders[1], { target: { value: "65" } });
    expect(onOpacityChange).toHaveBeenCalledWith("sel-2", 0.65);

    fireEvent.click(screen.getByRole("button", { name: "Aggiungi in mappa" }));
    expect(onLoad).toHaveBeenCalledWith("sel-2");

    fireEvent.click(screen.getAllByRole("button", { name: "Elimina" })[1]);
    expect(onDelete).toHaveBeenCalledWith("sel-2");
  });

  test("shows empty and disabled states", () => {
    const onRefresh = vi.fn();
    const onDelete = vi.fn();

    renderArchiveList({ savedSelections: [], savedBusy: true, onRefresh, onDelete });

    expect(screen.getByText("Nessuna selezione salvata.")).toBeInTheDocument();
    const refresh = screen.getByRole("button", { name: "Aggiorna" });
    expect(refresh).toBeDisabled();
    fireEvent.click(refresh);
    expect(onRefresh).not.toHaveBeenCalled();
    expect(screen.queryByRole("button", { name: "Elimina" })).not.toBeInTheDocument();
  });

  test("renders dark variant and default fill/opacity fallbacks", () => {
    const { rerender } = renderArchiveList({
      isDark: true,
      loadedSavedSelectionIds: new Set<string>(),
      loadedSavedSelectionLayerMap: new Map<string, GisMapOverlayLayer>(),
      savedSelectionFills: {},
      savedSelectionOpacities: {},
    });

    expect(screen.getByText("Archivio layer salvati")).toBeInTheDocument();
    const sliders = screen.getAllByRole("slider");
    expect(sliders[0]).toHaveValue("55");
    expect(sliders[1]).toHaveValue("55");

    rerender(<ArchiveList {...baseProps} isDark savedSelections={[]} />);
    expect(screen.getByText("Nessuna selezione salvata.")).toBeInTheDocument();
  });
});
