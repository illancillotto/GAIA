import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import DistrettiPanel from "@/components/catasto/gis/DistrettiPanel";
import type { CatDistretto } from "@/types/catasto";

const distretti = [
  { id: "dist-1", num_distretto: "1", nome_distretto: "Nord" },
  { id: "dist-2", num_distretto: "2", nome_distretto: "Sud" },
] as CatDistretto[];

const baseProps = {
  isDark: false,
  selectedDistretto: null as CatDistretto | null,
  distrettiOpen: true,
  onToggleOpen: vi.fn(),
  distrettoColorMap: { "1": "#2E7D32", "2": "#1565C0" } as Record<string, string>,
  showParticelleFill: false,
  onToggleParticelleFill: vi.fn(),
  distrettiSearch: "",
  onSearchChange: vi.fn(),
  onClearSearch: vi.fn(),
  distrettiLoading: false,
  distretti,
  filteredDistretti: distretti,
  distrettoLayer: "",
  onSelectDistretto: vi.fn(),
  onClearDistretto: vi.fn(),
};

function renderPanel(overrides: Partial<typeof baseProps> = {}) {
  const props = { ...baseProps, ...overrides };
  return { ...render(<DistrettiPanel {...props} />), props };
}

describe("DistrettiPanel", () => {
  test("renders selected distretto details and preserves controls", () => {
    const onToggleOpen = vi.fn();
    const onToggleParticelleFill = vi.fn();
    const onClearDistretto = vi.fn();

    renderPanel({
      selectedDistretto: distretti[0],
      distrettoLayer: "1",
      showParticelleFill: true,
      onToggleOpen,
      onToggleParticelleFill,
      onClearDistretto,
    });

    expect(screen.getByText("Filtro attivo: distretto 1")).toBeInTheDocument();
    expect(screen.getAllByText("Distretto 1")).toHaveLength(2);
    expect(screen.getAllByText("Nord")).toHaveLength(2);

    fireEvent.click(screen.getByRole("button", { name: /Distretti irrigui/i }));
    expect(onToggleOpen).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByRole("button", { name: "Tutti" }));
    expect(onClearDistretto).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByRole("button", { name: "Nascondi riempimento particelle" }));
    expect(onToggleParticelleFill).toHaveBeenCalledTimes(1);
  });

  test("updates search, clears search and selects a distretto", () => {
    const onSearchChange = vi.fn();
    const onClearSearch = vi.fn();
    const onSelectDistretto = vi.fn();

    renderPanel({
      distrettiSearch: "su",
      filteredDistretti: [distretti[1]],
      onSearchChange,
      onClearSearch,
      onSelectDistretto,
    });

    const input = screen.getByLabelText("Cerca distretto");
    fireEvent.change(input, { target: { value: "nord" } });
    expect(onSearchChange).toHaveBeenCalledWith("nord");

    fireEvent.click(screen.getByRole("button", { name: "Pulisci filtro distretti" }));
    expect(onClearSearch).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByRole("button", { name: /Distretto 2/i }));
    expect(onSelectDistretto).toHaveBeenCalledWith(distretti[1]);
  });

  test("shows loading, empty and no-result states", () => {
    const { rerender } = render(<DistrettiPanel {...baseProps} distrettiLoading />);
    expect(screen.getByText("Caricamento distretti...")).toBeInTheDocument();

    rerender(<DistrettiPanel {...baseProps} distretti={[]} filteredDistretti={[]} />);
    expect(screen.getByText("Nessun distretto disponibile.")).toBeInTheDocument();

    rerender(<DistrettiPanel {...baseProps} distrettiSearch="zzz" filteredDistretti={[]} />);
    expect(screen.getByText("Nessun distretto trovato per “zzz”.")).toBeInTheDocument();
  });

  test("keeps closed panel body hidden", () => {
    renderPanel({ distrettiOpen: false });

    expect(screen.getByText("Seleziona un distretto per centrare la mappa e isolare il perimetro.")).toBeInTheDocument();
    expect(screen.queryByLabelText("Cerca distretto")).not.toBeInTheDocument();
  });

  test("shows light selected distretto with fill disabled", () => {
    const onToggleParticelleFill = vi.fn();

    renderPanel({
      selectedDistretto: distretti[0],
      showParticelleFill: false,
      onToggleParticelleFill,
    });

    fireEvent.click(screen.getByRole("button", { name: "Mostra riempimento particelle" }));
    expect(onToggleParticelleFill).toHaveBeenCalledTimes(1);
  });

  test("shows dark loading, empty and no-result states", () => {
    const { rerender } = render(<DistrettiPanel {...baseProps} isDark distrettiLoading />);
    expect(screen.getByText("Caricamento distretti...")).toBeInTheDocument();

    rerender(<DistrettiPanel {...baseProps} isDark distretti={[]} filteredDistretti={[]} />);
    expect(screen.getByText("Nessun distretto disponibile.")).toBeInTheDocument();

    rerender(<DistrettiPanel {...baseProps} isDark distrettiSearch="zzz" filteredDistretti={[]} />);
    expect(screen.getByText("Nessun distretto trovato per “zzz”.")).toBeInTheDocument();
  });

  test("renders nonselected dark distretto rows", () => {
    const onSelectDistretto = vi.fn();

    renderPanel({ isDark: true, onSelectDistretto });

    fireEvent.click(screen.getByRole("button", { name: /Distretto 2/i }));
    expect(onSelectDistretto).toHaveBeenCalledWith(distretti[1]);
  });

  test("renders dark theme and fallback labels without changing actions", () => {
    const unnamed = { ...distretti[0], nome_distretto: null, num_distretto: "9" };
    const onSelectDistretto = vi.fn();
    const onToggleParticelleFill = vi.fn();

    renderPanel({
      isDark: true,
      selectedDistretto: unnamed,
      distretti: [unnamed],
      filteredDistretti: [unnamed],
      distrettoLayer: "9",
      distrettoColorMap: {},
      showParticelleFill: false,
      onSelectDistretto,
      onToggleParticelleFill,
    });

    expect(screen.getByText("Filtro attivo: distretto 9")).toBeInTheDocument();
    expect(screen.getAllByText("Senza nome")).toHaveLength(2);
    fireEvent.click(screen.getByRole("button", { name: "Mostra riempimento particelle" }));
    expect(onToggleParticelleFill).toHaveBeenCalledTimes(1);
    const distrettoButtons = screen.getAllByRole("button", { name: /Distretto 9/i });
    fireEvent.click(distrettoButtons[distrettoButtons.length - 1]);
    expect(onSelectDistretto).toHaveBeenCalledWith(unnamed);
  });
});
