"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import {
  getCatastoDocuments,
  getCurrentUser,
  getDashboardSummary,
  getMyPermissions,
  getNetworkDashboard,
  getUtenzeStats,
  isAuthError,
} from "@/lib/api";
import { clearStoredAccessToken, getStoredAccessToken } from "@/lib/auth";
import { cn } from "@/lib/cn";
import { hasSectionAccess } from "@/lib/section-access";
import type {
  AnagraficaStats,
  CatastoDocument,
  CurrentUser,
  DashboardSummary,
  NetworkDashboardSummary,
} from "@/types/api";

type ModuleStatus = "active" | "warming" | "coming";
type ModuleId = "accessi" | "rete" | "inventario" | "catasto" | "elaborazioni" | "utenze" | "operazioni" | "riordino" | "ruolo";

type HomeModule = {
  id: ModuleId;
  title: string;
  eyebrow: string;
  description: string;
  href: string;
  status: ModuleStatus;
  statusLabel: string;
  icon: string;
  enabledKeys: string[];
};

type SearchRoute = {
  label: string;
  href: string;
  moduleKey?: string;
  requiredSection?: string;
  requiredRoles?: string[];
  keywords?: string[];
};

const menuSearchRoutes: SearchRoute[] = [
  // NAS / Accessi
  { label: "NAS Control · Dashboard", href: "/nas-control", moduleKey: "accessi", keywords: ["nas", "accessi"] },
  { label: "NAS Control · Sincronizzazione", href: "/nas-control/sync", moduleKey: "accessi", keywords: ["sync", "sincronizzazione"] },
  { label: "NAS Control · Utenti", href: "/nas-control/users", moduleKey: "accessi", requiredSection: "accessi.users", keywords: ["utenti", "users"] },
  { label: "NAS Control · Gruppi", href: "/nas-control/groups", moduleKey: "accessi", keywords: ["gruppi", "groups"] },
  { label: "NAS Control · Cartelle condivise", href: "/nas-control/shares", moduleKey: "accessi", keywords: ["shares", "cartelle"] },
  { label: "NAS Control · Permessi effettivi", href: "/nas-control/effective-permissions", moduleKey: "accessi", keywords: ["permessi", "effective"] },
  { label: "NAS Control · Review NAS", href: "/nas-control/reviews", moduleKey: "accessi", keywords: ["review", "validazione"] },
  { label: "NAS Control · Report", href: "/nas-control/reports", moduleKey: "accessi", keywords: ["report"] },

  // Elaborazioni
  { label: "Elaborazioni · Dashboard", href: "/elaborazioni", moduleKey: "elaborazioni", keywords: ["batch"] },
  { label: "Elaborazioni · WhiteCompany Sync", href: "/elaborazioni/bonifica", moduleKey: "elaborazioni", keywords: ["white", "bonifica", "sync"] },
  { label: "Elaborazioni · Visure", href: "/elaborazioni/new-single", moduleKey: "elaborazioni", keywords: ["visure"] },
  { label: "Elaborazioni · Capacitas", href: "/elaborazioni/capacitas", moduleKey: "elaborazioni", keywords: ["capacitas"] },
  { label: "Elaborazioni · Credenziali", href: "/elaborazioni/settings", moduleKey: "elaborazioni", keywords: ["credenziali", "settings"] },

  // Catasto
  { label: "Catasto · Dashboard", href: "/catasto", moduleKey: "catasto" },
  { label: "Catasto · Distretti", href: "/catasto/distretti", moduleKey: "catasto", keywords: ["distretti"] },
  { label: "Catasto · Particelle", href: "/catasto/particelle", moduleKey: "catasto", keywords: ["mappali", "terreni"] },
  { label: "Catasto · Anomalie", href: "/catasto/anomalie", moduleKey: "catasto", keywords: ["errori"] },
  { label: "Catasto · Import", href: "/catasto/import", moduleKey: "catasto", keywords: ["caricamento"] },
  { label: "Catasto · Archivio documenti", href: "/catasto/archive", moduleKey: "catasto", keywords: ["documenti"] },

  // Network (rete)
  { label: "Rete · Dashboard", href: "/network", moduleKey: "rete" },
  { label: "Rete · Dispositivi", href: "/network/devices", moduleKey: "rete", keywords: ["switch", "ap", "devices"] },
  { label: "Rete · Planimetria", href: "/network/floor-plan", moduleKey: "rete", keywords: ["mappa", "planimetria"] },
  { label: "Rete · Alert", href: "/network/alerts", moduleKey: "rete", keywords: ["allarmi"] },
  { label: "Rete · Scansioni", href: "/network/scans", moduleKey: "rete", keywords: ["scan", "scansioni"] },

  // Utenze / Anagrafica
  { label: "Utenze · Dashboard", href: "/utenze", moduleKey: "utenze" },
  { label: "Utenze · Soggetti", href: "/utenze/import#utenze-soggetti", moduleKey: "utenze", keywords: ["anagrafica", "subjects"] },
  { label: "Utenze · Import dati", href: "/utenze/import", moduleKey: "utenze", keywords: ["import"] },

  // Operazioni
  { label: "Operazioni · Dashboard", href: "/operazioni", moduleKey: "operazioni" },
  { label: "Operazioni · Analisi operazioni", href: "/operazioni/analisi", moduleKey: "operazioni", keywords: ["analisi"] },
  { label: "Operazioni · Operatori", href: "/operazioni/operatori", moduleKey: "operazioni" },
  { label: "Operazioni · Carte carburante", href: "/operazioni/carte-carburante", moduleKey: "operazioni", keywords: ["fuel", "carburante"] },
  { label: "Operazioni · Mezzi", href: "/operazioni/mezzi", moduleKey: "operazioni", keywords: ["veicoli", "automezzi"] },
  { label: "Operazioni · Attività", href: "/operazioni/attivita", moduleKey: "operazioni" },
  { label: "Operazioni · Cruscotto segnalazioni", href: "/operazioni/segnalazioni/cruscotto", moduleKey: "operazioni", keywords: ["cruscotto"] },
  { label: "Operazioni · Segnalazioni", href: "/operazioni/segnalazioni", moduleKey: "operazioni" },
  { label: "Operazioni · Pratiche", href: "/operazioni/pratiche", moduleKey: "operazioni" },

  // Riordino
  { label: "Riordino · Dashboard", href: "/riordino", moduleKey: "riordino" },
  { label: "Riordino · Pratiche", href: "/riordino/pratiche", moduleKey: "riordino" },
  { label: "Riordino · Configurazione", href: "/riordino/configurazione", moduleKey: "riordino", keywords: ["settings"] },

  // Ruolo
  { label: "Ruolo · Dashboard", href: "/ruolo", moduleKey: "ruolo" },
  { label: "Ruolo · Avvisi", href: "/ruolo/avvisi", moduleKey: "ruolo" },
  { label: "Ruolo · Statistiche", href: "/ruolo/stats", moduleKey: "ruolo", keywords: ["analytics"] },
  { label: "Ruolo · Import Ruolo", href: "/ruolo/import", moduleKey: "ruolo", keywords: ["import"] },

  // Admin GAIA users (include section check)
  {
    label: "Amministrazione · Utenti GAIA",
    href: "/gaia/users",
    moduleKey: "accessi",
    requiredSection: "accessi.users",
    requiredRoles: ["admin", "super_admin"],
    keywords: ["admin", "utenti", "gaia"],
  },
];

