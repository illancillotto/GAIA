import Link from "next/link";
import type { ReactNode } from "react";

import { useAppShellContext } from "@/components/layout/app-shell-context";
import { DesktopTopNavigation } from "@/components/layout/desktop-top-navigation";
import { OperationalSearchBox } from "@/components/search/operational-search-box";
import { StatusPill } from "@/components/ui/status-pill";
import { MenuIcon } from "@/components/ui/icons";

type TopbarProps = {
  pageTitle: string;
  breadcrumb?: string;
  breadcrumbItems?: BreadcrumbItem[];
  actions?: ReactNode;
};

export type BreadcrumbItem = { label: string; href?: string };

function TopbarPagePath({ pageTitle, breadcrumb, items = [] }: {
  pageTitle: string;
  breadcrumb?: string;
  items?: BreadcrumbItem[];
}) {
  if (items.length) {
    return <nav aria-label="Percorso pagina" className="flex min-w-0 items-center gap-1.5 text-xs text-gray-600">{items.map((item, index) => <span className="flex min-w-0 items-center gap-1.5" key={`${item.label}-${index}`}>{index ? <span aria-hidden="true">/</span> : null}{item.href ? <Link className="relative z-10 inline-flex min-h-11 cursor-pointer items-center pointer-events-auto truncate underline-offset-4 hover:text-gray-900 hover:underline md:inline-flex md:min-h-9" href={item.href}>{item.label}</Link> : <span aria-current="page" className="truncate font-medium text-gray-900">{item.label}</span>}</span>)}</nav>;
  }
  return <><h1 className="min-w-0 shrink truncate text-sm font-medium text-gray-900">{pageTitle}</h1>{breadcrumb ? <span className="text-xs text-gray-600">/ {breadcrumb}</span> : null}</>;
}

export function Topbar({ pageTitle, breadcrumb, breadcrumbItems, actions }: TopbarProps) {
  const { currentUser, grantedSectionKeys, openMobileSidebar } = useAppShellContext();

  return (
    <>
      <header className="sticky top-0 z-20 flex h-[52px] items-center gap-3 border-b border-gray-100 bg-white px-4 md:px-7">
        {currentUser ? (
          <button
            type="button"
            aria-label="Apri navigazione"
            className="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-lg border border-gray-100 text-gray-600 transition hover:bg-gray-50 hover:text-gray-900 md:hidden"
            onClick={openMobileSidebar}
          >
            <MenuIcon className="h-4 w-4" />
          </button>
        ) : null}
        <TopbarPagePath breadcrumb={breadcrumb} items={breadcrumbItems} pageTitle={pageTitle} />
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
