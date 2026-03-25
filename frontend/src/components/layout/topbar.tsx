import type { ReactNode } from "react";

import { StatusPill } from "@/components/ui/status-pill";

type TopbarProps = {
  pageTitle: string;
  breadcrumb?: string;
  actions?: ReactNode;
};

export function Topbar({ pageTitle, breadcrumb, actions }: TopbarProps) {
  return (
    <header className="sticky top-0 z-10 flex h-[52px] items-center gap-3 border-b border-gray-100 bg-white px-7">
      <h1 className="text-sm font-medium text-gray-900">{pageTitle}</h1>
      {breadcrumb ? <span className="text-xs text-gray-400">/ {breadcrumb}</span> : null}
      <div className="ml-auto flex items-center gap-3">
        <StatusPill />
        {actions}
      </div>
    </header>
  );
}
