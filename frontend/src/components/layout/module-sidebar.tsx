"use client";

import {
  AlertTriangleIcon,
  CalendarIcon,
  CheckIcon,
  DocumentIcon,
  FolderIcon,
  GridIcon,
  LockIcon,
  RefreshIcon,
  SearchIcon,
  ServerIcon,
  TruckIcon,
  UserIcon,
  UsersIcon,
} from "@/components/ui/icons";
import { NavItem } from "@/components/layout/nav-item";

type ModuleSidebarProps = {
  currentModuleKey:
    | "nas_control"
    | "network"
    | "inventory"
    | "catasto"
    | "elaborazioni"
    | "utenze"
    | "gaia"
    | "operazioni"
    | "riordino"
    | "ruolo";
  reviewBadge?: number;
  userBadge?: number;
  grantedSectionKeys?: string[];
  currentUserRole?: string;
};

export function ModuleSidebar({
  currentModuleKey,
  reviewBadge = 0,
  userBadge = 0,
  grantedSectionKeys = [],
  currentUserRole,
}: ModuleSidebarProps) {
  const canAccessUsersSection = grantedSectionKeys.includes("accessi.users");
  const canAccessUtenzeAnprConfig = currentUserRole === "admin" || currentUserRole === "super_admin";

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

        <p className="px-2 pb-1 pt-4 text-[10px] font-medium uppercase tracking-widest text-gray-400">Catasto operativo</p>
        <NavItem href="/catasto/gis" icon={GridIcon} label="GIS" match="prefix" />
        <NavItem href="/catasto/distretti" icon={SearchIcon} label="Distretti" match="prefix" />
        <NavItem href="/catasto/particelle" icon={FolderIcon} label="Particelle" match="prefix" />
        <NavItem href="/catasto/anomalie" icon={AlertTriangleIcon} label="Anomalie" match="prefix" />
        <NavItem
          href="/catasto/elaborazioni-massive"
          icon={UserIcon}
          label="Elaborazione massiva"
          match="prefix"
        />
        <NavItem href="/catasto/import" icon={RefreshIcon} label="Import" match="prefix" />

        <NavItem href="/utenze" icon={UserIcon} label="Utenze" match="prefix" />

        <p className="px-2 pb-1 pt-4 text-[10px] font-medium uppercase tracking-widest text-gray-400">Link rapidi</p>
        <NavItem href="/catasto/archive" icon={DocumentIcon} label="Archivio documenti" match="prefix" />
      </div>
    );
  }

  if (currentModuleKey === "elaborazioni") {
    return (
      <div className="space-y-0.5 px-2 pb-3">
        <p className="px-2 pb-1 pt-4 text-[10px] font-medium uppercase tracking-widest text-gray-400">Panoramica</p>
        <NavItem href="/elaborazioni" icon={GridIcon} label="Dashboard" />

        <p className="px-2 pb-1 pt-4 text-[10px] font-medium uppercase tracking-widest text-gray-400">Operazioni</p>
        <NavItem href="/elaborazioni/bonifica" icon={RefreshIcon} label="WhiteCompany Sync" match="prefix" />
        <NavItem href="/elaborazioni/anpr" icon={UserIcon} label="ANPR batch" match="prefix" />
        <NavItem href="/elaborazioni/new-single" icon={SearchIcon} label="Visure" match="prefix" />
        <NavItem href="/elaborazioni/capacitas" icon={SearchIcon} label="Capacitas" match="prefix" />
        <NavItem href="/elaborazioni/ade-alignment" icon={GridIcon} label="Allineamento AdE" match="prefix" />

        <p className="px-2 pb-1 pt-4 text-[10px] font-medium uppercase tracking-widest text-gray-400">Configurazioni</p>
        <NavItem href="/elaborazioni/settings" icon={LockIcon} label="Credenziali" />
      </div>
    );
  }

  if (currentModuleKey === "network") {
    return (
      <div className="space-y-0.5 px-2 pb-3">
        <p className="px-2 pb-1 pt-4 text-[10px] font-medium uppercase tracking-widest text-gray-400">Panoramica</p>
        <NavItem href="/network" icon={GridIcon} label="Dashboard" />
        <NavItem href="/network/devices" icon={ServerIcon} label="Dispositivi" match="prefix" />
        <NavItem href="/network/floor-plan" icon={FolderIcon} label="Planimetria" />
        <NavItem href="/network/alerts" icon={AlertTriangleIcon} label="Alert" />
        <NavItem href="/network/scans" icon={RefreshIcon} label="Scansioni" match="prefix" />
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

  if (currentModuleKey === "utenze") {
    return (
      <div className="space-y-0.5 px-2 pb-3">
        <p className="px-2 pb-1 pt-4 text-[10px] font-medium uppercase tracking-widest text-gray-400">Panoramica</p>
        <NavItem href="/utenze" icon={GridIcon} label="Dashboard" />
        <NavItem href="/utenze/import" icon={RefreshIcon} label="Import dati" match="prefix" />
        {canAccessUtenzeAnprConfig ? (
          <NavItem href="/anagrafica/anpr-config" icon={LockIcon} label="Config. ANPR" match="prefix" />
        ) : null}
      </div>
    );
  }

  if (currentModuleKey === "operazioni") {
    return (
      <div className="space-y-0.5 px-2 pb-3">
        <p className="px-2 pb-1 pt-4 text-[10px] font-medium uppercase tracking-widest text-gray-400">Panoramica</p>
        <NavItem href="/operazioni" icon={GridIcon} label="Dashboard" />

        <p className="px-2 pb-1 pt-4 text-[10px] font-medium uppercase tracking-widest text-gray-400">Analisi</p>
        <NavItem href="/operazioni/analisi" icon={CalendarIcon} label="Analisi operazioni" match="prefix" />

        <p className="px-2 pb-1 pt-4 text-[10px] font-medium uppercase tracking-widest text-gray-400">Gestione</p>
        <NavItem href="/operazioni/operatori" icon={UsersIcon} label="Operatori" match="prefix" />
        <NavItem href="/operazioni/carte-carburante" icon={DocumentIcon} label="Carte carburante" match="prefix" />
        <NavItem href="/operazioni/mezzi" icon={TruckIcon} label="Mezzi" match="prefix" />
        <NavItem href="/operazioni/attivita" icon={RefreshIcon} label="Attività" match="prefix" />
        <NavItem href="/operazioni/segnalazioni/cruscotto" icon={GridIcon} label="Cruscotto segnalazioni" match="prefix" />
        <NavItem href="/operazioni/segnalazioni" icon={AlertTriangleIcon} label="Segnalazioni" match="prefix" />
        <NavItem href="/operazioni/pratiche" icon={DocumentIcon} label="Pratiche" match="prefix" />
      </div>
    );
  }

  if (currentModuleKey === "riordino") {
    return (
      <div className="space-y-0.5 px-2 pb-3">
        <p className="px-2 pb-1 pt-4 text-[10px] font-medium uppercase tracking-widest text-gray-400">Panoramica</p>
        <NavItem href="/riordino" icon={GridIcon} label="Dashboard" />
        <NavItem href="/riordino/pratiche" icon={FolderIcon} label="Pratiche" match="prefix" />

        <p className="px-2 pb-1 pt-4 text-[10px] font-medium uppercase tracking-widest text-gray-400">Gestione</p>
        <NavItem href="/riordino/configurazione" icon={LockIcon} label="Configurazione" match="prefix" />
      </div>
    );
  }

  if (currentModuleKey === "ruolo") {
    return (
      <div className="space-y-0.5 px-2 pb-3">
        <p className="px-2 pb-1 pt-4 text-[10px] font-medium uppercase tracking-widest text-gray-400">Panoramica</p>
        <NavItem href="/ruolo" icon={GridIcon} label="Dashboard" />

        <p className="px-2 pb-1 pt-4 text-[10px] font-medium uppercase tracking-widest text-gray-400">Dati</p>
        <NavItem href="/ruolo/avvisi" icon={DocumentIcon} label="Avvisi" match="prefix" />
        <NavItem href="/ruolo/stats" icon={SearchIcon} label="Statistiche" match="prefix" />

        <p className="px-2 pb-1 pt-4 text-[10px] font-medium uppercase tracking-widest text-gray-400">Gestione</p>
        <NavItem href="/ruolo/import" icon={RefreshIcon} label="Import Ruolo" match="prefix" />
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