const emptySummary: DashboardSummary = {
  nas_users: 0,
  nas_groups: 0,
  shares: 0,
  reviews: 0,
  snapshots: 0,
  sync_runs: 0,
};

const emptyNetworkSummary: NetworkDashboardSummary = {
  total_devices: 0,
  online_devices: 0,
  offline_devices: 0,
  open_alerts: 0,
  scans_last_24h: 0,
  floor_plans: 0,
  latest_scan_at: null,
};

const emptyUtenzeSummary: AnagraficaStats = {
  total_subjects: 0,
  total_persons: 0,
  total_companies: 0,
  total_unknown: 0,
  total_documents: 0,
  requires_review: 0,
  active_subjects: 0,
  inactive_subjects: 0,
  documents_unclassified: 0,
  deceased_updates_last_24h: 0,
  deceased_updates_current_month: 0,
  deceased_updates_current_year: 0,
  by_letter: {},
};

const allModules: HomeModule[] = [
  {
    id: "catasto",
    title: "GAIA Catasto",
    eyebrow: "Dominio dati",
    description:
      "Distretti, particelle, anomalie, ricerca anagrafica e import Capacitas.",
    href: "/catasto",
    status: "warming",
    statusLabel: "In sviluppo",
    icon: "account_balance",
    enabledKeys: ["catasto"],
  },
  {
    id: "operazioni",
    title: "GAIA Operazioni",
    eyebrow: "Field operations",
    description:
      "Modulo in sviluppo per mezzi, attività, segnalazioni e pratiche operative.",
    href: "/operazioni",
    status: "warming",
    statusLabel: "In sviluppo",
    icon: "local_shipping",
    enabledKeys: ["operazioni"],
  },
  {
    id: "utenze",
    title: "GAIA Utenze",
    eyebrow: "Soggetti e documenti",
    description:
      "Modulo in sviluppo per soggetti, documenti e qualità del dato, con superficie ancora non consolidata.",
    href: "/utenze",
    status: "warming",
    statusLabel: "In sviluppo",
    icon: "badge",
    enabledKeys: ["utenze"],
  },
  {
    id: "ruolo",
    title: "GAIA Ruolo",
    eyebrow: "Ruolo consortile",
    description:
      "Import e consultazione degli avvisi del ruolo consortile (Capacitas). Collegamento soggetti, statistiche per comune e anno tributario.",
    href: "/ruolo",
    status: "warming",
    statusLabel: "In sviluppo",
    icon: "receipt_long",
    enabledKeys: ["ruolo"],
  },
  {
    id: "accessi",
    title: "GAIA NAS Control",
    eyebrow: "Governance accessi",
    description:
      "Monitoraggio avanzato e gestione dei permessi per infrastrutture NAS Synology. Utenti, gruppi, cartelle condivise e workflow di review centralizzato.",
    href: "/nas-control",
    status: "active",
    statusLabel: "Operativo",
    icon: "storage",
    enabledKeys: ["accessi"],
  },
  {
    id: "rete",
    title: "GAIA Rete",
    eyebrow: "Monitoraggio infrastruttura",
    description:
      "Scansione dispositivi, mappa per piano, alert operativi e controllo dello stato rete con visualizzazioni immediate.",
    href: "/network",
    status: "active",
    statusLabel: "Operativo",
    icon: "hub",
    enabledKeys: ["rete"],
  },
  {
    id: "elaborazioni",
    title: "GAIA Elaborazioni",
    eyebrow: "Runtime operativo catasto",
    description:
      "Modulo in sviluppo: perimetro e workflow applicativi sono ancora in consolidamento.",
    href: "/elaborazioni",
    status: "warming",
    statusLabel: "In sviluppo",
    icon: "sync_alt",
    enabledKeys: ["catasto"],
  },
  {
    id: "riordino",
    title: "GAIA Riordino",
    eyebrow: "Workflow riordino catastale",
    description:
      "Modulo in sviluppo per pratiche, workflow, documenti e anomalie del riordino catastale.",
    href: "/riordino",
    status: "warming",
    statusLabel: "In sviluppo",
    icon: "description",
    enabledKeys: ["riordino"],
  },
  {
    id: "inventario",
    title: "GAIA Inventario",
    eyebrow: "Asset fisici",
    description:
      "Area non ancora avviata: non sono presenti workflow o dati operativi utilizzabili.",
    href: "/inventory",
    status: "coming",
    statusLabel: "Non avviato",
    icon: "inventory_2",
    enabledKeys: ["inventario"],
  },
];

