import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import DrawingTools, { MeasurementTools } from "@/components/catasto/gis/DrawingTools";

describe("DrawingTools", () => {
  test("renders horizontal empty and loading states and starts drawing", () => {
    const draw = vi.fn();
    const view = render(<DrawingTools onDrawPolygon={draw} onClearDrawing={vi.fn()} isLoading={false} hasSelection={false} />);
    expect(screen.getByText("Disegna un'area nel GIS")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Disegna area" }));
    expect(draw).toHaveBeenCalled();
    view.rerender(<DrawingTools onDrawPolygon={draw} onClearDrawing={vi.fn()} isLoading hasSelection={false} />);
    expect(screen.getByText("Analisi in corso...")).toBeInTheDocument();
    view.rerender(<DrawingTools onDrawPolygon={draw} onClearDrawing={vi.fn()} isLoading={false} hasSelection nParticelle={1} />);
    expect(screen.getByRole("button", { name: "Cancella selezione" })).toBeInTheDocument();
  });

  test("renders vertical selected states with and without a count", () => {
    const clear = vi.fn();
    const view = render(<DrawingTools orientation="vertical" onDrawPolygon={vi.fn()} onClearDrawing={clear} isLoading={false} hasSelection nParticelle={1234} />);
    expect(screen.getByText(/1234 particelle selezionate/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Cancella selezione" }));
    expect(clear).toHaveBeenCalled();
    view.rerender(<DrawingTools orientation="vertical" onDrawPolygon={vi.fn()} onClearDrawing={clear} isLoading={false} hasSelection />);
    expect(screen.getByText("Disegna un'area nel GIS")).toBeInTheDocument();
  });

  test("exposes measurement mode callbacks and optional result", () => {
    const mode = vi.fn();
    const clear = vi.fn();
    const view = render(<MeasurementTools mode={null} result={null} onModeChange={mode} onClear={clear} />);
    fireEvent.click(screen.getByRole("button", { name: "Distanza" }));
    fireEvent.click(screen.getByRole("button", { name: "Area" }));
    fireEvent.click(screen.getByRole("button", { name: "Pulisci" }));
    expect(mode.mock.calls).toEqual([["distance"], ["area"]]);
    expect(clear).toHaveBeenCalled();
    view.rerender(<MeasurementTools mode="area" result="2.50 ha" onModeChange={mode} onClear={clear} />);
    expect(screen.getByText("2.50 ha")).toBeInTheDocument();
  });
});
