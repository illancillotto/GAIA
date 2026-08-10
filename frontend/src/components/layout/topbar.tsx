import type { ReactNode } from "react";

import { useAppShellContext } from "@/components/layout/app-shell-context";
import { DesktopTopNavigation } from "@/components/layout/desktop-top-navigation";
import { OperationalSearchBox } from "@/components/search/operational-search-box";
import { StatusPill } from "@/components/ui/status-pill";
import { MenuIcon } from "@/components/ui/icons";

type TopbarProps = {
  pageTitle: string;
  breadcrumb?: string;
  actions?: ReactNode;
};

export function Topbar({ pageTitle, breadcrumb, actions }: TopbarProps) {
  const { currentUser, grantedSectionKeys, openMobileSidebar } = useAppShellContext();

  return (
    <>
      <header className="sticky top-0 z-20 flex h-[52px] items-center gap-3 border-b border-gray-100 bg-white px-4 md:px-7">
        {currentUser ? (
          <button
            type="button"
            aria-label="Apri navigazione"
            className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-gray-100 text-gray-600 transition hover:bg-gray-50 hover:text-gray-900 md:hidden"
            onClick={openMobileSidebar}
          >
            <MenuIcon className="h-4 w-4" />
          </button>
        ) : null}
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
      {currentUser ? <DesktopTopNavigation /> : null}
    </>
  );
}
