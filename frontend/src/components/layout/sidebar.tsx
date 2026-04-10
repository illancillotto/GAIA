"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/cn";
import type { CurrentUser } from "@/types/api";
import { Avatar } from "@/components/ui/avatar";
import { ModuleSidebar } from "@/components/layout/module-sidebar";
import { PlatformSidebar } from "@/components/layout/platform-sidebar";
import { UserIcon } from "@/components/ui/icons";

type SidebarProps = {
  currentUser: CurrentUser;
  onLogout: () => void;
  reviewBadge?: number;
  userBadge?: number;
  grantedSectionKeys?: string[];
};

export function Sidebar({
  currentUser,
  onLogout,
  reviewBadge = 0,
  userBadge = 0,
  grantedSectionKeys = [],
}: SidebarProps) {
  const pathname = usePathname();
  const currentModuleKey =
    pathname.startsWith("/gaia/users")
      ? "gaia"
      : pathname.startsWith("/nas-control")
        ? "nas_control"
        : pathname.startsWith("/elaborazioni")
          ? "elaborazioni"
          : pathname.startsWith("/catasto")
            ? "catasto"
            : pathname.startsWith("/utenze")
              ? "utenze"
              : pathname.startsWith("/anagrafica")
                ? "utenze"
                : pathname.startsWith("/network")
                  ? "network"
                  : pathname.startsWith("/inventory")
                    ? "inventory"
                    : pathname.startsWith("/operazioni")
                      ? "operazioni"
                      : pathname.startsWith("/riordino")
                        ? "riordino"
                      : "nas_control";

  const currentModuleLabel =
    currentModuleKey === "gaia"
      ? "Utenti GAIA"
      : currentModuleKey === "nas_control"
        ? "NAS Control"
        : currentModuleKey === "elaborazioni"
          ? "Elaborazioni"
          : currentModuleKey === "catasto"
            ? "Catasto"
            : currentModuleKey === "utenze"
              ? "Utenze"
              : currentModuleKey === "network"
                ? "Rete"
                : currentModuleKey === "inventory"
                  ? "Inventario"
                  : currentModuleKey === "operazioni"
                    ? "Operazioni"
                    : currentModuleKey === "riordino"
                      ? "Riordino"
                    : "NAS Control";
  const canManageGaiaUsers =
    (currentUser.role === "admin" || currentUser.role === "super_admin")
    && currentUser.enabled_modules.includes("accessi");

  return (
    <aside className="sticky top-0 flex h-screen w-[220px] shrink-0 flex-col border-r border-gray-100 bg-white">
      <div className="flex-1 overflow-y-auto">
        <PlatformSidebar currentModuleLabel={currentModuleLabel} currentUser={currentUser} />
        <ModuleSidebar
          currentModuleKey={currentModuleKey}
          reviewBadge={reviewBadge}
          userBadge={userBadge}
          grantedSectionKeys={grantedSectionKeys}
        />
      </div>

      <div className="border-t border-gray-100 px-4 py-3">
        {canManageGaiaUsers ? (
          <div className="mb-3 border-b border-gray-100 pb-3">
            <p className="pb-1 text-[10px] font-medium uppercase tracking-widest text-gray-400">
              Amministrazione
            </p>
            <Link
              href="/gaia/users"
              className={cn(
                "flex items-center gap-2 rounded-lg px-2 py-2 text-sm transition-colors",
                pathname === "/gaia/users" || pathname.startsWith("/gaia/users/")
                  ? "bg-[#EAF3E8] font-medium text-[#1D4E35]"
                  : "text-gray-500 hover:bg-gray-50 hover:text-gray-800",
              )}
            >
              <UserIcon className="h-4 w-4 shrink-0" />
              <span className="flex-1">Utenti GAIA</span>
            </Link>
          </div>
        ) : null}

        <div className="flex items-center gap-2">
          <Avatar label={currentUser.username} />
          <div className="min-w-0">
            <p className="truncate text-sm font-medium text-gray-800">{currentUser.username}</p>
            <p className="text-xs text-gray-400">{currentUser.role}</p>
          </div>
          <div className="ml-auto h-2 w-2 rounded-full bg-[#1D9E75]" title="Backend connesso" />
        </div>
        <button className="mt-2 text-xs font-medium text-gray-500 transition hover:text-[#1D4E35]" onClick={onLogout} type="button">
          Logout
        </button>
      </div>
    </aside>
  );
}
