import type { ReactNode } from "react";

import { useAppShellContext } from "@/components/layout/app-shell-context";
import { OperationalSearchBox } from "@/components/search/operational-search-box";
import { StatusPill } from "@/components/ui/status-pill";

type TopbarProps = {
  pageTitle: string;
  breadcrumb?: string;
  actions?: ReactNode;
};

export function Topbar({ pageTitle, breadcrumb, actions }: TopbarProps) {
  const { currentUser, grantedSectionKeys } = useAppShellContext();

  return (
    <header className="sticky top-0 z-10 flex h-[52px] items-center gap-3 border-b border-gray-100 bg-white px-7">
      <h1 className="min-w-0 shrink truncate text-sm font-medium text-gray-900">{pageTitle}</h1>
      {breadcrumb ? <span className="text-xs text-gray-400">/ {breadcrumb}</span> : null}
      <div className="ml-auto flex min-w-0 flex-1 items-center justify-end gap-3">
        {currentUser ? (
          <OperationalSearchBox
            currentUser={currentUser}
            grantedSectionKeys={grantedSectionKeys}
            variant="compact"
            enableHotkey
            className="hidden w-full max-w-xl min-[1100px]:block"
          />
        ) : null}
        <StatusPill />
        {actions}
      </div>
    </header>
  );
}
