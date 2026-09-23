import {
  AlertTriangleIcon,
  BellIcon,
  CalendarIcon,
  CheckIcon,
  DocumentIcon,
  FolderIcon,
  GridIcon,
  LockIcon,
  UsersIcon,
} from "@/components/ui/icons";

import type { NavigationSection } from "./navigation";

export const presenzeNavigationSections: NavigationSection[] = [
  { label: "Panoramica", items: [{ href: "/presenze", icon: GridIcon, label: "Dashboard" }] },
  {
    label: "Gestione",
    items: [
      { href: "/presenze/giornaliera-individuale", icon: CalendarIcon, label: "Giornaliera individuale", match: "prefix" },
      { href: "/presenze/giornaliere", icon: CalendarIcon, label: "Giornaliere", match: "prefix" },
      { href: "/presenze/squadre", icon: UsersIcon, label: "Squadre", match: "prefix" },
      { href: "/presenze/collaboratori", icon: UsersIcon, label: "Collaboratori", match: "prefix" },
      { href: "/presenze/organigramma", icon: UsersIcon, label: "Organigramma", match: "prefix" },
      { href: "/presenze/assegnazione-territoriale", icon: FolderIcon, label: "Assegnazione territoriale", match: "prefix" },
      { href: "/presenze/anomalie", icon: AlertTriangleIcon, label: "Anomalie", match: "prefix" },
      { href: "/presenze/regole", icon: DocumentIcon, label: "Regole", match: "prefix" },
      { href: "/presenze/export", icon: DocumentIcon, label: "Export", match: "prefix" },
      { href: "/presenze/festivita", icon: CalendarIcon, label: "Festivita", match: "prefix" },
      { href: "/presenze/recuperi", icon: CheckIcon, label: "Recuperi", match: "prefix" },
      { href: "/presenze/banca-ore", icon: DocumentIcon, label: "Banca ore", match: "prefix" },
      { href: "/presenze/configurazione", icon: LockIcon, label: "Configurazione", match: "prefix" },
      { href: "/presenze/whatsapp", icon: BellIcon, label: "Promemoria WhatsApp", match: "prefix" },
      { href: "/presenze/settings", icon: DocumentIcon, label: "Settings", match: "prefix" },
    ],
  },
];
