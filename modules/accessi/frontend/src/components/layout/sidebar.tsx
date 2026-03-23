"use client";

import Link from "next/link";

import type { CurrentUser } from "@/types/api";
import { Avatar } from "@/components/ui/avatar";
import { CheckIcon, DocumentIcon, FolderIcon, GridIcon, LockIcon, RefreshIcon, ServerIcon, UserIcon, UsersIcon } from "@/components/ui/icons";
import { NavItem } from "@/components/layout/nav-item";

type SidebarProps = {
  currentUser: CurrentUser;
  onLogout: () => void;
  reviewBadge?: number;
  userBadge?: number;
};

export function Sidebar({ currentUser, onLogout, reviewBadge = 0, userBadge = 0 }: SidebarProps) {
  return (
    <aside className="sticky top-0 flex h-screen w-[220px] shrink-0 flex-col border-r border-gray-100 bg-white">
      <div className="border-b border-gray-100 px-4 py-5">
        <div className="mb-3 flex w-fit items-center gap-2 rounded-lg bg-[#1D4E35] px-3 py-2 text-white">
          <ServerIcon className="h-4 w-4" />
          <span className="text-xs font-medium tracking-wide">NAS AUDIT</span>
        </div>
        <p className="text-sm font-medium leading-tight text-gray-800">Consorzio di Bonifica</p>
        <p className="text-xs text-gray-400">Oristanese — Synology NAS</p>
      </div>

      <nav className="flex-1 space-y-0.5 overflow-y-auto px-2 py-3">
        <div className="mx-2 mb-3 border-b border-gray-100 pb-3">
          <Link
            href="/"
            className="block rounded-lg px-2.5 py-2 text-xs font-medium tracking-wide text-gray-500 transition hover:bg-gray-50 hover:text-gray-800"
          >
            ← GAIA Home
          </Link>
        </div>

        <p className="px-2 pb-1 pt-4 text-[10px] font-medium uppercase tracking-widest text-gray-400">Panoramica</p>
        <NavItem href="/accessi" icon={GridIcon} label="Dashboard" />
        <NavItem href="/sync" icon={RefreshIcon} label="Sincronizzazione" />

        <p className="px-2 pb-1 pt-4 text-[10px] font-medium uppercase tracking-widest text-gray-400">Accessi</p>
        <NavItem href="/users" icon={UserIcon} label="Utenti" badge={userBadge || undefined} />
        <NavItem href="/groups" icon={UsersIcon} label="Gruppi" />
        <NavItem href="/shares" icon={FolderIcon} label="Cartelle condivise" />
        <NavItem href="/effective-permissions" icon={LockIcon} label="Permessi effettivi" />

        <p className="px-2 pb-1 pt-4 text-[10px] font-medium uppercase tracking-widest text-gray-400">Validazione</p>
        <NavItem href="/reviews" icon={CheckIcon} label="Review accessi" badge={reviewBadge || undefined} badgeVariant="danger" />
        <NavItem href="/reports" icon={DocumentIcon} label="Report" />
      </nav>

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
