import type { ComponentType, SVGProps } from "react";

import {
  AlertTriangleIcon,
  BellIcon,
  BookOpenIcon,
  CalendarIcon,
  CheckIcon,
  DocumentIcon,
  EyeIcon,
  FolderIcon,
  GridIcon,
  LockIcon,
  RefreshIcon,
  SearchIcon,
  ServerIcon,
  ShieldIcon,
  TruckIcon,
  UserIcon,
  UsersIcon,
} from "@/components/ui/icons";
import { hasUserModuleAccess } from "@/lib/module-access";
import type { CurrentUser } from "@/types/api";

type IconComponent = ComponentType<SVGProps<SVGSVGElement>>;

export type CurrentModuleKey =
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

export type NavigationItem = {
  href: string;
  label: string;
  icon: IconComponent;
  aliases?: string[];
  badge?: number;
  badgeVariant?: "danger" | "warning";
  match?: "exact" | "prefix";
  disabled?: boolean;
  inactiveWhenHash?: string;
};

export type NavigationSection = {
  label: string;
  items: NavigationItem[];
};

export type PlatformModule = {
  href: string;
  label: string;
  icon: IconComponent;
  aliases?: string[];
  isVisible?: (currentUser: CurrentUser) => boolean;
};

type ModuleNavigationOptions = {
  currentModuleKey: CurrentModuleKey;
  reviewBadge?: number;
  userBadge?: number;
  grantedSectionKeys?: string[];
  currentUserRole?: string;
};

