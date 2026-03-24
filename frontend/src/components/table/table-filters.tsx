import type { ReactNode } from "react";

type TableFiltersProps = {
  children: ReactNode;
};

export function TableFilters({ children }: TableFiltersProps) {
  return <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">{children}</div>;
}
