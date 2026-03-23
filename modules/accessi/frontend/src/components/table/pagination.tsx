type PaginationProps = {
  pageIndex: number;
  pageCount: number;
  canPreviousPage: boolean;
  canNextPage: boolean;
  onPreviousPage: () => void;
  onNextPage: () => void;
};

export function Pagination({
  pageIndex,
  pageCount,
  canPreviousPage,
  canNextPage,
  onPreviousPage,
  onNextPage,
}: PaginationProps) {
  return (
    <div className="flex items-center justify-between gap-3 border-t border-gray-100 px-4 py-3">
      <p className="text-xs text-gray-400">
        Pagina {pageCount === 0 ? 0 : pageIndex + 1} di {pageCount}
      </p>
      <div className="flex items-center gap-2">
        <button className="btn-secondary" disabled={!canPreviousPage} onClick={onPreviousPage} type="button">
          Precedente
        </button>
        <button className="btn-secondary" disabled={!canNextPage} onClick={onNextPage} type="button">
          Successiva
        </button>
      </div>
    </div>
  );
}