const currentModuleLabels: Record<CurrentModuleKey, string> = {
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

const platformModules: PlatformModule[] = [
  { href: "/me", label: "La mia attività", icon: UserIcon },
  {
    href: "/nas-control",
    label: "NAS Control",
    icon: LockIcon,
    isVisible: (currentUser) => hasUserModuleAccess(currentUser, "accessi"),
  },
  {
    href: "/network",
    label: "Rete",
    icon: ServerIcon,
    isVisible: (currentUser) => hasUserModuleAccess(currentUser, "rete"),
  },
  {
    href: "/inventory",
    label: "Inventario",
    icon: SearchIcon,
    isVisible: (currentUser) => hasUserModuleAccess(currentUser, "inventario"),
  },
  {
    href: "/gis/catalogo",
    aliases: ["/gis"],
    label: "GIS Platform",
    icon: GridIcon,
    isVisible: (currentUser) => hasUserModuleAccess(currentUser, "gis"),
  },
  {
    href: "/catasto",
    label: "Catasto",
    icon: GridIcon,
    isVisible: (currentUser) => hasUserModuleAccess(currentUser, "catasto"),
  },
  {
    href: "/elaborazioni",
    label: "Elaborazioni",
    icon: RefreshIcon,
    isVisible: (currentUser) => currentUser.role === "super_admin",
  },
  {
    href: "/utenze",
    label: "Utenze",
    icon: UserIcon,
    isVisible: (currentUser) => hasUserModuleAccess(currentUser, "utenze"),
  },
  {
    href: "/operazioni",
    label: "Operazioni",
    icon: TruckIcon,
    isVisible: (currentUser) => hasUserModuleAccess(currentUser, "operazioni"),
  },
  {
    href: "/riordino",
    label: "Riordino",
    icon: DocumentIcon,
    isVisible: (currentUser) => hasUserModuleAccess(currentUser, "riordino"),
  },
  {
    href: "/ruolo",
    label: "Ruolo",
    icon: CalendarIcon,
    isVisible: (currentUser) => hasUserModuleAccess(currentUser, "ruolo"),
  },
  {
    href: "/presenze",
    label: "Presenze",
    icon: CalendarIcon,
    isVisible: (currentUser) => hasUserModuleAccess(currentUser, "presenze"),
  },
  {
    href: "/organigramma",
    label: "Organigramma",
    icon: UsersIcon,
    isVisible: (currentUser) => hasUserModuleAccess(currentUser, "organigramma"),
  },
  { href: "/wiki", label: "Wiki", icon: BookOpenIcon },
];

function item(
  href: string,
  icon: IconComponent,
  label: string,
  options: Omit<NavigationItem, "href" | "icon" | "label"> = {},
): NavigationItem {
  return { href, icon, label, ...options };
}

export function getCurrentModuleKey(pathname: string): CurrentModuleKey {
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

export function getCurrentModuleLabel(currentModuleKey: CurrentModuleKey): string {
  return currentModuleLabels[currentModuleKey];
}

export function canManageGaiaUsers(currentUser: CurrentUser): boolean {
  return (
    (currentUser.role === "admin" || currentUser.role === "super_admin") &&
    currentUser.enabled_modules.includes("accessi")
  );
}

export function canAccessOperatorDashboard(currentUser: CurrentUser): boolean {
  return (
    currentUser.role === "admin" ||
    currentUser.role === "super_admin" ||
    currentUser.enabled_modules.includes("operazioni")
  );
}

export function getVisiblePlatformModules(currentUser: CurrentUser): PlatformModule[] {
  return platformModules.filter(({ isVisible }) => (isVisible ? isVisible(currentUser) : true));
}

export function getActivePlatformModule(pathname: string, currentUser: CurrentUser): PlatformModule | undefined {
  return getVisiblePlatformModules(currentUser).find(
    ({ href, aliases = [] }) =>
      pathname === href ||
      pathname.startsWith(`${href}/`) ||
      aliases.some((alias) => pathname === alias || pathname.startsWith(`${alias}/`)),
  );
}

export function getAdminNavigationItems(currentUser: CurrentUser): NavigationItem[] {
  if (!canManageGaiaUsers(currentUser)) {
    return [];
  }

  return [
    item("/gaia/users", UserIcon, "Utenti GAIA", { match: "prefix" }),
    item("/gaia/users/operatori-cruscotto", UserIcon, "Cruscotto operatori", { match: "prefix" }),
  ];
}

export function getSidebarState(currentUser: CurrentUser, pathname: string) {
  const currentModuleKey = getCurrentModuleKey(pathname);
  return {
    currentModuleKey,
    currentModuleLabel: getCurrentModuleLabel(currentModuleKey),
    canManageGaiaUsers: canManageGaiaUsers(currentUser),
    canAccessOperatorDashboard: canAccessOperatorDashboard(currentUser),
  };
}

export function getModuleSections({
  currentModuleKey,
  reviewBadge = 0,
  userBadge = 0,
  grantedSectionKeys = [],
  currentUserRole,
}: ModuleNavigationOptions): NavigationSection[] {
  const canAccessUsersSection = grantedSectionKeys.includes("accessi.users");
  const canAccessUtenzeAnprConfig = currentUserRole === "admin" || currentUserRole === "super_admin";
  const canManageCatastoAdmin = currentUserRole === "admin" || currentUserRole === "super_admin";
  const canManageUtenzeAdmin = currentUserRole === "admin" || currentUserRole === "super_admin";
  const canReadOrganigramma = grantedSectionKeys.includes("organigramma.read");
  const canManageOrganigramma = grantedSectionKeys.includes("organigramma.manage");

  switch (currentModuleKey) {
    case "nas_control":
      return [
        {
          label: "Panoramica",
          items: [
            item("/nas-control", GridIcon, "Dashboard"),
            item("/nas-control/sync", RefreshIcon, "Sincronizzazione"),
          ],
        },
        {
          label: "Dominio NAS",
          items: [
            item("/nas-control/users", UserIcon, "Utenti", {
              badge: canAccessUsersSection ? userBadge || undefined : undefined,
              disabled: !canAccessUsersSection,
              match: "prefix",
            }),
            item("/nas-control/groups", UsersIcon, "Gruppi"),
            item("/nas-control/shares", FolderIcon, "Cartelle condivise", { match: "prefix" }),
            item("/nas-control/effective-permissions", LockIcon, "Permessi effettivi"),
          ],
        },
        {
          label: "Validazione",
          items: [
            item("/nas-control/reviews", CheckIcon, "Review NAS", {
              badge: reviewBadge || undefined,
              badgeVariant: "danger",
            }),
            item("/nas-control/reports", DocumentIcon, "Report"),
          ],
        },
      ];
    case "me":
      return [
        {
          label: "Self service",
          items: [
            item("/me", GridIcon, "Panoramica"),
            item("/me/presenze", CalendarIcon, "Presenze"),
            item("/me/operativita", RefreshIcon, "Operatività"),
            item("/me/dotazioni", ServerIcon, "Dotazioni"),
            item("/me/anomalie", AlertTriangleIcon, "Anomalie"),
            item("/me/straordinari", DocumentIcon, "Richiesta straordinari", { match: "prefix" }),
          ],
        },
      ];
    case "catasto":
      return [
        {
          label: "Panoramica",
          items: [item("/catasto", GridIcon, "Dashboard")],
        },
        {
          label: "Catasto operativo",
          items: [
            item("/catasto/gis", GridIcon, "GIS", { match: "prefix" }),
            item("/catasto/distretti", SearchIcon, "Distretti", { match: "prefix" }),
            item("/catasto/indici", BookOpenIcon, "Indici", { match: "prefix" }),
            item("/catasto/colture", EyeIcon, "Colture", { match: "prefix" }),
            item("/catasto/particelle", FolderIcon, "Particelle", { match: "prefix" }),
            item("/catasto/domande-irrigue", DocumentIcon, "Domande irrigue", { match: "prefix" }),
            item("/catasto/letture-contatori", DocumentIcon, "Contatori irrigui", { match: "prefix" }),
            item("/catasto/anomalie", AlertTriangleIcon, "Anomalie", { match: "prefix" }),
            item("/catasto/elaborazioni-massive", UserIcon, "Elaborazione massiva", { match: "prefix" }),
            item("/catasto/import", RefreshIcon, "Import", { match: "prefix" }),
            ...(canManageCatastoAdmin
              ? [item("/catasto/punti-consegna-configurazione", LockIcon, "Config. punti consegna", { match: "prefix" })]
              : []),
            item("/utenze", UserIcon, "Utenze", { match: "prefix" }),
          ],
        },
        {
          label: "Link rapidi",
          items: [item("/catasto/archive", DocumentIcon, "Archivio documenti", { match: "prefix" })],
        },
      ];
    case "gis":
      return [
        {
          label: "Piattaforma",
          items: [item("/gis/catalogo", GridIcon, "Catalogo layer", { match: "prefix" })],
        },
        {
          label: "Workspace dominio",
          items: [item("/catasto/gis", GridIcon, "GIS Catasto", { match: "prefix" })],
        },
      ];
    case "elaborazioni":
      return [
        {
          label: "Panoramica",
          items: [item("/elaborazioni", GridIcon, "Dashboard")],
        },
        {
          label: "Operazioni",
          items: [
            item("/elaborazioni/bonifica", RefreshIcon, "WhiteCompany Sync", { match: "prefix" }),
            item("/elaborazioni/anpr", UserIcon, "ANPR batch", { match: "prefix" }),
            item("/elaborazioni/presenze-sync", RefreshIcon, "Presenze INAZ Sync", { match: "prefix" }),
            item("/elaborazioni/visure", EyeIcon, "Visure Sister", { match: "prefix" }),
            item("/elaborazioni/capacitas", BookOpenIcon, "Moduli Capacitas", { match: "prefix" }),
            item("/elaborazioni/ade-alignment", GridIcon, "Allineamento AdE", { match: "prefix" }),
            item("/elaborazioni/autodoc", TruckIcon, "AUTODOC mezzi", { match: "prefix" }),
            item("/elaborazioni/posta-online", DocumentIcon, "Poste Online", { match: "prefix" }),
            item("/elaborazioni/gaia-mobile-sync", ServerIcon, "GAIA Mobile Sync", { match: "prefix" }),
          ],
        },
        {
          label: "Configurazioni",
          items: [item("/elaborazioni/settings", LockIcon, "Credenziali")],
        },
      ];
    case "network":
      return [
        {
          label: "Panoramica",
          items: [
            item("/network", GridIcon, "Dashboard"),
            item("/network/devices", ServerIcon, "Dispositivi", { match: "prefix" }),
            item("/network/firewalls", ShieldIcon, "Firewall", { match: "prefix" }),
            item("/network/vpn-access", ShieldIcon, "Accessi VPN", { match: "prefix" }),
            item("/network/vpn-bypass", ShieldIcon, "VPN / Proxy Bypass", { match: "prefix" }),
            item("/network/statistics", SearchIcon, "Statistiche", { match: "prefix" }),
            item("/network/floor-plan", FolderIcon, "Planimetria"),
            item("/network/alerts", AlertTriangleIcon, "Alert"),
            item("/network/scans", RefreshIcon, "Scansioni", { match: "prefix" }),
            item("/network/sophos", BellIcon, "Sophos", { match: "prefix" }),
          ],
        },
      ];
    case "gaia":
      return [
        {
          label: "Amministrazione",
          items: [
            item("/gaia/users", UserIcon, "Utenti GAIA", { match: "prefix" }),
            item("/gaia/users/operatori-cruscotto", AlertTriangleIcon, "Cruscotto operatori", { match: "prefix" }),
          ],
        },
      ];
    case "utenze":
      return [
        {
          label: "Panoramica",
          items: [
            item("/utenze", GridIcon, "Dashboard"),
            item("/utenze/import", RefreshIcon, "Import dati", { match: "prefix" }),
            ...(canManageUtenzeAdmin
              ? [item("/utenze/visure-routing-anomalies", AlertTriangleIcon, "Anomalie visure", { match: "prefix" })]
              : []),
            ...(canAccessUtenzeAnprConfig
              ? [item("/anagrafica/anpr-config", LockIcon, "Config. ANPR", { match: "prefix" })]
              : []),
          ],
        },
      ];
    case "operazioni":
      return [
        {
          label: "Panoramica",
          items: [item("/operazioni", GridIcon, "Dashboard")],
        },
        {
          label: "Analisi",
          items: [item("/operazioni/analisi", CalendarIcon, "Analisi operazioni", { match: "prefix" })],
        },
        {
          label: "Gestione",
          items: [
            item("/operazioni/operatori", UsersIcon, "Operatori", { match: "prefix" }),
            item("/operazioni/carte-carburante", DocumentIcon, "Carte carburante", { match: "prefix" }),
            item("/operazioni/mezzi", TruckIcon, "Mezzi", { match: "prefix" }),
            item("/operazioni/attivita", RefreshIcon, "Attività", { match: "prefix" }),
            item("/operazioni/attivita-contatori", DocumentIcon, "Attività contatori", { match: "prefix" }),
            item("/operazioni/segnalazioni/cruscotto", GridIcon, "Cruscotto segnalazioni", { match: "prefix" }),
            item("/operazioni/segnalazioni", AlertTriangleIcon, "Segnalazioni", { match: "prefix" }),
            item("/operazioni/pratiche", DocumentIcon, "Pratiche", { match: "prefix" }),
          ],
        },
      ];
    case "riordino":
      return [
        {
          label: "Panoramica",
          items: [
            item("/riordino", GridIcon, "Dashboard"),
            item("/riordino/pratiche", FolderIcon, "Pratiche", { match: "prefix" }),
          ],
        },
        {
          label: "Gestione",
          items: [item("/riordino/configurazione", LockIcon, "Configurazione", { match: "prefix" })],
        },
      ];
    case "ruolo":
      return [
        {
          label: "Panoramica",
          items: [item("/ruolo", GridIcon, "Dashboard")],
        },
        {
          label: "Dati",
          items: [
            item("/ruolo/avvisi", DocumentIcon, "Avvisi", { match: "prefix" }),
            item("/ruolo/tributi", LockIcon, "Tributi", { match: "prefix" }),
            item("/ruolo/raccomandate", DocumentIcon, "Raccomandate", { match: "prefix" }),
            item("/ruolo/particelle", FolderIcon, "Particelle", { match: "prefix" }),
            item("/ruolo/calcolo-gaia", SearchIcon, "Calcolo ruolo", { match: "prefix" }),
            item("/ruolo/stats", SearchIcon, "Statistiche", { match: "prefix" }),
            item("/ruolo/controlli-capacitas", AlertTriangleIcon, "Audit Capacitas", { match: "prefix" }),
          ],
        },
        {
          label: "Gestione",
          items: [item("/ruolo/import", RefreshIcon, "Storico workflow", { match: "prefix" })],
        },
      ];
    case "presenze":
      return [
        {
          label: "Panoramica",
          items: [item("/presenze", GridIcon, "Dashboard")],
        },
        {
          label: "Gestione",
          items: [
            item("/presenze/giornaliere", CalendarIcon, "Giornaliere", { match: "prefix" }),
            item("/presenze/squadre", UsersIcon, "Squadre", { match: "prefix" }),
            item("/presenze/collaboratori", UsersIcon, "Collaboratori", { match: "prefix" }),
            item("/presenze/organigramma", UsersIcon, "Organigramma", { match: "prefix" }),
            item("/presenze/assegnazione-territoriale", FolderIcon, "Assegnazione territoriale", { match: "prefix" }),
            item("/presenze/anomalie", AlertTriangleIcon, "Anomalie", { match: "prefix" }),
            item("/presenze/regole", DocumentIcon, "Regole", { match: "prefix" }),
            item("/presenze/export", DocumentIcon, "Export", { match: "prefix" }),
            item("/presenze/festivita", CalendarIcon, "Festivita", { match: "prefix" }),
            item("/presenze/recuperi", CheckIcon, "Recuperi", { match: "prefix" }),
            item("/presenze/banca-ore", DocumentIcon, "Banca ore", { match: "prefix" }),
            item("/presenze/configurazione", LockIcon, "Configurazione", { match: "prefix" }),
            item("/presenze/settings", DocumentIcon, "Settings", { match: "prefix" }),
          ],
        },
      ];
    case "organigramma":
      return [
        {
          label: "Organigramma",
          items: [
            item("/organigramma", UsersIcon, "Albero & dettaglio", { disabled: !canReadOrganigramma }),
            item("/organigramma#chi-vede-chi", SearchIcon, "Chi vede chi", { disabled: !canReadOrganigramma }),
          ],
        },
        ...(canManageOrganigramma
          ? [
              {
                label: "Gestione",
                items: [item("/organigramma#override", ShieldIcon, "Eccezioni visibilità")],
              },
            ]
          : []),
      ];
    case "wiki":
      return [
        {
          label: "Panoramica",
          items: [
            item("/wiki", DocumentIcon, "Wiki"),
            item("/wiki/support", AlertTriangleIcon, "Supporto", { match: "prefix" }),
            item("/wiki/conversations", FolderIcon, "Conversazioni", { match: "prefix" }),
            item("/wiki/conversations/analytics", CalendarIcon, "Analytics conversazioni", { match: "prefix" }),
            item("/wiki/conversations/settings", DocumentIcon, "Settings conversazioni", { match: "prefix" }),
          ],
        },
        {
          label: "Governance",
          items: [
            item("/wiki/support/inbox", AlertTriangleIcon, "Inbox supporto", { match: "prefix" }),
            item("/wiki/support/analytics", CalendarIcon, "Analytics supporto", { match: "prefix" }),
            item("/wiki/requests", BellIcon, "Richieste", { match: "prefix" }),
            item("/wiki/audit", SearchIcon, "Audit tool call", { match: "prefix" }),
            item("/wiki/telemetry", GridIcon, "Telemetria", { match: "prefix" }),
          ],
        },
      ];
    case "inventory":
    default:
      return [
        {
          label: "Panoramica",
          items: [item("/inventory", SearchIcon, "Dashboard")],
        },
      ];
  }
}
