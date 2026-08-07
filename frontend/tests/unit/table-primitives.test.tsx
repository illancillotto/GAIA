import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import { Pagination } from "@/components/table/pagination";
import { TableFilters } from "@/components/table/table-filters";

describe("Pagination", () => {
  test("renders page info and navigation buttons", () => {
    const onPreviousPage = vi.fn();
    const onNextPage = vi.fn();

    render(
      <Pagination
        pageIndex={1}
        pageCount={3}
        canPreviousPage
        canNextPage
        onPreviousPage={onPreviousPage}
        onNextPage={onNextPage}
      />,
    );

    expect(screen.getByText("Pagina 2 di 3")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Precedente" }));
    fireEvent.click(screen.getByRole("button", { name: "Successiva" }));

    expect(onPreviousPage).toHaveBeenCalledTimes(1);
    expect(onNextPage).toHaveBeenCalledTimes(1);
  });

  test("shows zero page when page count is zero", () => {
    render(
      <Pagination
        pageIndex={0}
        pageCount={0}
        canPreviousPage={false}
        canNextPage={false}
        onPreviousPage={vi.fn()}
        onNextPage={vi.fn()}
      />,
    );

    expect(screen.getByText("Pagina 0 di 0")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Precedente" })).toBeDisabled();
  });
});

describe("TableFilters", () => {
  test("renders children inside grid container", () => {
    render(
      <TableFilters>
        <input aria-label="Filtro A" />
        <input aria-label="Filtro B" />
      </TableFilters>,
    );

    expect(screen.getByLabelText("Filtro A")).toBeInTheDocument();
    expect(screen.getByLabelText("Filtro B")).toBeInTheDocument();
  });
});
