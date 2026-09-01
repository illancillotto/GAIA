import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import DeliveryPointQuickFilters from "@/components/catasto/gis/DeliveryPointQuickFilters";

describe("DeliveryPointQuickFilters", () => {
  test("renders filter buttons and cache refresh action", () => {
    const onFilterChange = vi.fn();
    const onRefreshCache = vi.fn();

    render(
      <DeliveryPointQuickFilters
        isDark={false}
        selectedFilter="all"
        onFilterChange={onFilterChange}
        onRefreshCache={onRefreshCache}
        cacheRefreshing={false}
        cacheMessage="Cache aggiornata"
      />,
    );

    expect(screen.getByText("Filtro punti di consegna")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Tutti/i })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Con contatore/i }));
    expect(onFilterChange).toHaveBeenCalledWith("with_meter");

    fireEvent.click(screen.getByRole("button", { name: /Aggiorna cache/i }));
    expect(onRefreshCache).toHaveBeenCalledTimes(1);
    expect(screen.getByText("Cache aggiornata")).toBeInTheDocument();
  });

  test("renders selected states, disabled refresh and dark fallback dots", () => {
    const onFilterChange = vi.fn();
    const onRefreshCache = vi.fn();

    render(
      <DeliveryPointQuickFilters
        isDark
        selectedFilter="without_meter"
        onFilterChange={onFilterChange}
        onRefreshCache={onRefreshCache}
        cacheRefreshing
        cacheMessage="Cache scura aggiornata"
      />,
    );

    expect(screen.getByText("Cache scura aggiornata")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Senza contatore/i }));
    expect(onFilterChange).toHaveBeenCalledWith("without_meter");
    expect(screen.getByRole("button", { name: /Aggiorno/i })).toBeDisabled();
    expect(screen.queryByText("Cache aggiornata")).not.toBeInTheDocument();
  });

  test("renders the with-meter selected style branch", () => {
    render(
      <DeliveryPointQuickFilters
        isDark={false}
        selectedFilter="with_meter"
        onFilterChange={vi.fn()}
        onRefreshCache={vi.fn()}
        cacheRefreshing={false}
        cacheMessage={null}
      />,
    );

    expect(screen.getByRole("button", { name: /Con contatore/i })).toBeInTheDocument();
  });
});
