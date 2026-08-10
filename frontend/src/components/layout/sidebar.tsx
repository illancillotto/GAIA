"use client";

import { useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/cn";
import type { CurrentUser } from "@/types/api";
import { Avatar } from "@/components/ui/avatar";
import { ModuleSidebar } from "@/components/layout/module-sidebar";
import { PlatformSidebar } from "@/components/layout/platform-sidebar";
import { CloseIcon, UserIcon } from "@/components/ui/icons";

type CurrentModuleKey =
  | "nas_control"
  | "me"
  | "network"
  | "inventory"
  | "gis"
  | "catasto"
  | "elaborazioni"
  | "utenze"
  | "gaia"
  | "operazioni"
  | "riordino"
  | "ruolo"
  | "presenze"
  | "organigramma"
  | "wiki";

type SidebarProps = {
  currentUser: CurrentUser;
  onLogout: () => void;
  reviewBadge?: number;
  userBadge?: number;
  grantedSectionKeys?: string[];
};

type MobileSidebarDrawerProps = SidebarProps & {
  isOpen: boolean;
  onClose: () => void;
};

type SidebarContentProps = SidebarProps & {
  currentModuleKey: CurrentModuleKey;
  currentModuleLabel: string;
  canManageGaiaUsers: boolean;
};

function getCurrentModuleKey(pathname: string): CurrentModuleKey {
  if (pathname.startsWith("/gaia/users")) return "gaia";
  if (pathname.startsWith("/me")) return "me";
  if (pathname.startsWith("/nas-control")) return "nas_control";
  if (pathname.startsWith("/elaborazioni")) return "elaborazioni";
  if (pathname.startsWith("/gis")) return "gis";
  if (pathname.startsWith("/catasto")) return "catasto";
  if (pathname.startsWith("/utenze") || pathname.startsWith("/anagrafica")) return "utenze";
  if (pathname.startsWith("/network")) return "network";
  if (pathname.startsWith("/inventory")) return "inventory";
  if (pathname.startsWith("/operazioni")) return "operazioni";
  if (pathname.startsWith("/riordino")) return "riordino";
  if (pathname.startsWith("/ruolo")) return "ruolo";
  if (pathname.startsWith("/presenze")) return "presenze";
  if (pathname.startsWith("/organigramma")) return "organigramma";
  if (pathname.startsWith("/wiki")) return "wiki";
  return "nas_control";
}

function getCurrentModuleLabel(currentModuleKey: CurrentModuleKey): string {
  const labels: Record<CurrentModuleKey, string> = {
    gaia: "Utenti GAIA",
    me: "La mia attività",
    nas_control: "NAS Control",
    elaborazioni: "Elaborazioni",
    gis: "GIS Platform",
    catasto: "Catasto",
    utenze: "Utenze",
    network: "Rete",
    inventory: "Inventario",
    operazioni: "Operazioni",
    riordino: "Riordino",
    ruolo: "Ruolo",
    presenze: "Presenze",
    organigramma: "Organigramma",
    wiki: "Wiki",
  };
  return labels[currentModuleKey];
}

function getSidebarState(currentUser: CurrentUser, pathname: string) {
  const currentModuleKey = getCurrentModuleKey(pathname);
  const currentModuleLabel = getCurrentModuleLabel(currentModuleKey);
  const canManageGaiaUsers =
    (currentUser.role === "admin" || currentUser.role === "super_admin") &&
    currentUser.enabled_modules.includes("accessi");
  return { currentModuleKey, currentModuleLabel, canManageGaiaUsers };
}

export function Sidebar({
  currentUser,
  onLogout,
  reviewBadge = 0,
  userBadge = 0,
  grantedSectionKeys = [],
}: SidebarProps) {
  const pathname = usePathname();
  const sidebarState = getSidebarState(currentUser, pathname);

  return (
    <aside className="sticky top-0 hidden h-screen w-[220px] shrink-0 flex-col border-r border-gray-100 bg-white md:flex">
      <SidebarContent
        currentUser={currentUser}
        onLogout={onLogout}
        reviewBadge={reviewBadge}
        userBadge={userBadge}
        grantedSectionKeys={grantedSectionKeys}
        {...sidebarState}
      />
    </aside>
  );
}

export function MobileSidebarDrawer({
  currentUser,
  onLogout,
  reviewBadge = 0,
  userBadge = 0,
  grantedSectionKeys = [],
  isOpen,
  onClose,
}: MobileSidebarDrawerProps) {
  const pathname = usePathname();
  const sidebarState = getSidebarState(currentUser, pathname);

  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  useEffect(() => {
    onClose();
  }, [pathname, onClose]);

  if (!isOpen) return null;

  return (
    <>
      <button
        type="button"
        aria-label="Chiudi navigazione"
        className="fixed inset-0 z-40 bg-gray-900/30 md:hidden"
        onClick={onClose}
      />
      <aside className="fixed inset-y-0 left-0 z-50 flex w-[min(86vw,280px)] flex-col border-r border-gray-100 bg-white shadow-xl md:hidden">
        <div className="flex items-center justify-between border-b border-gray-100 px-4 py-3">
          <span className="text-sm font-medium text-gray-800">Navigazione</span>
          <button
            type="button"
            aria-label="Chiudi navigazione"
            className="rounded-lg border border-gray-100 p-2 text-gray-500 transition hover:bg-gray-50 hover:text-gray-800"
            onClick={onClose}
          >
            <CloseIcon className="h-4 w-4" />
          </button>
        </div>
        <SidebarContent
          currentUser={currentUser}
          onLogout={onLogout}
          reviewBadge={reviewBadge}
          userBadge={userBadge}
          grantedSectionKeys={grantedSectionKeys}
          {...sidebarState}
        />
      </aside>
    </>
  );
}

function SidebarContent({
  currentUser,
  onLogout,
  reviewBadge = 0,
  userBadge = 0,
  grantedSectionKeys = [],
  currentModuleKey,
  currentModuleLabel,
  canManageGaiaUsers,
}: SidebarContentProps) {
  const pathname = usePathname();

  return (
    <>
      <div className="flex-1 overflow-y-auto">
        <PlatformSidebar currentModuleLabel={currentModuleLabel} currentUser={currentUser} />
        <ModuleSidebar
          currentModuleKey={currentModuleKey}
          reviewBadge={reviewBadge}
          userBadge={userBadge}
          grantedSectionKeys={grantedSectionKeys}
          currentUserRole={currentUser.role}
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
            <Link
              href="/gaia/users/operatori-cruscotto"
              className={cn(
                "mt-1 flex items-center gap-2 rounded-lg px-2 py-2 text-sm transition-colors",
                pathname === "/gaia/users/operatori-cruscotto" || pathname.startsWith("/gaia/users/operatori-cruscotto/")
                  ? "bg-[#EAF3E8] font-medium text-[#1D4E35]"
                  : "text-gray-500 hover:bg-gray-50 hover:text-gray-800",
              )}
            >
              <UserIcon className="h-4 w-4 shrink-0" />
              <span className="flex-1">Cruscotto operatori</span>
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
    </>
  );
}
