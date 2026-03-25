"use client";

import {
  type ColumnDef,
  flexRender,
  getCoreRowModel,
  getPaginationRowModel,
  useReactTable,
} from "@tanstack/react-table";

import { EmptyState } from "@/components/ui/empty-state";
import { SearchIcon } from "@/components/ui/icons";
import { Pagination } from "@/components/table/pagination";

type DataTableProps<TData> = {
  data: TData[];
  columns: ColumnDef<TData>[];
  emptyTitle?: string;
  emptyDescription?: string;
  initialPageSize?: number;
  onRowClick?: (row: TData) => void;
};

export function DataTable<TData extends object>({
  data,
  columns,
  emptyTitle = "Nessun risultato",
  emptyDescription = "Nessun record disponibile per i filtri attivi.",
  initialPageSize = 10,
  onRowClick,
}: DataTableProps<TData>) {
  const table = useReactTable({
    data,
    columns,
    initialState: {
      pagination: {
        pageIndex: 0,
        pageSize: initialPageSize,
      },
    },
    getCoreRowModel: getCoreRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
  });

  const rows = table.getRowModel().rows;

  return (
    <div className="overflow-hidden rounded-xl border border-gray-100 bg-white">
      {rows.length === 0 ? (
        <div className="p-5">
          <EmptyState
            icon={SearchIcon}
            title={emptyTitle}
            description={emptyDescription}
          />
        </div>
      ) : (
        <>
          <div className="overflow-x-auto">
            <table className="data-table">
              <thead>
                {table.getHeaderGroups().map((headerGroup) => (
                  <tr key={headerGroup.id}>
                    {headerGroup.headers.map((header) => (
                      <th key={header.id}>
                        {header.isPlaceholder
                          ? null
                          : flexRender(header.column.columnDef.header, header.getContext())}
                      </th>
                    ))}
                  </tr>
                ))}
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr
                    key={row.id}
                    className={onRowClick ? "cursor-pointer transition hover:bg-gray-50 focus-within:bg-gray-50" : undefined}
                    onClick={onRowClick ? () => onRowClick(row.original) : undefined}
                  >
                    {row.getVisibleCells().map((cell) => (
                      <td key={cell.id}>
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Pagination
            pageIndex={table.getState().pagination.pageIndex}
            pageCount={table.getPageCount()}
            canPreviousPage={table.getCanPreviousPage()}
            canNextPage={table.getCanNextPage()}
            onPreviousPage={() => table.previousPage()}
            onNextPage={() => table.nextPage()}
          />
        </>
      )}
    </div>
  );
}
