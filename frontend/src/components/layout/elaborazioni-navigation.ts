import {
  BookOpenIcon,
  DocumentIcon,
  EyeIcon,
  GridIcon,
  LockIcon,
  RefreshIcon,
  ServerIcon,
  TruckIcon,
  UserIcon,
} from "@/components/ui/icons";
import type { NavigationSection } from "./navigation";

export const elaborazioniNavigationSections: NavigationSection[] = [
  { label: "Panoramica", items: [{ href: "/elaborazioni", icon: GridIcon, label: "Dashboard" }] },
  { label: "Operazioni", items: [
    { href: "/elaborazioni/bonifica", icon: RefreshIcon, label: "WhiteCompany Sync", match: "prefix" },
    { href: "/elaborazioni/anpr", icon: UserIcon, label: "ANPR batch", match: "prefix" },
    { href: "/elaborazioni/presenze-sync", icon: RefreshIcon, label: "Presenze INAZ Sync", match: "prefix" },
    { href: "/elaborazioni/sister", icon: EyeIcon, label: "SISTER / Visure", match: "prefix" },
    { href: "/elaborazioni/capacitas", icon: BookOpenIcon, label: "Moduli Capacitas", match: "prefix" },
    { href: "/elaborazioni/ade-alignment", icon: GridIcon, label: "Allineamento AdE", match: "prefix" },
    { href: "/elaborazioni/autodoc", icon: TruckIcon, label: "AUTODOC mezzi", match: "prefix" },
    { href: "/elaborazioni/posta-online", icon: DocumentIcon, label: "Poste Online", match: "prefix" },
    { href: "/elaborazioni/step", icon: DocumentIcon, label: "STEP riscossione", match: "prefix" },
    { href: "/elaborazioni/gaia-mobile-sync", icon: ServerIcon, label: "GAIA Mobile Sync", match: "prefix" },
  ] },
  { label: "Configurazioni", items: [{ href: "/elaborazioni/settings", icon: LockIcon, label: "Credenziali" }] },
];
