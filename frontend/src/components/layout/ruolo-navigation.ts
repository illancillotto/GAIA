import { AlertTriangleIcon, DocumentIcon, FolderIcon, GridIcon, LockIcon, RefreshIcon, SearchIcon } from "@/components/ui/icons";
import type { NavigationSection } from "./navigation";

export const ruoloNavigationSections: NavigationSection[] = [
  { label: "Panoramica", items: [{ href: "/ruolo", icon: GridIcon, label: "Dashboard" }] },
  { label: "Dati", items: [
    { href: "/ruolo/avvisi", icon: DocumentIcon, label: "Avvisi", match: "prefix" },
    { href: "/ruolo/tributi", icon: LockIcon, label: "Tributi", match: "prefix" },
    { href: "/ruolo/tributi/registro-avvisi", icon: DocumentIcon, label: "Registro avvisi", match: "prefix" },
    { href: "/ruolo/raccomandate", icon: DocumentIcon, label: "Raccomandate", match: "prefix" },
    { href: "/ruolo/particelle", icon: FolderIcon, label: "Particelle", match: "prefix" },
    { href: "/ruolo/calcolo-gaia", icon: SearchIcon, label: "Calcolo ruolo", match: "prefix" },
    { href: "/ruolo/stats", icon: SearchIcon, label: "Statistiche", match: "prefix" },
    { href: "/ruolo/controlli-capacitas", icon: AlertTriangleIcon, label: "Audit Capacitas", match: "prefix" },
  ] },
  { label: "Gestione", items: [{ href: "/ruolo/import", icon: RefreshIcon, label: "Storico workflow", match: "prefix" }] },
];