function formatNumber(value: number): string {
  return new Intl.NumberFormat("it-IT").format(value);
}

function HomePageSkeleton({ loadError }: { loadError: string | null }) {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-surface text-on-surface font-body">
      <span className="font-headline text-3xl font-bold text-primary mb-6">GAIA</span>
      <p className="text-outline text-sm mb-2">Verifica sessione in corso…</p>
      {loadError ? (
        <p className="text-error text-sm mt-2">{loadError}</p>
      ) : null}
      <Link
        className="mt-6 bg-primary text-on-primary px-6 py-3 rounded font-medium text-sm transition hover:opacity-90"
        href="/login"
      >
        Vai al login
      </Link>
    </div>
  );
}

export default function HomePage() {
  const router = useRouter();
  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null);
  const [summary, setSummary] = useState<DashboardSummary>(emptySummary);
  const [networkSummary, setNetworkSummary] = useState<NetworkDashboardSummary>(emptyNetworkSummary);
  const [utenzeSummary, setUtenzeSummary] = useState<AnagraficaStats>(emptyUtenzeSummary);
  const [catastoDocuments, setCatastoDocuments] = useState<CatastoDocument[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [isCheckingSession, setIsCheckingSession] = useState(true);
  const [grantedSectionKeys, setGrantedSectionKeys] = useState<string[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const searchBoxRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    async function loadHome() {
      const token = getStoredAccessToken();

      if (!token) {
        router.replace("/login");
        return;
      }

      try {
        const [user, dashboardSummary, permissionSummary] = await Promise.all([
          getCurrentUser(token),
          getDashboardSummary(token),
          getMyPermissions(token),
        ]);

        const hasNetwork = user.enabled_modules.includes("rete");
        const hasUtenze = user.enabled_modules.includes("utenze");
        const hasCatasto = user.enabled_modules.includes("catasto");

        const [networkDashboard, utenzeStats, documents] = await Promise.all([
          hasNetwork ? getNetworkDashboard(token) : Promise.resolve(emptyNetworkSummary),
          hasUtenze ? getUtenzeStats(token) : Promise.resolve(emptyUtenzeSummary),
          hasCatasto ? getCatastoDocuments(token) : Promise.resolve([]),
        ]);

        setCurrentUser(user);
        setSummary(dashboardSummary);
        setNetworkSummary(networkDashboard);
        setUtenzeSummary(utenzeStats);
        setCatastoDocuments(documents);
        setGrantedSectionKeys(permissionSummary.granted_keys);
        setLoadError(null);
      } catch (error) {
        setLoadError(error instanceof Error ? error.message : "Errore imprevisto");
        if (isAuthError(error)) {
          clearStoredAccessToken();
          setCurrentUser(null);
          setSummary(emptySummary);
          setNetworkSummary(emptyNetworkSummary);
          setUtenzeSummary(emptyUtenzeSummary);
          setCatastoDocuments([]);
          setGrantedSectionKeys([]);
          router.replace("/login");
        }
      } finally {
        setIsCheckingSession(false);
      }
    }

    void loadHome();
  }, [router]);

  function handleLogout(): void {
    clearStoredAccessToken();
    setCurrentUser(null);
    setSummary(emptySummary);
    setNetworkSummary(emptyNetworkSummary);
    setUtenzeSummary(emptyUtenzeSummary);
    setCatastoDocuments([]);
    setGrantedSectionKeys([]);
    router.replace("/login");
  }

  const searchResults = useMemo(() => {
    const user = currentUser;
    if (!user) return [];
    const query = searchQuery.trim().toLowerCase();
    if (!query) return [];

    const userRole = user.role;
    const enabledModuleSet = new Set(user.enabled_modules);
    const isAdmin = userRole === "admin" || userRole === "super_admin";

    function isRouteAllowed(route: SearchRoute): boolean {
      if (route.requiredRoles && !route.requiredRoles.includes(userRole)) return false;
      if (route.requiredSection && !hasSectionAccess(grantedSectionKeys, route.requiredSection)) return false;
      if (!route.moduleKey) return true;
      if (isAdmin) return true;
      return enabledModuleSet.has(route.moduleKey);
    }

    function scoreRoute(route: SearchRoute): number {
      const haystack = [route.label, ...(route.keywords ?? [])].join(" ").toLowerCase();
      if (haystack === query) return 100;
      if (route.label.toLowerCase().startsWith(query)) return 80;
      if (haystack.includes(query)) return 60;
      return 0;
    }

    return menuSearchRoutes
      .filter(isRouteAllowed)
      .map((route) => ({ route, score: scoreRoute(route) }))
      .filter((item) => item.score > 0)
      .sort((a, b) => b.score - a.score || a.route.label.localeCompare(b.route.label))
      .slice(0, 10)
      .map((item) => item.route);
  }, [currentUser, grantedSectionKeys, searchQuery]);

  useEffect(() => {
    function handleDocumentClick(event: MouseEvent) {
      const target = event.target as Node | null;
      if (!target) return;
      if (searchBoxRef.current && !searchBoxRef.current.contains(target)) {
        setIsSearchOpen(false);
      }
    }
    document.addEventListener("mousedown", handleDocumentClick);
    return () => document.removeEventListener("mousedown", handleDocumentClick);
  }, []);

  if (isCheckingSession || !currentUser) {
    return <HomePageSkeleton loadError={loadError} />;
  }

  const user = currentUser;

  const canManageGaiaUsers =
    (user.role === "admin" || user.role === "super_admin")
    && user.enabled_modules.includes("accessi")
    && hasSectionAccess(grantedSectionKeys, "accessi.users");

  const visibleModules = allModules.filter((mod) => {
    if (mod.status === "coming") return true;
    return mod.enabledKeys.some((key) => user.enabled_modules.includes(key));
  });

  const platformStats = [
    {
      label: "Utenze gestite",
      value: formatNumber(utenzeSummary.total_subjects),
      copy: `${formatNumber(utenzeSummary.active_subjects)} soggetti attivi e ${formatNumber(utenzeSummary.requires_review)} da verificare`,
      icon: "badge",
    },
    {
      label: "Dispositivi connessi",
      value: formatNumber(networkSummary.online_devices),
      copy: `${formatNumber(networkSummary.total_devices)} rilevati, ${formatNumber(networkSummary.offline_devices)} offline`,
      icon: "lan",
    },
    {
      label: "Alert rete aperti",
      value: formatNumber(networkSummary.open_alerts),
      copy: networkSummary.open_alerts === 0 ? "Nessun alert infrastrutturale aperto" : "Dispositivi sconosciuti o assenti da gestire",
      icon: "notifications_active",
    },
  ];

  const operationalStats = [
    {
      label: "Sync runs",
      value: formatNumber(summary.sync_runs),
      copy: "Cicli completati nelle ultime 24 ore",
      icon: "sync",
    },
    {
      label: "Documenti catasto",
      value: formatNumber(catastoDocuments.length),
      copy: "Archivio PDF disponibile per ricerca e download",
      icon: "description",
    },
    {
      label: "Moduli abilitati",
      value: formatNumber(currentUser.enabled_modules.length),
      copy: "Perimetro operativo disponibile nel profilo attuale",
      icon: "apps",
    },
  ];

  const statusBadge: Record<ModuleStatus, string> = {
    active: "bg-primary-fixed text-on-primary-fixed",
    warming: "bg-tertiary-fixed-dim text-on-tertiary-fixed-variant",
    coming: "bg-tertiary-fixed-dim text-on-tertiary-fixed-variant",
  };

  return (
    <div className="min-h-screen bg-surface text-on-surface font-body">
      {/* TopAppBar */}
      <header className="bg-surface fixed top-0 w-full z-50">
        <div className="flex justify-between items-center w-full px-8 py-3 max-w-full">
          <div className="flex items-center gap-12">
            <span className="font-headline text-xl font-bold italic text-primary">GAIA</span>
            <nav className="hidden md:flex gap-8">
              {visibleModules
                .filter((m) => m.status !== "coming")
                .map((mod) => (
                  <Link
                    key={mod.id}
                    href={mod.href}
                    className="font-body font-medium text-outline hover:text-primary transition-colors duration-200"
                  >
                    {mod.title.replace("GAIA ", "")}
                  </Link>
                ))}
            </nav>
          </div>

          <div className="flex items-center gap-4">
            {/* Search (lg+) */}
            <div className="relative hidden lg:block" ref={searchBoxRef}>
              <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-outline text-sm pointer-events-none">
                search
              </span>
              <input
                className="bg-surface-container-high border-none rounded-lg pl-10 pr-4 py-2 text-sm focus:ring-1 focus:ring-primary w-56 transition-all outline-none"
                placeholder="Ricerca globale…"
                type="text"
                value={searchQuery}
                onChange={(event) => {
                  setSearchQuery(event.target.value);
                  setIsSearchOpen(true);
                }}
                onFocus={() => setIsSearchOpen(true)}
                onKeyDown={(event) => {
                  if (event.key === "Escape") {
                    setIsSearchOpen(false);
                  }
                  if (event.key === "Enter" && searchResults[0]) {
                    setIsSearchOpen(false);
                    router.push(searchResults[0].href);
                  }
                }}
              />
              {isSearchOpen && searchQuery.trim() ? (
                <div className="absolute right-0 mt-2 w-[420px] max-w-[80vw] overflow-hidden rounded-xl border border-surface-container bg-white shadow-lg">
                  {searchResults.length === 0 ? (
                    <div className="px-4 py-3 text-sm text-outline">Nessun risultato disponibile per i permessi correnti.</div>
                  ) : (
                    <ul className="max-h-[320px] overflow-auto py-2">
                      {searchResults.map((item) => (
                        <li key={item.href}>
                          <button
                            type="button"
                            className="w-full px-4 py-2 text-left text-sm text-gray-900 hover:bg-surface-container-low"
                            onClick={() => {
                              setIsSearchOpen(false);
                              router.push(item.href);
                            }}
                          >
                            {item.label}
                          </button>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              ) : null}
            </div>

            {/* User + logout */}
            <span className="text-sm font-medium text-on-surface-variant hidden lg:block">
              {currentUser.username}
            </span>
            <button
              type="button"
              onClick={handleLogout}
              className="text-on-surface-variant hover:text-primary transition-colors"
              aria-label="Logout"
            >
              <span className="material-symbols-outlined">logout</span>
            </button>
          </div>
        </div>
        <div className="bg-surface-container h-[1px] w-full" />
      </header>

      {/* Main content */}
      <main className="pt-24 pb-12 px-8 max-w-[90rem] mx-auto min-h-screen">
        {/* Hero */}
        <section className="mb-12">
          <div>
            <h1 className="text-5xl font-headline font-medium text-primary leading-tight mb-3">
              Hub operativo GAIA
            </h1>
            <p className="text-lg font-body text-outline leading-relaxed">
              GAIA concentra oggi i moduli realmente operativi su accessi NAS e rete, mantenendo gli
              altri domini in evoluzione o non ancora avviati nello stesso ingresso applicativo.
            </p>
          </div>
        </section>

        <section className="mb-12">
          <div className="mb-5 flex items-end justify-between gap-4">
            <div>
              <h2 className="text-xl font-headline text-primary">Cruscotto rapido</h2>
              <p className="text-sm text-outline">Stato sintetico della piattaforma e del perimetro utente corrente.</p>
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
            {[...platformStats, ...operationalStats].map((stat) => (
              <div
                key={`quick-${stat.label}`}
                className="bg-surface-container-low p-4 rounded-xl flex flex-col justify-between min-h-[120px]"
              >
                <div className="flex justify-between items-start gap-3">
                  <span className="text-[11px] font-label tracking-[0.05em] uppercase text-outline">{stat.label}</span>
                  <span className="material-symbols-outlined text-primary text-[18px]">{stat.icon}</span>
                </div>
                <div className="mt-3">
                  <span className="text-2xl font-headline text-primary">{stat.value}</span>
                  <p className="text-xs text-on-secondary-container mt-2 leading-relaxed">{stat.copy}</p>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Admin section */}
        {canManageGaiaUsers ? (
          <div className="mb-10">
            <Link
              href="/gaia/users"
              className="flex items-center justify-between bg-surface-container-low p-6 rounded-xl hover:shadow-md transition-all duration-300 group"
            >
              <div className="flex items-center gap-4">
                <div className="w-10 h-10 bg-primary-container rounded-lg flex items-center justify-center">
                  <span className="material-symbols-outlined text-primary-fixed text-xl">manage_accounts</span>
                </div>
                <div>
                  <p className="font-medium text-primary text-sm tracking-wide">Amministrazione GAIA</p>
                  <p className="text-on-surface-variant text-sm">Utenti applicativi, ruoli e abilitazioni</p>
                </div>
              </div>
              <span className="material-symbols-outlined text-outline group-hover:text-primary transition-colors">
                arrow_forward
              </span>
            </Link>
          </div>
        ) : null}

        {/* Module domains */}
        <section>
          <div className="flex items-end justify-between mb-8">
            <div>
              <h2 className="text-3xl font-headline text-primary mb-2">Seleziona il dominio operativo</h2>
              <p className="text-outline font-body">Sistemi di controllo e gestione asset istituzionali</p>
            </div>
            <div className="flex gap-4">
              <span className="flex items-center gap-2 text-xs font-label tracking-widest uppercase text-outline">
                <span className="w-2 h-2 rounded-full bg-primary-fixed" /> Operativo
              </span>
              <span className="flex items-center gap-2 text-xs font-label tracking-widest uppercase text-outline">
                <span className="w-2 h-2 rounded-full bg-tertiary-fixed-dim" /> In sviluppo o non avviato
              </span>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {visibleModules.map((mod) => {
              const isInteractive = mod.status !== "coming";
              const card = (
                <article
                  className={cn(
                    "group bg-surface-container-lowest p-8 rounded-xl border border-outline-variant/15 transition-all duration-300 flex h-full flex-col justify-between relative overflow-hidden",
                    isInteractive
                      ? "hover:shadow-2xl cursor-pointer"
                      : "opacity-70 cursor-default",
                  )}
                >
                  {/* Status badge */}
                  <div className="absolute top-0 right-0 p-4">
                    <span
                      className={cn(
                        "inline-flex items-center rounded-full px-3 py-1 text-xs font-label uppercase tracking-wider",
                        statusBadge[mod.status],
                      )}
                    >
                      {mod.statusLabel}
                    </span>
                  </div>

                  <div>
                    <div className="w-12 h-12 bg-primary-container rounded-lg flex items-center justify-center mb-6">
                      <span className="material-symbols-outlined text-primary-fixed">{mod.icon}</span>
                    </div>
                    <p className="mb-2 text-[11px] font-label uppercase tracking-[0.18em] text-outline">{mod.eyebrow}</p>
                    <h3 className="text-2xl font-headline text-primary mb-3">{mod.title}</h3>
                    <p className="text-on-surface-variant leading-relaxed text-sm">{mod.description}</p>
                  </div>

                  <button
                    className={cn(
                      "mt-8 flex items-center gap-2 font-bold transition-all",
                      isInteractive
                        ? "text-primary group-hover:gap-4"
                        : "text-outline cursor-default",
                    )}
                    tabIndex={isInteractive ? 0 : -1}
                    aria-hidden={!isInteractive}
                  >
                    {isInteractive ? "Accedi al modulo" : "Disponibile prossimamente"}
                    <span className="material-symbols-outlined text-[18px]">arrow_forward</span>
                  </button>
                </article>
              );

              if (!isInteractive) return <div key={mod.id} className="h-full">{card}</div>;

              return (
                <Link
                  key={mod.id}
                  href={mod.href}
                  className="block h-full rounded-xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30"
                >
                  {card}
                </Link>
              );
            })}
          </div>
        </section>
      </main>

      <footer className="px-8 py-6 border-t border-outline-variant/20 max-w-[90rem] mx-auto flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 text-xs text-outline">
        <p>© GAIA platform · Consorzio di Bonifica dell&apos;Oristanese</p>
        <p>Sessione attiva: {currentUser.username} · {currentUser.role}</p>
      </footer>
    </div>
  );
}
