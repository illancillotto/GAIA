"use client";

import { usePathname } from "next/navigation";

import type { CurrentUser } from "@/types/api";
import { Avatar } from "@/components/ui/avatar";
import { ModuleSidebar } from "@/components/layout/module-sidebar";
import { PlatformSidebar } from "@/components/layout/platform-sidebar";

type SidebarProps = {
  currentUser: CurrentUser;
  onLogout: () => void;
  reviewBadge?: number;
  userBadge?: number;
};

export function Sidebar({ currentUser, onLogout, reviewBadge = 0, userBadge = 0 }: SidebarProps) {
  const pathname = usePathname();
  const currentModuleKey =
    pathname.startsWith("/catasto")
      ? "catasto"
      : pathname.startsWith("/network")
        ? "network"
        : pathname.startsWith("/inventory")
          ? "inventory"
          : "accessi";

  const currentModuleLabel =
    currentModuleKey === "catasto"
      ? "Catasto"
      : currentModuleKey === "network"
        ? "Rete"
        : currentModuleKey === "inventory"
          ? "Inventario"
          : "Accessi";

  return (
    <aside className="sticky top-0 flex h-screen w-[220px] shrink-0 flex-col border-r border-gray-100 bg-white">
      <div className="flex-1 overflow-y-auto">
        <PlatformSidebar currentModuleLabel={currentModuleLabel} />
        <ModuleSidebar currentModuleKey={currentModuleKey} reviewBadge={reviewBadge} userBadge={userBadge} />
      </div>

      <div className="border-t border-gray-100 px-4 py-3">
        <div className="flex items-center gap-2">
          <Avatar label={currentUser.username} />
          <div className="min-w-0">
            <p className="truncate text-sm font-medium text-gray-800">{currentUser.username}</p>
            <p className="text-xs text-gray-400">{currentUser.role}</p>
          </div>
          <div className="ml-auto h-2 w-2 rounded-full bg-[#1D9E75]" title="Backend connesso" />
        </div>
        <button className="btn-secondary mt-3 w-full" onClick={onLogout} type="button">
          Logout
        </button>
      </div>
    </aside>
  );
}
