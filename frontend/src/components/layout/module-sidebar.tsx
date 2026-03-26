"use client";

import {
  CheckIcon,
  DocumentIcon,
  FolderIcon,
  GridIcon,
  LockIcon,
  RefreshIcon,
  SearchIcon,
  UserIcon,
  UsersIcon,
} from "@/components/ui/icons";
import { NavItem } from "@/components/layout/nav-item";

type ModuleSidebarProps = {
  currentModuleKey: "nas_control" | "network" | "inventory" | "catasto" | "gaia";
  reviewBadge?: number;
  userBadge?: number;
  grantedSectionKeys?: string[];
};

export function ModuleSidebar({
  currentModuleKey,
  reviewBadge = 0,
  userBadge = 0,
  grantedSectionKeys = [],
}: ModuleSidebarProps) {
  const canAccessUsersSection = grantedSectionKeys.includes("accessi.users");

  if (currentModuleKey === "nas_control") {
    return (
      <div className="space-y-0.5 px-2 pb-3">
        <p className="px-2 pb-1 pt-4 text-[10px] font-medium uppercase tracking-widest text-gray-400">Panoramica</p>
        <NavItem href="/nas-control" icon={GridIcon} label="Dashboard" />
        <NavItem href="/nas-control/sync" icon={RefreshIcon} label="Sincronizzazione" />

        <p className="px-2 pb-1 pt-4 text-[10px] font-medium uppercase tracking-widest text-gray-400">Dominio NAS</p>
        <NavItem
          href="/nas-control/users"
          icon={UserIcon}
          label="Utenti"
          badge={canAccessUsersSection ? userBadge || undefined : undefined}
          match="prefix"
          disabled={!canAccessUsersSection}
        />
        <NavItem href="/nas-control/groups" icon={UsersIcon} label="Gruppi" />
        <NavItem href="/nas-control/shares" icon={FolderIcon} label="Cartelle condivise" match="prefix" />
        <NavItem href="/nas-control/effective-permissions" icon={LockIcon} label="Permessi effettivi" />

        <p className="px-2 pb-1 pt-4 text-[10px] font-medium uppercase tracking-widest text-gray-400">Validazione</p>
        <NavItem
          href="/nas-control/reviews"
          icon={CheckIcon}
          label="Review NAS"
          badge={reviewBadge || undefined}
          badgeVariant="danger"
        />
        <NavItem href="/nas-control/reports" icon={DocumentIcon} label="Report" />
      </div>
    );
  }

  if (currentModuleKey === "catasto") {
    return (
      <div className="space-y-0.5 px-2 pb-3">
        <p className="px-2 pb-1 pt-4 text-[10px] font-medium uppercase tracking-widest text-gray-400">Panoramica</p>
        <NavItem href="/catasto" icon={GridIcon} label="Dashboard" />
        <NavItem href="/catasto/new-single" icon={UserIcon} label="Visura singola" />
        <NavItem href="/catasto/new-batch" icon={RefreshIcon} label="Nuovo batch" />

        <p className="px-2 pb-1 pt-4 text-[10px] font-medium uppercase tracking-widest text-gray-400">Operazioni</p>
        <NavItem href="/catasto/batches" icon={DocumentIcon} label="Storico batch" match="prefix" />
        <NavItem href="/catasto/documents" icon={FolderIcon} label="Archivio documenti" match="prefix" />
        <NavItem href="/catasto/settings" icon={LockIcon} label="Credenziali SISTER" />
      </div>
    );
  }

  if (currentModuleKey === "network") {
    return (
      <div className="space-y-0.5 px-2 pb-3">
        <p className="px-2 pb-1 pt-4 text-[10px] font-medium uppercase tracking-widest text-gray-400">Panoramica</p>
        <NavItem href="/network" icon={GridIcon} label="Dashboard" />
      </div>
    );
  }

  if (currentModuleKey === "gaia") {
    return (
      <div className="space-y-0.5 px-2 pb-3">
        <p className="px-2 pb-1 pt-4 text-[10px] font-medium uppercase tracking-widest text-gray-400">Amministrazione</p>
        <NavItem href="/gaia/users" icon={UserIcon} label="Utenti GAIA" match="prefix" />
      </div>
    );
  }

  return (
    <div className="space-y-0.5 px-2 pb-3">
      <p className="px-2 pb-1 pt-4 text-[10px] font-medium uppercase tracking-widest text-gray-400">Panoramica</p>
      <NavItem href="/inventory" icon={SearchIcon} label="Dashboard" />
    </div>
  );
}
