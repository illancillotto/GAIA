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
  currentModuleKey: "accessi" | "network" | "inventory" | "catasto";
  reviewBadge?: number;
  userBadge?: number;
};

export function ModuleSidebar({
  currentModuleKey,
  reviewBadge = 0,
  userBadge = 0,
}: ModuleSidebarProps) {
  if (currentModuleKey === "accessi") {
    return (
      <div className="space-y-0.5 px-2 pb-3">
        <p className="px-2 pb-1 pt-4 text-[10px] font-medium uppercase tracking-widest text-gray-400">Panoramica</p>
        <NavItem href="/accessi" icon={GridIcon} label="Dashboard" />
        <NavItem href="/accessi/sync" icon={RefreshIcon} label="Sincronizzazione" />

        <p className="px-2 pb-1 pt-4 text-[10px] font-medium uppercase tracking-widest text-gray-400">Accessi</p>
        <NavItem href="/accessi/users" icon={UserIcon} label="Utenti" badge={userBadge || undefined} match="prefix" />
        <NavItem href="/accessi/groups" icon={UsersIcon} label="Gruppi" />
        <NavItem href="/accessi/shares" icon={FolderIcon} label="Cartelle condivise" match="prefix" />
        <NavItem href="/accessi/effective-permissions" icon={LockIcon} label="Permessi effettivi" />

        <p className="px-2 pb-1 pt-4 text-[10px] font-medium uppercase tracking-widest text-gray-400">Validazione</p>
        <NavItem
          href="/accessi/reviews"
          icon={CheckIcon}
          label="Review accessi"
          badge={reviewBadge || undefined}
          badgeVariant="danger"
        />
        <NavItem href="/accessi/reports" icon={DocumentIcon} label="Report" />
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

  return (
    <div className="space-y-0.5 px-2 pb-3">
      <p className="px-2 pb-1 pt-4 text-[10px] font-medium uppercase tracking-widest text-gray-400">Panoramica</p>
      <NavItem href="/inventory" icon={SearchIcon} label="Dashboard" />
    </div>
  );
}
