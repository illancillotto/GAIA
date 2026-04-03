"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useMemo, useState } from "react";

import { ChevronRightIcon, GridIcon, LockIcon, RefreshIcon, SearchIcon, ServerIcon, UserIcon } from "@/components/ui/icons";
import { cn } from "@/lib/cn";
import type { CurrentUser } from "@/types/api";

type PlatformSidebarProps = {
  currentModuleLabel: string;
  currentUser: CurrentUser;
};

type PlatformModule = {
  href: string;
  label: string;
  icon: typeof GridIcon;
};

const platformModules: PlatformModule[] = [
  { href: "/nas-control", label: "NAS Control", icon: LockIcon },
  { href: "/network", label: "Rete", icon: ServerIcon },
  { href: "/inventory", label: "Inventario", icon: SearchIcon },
  { href: "/catasto", label: "Catasto", icon: GridIcon },
  { href: "/elaborazioni", label: "Elaborazioni", icon: RefreshIcon },
  { href: "/utenze", label: "Utenze", icon: UserIcon },
];

export function PlatformSidebar({ currentModuleLabel, currentUser }: PlatformSidebarProps) {
  const pathname = usePathname();
  const [isModuleSwitcherOpen, setIsModuleSwitcherOpen] = useState(false);
  const visiblePlatformModules = platformModules.filter(({ href }) => {
    const moduleKey =
      href === "/nas-control"
        ? "accessi"
        : href === "/network"
          ? "rete"
          : href === "/inventory"
            ? "inventario"
            : href === "/catasto"
              ? "catasto"
              : href === "/elaborazioni"
                ? "catasto"
              : href === "/utenze"
                ? "utenze"
              : "";

    if (!moduleKey) return true;
    return currentUser.enabled_modules.includes(moduleKey);
  });
  const activePlatformModule = useMemo(
    () => visiblePlatformModules.find(({ href }) => pathname === href || pathname.startsWith(`${href}/`)),
    [pathname, visiblePlatformModules],
  );
  const ActiveModuleIcon = activePlatformModule?.icon || ServerIcon;

  return (
    <>
      <div className="border-b border-gray-100 px-4 py-5">
        <div className="mb-3 flex w-fit items-center gap-2 rounded-lg bg-[#1D4E35] px-3 py-2 text-white">
          <ServerIcon className="h-4 w-4" />
          <span className="text-xs font-medium tracking-wide">GAIA</span>
        </div>
        <p className="text-sm font-medium leading-tight text-gray-800">Consorzio di Bonifica</p>
        <p className="text-xs text-gray-400">dell&apos;Oristanese</p>
      </div>

      <nav className="px-2 py-3">
        <div className="mx-2 mb-3 border-b border-gray-100 pb-3">
          <Link
            href="/"
            className="inline-flex rounded-lg px-2.5 py-2 text-xs font-medium tracking-wide text-gray-500 transition hover:bg-gray-50 hover:text-gray-800"
          >
            ← Home GAIA
          </Link>
        </div>

        <p className="px-2 pb-1 text-[10px] font-medium uppercase tracking-widest text-gray-400">
          Modulo attivo
        </p>
        <div className="px-2">
          <button
            type="button"
            onClick={() => setIsModuleSwitcherOpen((currentValue) => !currentValue)}
            className="flex w-full items-center gap-2 rounded-xl border border-[#8CB39D] bg-[#EAF3E8] px-3 py-2.5 text-left text-sm text-[#1D4E35] shadow-[0_1px_0_rgba(29,78,53,0.04)] transition hover:bg-[#E3EFE1]"
          >
            <ActiveModuleIcon className="h-4 w-4 shrink-0" />
            <span className="flex-1 font-medium">{activePlatformModule?.label || currentModuleLabel}</span>
            <ChevronRightIcon className={cn("h-4 w-4 shrink-0 transition-transform", isModuleSwitcherOpen ? "rotate-90" : undefined)} />
          </button>

          {isModuleSwitcherOpen ? (
            <div className="mt-2 space-y-1 rounded-xl border border-gray-100 bg-gray-50 p-2">
              {visiblePlatformModules.map(({ href, label, icon: Icon }) => {
                const isActive = pathname === href || pathname.startsWith(`${href}/`);
                return (
                  <Link
                    key={href}
                    href={href}
                    className={cn(
                      "flex items-center gap-2 rounded-lg px-2.5 py-2 text-sm transition-colors",
                      isActive
                        ? "bg-white font-medium text-[#1D4E35] shadow-sm"
                        : "text-gray-500 hover:bg-white hover:text-gray-800",
                    )}
                    onClick={() => setIsModuleSwitcherOpen(false)}
                  >
                    <Icon className="h-4 w-4 shrink-0" />
                    <span className="flex-1">{label}</span>
                  </Link>
                );
              })}
            </div>
          ) : null}
        </div>
      </nav>
    </>
  );
}
